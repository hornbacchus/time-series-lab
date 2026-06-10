# Hand-off: `critical_slowing_down` wrapper — Phase 1 + Phase 2 specifications

**Date:** 2026-04-25
**Project:** TSL (Time Series Lab)
**Plan file:** `plans\glistening-wishing-mountain.md`
**Origin:** First new technique addition since the verification initiative
closed (commit `ee44ee4`). Implements Stage 1 of the deraAI deck evaluation —
Critical Slowing Down early-warning detector.

This document is the complete specification handoff for Phase 3 (Apply).
Phase 1 (Design Audit) and Phase 2 (Implementation Plan) are reproduced in
full. **Code should NOT invent design decisions during execution.** All
design choices are locked in this document; gaps that legitimately need
runtime determination (e.g., ewstools function signatures, technique
category from existing catalog) are explicitly flagged in §11.

---

## 0. Workflow framing

Standard 5-phase TSL follow-up workflow + Phase 4.5 parity check from day
one. Per the Phase 3.1 workflow doc shipped at commit `fe64405`, this is
the canonical "first new technique with full pattern" exercise.

| Phase | Status |
|---|---|
| Phase 1 — Design Audit | COMPLETE (reproduced §2-§6 below) |
| Phase 2 — Implementation Plan | COMPLETE (reproduced §7-§10 below) |
| Phase 3 — Apply | THIS HANDOFF — execute per §12 nine-stage sequence |
| Phase 4 — Invariants | gate at Stage 3.4 |
| Phase 4.5 — Reference parity | gate at Stage 3.7 |
| Phase 5 — Canonicals | gate at Stage 3.6 |

Single commit per Template C (Phase 3.1 workflow doc terminology) at
Stage 3.9.

---

## 1. Locked design decisions (Q1-Q9 + Refinements A/B)

These were reviewed and approved in the planning conversation. Code does
NOT re-derive these.

| Q | Decision |
|---|---|
| Q1 — Scope | Univariate v1 only. Multivariate deferred to future follow-up. |
| Q2 — Detrending | Three methods: gaussian (default), first_diff, linear. |
| Q3 — Indicators | All 6 standard indicators exposed: AR(1), variance, skewness, kurtosis, return rate, density ratio. |
| Q4 — Composite EWS | Equal-weight z-score default; Fisher-combined opt-in via composite_method param. |
| Q5 — Triggers | 5 D-triggers: composite_elevated, consistent_tau_pattern, post_transition, insufficient_data, non_stationary_residuals. |
| Q6 — Rolling series | Exposed by default in audit_fields, gated by `expose_rolling_series=True` (param-overridable). |
| Q7 — Phase 4.5 parity | Python `ewstools` (Bury 2023). In-process, no R subprocess overhead. |
| Q8 — Technique ID | `critical_slowing_down` (full name, not abbreviation). |
| Q9 — `compute_pvalues` default | `True` (surrogate p-values populate by default). |
| Refinement A — Phase 4.5 Tier 2 | Informational-only for v1 (composite score and p-values recorded but not asserted). |
| Refinement B — Surrogate method | AR(1) bootstrap only for v1. Phase-randomized deferred. |

---

## 2. Phase 1 — Step 1: Adjacent-wrapper references for design consistency

CSD detection isn't currently in TSL. Adjacent wrappers worth referencing:

- `stochastic_volatility.py` — closest analogue for "rolling-statistical-
  estimator + posterior-summary" structure
- `evt_pot_gpd.py` — closest analogue for "early-warning indicator with
  multiple sub-statistics"
- `har_cj.py` — closest analogue for "decomposed-output table with
  multiple coefficients"
- `johansen_cointegration.py` — closest analogue for "rank/regime-state
  output with critical-value comparison"

The `_kalman_common.py` and `_sv_mcmc.py` private-helper pattern is the
template for `_csd_helpers.py`.

---

## 3. Phase 1 — Step 2: Canonical CSD pipeline

Reading academic specifications carefully (Scheffer 2009, Dakos et al.
2012, Diks-Hommes-Wang 2018):

The CSD pipeline has four conceptual stages:

**Stage A — Detrending.** CSD signals are detected on residuals from a
slowly-varying mean. Three methods supported:
- Gaussian kernel smoothing (Dakos default)
- First differences (simpler, less sensitive)
- Linear OLS detrending (least common)

**Stage B — Rolling indicator computation.** On detrended residuals,
compute over a rolling window:
- Lag-1 autocorrelation AR(1) — primary signal
- Variance — primary signal
- Skewness — secondary
- Kurtosis — secondary
- Return rate (1 - AR(1)) — derived
- Density ratio (low-freq spectral power / total) — secondary

**Stage C — Trend statistic.** Kendall's τ over a configurable trailing
window of rolling indicator series. Rising τ on AR(1) and variance is
the "EWS firing" signal.

**Stage D — Composite scoring.** Standardize Kendall τ values and combine
into a single EWS score classified as normal / elevated / critical.

**Methodological knobs that matter:**
- Detrending bandwidth (Gaussian σ): drives signal sensitivity
- Rolling window size: too small → noisy; too large → late detection
- Kendall τ lookback: trade-off between trend power and recency
- Surrogate generation method: AR(1) bootstrap (locked v1)

---

## 4. Phase 1 — Step 4: File topology

| File | Action | LOC |
|---|---|---|
| `engine/techniques/critical_slowing_down.py` | NEW wrapper | ~470 |
| `engine/techniques/_csd_helpers.py` | NEW private helpers (14 functions) | ~250 |
| `engine/interpretation/specs/critical_slowing_down.py` | NEW spec (5 triggers) | ~360 |
| `engine/tests/test_interpretation_contract.py` | T14 fixture (32 keys) + T15 allowlist | +50 |
| `resources/catalog/techniques_catalog.json` | NEW technique entry | +60 |
| `resources/techniques_md/critical_slowing_down.md` | NEW documentation | ~200 |
| `tools/validate_critical_slowing_down_canonicals.py` | NEW canonicals (5 cases) | ~280 |
| `tools/reference_parity/harness/checks/critical_slowing_down.py` | NEW Phase 4.5 parity | ~180 |
| `tools/reference_parity/fixtures/critical_slowing_down_logistic_map.npz` | NEW fixture | (binary) |
| `tools/reference_parity/fixtures/critical_slowing_down_logistic_map.sha256` | NEW SHA sidecar | +1 |
| `docs/follow_up_check_coverage.md` | Update mapping table | +1 |
| **Total** | | **~1850 LOC** |

**Note:** Phase 1 originally said "12 helpers"; correct count is **14**
(see §7.1 below for full enumeration).

---

## 5. Phase 1 — Step 5: Canonical design (5 cases)

| # | Case | Verification |
|---|---|---|
| C1 | Stationary white noise (no CSD) | Composite score < 1.0σ; ews_state="normal"; D-CSD-1 does not fire |
| C2 | Logistic map approaching saddle-node bifurcation (canonical CSD) | Composite score > 1.0σ; ews_state in {"elevated","critical"}; D-CSD-2 fires (consistent τ on AR(1) + variance) |
| C3 | Already-shifted regime (post-transition) | High tail skewness/kurtosis; D-CSD-3 fires (post_transition_indicated=True) |
| C4 | Insufficient data (T < min_window + lookback) | status="insufficient_data"; D-CSD-4 fires; no crash |
| C5 | Non-stationary residuals after detrending (random walk + linear detrending) | D-CSD-5 fires; detrending_residuals_stationary=False |

---

## 6. Phase 1 — Step 6: Phase 4.5 parity design

**Reference:** Python `ewstools` (Bury 2023). In-process, no R subprocess.

**Fixture:** Logistic-map approaching saddle-node bifurcation per Dakos
2012 setup:
- T=2000 timesteps
- Slowly-varying control parameter from r=2.5 to r=3.6
- Gaussian observation noise σ=0.05
- True bifurcation at r≈3.0
- Seed=42; canonical_seed=42 in fixture metadata

**Tolerance ladder (per Phase 3.1 workflow doc):**

**Tier 1 (strict, bitwise):**
- Rolling AR(1) series: `abs_tol=1e-8`
- Rolling variance series: `abs_tol=1e-8`
- Kendall τ on AR(1): `abs_tol=1e-8`
- Kendall τ on variance: `abs_tol=1e-8`

**Tier 2 (informational only for v1):**
- Composite EWS score: not asserted (depends on weighting choice)
- Empirical p-values: not asserted (ewstools may use different surrogate
  methodology than TSL)

Per Refinement A, Tier 2 is recorded but not commit-blocking in v1.

---

## 7. Phase 2 — Implementation Plan

### 7.1 `_csd_helpers.py` — 14 private helpers

**Location:** `engine/techniques/_csd_helpers.py` (NEW). Single underscore
prefix per existing convention (`_sv_mcmc.py`, `_kalman_common.py`).

**Top-level docstring:**

