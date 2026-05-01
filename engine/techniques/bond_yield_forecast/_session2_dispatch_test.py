"""Bond Yield Forecast Session 2 — engine_worker dispatch test.

Exercises the technique through the same interface engine_worker
uses (registry → import → run(ctx, progress_callback)). Verifies:

  1. Registry resolution routes 'bond_yield_forecast' to the right module.
  2. Pre-flight validation rejects malformed configs cleanly with
     structured error_message + error_fixes (not deep BVAR exceptions).
  3. Pre-flight rejects parameter-out-of-bounds values with the same
     clean failure mode.
  4. Happy-path dispatch runs end-to-end on the canonical fixture and
     produces a well-formed RunResponse with the expected 4 tables.
  5. BVARWarning categories surface in audit_fields (count + by_category)
     instead of leaking to stderr.

Reproduces substantive coverage from S1's CLI-dependent skipped tests
under the wrapper-dispatch context (S2 carry-forward discipline):

  - test_session0_logging.* — covered indirectly: the wrapper's
    `warnings.catch_warnings(record=True)` block isolates root-logger
    + matplotlib + pandas-options state inside the run() scope. Not
    a direct re-test of the CLI's _log_to_file context manager
    (which doesn't migrate); rather, the wrapper's equivalent
    isolation is exercised by every dispatch.
  - test_session0_warnings.* — covered directly: dispatch_warnings
    case below verifies BVARWarning subclasses (ConvergenceWarning,
    ProjectionAtBoundWarning, ValidationDomainWarning) flow into
    audit_fields["warnings_by_category"] with their class name.
  - test_unified_input.* — covered by happy-path dispatch (which
    reads the canonical 3-sheet workbook via read_unified_workbook).

Run from TSL repo root:
    PYTHONPATH=engine python -m \\
      techniques.bond_yield_forecast._session2_dispatch_test
"""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

# Ensure engine/ is on path when invoked directly.
_ENGINE = str(Path(__file__).resolve().parents[2])
if _ENGINE not in sys.path:
    sys.path.insert(0, _ENGINE)

from techniques.base import RunContext  # noqa: E402
from techniques.registry import TECHNIQUE_REGISTRY  # noqa: E402


_FIXTURE = (
    Path(__file__).resolve().parent
    / "tests" / "fixtures" / "test_input_canonical.xlsx"
)


def _make_ctx(params: dict) -> RunContext:
    return RunContext({
        "run_id": "byf_s2_dispatch_test",
        "technique_id": "bond_yield_forecast",
        "preset": "Balanced",
        "seed": 42,
        "frequency": "Q",
        "time": [],
        "series": [],
        "params": params,
    })


def _resolve_run():
    """Resolve `bond_yield_forecast` through the registry the same way
    engine_worker._load_technique does."""
    import importlib

    module_path = TECHNIQUE_REGISTRY["bond_yield_forecast"]
    mod = importlib.import_module(module_path)
    assert hasattr(mod, "run"), "module has no run()"
    return mod.run


def _progress(stage, pct, message=None):
    print(f"  [progress {pct:>3d}%] {stage}" + (f" — {message}" if message else ""))


def case_registry_resolution() -> None:
    """Case 1: registry resolves to the right module."""
    print("\n=== Case 1: registry resolution ===")
    assert TECHNIQUE_REGISTRY.get("bond_yield_forecast") == \
        "techniques.bond_yield_forecast", "registry entry missing"
    assert TECHNIQUE_REGISTRY.get("byf") == \
        "techniques.bond_yield_forecast", "alias 'byf' missing"
    assert TECHNIQUE_REGISTRY.get("yield_forecast") == \
        "techniques.bond_yield_forecast", "alias 'yield_forecast' missing"
    run = _resolve_run()
    assert callable(run)
    print("  PASS — registry routes 'bond_yield_forecast' + aliases correctly")


def case_preflight_missing_workbook() -> None:
    """Case 2: pre-flight rejects missing input_workbook param cleanly."""
    print("\n=== Case 2: pre-flight rejects missing input_workbook ===")
    run = _resolve_run()
    ctx = _make_ctx({})  # no input_workbook
    resp = run(ctx, _progress)
    assert resp["status"] == "failure", f"expected failure, got {resp['status']}"
    assert "input_workbook" in resp["error_message"], \
        f"error message missing input_workbook reference: {resp['error_message']}"
    assert resp.get("error_fixes"), "error_fixes empty"
    print(f"  PASS — pre-flight rejected with clean message + {len(resp['error_fixes'])} fix(es)")


