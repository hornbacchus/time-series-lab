"""Phase 4 Session 11b — operational enforcement of P-1 §8.5.

Validates the install-matrix invariants per P-1 §8.5
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

  H1 (2026-09-30) — DP1: every environment that certifies the engine
  runs the validated versions (CI had installed unpinned packages and
  went red on statsmodels 0.15.0 / hierarchicalforecast 1.5.3):

  Rule 3 (pinned installs). Every ``python -m pip install`` in a gating
    job installs only exact pins: ``name==version`` tokens or ``-r``
    lock files whose every line is ``name==version``.

  Rule 4 (MANIFEST == locks). A Python package pinned in MANIFEST.toml
    and in the locks has the same version in both.

  Rule 5 (dated R snapshot). Every ``install.packages`` in a gating job
    installs from one dated Posit Package Manager snapshot
    (``https://packagemanager.posit.co/cran/YYYY-MM-DD``), not "latest"
    CRAN — CRAN moved (and archived tsDyn) under the same command.

  Gating jobs: parity-fast.yml's ``fast`` job, both parity-slow.yml jobs.
  parity-fast.yml's ``canary`` job (everything after its ``canary:`` job
  marker) resolves the LATEST versions on purpose and is exempt.

``-r <file>`` install tokens are read (relative to the repo root) so the
rules see the packages the lock files install.

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

# Job marker splitting parity-fast.yml: the pinned ``fast`` job before it,
# the unpinned drift canary (and its summary) after it.
CANARY_JOB_MARKER = "\n  canary:"

# pip options that consume the next token (never a package name).
_PIP_VALUE_OPTIONS = {
    "-i", "--index-url", "--extra-index-url", "-f", "--find-links",
    "-c", "--constraint", "--target", "-t", "--prefix", "--root",
}
_REQUIREMENT_OPTIONS = {"-r", "--requirement"}
_EXACT_PIN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.\-]*==[^\s=<>~!]+")
_SNAPSHOT_REPO = re.compile(
    r"https://packagemanager\.posit\.co/cran/(?:__linux__/[a-z0-9]+/)?(\d{4}-\d{2}-\d{2})"
)


def parse_manifest() -> tuple[set[str], set[str]]:
    """Return (python_packages, r_packages) sets from MANIFEST.toml."""
    with MANIFEST_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    py_pkgs = set((data.get("python", {}).get("packages") or {}).keys())
    r_pkgs = set((data.get("r", {}).get("packages") or {}).keys())
    return py_pkgs, r_pkgs


def parse_manifest_python_pins() -> dict[str, str]:
    with MANIFEST_PATH.open("rb") as fh:
        data = tomllib.load(fh)
    return {
        _canon(k): str(v)
        for k, v in (data.get("python", {}).get("packages") or {}).items()
    }


def _normalize(name: str) -> str:
    """Lowercase + strip pip-version-pin suffix and quotes."""
    name = name.strip().strip('"').strip("'")
    for op in ("==", ">=", "<=", "~=", ">", "<"):
        if op in name:
            name = name.split(op, 1)[0]
            break
    return name.lower()


def _canon(name: str) -> str:
    """PEP 503 name (MANIFEST keys and lock names spell some packages differently)."""
    return re.sub(r"[-_.]+", "-", _normalize(name))


def read_lock_file(rel_path: str) -> tuple[dict[str, str], list[str]]:
    """Return ({canonical name: version}, [non-exact-pin lines]) for a lock
    file referenced by ``-r`` (path relative to the repo root)."""
    path = REPO_ROOT / rel_path
    pins: dict[str, str] = {}
    bad: list[str] = []
    if not path.is_file():
        return pins, [f"<missing lock file {rel_path}>"]
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if _EXACT_PIN.fullmatch(line):
            name, version = line.split("==", 1)
            pins[_canon(name)] = version
        else:
            bad.append(line)
    return pins, bad


def _pip_install_token_lists(yml_text: str) -> list[list[str]]:
    return [
        m.group(1).split()
        for m in re.finditer(r"python\s+-m\s+pip\s+install\s+([^\n]+)", yml_text)
    ]


def _walk_pip_tokens(tokens: list[str]):
    """Yield ('pkg', token) / ('req', path) for one install line."""
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        if tok in _REQUIREMENT_OPTIONS and i + 1 < len(tokens):
            yield "req", tokens[i + 1]
            i += 2
            continue
        if tok.startswith("--requirement="):
            yield "req", tok.split("=", 1)[1]
        elif tok in _PIP_VALUE_OPTIONS:
            i += 2
            continue
        elif not tok.startswith(("-", "http")):
            yield "pkg", tok
        i += 1


def parse_pip_install_lines(yml_text: str) -> set[str]:
    """Extract Python packages from ``python -m pip install`` lines
    (canonical command form; rejects prose "pip install" in comments),
    including every package of the lock files installed with ``-r``."""
    pkgs: set[str] = set()
    for tokens in _pip_install_token_lists(yml_text):
        for kind, tok in _walk_pip_tokens(tokens):
            if kind == "req":
                pins, _ = read_lock_file(tok)
                pkgs.update(pins)
            else:
                pkgs.add(_canon(tok))
    return {p for p in pkgs if p}


def pip_pins(yml_text: str) -> dict[str, str]:
    """{package: version} for every exact pin a surface installs."""
    pins: dict[str, str] = {}
    for tokens in _pip_install_token_lists(yml_text):
        for kind, tok in _walk_pip_tokens(tokens):
            if kind == "req":
                pins.update(read_lock_file(tok)[0])
            elif _EXACT_PIN.fullmatch(tok):
                name, version = tok.split("==", 1)
                pins[_canon(name)] = version
    return pins


def unpinned_pip_installs(yml_text: str) -> list[str]:
    """Rule 3: every install token that is not an exact pin, and every
    non-pin line of an installed lock file."""
    out: list[str] = []
    for tokens in _pip_install_token_lists(yml_text):
        for kind, tok in _walk_pip_tokens(tokens):
            if kind == "req":
                out += [f"{tok}: {line}" for line in read_lock_file(tok)[1]]
            elif not _EXACT_PIN.fullmatch(tok):
                out.append(tok)
    return out


def _r_install_blocks(yml_text: str) -> list[str]:
    blocks: list[str] = []
    for match in re.finditer(r"install\.packages\s*\(", yml_text):
        start = match.end()
        depth, i = 1, start
        while i < len(yml_text) and depth > 0:
            depth += {"(": 1, ")": -1}.get(yml_text[i], 0)
            i += 1
        blocks.append(re.sub(r"#[^\n]*", "", yml_text[start : i - 1]))
    return blocks


def parse_r_install_packages(yml_text: str) -> set[str]:
    """Extract R packages from ``install.packages(c(...))`` blocks
    (multi-line + R `#` comment tolerant)."""
    pkgs: set[str] = set()
    for block in _r_install_blocks(yml_text):
        for quoted in re.findall(r'"([^"]+)"', block):
            if quoted.startswith("http"):
                continue
            pkgs.add(_normalize(quoted))
    return pkgs


def r_install_repos(yml_text: str) -> list[str]:
    """The ``repos =`` value of every install.packages block ('' if absent)."""
    out = []
    for block in _r_install_blocks(yml_text):
        m = re.search(r'repos\s*=\s*"([^"]+)"', block)
        out.append(m.group(1) if m else "")
    return out


def _parse_slow_tier_jobs(slow_yml: str) -> tuple[set[str], set[str]]:
    """Split slow-tier YAML on ``slow-linux:`` job marker;
    return (slow_windows_r, slow_linux_r)."""
    if "slow-linux:" in slow_yml:
        idx = slow_yml.index("slow-linux:")
        windows_block, linux_block = slow_yml[:idx], slow_yml[idx:]
    else:
        windows_block, linux_block = slow_yml, ""
    return parse_r_install_packages(windows_block), parse_r_install_packages(linux_block)


def split_fast_workflow(fast_yml: str) -> tuple[str, str]:
    """(gating ``fast`` job, exempt canary part) of parity-fast.yml."""
    idx = fast_yml.find(CANARY_JOB_MARKER)
    return (fast_yml, "") if idx < 0 else (fast_yml[:idx], fast_yml[idx:])


def _check_manifest_in_surface(
    surface_name: str, surface_pkgs: set[str], manifest_pkgs: set[str], family: str,
) -> list[str]:
    """Rule 1: every MANIFEST package must appear in this surface."""
    norm = _canon if family == "Python" else _normalize
    missing = {norm(p) for p in manifest_pkgs} - surface_pkgs
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


def _check_pinned(surface_name: str, yml_text: str) -> list[str]:
    """Rule 3."""
    return [
        f"  unpinned Python install in {surface_name}: '{tok}' "
        f"(DP1: install exact pins / lock files only)"
        for tok in unpinned_pip_installs(yml_text)
    ]


def _check_manifest_equals_locks(
    manifest_pins: dict[str, str], surface_pins: dict[str, str],
) -> list[str]:
    """Rule 4."""
    return [
        f"  Python package '{pkg}': MANIFEST.toml pins {manifest_pins[pkg]} "
        f"but the CI locks pin {surface_pins[pkg]}"
        for pkg in sorted(manifest_pins)
        if pkg in surface_pins and surface_pins[pkg] != manifest_pins[pkg]
    ]


def _check_r_snapshot(surfaces: dict[str, str]) -> list[str]:
    """Rule 5: one dated snapshot across every gating R install."""
    violations: list[str] = []
    dates: set[str] = set()
    for name, text in surfaces.items():
        for repo in r_install_repos(text):
            m = _SNAPSHOT_REPO.fullmatch(repo)
            if not m:
                violations.append(
                    f"  R install in {name} uses repos '{repo or '(none)'}': "
                    f"not a dated https://packagemanager.posit.co/cran/YYYY-MM-DD snapshot"
                )
            else:
                dates.add(m.group(1))
    if len(dates) > 1:
        violations.append(f"  R installs use different snapshot dates: {sorted(dates)}")
    return violations


def main() -> int:
    py_manifest, r_manifest = parse_manifest()
    print(
        f"MANIFEST.toml: {len(py_manifest)} Python packages, "
        f"{len(r_manifest)} R packages",
        file=sys.stderr,
    )

    fast_yml, _canary = split_fast_workflow(PARITY_FAST_YML.read_text(encoding="utf-8"))
    slow_yml = PARITY_SLOW_YML.read_text(encoding="utf-8")
    if "slow-linux:" in slow_yml:
        idx = slow_yml.index("slow-linux:")
        slow_win_yml, slow_lin_yml = slow_yml[:idx], slow_yml[idx:]
    else:
        slow_win_yml, slow_lin_yml = slow_yml, ""

    fast_py = parse_pip_install_lines(fast_yml)
    slow_py = parse_pip_install_lines(slow_win_yml) & parse_pip_install_lines(slow_lin_yml or slow_win_yml)
    fast_r = parse_r_install_packages(fast_yml)
    slow_windows_r, slow_linux_r = _parse_slow_tier_jobs(slow_yml)

    violations: list[str] = []
    # Rule 1: MANIFEST → slow-tier (Python install + both R jobs).
    violations += _check_manifest_in_surface(
        "parity-slow.yml (Python install, both jobs)", slow_py, py_manifest, "Python",
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
    # Rules 3-5 (H1 / DP1) over the gating jobs.
    surfaces = {
        "parity-fast.yml fast job": fast_yml,
        "parity-slow.yml Windows job": slow_win_yml,
        "parity-slow.yml Linux job": slow_lin_yml,
    }
    manifest_pins = parse_manifest_python_pins()
    for name, text in surfaces.items():
        violations += _check_pinned(name, text)
        violations += [f"{v} [{name}]" for v in
                       _check_manifest_equals_locks(manifest_pins, pip_pins(text))]
    violations += _check_r_snapshot(surfaces)

    if violations:
        print("\nERROR: install-matrix gaps detected (P-1 §8.5 / DP1):", file=sys.stderr)
        for v in violations:
            print(v, file=sys.stderr)
        print(
            "\nFix: add the missing packages to the listed workflow files "
            "(Python: regenerate the harness locks with "
            "tools/reference_parity/make_harness_lock.py on the dev interpreter). "
            "See P-1 §8.5 for the four-surface install-matrix gate.",
            file=sys.stderr,
        )
        return 1

    print(
        "OK — install matrix consistent: MANIFEST coverage in slow-tier "
        "(Win+Linux); fast-tier subset of slow-tier; gating installs pinned "
        "(locks == MANIFEST); R from one dated snapshot.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
