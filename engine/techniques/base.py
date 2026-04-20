"""
Base classes and helpers for Time Series Lab technique modules.

Every technique receives a RunContext and returns a dict matching the RunResponse schema.
"""

import datetime
import numpy as np


# Map human-readable frequency labels emitted by the C# TimeIndexDetector
# to the pandas-style short codes that every technique's _infer_period
# already understands. Unknown values pass through unchanged so that callers
# can still supply raw short codes like "M", "MS", "Q", "QS", "D", etc.
_FREQUENCY_ALIASES = {
    "calendardaily": "D",
    "businessdaily": "B",
    "daily": "D",
    "weekly": "W",
    "monthly": "M",
    "quarterly": "Q",
    "annual": "Y",
    "annually": "Y",
    "yearly": "Y",
}


def _normalize_frequency(raw: str) -> str:
    """Translate detector labels to pandas-style frequency codes."""
    if not raw:
        return ""
    key = str(raw).strip().lower()
    return _FREQUENCY_ALIASES.get(key, str(raw).strip())


# ── Identification convention helpers ───────────────────────────────
# Many time-series techniques produce solutions that are only
# identified up to sign, scale, or permutation. These helpers apply
# the standard deterministic conventions so the user sees consistent
# output across runs, numpy versions, and LAPACK implementations.


def flip_sign_svd(U, Vt=None, S=None):
    """Apply sklearn-style ``svd_flip`` sign normalization.

    Ensures each column of ``U`` has its largest-absolute-value entry
    positive. If ``Vt`` is supplied, the corresponding rows are flipped
    in lockstep so ``U @ diag(S) @ Vt`` is preserved exactly. Returns
    ``(U, Vt)`` (or just ``U`` when no ``Vt``).

    Use this anywhere eigenvectors / singular vectors get reported to
    the user: PCA loadings, SSA basis, DFM factors, EMD IMFs, wavelet
    detail bands. Without this step, the same input can yield visually
    flipped charts across runs or library versions.
    """
    U = np.asarray(U)
    if U.ndim == 1:
        U = U.reshape(-1, 1)
    abs_argmax = np.argmax(np.abs(U), axis=0)
    signs = np.sign(U[abs_argmax, np.arange(U.shape[1])])
    signs[signs == 0] = 1.0
    U_flipped = U * signs
    if Vt is not None:
        Vt = np.asarray(Vt)
        if Vt.ndim == 1:
            Vt = Vt.reshape(1, -1)
        Vt_flipped = Vt * signs[:, None]
        return U_flipped, Vt_flipped
    return U_flipped


def flip_sign_vector(v):
    """Sign-normalize a 1-D vector so its largest-absolute entry is positive.

    Convenience for single-component sign fixes (e.g., one IMF from EMD).
    """
    v = np.asarray(v)
    if v.size == 0:
        return v
    i = int(np.argmax(np.abs(v)))
    sign = 1.0 if v[i] >= 0 else -1.0
    return v * sign


def build_forecast_time_axis(last_time_label, frequency: str, horizon: int):
    """Extend an input DatetimeIndex by ``horizon`` steps at the detected
    frequency, returning a list of ISO date strings (``"YYYY-MM-DD"``).

    Shared helper used by wrappers that emit multi-step forecasts and
    need the forecast-row "Time" column to extend the input series'
    date axis rather than emit integer step numbers. Falls back to
    ``t+1..t+h`` when the last label can't be parsed as a date or the
    frequency is unknown.

    Originally ported from the retired kalman_filter_model.py during
    the Structural TS consolidation; now lives in base.py as the
    canonical implementation for every wrapper that produces a
    Forecast table on a date-indexed input.

    Parameters
    ----------
    last_time_label
        The last entry of the wrapper's input time axis. Any type
        that :func:`pandas.to_datetime` accepts.
    frequency : str
        One of "A"/"Annual"/"Y", "Q"/"Quarterly"/"QS", "M"/"Monthly"/"MS",
        "W"/"Weekly", "D"/"Daily"/"B", "H"/"Hourly" (case-insensitive).
        Other strings fall back to the ``t+1..t+h`` form.
    horizon : int
        Number of forecast steps.

    Returns
    -------
    list[str]
        Length-``horizon`` list of date strings extending the axis.
    """
    import warnings as _warnings
    import pandas as pd
    freq_map_modern = {
        "A": "YE-DEC", "ANNUAL": "YE-DEC", "Y": "YE-DEC",
        "Q": "QE-DEC", "QUARTERLY": "QE-DEC", "QS": "QS",
        "M": "ME", "MONTHLY": "ME", "MS": "MS",
        "W": "W", "WEEKLY": "W",
        "D": "D", "DAILY": "D", "B": "B",
        "H": "h", "HOURLY": "h",
    }
    freq_map_legacy = {
        "A": "A-DEC", "ANNUAL": "A-DEC", "Y": "A-DEC",
        "Q": "Q-DEC", "QUARTERLY": "Q-DEC", "QS": "QS",
        "M": "M", "MONTHLY": "M", "MS": "MS",
        "W": "W", "WEEKLY": "W",
        "D": "D", "DAILY": "D", "B": "B",
        "H": "H", "HOURLY": "H",
    }
    key = (frequency or "").strip().upper()
    modern = freq_map_modern.get(key)
    legacy = freq_map_legacy.get(key)
    if modern is None and legacy is None:
        return [f"t+{i + 1}" for i in range(horizon)]
    try:
        last_ts = pd.to_datetime(str(last_time_label))
    except Exception:
        return [f"t+{i + 1}" for i in range(horizon)]
    for code in (modern, legacy):
        if code is None:
            continue
        try:
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore", FutureWarning)
                dates = pd.date_range(start=last_ts, periods=horizon + 1, freq=code)[1:]
            return [d.strftime("%Y-%m-%d") for d in dates]
        except (ValueError, TypeError):
            continue
    return [f"t+{i + 1}" for i in range(horizon)]