```python
"""Private helpers for the critical_slowing_down wrapper.

Implements the four-stage CSD pipeline:
  Stage A — Detrending (Gaussian kernel / first-diff / linear)
  Stage B — Rolling indicator computation (6 indicators)
  Stage C — Kendall tau trend statistic with p-value option
  Stage D — Composite EWS scoring

References:
  Scheffer, M. (2009). Critical Transitions in Nature and Society.
    Princeton Univ. Press.
  Dakos, V. et al. (2012). Methods for detecting early warnings of
    critical transitions in time series illustrated using simulated
    ecological data. PLoS ONE 7(7): e41010.
  Diks, C., Hommes, C., Wang, J. (2018). Critical slowing down as
    an early warning signal for financial crises? Empirical
    Economics.
  Bury, T.M. et al. (2023). ewstools: A Python package for early
    warning signals of bifurcations in time series data.
"""
```

**Function signatures (14 functions):**

```python
# ─────────────────────────────────────────────────────
# Stage A — Detrending (3 functions + 1 stationarity check)
# ─────────────────────────────────────────────────────

def _gaussian_detrend(y: np.ndarray, bandwidth: float) -> np.ndarray:
    """Gaussian-kernel detrending. Returns residuals y - smoothed(y).

    Bandwidth is the kernel sigma (in samples). Default in literature
    is T/10. Uses scipy.ndimage.gaussian_filter1d with mode='reflect'
    to handle edges.
    """

def _first_difference_detrend(y: np.ndarray) -> np.ndarray:
    """First-difference detrending. Returns y[1:] - y[:-1].
    Output length T-1.
    """

def _linear_detrend(y: np.ndarray) -> np.ndarray:
    """Linear OLS detrending. Returns residuals from y ~ a + b*t.
    Uses scipy.signal.detrend(type='linear').
    """

def _check_residual_stationarity(
    residuals: np.ndarray,
    significance: float = 0.05,
) -> tuple[bool, float]:
    """ADF test for stationarity of detrending residuals.

    Returns (is_stationary, adf_pvalue). is_stationary is True
    when ADF rejects the unit-root null at `significance`.
    Used by D-CSD-5 (non-stationary-residuals) trigger.

    Uses statsmodels.tsa.stattools.adfuller(residuals).
    """

# ─────────────────────────────────────────────────────
# Stage B — Rolling indicators (6 functions)
# ─────────────────────────────────────────────────────

def _rolling_ar1(
    residuals: np.ndarray,
    window: int,
) -> np.ndarray:
    """Rolling lag-1 autocorrelation over window of size `window`.
    Returns array of length T - window + 1.

    Within each window: compute corrcoef(x[:-1], x[1:])[0,1].
    Right-aligned convention (output index k corresponds to window
    [k, k+window-1] in the input). Match ewstools convention at
    apply time — verify with unit test against ewstools output on
    a shared synthetic input.
    """

def _rolling_variance(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample variance (ddof=1). Returns length T-W+1.
    Right-aligned.
    """

def _rolling_skewness(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample skewness (Fisher-Pearson). Length T-W+1.
    Uses scipy.stats.skew with bias=False to match ewstools default.
    Right-aligned.
    """

def _rolling_kurtosis(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample excess kurtosis (Fisher). Length T-W+1.
    Uses scipy.stats.kurtosis(fisher=True, bias=False).
    Right-aligned.
    """

def _rolling_return_rate(rolling_ar1: np.ndarray) -> np.ndarray:
    """Rolling return rate = 1 - AR(1). Derived; same length as
    rolling_ar1. Higher return rate = faster recovery = less CSD.
    """

def _rolling_density_ratio(
    residuals: np.ndarray,
    window: int,
    cutoff_fraction: float = 0.1,
) -> np.ndarray:
    """Rolling spectral density ratio (low-freq power / total power).

    Within each window: compute periodogram (scipy.signal.periodogram),
    integrate power below cutoff_fraction * Nyquist, divide by total
    power. CSD theory predicts this ratio rises as system approaches
    transition.
    Length T-W+1. Right-aligned.
    """

# ─────────────────────────────────────────────────────
# Stage C — Kendall tau + surrogates (3 functions)
# ─────────────────────────────────────────────────────

def _kendall_tau(indicator_series: np.ndarray) -> tuple[float, float]:
    """Kendall tau-b on (time_index, indicator) pairs.
    Returns (tau, asymptotic_pvalue).
    Uses scipy.stats.kendalltau with method='asymptotic' for speed.

    The first return (tau) is the Kendall correlation coefficient
    in [-1, 1]; the second is the two-sided asymptotic p-value
    against the null of zero correlation.
    """

def _generate_ar1_surrogates(
    residuals: np.ndarray,
    n_surrogates: int = 1000,
    seed: int = 42,
) -> np.ndarray:
    """Generate AR(1)-bootstrap surrogates preserving variance and
    persistence of input residuals.

    Algorithm:
      1. Fit AR(1) to residuals: r_t = phi * r_{t-1} + eps_t
      2. Estimate phi_hat and sigma_eps_hat
      3. For each surrogate i in 0..n_surrogates-1:
         - Initialize x_0 ~ N(0, sigma_eps_hat / sqrt(1 - phi_hat^2))
         - Iterate x_t = phi_hat * x_{t-1} + eps_t,
           eps_t ~ N(0, sigma_eps_hat)
      4. Return shape (n_surrogates, len(residuals))

    Uses np.random.default_rng(seed) for reproducibility.
    """

def _kendall_tau_with_empirical_pvalue(
    indicator_series: np.ndarray,
    surrogate_indicators: np.ndarray,
) -> tuple[float, float]:
    """Compute Kendall tau on observed indicator series and the
    empirical p-value from the surrogate-derived null distribution.

    surrogate_indicators shape (n_surrogates, n_indicator_points).
    Each row is the SAME rolling indicator (e.g., rolling AR(1))
    computed on a different surrogate series.

    Returns (observed_tau, empirical_pvalue).
    Empirical p-value is fraction of surrogate taus >= observed.
    Lower p-value = more extreme observed tau = stronger CSD signal.
    """

# ─────────────────────────────────────────────────────
# Stage D — Composite scoring (1 function)
# ─────────────────────────────────────────────────────

def _composite_ews_score(
    indicator_taus: dict[str, float],
    indicator_pvalues: dict[str, float] | None,
    method: str = "equal_weight_zscore",
) -> tuple[float, str]:
    """Combine per-indicator Kendall taus into single EWS score.

    method='equal_weight_zscore':
      - For each indicator, compute z-score against asymptotic null
        (mean=0, var=2*(2T+5)/(9*T*(T-1)) for length-T series)
      - Average z-scores across indicators
      - Result is composite z-score in standardized units

    method='fisher_combined':
      - Requires indicator_pvalues to be non-None
      - Combine p-values via Fisher's method:
        chi2 = -2 * sum(log(p_i)), df = 2*k where k = num indicators
      - Convert chi2 to standardized z-score equivalent

    State classification thresholds (per Phase 1 design lock):
      composite_score < 1.0σ  → "normal"
      1.0σ ≤ score < 1.5σ     → "elevated"
      score ≥ 1.5σ            → "critical"

    Returns (composite_score, ews_state).
    """
```

### 7.2 `critical_slowing_down.py` — main wrapper

**Location:** `engine/techniques/critical_slowing_down.py` (NEW).

**Top-level docstring:**

```python
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
```

**Preset configuration:**

```python
_PRESET_CONFIG = {
    "Fast":     {"window_fraction": 0.5, "kendall_lookback_fraction": 0.3,
                 "n_surrogates": 200,  "default_compute_pvalues": True},
    "Balanced": {"window_fraction": 0.5, "kendall_lookback_fraction": 0.5,
                 "n_surrogates": 1000, "default_compute_pvalues": True},
    "Thorough": {"window_fraction": 0.5, "kendall_lookback_fraction": 0.5,
                 "n_surrogates": 5000, "default_compute_pvalues": True},
}

# State classification thresholds (composite z-score sigma)
_THRESHOLD_ELEVATED = 1.0
_THRESHOLD_CRITICAL = 1.5
```

**Wrapper run() signature and structure** — see §7.2.1 below for the full
sketch. Audit fields enumerated in §7.2.2.

#### 7.2.1 run() function structure

