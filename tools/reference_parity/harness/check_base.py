"""Extended ParityCheck base for Phase 3 Session 5.

Additions over ``harness/base.py:ParityCheck`` (which remains
in place for backward-compat with pre-Phase-3 checks):

- **Mandatory class attributes** (Session 5 lock):
    - ``verdict_class : str`` — one of the registered class
      names (``closed_form`` / ``mle_fit`` / ``state_space_reform``
      / ``iterative_loess`` / ``mcmc`` / ``em_stochastic`` /
      ``dl_seed_pinned`` / ``bootstrap_distributional`` /
      ``conformal_coverage``).
    - ``verdict_class_rationale : str`` — free-form string
      documenting why this class is correct for the wrapper.
- **Default-flipped attributes** (Session 5 lock):
    - ``reroll_on_caveat : bool = False`` — default-flipped
      from base.py's True. Deterministic checks
      (which is most checks per Session 4 finding) get the
      false default; MC / EM-stochastic checks override to
      True. Replaces the per-check
      ``def on_caveat_reroll(self, ...): return False`` that
      Batch 1 established as a discipline pattern.
- **Optional attributes** (Session 5 lock):
    - ``reference_isolate : bool = False`` — Batch 9 DL
      checks set True for subprocess isolation via
      ``PyBridge`` (see ``harness/py_invoke.py``).
    - ``structural_invariants : tuple = ()`` — declarative
      Pattern F invariants (see
      ``harness/structural_invariants.py``).
- **Behavior**: ``__init_subclass__`` enforces
  ``verdict_class`` + ``verdict_class_rationale`` at class-
  definition time; missing attributes raise TypeError.

The base class still implements the same 4-method ABC
contract (``setup_fixture`` / ``run_tsl`` / ``run_reference``
/ ``compare``); subclasses don't need lifecycle methods
beyond those four. The ``on_caveat_reroll`` method is
provided here as a default returning ``self.reroll_on_caveat``
so subclasses opt-in via class attribute rather than method
override.
"""

from __future__ import annotations

import abc
from typing import Any, Literal

from reference_parity.harness.base import ParityCheck as _BaseParityCheck
from reference_parity.harness.base import ParityResult, Tier  # noqa: F401 — re-export


VerdictClass = Literal[
    "closed_form",
    "mle_fit",
    "single_impl_mle",
    "state_space_reform",
    "iterative_loess",
    "mcmc",
    "em_stochastic",
    "dl_seed_pinned",
    "bootstrap_distributional",
    "conformal_coverage",
]


# Frozen set for fast lookup + future-extension safety.
#
# Phase 3.5 Session 3 (Item 1): added ``single_impl_mle`` between
# ``closed_form`` and ``mle_fit``. Use for wrappers where:
# - The TSL backend and reference reduce to the same closed-form
#   linear-algebra solve (e.g., reduced-rank regression that
#   collapses to OLS on the cointegration vectors), and
# - Achieved tolerance demonstrates >=3 orders of magnitude
#   headroom inside the canonical mle_fit band (1e-3 abs / 1e-2
#   rel).
# Band: 1e-5 abs / 1e-4 rel (per master plan §4 Item 1 spec;
# 1.5x achieved-tolerance margin per §4 risk 4 mitigation).
_REGISTERED_VERDICT_CLASSES = frozenset({
    "closed_form",
    "mle_fit",
    "single_impl_mle",
    "state_space_reform",
    "iterative_loess",
    "mcmc",
    "em_stochastic",
    "dl_seed_pinned",
    "bootstrap_distributional",
    "conformal_coverage",
})


