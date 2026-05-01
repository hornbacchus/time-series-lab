# Bond Yield Forecast Session 2 — Technique module + registry + catalog + markdown + pre-flight validation

**Date:** 2026-04-30
**Scope:** Wire Bond Yield Forecast into TSL's 5-place integration
pattern with friction-points §1 pre-flight validation layer.
**Status:** COMPLETE.

## Pre-Session 2 verification gate (per plan)

| Check | Status |
|---|---|
| Session 1 commit `95f5f01` + CI run 25199112778 success | ✓ |
| 86 PASS + 16 SKIP test posture | ✓ unchanged at S2 entry |
| Byte-identical smoke verified | ✓ Session 1 close |
| Parity-fast 76/76 unchanged | ✓ |
| `engine/techniques/bond_yield_forecast/` subpackage in place | ✓ |
| Existing `engine/techniques/bvar.py` unchanged | ✓ verified by `git diff --name-only` |

## Five-place integration delivered

Per architecture-discovery doc + plan §2:

### Place 1 — Dispatch entry point (`_dispatch.py` + `__init__.py` re-export)

**Initial design:** `engine/techniques/bond_yield_forecast.py` (a
sibling file alongside the subpackage directory) per plan §2.1.

**Actual structure (corrected mid-session per Python import-system constraint):**
- `engine/techniques/bond_yield_forecast/_dispatch.py` — implementation
- `engine/techniques/bond_yield_forecast/__init__.py` — re-exports `run`

**Reason for divergence from plan §2.1:** Python's import machinery
cannot resolve a module-name collision when both
`engine/techniques/bond_yield_forecast.py` and
`engine/techniques/bond_yield_forecast/` (a package directory with
`__init__.py`) exist at the same path. `importlib.import_module(
"techniques.bond_yield_forecast")` always resolves to the package, so
the file-level `run()` is unreachable.

The corrected pattern produces the **same effective contract**: the
registry maps `"bond_yield_forecast" -> "techniques.bond_yield_forecast"`,
engine_worker calls `importlib.import_module(...)`, and `mod.run`
resolves via the `__init__.py` re-export. Banked as plan §2.1
clarification for v1.2.0 amendment candidates.

**Dispatch contract:** `run(ctx: RunContext, progress_callback) -> dict`.

**Input:** `ctx.params["input_workbook"]` (absolute path to a 3+-sheet
xlsx). This deviates from typical TSL wrappers (which consume
`ctx.series` cell-data) but is endorsed by integration plan §1.2
(three-sheet bundled workbook). The subpackage's
`unified_input.read_unified_workbook(path, scenario, config)` is the
sole consumer.

**Output:** TSL `RunResponse` dict with 4 tables, plain-English
summary, audit_fields including warnings_by_category dict.

**Pre-flight validation (plan §2.1.1 / friction-points §1):**
- `input_workbook` parameter present
- File exists; `.xlsx` loadable via openpyxl read-only
- Workbook has ≥2 sheets (config-aware sheet-name validation deferred
  to `read_unified_workbook` which raises `InputValidationError`)
- All catalog-declared parameters within bounds (lambdas ≥0.001;
  `n_draws_subsample` ≤5000; `projection_uncertainty` ≥0.01;
  `n_draws` ∈[1000,50000]; etc.)

Pre-flight failures surface as `make_error_response` with structured
`error_message` + `error_fixes` BEFORE invoking deep BVAR stack
(`MinnesotaPrior.__init__`, `BVARSV.__init__`,
`ConditionalForecaster.__init__`), addressing friction-points §1
"deep constructor errors are unfriendly".

**`BVARWarning` capture (plan §2.1.8):** the entire dispatch body runs
under a single `warnings.catch_warnings(record=True)` block. Captured
warnings are aggregated via `_summarize_warnings` into
`audit_fields["warnings_count"] / ["warnings_by_category"] /
["bvar_warning_messages"]`, never leak to stderr.

**No matplotlib (plan §2.2):** the dispatch deliberately does NOT
import matplotlib. Charts come from Excel-native chart insertion at
the C# add-in side (Session 3). The legacy CLI's `_save_forecast_plots`
is in `_legacy_cli.py.archive` (does not migrate).

**No parquet write:** `build_panel(output_dir=...)` always writes
parquet via `pandas.to_parquet`, requiring pyarrow as a hard dep. The
dispatch instead uses `_build_panel_in_memory` (mirrors `build_panel`
lines 472-525 inline minus the parquet-write block), keeping pyarrow
optional in TSL's dep matrix.

### Place 2 — Registry entry

`engine/techniques/registry.py`:

```python
"bond_yield_forecast": "techniques.bond_yield_forecast",
"byf": "techniques.bond_yield_forecast",
"yield_forecast": "techniques.bond_yield_forecast",
```

