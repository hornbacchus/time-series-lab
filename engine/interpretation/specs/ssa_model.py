"""
InterpretationSpec for ssa_model (Singular Spectrum Analysis).

Class 4 (component decomposition). Labels are ordinal (Group 0,
Group 1, ...) per Decision 3 — wrapper does not attempt semantic
classification; Tier 2 honestly discloses that semantic identity
requires eigenvector inspection.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _concentration_band(pct):
    """Reuse power-concentration band for SSA group-variance shares."""
    if pct is None:
        return "unknown"
    s = float(pct)
    if s < 10.0:
        return "weak"
    if s < 30.0:
        return "moderate"
    if s < 60.0:
        return "strong"
    return "dominant"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    L = int(results.get("window_length", 0))
    n_components = int(results.get("n_components", 0))
    n_groups = int(results.get("n_groups", 0))
    dom_group_share = results.get("dominant_group_share")
    second_group_share = results.get("second_group_share")
    components_for_95pct = results.get("components_for_95pct")
    components_for_99pct = results.get("components_for_99pct")

    band = _concentration_band(dom_group_share)
    dom_str = (
        f"{float(dom_group_share):.1f}" if dom_group_share is not None
        else "(not reported)"
    )
    second_clause = ""
    if second_group_share is not None and float(second_group_share) >= 0.5:
        second_clause = (
            f"; Group 2 (paired eigentriples) carries an additional "
            f"{float(second_group_share):.1f}%"
        )

    reconstruction_clause = ""
    if components_for_99pct is not None and components_for_95pct is not None:
        reconstruction_clause = (
            f" {int(components_for_99pct)} components together reconstruct "
            f"99% of the series' eigenvalue variance; only "
            f"{int(components_for_95pct)} is needed for 95%."
        )

    return (
        f"SSA decomposition of {format_series_reference(name)} ({n} "
        f"observations) with window L={L}. The trajectory-matrix SVD "
        f"produces {n_components} singular components grouped into "
        f"{n_groups} reconstructed components by w-correlation. Group 1 "
        f"(eigentriple 0) carries {dom_str}% of total reconstructed "
        f"variance ({band} concentration){second_clause}."
        f"{reconstruction_clause}"
    )


def _tier2(results: dict) -> str:
    n = int(results.get("n_obs", 0))
    L = int(results.get("window_length", 0))
    K = max(1, n - L + 1)
    n_components = int(results.get("n_components", 0))
    n_groups = int(results.get("n_groups", 0))
    explained_variance_pct_1 = results.get("explained_variance_pct_1")

    eig_share_str = (
        f"{float(explained_variance_pct_1):.1f}" if explained_variance_pct_1 is not None
        else "(not reported)"
    )
    return (
        f"Singular Spectrum Analysis via SVD of the trajectory matrix "
        f"(window length L={L}, embedding dimension K={K}). The "
        f"{n_components} retained singular components are grouped into "
        f"{n_groups} reconstructed components using the w-correlation "
        f"heuristic (threshold 0.5). The first eigenvalue alone captures "
        f"{eig_share_str}% of the eigenvalue variance. Component labels "
        f"are ordinal (Group 0, Group 1, ...) by variance contribution; "
        f"semantic identity requires eigenvector inspection. Typical "
        f"patterns: the first group usually captures level/trend; "
        f"lower-variance groups may carry periodic components whose "
        f"periods can be estimated from the eigenvector's spectrum. "
        f"This wrapper does not automatically classify components by "
        f"type — downstream semantic labeling is the user's "
        f"responsibility. For seasonal series, visual inspection of the "
        f"Group 2 eigenvectors is recommended to confirm periodic "
        f"structure."
    )


def _trigger_single_component_dominates(results: dict) -> Optional[str]:
    ev_pct_1 = results.get("explained_variance_pct_1")
    dom_group_share = results.get("dominant_group_share")
    L = results.get("window_length")
    n = results.get("n_obs")
    if ev_pct_1 is None or float(ev_pct_1) < 95.0:
        return None
    share_str = (
        f"{float(dom_group_share):.1f}" if dom_group_share is not None
        else "(not reported)"
    )
    recommend_L_clause = ""
    if L is not None and n is not None and int(L) > int(n) / 4:
        new_L = max(10, int(n) // 4)
        recommend_L_clause = (
            f" Window length L={int(L)} may be too large for this short "
            f"series (n={int(n)}) — reducing L to n/4 ≈ {new_L} may "
            f"expose secondary structure."
        )
    return (
        f"Group 1 carries {share_str}% of total reconstructed variance "
        f"and the first eigenvalue alone captures {float(ev_pct_1):.1f}% "
        f"of singular-value variance. The series is effectively single-"
        f"component in the SVD basis; consider whether SSA adds value "
        f"over a simple polynomial or spline detrend at this data "
        f"shape.{recommend_L_clause}"
    )


def _trigger_few_99pct_components(results: dict) -> Optional[str]:
    k99 = results.get("components_for_99pct")
    if k99 is None or int(k99) >= 5:
        return None
    return (
        f"Only {int(k99)} components needed to reconstruct 99% of "
        f"variance; the decomposition is numerically low-rank. "
        f"Components beyond the first few are at noise scale; treat as "
        f"numerical residual rather than signal."
    )


SPEC = InterpretationSpec(
    technique_id="ssa_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_single_component_dominates,
        _trigger_few_99pct_components,
    ),
    mode_aware=False,
)

register(SPEC)
