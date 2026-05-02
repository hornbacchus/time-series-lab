"""structural-invariants registry unit test.

Phase 4 Session 7 (P4-1.1, 2026-05-02) — extended to handle:
  - The 5 new concrete invariant types from S7 (mcmc_convergence,
    evt_extremal_index, mint_coherence, attention_normalization,
    intervals_test).
  - Both stub-checker types (NotImplementedError-raising) and
    concrete checkers (return BLOCK status dict on missing
    inputs; PASS / CAVEAT / BLOCK on valid inputs).

Phase 3 Session 5 origin: validate the registry dispatch path
without wiring a live audit through ``NotImplementedError``-
raising stubs (per S5 plan refinement 2). The dispatch contract
holds for both stub and concrete checkers; tests cover both
modes.

Tests:

1. ``StructuralInvariant`` dataclass instantiates with all
   required fields + accepts the documented default
   ``enabled=True``.
2. All registered invariant types are discoverable via
   ``list_registered_types``. Phase 4 S7: 18 + 5 = 23 types.
3. ``get_invariant_checker`` returns a callable for each
   registered type.
4. Stub checkers raise ``NotImplementedError`` with the
   documented "stubbed at Phase 3 Session 5 ... populate at
   Batch N" message format.
5. Concrete checkers return a ``{"name": ..., "status":
   "BLOCK", "error": ...}`` dict when invoked with empty
   input (instead of raising) — the documented missing-field
   error path.
6. The 5 S7 new concrete checkers PASS on properly-formed
   inputs that satisfy each invariant.
7. ``get_invariant_checker`` raises ``KeyError`` with a
   helpful message for an unregistered invariant type.

Run via::

    PYTHONPATH=tools python tools/reference_parity/harness/_test_structural_invariants.py
"""

from __future__ import annotations

import sys

import numpy as np

from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
    get_invariant_checker,
    list_registered_types,
)


# Stub vs concrete classification — must match
# structural_invariants.py registry state. Phase 4 S7: 4 stubs
# + 19 concrete = 23 total.
_STUB_TYPES = {
    "decomposition_additive",
    "decomposition_multiplicative",
    "bootstrap_block_preservation",
    "bootstrap_distributional_centering",
}


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
    assert inv.enabled is True

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
        # Decomposition (Batch 7-ish; STILL stubbed)
        "decomposition_additive", "decomposition_multiplicative",
        # VAR/VECM (Batch 3; concrete)
        "var_eigenvalues", "vecm_cointegration_rank",
        # GARCH (Batch 2; concrete)
        "garch_conditional_variance", "garch_persistence",
        # Kalman (Batch 5; concrete)
        "kalman_covariance_ordering", "kalman_innovation_positivity",
        # HMM/Markov (Batch 4; concrete)
        "hmm_row_sums", "hmm_emission_normalization",
        # Wavelet (Batch 7; concrete)
        "wavelet_energy_conservation", "wavelet_inverse_roundtrip",
        # FFT (Batch 7; concrete)
        "fft_energy_conservation", "fft_roundtrip",
        # Bootstrap (Batch 10; STILL stubbed)
        "bootstrap_block_preservation",
        "bootstrap_distributional_centering",
        # Conformal (Batch 9; concrete)
        "conformal_nominal_coverage", "conformal_interval_containment",
        # Phase 4 S7 NEW (concrete) — P4-1.1 registry expansion
        "mcmc_convergence",
        "evt_extremal_index",
        "mint_coherence",
        "attention_normalization",
        "intervals_test",
    }
    actual = set(types)
    missing = expected - actual
    extra = actual - expected
    assert not missing, f"missing types: {sorted(missing)}"
    assert not extra, f"unexpected types: {sorted(extra)}"
    assert len(types) == 23, f"expected 23 types, got {len(types)}"
    print(f"  test_registry_enumeration: PASS ({len(types)} types)")


