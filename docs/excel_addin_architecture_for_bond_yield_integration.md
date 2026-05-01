# Excel Add-in Architecture — Reference for Bond Yield Forecast Integration

**Purpose:** Read-only architecture discovery to plan integration of a new
Bond Yield Forecast method into the TSL Excel add-in.

**Scope:** No code modifications. This document describes the established
pattern "how a new method gets added to the Ribbon and wired to a Python
wrapper."

**Last verified:** 2026-04-30 against working tree at commit `80e5159`.

---

## 1. Excel add-in codebase location

The add-in lives in the **same Git repo** as the Python engine, under
`src/`. There is no separate sibling repo, no submodule, and no vendoring.

```
TimeSeriesLab/                              <- repo root
├── TimeSeriesLab.sln                       <- Visual Studio solution
├── src/
│   ├── TSL.AddIn/                          <- Excel add-in (C#, net48)
│   │   ├── AddIn.cs                        <- IExcelAddIn entry point
│   │   ├── Ribbon.cs                       <- COM Ribbon callbacks (handlers)
│   │   ├── RibbonXml.cs                    <- Office Ribbon XML (button definitions)
│   │   ├── EngineClient.cs                 <- Named Pipes client to Python worker
│   │   ├── ExcelWriter.cs                  <- Writes results to Excel sheets
│   │   ├── TaskPaneManager.cs              <- Custom Task Pane lifecycle + run dispatch
│   │   ├── TechniqueCatalogService.cs      <- Loads catalog JSON + markdown
│   │   ├── SettingsManager.cs              <- Per-user config.json
│   │   ├── SelectionService.cs             <- Reads Excel selection
│   │   ├── TimeIndexDetector.cs            <- Auto-detects time column
│   │   ├── TriggerManager.cs               <- THOROUGH UDF recompute trigger
│   │   ├── ResultStore.cs                  <- Run-record store (handle-based UDFs)
│   │   ├── Functions/
│   │   │   ├── AutoFunctions.cs            <- AUTO UDFs (TSL_GRANGER, etc.)
│   │   │   ├── ThoroughFunctions.cs        <- THOROUGH UDFs (TSL_RUN_THR, TSL_TABLE)
│   │   │   └── UdfHelpers.cs
│   │   ├── Models/
│   │   │   ├── RunRequest.cs               <- C# DTO sent to Python (JSON)
│   │   │   ├── RunResponse.cs              <- C# DTO received from Python
│   │   │   └── TechniqueCatalogEntry.cs
│   │   ├── TimeSeriesLab-AddIn.dna         <- Excel-DNA manifest
│   │   ├── TSL.AddIn.csproj
│   │   └── ...
│   ├── TSL.UI/                             <- WPF MVVM views (hosted in WinForms)
│   │   └── ... (Explorer, Run, Recommender, DataReadiness, UdfBrowser, Settings)
│   └── TSL.Installer/                      <- ClickOnce WPF installer
├── engine/                                 <- Python engine
│   ├── engine_worker.py                    <- Named pipe server main loop
│   ├── techniques/
│   │   ├── registry.py                     <- technique_id -> module path
│   │   ├── base.py                         <- RunContext, make_response, etc.
│   │   ├── var_model.py                    <- one technique
│   │   ├── ... (67+ technique modules)
│   ├── interpretation/                     <- 3-tier plain-language synthesis
│   └── ...
├── resources/
│   ├── catalog/techniques_catalog.json     <- canonical technique registry
│   └── techniques_md/                      <- per-technique markdown descriptions
└── tools/                                  <- build, generate, smoke scripts
```

**Solution-level summary:**
- 3 C# projects: `TSL.AddIn` (XLL), `TSL.UI` (WPF), `TSL.Installer` (ClickOnce installer).
- 1 Python tree at `engine/` (out-of-process worker; not built by Visual Studio).
- Shared canonical state: `resources/catalog/techniques_catalog.json` is read by **both** the C# add-in (`TechniqueCatalogService.GetCatalog()`) and the Python engine.

## 2. Excel-Python bridge architecture

**Bridge:** **Excel-DNA** (XLL via .NET Framework 4.8) + **Windows Named Pipes** + **JSON message protocol**.

NOT xlwings, NOT PyXLL, NOT VSTO, NOT pure-COM.

### 2.1 Add-in shell — Excel-DNA