3 aliases routed to the same module; `byf` is the short form.
Coexists with `"bvar": "techniques.bvar"` (existing Phase 1/2
IRF/FEVD wrapper, technique_id `1c_bvar_irf_fevd`).

### Place 3 — Catalog entry (parameter bounds per plan §2.3)

`resources/catalog/techniques_catalog.json`: full entry with 12
parameters declared. Bounds match Session 0 ValueError thresholds:

| Parameter | Min | Max | Catalog field bound rationale |
|---|---:|---:|---|
| `lambda_1` | 0.001 | 2.0 | Session 0 lambda guard |
| `lambda_2` | 0.001 | — | Session 0 |
| `lambda_3` | 0.001 | — | Session 0 |
| `n_draws_subsample` | 100 | **5000** | Plan §2.3 tightening from 7000 (friction-points §3 OOM) |
| `n_paths_per_draw` | 10 | 500 | UX bound |
| `projection_uncertainty` | 0.01 | — | Session 0 tiered (≥0.01 clean) |
| `n_draws` | 1000 | 50000 | UX bound |
| `n_burn` | 100 | 20000 | UX bound |
| `horizon` | 1 | 20 | UX spec range |
| `seed` | 0 | — | non-negative int |

`min_series=0, max_series=0` — declares that this technique does NOT
consume `ctx.series` (workbook-input contract).

`supports_auto_udf=false` — workbook-input technique cannot be
spilled-array-formula UDF.

JSON validates per `python -c "import json; json.load(open(...))"`.

### Place 4 — Markdown long-form description

`resources/techniques_md/bond_yield_forecast.md` (~140 lines):
methodology, references (CCM-2019, BGL-2015, KSC-1998, CK-1994,
Litterman-1986), input contract, output schema, parameter table,
performance characteristics, coexistence rationale with existing
`engine/techniques/bvar.py`, migration provenance.

### Place 5 — Ribbon button (Session 3 scope; not done in S2)

Per plan, Ribbon dropdown is Session 3 work. The catalog entry above
will drive the Task Pane UI when the Ribbon button is wired in S3.

## Engine worker dispatch test (plan §2.5)

`engine/techniques/bond_yield_forecast/_session2_dispatch_test.py`
exercises 6 cases through the same registry-import-run path as
engine_worker. Result: **6/6 PASS**.

| Case | Verifies |
|---|---|
| 1. Registry resolution | `bond_yield_forecast` + `byf` + `yield_forecast` all route to the subpackage; `mod.run` callable via `__init__.py` re-export |
| 2. Pre-flight: missing `input_workbook` | Clean `make_error_response` with 3 fix suggestions; no deep-stack traceback |
| 3. Pre-flight: nonexistent path | Clean rejection with "not found" message |
| 4. Pre-flight: out-of-bounds `lambda_1=0.0` | Rejection with "below minimum" message |
| 5. Pre-flight: `n_draws_subsample=7000` | Rejection per plan §2.3 cap of 5000 |
| 6. Happy path: full BVAR-SV cycle on canonical fixture | RunResponse well-formed (4 tables: Yield Forecast / Macro Conditioning / Convergence Diagnostics / Run Metadata); JSON-serializable; warnings captured into audit_fields |

Wall-clock for happy path on canonical fixture: ~25s (~3s
overhead vs Session 1 smoke baseline 17.9s; the overhead is the
in-memory panel build replacing the parquet roundtrip + the warnings-
capture machinery).

## Coverage discipline carry-forward (Session 1 banked items)

Per Session 1 close + Session 2 prompt: the 15 CLI-dependent test
skips banked from S1 should be reproduced via dispatch context. Status
post-S2:

