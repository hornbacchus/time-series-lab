"""
InterpretationSpec for vecm_model (Vector Error Correction / cointegration).

Describes the cointegrating-pair finding and half-life of adjustment in
Tier 1, and the Johansen trace test + Phillips β + α in Tier 2. Reads
β and α matrices from the wrapper's newly-exposed ``beta_normalized`` /
``alpha_normalized`` audit fields (Phillips-normalized so β[0, j] = 1).

Results-dict keys consumed:

    variable_names       : list[str]
    coint_rank           : int (r; 0 = not cointegrated)
    lag_order            : int
    n_obs                : int
    beta_normalized      : list[list[float]] (k × r)
    alpha_normalized     : list[list[float]] (k × r)
    half_life_periods    : float or None
    trace_stat           : float (first-rank trace statistic, H0: r=0)
    trace_cv_5pct        : float
    trace_stat_r1        : float or None (next-rank trace, H0: r=1)
    trace_cv_r1_5pct     : float or None
    significance         : float (α used for decision, typically 0.05)
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    interpret_coefficient_magnitude,
    format_stat_technical,
    FMT_COEF_SIGNED,
    FMT_HALF_LIFE,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _pair_names(results: dict) -> tuple:
    names = list(results.get("variable_names") or [])
    x = str(names[0]) if len(names) >= 1 else "Y1"
    y = str(names[1]) if len(names) >= 2 else "Y2"
    return x, y


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    x, y = _pair_names(results)
    rank = int(results.get("coint_rank", 0))

    if rank >= 1:
        return _tier1_cointegrated(results, x, y)
    return _tier1_not_cointegrated(results, x, y)


def _tier1_cointegrated(results: dict, x: str, y: str) -> str:
    beta = results.get("beta_normalized") or [[1.0], [0.0]]
    beta_yx = float(beta[1][0]) if len(beta) >= 2 else 0.0
    # β is normalized so first entry is 1.0; the second entry carries
    # the cointegrating ratio. Spread = x − |beta_yx|·y when beta_yx<0
    # (most cointegrating pairs); show as a subtraction for readability.
    abs_beta = abs(beta_yx)
    spread_str = f"{x} − {abs_beta:.2f}·{y}" if beta_yx < 0 else f"{x} + {abs_beta:.2f}·{y}"
    hl = results.get("half_life_periods")
    if hl is not None:
        hl_clause = (
            f" and mean-reverts with a half-life of about "
            f"{FMT_HALF_LIFE.format(float(hl))} periods"
        )
    else:
        hl_clause = ""
    return (
        f"'{x}' and '{y}' form a cointegrating relationship — the spread "
        f"({spread_str}) is stationary{hl_clause}. The relationship "
        f"supports joint modeling of the level via an error-correction "
        f"specification; the spread itself is a valid stationary state "
        f"variable."
    )


def _tier1_not_cointegrated(results: dict, x: str, y: str) -> str:
    return (
        f"'{x}' and '{y}' do not form a cointegrating relationship "
        f"(Johansen rank = 0). No stable long-run spread between them "
        f"exists; any apparent co-movement in levels is either spurious "
        f"or regime-dependent. The series do not share a common "
        f"stochastic trend."
    )


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    rank = int(results.get("coint_rank", 0))
    if rank >= 1:
        return _tier2_cointegrated(results)
    return _tier2_not_cointegrated(results)


def _tier2_cointegrated(results: dict) -> str:
    trace = float(results.get("trace_stat", 0.0))
    cv = float(results.get("trace_cv_5pct", 0.0))
    trace_r1 = results.get("trace_stat_r1")
    cv_r1 = results.get("trace_cv_r1_5pct")

    beta = results.get("beta_normalized") or [[1.0], [0.0]]
    beta_yx = float(beta[1][0]) if len(beta) >= 2 else 0.0
    alpha = results.get("alpha_normalized") or [[0.0]]
    alpha_11 = float(alpha[0][0]) if alpha else 0.0
    hl = results.get("half_life_periods")

    trace_sentence = (
        f"Johansen trace test rejects r=0 at the 5% level (trace="
        f"{trace:.2f}, CV(5%)={cv:.2f})"
    )
    if trace_r1 is not None and cv_r1 is not None:
        trace_sentence += (
            f" and fails to reject r=1 (trace={float(trace_r1):.2f}, "
            f"CV(5%)={float(cv_r1):.2f})"
        )
    trace_sentence += ", establishing a single cointegrating vector."

    # Phillips-normalized vector citation: show (1, β_yx) with β signed.
    vec_frag = f"(1, {FMT_COEF_SIGNED.format(beta_yx)})"
    alpha_frag = (
        f"the error-correction coefficient "
        f"α₁={FMT_COEF_SIGNED.format(alpha_11)}"
    )
    if hl is not None:
        hl_frag = (
            f" yields a half-life of about {FMT_HALF_LIFE.format(float(hl))} "
            f"periods on the first series"
        )
    else:
        hl_frag = ""
    vec_sentence = (
        f"After Phillips triangular normalization the vector is "
        f"{vec_frag}, and {alpha_frag}{hl_frag}."
    )

    return f"{trace_sentence} {vec_sentence}"


def _tier2_not_cointegrated(results: dict) -> str:
    trace = float(results.get("trace_stat", 0.0))
    cv = float(results.get("trace_cv_5pct", 0.0))
    return (
        f"Johansen trace test fails to reject r=0 (trace={trace:.2f}, "
        f"CV(5%)={cv:.2f}), so no cointegrating vector is supported. The "
        "two series appear independent at the integration level; any "
        "apparent co-movement is likely spurious or regime-dependent "
        "rather than structurally anchored."
    )


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_fast_half_life(results: dict) -> Optional[str]:
    hl = results.get("half_life_periods")
    if hl is None or float(hl) >= 5.0:
        return None
    return (
        f"The computed half-life of {FMT_HALF_LIFE.format(float(hl))} "
        "periods is faster than typical macro cointegrating relationships "
        "and may reflect high-frequency noise rather than a durable "
        "long-run equilibrium. Verify the relationship holds on a longer "
        "window."
    )


def _trigger_slow_half_life(results: dict) -> Optional[str]:
    hl = results.get("half_life_periods")
    if hl is None or float(hl) <= 100.0:
        return None
    return (
        f"The computed half-life of {FMT_HALF_LIFE.format(float(hl))} "
        "periods is slower than most cointegrating relationships on this "
        "sampling frequency. The long-run equilibrium may be weakly "
        "identified, and forecasting on a horizon shorter than the "
        "half-life should not rely heavily on the error-correction "
        "channel."
    )


def _trigger_borderline_trace(results: dict) -> Optional[str]:
    trace = float(results.get("trace_stat", 0.0))
    cv = float(results.get("trace_cv_5pct", 0.0))
    if cv == 0.0:
        return None
    gap = abs(trace - cv) / cv
    if gap >= 0.10:
        return None
    sig = float(results.get("significance", 0.05))
    sig_pct = int(round(sig * 100))
    return (
        f"The trace statistic at the decision boundary ({trace:.2f}) is "
        f"within 10% of the {sig_pct}% critical value ({cv:.2f}). The "
        "cointegration rank verdict is marginal; re-examine under a "
        "different lag order or deterministic trend specification."
    )


def _trigger_near_unit_alpha(results: dict) -> Optional[str]:
    alpha = results.get("alpha_normalized")
    if not alpha:
        return None
    try:
        a = float(alpha[0][0])
    except (IndexError, TypeError, ValueError):
        return None
    if abs(1.0 + a) <= 0.99:
        return None
    abs_alpha = abs(a)
    return (
        f"The error-correction coefficient α₁=−{abs_alpha:.4f} is very "
        "close to zero, meaning the first series barely adjusts toward "
        "the long-run equilibrium. The cointegrating relationship may be "
        "weakly identified despite the rejection."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="vecm_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_fast_half_life,
        _trigger_slow_half_life,
        _trigger_borderline_trace,
        _trigger_near_unit_alpha,
    ),
    mode_aware=False,
)

register(SPEC)