class P3ParityCheck(_BaseParityCheck):
    """Phase 3 ``ParityCheck`` extension with Session 5
    locked attributes.

    Subclasses MUST set:
        verdict_class : VerdictClass
            One of ``_REGISTERED_VERDICT_CLASSES``.
        verdict_class_rationale : str
            Why this class is correct for the wrapper.
        + the inherited ``technique_id``, ``tier``,
          ``fixture_id`` attributes (per ``base.ParityCheck``).

    Subclasses MAY override:
        reroll_on_caveat : bool = False
            Default flipped from base True; deterministic
            checks keep False, MC checks set True.
        reference_isolate : bool = False
            Batch 9 DL checks set True for subprocess
            isolation via ``PyBridge``.
        structural_invariants : tuple[StructuralInvariant, ...]
            Pattern F invariant declarations (default empty).

    The ABC's 4-method contract (``setup_fixture`` /
    ``run_tsl`` / ``run_reference`` / ``compare``) remains
    unchanged.
    """

    # Sentinel: None means "must be set by subclass". Enforced
    # by ``__init_subclass__``.
    verdict_class: VerdictClass | None = None  # type: ignore[assignment]
    verdict_class_rationale: str | None = None  # type: ignore[assignment]

    # Default-flipped from base True (Session 5 lock).
    reroll_on_caveat: bool = False

    # Phase 3 Session 5 additions for PyBridge + structural invariants.
    reference_isolate: bool = False
    structural_invariants: tuple = ()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Allow intermediate abstract classes to skip enforcement
        # (concrete checks have non-empty technique_id; abstracts
        # leave it as ""). Match base ParityCheck convention.
        if not getattr(cls, "technique_id", ""):
            return
        vc = getattr(cls, "verdict_class", None)
        if vc is None:
            raise TypeError(
                f"{cls.__name__} must define class attribute "
                f"verdict_class (one of "
                f"{sorted(_REGISTERED_VERDICT_CLASSES)})."
            )
        if vc not in _REGISTERED_VERDICT_CLASSES:
            raise TypeError(
                f"{cls.__name__}.verdict_class={vc!r} is not "
                f"registered. Permitted: "
                f"{sorted(_REGISTERED_VERDICT_CLASSES)}."
            )
        rationale = getattr(cls, "verdict_class_rationale", None)
        if not isinstance(rationale, str) or not rationale.strip():
            raise TypeError(
                f"{cls.__name__} must define non-empty class "
                f"attribute verdict_class_rationale (string)."
            )

    def on_caveat_reroll(
        self, first_result: ParityResult,
    ) -> bool:
        """Default implementation reads the
        ``reroll_on_caveat`` class attribute. Subclasses
        rarely need to override; they set the attribute
        instead. Backward-compat: the base ``ParityCheck``
        still allows method override.
        """
        return bool(self.reroll_on_caveat)

    # Per-invariant-type required-field map. Used by
    # `check_invariants` defensive layer (Q-Allowlist-3=(c)) to
    # verify TSL output exposes the fields a checker requires
    # before dispatching. If required fields missing, return
    # INFO outcome (not BLOCK) so wrappers in allowlist whose
    # output structure shifts don't silently break the runner;
    # missing-fields cases surface in audit trail without
    # masquerading as invariant violations. Phase 5 S2-α-1-redux
    # baseline; extended per per-wrapper allowlist additions.
    # Phase 5 S2-α-2-redux extension: vecm_cointegration_rank
    # added (TSL-side field; ref-side check delegated to checker
    # internal logic since defensive layer only sees TSL side).
    _INVARIANT_REQUIRED_FIELDS: dict[str, tuple] = {
        "kalman_covariance_ordering": (
            "filtered_state_cov", "predicted_state_cov",
        ),
        "vecm_cointegration_rank": (
            "cointegrating_rank",
        ),
        "evt_extremal_index": (
            "theta",
        ),
    }

    def check_invariants(
        self,
        tsl_output: dict[str, Any],
        ref_output: dict[str, Any] | None = None,
        fixture: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Phase 5 S2-α-1-redux (extended at S2-α-2-redux) —
        dispatch declared ``structural_invariants`` against
        ``tsl_output`` (+ optional ``ref_output`` + ``fixture``
        for invariants that need reference-side comparison
        e.g. ``vecm_cointegration_rank``).

        Per-wrapper allowlist gating happens in
        ``runner.py:run_check`` step 4.5 (only allowlist
        wrappers reach this method); this method handles
        per-invariant defensive field check + dispatch.

        Defensive layer (Q-Allowlist-3=(c)): for each declared
        invariant, verify the required fields per
        ``_INVARIANT_REQUIRED_FIELDS`` are present + non-None
        in ``tsl_output``. If missing, emit INFO outcome with
        diagnostic message identifying the missing fields. If
        present, dispatch the registered checker per
        ``structural_invariants.get_invariant_checker``.

        Backward-compat: ``ref_output`` + ``fixture`` are
        optional with empty-dict defaults. S2-α-1-redux test
        calling with single arg continues to work; S2-α-2-redux
        adds ref-side support for multi-side invariants.

        Returns aggregated invariant outcomes dict:
        ``{name: {status, details, ...}}`` — one entry per
        declared invariant (regardless of dispatch / skip /
        INFO disposition).
        """
        from reference_parity.harness.structural_invariants import (
            get_invariant_checker,
        )
        ref_output = ref_output if ref_output is not None else {}
        fixture = fixture if fixture is not None else {}
        results: dict[str, Any] = {}
        for inv in self.structural_invariants:
            if not inv.enabled:
                continue
            req = self._INVARIANT_REQUIRED_FIELDS.get(
                inv.invariant_type, (),
            )
            missing = [
                f for f in req
                if tsl_output.get(f) is None
            ]
            if missing:
                results[inv.name] = {
                    "name": inv.name,
                    "invariant_type": inv.invariant_type,
                    "status": "INFO",
                    "details": (
                        f"required fields missing from TSL "
                        f"output: {missing}; dispatch skipped"
                    ),
                }
                continue
            checker = get_invariant_checker(inv.invariant_type)
            results[inv.name] = checker(
                tsl_output, ref_output, fixture, inv,
            )
        return results


__all__ = [
    "P3ParityCheck",
    "VerdictClass",
    "_REGISTERED_VERDICT_CLASSES",
]
