"""Verify that a CI job's environment IS the validated environment (DP1).

Run right after the installs, before any check:

    python tools/check_pinned_env.py --lock engine/requirements.lock.txt \
        --lock engine/requirements.optional.lock.txt \
        --lock tools/reference_parity/requirements.harness.lock.txt \
        [--extras fail|warn] [--r-packages hts,forecast,...]

Python: every pin in the given lock files must be installed at exactly the
pinned version (a mismatch always fails). Any installed distribution that no
lock pins is an unvalidated package: it fails with --extras fail (CI jobs
install with --no-deps, so nothing else should be there) and warns with
--extras warn (the dev interpreter, which carries other packages).

Completeness: every requirement of every pinned distribution that applies on
this platform - honouring requested extras, e.g. hierarchicalforecast's
qpsolvers[clarabel] - must itself be pinned, and the installed version must
satisfy it. With --no-deps installs this is the only thing that proves the
locks are the whole closure (a missing clarabel once passed "0 wrong or
missing" while hierarchicalforecast could not be imported). An unpinned
requirement fails with --unpinned-requirements fail (Windows, and the dev
interpreter) and warns with warn (Linux, where platform-only requirements
such as xgboost's nvidia-nccl-cu12 are expected and unused on CPU). A
specifier the validated environment itself violates is allowed only by name
(KNOWN_SPECIFIER_CONFLICTS).

R (optional): every package in --r-packages must be installed (a missing one
always fails - install.packages() only warns, which is how tsDyn went missing
from CI unnoticed). Versions are compared with MANIFEST.toml's [r.packages]
pins and reported; a difference is a warning, because R versions come from a
dated package snapshot rather than a lock.

Exit 0 = the environment matches; 1 = it does not.
"""

from __future__ import annotations

import argparse
import importlib.metadata as md
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
MANIFEST = REPO / "tools" / "reference_parity" / "harness" / "MANIFEST.toml"
# Installer tooling, not part of any validated environment.
ALWAYS_ALLOWED = {"pip"}
# (package, requirement) pairs whose declared specifier the VALIDATED
# environment violates: particles 0.4 declares numpy<2 and runs, validated
# (p3_particle_filter PASS), on numpy 2.4.4.
KNOWN_SPECIFIER_CONFLICTS = {("particles", "numpy")}


def canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_pins(paths: list[str]) -> dict[str, tuple[str, str, str]]:
    pins: dict[str, tuple[str, str, str]] = {}
    for p in paths:
        path = (REPO / p) if not Path(p).is_absolute() else Path(p)
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            m = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.\-]*)==(\S+)", line)
            if not m:
                raise SystemExit(f"{p}: not an exact pin: {raw!r}")
            key = canon(m.group(1))
            if key in pins and pins[key][1] != m.group(2):
                raise SystemExit(
                    f"{m.group(1)} pinned twice with different versions: "
                    f"{pins[key][1]} ({pins[key][2]}) and {m.group(2)} ({p})"
                )
            pins[key] = (m.group(1), m.group(2), p)
    return pins


def annotate(level: str, msg: str) -> None:
    # GitHub Actions annotation when running in Actions; plain text otherwise.
    print(f"::{level}::{msg}" if "GITHUB_ACTIONS" in os.environ else f"{level.upper()}: {msg}")


def check_complete(pins: dict, dists: dict, mode: str) -> bool:
    """Every applicable requirement of every pinned distribution is pinned and
    satisfied (see the module docstring)."""
    from packaging.markers import default_environment
    from packaging.requirements import Requirement

    env = default_environment()
    reqs: dict[str, list] = {}
    for key in pins:
        dist = dists.get(key)
        if dist is not None:
            reqs[key] = [Requirement(r) for r in (dist.requires or [])]

    def applies(r, extras: set[str]) -> bool:
        return r.marker is None or any(r.marker.evaluate({**env, "extra": e}) for e in extras)

    # Active extras per distribution, to a fixpoint: an extra counts only when
    # an APPLICABLE requirement asks for it (astropy's own
    # "astropy[...]; extra == 'all'" must not switch on every extra).
    active: dict[str, set[str]] = {k: {""} for k in reqs}
    changed = True
    while changed:
        changed = False
        for key, rs in reqs.items():
            for r in rs:
                dep = canon(r.name)
                if r.extras and dep in active and applies(r, active[key]):
                    new = set(r.extras) - active[dep]
                    if new:
                        active[dep] |= new
                        changed = True
    ok = True
    unpinned = conflicts = 0
    for key, rs in sorted(reqs.items()):
        for r in rs:
            if not applies(r, active[key]):
                continue
            dep = canon(r.name)
            owner = pins[key][0]
            if dep not in pins:
                unpinned += 1
                where = "installed" if dep in dists else "NOT installed"
                annotate("error" if mode == "fail" else "warning",
                         f"{owner} requires {r} - pinned by no lock ({where}): the locks are not the whole closure")
                if mode == "fail":
                    ok = False
                continue
            if dep in dists and r.specifier and not r.specifier.contains(dists[dep].version, prereleases=True):
                if (key, dep) in KNOWN_SPECIFIER_CONFLICTS:
                    print(f"note: {owner} declares {r}; the validated environment runs "
                          f"{dists[dep].metadata['Name']} {dists[dep].version} (known, allowed by name)")
                else:
                    conflicts += 1
                    annotate("error", f"{owner} requires {r} but {dists[dep].metadata['Name']} "
                                      f"{dists[dep].version} is pinned")
                    ok = False
    print(f"Completeness: {unpinned} requirement(s) pinned by no lock ({mode}); "
          f"{conflicts} unexpected specifier conflict(s).")
    return ok


