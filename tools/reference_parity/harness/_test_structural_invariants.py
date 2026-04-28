"""Phase 3 Session 5 — structural-invariants registry unit test.

Per Session 5 plan §Verification step 6 (refinement 2): validate
the registry dispatch path *without* wiring a live audit through
``NotImplementedError``-raising stubs. p3_mstl is NOT declaring
structural_invariants this session per refinement 2; the
declaration is deferred to Batch 7 when wavelet/FFT class
invariants populate.

Tests:

1. ``StructuralInvariant`` dataclass instantiates with all
   required fields + accepts the documented default
   ``enabled=True``.
2. All 18 registered invariant types are discoverable via
   ``list_registered_types``.
3. ``get_invariant_checker`` returns a callable for each
   registered type.
4. Each registered checker raises ``NotImplementedError`` with
   the documented batch-N message when invoked.
5. ``get_invariant_checker`` raises ``KeyError`` with a
   helpful message for an unregistered invariant type.

Run via::

    PYTHONPATH=tools python tools/reference_parity/harness/_test_structural_invariants.py
"""

from __future__ import annotations

import sys

from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
    get_invariant_checker,
    list_registered_types,
)


def test_dataclass_instantiation() -> None:
    inv = StructuralInvariant(
        name="test",
        invariant_type="garch_persistence",
        tolerance=1e-3,
        tolerance_type="relative",
    )
    assert inv.name == "test"
    assert inv.invariant_type == "garch_persistence"
    assert inv.tolerance == 1e-3
    assert inv.tolerance_type == "relative"
    assert inv.enabled is True  # documented default

    inv2 = StructuralInvariant(
        name="test2",
        invariant_type="garch_persistence",
        tolerance=0.0,
        tolerance_type="absolute",
        enabled=False,
    )
    assert inv2.enabled is False
    print("  test_dataclass_instantiation: PASS")


def test_registry_enumeration() -> None:
    types = list_registered_types()
    expected = {
        # Decomposition (Batch 7-ish)
        "decomposition_additive", "decomposition_multiplicative",
        # VAR/VECM (Batch 3)
        "var_eigenvalues", "vecm_cointegration_rank",
        # GARCH (Batch 2)
        "garch_conditional_variance", "garch_persistence",
        # Kalman (Batch 5)
        "kalman_covariance_ordering", "kalman_innovation_positivity",
        # HMM/Markov (Batch 4)
        "hmm_row_sums", "hmm_emission_normalization",
        # Wavelet (Batch 7)
        "wavelet_energy_conservation", "wavelet_inverse_roundtrip",
        # FFT (Batch 7)
        "fft_energy_conservation", "fft_roundtrip",
        # Bootstrap (Batch 10)
        "bootstrap_block_preservation",
        "bootstrap_distributional_centering",
        # Conformal (Batch 9)
        "conformal_nominal_coverage", "conformal_interval_containment",
    }
    actual = set(types)
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"missing types: {sorted(missing)}"
    assert not extra, f"unexpected types: {sorted(extra)}"
    assert len(types) == 18, f"expected 18 types, got {len(types)}"
    print(f"  test_registry_enumeration: PASS ({len(types)} types)")


def test_checker_dispatch() -> None:
    """Each registered checker is callable and raises
    NotImplementedError with the documented Session 5 stub
    message format."""
    types = list_registered_types()
    sample_inv = StructuralInvariant(
        name="probe", invariant_type="placeholder",
        tolerance=0.0, tolerance_type="absolute",
    )
    raised_count = 0
    for t in types:
        checker = get_invariant_checker(t)
        assert callable(checker), f"{t}: not callable"
        # Build a fresh placeholder invariant matching this type
        inv = StructuralInvariant(
            name="probe", invariant_type=t,
            tolerance=0.0, tolerance_type="absolute",
        )
        try:
            checker({}, {}, {}, inv)
        except NotImplementedError as e:
            msg = str(e)
            assert "stubbed at Phase 3 Session 5" in msg, (
                f"{t}: stub message missing canonical phrase: {msg}"
            )
            assert "populate at Batch" in msg, (
                f"{t}: stub message missing batch-N hint: {msg}"
            )
            raised_count += 1
    assert raised_count == len(types), (
        f"only {raised_count}/{len(types)} types raised correctly"
    )
    print(f"  test_checker_dispatch: PASS "
          f"({raised_count} stubs all raised NotImplementedError)")


def test_unregistered_type_raises_keyerror() -> None:
    try:
        get_invariant_checker("does_not_exist")
    except KeyError as e:
        msg = str(e)
        assert "does_not_exist" in msg
        assert "Registered types:" in msg or "register_invariant" in msg
        print("  test_unregistered_type_raises_keyerror: PASS")
        return
    raise AssertionError(
        "get_invariant_checker accepted unregistered type"
    )


def main() -> int:
    print("Phase 3 Session 5 — structural_invariants registry unit test")
    try:
        test_dataclass_instantiation()
        test_registry_enumeration()
        test_checker_dispatch()
        test_unregistered_type_raises_keyerror()
    except AssertionError as e:
        print(f"\nFAILED: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"\nERROR: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print("\nAll tests PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