```python
def run(
    ctx: RunContext,
    progress_callback,
) -> dict:
    """Execute CSD early-warning detection on input series.

    Required ctx params:
      series: list of {"name": str, "values": list[float]}
        Single series for univariate analysis.
      time: list of timestamps matching series length.

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

    Returns:
      dict with status, output_table, audit_fields, fit_time_seconds.
    """
    t0 = time.time()

    # ---- Input validation
    series = ctx.get_series_by_name_or_index(0)
    y = np.asarray(series["values"], dtype=np.float64)
    T = len(y)

    preset = ctx.preset
    cfg = _PRESET_CONFIG[preset]

    # Resolve params
    detrending_method = ctx.params.get("detrending_method", "gaussian")
    rolling_window = int(ctx.params.get(
        "rolling_window", max(50, int(cfg["window_fraction"] * T))
    ))
    kendall_lookback = int(ctx.params.get(
        "kendall_lookback",
        max(30, int(cfg["kendall_lookback_fraction"] *
                    (T - rolling_window + 1)))
    ))
    compute_pvalues = bool(ctx.params.get(
        "compute_pvalues", cfg["default_compute_pvalues"]
    ))
    n_surrogates = int(ctx.params.get("n_surrogates", cfg["n_surrogates"]))
    composite_method = ctx.params.get(
        "composite_method", "equal_weight_zscore"
    )
    expose_rolling_series = bool(ctx.params.get(
        "expose_rolling_series", True
    ))

    # Insufficient-data guard (D-CSD-4 trigger fires)
    if T < rolling_window + kendall_lookback:
        return _build_insufficient_data_result(
            T, rolling_window, kendall_lookback, t0,
        )

    # ---- Stage A: Detrending
    progress_callback("Stage A: Detrending residuals", 10)
    detrending_bandwidth = None
    if detrending_method == "gaussian":
        detrending_bandwidth = float(ctx.params.get(
            "detrending_bandwidth", T / 10.0
        ))
        residuals = csd._gaussian_detrend(y, detrending_bandwidth)
    elif detrending_method == "first_diff":
        residuals = csd._first_difference_detrend(y)
    elif detrending_method == "linear":
        residuals = csd._linear_detrend(y)
    else:
        return _build_invalid_param_result(
            f"detrending_method={detrending_method!r} not in "
            f"{{gaussian, first_diff, linear}}", t0,
        )

    # Stationarity check on residuals
    is_stationary, adf_pvalue = csd._check_residual_stationarity(residuals)

    # ---- Stage B: Rolling indicators
    progress_callback("Stage B: Rolling indicators", 25)
    rolling_ar1 = csd._rolling_ar1(residuals, rolling_window)
    rolling_var = csd._rolling_variance(residuals, rolling_window)
    rolling_skew = csd._rolling_skewness(residuals, rolling_window)
    rolling_kurt = csd._rolling_kurtosis(residuals, rolling_window)
    rolling_return = csd._rolling_return_rate(rolling_ar1)
    rolling_density = csd._rolling_density_ratio(
        residuals, rolling_window
    )

    indicator_series = {
        "ar1": rolling_ar1,
        "variance": rolling_var,
        "skewness": rolling_skew,
        "kurtosis": rolling_kurt,
        "return_rate": rolling_return,
        "density_ratio": rolling_density,
    }

    # Restrict to Kendall lookback window (last `kendall_lookback` points)
    tail_indicators = {
        name: arr[-kendall_lookback:]
        for name, arr in indicator_series.items()
    }

    # ---- Stage C: Kendall tau + p-values
    progress_callback("Stage C: Kendall tau", 50)
    indicator_taus = {}
    indicator_pvalues = {}

    if compute_pvalues:
        progress_callback(
            f"Stage C: Computing {n_surrogates} AR(1) surrogates",
            55,
        )
        surrogates = csd._generate_ar1_surrogates(
            residuals, n_surrogates=n_surrogates, seed=ctx.seed,
        )
        # For each indicator, recompute on each surrogate to build
        # the empirical null distribution, then compute empirical
        # p-value as fraction of surrogate taus >= observed.
        surrogate_taus = _compute_surrogate_taus(
            surrogates, rolling_window, kendall_lookback,
            list(indicator_series.keys()), progress_callback,
        )
        for name, observed_arr in tail_indicators.items():
            tau, _ = csd._kendall_tau(observed_arr)
            null_dist = surrogate_taus[name]
            empirical_p = float(np.mean(null_dist >= tau))
            indicator_taus[name] = tau
            indicator_pvalues[name] = empirical_p
    else:
        for name, observed_arr in tail_indicators.items():
            tau, asymp_p = csd._kendall_tau(observed_arr)
            indicator_taus[name] = tau
            indicator_pvalues[name] = asymp_p

    # ---- Stage D: Composite scoring
    progress_callback("Stage D: Composite EWS score", 85)
    composite_score, ews_state = csd._composite_ews_score(
        indicator_taus,
        indicator_pvalues if composite_method == "fisher_combined" else None,
        method=composite_method,
    )

    # ---- Post-transition detection (tail residuals)
    tail_residuals = residuals[-kendall_lookback:]
    tail_skewness = float(scipy.stats.skew(tail_residuals, bias=False))
    tail_kurtosis = float(scipy.stats.kurtosis(
        tail_residuals, fisher=True, bias=False,
    ))
    post_transition_indicated = (
        abs(tail_skewness) > 1.0 or abs(tail_kurtosis) > 3.0
    )

    # ---- Build audit_fields (32 keys per §7.2.2)
    fit_time = round(time.time() - t0, 2)
    audit_fields = {
        # Composite (3)
        "ews_composite_score": float(composite_score),
        "ews_state": ews_state,
        "composite_method": composite_method,

        # Detrending (4)
        "detrending_method": detrending_method,
        "detrending_bandwidth": detrending_bandwidth,
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
        "tau_density_ratio_pvalue": float(indicator_pvalues["density_ratio"]),

        # Post-transition disambiguation (3)
        "tail_skewness": tail_skewness,
        "tail_kurtosis": tail_kurtosis,
        "post_transition_indicated": post_transition_indicated,

        # Methodology disclosure (5)
        "rolling_window": rolling_window,
        "kendall_lookback": kendall_lookback,
        "compute_pvalues": compute_pvalues,
        "n_surrogates": n_surrogates if compute_pvalues else None,
        "fit_time_seconds": fit_time,

        # Series length for D-CSD-4 (1)
        "series_length": T,
    }
    # Total: 28 scalar/string fields

    # Optional rolling-indicator series (6 fields, conditionally None)
    if expose_rolling_series:
        audit_fields["rolling_ar1_series"] = rolling_ar1.tolist()
        audit_fields["rolling_variance_series"] = rolling_var.tolist()
        audit_fields["rolling_skewness_series"] = rolling_skew.tolist()
        audit_fields["rolling_kurtosis_series"] = rolling_kurt.tolist()
        audit_fields["rolling_return_rate_series"] = rolling_return.tolist()
        audit_fields["rolling_density_ratio_series"] = rolling_density.tolist()
    else:
        for key in (
            "rolling_ar1_series", "rolling_variance_series",
            "rolling_skewness_series", "rolling_kurtosis_series",
            "rolling_return_rate_series", "rolling_density_ratio_series",
        ):
            audit_fields[key] = None
    # Total now: 28 + 6 = 34 audit_fields

    output_table = _build_output_table(audit_fields)

    return {
        "status": "success",
        "output_table": output_table,
        "audit_fields": audit_fields,
        "fit_time_seconds": fit_time,
    }
```

**Note on field count:** Phase 2 originally said "32 audit fields". Exact
count when rolling_series included = 34 (28 scalar + 6 series). Plus
`series_length` (which is in the 28 scalar count above). The T14 fixture
(§8.1) lists all 33 names that need None defaults — `fit_time_seconds`
is excluded from T14 since it's a runtime artifact, not a result field.
Code should treat the canonical count as 33 T14 fixture entries.

#### 7.2.2 Audit fields — full enumeration (33 T14 entries)

**Composite scoring block (3):**
- `ews_composite_score` — float
- `ews_state` — str ("normal" | "elevated" | "critical")
- `composite_method` — str ("equal_weight_zscore" | "fisher_combined")

**Detrending diagnostics block (4):**
- `detrending_method` — str ("gaussian" | "first_diff" | "linear")
- `detrending_bandwidth` — float | None (only set if method=gaussian)
- `detrending_residuals_stationary` — bool
- `detrending_residuals_adf_pvalue` — float

**Per-indicator Kendall taus block (6):**
- `tau_ar1` — float
- `tau_variance` — float
- `tau_skewness` — float
- `tau_kurtosis` — float
- `tau_return_rate` — float
- `tau_density_ratio` — float

**Per-indicator p-values block (6):**
- `tau_ar1_pvalue` — float
- `tau_variance_pvalue` — float
- `tau_skewness_pvalue` — float
- `tau_kurtosis_pvalue` — float
- `tau_return_rate_pvalue` — float
- `tau_density_ratio_pvalue` — float

**Post-transition disambiguation block (3):**
- `tail_skewness` — float
- `tail_kurtosis` — float
- `post_transition_indicated` — bool

**Methodology disclosure block (5):**
- `rolling_window` — int
- `kendall_lookback` — int
- `compute_pvalues` — bool
- `n_surrogates` — int | None (None when compute_pvalues=False)
- `series_length` — int

**Rolling-indicator series block (6, all gated by expose_rolling_series):**
- `rolling_ar1_series` — list[float] | None
- `rolling_variance_series` — list[float] | None
- `rolling_skewness_series` — list[float] | None
- `rolling_kurtosis_series` — list[float] | None
- `rolling_return_rate_series` — list[float] | None
- `rolling_density_ratio_series` — list[float] | None

**Grand total: 33 T14 fixture entries.**

### 7.3 `specs/critical_slowing_down.py` — interpretation contract

**Location:** `engine/interpretation/specs/critical_slowing_down.py` (NEW).

**Top-level docstring:**

```python
"""Interpretation contract for critical_slowing_down."""
```

#### 7.3.1 _tier1 builder

