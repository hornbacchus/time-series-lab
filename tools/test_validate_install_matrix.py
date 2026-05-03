"""Unit tests for tools/validate_install_matrix.py.

Exercises the parsing helpers + check rules against synthetic
fixtures. Validates:
  - Multi-line ``install.packages(c(...))`` parsing.
  - Pip install line parsing with version pins + flags.
  - Comment-line tolerance (R `#` and YAML `#`).
  - Quote-style tolerance.
  - Linux-only package allowlist (NOT enforced; one-directional check).
  - Rule 1 enforcement (MANIFEST → slow-tier).
  - Rule 2 enforcement (fast-tier ⊂ slow-tier).

Run from repo root:
    python tools/test_validate_install_matrix.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import validate_install_matrix as vim  # type: ignore


_FAILURES: list[str] = []


def _assert(condition: bool, msg: str) -> None:
    if not condition:
        _FAILURES.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  PASS: {msg}")


def test_normalize() -> None:
    print("\n=== test_normalize ===")
    _assert(vim._normalize("BVAR") == "bvar", "lowercase")
    _assert(vim._normalize('"BVAR"') == "bvar", "strip double quotes")
    _assert(vim._normalize("'BVAR'") == "bvar", "strip single quotes")
    _assert(vim._normalize("torch==2.11.0") == "torch", "strip == version pin")
    _assert(vim._normalize("ewstools>=2.0") == "ewstools", "strip >= pin")
    _assert(vim._normalize("  BVAR  ") == "bvar", "strip whitespace")


def test_parse_pip_install_simple() -> None:
    print("\n=== test_parse_pip_install_simple ===")
    yml = """
    - name: install
      run: |
        python -m pip install numpy scipy pandas torch==2.11.0
    """
    pkgs = vim.parse_pip_install_lines(yml)
    _assert("numpy" in pkgs, "numpy detected")
    _assert("scipy" in pkgs, "scipy detected")
    _assert("torch" in pkgs, "torch detected (pin stripped)")


def test_parse_pip_install_with_flags() -> None:
    print("\n=== test_parse_pip_install_with_flags ===")
    yml = """
        python -m pip install --upgrade pip
        python -m pip install --index-url https://download.pytorch.org/whl/cpu torch==2.11.0
        python -m pip install scipy pmdarima
    """
    pkgs = vim.parse_pip_install_lines(yml)
    _assert("torch" in pkgs, "torch detected past --index-url flag")
    _assert("scipy" in pkgs, "scipy detected on subsequent line")
    _assert("--upgrade" not in pkgs, "--upgrade flag not in pkgs")
    _assert("https://download.pytorch.org/whl/cpu" not in pkgs, "URL not in pkgs")


def test_parse_r_install_packages_singleline() -> None:
    print("\n=== test_parse_r_install_packages_singleline ===")
    yml = """
        install.packages(c("hts", "BVAR"), repos = "https://cloud.r-project.org")
    """
    pkgs = vim.parse_r_install_packages(yml)
    _assert("hts" in pkgs, "hts detected single-line")
    _assert("bvar" in pkgs, "bvar detected single-line + lowercased")
    _assert("https://cloud.r-project.org" not in pkgs, "repos URL excluded")


def test_parse_r_install_packages_multiline() -> None:
    print("\n=== test_parse_r_install_packages_multiline ===")
    yml = """
        install.packages(
            c("hts", "stochvol",
              "urca", "extRemes",
              # Phase 4 Session 5 addition:
              "BVAR"),
            repos = "https://cloud.r-project.org"
        )
    """
    pkgs = vim.parse_r_install_packages(yml)
    _assert(pkgs == {"hts", "stochvol", "urca", "extremes", "bvar"},
            f"all 5 R packages detected across multi-line; got {pkgs}")


def test_r_comment_tolerance() -> None:
    print("\n=== test_r_comment_tolerance ===")
    yml = '''
        install.packages(
            c("hts",
              # comment with quoted "FAKE_PKG" inside should NOT be parsed
              "BVAR"),
            repos = "https://cloud.r-project.org"
        )
    '''
    pkgs = vim.parse_r_install_packages(yml)
    _assert("fake_pkg" not in pkgs, "quoted token inside R comment excluded")
    _assert("hts" in pkgs and "bvar" in pkgs, "real entries detected")


def test_rule1_manifest_in_surface() -> None:
    print("\n=== test_rule1_manifest_in_surface ===")
    manifest = {"BVAR", "hts", "stochvol"}
    surface = {"hts", "stochvol"}  # missing BVAR
    violations = vim._check_manifest_in_surface(
        "test.yml", surface, manifest, "R",
    )
    _assert(len(violations) == 1, "one missing package detected")
    _assert("bvar" in violations[0].lower(), "BVAR named in violation")

    violations_clean = vim._check_manifest_in_surface(
        "test.yml", {"hts", "stochvol", "bvar"}, manifest, "R",
    )
    _assert(violations_clean == [], "clean state returns empty violations")


def test_rule2_fast_subset_of_slow() -> None:
    print("\n=== test_rule2_fast_subset_of_slow ===")
    fast = {"BVAR", "forecast"}
    slow = {"forecast", "stochvol"}  # missing BVAR
    violations = vim._check_fast_subset_of_slow(fast, slow, "R")
    _assert(len(violations) == 1, "one fast-not-in-slow detected")
    _assert("bvar" in violations[0].lower(), "BVAR named in violation")

    violations_clean = vim._check_fast_subset_of_slow(
        {"forecast"}, {"forecast", "stochvol"}, "R",
    )
    _assert(violations_clean == [], "fast subset of slow returns empty violations")


def test_slow_tier_jobs_split() -> None:
    print("\n=== test_slow_tier_jobs_split ===")
    yml = """
jobs:
  slow:
    runs-on: windows-latest
    steps:
      - shell: Rscript {0}
        run: |
          install.packages(c("WIN_PKG"), repos = "X")
  slow-linux:
    runs-on: ubuntu-latest
    steps:
      - shell: Rscript {0}
        run: |
          install.packages(c("LIN_PKG", "WIN_PKG"), repos = "X")
    """
    win_r, lin_r = vim._parse_slow_tier_jobs(yml)
    _assert("win_pkg" in win_r, "Windows pkg in win_r")
    _assert("win_pkg" in lin_r, "Windows pkg also expected in lin_r")
    _assert("lin_pkg" not in win_r, "Linux-only pkg NOT in win_r")
    _assert("lin_pkg" in lin_r, "Linux pkg in lin_r")


def test_real_manifest_clean() -> None:
    print("\n=== test_real_manifest_clean (live state check) ===")
    rc = vim.main()
    _assert(rc == 0, f"live install matrix passes; exit code {rc}")


if __name__ == "__main__":
    test_normalize()
    test_parse_pip_install_simple()
    test_parse_pip_install_with_flags()
    test_parse_r_install_packages_singleline()
    test_parse_r_install_packages_multiline()
    test_r_comment_tolerance()
    test_rule1_manifest_in_surface()
    test_rule2_fast_subset_of_slow()
    test_slow_tier_jobs_split()
    test_real_manifest_clean()

    if _FAILURES:
        print(f"\n{len(_FAILURES)} failures:")
        for f in _FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("\nAll tests PASSED.")
    sys.exit(0)
