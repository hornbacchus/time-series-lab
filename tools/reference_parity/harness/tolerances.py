"""Tolerance ladders for the reference-parity harness.

Each entry in ``TOLERANCE_LADDERS`` is a per-technique
configuration consumed by the corresponding ``ParityCheck``
subclass. Centralising here keeps tolerance review surface
small (a single file to audit) and lets the harness itself
print the ladder when ``--check-environment`` runs.

Three ladder types:

- **absolute**: simple ``abs_tol`` / ``rel_tol`` floor for
  closed-form computations. Outcome PASS iff
  ``max_abs_diff <= abs_tol`` OR ``max_rel_diff <= rel_tol``;
  otherwise BLOCK.
- **three_outcome**: the B6 / B7 ladder. Two thresholds split
  the metric into PASS / CAVEAT / BLOCK bands; CAVEAT triggers
  a single re-roll with seed+1.
- **correlation**: Pearson-correlation-driven (B7-style).
  Two thresholds: ``corr_pass_threshold`` and
  ``corr_block_threshold``. Above pass → PASS; in between →
  CAVEAT; below block → BLOCK.

Each entry MUST include a ``justification`` field tying back
to a Phase 1 audit report under
``tools/reference_parity/reports/`` so future reviewers can
trace where the tolerance came from.
"""

from __future__ import annotations

from typing import Any


# Public mapping consumed by check modules. Keys are the
# ``technique_id`` attribute of the corresponding ParityCheck.
TOLERANCE_LADDERS: dict[str, dict[str, Any]] = {

    "_smoke_test": {
        "type": "absolute",
        "abs_tol": 1e-12,
        "rel_tol": 1e-12,
        "justification": (
            "Smoke test computes mean of 100 standard normals via "
            "R base mean() and numpy mean. Both paths use IEEE 754 "
            "double-precision floating point with identical input; "
            "result should agree to machine precision. 1e-12 leaves "
            "12 orders of magnitude of headroom for any future "
            "subprocess CSV roundtrip noise."
        ),
    },

    "3e_mint_family": {
        "type": "absolute",
        "abs_tol": 1e-8,
        "rel_tol": 1e-8,
        "lambda_abs_tol": 1e-4,
        "lambda_rel_tol": 1e-4,
        "justification": (
            "MinT reconciliation closed-form algebra: y_tilde = "
            "S (S' W^-1 S)^-1 S' W^-1 y_hat. Phase 1 audit 3e "
            "(reports/3e_mint_audit.md) measured TSL vs R hts "
            "max abs diff 4.66e-15 on mint_shrinkage, 4.44e-15 on "
            "ols and wls_variance. The 1e-8 floor leaves seven "
            "orders of magnitude of headroom for harness-level "
            "subprocess CSV roundtrip noise without sacrificing "
            "regression detection. Schaefer-Strimmer lambda is "
            "reported to 4 decimal places by hts (printed character "
            "vector); 1e-4 is the precision the reference exposes."
        ),
    },
}


def get_ladder(technique_id: str) -> dict[str, Any]:
    """Look up the tolerance ladder for a technique id.

    Raises
    ------
    KeyError
        If no ladder is registered for the given id. Adding a
        new ParityCheck without a corresponding ladder entry is
        a contributor-guide violation — fail loudly.
    """
    if technique_id not in TOLERANCE_LADDERS:
        raise KeyError(
            f"No tolerance ladder registered for technique_id "
            f"'{technique_id}'. Add an entry to "
            f"reference_parity/harness/tolerances.py with a "
            f"justification citing the Phase 1 audit report."
        )
    return TOLERANCE_LADDERS[technique_id]


__all__ = ["TOLERANCE_LADDERS", "get_ladder"]
