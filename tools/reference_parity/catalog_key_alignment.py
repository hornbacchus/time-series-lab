"""catalog_key_alignment — structural guard for the inert-control defect class.

★ HONEST LABEL: this guards catalog<->engine KEY ALIGNMENT — that every dialog
control (`techniques_catalog.json` parameters[].name) is actually read by its
technique's engine `get_param`. It is NOT numerical parity; it is the structural
backstop for the INERT-CONTROL bug (a dialog control whose key the engine never
reads -> the user's setting is silently dropped; the Max Lags / k_ar_diff /
forecast_combination-models class).

Usage:
    python catalog_key_alignment.py            # CHECK: exit 1 if any NEW inert
                                               #        control (inert, not in
                                               #        KNOWN_INERT baseline)
    python catalog_key_alignment.py --report   # AUDIT: print every inert control
                                               #        (+ helper-suspect flags),
                                               #        for seeding / review

Disposition (b): KNOWN_INERT is a documented baseline of the inert controls that
EXIST TODAY (pending per-control fixes). The guard is GREEN for regressions —
it fails only on a NEW inert control not in the baseline. As each per-control
fix lands (rename the catalog key to the engine's, or wire the engine), remove
that control from KNOWN_INERT; the guard then enforces it stays fixed.
"""

from __future__ import annotations

import json
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, "..", ".."))
_CATALOG = os.path.join(_ROOT, "resources", "catalog", "techniques_catalog.json")
_REGISTRY = os.path.join(_ROOT, "engine", "techniques", "registry.py")
_ENGINE_DIR = os.path.join(_ROOT, "engine", "techniques")

_GET_PARAM = re.compile(r"get_param\(\s*\W(\w+)")

# ★ D-set allowlist (VERIFIED read-only): techniques whose config reaches the
# engine via a NON-get_param path, so a get_param scan is blind. Documented +
# auditable — NOT a silent skip. If an allowlisted technique later shows a
# control its documented path does not consume, re-classify it.
ALLOWLIST = {
    "bond_yield_forecast": "bespoke workbook-input; controls feed read_unified_workbook + _dispatch.py get_param, not ctx.params",
    "breakeven_payroll": "bespoke workbook-input package",
    "kalman_filter": "reads ctx.params via the _resolve_params(ctx) helper, not direct get_param",
    "kalman_smoother": "reads ctx.params via the _resolve_params(ctx) helper, not direct get_param",
    # 2026-06-12 (K2 exposure): Bespoke #3, the breakeven D-set shape --
    # workbook-input; the only catalog control (input_workbook) is consumed by
    # the dispatch's workbook reader, not via per-key get_param of dialog knobs.
    "kronos_forecast": "bespoke workbook-input (Kronos subprocess; experimental); knobs live in the workbook",
}