def check_python(lock_paths: list[str], extras_mode: str, unpinned_mode: str = "fail") -> bool:
    pins = read_pins(lock_paths)
    dists = {canon(d.metadata["Name"]): d for d in md.distributions()}
    inst = {k: (d.metadata["Name"], d.version) for k, d in dists.items()}
    ok = True
    wrong = [
        (n, v, inst[k][1] if k in inst else "NOT INSTALLED", src)
        for k, (n, v, src) in sorted(pins.items())
        if k not in inst or inst[k][1] != v
    ]
    for n, want, have, src in wrong:
        annotate("error", f"{n}: pinned {want} ({src}) but installed {have}")
        ok = False
    extras = sorted(inst[k] for k in inst if k not in pins and k not in ALWAYS_ALLOWED)
    for n, v in extras:
        annotate("error" if extras_mode == "fail" else "warning",
                 f"{n}=={v} is installed but pinned by no lock (unvalidated)")
    if extras and extras_mode == "fail":
        ok = False
    print(f"Python: {len(pins)} pins from {len(lock_paths)} lock file(s); "
          f"{len(wrong)} wrong or missing; {len(extras)} unpinned extra(s) ({extras_mode}).")
    ok &= check_complete(pins, dists, unpinned_mode)
    return ok


def check_r(packages: list[str]) -> bool:
    with MANIFEST.open("rb") as fh:
        manifest = tomllib.load(fh)
    manifest_r = manifest.get("r", {}).get("packages") or {}
    # Same lookup order as the harness (r_bridge._resolve_rscript_exe):
    # RSCRIPT_EXE, else the manifest's rscript_exe if it exists, else PATH;
    # the manifest's libs_user first on .libPaths() when it exists.
    manifest_rscript = manifest.get("r", {}).get("rscript_exe", "")
    rscript = next((c for c in (os.environ.get("RSCRIPT_EXE", ""), manifest_rscript)
                    if c and Path(c).exists()), None) or shutil.which("Rscript") or ""
    libs_user = manifest.get("r", {}).get("libs_user", "")
    prolog = (f".libPaths(c('{libs_user}', .libPaths())); "
              if libs_user and Path(libs_user).is_dir() else "")
    expr = prolog + "p <- c({}); cat(sprintf('%s=%s\\n', p, sapply(p, function(x) tryCatch(as.character(packageVersion(x)), error = function(e) 'MISSING'))), sep = '')".format(
        ", ".join(f'"{p}"' for p in packages))
    if not rscript or not Path(rscript).exists() and not shutil.which(rscript):
        annotate("error", "Rscript not found; cannot verify the R packages")
        return False
    out = subprocess.run([rscript, "-e", expr], capture_output=True, text=True, timeout=300)
    have = dict(line.split("=", 1) for line in out.stdout.splitlines() if "=" in line)
    ok = True
    missing = [p for p in packages if have.get(p, "MISSING") == "MISSING"]
    for p in missing:
        annotate("error", f"R package {p} is NOT installed (install.packages only warned)")
        ok = False
    for p in packages:
        pin = manifest_r.get(p)
        v = have.get(p, "MISSING")
        if pin and v != "MISSING" and v.replace("-", ".") != str(pin).replace("-", "."):
            annotate("warning", f"R package {p}: installed {v}, MANIFEST.toml pins {pin}")
    print(f"R: {len(packages)} package(s) required; {len(missing)} missing; "
          + ", ".join(f"{p} {have.get(p, 'MISSING')}" for p in packages))
    return ok


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify the CI environment against the locks.")
    ap.add_argument("--lock", action="append", default=[], help="lock file (repeatable)")
    ap.add_argument("--extras", choices=["fail", "warn"], default="fail",
                    help="installed distributions no lock pins")
    ap.add_argument("--unpinned-requirements", choices=["fail", "warn"], default="fail",
                    help="requirements of pinned distributions that no lock pins")
    ap.add_argument("--r-packages", default="", help="comma-separated R packages that must be installed")
    args = ap.parse_args()
    ok = True
    if args.lock:
        ok &= check_python(args.lock, args.extras, args.unpinned_requirements)
    if args.r_packages:
        ok &= check_r([p.strip() for p in args.r_packages.split(",") if p.strip()])
    print("ENVIRONMENT OK" if ok else "ENVIRONMENT DOES NOT MATCH THE VALIDATED ONE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