```python
def _tier1(results: dict) -> str:
    """Single-sentence summary of CSD detection result."""
    audit = results.get("audit_fields", {})
    state = audit.get("ews_state", "unknown")
    score = audit.get("ews_composite_score", 0.0)

    if state == "critical":
        return (
            f"Critical Slowing Down indicators are in CRITICAL "
            f"state (composite EWS score = {score:.2f}σ). The series "
            f"shows statistical signatures consistent with approaching "
            f"a phase transition."
        )
    elif state == "elevated":
        return (
            f"Critical Slowing Down indicators are ELEVATED "
            f"(composite EWS score = {score:.2f}σ). Some — but not all — "
            f"indicators show patterns consistent with rising instability."
        )
    elif state == "normal":
        return (
            f"Critical Slowing Down indicators are NORMAL "
            f"(composite EWS score = {score:.2f}σ). The series does not "
            f"show statistical signatures of an approaching transition."
        )
    else:
        return (
            "Critical Slowing Down analysis did not complete; see "
            "Tier 3 triggers for diagnostics."
        )
```

#### 7.3.2 _tier2 builder

```python
def _tier2(results: dict) -> str:
    """Multi-paragraph methodology disclosure + result narrative."""
    audit = results.get("audit_fields", {})
    status = results.get("status")

    # Insufficient-data short-circuit
    if status == "insufficient_data":
        return (
            "CSD analysis did not complete: input series too short "
            "for stable estimation. See Tier 3 trigger for "
            "specific data-length recommendations."
        )

    # Build estimation_clause
    estimation_clause = (
        f"CSD analysis applied {audit.get('detrending_method')} "
        f"detrending"
    )
    if audit.get("detrending_method") == "gaussian":
        estimation_clause += (
            f" (Gaussian kernel sigma = "
            f"{audit.get('detrending_bandwidth'):.2f} samples)"
        )
    estimation_clause += (
        f" with rolling window = {audit.get('rolling_window')} "
        f"and Kendall tau computed over a "
        f"{audit.get('kendall_lookback')}-point trailing window."
    )
    if audit.get("compute_pvalues"):
        estimation_clause += (
            f" Statistical significance was assessed via "
            f"{audit.get('n_surrogates')} AR(1)-bootstrap "
            f"surrogates."
        )
    else:
        estimation_clause += (
            " Statistical significance was assessed via "
            "asymptotic Kendall tau p-values (compute_pvalues=False)."
        )

    # Build per-indicator narrative
    indicators = ["ar1", "variance", "skewness", "kurtosis",
                  "return_rate", "density_ratio"]
    indicator_clauses = []
    for ind in indicators:
        tau = audit.get(f"tau_{ind}")
        pval = audit.get(f"tau_{ind}_pvalue")
        if tau is None or pval is None:
            continue
        sig = "significant" if pval < 0.05 else "not significant"
        sign = "rising" if tau > 0 else "falling"
        indicator_clauses.append(
            f"{ind.replace('_', ' ')}: tau = {tau:+.3f} "
            f"({sign}, p = {pval:.3f}, {sig})"
        )
    indicator_block = (
        "Per-indicator Kendall tau values: "
        + "; ".join(indicator_clauses) + "."
    )

    # Methodology caveats — first-class output (Phase 1 design lock)
    caveat_block = (
        "Methodological caveats: (1) CSD signals are descriptive "
        "of approaching transitions in dynamical-systems theory, "
        "but their predictive value out-of-sample on financial "
        "market data is contested in the empirical literature "
        "(see Diks-Hommes-Wang 2018, who find mixed results on "
        "real financial crises). (2) Detrending bandwidth choice "
        "materially affects results — a different bandwidth may "
        "yield different EWS conclusions. (3) Rising variance "
        "can also signal volatility clustering without any phase "
        "transition. (4) Kendall tau on rolling indicators has "
        "known limitations on trending or cyclical underlying "
        "series."
    )

    # Post-transition disambiguation
    post_transition_block = ""
    if audit.get("post_transition_indicated"):
        post_transition_block = (
            f" The tail residuals show high "
            f"skewness ({audit.get('tail_skewness'):+.2f}) or "
            f"kurtosis ({audit.get('tail_kurtosis'):+.2f}), which "
            "may indicate the series has already undergone a "
            "regime shift rather than approaching one — CSD "
            "indicators are most reliable in pre-transition "
            "regimes."
        )

    # Detrending residuals stationarity
    stationarity_block = ""
    if audit.get("detrending_residuals_stationary") is False:
        stationarity_block = (
            f" Detrending residuals failed the ADF stationarity "
            f"test (p = "
            f"{audit.get('detrending_residuals_adf_pvalue'):.3f}); "
            "CSD-pipeline assumptions require stationary residuals, "
            "so results should be interpreted with caution. "
            "Consider an alternative detrending method or a longer "
            "Gaussian kernel bandwidth."
        )

    return (
        estimation_clause + " " + indicator_block + " " +
        caveat_block + post_transition_block + stationarity_block
    )
```

#### 7.3.3 Trigger D-CSD-1: composite_elevated

```python
def _trigger_composite_elevated(results: dict) -> Optional[str]:
    """D-CSD-1 — composite EWS score is elevated or critical."""
    audit = results.get("audit_fields", {})
    state = audit.get("ews_state")
    score = audit.get("ews_composite_score")
    if state not in ("elevated", "critical"):
        return None
    if score is None:
        return None
    severity = "CRITICAL" if state == "critical" else "ELEVATED"
    return (
        f"Composite EWS score in {severity} regime "
        f"({score:+.2f}σ above null). The Kendall tau values "
        f"across rolling CSD indicators show a statistically "
        f"meaningful trend pattern consistent with approaching "
        f"a phase transition. This is a descriptive statistical "
        f"finding, not a forecast — interpret in conjunction "
        f"with the methodological caveats in Tier 2 disclosure. "
        f"For investment use, treat as one input among several "
        f"regime-detection signals rather than a standalone "
        f"trading signal."
    )
```

#### 7.3.4 Trigger D-CSD-2: consistent_tau_pattern

```python
def _trigger_consistent_tau_pattern(results: dict) -> Optional[str]:
    """D-CSD-2 — both AR(1) and variance show significant rising
    Kendall tau (the strictest historical predictor in Dakos work).
    """
    audit = results.get("audit_fields", {})
    tau_ar1 = audit.get("tau_ar1")
    tau_var = audit.get("tau_variance")
    p_ar1 = audit.get("tau_ar1_pvalue")
    p_var = audit.get("tau_variance_pvalue")
    if (tau_ar1 is None or tau_var is None or
        p_ar1 is None or p_var is None):
        return None
    if not (tau_ar1 > 0 and tau_var > 0
            and p_ar1 < 0.05 and p_var < 0.05):
        return None
    return (
        f"Both lag-1 autocorrelation (tau = {tau_ar1:+.3f}, "
        f"p = {p_ar1:.3f}) AND variance (tau = {tau_var:+.3f}, "
        f"p = {p_var:.3f}) show statistically significant rising "
        f"trends. This is the strictest CSD pattern in the "
        f"Dakos 2012 framework — both primary indicators "
        f"agreeing increases confidence that the underlying "
        f"system is approaching a transition rather than "
        f"experiencing transient volatility. Consistent rising "
        f"AR(1) reflects slower recovery from perturbations; "
        f"consistent rising variance reflects accumulating "
        f"shock impacts."
    )
```

#### 7.3.5 Trigger D-CSD-3: post_transition

```python
def _trigger_post_transition(results: dict) -> Optional[str]:
    """D-CSD-3 — post-transition disambiguation."""
    audit = results.get("audit_fields", {})
    if not audit.get("post_transition_indicated"):
        return None
    skew = audit.get("tail_skewness")
    kurt = audit.get("tail_kurtosis")
    if skew is None or kurt is None:
        return None
    return (
        f"Tail residuals show elevated skewness "
        f"({skew:+.2f}) or kurtosis ({kurt:+.2f}), suggesting "
        f"the series may have already undergone a regime shift "
        f"rather than approaching one. CSD indicators are "
        f"most reliable as early warnings in pre-transition "
        f"regimes; in post-transition regimes they may show "
        f"residual signals from the recent shift but lose "
        f"predictive interpretation. Consider examining the "
        f"underlying series visually for evidence of a recent "
        f"discontinuity or level shift."
    )
```

#### 7.3.6 Trigger D-CSD-4: insufficient_data

```python
def _trigger_insufficient_data(results: dict) -> Optional[str]:
    """D-CSD-4 — insufficient data for stable CSD estimation."""
    audit = results.get("audit_fields", {})
    status = results.get("status")
    if status != "insufficient_data":
        return None
    T = audit.get("series_length")
    return (
        f"Input series of length {T} is too short for stable "
        f"CSD estimation given the rolling window and Kendall "
        f"lookback parameters. CSD literature recommends at "
        f"least T = 500 for reliable indicator trends, with "
        f"longer series (T > 1000) preferred for surrogate-"
        f"based significance testing. Consider using a longer "
        f"data window or shortening the rolling-window parameter."
    )
```

#### 7.3.7 Trigger D-CSD-5: non_stationary_residuals

