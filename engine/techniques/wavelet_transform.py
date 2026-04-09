"""
Wavelet Decomposition for Time Series Lab.

Decomposes a time series into frequency sub-bands at different scales using
the Discrete Wavelet Transform (DWT) from the ``pywt`` (PyWavelets) package.
This reveals time-localised frequency content that FFT cannot capture.
"""

import numpy as np
import pywt

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _prepare_series(values):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([]), 0
    trimmed = values[first:last + 1].copy()
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


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run discrete wavelet decomposition on the primary series.

    Parameters (via ctx.params)
    ---------------------------
    wavelet : str, optional
        Wavelet family: 'db4' (default), 'db2', 'haar', 'sym4', 'coif2', etc.
        See pywt.wavelist() for all options.
    level : int, optional
        Decomposition level. If omitted, auto-selected based on series length.
    mode : str, optional
        Signal extension mode: 'symmetric' (default), 'zero', 'constant',
        'periodic', 'smooth', 'reflect'.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 8:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} observations. Wavelet decomposition needs at least 8.",
                error_fixes=["Provide a longer time series."],
            )

        wavelet_name = ctx.get_param("wavelet", "db4")
        mode = ctx.get_param("mode", "symmetric")

        # Validate wavelet
        try:
            wavelet = pywt.Wavelet(wavelet_name)
        except ValueError:
            available = pywt.wavelist(kind="discrete")[:20]
            return make_error_response(
                ctx,
                f"Unknown wavelet '{wavelet_name}'. Some valid options: {available}",
                error_fixes=[f"Choose from: {', '.join(available[:10])}, ..."],
            )

        # Determine decomposition level
        level_param = ctx.get_param("level")
        max_level = pywt.dwt_max_level(n, wavelet.dec_len)
        if level_param is not None:
            level = int(level_param)
            if level > max_level:
                warn_list.append(
                    f"Requested level {level} exceeds max ({max_level}) for n={n}. "
                    f"Using level={max_level}."
                )
                level = max_level
        else:
            # Preset-based default
            preset_levels = {
                "Fast": min(3, max_level),
                "Balanced": min(max_level, 5),
                "Thorough": max_level,
            }
            level = preset_levels.get(ctx.preset, min(max_level, 5))

        if level < 1:
            return make_error_response(
                ctx,
                "Cannot perform wavelet decomposition: series too short for even 1 level.",
                error_fixes=["Provide a longer series or use a shorter wavelet (e.g. 'haar')."],
            )

        progress_callback(f"Running DWT ({wavelet_name}, level={level})", 20)

        # Perform multi-level DWT
        coeffs = pywt.wavedec(clean, wavelet, mode=mode, level=level)
        # coeffs = [cA_n, cD_n, cD_{n-1}, ..., cD_1]

        progress_callback("Reconstructing sub-bands", 40)

        # Reconstruct each detail level and the approximation
        # Each component is reconstructed to the original length
        reconstructed = {}

        # Approximation (lowest frequency)
        approx_coeffs = [coeffs[0]] + [np.zeros_like(c) for c in coeffs[1:]]
        approx = pywt.waverec(approx_coeffs, wavelet, mode=mode)[:n]
        reconstructed["Approximation (A)"] = approx

        # Detail levels
        for i in range(1, level + 1):
            detail_coeffs = [np.zeros_like(c) for c in coeffs]
            detail_coeffs[i] = coeffs[i]
            detail = pywt.waverec(detail_coeffs, wavelet, mode=mode)[:n]
            reconstructed[f"Detail D{level - i + 1}"] = detail

        progress_callback("Computing energy distribution", 60)

        # Energy (variance) of each component
        total_energy = float(np.sum(clean ** 2))
        energy_rows = []
        for comp_name, comp_signal in reconstructed.items():
            energy = float(np.sum(comp_signal ** 2))
            pct = round(energy / total_energy * 100, 2) if total_energy > 0 else 0
            energy_rows.append([
                comp_name,
                round(energy, 4),
                pct,
                len(coeffs[0]) if "Approximation" in comp_name else len(coeffs[list(reconstructed.keys()).index(comp_name)]),
            ])

        energy_table = make_table(
            "Energy Distribution",
            ["Component", "Energy", "Energy %", "Coefficients"],
            energy_rows,
        )

        # Coefficient statistics
        progress_callback("Coefficient statistics", 70)
        coef_stat_rows = []
        coef_labels = ["Approx A"] + [f"Detail D{level - i}" for i in range(level)]
        for i, (label, c) in enumerate(zip(coef_labels, coeffs)):
            c_arr = np.asarray(c)
            coef_stat_rows.append([
                label,
                len(c_arr),
                round(float(np.mean(c_arr)), 6),
                round(float(np.std(c_arr, ddof=1)), 6) if len(c_arr) > 1 else 0,
                round(float(np.min(c_arr)), 6),
                round(float(np.max(c_arr)), 6),
                int(np.sum(np.abs(c_arr) < 1e-10)),  # near-zero count
            ])

        coef_table = make_table(
            "Coefficient Statistics",
            ["Level", "Count", "Mean", "Std Dev", "Min", "Max", "Near-Zero"],
            coef_stat_rows,
        )

        # Decomposition output table (subsampled for large series)
        progress_callback("Building decomposition table", 80)
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        columns = ["Time", name] + list(reconstructed.keys())
        step = max(1, n // 500) if ctx.preset == "Fast" else max(1, n // 1000)
        decomp_rows = []
        for i in range(0, n, step):
            row = [time_col[i], clean[i]]
            for comp_signal in reconstructed.values():
                row.append(round(float(comp_signal[i]), 6))
            decomp_rows.append(row)

        decomp_table = make_table("Wavelet Decomposition", columns, decomp_rows)

        # Diagnostics
        diag_rows = [
            ["Wavelet", wavelet_name],
            ["Decomposition Level", level],
            ["Max Possible Level", max_level],
            ["Extension Mode", mode],
            ["Filter Length", wavelet.dec_len],
            ["Observations", n],
            ["Total Components", level + 1],
        ]

        # Approximate frequency bands (in terms of observation periods)
        for i in range(level + 1):
            if i == 0:
                band = f"> {2 ** (level + 1)} obs"
                diag_rows.append(["Approx A Frequency Band", f"Low (period {band})"])
            else:
                low = 2 ** i
                high = 2 ** (i + 1)
                diag_rows.append([f"Detail D{i} Frequency Band", f"Period {low}-{high} obs"])

        diag_table = make_table("Analysis Parameters", ["Metric", "Value"], diag_rows)

        # Plain English
        # Find dominant component
        energies = {k: float(np.sum(v ** 2)) for k, v in reconstructed.items()}
        dominant = max(energies, key=energies.get)
        dom_pct = round(energies[dominant] / total_energy * 100, 1) if total_energy > 0 else 0

        plain = (
            f"Wavelet decomposition of '{name}' ({n} observations) using {wavelet_name} wavelet, "
            f"{level} level(s). The dominant component is '{dominant}' carrying {dom_pct}% "
            f"of the total energy."
        )

        if "Approximation" in dominant:
            plain += " Most energy is in the low-frequency (trend) component."
        else:
            plain += " Significant energy in the detail (oscillatory) component(s)."

        charting = (
            f"Stacked panel chart with {level + 2} panels sharing the x-axis: "
            "Original at top, followed by Approximation and Detail levels from "
            "lowest to highest frequency. Energy pie chart or bar chart on the side."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[energy_table, coef_table, decomp_table, diag_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "wavelet": wavelet_name,
                "level": level,
                "max_level": max_level,
                "mode": mode,
                "dominant_component": dominant,
                "dominant_energy_pct": dom_pct,
                "n_observations": n,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Wavelet decomposition failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try a different wavelet ('haar', 'db2', 'sym4').",
                "Reduce the decomposition level for short series.",
                "Check pywt.wavelist() for available wavelets.",
            ],
        )