The add-in is a `.xll` file produced by Excel-DNA from
`src/TSL.AddIn/TSL.AddIn.csproj`. Manifest at
`src/TSL.AddIn/TimeSeriesLab-AddIn.dna`:

```xml
<DnaLibrary Name="Time Series Lab" RuntimeVersion="v4.0" Language="CS">
  <ExternalLibrary Path="TSL.AddIn.dll" ExplicitExports="false" LoadFromBytes="true" Pack="false" />
</DnaLibrary>
```

The add-in is a **single .xll** loaded by Excel via `Tools → Add-ins`.
Entry point is `AddIn.cs` (`class AddIn : IExcelAddIn`):

```csharp
public void AutoOpen()
{
    Directory.CreateDirectory(AppDataPath);                              // %LOCALAPPDATA%\TimeSeriesLab\
    _settings = new SettingsManager(Path.Combine(AppDataPath, "config.json"));
    _resultStore = new ResultStore();
    _engineClient = new EngineClient();                                  // builds pipe-name TSL_ENGINE_PIPE_<SID>
    _engineClient.KillStaleEngineProcess();                              // kills orphan Python from prior session

    ExcelDna.IntelliSense.IntelliSenseServer.Install();                  // optional; UDF tooltips
    ExcelAsyncUtil.QueueAsMacro(() =>
    {
        ExcelComAddInHelper.LoadComAddIn(new Ribbon());                  // delayed Ribbon registration
    });
}
```

The `Ribbon` instance is registered **manually** via `ExcelComAddIn`, NOT
via Excel-DNA's auto-discovery. Reason (per code comment): so the TSL tab
appears AFTER external COM add-ins like Acrobat in the Ribbon.

### 2.2 Engine bridge — Named Pipes + JSON

The Python engine is a **separate process**, started lazily on first
analysis request, communicating via a Windows Named Pipe.

**Pipe naming** (from `EngineClient.cs:32`):
```csharp
var sid = WindowsIdentity.GetCurrent().User?.Value ?? "default";
_pipeName = $"TSL_ENGINE_PIPE_{sid}";
```

Per-user pipe; multiple Excel sessions for different users coexist.

**Protocol** (little-endian length-prefixed UTF-8 JSON, per
`engine_worker.py` docstring):

```
Client -> Server: [4-byte length][UTF-8 JSON RunRequest]
Server -> Client: [4-byte length][UTF-8 JSON progress event]  (0..N times)
Server -> Client: [4-byte length][UTF-8 JSON RunResponse]     (exactly once)
```

Progress messages and the final RunResponse are distinguished by a
`"type"` field on the JSON (see `EngineClient.cs:312` —
`if (string.Equals(msgType, "progress", ...))`).

**Process management** (`EngineClient.cs`):
- Engine spawned by `EnsureRunning()` on first RunAsync; stays warm across
  multiple runs in the same Excel session.
- PID file at `%LOCALAPPDATA%\TimeSeriesLab\engine.pid`.
- `KillStaleEngineProcess()` runs at AutoOpen so updated Python modules
  (e.g. an edited `var_model.py`) are picked up on Excel restart.
- `CancelCurrentRun()` does a hard `Process.Kill()` (no graceful protocol;
  the Python worker has no try/except for SIGTERM-equivalent shutdown).

**Python runtime** (from `EngineClient.cs:36-37`):
```csharp
private string EnginePath => Path.Combine(AddIn.AppDataPath, "engine");
private string PythonExePath => Path.Combine(EnginePath, "runtime", "python.exe");
private string WorkerScriptPath => Path.Combine(EnginePath, "engine_worker.py");
```

Production deployment: embedded Python under
`%LOCALAPPDATA%\TimeSeriesLab\engine\runtime\python.exe`. Dev fallback:
system `python` on PATH (`EngineClient.cs:117`).

### 2.3 Deployment model

