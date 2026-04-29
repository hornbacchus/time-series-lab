"""Phase 3 Batch 2 — EGARCH(1,1,1) parity check.

Nelson Exponential GARCH variant: parameterizes log-variance
(not variance) and uses an asymmetric news-impact function:

    log(sigma2_t) = omega + alpha*(|z_{t-1}| - E|z|)
                          + gamma * z_{t-1}
                          + beta * log(sigma2_{t-1})

Compares TSL ``garch_model.py`` (vol="EGARCH" path; arch
package backbone) against R ``rugarch::ugarchspec(model='eGARCH')``.

**Documented divergence (Pattern surfaced this session):**
arch package and rugarch use **swapped naming conventions** for
the alpha and gamma roles in EGARCH. arch's "alpha" is the
magnitude-of-shock coefficient (multiplying ``|z| - E|z|``);
rugarch's "alpha" is the leverage / sign-of-shock coefficient.
``_garch_helpers.run_reference_garch`` swaps the names on the
rugarch side so the per-coef comparison aligns by economic role
rather than by raw name.

Persistence formula for EGARCH: ``|beta|`` (log-variance AR
coefficient; the standard alpha+beta formula is GARCH-family-
specific to variance-level dynamics). Per CAI Phase 2 Session 6
fix F-G-T2-EGARCH-PERSIST.
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


class EgarchParity(P3ParityCheck):
    """EGARCH(1,1,1) parity vs R rugarch with documented
    parameter-name swap."""

    technique_id = "p3_egarch"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Python arch and R rugarch EGARCH MLE; well-documented "
        "alpha/gamma name swap (arch: alpha=magnitude, "
        "gamma=leverage; rugarch: alpha=leverage, gamma=magnitude). "
        "Helper aligns by economic role. EGARCH log-variance "
        "parameterization tends to amplify optimizer divergence "
        "relative to sGARCH/GJR; tolerance class still mle_fit "
        "but at the looser end of the band. §7.1."
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
        return run_tsl_garch(fixture, variant="EGARCH")

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return run_reference_garch(fixture, variant="EGARCH")

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary, secondary, statuses = compare_garch(
            tsl, ref, ladder, variant="EGARCH",
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
                "param_name_swap_applied": True,
            },
        )

    # EGARCH may produce CAVEAT due to log-variance optimizer
    # divergence; per Session 5 default reroll_on_caveat=False
    # is correct (deterministic computation; reroll won't help).
