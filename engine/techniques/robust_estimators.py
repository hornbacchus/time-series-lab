"""
Robust Location/Scale Estimators for Time Series Lab.

Computes robust alternatives to the mean and standard deviation:
- Trimmed mean
- Winsorized mean
- Median Absolute Deviation (MAD)
- Qn scale estimator (Rousseeuw & Croux, 1993)
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"trim_fraction": 0.1, "winsor_fraction": 0.1},
    "Balanced": {"trim_fraction": 0.1, "winsor_fraction": 0.1},
    "Thorough": {"trim_fractions": [0.05, 0.10, 0.15, 0.20, 0.25],
                 "winsor_fractions": [0.05, 0.10, 0.15, 0.20, 0.25]},
}


def _trimmed_mean(x, fraction):
    """Compute the trimmed mean, trimming fraction from each tail."""
    return float(sp_stats.trim_mean(x, fraction))


def _winsorized_mean(x, fraction):
    """Compute the Winsorized mean."""
    w = sp_stats.mstats.winsorize(x, limits=[fraction, fraction])
    return float(np.mean(w))


def _winsorized_std(x, fraction):
    """Compute the Winsorized standard deviation."""
    w = sp_stats.mstats.winsorize(x, limits=[fraction, fraction])
    return float(np.std(w, ddof=1))


def _mad(x):
    """Median Absolute Deviation with consistency factor for normal distribution."""
    med = np.median(x)
    mad_raw = np.median(np.abs(x - med))
    # Consistency factor for normal distribution: 1.4826
    return float(mad_raw * 1.4826)


def _qn_scale(x):
    """
    Qn scale estimator (Rousseeuw & Croux, 1993).
    Qn = c_n * {|xi - xj|; i < j}_(h),
    where h = choose(floor(n/2)+1, 2) and c_n is a consistency factor.
    This is the h-th order statistic of all pairwise absolute differences.
    """
    n = len(x)
    if n < 2:
        return 0.0

    # For large n, computing all pairwise differences is O(n^2).
    # Cap at n=2000 for performance; subsample otherwise.
    if n > 2000:
        rng = np.random.default_rng(42)
        idx = rng.choice(n, size=2000, replace=False)
        x = x[idx]
        n = 2000

    # Compute all pairwise absolute differences
    sorted_x = np.sort(x)
    diffs = []
    for i in range(n):
        for j in range(i + 1, n):
            diffs.append(sorted_x[j] - sorted_x[i])
    diffs = np.array(diffs)

    h = int(np.floor(n / 2) + 1)
    k = int(h * (h - 1) / 2)
    k = min(k, len(diffs)) - 1  # 0-indexed
    k = max(k, 0)

    diffs_sorted = np.sort(diffs)
    qn_raw = diffs_sorted[k]

    # Consistency factor for normal distribution: 2.2219
    return float(qn_raw * 2.2219)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute robust location and scale estimators.

    Parameters (via ctx.params)
    ---------------------------
    trim_fraction : float, optional
        Fraction to trim from each tail for trimmed mean. Default 0.10.
    winsor_fraction : float, optional
        Fraction to Winsorize from each tail. Default 0.10.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        # Remove NaN
        clean = values[~np.isnan(values)]
        n_missing = len(values) - len(clean)
        if n_missing > 0:
            warn_list.append(f"{n_missing} missing values excluded from calculations.")

        n = len(clean)
        if n < 5:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Robust estimators need at least 5.",
                error_fixes=["Provide more data points."],
            )

        progress_callback("Computing classical estimators", 15)

        # Classical estimators
        classical_mean = float(np.mean(clean))
        classical_std = float(np.std(clean, ddof=1))
        classical_median = float(np.median(clean))

        progress_callback("Computing robust estimators", 30)

        # Determine fractions based on preset
        if ctx.preset == "Thorough":
            trim_fracs = _PRESET_CONFIG["Thorough"]["trim_fractions"]
            winsor_fracs = _PRESET_CONFIG["Thorough"]["winsor_fractions"]
        else:
            tf = float(ctx.get_param("trim_fraction", 0.10))
            wf = float(ctx.get_param("winsor_fraction", 0.10))
            trim_fracs = [tf]
            winsor_fracs = [wf]

        # Validate fractions
        trim_fracs = [f for f in trim_fracs if 0 < f < 0.5]
        winsor_fracs = [f for f in winsor_fracs if 0 < f < 0.5]
        if not trim_fracs:
            trim_fracs = [0.10]
        if not winsor_fracs:
            winsor_fracs = [0.10]

        # Location estimators table
        location_rows = [
            ["Arithmetic Mean", round(classical_mean, 6), "Classical", "None"],
            ["Median", round(classical_median, 6), "Robust", "None"],
        ]
        for tf in trim_fracs:
            tm = _trimmed_mean(clean, tf)
            location_rows.append([
                f"Trimmed Mean ({tf*100:.0f}%)",
                round(tm, 6),
                "Robust",
                f"Trim {tf*100:.0f}% each tail",
            ])

        for wf in winsor_fracs:
            wm = _winsorized_mean(clean, wf)
            location_rows.append([
                f"Winsorized Mean ({wf*100:.0f}%)",
                round(wm, 6),
                "Robust",
                f"Winsorize {wf*100:.0f}% each tail",
            ])

        location_table = make_table(
            "Location Estimators",
            ["Estimator", "Value", "Type", "Tuning"],
            location_rows,
        )

        progress_callback("Computing scale estimators", 60)

        # Scale estimators table
        mad_val = _mad(clean)

        scale_rows = [
            ["Standard Deviation", round(classical_std, 6), "Classical", "None"],
            ["IQR", round(float(np.percentile(clean, 75) - np.percentile(clean, 25)), 6),
             "Robust", "None"],
            ["MAD (normalized)", round(mad_val, 6), "Robust", "Factor=1.4826"],
        ]

        for wf in winsor_fracs:
            ws = _winsorized_std(clean, wf)
            scale_rows.append([
                f"Winsorized Std ({wf*100:.0f}%)",
                round(ws, 6),
                "Robust",
                f"Winsorize {wf*100:.0f}% each tail",
            ])

        progress_callback("Computing Qn scale estimator", 75)

        if n <= 5000:
            qn_val = _qn_scale(clean)
            scale_rows.append([
                "Qn Scale", round(qn_val, 6), "Robust", "Factor=2.2219",
            ])
        else:
            qn_val = _qn_scale(clean)  # uses subsampling internally
            scale_rows.append([
                "Qn Scale (subsampled)", round(qn_val, 6), "Robust",
                "Factor=2.2219, n>2000 subsampled",
            ])
            warn_list.append("Qn scale computed on a subsample of 2000 points for performance.")

        scale_table = make_table(
            "Scale Estimators",
            ["Estimator", "Value", "Type", "Tuning"],
            scale_rows,
        )

        progress_callback("Computing comparison diagnostics", 85)

        # Comparison / outlier diagnostics
        # Compare robust vs classical to gauge outlier influence
        primary_trim = trim_fracs[0]
        primary_winsor = winsor_fracs[0]
        tm_val = _trimmed_mean(clean, primary_trim)
        wm_val = _winsorized_mean(clean, primary_winsor)

        mean_median_diff = abs(classical_mean - classical_median)
        mean_trimmed_diff = abs(classical_mean - tm_val)
        std_mad_ratio = classical_std / mad_val if mad_val > 0 else float('inf')

        diag_rows = [
            ["|Mean - Median|", round(mean_median_diff, 6)],
            ["|Mean - Trimmed Mean|", round(mean_trimmed_diff, 6)],
            ["Std / MAD ratio", round(std_mad_ratio, 4)],
            ["Observations", n],
            ["Missing Values Excluded", n_missing],
        ]

        # Skewness and kurtosis
        if n >= 8:
            skew = float(sp_stats.skew(clean))
            kurt = float(sp_stats.kurtosis(clean))
            diag_rows.append(["Skewness", round(skew, 4)])
            diag_rows.append(["Excess Kurtosis", round(kurt, 4)])

        diag_table = make_table("Diagnostics", ["Metric", "Value"], diag_rows)

        # Interpretation
        outlier_evidence = []
        if std_mad_ratio > 1.5:
            outlier_evidence.append(
                f"Std/MAD ratio is {std_mad_ratio:.2f} (>1.5), suggesting outlier influence"
            )
        if mean_median_diff > 0.5 * classical_std:
            outlier_evidence.append(
                "large mean-median gap relative to standard deviation"
            )
        if mean_trimmed_diff > 0.3 * classical_std:
            outlier_evidence.append(
                "trimmed mean differs substantially from arithmetic mean"
            )

        if outlier_evidence:
            outlier_msg = (
                "Evidence of outlier influence detected: " +
                "; ".join(outlier_evidence) + ". "
                "Robust estimators may be more appropriate for this data."
            )
            warn_list.append(outlier_msg)
        else:
            outlier_msg = "No strong evidence of outlier influence."

        plain_english = (
            f"Robust estimators for '{name}' ({n} observations). "
            f"Classical mean={classical_mean:.4f}, median={classical_median:.4f}, "
            f"trimmed mean ({primary_trim*100:.0f}%)={tm_val:.4f}. "
            f"Classical std={classical_std:.4f}, MAD={mad_val:.4f}"
        )
        if n <= 5000:
            plain_english += f", Qn={qn_val:.4f}"
        plain_english += f". {outlier_msg}"

        charting = (
            "Box plot or violin plot of the series with horizontal lines marking "
            "the mean (solid), median (dashed), and trimmed mean (dotted). "
            "Side panel: bar chart comparing scale estimators (Std, MAD, Qn)."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[location_table, scale_table, diag_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "n_valid": n,
                "classical_mean": round(classical_mean, 6),
                "median": round(classical_median, 6),
                "trimmed_mean": round(tm_val, 6),
                "trim_fraction": primary_trim,
                "winsorized_mean": round(wm_val, 6),
                "classical_std": round(classical_std, 6),
                "mad": round(mad_val, 6),
                "qn_scale": round(qn_val, 6) if n <= 5000 else None,
                "std_mad_ratio": round(std_mad_ratio, 4),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Robust estimators failed: {e}",
            error_fixes=[
                "Ensure your data is numeric.",
                "Check for constant series (zero variance).",
            ],
        )
