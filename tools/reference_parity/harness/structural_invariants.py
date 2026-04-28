"""Structural-invariants registry stub for Phase 3.

Phase 3 Session 5 abstraction: enumerates the 9 wrapper
classes that have natural structural invariants suitable for
**Pattern F** (structural-identity diagnostic separate from
per-component parity, established in Session 4 via
`p3_mstl.py`'s `recon_cross_max_abs_diff` diagnostic).

Per-batch population discipline:

- Session 5 (this commit): registry stubbed; all 9 invariant
  types are registered with ``NotImplementedError("populate at
  Batch <N>")`` placeholders. The registry dispatch path is
  exercised via the unit test in
  ``_test_structural_invariants.py``.
- Batch 2 (Session 6): populates ``garch_persistence`` and
  ``garch_conditional_variance``.
- Subsequent batches populate their wrapper-class invariants
  as wrappers land. P-2 (`docs/engineering/
  parity_diagnostic_reference.md`, Session 25) documents the
  populated invariants.

Per user-locked refinement 2 (Session 5 plan): NO live audit
declares structural_invariants this session. p3_mstl
declaration deferred to Batch 7 when wavelet/FFT class
invariants populate. The registry dispatch is validated via
unit test, not live-audit dispatch.

Per-check declaration pattern (Python attribute, not TOML):

    class FutureGarchModelParity(ParityCheck):
        structural_invariants = (
            StructuralInvariant(
                name="conditional_variance_positivity",
                invariant_type="garch_conditional_variance",
                tolerance=0.0,
                tolerance_type="absolute",
            ),
        )
"""

from __future__ import annotations

import dataclasses
from typing import Any, Callable, Literal


ToleranceType = Literal["absolute", "relative", "probabilistic"]


@dataclasses.dataclass(frozen=True)
class StructuralInvariant:
    """Declarative invariant attached to a ParityCheck class.

    The harness's `check_invariants` lifecycle method (see
    `harness/check_base.py`) iterates through each
    ``structural_invariants`` entry on a check, looks up the
    registered checker via ``invariant_type``, and dispatches.

    Attributes
    ----------
    name : str
        Human-readable identifier for the invariant
        (per-wrapper unique). Used in audit reports.
    invariant_type : str
        Key into the ``_REGISTRY`` dict mapping to a checker
        callable.
    tolerance : float
        Numeric tolerance for the invariant's residual.
        Interpretation depends on ``tolerance_type``.
    tolerance_type : ToleranceType
        ``absolute`` → residual ≤ tolerance.
        ``relative`` → residual / scale ≤ tolerance.
        ``probabilistic`` → residual within Clopper-Pearson
        / sqrt(Var/B) confidence band.
    enabled : bool
        Default True; allows per-fixture disabling without
        deleting the declaration.
    """

    name: str
    invariant_type: str
    tolerance: float
    tolerance_type: ToleranceType = "absolute"
    enabled: bool = True


# Checker callable contract (informal): given (tsl_outputs,
# ref_outputs, fixture, invariant) → dict with PASS / CAVEAT /
# BLOCK status + measured residual + diagnostic context.
InvariantChecker = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any], StructuralInvariant],
    dict[str, Any],
]


# Per-batch populated registry. Session 5 stubs all 9 wrapper
# classes with ``NotImplementedError`` raisers; subsequent
# batches replace with concrete implementations as wrappers
# land. Lookup happens via ``register_invariant`` /
# ``get_invariant_checker``.
_REGISTRY: dict[str, InvariantChecker] = {}


def register_invariant(invariant_type: str) -> Callable[[InvariantChecker], InvariantChecker]:
    """Decorator to register a checker for an invariant type.

    Usage (in a future batch session):

        @register_invariant("garch_persistence")
        def _check_garch_persistence(tsl, ref, fixture, inv):
            alpha = float(tsl["alpha"])
            beta = float(tsl["beta"])
            persistence = alpha + beta
            ...
    """
    def _decorator(fn: InvariantChecker) -> InvariantChecker:
        _REGISTRY[invariant_type] = fn
        return fn
    return _decorator


