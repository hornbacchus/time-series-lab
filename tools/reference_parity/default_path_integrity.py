"""default_path_integrity — empirical dialog-default smoke sweep (read-but-crashes axis).

★ HONEST LABEL: this guards the DEFAULT-PATH INTEGRITY of every dialog — that a
technique run with its FULL dialog-default parameter set, typed exactly as the
add-in EMITS it, does not fail. It is the empirical sibling of
catalog_key_alignment (which checks key ALIGNMENT structurally and is, by
construction, name-blind to this class): vecm's coint_rank="auto" crashed at
its own dialog DEFAULT while the key-alignment guard stayed green.

EMISSION FIDELITY (read from the C# source, the single emission rule):
TechniqueParameterItem.OutputValue (src/TSL.UI/ViewModels/
TechniqueExplorerViewModel.cs): bool -> bool; int -> int.TryParse(str(default))
else THE RAW STRING; float/double -> double.TryParse else the raw string;
string -> the string as-is. Defaults populate via Default?.ToString() ?? "".
★ F1 (the addin: GetParametersDict fix): an EMPTY value is "unset" -- the dict
builder OMITS the key (string.IsNullOrWhiteSpace skip), so a null catalog
default or a cleared box no longer emits "" (the ""-emission class is closed
at the source; key-absent -> the engine's own default). Both TaskPaneManager
consumers (l.445 workbook path, l.843 generic run dispatch) pass the dict
verbatim. The constructor below replicates the post-F1 rule exactly (the
empty-skip mirrored as str.strip() == "").

RUN IDENTITY: pane-style run_ids (NOT "udf_"-prefixed) so run_id-gated engine
branches take the DIALOG path -- e.g. adf_test's _is_triage_mode routes udf_*
to single-test (UDF back-compat) and pane/ribbon run_ids to triage; a dialog
run is the triage branch. The sweep simulates a dialog run, not a harness run.

DESIGN (baseline-control): each technique runs TWICE on the same fixture --
(i) NO-params baseline, (ii) the dialog-default param set. Four quadrants:
  baseline OK + default OK      -> PASS
  baseline OK + default FAIL    -> ★ FINDING (the param set caused it)
  baseline FAIL + default OK    -> params-required (recorded, not a finding)
  baseline FAIL + default FAIL  -> fixture-inadequate -> DISCLOSED exclusion
A baseline failure trivially attributable to input shape gets ONE cheap retry
with the obvious shape before exclusion (both attempts recorded).

Usage:
    python default_path_integrity.py            # CHECK: exit 1 on NEW findings
                                                #        beyond the baseline
    python default_path_integrity.py --report   # full per-technique table

KNOWN_DEFAULT_FAILURES is a documented baseline of the findings that exist
today (disclosure, not fixing -- fixes are adjudicated separately). The tool
fails only on NEW findings; a baselined entry that passes prints a
stale-baseline nudge (fix-confirmation semantics, same as the inert guard).
"""

from __future__ import annotations

import json
import os
import sys
import time
import warnings

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_CATALOG = os.path.join(_ROOT, "resources", "catalog", "techniques_catalog.json")
sys.path.insert(0, os.path.join(_ROOT, "engine"))

# Bespoke pane paths: the generic emission does not apply (BYF sends a CURATED
# whitelist, breakeven an EMPTY list; both are workbook-input).
EXCLUDED = {
    "bond_yield_forecast": "bespoke pane (curated param whitelist + workbook input)",
    "breakeven_payroll": "bespoke pane (empty param list + workbook input)",
}