```python
def _trigger_non_stationary_residuals(results: dict) -> Optional[str]:
    """D-CSD-5 — detrending residuals failed stationarity check."""
    audit = results.get("audit_fields", {})
    if audit.get("detrending_residuals_stationary") is None:
        return None  # not computed (e.g., insufficient_data path)
    if audit.get("detrending_residuals_stationary"):
        return None  # was stationary, no trigger
    p = audit.get("detrending_residuals_adf_pvalue")
    method = audit.get("detrending_method")
    if p is None or method is None:
        return None
    return (
        f"Detrending residuals failed the ADF stationarity test "
        f"(p = {p:.3f}) using {method} detrending. The CSD "
        f"pipeline assumes stationary residuals; non-stationary "
        f"residuals produce spurious trends in the rolling "
        f"indicators that can mimic CSD without an actual "
        f"underlying transition. Recommended actions: (a) try "
        f"an alternative detrending method; (b) increase the "
        f"Gaussian kernel bandwidth if currently using gaussian; "
        f"(c) examine the input series for outliers or structural "
        f"breaks that may need preprocessing."
    )
```

#### 7.3.8 SPEC tuple

```python
SPEC = InterpretationSpec(
    technique_id="critical_slowing_down",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_composite_elevated,
        _trigger_consistent_tau_pattern,
        _trigger_post_transition,
        _trigger_insufficient_data,
        _trigger_non_stationary_residuals,
    ),
    mode_aware=False,
)
```

---

## 8. Phase 2 — Test invariants

### 8.1 T14 fixture additions (33 keys)

`engine/tests/test_interpretation_contract.py`, in `_MINIMAL_INPUT` dict —
add a new technique-block. All values are `None` (None-default pattern):

```python
        # ─────────────────────────────────────────────
        # critical_slowing_down (Stage 1 of deraAI deck)
        # ─────────────────────────────────────────────
        # Composite scoring (3)
        "ews_composite_score": None,
        "ews_state": None,
        "composite_method": None,
        # Detrending (4)
        "detrending_method": None,
        "detrending_bandwidth": None,
        "detrending_residuals_stationary": None,
        "detrending_residuals_adf_pvalue": None,
        # Per-indicator Kendall taus (6)
        "tau_ar1": None,
        "tau_variance": None,
        "tau_skewness": None,
        "tau_kurtosis": None,
        "tau_return_rate": None,
        "tau_density_ratio": None,
        # Per-indicator p-values (6)
        "tau_ar1_pvalue": None,
        "tau_variance_pvalue": None,
        "tau_skewness_pvalue": None,
        "tau_kurtosis_pvalue": None,
        "tau_return_rate_pvalue": None,
        "tau_density_ratio_pvalue": None,
        # Post-transition (3)
        "tail_skewness": None,
        "tail_kurtosis": None,
        "post_transition_indicated": None,
        # Methodology (5)
        "rolling_window": None,
        "kendall_lookback": None,
        "compute_pvalues": None,
        "n_surrogates": None,
        "series_length": None,
        # Rolling-indicator series (6)
        "rolling_ar1_series": None,
        "rolling_variance_series": None,
        "rolling_skewness_series": None,
        "rolling_kurtosis_series": None,
        "rolling_return_rate_series": None,
        "rolling_density_ratio_series": None,
```

**Total: 33 None-default keys.**

### 8.2 T15 allowlist additions

`_PROGRAMMATIC_TOKEN_ALLOWLIST` block — append a new section labeled per
existing convention (next available letter group; `(c17)` is recommended
based on Phase 1 sketch but Code should verify by inspecting existing
labels in the test file):

```python
        # (c17) critical_slowing_down — programmatic identifiers
        # appearing in spec text. Detrending method names, indicator
        # names, EWS state values, surrogate-method nouns.
        "first_diff", "compute_pvalues", "n_surrogates",
        "kendall_lookback", "rolling_window",
        "post_transition_indicated", "ews_composite_score",
        "ews_state", "tau_ar1", "tau_variance",
        "tau_skewness", "tau_kurtosis", "tau_return_rate",
        "tau_density_ratio", "rolling_ar1_series",
        "rolling_variance_series", "rolling_skewness_series",
        "rolling_kurtosis_series", "rolling_return_rate_series",
        "rolling_density_ratio_series",
        "fisher_combined", "equal_weight_zscore",
```

**Approximately 22 tokens.** Code should add any additional programmatic
tokens that surface during apply (e.g., if spec prose adds new field
references that contain underscores).

### 8.3 Expected outcome

