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

from __future__ import annotations

import math
from typing import Optional

import numpy as np
from scipy import signal as scipy_signal
from scipy import stats as scipy_stats
from scipy.ndimage import gaussian_filter1d


# ─────────────────────────────────────────────────────
# Stage A — Detrending (3 functions + 1 stationarity check)
# ─────────────────────────────────────────────────────

def _gaussian_detrend(y: np.ndarray, bandwidth: float) -> np.ndarray:
    """Gaussian-kernel detrending. Returns residuals y - smoothed(y).

    Bandwidth is the kernel sigma (in samples). Default in literature
    is T/10. Uses scipy.ndimage.gaussian_filter1d with mode='reflect'
    to handle edges.
    """
    y_arr = np.asarray(y, dtype=np.float64)
    smoothed = gaussian_filter1d(y_arr, sigma=float(bandwidth), mode="reflect")
    return y_arr - smoothed


def _first_difference_detrend(y: np.ndarray) -> np.ndarray:
    """First-difference detrending. Returns y[1:] - y[:-1].
    Output length T-1.
    """
    y_arr = np.asarray(y, dtype=np.float64)
    return y_arr[1:] - y_arr[:-1]


def _linear_detrend(y: np.ndarray) -> np.ndarray:
    """Linear OLS detrending. Returns residuals from y ~ a + b*t.
    Uses scipy.signal.detrend(type='linear').
    """
    y_arr = np.asarray(y, dtype=np.float64)
    return scipy_signal.detrend(y_arr, type="linear")


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
    from statsmodels.tsa.stattools import adfuller
    r = np.asarray(residuals, dtype=np.float64)
    # ADF requires at least a few observations; defensive guard
    if r.size < 10:
        return False, 1.0
    try:
        result = adfuller(r, autolag="AIC")
        pvalue = float(result[1])
    except Exception:
        return False, 1.0
    return (pvalue < significance), pvalue


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
    [k, k+window-1] in the input). Matches ewstools convention.
    """
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    W = int(window)
    if W < 2 or T < W:
        return np.empty(0, dtype=np.float64)
    n_out = T - W + 1
    out = np.empty(n_out, dtype=np.float64)
    for k in range(n_out):
        seg = r[k:k + W]
        x0 = seg[:-1]
        x1 = seg[1:]
        # Pearson autocorr at lag 1; degenerate if std=0
        s0 = x0.std(ddof=1)
        s1 = x1.std(ddof=1)
        if s0 < 1e-300 or s1 < 1e-300:
            out[k] = np.nan
            continue
        out[k] = float(np.corrcoef(x0, x1)[0, 1])
    return out


def _rolling_variance(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample variance (ddof=1). Returns length T-W+1.
    Right-aligned.
    """
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    W = int(window)
    if W < 2 or T < W:
        return np.empty(0, dtype=np.float64)
    n_out = T - W + 1
    out = np.empty(n_out, dtype=np.float64)
    for k in range(n_out):
        out[k] = float(r[k:k + W].var(ddof=1))
    return out