# ★ Findings baseline (disclosure): baseline-success + dialog-default-failure,
# AS MEASURED by the first full sweep (2026-06-11, HEAD 36589d3, 16 findings,
# runtime 224s). Each entry is a control-level defect pending separate
# adjudication. Trim an entry when its fix lands (the tool then nudges if it
# stops failing). Shapes: ""-class = a null-default numeric control emits ""
# (int()/float() crash); "auto"-class = a string "auto" catalog default the
# engine does not sentinel-handle (the adf/k_ar_diff shape, un-wired);
# vocab = a catalog default value outside the engine's accepted set;
# type = a structural type-handling crash.
KNOWN_DEFAULT_FAILURES: dict[str, str] = {
    # ★ BASELINE EMPTIED 2026-06-12 — the default-path fix program is COMPLETE
    # and this tool is henceforth a PURE REGRESSION GUARD (exit 1 on ANY
    # finding). The arc, for the record:
    #   - the ""-class x7: FIXED at the C# source (F1, addin: GetParametersDict
    #     omits empty values, d7d48b8) — null-default/cleared boxes now emit
    #     key-absent.
    #   - the "auto"-class x4 (mstl periods, ssa window_length, wavelet level,
    #     pelt penalty at BOTH read sites): engine string-sentinel branches —
    #     "auto"/""/"none" -> the verified-adaptive absent path; explicit
    #     values/tokens byte-identical (F2, the engine: commit of this unit).
    #   - vocabulary x2: catalog corrections — denton method chow_lin->chowlin;
    #     particle_filter options -> the engine's real 4-token set, default
    #     local_level (preserve-delivered) (F3, same commit).
    #   - type x3: arimax order string parse ("auto"->auto-select; "1,1,1"->
    #     tuple — BOTH dialog paths were dead pre-fix); nbeats stack_types
    #     str->split->list; tcn n_channels int->preset-depth list (F3, same
    #     commit).
    # Each fix verified: auto==absent byte-identical (nan-aware), explicit
    # values land, sentinels unchanged, and the two-run protocol went
    # stale-on-exactly-the-9 -> trim -> clean PASS at 0.
}


def _emit(ptype, default):
    """Replicate TechniqueParameterItem.OutputValue for the dialog-DEFAULT
    state: StringValue = Default?.ToString() ?? ''."""
    t = (ptype or "string").lower()
    if t == "bool":
        return bool(default) if isinstance(default, bool) else False
    s = "" if default is None else str(default)
    if t == "int":
        try:
            return int(s)
        except ValueError:
            return s  # the raw string -- including "" for null defaults
    if t in ("float", "double"):
        try:
            return float(s)
        except ValueError:
            return s
    return s  # string / dropdown


def _techniques():
    with open(_CATALOG, encoding="utf-8") as fh:
        cat = json.load(fh)
    out = []

    def walk(o):
        if isinstance(o, dict):
            if "id" in o and isinstance(o.get("parameters"), list):
                out.append(o)
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(cat)
    return out


def _fixture(k: int, n: int = 240):
    """k correlated positive series with trend + seasonality + noise."""
    import numpy as np
    rng = np.random.default_rng(42)
    base = (np.cumsum(rng.standard_normal(n) * 0.4)
            + 6.0 * np.sin(np.arange(n) * 2 * np.pi / 12) + 60.0)
    series = []
    for i in range(k):
        y = base * (0.7 + 0.3 * (i + 1)) + np.cumsum(rng.standard_normal(n) * 0.3)
        series.append({"name": f"s{i+1}", "values": [float(v) for v in (y - y.min() + 5.0)]})
    return series


def _run(tid, series, params):
    """One engine invocation; returns (status, error_text)."""
    from techniques.base import RunContext  # type: ignore
    from techniques import registry  # type: ignore
    import importlib
    mod_path = registry.TECHNIQUE_REGISTRY.get(tid)
    if not mod_path:
        return "no-module", "not in registry"
    try:
        mod = importlib.import_module(mod_path)
    except Exception as e:
        return "import-error", f"{type(e).__name__}: {e}"
    n = len(series[0]["values"])
    ctx = RunContext({
        # pane-style run_id (NOT udf_-prefixed): run_id-gated branches take the
        # dialog path (e.g. adf triage), simulating a dialog run.
        "run_id": f"dpi_{tid}", "technique_id": tid,
        # frequency "M" matches the fixture's 12-period seasonality so
        # period-inferring techniques (stl/classical/...) baseline cleanly.
        "preset": "Balanced", "seed": 42, "frequency": "M",
        "time": list(range(n)), "series": series, "params": params,
    })
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            r = mod.run(ctx, lambda *a, **k: None)
        st = r.get("status", "no-status")
        return ("ok", "") if st == "success" else ("fail", str(r.get("error_message", ""))[:140])
    except Exception as e:
        return "exception", f"{type(e).__name__}: {str(e)[:120]}"