All invariants continue passing at the count they currently pass at.
This is the Phase 4 gate. Code should run the full
`test_interpretation_contract.py` suite and report the count
(e.g., "96/96 PASS" — the actual current count needs to be verified at
apply time since I don't have visibility into the latest count).

---

## 9. Phase 2 — Catalog entry

`resources/catalog/techniques_catalog.json`, NEW entry. **Code must
inspect the existing catalog at apply time to determine:**

1. **Category value** — Phase 1 used "Regime Detection" as a placeholder.
   The actual TSL catalog may use a letter-group convention (A-M per Code's
   reference to MEMORY.md) or a category-string convention. Code should
   match whichever pattern existing entries use. If "Regime Detection"
   doesn't exist as an existing category, Code picks the closest match
   from existing categories (e.g., "Volatility Analysis" or "Structural
   Analysis") OR flags for human decision before commit.

2. **Required catalog schema fields** — beyond the params block below,
   Code should match existing entries' top-level structure (e.g., some
   entries may require `display_order`, `version`, `inputs_required`,
   `outputs_format` keys that the Phase 2 sketch didn't enumerate).

**Params block (locked):**

```json
{
  "technique_id": "critical_slowing_down",
  "display_name": "Critical Slowing Down (Early Warning)",
  "category": "<<CODE-DETERMINED — match existing catalog convention>>",
  "description": "Detects statistical signatures of approaching critical transitions (regime shifts, phase transitions, bifurcations) in time series via the canonical CSD pipeline: detrending, rolling indicators (AR(1), variance, skewness, kurtosis, return rate, density ratio), Kendall tau trend statistics, and composite EWS scoring. Based on Scheffer 2009, Dakos 2012, and Diks-Hommes-Wang 2018.",
  "params": [
    {
      "name": "detrending_method",
      "type": "string",
      "default": "gaussian",
      "options": ["gaussian", "first_diff", "linear"],
      "description": "Method for removing slowly-varying mean from input series. Gaussian kernel is the literature default. Detrending choice materially affects results."
    },
    {
      "name": "detrending_bandwidth",
      "type": "float",
      "default": null,
      "description": "Gaussian kernel sigma in samples. Default T/10 per Dakos convention. Ignored unless detrending_method='gaussian'."
    },
    {
      "name": "rolling_window",
      "type": "int",
      "default": null,
      "description": "Rolling-window size for indicator computation. Default per preset (Fast/Balanced/Thorough = 50% of T)."
    },
    {
      "name": "kendall_lookback",
      "type": "int",
      "default": null,
      "description": "Trailing-window size for Kendall tau. Default per preset (Fast=30%, Balanced/Thorough=50% of indicator-series length)."
    },
    {
      "name": "compute_pvalues",
      "type": "bool",
      "default": true,
      "description": "When True (default), computes empirical p-values for Kendall tau via AR(1)-bootstrap surrogates. Adds significant runtime: 200-5000 surrogates per preset. Set False for fast asymptotic p-values."
    },
    {
      "name": "n_surrogates",
      "type": "int",
      "default": null,
      "description": "Surrogate count for empirical p-values. Default per preset (Fast=200, Balanced=1000, Thorough=5000). Higher counts yield tighter p-value precision at proportional runtime cost."
    },
    {
      "name": "composite_method",
      "type": "string",
      "default": "equal_weight_zscore",
      "options": ["equal_weight_zscore", "fisher_combined"],
      "description": "Method for combining per-indicator Kendall taus into composite EWS score. equal_weight_zscore averages z-scored taus. fisher_combined uses Fisher's method on p-values; requires compute_pvalues=True."
    },
    {
      "name": "expose_rolling_series",
      "type": "bool",
      "default": true,
      "description": "When True, populates the six rolling-indicator time series in audit_fields for plotting. Set False to reduce payload size on long input series."
    }
  ]
}
```

---

## 10. Phase 2 — Markdown documentation

`resources/techniques_md/critical_slowing_down.md` — section outline. Code
writes the prose. Approximately 200 LOC.

```markdown
# Critical Slowing Down (Early Warning)

## Overview
[2-3 paragraphs: what CSD is, why it matters, where it comes from
(Scheffer 2009 origin), what TSL's wrapper does]

## The Four-Stage Pipeline
[Brief overview of Stage A-D structure]

## Indicator Definitions
[Formal definitions of each of the 6 rolling indicators with formulas:
AR(1), variance, skewness, kurtosis, return rate, density ratio]

## Detrending Methods
[Gaussian, first-diff, linear — when to use each, sensitivity discussion]

## Surrogate-Based P-Values
[AR(1) bootstrap explanation, why p-values matter, runtime considerations,
why True is the default]

## Composite EWS Score Interpretation
[State thresholds: normal (<1.0σ), elevated (1.0-1.5σ), critical (>1.5σ).
How equal_weight_zscore vs fisher_combined work.]

## Tier 3 Triggers
[D-CSD-1 through D-CSD-5 with firing conditions and example output]

## Methodological Caveats
[FIRST-CLASS SECTION, NOT BURIED IN A FOOTNOTE]
- Predictive vs descriptive value (citing Diks-Hommes-Wang 2018 mixed
  empirical results)
- Detrending bandwidth sensitivity
- Volatility-clustering confound
- Kendall tau limitations on cyclical/trending data

## References
- Scheffer, M. (2009). Critical Transitions in Nature and Society.
  Princeton Univ. Press.
- Dakos, V. et al. (2012). Methods for detecting early warnings of
  critical transitions in time series illustrated using simulated
  ecological data. PLoS ONE 7(7): e41010.
- Diks, C., Hommes, C., Wang, J. (2018). Critical slowing down as
  an early warning signal for financial crises? Empirical Economics.
- Bury, T.M. et al. (2023). ewstools: A Python package for early
  warning signals of bifurcations in time series data.

## Application Examples
[Synthetic logistic-map approaching bifurcation example with expected
output. Brief financial example with appropriate caveats — NO actual
trading-signal language.]
```

---

## 11. Phase 2 — Canonicals

`tools/validate_critical_slowing_down_canonicals.py` (NEW, ~280 LOC).

```python
"""Phase 5 canonical validation for critical_slowing_down.

Five cases:
  C1: Stationary white noise (no CSD) → ews_state="normal",
      D-CSD-1 does not fire.
  C2: Logistic-map approaching saddle-node bifurcation
      (canonical CSD test case, Dakos 2012) →
      ews_state in {"elevated", "critical"}, D-CSD-2 fires
      (consistent rising AR(1) + variance).
  C3: Already-shifted regime (post-transition) →
      D-CSD-3 fires (post_transition_indicated=True).
  C4: Insufficient data (T < min for stable estimation) →
      D-CSD-4 fires, status="insufficient_data".
  C5: Non-stationary detrending residuals →
      D-CSD-5 fires.

Run from project root:
    python tools/validate_critical_slowing_down_canonicals.py
"""

import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import critical_slowing_down as csd_mod


# ─────────────────────────────────────────────────────
# Synthetic data generators
# ─────────────────────────────────────────────────────

def _generate_white_noise(T=2000, seed=42):
    """Stationary white noise — no CSD, no transition."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(T)


def _generate_logistic_bifurcation(T=2000, seed=42):
    """Logistic map approaching saddle-node bifurcation per
    Dakos 2012 setup. Slowly-varying control parameter from
    r=2.5 to r=3.6, observation noise sigma=0.05, Gaussian.
    True bifurcation at r=3.0.
    """
    rng = np.random.default_rng(seed)
    r_values = np.linspace(2.5, 3.6, T)
    x = np.zeros(T)
    x[0] = 0.5
    for t in range(1, T):
        x[t] = r_values[t] * x[t-1] * (1 - x[t-1])
    return x + 0.05 * rng.standard_normal(T)


def _generate_already_shifted(T=2000, seed=42):
    """Mean-shifted regime: stable AR(1) before shift, large jump
    at midpoint, stable AR(1) after shift. Tail residuals show
    high skewness/kurtosis from the discontinuity; CSD shouldn't
    fire because there's no approaching transition."""
    rng = np.random.default_rng(seed)
    half = T // 2
    pre = 0.2 * np.cumsum(rng.standard_normal(half)) - 1.0
    post = 0.2 * np.cumsum(rng.standard_normal(T - half)) + 5.0
    return np.concatenate([pre, post])


def _generate_short_series(T=50, seed=42):
    """Too-short series for stable CSD."""
    rng = np.random.default_rng(seed)
    return rng.standard_normal(T)


def _generate_non_stationary(T=2000, seed=42):
    """Random walk: linear detrending won't fully remove drift;
    residuals fail ADF."""
    rng = np.random.default_rng(seed)
    return np.cumsum(rng.standard_normal(T))


# ─────────────────────────────────────────────────────
# Helper construction
# ─────────────────────────────────────────────────────

def _build_ctx(y, params=None, preset="Balanced"):
    return RunContext({
        "run_id": "test_csd",
        "technique_id": "critical_slowing_down",
        "preset": preset,
        "seed": 42,
        "frequency": "daily",
        "time": list(range(len(y))),
        "series": [{"name": "y", "values": y.tolist()}],
        "params": params or {},
    })


def _null_progress(*args, **kwargs):
    pass


# ─────────────────────────────────────────────────────
# Canonical cases
# ─────────────────────────────────────────────────────

def canonical_1_white_noise():
    """C1: White noise → no CSD."""
    print("\n=== C1: White noise (no CSD) ===")
    y = _generate_white_noise()
    ctx = _build_ctx(y)
    res = csd_mod.run(ctx, _null_progress)
    a = res["audit_fields"]
    assert a["ews_state"] == "normal", \
        f"Expected ews_state=normal, got {a['ews_state']}"
    assert abs(a["ews_composite_score"]) < 1.0, \
        f"Expected |composite| < 1.0, got {a['ews_composite_score']}"
    # D-CSD-1 should NOT fire
    triggers = (res.get("interpretation") or {}).get("tier3", [])
    assert not any("ELEVATED" in t or "CRITICAL" in t
                   for t in triggers), \
        "D-CSD-1 should not fire on white noise"
    print(f"  ✓ ews_state = {a['ews_state']}")
    print(f"  ✓ composite score = {a['ews_composite_score']:.3f}")
    print(f"  ✓ D-CSD-1 does not fire")
    print("C1: PASS")
    return True


def canonical_2_logistic_bifurcation():
    """C2: Logistic-map approaching bifurcation → CSD fires."""
    print("\n=== C2: Logistic map approaching bifurcation ===")
    y = _generate_logistic_bifurcation()
    ctx = _build_ctx(y)
    res = csd_mod.run(ctx, _null_progress)
    a = res["audit_fields"]
    assert a["ews_state"] in ("elevated", "critical"), \
        f"Expected elevated/critical, got {a['ews_state']}"
    assert a["ews_composite_score"] > 1.0, \
        f"Expected composite > 1.0, got {a['ews_composite_score']}"
    # D-CSD-2 (consistent tau pattern) should fire
    assert a["tau_ar1"] > 0, f"tau_ar1 = {a['tau_ar1']}"
    assert a["tau_variance"] > 0, f"tau_variance = {a['tau_variance']}"
    assert a["tau_ar1_pvalue"] < 0.05, \
        f"tau_ar1_pvalue = {a['tau_ar1_pvalue']}"
    assert a["tau_variance_pvalue"] < 0.05, \
        f"tau_variance_pvalue = {a['tau_variance_pvalue']}"
    print(f"  ✓ ews_state = {a['ews_state']}")
    print(f"  ✓ composite score = {a['ews_composite_score']:.3f}")
    print(f"  ✓ tau_ar1 = {a['tau_ar1']:+.3f} "
          f"(p = {a['tau_ar1_pvalue']:.3f})")
    print(f"  ✓ tau_variance = {a['tau_variance']:+.3f} "
          f"(p = {a['tau_variance_pvalue']:.3f})")
    print("C2: PASS")
    return True


def canonical_3_already_shifted():
    """C3: Mean-shifted series → post-transition disambiguation."""
    print("\n=== C3: Already-shifted regime ===")
    y = _generate_already_shifted()
    ctx = _build_ctx(y)
    res = csd_mod.run(ctx, _null_progress)
    a = res["audit_fields"]
    assert a["post_transition_indicated"] is True, \
        f"Expected post_transition_indicated=True"
    assert (abs(a["tail_skewness"]) > 1.0 or
            abs(a["tail_kurtosis"]) > 3.0), \
        f"Expected high tail skew or kurt"
    triggers = (res.get("interpretation") or {}).get("tier3", [])
    assert any("post-transition" in t.lower() or
               "regime shift" in t.lower()
               for t in triggers), \
        "D-CSD-3 should fire"
    print(f"  ✓ post_transition_indicated = True")
    print(f"  ✓ tail_skewness = {a['tail_skewness']:+.3f}")
    print(f"  ✓ tail_kurtosis = {a['tail_kurtosis']:+.3f}")
    print(f"  ✓ D-CSD-3 fires")
    print("C3: PASS")
    return True


def canonical_4_insufficient_data():
    """C4: T too short for stable estimation."""
    print("\n=== C4: Insufficient data ===")
    y = _generate_short_series(T=50)
    ctx = _build_ctx(y)
    res = csd_mod.run(ctx, _null_progress)
    assert res["status"] == "insufficient_data", \
        f"Expected status=insufficient_data, got {res['status']}"
    triggers = (res.get("interpretation") or {}).get("tier3", [])
    assert any("too short" in t.lower() or
               "insufficient" in t.lower()
               for t in triggers), \
        "D-CSD-4 should fire"
    print(f"  ✓ status = {res['status']}")
    print(f"  ✓ D-CSD-4 fires")
    print("C4: PASS")
    return True


def canonical_5_non_stationary_residuals():
    """C5: Random walk → detrending residuals fail ADF."""
    print("\n=== C5: Non-stationary residuals ===")
    y = _generate_non_stationary()
    # Use linear detrending, which doesn't fully remove RW drift
    ctx = _build_ctx(
        y, params={"detrending_method": "linear"},
    )
    res = csd_mod.run(ctx, _null_progress)
    a = res["audit_fields"]
    assert a["detrending_residuals_stationary"] is False, \
        f"Expected non-stationary, got {a['detrending_residuals_stationary']}"
    assert a["detrending_residuals_adf_pvalue"] >= 0.05, \
        f"Expected ADF p >= 0.05, got {a['detrending_residuals_adf_pvalue']}"
    triggers = (res.get("interpretation") or {}).get("tier3", [])
    assert any("ADF" in t or "stationarity" in t.lower()
               for t in triggers), \
        "D-CSD-5 should fire"
    print(f"  ✓ detrending_residuals_stationary = False")
    print(f"  ✓ ADF p-value = {a['detrending_residuals_adf_pvalue']:.3f}")
    print(f"  ✓ D-CSD-5 fires")
    print("C5: PASS")
    return True


# ─────────────────────────────────────────────────────
# Main runner
# ─────────────────────────────────────────────────────

def main():
    results = []
    for fn in (canonical_1_white_noise,
               canonical_2_logistic_bifurcation,
               canonical_3_already_shifted,
               canonical_4_insufficient_data,
               canonical_5_non_stationary_residuals):
        try:
            results.append(fn())
        except AssertionError as e:
            print(f"  FAIL: {e}")
            results.append(False)
    print(f"\n{'='*50}")
    print(f"Summary: {sum(results)}/{len(results)} PASS")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
```

---

## 12. Phase 2 — Phase 4.5 reference parity check

`tools/reference_parity/harness/checks/critical_slowing_down.py` (NEW,
~180 LOC).

**Critical alignment requirement:** TSL helpers and ewstools must use
the same rolling-window alignment convention. ewstools uses pandas
rolling with default right-aligned (the window ends at the indexed
position). TSL helpers per §7.1 also use right-aligned. Code MUST
verify ewstools alignment by inspecting the installed package's
source at apply time, BEFORE running parity. If ewstools uses a
different alignment, TSL must be adjusted to match (this is critical
for `abs_tol=1e-8` to be achievable).

```python
"""Phase 4.5 reference parity check for critical_slowing_down.

Validates that TSL's CSD pipeline matches Python `ewstools`
(Bury 2023) on the canonical logistic-map fixture.

Tolerance ladder (per Phase 3.1 workflow doc + Refinement A):
  Tier 1 (strict, bitwise) — ASSERTED:
    - Rolling AR(1) series: abs_tol=1e-8
    - Rolling variance series: abs_tol=1e-8
    - Kendall tau on AR(1): abs_tol=1e-8
    - Kendall tau on variance: abs_tol=1e-8
  Tier 2 (informational only for v1) — RECORDED, NOT ASSERTED:
    - Composite EWS score
    - Empirical p-values

Fixture: tools/reference_parity/fixtures/
         critical_slowing_down_logistic_map.npz
  - T=2000 logistic-map values approaching bifurcation
  - Control parameter r=2.5 to r=3.6
  - Observation noise sigma=0.05
  - Seed=42
  - canonical_seed metadata = 42
"""

from harness.base import ParityCheck
import numpy as np


class CriticalSlowingDownParityCheck(ParityCheck):
    fixture_id = "critical_slowing_down_logistic_map"
    technique_id = "critical_slowing_down"

    # Tier 1 strict tolerances
    ROLLING_AR1_ABS_TOL = 1e-8
    ROLLING_VAR_ABS_TOL = 1e-8
    TAU_ABS_TOL = 1e-8

    def run_tsl(self, fixture_data, canonical_seed):
        """Run TSL critical_slowing_down on fixture."""
        from techniques.base import RunContext
        from techniques import critical_slowing_down as csd_mod

        y = fixture_data["y"]
        ctx = RunContext({
            "run_id": "parity_csd",
            "technique_id": "critical_slowing_down",
            "preset": "Balanced",
            "seed": int(canonical_seed),
            "frequency": "daily",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "detrending_method": "gaussian",
                "detrending_bandwidth": len(y) / 10.0,
                "compute_pvalues": True,
                "n_surrogates": 1000,
                "rolling_window": int(0.5 * len(y)),
            },
        })
        return csd_mod.run(ctx, lambda *a, **k: None)

    def run_reference(self, fixture_data, canonical_seed):
        """Run ewstools on same fixture.

        IMPORTANT: ewstools API may differ across versions. Code MUST
        verify the actual installed-version API and adjust this code
        to match. The general pipeline is:
          1. Construct ewstools.TimeSeries (or equivalent)
          2. Detrend via Gaussian kernel with same bandwidth as TSL
          3. Compute rolling AR(1), variance with same window as TSL
          4. Compute Kendall tau on rolling indicators
          5. Extract numeric arrays for comparison
        """
        import ewstools
        y = fixture_data["y"]
        # NOTE TO CODE: Verify exact ewstools API at apply time. The
        # signature below is the v2.x API as of 2024; older or newer
        # versions may differ. Common functions:
        #   ewstools.TimeSeries(data=y) — wraps the series
        #   .detrend(method="Gaussian", bandwidth=...)
        #   .compute_var(rolling_window=...)
        #   .compute_auto(rolling_window=..., lag=1)
        #   .compute_ktau() — Kendall tau on accumulated indicators
        ts = ewstools.TimeSeries(data=y, transition=None)
        ts.detrend(method="Gaussian", bandwidth=len(y) / 10.0)
        rolling_window = int(0.5 * len(y))
        ts.compute_var(rolling_window=rolling_window)
        ts.compute_auto(rolling_window=rolling_window, lag=1)
        ts.compute_ktau()

        # Extract: ewstools stores in ts.ews (DataFrame) and
        # ts.ktau (dict-like). Field names: "ac1" for AR(1),
        # "variance" for variance.
        return {
            "rolling_ar1": ts.ews["ac1"].dropna().values,
            "rolling_variance": ts.ews["variance"].dropna().values,
            "tau_ar1": float(ts.ktau["ac1"]),
            "tau_variance": float(ts.ktau["variance"]),
        }

    def compare(self, tsl_result, ref_result):
        """Two-tier comparison."""
        tsl_audit = tsl_result["audit_fields"]

        # ─── Tier 1 (strict) ───
        tsl_ar1 = np.asarray(tsl_audit["rolling_ar1_series"])
        ref_ar1 = ref_result["rolling_ar1"]
        if len(tsl_ar1) != len(ref_ar1):
            return {
                "verdict": "FAIL",
                "tier": 1,
                "details": [
                    f"rolling_ar1 length mismatch: TSL={len(tsl_ar1)}, "
                    f"ref={len(ref_ar1)} — likely alignment convention "
                    f"difference. Check ewstools windowing vs TSL "
                    f"right-alignment."
                ],
            }
        ar1_diff = np.max(np.abs(tsl_ar1 - ref_ar1))

        tsl_var = np.asarray(tsl_audit["rolling_variance_series"])
        ref_var = ref_result["rolling_variance"]
        if len(tsl_var) != len(ref_var):
            return {
                "verdict": "FAIL",
                "tier": 1,
                "details": [
                    f"rolling_variance length mismatch: "
                    f"TSL={len(tsl_var)}, ref={len(ref_var)}"
                ],
            }
        var_diff = np.max(np.abs(tsl_var - ref_var))

        tau_ar1_diff = abs(tsl_audit["tau_ar1"] - ref_result["tau_ar1"])
        tau_var_diff = abs(
            tsl_audit["tau_variance"] - ref_result["tau_variance"]
        )

        tier1_failures = []
        if ar1_diff > self.ROLLING_AR1_ABS_TOL:
            tier1_failures.append(
                f"rolling_ar1 max abs diff = {ar1_diff:.2e} "
                f"> {self.ROLLING_AR1_ABS_TOL}"
            )
        if var_diff > self.ROLLING_VAR_ABS_TOL:
            tier1_failures.append(
                f"rolling_variance max abs diff = {var_diff:.2e} "
                f"> {self.ROLLING_VAR_ABS_TOL}"
            )
        if tau_ar1_diff > self.TAU_ABS_TOL:
            tier1_failures.append(
                f"tau_ar1 abs diff = {tau_ar1_diff:.2e} "
                f"> {self.TAU_ABS_TOL}"
            )
        if tau_var_diff > self.TAU_ABS_TOL:
            tier1_failures.append(
                f"tau_variance abs diff = {tau_var_diff:.2e} "
                f"> {self.TAU_ABS_TOL}"
            )

        if tier1_failures:
            return {
                "verdict": "FAIL",
                "tier": 1,
                "details": tier1_failures,
            }

        # Tier 2 informational (composite, p-values not asserted)
        return {
            "verdict": "PASS",
            "tier": 1,
            "details": (
                f"Tier 1 strict parity passed: AR(1) max diff "
                f"{ar1_diff:.2e}, variance max diff {var_diff:.2e}, "
                f"tau_ar1 diff {tau_ar1_diff:.2e}, tau_var diff "
                f"{tau_var_diff:.2e}. Tier 2 (composite + p-values) "
                f"recorded but not asserted per v1 Refinement A."
            ),
        }
```

**Fixture generation script** (one-off, run during Stage 3.7, NOT
committed to repo):

```python
# tools/reference_parity/fixtures/_generate_csd_logistic_map.py
import numpy as np
import hashlib

T = 2000
seed = 42
canonical_seed = 42  # metadata for harness

rng = np.random.default_rng(seed)
r_values = np.linspace(2.5, 3.6, T)
x = np.zeros(T)
x[0] = 0.5
for t in range(1, T):
    x[t] = r_values[t] * x[t-1] * (1 - x[t-1])
y = x + 0.05 * rng.standard_normal(T)

np.savez(
    "tools/reference_parity/fixtures/critical_slowing_down_logistic_map.npz",
    y=y,
    r_values=r_values,
    _canonical_seed=canonical_seed,
    _seed=seed,
    _bifurcation_r=3.0,
    _generator="logistic_map_approaching_saddle_node",
)

# Compute SHA256 of the npz file
with open(
    "tools/reference_parity/fixtures/critical_slowing_down_logistic_map.npz",
    "rb"
) as f:
    sha = hashlib.sha256(f.read()).hexdigest()

with open(
    "tools/reference_parity/fixtures/critical_slowing_down_logistic_map.sha256",
    "w"
) as f:
    f.write(sha + "\n")
```

---

## 13. Items Code must determine at apply time

These were not locked in Phase 1/Phase 2 because they require runtime
inspection of the actual environment / codebase. Code should resolve
each before commit, NOT invent.

| # | Item | Resolution |
|---|---|---|
| R1 | Technique category in catalog | Inspect `resources/catalog/techniques_catalog.json`. Match the category-naming convention used by adjacent wrappers (likely "Volatility Analysis" or "Structural Analysis" or whatever taxonomy exists). If "Regime Detection" doesn't exist, pick closest fit OR flag for human decision before commit. Do NOT invent a new category. |
| R2 | T15 allowlist letter group | Inspect existing labels `(c1)` through `(c16)` in `_PROGRAMMATIC_TOKEN_ALLOWLIST` — use next available letter (likely `(c17)`, but verify). |
| R3 | Current invariant test count | Run `pytest engine/tests/test_interpretation_contract.py -v` and capture pre-change count. Goal: post-change count equals pre-change count (no regression). Report actual numbers in commit message. |
| R4 | ewstools installed version + API | Run `pip show ewstools` and inspect the installed module's API. Verify: (a) `ewstools.TimeSeries` constructor signature, (b) `.detrend()` method signature, (c) `.compute_var()` and `.compute_auto()` signatures, (d) `.compute_ktau()` and the resulting `ts.ktau` field structure, (e) `ts.ews` DataFrame column names. If installed API differs from §12 sketch, update the parity check accordingly. |
| R5 | ewstools rolling-window alignment | Inspect ewstools source for rolling-window alignment (left/center/right). If different from TSL's right-aligned convention (§7.1), adjust either TSL helpers OR parity-check code to align. This is critical for `abs_tol=1e-8` to be achievable. |
| R6 | ewstools availability on machine | Run `pip install ewstools` if not already installed. If installation fails (Python version incompatibility, dependency conflicts), fall back to R `earlywarnings` via existing rscript_bridge infrastructure. Report which path was taken. |
| R7 | Catalog schema completeness | The §9 entry sketch shows params + description + display_name + category. Existing catalog entries may require additional top-level fields (display_order, version, etc.). Match existing-entry schema. |
| R8 | RunContext API specifics | The wrapper uses `ctx.get_series_by_name_or_index(0)`, `ctx.preset`, `ctx.seed`, `ctx.params`. Verify these match the actual RunContext API; adjust if conventions differ. |

---

## 14. Phase 3 — Nine-stage execution sequence

Per the original Phase 3 hand-off, but now with full specifications above.

### Stage 3.1 — `_csd_helpers.py`
Build the 14 helper functions per §7.1. Inline smoke tests in
`if __name__ == "__main__"` block validate each helper against
hand-computed expected values. ~250 LOC.

**Validation gate:** all smoke tests pass; no import errors.

### Stage 3.2 — `critical_slowing_down.py`
Build wrapper per §7.2 using validated helpers. Validate end-to-end
on synthetic logistic-map fixture; verify all 33 audit fields populate
(34 with rolling-series, depending on `expose_rolling_series`).
~470 LOC.

**Validation gate:** wrapper completes without error on synthetic
input; audit_fields dict has expected keys.

### Stage 3.3 — `specs/critical_slowing_down.py`
Build spec per §7.3 with all 5 trigger functions. Test interpretation
contract by feeding wrapper output through spec; verify all 5 triggers
fire correctly under their target conditions. ~360 LOC.

**Validation gate:** triggers fire under target conditions; null-guards
work for missing fields.

### Stage 3.4 — Test invariants
Update `engine/tests/test_interpretation_contract.py`:
- T14 fixture: 33 None-default keys per §8.1
- T15 allowlist: ~22 tokens per §8.2

**Validation gate (Phase 4):** full pytest run on
`test_interpretation_contract.py`; pass count matches pre-change count.
Report actual count in stage report.

### Stage 3.5 — Catalog + markdown
Build catalog entry per §9 (resolve R1 and R7 first). Build markdown
documentation per §10. ~260 LOC structured + prose.

**Validation gate:** JSON validates; markdown renders.

### Stage 3.6 — Canonicals
Build `tools/validate_critical_slowing_down_canonicals.py` per §11.
Run all 5 cases.

**Validation gate (Phase 5):** 5/5 PASS.

### Stage 3.7 — Phase 4.5 parity infrastructure
- (a) Generate fixture via one-off script (§12 fixture-generation).
  Place `.npz` and `.sha256` in `tools/reference_parity/fixtures/`.
- (b) Build harness check per §12. Resolve R4-R6 first (ewstools API
  inspection).
- (c) Run parity check.

**Validation gate (Phase 4.5):** Tier 1 strict comparison passes at
`abs_tol=1e-8`. If failed, root-cause and either adjust TSL alignment
to match ewstools or document why parity is informational-only.

### Stage 3.8 — Coverage map update
`docs/follow_up_check_coverage.md` adds critical_slowing_down to
mapped-wrappers table. +1 line.

### Stage 3.9 — Commit
Single commit per Template C. Commit message structure:

```
NEW technique: critical_slowing_down (Stage 1 of deraAI evaluation)

Implements the canonical CSD pipeline (Scheffer 2009, Dakos 2012):
detrending → rolling indicators → Kendall tau → composite EWS score.
First new technique addition since the verification initiative closed
at commit ee44ee4, exercising the Phase 3.1 workflow doc's full
pattern (Phase 1 design audit → Phase 2 implementation plan → Phase 3
apply → Phase 4 invariants → Phase 4.5 parity → Phase 5 canonicals).

Phase 4.5 parity check against ewstools (Bury 2023):
  Tier 1 strict (rolling AR(1), rolling variance, Kendall taus):
    PASS at abs_tol=1e-8 [or actual achieved tolerance]
  Tier 2 informational (composite score, p-values):
    Recorded, not asserted (Refinement A — v1).

Tier 3 triggers (5):
  D-CSD-1: composite_elevated
  D-CSD-2: consistent_tau_pattern
  D-CSD-3: post_transition
  D-CSD-4: insufficient_data
  D-CSD-5: non_stationary_residuals

Honest disclosure: methodology caveats are first-class output
(Tier 2 disclosure block). Predictive value out-of-sample on
financial data is contested in the empirical literature.

Files: 11 new/modified, [actual] LOC.
Canonicals: 5/5 PASS.
Phase 4.5: PASS [Tier 1 strict].
Invariants: [actual]/[actual] PASS (no regression).
```

Push to origin/master.

---

## 15. Stage report requirements

After Phase 3 completes (or after any failed gate), Code reports:

1. Pre-commit HEAD SHA
2. New HEAD SHA (short)
3. Total commits on origin/master after push
4. All gate statuses (Stages 3.1-3.7)
5. R1-R8 resolutions (what was determined for each)
6. Any Stage 3.x divergences from this plan
7. Actual LOC delta (insertions/deletions)
8. Phase 4 gate: invariant test count (before / after)
9. Phase 4.5 gate: Tier 1 max diff values for each compared metric
10. Phase 5 gate: canonical pass count

---

## 16. End-of-handoff

This document is self-contained. Code should:

1. Read this document end-to-end before starting Stage 3.1.
2. Resolve R1-R8 at the appropriate stage (R4-R6 before Stage 3.7;
   R1 before Stage 3.5; R2-R3, R7-R8 inline as needed).
3. Execute the 9-stage sequence per §14.
4. Report per §15 at completion.

If a gate fails or a specification ambiguity surfaces that this document
does not resolve, STOP and request clarification. Do NOT invent design
decisions to keep moving.

— End of handoff document —