**Production:** ClickOnce installer (`src/TSL.Installer/`) — copies the
`.xll`, the embedded Python runtime, the engine source tree, and the
catalog/markdown resources into `%LOCALAPPDATA%\TimeSeriesLab\`. The
installer also writes a registry entry so the .xll auto-loads on Excel
launch.

**Dev:** load `.xll` from `src/TSL.AddIn/bin/x64/Release/net48/` directly
via Excel `Tools → Add-ins` UI (or `Launch.cmd` script in repo root).
The engine is found via the `ResolveWorkerScript()` search path
(`EngineClient.cs:185-225`) which walks up to the repo's `engine/`
directory.

## 3. Ribbon definition

### 3.1 Ribbon XML

The Ribbon is defined in **Office Ribbon XML** (the standard 2009/07
schema), generated as a string by `RibbonXml.cs`:

```csharp
// src/TSL.AddIn/RibbonXml.cs:8
public static string GetXml()
{
    return @"
<customUI xmlns='http://schemas.microsoft.com/office/2009/07/customui'
         xmlns:tsl='TimeSeriesLab'
         onLoad='OnRibbonLoad'>
  <ribbon>
    <tabs>
      <tab idQ='tsl:tslTab' label='Time Series Lab'>
        <group id='grpQuickActions' label='Quick Actions'>
          <button id='btnVar'
                  label='VAR'
                  size='large'
                  imageMso='ChartTypeColumnInsertGallery'
                  onAction='OnVar'
                  screentip='Vector Autoregression (VAR)'
                  supertip='Fit a Vector Autoregression to a system ...' />
          ...
        </group>
        ...
      </tab>
    </tabs>
  </ribbon>
</customUI>";
}
```

The XML is returned to Excel via the COM `IRibbonExtensibility` interface
(defined locally in `Ribbon.cs:17-24` to avoid taking a dependency on the
Office PIA `office.dll`):

```csharp
[ComVisible(true)]
public class Ribbon : ExcelComAddIn, IRibbonExtensibility
{
    public string GetCustomUI(string ribbonId)
    {
        return RibbonXml.GetXml();
    }
}
```

**Tab structure** (from `RibbonXml.cs`):

| Group | Buttons |
|---|---|
| Quick Actions | VAR, PCA, DFM, Cointegration, Granger, Rolling CCF, Seasonal Adj, Forecast, Prophet, Conformal, Regime Switch, Change Point, GARCH, Structural TS |
| Explore | Technique Explorer (split button with category menu), Recommender, Data Readiness |
| Run | Preset (Fast/Balanced/Thorough toggle), **Run**, Cancel, Re-run Thorough, **Settings** |
| Help | UDF Formula Guide, User Guide, Sample Data |

### 3.2 End-to-end trace: VAR button

A user clicks the VAR button. Eight steps follow.

#### Step 1 — Ribbon XML declares the button + handler name

```xml
<!-- src/TSL.AddIn/RibbonXml.cs:20-26 -->
<button id='btnVar'
        label='VAR'
        size='large'
        imageMso='ChartTypeColumnInsertGallery'
        onAction='OnVar' />