def label_regimes_by_dominant_key(means, stds, *, covars=None,
                                   transmat=None, labels=None, probs=None):
    """Sort latent states by whichever axis — mean or standard deviation —
    dominates the regime separation, returning an axis-aware view for
    wrappers that fit variance-bearing emission distributions (Markov
    Switching with ``switching_variance=True``, GaussianHMM with
    ``covariance_type="full"``/``"diag"``, etc.).

    Motivating case: Markov Switching on Real GDP Q/Q SAAR produced
    regimes with μ=(3.00, 3.60) — a 60bp mean gap — and σ=(1.86, 6.48)
    — a 12× variance ratio. Sorting by mean labels the output as
    though the regimes differ in mean growth, when in fact the model
    has separated quiet volatility from turbulent volatility. Sorting
    by std exposes the real structure.

    Classification rule (only applied when n_regimes >= 2):

        variance_ratio         = max(σ²) / min(σ²)
        mean_sep               = |max(μ) − min(μ)|            (k=2)
                                  min adjacent gap after mean-sort  (k>=3)
        mean_sep_in_min_sigma  = mean_sep / max(min(σ), eps)
        denom                  = max(mean_sep_in_min_sigma, 0.5)
        dominance              = variance_ratio / denom

        axis_name = 'std' if (variance_ratio >= 3.0 AND dominance > 2.0)
                    else 'mean'

    Tuning rationale: the 3.0 floor on variance_ratio prevents a
    narrow-μ cluster from flipping to std-sort when both regimes have
    nearly identical variance. The ``> 2.0`` strict-inequality
    dominance threshold with a 0.5 floor on mean_sep_in_min_sigma
    keeps mean-dominant cases (e.g., μ=(-1.20, 3.40), σ=(1.10, 1.10))
    firmly on the mean-sort path even when their variance_ratio drifts
    slightly above 1.0.

    Caller pre-computes the per-regime std vector — this helper does
    NOT infer std from statsmodels ``sigma2[*]`` parameters or
    hmmlearn ``covars_`` matrices; that translation is wrapper-side
    where the layout varies by model class.

    Degenerate-input behavior matches :func:`sort_states_by_mean` for
    drop-in migration safety: ``n=0`` returns empty arrays (no
    exception); ``n=1`` returns ``order=[0], axis_name="mean"``. Zero
    or NaN in any std triggers a mean-axis fallback regardless of the
    variance_ratio.

    Parameters
    ----------
    means : array-like, shape (n_states,) or (n_states, n_vars)
        Per-regime mean. First column used as the sort key if 2-D.
    stds : array-like, shape (n_states,)
        Per-regime standard deviation. Caller's responsibility to
        extract from whatever covariance layout the underlying model
        class uses.
    covars : array, shape (n_states, ...), optional
        Per-state covariances. Reordered under the chosen axis.
    transmat : array, shape (n_states, n_states), optional
        Transition matrix — rows AND columns are permuted.
    labels : array of ints, shape (T,), optional
        Decoded state sequence — remapped to new labels.
    probs : array, shape (T, n_states), optional
        Smoothed/filtered per-state probabilities — columns permuted.

    Returns
    -------
    dict with keys:
        order       : ndarray[int], the permutation applied
        axis_name   : str, "mean" or "std"
        means       : reordered means
        stds        : reordered stds
        variance_ratio        : float or None (None when n < 2)
        mean_sep_in_min_sigma : float or None (None when n < 2)
        plus reordered ``covars``, ``transmat``, ``labels``, ``probs``
        when the corresponding input was supplied.
    """
    means_arr = np.asarray(means)
    stds_arr = np.asarray(stds, dtype=float)

    if means_arr.ndim == 2:
        mean_key = means_arr[:, 0]
    else:
        mean_key = means_arr

    n = int(len(mean_key))

    # Degenerate inputs: match sort_states_by_mean's silent-return
    # contract. No exceptions on n=0.
    if n < 2:
        order = np.arange(n, dtype=int)
        out = {
            "order": order,
            "axis_name": "mean",
            "means": means_arr[order] if n > 0 else means_arr,
            "stds": stds_arr[order] if n > 0 else stds_arr,
            "variance_ratio": None,
            "mean_sep_in_min_sigma": None,
        }
        if covars is not None:
            out["covars"] = np.asarray(covars)[order] if n > 0 else np.asarray(covars)
        if transmat is not None:
            tm = np.asarray(transmat)
            out["transmat"] = tm[order][:, order] if n > 0 else tm
        if labels is not None:
            out["labels"] = np.asarray(labels)
        if probs is not None:
            p = np.asarray(probs)
            out["probs"] = p[:, order] if n > 0 else p
        return out

    # Classification inputs. Guard against zero/NaN std (→ mean-axis).
    stds_finite = np.isfinite(stds_arr) & (stds_arr > 0)
    if not stds_finite.all():
        axis_name = "mean"
        variance_ratio = None
        mean_sep_in_min_sigma = None
    else:
        sigma2 = stds_arr ** 2
        variance_ratio = float(np.max(sigma2) / np.min(sigma2))
        if n == 2:
            mean_sep = float(np.abs(mean_key[0] - mean_key[1]))
        else:
            # Min adjacent gap after mean-sort (k >= 3).
            sorted_means = np.sort(mean_key)
            mean_sep = float(np.min(np.diff(sorted_means)))
        min_sigma = float(np.min(stds_arr))
        mean_sep_in_min_sigma = (
            mean_sep / max(min_sigma, 1e-12)
        )
        denom = max(mean_sep_in_min_sigma, 0.5)
        dominance = variance_ratio / denom
        axis_name = (
            "std" if (variance_ratio >= 3.0 and dominance > 2.0) else "mean"
        )

    sort_key = stds_arr if axis_name == "std" else mean_key
    order = np.argsort(sort_key)

    out = {
        "order": order,
        "axis_name": axis_name,
        "means": means_arr[order],
        "stds": stds_arr[order],
        "variance_ratio": variance_ratio,
        "mean_sep_in_min_sigma": mean_sep_in_min_sigma,
    }
    if covars is not None:
        out["covars"] = np.asarray(covars)[order]
    if transmat is not None:
        tm = np.asarray(transmat)
        out["transmat"] = tm[order][:, order]
    if labels is not None:
        labels_arr = np.asarray(labels)
        inv = np.empty_like(order)
        inv[order] = np.arange(len(order))
        out["labels"] = inv[labels_arr]
    if probs is not None:
        out["probs"] = np.asarray(probs)[:, order]
    return out


