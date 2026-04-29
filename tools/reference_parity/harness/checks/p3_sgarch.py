"""Phase 3 Batch 2 — sGARCH (standard GARCH(1,1)) parity check.

Compares TSL ``garch_model.py`` (vol="GARCH" path; arch package
backbone) against R rugarch ``ugarchspec(model='sGARCH')``.
Both fit Gaussian-innovation MLE on the canonical GARCH(1,1)
specification:

    sigma2_t = omega + alpha * eps_{t-1}^2 + beta * sigma2_{t-1}

Per Session 5 generator pattern + Session 6 batch design,
business logic centralizes in ``_garch_helpers.py``; this
module is the thin per-variant entry point (~60 LOC).

Structural invariants (Session 5 registry, populated this
session):

- ``garch_conditional_variance``: sigma2_t > 0 for all t
- ``garch_persistence``: alpha + beta < 1 (variance-level
  persistence)
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


class SgarchParity(P3ParityCheck):
    """sGARCH(1,1) parity vs R rugarch."""

    technique_id = "p3_sgarch"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Python arch package and R rugarch are independent "
        "implementations of the De Livera GARCH-family MLE. "
        "Different optimizer initialization + convergence "
        "criteria produce 1e-3 to 1e-2 abs divergence on "
        "coefficients; well within the §7.1 MLE-fit band."
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
        return run_tsl_garch(fixture, variant="sGARCH")

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return run_reference_garch(fixture, variant="sGARCH")

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary, secondary, statuses = compare_garch(
            tsl, ref, ladder, variant="sGARCH",
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