```

`onAction='OnVar'` tells Excel to invoke a method named `OnVar` on the
COM Ribbon object when the button is clicked.

#### Step 2 — Ribbon class implements the handler

```csharp
// src/TSL.AddIn/Ribbon.cs:150-153
public void OnVar(IRibbonControl control)
{
    TaskPaneManager.RunTechnique("var");
}
```

The Ribbon handler is a one-liner: it forwards to
`TaskPaneManager.RunTechnique("var")` with the canonical `technique_id`
string. **All Quick Action handlers follow this pattern** (lines 150-229
in `Ribbon.cs`).

#### Step 3 — TaskPaneManager opens the pane + dispatches

```csharp
// src/TSL.AddIn/TaskPaneManager.cs:46-55
public static void RunTechnique(string techniqueId)
{
    EnsureTaskPane();                                              // create if first time
    _taskPane.Visible = true;
    OnRunRequested(techniqueId, AddIn.Settings?.GetGlobalPreset() ?? "Balanced");
}
```

`EnsureTaskPane()` constructs a WinForms `TaskPaneHostControl` (which
hosts the WPF UI via `ElementHost`) and registers the run-request event.

#### Step 4 — OnRunRequested extracts data + builds RunRequest

```csharp
// src/TSL.AddIn/TaskPaneManager.cs:176-361
private static void OnRunRequested(string techniqueId, string preset)
{
    // Read selected columns from Excel
    var selectionResult = _selectionService.ExtractFromSelection();

    // Auto-detect time index (left-most date column)
    var detection = _timeDetector.Detect(firstArea, ...);
    string[] timeArray = detection.ParsedDates;
    string detectedFrequency = detection.BestCandidate?.SuggestedFrequency;

    // Navigate WPF Run view + populate previews
    _hostControl.ViewModel.NavigateToRun(techniqueId);
    runVm.SetSeriesPreviews(...);
    runVm.IsRunning = true;

    // Build the RunRequest (DTO that serializes to JSON for the engine)
    var paramsDict = runVm.GetParametersDict();
    var request = new RunRequest
    {
        RunId = $"pane_{Guid.NewGuid():N}",
        TechniqueId = techniqueId,                                 // "var"
        Preset = preset ?? "Balanced",
        Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
        Time = timeArray,
        Frequency = detectedFrequency,
        Series = selectionResult.Series.Select(s => new SeriesData { ... }).ToList(),
        Params = paramsDict,
        FillConfig = new FillConfig(),
    };

    // Run async on background thread
    Task.Run(async () =>
    {
        AddIn.Engine.EnsureRunning();
        AddIn.Engine.ProgressReceived += progressHandler;
        var response = await AddIn.Engine.RunAsync(request);

        // Write results to Excel on the main thread (COM requires it)
        ExcelAsyncUtil.QueueAsMacro(() =>
        {
            var writeResult = ExcelWriter.WriteRunResult(request, response);
            ...
            runVm.CompleteRun(summary, sheets);
        });
    });
}
```

#### Step 5 — EngineClient sends RunRequest over the pipe

```csharp
// src/TSL.AddIn/EngineClient.cs:231-262
public async Task<RunResponse> RunAsync(RunRequest request, CancellationToken ct = default)
{
    EnsureRunning();
    var requestJson = JsonConvert.SerializeObject(request);        // C# DTO -> JSON
    var responseJson = await SendAndReceiveAsync(requestJson, _currentRunCts.Token);
    return JsonConvert.DeserializeObject<RunResponse>(responseJson);
}
```

The JSON is length-prefixed and written to the Named Pipe; progress events
arrive as multiple framed JSON messages, terminated by the final
RunResponse (`SendAndReceiveAsync` at lines 264-335 distinguishes
progress-vs-final by `"type"` field).

#### Step 6 — Python engine dispatches via registry

```python
# engine/engine_worker.py:329-350
def _load_technique(technique_id: str):
    from techniques.registry import TECHNIQUE_REGISTRY
    module_path = TECHNIQUE_REGISTRY.get(technique_id)
    if module_path is None:
        raise ValueError(f"Unknown technique '{technique_id}'. ...")

    if module_path not in _module_cache:
        _module_cache[module_path] = importlib.import_module(module_path)

    mod = _module_cache[module_path]
    if not hasattr(mod, "run"):
        raise ValueError(f"Technique module '{module_path}' has no 'run' function.")
    return mod.run
```

For VAR, `TECHNIQUE_REGISTRY["var"] = "techniques.var_model"`
(`engine/techniques/registry.py:48`). The dispatcher imports
`engine/techniques/var_model.py` lazily and caches it.

#### Step 7 — Technique module computes and returns RunResponse

```python
# engine/techniques/var_model.py:46-373 (abridged)
def run(ctx: RunContext, progress_callback) -> dict:
    progress_callback("Validating inputs", 5)
    ctx.validate_min_series(2)
    ...
    progress_callback("Fitting VAR", 60)
    fit = VAR(data).fit(maxlags=p, ic=ic, trend=trend_param)
    ...
    return make_response(
        ctx,
        tables=[fc_table, irf_table, fevd_table, summary_table, ...],
        plain_english_summary=plain,
        warnings=warn_list,
        charting_suggestions=charting,
        interpretation=interp,
        audit_fields={"var_order": p, "n_variables": k, ...},
    )
