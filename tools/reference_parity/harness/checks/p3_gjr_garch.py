"""Phase 3 Batch 2 — GJR-GARCH(1,1,1) parity check.

Glosten-Jagannathan-Runkle GARCH variant: adds asymmetric
response to negative shocks via the gamma term:

    sigma2_t = omega + alpha * eps_{t-1}^2
                     + gamma * I(eps_{t-1} < 0) * eps_{t-1}^2
                     + beta * sigma2_{t-1}

Compares TSL ``garch_model.py`` (vol="GJR-GARCH" path) against
R ``rugarch::ugarchspec(model='gjrGARCH')``. Persistence
formula: ``alpha + beta + 0.5*gamma`` (the 0.5 weight reflects
that the asymmetric term applies only to negative shocks
~50% of the time under symmetric innovation distributions).
"""

from __future__ import annotations

from typing import Any

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
)
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks._garch_helpers import (
    compare_garch,
    generate_garch_dgp,
    run_reference_garch,
    run_tsl_garch,
)


class GjrGarchParity(P3ParityCheck):
    """GJR-GARCH(1,1,1) parity vs R rugarch."""

    technique_id = "p3_gjr_garch"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Python arch and R rugarch independent implementations "
        "of the GJR-GARCH MLE. Asymmetry term (gamma) adds an "
        "extra parameter to fit; convergence-criterion divergence "
        "1e-3 to 1e-2 abs expected. §7.1 MLE-fit band."
    )

    structural_invariants = (
        StructuralInvariant(
            name="conditional_variance_positivity",
            invariant_type="garch_conditional_variance",
            tolerance=0.0,
            tolerance_type="absolute",
        ),
        StructuralInvariant(
            name="persistence_below_one",
            invariant_type="garch_persistence",
            tolerance=1e-3,
            tolerance_type="relative",
        ),
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "y": generate_garch_dgp(seed=seed, n=1000),
            "horizon": 5,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return run_tsl_garch(fixture, variant="GJR-GARCH")

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return run_reference_garch(fixture, variant="GJR-GARCH")

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary, secondary, statuses = compare_garch(
            tsl, ref, ladder, variant="GJR-GARCH",
        )
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                "rugarch_version": ref.get("rugarch_version", "unknown"),
                "n_obs": len(tsl["conditional_variance"]),
                "wrapper_aic": tsl.get("wrapper_aic"),
            },
        )
