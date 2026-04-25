"""Reference-parity harness for the Time Series Lab.

Phase 2 of the retrospective correctness verification initiative.
Provides a tier-aware parity-check runner that compares TSL
wrapper outputs against external reference implementations
(R packages via subprocess, Python packages via direct import)
on seeded synthetic fixtures.

Public entry point: ``python -m reference_parity``. See the
contributor guide at
``docs/reference_parity_contributor_guide.md`` for how to add
new checks.

Phase 1 audit infrastructure (``fixtures/``, ``reports/``,
``scripts/``) coexists in this directory but is intentionally
untracked; the harness/ subdirectory is the Phase 2 deliverable.
"""

__all__ = []
