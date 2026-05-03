"""Phase 4 Session 11b — operational enforcement of P-1 §8.5.

Validates two install-matrix invariants per P-1 §8.5
(install-matrix gate; B-Phase4-S5-4 banking) using
``tools/reference_parity/harness/MANIFEST.toml`` as the
authoritative package list:

  Rule 1 (MANIFEST → slow-tier full coverage). Every
    package pinned in MANIFEST.toml must appear in BOTH
    parity-slow.yml jobs (Windows + Linux). Slow-tier
    install runs the full reference manifest because every
    check class imports at runner-discovery time regardless
    of tier (Phase 3.5 S1 Item 4 protocol).

  Rule 2 (fast-tier ⊂ slow-tier subset preservation). Every
    package in parity-fast.yml install lines must also
    appear in slow-tier install lines. Fast-tier is
    intentionally a subset of slow-tier; an addition that
    lands on fast but not slow (the BVAR S5 case) is the
    gap §8.5 exists to catch.

NOT enforced: "every MANIFEST package must be in fast-tier"
— fast-tier is documented as a subset (see parity-fast.yml
"Install fast-tier R packages" comment). Linux-only packages
(x13binary, seasonal) appear in slow-tier Linux install but
not in MANIFEST; the check is one-directional, so these
extras don't violate the gate.

Belt-and-suspenders pattern: this script runs as a local
pre-commit hook AND as a CI step in parity-fast.yml. See
P-1 §13.5.4 (S1/S5 self-validating-irony case study) for
why prose discipline alone is insufficient.

Usage:
    python tools/validate_install_matrix.py

Exit codes:
    0 — install matrix consistent.
    1 — at least one gap; gaps printed to stderr.
"""

from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MANIFEST_PATH = REPO_ROOT / "tools" / "reference_parity" / "harness" / "MANIFEST.toml"
PARITY_FAST_YML = REPO_ROOT / ".github" / "workflows" / "parity-fast.yml"
PARITY_SLOW_YML = REPO_ROOT / ".github" / "workflows" / "parity-slow.yml"


def parse_manifest() -> tuple[set[str], set[str]]:
    """Return (python_packages, r_packages) sets from MANIFEST.toml."""
    with MANIFEST_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    py_pkgs = set((data.get("python", {}).get("packages") or {}).keys())
    r_pkgs = set((data.get("r", {}).get("packages") or {}).keys())
    return py_pkgs, r_pkgs


def _normalize(name: str) -> str:
    """Lowercase + strip pip-version-pin suffix and quotes."""
    name = name.strip().strip('"').strip("'")
    for op in ("==", ">=", "<=", "~=", ">", "<"):
        if op in name:
            name = name.split(op, 1)[0]
            break
    return name.lower()


def parse_pip_install_lines(yml_text: str) -> set[str]:
    """Extract Python packages from ``python -m pip install`` lines
    (canonical command form; rejects prose "pip install" in comments)."""
    pkgs: set[str] = set()
    for match in re.finditer(
        r"python\s+-m\s+pip\s+install\s+([^\n]+)", yml_text,
    ):
        for tok in match.group(1).split():
            if tok.startswith(("-", "http")):
                continue
            pkgs.add(_normalize(tok))
    return {p for p in pkgs if p}


def parse_r_install_packages(yml_text: str) -> set[str]:
    """Extract R packages from ``install.packages(c(...))`` blocks
    (multi-line + R `#` comment tolerant)."""
    pkgs: set[str] = set()
    for match in re.finditer(r"install\.packages\s*\(", yml_text):
        start = match.end()
        depth, i = 1, start
        while i < len(yml_text) and depth > 0:
            depth += {"(": 1, ")": -1}.get(yml_text[i], 0)
            i += 1
        block = re.sub(r"#[^\n]*", "", yml_text[start : i - 1])
        for quoted in re.findall(r'"([^"]+)"', block):
            if quoted.startswith("http"):
                continue
            pkgs.add(_normalize(quoted))
    return pkgs


def _parse_slow_tier_jobs(slow_yml: str) -> tuple[set[str], set[str]]:
    """Split slow-tier YAML on ``slow-linux:`` job marker;
    return (slow_windows_r, slow_linux_r)."""
    if "slow-linux:" in slow_yml:
        idx = slow_yml.index("slow-linux:")
        windows_block, linux_block = slow_yml[:idx], slow_yml[idx:]
    else:
        windows_block, linux_block = slow_yml, ""
    return parse_r_install_packages(windows_block), parse_r_install_packages(linux_block)


def _check_manifest_in_surface(
    surface_name: str, surface_pkgs: set[str], manifest_pkgs: set[str], family: str,
) -> list[str]:
    """Rule 1: every MANIFEST package must appear in this surface."""
    missing = {_normalize(p) for p in manifest_pkgs} - surface_pkgs
    return [
        f"  {family} package '{pkg}' in MANIFEST.toml but missing from {surface_name}"
        for pkg in sorted(missing)
    ]


def _check_fast_subset_of_slow(
    fast_pkgs: set[str], slow_pkgs: set[str], family: str,
) -> list[str]:
    """Rule 2: every fast-tier package must appear in slow-tier."""
    return [
        f"  {family} package '{pkg}' in parity-fast.yml install line "
        f"but missing from parity-slow.yml install line "
        f"(fast-tier MUST be a subset of slow-tier per P-1 §8.5)"
        for pkg in sorted(fast_pkgs - slow_pkgs)
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

    violations: list[str] = []
    # Rule 1: MANIFEST → slow-tier (Python install + both R jobs).
    violations += _check_manifest_in_surface(
        "parity-slow.yml (Python install)", slow_py, py_manifest, "Python",
    )
    violations += _check_manifest_in_surface(
        "parity-slow.yml Windows job (R install.packages)",
        slow_windows_r, r_manifest, "R",
    )
    violations += _check_manifest_in_surface(
        "parity-slow.yml Linux job (R install.packages)",
        slow_linux_r, r_manifest, "R",
    )
    # Rule 2: fast-tier ⊂ slow-tier.
    violations += _check_fast_subset_of_slow(fast_py, slow_py, "Python")
    violations += _check_fast_subset_of_slow(fast_r, slow_windows_r, "R")

    if violations:
        print("\nERROR: install-matrix gaps detected (P-1 §8.5):", file=sys.stderr)
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
        "(Win+Linux); fast-tier subset of slow-tier.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
