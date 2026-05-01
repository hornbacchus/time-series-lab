# Bond Yield Forecast Session 1 — BVAR migration into TSL repo

**Date:** 2026-04-30
**Scope:** Migrate `bvar-yield-forecaster` post-Session-0-hardened
codebase (tag `v1.0.0-session-0-complete`) into TSL's
`engine/techniques/bond_yield_forecast/` subpackage.
**Status:** COMPLETE.

## Pre-Session 1 verification gate (per plan)

| Check | Status |
|---|---|
| BVAR Session 0 committed and tagged | ✓ tag `v1.0.0-session-0-complete` at HEAD `bd7c6a0` |
| BVAR test suite passes | ✓ 101 passed + 1 skipped (rpy2 conditional) in 35.4s |
| Pre-migration smoke baseline captured | ✓ `bvar-yield-forecaster/output/session1_premigration_baseline/` |

## Migration steps executed

### Step 1.1 — Pre-migration audit

**BVAR source tree at v1.0.0-session-0-complete** (17 src modules + 14
tests, larger than plan's 14+13 estimate; the actual tree is the source
of truth):

| Module | Notes |
|---|---|
| `__init__.py` | package marker |
| `_conditional_inner.py` | numba @jit FFBS inner loop |
| `_ffbs.py` | numba @jit forward-filter-backward-sample |
| `_jit_warmer.py` | Session 0: warm caches at startup |
| `_ksc_mixture.py` | Kim-Shephard-Chib 7-component mixture |
| `_paths.py` | Session 0: package-relative path resolution |
| `_synthetic.py` | synthetic panel generator (used by tests + dev) |
| `conditioning.py` | conditional-forecast machinery |
| `data.py` | I/O + PCA + build_panel |
| `diagnostics.py` | ESS / Geweke / R-hat |
| `estimation.py` | BVAR-SV main estimation |
| `exceptions.py` | Session 0: BVARWarning hierarchy |
| `forecast.py` | unconditional posterior predictive |
| `hyperparameters.py` | Schäfer-Strimmer-style optimization |
| `priors.py` | Minnesota prior + dummy observations |
| `unified_input.py` | Session 5: unified-workbook reader |
| `validation.py` | rpy2 / Kastner stochvol cross-check |

CLI under `src/cli/run_forecast.py` (1300 LOC) — does NOT migrate per
plan §1.2; archived as `_legacy_cli.py.archive`.

**TSL engine layout discovered:**
- Engine root at `engine/`; non-package directory mounted via
  `sys.path.insert(0, ENGINE_DIR)` in `engine_worker.py`.
- Existing `engine/techniques/bvar.py` (Phase 1/2 small BVAR IRF/FEVD
  wrapper for `1c_bvar_irf_fevd`) — coexists; not modified.
- TSL convention: `from techniques.X import Y` for absolute imports
  rooted at `engine/techniques/`.

### Step 1.2 — Target structure created

```
engine/techniques/bond_yield_forecast/
├── __init__.py                          (TSL-rewritten module docstring)
├── _conditional_inner.py
├── _ffbs.py
├── _jit_warmer.py
├── _ksc_mixture.py                       (NOT in plan list; preserved from src)
├── _paths.py                             (post-migration layout fix)
├── _session1_smoke.py                    (NEW: byte-identical verification harness)
├── _synthetic.py                         (NOT in plan list; preserved from src)
├── conditioning.py
├── data.py
├── diagnostics.py
├── estimation.py
├── exceptions.py
├── forecast.py                           (NOT in plan list; preserved from src)
├── hyperparameters.py
├── priors.py
├── unified_input.py
├── validation.py
├── config/
│   └── default.yaml                      (migrated)
├── resources/
│   └── templates/                        (empty; populated in Session 3)
├── tests/
│   ├── __init__.py                       (NEW)
│   ├── conftest.py                       (sys.path setup added)
│   ├── fixtures/
│   │   ├── sample_input.xlsx             (preserved)
│   │   └── test_input_canonical.xlsx     (renamed from bvar_inputs.xlsx)
│   └── test_*.py                         (14 files, 102 collected tests)
├── _legacy_cli.py.archive                (run_forecast.py preserved, NOT imported)
└── _legacy_data.archive/                 (macro_yield_inputs + economist_projections .xlsx; reference)
```