def sort_states_by_mean(means, *arrays, covars=None, transmat=None,
                       labels=None, probs=None):
    """Sort latent states (HMM, Markov Switching) by mean value.

    Without a convention the library's arbitrary state order can flip
    between runs — same data gives charts where "State 0" is sometimes
    the high-mean regime and sometimes the low-mean one. This helper
    returns the re-ordered arrays along with the permutation itself.

    Parameters
    ----------
    means : array, shape (n_states,) or (n_states, n_vars)
        Per-state mean (first column used for sorting if 2-D).
    *arrays : any per-state arrays indexed along axis 0
        Additional quantities to reorder (e.g., fitted parameters).
    covars : array, shape (n_states, ...), optional
        Per-state covariances.
    transmat : array, shape (n_states, n_states), optional
        Transition matrix — rows AND columns get permuted.
    labels : array of ints, shape (T,), optional
        Decoded state sequence — remapped to new labels.
    probs : array, shape (T, n_states), optional
        Smoothed or filtered per-state probabilities — columns permuted.

    Returns
    -------
    dict with keys for whichever inputs were supplied, plus 'order'
    (the permutation array that was applied).
    """
    means = np.asarray(means)
    if means.ndim == 2:
        sort_key = means[:, 0]
    else:
        sort_key = means
    order = np.argsort(sort_key)

    out = {"order": order, "means": means[order]}
    if arrays:
        out["arrays"] = tuple(np.asarray(a)[order] for a in arrays)
    if covars is not None:
        covars = np.asarray(covars)
        out["covars"] = covars[order]
    if transmat is not None:
        tm = np.asarray(transmat)
        out["transmat"] = tm[order][:, order]
    if labels is not None:
        labels = np.asarray(labels)
        inv = np.empty_like(order)
        inv[order] = np.arange(len(order))
        out["labels"] = inv[labels]
    if probs is not None:
        out["probs"] = np.asarray(probs)[:, order]
    return out