```

`make_response` and `make_table` (in `engine/techniques/base.py`) build
the JSON-shaped dict that the engine worker writes back to the pipe.

#### Step 8 — ExcelWriter renders the response back to the workbook

`ExcelWriter.WriteRunResult(request, response)` (`ExcelWriter.cs:98-171`)
runs **on the main thread** (COM requirement, hence the
`ExcelAsyncUtil.QueueAsMacro` wrap). It produces:

1. A new `Results` sheet (e.g. "VAR Results"; sheet name unique-suffixed
   if a prior one exists) inserted **before** the source sheet.
2. A new `Audit` sheet with seed, package versions, run timestamp.
3. An embedded JSON record on a hidden `_TSL_RUNS` sheet (used by
   handle-based THOROUGH UDFs for re-extraction).
4. Activates the Results sheet so the user lands on the Summary block.

## 4. Button-to-wrapper pattern

### 4.1 What clicking VAR does

**(c) Opens / shows the Task Pane sidebar** (the WPF UI hosted in a
`CustomTaskPane` on the right edge of Excel). Specifically:

1. Reads the current Excel cell selection (handled by `SelectionService`).
2. Auto-detects the time-index column (handled by `TimeIndexDetector`).
3. Navigates the Task Pane to the **Run** view, populated with the
   detected series previews + the technique's parameter controls
   (rendered from `parameters[]` in the catalog JSON).
4. **Immediately kicks off the analysis** with the active preset
   (`Fast`/`Balanced`/`Thorough` from the Preset menu).
5. Streams progress to the Run view's progress log.
6. On completion, writes a Results sheet + Audit sheet + activates Results.

This is the **one-click** Quick Action path: ribbon click → Task Pane open
→ analysis kicked off → Results sheet ready, in a single user gesture.
There's no separate configuration dialog before the run; the Task Pane is
the configuration surface (the user can re-run with edited params using
the Run button — see §4.3).

### 4.2 Settings button role

```csharp
// src/TSL.AddIn/Ribbon.cs:335-338
public void OnSettings(IRibbonControl control)
{
    TaskPaneManager.ShowSettings();
}
```

`ShowSettings()` navigates the Task Pane to the **Settings view**, which
edits a per-user `config.json` at
`%LOCALAPPDATA%\TimeSeriesLab\config.json`. Settings are global to the
add-in (default seed, fill method, missing-value handling, default
preset) — NOT per-method configuration of the Quick Action buttons. A
Quick Action is "always run with current global preset"; per-run
parameter customization happens in the Run view's parameter controls
**after** the user clicks the button.

### 4.3 Run button role

```csharp
// src/TSL.AddIn/Ribbon.cs:319-322
public void OnRun(IRibbonControl control)
{
    TaskPaneManager.RunCurrent();
}
```

`RunCurrent()` re-executes the **currently configured** technique in the
Task Pane (whichever technique was last selected via Quick Action /
Explorer / Recommender). Used after the user edits parameters (e.g.
changing `max_lags` from 12 → 6 in the VAR Run view) and wants to
re-fit. The Run button is essentially "re-run with my current edits to
the parameters in the Task Pane."

This is distinct from the Cancel / Re-run Thorough buttons:
- **Cancel** (`Ribbon.cs:324-327`): hard-kills the engine process for an
  in-flight run.
- **Re-run Thorough** (`Ribbon.cs:329-333`): increments a workbook-scoped
  trigger token in `_TSL_META` that THOROUGH UDF formulas (e.g.
  `=TSL_RUN_THR(...)`) read — forces all THOROUGH formulas to recompute
  without changing their input cells.

## 5. Output-to-Excel pattern

### 5.1 The pattern

Every Quick Action / Run produces THREE artifacts:

| Artifact | Location | Content |
|---|---|---|
| **Results sheet** (e.g. "VAR Results") | New sheet inserted before the source sheet | Summary, Interpretation, Warnings, Diagnostics, **all output tables** as rendered cell ranges |
| **Audit sheet** (e.g. "VAR Audit") | New sheet | Run ID, technique ID, preset, seed, timestamp, package versions, audit fields |
| **Embedded JSON record** | `_TSL_RUNS` hidden sheet | Full `RunResponse` JSON, keyed by run ID; used by handle-based THOROUGH UDFs |

The rendering is handled entirely by `ExcelWriter.cs`. The Python engine
returns a structured `RunResponse` object (logical tables, summary text,
audit fields, etc.); ExcelWriter is the ONLY place that knows how to
project that into an Excel sheet.

### 5.2 Standard output schema across methods

Yes, there is a **uniform output schema**. Every technique returns a
`RunResponse` with the same shape (`src/TSL.AddIn/Models/RunResponse.cs`):

```csharp
public class RunResponse
{
    public string RunId;
    public string Status;                                  // "success" | "failure"
    public string PlainEnglishSummary;                     // 1-3 sentence narrative
    public List<OutputTable> Tables;                       // logical data tables
    public Dictionary<string, object> Artifacts;
    public List<string> Warnings;
    public Dictionary<string, object> AuditFields;         // diagnostics + audit
    public EngineVersions EngineVersions;
    public string ChartingSuggestions;
    public string ErrorMessage;
    public List<string> ErrorFixes;
    public Interpretation Interpretation;                  // 3-tier plain-language
}