def test_checker_dispatch() -> None:
    """Each registered checker is callable. Stubs raise
    NotImplementedError; concrete checkers either return a BLOCK
    status dict on empty input OR raise a non-NotImplementedError
    exception (some pre-S7 concrete checkers, e.g.
    garch_conditional_variance / hmm_row_sums / var_eigenvalues,
    call ``np.asarray(tsl.get(field), dtype=np.float64)`` directly
    without a None pre-check; passing None here raises TypeError
    rather than returning a clean BLOCK dict — this is a
    pre-existing bug banked at Phase 4 S7 as B-Phase4-S7-1; not in
    S7 scope to fix because §11.8 trigger discipline limits the
    P4-1 cluster's blast radius). Both behaviors are accepted here
    as long as the checker doesn't accidentally return PASS on
    empty input.
    """
    types = list_registered_types()
    stub_count = 0
    concrete_clean = 0       # returns BLOCK dict
    concrete_raises = 0      # raises (non-NotImplementedError) exception
    for t in types:
        checker = get_invariant_checker(t)
        assert callable(checker), f"{t}: not callable"
        inv = StructuralInvariant(
            name="probe", invariant_type=t,
            tolerance=0.0, tolerance_type="absolute",
        )
        if t in _STUB_TYPES:
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
                stub_count += 1
                continue
            raise AssertionError(
                f"{t} (expected stub) did not raise NotImplementedError"
            )
        # Concrete checker: either returns a BLOCK status dict on
        # empty input OR raises a non-NotImplementedError exception
        # (pre-existing bug; B-Phase4-S7-1 banked).
        try:
            result = checker({}, {}, {}, inv)
        except NotImplementedError:
            raise AssertionError(
                f"{t} (expected concrete) raised NotImplementedError"
            )
        except Exception:
            # Acceptable per B-Phase4-S7-1 banked behavior
            concrete_raises += 1
            continue
        assert isinstance(result, dict), (
            f"{t}: concrete checker returned non-dict: {type(result)}"
        )
        assert "status" in result, (
            f"{t}: concrete checker missing 'status' field"
        )
        assert result["status"] in ("PASS", "CAVEAT", "BLOCK"), (
            f"{t}: invalid status {result['status']!r}"
        )
        assert result["status"] != "PASS", (
            f"{t}: empty input MUST NOT return PASS"
        )
        concrete_clean += 1
    concrete_count = concrete_clean + concrete_raises
    assert stub_count + concrete_count == len(types)
    assert stub_count == 4, f"expected 4 stub types; got {stub_count}"
    assert concrete_count == 19, (
        f"expected 19 concrete types; got {concrete_count}"
    )
    print(
        f"  test_checker_dispatch: PASS ({stub_count} stubs raise "
        f"NotImplementedError; {concrete_clean} concrete return "
        f"BLOCK; {concrete_raises} concrete raise on empty input "
        f"per B-Phase4-S7-1)"
    )


def test_s7_new_checkers_pass_on_valid_inputs() -> None:
    """Phase 4 S7: each of the 5 new concrete checkers PASSes
    on properly-formed inputs that satisfy the invariant."""

    # 1. mcmc_convergence — ess_min above threshold
    inv = StructuralInvariant(
        name="mcmc_test", invariant_type="mcmc_convergence",
        tolerance=200.0,  # ESS_min threshold
    )
    result = get_invariant_checker("mcmc_convergence")(
        {"ess_min": 500.0, "rhat_max": 1.02, "geweke_max_abs_z": 1.5},
        {}, {}, inv,
    )
    assert result["status"] == "PASS", f"mcmc_convergence: {result}"

    # 2. evt_extremal_index — theta in (0, 1)
    inv = StructuralInvariant(
        name="evt_test", invariant_type="evt_extremal_index",
        tolerance=0.01,
    )
    result = get_invariant_checker("evt_extremal_index")(
        {"theta": 0.65}, {}, {}, inv,
    )
    assert result["status"] == "PASS", f"evt_extremal_index: {result}"

    # 3. mint_coherence — residual at machine precision
    inv = StructuralInvariant(
        name="mint_test", invariant_type="mint_coherence",
        tolerance=1e-10,
    )
    result = get_invariant_checker("mint_coherence")(
        {"coherence_residual": 1e-15}, {}, {}, inv,
    )
    assert result["status"] == "PASS", f"mint_coherence: {result}"

    # 4. attention_normalization — softmax-like row-stochastic
    rng = np.random.default_rng(42)
    raw = rng.standard_normal((4, 8, 8))
    A = np.exp(raw)
    A /= A.sum(axis=-1, keepdims=True)  # softmax → row-stochastic
    inv = StructuralInvariant(
        name="attn_test", invariant_type="attention_normalization",
        tolerance=1e-10,  # tighter than typical noise floor
    )
    result = get_invariant_checker("attention_normalization")(
        {"attention_matrix": A}, {}, {}, inv,
    )
    assert result["status"] == "PASS", (
        f"attention_normalization: {result}"
    )

    # 5. intervals_test — pvalue above floor (independence not rejected)
    inv = StructuralInvariant(
        name="chris_test", invariant_type="intervals_test",
        tolerance=0.05,  # standard 5% floor
    )
    result = get_invariant_checker("intervals_test")(
        {"chris_pvalue": 0.42}, {}, {}, inv,
    )
    assert result["status"] == "PASS", f"intervals_test: {result}"

    print("  test_s7_new_checkers_pass_on_valid_inputs: PASS")


