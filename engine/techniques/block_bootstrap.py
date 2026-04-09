"""
Block Bootstrap for Time Series Lab.

Generates bootstrap samples of a time series preserving temporal dependence
via non-overlapping or moving block bootstrap. Reports confidence intervals
for the mean, variance, and autocorrelation at lag 1.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


_PRESET_CONFIG = {
    "Fast": {"n_bootstrap": 500, "block_length": "auto"},
    "Balanced": {"n_bootstrap": 1000, "block_length": "auto"},
    "Thorough": {"n_bootstrap": 5000, "block_length": "auto"},
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


def _optimal_block_length(n):
    """
    Estimate optimal block length using the rule of thumb: n^(1/3).
    Politis & Romano (1994) suggest this as a reasonable starting point.
    """
    bl = max(2, int(round(n ** (1.0 / 3.0))))
    return min(bl, n // 2)


def _block_bootstrap_sample(data, block_length, rng):
    """
    Generate one block bootstrap replicate of the given data.
    Uses the moving block bootstrap (MBB) approach.
    """
    n = len(data)
    n_blocks_needed = int(np.ceil(n / block_length))
    max_start = n - block_length

    if max_start < 0:
        # Block length >= n, just return a random permutation-like sample
        return data.copy()

    starts = rng.integers(0, max_start + 1, size=n_blocks_needed)
    blocks = [data[s:s + block_length] for s in starts]
    sample = np.concatenate(blocks)[:n]
    return sample


def _acf_lag1(x):
    """Compute autocorrelation at lag 1."""
    if len(x) < 2:
        return np.nan
    xm = x - np.mean(x)
    c0 = np.sum(xm ** 2)
    if c0 == 0:
        return 0.0
    c1 = np.sum(xm[:-1] * xm[1:])
    return float(c1 / c0)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Block bootstrap for time series.

    Parameters (via ctx.params)
    ---------------------------
    n_bootstrap : int, optional
        Number of bootstrap replications. Default from preset.
    block_length : int or "auto", optional
        Block length. Default "auto" = n^(1/3).
    confidence_level : float, optional
        Confidence level for intervals. Default 0.95.
    statistic : str, optional
        Which statistics to bootstrap. Default "all" (mean, variance, acf1).
    """
    try:
        progress_callback("Validating inputs", 5)
        rng = np.random.default_rng(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")

        n = len(clean)
        if n < 10:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Block bootstrap needs at least 10.",
                error_fixes=["Provide a longer time series."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_bootstrap = int(ctx.get_param("n_bootstrap", preset_cfg["n_bootstrap"]))
        conf_level = float(ctx.get_param("confidence_level", 0.95))
        alpha = 1.0 - conf_level

        bl_param = ctx.get_param("block_length", preset_cfg["block_length"])
        if bl_param == "auto" or bl_param is None:
            block_length = _optimal_block_length(n)
        else:
            block_length = int(bl_param)
            if block_length < 1:
                block_length = 1
            if block_length > n:
                warn_list.append(
                    f"Block length ({block_length}) exceeds series length ({n}). "
                    f"Capped to {n}."
                )
                block_length = n

        progress_callback("Generating bootstrap samples", 15)

        # Original statistics
        orig_mean = float(np.mean(clean))
        orig_var = float(np.var(clean, ddof=1))
        orig_acf1 = _acf_lag1(clean)

        # Bootstrap
        boot_means = np.empty(n_bootstrap)
        boot_vars = np.empty(n_bootstrap)
        boot_acf1s = np.empty(n_bootstrap)

        report_every = max(1, n_bootstrap // 10)
        for b in range(n_bootstrap):
            if b % report_every == 0:
                pct = 15 + int(65 * b / n_bootstrap)
                progress_callback(f"Bootstrap sample {b + 1}/{n_bootstrap}", pct)

            sample = _block_bootstrap_sample(clean, block_length, rng)
            boot_means[b] = np.mean(sample)
            boot_vars[b] = np.var(sample, ddof=1)
            boot_acf1s[b] = _acf_lag1(sample)

        progress_callback("Computing confidence intervals", 85)

        lo = (alpha / 2) * 100
        hi = (1.0 - alpha / 2) * 100

        def _ci(boot_arr):
            return (float(np.percentile(boot_arr, lo)),
                    float(np.percentile(boot_arr, hi)))

        mean_ci = _ci(boot_means)
        var_ci = _ci(boot_vars)
        acf1_ci = _ci(boot_acf1s)

        # Bias and standard error
        mean_bias = float(np.mean(boot_means) - orig_mean)
        mean_se = float(np.std(boot_means, ddof=1))
        var_bias = float(np.mean(boot_vars) - orig_var)
        var_se = float(np.std(boot_vars, ddof=1))
        acf1_bias = float(np.mean(boot_acf1s) - orig_acf1)
        acf1_se = float(np.std(boot_acf1s, ddof=1))

        # Results table
        ci_label = f"{conf_level * 100:.0f}%"
        results_rows = [
            ["Mean", round(orig_mean, 6), round(mean_bias, 6), round(mean_se, 6),
             round(mean_ci[0], 6), round(mean_ci[1], 6)],
            ["Variance", round(orig_var, 6), round(var_bias, 6), round(var_se, 6),
             round(var_ci[0], 6), round(var_ci[1], 6)],
            ["ACF(1)", round(orig_acf1, 6), round(acf1_bias, 6), round(acf1_se, 6),
             round(acf1_ci[0], 6), round(acf1_ci[1], 6)],
        ]
        results_table = make_table(
            "Bootstrap Results",
            ["Statistic", "Original", "Bias", "Std Error",
             f"Lower {ci_label}", f"Upper {ci_label}"],
            results_rows,
        )

        # Distribution summary (quantiles of bootstrap distributions)
        quantiles = [5, 25, 50, 75, 95]
        dist_rows = []
        for q in quantiles:
            dist_rows.append([
                f"{q}th percentile",
                round(float(np.percentile(boot_means, q)), 6),
                round(float(np.percentile(boot_vars, q)), 6),
                round(float(np.percentile(boot_acf1s, q)), 6),
            ])
        dist_table = make_table(
            "Bootstrap Distributions",
            ["Quantile", "Mean", "Variance", "ACF(1)"],
            dist_rows,
        )

        # Config table
        config_rows = [
            ["Block Length", block_length],
            ["Bootstrap Replications", n_bootstrap],
            ["Confidence Level", f"{conf_level * 100:.0f}%"],
            ["Series Length", n],
            ["Seed", ctx.seed],
            ["Preset", ctx.preset],
        ]
        config_table = make_table("Configuration", ["Parameter", "Value"], config_rows)

        # Plain English
        plain_english = (
            f"Block bootstrap of '{name}' ({n} observations) with block length {block_length} "
            f"and {n_bootstrap} replications. "
            f"The {ci_label} CI for the mean is [{mean_ci[0]:.4f}, {mean_ci[1]:.4f}]. "
            f"The bootstrap standard error of the mean is {mean_se:.4f}."
        )
        if abs(mean_bias) > mean_se * 0.5:
            plain_english += (
                f" Notable bias detected in the mean estimate ({mean_bias:.4f}); "
                "consider bias-corrected intervals."
            )

        charting = (
            "Histogram of bootstrap distribution of the mean with vertical lines for the "
            f"original estimate and {ci_label} CI bounds. "
            "Secondary panels: histograms for variance and ACF(1) bootstrap distributions."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=[results_table, dist_table, config_table],
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "block_length": block_length,
                "n_bootstrap": n_bootstrap,
                "confidence_level": conf_level,
                "original_mean": round(orig_mean, 6),
                "mean_ci_lower": round(mean_ci[0], 6),
                "mean_ci_upper": round(mean_ci[1], 6),
                "mean_se": round(mean_se, 6),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Block bootstrap failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations.",
                "Try a smaller block length.",
                "Check for constant or near-constant series.",
            ],
        )
