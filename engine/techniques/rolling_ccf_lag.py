"""
Rolling window cross-correlation for time-varying lag detection, for Time Series Lab.

Computes the cross-correlation function (CCF) between two series within a
sliding window, tracking how the optimal lag and correlation strength change
over time.

This module is the *reference implementation* for two platform-wide
conventions enforced via ``engine/techniques/base.py``:

  F2 — Pairwise-summary convention: every pairwise-output technique reports
       sign AND magnitude AND direction as a paired fact in the primary
       sentence, not lag-only or rho-only. Enforced via
       ``format_pairwise_summary``.

  F3 — Significance-disclosure convention: every significance-emitting
       technique discloses its test name, critical-value formula, and
       AC-correction status in the audit sheet. Where the inputs are
       plausibly autocorrelated time series, the naive ±1.96/sqrt(n) band
       is replaced with a Bartlett-effective-n adjustment. Enforced via
       ``format_significance_disclosure`` and ``bartlett_effective_n``.

Boundary-lag handling and structural-break detection are further F1
fixes specific to this technique — boundary-hit windows are flagged and
excluded from summary statistics, and a regime shift is detected via
``ruptures.Pelt`` on the CCF-at-optimal-lag series (and on the sign
series), triggering a split-regime summary when confirmed.
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    dropna_aligned,
    flag_boundary_hits,
    bartlett_effective_n,
    format_pairwise_summary,
    format_significance_disclosure,
)

# Interpretation layer (Prompt B).
try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None

# Preset config no longer hard-codes default_window; it is derived from `n`
# via ``_default_window`` below. Keeps Balanced-default appropriate across
# short and long inputs.
_PRESET_CONFIG = {
    "Fast":     {"step": 5, "max_lag_frac": 0.25},
    "Balanced": {"step": 1, "max_lag_frac": 0.33},
    "Thorough": {"step": 1, "max_lag_frac": 0.40},
}


def _default_window(n: int, preset: str) -> int:
    """Heuristic default window length.

    For Balanced/Thorough: ``max(40, min(80, n // 3))``. This caps at a
    20-year quarterly window, prevents 40% of-sample rolls on short series,
    and scales down gracefully when the caller has limited data. For Fast:
    ``max(30, min(60, n // 4))`` — slightly narrower for speed.
    """
    if preset == "Fast":
        return max(30, min(60, n // 4))
    return max(40, min(80, n // 3))


def _detect_structural_break(optimal_ccfs, optimal_lags, min_segment: int = 8):
    """Detect a structural break in the rolling CCF output via ruptures.Pelt.

    Runs PELT on two derived series:
      1. The CCF-at-optimal-lag series (magnitude + sign over time).
      2. The sign-of-CCF series (±1 per window).

    A break is *confirmed* only if the post-break segment has at least
    ``min_segment`` consecutive windows of consistent lag-sign OR consistent
    rho-sign relative to the pre-break segment. Conservative by design —
    prefer missing borderline breaks over reporting a regime split on noise.

    Parameters
    ----------
    optimal_ccfs : array, shape (n_windows,)
        CCF value at the optimal lag in each window.
    optimal_lags : array, shape (n_windows,)
        Optimal lag in each window.
    min_segment : int, default 8
        Minimum consecutive-consistent windows required post-break.

    Returns
    -------
    (break_idx or None, details dict)
        ``break_idx`` is the window index at which the break occurred; None
        if no confirmed break. ``details`` contains diagnostics.
    """
    details = {"confirmed": False, "reason": None}
    try:
        import ruptures as rpt
    except ImportError:
        details["reason"] = "ruptures not available"
        return None, details

    n_windows = len(optimal_ccfs)
    # Require each segment to be at least max(min_segment, 12.5% of windows).
    # This filters out "breaks" at the extreme start/end of the run — those
    # can be triggered by a small initial/final segment of persistent noise
    # and rarely correspond to real regime changes.
    min_segment = max(min_segment, n_windows // 8)
    if n_windows < 2 * min_segment + 4:
        details["reason"] = f"too few windows ({n_windows}) to detect a break"
        return None, details

    def _run_pelt(series_1d):
        arr = np.asarray(series_1d, dtype=float).reshape(-1)
        var = float(np.var(arr))
        if var <= 1e-10:
            return []
        pen = float(np.log(len(arr))) * max(var, 1e-6)
        try:
            algo = rpt.Pelt(model="l2").fit(arr)
            bps = algo.predict(pen=pen)
        except Exception:
            return []
        # ruptures returns end-indices; the last one is always n — drop it.
        return [int(b) for b in bps if 0 < b < len(arr)]

    candidate_breaks = []
    # Channel 1: CCF magnitude + sign
    for b in _run_pelt(optimal_ccfs):
        candidate_breaks.append(("ccf", b))
    # Channel 2: sign-only (more robust when magnitudes are noisy)
    sign_series = np.sign(optimal_ccfs)
    for b in _run_pelt(sign_series):
        candidate_breaks.append(("sign", b))

    if not candidate_breaks:
        details["reason"] = "PELT detected no changepoints"
        return None, details

    def _segment_consistent(arr, start, end, check="sign"):
        """Run-length of consistent sign across ``arr[start:end]``."""
        if start >= end:
            return 0
        if check == "sign":
            signs = np.sign(arr[start:end])
        else:
            signs = np.sign(arr[start:end])
        if len(signs) == 0:
            return 0
        # Longest run of the modal sign (zero treated as match to whichever
        # side the segment leans)
        modal = 1 if np.sum(signs > 0) >= np.sum(signs < 0) else -1
        best = cur = 0
        for s in signs:
            if (s >= 0 and modal == 1) or (s < 0 and modal == -1):
                cur += 1
                best = max(best, cur)
            else:
                cur = 0
        return best

    def _modal_sign_fraction(arr):
        """Fraction of entries sharing the modal sign. 0.5 = no preference,
        1.0 = unanimous. Used to distinguish true regimes (high consistency)
        from persistent noise (sign can wander but usually flip-flops more)."""
        arr = np.asarray(arr, dtype=float)
        if arr.size == 0:
            return 0.0
        signs = np.sign(arr)
        pos = float(np.sum(signs > 0))
        neg = float(np.sum(signs < 0))
        total = pos + neg
        if total <= 0:
            return 0.0
        return max(pos, neg) / total

    # For each candidate break, apply four criteria. All four must hold for
    # the break to be confirmed — this is deliberately conservative because
    # rolling CCFs on persistent independent series naturally wander from
    # negative to positive territory and would generate false-positive
    # "breaks" under a looser rule.
    #
    #   (1) Each segment has at least `min_segment` windows of consistent
    #       run-length in either the rho sign or the lag sign series.
    #   (2) Each segment has >2/3 modal-sign consistency (genuine regime,
    #       not 50/50 random wandering).
    #   (3) The pre and post modal signs DIFFER (rho or lag).
    #   (4) The magnitude of |median_pre - median_post| for rho exceeds
    #       0.25 (not a marginal wobble).
    CONSISTENCY_THRESHOLD = 2.0 / 3.0
    MAGNITUDE_CONTRAST = 0.25
    best_break = None
    best_quality = 0
    for channel, b in sorted(set(candidate_breaks), key=lambda x: x[1]):
        if b < min_segment or b > n_windows - min_segment:
            continue
        post_ccf_run = _segment_consistent(optimal_ccfs, b, n_windows)
        post_lag_run = _segment_consistent(np.sign(optimal_lags), b, n_windows)
        quality = max(post_ccf_run, post_lag_run)
        pre_ccf_run = _segment_consistent(optimal_ccfs, 0, b)
        pre_lag_run = _segment_consistent(np.sign(optimal_lags), 0, b)
        pre_quality = max(pre_ccf_run, pre_lag_run)
        if not (quality >= min_segment and pre_quality >= min_segment):
            continue
        pre_ccf = optimal_ccfs[:b]
        post_ccf = optimal_ccfs[b:]
        pre_lag = optimal_lags[:b]
        post_lag = optimal_lags[b:]
        pre_ccf_frac = _modal_sign_fraction(pre_ccf)
        post_ccf_frac = _modal_sign_fraction(post_ccf)
        pre_lag_frac = _modal_sign_fraction(pre_lag)
        post_lag_frac = _modal_sign_fraction(post_lag)
        # Segment consistency in either channel
        ccf_both_consistent = (pre_ccf_frac >= CONSISTENCY_THRESHOLD
                               and post_ccf_frac >= CONSISTENCY_THRESHOLD)
        lag_both_consistent = (pre_lag_frac >= CONSISTENCY_THRESHOLD
                               and post_lag_frac >= CONSISTENCY_THRESHOLD)
        if not (ccf_both_consistent or lag_both_consistent):
            continue
        # Sign contrast in a channel where BOTH segments are consistent
        pre_ccf_med = float(np.median(pre_ccf))
        post_ccf_med = float(np.median(post_ccf))
        pre_lag_med = float(np.median(pre_lag))
        post_lag_med = float(np.median(post_lag))
        ccf_contrast = ccf_both_consistent and (pre_ccf_med * post_ccf_med < 0)
        lag_contrast = lag_both_consistent and (pre_lag_med * post_lag_med < 0)
        mag_contrast = abs(pre_ccf_med - post_ccf_med) > MAGNITUDE_CONTRAST
        if not (ccf_contrast or lag_contrast):
            continue
        if not mag_contrast:
            continue
        if quality > best_quality:
            best_break = b
            best_quality = quality
            details["channel"] = channel
            details["post_run"] = int(quality)
            details["pre_run"] = int(pre_quality)
            details["pre_modal_ccf_fraction"] = round(pre_ccf_frac, 3)
            details["post_modal_ccf_fraction"] = round(post_ccf_frac, 3)
            details["pre_median_ccf"] = round(pre_ccf_med, 3)
            details["post_median_ccf"] = round(post_ccf_med, 3)

    if best_break is None:
        details["reason"] = "no changepoint passed consistency threshold"
        return None, details

    details["confirmed"] = True
    return int(best_break), details


def _regime_stats(optimal_lags, optimal_ccfs, boundary_mask):
    """Compute the direction/sign/magnitude/lag facts for a regime segment.

    Excludes boundary-hit windows from the computation. Returns a dict with
    ``sign`` ('+' or '-'), ``magnitude`` (|rho|), ``lag`` (median lag),
    ``direction_verb`` ("leads" / "lags"), and ``n_used`` (count after
    boundary exclusion).
    """
    valid = ~np.asarray(boundary_mask, dtype=bool)
    lags = np.asarray(optimal_lags)[valid]
    ccfs = np.asarray(optimal_ccfs)[valid]
    n_used = int(lags.size)
    if n_used == 0:
        return {
            "sign": "+",
            "magnitude": 0.0,
            "lag": 0,
            "direction_verb": "is uncorrelated with",
            "n_used": 0,
        }
    median_lag = int(np.round(np.median(lags)))
    # Median CCF sign — robust to outlier windows
    median_ccf = float(np.median(ccfs))
    sign = "+" if median_ccf >= 0 else "-"
    magnitude = float(np.median(np.abs(ccfs)))
    if median_lag > 0:
        verb = "leads"
    elif median_lag < 0:
        verb = "lags"
    else:
        verb = "is contemporaneously correlated with"
    return {
        "sign": sign,
        "magnitude": magnitude,
        "lag": median_lag,
        "direction_verb": verb,
        "n_used": n_used,
    }


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Compute rolling cross-correlation between two series with boundary-lag
    flagging, structural-break detection, and AC-corrected significance.

    Requires 2 series. If >2 are supplied, uses the first two and emits a
    disclosure warning naming the pair used and the pair ignored.

    Parameters (via ctx.params)
    ---------------------------
    window : int, optional
        Rolling window size. Defaults to max(40, min(80, n//3)) for
        Balanced/Thorough presets, max(30, min(60, n//4)) for Fast.
    max_lag : int, optional
        Maximum lag to search. Defaults to ``int(window * max_lag_frac)``.
    step : int, optional
        Step size between windows. Defaults per preset.
    significance_level : float, optional
        Two-sided significance level for the Bartlett confidence band.
        Default 0.05.
    boundary_threshold : float, optional
        Fraction of max_lag above which a window is flagged as boundary-hit.
        Default 0.8.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        warnings = []

        # F2 multi-series disclosure: pair used, pairs ignored.
        if len(all_series) > 2:
            ignored = [s[0] for s in all_series[2:]]
            warnings.append(
                f"Rolling CCF is a pairwise technique. Used '{all_series[0][0]}' "
                f"and '{all_series[1][0]}' as the (x, y) pair; ignored "
                f"{len(ignored)} additional series: {', '.join(ignored)}. "
                f"Rerun with a different column order to analyze a different pair."
            )

        x_name, x_vals = all_series[0]
        y_name, y_vals = all_series[1]

        if len(x_vals) != len(y_vals):
            return make_error_response(
                ctx,
                f"Series lengths differ: '{x_name}' has {len(x_vals)}, "
                f"'{y_name}' has {len(y_vals)}.",
                error_fixes=["Select two columns of the same length."],
            )

        x_clean, y_clean = dropna_aligned(x_vals, y_vals)
        n_dropped = len(x_vals) - len(x_clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} rows dropped due to missing values.")

        n = len(x_clean)

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        window_param = ctx.get_param("window")
        if window_param is None:
            window = _default_window(n, ctx.preset)
        else:
            window = int(window_param)
            if window > n // 2:
                warnings.append(
                    f"User-supplied window ({window}) exceeds half the "
                    f"sample size ({n // 2}). Summary statistics may be "
                    f"dominated by a single regime; consider reducing window."
                )
        window = min(window, n - 1)

        step = int(ctx.get_param("step", cfg["step"]))
        significance = float(ctx.get_param("significance_level", 0.05))
        boundary_threshold = float(ctx.get_param("boundary_threshold", 0.8))

        max_lag_param = ctx.get_param("max_lag")
        if max_lag_param is not None:
            max_lag = int(max_lag_param)
        else:
            max_lag = max(1, int(window * cfg["max_lag_frac"]))

        if window < 20:
            return make_error_response(
                ctx,
                f"Window size ({window}) is too small. Need at least 20.",
                error_fixes=["Increase the window parameter or provide more data."],
            )

        if n < window + 10:
            return make_error_response(
                ctx,
                f"Only {n} valid observations with window={window}. Need at least window + 10.",
                error_fixes=["Provide longer series or reduce window size."],
            )

        progress_callback("Computing rolling cross-correlations", 15)

        # Rolling windows
        window_starts = list(range(0, n - window + 1, step))
        n_windows = len(window_starts)

        # Results storage
        optimal_lags = np.zeros(n_windows)
        optimal_ccfs = np.zeros(n_windows)
        center_times = np.zeros(n_windows, dtype=int)
        lag_stability = np.zeros(n_windows)  # sharpness around peak

        # Full CCF matrix (windows x lags)
        n_lags_total = 2 * max_lag + 1
        ccf_matrix = np.zeros((n_windows, n_lags_total))

        # Naive Bartlett band at alpha — AC-inflation correction applied
        # globally below using bartlett_effective_n on the full series.
        z_crit = float(sp_stats.norm.ppf(1.0 - significance / 2.0))
        bartlett_band_naive = z_crit / np.sqrt(window)

        for w_idx, w_start in enumerate(window_starts):
            pct = 15 + int(60 * w_idx / n_windows)
            if w_idx % max(1, n_windows // 20) == 0:
                progress_callback(f"Window {w_idx + 1}/{n_windows}", pct)

            w_end = w_start + window
            x_w = x_clean[w_start:w_end]
            y_w = y_clean[w_start:w_end]

            center_times[w_idx] = w_start + window // 2

            # Compute CCF for lags -max_lag to +max_lag
            x_dm = x_w - np.mean(x_w)
            y_dm = y_w - np.mean(y_w)
            denom = np.sqrt(np.sum(x_dm ** 2) * np.sum(y_dm ** 2))

            if denom < 1e-15:
                ccf_matrix[w_idx, :] = 0
                optimal_lags[w_idx] = 0
                optimal_ccfs[w_idx] = 0
                continue

            best_lag = 0
            best_abs_ccf = 0
            best_ccf_val = 0

            for lag_idx, lag in enumerate(range(-max_lag, max_lag + 1)):
                if lag >= 0:
                    ccf_val = np.sum(x_dm[:window - lag] * y_dm[lag:]) / denom if lag < window else 0
                else:
                    alag = -lag
                    ccf_val = np.sum(x_dm[alag:] * y_dm[:window - alag]) / denom if alag < window else 0

                ccf_matrix[w_idx, lag_idx] = ccf_val

                if abs(ccf_val) > best_abs_ccf:
                    best_abs_ccf = abs(ccf_val)
                    best_ccf_val = ccf_val
                    best_lag = lag

            optimal_lags[w_idx] = best_lag
            optimal_ccfs[w_idx] = best_ccf_val

            ccf_abs = np.abs(ccf_matrix[w_idx, :])
            if np.max(ccf_abs) > 0:
                lag_stability[w_idx] = np.max(ccf_abs) - np.mean(ccf_abs)

        progress_callback("Flagging boundary-hit windows", 78)

        # F1 — Boundary flag: windows whose optimal lag sits at/near ±max_lag
        # are not reliable (the optimizer wanted a lag outside the search
        # range). Exclude from summary stats; disclose the count.
        boundary_mask = flag_boundary_hits(
            optimal_lags.astype(int), max_lag=max_lag, threshold=boundary_threshold
        )
        n_boundary = int(boundary_mask.sum())

        # AC-corrected significance band: Bartlett-effective-n adjusts for
        # the autocorrelation in x and y. On persistent series the effective
        # n collapses (AR(0.9) → ~1/8 of nominal n), which widens the band
        # and lowers pct_significant materially.
        progress_callback("Computing AC-corrected significance", 82)
        n_eff_full, ac_inflation = bartlett_effective_n(x_clean, y_clean)
        # Per-window effective n scales with min(window, n_eff_full)
        n_eff_window = max(3.0, min(float(window), float(n_eff_full) * window / float(n)))
        bartlett_band_ac = z_crit / np.sqrt(n_eff_window)
        ac_corrected = ac_inflation >= 1.05  # <5% inflation ≈ iid; skip
        if ac_corrected and ac_inflation >= 1.5:
            warnings.append(
                f"Autocorrelation inflation factor {ac_inflation:.1f}x "
                f"(effective n per window ≈ {n_eff_window:.0f} vs nominal "
                f"{window}). Significance band widened accordingly."
            )
        chosen_band = bartlett_band_ac if ac_corrected else bartlett_band_naive

        progress_callback("Detecting structural breaks", 85)

        # F1 — Structural break detection via ruptures.Pelt on the CCF-at-
        # optimal-lag and sign series. If confirmed, split the summary.
        break_idx, break_details = _detect_structural_break(
            optimal_ccfs, optimal_lags, min_segment=8
        )

        progress_callback("Computing summary statistics", 90)

        # Time column
        time_col = ctx.time if ctx.time and len(ctx.time) >= n else None

        # Rolling results table — now with Boundary_Hit column
        rolling_rows = []
        for w_idx in range(n_windows):
            cidx = center_times[w_idx]
            t_label = time_col[cidx] if time_col else int(cidx + 1)
            is_sig = abs(optimal_ccfs[w_idx]) > chosen_band

            rolling_rows.append([
                t_label,
                int(optimal_lags[w_idx]),
                round(float(optimal_ccfs[w_idx]), 6),
                round(float(lag_stability[w_idx]), 4),
                "Yes" if is_sig else "No",
                "Yes" if bool(boundary_mask[w_idx]) else "No",
            ])

        rolling_table = make_table(
            "Rolling Optimal Lag",
            ["Center Time", "Optimal Lag", "CCF at Lag", "Peak Sharpness",
             "Significant", "Boundary_Hit"],
            rolling_rows,
        )

        # Lag distribution — exclude boundary hits
        sig_mask = (np.abs(optimal_ccfs) > chosen_band) & (~boundary_mask)
        sig_lags = optimal_lags[sig_mask]

        lag_dist_rows = []
        if len(sig_lags) > 0:
            unique_lags, counts = np.unique(sig_lags.astype(int), return_counts=True)
            sorted_idx = np.argsort(-counts)
            for i in sorted_idx[:min(15, len(sorted_idx))]:
                lag = int(unique_lags[i])
                cnt = int(counts[i])
                pct = 100 * cnt / len(sig_lags)
                mean_ccf = float(np.mean(optimal_ccfs[sig_mask & (optimal_lags == lag)]))
                lag_dist_rows.append([
                    lag,
                    cnt,
                    round(pct, 1),
                    round(mean_ccf, 4),
                ])

        lag_dist_table = make_table(
            "Lag Distribution (significant, non-boundary windows)",
            ["Lag", "Count", "% of Windows", "Mean CCF"],
            lag_dist_rows,
        )

        # Summary statistics — computed on boundary-EXCLUDED subset
        valid_mask = ~boundary_mask
        valid_lags = optimal_lags[valid_mask]
        valid_ccfs = optimal_ccfs[valid_mask]

        if valid_lags.size > 0:
            mean_lag = float(np.mean(valid_lags))
            std_lag = float(np.std(valid_lags))
            median_lag = float(np.median(valid_lags))
            mean_abs_ccf = float(np.mean(np.abs(valid_ccfs)))
        else:
            mean_lag = std_lag = median_lag = mean_abs_ccf = 0.0

        pct_significant = float(100 * np.sum(sig_mask) / max(1, n_windows))
        # What naive would have said — for AC-correction materiality check
        naive_sig_mask = np.abs(optimal_ccfs) > bartlett_band_naive
        pct_significant_naive = float(100 * np.sum(naive_sig_mask) / max(1, n_windows))

        if ac_corrected and (pct_significant_naive - pct_significant) > 10.0:
            warnings.append(
                f"AC correction materially changed significance: naive band "
                f"would have reported {pct_significant_naive:.0f}% significant "
                f"vs {pct_significant:.0f}% after correction. Treat naive "
                f"rolling-CCF significance estimates on persistent macro "
                f"data with caution."
            )

        # Stability descriptor
        lag_cv = std_lag / abs(mean_lag) if abs(mean_lag) > 0.5 else std_lag
        if lag_cv < 0.5 and std_lag < 2:
            stability_desc = "stable"
        elif lag_cv < 1.5:
            stability_desc = "moderately varying"
        else:
            stability_desc = "highly variable"

        stats_rows = [
            ["Window size", window],
            ["Step size", step],
            ["Max lag", max_lag],
            ["N windows", n_windows],
            ["N boundary-excluded", n_boundary],
            ["Boundary threshold", boundary_threshold],
            ["Mean optimal lag (ex-boundary)", round(mean_lag, 2)],
            ["Median optimal lag (ex-boundary)", round(median_lag, 1)],
            ["Std of optimal lag (ex-boundary)", round(std_lag, 2)],
            ["Mean |CCF| (ex-boundary)", round(mean_abs_ccf, 4)],
            ["% significant windows (AC-corrected)"
             if ac_corrected else "% significant windows",
             round(pct_significant, 1)],
            ["% significant windows (naive, for reference)",
             round(pct_significant_naive, 1)],
            ["Bartlett band at sig level "
             f"{significance:g} (AC-corrected)" if ac_corrected
             else f"Bartlett band at sig level {significance:g} (naive)",
             round(float(chosen_band), 4)],
            ["Effective n per window", round(float(n_eff_window), 1)],
            ["AC inflation factor", round(float(ac_inflation), 2)],
            ["Lag stability", stability_desc],
            ["Structural break detected",
             "Yes" if break_idx is not None else "No"],
        ]
        if break_idx is not None:
            center_ts = time_col[center_times[break_idx]] if time_col else f"window {break_idx}"
            stats_rows.append(["Structural break at", str(center_ts)])
        stats_table = make_table("Summary Statistics", ["Metric", "Value"], stats_rows)

        # CCF heatmap data (subsampled)
        max_heat_rows = 200
        heat_step = max(1, n_windows // max_heat_rows)
        heat_rows = []
        for w_idx in range(0, n_windows, heat_step):
            cidx = center_times[w_idx]
            t_label = time_col[cidx] if time_col else int(cidx + 1)
            row = [t_label]
            for lag_idx in range(n_lags_total):
                row.append(round(float(ccf_matrix[w_idx, lag_idx]), 4))
            heat_rows.append(row)

        heat_cols = ["Center Time"] + [str(lag) for lag in range(-max_lag, max_lag + 1)]
        heat_table = make_table("CCF Heatmap Data", heat_cols, heat_rows)

        # Build summary string via format_pairwise_summary (F2 convention).
        test_name = "Bartlett white-noise band"
        if ac_corrected:
            cv_formula = (f"±z(1-α/2)/sqrt(n_eff) with n_eff={n_eff_window:.0f} "
                          f"from Bartlett AC adjustment")
            ac_note = f"AC-corrected, n_eff={n_eff_window:.0f}"
        else:
            cv_formula = f"±z(1-α/2)/sqrt(window) = ±{chosen_band:.4f}"
            ac_note = "naive band (inputs appear ≈iid)"

        excluded_n = n_boundary

        prefix = (f"Rolling cross-correlation between '{x_name}' and "
                  f"'{y_name}' ({n} obs, window={window})")

        if break_idx is not None and pct_significant >= 10:
            # Split-regime summary. Compute pre/post regime stats on
            # boundary-excluded subsets of each segment.
            pre_boundary = boundary_mask[:break_idx]
            post_boundary = boundary_mask[break_idx:]
            pre_stats = _regime_stats(
                optimal_lags[:break_idx], optimal_ccfs[:break_idx], pre_boundary
            )
            post_stats = _regime_stats(
                optimal_lags[break_idx:], optimal_ccfs[break_idx:], post_boundary
            )
            break_date = (time_col[center_times[break_idx]]
                          if time_col else f"window {break_idx}")
            break_info = {
                "date": str(break_date),
                "n_pre": pre_stats["n_used"],
                "sign_pre": pre_stats["sign"],
                "magnitude_pre": pre_stats["magnitude"],
                "lag_pre": pre_stats["lag"],
                "direction_pre": pre_stats["direction_verb"],
                "n_post": post_stats["n_used"],
                "sign_post": post_stats["sign"],
                "magnitude_post": post_stats["magnitude"],
                "lag_post": post_stats["lag"],
                "direction_post": post_stats["direction_verb"],
            }
            plain_english = format_pairwise_summary(
                prefix, x_name, y_name,
                sign=pre_stats["sign"],
                magnitude=pre_stats["magnitude"],
                lag=pre_stats["lag"],
                direction_verb=pre_stats["direction_verb"],
                test_name=test_name,
                ac_note=ac_note,
                break_info=break_info,
                excluded_n=excluded_n,
            )
        elif pct_significant < 10:
            summary_stats = _regime_stats(optimal_lags, optimal_ccfs, boundary_mask)
            plain_english = format_pairwise_summary(
                prefix, x_name, y_name,
                sign=summary_stats["sign"],
                magnitude=summary_stats["magnitude"],
                lag=summary_stats["lag"],
                direction_verb=summary_stats["direction_verb"],
                test_name=test_name,
                ac_note=ac_note,
                excluded_n=excluded_n,
                extra=(f"Only {pct_significant:.0f}% of windows are "
                       f"significant — no consistent lead/lag relationship."),
            )
        else:
            summary_stats = _regime_stats(optimal_lags, optimal_ccfs, boundary_mask)
            plain_english = format_pairwise_summary(
                prefix, x_name, y_name,
                sign=summary_stats["sign"],
                magnitude=summary_stats["magnitude"],
                lag=summary_stats["lag"],
                direction_verb=summary_stats["direction_verb"],
                test_name=test_name,
                ac_note=ac_note,
                excluded_n=excluded_n,
                extra=(f"Pattern seen in {pct_significant:.0f}% of windows; "
                       f"lag is {stability_desc} (std={std_lag:.1f})."),
            )

        charting = (
            "Three-panel chart: (1) Heat map of CCF values over time and lag, "
            "(2) Time series of the optimal lag with significance band and "
            "boundary-hit windows marked, (3) Time series of the CCF at the "
            "optimal lag with the AC-corrected significance threshold overlaid. "
            "If a structural break was detected, shade pre- and post-break "
            "regions differently on all three panels."
        )

        progress_callback("Done", 100)

        # F3 — audit disclosure block.
        disclosure = format_significance_disclosure(
            test_name=test_name,
            critical_value_formula=cv_formula,
            ac_corrected=bool(ac_corrected),
            effective_n=float(n_eff_window),
        )

        audit = {
            "x_series": x_name,
            "y_series": y_name,
            "pair_used": [x_name, y_name],
            "pairs_ignored": [s[0] for s in all_series[2:]],
            "window": window,
            "step": step,
            "max_lag": max_lag,
            "n_windows": n_windows,
            "boundary_threshold_used": boundary_threshold,
            "n_windows_boundary_excluded": n_boundary,
            "mean_lag_ex_boundary": round(mean_lag, 2),
            "median_lag_ex_boundary": round(median_lag, 1),
            "std_lag_ex_boundary": round(std_lag, 2),
            "mean_abs_ccf_ex_boundary": round(mean_abs_ccf, 4),
            "pct_significant": round(pct_significant, 1),
            "pct_significant_naive_reference": round(pct_significant_naive, 1),
            "lag_stability": stability_desc,
            "n_obs": n,
            "structural_break_detected": break_idx is not None,
            "structural_break_details": {
                "confirmed": break_details.get("confirmed", False),
                "reason": break_details.get("reason"),
                "channel": break_details.get("channel"),
                "post_run": break_details.get("post_run"),
                "pre_run": break_details.get("pre_run"),
            },
            "structural_break_window_index": int(break_idx) if break_idx is not None else None,
            "structural_break_date": (
                str(time_col[center_times[break_idx]])
                if break_idx is not None and time_col else None
            ),
        }
        audit.update(disclosure)

        # Assemble interpretation-input dict. The spec's split/single
        # routing reads `structural_break`; per-regime facts live in
        # pre_* / post_* (split) or single_* (single/sub-threshold).
        _interp_input = {
            "series_name_x": x_name,
            "series_name_y": y_name,
            "n_obs": n,
            "window": window,
            "n_windows": n_windows,
            "pct_significant": float(pct_significant),
            "n_excluded": int(n_boundary),
            "ac_corrected": bool(ac_corrected),
            "frequency": ctx.frequency,
            "structural_break": break_idx is not None and pct_significant >= 10,
            "candidate_break_idx": (int(break_idx)
                                    if break_idx is not None else None),
            "min_segment": 8,
        }
        if break_idx is not None and pct_significant >= 10:
            # Signed ρ = +magnitude when sign is "+", else -magnitude
            _pre_signed = (pre_stats["magnitude"]
                           if pre_stats["sign"] == "+" else -pre_stats["magnitude"])
            _post_signed = (post_stats["magnitude"]
                            if post_stats["sign"] == "+" else -post_stats["magnitude"])
            # Per-segment pct-significant derived from sig_mask on slices
            pre_mask = sig_mask[:break_idx]
            post_mask = sig_mask[break_idx:]
            _interp_input.update({
                "break_date": break_date,
                "pre_median_rho": float(_pre_signed),
                "pre_median_lag": int(pre_stats["lag"]),
                "pre_pct_significant": float(100.0 * pre_mask.mean())
                    if len(pre_mask) else 0.0,
                "pre_n_windows": int(break_idx),
                "post_median_rho": float(_post_signed),
                "post_median_lag": int(post_stats["lag"]),
                "post_pct_significant": float(100.0 * post_mask.mean())
                    if len(post_mask) else 0.0,
                "post_n_windows": int(n_windows - break_idx),
            })
        else:
            # Single-regime (or low-significance) path
            _single_signed = (summary_stats["magnitude"]
                              if summary_stats["sign"] == "+"
                              else -summary_stats["magnitude"])
            _interp_input.update({
                "single_median_rho": float(_single_signed),
                "single_median_lag": int(summary_stats["lag"]),
            })

        interp = build_interpretation("rolling_ccf_lag", _interp_input)

        return make_response(
            ctx,
            tables=[rolling_table, lag_dist_table, stats_table, heat_table],
            plain_english_summary=plain_english,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Rolling CCF analysis failed: {e}",
            error_fixes=[
                "Ensure both series are numeric and the same length.",
                "Reduce window size if the series is short.",
                "Increase step size for faster computation.",
            ],
        )