# ── Pairwise-summary and significance-disclosure convention helpers ──
# These enforce two platform-wide conventions introduced after a macro
# run of rolling_ccf_lag produced a misleading summary that averaged
# across two regimes and hid the actual sign reversal.
#
#   F2 — Every pairwise-output technique reports sign AND magnitude AND
#        direction as a paired fact in the primary sentence.
#   F3 — Every significance-emitting technique discloses its test name,
#        critical-value formula, and AC-correction status.
#
# The helpers are convention enforcers, not statistical methods. Math
# stays in libraries (scipy, statsmodels) per §4.1 of the design
# mandate. The helper signatures make it *impossible* for a caller to
# emit a summary or audit sheet that omits any of the required parts.


def flag_boundary_hits(lags, max_lag: int, threshold: float = 0.8):
    """Flag windows whose optimal lag sits near the search boundary.

    When a rolling cross-correlation search is bounded to ``[-max_lag,
    +max_lag]`` and the "best" lag lands at or near that edge, the
    reported lag is not actually informative — the optimizer likely
    wanted a lag outside the search window but got clipped. These
    windows should be *excluded* from summary statistics (mean, median,
    std of optimal lag) and their count disclosed to the user.

    Parameters
    ----------
    lags : array-like of ints
        The optimal lag selected in each rolling window.
    max_lag : int
        The absolute bound of the lag search, inclusive.
    threshold : float, default 0.8
        Fraction of ``max_lag`` above which a window is considered a
        boundary hit. Default 0.8 means ``|lag| >= 0.8 * max_lag``
        triggers the flag.

    Returns
    -------
    np.ndarray of bool
        Same length as ``lags``; True where the window hit the boundary.

    See also §4.4 honest disclosure and the T1 regression invariant.
    """
    lags_arr = np.asarray(lags)
    if lags_arr.size == 0 or max_lag <= 0:
        return np.zeros_like(lags_arr, dtype=bool)
    cutoff = threshold * float(max_lag)
    return np.abs(lags_arr.astype(float)) >= cutoff


def bartlett_effective_n(series_x, series_y, max_lag: int = None):
    """Compute the Bartlett-effective sample size for two autocorrelated series.

    Naive cross-correlation confidence bands use ``±z / sqrt(n)``, which
    assumes independent observations. For two plausibly autocorrelated
    time series (the common case for macro/financial data), the
    effective n shrinks by the factor

        n_eff = n / (1 + 2 * Σ_{k=1..K} ρ_x(k) * ρ_y(k))

    Inflation in the denominator → smaller n_eff → wider confidence
    band → fewer spurious significant lags. This is the standard
    Bartlett (1946) correction; we use the Box-Jenkins variant that
    multiplies the two autocorrelation sequences.

    Parameters
    ----------
    series_x, series_y : array-like, same length
        Two observed series (or equivalent aligned samples).
    max_lag : int, optional
        Highest lag to include in the sum. Defaults to ``int(sqrt(n))``,
        which is the common practical truncation.

    Returns
    -------
    (n_eff, inflation_factor) : tuple of (float, float)
        ``n_eff`` is the effective sample size (<= n).
        ``inflation_factor`` is ``n / n_eff`` so callers can decide
        whether the AC correction is material (>1.5x is a common
        disclosure threshold).

    This helper does not *test* significance — it only returns the
    effective n that a caller can substitute into whatever critical-
    value formula they already use. See §4.1 (math from libraries,
    convention in the wrapper).
    """
    x = np.asarray(series_x, dtype=float)
    y = np.asarray(series_y, dtype=float)
    n = min(x.size, y.size)
    if n < 3:
        return float(n), 1.0
    x = x[:n]
    y = y[:n]
    mask = np.isfinite(x) & np.isfinite(y)
    x = x[mask]
    y = y[mask]
    n_obs = x.size
    if n_obs < 3:
        return float(n_obs), 1.0
    if max_lag is None:
        max_lag = max(1, int(np.sqrt(n_obs)))
    max_lag = min(max_lag, n_obs - 2)
    x_c = x - x.mean()
    y_c = y - y.mean()
    x_var = float(np.sum(x_c ** 2))
    y_var = float(np.sum(y_c ** 2))
    if x_var <= 0 or y_var <= 0:
        return float(n_obs), 1.0
    denom = 1.0
    for k in range(1, max_lag + 1):
        rx = float(np.sum(x_c[:-k] * x_c[k:])) / x_var
        ry = float(np.sum(y_c[:-k] * y_c[k:])) / y_var
        denom += 2.0 * rx * ry
    if denom <= 0:
        # Over-persistent series can drive the sum negative; clamp to a
        # conservative worst-case (large inflation, small n_eff).
        return max(3.0, float(n_obs) / max(1.0, 2.0 * max_lag)), float(n_obs) / max(3.0, float(n_obs) / max(1.0, 2.0 * max_lag))
    n_eff = float(n_obs) / denom
    n_eff = max(3.0, min(float(n_obs), n_eff))
    inflation = float(n_obs) / n_eff
    return n_eff, inflation


