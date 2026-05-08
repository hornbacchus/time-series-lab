"""Reference-parity runner CLI.

Usage:
    python -m reference_parity --check-environment
    python -m reference_parity --tier fast
    python -m reference_parity --tier slow --json
    python -m reference_parity --technique 3e_mint_family

Exit codes:
    0 — all PASS / SKIP only.
    1 — any BLOCK.
    2 — any CAVEAT, no BLOCK / DOCUMENTED-DIVERGENCE.
    3 — ERROR or fatal environment mismatch.
    4 — any DOCUMENTED-DIVERGENCE, no BLOCK / ERROR
        (Phase 3.5 Session 1 Item 7 forward-provision; not yet
        triggered by any current wrapper).

The workflow YAMLs map exit codes 2 (CAVEAT) and 4
(DOCUMENTED-DIVERGENCE) to 0 (CI green) per
[P-1 §6.4](../../../docs/engineering/parity_standard.md#64-exit-code-policy-b).
"""

from __future__ import annotations

import argparse
import dataclasses
import importlib
import importlib.metadata as _md
import json
import pathlib
import pkgutil
import sys
import time
import traceback
from typing import Any

import numpy as np

from reference_parity.harness.base import (
    ParityCheck,
    ParityResult,
    Tier,
    aggregate_outcomes,
)
from reference_parity.harness.fixtures import (
    FixtureLoader,
    FixtureHashMismatchError,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import (
    RBridge,
    RBridgeError,
    RNotAvailableError,
    RPackageMissingError,
)


# ---------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------

def discover_checks() -> dict[str, type[ParityCheck]]:
    """Auto-import all modules under ``harness.checks`` and
    return the registered ``ParityCheck`` subclasses keyed by
    ``technique_id``."""
    from reference_parity.harness import checks as checks_pkg
    discovered: dict[str, type[ParityCheck]] = {}
    pkg_path = pathlib.Path(checks_pkg.__file__).parent
    for module_info in pkgutil.iter_modules([str(pkg_path)]):
        if module_info.name.startswith("__"):
            continue
        full_name = f"reference_parity.harness.checks.{module_info.name}"
        importlib.import_module(full_name)

    # Walk subclass tree
    def _walk(cls: type) -> list[type[ParityCheck]]:
        out = []
        for sub in cls.__subclasses__():
            if not getattr(sub, "__abstractmethods__", set()):
                out.append(sub)
            out.extend(_walk(sub))
        return out

    for cls in _walk(ParityCheck):
        tid = getattr(cls, "technique_id", "")
        if not tid:
            continue
        if tid in discovered:
            raise RuntimeError(
                f"Duplicate technique_id '{tid}' in "
                f"{cls.__module__} and "
                f"{discovered[tid].__module__}"
            )
        discovered[tid] = cls
    return discovered


# ---------------------------------------------------------------------
# Allowlist of wrapper IDs verified for invariants dispatch.
# Each entry must have TSL output exposing fields the declared
# structural_invariants require. Verified per Code authoring at
# session that adds the entry. See B-Phase5-S2-α-1-redux-
# ALLOWLIST-MECHANISM banking entry. Per Q-Allowlist-2=(a)
# kalman-only initial population at S2-α-1-redux; per-wrapper
# additions through subsequent S2 sub-sessions (johansen +
# evt + ...).
# ---------------------------------------------------------------------

_INVARIANTS_DISPATCH_ALLOWLIST = (
    "2a_kalman_filter_smoother",
    "3d_johansen_bartlett",
    "3c_evt_ferro_segers",
    "2b_mcmc_sv_gaussian",       # S3 — Case 0 outcome per pre-flight `1fd1ad3`
    "2c_mcmc_sv_student_t",      # S3 — Case 0 outcome per pre-flight `1fd1ad3`
    "3e_mint_family",            # S4-α — Case (i) outcome per pre-flight `d7e4cf7`
    "3f_transformer_attention",  # S4-β — Case (i) outcome per pre-flight `e3b55c0`/`ee6c973`/`cc053fd`
    "3a_caviar_sav",             # S4-γ — Case (i) variant (rename mapping) per pre-flight `086592c`/`5120c81`/`75e9fcf`
)


# ---------------------------------------------------------------------
# Per-check orchestration
# ---------------------------------------------------------------------

def _python_versions(pkgs: list[str]) -> dict[str, str]:
    out = {}
    for p in pkgs:
        try:
            out[p] = _md.version(p)
        except Exception:
            out[p] = "MISSING"
    return out


def run_check(
    check: ParityCheck,
    *,
    seed: int = 42,
    manifest: Manifest | None = None,
) -> ParityResult:
    """Orchestrate one check end-to-end. Translates exceptions
    into ParityResult outcomes (SKIP for missing-R, ERROR for
    unexpected). Implements the CAVEAT re-roll protocol."""
    t0 = time.monotonic()
    tid = check.technique_id
    fixture_sha = ""

    try:
        # 1. Load fixture (with hash verify if on-disk).
        # Phase 3.3: loader now returns (data, metadata, sha).
        # If the fixture provides ``canonical_seed`` in metadata,
        # use it as the effective seed for setup_fixture and for
        # CAVEAT-reroll (which bumps effective_seed + 1).
        # Replaces the per-check ``SEED_OFFSET`` workaround.
        effective_seed = seed
        fixture_data: dict = {}
        if check.fixture_id:
            loader = FixtureLoader()
            fixture_data, metadata, fixture_sha = loader.load(
                check.fixture_id,
            )
            if "canonical_seed" in metadata:
                effective_seed = int(metadata["canonical_seed"])
            # Allow setup_fixture to merge / supplement
            fixture = check.setup_fixture(effective_seed)
            fixture.update(fixture_data)
        else:
            fixture = check.setup_fixture(effective_seed)

        # 2. Run TSL. Phase 3 Session 14: ImportError from
        # run_tsl now also maps to SKIP — used by p3_x13 to
        # signal missing X-13 binary on host. This generalizes
        # the SKIP-on-missing-dep semantics from run_reference
        # (where it was added Session 1) to run_tsl (where it
        # was historically an ERROR-class exception).
        try:
            tsl_out = check.run_tsl(fixture)
        except ImportError as e:
            return ParityResult(
                technique_id=tid, outcome="SKIP",
                error=f"TSL wrapper dependency missing: {e}",
                duration_sec=round(time.monotonic() - t0, 3),
                seed_used=effective_seed, fixture_sha=fixture_sha,
            )

        # 3. Run reference (may raise R unavailable / package missing
        #    → SKIP)
        try:
            ref_out = check.run_reference(fixture)
        except RNotAvailableError as e:
            return ParityResult(
                technique_id=tid, outcome="SKIP",
                error=f"R unavailable: {e}",
                duration_sec=round(time.monotonic() - t0, 3),
                seed_used=effective_seed, fixture_sha=fixture_sha,
            )
        except RPackageMissingError as e:
            return ParityResult(
                technique_id=tid, outcome="SKIP",
                error=f"R package missing: {e}",
                duration_sec=round(time.monotonic() - t0, 3),
                seed_used=effective_seed, fixture_sha=fixture_sha,
            )
        except ImportError as e:
            return ParityResult(
                technique_id=tid, outcome="SKIP",
                error=f"Python reference import failed: {e}",
                duration_sec=round(time.monotonic() - t0, 3),
                seed_used=effective_seed, fixture_sha=fixture_sha,
            )

        # 4. Compare → first ParityResult
        first_result = check.compare(tsl_out, ref_out)
        first_result.duration_sec = round(time.monotonic() - t0, 3)
        first_result.seed_used = effective_seed
        first_result.fixture_sha = fixture_sha

        # 4.5. Phase 5 S2-α-1-redux — dispatch declared
        # structural invariants for allowlist wrappers.
        # Allowlist gating per _INVARIANTS_DISPATCH_ALLOWLIST
        # restricts dispatch to verified-field-availability
        # wrappers per B-Phase5-S2-α-1-redux-ALLOWLIST-MECHANISM
        # banking. Wrappers NOT in allowlist: skip dispatch
        # entirely (no INFO/BLOCK emitted; behavior matches
        # pre-S2-α-1).
        if (
            tid in _INVARIANTS_DISPATCH_ALLOWLIST
            and hasattr(check, "check_invariants")
            and getattr(check, "structural_invariants", ())
        ):
            invariant_results = check.check_invariants(
                tsl_out, ref_out, fixture,
            )
            if invariant_results:
                first_result.metrics["invariants"] = invariant_results
                inv_outcomes = [
                    str(r.get("status", "PASS"))
                    for r in invariant_results.values()
                    # INFO outcomes from defensive field-check
                    # layer don't affect overall outcome
                    # (they're audit-trail signal, not parity
                    # outcome).
                    if r.get("status") != "INFO"
                ]
                if inv_outcomes:
                    worst_inv = aggregate_outcomes(inv_outcomes)
                    first_result.outcome = aggregate_outcomes([
                        first_result.outcome, worst_inv,
                    ])

        # 5. CAVEAT re-roll. Bumps the EFFECTIVE seed by +1
        # (Phase 3.3): for fixtures with canonical_seed metadata
        # this is canonical_seed+1, NOT runner_seed+1. Without
        # canonical_seed, effective_seed == runner seed so this
        # behaves identically to the pre-3.3 path.
        if first_result.outcome == "CAVEAT" and check.on_caveat_reroll(first_result):
            try:
                seed_b = effective_seed + 1
                fixture_b = check.setup_fixture(seed_b)
                if check.fixture_id:
                    fixture_b.update(fixture_data)
                tsl_b = check.run_tsl(fixture_b)
                ref_b = check.run_reference(fixture_b)
                second_result = check.compare(tsl_b, ref_b)
                if second_result.outcome == "PASS":
                    second_result.outcome = "PASS"
                    second_result.duration_sec = round(
                        time.monotonic() - t0, 3,
                    )
                    second_result.seed_used = seed_b
                    second_result.fixture_sha = fixture_sha
                    second_result.diagnostics["caveat_reroll"] = (
                        "first run CAVEAT, retry with seed+1 PASS"
                    )
                    return second_result
                # CAVEAT-on-retry → escalate to BLOCK
                first_result.outcome = "BLOCK"
                first_result.diagnostics["caveat_reroll"] = (
                    f"first run CAVEAT, retry seed={seed_b} also "
                    f"CAVEAT — escalated to BLOCK"
                )
                first_result.duration_sec = round(
                    time.monotonic() - t0, 3,
                )
                return first_result
            except Exception as e:
                first_result.outcome = "ERROR"
                first_result.error = (
                    f"CAVEAT re-roll failed: "
                    f"{type(e).__name__}: {e}"
                )
                first_result.duration_sec = round(
                    time.monotonic() - t0, 3,
                )
                return first_result

        return first_result

    except FixtureHashMismatchError as e:
        return ParityResult(
            technique_id=tid, outcome="ERROR",
            error=f"Fixture hash mismatch: {e}",
            duration_sec=round(time.monotonic() - t0, 3),
            seed_used=seed, fixture_sha=fixture_sha,
        )
    except FileNotFoundError as e:
        return ParityResult(
            technique_id=tid, outcome="ERROR",
            error=f"Fixture file missing: {e}",
            duration_sec=round(time.monotonic() - t0, 3),
            seed_used=seed, fixture_sha=fixture_sha,
        )
    except Exception as e:
        return ParityResult(
            technique_id=tid, outcome="ERROR",
            error=f"{type(e).__name__}: {e}\n{traceback.format_exc()}",
            duration_sec=round(time.monotonic() - t0, 3),
            seed_used=seed, fixture_sha=fixture_sha,
        )


# ---------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------

def _check_environment(manifest: Manifest, *, json_out: bool) -> int:
    """Probe R + Python environment, report divergences."""
    bridge = RBridge(manifest)
    try:
        r_info = bridge.check_environment()
    except RNotAvailableError as e:
        result = {
            "status": "R_NOT_AVAILABLE",
            "error": str(e),
            "manifest_path": str(manifest.source_path),
        }
        if json_out:
            print(json.dumps(result, indent=2))
        else:
            print(f"R NOT AVAILABLE: {e}", file=sys.stderr)
        return 3

    py_versions = _python_versions(
        list(manifest.python.packages.keys())
    )
    py_divergences = {
        p: {"pinned": pin, "actual": py_versions.get(p, "MISSING")}
        for p, pin in manifest.python.packages.items()
        if py_versions.get(p, "MISSING") != pin
    }

    payload = {
        "status": "OK",
        "manifest_path": str(manifest.source_path),
        "manifest_last_review": manifest.last_review.isoformat(),
        "manifest_next_review": manifest.next_review.isoformat(),
        "manifest_is_stale": manifest.is_stale(),
        "r_version_pinned": manifest.r.version,
        "r_version_actual": r_info["r_version"],
        "r_packages_divergences": r_info["r_packages_divergences"],
        "python_packages_actual": py_versions,
        "python_packages_divergences": py_divergences,
    }
    if json_out:
        print(json.dumps(payload, indent=2))
    else:
        print(f"manifest: {payload['manifest_path']}")
        print(f"  last_review={payload['manifest_last_review']} "
              f"next_review={payload['manifest_next_review']} "
              f"stale={payload['manifest_is_stale']}")
        print(f"R: pinned={payload['r_version_pinned']} "
              f"actual={payload['r_version_actual']}")
        if payload["r_packages_divergences"]:
            print("  R divergences:")
            for k, v in payload["r_packages_divergences"].items():
                print(f"    {k}: pinned={v['pinned']} "
                      f"actual={v['actual']}")
        else:
            print("  R packages: all match")
        if payload["python_packages_divergences"]:
            print("  Python divergences:")
            for k, v in payload["python_packages_divergences"].items():
                print(f"    {k}: pinned={v['pinned']} "
                      f"actual={v['actual']}")
        else:
            print("  Python packages: all match")
    return 0


def _run_one(
    technique_id: str,
    *,
    seed: int,
    json_out: bool,
    manifest: Manifest,
) -> int:
    checks = discover_checks()
    if technique_id not in checks:
        msg = (
            f"Unknown technique_id '{technique_id}'. "
            f"Registered: {sorted(checks.keys())}"
        )
        if json_out:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 3
    check = checks[technique_id]()
    result = run_check(check, seed=seed, manifest=manifest)
    return _emit_results([result], json_out=json_out)


def _run_tier(
    tier: Tier,
    *,
    seed: int,
    json_out: bool,
    manifest: Manifest,
) -> int:
    checks = discover_checks()
    selected = [
        cls for cls in checks.values() if cls.tier == tier
    ]
    results: list[ParityResult] = []
    for cls in selected:
        results.append(run_check(cls(), seed=seed, manifest=manifest))
    return _emit_results(results, json_out=json_out)


def _emit_results(
    results: list[ParityResult],
    *,
    json_out: bool,
) -> int:
    payload = [
        {**r.to_dict(), "metrics": _coerce(r.metrics),
         "diagnostics": _coerce(r.diagnostics)}
        for r in results
    ]
    if json_out:
        print(json.dumps(payload, indent=2, default=_json_default))
    else:
        for r in results:
            line = (
                f"[{r.outcome}] {r.technique_id} "
                f"({r.duration_sec:.2f}s seed={r.seed_used})"
            )
            if r.error:
                line += f" — {r.error.splitlines()[0]}"
            print(line)
            if r.metrics:
                for k, v in r.metrics.items():
                    print(f"    metric.{k}: {v}")
        outcomes = [r.outcome for r in results]
        overall = aggregate_outcomes(outcomes)
        print(f"overall: {overall}")
    overall = aggregate_outcomes([r.outcome for r in results])
    return _exit_code_for(overall)


def _exit_code_for(overall: str) -> int:
    """Map aggregate outcome to runner exit code.

    Exit code policy (per [P-1 §6.4](../../../docs/engineering/parity_standard.md#64-exit-code-policy-b)):
        0 — PASS / SKIP only → CI green
        1 — BLOCK            → CI red
        2 — CAVEAT           → mapped to 0 in workflow YAML
        3 — ERROR            → CI red
        4 — DOCUMENTED-DIVERGENCE → mapped to 0 in workflow YAML
            (Phase 3.5 Session 1 Item 7 forward-provision; no
            current wrapper triggers DD; reserved per P-1 §2.3)
    """
    if overall == "BLOCK":
        return 1
    if overall == "CAVEAT":
        return 2
    if overall == "ERROR":
        return 3
    if overall == "DOCUMENTED-DIVERGENCE":
        return 4
    return 0


def _coerce(d: dict[str, Any]) -> dict[str, Any]:
    """Coerce numpy scalars to Python builtins for JSON."""
    out = {}
    for k, v in d.items():
        out[k] = _json_default(v) if not _is_json_native(v) else v
    return out


def _is_json_native(v: Any) -> bool:
    return isinstance(v, (int, float, str, bool, type(None), list, dict))


def _json_default(v: Any) -> Any:
    if isinstance(v, np.ndarray):
        return v.tolist()
    if isinstance(v, (np.floating, np.integer)):
        return v.item()
    if isinstance(v, dict):
        return {k: _json_default(x) for k, x in v.items()}
    if isinstance(v, (list, tuple)):
        return [_json_default(x) for x in v]
    return str(v)


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="reference_parity",
        description=(
            "Reference-parity harness runner. Compares TSL "
            "wrapper outputs against external reference "
            "implementations on seeded synthetic fixtures."
        ),
    )
    parser.add_argument(
        "--tier", choices=["fast", "slow"],
        help="Run all checks at this tier.",
    )
    parser.add_argument(
        "--technique",
        help="Run a single check by technique_id.",
    )
    parser.add_argument(
        "--check-environment", action="store_true",
        help="Probe R + Python environment vs manifest pins.",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Seed for fixture generation (default 42).",
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Emit machine-readable JSON.",
    )
    args = parser.parse_args(argv)

    try:
        manifest = Manifest.load()
    except Exception as e:
        msg = f"Failed to load manifest: {type(e).__name__}: {e}"
        if args.json:
            print(json.dumps({"error": msg}))
        else:
            print(msg, file=sys.stderr)
        return 3

    if args.check_environment:
        return _check_environment(manifest, json_out=args.json)
    if args.technique:
        return _run_one(
            args.technique, seed=args.seed,
            json_out=args.json, manifest=manifest,
        )
    if args.tier:
        return _run_tier(
            args.tier, seed=args.seed,
            json_out=args.json, manifest=manifest,
        )
    parser.print_help()
    return 3


if __name__ == "__main__":
    sys.exit(main())