def get_invariant_checker(invariant_type: str) -> InvariantChecker:
    """Look up the checker for a registered invariant type.

    Raises
    ------
    KeyError
        If no checker is registered for the given type.
        Adding a ``StructuralInvariant`` declaration without
        corresponding registry entry is a contributor-guide
        violation; fail loudly.
    """
    if invariant_type not in _REGISTRY:
        raise KeyError(
            f"No structural-invariants checker registered for "
            f"invariant_type={invariant_type!r}. Registered "
            f"types: {sorted(_REGISTRY.keys())}. "
            f"To register, decorate a checker callable with "
            f"@register_invariant({invariant_type!r})."
        )
    return _REGISTRY[invariant_type]


# ---------------------------------------------------------------------
# Phase 3 stub registry — 9 wrapper-class invariant types
#
# Each entry below registers the ``invariant_type`` name with a
# ``NotImplementedError``-raising placeholder. Subsequent batches
# replace these stubs with concrete checker implementations.
#
# Per user-locked refinement 2: NO live audit declares any of
# these in Session 5. Validation of the dispatch path happens
# in ``_test_structural_invariants.py``.
# ---------------------------------------------------------------------


def _stub(invariant_type: str, batch_n: int) -> InvariantChecker:
    """Generate a stub checker that raises NotImplementedError."""

    def _raise(tsl, ref, fixture, inv):  # noqa: ARG001 — stub
        raise NotImplementedError(
            f"structural_invariants checker for "
            f"invariant_type={invariant_type!r} is stubbed at "
            f"Phase 3 Session 5; populate at Batch {batch_n}."
        )

    _raise.__name__ = f"_stub_{invariant_type}"
    return _raise


# Decomposition family (Batch 7-ish; STL/MSTL/FFT/wavelet)
_REGISTRY["decomposition_additive"] = _stub("decomposition_additive", 7)
_REGISTRY["decomposition_multiplicative"] = _stub(
    "decomposition_multiplicative", 7,
)

# VAR / VECM family (Batch 3)
_REGISTRY["var_eigenvalues"] = _stub("var_eigenvalues", 3)
_REGISTRY["vecm_cointegration_rank"] = _stub("vecm_cointegration_rank", 3)

# GARCH family (Batch 2 — first to populate)
_REGISTRY["garch_conditional_variance"] = _stub(
    "garch_conditional_variance", 2,
)
_REGISTRY["garch_persistence"] = _stub("garch_persistence", 2)

# Kalman family (Batch 5)
_REGISTRY["kalman_covariance_ordering"] = _stub(
    "kalman_covariance_ordering", 5,
)
_REGISTRY["kalman_innovation_positivity"] = _stub(
    "kalman_innovation_positivity", 5,
)

# HMM / Markov switching (Batch 4)
_REGISTRY["hmm_row_sums"] = _stub("hmm_row_sums", 4)
_REGISTRY["hmm_emission_normalization"] = _stub(
    "hmm_emission_normalization", 4,
)

# Wavelet (Batch 7)
_REGISTRY["wavelet_energy_conservation"] = _stub(
    "wavelet_energy_conservation", 7,
)
_REGISTRY["wavelet_inverse_roundtrip"] = _stub(
    "wavelet_inverse_roundtrip", 7,
)

# FFT / periodogram (Batch 7)
_REGISTRY["fft_energy_conservation"] = _stub(
    "fft_energy_conservation", 7,
)
_REGISTRY["fft_roundtrip"] = _stub("fft_roundtrip", 7)

# Bootstrap (Batch 10)
_REGISTRY["bootstrap_block_preservation"] = _stub(
    "bootstrap_block_preservation", 10,
)
_REGISTRY["bootstrap_distributional_centering"] = _stub(
    "bootstrap_distributional_centering", 10,
)

# Conformal intervals (Batch 9)
_REGISTRY["conformal_nominal_coverage"] = _stub(
    "conformal_nominal_coverage", 9,
)
_REGISTRY["conformal_interval_containment"] = _stub(
    "conformal_interval_containment", 9,
)


def list_registered_types() -> list[str]:
    """Return all registered invariant_type names. Useful for
    test enumeration and documentation."""
    return sorted(_REGISTRY.keys())


__all__ = [
    "StructuralInvariant",
    "InvariantChecker",
    "register_invariant",
    "get_invariant_checker",
    "list_registered_types",
]
