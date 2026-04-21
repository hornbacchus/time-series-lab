"""
Empirical Mode Decomposition & Hilbert-Huang Transform for Time Series Lab.

Decomposes a time series into Intrinsic Mode Functions (IMFs) using EMD,
then applies the Hilbert transform to obtain instantaneous frequency and
amplitude. Uses the `emd` package when available, falling back to a
numpy-based sifting implementation.
"""

import numpy as np

from techniques.base import (
    flip_sign_vector,
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _has_emd():
    try:
        import emd
        return True
    except ImportError:
        return False


_PRESET_CONFIG = {
    "Fast": {
        "max_imfs": 4,
        "max_sift_iterations": 50,
        "method": "emd",
    },
    "Balanced": {
        "max_imfs": 8,
        "max_sift_iterations": 200,
        "method": "emd",
    },
    "Thorough": {
        "max_imfs": 12,
        "max_sift_iterations": 500,
        "method": "eemd",
        "ensemble_size": 100,
        "noise_width": 0.05,
    },
}


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([]), 0
    trimmed = values[first_valid:last_valid + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
        else:
            trimmed = trimmed[~np.isnan(trimmed)]
            nan_count = 0
    return trimmed, nan_count


# ── Fallback sifting when `emd` package is not installed ──────────────

def _find_extrema(x):
    """Find indices of local maxima and minima."""
    maxima = []
    minima = []
    for i in range(1, len(x) - 1):
        if x[i] > x[i - 1] and x[i] >= x[i + 1]:
            maxima.append(i)
        elif x[i] < x[i - 1] and x[i] <= x[i + 1]:
            minima.append(i)
    return np.array(maxima, dtype=int), np.array(minima, dtype=int)


def _envelope_mean(x, maxima, minima):
    """Compute mean of upper and lower cubic-spline envelopes."""
    t = np.arange(len(x))

    if len(maxima) < 2 or len(minima) < 2:
        return np.zeros_like(x), False

    # Extend endpoints to avoid edge effects
    max_idx = np.concatenate([[0], maxima, [len(x) - 1]])
    max_val = np.concatenate([[x[0]], x[maxima], [x[-1]]])
    min_idx = np.concatenate([[0], minima, [len(x) - 1]])
    min_val = np.concatenate([[x[0]], x[minima], [x[-1]]])

    upper = np.interp(t, max_idx, max_val)
    lower = np.interp(t, min_idx, min_val)

    return (upper + lower) / 2.0, True


def _sift_one_imf(signal, max_iterations):
    """Extract one IMF via basic sifting."""
    h = signal.copy()
    for _ in range(max_iterations):
        maxima, minima = _find_extrema(h)
        if len(maxima) < 2 or len(minima) < 2:
            break
        mean_env, ok = _envelope_mean(h, maxima, minima)
        if not ok:
            break
        h_new = h - mean_env
        # Cauchy convergence criterion
        sd = np.sum((h - h_new) ** 2) / (np.sum(h ** 2) + 1e-15)
        h = h_new
        if sd < 0.001:
            break
    return h


def _numpy_emd(signal, max_imfs, max_iterations):
    """Simple EMD using numpy (fallback when emd package unavailable)."""
    imfs = []
    residual = signal.copy()

    for _ in range(max_imfs):
        maxima, minima = _find_extrema(residual)
        if len(maxima) < 2 or len(minima) < 2:
            break

        imf = _sift_one_imf(residual, max_iterations)
        imfs.append(imf)
        residual = residual - imf

        # Stop if residual is monotonic
        maxr, minr = _find_extrema(residual)
        if len(maxr) + len(minr) < 2:
            break

    return np.array(imfs) if imfs else np.empty((0, len(signal))), residual


def _numpy_eemd(signal, max_imfs, max_iterations, ensemble_size, noise_width, seed):
    """Ensemble EMD using numpy (fallback)."""
    rng = np.random.default_rng(seed)
    n = len(signal)
    accumulated = None

    for e in range(ensemble_size):
        noisy = signal + noise_width * np.std(signal) * rng.standard_normal(n)
        imfs, _ = _numpy_emd(noisy, max_imfs, max_iterations)
        if accumulated is None:
            accumulated = imfs
        else:
            # Pad to same number of IMFs
            n_imfs = max(len(accumulated), len(imfs))
            if len(accumulated) < n_imfs:
                pad = np.zeros((n_imfs - len(accumulated), n))
                accumulated = np.vstack([accumulated, pad])
            if len(imfs) < n_imfs:
                pad = np.zeros((n_imfs - len(imfs), n))
                imfs = np.vstack([imfs, pad])
            accumulated += imfs

    if accumulated is not None:
        accumulated /= ensemble_size

    residual = signal - accumulated.sum(axis=0) if accumulated is not None else signal
    return accumulated, residual


# ── Hilbert transform for instantaneous frequency/amplitude ───────────

def _hilbert_transform(imfs):
    """Compute instantaneous amplitude and frequency via Hilbert transform."""
    from scipy.signal import hilbert

    n_imfs, n_pts = imfs.shape
    inst_amp = np.zeros_like(imfs)
    inst_freq = np.zeros_like(imfs)

    for i in range(n_imfs):
        analytic = hilbert(imfs[i])
        inst_amp[i] = np.abs(analytic)
        phase = np.unwrap(np.angle(analytic))
        # Instantaneous frequency = d(phase)/dt / (2*pi)
        inst_freq[i, 1:] = np.diff(phase) / (2.0 * np.pi)
        inst_freq[i, 0] = inst_freq[i, 1] if n_pts > 1 else 0.0

    return inst_amp, inst_freq


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Empirical Mode Decomposition with Hilbert-Huang Transform.

    Parameters (via ctx.params)
    ---------------------------
    max_imfs : int, optional
        Maximum number of IMFs to extract. Default from preset.
    method : str, optional
        "emd" (standard) or "eemd" (ensemble). Default from preset.
    ensemble_size : int, optional
        Number of ensemble trials for EEMD. Default 100.
    noise_width : float, optional
        Noise amplitude for EEMD as fraction of signal std. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")

        n = len(clean)
        if n < 20:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "EMD needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        max_imfs = int(ctx.get_param("max_imfs", preset_cfg["max_imfs"]))
        max_sift = preset_cfg["max_sift_iterations"]
        method = ctx.get_param("method", preset_cfg.get("method", "emd")).lower()
        ensemble_size = int(ctx.get_param("ensemble_size", preset_cfg.get("ensemble_size", 100)))
        noise_width = float(ctx.get_param("noise_width", preset_cfg.get("noise_width", 0.05)))

        use_emd_lib = _has_emd()
        backend = "emd_library" if use_emd_lib else "numpy_fallback"

        if not use_emd_lib:
            warn_list.append(
                "The 'emd' package is not installed. Using numpy fallback. "
                "Install emd (pip install emd) for optimized sifting and EEMD/CEEMDAN."
            )

        progress_callback("Decomposing signal", 15)

        if use_emd_lib:
            import emd as emd_lib

            if method == "eemd":
                progress_callback("Running Ensemble EMD", 20)
                imfs = emd_lib.sift.ensemble_sift(
                    clean,
                    max_imfs=max_imfs,
                    nensembles=ensemble_size,
                    noise_amp=noise_width,
                    nprocesses=1,
                )
            else:
                imfs = emd_lib.sift.sift(clean, max_imfs=max_imfs)

            # emd library returns (n_samples, n_imfs) — transpose to (n_imfs, n_samples)
            if imfs.ndim == 2:
                imfs = imfs.T
                # Last row is residual
                if imfs.shape[0] > 1:
                    residual = imfs[-1]
                    imfs = imfs[:-1]
                else:
                    residual = np.zeros(n)
            else:
                residual = np.zeros(n)
        else:
            if method == "eemd":
                progress_callback("Running Ensemble EMD (numpy)", 20)
                imfs, residual = _numpy_eemd(
                    clean, max_imfs, max_sift, ensemble_size, noise_width, ctx.seed
                )
            else:
                imfs, residual = _numpy_emd(clean, max_imfs, max_sift)

        # Sign-normalize each IMF. EMD sifting is a nonlinear iterative
        # procedure and both the `emd` library and the numpy fallback can
        # return IMFs with flipped signs for equivalent data (depends on
        # initialization, extrema detection, library version). Mathematics
        # of the reconstruction (sum of IMFs ≈ signal) is invariant to
        # per-component sign flips AS LONG AS the residual absorbs the
        # flip, but from a user-chart perspective an oscillatory
        # component should have a stable orientation run-to-run. Use
        # the same "largest-absolute entry positive" convention as SVD.
        # Adjust the residual so the total reconstruction is unchanged.
        imfs = np.asarray(imfs) if not isinstance(imfs, np.ndarray) else imfs
        for i in range(len(imfs)):
            flipped = flip_sign_vector(imfs[i])
            if not np.array_equal(flipped, imfs[i]):
                # Sign was flipped — compensate the residual so that
                # sum(imfs) + residual stays equal to the original signal.
                delta = flipped - imfs[i]
                imfs[i] = flipped
                residual = residual - delta  # subtract the added signal

        n_imfs = len(imfs) if len(imfs) > 0 else 0

        if n_imfs == 0:
            return make_error_response(
                ctx,
                "EMD could not extract any Intrinsic Mode Functions. "
                "The series may be too short or monotonic.",
                error_fixes=[
                    "Provide a longer series with oscillatory behavior.",
                    "Check that the data is not constant or purely linear.",
                ],
            )

        progress_callback("Hilbert transform", 55)

        # Hilbert-Huang analysis
        inst_amp, inst_freq = _hilbert_transform(imfs)

        progress_callback("Building output tables", 80)

        # ── IMF summary table ──
        imf_rows = []
        total_var = float(np.var(clean))
        for i in range(n_imfs):
            imf_var = float(np.var(imfs[i]))
            var_pct = (imf_var / total_var * 100) if total_var > 0 else 0.0
            mean_freq = float(np.mean(np.abs(inst_freq[i, 1:])))
            mean_amp = float(np.mean(inst_amp[i]))
            # Estimate period from mean frequency
            mean_period = 1.0 / mean_freq if mean_freq > 1e-10 else float('inf')

            imf_rows.append([
                f"IMF {i + 1}",
                round(imf_var, 6),
                round(var_pct, 2),
                round(mean_freq, 6),
                round(mean_period, 2) if mean_period < 1e6 else "∞",
                round(mean_amp, 6),
            ])

        # Residual row
        res_var = float(np.var(residual))
        res_pct = (res_var / total_var * 100) if total_var > 0 else 0.0
        imf_rows.append(["Residual", round(res_var, 6), round(res_pct, 2), "-", "-", "-"])

        imf_table = make_table(
            "IMF Summary",
            ["Component", "Variance", "Variance %", "Mean Freq (cycles/sample)",
             "Mean Period (samples)", "Mean Amplitude"],
            imf_rows,
        )

        # ── IMF values table (subsampled for large series) ──
        max_rows = 200 if ctx.preset == "Fast" else (500 if ctx.preset == "Balanced" else n)
        step = max(1, n // max_rows)
        indices = list(range(0, n, step))

        imf_val_cols = ["Index"] + [f"IMF {i + 1}" for i in range(n_imfs)] + ["Residual"]
        imf_val_rows = []
        for idx in indices:
            row = [idx + 1]
            for i in range(n_imfs):
                row.append(round(float(imfs[i][idx]), 6))
            row.append(round(float(residual[idx]), 6))
            imf_val_rows.append(row)

        imf_val_table = make_table("IMF Components", imf_val_cols, imf_val_rows)

        # ── Instantaneous frequency table (subsampled) ──
        freq_cols = ["Index"] + [f"IMF {i + 1} Freq" for i in range(n_imfs)]
        freq_rows = []
        for idx in indices:
            row = [idx + 1]
            for i in range(n_imfs):
                row.append(round(float(inst_freq[i][idx]), 6))
            freq_rows.append(row)

        freq_table = make_table("Instantaneous Frequency", freq_cols, freq_rows)

        # ── Configuration table ──
        config_rows = [
            ["Method", method.upper()],
            ["Backend", backend],
            ["Max IMFs", max_imfs],
            ["Extracted IMFs", n_imfs],
            ["Series Length", n],
            ["Seed", ctx.seed],
            ["Preset", ctx.preset],
        ]
        if method == "eemd":
            config_rows.append(["Ensemble Size", ensemble_size])
            config_rows.append(["Noise Width", noise_width])
        config_table = make_table("Configuration", ["Parameter", "Value"], config_rows)

        # ── Plain English summary ──
        dominant_imf = int(np.argmax([np.var(imfs[i]) for i in range(n_imfs)])) + 1
        dominant_pct = float(np.var(imfs[dominant_imf - 1]) / total_var * 100) if total_var > 0 else 0

        plain_english = (
            f"Empirical Mode Decomposition ({method.upper()}) of '{name}' "
            f"({n} observations) extracted {n_imfs} Intrinsic Mode Functions. "
            f"IMF {dominant_imf} carries the most variance ({dominant_pct:.1f}% of total). "
            f"The residual accounts for {res_pct:.1f}% of variance."
        )

        charting = (
            "Multi-panel plot: original series on top, each IMF below, residual at bottom. "
            "Hilbert-Huang spectrum: time on x-axis, frequency on y-axis, amplitude as color. "
            "Bar chart of variance contribution per IMF."
        )

        progress_callback("Done", 100)

        # Prompt C4: per-IMF periods for Tier 1 citation.
        per_imf_periods = []
        for row in imf_rows:
            if row[0] != "Residual":
                p = row[4]
                per_imf_periods.append(float(p) if isinstance(p, (int, float)) else None)
        dominant_imf_period = None
        if dominant_imf is not None and 1 <= int(dominant_imf) <= len(per_imf_periods):
            dominant_imf_period = per_imf_periods[int(dominant_imf) - 1]

        audit = {
            "backend": backend,
            "method": method,
            "n_imfs": n_imfs,
            "max_imfs": max_imfs,
            "n_observations": n,
            "dominant_imf": dominant_imf,
            "dominant_imf_variance_pct": round(dominant_pct, 2),
            "dominant_imf_period": dominant_imf_period,
            "per_imf_periods": per_imf_periods,
            "residual_variance_pct": round(res_pct, 2),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        _interp_dict["series_name"] = name
        _interp_dict["n_obs"] = n
        interp = build_interpretation("emd_hht", _interp_dict)

        return make_response(
            ctx,
            tables=[imf_table, imf_val_table, freq_table, config_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"EMD/Hilbert-Huang transform failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try standard EMD if EEMD fails.",
                "Install emd (pip install emd) for optimized implementation.",
                "Check that scipy is installed for the Hilbert transform.",
            ],
        )
