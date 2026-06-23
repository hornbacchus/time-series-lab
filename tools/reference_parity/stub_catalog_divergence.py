"""stub_catalog_divergence — regression sentinel for the hardcoded C# param stub.

★ FINDING (Phase 4a-audit #4): TechniqueExplorerViewModel.cs holds a hardcoded
DESIGN-TIME parameter stub (~8 techniques) that is a SECOND source of param truth
diverging from the JSON catalog. The stub is design-time-preview ONLY -- the real
run loads params from the JSON catalog via TaskPaneManager -- so the divergences
are cosmetic-to-the-run BUT a latent trap (a future reader trusting the stub). The
catalog is AUTHORITATIVE; the stub is documented-stale.

Disposition (Phase 4a-harden): (c) document the stub as design-time-only + THIS
guard, which sentinels the stub against NEW drift with no C# rebuild. (b) ELIMINATE
the stub (have the design-time preview read the catalog too, removing the second
source) is banked for the next C# build cycle.

What it checks (behaviorally-meaningful drift only; cosmetic label/advanced/
description are NOT compared): for each technique the stub DEFINES,
  - the technique exists in the catalog (else 'technique_stale');
  - each stub param exists in the catalog (else 'param_stub_only' -- the stub
    invented/kept a param the catalog doesn't have);
  - the stub param's default + type MATCH the catalog (else 'default_mismatch' /
    'type_mismatch').
The stub being an INCOMPLETE subset (omitting catalog params) is BY DESIGN (a
preview) and is NOT flagged. KNOWN_STUB_DIVERGENCE baselines today's divergences;
the guard fails (exit 1) only on a NEW one. A baselined divergence that is fixed
prints a stale-baseline nudge (same fix-confirmation semantics as the other guards).

Usage:
    python stub_catalog_divergence.py            # CHECK: exit 1 on NEW divergence
    python stub_catalog_divergence.py --report   # full divergence list
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_CATALOG = os.path.join(_ROOT, "resources", "catalog", "techniques_catalog.json")
_STUB = os.path.join(_ROOT, "src", "TSL.UI", "ViewModels", "TechniqueExplorerViewModel.cs")

# ★ KNOWN_STUB_DIVERGENCE baseline (Phase 4a-harden #4): the divergences that
# EXIST TODAY between the design-time C# stub and the authoritative JSON catalog.
# The catalog is correct; the stub is documented-stale. The guard fails only on a
# NEW divergence beyond this set. Shrink it when the stub is reconciled or
# eliminated (the (b) disposition, banked for the next C# build).
KNOWN_STUB_DIVERGENCE: set[str] = {
    # 3 stub techniques whose id no longer exists in the catalog:
    "adf_kpss_stationarity::technique_stale",
    "ets_forecast::technique_stale",          # catalog: ets_hw
    "rolling_correlation::technique_stale",    # catalog: rolling_ccf_lag
    # in-catalog stub techniques whose params diverge (default/type/stub-only):
    "stl_decompose.period::default_mismatch",          # stub 0 vs catalog null
    "auto_arima.ci_level::param_stub_only",            # stub-only; catalog has none
    "granger_causality.max_lag::default_mismatch",     # stub 4 vs catalog 12
    "prewhitened_ccf_lag.max_lag::default_mismatch",   # stub 20 vs catalog 30
}


def _norm_default(v):
    """Normalize a default to (kind, value) for cross-source comparison."""
    if v is None:
        return ("none", None)
    if isinstance(v, bool):
        return ("bool", v)
    if isinstance(v, (int, float)):
        return ("num", float(v))
    s = str(v).strip()
    return ("str", s)


def _catalog_params():
    with open(_CATALOG, encoding="utf-8") as fh:
        cat = json.load(fh)
    out = {}

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and isinstance(o.get("parameters"), list):
                out[o["id"]] = {
                    p["name"]: {"type": (p.get("type") or "").lower(),
                                "default": _norm_default(p.get("default"))}
                    for p in o["parameters"] if isinstance(p, dict) and p.get("name")
                }
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(cat)
    return out


def _csharp_default(expr: str):
    e = expr.strip().rstrip(",").strip()
    if e in ("true", "false"):
        return ("bool", e == "true")
    if e == "null":
        return ("none", None)
    if len(e) >= 2 and e[0] == '"' and e[-1] == '"':
        return ("str", e[1:-1])
    try:
        return ("num", float(e))
    except ValueError:
        return ("str", e)


def _stub_params():
    """Parse the hardcoded stub: {technique_id: {param: {type, default}}}."""
    with open(_STUB, encoding="utf-8") as fh:
        txt = fh.read()
    out = {}
    # Each technique block starts at Id = "..."; params are the
    # `new TechniqueParameterItem { ... }` initializers until the next Id.
    id_marks = [(m.start(), m.group(1)) for m in re.finditer(r'Id\s*=\s*"([a-z0-9_]+)"', txt)]
    for i, (pos, tid) in enumerate(id_marks):
        end = id_marks[i + 1][0] if i + 1 < len(id_marks) else len(txt)
        block = txt[pos:end]
        params = {}
        for item in re.finditer(r"new\s+TechniqueParameterItem\s*\{([^}]*)\}", block):
            body = item.group(1)
            nm = re.search(r'Name\s*=\s*"(\w+)"', body)
            if not nm:
                continue
            ty = re.search(r'Type\s*=\s*"(\w+)"', body)
            de = re.search(r'Default\s*=\s*([^,}]+)', body)
            params[nm.group(1)] = {
                "type": (ty.group(1).lower() if ty else ""),
                "default": _csharp_default(de.group(1)) if de else ("none", None),
            }
        out[tid] = params
    return out


def audit():
    cat = _catalog_params()
    stub = _stub_params()
    divergences = []  # (key, detail)
    for tid, params in stub.items():
        if tid not in cat:
            divergences.append((f"{tid}::technique_stale",
                                f"stub technique '{tid}' is not in the catalog"))
            continue
        for pname, sp in params.items():
            cp = cat[tid].get(pname)
            if cp is None:
                divergences.append((f"{tid}.{pname}::param_stub_only",
                                    f"stub defines '{pname}'; catalog has no such param"))
                continue
            if sp["default"] != cp["default"]:
                divergences.append((f"{tid}.{pname}::default_mismatch",
                                    f"default stub={sp['default']} catalog={cp['default']}"))
            if sp["type"] and cp["type"] and sp["type"] != cp["type"]:
                divergences.append((f"{tid}.{pname}::type_mismatch",
                                    f"type stub={sp['type']!r} catalog={cp['type']!r}"))
    return divergences


def main(argv):
    report = "--report" in argv
    divs = audit()
    keys = {k for k, _ in divs}
    print("# stub_catalog_divergence - C# design-time stub vs authoritative JSON catalog")
    print(f"# stub techniques: {len(_stub_params())} | divergences: {len(divs)}")
    if report:
        for k, d in sorted(divs):
            print(f"  {k}  --  {d}")
    new = sorted(k for k in keys if k not in KNOWN_STUB_DIVERGENCE)
    stale = sorted(k for k in KNOWN_STUB_DIVERGENCE if k not in keys)
    if stale:
        print("\n## STALE baseline (stub now matches the catalog - trim from KNOWN_STUB_DIVERGENCE):")
        for k in stale:
            print(f"  {k}")
    if new:
        print("\n## [FAIL] NEW stub<->catalog divergence(s) (not in the baseline):")
        for k in new:
            print(f"  {k}  --  {dict(divs)[k]}")
        print("\nThe design-time stub drifted further from the authoritative catalog. "
              "Reconcile the stub value to the catalog, or (preferred) ELIMINATE the "
              "stub so the design-time preview reads the catalog (removes the second "
              "source). Add to KNOWN_STUB_DIVERGENCE only with a justification.")
        return 1
    print("\n## [PASS] no NEW stub<->catalog divergence beyond the documented baseline.")
    print(f"   (baselined design-time-stub divergences: {len(KNOWN_STUB_DIVERGENCE)}; "
          f"the catalog is authoritative -- (b)-eliminate the stub banked for the next C# build)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
