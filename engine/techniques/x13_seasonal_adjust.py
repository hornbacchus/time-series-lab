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

    # Binary names to look for
    if sys.platform == "win32":
        binary_names = ["x13as.exe", "x13ashtml.exe"]
    else:
        binary_names = ["x13as", "x13ashtml"]

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


def _write_x13_spec(spec_path, data_path, period, transform, outlier, start_year, start_period):
    """Write an X-13 spec file."""
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

    # automdl for ARIMA model selection
    spec_lines.append("automdl{}")
    spec_lines.append("")

    # Outlier detection
    if outlier:
        spec_lines.append("outlier{}")
        spec_lines.append("")

    # X-11 decomposition
    spec_lines.append("x11{")
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

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        transform = ctx.get_param("transform", preset_cfg["transform"])
        outlier = ctx.get_param("outlier", preset_cfg["outlier"])
        start_year = int(ctx.get_param("start_year", 2000))
        start_period = int(ctx.get_param("start_period", 1))

        # Try to infer start date from time column
        if ctx.time and len(ctx.time) > 0:
            try:
                from datetime import datetime
                first_time = str(ctx.time[0])
                # Try ISO format
                dt = datetime.fromisoformat(first_time.replace("Z", ""))
                start_year = dt.year
                start_period = dt.month if period == 12 else ((dt.month - 1) // 3 + 1)
            except (ValueError, TypeError):
                pass

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
                        "On Windows: resources/x13/x13as.exe",
                        "On macOS/Linux: resources/x13/x13as (ensure it is executable).",
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

                _write_x13_spec(spec_path, data_path, period, transform, outlier,
                               start_year, start_period)

                progress_callback("Executing X-13", 40)

                try:
                    result = subprocess.run(
                        [x13_binary, spec_path],
                        capture_output=True,
                        text=True,
                        timeout=120,
                        cwd=tmpdir,
                    )
                except subprocess.TimeoutExpired:
                    return make_error_response(
                        ctx,
                        "X-13 execution timed out after 120 seconds.",
                        error_fixes=["Try a shorter series.", "Try Fast preset."],
                    )

                if result.returncode != 0:
                    error_msg = result.stderr[:500] if result.stderr else "Unknown error"
                    return make_error_response(
                        ctx,
                        f"X-13 returned error code {result.returncode}: {error_msg}",
                        error_fixes=[
                            "Check that your data is appropriate for X-13 (monthly or quarterly).",
                            "Ensure no extreme outliers or structural breaks.",
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

                # Try standard X-13 output file names
                base = os.path.splitext(spec_path)[0]
                sa = _read_x13_output(base + ".d11")  # seasonally adjusted
                trend = _read_x13_output(base + ".d12")  # trend
                seasonal = _read_x13_output(base + ".d10")  # seasonal factors
                irregular = _read_x13_output(base + ".d13")  # irregular

                if sa is None:
                    # Fallback: try using the stdout
                    warn_list.append("Could not parse X-13 output files. Using simplified output.")
                    sa = values.copy()
                    trend = np.full(n, np.nan)
                    seasonal = np.zeros(n)
                    irregular = np.zeros(n)

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

        # Build output tables
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
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
