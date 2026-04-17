"""
X-13 ARIMA-SEATS Seasonal Adjustment for Time Series Lab.

Wraps the US Census Bureau's X-13ARIMA-SEATS program for seasonal adjustment.
Looks for the x13 binary in ../resources/x13/. If not found, returns a clear
error message with installation instructions.
"""

import os
import sys
import tempfile
import subprocess
import numpy as np
import warnings as _warnings

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"transform": "auto", "outlier": False},
    "Balanced": {"transform": "auto", "outlier": True},
    "Thorough": {"transform": "auto", "outlier": True},
}


def _find_x13_binary():
    """
    Search for x13 binary in standard locations.
    Returns path to binary or None.
    """
    # Check relative to the engine directory
    engine_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_dir = os.path.dirname(engine_dir)

    search_paths = [
        os.path.join(project_dir, "resources", "x13"),
        os.path.join(project_dir, "resources", "x13arima"),
        os.path.join(engine_dir, "resources", "x13"),
        os.path.join(project_dir, "x13"),
    ]

    # Binary names to look for. Census ships builds named "x13as_html.exe"
    # / "x13as_ascii.exe" (current, e.g. v1-1-b62, 2024-07) and older
    # builds sometimes named "x13as.exe" / "x13ashtml.exe".
    if sys.platform == "win32":
        binary_names = [
            "x13as_html.exe", "x13as_ascii.exe",
            "x13ashtml.exe", "x13as.exe",
        ]
    else:
        binary_names = [
            "x13as_html", "x13as_ascii",
            "x13ashtml", "x13as",
        ]

    for search_dir in search_paths:
        if os.path.isdir(search_dir):
            for bname in binary_names:
                bpath = os.path.join(search_dir, bname)
                if os.path.isfile(bpath):
                    return bpath

    # Check if it's on PATH
    for bname in binary_names:
        try:
            result = subprocess.run(
                [bname, "--help"],
                capture_output=True,
                timeout=5,
            )
            return bname  # found on PATH
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue

    return None


def _infer_period(ctx):
    """Infer period from frequency."""
    user_period = ctx.get_param("period")
    if user_period is not None:
        return int(user_period)
    freq_map = {
        "M": 12, "MS": 12, "Q": 4, "QS": 4,
    }
    f = (ctx.frequency or "").strip().upper()
    return freq_map.get(f, None)


def _write_x13_spec(spec_path, data_path, period, transform, outlier,
                    start_year, start_period, arima_model=None,
                    covid_outliers=False, n_obs=0):
    """Write an X-13 spec file.

    If ``arima_model`` is None, use automdl (automatic model selection).
    Otherwise supply the model as a tuple/string (e.g. "(0 1 1)(0 1 1)") to
    use a fixed ARIMA specification — useful as a fallback when automdl
    fails to converge on long or difficult series.

    If ``covid_outliers`` is True AND the series covers March/April 2020
    AND the frequency is monthly (period=12), add BLS-style pandemic
    outlier regressors: AO at March 2020, LS at April 2020. This matches
    how BLS treats the CES payroll series during the pandemic.
    """
    spec_lines = []
    spec_lines.append("series{")
    spec_lines.append(f'  file = "{data_path}"')
    spec_lines.append(f"  period = {period}")
    spec_lines.append(f"  start = {start_year}.{start_period}")
    spec_lines.append("}")
    spec_lines.append("")

    # Transform
    if transform == "auto":
        spec_lines.append("transform{")
        spec_lines.append("  function = auto")
        spec_lines.append("}")
    elif transform == "log":
        spec_lines.append("transform{")
        spec_lines.append("  function = log")
        spec_lines.append("}")
    # else: no transform

    spec_lines.append("")

    # Pandemic outlier regressors (BLS-style). Only add if the series is
    # monthly and actually spans March/April 2020.
    covid_regressors = []
    if covid_outliers and period == 12 and n_obs > 0:
        # Compute [start, end] as (year, month) of the truncated series.
        total_start_idx = (start_year * 12 + (start_period - 1))
        total_end_idx = total_start_idx + n_obs - 1
        mar20_idx = 2020 * 12 + 2   # March (0-based month = 2)
        apr20_idx = 2020 * 12 + 3
        if total_start_idx <= mar20_idx <= total_end_idx:
            covid_regressors.append("ao2020.mar")
        if total_start_idx <= apr20_idx <= total_end_idx:
            covid_regressors.append("ls2020.apr")
        if covid_regressors:
            spec_lines.append("regression{")
            spec_lines.append("  variables = (" + " ".join(covid_regressors) + ")")
            spec_lines.append("}")
            spec_lines.append("")

    if arima_model is None:
        # Automatic model selection
        spec_lines.append("automdl{")
        spec_lines.append("  savelog = amd")
        spec_lines.append("}")
    else:
        # Fixed ARIMA model with liberal iteration limits to help
        # convergence on long or outlier-heavy series.
        spec_lines.append("arima{")
        spec_lines.append(f"  model = {arima_model}")
        spec_lines.append("}")
        spec_lines.append("")
        spec_lines.append("estimate{")
        spec_lines.append("  maxiter = 1500")
        spec_lines.append("  tol = 1.0e-4")
        spec_lines.append("}")
    spec_lines.append("")

    # Outlier detection
    if outlier:
        spec_lines.append("outlier{}")
        spec_lines.append("")

    # X-11 decomposition. Default X-11 mode is "mult" (multiplicative),
    # which requires strictly positive values. When the caller chose no
    # transform (typical for change/flow series with negatives), force
    # additive decomposition instead.
    spec_lines.append("x11{")
    if transform == "none":
        spec_lines.append("  mode = add")
    spec_lines.append("  save = (d10 d11 d12 d13)")
    spec_lines.append("}")

    with open(spec_path, "w") as f:
        f.write("\n".join(spec_lines))