def format_pairwise_summary(
    primary_prefix: str,
    x_name: str,
    y_name: str,
    *,
    sign: str,
    magnitude: float,
    direction_verb: str,
    test_name: str,
    ac_note: str,
    lag=None,
    lag_unit: str = "",
    stat_name: str = "ρ",
    break_info: dict = None,
    excluded_n: int = 0,
    extra: str = None,
) -> str:
    """Build a pairwise-technique summary that cannot omit sign/magnitude/direction.

    F2 convention enforcement. The signature demands every primary-
    sentence part by name: the caller must supply ``sign``,
    ``magnitude``, and ``direction_verb`` — there is no way to emit a
    summary that drops one. Lag, lag unit, and the statistic label
    (``ρ``, ``F``, ``coherence``, ``distance``, …) are caller-chosen
    keywords so each technique keeps its native vocabulary.

    Parameters
    ----------
    primary_prefix : str
        Technique-specific opening clause. Examples:
            "Rolling cross-correlation between 'X' and 'Y' (300 obs, window=80)"
            "Granger causality test of 'X' → 'Y' at lags 1-8 (n=286)"
            "DTW alignment of 'X' and 'Y' (286 obs)"
        Should NOT end with a period — the helper appends one.
    x_name, y_name : str
        Series names (already stripped of quotes; the helper adds them).
    sign : {"+", "-"}
        Sign of the correlation / coefficient / effect.
    magnitude : float
        Absolute value of the statistic. Helper formats with 2 decimals.
    direction_verb : {"leads", "lags", "causes", "follows", "aligns with",
                      "is contemporaneously correlated with", ...}
        Connecting verb. Caller chooses.
    test_name : str
        Name of the significance test (e.g., "Bartlett band",
        "Granger F-test", "Trace test"). Required for traceability.
    ac_note : str
        Autocorrelation correction status — ``"AC-corrected, n_eff=N"``
        or ``"naive, AC inflation likely"``.
    lag : int or None, optional
        Signed lag in ``lag_unit``. If None, the "at lag X" phrase is
        omitted (appropriate for contemporaneous / non-lag techniques
        like Johansen or Copula).
    lag_unit : str, optional
        Unit suffix, e.g. " period(s)", "q", " hours". Default empty.
    stat_name : str, default "ρ"
        Label for the reported statistic. Pass "F" for Granger, "β"
        for cointegrating coefficients, "coherence" for wavelet, etc.
    break_info : dict, optional
        If present, switches to the split-regime template. Required
        keys: ``date``, ``n_pre``, ``sign_pre``, ``magnitude_pre``,
        ``lag_pre``, ``direction_pre`` and the ``_post`` counterparts.
    excluded_n : int, default 0
        Number of windows / observations excluded (e.g., boundary hits).
    extra : str, optional
        Appended sentence for stability / diagnostic color.

    Returns
    -------
    str
        Single-paragraph plain-English summary.
    """
    if sign not in ("+", "-"):
        raise ValueError(f"sign must be '+' or '-', got {sign!r}")
    mag = abs(float(magnitude))

    # Normalize the prefix — strip trailing punctuation so we can re-append
    # a period consistently.
    prefix = str(primary_prefix).rstrip().rstrip(".")

    def _lag_clause(l):
        if l is None:
            return ""
        try:
            return f" by {int(l)}{lag_unit}"
        except (TypeError, ValueError):
            return f" by {l}{lag_unit}"

    excluded_clause = (
        f" {int(excluded_n)} observation(s) excluded."
        if excluded_n and excluded_n > 0
        else ""
    )
    sig_clause = f" Significance: {test_name} ({ac_note})."

    if break_info is not None:
        req = {"date", "n_pre", "sign_pre", "magnitude_pre", "lag_pre",
               "direction_pre", "n_post", "sign_post", "magnitude_post",
               "lag_post", "direction_post"}
        missing = req - set(break_info.keys())
        if missing:
            raise ValueError(f"break_info missing keys: {sorted(missing)}")
        s1 = break_info["sign_pre"]
        s2 = break_info["sign_post"]
        if s1 not in ("+", "-") or s2 not in ("+", "-"):
            raise ValueError("break_info sign_pre/sign_post must be '+' or '-'")
        out = (
            f"{prefix}. Structural break detected at {break_info['date']}. "
            f"Pre-break (N={int(break_info['n_pre'])}): '{x_name}' "
            f"{break_info['direction_pre']} '{y_name}'"
            f"{_lag_clause(break_info['lag_pre'])} with {stat_name}={s1}"
            f"{abs(float(break_info['magnitude_pre'])):.2f}. "
            f"Post-break (N={int(break_info['n_post'])}): '{x_name}' "
            f"{break_info['direction_post']} '{y_name}'"
            f"{_lag_clause(break_info['lag_post'])} with {stat_name}={s2}"
            f"{abs(float(break_info['magnitude_post'])):.2f}."
            f"{excluded_clause}{sig_clause}"
        )
    else:
        out = (
            f"{prefix}. '{x_name}' {direction_verb} '{y_name}'"
            f"{_lag_clause(lag)} with {stat_name}={sign}{mag:.2f}."
            f"{excluded_clause}{sig_clause}"
        )

    if extra:
        out = out + " " + str(extra).strip()
    return out


