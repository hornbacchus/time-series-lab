"""
InterpretationSpec for hmm (Gaussian Hidden Markov Model).

Adapted from markov_switching spec. HMM shares the sort-axis labeling
and regime-probability conventions; the distinctive emission
assumption is i.i.d. within each state (no AR dynamics, unlike
Markov Switching with order>=1). Also adds disclosure of
covariance_type.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_PROBABILITY,
    FMT_RHO,
    interpret_regime_label,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _axis_labels(sort_axis: str) -> dict:
    key = str(sort_axis or "").strip().lower()
    if key == "std":
        return {"label": "σ", "prose": "standard deviation"}
    return {"label": "mean", "prose": "mean"}


def _regime_label(regime_idx: int, n_regimes: int, axis: str = "mean") -> str:
    rec = interpret_regime_label(regime_idx, n_regimes, axis=axis)
    return str(rec["label"])


def _signed(val: float) -> str:
    v = float(val)
    s = f"{abs(v):.2f}"
    return f"−{s}" if v < 0 else s


def _tier1(results: dict) -> str:
    k = int(results.get("k_regimes", 2))
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    current = int(results.get("current_regime", 0))
    current_p = float(results.get("current_prob", 0.0))
    cov_type = str(results.get("covariance_type", "diag"))
    n_obs = int(results.get("n_obs", 0))
    axis_tokens = _axis_labels(results.get("sort_axis", "mean"))
    label_axis = axis_tokens["label"]
    current_label = _regime_label(current, k, axis=label_axis)

    if k == 2 and len(means) >= 2 and len(stds) >= 2:
        mu0 = _signed(means[0])
        mu1 = _signed(means[1])
        s0 = _signed(stds[0])
        s1 = _signed(stds[1])
        return (
            f"2-state Gaussian HMM on the series ({n_obs} "
            f"observations, {cov_type} covariance). After sorting by "
            f"empirical mean, the {_regime_label(0, 2, label_axis)} "
            f"(μ={mu0}) and {_regime_label(1, 2, label_axis)} "
            f"(μ={mu1}) are well-separated with distinct volatilities "
            f"(σ={s0}, σ={s1}). The series is currently in the "
            f"{current_label} with smoothed probability "
            f"{FMT_PROBABILITY.format(current_p)}."
        )

    # k >= 3
    parts = []
    for i in range(k):
        mu = _signed(means[i]) if i < len(means) else "0.00"
        parts.append(f"{_regime_label(i, k, label_axis)} (μ={mu})")
    listing = ", ".join(parts[:-1]) + ", and " + parts[-1]
    return (
        f"{k}-state Gaussian HMM on the series ({n_obs} observations, "
        f"{cov_type} covariance). After sorting by empirical mean, "
        f"the {listing} are distinguishable. The series is currently "
        f"in the {current_label} with smoothed probability "
        f"{FMT_PROBABILITY.format(current_p)}."
    )


def _tier2(results: dict) -> str:
    k = int(results.get("k_regimes", 2))
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    durations = list(results.get("expected_durations") or [])
    cov_type = str(results.get("covariance_type", "diag"))
    axis_tokens = _axis_labels(results.get("sort_axis", "mean"))
    prose_axis = axis_tokens["prose"]
    lines = []
    for i in range(k):
        mu = _signed(means[i]) if i < len(means) else "0.00"
        sigma = f"{float(stds[i]):.2f}" if i < len(stds) else "0.00"
        dur = (
            f"{float(durations[i]):.1f}" if i < len(durations) and durations[i] != float("inf")
            else "∞" if i < len(durations) else "?"
        )
        lines.append(f"State {i} (μ={mu}, σ={sigma}, expected duration {dur})")
    per_state = (
        f"States sorted by empirical {prose_axis}: "
        + "; ".join(lines) + "."
    )
    return (
        f"Gaussian HMM fit via EM (hmmlearn) with {cov_type} "
        f"covariance. {per_state} Unlike Markov Switching (which "
        f"fits AR dynamics within each regime), Gaussian HMM assumes "
        f"i.i.d. emissions within each state — appropriate for "
        f"series where mean or variance shifts dominate AR structure. "
        f"Transition matrix in the data tables governs regime "
        f"probabilities at multi-step horizons."
    )


def _trigger_weak_separation(results: dict) -> Optional[str]:
    means = list(results.get("regime_means") or [])
    stds = list(results.get("regime_stds") or [])
    if len(means) < 2 or len(stds) < 2:
        return None
    for i in range(len(means)):
        for j in range(i + 1, len(means)):
            if len(stds) <= j:
                continue
            common = 0.5 * (float(stds[i]) + float(stds[j]))
            if abs(float(means[i]) - float(means[j])) < common:
                return (
                    f"Regime means ({_signed(means[i])}, "
                    f"{_signed(means[j])}) are separated by less than "
                    f"one common-σ unit. The two states are weakly "
                    f"distinguishable; the HMM interpretation should "
                    f"be treated with caution, and a single-state "
                    f"model with heteroskedasticity may fit "
                    f"comparably."
                )
    return None


def _trigger_tied_covariance_heterogeneous(results: dict) -> Optional[str]:
    cov_type = str(results.get("covariance_type", ""))
    stds = list(results.get("regime_stds") or [])
    if cov_type != "tied" or len(stds) < 2:
        return None
    if max(stds) - min(stds) < 0.1:
        return None
    return (
        "covariance_type='tied' forces identical variance across "
        "states, but the sorted-state std range suggests genuinely "
        "different within-state volatilities. Re-run with "
        "covariance_type='diag' or 'full' to let the states express "
        "their distinct volatility."
    )


def _trigger_near_absorbing(results: dict) -> Optional[str]:
    durations = list(results.get("expected_durations") or [])
    for i, d in enumerate(durations):
        try:
            d_f = float(d)
        except (TypeError, ValueError):
            continue
        if d_f > 50:
            return (
                f"State {i} has expected duration {int(round(d_f))} "
                f"periods, close to an absorbing-state regime. If the "
                f"current state is this one, forecasts can treat it "
                f"as effectively permanent on short-to-medium horizons."
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
        f"The most recent period's smoothed state probabilities are "
        f"diffuse (max P={FMT_PROBABILITY.format(max_p)}). The "
        f"current state is not confidently identified; forecasts "
        f"should weight multiple states rather than conditioning on "
        f"a single one."
    )


SPEC = InterpretationSpec(
    technique_id="hmm",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_weak_separation,
        _trigger_tied_covariance_heterogeneous,
        _trigger_near_absorbing,
        _trigger_ambiguous_current_state,
    ),
    mode_aware=False,
)

register(SPEC)