# ★ KNOWN_INERT baseline (disposition b) — the inert controls that exist today,
# pending per-control fixes. Seeded from the reconciled first-run audit. The
# guard fails only on inert controls NOT listed here. Shrink this as fixes land.
KNOWN_INERT: dict[str, list[str]] = {
    # Seeded from the reconciled first-run audit (robust scan == the sweep's 39;
    # D-set allowlisted). Classified for the per-control fix queue:
    #   A pure-rename (catalog key -> the engine key)
    #   B type/semantic-mismatch (needs the engine to accept the value/transform)
    #   C genuinely-absent (engine doesn't honor the concept -> wire or relabel)
    # Shrink this dict as each per-control fix lands. (# helper-suspect = the key
    # is read by SOME other technique's get_param, verified COINCIDENTAL common
    # key-name here, not a cross-module helper read.)
    # adf_test max_lags: FIXED (engine-wired -> max_lag with an "auto" string-
    # sentinel branch; Commit pending) -> removed from the baseline; the guard
    # now enforces it.
    # auto_arima ic: FIXED (engine-wired -> information_criterion; catalog
    # default corrected aicc->aic to state the delivered value; A-batch).
    "autoencoder_anomaly": ["threshold_sigma", "encoding_dim"],  # C
    "block_bootstrap": ["statistic"],                          # C
    "bocpd": ["hazard_rate"],                                  # B inverse of hazard_lambda
    # bvar lambda_shrinkage: FIXED (engine-wired -> lambda1; Commit pending) ->
    # removed from the baseline; the guard now enforces it.
    # caviar_quantile_dynamics quantile + model_type: FIXED (engine-wired ->
    # theta + specification via a value-map; Commit pending) -> removed from the
    # baseline; the guard now enforces them.
    # conformal_intervals coverage: FIXED (engine-wired -> confidence_level,
    # a clean same-quantity alias; Commit pending) -> removed from the baseline;
    # the guard now enforces it.
    # cusum_page_hinkley threshold/drift: FIXED (Fix B Tier 1c-3) -- the inert
    # catalog controls were renamed threshold->cusum_h, drift->cusum_k to match
    # the engine reads (null defaults preserved -> auto 5sigma/0.5sigma, byte-
    # identical) -> removed from the baseline; the guard now enforces them.
    "denton_chowlin_disaggregation": ["target_frequency"],     # B (vs conversion_ratio)
    "dtw_alignment_lag": ["max_warp"],                         # C (vs window_frac)
    "fft_spectrum": ["top_n"],                                 # A -> n_top
    # forecast_combination models + combination_method: FIXED (engine-wired,
    # Commit pending) -> removed from the baseline; the guard now enforces them.
    "forecast_reconciliation": ["hierarchy_table"],            # C (vs S_matrix)
    # gaussian_process_forecast max_lag: FIXED (Fix B Tier 1b-bis) -- the dead
    # catalog control was REMOVED (GP regresses value~time-index, no lag concept;
    # the engine never read it) -> removed from the baseline.
    # gradient_boosting_forecast max_lag: FIXED (Fix B Tier 1b-bis) -- catalog
    # control renamed max_lag -> n_lags to match the engine read (type-A);
    # default blank -> preset cfg (byte-identical) -> removed from the baseline.
    # har_rv horizon: FIXED (engine-wired -> h_ahead; catalog default corrected
    # 10->1 to state the delivered value; A-batch).
    "intervention_analysis": ["intervention_dates", "intervention_type"],  # C (vs interventions/order)
    # johansen_cointegration k_ar_diff: FIXED (engine-wired -> lag via the adf
    # string-sentinel pattern; catalog int->string default "auto"; A-batch).
    "lomb_scargle": ["min_period", "max_period"],              # B inverse (period=1/freq)
    # lstm_gru_forecast cell_type: FIXED (Fix B Tier 1b) -- the catalog control
    # was renamed cell_type -> model_type to match the engine read; default
    # "LSTM".lower() == the engine default "lstm" (byte-identical) -> removed from
    # the baseline; the guard now enforces it.
    "nar_narx": ["max_lag", "hidden_size"],                    # A -> ar_lags/hidden_layers
    "robust_estimators": ["trim_pct"],                         # B scale (x100 vs trim_fraction)
    "rolling_origin_cv": ["n_folds", "model"],                 # A n_folds->folds; model C
    # star max_lag/transition: FIXED (Fix B Tier 1c-3) -- the inert catalog
    # controls were renamed max_lag->ar_order, transition->star_type (and
    # transition's wrong options {logistic,exponential} -> the engine tokens
    # {LSTAR,ESTAR,both}); null defaults preserve the preset-aware/data-driven
    # engine defaults (Thorough star_type="both") -> removed from the baseline.
    "stl_decompose": ["seasonal_window"],                      # A/C -> seasonal (verify semantics)
    "structural_ts": ["trend"],                                # C (reads level/autoregressive)
    "tar_setar": ["max_lag"],                                  # A -> ar_order
    # vecm k_ar_diff: FIXED (engine-wired -> lag via the adf string-sentinel
    # pattern; catalog int->string default "auto"; the same unit also fixed the
    # vecm coint_rank="auto" default-path crash -- coint_rank was never
    # baselined here, the guard is name-blind to read-but-crashes; A-batch).
    "x13_seasonal_adjust": ["method"],                         # C
}


def _walk_techniques(obj, out):
    if isinstance(obj, dict):
        if "id" in obj and isinstance(obj.get("parameters"), list):
            names = [p.get("name") for p in obj["parameters"]
                     if isinstance(p, dict) and p.get("name")]
            out[obj["id"]] = names
        for v in obj.values():
            _walk_techniques(v, out)
    elif isinstance(obj, list):
        for v in obj:
            _walk_techniques(v, out)


def _catalog_controls():
    with open(_CATALOG, encoding="utf-8") as fh:
        cat = json.load(fh)
    out = {}
    _walk_techniques(cat, out)
    return out


def _registry_map():
    with open(_REGISTRY, encoding="utf-8") as fh:
        txt = fh.read()
    return dict(re.findall(r'"([a-z0-9_]+)"\s*:\s*"techniques\.([a-z0-9_.]+)"', txt))


def _module_files(module_dotted):
    """Resolve techniques.X (or techniques.X.sub) to its .py file(s). For a
    PACKAGE dir, scan ALL .py recursively (catch sub-module get_param reads)."""
    rel = module_dotted.replace("techniques.", "").split(".")[0]
    single = os.path.join(_ENGINE_DIR, rel + ".py")
    pkg = os.path.join(_ENGINE_DIR, rel)
    files = []
    if os.path.isfile(single):
        files.append(single)
    if os.path.isdir(pkg):
        for dp, _, fns in os.walk(pkg):
            files += [os.path.join(dp, fn) for fn in fns if fn.endswith(".py")]
    return files


def _keys_in(files):
    keys = set()
    for f in files:
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                keys.update(_GET_PARAM.findall(fh.read()))
        except OSError:
            pass
    return keys