def format_significance_disclosure(
    test_name: str,
    critical_value_formula: str,
    ac_corrected: bool,
    effective_n=None,
) -> dict:
    """Return the four audit fields every significance-emitting technique must expose.

    F3 convention: any wrapper that reports a p-value, is_significant
    flag, pct_significant, confidence band, or prediction interval owes
    the user four disclosures in its audit sheet:

      - ``test_name`` : the statistical test by name (e.g., "Augmented
        Dickey-Fuller", "Bartlett white-noise band"). No empty strings.
      - ``critical_value_formula`` : plain-text formula or library
        reference (e.g., ``"±1.96/√window"``,
        ``"statsmodels.tsa.stattools.adfuller critical values"``).
      - ``ac_corrected`` : bool. True if the critical value accounts
        for autocorrelation in the input series.
      - ``effective_n`` : optional float. When ``ac_corrected=True``,
        the AC-adjusted sample size used.

    The helper is a thin dict builder — the value comes from the
    signature forcing every caller to name the test and declare AC
    status. That's the point. See §4.4 honest disclosure.
    """
    if not test_name or not str(test_name).strip():
        raise ValueError("test_name must be non-empty")
    if not critical_value_formula or not str(critical_value_formula).strip():
        raise ValueError("critical_value_formula must be non-empty")
    if not isinstance(ac_corrected, (bool, np.bool_)):
        raise TypeError(f"ac_corrected must be bool, got {type(ac_corrected).__name__}")
    out = {
        "test_name": str(test_name).strip(),
        "critical_value_formula": str(critical_value_formula).strip(),
        "ac_corrected": bool(ac_corrected),
    }
    if effective_n is not None:
        out["effective_n"] = float(effective_n)
    return out


def order_critical_values(cv_dict):
    """Return ``[(level_str, value), ...]`` sorted by the numeric significance
    level parsed from each key.

    statsmodels and arch unit-root tests return critical-value tables as
    dicts keyed by strings like ``"1%"``, ``"5%"``, ``"10%"``. Wrappers that
    naively iterate the dict (or sort lexicographically) end up displaying
    the levels in insertion/lexicographic order, which yields the confusing
    ``1% / 10% / 5%`` ordering the user reported.

    This helper parses the trailing numeric portion of each key — stripping
    the percent sign and any whitespace — and sorts ascending. Keys that
    cannot be parsed sort to the end in stable insertion order; they do not
    raise.

    Returns a list of ``(key, value)`` tuples, not a dict, so callers can
    keep the original key strings in the display but iterate in numeric
    order. Enforces the specification-transparency convention (§4.3) for
    every stationarity test wrapper.
    """
    if not cv_dict:
        return []
    items = list(cv_dict.items())

    def _level(k):
        try:
            return float(str(k).replace("%", "").strip())
        except (ValueError, AttributeError):
            return float("inf")

    items.sort(key=lambda kv: _level(kv[0]))
    return [(str(k), float(v)) for k, v in items]


