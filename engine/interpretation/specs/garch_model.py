"""
InterpretationSpec for garch_model.

GARCH is descriptive (no hypothesis-test verdict), so the Tier 1
actionable is persistence-keyed: high α+β suggests short-horizon
forecasts are well-supported but long-horizon converge slowly; low
α+β suggests the series resembles iid returns.

Results-dict keys consumed:

    series_name       : str
    n_obs             : int
    dist              : str ("Normal" / "Student-t" / ...)
    order_p / order_q : int
    alpha             : float (ARCH coefficient sum if multiple)
    beta              : float (GARCH coefficient sum)
    persistence       : float (alpha + beta; wrapper already computes)
    ljung_box_sq_p    : float (Ljung-Box on squared standardized resids)
    asymmetry         : float or None (GJR γ, if present)
"""

import math
from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_stat_technical,
    FMT_PERSISTENCE,
    FMT_COEF_UNSIGNED,
    FMT_P_VALUE,
    FMT_HALF_LIFE,
)
from interpretation.registry import register

# Preset-gated input-dict keys (T11 invariant). Empty tuple means no
# input keys are conditioned on the preset; Tier 1 has no preset-
# dependent assertions to guard.
PRESET_GATED_KEYS = ()


def _half_life(persistence: float) -> Optional[float]:
    """Derive shock half-life from persistence. Returns None when the
    formula is undefined (persistence >= 1 or <= 0)."""
    try:
        p = float(persistence)
    except (TypeError, ValueError):
        return None
    if not (0.0 < p < 1.0):
        return None
    try:
        return math.log(0.5) / math.log(p)
    except (ValueError, ZeroDivisionError):
        return None


def _persistence_descriptor(persistence: float) -> str:
    """Map α+β to a plain-English adjective band.

    Bands (persistence lies in [0, 1]):
        < 0.30       : low
        0.30 – 0.70  : moderate
        0.70 – 0.90  : high
        >= 0.90      : high (same word — phrasing adds "very" via the
                       near-IGARCH trigger if α+β > 0.98)
    """
    p = float(persistence)
    if p < 0.30:
        return "low"
    if p < 0.70:
        return "moderate"
    return "high"


# ---------------------------------------------------------------------
# Tier 1
# ---------------------------------------------------------------------

def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "The series"))
    persistence = float(results.get("persistence", 0.0))
    band = _persistence_descriptor(persistence)
    hl = _half_life(persistence)

    persistence_str = FMT_PERSISTENCE.format(persistence)
    # Note: α+β allowed in Tier 1 in citation form per T4 update.
    opener = (
        f"'{name}' show {band} conditional-volatility persistence: "
        f"α+β={persistence_str} implies a shock half-life of about "
        f"{FMT_HALF_LIFE.format(hl) if hl is not None else '∞'} "
        f"{'days' if hl is None or hl >= 1 else 'day'}."
    )

    if band == "high":
        return (
            f"{opener} The GARCH fit is suitable for short-horizon "
            "volatility forecasts (≤5 days). Long-horizon forecasts "
            "converge only gradually to the unconditional variance, so "
            "prediction intervals widen appreciably past two weeks."
        )
    if band == "moderate":
        return (
            f"{opener} The GARCH fit supports short-to-medium horizon "
            "volatility forecasts, and long-horizon forecasts converge "
            "to the unconditional variance within a reasonable window."
        )
    # low
    return (
        f"{opener} The series is well-suited for short-horizon volatility "
        "forecasting, and long-horizon forecasts converge quickly to the "
        "unconditional variance. Treat any calm stretches in the history "
        "as the stable attractor rather than as transient."
    )


# ---------------------------------------------------------------------
# Tier 2
# ---------------------------------------------------------------------

