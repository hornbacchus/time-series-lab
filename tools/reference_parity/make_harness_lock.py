"""Write the reference-parity harness lock files from the DEV interpreter.

DP1: every environment that certifies the engine runs the validated
versions. CI installs every Python package from lock files:

  engine/requirements.lock.txt             engine core (build_pack installs it)
  engine/requirements.optional.lock.txt    engine optional (build_pack installs it)
  tools/reference_parity/requirements.harness.lock.txt
      reference packages the fast tier imports, plus their whole dependency
      closure, minus anything the engine locks already pin
  tools/reference_parity/requirements.harness-slow.lock.txt
      what the slow tier adds on top (pymc / arviz / pyextremes / tbats ...)

This script NEVER resolves anything: it walks the installed metadata of the
interpreter running it (the dev interpreter that validated the engine) and
pins exactly what is installed. It refuses to write if the engine locks no
longer mirror that interpreter, because then there is no single validated
environment to pin.

CI installs these files with ``pip install --no-deps``: they are the whole
closure, and the validated set is not resolver-consistent (particles 0.4
declares numpy<2 but runs, validated, on numpy 2.4.4), so pip's resolver
would refuse it. tools/check_pinned_env.py then proves the installed set is
exactly the locks.

Usage (from the repo root, with the dev interpreter):
    python tools/reference_parity/make_harness_lock.py          # write
    python tools/reference_parity/make_harness_lock.py --check  # exit 1 if stale
"""

from __future__ import annotations

import argparse
import datetime as _dt
import importlib.metadata as md
import platform
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ENGINE_LOCKS = [
    REPO / "engine" / "requirements.lock.txt",
    REPO / "engine" / "requirements.optional.lock.txt",
]
HARNESS_LOCK = REPO / "tools" / "reference_parity" / "requirements.harness.lock.txt"
HARNESS_SLOW_LOCK = REPO / "tools" / "reference_parity" / "requirements.harness-slow.lock.txt"

# The packages the fast tier imports (engine wrappers + references). Their
# dependency closure is walked from installed metadata. MAPIE: the
# p3_conformal_cqr / p3_conformal_enbpi reference (CI never installed it, so
# p3_conformal_cqr SKIPped in CI while it PASSes on the dev interpreter).
FAST_ROOTS = (
    "numpy scipy pandas hierarchicalforecast statsmodels torch ewstools "
    "pmdarima arch scikit-learn hmmlearn particles ruptures astropy "
    "PyWavelets EMD-signal pyts xgboost lightgbm reservoirpy prophet "
    "dtaidistance numba PyYAML openpyxl MAPIE"
).split()
SLOW_ROOTS = FAST_ROOTS + "pyextremes tbats pymc arviz".split()


def canon(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def read_lock(path: Path) -> dict[str, tuple[str, str]]:
    pins: dict[str, tuple[str, str]] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        m = re.fullmatch(r"([A-Za-z0-9][A-Za-z0-9_.\-]*)==(\S+)", line)
        if not m:
            raise SystemExit(f"{path}: not an exact pin: {raw!r}")
        pins[canon(m.group(1))] = (m.group(1), m.group(2))
    return pins


def installed() -> dict[str, tuple[str, str, md.Distribution]]:
    out = {}
    for d in md.distributions():
        name = d.metadata["Name"]
        out[canon(name)] = (name, d.version, d)
    return out


def closure(roots: list[str], inst) -> dict[str, tuple[str, str]]:
    """Every distribution reachable from ``roots`` through installed
    Requires-Dist, honouring requested extras: ``qpsolvers[clarabel]`` (as
    hierarchicalforecast requires it) reaches clarabel through qpsolvers'
    ``extra == "clarabel"`` requirement. A node reached again with a new
    extra is walked again for that extra."""
    from packaging.markers import default_environment
    from packaging.requirements import Requirement

    env = default_environment()
    seen: dict[str, tuple[str, str]] = {}
    walked: dict[str, set[str]] = {}  # key -> extras already expanded ("" = base)
    missing: list[str] = []
    stack: list[tuple[str, frozenset[str]]] = [(canon(r), frozenset()) for r in roots]
    while stack:
        key, extras = stack.pop()
        if key not in inst:
            missing.append(key)
            continue
        wanted = {""} | set(extras)
        todo = wanted - walked.get(key, set())
        if not todo:
            continue
        walked.setdefault(key, set()).update(todo)
        name, ver, dist = inst[key]
        seen[key] = (name, ver)
        for req in dist.requires or []:
            r = Requirement(req)
            if r.marker is not None and not any(
                r.marker.evaluate({**env, "extra": e}) for e in todo
            ):
                continue
            stack.append((canon(r.name), frozenset(r.extras)))
    if missing:
        raise SystemExit(
            "Not installed on this interpreter (cannot pin what was never "
            f"validated): {sorted(set(missing))}"
        )
    return seen


def render(title: str, pins: dict[str, tuple[str, str]]) -> str:
    today = _dt.date.today().isoformat()
    head = [
        f"# {title}",
        "# GENERATED by tools/reference_parity/make_harness_lock.py from the dev",
        f"# interpreter's installed metadata (Python {platform.python_version()}, "
        f"{sys.platform}), {today}.",
        "# Never a fresh resolve. Do not edit by hand: re-run the script on the",
        "# validated interpreter after a deliberate lock refresh.",
    ]
    body = [f"{n}=={v}" for _, (n, v) in sorted(pins.items())]
    return "\n".join(head + body) + "\n"


def pins_of(text: str) -> list[str]:
    return [l for l in text.splitlines() if l and not l.startswith("#")]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if the committed harness locks differ from this interpreter")
    args = ap.parse_args()

    inst = installed()
    engine: dict[str, tuple[str, str]] = {}
    for lock in ENGINE_LOCKS:
        engine.update(read_lock(lock))
    drift = [
        f"{n}=={v} (installed {inst[k][1] if k in inst else 'NOT INSTALLED'})"
        for k, (n, v) in sorted(engine.items())
        if k not in inst or inst[k][1] != v
    ]
    if drift:
        print("The engine locks no longer mirror this interpreter:", file=sys.stderr)
        for d in drift:
            print(f"  {d}", file=sys.stderr)
        return 1

    fast = {k: v for k, v in closure(FAST_ROOTS, inst).items() if k not in engine}
    slow = {k: v for k, v in closure(SLOW_ROOTS, inst).items() if k not in engine and k not in fast}
    fast_text = render(
        "Reference-parity harness lock (fast tier): reference packages + closure, "
        "beyond the engine locks.", fast)
    slow_text = render(
        "Reference-parity harness lock (slow-tier additions on top of the fast "
        "harness lock).", slow)

    if args.check:
        stale = []
        for path, text in ((HARNESS_LOCK, fast_text), (HARNESS_SLOW_LOCK, slow_text)):
            have = pins_of(path.read_text(encoding="utf-8")) if path.exists() else []
            if have != pins_of(text):
                stale.append(path.name)
        if stale:
            print(f"Stale vs this interpreter: {stale}", file=sys.stderr)
            return 1
        print("Harness locks match this interpreter.")
        return 0

    HARNESS_LOCK.write_text(fast_text, encoding="utf-8", newline="\n")
    HARNESS_SLOW_LOCK.write_text(slow_text, encoding="utf-8", newline="\n")
    print(f"{HARNESS_LOCK.relative_to(REPO)}: {len(fast)} pins")
    print(f"{HARNESS_SLOW_LOCK.relative_to(REPO)}: {len(slow)} pins")
    return 0


if __name__ == "__main__":
    sys.exit(main())