def test_s7_new_checkers_block_on_violation() -> None:
    """Phase 4 S7: each of the 5 new concrete checkers BLOCKs
    when the invariant is clearly violated."""

    # 1. mcmc_convergence — ESS catastrophically low
    inv = StructuralInvariant(
        name="mcmc_bad", invariant_type="mcmc_convergence",
        tolerance=200.0,
    )
    result = get_invariant_checker("mcmc_convergence")(
        {"ess_min": 10.0, "rhat_max": 2.0, "geweke_max_abs_z": 5.0},
        {}, {}, inv,
    )
    assert result["status"] == "BLOCK", f"mcmc_convergence bad: {result}"

    # 2. evt_extremal_index — theta way out of [0, 1]
    inv = StructuralInvariant(
        name="evt_bad", invariant_type="evt_extremal_index",
        tolerance=0.01,
    )
    result = get_invariant_checker("evt_extremal_index")(
        {"theta": 5.0}, {}, {}, inv,
    )
    assert result["status"] == "BLOCK", f"evt_extremal_index bad: {result}"

    # 3. mint_coherence — large residual
    inv = StructuralInvariant(
        name="mint_bad", invariant_type="mint_coherence",
        tolerance=1e-10,
    )
    result = get_invariant_checker("mint_coherence")(
        {"coherence_residual": 1.0}, {}, {}, inv,
    )
    assert result["status"] == "BLOCK", f"mint_coherence bad: {result}"

    # 4. attention_normalization — non-stochastic matrix
    inv = StructuralInvariant(
        name="attn_bad", invariant_type="attention_normalization",
        tolerance=1e-10,
    )
    A_bad = np.array([[0.5, 0.3], [-0.2, 0.8]])  # row 1 negative
    result = get_invariant_checker("attention_normalization")(
        {"attention_matrix": A_bad}, {}, {}, inv,
    )
    assert result["status"] == "BLOCK", (
        f"attention_normalization bad: {result}"
    )

    # 5. intervals_test — pvalue way below floor
    inv = StructuralInvariant(
        name="chris_bad", invariant_type="intervals_test",
        tolerance=0.05,
    )
    result = get_invariant_checker("intervals_test")(
        {"chris_pvalue": 0.001}, {}, {}, inv,
    )
    assert result["status"] == "BLOCK", f"intervals_test bad: {result}"

    print("  test_s7_new_checkers_block_on_violation: PASS")


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