public class OutputTable
{
    public string Name;                                    // e.g. "Forecasts"
    public string[] Columns;                               // e.g. ["Time", "y_hat", ...]
    public object[][] Rows;                                // 2D data
}

public class Interpretation
{
    public string Tier1;                                   // plain-language finding
    public string Tier2;                                   // technical interpretation
    public List<string> Tier3;                             // conditional caveats
}
```

The **per-technique variation** is in:
- The number and naming of `OutputTable`s (VAR has Forecasts, IRF, FEVD,
  Model Summary, Coefficients, Granger; PCA has Loadings, Scores,
  Variance Explained; etc.).
- The fields inside `AuditFields`.

ExcelWriter renders each `OutputTable` as a labeled cell block (bold
header row, then data rows), with NumberFormat propagation:
- "Time" / "Date" / "Timestamp" columns get the source time-column
  NumberFormat.
- Columns named `Seasonally Adjusted`, `Trend`, `Seasonal`, `Irregular`,
  `Fitted`, `Forecast`, `Level`, `Lower`, `Upper`, `Residual`, OR matching
  the input series name → get the source series NumberFormat (so units
  carry through).
- Everything else (ratios, lags, coefficients) → Excel default.

### 5.3 No charts, no named ranges, no dynamic arrays

The Quick Action path produces **plain cell-block output**, not charts or
named ranges or dynamic-array spilled formulas. Charting is suggested via
`response.ChartingSuggestions` (a free-text string surfaced to the user)
but not auto-rendered; users add charts manually from the Results sheet.

Dynamic-array UDFs (`=TSL_GRANGER(...)`, `=TSL_RUN_THR(...)`,
`=TSL_TABLE(...)`) are a **parallel** code path (`Functions/AutoFunctions.cs`
+ `Functions/ThoroughFunctions.cs`); they run the same engine but render
results as spilled arrays via Excel-DNA's `IExcelObservable`/
`ExcelAsyncUtil`. The Quick Action ribbon path does NOT use UDFs —
every Quick Action produces sheet-level output. UDFs are an
alternative entry point for users who prefer spreadsheet-native workflows.

## 6. Existing wrapper integration pattern — how a new method gets added

A new technique becomes available end-to-end (Ribbon button → Python
wrapper → Excel output) by touching **5 places**. There is no single
registration decorator; instead, the technique appears in 5 file
locations, all keyed off a single canonical `technique_id` string. The
technique_id is the identifier that flows through every layer.

### The 5 places

#### Place 1 — Python technique module (the actual algorithm)

`engine/techniques/<technique_id>.py` — implements `run(ctx, progress_callback) -> dict`.

Contract (from `engine/techniques/base.py`):
- Receives `ctx: RunContext` (parsed from RunRequest JSON; exposes
  `ctx.series`, `ctx.params`, `ctx.preset`, `ctx.seed`, `ctx.time`,
  `ctx.frequency`).
- Calls `progress_callback(stage_name: str, pct: int, message: str = None)`
  to stream progress over the pipe.
- Returns `make_response(ctx, tables=[...], plain_english_summary=...,
  warnings=..., charting_suggestions=..., interpretation=...,
  audit_fields={...})`.

Pattern: see `engine/techniques/var_model.py` (374 LOC) for a representative
example. Helpers `make_table(name, columns, rows)`, `make_response(...)`,
and `make_error_response(...)` are in `engine/techniques/base.py`.

#### Place 2 — Python registry mapping

`engine/techniques/registry.py`:

```python
TECHNIQUE_REGISTRY = {
    ...
    "var_model": "techniques.var_model",
    "var": "techniques.var_model",                         # alias
    ...
}
```

Both the canonical id and any aliases map to the same module path. The
engine's `_load_technique` (`engine/engine_worker.py:329`) does an
`importlib.import_module(module_path)` to import lazily.

#### Place 3 — Catalog entry (canonical metadata)

`resources/catalog/techniques_catalog.json`:

```json
{
  "id": "var",
  "name": "Vector Autoregression (VAR)",
  "category": "Multivariate Systems",
  "summary": "Fit a VAR model to multiple time series for joint forecasting and impulse responses.",
  "description_file": "var.md",
  "min_series": 2,
  "max_series": null,
  "supports_auto_udf": false,
  "auto_udf_name": null,
  "presets": ["Fast", "Balanced", "Thorough"],
  "parameters": [
    { "name": "max_lags", "label": "Max Lags", "type": "int", "default": 12, ... },
    { "name": "ic", "label": "Info Criterion", "type": "string", "default": "aic",
      "options": ["aic", "bic", "hqic"], ... },
    { "name": "horizon", "label": "Forecast Horizon", "type": "int", "default": 12, ... }
  ],
  "output_tables": ["forecasts", "irf", "fevd", "model_summary"],
  "tags": ["multivariate", "var", ...]
}
```

The catalog is read by **both** sides:
- C# `TechniqueCatalogService.GetCatalog()` (`src/TSL.AddIn/TechniqueCatalogService.cs`)
  — populates the Technique Explorer + drives the Run view's parameter
  controls (the `parameters[]` array becomes checkboxes / dropdowns / text
  boxes in WPF).
- Python `engine/` reads it for cross-checks if needed.

The `min_series` / `max_series` fields drive the Selection validation
(error if user selected fewer/more columns than supported).

#### Place 4 — Markdown description (long-form documentation)

`resources/techniques_md/<id>.md` — ~2500 chars typical. Rendered in the
Technique Explorer's description pane and in the User Guide.

#### Place 5 — Ribbon button (only if it's a Quick Action)

NOT every technique gets a Ribbon button — the catalog has 67+
techniques but only 14 Quick Action buttons (the most-used macro
strategist toolkit). For a technique that warrants a button:

**5a — Add the button to `RibbonXml.cs`:**

```csharp
<button id='btnVar'
        label='VAR'
        size='large'
        imageMso='ChartTypeColumnInsertGallery'
        onAction='OnVar'
        screentip='Vector Autoregression (VAR)'
        supertip='Fit a Vector Autoregression to a system of time series. Produces impulse-response functions, variance decompositions, and forecasts for each variable.' />