def _try_statsmodels_x13(values, period, start_date, transform, warn_list):
    """
    Attempt to use statsmodels x13_arima_analysis as an alternative.
    This requires x13 binary to be findable by statsmodels too.
    """
    try:
        import pandas as pd
        from statsmodels.tsa.x13 import x13_arima_analysis

        # Create a pandas series with proper index
        if start_date:
            idx = pd.date_range(start=start_date, periods=len(values), freq="MS" if period == 12 else "QS")
        else:
            idx = pd.date_range(start="2000-01-01", periods=len(values), freq="MS" if period == 12 else "QS")

        ts = pd.Series(values, index=idx)

        result = x13_arima_analysis(
            ts,
            log=True if transform == "log" else (None if transform == "auto" else False),
        )
        return result
    except Exception as e:
        warn_list.append(f"statsmodels x13 wrapper also failed: {e}")
        return None


def run(ctx: RunContext, progress_callback) -> dict:
    """
    X-13 ARIMA-SEATS seasonal adjustment.

    Parameters (via ctx.params)
    ---------------------------
    period : int, optional
        Seasonal period (12 for monthly, 4 for quarterly). Auto-inferred from frequency.
    transform : str, optional
        "auto" (default), "log", or "none".
    outlier : bool, optional
        Whether to detect outliers. Default from preset.
    start_year : int, optional
        Start year of the series. Default 2000.
    start_period : int, optional
        Start period (month or quarter). Default 1.
    fit_window_obs : int, optional
        Number of most recent observations to fit on (rolling window). Default
        120 for monthly, 40 for quarterly — matches BLS CES concurrent
        seasonal adjustment practice. Set to 0 (or negative) to use all
        available data, subject to X-13's 85-year program limit.
    covid_outliers : bool, optional
        When True, add BLS-style pandemic outlier regressors to the regARIMA
        specification: an additive outlier at March 2020 (ao2020.mar) and a
        level shift at April 2020 (ls2020.apr). Matches the intervention
        analysis BLS uses for the CES payroll series (PAYEMS/PAYNSA).
        No-op if the fit window does not cover March-April 2020 or if the
        data is not monthly. Default False.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        # Check for NaN
        nan_mask = np.isnan(values)
        n_missing = int(nan_mask.sum())
        if n_missing > 0:
            # X-13 can handle some missing values but not many
            if n_missing > len(values) * 0.1:
                return make_error_response(
                    ctx,
                    f"Series has {n_missing} missing values ({n_missing/len(values)*100:.0f}%). "
                    "X-13 cannot handle more than ~10% missing values.",
                    error_fixes=[
                        "Impute missing values first (try Kalman or LOESS imputation).",
                        "Remove rows with missing values.",
                    ],
                )
            warn_list.append(f"{n_missing} missing values detected. X-13 will attempt to handle them.")

        n = len(values)
        period = _infer_period(ctx)
        if period is None:
            return make_error_response(
                ctx,
                "Cannot infer seasonal period from frequency. "
                "X-13 requires monthly (period=12) or quarterly (period=4) data.",
                error_fixes=[
                    "Set period=12 for monthly data or period=4 for quarterly data.",
                    "Ensure the frequency is set to 'M', 'MS', 'Q', or 'QS'.",
                ],
            )

        if period not in (4, 12):
            return make_error_response(
                ctx,
                f"X-13 only supports monthly (period=12) or quarterly (period=4) data. "
                f"Got period={period}.",
                error_fixes=[
                    "X-13 is designed for monthly or quarterly economic time series.",
                    "Use STL decomposition for other frequencies.",
                ],
            )

        if n < 3 * period:
            return make_error_response(
                ctx,
                f"Series has {n} observations but X-13 needs at least {3 * period} "
                f"(3 full seasonal cycles) for period={period}.",
                error_fixes=["Provide a longer time series."],
            )

        # Determine the effective fit window. Two caps apply:
        #   1. Hard cap of 83 years (997 months / 332 quarters) to stay under
        #      X-13's 85-year program limit after forecast augmentation.
        #   2. User-specified rolling window via fit_window_obs (default 120
        #      months / 40 quarters, matching BLS CES practice). Pass 0 or
        #      a negative value to disable and use all data up to the hard cap.
        hard_cap_years = 83
        hard_cap_obs = hard_cap_years * period

        default_window = 10 * period  # 120 months / 40 quarters
        user_window_raw = ctx.get_param("fit_window_obs", default_window)
        try:
            user_window = int(user_window_raw) if user_window_raw is not None else 0
        except (TypeError, ValueError):
            user_window = default_window

        if user_window and user_window > 0:
            effective_cap = min(user_window, hard_cap_obs)
        else:
            effective_cap = hard_cap_obs

        truncated_time = ctx.time
        if n > effective_cap:
            dropped = n - effective_cap
            years_kept = effective_cap / period
            if user_window and user_window > 0 and effective_cap == user_window:
                # Truncation driven by the user's rolling-window choice.
                warn_list.append(
                    f"Fit window set to {effective_cap} observations "
                    f"(~{years_kept:.0f} years); dropped {dropped} older "
                    f"observation(s). BLS-style concurrent adjustment uses "
                    f"~{default_window} observations. "
                    f"Set fit_window_obs=0 to use all data."
                )
            else:
                # Truncation driven by X-13's 85-year hard limit.
                warn_list.append(
                    f"Series spans {n/period:.1f} years, exceeds X-13's "
                    f"85-year program limit. Using most recent {effective_cap} "
                    f"observations ({years_kept:.0f} years); dropped {dropped} "
                    f"oldest observation(s)."
                )
            values = values[-effective_cap:]
            nan_mask = nan_mask[-effective_cap:]
            if ctx.time and len(ctx.time) >= effective_cap:
                truncated_time = list(ctx.time)[-effective_cap:]
            n = len(values)

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        transform = ctx.get_param("transform", preset_cfg["transform"])
        outlier = ctx.get_param("outlier", preset_cfg["outlier"])
        start_year = int(ctx.get_param("start_year", 2000))
        start_period = int(ctx.get_param("start_period", 1))

        # Auto / log transform require strictly positive values. Payroll job
        # gains, trade balances, and other change/flow series routinely have
        # zeros or negatives, so fall back to no transform with a warning if
        # the user didn't explicitly pick one.
        user_supplied_transform = ctx.get_param("transform") is not None
        has_nonpositive = bool(np.any((~nan_mask) & (values <= 0)))
        if transform in ("auto", "log") and has_nonpositive and not user_supplied_transform:
            warn_list.append(
                f"Series contains zero or negative values, which are incompatible "
                f"with transform='{transform}'. Running without a transform."
            )
            transform = "none"

        # BLS-style pandemic outlier regressors. Accept booleans and common
        # string forms ("true", "yes", "1"). Only meaningful for monthly data.
        _raw_covid = ctx.get_param("covid_outliers", False)
        if isinstance(_raw_covid, str):
            covid_outliers = _raw_covid.strip().lower() in ("1", "true", "yes", "on")
        else:
            covid_outliers = bool(_raw_covid)

        # Try to infer start date from time column (use the truncated time
        # array so the start date matches the truncated values). This must
        # happen BEFORE the COVID-range pre-flight below, which reads
        # start_year / start_period.
        if truncated_time and len(truncated_time) > 0:
            try:
                from datetime import datetime
                first_time = str(truncated_time[0])
                # Try ISO format
                dt = datetime.fromisoformat(first_time.replace("Z", ""))
                start_year = dt.year
                start_period = dt.month if period == 12 else ((dt.month - 1) // 3 + 1)
            except (ValueError, TypeError):
                pass

        # Predict which COVID regressors will actually be added so we can
        # surface a clear warning if the user asked for them. The spec
        # writer computes the same condition from start_year, start_period,
        # and n.
        if covid_outliers:
            if period != 12:
                warn_list.append(
                    "BLS-style COVID outlier adjustments were requested but "
                    "only apply to monthly data; skipped."
                )
                covid_outliers = False
            else:
                total_start_idx = start_year * 12 + (start_period - 1)
                total_end_idx = total_start_idx + n - 1
                mar20 = 2020 * 12 + 2
                apr20 = 2020 * 12 + 3
                applied = []
                if total_start_idx <= mar20 <= total_end_idx:
                    applied.append("AO March 2020")
                if total_start_idx <= apr20 <= total_end_idx:
                    applied.append("LS April 2020")
                if applied:
                    warn_list.append(
                        "BLS-style COVID outlier adjustments applied: "
                        + ", ".join(applied) + "."
                    )
                else:
                    warn_list.append(
                        "BLS-style COVID outlier adjustments were requested "
                        "but the series does not cover March-April 2020; "
                        "no regressors added."
                    )

        progress_callback("Searching for X-13 binary", 15)

        x13_binary = _find_x13_binary()

        if x13_binary is None:
            # Try statsmodels as last resort
            progress_callback("X-13 binary not found, trying statsmodels wrapper", 20)
            start_date_str = f"{start_year}-{start_period:02d}-01" if period == 12 else None

            sm_result = _try_statsmodels_x13(
                values[~nan_mask] if n_missing > 0 else values,
                period, start_date_str, transform, warn_list,
            )

            if sm_result is None:
                return make_error_response(
                    ctx,
                    "X-13 ARIMA-SEATS binary not found. "
                    "The X-13 seasonal adjustment program must be installed separately.",
                    error_fixes=[
                        "Download X-13 from the US Census Bureau: "
                        "https://www.census.gov/data/software/x13as.html",
                        "Place the x13as executable in the 'resources/x13/' folder "
                        "relative to the project root.",
                        "On Windows: resources/x13/x13as_html.exe "
                        "(or x13as_ascii.exe).",
                        "On macOS/Linux: resources/x13/x13as_html "
                        "(or x13as_ascii) — make it executable with chmod +x.",
                        "Alternatively, install via conda: conda install -c conda-forge x13as",
                        "As a workaround, use the STL Decomposition technique instead.",
                    ],
                )

            # Parse statsmodels result
            progress_callback("Processing statsmodels X-13 result", 60)
            sa = np.array(sm_result.seasadj)
            trend = np.array(sm_result.trend)
            seasonal = values[:len(sa)] - sa  # approximate
            irregular = sa - trend

            clean_values = values[~nan_mask] if n_missing > 0 else values
            backend_note = "statsmodels x13 wrapper"
        else:
            progress_callback("Running X-13 ARIMA-SEATS", 25)

            with tempfile.TemporaryDirectory() as tmpdir:
                data_path = os.path.join(tmpdir, "input.dat")
                spec_path = os.path.join(tmpdir, "input.spc")

                # Write data file (one value per line)
                with open(data_path, "w") as f:
                    for v in values:
                        if np.isnan(v):
                            f.write("-999\n")
                        else:
                            f.write(f"{v}\n")

                # X-13 requires the spec filename *without* the .spc extension.
                # Passing "input.spc" makes X-13 look for "input.spc.spc" and
                # fail — but it still returns exit code 0, so the outer
                # returncode check below won't catch it.
                spec_stem = os.path.splitext(spec_path)[0]

                def _invoke_x13(arima_model):
                    """Write the spec and invoke X-13. Returns (result, hard_fail, combined)."""
                    # Remove any output files from a prior attempt so we
                    # don't pick up stale .d11 etc. from the earlier run.
                    for fname in list(os.listdir(tmpdir)):
                        if fname.startswith(os.path.basename(spec_stem) + ".") \
                                and not fname.endswith(".dat") \
                                and not fname.endswith(".spc"):
                            try:
                                os.remove(os.path.join(tmpdir, fname))
                            except OSError:
                                pass
                    _write_x13_spec(
                        spec_path, data_path, period, transform, outlier,
                        start_year, start_period, arima_model=arima_model,
                        covid_outliers=covid_outliers, n_obs=n,
                    )
                    r = subprocess.run(
                        [x13_binary, spec_stem],
                        capture_output=True, text=True, timeout=120, cwd=tmpdir,
                    )
                    combined = (r.stdout or "") + "\n" + (r.stderr or "")
                    # X-13 frequently writes the real error text to
                    # input_err.html while stdout shows only a generic
                    # "program halted" line. Append the stripped HTML body
                    # so downstream marker detection (and error message
                    # extraction) can see it.
                    err_file = os.path.join(tmpdir, "input_err.html")
                    if os.path.exists(err_file):
                        try:
                            import re as _re
                            with open(err_file, "r", errors="replace") as _f:
                                _html = _f.read()
                            _html = _re.sub(r"<style[^>]*>.*?</style>", " ",
                                            _html, flags=_re.DOTALL | _re.IGNORECASE)
                            _html = _re.sub(r"<script[^>]*>.*?</script>", " ",
                                            _html, flags=_re.DOTALL | _re.IGNORECASE)
                            _html = _re.sub(r"<[^>]+>", " ", _html)
                            _html = _re.sub(r"&nbsp;", " ", _html)
                            _html = _re.sub(r"\s+", " ", _html).strip()
                            combined += "\n" + _html
                        except Exception:
                            pass
                    hf = (
                        r.returncode != 0
                        or "Program error(s) halt execution" in combined
                        or "ERROR:" in combined
                    )
                    return r, hf, combined

                progress_callback("Executing X-13", 40)
                try:
                    result, hard_fail, combined_output = _invoke_x13(arima_model=None)
                except subprocess.TimeoutExpired:
                    return make_error_response(
                        ctx,
                        "X-13 execution timed out after 120 seconds.",
                        error_fixes=["Try a shorter series.", "Try Fast preset."],
                    )

                # Chain of fallbacks for convergence failures. Each retry
                # uses a progressively simpler ARIMA specification:
                #   1. automdl (already tried above) — flexible but can fail
                #      on long, noisy, or pre-differenced series.
                #   2. (0 1 1)(0 1 1) — classical airline model; X-11 default.
                #   3. (0 0 1)(0 1 1) — MA-only non-seasonal; suits
                #      already-differenced series (e.g. "job gains").
                #   4. (0 0 0)(0 1 1) — pure seasonal MA; simplest stable model.
                def _is_convergence_failure(combined):
                    return (
                        "failed to converge" in combined
                        or "maximum iterations" in combined
                        or "automdl" in combined.lower()
                    )

                fallback_models = [
                    ("(0 1 1)(0 1 1)", "classical airline model"),
                    ("(0 0 1)(0 1 1)", "MA-only non-seasonal model "
                                       "(suits pre-differenced series)"),
                    ("(0 0 0)(0 1 1)", "seasonal-MA-only model"),
                ]

                for model_spec, model_desc in fallback_models:
                    if not hard_fail or not _is_convergence_failure(combined_output):
                        break
                    progress_callback(f"Retrying with {model_desc}", 50)
                    warn_list.append(
                        f"ARIMA estimation did not converge with previous "
                        f"model; retrying with {model_desc} {model_spec}."
                    )
                    try:
                        result, hard_fail, combined_output = _invoke_x13(
                            arima_model=model_spec
                        )
                    except subprocess.TimeoutExpired:
                        return make_error_response(
                            ctx,
                            f"X-13 {model_desc} retry timed out after 120 seconds.",
                            error_fixes=["Try a shorter series.", "Try Fast preset."],
                        )
                if hard_fail:
                    # Prefer clean ERROR: lines from stdout/stderr — they are
                    # far more readable than the HTML error file, which is
                    # mostly boilerplate styling.
                    import re as _re
                    err_lines = []
                    for line in combined_output.splitlines():
                        s = line.rstrip()
                        if not s:
                            continue
                        if "ERROR:" in s or "error in " in s.lower():
                            err_lines.append(s.strip())
                            continue
                        # Continuation lines from a multi-line ERROR block
                        # (X-13 typically indents continuation with spaces)
                        if err_lines and line.startswith(" " * 6):
                            err_lines.append(s.strip())
                    err_msg = " ".join(err_lines)[:500] if err_lines else ""

                    # Fall back to the HTML error file with style/script
                    # blocks stripped.
                    if not err_msg:
                        err_file = os.path.join(tmpdir, "input_err.html")
                        if os.path.exists(err_file):
                            try:
                                with open(err_file, "r", errors="replace") as _f:
                                    html = _f.read()
                                html = _re.sub(r"<style[^>]*>.*?</style>", " ",
                                               html, flags=_re.DOTALL | _re.IGNORECASE)
                                html = _re.sub(r"<script[^>]*>.*?</script>", " ",
                                               html, flags=_re.DOTALL | _re.IGNORECASE)
                                html = _re.sub(r"<[^>]+>", " ", html)
                                html = _re.sub(r"\s+", " ", html).strip()
                                err_msg = html[:500]
                            except Exception:
                                pass

                    error_msg = err_msg or (combined_output[-500:] if combined_output else "Unknown error")
                    return make_error_response(
                        ctx,
                        f"X-13 halted execution (code {result.returncode}): {error_msg}",
                        error_fixes=[
                            "Check that your data is appropriate for X-13 (monthly or quarterly).",
                            "Ensure no extreme outliers or structural breaks.",
                            "Try transform=none if the series contains zeros or negatives.",
                        ],
                    )

                progress_callback("Parsing X-13 output", 60)

                # Parse output files
                def _read_x13_output(filepath):
                    if not os.path.exists(filepath):
                        return None
                    with open(filepath, "r") as f:
                        lines = f.readlines()
                    vals = []
                    for line in lines:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            parts = line.split()
                            if len(parts) >= 2:
                                try:
                                    vals.append(float(parts[-1]))
                                except ValueError:
                                    continue
                    return np.array(vals) if vals else None

                # Try standard X-13 output file names. Files are created
                # in the cwd (tmpdir) using the spec stem as the base.
                sa = _read_x13_output(spec_stem + ".d11")  # seasonally adjusted
                trend = _read_x13_output(spec_stem + ".d12")  # trend
                seasonal = _read_x13_output(spec_stem + ".d10")  # seasonal factors
                irregular = _read_x13_output(spec_stem + ".d13")  # irregular

                if sa is None:
                    # X-13 finished but produced no d11 table — surface this
                    # instead of silently returning the raw input. List any
                    # files we did see so the user can diagnose.
                    present = sorted(
                        f for f in os.listdir(tmpdir)
                        if f.startswith(os.path.basename(spec_stem))
                    )
                    return make_error_response(
                        ctx,
                        "X-13 did not produce a seasonally-adjusted series "
                        "(.d11 file missing). "
                        f"Files present: {', '.join(present) or '(none)'}",
                        error_fixes=[
                            "Check that the series has clear seasonality (12 or 4 periods).",
                            "Try transform=none if the series contains zeros or negatives.",
                            "Try period=4 for quarterly data if period=12 was inferred wrongly.",
                        ],
                    )

            backend_note = f"X-13 binary ({x13_binary})"
            clean_values = values

        progress_callback("Building output", 80)

        # Ensure all arrays are the right length
        def _pad_or_trim(arr, target_len):
            if arr is None:
                return np.full(target_len, np.nan)
            if len(arr) >= target_len:
                return arr[:target_len]
            return np.concatenate([arr, np.full(target_len - len(arr), np.nan)])

        sa = _pad_or_trim(sa, n)
        trend = _pad_or_trim(trend, n)
        seasonal = _pad_or_trim(seasonal, n)
        irregular = _pad_or_trim(irregular, n)

        # Build output tables — use the (possibly truncated) time array,
        # falling back to a 1..n integer index only if no time column is
        # available.
        if truncated_time and len(truncated_time) == n:
            time_col = truncated_time
        elif ctx.time and len(ctx.time) == n:
            time_col = ctx.time
        else:
            time_col = list(range(1, n + 1))
        decomp_rows = []
        for i in range(n):
            decomp_rows.append([
                time_col[i],
                values[i],
                float(sa[i]) if not np.isnan(sa[i]) else None,
                float(trend[i]) if not np.isnan(trend[i]) else None,
                float(seasonal[i]) if not np.isnan(seasonal[i]) else None,
                float(irregular[i]) if not np.isnan(irregular[i]) else None,
            ])
        decomp_table = make_table(
            "X-13 Decomposition",
            ["Time", name, "Seasonally Adjusted", "Trend", "Seasonal", "Irregular"],
            decomp_rows,
        )

        # Seasonal strength
        valid_seasonal = seasonal[~np.isnan(seasonal)]
        valid_irregular = irregular[~np.isnan(irregular)]
        if len(valid_seasonal) > 1 and len(valid_irregular) > 1:
            var_ir = np.var(valid_irregular, ddof=1)
            var_sir = np.var(valid_seasonal + valid_irregular, ddof=1) if len(valid_seasonal) == len(valid_irregular) else 1.0
            seasonal_strength = max(0.0, 1.0 - var_ir / var_sir) if var_sir > 0 else 0.0
        else:
            seasonal_strength = 0.0

        diag_rows = [
            ["Backend", backend_note],
            ["Period", period],
            ["Transform", transform],
            ["Outlier Detection", outlier],
            ["Start", f"{start_year}.{start_period}"],
            ["Observations", n],
            ["Seasonal Strength", round(seasonal_strength, 4)],
        ]
        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        s_pct = round(seasonal_strength * 100, 1)
        if seasonal_strength > 0.6:
            strength_desc = f"Strong seasonality detected ({s_pct}%)"
        elif seasonal_strength > 0.3:
            strength_desc = f"Moderate seasonality ({s_pct}%)"
        else:
            strength_desc = f"Weak seasonality ({s_pct}%)"

        plain_english = (
            f"X-13 ARIMA-SEATS seasonal adjustment of '{name}' ({n} observations, "
            f"period={period}). {strength_desc}. "
            f"Seasonal adjustment performed using {backend_note}."
        )

        charting = (
            "Line chart with 4 panels stacked vertically: "
            "Original + Seasonally Adjusted (overlaid), Trend, Seasonal Factors, Irregular. "
            "Use a shared x-axis."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[decomp_table, diag_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "backend": backend_note,
                "period": period,
                "transform": transform,
                "outlier": outlier,
                "start_year": start_year,
                "start_period": start_period,
                "seasonal_strength": round(seasonal_strength, 4),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"X-13 seasonal adjustment failed: {e}",
            error_fixes=[
                "Ensure X-13 binary is installed in resources/x13/.",
                "Download from: https://www.census.gov/data/software/x13as.html",
                "Check that your data is monthly or quarterly.",
                "Use STL decomposition as an alternative.",
            ],
        )