def _global_keys():
    keys = set()
    for dp, _, fns in os.walk(_ENGINE_DIR):
        for fn in fns:
            if fn.endswith(".py"):
                with open(os.path.join(dp, fn), encoding="utf-8", errors="ignore") as fh:
                    keys.update(_GET_PARAM.findall(fh.read()))
    return keys


def audit():
    controls = _catalog_controls()
    reg = _registry_map()
    gkeys = _global_keys()
    results = {}  # tid -> {"inert": [...], "helper_suspect": [...], "module": str}
    for tid, names in controls.items():
        if tid in ALLOWLIST:
            continue
        mod = reg.get(tid) or ("techniques." + tid)
        files = _module_files(mod)
        tkeys = _keys_in(files)
        inert = [n for n in names if n not in tkeys]
        if not inert:
            continue
        # helper-suspect = inert here but read SOMEWHERE in the engine (a
        # cross-module helper may consume it) -> verify per-control.
        helper_suspect = [n for n in inert if n in gkeys]
        results[tid] = {"inert": inert, "helper_suspect": helper_suspect,
                        "module": mod, "engine_keys": sorted(tkeys)}
    return results


def registry_invariant():
    """catalog SUBSET-OF registry: every catalog technique_id must be a
    TECHNIQUE_REGISTRY key (else the dialog advertises a technique no run can
    reach -- the critical_slowing_down gap, F4). Returns (violations, n_alias,
    orphans): the REVERSE set (registry-not-in-catalog) is REPORT-only -- the
    registry is an INTENTIONAL superset (alias/convenience ids); an ORPHAN
    (a registry entry whose MODULE no catalog id reaches) is the mirror class
    of the gap, reported + banked, never failed here."""
    controls = _catalog_controls()
    reg = _registry_map()
    violations = sorted(t for t in controls if t not in reg)
    catalog_targets = {reg[t] for t in controls if t in reg}
    rev = {k: v for k, v in reg.items() if k not in controls}
    orphans = sorted(k for k, v in rev.items() if v not in catalog_targets)
    return violations, len(rev) - len(orphans), orphans


def main(argv):
    report = "--report" in argv
    results = audit()
    print("# catalog_key_alignment - structural KEY-ALIGNMENT guard (NOT parity)")
    print(f"# techniques with inert controls (D-set allowlisted): {len(results)}")
    total = sum(len(r["inert"]) for r in results.values())
    print(f"# total inert controls: {total}")

    # --- catalog SUBSET-OF registry invariant (F4) ---
    violations, n_alias, orphans = registry_invariant()
    print(f"# registry invariant: catalog-not-in-registry={len(violations)} | "
          f"reverse: alias={n_alias}, orphan={len(orphans)}")
    if orphans:
        print("## REPORT-ONLY: registry entries whose module no catalog id reaches "
              "(implemented-but-unexposed; banked, not failed):")
        for k in orphans:
            print(f"  {k}")
    if violations:
        print("\n## [FAIL] catalog technique(s) ABSENT from TECHNIQUE_REGISTRY "
              "(the dialog advertises an unreachable technique):")
        for t in violations:
            print(f"  {t}")
        print("\nRegister the technique in engine/techniques/registry.py, or "
              "remove/mark the catalog entry.")
        return 1

    new_inert = {}
    for tid, r in sorted(results.items()):
        baseline = set(KNOWN_INERT.get(tid, []))
        new = [c for c in r["inert"] if c not in baseline]
        if new:
            new_inert[tid] = new

    # stale-baseline check: baselined controls that are now read (fixed)
    stale = {}
    for tid, baselined in KNOWN_INERT.items():
        cur = set(results.get(tid, {}).get("inert", []))
        fixed = [c for c in baselined if c not in cur]
        if fixed:
            stale[tid] = fixed

    if report:
        print("\n## Full inert audit (paste the dict below into KNOWN_INERT):\n")
        print("KNOWN_INERT = {")
        for tid, r in sorted(results.items()):
            sus = (" # helper-suspect: " + ",".join(r["helper_suspect"])) if r["helper_suspect"] else ""
            print(f'    {tid!r}: {r["inert"]!r},{sus}')
        print("}")

    if stale:
        print("\n## STALE baseline (now engine-read — trim from KNOWN_INERT):")
        for tid, fixed in sorted(stale.items()):
            print(f"  {tid}: {fixed}")

    if new_inert:
        print("\n## [FAIL] NEW inert control(s) (not in the KNOWN_INERT baseline):")
        for tid, new in sorted(new_inert.items()):
            print(f"  {tid}: {new}  (engine reads: {results[tid]['engine_keys']})")
        print("\nA dialog control was added whose key the engine never get_param-reads "
              "(the inert-control bug). Rename the catalog control to the engine's key, "
              "or wire the engine to read it, or (if config is via a non-get_param path) "
              "add it to the documented ALLOWLIST.")
        return 1

    print("\n## [PASS] no NEW inert controls beyond the known baseline.")
    print(f"   (known-inert backlog pending per-control fixes: "
          f"{sum(len(v) for v in KNOWN_INERT.values())})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