def _tier2(results: dict) -> str:
    name = str(results.get("series_name", "The series"))
    dist = str(results.get("dist", "Normal"))
    p_order = int(results.get("order_p", 1))
    q_order = int(results.get("order_q", 1))
    alpha = float(results.get("alpha", 0.0))
    beta = float(results.get("beta", 0.0))
    persistence = float(results.get("persistence", alpha + beta))
    hl = _half_life(persistence)
    lb_p = results.get("ljung_box_sq_p")

    header = (
        f"GARCH({p_order},{q_order}) with {dist} innovations fit to "
        f"'{name}'."
    )
    # Coefficient citation: α and β with their descriptive gloss.
    coef_sentence = (
        f"ARCH α={FMT_COEF_UNSIGNED.format(alpha)} (recent-shock response) "
        f"and GARCH β={FMT_COEF_UNSIGNED.format(beta)} (volatility memory) "
        f"sum to a persistence of {FMT_PERSISTENCE.format(persistence)}"
    )
    if hl is not None:
        coef_sentence += (
            f", giving a half-life of ln(0.5)/ln({FMT_PERSISTENCE.format(persistence)}) "
            f"≈ {FMT_HALF_LIFE.format(hl)} trading days."
        )
    else:
        coef_sentence += (
            ", which sits at or above the IGARCH boundary and does not "
            "admit a finite half-life."
        )

    if lb_p is None:
        lb_sentence = (
            "Ljung-Box on squared standardized residuals was not reported "
            "for this run."
        )
    else:
        lb_p_f = float(lb_p)
        if lb_p_f < 0.05:
            lb_sentence = (
                f"Ljung-Box on squared standardized residuals rejects the "
                f"no-remaining-ARCH null (p={FMT_P_VALUE.format(lb_p_f)}); "
                "residual variance structure persists, and the "
                "specification may be under-parameterized."
            )
        else:
            lb_sentence = (
                f"Ljung-Box on squared standardized residuals does not "
                f"reject the no-remaining-ARCH null "
                f"(p={FMT_P_VALUE.format(lb_p_f)}), so model adequacy is "
                "acceptable."
            )

    return f"{header} {coef_sentence} {lb_sentence}"


# ---------------------------------------------------------------------
# Tier 3 triggers
# ---------------------------------------------------------------------

def _trigger_near_igarch(results: dict) -> Optional[str]:
    persistence = float(results.get("persistence", 0.0))
    if persistence <= 0.98:
        return None
    return (
        f"Persistence α+β={FMT_PERSISTENCE.format(persistence)} is very "
        "close to the IGARCH boundary of 1.0. Volatility shocks "
        "effectively do not decay in finite time; the unconditional-"
        "variance approximation breaks down and long-horizon forecasts "
        "should not rely on convergence to it."
    )


def _trigger_lb_sq_rejects(results: dict) -> Optional[str]:
    lb_p = results.get("ljung_box_sq_p")
    if lb_p is None or float(lb_p) >= 0.05:
        return None
    return (
        f"Ljung-Box on squared standardized residuals rejects the "
        f"no-remaining-ARCH null at the 5% level "
        f"({FMT_P_VALUE.format(float(lb_p))}). The GARCH specification "
        "is under-parameterized; consider GARCH(2,1), GJR-GARCH for "
        "asymmetry, or a Student-t distribution for the innovations."
    )


def _trigger_very_low_persistence(results: dict) -> Optional[str]:
    persistence = float(results.get("persistence", 0.0))
    if persistence >= 0.30:
        return None
    return (
        f"Persistence α+β={FMT_PERSISTENCE.format(persistence)} is "
        "unusually low for a financial time series. Either the series "
        "is closer to iid than typical returns, or the model is "
        "under-fit — verify residual-diagnostic tables for signs of "
        "remaining structure."
    )


# ---------------------------------------------------------------------
# Register
# ---------------------------------------------------------------------

SPEC = InterpretationSpec(
    technique_id="garch_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_near_igarch,
        _trigger_lb_sq_rejects,
        _trigger_very_low_persistence,
    ),
    mode_aware=False,
)

register(SPEC)