```

**5b — Add the handler to `Ribbon.cs`:**

```csharp
public void OnVar(IRibbonControl control)
{
    TaskPaneManager.RunTechnique("var");
}
```

**5c (optional) — Add a sample-data entry** in `Ribbon.cs:43-126`'s
`_sampleDatasetByTechnique` dictionary so the Sample Data menu has a
"VAR Data: Macro VAR" entry:

```csharp
{ "var", ("macro_var.csv", "Macro VAR") },
```

A technique without a Ribbon button is still fully usable via the
Technique Explorer (the catalog drives the Explorer view; any catalog
entry is automatically accessible there).

### The "registration mechanism" question

There is **no decorator-based or factory-based registration**. The 5
places above are independently authored and keyed by the
`technique_id` string. Specifically:

- **No `@register_technique("var")` decorator** in Python.
- **No `[ExcelTechnique("var")]` attribute** in C#.
- **No central manifest** beyond `techniques_catalog.json` (which itself
  is a flat JSON list of entries, not a registration system).

The discipline is:
1. The same `technique_id` string appears in: catalog JSON `"id"` field,
   registry.py key (and any aliases), Ribbon button's `OnX` handler call
   to `RunTechnique("x")`, and the Python module's filename (by
   convention).
2. The catalog JSON is the **canonical source of truth** for everything
   user-visible (name, category, parameters, tables, tags); Python
   modules implement the algorithm; the Ribbon is a curated subset.
3. Drift between the 5 places is caught at **runtime**: if you click a
   Ribbon button whose technique_id isn't in the registry, the engine
   raises `ValueError: Unknown technique 'x'`; if the catalog references
   a technique_id whose module is missing, importlib raises ModuleNotFoundError;
   if a registry entry exists without a catalog entry, the technique runs
   but is invisible in the Explorer / Run view.

### Concrete checklist for adding **Bond Yield Forecast**

Assuming the chosen `technique_id` is `bond_yield_forecast`:

1. **Place 1** — write `engine/techniques/bond_yield_forecast.py` with
   `def run(ctx, progress_callback) -> dict` returning
   `make_response(...)`. Add any new pip dep to
   `engine/requirements.lock.txt` AND
   `tools/reference_parity/harness/MANIFEST.toml`'s `[python.packages]`
   per [P-1 §7.2](engineering/parity_standard.md#72-adding-a-new-dep-b)
   if it surfaces numerical output that warrants a parity check.
2. **Place 2** — register `"bond_yield_forecast": "techniques.bond_yield_forecast"`
   (and any aliases like `"bond_yield"`) in
   `engine/techniques/registry.py`.
3. **Place 3** — add a catalog entry to
   `resources/catalog/techniques_catalog.json` with `id`, `name`,
   `category`, `summary`, `description_file`, `min_series`, `max_series`,
   `parameters[]`, `output_tables[]`, `tags[]`.
4. **Place 4** — write `resources/techniques_md/bond_yield_forecast.md`
   (the long-form description; ~2500 chars).
5. **Place 5** (optional, if it gets a Quick Action button):
   - Add `<button id='btnBondYield' ... onAction='OnBondYieldForecast' />`
     to `RibbonXml.cs` inside an appropriate `<group>`.
   - Add `public void OnBondYieldForecast(IRibbonControl control) {
     TaskPaneManager.RunTechnique("bond_yield_forecast"); }` to
     `Ribbon.cs`.
   - Optionally add a sample-data tuple to `_sampleDatasetByTechnique` in
     `Ribbon.cs`.

### One thing to confirm before integration

The above pattern is for a Phase 3-style technique surfacing a
`run(ctx, progress_callback) -> dict` function. **If Bond Yield Forecast
needs cross-validation against an external reference implementation
(e.g. a published yield-curve forecasting reference like Diebold-Li),
also consider adding a parity check** under
`tools/reference_parity/harness/checks/` per the P-1 standard. This is
NOT required for first-pass integration but is recommended once the
wrapper math is stable.

The parity-check pattern has its own discipline (verdict_class,
fixture_id, R/Py reference) documented in:
- [P-1 parity standard](engineering/parity_standard.md) v1.1.0 (binding directive)
- [P-2 parity diagnostic reference](engineering/parity_diagnostic_reference.md) v1.1.0 (descriptive playbook)

This is independent of the Excel-side integration above; the parity
check runs in CI, not in the Excel add-in.

---

## Quick reference — file-path index

| Question | File |
|---|---|
| Excel add-in entry point | `src/TSL.AddIn/AddIn.cs` |
| Excel-DNA manifest | `src/TSL.AddIn/TimeSeriesLab-AddIn.dna` |
| Ribbon XML (button definitions) | `src/TSL.AddIn/RibbonXml.cs` |
| Ribbon callbacks (button handlers) | `src/TSL.AddIn/Ribbon.cs` |
| Task Pane lifecycle + run dispatch | `src/TSL.AddIn/TaskPaneManager.cs` |
| Named Pipes client to Python | `src/TSL.AddIn/EngineClient.cs` |
| Excel output rendering | `src/TSL.AddIn/ExcelWriter.cs` |
| C# DTOs (RunRequest / RunResponse) | `src/TSL.AddIn/Models/` |
| Catalog JSON loader | `src/TSL.AddIn/TechniqueCatalogService.cs` |
| AUTO UDFs | `src/TSL.AddIn/Functions/AutoFunctions.cs` |
| THOROUGH UDFs | `src/TSL.AddIn/Functions/ThoroughFunctions.cs` |
| WPF views (hosted in WinForms) | `src/TSL.UI/` |
| ClickOnce installer | `src/TSL.Installer/` |
| Python pipe server | `engine/engine_worker.py` |
| Python technique registry | `engine/techniques/registry.py` |
| Python technique base helpers | `engine/techniques/base.py` |
| Python technique modules | `engine/techniques/*.py` (67+ files) |
| Canonical catalog JSON | `resources/catalog/techniques_catalog.json` |
| Long-form descriptions | `resources/techniques_md/*.md` |
| Build / pack scripts | `tools/build_pack.ps1`, `tools/smoke_tests.ps1` |
| Parity standard (P-1 v1.1.0) | `docs/engineering/parity_standard.md` |
| Diagnostic reference (P-2 v1.1.0) | `docs/engineering/parity_diagnostic_reference.md` |