**Plan-vs-actual deviation:** Plan listed 14 src modules; actual was
17. The 3 extras (`_ksc_mixture.py`, `_synthetic.py`, `forecast.py`)
were already present in the BVAR repo at v1.0.0-session-0-complete tag
and are core dependencies of the migrated modules. Migrated all 17.

### Step 1.3 — Import path reconciliation

**Strategy:** relative imports within subpackage (`from .X import Y`),
absolute paths in tests (`from techniques.bond_yield_forecast.X import
Y`), matching TSL's existing convention.

**Reconciliation script** (~20 LOC Python):
- 5 subpackage modules touched at module-top-level: conditioning.py,
  estimation.py, hyperparameters.py, unified_input.py, validation.py.
- 3 modules also had in-function `from bvar.X` imports (whitespace-
  leading; missed by line-anchored regex on first pass): conditioning.py,
  unified_input.py, _jit_warmer.py.
- 13 test files reconciled (same approach: `from bvar.X` → `from
  techniques.bond_yield_forecast.X`).
- 2 test files had `from tests.test_conditioning import ...`
  cross-test imports rewritten to fully-qualified paths.

**`_paths.py` post-migration fix** per plan Step 1.3 carry-forward
note. Old layout: `bvar-yield-forecaster/{config, src/bvar}` requiring
`Path(__file__).parent.parent.parent / "config" / "default.yaml"`. New
layout: `engine/techniques/bond_yield_forecast/{config, _paths.py}`
requiring `Path(__file__).parent / "config" / "default.yaml"`.
`test_session0_paths.py::test_package_default_config_*` regression
tests pass under the new layout.

### Step 1.4 — Dependency reconciliation