class RunContext:
    """
    Encapsulates everything a technique needs to execute.

    Constructed from the JSON RunRequest sent by the C# add-in over Named Pipes.
    """

    def __init__(self, raw: dict):
        self.run_id: str = raw.get("run_id", "")
        self.technique_id: str = raw.get("technique_id", "")
        self.preset: str = raw.get("preset", "Balanced")
        self.seed: int = raw.get("seed", 42)
        # Normalize frequency: the C# TimeIndexDetector emits human-readable
        # labels ("Monthly", "Quarterly", "CalendarDaily", ...) but every
        # technique's _infer_period maps pandas-style short codes ("M", "Q",
        # "D", ...). Translate once here so all techniques work uniformly.
        self.frequency: str = _normalize_frequency(raw.get("frequency", ""))
        self.time: list = raw.get("time", [])
        self.series: list = raw.get("series", [])  # list of {name, values}
        self.exog: list = raw.get("exog", [])       # list of {name, values}
        self.params: dict = raw.get("params", {})
        self.fill_config: dict = raw.get("fill_config", {})
        self.resample_config: dict = raw.get("resample_config", {})

        # Normalize chronological order. Many of our sample CSVs and a
        # common Excel convention are "newest-first" (most recent row at
        # the top of the selection). Every technique's math assumes an
        # oldest-first order — so if we detect the input is descending
        # in time, flip both `time` and every series/exog values array
        # once up-front. Downstream code then never has to think about it.
        self.input_was_reversed: bool = False
        self._normalize_chronological_order()

    def _normalize_chronological_order(self) -> None:
        """If `self.time` is strictly descending, reverse it and every
        parallel series/exog values array in place. Leaves things alone
        if the order is already ascending, mixed, or mostly unparseable.

        Tolerates unparseable entries (header rows, blanks, garbage cells)
        by recording their index position as None and making the direction
        decision only from pairs of adjacent parseable dates.
        """
        if not self.time or len(self.time) < 2:
            return
        import datetime as _dt

        parsed = [None] * len(self.time)
        for i, t in enumerate(self.time):
            if t is None:
                continue
            s = str(t).strip()
            if not s:
                continue
            if "T" in s:
                s = s.split("T", 1)[0]
            s = s.replace("/", "-").replace("Z", "").strip()
            try:
                parsed[i] = _dt.date.fromisoformat(s[:10])
            except (ValueError, TypeError):
                # Unparseable (e.g. the literal string "Date" from a
                # header row). Leave as None and move on.
                continue

        # Require at least a handful of parseable dates to make any call.
        parseable_count = sum(1 for p in parsed if p is not None)
        if parseable_count < 3:
            return

        # Walk consecutive pairs where BOTH sides parsed. Count ascending
        # vs descending. Unparseable positions don't vote.
        asc = desc = tied = 0
        for i in range(len(parsed) - 1):
            a, b = parsed[i], parsed[i + 1]
            if a is None or b is None:
                continue
            if a < b:
                asc += 1
            elif a > b:
                desc += 1
            else:
                tied += 1

        pairs_considered = asc + desc + tied
        if pairs_considered == 0:
            return

        # Reverse only if overwhelmingly descending. A single out-of-order
        # row or tie shouldn't flip the series.
        if desc > asc and desc >= 0.9 * pairs_considered:
            self.input_was_reversed = True
            self.time = list(reversed(self.time))
            parsed = list(reversed(parsed))
            for s in self.series or []:
                vals = s.get("values")
                if isinstance(vals, list):
                    s["values"] = list(reversed(vals))
            for s in self.exog or []:
                vals = s.get("values")
                if isinstance(vals, list):
                    s["values"] = list(reversed(vals))

        # After ordering is normalized, trim unparseable entries from the
        # ends. These are almost always header rows that got swept into
        # the C# selection (e.g. cell A1 containing the literal "Date"
        # becomes an empty string). Leaving them in place would mean the
        # last row of the output table shows a blank date, and any
        # downstream truncation (fit_window_obs, 85-year X-13 cap) would
        # treat the header position as a real observation.
        def _first_parseable(idx_range):
            for i in idx_range:
                if parsed[i] is not None:
                    return i
            return None

        n_orig = len(self.time)
        head = _first_parseable(range(n_orig)) or 0
        tail = _first_parseable(range(n_orig - 1, -1, -1))
        tail = (tail + 1) if tail is not None else n_orig

        if head > 0 or tail < n_orig:
            self.time = self.time[head:tail]
            for s in self.series or []:
                vals = s.get("values")
                if isinstance(vals, list) and len(vals) == n_orig:
                    s["values"] = vals[head:tail]
            for s in self.exog or []:
                vals = s.get("values")
                if isinstance(vals, list) and len(vals) == n_orig:
                    s["values"] = vals[head:tail]

    # ------------------------------------------------------------------
    # Series helpers
    # ------------------------------------------------------------------

    def get_series_by_name(self, name: str) -> np.ndarray:
        """Return the values array for a named series, or raise."""
        for s in self.series:
            if s.get("name") == name:
                return _to_float_array(s.get("values", []))
        raise ValueError(f"Series '{name}' not found. Available: {[s['name'] for s in self.series]}")

    def get_primary_series(self) -> tuple:
        """Return (name, values) for the first series."""
        if not self.series:
            raise ValueError("No series provided. Please select at least one data column.")
        s = self.series[0]
        return s.get("name", "Series1"), _to_float_array(s.get("values", []))

    def get_all_series(self) -> list:
        """Return list of (name, np.ndarray) for all series."""
        result = []
        for s in self.series:
            name = s.get("name", f"Series{len(result) + 1}")
            values = _to_float_array(s.get("values", []))
            result.append((name, values))
        return result

    def validate_min_series(self, n: int):
        """Raise if fewer than n series are present."""
        if len(self.series) < n:
            raise ValueError(
                f"This technique requires at least {n} series, but only "
                f"{len(self.series)} were provided. Please select more data columns."
            )

    def get_param(self, key: str, default=None):
        """Safely retrieve a technique parameter with a default."""
        return self.params.get(key, default)