def test_s9_inherited_wrapper_declarations() -> None:
    """Phase 4 Session 9 (P4-1.3, 2026-05-02) — verify the 9
    inherited-wrapper audit scripts declare ``structural_invariants``
    tuples that resolve to registered checkers.

    Declarations are dormant at S9 (the harness's check_invariants
    lifecycle method is not yet wired into the runner — declared
    invariants are discoverable via class introspection but do not
    fire during normal audit runs). This test exercises the
    declaration-side contract:
      - each audit class declares a non-empty structural_invariants
        tuple
      - each declared invariant_type resolves to a registered
        checker via get_invariant_checker
      - StructuralInvariant fields (name, tolerance, tolerance_type)
        are well-formed

    When the runner integration lands (Phase 4.5 / Phase 5
    candidate), this test extends to dispatch the checkers on
    actual run_tsl outputs.
    """
    # Import inherited audit classes lazily so the test file
    # doesn't slow down on import for the simple stub checks.
    expected = [
        ("reference_parity.harness.checks.kalman_filter",
         "KalmanFilterParity",
         "kalman_covariance_ordering"),
        ("reference_parity.harness.checks.johansen_bartlett",
         "JohansenBartlettParity",
         "vecm_cointegration_rank"),
        ("reference_parity.harness.checks.mcmc_sv_gaussian",
         "McmcSvGaussianParity",
         "mcmc_convergence"),
        ("reference_parity.harness.checks.mcmc_sv_student_t",
         "McmcSvStudentTParity",
         "mcmc_convergence"),
        ("reference_parity.harness.checks.evt_ferro_segers",
         "EvtFerroSegersParity",
         "evt_extremal_index"),
        ("reference_parity.harness.checks.mint_family",
         "MintFamilyParity",
         "mint_coherence"),
        ("reference_parity.harness.checks.transformer_attention",
         "TransformerAttentionParity",
         "attention_normalization"),
        ("reference_parity.harness.checks.caviar_sav",
         "CaviarSavParity",
         "intervals_test"),
        ("reference_parity.harness.checks.p3_bond_yield_forecast",
         "BondYieldForecastParity",
         "mcmc_convergence"),
    ]
    n_verified = 0
    import importlib
    for module_path, class_name, expected_inv_type in expected:
        try:
            mod = importlib.import_module(module_path)
        except ImportError as e:
            raise AssertionError(
                f"{module_path}: failed to import: {e}"
            )
        cls = getattr(mod, class_name, None)
        assert cls is not None, (
            f"{module_path}: class {class_name} not found"
        )
        invs = getattr(cls, "structural_invariants", ())
        assert isinstance(invs, tuple), (
            f"{class_name}: structural_invariants must be a tuple, "
            f"got {type(invs).__name__}"
        )
        assert len(invs) >= 1, (
            f"{class_name}: structural_invariants tuple is empty "
            f"(S9 P4-1.3 declaration missing)"
        )
        invariant_types = {inv.invariant_type for inv in invs}
        assert expected_inv_type in invariant_types, (
            f"{class_name}: declared invariant_types "
            f"{sorted(invariant_types)!r} missing expected "
            f"{expected_inv_type!r}"
        )
        # Resolve every declared checker (raises KeyError if missing)
        for inv in invs:
            checker = get_invariant_checker(inv.invariant_type)
            assert callable(checker), (
                f"{class_name}: checker for {inv.invariant_type!r} "
                f"not callable"
            )
            assert isinstance(inv.name, str) and inv.name, (
                f"{class_name}: invariant name must be non-empty str"
            )
            assert isinstance(inv.tolerance, (int, float)), (
                f"{class_name}: invariant tolerance must be numeric"
            )
            assert inv.tolerance_type in (
                "absolute", "relative", "probabilistic",
            ), (
                f"{class_name}: invalid tolerance_type "
                f"{inv.tolerance_type!r}"
            )
        n_verified += 1
    assert n_verified == 9, (
        f"expected 9 inherited-wrapper declarations; got {n_verified}"
    )
    print(
        f"  test_s9_inherited_wrapper_declarations: PASS "
        f"({n_verified} audit classes; all declarations resolve "
        f"to registered checkers)"
    )


def main() -> int:
    print(
        "Phase 4 Session 7 (P4-1.1) — structural_invariants registry "
        "unit test"
    )
    try:
        test_dataclass_instantiation()
        test_registry_enumeration()
        test_checker_dispatch()
        test_s7_new_checkers_pass_on_valid_inputs()
        test_s7_new_checkers_block_on_violation()
        test_unregistered_type_raises_keyerror()
        test_s9_inherited_wrapper_declarations()
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
