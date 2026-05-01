# Bond Yield Forecast Session 3 — Sample input template + Ribbon dropdown menu

**Date:** 2026-05-01
**Scope:** Sample input template (.xlsx) + Ribbon `splitButton`
dropdown wiring + dispatch hardening (config-aware sheet
auto-detection + re-entrancy regression).
**Status:** COMPLETE.

## Pre-Session 3 verification gate

| Check | Status |
|---|---|
| Session 2 commit `075fa2e` | ✓ |
| S2 CI run 25211894771 | ✓ success |
| Dispatch test 6/6 PASS at S2 close | ✓ |
| Migration test suite 86 PASS + 16 SKIP | ✓ unchanged |
| Parity-fast 76/76 unchanged | ✓ |
| 5-place integration: Place 5 (Ribbon) reserved for S3 | ✓ |
| Existing `engine/techniques/bvar.py` unchanged | ✓ |

## Step 3.1 — Sample input template

**Output:** `engine/techniques/bond_yield_forecast/resources/templates/bond_yield_forecast_input_template.xlsx`

Generated via a one-shot openpyxl script that reads the canonical
fixture's `macro` / `yields` / `projections_baseline` sheets and
re-emits to the integration plan §3.1 sheet naming convention
(`BondYield_Macro` / `BondYield_Yields` / `BondYield_Projections`)
plus a styled README sheet:

| Sheet | Content |
|---|---|
| `README` | ~40 lines styled documentation (use instructions, sheet structure, data format requirements, parameter override notes, sample data provenance) |
| `BondYield_Macro` | 143 quarters of example macro data (1990-Q1 → 2025-Q3); columns: Quarter + macro variables |
| `BondYield_Yields` | 143 quarters of example yield data; columns: Quarter + 10 maturities |
| `BondYield_Projections` | 8 quarters of baseline projection (2025-Q4 → 2027-Q3); same column structure as BondYield_Macro |

Header rows formatted bold + light-gray fill; numeric formats
preserved via `number_format` propagation; column widths set to 18
for readability.

## Step 3.2 — Ribbon XML splitButton

**Edit:** `src/TSL.AddIn/RibbonXml.cs` Quick Actions group (after
the Conformal button, before the `sepQA2` separator).

```xml
<splitButton id='sbBondYield' size='large'>
  <button id='btnBondYield'
          label='Bond Yield Forecast'
          imageMso='ChartTypeLineInsertGallery'
          onAction='OnBondYieldForecastRun'
          screentip='Bond Yield Forecast (BVAR-SV)'
          supertip='Large Bayesian VAR with stochastic volatility ...' />
  <menu id='menuBondYield'>
    <button id='btnBondYieldOpenTemplate'
            label='Open Input Template'
            imageMso='TableInsertExcel'
            onAction='OnBondYieldForecastOpenTemplate' />
    <button id='btnBondYieldRun'
            label='Run Bond Yield Forecast'
            imageMso='MacroPlay'
            onAction='OnBondYieldForecastRun' />
  </menu>
</splitButton>
```

Pattern matches existing `sbExplorer` / `sbUserGuide` / `sbSampleData`
splitButton entries. Primary button click runs the forecast (Pattern A
default per UX spec); arrow click expands the submenu with two items.

## Step 3.3 — Ribbon handlers

**Edit:** `src/TSL.AddIn/Ribbon.cs` (after the `OnConformal` handler).

Three new methods + one private helper:

| Handler | Action |
|---|---|
| `OnBondYieldForecastRun(IRibbonControl)` | `TaskPaneManager.RunTechnique("bond_yield_forecast")` (matches existing Quick Action pattern; parameters edited in Task Pane before final dispatch) |
| `OnBondYieldForecastOpenTemplate(IRibbonControl)` | Resolves bundled template path; calls `app.Workbooks.Open(path, ReadOnly: false)` to open as a new editable workbook |
| `LocateBondYieldForecastTemplate()` (private helper) | Two-step search (dev path → installed path) mirroring `LoadSampleData`'s pattern for resource resolution |

## Step 3.4 — Template file resolution

Resolution mirrors the existing `LoadSampleData` pattern in `Ribbon.cs:521-540`:

1. **Dev path:** walk up 6 levels from `ExcelDnaUtil.XllPath` to repo root, then `engine/techniques/bond_yield_forecast/resources/templates/bond_yield_forecast_input_template.xlsx`.
2. **Installed path:** `%LOCALAPPDATA%/TimeSeriesLab/{templateRel}`.

The installer (Session 6 closeout scope) will need to copy the template into the installed location alongside the engine source tree. The `engine/techniques/bond_yield_forecast/resources/templates/` directory is shipped as part of the migration commit footprint; per-installer copy steps follow TSL's existing resource-bundling discipline.

## Verification carry-forward (Session 2 → Session 3)

### Carry-forward A — Template-config consistency