def sweep():
    results = {}
    for entry in _techniques():
        tid = entry["id"]
        if tid in EXCLUDED:
            results[tid] = {"quadrant": "EXCLUDED", "reason": EXCLUDED[tid]}
            continue
        k = max(1, int(entry.get("min_series") or 1))
        series = _fixture(k)
        defaults = {p["name"]: _emit(p.get("type"), p.get("default"))
                    for p in entry["parameters"] if p.get("name")}
        # F1 mirror (the C# GetParametersDict empty-skip): an empty emission is
        # "unset" -- the key is omitted, the engine applies its own default.
        defaults = {k: v for k, v in defaults.items()
                    if not (isinstance(v, str) and v.strip() == "")}
        t0 = time.time()
        b_st, b_err = _run(tid, series, {})
        # cheap retry: a baseline failure trivially attributable to input shape
        retried = None
        if b_st != "ok" and k == 1 and any(
                w in (b_err or "").lower()
                for w in ("series", "exog", "column", "two", "second", "at least 2")):
            series = _fixture(3)
            retried = (b_st, b_err)
            b_st, b_err = _run(tid, series, {})
        d_st, d_err = _run(tid, series, defaults)
        dt = time.time() - t0
        if b_st == "ok" and d_st == "ok":
            quad = "PASS"
        elif b_st == "ok":
            quad = "FINDING"      # baseline OK + default FAIL
        elif d_st == "ok":
            quad = "PARAMS-REQUIRED"  # baseline FAIL + default OK
        else:
            quad = "FIXTURE-EXCLUDED"  # both fail -> disclosed exclusion
        results[tid] = {"quadrant": quad, "baseline": (b_st, b_err),
                        "default": (d_st, d_err), "defaults_sent": defaults,
                        "retried_first_attempt": retried, "secs": round(dt, 1)}
    return results


def main(argv):
    report = "--report" in argv
    t0 = time.time()
    results = sweep()
    total_dt = time.time() - t0
    scanned = [t for t, r in results.items() if r["quadrant"] != "EXCLUDED"]
    findings = {t: r for t, r in results.items() if r["quadrant"] == "FINDING"}
    fixture_excl = {t: r for t, r in results.items() if r["quadrant"] == "FIXTURE-EXCLUDED"}

    print("# default_path_integrity - empirical dialog-default sweep (read-but-crashes axis)")
    print(f"# scanned: {len(scanned)} | bespoke-excluded: {len(EXCLUDED)} | "
          f"fixture-excluded: {len(fixture_excl)} | findings: {len(findings)} | "
          f"runtime: {total_dt:.0f}s")

    if report:
        print("\n## Full table (quadrant | baseline | dialog-default)")
        for tid, r in sorted(results.items()):
            if r["quadrant"] == "EXCLUDED":
                print(f"  {tid}: EXCLUDED ({r['reason']})")
                continue
            b, d = r["baseline"], r["default"]
            line = f"  {tid}: {r['quadrant']} | baseline={b[0]} | default={d[0]} ({r['secs']}s)"
            if b[0] != "ok":
                line += f"\n      baseline-err: {b[1]}"
            if d[0] != "ok":
                line += f"\n      default-err:  {d[1]}"
            if r.get("retried_first_attempt"):
                line += f"\n      first-attempt(1-series): {r['retried_first_attempt']}"
            print(line)

    new = {t: r for t, r in findings.items() if t not in KNOWN_DEFAULT_FAILURES}
    stale = [t for t in KNOWN_DEFAULT_FAILURES
             if results.get(t, {}).get("quadrant") not in ("FINDING", None)]

    if stale:
        print("\n## STALE baseline (default path now OK - trim from KNOWN_DEFAULT_FAILURES):")
        for t in sorted(stale):
            print(f"  {t}")
    if new:
        print("\n## [FAIL] NEW default-path failures (not in the baseline):")
        for t, r in sorted(new.items()):
            print(f"  {t}: {r['default'][1]}")
        return 1
    print("\n## [PASS] no NEW default-path failures beyond the known baseline.")
    print(f"   (baselined findings pending adjudication: {len(KNOWN_DEFAULT_FAILURES)})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
