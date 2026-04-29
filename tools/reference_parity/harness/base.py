"""Base types for the reference-parity harness.

Defines:
- ``Outcome`` literal union (PASS / CAVEAT / DOCUMENTED-DIVERGENCE
  / BLOCK / ERROR / SKIP)
- ``Tier`` literal union (fast / slow)
- ``ParityResult`` dataclass — the per-check return shape
- ``ParityCheck`` abstract base class — the contract every
  per-technique check implements

The runner discovers ``ParityCheck`` subclasses, calls their
``setup_fixture`` / ``run_tsl`` / ``run_reference`` / ``compare``
methods in sequence, and packages the result.

**Phase 3.5 Session 1 (Item 7):** ``DOCUMENTED-DIVERGENCE``
added as a runtime outcome distinct from ``CAVEAT``. Per
P-1 §2.1, DD means "output does not match reference; divergence
is methodology-equivalent (different optimizer / prior / scale
/ parameterization), not a bug." Empirically not encountered
in Phase 3 (CAVEAT absorbed all such cases); reserved here for
first-instance use in post-Phase-3 work. Maps to CI green per
CAVEAT precedent (exit code 4 → 0 in workflow YAML).
"""

from __future__ import annotations

import abc
import dataclasses
from typing import Any, Literal


Outcome = Literal[
    "PASS",
    "CAVEAT",
    "DOCUMENTED-DIVERGENCE",
    "BLOCK",
    "ERROR",
    "SKIP",
]
Tier = Literal["fast", "slow"]


# Canonical priority order for combining outcomes across multiple
# checks (e.g., when a tier sweep contains many checks). The runner
# uses these to derive the overall exit code.
#
# PASS ranks above SKIP so a mixed run with at least one passing
# check aggregates to PASS (the harness produced positive signal).
# Both still map to exit code 0 in ``_exit_code_for`` — the
# distinction matters only for the human-readable summary.
#
# DOCUMENTED-DIVERGENCE ranks between CAVEAT and ERROR — it's a
# stronger signal than CAVEAT (the divergence is documented as
# real, not "matches except in stated regime") but still maps to
# CI green (no bug; methodology-equivalent). Phase 3.5 Session 1
# Item 7: DD is forward-provisioned here; no current wrapper
# triggers it.
_OUTCOME_PRIORITY: dict[Outcome, int] = {
    "SKIP": 0,
    "PASS": 1,
    "CAVEAT": 2,
    "DOCUMENTED-DIVERGENCE": 3,
    "ERROR": 4,
    "BLOCK": 5,
}


def aggregate_outcomes(outcomes: list[Outcome]) -> Outcome:
    """Combine many outcomes into a single overall outcome.

    Returns the worst outcome encountered. Empty input → PASS
    (vacuously true; no checks failed because none ran).
    Priority (worst → best):
    BLOCK > ERROR > DOCUMENTED-DIVERGENCE > CAVEAT > PASS > SKIP.
    """
    if not outcomes:
        return "PASS"
    worst = max(outcomes, key=lambda o: _OUTCOME_PRIORITY.get(o, 0))
    return worst


@dataclasses.dataclass
class ParityResult:
    """The contract every parity check returns.

    Attributes
    ----------
    technique_id : str
        Stable identifier (matches the check class's
        ``technique_id`` attribute and the ``--technique`` CLI
        argument).
    outcome : Outcome
        PASS / CAVEAT / BLOCK / ERROR / SKIP per the harness's
        outcome ladder.
    metrics : dict
        Numerical metrics the check measured (max abs diff,
        Pearson correlation, RMS, etc.). Schema is per-check.
    diagnostics : dict
        Supplementary metrics (reported, not asserted) and
        per-method breakdowns. Schema is per-check.
    reference_versions : dict
        Snapshot of the reference packages actually used at
        runtime — populated by the runner from ``r_bridge.check_environment``
        (R) and importlib.metadata (Python).
    fixture_sha : str
        SHA-256 hash of the fixture file consumed (or "" if the
        check generates its fixture at runtime).
    duration_sec : float
        Wall-clock seconds for the entire check (setup + tsl +
        reference + compare).
    seed_used : int
        The seed actually used. CAVEAT re-roll bumps this by 1.
    error : str
        Formatted exception message when outcome == "ERROR";
        empty otherwise.
    """

    technique_id: str
    outcome: Outcome
    metrics: dict[str, Any] = dataclasses.field(default_factory=dict)
    diagnostics: dict[str, Any] = dataclasses.field(default_factory=dict)
    reference_versions: dict[str, str] = dataclasses.field(default_factory=dict)
    fixture_sha: str = ""
    duration_sec: float = 0.0
    seed_used: int = 0
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        """JSON-serialisable representation. Numpy types coerced
        to Python builtins by callers if needed."""
        return dataclasses.asdict(self)


class ParityCheck(abc.ABC):
    """Abstract base class for per-technique parity checks.

    Subclasses MUST set:
        technique_id : str
            Used by ``--technique`` CLI flag and the check
            registry.
        tier : Tier
            "fast" (CI-runnable in minutes) or "slow" (nightly /
            on-demand only).
        fixture_id : str
            Stem of the on-disk fixture file (without
            extension). Empty string means generated at runtime
            with no on-disk hash to verify.

    Subclasses MUST override:
        setup_fixture(seed: int) -> dict
            Load (or generate) the fixture data.
        run_tsl(fixture: dict) -> dict
            Run the TSL wrapper, return canonical numeric outputs.
        run_reference(fixture: dict) -> dict
            Run the external reference implementation.
        compare(tsl: dict, ref: dict) -> ParityResult
            Apply the per-check tolerance ladder and produce a
            partially-populated ParityResult (the runner fills in
            ``duration_sec``, ``seed_used``, ``reference_versions``,
            ``fixture_sha`` afterward).

    Subclasses MAY override:
        on_caveat_reroll(...) -> bool
            Hook for the runner to decide whether to attempt the
            re-roll. Default: True for all CAVEAT outcomes.
    """

    technique_id: str = ""
    tier: Tier = "fast"
    fixture_id: str = ""

    @abc.abstractmethod
    def setup_fixture(self, seed: int) -> dict[str, Any]:
        """Load or generate the fixture data.

        Returns a dict the check's other methods consume. Runner
        will hash on-disk fixtures (when ``fixture_id`` is
        non-empty) before invoking this — if the file's SHA
        diverges from the recorded ``.sha256`` sidecar, the runner
        raises ``FixtureHashMismatchError`` BEFORE this method is
        called.
        """

    @abc.abstractmethod
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke the TSL wrapper and return canonical numeric
        outputs (per-check schema)."""

    @abc.abstractmethod
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke the external reference implementation. May raise
        ``RNotAvailableError`` / ``ImportError`` etc.; the runner
        translates these to SKIP outcome."""

    @abc.abstractmethod
    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        """Apply the tolerance ladder. Runner fills in
        ``duration_sec``, ``seed_used``, ``reference_versions``,
        ``fixture_sha`` after this returns; this method only sets
        ``technique_id``, ``outcome``, ``metrics``, ``diagnostics``,
        and (on ERROR) ``error``."""

    def on_caveat_reroll(self, first_result: ParityResult) -> bool:
        """Should the runner re-roll on CAVEAT? Default True.
        Override to disable for checks where re-roll doesn't make
        sense (e.g., deterministic computations where CAVEAT
        means a real divergence, not MC noise)."""
        return True


__all__ = [
    "Outcome",
    "Tier",
    "ParityResult",
    "ParityCheck",
    "aggregate_outcomes",
]