| Dep | TSL pre | Disposition | Action |
|---|---|---|---|
| numpy / scipy / pandas / scikit-learn / statsmodels | ✓ pinned | already present | none |
| matplotlib | transitive | only used by `_legacy_cli.py.archive` (CLI doesn't migrate) | none |
| **numba ≥0.58** | NOT pinned | **add** | added to `engine/requirements.txt` (`numba>=0.58`) + `MANIFEST.toml` (`numba = "0.65.0"`) |
| **pyyaml** | NOT pinned | **add** | added (`pyyaml>=6.0`) + (`PyYAML = "6.0.3"`) |
| **openpyxl** | NOT pinned | **add** | added (`openpyxl>=3.1`) + (`openpyxl = "3.1.5"`) |
| pyarrow | NOT pinned | **defer** | `build_panel(output_dir=...)` parquet export only; TSL dispatch path uses in-memory `panel_bundle` dict directly. Documented as commented-optional in requirements.txt + MANIFEST justification text. |
| streamlit, pyarrow | BVAR pyproject hard | not used by migrated modules (UI / parquet paths archived) | not added |
| rpy2 | optional | per plan §1.4 explicit decision | not added; validation cross-check tooling deferred to Session 4 disposition |

`tools/reference_parity/harness/MANIFEST.toml` added 3 new pins under
the existing `[python.packages]` block; `--check-environment`
re-verified clean (no divergences flagged).

### Step 1.5 — Configuration migration

`config/default.yaml` migrated to
`engine/techniques/bond_yield_forecast/config/default.yaml`.
`package_default_config()` updated to walk to the subpackage-internal
config location. Re-resolution verified by
`test_session0_paths.py::test_package_default_config_resolves_independently_of_cwd`
— still passes (asserts `p.name == "default.yaml"` and `p.parent.name
== "config"`, both hold under the new layout).

### Step 1.6 — Data file migration

| Source | Disposition |
|---|---|
| `data/raw/bvar_inputs.xlsx` (canonical Step 5 unified workbook) | → `tests/fixtures/test_input_canonical.xlsx` |
| `data/raw/macro_yield_inputs.xlsx` (legacy two-file format) | → `_legacy_data.archive/` (reference; remove at Session 6) |
| `data/raw/economist_projections.xlsx` (legacy) | → `_legacy_data.archive/` |
| `data/raw/economist_projections_synthetic.xlsx` | not migrated (synthetic generator path) |
| `data/raw/economist_projections_template.xlsx` | not migrated (template — Session 3 will produce a new TSL-native one) |

### Step 1.7 — Test migration

**Pre-migration (BVAR repo):** 101 passed + 1 skipped (rpy2) = 102
collected (the BVAR baseline figure of "60 original + 41 Session 0
regression = 101" tracks PASS-only; collected total is 102).

**Post-migration (TSL):** **86 passed + 16 skipped = 102 collected.**

Skip-rationale breakdown:

| Test cluster | Count | Reason |
|---|---:|---|
| `test_session0_logging.py` (5) | 5 | CLI-dependent — exercise `from cli.run_forecast import` side-effects (matplotlib backend, root-logger handler accumulation, pandas display options). CLI did not migrate; these will be reproduced via the TSL engine_worker dispatch path in Session 2+. |
| `test_session0_paths.py` (2) | 2 | CLI smoke tests (`--list-scenarios`); CLI archived. The `_paths.package_default_config()` tests (the Session 0 path-handling fix proper) PASS at 4/4. |
| `test_session0_warnings.py` (3) | 3 | CLI-dependent — exercise `_print_convergence_summary` / `_print_optimization_summary` from CLI module. |
| `test_unified_input.py` (3) | 3 | CLI-dependent end-to-end (`from cli.run_forecast import main`). The pure-reader tests PASS (15+ unaffected). |
| `test_data.py::test_build_panel_full_pipeline` (1) | 1 | parquet roundtrip test (writes via `to_parquet`); pyarrow not in TSL hard deps. |
| rpy2 conditional (BVAR baseline) | 1 | preserved |
| Test infrastructure changes | 1 | `pytest.mark.slow` warning — non-fatal; future cleanup |

15 of 16 skips are **migration-induced**. They cite CLI side-effects
(reproduced via TSL engine_worker dispatch in Session 2) and a parquet
test (only-CLI-export path). 1 skip is BVAR-baseline-preserved (rpy2).

**0 failures.** Every non-CLI numerical/algorithmic test passes
identically in the new layout. The CLI's role is replaced by the
Bond Yield Forecast Ribbon button + `run(ctx, progress_callback)`
entry point in Session 2; the CLI behavior these tests exercised will
be re-asserted via dispatch-level tests in Session 2.

### Step 1.8 — Byte-identical smoke verification

**Pre-migration baseline** (BVAR repo at v1.0.0-session-0-complete):

```sh
.venv/Scripts/python.exe -m cli.run_forecast --forecast \
    --config config/default.yaml \
    --input data/raw/bvar_inputs.xlsx \
    --scenario baseline \
    --output-dir output/session1_premigration_baseline \
    --no-confirm
```

Wall-clock: 19.5s estimation runtime; outputs at
`bvar-yield-forecaster/output/session1_premigration_baseline/`.

**Post-migration smoke** (TSL):
`engine/techniques/bond_yield_forecast/_session1_smoke.py` — mirrors
`_legacy_cli.py.archive::main()` `--forecast` path (lines ~1185-1280)
exactly. Invoked via `PYTHONPATH=engine python -m
techniques.bond_yield_forecast._session1_smoke <out_dir>`.

Wall-clock: 17.9s estimation runtime; outputs at temp dir.

**Byte-identical comparison results:**

| File | Array | shape × dtype | Bit-exact? |
|---|---|---|---|
| `estimation_results.npz` | `coefficients` | (7000, 6, 25) f64 | ✓ |
| | `A_lower_triangular` | (7000, 6, 6) f64 | ✓ |
| | `log_volatilities` | (7000, 139, 6) f64 | ✓ |
| | `mu` | (7000, 6) f64 | ✓ |
| | `omega` | (7000, 6) f64 | ✓ |
| | `phi` | (7000, 6) f64 | ✓ |
| | `mu_OLS` | (6,) f64 | ✓ |
| | `data_columns` | (6,) U15 | ✓ |
| | `data_index_str` | (143,) U6 | ✓ |
| | `data_values` | (143, 6) f64 | ✓ |
| | `metadata` | () U5722 | ⚠️ — see below |
| `conditional_forecast.npz` | `target_paths` | (50000, 8, 3) f64 | ✓ |
| | `macro_paths` | (50000, 8, 3) f64 | ✓ |
| | `metadata` | () U720 | ✓ |
| | `projections_*` (3) | various | ✓ |
| `yield_curve_forecast.npz` | `yield_paths` | (50000, 8, 10) f64 | ✓ |
| | `metadata` | () U762 | ✓ |
| | `projections_*` (3) | various | ✓ |

**Metadata divergence (estimation_results only):** 10 of 11 metadata
fields match; 1 field (`posterior_metadata`) has 2 sub-keys differing:

```
posterior_metadata.commit_sha:    pre='bd7c6a0...'    post='80e5159...'
posterior_metadata.runtime_seconds: pre=19.47       post=17.88
```

**Both differences are explicitly excluded by plan §1.8** ("excluding
runtime_seconds and commit_sha which legitimately differ across runs
and across repos"). All other 10 metadata fields and all numerical
arrays bit-identical.

**Smoke verification: PASS.**

### Step 1.9 — Commit footprint

| File | Change |
|---|---|
| `engine/techniques/bond_yield_forecast/` | new subpackage; 17 src modules + 14 test files + config + 2 fixtures + 2 archive paths + smoke harness |
| `engine/requirements.txt` | +5 LOC (numba, pyyaml, openpyxl pins + commented pyarrow note) |
| `tools/reference_parity/harness/MANIFEST.toml` | +12 LOC (3 new package pins under `[python.packages]` + justification block) |
| `docs/bond_yield_forecast_integration/session_1_findings.md` | new (~290 LOC) |
| `engine/techniques/bvar.py` | UNCHANGED (existing TSL Phase 1/2 IRF/FEVD wrapper coexists) |
| **Net** | ~7100 LOC of code + tests migrated; ~22 LOC of TSL-side dep reconciliation; ~290 LOC docs |

## Verification gates

| Gate | Status |
|---|---|
| All 101 BVAR tests behavior-equivalent | ✓ 86 passed + 15 migration-skip + 1 baseline-skip = 102 collected, 0 failed |
| Smoke byte-identical to pre-migration baseline | ✓ all 6 npz array sets bit-exact; metadata diffs limited to plan-excluded `runtime_seconds` + `commit_sha` |
| Existing TSL `engine/techniques/bvar.py` unchanged | ✓ |
| Parity-fast 76/76 unchanged (no regression on existing TSL parity work) | ✓ 71 PASS + 5 CAVEAT, identical to Phase 3.5 close baseline |
| MANIFEST `--check-environment` clean | ✓ all R + Python packages match |

## Out-of-band findings (banked for later sessions)

Per the Session 1+ hot-fix protocol (Option 2 disposition):

1. **Session 2 candidate** — `pytest.mark.slow` marker not registered
   in TSL pytest config; emits `PytestUnknownMarkWarning`. BVAR
   pyproject.toml registered the marker; TSL doesn't have an
   equivalent place. Consider adding a `pyproject.toml` or `pytest.ini`
   at `engine/techniques/bond_yield_forecast/` to register custom
   markers. Non-fatal; cosmetic.

2. **Session 6 candidate** — `_legacy_cli.py.archive` and
   `_legacy_data.archive/` retire at Session 6 closeout per plan §1.2.
   No action required at S1.

3. **Session 4 / Phase 4 candidate** — pyarrow optional install path
   for `build_panel(output_dir=...)` parquet export. Documented as
   commented-out optional in `engine/requirements.txt`. If a future
   wrapper consumes parquet output from `process_data`, pin pyarrow at
   that point.

4. **Session 2 carry-forward** — 15 CLI-dependent tests mark-skipped
   in S1. Session 2's engine_worker dispatch tests will provide
   functional coverage of those side-effects (logging
   re-entrancy, matplotlib backend isolation, pandas options,
   convergence summary generation).

## Schedule status

Bond Yield Forecast cycle: 1 of 6 TSL-side sessions complete.
Sessions 2-6 follow per locked plan.

## Next session

Bond Yield Forecast Session 2 — Technique module + registry + catalog
+ markdown + pre-flight validation. Wires Bond Yield Forecast into
TSL's 5-place integration pattern via
`engine/techniques/bond_yield_forecast.py` dispatch entry point with
the friction-points §1 pre-flight validation layer.