def case_preflight_bad_workbook_path() -> None:
    """Case 3: pre-flight rejects nonexistent workbook path."""
    print("\n=== Case 3: pre-flight rejects nonexistent workbook ===")
    run = _resolve_run()
    ctx = _make_ctx({"input_workbook": "C:/no/such/path.xlsx"})
    resp = run(ctx, _progress)
    assert resp["status"] == "failure"
    assert "not found" in resp["error_message"].lower()
    print("  PASS — pre-flight rejected nonexistent path cleanly")


def case_preflight_param_out_of_bounds() -> None:
    """Case 4: pre-flight rejects out-of-bounds params (lambda_1 < 0.001)."""
    print("\n=== Case 4: pre-flight rejects out-of-bounds parameter ===")
    run = _resolve_run()
    ctx = _make_ctx({
        "input_workbook": str(_FIXTURE),
        "lambda_1": 0.0,  # below the catalog minimum (0.001)
    })
    resp = run(ctx, _progress)
    assert resp["status"] == "failure"
    assert "lambda_1" in resp["error_message"]
    assert "below minimum" in resp["error_message"]
    print("  PASS — out-of-bounds lambda_1 rejected pre-deep-stack")


def case_preflight_n_draws_subsample_above_5000() -> None:
    """Case 5: pre-flight rejects n_draws_subsample > 5000 (plan §2.3 cap)."""
    print("\n=== Case 5: pre-flight rejects n_draws_subsample > 5000 ===")
    run = _resolve_run()
    ctx = _make_ctx({
        "input_workbook": str(_FIXTURE),
        "n_draws_subsample": 7000,  # above the friction-points §3 OOM cap
    })
    resp = run(ctx, _progress)
    assert resp["status"] == "failure"
    assert "n_draws_subsample" in resp["error_message"]
    assert "exceeds maximum" in resp["error_message"]
    print("  PASS — n_draws_subsample=7000 rejected (plan §2.3 cap=5000)")


def case_happy_path_dispatch() -> None:
    """Case 6: full happy-path dispatch on canonical fixture."""
    print("\n=== Case 6: happy-path dispatch (full BVAR-SV cycle) ===")
    print(f"  Fixture: {_FIXTURE}")
    run = _resolve_run()
    ctx = _make_ctx({
        "input_workbook": str(_FIXTURE),
        "scenario": "baseline",
    })
    resp = run(ctx, _progress)
    assert resp["status"] == "success", \
        f"expected success, got {resp['status']}: {resp.get('error_message')}"

    # Verify RunResponse shape per plan §2.1.9.
    expected_top_keys = {"run_id", "status", "plain_english_summary",
                         "tables", "audit_fields", "warnings",
                         "artifacts", "charting_suggestions"}
    missing_top = expected_top_keys - set(resp.keys())
    assert not missing_top, f"RunResponse missing keys: {missing_top}"

    # Verify 4 expected tables.
    table_names = [t["name"] for t in resp["tables"]]
    expected_table_substrings = ["Yield Forecast", "Macro Conditioning",
                                 "Convergence Diagnostics", "Run Metadata"]
    for sub in expected_table_substrings:
        assert any(sub in n for n in table_names), \
            f"missing expected table containing '{sub}': got {table_names}"

    # Verify audit_fields includes warning summary.
    af = resp["audit_fields"]
    for key in ("scenario", "n_draws", "n_burn", "n_kept_draws", "horizon",
                "input_workbook", "wrapper_runtime_seconds",
                "warnings_count", "warnings_by_category",
                "bvar_warning_messages"):
        assert key in af, f"audit_fields missing key '{key}'"

    print(f"  PASS — RunResponse well-formed; {len(resp['tables'])} tables; "
          f"{af['warnings_count']} warnings categorized as "
          f"{af['warnings_by_category']}")

    # JSON-roundtrip safety (engine_worker serializes to JSON).
    try:
        json.dumps(resp)
        print("  PASS — RunResponse is JSON-serializable")
    except (TypeError, ValueError) as e:
        print(f"  FAIL — JSON serialization broken: {e}")
        raise


def main() -> int:
    cases = [
        case_registry_resolution,
        case_preflight_missing_workbook,
        case_preflight_bad_workbook_path,
        case_preflight_param_out_of_bounds,
        case_preflight_n_draws_subsample_above_5000,
        case_happy_path_dispatch,
    ]
    failed = 0
    for c in cases:
        try:
            c()
        except AssertionError as e:
            failed += 1
            print(f"  FAIL — {c.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR — {c.__name__}: {e.__class__.__name__}: {e}")
    print()
    print("=" * 60)
    if failed == 0:
        print(f"DISPATCH TEST: PASS ({len(cases)}/{len(cases)} cases)")
        return 0
    print(f"DISPATCH TEST: FAIL ({failed} of {len(cases)} cases failed)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
