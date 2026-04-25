#!/usr/bin/env python3
"""Phase 4.5 helper: enumerate harness checks affected by
uncommitted changes.

Reads ``docs/follow_up_check_coverage.md`` and prints suggested
Phase 4.5 actions for each modified wrapper in
``engine/techniques/``.

This script is a soft aid — the workflow doesn't depend on it.
Authors can consult ``docs/follow_up_check_coverage.md``
directly. Exit code is always 0; this is informational, not
enforcement.

Usage:
    python tools/follow_up_phase_check.py
    python tools/follow_up_phase_check.py --base origin/master
    python tools/follow_up_phase_check.py --base 75aa182

See ``docs/follow_up_workflow.md`` for the full Phase 4.5
disclosure protocol.
"""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys


ROOT = pathlib.Path(__file__).resolve().parent.parent
COVERAGE_DOC = ROOT / "docs" / "follow_up_check_coverage.md"


def load_coverage_map() -> dict[str, list[tuple[str, str, str]]]:
    """Parse the static mapping table from the coverage doc.

    Returns a dict mapping wrapper basename (e.g.
    ``stochastic_volatility.py``) to a list of
    ``(technique_id, tier, invocation_pattern)`` tuples. A
    wrapper appearing multiple times in the table (e.g.
    stochastic_volatility.py covered by both 2b and 2c) yields
    multiple list entries.

    Tolerates whitespace variations in the markdown table.
    Skips section-header rows and the table-separator row.
    """
    if not COVERAGE_DOC.exists():
        raise FileNotFoundError(
            f"Coverage doc missing: {COVERAGE_DOC}. "
            f"Run from a checked-out repo where Phase 3.1 has "
            f"shipped, or update COVERAGE_DOC path in this script."
        )
    mapping: dict[str, list[tuple[str, str, str]]] = {}
    in_table = False
    for raw_line in COVERAGE_DOC.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line.startswith("| TSL wrapper"):
            in_table = True
            continue
        if in_table and line.startswith("|---"):
            continue
        if in_table and not line.startswith("|"):
            in_table = False
            continue
        if not in_table:
            continue
        # Parse a data row: |col1|col2|col3|col4|
        parts = [p.strip() for p in line.strip("|").split("|")]
        if len(parts) != 4:
            continue
        wrapper, tid, tier, invocation = parts
        if not wrapper or not tid:
            continue
        mapping.setdefault(wrapper, []).append((tid, tier, invocation))
    return mapping


def get_modified_wrappers(base: str) -> list[str]:
    """Run ``git diff --name-only <base>...HEAD``; return list
    of basenames in ``engine/techniques/``.

    Returns an empty list if the diff command fails (logged to
    stderr) — the caller treats that as "nothing to check"
    rather than an error.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base}...HEAD"],
            capture_output=True, text=True, check=True,
            cwd=ROOT,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"git diff failed (returncode {e.returncode}): "
            f"{(e.stderr or '').strip()}",
            file=sys.stderr,
        )
        return []
    except FileNotFoundError:
        print(
            "git not found on PATH; cannot enumerate modified "
            "wrappers.",
            file=sys.stderr,
        )
        return []

    modified: list[str] = []
    for path in result.stdout.splitlines():
        path = path.strip()
        if not path:
            continue
        if path.startswith("engine/techniques/") and path.endswith(".py"):
            basename = pathlib.PurePosixPath(path).name
            # Skip non-wrapper modules; they're listed in the
            # "Non-wrapper modules" section of the coverage doc.
            if basename in {
                "__init__.py", "base.py", "registry.py",
                "_kalman_common.py", "_sv_mcmc.py",
                "_sv_mcmc_gibbs.py",
            }:
                continue
            modified.append(basename)
    return modified


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 4.5 helper: enumerate harness checks affected "
            "by uncommitted changes."
        ),
    )
    parser.add_argument(
        "--base", default="origin/master",
        help=(
            "Git base ref to diff against (default: "
            "origin/master). Common alternatives: HEAD~1, "
            "the SHA of the previous commit on the branch."
        ),
    )
    args = parser.parse_args()

    coverage = load_coverage_map()
    modified = get_modified_wrappers(args.base)

    if not modified:
        print(
            f"No modified wrappers in engine/techniques/ vs "
            f"{args.base}."
        )
        return 0

    print(f"Modified wrappers vs {args.base}:")
    for wrapper in modified:
        print(f"  engine/techniques/{wrapper}")
        checks = coverage.get(wrapper, [])
        if not checks:
            print(f"    -> No harness coverage.")
            print(
                f"      Phase 4.5 disclosure: "
                f"'N/A: no harness check exists for this wrapper.'"
            )
            continue
        for tid, tier, invocation in checks:
            print(f"    -> {tid} (tier: {tier})")
            print(
                f"      run: python -m reference_parity "
                f"--technique {tid}"
            )
            print(f"      invocation pattern: {invocation}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