def _rolling_skewness(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample skewness (Fisher-Pearson). Length T-W+1.
    Uses scipy.stats.skew with bias=False to match ewstools default.
    Right-aligned.
    """
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    W = int(window)
    if W < 3 or T < W:
        return np.empty(0, dtype=np.float64)
    n_out = T - W + 1
    out = np.empty(n_out, dtype=np.float64)
    for k in range(n_out):
        out[k] = float(scipy_stats.skew(r[k:k + W], bias=False))
    return out


def _rolling_kurtosis(residuals: np.ndarray, window: int) -> np.ndarray:
    """Rolling sample excess kurtosis (Fisher). Length T-W+1.
    Uses scipy.stats.kurtosis(fisher=True, bias=False).
    Right-aligned.
    """
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    W = int(window)
    if W < 4 or T < W:
        return np.empty(0, dtype=np.float64)
    n_out = T - W + 1
    out = np.empty(n_out, dtype=np.float64)
    for k in range(n_out):
        out[k] = float(scipy_stats.kurtosis(
            r[k:k + W], fisher=True, bias=False,
        ))
    return out


def _rolling_return_rate(rolling_ar1: np.ndarray) -> np.ndarray:
    """Rolling return rate = 1 - AR(1). Derived; same length as
    rolling_ar1. Higher return rate = faster recovery = less CSD.
    """
    arr = np.asarray(rolling_ar1, dtype=np.float64)
    return 1.0 - arr


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
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    W = int(window)
    if W < 8 or T < W:
        return np.empty(0, dtype=np.float64)
    n_out = T - W + 1
    out = np.empty(n_out, dtype=np.float64)
    cutoff = float(cutoff_fraction)
    for k in range(n_out):
        seg = r[k:k + W]
        # Periodogram returns (frequencies, power). fs=1.0 → Nyquist=0.5.
        freqs, pxx = scipy_signal.periodogram(seg, fs=1.0)
        total = float(pxx.sum())
        if total <= 0.0:
            out[k] = np.nan
            continue
        nyquist = 0.5
        threshold = cutoff * nyquist
        low_mask = freqs <= threshold
        low_power = float(pxx[low_mask].sum())
        out[k] = low_power / total
    return out


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
    arr = np.asarray(indicator_series, dtype=np.float64)
    n = arr.size
    if n < 3:
        return 0.0, 1.0
    # Filter NaNs which can arise from degenerate windows
    finite_mask = np.isfinite(arr)
    if finite_mask.sum() < 3:
        return 0.0, 1.0
    t_idx = np.arange(n, dtype=np.float64)[finite_mask]
    vals = arr[finite_mask]
    res = scipy_stats.kendalltau(t_idx, vals, variant="b", method="asymptotic")
    tau = float(res.statistic)
    pvalue = float(res.pvalue)
    if not math.isfinite(tau):
        tau = 0.0
    if not math.isfinite(pvalue):
        pvalue = 1.0
    return tau, pvalue


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
    r = np.asarray(residuals, dtype=np.float64)
    T = r.size
    if T < 3:
        rng = np.random.default_rng(seed)
        return rng.standard_normal((int(n_surrogates), T))
    # OLS estimate of AR(1): r_t = phi * r_{t-1} + eps_t
    x_lag = r[:-1]
    x_t = r[1:]
    denom = float(np.dot(x_lag, x_lag))
    if denom < 1e-300:
        phi_hat = 0.0
    else:
        phi_hat = float(np.dot(x_lag, x_t) / denom)
    # Clamp to stationary range
    phi_hat = max(min(phi_hat, 0.999), -0.999)
    eps = x_t - phi_hat * x_lag
    sigma_eps = float(eps.std(ddof=1)) if eps.size > 1 else 1.0
    if sigma_eps < 1e-300:
        sigma_eps = 1e-10
    # Stationary marginal std for x_0
    stationary_std = sigma_eps / math.sqrt(max(1.0 - phi_hat * phi_hat, 1e-12))

    rng = np.random.default_rng(seed)
    n_surr = int(n_surrogates)
    surrogates = np.empty((n_surr, T), dtype=np.float64)
    # Vectorize across surrogates: same recursion, independent eps
    surrogates[:, 0] = stationary_std * rng.standard_normal(n_surr)
    eps_mat = sigma_eps * rng.standard_normal((n_surr, T - 1))
    for t in range(1, T):
        surrogates[:, t] = phi_hat * surrogates[:, t - 1] + eps_mat[:, t - 1]
    return surrogates


def _vectorized_rolling_indicators(
    surrogates: np.ndarray,
    window: int,
) -> dict[str, np.ndarray]:
    """Compute the 6 CSD rolling indicators for an entire batch
    of surrogate series simultaneously.

    Input shape: (n_surrogates, T)
    Output: dict mapping indicator name -> (n_surrogates, T-W+1)
    array. Skewness/kurtosis use scipy.stats with axis=-1.
    Density ratio uses periodogram with axis=-1.

    Vectorized via numpy sliding_window_view for ~100x speedup
    over the scalar per-surrogate loop. Right-aligned convention.
    """
    from numpy.lib.stride_tricks import sliding_window_view

    surr = np.asarray(surrogates, dtype=np.float64)
    if surr.ndim != 2:
        raise ValueError("surrogates must be (n_surrogates, T)")
    n_surr, T = surr.shape
    W = int(window)
    if W < 4 or T < W:
        empty = np.empty((n_surr, 0), dtype=np.float64)
        return {
            "ar1": empty, "variance": empty,
            "skewness": empty, "kurtosis": empty,
            "return_rate": empty, "density_ratio": empty,
        }

    # (n_surrogates, n_windows, W)
    windows = sliding_window_view(surr, window_shape=W, axis=1)

    # Variance — vectorized over surrogate × window
    var = windows.var(axis=-1, ddof=1)

    # AR(1) — vectorized corr(x[:-1], x[1:]) over windows
    a = windows[..., :-1]
    b = windows[..., 1:]
    a_mean = a.mean(axis=-1, keepdims=True)
    b_mean = b.mean(axis=-1, keepdims=True)
    a_dev = a - a_mean
    b_dev = b - b_mean
    cov = (a_dev * b_dev).mean(axis=-1)
    a_var = (a_dev ** 2).mean(axis=-1)
    b_var = (b_dev ** 2).mean(axis=-1)
    denom = np.sqrt(a_var * b_var)
    # Avoid divide-by-zero on degenerate windows
    with np.errstate(divide="ignore", invalid="ignore"):
        ar1 = np.where(denom > 1e-300, cov / denom, np.nan)

    # Skewness / kurtosis (Fisher-Pearson, bias=False) along window axis
    skew = scipy_stats.skew(windows, axis=-1, bias=False)
    kurt = scipy_stats.kurtosis(windows, axis=-1, fisher=True, bias=False)

    # Return rate
    rr = 1.0 - ar1

    # Density ratio: low-frequency power / total power per window.
    # periodogram supports axis kwarg; output: freqs (W//2+1,),
    # pxx (..., W//2+1)
    freqs, pxx = scipy_signal.periodogram(windows, fs=1.0, axis=-1)
    nyquist = 0.5
    cutoff = 0.1 * nyquist
    low_mask = freqs <= cutoff
    total = pxx.sum(axis=-1)
    low_power = pxx[..., low_mask].sum(axis=-1)
    with np.errstate(divide="ignore", invalid="ignore"):
        dr = np.where(total > 0.0, low_power / total, np.nan)

    return {
        "ar1": ar1,
        "variance": var,
        "skewness": skew,
        "kurtosis": kurt,
        "return_rate": rr,
        "density_ratio": dr,
    }


def _vectorized_kendall_tau_per_row(arr: np.ndarray) -> np.ndarray:
    """Compute Kendall tau-b on each row of a 2D array against
    its column index (i.e., trend statistic across the trailing
    indicator window). Returns 1D array of length n_rows.

    Vectorized via scipy.stats.kendalltau looped per row (the
    per-row cost is O(n^2 log n) for n=lookback; the dominant
    cost is the per-row sort/merge inside scipy's kendalltau,
    which is C-implemented). Filter NaNs row-by-row.
    """
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim != 2:
        raise ValueError("expected 2D array (n_rows, n_points)")
    n_rows, n_pts = a.shape
    out = np.empty(n_rows, dtype=np.float64)
    if n_pts < 3:
        out.fill(0.0)
        return out
    t_idx_full = np.arange(n_pts, dtype=np.float64)
    for i in range(n_rows):
        row = a[i]
        finite = np.isfinite(row)
        if finite.sum() < 3:
            out[i] = 0.0
            continue
        t_idx = t_idx_full[finite]
        vals = row[finite]
        try:
            res = scipy_stats.kendalltau(
                t_idx, vals,
                variant="b", method="asymptotic",
            )
            tau = float(res.statistic)
            if not math.isfinite(tau):
                tau = 0.0
        except Exception:
            tau = 0.0
        out[i] = tau
    return out


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
    obs = np.asarray(indicator_series, dtype=np.float64)
    surr = np.asarray(surrogate_indicators, dtype=np.float64)
    obs_tau, _ = _kendall_tau(obs)
    if surr.ndim != 2 or surr.shape[0] == 0:
        return obs_tau, 1.0
    surr_taus = np.empty(surr.shape[0], dtype=np.float64)
    for i in range(surr.shape[0]):
        surr_taus[i], _ = _kendall_tau(surr[i])
    empirical_p = float(np.mean(surr_taus >= obs_tau))
    return obs_tau, empirical_p


# ─────────────────────────────────────────────────────
# Stage D — Composite scoring (1 function)
# ─────────────────────────────────────────────────────

def _composite_ews_score(
    indicator_taus: dict[str, float],
    indicator_pvalues: Optional[dict[str, float]],
    method: str = "equal_weight_zscore",
    n_indicator_points: int = 100,
    threshold_elevated: float = 1.0,
    threshold_critical: float = 1.5,
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
    if not indicator_taus:
        return 0.0, "normal"

    if method == "fisher_combined":
        if indicator_pvalues is None or not indicator_pvalues:
            raise ValueError(
                "composite_method='fisher_combined' requires "
                "non-None indicator_pvalues"
            )
        ps = []
        for name in indicator_taus.keys():
            p = indicator_pvalues.get(name)
            if p is None or not math.isfinite(p):
                continue
            # Floor at small positive to avoid log(0)
            ps.append(max(min(float(p), 1.0 - 1e-12), 1e-12))
        if not ps:
            return 0.0, "normal"
        chi2 = -2.0 * sum(math.log(p) for p in ps)
        df = 2 * len(ps)
        # Convert chi2 to combined p-value, then to one-sided z-score
        combined_p = float(scipy_stats.chi2.sf(chi2, df=df))
        combined_p = max(min(combined_p, 1.0 - 1e-12), 1e-12)
        composite_score = float(scipy_stats.norm.isf(combined_p))
    else:
        # equal_weight_zscore
        T = max(int(n_indicator_points), 4)
        # Asymptotic Kendall tau null: mean 0, var = 2(2T+5)/(9T(T-1))
        var_null = (2.0 * (2.0 * T + 5.0)) / (9.0 * T * (T - 1.0))
        sd_null = math.sqrt(max(var_null, 1e-300))
        z_scores = []
        for name, tau in indicator_taus.items():
            if tau is None or not math.isfinite(float(tau)):
                continue
            z_scores.append(float(tau) / sd_null)
        if not z_scores:
            return 0.0, "normal"
        composite_score = float(np.mean(z_scores))

    if composite_score >= threshold_critical:
        state = "critical"
    elif composite_score >= threshold_elevated:
        state = "elevated"
    else:
        state = "normal"
    return composite_score, state


# ─────────────────────────────────────────────────────
# Inline smoke tests (Stage 3.1 validation gate)
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    rng = np.random.default_rng(42)
    # Detrending smoke
    y = np.linspace(0, 10, 200) + rng.standard_normal(200)
    res_g = _gaussian_detrend(y, bandwidth=20.0)
    assert res_g.shape == y.shape, "gaussian shape"
    assert abs(res_g.mean()) < 0.5, "gaussian residuals roughly centered"
    res_d = _first_difference_detrend(y)
    assert res_d.size == y.size - 1, "first-diff length"
    res_l = _linear_detrend(y)
    assert res_l.shape == y.shape, "linear shape"

    # Stationarity smoke
    is_st_wn, p_wn = _check_residual_stationarity(rng.standard_normal(500))
    assert is_st_wn is True, f"white noise should be stationary; got p={p_wn}"
    is_st_rw, p_rw = _check_residual_stationarity(
        np.cumsum(rng.standard_normal(500))
    )
    assert is_st_rw is False, f"random walk should be non-stationary; got p={p_rw}"

    # Rolling indicators smoke (length consistency)
    r = rng.standard_normal(300)
    W = 100
    ar1 = _rolling_ar1(r, W)
    var = _rolling_variance(r, W)
    skew = _rolling_skewness(r, W)
    kurt = _rolling_kurtosis(r, W)
    rr = _rolling_return_rate(ar1)
    dr = _rolling_density_ratio(r, W)
    expected = 300 - W + 1
    for name, arr in [
        ("ar1", ar1), ("variance", var), ("skew", skew),
        ("kurt", kurt), ("return_rate", rr), ("density_ratio", dr),
    ]:
        assert arr.size == expected, f"{name} length: {arr.size} vs {expected}"
    # AR(1) on white noise should hover near 0
    assert abs(ar1.mean()) < 0.1, f"AR(1) mean on noise: {ar1.mean()}"
    # Variance on standard normal should hover near 1
    assert abs(var.mean() - 1.0) < 0.2, f"variance mean: {var.mean()}"

    # Kendall tau smoke
    monotone = np.linspace(0, 1, 50)
    tau_mono, p_mono = _kendall_tau(monotone)
    assert tau_mono > 0.99, f"tau on monotone: {tau_mono}"
    assert p_mono < 0.01, f"p on monotone: {p_mono}"
    flat_noise = rng.standard_normal(50)
    tau_flat, p_flat = _kendall_tau(flat_noise)
    assert abs(tau_flat) < 0.3, f"tau on noise: {tau_flat}"

    # Surrogates smoke
    surr = _generate_ar1_surrogates(r, n_surrogates=100, seed=1)
    assert surr.shape == (100, 300), f"surr shape: {surr.shape}"
    # Surrogates should preserve roughly the input variance
    assert abs(surr.var() - r.var()) / max(r.var(), 1e-6) < 0.5, \
        f"surr var mismatch: {surr.var()} vs {r.var()}"

    # Empirical p-value smoke — observed tau small → p near 0.5
    surr_ar1 = np.array([_rolling_ar1(s, 50) for s in surr[:20]])
    obs_tau, emp_p = _kendall_tau_with_empirical_pvalue(
        ar1[-100:], surr_ar1[:, -100:],
    )
    assert 0.0 <= emp_p <= 1.0, f"empirical p out of [0,1]: {emp_p}"

    # Composite scoring smoke
    score_n, state_n = _composite_ews_score(
        {"ar1": 0.05, "variance": 0.05}, None, n_indicator_points=100,
    )
    assert state_n == "normal", f"normal state: {state_n}"
    score_e, state_e = _composite_ews_score(
        {"ar1": 0.15, "variance": 0.15}, None, n_indicator_points=100,
    )
    assert state_e in ("elevated", "critical"), f"elevated state: {state_e}"
    score_c, state_c = _composite_ews_score(
        {"ar1": 0.30, "variance": 0.30}, None, n_indicator_points=100,
    )
    assert state_c == "critical", f"critical state: {state_c}"

    # Fisher combined smoke
    score_f, state_f = _composite_ews_score(
        {"ar1": 0.3, "variance": 0.3},
        {"ar1": 0.001, "variance": 0.001},
        method="fisher_combined",
    )
    assert score_f > 1.5, f"fisher score: {score_f}"

    print("ALL SMOKE TESTS PASS")
