"""Phase 4 Session 11b — operational enforcement of P-1 §8.5
install-matrix gate (B-Phase4-S5-4).

Validates the install-matrix consistency rules per P-1 §8.5,
catching the failure pattern that surfaced at Phase 4 Session
5 (BVAR added to MANIFEST.toml + parity-fast.yml but missed
parity-slow.yml).

Two enforcement rules:

1. **MANIFEST → slow-tier (full coverage).** Every package
   pinned in ``MANIFEST.toml`` must appear in BOTH
   ``parity-slow.yml`` jobs (Windows + Linux). Slow-tier
   install runs the full reference manifest because every
   check class imports at runner-discovery time regardless
   of tier (Phase 3.5 Session 1 Item 4 protocol).

2. **fast-tier ⊂ slow-tier (subset preservation).** Every
   package in ``parity-fast.yml`` install lines must also
   appear in the slow-tier install lines. Fast-tier is
   intentionally a subset of slow-tier; an addition that
   lands on fast but not slow (the BVAR S5 case) is a gap
   the §8.5 gate exists to catch.

NOT enforced: "every MANIFEST package must be in fast-tier".
Fast-tier is documented as a subset per ``parity-fast.yml``
"Install fast-tier R packages" step comment ("Subset matching
the fast tier of MANIFEST.toml. Slow tier (full N packages)
lives in parity-slow.yml.").

Authoritative source: ``tools/reference_parity/harness/MANIFEST.toml``.

Python packages: any line containing ``pip install`` followed
by space-separated package names (with optional version pins
like ``torch==2.11.0`` or ``ewstools==2.1.2``).

R packages: any package name appearing inside a quoted string
within an ``install.packages(c(...))`` call. Multi-line
``c(...)`` blocks are handled — every double-quoted token
inside the install.packages() block counts.

Linux-only packages (``x13binary``, ``seasonal``) appear in
``parity-slow.yml`` Linux install lines but not in MANIFEST;
the check is one-directional (MANIFEST → workflow), so
Linux-only extras don't violate the gate.

Usage:
    python tools/validate_install_matrix.py

Exit codes:
    0 — install matrix consistent.
    1 — at least one gap found; gaps printed to stderr.

Per the Phase 4 cycle's belt-and-suspenders pattern, this
validator runs in two contexts:
  - Local pre-commit hook (catches gaps before commit).
  - CI workflow step (catches gaps if the local hook missed).
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

# Optional packages: appear in MANIFEST as documentation pins
# but legitimately absent from one or more workflow install
# lines. Examples:
# - ``pyts``: Session 11 documented for potential Batch 8 use;
#   NOT actually consumed by any check yet, but imports succeed
#   so it stays in MANIFEST as a documentation pin.
# - ``forecastHybrid``: Session 14 documented; not currently
#   consumed but pinned for future use.
# Override via this allowlist; surface as INFO not BLOCK.
ALLOWLIST_PARTIAL_INSTALL: set[str] = set()

# Linux-only packages: appear in workflow install lines but
# NOT in MANIFEST.toml. Examples:
# - ``x13binary`` / ``seasonal``: Linux-only X-13 binary
#   support per Phase 3.5 S6 + Phase 4 S2.
# These are documented exceptions; the check is one-directional
# (MANIFEST → workflow), so Linux-only extras don't violate
# the gate.

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tools" / "reference_parity" / "harness" / "MANIFEST.toml"
PARITY_FAST_YML = REPO_ROOT / ".github" / "workflows" / "parity-fast.yml"
PARITY_SLOW_YML = REPO_ROOT / ".github" / "workflows" / "parity-slow.yml"


def parse_manifest() -> tuple[set[str], set[str]]:
    """Parse MANIFEST.toml; return (python_packages, r_packages)."""
    with MANIFEST_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    py_pkgs = set((data.get("python", {}).get("packages") or {}).keys())
    r_pkgs = set((data.get("r", {}).get("packages") or {}).keys())
    return py_pkgs, r_pkgs


def _normalize(name: str) -> str:
    """Lowercase + strip pip-version-pin suffix and quotes."""
    name = name.strip().strip('"').strip("'")
    # Strip pip version-pin (==, >=, etc.)
    for op in ("==", ">=", "<=", "~=", ">", "<"):
        if op in name:
            name = name.split(op, 1)[0]
            break
    return name.lower()


def parse_pip_install_lines(yml_text: str) -> set[str]:
    """Extract Python package names from ``python -m pip install`` lines.

    Matches ONLY the canonical workflow command form ``python -m pip
    install`` to avoid false positives on prose mentioning "pip install"
    in comments / narrative text. Handles multi-line and single-line
    invocations with optional version pins, --index-url overrides,
    --upgrade flags.
    """
    pkgs: set[str] = set()
    # Match the canonical ``python -m pip install`` command form;
    # exclude prose mentions of "pip install" in YAML comments.
    for match in re.finditer(
        r"python\s+-m\s+pip\s+install\s+([^\n]+)", yml_text,
    ):
        tokens = match.group(1).split()
        for tok in tokens:
            # Skip flags / URLs.
            if tok.startswith("-") or tok.startswith("http") or tok.startswith("--"):
                continue
            normalized = _normalize(tok)
            if normalized and not normalized.startswith("--"):
                pkgs.add(normalized)
    return pkgs


def parse_r_install_packages(yml_text: str) -> set[str]:
    """Extract R package names from ``install.packages(c(...))`` blocks.

    Handles multi-line ``c(...)`` lists. Strategy: find each
    ``install.packages(`` open paren, scan to its matching close
    paren tracking nesting, extract every double-quoted token
    inside the block.
    """
    pkgs: set[str] = set()
    for match in re.finditer(r"install\.packages\s*\(", yml_text):
        start = match.end()
        depth = 1
        i = start
        while i < len(yml_text) and depth > 0:
            c = yml_text[i]
            if c == "(":
                depth += 1
            elif c == ")":
                depth -= 1
            i += 1
        block = yml_text[start : i - 1]
        # Strip R comments (# to end of line).
        block_no_comments = re.sub(r"#[^\n]*", "", block)
        for quoted in re.findall(r'"([^"]+)"', block_no_comments):
            # Skip URLs (e.g., the repos= argument).
            if quoted.startswith("http"):
                continue
            pkgs.add(_normalize(quoted))
    return pkgs


def _parse_slow_tier_jobs(slow_yml: str) -> tuple[set[str], set[str]]:
    """Slow-tier YAML has two jobs (Windows + Linux). Return
    (slow_windows_r, slow_linux_r) by splitting on the
    ``slow-linux:`` job marker.

    Python pip install lines on the two jobs are merged into a
    single set since both jobs install the same Python deps
    (the Linux job uses --index-url for torch only); we treat
    Python install coverage as a single ``slow_py`` set.
    """
    if "slow-linux:" in slow_yml:
        idx = slow_yml.index("slow-linux:")
        windows_block = slow_yml[:idx]
        linux_block = slow_yml[idx:]
    else:
        windows_block = slow_yml
        linux_block = ""
    return parse_r_install_packages(windows_block), parse_r_install_packages(linux_block)


def _check_manifest_in_surface(
    surface_name: str,
    surface_pkgs: set[str],
    manifest_pkgs: set[str],
    family: str,
) -> list[str]:
    """Rule 1: every MANIFEST package must appear in this surface."""
    expected_norm = {_normalize(p) for p in manifest_pkgs}
    missing = expected_norm - surface_pkgs
    return [
        f"  {family} package '{pkg}' in MANIFEST.toml but missing from {surface_name}"
        for pkg in sorted(missing)
    ]


def _check_fast_subset_of_slow(
    fast_pkgs: set[str], slow_pkgs: set[str], family: str,
) -> list[str]:
    """Rule 2: every fast-tier package must appear in slow-tier."""
    missing = fast_pkgs - slow_pkgs
    return [
        f"  {family} package '{pkg}' in parity-fast.yml install line "
        f"but missing from parity-slow.yml install line "
        f"(fast-tier MUST be a subset of slow-tier per P-1 §8.5)"
        for pkg in sorted(missing)
    ]


def main() -> int:
    py_manifest, r_manifest = parse_manifest()
    print(
        f"MANIFEST.toml: {len(py_manifest)} Python packages, "
        f"{len(r_manifest)} R packages",
        file=sys.stderr,
    )

    fast_yml = PARITY_FAST_YML.read_text(encoding="utf-8")
    slow_yml = PARITY_SLOW_YML.read_text(encoding="utf-8")

    fast_py = parse_pip_install_lines(fast_yml)
    slow_py = parse_pip_install_lines(slow_yml)
    fast_r = parse_r_install_packages(fast_yml)
    slow_windows_r, slow_linux_r = _parse_slow_tier_jobs(slow_yml)

    py_manifest_norm = {_normalize(p) for p in py_manifest}
    r_manifest_norm = {_normalize(p) for p in r_manifest}

    violations: list[str] = []
    # Rule 1: MANIFEST → slow-tier (full coverage; both jobs).
    violations += _check_manifest_in_surface(
        "parity-slow.yml (Python install line)", slow_py, py_manifest, "Python"
    )
    violations += _check_manifest_in_surface(
        "parity-slow.yml Windows job (R install.packages)", slow_windows_r, r_manifest, "R"
    )
    violations += _check_manifest_in_surface(
        "parity-slow.yml Linux job (R install.packages)", slow_linux_r, r_manifest, "R"
    )
    # Rule 2: fast-tier ⊂ slow-tier.
    violations += _check_fast_subset_of_slow(fast_py, slow_py, "Python")
    violations += _check_fast_subset_of_slow(fast_r, slow_windows_r, "R")

    if violations:
        print(
            "\nERROR: install-matrix gaps detected (P-1 §8.5):",
            file=sys.stderr,
        )
        for v in violations:
            print(v, file=sys.stderr)
        print(
            "\nFix: add the missing packages to the listed workflow files. "
            "See P-1 §8.5 for the four-surface install-matrix gate.",
            file=sys.stderr,
        )
        return 1

    print(
        "OK — install matrix consistent: MANIFEST coverage in slow-tier "
        "(Win+Linux); fast-tier ⊂ slow-tier.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