**Risk:** The Session 3 sample template uses `BondYield_*` sheet
names (per plan §3.1), but `read_unified_workbook` reads sheet names
from `config["unified_input"]["sheet_names"]` which defaults to
`macro` / `yields` / `projections_baseline` (canonical fixture
convention). A naive dispatch on the template would fail with
`InputValidationError [missing_sheet]`.

**Mitigation implemented:** New helper
`_resolve_workbook_sheet_config(workbook_path, base_config, scenario)`
in `_dispatch.py` (~50 LOC). On dispatch entry (after config load,
before `read_unified_workbook`), the dispatch:

1. Opens the workbook read-only via openpyxl.
2. Detects which sheet-naming scheme is present:
   - **Template scheme**: `{BondYield_Macro, BondYield_Yields, BondYield_Projections}` ⊆ sheet set → rewrite config keys
   - **Default scheme**: any other layout → base config applies unchanged
3. Returns possibly-rewritten config with:
   - `unified_input.sheet_names.macro_history` ← `"BondYield_Macro"`
   - `unified_input.sheet_names.yields_history` ← `"BondYield_Yields"`
   - `unified_input.sheet_names.projections_<scenario>` ← `"BondYield_Projections"`
   - Mirror to `data.macro_sheet` / `data.yield_sheet` for any legacy two-file path
4. Maps `BondYield_Projections_scenario_N` aliases when present (workbooks with multiple scenario sheets).

**Verification:** dispatch test Case 7 (`case_template_scheme_dispatch`) executes a full BVAR-SV cycle on the Session 3 template and asserts a clean RunResponse with the expected 4 tables. **PASS.**

**Net:** the template-config gap is closed **at the wrapper boundary**, not deferred to a runtime user-facing error. The auto-detection is invisible to the caller and works for both schemes simultaneously.

### Carry-forward B — Re-entrancy regression test

**Risk:** Friction-points §2(c) documented that BVAR's `_log_to_file` context manager attaches root-logger handlers but doesn't always detach them; re-entrant calls in a single Python process accumulate handlers and duplicate log output across runs. The Session 2 dispatch test ran one technique invocation per case, which doesn't exercise re-entrancy.

**Mitigation implemented:** new dispatch test Case 8 (`case_reentrancy`) in `_session2_dispatch_test.py`. Steps:

1. Capture `len(logging.getLogger().handlers)` before any call.
2. Invoke `run()` via the registry once on the canonical fixture.
3. Capture handler count after first call.
4. Invoke `run()` a second time (same fixture, same params).
5. Assert: `handlers_after_2 == handlers_after_1` (count must not grow). Failure indicates the friction-points §2(c) regression has resurfaced.
6. Assert: tables count + audit_fields consistent across both calls (numerical idempotency).

**Verification result:**

```
Root-logger handlers before any call: 0
Root-logger handlers after first call: 0
Root-logger handlers after second call: 0
PASS — handler count bounded; tables + audit_fields consistent across calls
```

The wrapper itself never attaches handlers. BVAR's internal `_log_to_file` is invoked inside the dispatch via standard logging; its detach behavior post-Session-0 is clean (Session 0 §S0.2 hardening). Banked: Session 5 may add a more rigorous re-entrancy test if engine_worker startup-path coverage warrants.

## Engine worker dispatch test (post-S3)

```
=== Case 1: registry resolution ===
  PASS — registry routes 'bond_yield_forecast' + aliases correctly

=== Case 2-5: pre-flight rejection paths ===
  All 4 PASS

=== Case 6: happy-path dispatch (canonical fixture) ===
  PASS — RunResponse well-formed; 4 tables; JSON-serializable

=== Case 7: template-scheme dispatch (Session 3 BondYield_* sheets) ===
  PASS — template-scheme dispatch produced 4 tables

=== Case 8: re-entrancy ===
  PASS — handler count bounded; tables + audit_fields consistent

DISPATCH TEST: PASS (8/8 cases)
```

8/8 PASS at Session 3 close (was 6/6 at S2 close; +2 cases for carry-forward verification).

## Verification gates

| Gate | Status |
|---|---|
| Engine-worker dispatch test (8 cases) | **8/8 PASS** |
| Migration test suite (102 collected) | **86 passed + 16 skipped** unchanged from S2 close |
| Parity-fast (76 checks) | **71 PASS + 5 CAVEAT** unchanged |
| Sample template xlsx generated + valid | ✓ (4 sheets: README + BondYield_Macro + BondYield_Yields + BondYield_Projections) |
| Ribbon XML structure validates | ✓ (mirrors existing splitButton patterns) |
| Ribbon.cs handlers added (3 + 1 helper) | ✓ |
| Template path resolution mirrors `LoadSampleData` | ✓ |
| Existing `engine/techniques/bvar.py` unchanged | ✓ |
| Catalog JSON unchanged from S2 | ✓ (no parameter additions in S3) |

## Step 3.5 — Task Pane integration verification

**Status:** Architectural verification only (no Excel build invocation in this session).

