"""Critical Slowing Down early-warning signal detector.

Detects whether a time series exhibits the statistical signatures
of approaching a critical transition (phase transition, regime shift,
bifurcation). Implements the canonical CSD pipeline from the
dynamical-systems literature (Scheffer 2009, Dakos 2012,
Diks-Hommes-Wang 2018):

  Stage A: detrend the input series (Gaussian kernel / first diff /
           linear) to produce residuals.
  Stage B: compute rolling indicators on the residuals (AR(1),
           variance, skewness, kurtosis, return rate, density ratio).
  Stage C: compute Kendall's tau trend statistic on each rolling
           indicator series. With compute_pvalues=True (default),
           also compute empirical p-values via AR(1)-bootstrap
           surrogates.
  Stage D: combine per-indicator taus into composite EWS score and
           classify state as normal / elevated / critical.

Honest disclosure: CSD signals are descriptive of approaching
transitions in dynamical-systems theory. Their predictive value
out-of-sample on financial market data is contested in the
empirical literature. Detrending bandwidth choice materially
affects results. Rising variance can signal volatility clustering
without phase transition.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
import scipy.stats

from techniques import _csd_helpers as csd
from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# Preset configuration: rolling-window/lookback fractions + surrogate
# count. Defaults applied when ctx.params doesn't override.
#
# Phase 4 Session 3 (P4-3 pathway b, 2026-05-01) — auto-cap by series
# length. The preset ``n_surrogates`` value is the UPPER BOUND on the
# effective surrogate count when the user does not explicitly override.
# When defaulting, the wrapper computes::
#
#     n_surrogates_effective = max(MIN_SURROGATES_FLOOR,
#                                  min(preset_default, T // 10))
#
# where ``MIN_SURROGATES_FLOOR`` (=100) is the methodological floor for
# stable empirical p-value estimation. The cap protects against the
# Phase 3.5 Session 8 OOM-blow-up case (T10Y2Y at T=2501 with
# ``n_surrogates=1000`` produced an ~11.7 GiB complex128 allocation in
# the surrogate-rolling-indicator vectorisation). Empirical workaround
# at S8 used n_surrogates=100; the auto-cap yields between 100 and the
# preset default, scaling smoothly with T.
#
# Explicit user-supplied ``n_surrogates`` is NOT capped — users typing
# the value have implicitly opted into managing their own memory
# constraints.
_PRESET_CONFIG = {
    "Fast": {
        "window_fraction": 0.5,
        "kendall_lookback_fraction": 0.3,
        "n_surrogates": 200,
        "default_compute_pvalues": True,
    },
    "Balanced": {
        "window_fraction": 0.5,
        "kendall_lookback_fraction": 0.5,
        "n_surrogates": 1000,
        "default_compute_pvalues": True,
    },
    "Thorough": {
        "window_fraction": 0.5,
        "kendall_lookback_fraction": 0.5,
        "n_surrogates": 5000,
        "default_compute_pvalues": True,
    },
}

# Phase 4 S3 (P4-3): methodological floor on n_surrogates for stable
# empirical p-value estimation. The auto-cap formula never goes below
# this regardless of T.
_MIN_SURROGATES_FLOOR = 100

# State classification thresholds (composite z-score sigma)
_THRESHOLD_ELEVATED = 1.0
_THRESHOLD_CRITICAL = 1.5

_INDICATOR_NAMES = (
    "ar1", "variance", "skewness", "kurtosis",
    "return_rate", "density_ratio",
)


def _none_audit_fields() -> dict[str, Any]:
    """Return a dict with all 33 audit field keys defaulted to None.
    Used by error / insufficient-data short-circuits so downstream
    spec triggers always have a stable schema to inspect."""
    base = {
        "ews_composite_score": None,
        "ews_state": None,
        "composite_method": None,
        "detrending_method": None,
        "detrending_bandwidth": None,
        "detrending_residuals_stationary": None,
        "detrending_residuals_adf_pvalue": None,
        "rolling_window": None,
        "kendall_lookback": None,
        "compute_pvalues": None,
        "n_surrogates": None,
        # Phase 4 S3 (P4-3): transparency on auto-cap behaviour.
        "n_surrogates_default_per_preset": None,
        "n_surrogates_auto_capped": None,
        "series_length": None,
        "tail_skewness": None,
        "tail_kurtosis": None,
        "post_transition_indicated": None,
    }
    for name in _INDICATOR_NAMES:
        base[f"tau_{name}"] = None
        base[f"tau_{name}_pvalue"] = None
        base[f"rolling_{name}_series"] = None
    return base


def _build_insufficient_data_audit(
    T: int,
    rolling_window: int,
    kendall_lookback: int,
) -> dict[str, Any]:
    audit = _none_audit_fields()
    audit["series_length"] = int(T)
    audit["rolling_window"] = int(rolling_window)
    audit["kendall_lookback"] = int(kendall_lookback)
    return audit


def _compute_surrogate_taus(
    surrogates: np.ndarray,
    rolling_window: int,
    kendall_lookback: int,
    indicator_keys: list[str],
    progress_callback,
) -> dict[str, np.ndarray]:
    """For all surrogates simultaneously, compute the rolling
    indicators and apply Kendall tau on the trailing
    kendall_lookback points. Returns dict mapping indicator name
    -> length-n_surrogates array of surrogate taus.

    Vectorized via _vectorized_rolling_indicators (sliding-window
    numpy ops across all surrogates) + _vectorized_kendall_tau_per_row
    (per-row scipy kendalltau on the trailing slice). Roughly two
    orders of magnitude faster than the prior per-surrogate
    Python loop.

    The empirical p-value is then `mean(surrogate_tau >= observed_tau)`.
    """
    n_surr = surrogates.shape[0]
    progress_callback(
        f"Vectorized rolling indicators on {n_surr} surrogates", 60,
    )
    rolling = csd._vectorized_rolling_indicators(
        surrogates, rolling_window,
    )
    taus: dict[str, np.ndarray] = {}
    progress_callback("Computing Kendall tau on surrogate trails", 70)
    for name in indicator_keys:
        arr_2d = rolling[name]  # (n_surr, n_windows)
        if arr_2d.size == 0:
            taus[name] = np.zeros(n_surr, dtype=np.float64)
            continue
        # Restrict to the trailing kendall_lookback slice
        if arr_2d.shape[1] > kendall_lookback:
            tail_2d = arr_2d[:, -kendall_lookback:]
        else:
            tail_2d = arr_2d
        taus[name] = csd._vectorized_kendall_tau_per_row(tail_2d)
    return taus


def _build_output_table(audit: dict) -> dict:
    """Render compact output table summarizing the EWS result."""
    rows = [
        ["Composite EWS score", round(float(audit["ews_composite_score"]), 4)
         if audit.get("ews_composite_score") is not None else None],
        ["EWS state", audit.get("ews_state")],
        ["Composite method", audit.get("composite_method")],
        ["Detrending method", audit.get("detrending_method")],
        ["Rolling window", audit.get("rolling_window")],
        ["Kendall lookback", audit.get("kendall_lookback")],
        ["Series length", audit.get("series_length")],
        [
            "Residuals stationary",
            audit.get("detrending_residuals_stationary"),
        ],
        [
            "Residuals ADF p-value",
            round(float(audit["detrending_residuals_adf_pvalue"]), 4)
            if audit.get("detrending_residuals_adf_pvalue") is not None
            else None,
        ],
        [
            "Post-transition indicated",
            audit.get("post_transition_indicated"),
        ],
    ]
    for name in _INDICATOR_NAMES:
        tau = audit.get(f"tau_{name}")
        pval = audit.get(f"tau_{name}_pvalue")
        rows.append([
            f"tau_{name}",
            round(float(tau), 4) if tau is not None else None,
        ])
        rows.append([
            f"tau_{name}_pvalue",
            round(float(pval), 4) if pval is not None else None,
        ])
    return make_table(
        name="CSD Indicator Summary",
        columns=["metric", "value"],
        rows=rows,
    )


def run(ctx: RunContext, progress_callback) -> dict:
    """Execute CSD early-warning detection on input series.

    Required ctx series:
      single primary series (univariate v1).

    Optional ctx.params:
      detrending_method: "gaussian" (default) | "first_diff" | "linear"
      detrending_bandwidth: float
        Gaussian kernel sigma in samples. Default T/10.
        Ignored if detrending_method != "gaussian".
      rolling_window: int
        Default per preset (window_fraction * T).
      kendall_lookback: int
        Default per preset.
      compute_pvalues: bool
        Default True (per Q9 design lock).
      n_surrogates: int
        Default per preset (Fast=200, Balanced=1000, Thorough=5000).
      composite_method: "equal_weight_zscore" (default) |
        "fisher_combined"
      expose_rolling_series: bool (default True)
    """
    t0 = time.time()
    progress_callback("Loading series", 5)

    # Input
    try:
        name, values = ctx.get_primary_series()
    except Exception as e:
        return make_error_response(
            ctx, error_message=f"Failed to load primary series: {e}",
        )
    y = np.asarray(values, dtype=np.float64)
    T = int(y.size)

    cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

    # Resolve params
    detrending_method = str(
        ctx.get_param("detrending_method", "gaussian")
    )
    if detrending_method not in ("gaussian", "first_diff", "linear"):
        audit = _none_audit_fields()
        audit["series_length"] = T
        return make_error_response(
            ctx,
            error_message=(
                f"detrending_method={detrending_method!r} not in "
                f"{{gaussian, first_diff, linear}}"
            ),
        )

    rolling_window_param = ctx.get_param("rolling_window", None)
    # CAI Phase 2 Session 28 fix (F-CSD-ROLLINGWIN +
    # F-CSD-ROLLINGWIN-NEG): explicit range gate. Pre-fix,
    # rolling_window=0 silently fell back to default (truthy
    # check at line 258); negative values flowed through to
    # int() conversion and downstream rolling helpers with
    # undefined behavior.
    if rolling_window_param is not None:
        try:
            _rw_int = int(rolling_window_param)
        except (TypeError, ValueError):
            return make_error_response(
                ctx,
                f"rolling_window must be a positive integer. "
                f"Got {rolling_window_param!r}.",
                error_fixes=[
                    "Use a positive integer (typical 50-200).",
                ],
            )
        if _rw_int < 1:
            return make_error_response(
                ctx,
                f"rolling_window must be >= 1. Got {_rw_int}.",
                error_fixes=[
                    "Use a positive integer (typical 50-200). "
                    "Pass None to use the preset-based default.",
                ],
            )
        rolling_window = _rw_int
    else:
        rolling_window = max(50, int(cfg["window_fraction"] * T))

    indicator_axis_len_default = max(1, T - rolling_window + 1)
    kendall_lookback_param = ctx.get_param("kendall_lookback", None)
    # CAI Phase 2 Session 28 fix (F-CSD-KENDALL): explicit
    # range gate.
    if kendall_lookback_param is not None:
        try:
            _kl_int = int(kendall_lookback_param)
        except (TypeError, ValueError):
            return make_error_response(
                ctx,
                f"kendall_lookback must be a positive integer. "
                f"Got {kendall_lookback_param!r}.",
                error_fixes=[
                    "Use a positive integer (typical 30-100).",
                ],
            )
        if _kl_int < 1:
            return make_error_response(
                ctx,
                f"kendall_lookback must be >= 1. Got {_kl_int}.",
                error_fixes=[
                    "Use a positive integer (typical 30-100).",
                ],
            )
        kendall_lookback = _kl_int
    else:
        kendall_lookback = max(
            30, int(cfg["kendall_lookback_fraction"] * indicator_axis_len_default),
        )

    compute_pvalues = bool(
        ctx.get_param("compute_pvalues", cfg["default_compute_pvalues"])
    )
    # Phase 4 S3 (P4-3 pathway b, 2026-05-01) — auto-cap n_surrogates
    # by series length when defaulting from preset config. Closes the
    # Phase 3.5 S8 OOM-blow-up on long fixtures (T10Y2Y T=2501 with
    # n_surrogates=1000 produced an ~11.7 GiB complex128 allocation).
    # Cap formula: effective = max(MIN_FLOOR, min(preset_default, T//10)).
    # User-supplied values bypass the cap (explicit user opt-in to
    # managing their own memory constraints).
    n_surrogates_user = ctx.get_param("n_surrogates")
    n_surrogates_default_per_preset = int(cfg["n_surrogates"])
    if n_surrogates_user is not None:
        n_surrogates = int(n_surrogates_user)
        n_surrogates_auto_capped = False
    else:
        n_surrogates_capped = max(
            _MIN_SURROGATES_FLOOR,
            min(n_surrogates_default_per_preset, T // 10),
        )
        n_surrogates_auto_capped = (
            n_surrogates_capped < n_surrogates_default_per_preset
        )
        n_surrogates = n_surrogates_capped
    composite_method = str(
        ctx.get_param("composite_method", "equal_weight_zscore")
    )
    # CAI Phase 2 Session 28 fix (F-CSD-COMPOSITE): explicit
    # allowlist gate. Pre-fix, invalid composite_method silently
    # fell through to "equal_weight_zscore" via if/else at
    # _csd_helpers.py:_composite_ews_score line 492/513.
    # Session 18 silent-fall-through pattern.
    _COMPOSITE_OPTS = ("equal_weight_zscore", "fisher_combined")
    if composite_method not in _COMPOSITE_OPTS:
        return make_error_response(
            ctx,
            f"Unknown composite_method '{composite_method}'. Must "
            f"be one of: {', '.join(_COMPOSITE_OPTS)}.",
            error_fixes=[
                "Use 'equal_weight_zscore' (default; averages "
                "z-scored Kendall taus across indicators) or "
                "'fisher_combined' (combines per-indicator "
                "p-values via Fisher's method; requires "
                "compute_pvalues=True).",
            ],
        )
    expose_rolling_series = bool(
        ctx.get_param("expose_rolling_series", True)
    )

    # Insufficient-data guard (D-CSD-4 trigger fires)
    if T < rolling_window + kendall_lookback:
        audit = _build_insufficient_data_audit(
            T, rolling_window, kendall_lookback,
        )
        return make_response(
            ctx,
            status="insufficient_data",
            audit_fields=audit,
            error_message=(
                f"Series length T={T} is less than required "
                f"rolling_window + kendall_lookback = "
                f"{rolling_window + kendall_lookback}. CSD "
                f"literature recommends T >= 500 for stable "
                f"estimation."
            ),
            tables=[],
        )

    # ---- Stage A: Detrending
    progress_callback("Stage A: Detrending residuals", 10)
    detrending_bandwidth: float | None = None
    if detrending_method == "gaussian":
        bw_param = ctx.get_param("detrending_bandwidth", None)
        detrending_bandwidth = float(bw_param) if bw_param else float(T / 10.0)
        residuals = csd._gaussian_detrend(y, detrending_bandwidth)
    elif detrending_method == "first_diff":
        residuals = csd._first_difference_detrend(y)
    else:  # linear
        residuals = csd._linear_detrend(y)

    # Stationarity check on residuals (D-CSD-5)
    is_stationary, adf_pvalue = csd._check_residual_stationarity(residuals)

    # ---- Stage B: Rolling indicators
    progress_callback("Stage B: Rolling indicators", 25)
    rolling_ar1 = csd._rolling_ar1(residuals, rolling_window)
    rolling_var = csd._rolling_variance(residuals, rolling_window)
    rolling_skew = csd._rolling_skewness(residuals, rolling_window)
    rolling_kurt = csd._rolling_kurtosis(residuals, rolling_window)
    rolling_rr = csd._rolling_return_rate(rolling_ar1)
    rolling_dr = csd._rolling_density_ratio(residuals, rolling_window)

    indicator_series = {
        "ar1": rolling_ar1,
        "variance": rolling_var,
        "skewness": rolling_skew,
        "kurtosis": rolling_kurt,
        "return_rate": rolling_rr,
        "density_ratio": rolling_dr,
    }

    # Restrict to the trailing Kendall-lookback window (per Dakos
    # 2012: tau is computed on a trailing slice of indicator series).
    tail_indicators = {
        name: arr[-kendall_lookback:] if arr.size >= kendall_lookback
        else arr
        for name, arr in indicator_series.items()
    }

    # ---- Stage C: Kendall tau + p-values
    progress_callback("Stage C: Kendall tau", 50)
    indicator_taus: dict[str, float] = {}
    indicator_pvalues: dict[str, float] = {}

    if compute_pvalues:
        progress_callback(
            f"Stage C: Computing {n_surrogates} AR(1) surrogates",
            55,
        )
        surrogates = csd._generate_ar1_surrogates(
            residuals, n_surrogates=n_surrogates, seed=int(ctx.seed),
        )
        surrogate_taus = _compute_surrogate_taus(
            surrogates, rolling_window, kendall_lookback,
            list(indicator_series.keys()), progress_callback,
        )
        for name, observed_arr in tail_indicators.items():
            tau, _ = csd._kendall_tau(observed_arr)
            null_dist = surrogate_taus[name]
            empirical_p = float(np.mean(null_dist >= tau))
            indicator_taus[name] = float(tau)
            indicator_pvalues[name] = empirical_p
    else:
        for name, observed_arr in tail_indicators.items():
            tau, asymp_p = csd._kendall_tau(observed_arr)
            indicator_taus[name] = float(tau)
            indicator_pvalues[name] = float(asymp_p)

    # ---- Stage D: Composite scoring
    progress_callback("Stage D: Composite EWS score", 85)
    composite_score, ews_state = csd._composite_ews_score(
        indicator_taus,
        indicator_pvalues if composite_method == "fisher_combined" else None,
        method=composite_method,
        n_indicator_points=int(kendall_lookback),
        threshold_elevated=_THRESHOLD_ELEVATED,
        threshold_critical=_THRESHOLD_CRITICAL,
    )

    # ---- Post-transition disambiguation (tail residuals)
    tail_residuals = residuals[-kendall_lookback:] if residuals.size >= kendall_lookback else residuals
    if tail_residuals.size >= 4:
        tail_skewness = float(scipy.stats.skew(tail_residuals, bias=False))
        tail_kurtosis = float(
            scipy.stats.kurtosis(tail_residuals, fisher=True, bias=False)
        )
    else:
        tail_skewness = 0.0
        tail_kurtosis = 0.0
    post_transition_indicated = bool(
        abs(tail_skewness) > 1.0 or abs(tail_kurtosis) > 3.0
    )

    # ---- Build audit_fields (33 keys)
    fit_time = round(time.time() - t0, 2)
    audit: dict[str, Any] = {
        # Composite (3)
        "ews_composite_score": float(composite_score),
        "ews_state": ews_state,
        "composite_method": composite_method,
        # Detrending (4)
        "detrending_method": detrending_method,
        "detrending_bandwidth": (
            float(detrending_bandwidth)
            if detrending_bandwidth is not None else None
        ),
        "detrending_residuals_stationary": bool(is_stationary),
        "detrending_residuals_adf_pvalue": float(adf_pvalue),
        # Per-indicator Kendall taus (6)
        "tau_ar1": float(indicator_taus["ar1"]),
        "tau_variance": float(indicator_taus["variance"]),
        "tau_skewness": float(indicator_taus["skewness"]),
        "tau_kurtosis": float(indicator_taus["kurtosis"]),
        "tau_return_rate": float(indicator_taus["return_rate"]),
        "tau_density_ratio": float(indicator_taus["density_ratio"]),
        # Per-indicator p-values (6)
        "tau_ar1_pvalue": float(indicator_pvalues["ar1"]),
        "tau_variance_pvalue": float(indicator_pvalues["variance"]),
        "tau_skewness_pvalue": float(indicator_pvalues["skewness"]),
        "tau_kurtosis_pvalue": float(indicator_pvalues["kurtosis"]),
        "tau_return_rate_pvalue": float(indicator_pvalues["return_rate"]),
        "tau_density_ratio_pvalue": float(
            indicator_pvalues["density_ratio"]
        ),
        # Post-transition disambiguation (3)
        "tail_skewness": tail_skewness,
        "tail_kurtosis": tail_kurtosis,
        "post_transition_indicated": post_transition_indicated,
        # Methodology disclosure (5)
        "rolling_window": int(rolling_window),
        "kendall_lookback": int(kendall_lookback),
        "compute_pvalues": bool(compute_pvalues),
        "n_surrogates": (int(n_surrogates) if compute_pvalues else None),
        # Phase 4 S3 (P4-3): auto-cap transparency. The default-per-
        # preset is what the Balanced/Fast/Thorough preset would
        # produce ABSENT the cap; n_surrogates_auto_capped indicates
        # whether the cap fired (True) or not (False). Both fields
        # are None when n_surrogates is user-supplied (no cap then)
        # OR when compute_pvalues is False (no surrogates path
        # exercised).
        "n_surrogates_default_per_preset": (
            int(n_surrogates_default_per_preset) if compute_pvalues else None
        ),
        "n_surrogates_auto_capped": (
            bool(n_surrogates_auto_capped) if compute_pvalues else None
        ),
        "series_length": int(T),
    }

    # Optional rolling-indicator series (6 fields, conditionally None)
    if expose_rolling_series:
        audit["rolling_ar1_series"] = rolling_ar1.tolist()
        audit["rolling_variance_series"] = rolling_var.tolist()
        audit["rolling_skewness_series"] = rolling_skew.tolist()
        audit["rolling_kurtosis_series"] = rolling_kurt.tolist()
        audit["rolling_return_rate_series"] = rolling_rr.tolist()
        audit["rolling_density_ratio_series"] = rolling_dr.tolist()
    else:
        for key in (
            "rolling_ar1_series", "rolling_variance_series",
            "rolling_skewness_series", "rolling_kurtosis_series",
            "rolling_return_rate_series", "rolling_density_ratio_series",
        ):
            audit[key] = None

    output_table = _build_output_table(audit)

    plain_summary = (
        f"Critical Slowing Down: composite EWS score = "
        f"{composite_score:+.2f}σ ({ews_state}). "
        f"Detrending: {detrending_method}; rolling window = "
        f"{rolling_window}; Kendall lookback = {kendall_lookback}."
    )

    progress_callback("Done", 100)

    return make_response(
        ctx,
        status="success",
        audit_fields=audit,
        tables=[output_table],
        plain_english_summary=plain_summary,
    )
