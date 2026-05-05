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


__all__ = [
    "P3ParityCheck",
    "VerdictClass",
    "_REGISTERED_VERDICT_CLASSES",
]