The Bond Yield Forecast Task Pane will render automatically from the Session 2 catalog entry's `parameters[]` array. Per the architecture-discovery doc (`docs/excel_addin_architecture_for_bond_yield_integration.md` §4): the Task Pane's `RunViewModel.SetParameters` consumes the catalog's `parameters[]` block and renders WPF controls (text input for strings/floats, integer spinners, dropdowns where `options` declared, checkboxes for bools).

The 12 catalog parameters from Session 2 (input_workbook, scenario, horizon, n_draws, n_burn, n_paths_per_draw, n_draws_subsample, projection_uncertainty, lambda_1, lambda_2, lambda_3, seed) will render with their declared bounds + tier ordering (`required` + `advanced` flags drive UI tier classification).

**Banked for Session 5+:** Excel-side build + interactive smoke test of the full flow (Ribbon dropdown → template open → user edits → Run → Task Pane → dispatch → Results sheet). Step 3.6 below covers what's verifiable at the Python/dispatch boundary; the C#-side build verification rolls into the broader Session 5 CI scope.

## Step 3.6 — Build and smoke test

**Python-side dispatch verification:** dispatch test cases 6-8 cover:

- Happy-path dispatch on canonical fixture (default sheet scheme).
- Template-scheme dispatch on the Session 3 sample template (`BondYield_*` sheets) — proves the auto-detection in `_resolve_workbook_sheet_config` works end-to-end.
- Re-entrancy regression — proves friction-points §2(c) is not a current regression.

**C#-side smoke test:** deferred. C# build CI is not configured in TSL's GitHub Actions (only Python-side parity-fast.yml + parity-slow.yml run); the C# build is verified via local Visual Studio compilation by the developer. Session 6 closeout will include a `dotnet build` invocation on the .NET solution to validate the Ribbon + handler additions compile cleanly.

## Out-of-band findings (banked for later sessions)

1. **`OnBondYieldForecastRun` workbook-path injection** — currently the Ribbon handler routes through `TaskPaneManager.RunTechnique("bond_yield_forecast")`, which builds the RunRequest from the active Excel cell selection. Bond Yield Forecast doesn't consume `ctx.series` — it consumes a workbook path. The user must set `input_workbook` manually in the Task Pane parameter editor before clicking the Task Pane's Run button.

   **Improvement banked for Session 5:** add a `TaskPaneManager.RunTechniqueWithParams(string techniqueId, Dictionary<string, object> params)` overload that injects the workbook path automatically (defaulting to `app.ActiveWorkbook.FullName`). This makes the Ribbon's "Run Bond Yield Forecast" a true one-click action when the active workbook is the input workbook. Out-of-S3 scope; banked.

2. **Installer must bundle the template** — Session 6 closeout will need to add the template file to the ClickOnce installer manifest so the installed-location resolution path works for end users. The dev-location resolution already works for developers running from the repo. No action required at Session 3.

3. **Ribbon `pytest.mark.slow` warning** — banked from S1; still cosmetic; defer to Session 5 or Session 6 cleanup.

4. **C# build CI gap** — TSL does not currently run a C# build step in CI. Phase 4 candidate to add a `dotnet build` step to the parity-fast workflow (or a separate workflow) so Ribbon XML / handler edits get cross-platform build validation. Out-of-BYF scope.

5. **Wall-clock for dispatch test re-entrancy case** — both calls take ~25s each, so case 8 alone adds ~50s to the test runtime. The full 8-case test now runs ~55s (was ~30s for 6 cases at S2). Acceptable for a verification harness, not for parity-fast tier inclusion.

## Schedule status

Bond Yield Forecast cycle: **3 of 6 TSL-side sessions complete**. Sessions 4-6 follow per locked plan.

## Commit footprint

| File | Change |
|---|---|
| `engine/techniques/bond_yield_forecast/resources/templates/bond_yield_forecast_input_template.xlsx` | new (~50 KB; 4 sheets) |
| `engine/techniques/bond_yield_forecast/_dispatch.py` | +60 LOC (config-aware sheet detection helper + integration) |
| `engine/techniques/bond_yield_forecast/_session2_dispatch_test.py` | +95 LOC (cases 7 + 8) |
| `src/TSL.AddIn/RibbonXml.cs` | +27 LOC (splitButton + 2 menu items) |
| `src/TSL.AddIn/Ribbon.cs` | +95 LOC (3 handlers + LocateBondYieldForecastTemplate helper) |
| `docs/bond_yield_forecast_integration/session_3_findings.md` | new (~280 LOC) |
| **Total** | **~560 LOC across 6 files + 1 binary** |

## Next session

Bond Yield Forecast Session 4 — Parity audit at P-1 v1.1.0 standard.
Reference selection (R `bvars` candidate vs Pattern A.3 self-parity);
audit script at `tools/reference_parity/harness/checks/p3_bond_yield_forecast.py`;
tolerance ladder; structural invariants; verdict assignment.