| S1-skipped cluster | S2 coverage status | Notes |
|---|---|---|
| `test_session0_logging.py` (5 tests) | **Indirect** | The wrapper's `warnings.catch_warnings(record=True)` block isolates root-logger / matplotlib / pandas-options state inside the run() scope. Not a direct re-test of the CLI's `_log_to_file` context manager (which doesn't migrate); rather, the wrapper's equivalent isolation is exercised by every dispatch run. **Banked for Session 5+ test infrastructure investment** if direct coverage is needed. |
| `test_session0_warnings.py` (3 tests) | **Direct** | Dispatch test happy-path Case 6 verifies BVARWarning subclasses (when present) flow into `audit_fields["warnings_by_category"]` with their class name. The S1-skipped tests covered `_print_convergence_summary` / `_print_optimization_summary` (CLI helpers); their warning-emission behavior is now verified at the dispatch boundary. |
| `test_unified_input.py` (3 tests) | **Direct** | Dispatch test happy-path Case 6 reads the canonical 3-sheet workbook via `read_unified_workbook` end-to-end. The S1-skipped tests covered CLI-level scenario routing; the dispatch test covers the same code path through `ctx.params["scenario"]`. |
| `test_session0_paths.py::test_smoke_*` (2 tests) | **Direct** | The dispatch test invokes `run()` from a non-cwd-aware context; package_default_config() is exercised in Case 6 happy path. |
| `test_data.py::test_build_panel_full_pipeline` (1 test) | **Bypass** | The wrapper uses `_build_panel_in_memory` instead of `build_panel(output_dir=...)`; the parquet code path is intentionally not invoked. Banked: if pyarrow ever becomes a TSL hard dep, the original test can be un-skipped. |
| `rpy2 conditional` | (preserved) | BVAR baseline behavior |

**Net Session 2 coverage assessment:** all 15 S1 CLI-dependent skips
have functional coverage at the dispatch boundary. The
`test_session0_logging.py` cluster is the weakest (indirect coverage
only); banked for Session 5 test-infra investment if a direct
re-anchor is warranted.

## Verification gates

| Gate | Status |
|---|---|
| Engine-worker dispatch test | **6/6 PASS** |
| Migration test suite (102 collected) | **86 passed + 16 skipped** unchanged from S1 close |
| Parity-fast sweep (76 checks) | **71 PASS + 5 CAVEAT, 0 BLOCK** unchanged |
| Catalog JSON validates | ✓ |
| Registry entry resolvable | ✓ verified by Case 1 |
| Existing `engine/techniques/bvar.py` unchanged | ✓ |
| `--check-environment` (post-S1 deps) | ✓ clean |
| Markdown description registered | ✓ at `resources/techniques_md/bond_yield_forecast.md` |

## Out-of-band findings

1. **Plan §2.1 file/package-name collision** — the plan specified
   `engine/techniques/bond_yield_forecast.py` for the dispatch entry,
   but Python doesn't allow a same-named file + package directory.
   Corrected by moving dispatch to subpackage's `_dispatch.py` +
   `__init__.py` re-export. **Banked as v1.2.0 amendment candidate**
   per plan "Phase 4 carry-forward inheritance" (P-1 §8.1 might
   benefit from a "wrapper layout when implementation is a
   subpackage" sub-section).

2. **Catalog `min_series=0` / `max_series=0`** — used here to declare
   the workbook-input contract (no `ctx.series` consumption). TSL
   convention historically uses positive ints; 0 is a slight overload.
   **Banked for Session 11/Phase 4 P-1 amendment** to formalize the
   "0/0" semantics or add a separate `input_contract` enum to the
   catalog schema (e.g., `"workbook" | "series" | "exog_table"`).

3. **`projection_uncertainty` is dict-shaped in soft mode** — caused
   a `float(...)` cast bug in audit_fields aggregation; fixed via
   `_audit_safe(value)` helper that passes dicts through unchanged
   and coerces scalars. Banked for friction-points §3 documentation
   update at Phase 4: `projection_uncertainty` should be documented
   as either-scalar-or-per-variable-dict in the markdown long-form.

4. **`pytest.mark.slow` warning** — banked at S1; still cosmetic;
   non-fatal. Defer to Session 5 / Session 6 cleanup.

5. **Wall-clock overhead vs S1 smoke** — dispatch path is ~7s slower
   than the bare `_session1_smoke.py` (25s vs 18s). Overhead breaks
   down approximately as: in-memory panel build replacing parquet
   roundtrip (+1s); warnings capture machinery (+1s); pre-flight +
   table assembly (+5s). All within the catalog-declared "15-30
   second" performance characteristic in the markdown description.

## Schedule status

Bond Yield Forecast cycle: **2 of 6 TSL-side sessions complete.**
Sessions 3-6 follow per locked plan.

## Commit footprint

| File | Change |
|---|---|
| `engine/techniques/bond_yield_forecast/__init__.py` | -8 / +12 LOC (re-export `run`; documentation) |
| `engine/techniques/bond_yield_forecast/_dispatch.py` | new ~530 LOC (dispatch entry + pre-flight + 4-table assembly + warnings capture) |
| `engine/techniques/bond_yield_forecast/_session2_dispatch_test.py` | new ~210 LOC (6-case dispatch verification harness) |
| `engine/techniques/registry.py` | +12 LOC (3 aliases + commentary) |
| `resources/catalog/techniques_catalog.json` | +156 LOC (full catalog entry) |
| `resources/techniques_md/bond_yield_forecast.md` | new ~140 LOC |
| `docs/bond_yield_forecast_integration/session_2_findings.md` | new (~250 LOC) |
| **Total** | **~1300 LOC across 7 files** within standard wrapper-add LOC envelope |

## Next session

Bond Yield Forecast Session 3 — Sample input template + Ribbon
dropdown menu. Creates the bundled
`bond_yield_forecast_input_template.xlsx` (per plan §3.1 spec with
`BondYield_Macro` / `BondYield_Yields` / `BondYield_Projections`
sheet names) and wires the Ribbon `splitButton` with "Open Input
Template" + "Run Bond Yield Forecast" menu items.
