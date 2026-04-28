"""Phase 3 Session 5 split-fidelity diff validator.

Implements the Session 5 plan §Validation step 4 split:
(a) Numerical fidelity — strict byte-identical on
    metrics/outcome/seed_used/fixture_sha. Halt on regression.
(b) Metadata fidelity — informative diff on error/diagnostics
    version-snapshot fields. Trigger investigation, don't auto-
    fail.

Usage::

    python tools/reference_parity/harness/_validate_session5_diff.py \\
        /tmp/batch1_pre.json /tmp/batch1_post.json
"""

from __future__ import annotations

import json
import sys
from typing import Any


# Per Session 5 plan: numerical fidelity is strict.
NUMERICAL_FIDELITY_FIELDS = ("metrics", "outcome", "seed_used", "fixture_sha")

# Per Session 5 plan: metadata fidelity is investigative.
# `diagnostics` keys vary across checks; we diff the whole
# diagnostics block but report softly. `error` should be empty
# for PASS/CAVEAT outcomes.
METADATA_FIELDS = ("error", "diagnostics", "reference_versions")


def _by_id(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {r["technique_id"]: r for r in records}


def _format_diff(label: str, pre: Any, post: Any) -> str:
    pre_s = json.dumps(pre, sort_keys=True, default=str)[:200]
    post_s = json.dumps(post, sort_keys=True, default=str)[:200]
    return f"  {label}:\n    pre:  {pre_s}\n    post: {post_s}"


def main(pre_path: str, post_path: str) -> int:
    with open(pre_path) as f:
        pre_records = json.load(f)
    with open(post_path) as f:
        post_records = json.load(f)

    pre = _by_id(pre_records)
    post = _by_id(post_records)

    print("=" * 70)
    print("Phase 3 Session 5 — split-fidelity validation")
    print("=" * 70)
    print(f"  pre:  {pre_path} ({len(pre)} checks)")
    print(f"  post: {post_path} ({len(post)} checks)")
    print()

    # Membership check
    only_pre = set(pre) - set(post)
    only_post = set(post) - set(pre)
    if only_pre:
        print(f"!! REGRESSION: checks present in pre but missing post: "
              f"{sorted(only_pre)}")
    if only_post:
        print(f"!! Note: checks added by refactor (informational): "
              f"{sorted(only_post)}")
    common_ids = sorted(set(pre) & set(post))

    # ----- (a) Numerical fidelity check -----
    print("\n--- (a) Numerical fidelity (strict; regression halt) ---")
    numerical_failures: list[str] = []
    for tid in common_ids:
        for field in NUMERICAL_FIDELITY_FIELDS:
            if pre[tid].get(field) != post[tid].get(field):
                numerical_failures.append(tid)
                print(f"!! NUMERICAL DIVERGENCE in {tid}.{field}:")
                print(_format_diff(field, pre[tid].get(field), post[tid].get(field)))
    if numerical_failures:
        print(f"\n  RESULT: REGRESSION on {len(set(numerical_failures))} "
              f"check(s). HALT — do NOT commit.")
    else:
        print(f"  RESULT: all {len(common_ids)} checks numerically "
              f"byte-identical. PASS.")

    # ----- (b) Metadata fidelity check -----
    print("\n--- (b) Metadata fidelity (investigative; non-blocking) ---")
    metadata_diffs: list[tuple[str, str]] = []
    for tid in common_ids:
        for field in METADATA_FIELDS:
            pre_v = pre[tid].get(field)
            post_v = post[tid].get(field)
            if pre_v != post_v:
                metadata_diffs.append((tid, field))
    if metadata_diffs:
        print(f"  RESULT: {len(metadata_diffs)} metadata field(s) differ:")
        for tid, field in metadata_diffs:
            print(f"\n  {tid}.{field}:")
            print(_format_diff(field, pre[tid].get(field),
                               post[tid].get(field)))
        print("\n  → investigate per Session 5 plan §Validation step 4 (b).")
    else:
        print(f"  RESULT: all {len(common_ids)} checks metadata "
              f"byte-identical.")

    print()
    print("=" * 70)
    if numerical_failures:
        print("OVERALL: NUMERICAL REGRESSION — HALT.")
        return 1
    if metadata_diffs:
        print("OVERALL: PASS (numerical) + metadata diffs to investigate.")
        return 2
    print("OVERALL: PASS (numerical + metadata both byte-identical).")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <pre.json> <post.json>", file=sys.stderr)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2]))
