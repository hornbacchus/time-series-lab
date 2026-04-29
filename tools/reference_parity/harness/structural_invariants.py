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

# VAR / VECM family — populated at Phase 3 Session 7 (Batch 3 entry).


def _check_var_eigenvalues(tsl, ref, fixture, inv):
    """VAR companion-form eigenvalue stability: max |lambda| < 1.

    The VAR(p) process is stable iff all eigenvalues of the
    companion form (k*p, k*p) matrix lie strictly inside the unit
    circle. TSL emits the pre-computed companion eigenvalue
    magnitudes (or we compute from extracted A_p coefficients).
    Reference (R vars::roots) provides the same; we compare both
    for invariance separately rather than for parity (eigenvalues
    are deterministic given identical coefficient matrix).
    """
    import numpy as np
    eigs = np.asarray(tsl.get("companion_eig_magnitudes"), dtype=np.float64)
    if eigs.size == 0:
        return {
            "name": inv.name,
            "status": "BLOCK",
            "error": "TSL output missing 'companion_eig_magnitudes' field",
        }
    max_abs_eig = float(np.max(np.abs(eigs)))
    # Tolerance interpretation: relative tolerance against unit
    # circle boundary. PASS iff max_abs < 1 - tolerance; CAVEAT if
    # max_abs < 1 + tolerance (boundary regime); BLOCK if
    # max_abs >= 1 + tolerance.
    pass_threshold = 1.0 - float(inv.tolerance)
    block_threshold = 1.0 + float(inv.tolerance)
    if max_abs_eig < pass_threshold:
        status = "PASS"
    elif max_abs_eig < block_threshold:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "name": inv.name,
        "status": status,
        "max_abs_eig": max_abs_eig,
        "n_eigs": int(eigs.size),
        "pass_threshold": pass_threshold,
        "block_threshold": block_threshold,
    }


def _check_vecm_cointegration_rank(tsl, ref, fixture, inv):
    """VECM cointegrating-rank invariance: TSL-fitted rank ==
    reference-fitted rank within stated tolerance of trace
    statistic differences.

    The VECM cointegration rank r is the integer count of
    cointegrating vectors implied by Johansen's trace statistic
    test. Both TSL (statsmodels.tsa.vector_ar.vecm) and R
    (urca::ca.jo with cointegration test → vec2var) determine r
    from the same trace-statistic + critical-value comparison;
    given identical fixture, they should agree on r exactly.

    Tolerance interpretation: with tolerance_type="absolute" and
    tolerance=0.0 (canonical), r_TSL must equal r_REF exactly. A
    non-zero tolerance permits ±tolerance integer mismatch (e.g.,
    tolerance=1 allows r_TSL=2, r_REF=1 — for boundary fixtures
    where the trace statistic is near a critical value).
    """
    r_tsl = tsl.get("cointegrating_rank")
    r_ref = ref.get("cointegrating_rank")
    if r_tsl is None or r_ref is None:
        return {
            "name": inv.name,
            "status": "BLOCK",
            "error": (
                f"Missing rank field: tsl={r_tsl}, ref={r_ref}"
            ),
        }
    diff = abs(int(r_tsl) - int(r_ref))
    threshold = int(inv.tolerance)
    if diff <= threshold:
        status = "PASS"
    elif diff <= threshold + 1:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "name": inv.name,
        "status": status,
        "tsl_rank": int(r_tsl),
        "ref_rank": int(r_ref),
        "abs_diff": diff,
    }


_REGISTRY["var_eigenvalues"] = _check_var_eigenvalues
_REGISTRY["vecm_cointegration_rank"] = _check_vecm_cointegration_rank

# GARCH family — populated at Phase 3 Session 6 (Batch 2 entry).
# These are the FIRST concrete invariant implementations
# replacing Session 5 NotImplementedError stubs. They establish
# the checker contract: callable receives
# (tsl_outputs, ref_outputs, fixture, invariant) and returns a
# metric dict with status (PASS/CAVEAT/BLOCK), measured residual,
# and diagnostic context.


def _check_garch_conditional_variance(tsl, ref, fixture, inv):
    """sigma2_t > 0 for all t. Conditional variance positivity is
    a non-negotiable structural property of GARCH-family models;
    any sigma2_t <= 0 indicates the optimizer landed at an
    invalid parameter region. Apply on TSL side only — R rugarch
    enforces positivity via parameter constraints, so we don't
    expect to detect ref-side violations.
    """
    import numpy as np  # local import; harness modules avoid top-level numpy
    sigma2 = np.asarray(tsl.get("conditional_variance"), dtype=np.float64)
    if sigma2.size == 0:
        return {
            "name": inv.name,
            "status": "BLOCK",
            "error": "TSL output missing 'conditional_variance' field",
        }
    n_nonpositive = int(np.sum(sigma2 <= 0))
    min_sigma2 = float(np.min(sigma2))
    # Tolerance interpretation: with tolerance_type="absolute" and
    # tolerance=0.0 (the canonical config), we allow no violations.
    # Numerical noise near zero (sigma2 ~ 1e-300) is treated as a
    # PASS since the GARCH math guarantees only sigma2 > 0, not
    # sigma2 >= eps for any positive eps.
    threshold = -float(inv.tolerance) if inv.tolerance > 0 else 0.0
    if min_sigma2 > threshold:
        status = "PASS"
    elif n_nonpositive == 0 and min_sigma2 > -1e-10:
        # Exactly-zero or near-zero negative — within numerical
        # noise. Surface as CAVEAT for audit-trail visibility.
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "name": inv.name,
        "status": status,
        "min_sigma2": min_sigma2,
        "n_nonpositive": n_nonpositive,
        "n_total": int(sigma2.size),
    }


def _check_garch_persistence(tsl, ref, fixture, inv):
    """Persistence < 1 for sGARCH/GJR (variance-level dynamics)
    or |beta| < 1 for EGARCH (log-variance AR). The checker
    receives the persistence value pre-computed by the wrapper
    (TSL's garch_model.py emits a 'persistence' audit field with
    the model-appropriate formula already applied per the CAI
    Phase 2 Session 6 fix F-G-T2-EGARCH-PERSIST). We just check
    that the absolute persistence value is < 1 within the stated
    tolerance.

    For IGARCH (which TSL doesn't expose as a distinct
    technique_id), persistence == 1 exactly; that variant is
    out of scope for Phase 3 Session 6.
    """
    persistence = tsl.get("persistence")
    if persistence is None:
        return {
            "name": inv.name,
            "status": "BLOCK",
            "error": "TSL output missing 'persistence' field",
        }
    abs_p = abs(float(persistence))
    # tolerance_type="relative" with tolerance=1e-3 means we allow
    # persistence to be within 1e-3 of 1.0 (i.e., the
    # near-IGARCH boundary). PASS iff abs_p < 1 - tolerance;
    # CAVEAT iff abs_p < 1 + tolerance (boundary regime);
    # BLOCK iff abs_p >= 1 + tolerance (unstable).
    pass_threshold = 1.0 - float(inv.tolerance)
    block_threshold = 1.0 + float(inv.tolerance)
    if abs_p < pass_threshold:
        status = "PASS"
    elif abs_p < block_threshold:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "name": inv.name,
        "status": status,
        "persistence": float(persistence),
        "abs_persistence": abs_p,
        "pass_threshold": pass_threshold,
        "block_threshold": block_threshold,
    }


_REGISTRY["garch_conditional_variance"] = _check_garch_conditional_variance
_REGISTRY["garch_persistence"] = _check_garch_persistence

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
