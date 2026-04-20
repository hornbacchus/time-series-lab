"""
InterpretationSpec for denton_chowlin_disaggregation.

Distinct from the two imputation specs in this family: temporal
disaggregation (expanding a low-frequency series to higher frequency
under an aggregate constraint). Tier 1 centers on constraint
satisfaction, not uncertainty.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_SIGNED,
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    method = str(results.get("method", "denton"))
    method_display = "Chow-Lin" if method.lower() == "chowlin" else "Denton"
    n_low = int(results.get("n_low", 0))
    n_high = int(results.get("n_high", 0))
    ratio = int(results.get("ratio", 1))
    indicator = results.get("indicator_name")
    max_disc = float(results.get("max_discrepancy", 0.0))
    indicator_clause = (
        f" with indicator {format_series_reference(str(indicator))}"
        if indicator else " (no indicator series)"
    )
    return (
        f"Disaggregated {format_series_reference(name)} from {n_low} "
        f"low-frequency periods to {n_high} high-frequency points "
        f"(ratio {ratio}:1) using {method_display}{indicator_clause}. "
        f"Aggregate constraint satisfied to within max discrepancy of "
        f"{FMT_COEF_UNSIGNED.format(max_disc)}. The disaggregated "
        f"series respects the low-frequency totals exactly at period "
        f"boundaries; use it for high-frequency analysis."
    )


def _tier2(results: dict) -> str:
    method = str(results.get("method", "denton")).lower()
    rho = results.get("rho")
    betas = list(results.get("betas") or [])
    if method == "chowlin":
        rho_clause = (
            f"AR(1) disturbance ρ={FMT_COEF_UNSIGNED.format(float(rho))}"
            if rho is not None else "AR(1) disturbance (ρ not reported)"
        )
        beta_clause = (
            "Indicator coefficients: " + ", ".join(
                f"β{i}={FMT_COEF_SIGNED.format(float(b))}"
                for i, b in enumerate(betas)
            ) + "."
            if betas else "No indicator coefficients reported."
        )
        return (
            f"Chow-Lin method with {rho_clause} and indicator "
            f"regression. {beta_clause} Denton would produce a "
            f"smoother but less informative disaggregation when a "
            f"relevant indicator is available; choose Chow-Lin when "
            f"the indicator carries meaningful high-frequency "
            f"variation and Denton when it does not."
        )
    # Denton
    return (
        "Denton method (proportional variant) respects the aggregate "
        "constraint via a proportional first-difference minimization "
        "— no indicator series required. Use Chow-Lin instead when a "
        "relevant high-frequency indicator series is available; it "
        "carries genuine within-period variation that Denton cannot "
        "recover."
    )


def _trigger_loose_constraint(results: dict) -> Optional[str]:
    max_disc = float(results.get("max_discrepancy", 0.0))
    if max_disc <= 0.01:
        return None
    return (
        f"Maximum aggregation discrepancy {FMT_COEF_UNSIGNED.format(max_disc)} "
        f"exceeds 0.01 — the aggregate constraint is only loosely "
        f"satisfied. Re-run with the Denton method or verify the "
        f"input frequency specification."
    )


def _trigger_chowlin_rho_edge(results: dict) -> Optional[str]:
    method = str(results.get("method", "")).lower()
    rho = results.get("rho")
    if method != "chowlin" or rho is None:
        return None
    rho_f = float(rho)
    if rho_f < 0.1 or rho_f > 0.95:
        return (
            f"Chow-Lin's AR(1) disturbance parameter "
            f"ρ={FMT_COEF_UNSIGNED.format(rho_f)} is near the boundary "
            f"of the admissible range. The AR(1) assumption may be "
            f"dubious; the indicator regression may be doing most of "
            f"the work. Validate by re-running with Denton and "
            f"comparing the disaggregated paths."
        )
    return None


SPEC = InterpretationSpec(
    technique_id="denton_chowlin_disaggregation",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_loose_constraint, _trigger_chowlin_rho_edge),
    mode_aware=False,
)

register(SPEC)