# ======================================================================
# Output builders
# ======================================================================

def make_table(name: str, columns: list, rows: list) -> dict:
    """
    Build a single output table dict matching the OutputTable schema.

    Parameters
    ----------
    name : str
        Table name (e.g. "Decomposition", "Test Results").
    columns : list[str]
        Column header names.
    rows : list[list]
        Each inner list is one row of values. Values should be JSON-safe
        (str, int, float, bool, None). numpy types are converted.

    Returns
    -------
    dict with keys: name, columns, rows
    """
    safe_rows = []
    for row in rows:
        safe_row = [_json_safe(v) for v in row]
        safe_rows.append(safe_row)
    return {
        "name": name,
        "columns": list(columns),
        "rows": safe_rows,
    }


def make_response(
    ctx: RunContext,
    *,
    status: str = "success",
    tables: list = None,
    plain_english_summary: str = "",
    warnings: list = None,
    audit_fields: dict = None,
    charting_suggestions: str = "",
    artifacts: dict = None,
    error_message: str = None,
    error_fixes: list = None,
    engine_versions: dict = None,
    interpretation: dict = None,
) -> dict:
    """
    Build a RunResponse dict matching the C# RunResponse schema.

    This is the canonical way for techniques to return results.

    The ``interpretation`` kwarg carries the two-tier plain-language
    Interpretation block (tier1 Plain-Language Finding, tier2 Technical
    Interpretation, tier3 Caveats). Produced by
    :func:`engine.interpretation.build_interpretation`. When ``None``
    (e.g., techniques that have not yet been wired in Prompts B/C),
    the response omits the ``"interpretation"`` key entirely and the
    C# writer renders the sheet as before — purely additive rollout.
    """
    if audit_fields is None:
        audit_fields = {}

    # Stamp standard audit fields
    audit_fields.setdefault("technique_id", ctx.technique_id)
    audit_fields.setdefault("preset", ctx.preset)
    audit_fields.setdefault("seed", ctx.seed)
    audit_fields.setdefault("n_observations", _count_obs(ctx))
    audit_fields.setdefault("timestamp_utc", datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z")

    resp = {
        "run_id": ctx.run_id,
        "status": status,
        "plain_english_summary": plain_english_summary,
        "tables": tables or [],
        "artifacts": artifacts or {},
        "warnings": warnings or [],
        "audit_fields": audit_fields,
        "charting_suggestions": charting_suggestions,
    }
    if interpretation is not None:
        resp["interpretation"] = interpretation

    if engine_versions:
        resp["engine_versions"] = engine_versions

    if error_message:
        resp["error_message"] = error_message
    if error_fixes:
        resp["error_fixes"] = error_fixes

    return resp


def make_error_response(
    ctx: RunContext,
    error_message: str,
    error_fixes: list = None,
    warnings: list = None,
    engine_versions: dict = None,
) -> dict:
    """Convenience: build a failure RunResponse."""
    return make_response(
        ctx,
        status="failure",
        error_message=error_message,
        error_fixes=error_fixes or [],
        warnings=warnings or [],
        engine_versions=engine_versions,
    )


# ======================================================================
# Internal helpers
# ======================================================================

def _to_float_array(values: list) -> np.ndarray:
    """
    Convert a list of nullable doubles to a numpy float64 array.

    None / null values become np.nan.
    """
    out = np.empty(len(values), dtype=np.float64)
    for i, v in enumerate(values):
        if v is None:
            out[i] = np.nan
        else:
            try:
                out[i] = float(v)
            except (TypeError, ValueError):
                out[i] = np.nan
    return out


def _json_safe(v):
    """Convert numpy scalars to Python native types for JSON serialisation."""
    if v is None:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        if np.isnan(v) or np.isinf(v):
            return None
        return float(v)
    if isinstance(v, np.bool_):
        return bool(v)
    if isinstance(v, (np.ndarray,)):
        return v.tolist()
    if isinstance(v, float):
        if np.isnan(v) or np.isinf(v):
            return None
        return v
    return v


def _count_obs(ctx: RunContext) -> int:
    """Count observations from first series or time array."""
    if ctx.series:
        vals = ctx.series[0].get("values", [])
        return len(vals)
    return len(ctx.time)


def dropna_aligned(*arrays):
    """
    Drop rows where ANY of the input arrays has NaN.
    Returns a tuple of cleaned arrays (same order).
    """
    mask = np.ones(len(arrays[0]), dtype=bool)
    for a in arrays:
        mask &= ~np.isnan(a)
    return tuple(a[mask] for a in arrays)
