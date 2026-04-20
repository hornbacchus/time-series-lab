"""
InterpretationSpec for markov_switching.

Tier 1 leads with regime count + sorted labels (by mean or by std,
whichever axis dominates regime separation) + current state +
smoothed probability, then a structure-implication closer (not a
forecasting directive). Tier 2 enumerates per-regime (μ, σ) and notes
the transition-matrix role in multi-step forecasts.

Results-dict keys consumed:

    k_regimes           : int
    regime_means        : list[float] (sorted per sort_axis)
    regime_stds         : list[float] (in the same permutation)
    current_regime      : int (index into the sorted list)
    current_prob        : float (smoothed probability on final period)
    expected_durations  : list[float] (1/(1-P(stay)) per regime)
    final_period_probs  : list[float] (for the ambiguous-state trigger)
    sort_axis           : str ("mean" or "std"; wrapper classifies via
                               label_regimes_by_dominant_key)
    forecast_method     : str | None ("transition_matrix_closed_form" |
                                      "iterated_regime_weighted")
    forecast_horizon    : int | None (horizon in forecast periods)
    forecast_h_probs    : list[float] | None (pi_h at final horizon,
                                              sorted order)
    forecast_stationary : list[float] | None (stationary distribution
                                              of the transition matrix)
    markov_rmse         : float | None (in-sample RMSE of the Markov fit)
    benchmark_rmse      : float | None (in-sample RMSE of a single-
                                        regime same-AR-order reference)
    benchmark_name      : str | None ("constant mean" | "AR(k)")
    rmse_lift_vs_benchmark : float | None ((bench - markov) / bench)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_regime_label,
    format_stat_technical,
    FMT_RHO,          # reused for μ/σ to 2dp (same numeric scale)
    FMT_PROBABILITY,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _regime_label(regime_idx: int, n_regimes: int, axis: str = "mean") -> str:
    """Plain-English label for a regime index given the sort axis."""
    rec = interpret_regime_label(regime_idx, n_regimes, axis=axis)
    return str(rec["label"])


def _axis_labels(sort_axis: str) -> dict:
    """Translate the wrapper's machine-readable ``sort_axis`` token
    into the spec's label-vs-prose vocabulary pair.

    - ``label`` is the token fed to :func:`interpret_regime_label` to
      produce regime-label strings like ``"low-{label} regime"``.
    - ``prose`` is the word-form used in full-prose sentences like
      ``"sorted by empirical {prose}"``.

    Mapping (§Prompt-2 Markov batch decisions):

        sort_axis == "mean" → label="mean", prose="mean"
        sort_axis == "std"  → label="σ",    prose="standard deviation"

    Any other string is treated as ``"mean"`` for robustness.
    """
    key = str(sort_axis or "").strip().lower()
    if key == "std":
        return {"label": "σ", "prose": "standard deviation"}
    return {"label": "mean", "prose": "mean"}


def _format_mu(mu: float) -> str:
    # μ is a location value on the input series' scale; pin to 2dp.
    return f"{float(mu):.2f}"


def _format_sigma(sigma: float) -> str:
    return f"{float(sigma):.2f}"


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    k = int(results.get("k_regimes", 2))
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    current = int(results.get("current_regime", 0))
    current_p = float(results.get("current_prob", 0.0))
    axis_tokens = _axis_labels(results.get("sort_axis", "mean"))
    label_axis = axis_tokens["label"]
    prose_axis = axis_tokens["prose"]
    current_label = _regime_label(current, k, axis=label_axis)

    # Build per-regime (μ) citation string, sorted as provided
    if k == 2:
        # Case (a) shape: "the low-mean regime (μ=−1.20) and high-mean
        # regime (μ=3.40) are well-separated with common volatility
        # (σ=σ_val)" — the common-σ clause only when stds are ≈ equal.
        mu0 = _format_mu(means[0]) if len(means) > 0 else "0.00"
        mu1 = _format_mu(means[1]) if len(means) > 1 else "0.00"
        s0 = float(stds[0]) if len(stds) > 0 else 0.0
        s1 = float(stds[1]) if len(stds) > 1 else 0.0
        if abs(s0 - s1) < 0.1:
            vol_clause = f" with common volatility (σ={_format_sigma(s0)})"
        else:
            vol_clause = ""
        regime_listing = (
            f"the {_regime_label(0, 2, label_axis)} (μ=−{mu0[1:]}) "
            if means and means[0] < 0 else
            f"the {_regime_label(0, 2, label_axis)} (μ={mu0}) "
        )
        # Normalize signed μ display with Unicode minus
        regime_listing = (
            f"the {_regime_label(0, 2, label_axis)} (μ={_signed_mu(means[0])}) "
            f"and {_regime_label(1, 2, label_axis)} (μ={_signed_mu(means[1])}) "
            f"are well-separated{vol_clause}"
        )
        return (
            f"2-regime Markov switching model. After sorting regimes by "
            f"empirical {prose_axis}, {regime_listing}. The current state is "
            f"the {current_label} with smoothed probability "
            f"{FMT_PROBABILITY.format(current_p)}. The {current_label}'s "
            f"dynamics, not the unconditional-sample mean, characterize "
            f"the current state."
        )

    # k >= 3 case: lowest / mid / highest labels
    regime_fragments = []
    for i in range(k):
        mu = _signed_mu(means[i]) if i < len(means) else "0.00"
        regime_fragments.append(
            f"{_regime_label(i, k, label_axis)} (μ={mu})"
        )
    regime_listing = ", ".join(regime_fragments[:-1]) + ", and " + regime_fragments[-1]
    return (
        f"{k}-regime Markov switching model. After sorting by empirical "
        f"{prose_axis}, the {regime_listing} are well-separated. The current "
        f"state is the {current_label} with smoothed probability "
        f"{FMT_PROBABILITY.format(current_p)}. The current state and "
        f"its transition probabilities to adjacent regimes characterize "
        f"the short-horizon forecast distribution more informatively "
        f"than the unconditional mean."
    )


def _signed_mu(mu: float) -> str:
    """Render μ with an explicit sign character using the Unicode minus
    (matches the Tier 1 convention in ADF, rolling_ccf_lag, etc.)."""
    val = float(mu)
    s = f"{abs(val):.2f}"
    return f"−{s}" if val < 0 else s


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    k = int(results.get("k_regimes", 2))
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    current = int(results.get("current_regime", 0))
    current_p = float(results.get("current_prob", 0.0))
    axis_tokens = _axis_labels(results.get("sort_axis", "mean"))
    label_axis = axis_tokens["label"]
    prose_axis = axis_tokens["prose"]

    header = f"Markov switching fit with {k} regimes."
    # Per-regime citation: Regime i (label): μ=..., σ=...
    lines = []
    for i in range(k):
        label = _regime_label(i, k, label_axis)
        mu = _signed_mu(means[i]) if i < len(means) else "0.00"
        sigma = _format_sigma(stds[i]) if i < len(stds) else "0.00"
        if k == 2:
            lines.append(f"Regime {i} (μ={mu}, σ={sigma})")
        else:
            lines.append(f"Regime {i} ({label.split(' regime')[0]}): μ={mu}, σ={sigma}")
    if k == 2:
        per_regime = " and ".join(lines) + "."
        # Rewrite for the 2-regime case: sentence-final form with both
        # regimes in a single "Regime 0 (μ=..., σ=...) and Regime 1
        # (μ=..., σ=...)." construction.
        per_regime = (
            f"Regimes are sorted by empirical {prose_axis}: "
            f"{lines[0]} and {lines[1]}."
        )
    else:
        per_regime = ". ".join(lines) + "."

    current_sentence = (
        f"The most recent period's smoothed probability places the "
        f"series in Regime {current} at "
        f"{FMT_PROBABILITY.format(current_p)}."
    )

    # Closer — mechanical, no directive (per R9)
    closer = (
        "Expected durations and the full transition matrix appear in "
        "the data tables; the transition matrix governs how regime "
        "probabilities evolve at multi-step horizons."
    )
    if k >= 3:
        # Shorter closer for k>=3 cases since Tier 1 already says this
        closer = (
            "Transition dynamics and per-regime sample counts appear in "
            "the data tables."
        )

    # Forecast-disclosure sentence. Appended after the closer so Tier 1
    # and Tier 2 prose don't overlap on "transition matrix" / "regime
    # probabilities" vocabulary. Named by method so the Hamilton (1994)
    # iterated-convention bias is disclosed when it applies.
    method = str(results.get("forecast_method") or "")
    h = results.get("forecast_horizon")
    forecast_sentence = ""
    if method and h:
        if method == "transition_matrix_closed_form":
            method_prose = "the closed-form π_h · μ construction"
        else:
            method_prose = (
                "the iterated regime-weighted scheme (Hamilton 1994), "
                "treating earlier forecasts as realized observations"
            )
        if k == 2:
            forecast_sentence = (
                f" The {int(h)}-step forecast in the data tables uses "
                f"{method_prose}; 95% intervals assume Gaussian "
                f"within-regime emissions, ignore parameter estimation "
                f"uncertainty, and do not compound AR-innovation "
                f"variance across forecast horizons."
            )
        else:
            forecast_sentence = (
                f" The {int(h)}-step forecast uses {method_prose}; "
                f"95% intervals assume Gaussian within-regime emissions."
            )

    # Single-regime benchmark disclosure. Converts the Markov fit's
    # absolute RMSE into a lift metric users can actually reason about.
    # Placed after the forecast disclosure to keep the reporting order
    # "fit details → forecast math → calibration check against a
    # simpler alternative".
    markov_rmse = results.get("markov_rmse")
    benchmark_rmse = results.get("benchmark_rmse")
    benchmark_name = results.get("benchmark_name")
    lift = results.get("rmse_lift_vs_benchmark")
    benchmark_sentence = ""
    if (markov_rmse is not None and benchmark_rmse is not None
            and benchmark_name and lift is not None):
        benchmark_sentence = (
            f" The model's RMSE of {float(markov_rmse):.2f} compares with "
            f"a single-regime {benchmark_name} benchmark RMSE of "
            f"{float(benchmark_rmse):.2f}, an in-sample lift of "
            f"{float(lift):+.1%}."
        )

    return f"{header} {per_regime} {current_sentence} {closer}{forecast_sentence}{benchmark_sentence}"


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_weak_separation(results: dict) -> Optional[str]:
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    if len(means) < 2 or len(stds) < 2:
        return None
    for i in range(len(means)):
        for j in range(i + 1, len(means)):
            if len(stds) <= j:
                continue
            common_sigma = 0.5 * (float(stds[i]) + float(stds[j]))
            if abs(float(means[i]) - float(means[j])) < common_sigma:
                return (
                    f"Regime means ({_signed_mu(means[i])}, "
                    f"{_signed_mu(means[j])}) are separated by less than "
                    "one common-σ unit. The two regimes are weakly "
                    "distinguishable in the data; the regime-switching "
                    "interpretation should be treated with caution, and "
                    "a single-regime specification with heteroskedasticity "
                    "may fit comparably."
                )
    return None


def _trigger_near_absorbing(results: dict) -> Optional[str]:
    durations = list(results.get("expected_durations") or [])
    for i, d in enumerate(durations):
        try:
            d_f = float(d)
        except (TypeError, ValueError):
            continue
        if d_f > 50:
            return (
                f"Regime {i} has expected duration {int(round(d_f))} "
                "periods, close to an absorbing-state regime. If this is "
                "the current state, forecasts can treat the current "
                "regime as effectively permanent on short-to-medium "
                "horizons."
            )
    return None


def _trigger_ambiguous_current_state(results: dict) -> Optional[str]:
    probs = list(results.get("final_period_probs") or [])
    if not probs:
        current_p = results.get("current_prob")
        if current_p is None:
            return None
        max_p = float(current_p)
    else:
        try:
            max_p = max(float(p) for p in probs)
        except (TypeError, ValueError):
            return None
    if max_p >= 0.6:
        return None
    return (
        f"The most recent period's smoothed regime probabilities are "
        f"diffuse (max P={FMT_PROBABILITY.format(max_p)}). The current "
        "state is not confidently identified; forecasts should weight "
        "multiple regimes rather than conditioning on a single one."
    )


def _trigger_near_stationary_at_horizon(results: dict) -> Optional[str]:
    """Fires when the h-step regime-probability forecast is within 1%
    (max-norm) of the stationary distribution of the transition matrix.
    Under that condition, forecasts beyond this horizon carry no
    additional regime-path information — they all reduce to the
    unconditional stationary mixture."""
    h_probs = results.get("forecast_h_probs")
    stationary = results.get("forecast_stationary")
    horizon = results.get("forecast_horizon")
    if h_probs is None or stationary is None or horizon is None:
        return None
    try:
        h_arr = [float(p) for p in h_probs]
        s_arr = [float(p) for p in stationary]
    except (TypeError, ValueError):
        return None
    if len(h_arr) != len(s_arr) or not h_arr:
        return None
    max_abs_diff = max(abs(hp - sp) for hp, sp in zip(h_arr, s_arr))
    # 1e-2 threshold chosen for informative coverage at horizon=10 on
    # typical macro regime persistence. The tighter 1e-3 would rarely
    # fire; 1e-2 surfaces genuinely near-stationary chains.
    if max_abs_diff >= 1e-2:
        return None
    return (
        f"Regime probabilities at h={int(horizon)} are within 1% of "
        f"the stationary distribution — forecasts beyond this horizon "
        f"converge to the unconditional mixture and carry no "
        f"additional regime information."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="markov_switching",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_weak_separation,
        _trigger_near_absorbing,
        _trigger_ambiguous_current_state,
        _trigger_near_stationary_at_horizon,
    ),
    mode_aware=False,
)

register(SPEC)
