using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;
using Microsoft.Office.Interop.Excel;
using TSL.AddIn.Models;
using TSL.UI;
using TSL.UI.ViewModels;

namespace TSL.AddIn
{
    /// <summary>
    /// Manages the Custom Task Pane lifecycle. Excel-DNA requires a WinForms UserControl
    /// as the root host; we then embed a WPF ElementHost inside it.
    /// </summary>
    public static class TaskPaneManager
    {
        private static CustomTaskPane _taskPane;
        private static TSL.UI.TaskPaneHostControl _hostControl;
        private static readonly SelectionService _selectionService = new SelectionService();
        private static readonly TimeIndexDetector _timeDetector = new TimeIndexDetector();

        // Cancellation source for the in-flight run. Created per dispatch; its
        // token is passed to Engine.RunAsync so the Run view's Cancel button can
        // actually abort the run (in addition to the hard engine kill).
        private static System.Threading.CancellationTokenSource _activeRunCts;

        // What the Run view was last filled from (A2 U6, N5): the workbook, the sheet and
        // the extracted columns' addresses. A Run click on a different selection runs nothing.
        // The workbook and sheet are compared as objects, so saving or renaming them is no change.
        private static Workbook _previewedWorkbook;
        private static Worksheet _previewedSheet;
        private static string _previewedAddresses;

        // The workbook a Bespoke tool's Run view is set up for (A2 U6, B7 / N9): Run reads
        // it, never whichever workbook is active at the click (after a run, that is the
        // results workbook). Kept as the object and its full name, so a workbook that was
        // saved under a new name, or closed and reopened, is still found.
        private static Workbook _bespokeInputWorkbook;
        private static string _bespokeInputFullName;
        private static string _bespokeInputTechniqueId;

        // Results workbooks this Excel session created (full names): never a Bespoke input.
        private static readonly HashSet<string> _resultsWorkbooks =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase);

        // Task pane runs dispatched and not yet returned from the engine. The Run view's
        // IsRunning can be reset under a run (opening another technique), so the ribbon's
        // Run and Cancel also look here.
        private static int _paneRunsInFlight;

        // House-message areas (docs/HOUSE_STYLE.md, A2 ratification Q2): every message
        // names the action it came from, written exactly as its button is labelled.
        // The Techniques group's Quick Action buttons (RibbonXml.cs grpQuickActions),
        // technique id -> ribbon label; keep in step with the ribbon.
        private static readonly Dictionary<string, string> QuickActionLabels =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                { "var", "VAR" },
                { "pca_analysis", "PCA" },
                { "dynamic_factor_model", "DFM" },
                { "vecm", "Cointegration" },
                { "granger_causality", "Granger" },
                { "rolling_ccf_lag", "Rolling CCF" },
                { "stl_decompose", "Seasonal Adj" },
                { "auto_arima", "Forecast" },
                { "prophet_forecast", "Prophet" },
                { "conformal_intervals", "Conformal" },
                { "markov_switching", "Regime Switch" },
                { "pelt_change_points", "Change Point" },
                { "garch", "GARCH" },
                { "structural_ts", "Structural TS" },
            };

        // The Bespoke group's tools (RibbonXml.cs grpBespoke), technique id -> menu label.
        private static readonly Dictionary<string, string> BespokeLabels =
            new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase)
            {
                { "bond_yield_forecast", "Bond Yield Forecast" },
                { "breakeven_payroll", "Breakeven Payrolls" },
                { "kronos_forecast", "Kronos Forecast" },
            };

        private const string RunArea = "Run";
        private const string ExplorerArea = "Technique Explorer";

        /// <summary>
        /// Show the task pane (create if needed) and open the Technique
        /// Explorer pre-selected to <paramref name="techniqueId"/>. Used by
        /// Task Pane navigation flows that want the user to read the
        /// description before running.
        /// </summary>
        public static void ShowAndSelect(string techniqueId)
        {
            if (!EnsureTaskPane(ExplorerArea)) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToTechnique(techniqueId);
        }

        /// <summary>
        /// Show the task pane and navigate to the Run view for
        /// <paramref name="techniqueId"/> with the selection + parameters
        /// populated, then WAIT for the user to click Run. No technique
        /// auto-runs on ribbon-click: the platform produces publishable output
        /// under the user's name, so nothing executes before the user reviews
        /// the pane and clicks Run (the same configure-then-run contract the
        /// Bespoke workbook techniques use). The Run click raises RunRequested
        /// → OnRunRequested → the engine.
        /// </summary>
        public static void RunTechnique(string techniqueId)
        {
            // A ribbon Quick Action: its messages carry the button's label (A2 Q2).
            QuickActionLabels.TryGetValue(techniqueId ?? "", out var label);
            OpenPopulated(techniqueId, label, label != null ? $"click {label} again" : "try again");
        }

        /// <summary>
        /// Fill the Run view from the selection and WAIT (execute:false): the user's Run
        /// click (RunRequested → OnRunRequested) runs it. Mirrors the Bespoke OpenXxxConfig
        /// open-pane-then-wait. <paramref name="area"/> and <paramref name="retry"/> word
        /// the selection refusals for the action that launched it.
        /// </summary>
        private static void OpenPopulated(string techniqueId, string area, string retry)
        {
            if (!EnsureTaskPane(area)) return;
            _taskPane.Visible = true;
            LaunchTechnique(techniqueId, AddIn.Settings?.GetGlobalPreset() ?? "Balanced",
                execute: false, area: area, retry: retry);
        }

        /// <summary>
        /// One-shot run for a WORKBOOK-INPUT technique (e.g. Bond Yield
        /// Forecast). Unlike <see cref="RunTechnique"/>, this does NOT extract
        /// a cell selection — workbook-input techniques have no series
        /// selection; the engine reads its input from a path passed in
        /// <paramref name="injectedParams"/> (e.g. "input_workbook"). Dispatch
        /// and result-rendering reuse the same technique-agnostic
        /// engine + ExcelWriter path that the selection flow uses.
        ///
        /// Deliberately a SEPARATE method (not a refactor of OnRunRequested):
        /// the selection path must stay byte-identical so every other ribbon
        /// button is provably unaffected.
        /// </summary>
        public static void RunTechniqueWithParams(
            string techniqueId, IDictionary<string, object> injectedParams,
            string cleanupTempFile = null,
            string sourceWorkbookName = null, string sourceWorkbookPath = null)
        {
            if (string.IsNullOrEmpty(techniqueId)) return;

            BespokeLabels.TryGetValue(techniqueId, out var tool);
            if (!EnsureTaskPane(tool)) return;
            _taskPane.Visible = true;

            // Navigate to the Run view so progress + result-sheet links render.
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            try
            {
                var techEntry = TechniqueCatalogService.GetTechnique(techniqueId);
                if (techEntry != null && !string.IsNullOrEmpty(techEntry.Name))
                    runVm.TechniqueName = techEntry.Name;
                runVm.TechniqueSummary = techEntry?.Summary ?? "";
                runVm.TechniqueId = techniqueId;
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not resolve technique metadata for {techniqueId}: {ex.Message}");
            }

            runVm.IsRunning = true;

            var preset = AddIn.Settings?.GetGlobalPreset() ?? "Balanced";
            var request = new RunRequest
            {
                RunId = $"pane_{Guid.NewGuid():N}",
                TechniqueId = techniqueId,
                Preset = preset,
                Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                Time = null,
                Frequency = null,
                // Workbook-input technique: no cell-selection series. The engine
                // reads its data from the path(s) in Params.
                Series = new List<SeriesData>(),
                Params = injectedParams != null
                    ? new Dictionary<string, object>(injectedParams)
                    : new Dictionary<string, object>(),
                FillConfig = new FillConfig(),
                // Anchor the results filename/folder to the ORIGINAL input
                // workbook (passed by the launcher), not the active workbook.
                SourceWorkbookName = sourceWorkbookName,
                SourceWorkbookPath = sourceWorkbookPath,
            };

            // Run async (mirrors the selection flow's dispatch tail; ExcelWriter
            // renders the engine's tables to the Results/Audit sheets
            // technique-agnostically).
            _activeRunCts = new System.Threading.CancellationTokenSource();
            var runToken = _activeRunCts.Token;
            System.Threading.Interlocked.Increment(ref _paneRunsInFlight);
            Task.Run(async () =>
            {
                Action<ProgressEvent> progressHandler = (evt) =>
                {
                    // Progress updates are fire-and-forget UI refreshes (no
                    // return value, order/drop-tolerant). Post them with the
                    // NON-BLOCKING BeginInvoke so the pipe-read thread — which
                    // invokes this handler synchronously per progress event —
                    // NEVER blocks on the Excel UI thread. A blocking Invoke
                    // here can stall the read loop mid-run, starving the named
                    // pipe; the engine then blocks in FlushFileBuffers waiting
                    // for the client to drain, deadlocking the run at completion
                    // (the "95%" hang) and orphaning the engine process.
                    // BeginInvoke keeps the reader draining continuously.
                    _hostControl?.BeginInvoke((System.Action)(() =>
                    {
                        runVm.ReportProgress(evt.Stage, evt.Pct, evt.Message ?? evt.Stage);
                    }));
                };

                try
                {
                    AddIn.Engine.EnsureRunning();
                    AddIn.Engine.ProgressReceived += progressHandler;

                    var response = await AddIn.Engine.RunAsync(request, runToken);

                    AddIn.Engine.ProgressReceived -= progressHandler;

                    if (runToken.IsCancellationRequested || response.Status == "canceled")
                    {
                        // User canceled — OnCancelRequested already reset the view
                        // and hard-stopped the engine; don't write results.
                    }
                    else if (response.Status == "failure")
                    {
                        _hostControl?.Invoke((System.Action)(() =>
                        {
                            runVm.FailRun(EngineFailureText(response));
                        }));
                    }
                    else
                    {
                        ExcelAsyncUtil.QueueAsMacro(() =>
                        {
                            // A Cancel between the engine's reply and this step: write nothing
                            // (the pane already says "The run was canceled. Nothing was written.").
                            if (runToken.IsCancellationRequested)
                            {
                                Logger.Info("Run canceled before its results were written; nothing was written.");
                                return;
                            }
                            ExcelWriter.WriteResult writeResult = null;
                            try
                            {
                                writeResult = ExcelWriter.WriteRunResult(request, response);
                                RememberResultsWorkbook(writeResult);
                            }
                            catch (Exception writeEx)
                            {
                                Logger.Error("ExcelWriter.WriteRunResult threw on main thread.", writeEx);
                            }

                            // Kronos Forecast (EXPERIMENTAL): overlay the fan chart
                            // on the freshly written results sheet. Best-effort
                            // enhancement -- the tables already carry the data; a
                            // chart failure never fails the run.
                            if (writeResult != null && writeResult.Success &&
                                string.Equals(request?.TechniqueId, "kronos_forecast",
                                    StringComparison.OrdinalIgnoreCase))
                            {
                                try { ExcelWriter.TryAddKronosFanChart(writeResult.ResultSheetName); }
                                catch (Exception chartEx)
                                { Logger.Info($"Kronos fan chart skipped: {chartEx.Message}"); }
                            }

                            // Run-archiving (owner ruling, K3.1): every successful
                            // Bespoke workbook-input run self-archives the results
                            // workbook to <repoRoot>\output\{tool}_runs\. Placed
                            // AFTER the chart hook so the archived copy contains
                            // the chart. Best-effort -- never fails the run.
                            if (writeResult != null && writeResult.Success &&
                                _workbookInputTechniques.Contains(request?.TechniqueId ?? ""))
                            {
                                try
                                {
                                    ExcelWriter.TryArchiveRunWorkbook(
                                        request?.TechniqueId, writeResult.ResultSheetName,
                                        response?.AuditFields);
                                }
                                catch (Exception archEx)
                                { Logger.Info($"Run archive skipped: {archEx.Message}"); }
                            }

                            _hostControl?.Invoke((System.Action)(() =>
                            {
                                PresentResult(runVm, response, writeResult);
                            }));
                        });
                    }
                }
                catch (Exception ex)
                {
                    AddIn.Engine.ProgressReceived -= progressHandler;
                    Logger.Error("Task pane run-with-params failed.", ex);
                    _hostControl?.Invoke((System.Action)(() =>
                    {
                        // A cancel while the engine was starting: the Cancel click already reset the view.
                        if (ex is OperationCanceledException) return;
                        runVm.FailRun(RunExceptionText(ex));
                    }));
                }
                finally
                {
                    System.Threading.Interlocked.Decrement(ref _paneRunsInFlight);

                    // Delete the per-run temp workbook copy once the engine has
                    // finished reading it. By the time RunAsync has returned (or
                    // thrown), the engine is done with the input file and the
                    // results are rendered from the in-memory response, so the
                    // temp copy is no longer needed. Best-effort.
                    if (!string.IsNullOrEmpty(cleanupTempFile))
                    {
                        try
                        {
                            if (System.IO.File.Exists(cleanupTempFile))
                                System.IO.File.Delete(cleanupTempFile);
                        }
                        catch (Exception delEx)
                        {
                            Logger.Info($"Temp workbook cleanup failed for {cleanupTempFile}: {delEx.Message}");
                        }
                    }
                }
            });
        }

        /// <summary>
        /// Open the Run view for Bond Yield Forecast in CONFIGURE-then-run mode:
        /// surface the curated parameters (pre-filled with catalog defaults),
        /// enable Run without a cell selection, and route the Run button to the
        /// workbook-input dispatch. Replaces the immediate one-shot so the user
        /// can edit horizon / scenario / chain length / prior tightness first.
        /// </summary>
        public static void OpenBondYieldForecastConfig()
        {
            if (!EnsureTaskPane("Bond Yield Forecast")) return;
            _taskPane.Visible = true;

            const string techniqueId = "bond_yield_forecast";
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            try
            {
                var techEntry = TechniqueCatalogService.GetTechnique(techniqueId);
                if (techEntry != null && !string.IsNullOrEmpty(techEntry.Name))
                    runVm.TechniqueName = techEntry.Name;
                runVm.TechniqueSummary = techEntry?.Summary ?? "";
                runVm.TechniqueId = techniqueId;

                // Curated, forecasting-intent params only (README's named knobs):
                // scenario, horizon, chain length (n_draws/n_burn), prior tightness
                // (lambda_1/2/3). The 4 sampler internals (n_paths_per_draw,
                // n_draws_subsample, projection_uncertainty, seed) stay at catalog
                // defaults; input_workbook is auto-resolved at Run-click.
                if (techEntry?.Parameters != null)
                {
                    var curated = new[]
                    {
                        "scenario", "horizon", "n_draws", "n_burn",
                        "lambda_1", "lambda_2", "lambda_3",
                    };
                    var specs = techEntry.Parameters
                        .Where(p => curated.Contains(p.Name))
                        .OrderBy(p => Array.IndexOf(curated, p.Name))
                        .Select(p =>
                        (
                            Name: p.Name,
                            Label: p.Label,
                            Type: p.Type,
                            Description: p.Description,
                            Options: p.Options?.ToList(),
                            Default: p.Default
                        )).ToList();
                    runVm.SetParameters(specs);
                }
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not load Bond Yield Forecast parameters: {ex.Message}");
            }

            // Workbook-input technique: no cell selection. Enable Run without a
            // selection and route the Run button to OnWorkbookRunRequested.
            runVm.SetSeriesPreviews(new List<SeriesPreviewItem>());
            runVm.RequiresSelection = false;
            runVm.WorkbookInputMode = true;
            runVm.IsRunning = false;
            SetBespokeInputAtOpen(runVm);
        }

        /// <summary>
        /// Open the Run view for Breakeven Payrolls in CONFIGURE-then-run mode.
        /// Workbook-input technique (mirrors OpenBondYieldForecastConfig): no cell
        /// selection, Run enabled without a selection, the Run button routed to the
        /// shared OnWorkbookRunRequested. The scenario (net migration) and all data
        /// live IN the workbook (the scenario_inputs tab + the baked CBO/population
        /// tabs), so there are NO curated pane params — the user edits the workbook,
        /// then clicks Run.
        /// </summary>
        public static void OpenBreakevenPayrollConfig()
        {
            if (!EnsureTaskPane("Breakeven Payrolls")) return;
            _taskPane.Visible = true;

            const string techniqueId = "breakeven_payroll";
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            try
            {
                var techEntry = TechniqueCatalogService.GetTechnique(techniqueId);
                if (techEntry != null && !string.IsNullOrEmpty(techEntry.Name))
                    runVm.TechniqueName = techEntry.Name;
                runVm.TechniqueSummary = techEntry?.Summary ?? "";
                runVm.TechniqueId = techniqueId;
                // No curated pane params: the scenario is set in the workbook's
                // scenario_inputs tab, not the pane. input_workbook is auto-resolved
                // at Run-click. Surface an empty parameter list so the view renders
                // the Run affordance without knobs.
                runVm.SetParameters(new List<(string Name, string Label, string Type,
                    string Description, List<string> Options, object Default)>());
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not load Breakeven Payrolls parameters: {ex.Message}");
            }

            runVm.SetSeriesPreviews(new List<SeriesPreviewItem>());
            runVm.RequiresSelection = false;
            runVm.WorkbookInputMode = true;
            runVm.IsRunning = false;
            SetBespokeInputAtOpen(runVm);
        }

        /// <summary>
        /// Open the Run view for Kronos Forecast (Bespoke #3; EXPERIMENTAL) in
        /// CONFIGURE-then-run mode — the Breakeven shape exactly: no cell
        /// selection, no pane params (every knob lives in the workbook's
        /// kronos_input sheet), the Run button routed to the shared
        /// OnWorkbookRunRequested.
        /// </summary>
        public static void OpenKronosConfig()
        {
            if (!EnsureTaskPane("Kronos Forecast")) return;
            _taskPane.Visible = true;

            const string techniqueId = "kronos_forecast";
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            try
            {
                var techEntry = TechniqueCatalogService.GetTechnique(techniqueId);
                if (techEntry != null && !string.IsNullOrEmpty(techEntry.Name))
                    runVm.TechniqueName = techEntry.Name;
                runVm.TechniqueSummary = techEntry?.Summary ?? "";
                runVm.TechniqueId = techniqueId;
                // No curated pane params: L/H/M/seed live in the workbook's
                // kronos_input parameter cells. input_workbook is auto-resolved
                // at Run-click. An empty list renders the Run affordance only.
                runVm.SetParameters(new List<(string Name, string Label, string Type,
                    string Description, List<string> Options, object Default)>());
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not load Kronos Forecast parameters: {ex.Message}");
            }

            runVm.SetSeriesPreviews(new List<SeriesPreviewItem>());
            runVm.RequiresSelection = false;
            runVm.WorkbookInputMode = true;
            runVm.IsRunning = false;
            SetBespokeInputAtOpen(runVm);
        }

        /// <summary>
        /// Handles the Run button for a WORKBOOK-INPUT technique. Takes the
        /// workbook the Run view was set up for (A2 U6, B7: ResolveBespokeInput),
        /// writes a clean local %TEMP% copy (off OneDrive,
        /// captures unsaved edits — the d923c6a mechanism), merges the user's
        /// edited parameters, and dispatches via RunTechniqueWithParams.
        /// </summary>
        // Registry of workbook-input technique ids — Bespoke techniques that
        // consume a whole .xlsx workbook (via params["input_workbook"]) instead
        // of a cell selection. The Run button routes through the shared
        // OnWorkbookRunRequested for every id in this set; adding a new
        // workbook-input member is one line here. (A catalog input_mode property
        // is the cleaner long-term home; banked for a 3rd member.)
        private static readonly HashSet<string> _workbookInputTechniques =
            new HashSet<string>(StringComparer.OrdinalIgnoreCase)
            {
                "bond_yield_forecast",
                "breakeven_payroll",
                "kronos_forecast",
            };

        private static void OnWorkbookRunRequested(string techniqueId)
        {
            // Route only the registered workbook-input techniques. BVAR's path is
            // unchanged below (the only behavioral specialization is the
            // scenario="baseline" default, gated on its id).
            if (!_workbookInputTechniques.Contains(techniqueId))
                return;

            BespokeLabels.TryGetValue(techniqueId, out var tool);
            try
            {
                var runVm = _hostControl?.ViewModel?.CurrentView as RunViewModel;

                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                // The workbook this Run view was set up for (A2 U6, B7), not the active one:
                // after a run the active workbook is the results workbook (N9).
                var wb = ResolveBespokeInput(app, runVm, out var closedInput, out var resultsInput);
                if (wb == null && closedInput != null)
                {
                    // A workbook that was never saved (no folder in its name) cannot be opened again.
                    bool neverSaved = closedInput.IndexOfAny(new[] { '\\', '/' }) < 0;
                    HouseDialog.ShowHouseAlert(
                        $"The {tool} input workbook that the task pane was set up for is no longer open, " +
                        "so nothing was run." +
                        (neverSaved ? " It had never been saved, so it cannot be opened again." : "") + "\n\n" +
                        "The workbook:\n" + HouseDialog.Indent(closedInput) + "\n\n" +
                        (neverSaved ? "" : "Open it again, then click Run in the task pane. ") +
                        "To use another workbook, make it the active workbook, then click " +
                        $"Bespoke > {tool} > Run {tool}.",
                        HouseDialog.Title(tool));
                    return;
                }
                if (wb == null && resultsInput != null)
                {
                    HouseDialog.ShowHouseAlert(
                        "The active workbook holds the results of an earlier run, so nothing was run.\n\n" +
                        "The workbook:\n" + HouseDialog.Indent(resultsInput) + "\n\n" +
                        $"Make the {tool} input workbook the active workbook, then click Run again.",
                        HouseDialog.Title(tool));
                    return;
                }
                if (wb == null)
                {
                    HouseDialog.ShowHouseAlert(
                        "No workbook is open, so nothing was run.\n\n" +
                        $"Open the {tool} input workbook, or use Bespoke > {tool} > Open Input Template, " +
                        "then click Run in the task pane.",
                        HouseDialog.Title(tool));
                    return;
                }

                // Capture the input workbook's identity for the results (the results land
                // next to THIS workbook with a name derived from it).
                string srcName = null, srcDir = null;
                try { srcName = wb.Name; } catch { /* best-effort */ }
                try { srcDir = wb.Path; } catch { /* best-effort */ }

                var tempPath = System.IO.Path.Combine(
                    System.IO.Path.GetTempPath(), $"tsl_wbk_{Guid.NewGuid():N}.xlsx");
                wb.SaveCopyAs(tempPath);

                var injected = runVm?.GetParametersDict()
                               ?? new Dictionary<string, object>();
                injected["input_workbook"] = tempPath;
                // Bond Yield Forecast carries a scenario name (BondYield_Projections
                // column); default it to "baseline". Breakeven Payrolls reads its
                // scenario from the workbook's scenario_inputs tab — no injection.
                if (string.Equals(techniqueId, "bond_yield_forecast", StringComparison.OrdinalIgnoreCase)
                    && !injected.ContainsKey("scenario"))
                    injected["scenario"] = "baseline";

                RunTechniqueWithParams(techniqueId, injected, tempPath, srcName, srcDir);
            }
            catch (Exception ex)
            {
                Logger.Error($"Starting the {tool} run failed.", ex);
                HouseDialog.ShowHouseAlert(
                    $"Time Series Lab could not start the {tool} run, so nothing was run. " +
                    "The input workbook was not changed.\n\n" +
                    HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                    "Try again. If this message returns, tell Matthew Hornbach.",
                    HouseDialog.Title(tool), isError: true);
            }
        }

        /// <summary>
        /// Handles the Run view's Cancel button: cancels the in-flight run token
        /// AND hard-kills the engine process (so a mid-MCMC run actually stops;
        /// the engine relaunches on the next run via EnsureRunning), then returns
        /// the view to a ready state.
        /// </summary>
        private static void OnCancelRequested()
        {
            try
            {
                _activeRunCts?.Cancel();
                AddIn.Engine?.CancelCurrentRun();

                // The Run view even when another view is showing (the run lives there).
                var runVm = _hostControl?.ViewModel?.RunViewIfCreated;
                if (runVm != null)
                {
                    _hostControl?.Invoke((System.Action)(() =>
                    {
                        runVm.ReportProgress("Canceled", runVm.ProgressPercent, "The run was canceled. Nothing was written.");
                        runVm.IsRunning = false;
                    }));
                }
                Logger.Info("Run canceled by user (engine hard-stopped).");
            }
            catch (Exception ex)
            {
                Logger.Error("Error during run cancel.", ex);
            }
        }

        public static void ShowExplorer()
        {
            if (!EnsureTaskPane(ExplorerArea)) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToExplorer();
        }

        public static void ShowRecommender()
        {
            if (!EnsureTaskPane("Recommender")) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToRecommender();
        }

        public static void ShowRecommenderWithGoal(string goal)
        {
            if (!EnsureTaskPane("Recommender")) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToRecommenderWithGoal(goal);
        }

        public static void ShowExplorerWithCategory(string category)
        {
            if (!EnsureTaskPane(ExplorerArea)) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToExplorerWithCategory(category);
        }

        public static void ShowDataReadiness()
        {
            if (!EnsureTaskPane("Data Readiness")) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToDataReadiness();
        }

        public static void ShowSettings()
        {
            if (!EnsureTaskPane("Settings")) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToSettings();
        }

        public static void ShowUdfBrowser()
        {
            if (!EnsureTaskPane("UDF Formula Guide")) return;
            _taskPane.Visible = true;
            _hostControl?.NavigateToUdfBrowser();
        }

        /// <summary>
        /// The ribbon's Run (A2 U6, Part 4(v), K2): exactly what the task pane's Run button
        /// does, and nothing else. When the pane is not showing a Run view that can run,
        /// nothing runs: the pane is shown, with a house message saying why.
        /// </summary>
        public static void RunCurrent()
        {
            var runVm = _hostControl?.ViewModel?.RunViewIfCreated;
            if (System.Threading.Volatile.Read(ref _paneRunsInFlight) > 0 || (runVm?.IsRunning ?? false))
            {
                HouseDialog.ShowHouseAlert(
                    "A run is already in progress in the task pane, so nothing new was started.\n\n" +
                    "Wait for it to finish, or click Run > Cancel to stop it.",
                    HouseDialog.Title(RunArea));
                return;
            }

            // Where the pane is. Excel gives each workbook its own window, and the task pane
            // belongs to the window it was created in: Visible stays true while the user
            // works in another window, where the pane is not on screen.
            var where = LocatePane();
            if (where.Alive && !where.InActiveWindow)
            {
                Logger.Info($"Ribbon Run: the task pane is in another window ({where.WindowCaption}); nothing was run.");
                HouseDialog.ShowHouseAlert(
                    "The task pane is in another workbook window, so nothing was run.\n\n" +
                    "Its window:\n" + HouseDialog.Indent(where.WindowCaption ?? "(unknown)") + "\n\n" +
                    "Switch to that window, check the task pane, then click Run.",
                    HouseDialog.Title(RunArea));
                return;
            }

            var outcome = RunCurrentOutcome.NothingSetUp;
            if (where.Alive && where.Visible && _hostControl != null)
                outcome = _hostControl.RunCurrentTechnique();
            if (outcome == RunCurrentOutcome.Started) return;

            bool wasClosed = where.Alive && !where.Visible;
            if (!EnsureTaskPane(RunArea)) return;
            _taskPane.Visible = true;
            runVm = _hostControl?.ViewModel?.RunViewIfCreated;
            if (outcome == RunCurrentOutcome.AlreadyRunning)
            {
                HouseDialog.ShowHouseAlert(
                    "A run is already in progress in the task pane, so nothing new was started.\n\n" +
                    "Wait for it to finish, or click Run > Cancel to stop it.",
                    HouseDialog.Title(RunArea));
            }
            else if (wasClosed && runVm != null && ReferenceEquals(_hostControl.ViewModel.CurrentView, runVm) &&
                     runVm.CanRun && !string.IsNullOrEmpty(runVm.TechniqueId))
            {
                // A Run view set up and ready, but the pane had been closed: say that, not
                // "nothing is set up".
                HouseDialog.ShowHouseAlert(
                    "The task pane was closed, so nothing was run.\n\n" +
                    "It is open again and shows " + HouseDialog.Ascii(runVm.TechniqueDisplayName) + ". " +
                    "Check it, then click Run.",
                    HouseDialog.Title(RunArea));
            }
            else
            {
                HouseDialog.ShowHouseAlert(
                    "Nothing is set up to run.\n\n" +
                    "Choose a technique on the Time Series Lab tab or in Explore > Technique Explorer, " +
                    "check it in the task pane, then click Run.",
                    HouseDialog.Title(RunArea));
            }
        }

        /// <summary>
        /// Whether the task pane exists and answers (Alive), is shown (Visible), and belongs
        /// to the active workbook window. When the window cannot be read, the pane counts as
        /// in the active window (the behaviour before this check).
        /// </summary>
        private static (bool Alive, bool Visible, bool InActiveWindow, string WindowCaption) LocatePane()
        {
            if (_taskPane == null) return (false, false, false, null);
            bool visible;
            try { visible = _taskPane.Visible; }
            catch { return (false, false, false, null); }
            try
            {
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                var paneWindow = _taskPane.Window as Window;
                var active = app?.ActiveWindow;
                if (paneWindow == null || active == null) return (true, visible, true, null);
                return (true, visible, paneWindow.Hwnd == active.Hwnd, Convert.ToString((object)paneWindow.Caption));
            }
            catch
            {
                return (true, visible, true, null);
            }
        }

        /// <summary>
        /// The ribbon's Cancel (A2 U6, N2): the task pane's own cancel path, so the Run view
        /// resets. With no task pane run in progress, worksheet-function runs in flight are
        /// stopped as before (they share the engine); with nothing running at all, a house
        /// message says so.
        /// </summary>
        internal static void CancelFromRibbon()
        {
            var runVm = _hostControl?.ViewModel?.RunViewIfCreated;
            if (System.Threading.Volatile.Read(ref _paneRunsInFlight) > 0 || (runVm?.IsRunning ?? false))
            {
                OnCancelRequested();
                return;
            }
            if (AddIn.Engine != null && AddIn.Engine.HasRunsInFlight)
            {
                AddIn.Engine.CancelCurrentRun();
                Logger.Info("Ribbon Cancel: worksheet-function runs stopped (engine hard-stopped).");
                return;
            }
            Logger.Info("Ribbon Cancel: nothing was running.");
            HouseDialog.ShowHouseAlert("Nothing is running.", HouseDialog.Title("Cancel"));
        }

        /// <summary>The active workbook, or null when none is open or Excel cannot say.</summary>
        private static Workbook ActiveWorkbookOrNull()
        {
            try { return ((Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application)?.ActiveWorkbook; }
            catch { return null; }
        }

        /// <summary>
        /// Record the workbook a Bespoke tool's Run view is set up for (A2 U6, B7) and show
        /// it in the view. <paramref name="wb"/> may be null (no workbook was active).
        /// </summary>
        private static void SetBespokeInput(RunViewModel runVm, Workbook wb)
        {
            string fullName = null, name = null;
            if (wb != null)
            {
                try { fullName = wb.FullName; name = wb.Name; }
                catch { wb = null; fullName = null; name = null; }
            }
            _bespokeInputWorkbook = wb;
            _bespokeInputFullName = fullName;
            _bespokeInputTechniqueId = runVm?.TechniqueId;
            if (runVm != null) runVm.InputWorkbookName = name;
            Logger.Info($"Bespoke Run view set up for workbook: {fullName ?? "(none)"}.");
        }

        /// <summary>
        /// A Bespoke opener sets its Run view up for the active workbook (A2 U6, B7) - unless
        /// that is the results workbook of an earlier run (N9). Then the input already
        /// recorded for this tool is kept while it is open; otherwise none is recorded, and
        /// Run takes the active workbook at the first click (refusing a results workbook there).
        /// </summary>
        private static void SetBespokeInputAtOpen(RunViewModel runVm)
        {
            var active = ActiveWorkbookOrNull();
            if (active != null && IsResultsWorkbook(active))
            {
                bool keep = _bespokeInputWorkbook != null &&
                            string.Equals(_bespokeInputTechniqueId, runVm?.TechniqueId, StringComparison.OrdinalIgnoreCase) &&
                            IsOpen(_bespokeInputWorkbook);
                Logger.Info("Bespoke Run view opened from a results workbook; " +
                            (keep ? "the input recorded for this tool is kept." : "no input is recorded yet."));
                SetBespokeInput(runVm, keep ? _bespokeInputWorkbook : null);
                return;
            }
            SetBespokeInput(runVm, active);
        }

        /// <summary>A results workbook this Excel session created (never a Bespoke input).</summary>
        private static bool IsResultsWorkbook(Workbook wb)
        {
            try { return wb != null && _resultsWorkbooks.Contains(wb.FullName); }
            catch { return false; }
        }

        private static void RememberResultsWorkbook(ExcelWriter.WriteResult writeResult)
        {
            if (writeResult != null && writeResult.Success && !string.IsNullOrEmpty(writeResult.WorkbookFullName))
                _resultsWorkbooks.Add(writeResult.WorkbookFullName);
        }

        /// <summary>Whether <paramref name="wb"/> is still one of Excel's open workbooks.</summary>
        private static bool IsOpen(Workbook wb)
        {
            try
            {
                var fullName = wb.FullName;
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                foreach (Workbook w in app.Workbooks)
                {
                    try { if (string.Equals(w.FullName, fullName, StringComparison.OrdinalIgnoreCase)) return true; }
                    catch { /* skip */ }
                }
                return false;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// The workbook a Bespoke run reads (A2 U6, B7): the one its Run view was set up
        /// for, found by its current full name (so a Save As keeps it) or, if Excel closed
        /// and reopened it, by the name it was recorded under. With none recorded, the active
        /// workbook, which is then recorded - unless it is the results workbook of an earlier
        /// run (<paramref name="resultsWorkbook"/> names it; the result is null). Null with
        /// <paramref name="closedName"/> set when the recorded workbook is no longer open;
        /// null alone when no workbook is open.
        /// </summary>
        private static Workbook ResolveBespokeInput(Microsoft.Office.Interop.Excel.Application app,
            RunViewModel runVm, out string closedName, out string resultsWorkbook)
        {
            closedName = null;
            resultsWorkbook = null;
            if (_bespokeInputWorkbook == null && _bespokeInputFullName == null)
            {
                var active = app?.ActiveWorkbook;
                if (active != null && IsResultsWorkbook(active))
                {
                    try { resultsWorkbook = active.Name; } catch { resultsWorkbook = "(unknown)"; }
                    return null;
                }
                if (active != null) SetBespokeInput(runVm, active);
                return active;
            }

            string current = null;
            try { if (_bespokeInputWorkbook != null) current = _bespokeInputWorkbook.FullName; }
            catch { /* closed: look it up by the name it was recorded under */ }

            foreach (Workbook w in app.Workbooks)
            {
                string fullName = null;
                try { fullName = w.FullName; } catch { /* skip */ }
                if (fullName != null &&
                    (string.Equals(fullName, current, StringComparison.OrdinalIgnoreCase) ||
                     string.Equals(fullName, _bespokeInputFullName, StringComparison.OrdinalIgnoreCase)))
                {
                    if (!ReferenceEquals(w, _bespokeInputWorkbook) || fullName != _bespokeInputFullName)
                        SetBespokeInput(runVm, w);
                    return w;
                }
            }
            closedName = current ?? _bespokeInputFullName;
            return null;
        }

        public static void UpdatePreset(string preset)
        {
            _hostControl?.SetPreset(preset);
        }

        /// <summary>
        /// Make sure the task pane exists; false (after a house error naming
        /// <paramref name="area"/>, the action that needed it) when it cannot be created,
        /// so the caller stops instead of using a pane that does not exist.
        /// </summary>
        private static bool EnsureTaskPane(string area)
        {
            // A cached CustomTaskPane reference can become a DEAD COM object: Excel
            // tears the pane down when its host window is destroyed (the separate-
            // file results workbook opening, the working-copy Open, the input window
            // closing during a run). Reusing it throws "The taskpane has been deleted
            // or is otherwise no longer valid" at the next `.Visible` access. So
            // validate the handle; if it's dead, fully tear down (UNWIRE events +
            // dispose) BEFORE recreating, so the rebuilt pane wires its events exactly
            // once — no leaked / double subscriptions. The valid-pane path is unchanged
            // (one cheap property read, then return); the only new behavior is that a
            // stale pane is recreated instead of throwing. Every technique launch
            // (Bespoke, selection, Explorer/Recommender) goes through here.
            if (_taskPane != null)
            {
                bool alive;
                try { var _ = _taskPane.Visible; alive = true; }
                catch { alive = false; }
                if (alive) return true;

                Logger.Info("Task pane handle is stale (host window destroyed); recreating.");
                try { _taskPane.VisibleStateChange -= OnVisibleStateChange; } catch { /* dead */ }
                if (_hostControl?.ViewModel != null)
                {
                    try
                    {
                        _hostControl.ViewModel.RunRequested -= OnRunRequested;
                        _hostControl.ViewModel.ConfigureRunRequested -= OnConfigureRunRequested;
                        _hostControl.ViewModel.WorkbookRunRequested -= OnWorkbookRunRequested;
                        _hostControl.ViewModel.RunCancelRequested -= OnCancelRequested;
                        _hostControl.ViewModel.DataReadinessChecksRequested -= OnDataReadinessChecksRequested;
                    }
                    catch { /* best-effort unwire */ }
                }
                try { _taskPane.Delete(); } catch { /* already gone */ }
                try { _hostControl?.Dispose(); } catch { /* already disposed */ }
                _taskPane = null;
                _hostControl = null;
            }

            try
            {
                _hostControl = new TSL.UI.TaskPaneHostControl();

                // Wire the RunRequested event to extract selection and run the engine
                _hostControl.ViewModel.RunRequested += OnRunRequested;

                // The Explorer's "Configure & Run" -> open the pane populated and
                // WAIT (RunTechnique = LaunchTechnique execute:false). Distinct
                // from RunRequested so the Explorer action no longer auto-runs
                // (Fix A2); execution stays the panel "Run" click's job.
                _hostControl.ViewModel.ConfigureRunRequested += OnConfigureRunRequested;

                // Workbook-input dispatch (Bond Yield Forecast Run button) and the
                // Run view's Cancel button.
                _hostControl.ViewModel.WorkbookRunRequested += OnWorkbookRunRequested;
                _hostControl.ViewModel.RunCancelRequested += OnCancelRequested;

                // Wire the Data Readiness checks request
                _hostControl.ViewModel.DataReadinessChecksRequested += OnDataReadinessChecksRequested;

                // Push the real technique catalog into the Explorer VM. The VM now
                // constructs EMPTY (the design-time preview stub was removed -- the
                // JSON catalog is the single source of truth); this push happens
                // BEFORE CreateCustomTaskPane below, so the pane is never shown
                // before the catalog is loaded.
                try
                {
                    var catalog = TechniqueCatalogService.GetCatalog();
                    // Kronos Forecast is listed only where its environment exists, by the
                    // ribbon's own test (A2 U6, K3).
                    bool kronos = KronosEnvironment.IsAvailable();
                    var items = catalog?.Techniques?
                        .Where(t => kronos || !string.Equals(t.Id, KronosEnvironment.TechniqueId, StringComparison.OrdinalIgnoreCase))
                        .Select(ConvertCatalogEntry).ToList();
                    if (items != null && items.Count > 0)
                    {
                        _hostControl.LoadTechniqueCatalog(items);
                        Logger.Info($"Pushed {items.Count} techniques into Explorer VM.");
                    }
                    else
                    {
                        Logger.Warn("Technique catalog is empty; the Explorer will be empty (no built-in stub fallback).");
                    }
                }
                catch (Exception catEx)
                {
                    Logger.Error("Failed to push technique catalog to Explorer VM.", catEx);
                }

                _taskPane = CustomTaskPaneFactory.CreateCustomTaskPane(
                    _hostControl, "Time Series Lab");

                _taskPane.DockPosition = MsoCTPDockPosition.msoCTPDockPositionRight;
                // Wider default gives result tables, progress log, and technique
                // descriptions room to breathe. Users can still drag the edge to resize.
                _taskPane.Width = 720;
                _taskPane.VisibleStateChange += OnVisibleStateChange;
                return true;
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to create task pane.", ex);
                // The pane was created and only its docking, width or visibility logging
                // failed: carry on if it answers (logged above).
                if (_taskPane != null)
                {
                    try { var _ = _taskPane.Visible; return true; }
                    catch { /* not usable: tear it down and report below */ }
                }

                try { _taskPane.VisibleStateChange -= OnVisibleStateChange; } catch { /* absent or dead */ }
                if (_hostControl?.ViewModel != null)
                {
                    try
                    {
                        _hostControl.ViewModel.RunRequested -= OnRunRequested;
                        _hostControl.ViewModel.ConfigureRunRequested -= OnConfigureRunRequested;
                        _hostControl.ViewModel.WorkbookRunRequested -= OnWorkbookRunRequested;
                        _hostControl.ViewModel.RunCancelRequested -= OnCancelRequested;
                        _hostControl.ViewModel.DataReadinessChecksRequested -= OnDataReadinessChecksRequested;
                    }
                    catch { /* best-effort unwire */ }
                }
                try { _taskPane?.Delete(); } catch { /* already gone */ }
                try { _hostControl?.Dispose(); } catch { /* best-effort */ }
                _taskPane = null;
                _hostControl = null;
                HouseDialog.ShowHouseAlert(
                    "Time Series Lab could not open its task pane. Nothing was changed.\n\n" +
                    HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                    "Close Excel and start it again. If this message returns, tell Matthew Hornbach.",
                    HouseDialog.Title(area), isError: true);
                return false;
            }
        }

        /// <summary>
        /// The RunRequested event handler (the user clicked Run in the pane).
        /// Always executes — delegates to <see cref="LaunchTechnique"/> with
        /// execute:true.
        /// </summary>
        private static void OnRunRequested(string techniqueId, string preset)
            => LaunchTechnique(techniqueId, preset, execute: true, area: RunArea, retry: "click Run again");

        /// <summary>
        /// The Explorer's "Configure &amp; Run" handler (Fix A2). Opens the Run
        /// pane POPULATED (selection + previews + params) and WAITS — does NOT
        /// execute. The same populate-then-stop path the ribbon uses
        /// (LaunchTechnique execute:false); execution happens only on the pane's
        /// own "Run" click (OnRunRequested).
        /// </summary>
        private static void OnConfigureRunRequested(string techniqueId)
        {
            // A Bespoke tool listed in the Explorer opens exactly as its ribbon Run item
            // does (A2 U6, N3): its own workbook-input Run view, never the selection path.
            if (_workbookInputTechniques.Contains(techniqueId ?? ""))
            {
                BespokeLabels.TryGetValue(techniqueId, out var tool);
                try
                {
                    switch (techniqueId.ToLowerInvariant())
                    {
                        case "bond_yield_forecast": OpenBondYieldForecastConfig(); break;
                        case "breakeven_payroll": OpenBreakevenPayrollConfig(); break;
                        case "kronos_forecast": OpenKronosConfig(); break;
                    }
                }
                catch (Exception ex)
                {
                    Ribbon.ReportOpenFailure(tool, ex);
                }
                return;
            }
            OpenPopulated(techniqueId, ExplorerArea, "click Configure & Run again");
        }

        /// <summary>
        /// Extracts data from the current Excel selection (including non-adjacent
        /// ranges), detects a time index, validates series lengths, populates the
        /// Run view, and — only when <paramref name="execute"/> is true —
        /// dispatches to the engine. The ribbon launch (RunTechnique) calls this
        /// with execute:false to open the pane populated + wait for the user's
        /// Run click; the Run click (OnRunRequested) calls it with execute:true.
        /// A selection refusal is a house message from <paramref name="area"/> (the
        /// launching button's label, or "Run" at a Run click) that ends with
        /// <paramref name="retry"/>.
        /// </summary>
        private static void LaunchTechnique(string techniqueId, string preset, bool execute,
            string area, string retry)
        {
            if (string.IsNullOrEmpty(techniqueId)) return;

            // Extract series from current selection (handles non-adjacent via selection.Areas)
            var selectionResult = _selectionService.ExtractFromSelection();
            if (!selectionResult.Success || selectionResult.Series.Count == 0)
            {
                var what = selectionResult.ErrorMessage ?? "No data is selected.";
                if (selectionResult.ReadFailed)
                {
                    HouseDialog.ShowHouseAlert(
                        what + " Nothing was run.\n\n" +
                        HouseDialog.ErrorBlock(selectionResult.ErrorDetail) + "\n\n" +
                        $"Select the data again, then {retry}. If this message returns, tell Matthew Hornbach.",
                        HouseDialog.Title(area), isError: true);
                }
                else
                {
                    HouseDialog.ShowHouseAlert(
                        what + " Nothing was run.\n\n" +
                        $"Select one or more columns of numbers, then {retry}.",
                        HouseDialog.Title(area));
                }
                return;
            }

            // Validate all series have the same length
            var lengths = selectionResult.Series.Select(s => s.Length).Distinct().ToList();
            if (lengths.Count > 1)
            {
                HouseDialog.ShowHouseAlert(
                    "The selected columns have different lengths. Nothing was run.\n\n" +
                    "Lengths:\n" + HouseDialog.Indent(string.Join(", ", lengths)) + "\n\n" +
                    $"Select columns with the same number of rows, then {retry}.",
                    HouseDialog.Title(area));
                return;
            }

            // Selection guard (A2 U6, N5; ratification Q6): a Run click runs only the
            // selection the Run view shows. A different one is shown instead, and nothing runs.
            var shown = CurrentSelectionIdentity(selectionResult);
            bool selectionChanged = execute && !IsPreviewedSelection(shown);
            if (selectionChanged)
                Logger.Info($"Run refused: the selection changed after the Run view was filled " +
                            $"(was {DescribeSelection(_previewedWorkbook, _previewedSheet, _previewedAddresses)}, " +
                            $"now {DescribeSelection(shown.Wb, shown.Ws, shown.Addresses)}).");

            // Detect time index using TimeIndexDetector. If a time column is
            // found inside the user's selection, also remove it from the list
            // of numeric series (so PCA / VAR / etc. don't try to treat dates
            // as just another variable).
            string[] timeArray = null;
            string timeColumnLetter = null;
            string timeColumnAddress = null;
            string detectedFrequency = null;
            try
            {
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                var selection = app.Selection as Range;
                if (selection?.Areas.Count > 0)
                {
                    var firstArea = selection.Areas[1];
                    var detection = _timeDetector.Detect(firstArea, firstArea.Row, firstArea.Rows.Count);

                    // Always log what the detector saw — this is the only way
                    // to debug "why didn't dates show up?" complaints from
                    // the field. Includes every candidate it considered, not
                    // just the winner, so we can see scoring near-misses.
                    var candidatesLog = string.Join("; ",
                        detection.AllCandidates.Select(c =>
                            $"{c.ColumnLetter}(\"{c.HeaderName}\") score={c.OverallScore:F2} " +
                            $"parse={c.ParseableRatio:F2} mono={c.MonotonicRatio:F2} " +
                            $"uniq={c.UniquenessRatio:F2} reg={c.RegularityScore:F2}"));
                    Logger.Info(
                        $"TimeIndexDetector: best={detection.BestCandidate?.ColumnLetter ?? "none"} " +
                        $"score={detection.BestCandidate?.OverallScore.ToString("F2") ?? "n/a"} " +
                        $"freq={detection.BestCandidate?.SuggestedFrequency ?? "n/a"} | " +
                        $"candidates: {candidatesLog}");

                    if (detection.BestCandidate != null && detection.ParsedDates != null)
                    {
                        timeArray = detection.ParsedDates;
                        timeColumnLetter = detection.BestCandidate.ColumnLetter;
                        detectedFrequency = detection.BestCandidate.SuggestedFrequency;
                        timeColumnAddress =
                            $"{timeColumnLetter}{firstArea.Row}:" +
                            $"{timeColumnLetter}{firstArea.Row + firstArea.Rows.Count - 1}";
                    }
                }
            }
            catch (Exception ex)
            {
                Logger.Info($"Time index detection skipped: {ex.Message}");
            }

            // If the detected time column is one of the selected series, drop it.
            // We match on the Address prefix (e.g. "A1:A11901" starts with "A").
            // We only drop if at least two numeric series would remain, so we
            // don't silently destroy a single-series selection.
            if (!string.IsNullOrEmpty(timeColumnLetter))
            {
                var before = selectionResult.Series.Count;
                var filtered = selectionResult.Series
                    .Where(s => !SeriesAddressStartsWithColumn(s.Address, timeColumnLetter))
                    .ToList();
                if (filtered.Count >= 1 && filtered.Count < before)
                {
                    Logger.Info(
                        $"Excluded time column {timeColumnLetter} from series " +
                        $"({before} -> {filtered.Count} numeric series).");
                    selectionResult.Series = filtered;
                }
            }

            // Capture the technique the Run view is CURRENTLY bound to BEFORE
            // NavigateToRun overwrites it -- the gate below compares against
            // this (NavigateToRun sets TechniqueId = techniqueId up front, so
            // comparing the post-navigation id was always equal -> the dead
            // gate that left every selection technique with zero param controls).
            var priorTechniqueId = _hostControl.ViewModel.CurrentRunTechniqueId;

            // Navigate to Run view and populate series previews
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            // A selection technique: the Run view leaves workbook-input mode, which a Bespoke
            // tool may have set (A2 U6, N1), and forgets the Bespoke input workbook.
            runVm.RequiresSelection = true;
            runVm.WorkbookInputMode = false;
            runVm.InputWorkbookName = null;
            _bespokeInputWorkbook = null;
            _bespokeInputFullName = null;

            // Populate the real display name from the catalog (avoids "pca analysis"
            // fallback rendering of the raw ID). Also populate the
            // technique-specific parameter list so the Run pane renders
            // controls (checkboxes / dropdowns / text inputs) for each param
            // declared in the catalog. Only re-populate when the technique
            // changed — otherwise we'd clobber user edits between runs.
            try
            {
                var techEntry = TechniqueCatalogService.GetTechnique(techniqueId);
                if (techEntry != null && !string.IsNullOrEmpty(techEntry.Name))
                    runVm.TechniqueName = techEntry.Name;
                runVm.TechniqueSummary = techEntry?.Summary ?? "";

                // Compare against the PRE-navigation id (NavigateToRun already
                // set runVm.TechniqueId = techniqueId). The empty-Parameters
                // belt repopulates a first-ever load even if the prior id
                // somehow matched. Edit-preservation holds: a same-technique
                // re-run has priorTechniqueId == techniqueId AND a non-empty
                // Parameters collection, so it does NOT clobber the user's
                // edits; a technique switch repopulates at defaults.
                bool techniqueChanged =
                    !string.Equals(priorTechniqueId, techniqueId, StringComparison.OrdinalIgnoreCase)
                    || runVm.Parameters.Count == 0;
                runVm.TechniqueId = techniqueId;

                if (techniqueChanged && techEntry?.Parameters != null)
                {
                    var specs = techEntry.Parameters.Select(p =>
                        (
                            Name: p.Name,
                            Label: p.Label,
                            Type: p.Type,
                            Description: p.Description,
                            Options: p.Options?.ToList(),
                            Default: p.Default
                        )).ToList();
                    runVm.SetParameters(specs);
                }
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not resolve technique metadata for {techniqueId}: {ex.Message}");
            }

            runVm.SetSeriesPreviews(selectionResult.Series.Select(s => new SeriesPreviewItem
            {
                Name = s.Name,
                Address = s.Address,
                Length = s.Length,
                MissingPct = s.MissingPct,
            }));

            // Surface the auto-detected time index in the Run view so the
            // user can actually SEE that detection happened (without having
            // to dig through the log file). The CheckBox auto-ticks, the
            // address textbox shows the column range, and the "Detected:"
            // label shows the inferred frequency.
            if (timeArray != null && !string.IsNullOrEmpty(timeColumnAddress))
            {
                runVm.TimeIndexAddress = timeColumnAddress;
                runVm.UseTimeIndex = true;
                if (!string.IsNullOrEmpty(detectedFrequency))
                    runVm.DetectedFrequency = detectedFrequency;
            }
            else
            {
                runVm.UseTimeIndex = false;
                runVm.TimeIndexAddress = "";
                runVm.DetectedFrequency = "Not detected";
            }

            _previewedWorkbook = shown.Wb;
            _previewedSheet = shown.Ws;
            _previewedAddresses = shown.Addresses;

            // ── No-auto-run gate ──────────────────────────────────────────
            // The pane is now fully populated (selection extracted, series
            // previews, params, detected time index). On a ribbon LAUNCH
            // (execute:false) we STOP here — the user reviews and clicks Run.
            // Only the Run click (execute:true) proceeds to dispatch, and only
            // on the selection the pane showed (the guard above).
            if (!execute || selectionChanged)
            {
                runVm.IsRunning = false;
                if (selectionChanged)
                {
                    HouseDialog.ShowHouseAlert(
                        "The selection changed after the task pane was filled, so nothing was run.\n\n" +
                        "The task pane now shows the new selection. Check it, then click Run.",
                        HouseDialog.Title(area));
                }
                return;
            }

            runVm.IsRunning = true;

            // Build the RunRequest. Pull per-technique parameter values from
            // the Run pane so the engine sees the user's current settings
            // (e.g. covid_outliers checkbox, fit_window_obs text box) instead
            // of running with nothing but defaults.
            var paramsDict = runVm.GetParametersDict() ?? new Dictionary<string, object>();

            // Capture the input workbook's identity NOW. The selection was just
            // extracted from the active workbook (above), so the active workbook
            // here IS the input — anchor the results filename/folder to it so
            // results never derive their name from a prior run's results file.
            string srcWbName = null, srcWbDir = null;
            try
            {
                var srcApp = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                var srcWb = srcApp?.ActiveWorkbook;
                if (srcWb != null) { srcWbName = srcWb.Name; srcWbDir = srcWb.Path; }
            }
            catch (Exception wbEx)
            {
                Logger.Info($"Could not capture source workbook identity: {wbEx.Message}");
            }

            var request = new RunRequest
            {
                RunId = $"pane_{Guid.NewGuid():N}",
                TechniqueId = techniqueId,
                Preset = preset ?? "Balanced",
                Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                Time = timeArray,
                SourceWorkbookName = srcWbName,
                SourceWorkbookPath = srcWbDir,
                // Pass detected frequency to the engine so techniques that
                // consume it (seasonal adjust, ARIMA, etc.) get a sensible
                // default without forcing the user to set it manually.
                Frequency = detectedFrequency,
                Series = selectionResult.Series.Select(s => new SeriesData
                {
                    Name = s.Name,
                    Values = s.Values,
                    NumberFormat = s.NumberFormat,
                }).ToList(),
                Params = paramsDict,
                FillConfig = new FillConfig(),
            };

            // Capture the time column's cell NumberFormat (e.g. "dd-mmm-yyyy",
            // "m/d/yyyy"), if available, so the Time column in output tables
            // uses the same format as the source.
            try
            {
                if (!string.IsNullOrEmpty(timeColumnAddress) && request.Series.Count > 0)
                {
                    var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                    var src = app.ActiveSheet as Worksheet;
                    var timeRange = src?.Range[timeColumnAddress];
                    if (timeRange != null)
                    {
                        // Pick the second cell (skip a likely header row).
                        var probeRow = timeRange.Row + (timeRange.Rows.Count > 1 ? 1 : 0);
                        var probe = (Range)src.Cells[probeRow, timeRange.Column];
                        var tf = probe.NumberFormat as string;
                        if (!string.IsNullOrEmpty(tf) && !string.Equals(tf, "General",
                            StringComparison.OrdinalIgnoreCase))
                        {
                            // Stash on the first series so the writer can
                            // find it without a separate plumbing channel.
                            request.Series[0].TimeNumberFormat = tf;
                        }
                    }
                }
            }
            catch (Exception nfEx)
            {
                Logger.Info($"Could not capture time column NumberFormat: {nfEx.Message}");
            }

            // Run async on background thread
            _activeRunCts = new System.Threading.CancellationTokenSource();
            var runToken = _activeRunCts.Token;
            System.Threading.Interlocked.Increment(ref _paneRunsInFlight);
            Task.Run(async () =>
            {
                Action<ProgressEvent> progressHandler = (evt) =>
                {
                    // Progress updates are fire-and-forget UI refreshes (no
                    // return value, order/drop-tolerant). Post them with the
                    // NON-BLOCKING BeginInvoke so the pipe-read thread — which
                    // invokes this handler synchronously per progress event —
                    // NEVER blocks on the Excel UI thread. A blocking Invoke
                    // here can stall the read loop mid-run, starving the named
                    // pipe; the engine then blocks in FlushFileBuffers waiting
                    // for the client to drain, deadlocking the run at completion
                    // (the "95%" hang) and orphaning the engine process.
                    // BeginInvoke keeps the reader draining continuously.
                    _hostControl?.BeginInvoke((System.Action)(() =>
                    {
                        runVm.ReportProgress(evt.Stage, evt.Pct, evt.Message ?? evt.Stage);
                    }));
                };

                try
                {
                    AddIn.Engine.EnsureRunning();
                    AddIn.Engine.ProgressReceived += progressHandler;

                    var response = await AddIn.Engine.RunAsync(request, runToken);

                    AddIn.Engine.ProgressReceived -= progressHandler;

                    if (runToken.IsCancellationRequested || response.Status == "canceled")
                    {
                        // User canceled — OnCancelRequested already reset the view
                        // and hard-stopped the engine; don't write results.
                    }
                    else if (response.Status == "failure")
                    {
                        _hostControl?.Invoke((System.Action)(() =>
                        {
                            runVm.FailRun(EngineFailureText(response));
                        }));
                    }
                    else
                    {
                        // Write results to Excel on the main thread (COM calls require it),
                        // then update the VM on the WinForms UI thread with the resulting
                        // sheet names so the "Go to Sheet" links have real targets.
                        ExcelAsyncUtil.QueueAsMacro(() =>
                        {
                            // A Cancel between the engine's reply and this step: write nothing
                            // (the pane already says "The run was canceled. Nothing was written.").
                            if (runToken.IsCancellationRequested)
                            {
                                Logger.Info("Run canceled before its results were written; nothing was written.");
                                return;
                            }
                            ExcelWriter.WriteResult writeResult = null;
                            try
                            {
                                writeResult = ExcelWriter.WriteRunResult(request, response);
                                RememberResultsWorkbook(writeResult);
                            }
                            catch (Exception writeEx)
                            {
                                Logger.Error("ExcelWriter.WriteRunResult threw on main thread.", writeEx);
                            }

                            _hostControl?.Invoke((System.Action)(() =>
                            {
                                PresentResult(runVm, response, writeResult);
                            }));
                        });
                    }
                }
                catch (Exception ex)
                {
                    AddIn.Engine.ProgressReceived -= progressHandler;
                    Logger.Error("Task pane run failed.", ex);
                    _hostControl?.Invoke((System.Action)(() =>
                    {
                        // A cancel while the engine was starting: the Cancel click already reset the view.
                        if (ex is OperationCanceledException) return;
                        runVm.FailRun(RunExceptionText(ex));
                    }));
                }
                finally
                {
                    System.Threading.Interlocked.Decrement(ref _paneRunsInFlight);
                }
            });
        }

        // ── Pane message text (docs/HOUSE_STYLE.md: Text, Errors and refusals) ──

        private static string LogsFolder => System.IO.Path.Combine(AddIn.AppDataPath, "logs");

        /// <summary>
        /// The engine reported a failure (A2 T1): a plain sentence and the state first, the
        /// engine's own text after it, then its suggested fixes (error_fixes, which were
        /// dropped before - A2 N11). A failure the add-in itself made (identity mismatch,
        /// stalled or unreadable reply) is already a complete house message.
        /// </summary>
        private static string EngineFailureText(RunResponse response)
        {
            if (response.FromAddIn && !string.IsNullOrWhiteSpace(response.ErrorMessage))
                return response.ErrorMessage;

            var text = "The run did not complete, so nothing was written.\n\n" +
                       "The engine reported:\n" +
                       HouseDialog.Indent(string.IsNullOrWhiteSpace(response.ErrorMessage)
                           ? "(no description)" : response.ErrorMessage);
            var fixes = (response.ErrorFixes ?? new List<string>())
                .Where(f => !string.IsNullOrWhiteSpace(f)).ToList();
            if (fixes.Count > 0)
            {
                text += "\n\nSuggested fixes:\n" + string.Join("\n", fixes.Select(f => HouseDialog.Indent("- " + f.Trim()))) +
                        "\n\nIf the run still fails, tell Matthew Hornbach.";
            }
            else
            {
                text += "\n\nCheck the data and the parameters in the task pane, then click Run again. " +
                        "If the run still fails, tell Matthew Hornbach.";
            }
            return text;
        }

        /// <summary>
        /// A run that threw (A2 T2). The engine's start and identity refusals are already
        /// complete house messages; anything else gets the plain sentence and state first.
        /// </summary>
        private static string RunExceptionText(Exception ex)
        {
            if (ex is EngineRefusalException) return ex.Message;
            return "The run did not complete, so nothing was written.\n\n" +
                   HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                   "Try again. If this message returns, tell Matthew Hornbach.";
        }

        /// <summary>
        /// Show what the results write did (A2 T3/T4). A write that failed, or never
        /// reported, is a failure in the red error area (A2 N10: it used to read as a
        /// "Warning:" inside the green success area, or as plain success).
        /// </summary>
        private static void PresentResult(RunViewModel runVm, RunResponse response, ExcelWriter.WriteResult writeResult)
        {
            if (writeResult == null || !writeResult.Success)
            {
                var detail = writeResult?.ErrorMessage;
                runVm.FailRun(
                    "The analysis finished, but its results could not be written to Excel. " +
                    "The data workbook was not changed; if a new results workbook opened, it is incomplete and was not saved.\n\n" +
                    (string.IsNullOrWhiteSpace(detail)
                        ? "The log has the details:\n" + HouseDialog.Indent(LogsFolder)
                        : HouseDialog.ErrorBlock(detail)) + "\n\n" +
                    "Click Run to try again. If this message returns, tell Matthew Hornbach.");
                return;
            }

            var sheets = new List<OutputSheetLink>();
            if (!string.IsNullOrEmpty(writeResult.ResultSheetName))
                sheets.Add(new OutputSheetLink { TableName = "Results", SheetName = writeResult.ResultSheetName });
            if (!string.IsNullOrEmpty(writeResult.AuditSheetName))
                sheets.Add(new OutputSheetLink { TableName = "Audit", SheetName = writeResult.AuditSheetName });

            // Also list the logical tables from the engine response (even if ExcelWriter
            // bundled them into the single results sheet, this gives the user a map of
            // what's there).
            if (response.Tables != null)
            {
                foreach (var t in response.Tables)
                    sheets.Add(new OutputSheetLink { TableName = t.Name, SheetName = writeResult.ResultSheetName });
            }

            var summary = HouseDialog.Ascii(string.IsNullOrWhiteSpace(response.PlainEnglishSummary)
                ? "The run completed." : response.PlainEnglishSummary.Trim());
            if (!string.IsNullOrEmpty(writeResult.OutputPath))
            {
                // Results go to a SEPARATE workbook - the input workbook is never
                // modified. Tell the user where.
                summary += "\n\nThe results were saved to a new workbook:\n" + HouseDialog.Indent(writeResult.OutputPath) +
                           "\n\nThe data workbook was not changed." +
                           (writeResult.UsedFallbackFolder
                               ? " It has never been saved, so the results went to the Documents folder."
                               : "");
            }
            else if (!string.IsNullOrEmpty(writeResult.SaveWarning))
            {
                summary += "\n\n" + writeResult.SaveWarning;
            }

            runVm.CompleteRun(summary, sheets);
        }

        /// <summary>
        /// Handle the Analyze Selection click from the Data Readiness view.
        /// Extracts the current Excel selection, runs a battery of data-quality
        /// checks in-process (no engine round-trip needed), and populates the VM.
        /// </summary>
        private static void OnDataReadinessChecksRequested(DataReadinessViewModel vm)
        {
            if (vm == null) return;
            vm.IsAnalysing = true;

            try
            {
                var checks = new List<ReadinessCheckItem>();
                var selectionResult = _selectionService.ExtractFromSelection();

                // ── Check 1: Selection exists ─────────────────────────────
                if (!selectionResult.Success || selectionResult.Series.Count == 0)
                {
                    var detail = selectionResult.ErrorMessage ?? "The selection contains no numbers.";
                    var suggestion = "Select one or more data columns in Excel, then click Refresh.";
                    if (selectionResult.ReadFailed)
                    {
                        detail += "\n\n" + HouseDialog.ErrorBlock(selectionResult.ErrorDetail);
                        suggestion = "Select the data again, then click Refresh. If this message returns, tell Matthew Hornbach.";
                    }
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Selection",
                        Status = "Fail",
                        Detail = detail,
                        Suggestion = suggestion
                    });
                    vm.ShowResults(0, 0, checks);
                    return;
                }

                int seriesCount = selectionResult.Series.Count;
                int totalPoints = selectionResult.Series.Sum(s => s.Length);

                checks.Add(new ReadinessCheckItem
                {
                    CheckName = "Selection",
                    Status = "Pass",
                    Detail = $"{seriesCount} series, {totalPoints} total points extracted.",
                    Suggestion = ""
                });

                // ── Check 2: Minimum length (≥20 for most techniques) ────
                int minLen = selectionResult.Series.Min(s => s.Length);
                if (minLen >= 50)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Minimum length",
                        Status = "Pass",
                        Detail = $"Shortest series has {minLen} observations (ample).",
                        Suggestion = ""
                    });
                }
                else if (minLen >= 20)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Minimum length",
                        Status = "Warning",
                        Detail = $"Shortest series has {minLen} observations. Enough for basic analysis, but some techniques (VAR, GARCH, ML) need at least 50.",
                        Suggestion = "For volatility or multivariate models, aim for at least 50 points."
                    });
                }
                else
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Minimum length",
                        Status = "Fail",
                        Detail = $"Shortest series has only {minLen} observations. Most techniques need at least 20.",
                        Suggestion = "Select a longer range with at least 20 numeric rows."
                    });
                }

                // ── Check 3: Equal lengths across series ──────────────────
                var lengths = selectionResult.Series.Select(s => s.Length).Distinct().ToList();
                if (lengths.Count == 1)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Aligned series",
                        Status = "Pass",
                        Detail = $"All {seriesCount} series have the same length ({lengths[0]}).",
                        Suggestion = ""
                    });
                }
                else
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Aligned series",
                        Status = "Fail",
                        Detail = $"Series have different lengths: {string.Join(", ", lengths)}.",
                        Suggestion = "Reselect so all columns share the same row range."
                    });
                }

                // ── Check 4: Missing data ────────────────────────────────
                double overallMissingPct = totalPoints == 0 ? 0
                    : 100.0 * selectionResult.Series.Sum(s => s.MissingCount) / totalPoints;
                var worstMissing = selectionResult.Series.OrderByDescending(s => s.MissingPct).First();
                if (overallMissingPct == 0)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Missing data",
                        Status = "Pass",
                        Detail = "No missing values detected.",
                        Suggestion = ""
                    });
                }
                else if (overallMissingPct < 5)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Missing data",
                        Status = "Warning",
                        Detail = $"{overallMissingPct:F1}% missing overall (worst: '{worstMissing.Name}' at {worstMissing.MissingPct:F1}%).",
                        Suggestion = "Kalman imputation will fill gaps automatically at run time."
                    });
                }
                else
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Missing data",
                        Status = "Fail",
                        Detail = $"{overallMissingPct:F1}% missing overall, which is high. Worst: '{worstMissing.Name}' at {worstMissing.MissingPct:F1}%.",
                        Suggestion = "Investigate the gaps before modeling; consider a shorter window with complete data."
                    });
                }

                // ── Check 5: Constant series ─────────────────────────────
                var constantSeries = selectionResult.Series.Where(IsConstantSeries).ToList();
                if (constantSeries.Count == 0)
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Variability",
                        Status = "Pass",
                        Detail = "All series show variation.",
                        Suggestion = ""
                    });
                }
                else
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Variability",
                        Status = "Fail",
                        Detail = $"Constant or near-constant series: {string.Join(", ", constantSeries.Select(s => s.Name))}.",
                        Suggestion = "Remove constant columns. Time series techniques need variation."
                    });
                }

                // ── Check 6: Time index ──────────────────────────────────
                try
                {
                    var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                    var selection = app.Selection as Range;
                    if (selection?.Areas.Count > 0)
                    {
                        var firstArea = selection.Areas[1];
                        var detection = _timeDetector.Detect(firstArea, firstArea.Row, firstArea.Rows.Count);
                        if (detection.BestCandidate != null && detection.ParsedDates != null)
                        {
                            var cand = detection.BestCandidate;
                            string freq = string.IsNullOrEmpty(cand.SuggestedFrequency) ? "unknown frequency" : cand.SuggestedFrequency;
                            checks.Add(new ReadinessCheckItem
                            {
                                CheckName = "Time index",
                                Status = cand.OverallScore >= 0.8 ? "Pass" : "Warning",
                                Detail = $"Detected '{cand.HeaderName ?? cand.ColumnLetter}' as time index ({freq}).",
                                Suggestion = cand.OverallScore >= 0.8 ? "" : "Some dates could not be parsed or are irregular."
                            });
                        }
                        else
                        {
                            checks.Add(new ReadinessCheckItem
                            {
                                CheckName = "Time index",
                                Status = "Warning",
                                Detail = "No clear time/date column adjacent to selection.",
                                Suggestion = "Place a date column immediately left of your data for best results."
                            });
                        }
                    }
                }
                catch (Exception ex)
                {
                    Logger.Info($"Time index detection failed in readiness check: {ex.Message}");
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Time index",
                        Status = "Warning",
                        Detail = "Could not evaluate time index.",
                        Suggestion = "Place a date column immediately left of your data."
                    });
                }

                vm.ShowResults(seriesCount, totalPoints, checks);
            }
            catch (Exception ex)
            {
                Logger.Error("Data readiness checks failed.", ex);
                vm.ShowResults(0, 0, new[]
                {
                    new ReadinessCheckItem
                    {
                        CheckName = "Error",
                        Status = "Fail",
                        Detail = "Time Series Lab could not finish the readiness checks. Nothing was changed.\n\n" +
                                 HouseDialog.ErrorBlock(ex.Message),
                        Suggestion = "Click Refresh to try again. If this message returns, tell Matthew Hornbach.\n\n" +
                                     "The log has the details:\n" + HouseDialog.Indent(LogsFolder)
                    }
                });
            }
        }

        /// <summary>
        /// Convert an AddIn-side catalog entry into a UI-layer TechniqueItem.
        /// Loads the long-form markdown description on demand.
        /// </summary>
        private static TechniqueItem ConvertCatalogEntry(TechniqueCatalogEntry entry)
        {
            string description;
            try
            {
                description = TechniqueCatalogService.GetDescription(entry.Id);
            }
            catch
            {
                description = entry.Summary ?? "";
            }

            var parameters = new List<TechniqueParameterItem>();
            if (entry.Parameters != null)
            {
                foreach (var p in entry.Parameters)
                {
                    parameters.Add(new TechniqueParameterItem
                    {
                        Name = p.Name,
                        Label = p.Label,
                        Type = p.Type,
                        Default = p.Default,
                        Required = p.Required,
                        Advanced = p.Advanced,
                        Description = p.Description,
                        Options = p.Options,
                    });
                }
            }

            return new TechniqueItem
            {
                Id = entry.Id,
                Name = entry.Name,
                Category = entry.Category,
                Summary = entry.Summary,
                Description = description,
                SupportsAutoUdf = entry.SupportsAutoUdf,
                AutoUdfName = entry.AutoUdfName,
                MinSeries = entry.MinSeries,
                MaxSeries = entry.MaxSeries,
                Tags = entry.Tags ?? new List<string>(),
                Presets = entry.Presets ?? new List<string> { "Fast", "Balanced", "Thorough" },
                Parameters = parameters,
                OutputTables = entry.OutputTables ?? new List<string>(),
            };
        }

        private static bool IsConstantSeries(SelectionService.ExtractedSeries s)
        {
            if (s.Values == null || s.Length < 2) return true;
            double? first = null;
            foreach (var v in s.Values)
            {
                if (!v.HasValue) continue;
                if (first == null) { first = v; continue; }
                if (Math.Abs(v.Value - first.Value) > 1e-12) return false;
            }
            return true; // All values equal or all missing
        }

        /// <summary>
        /// What a Run view is filled from (A2 U6, N5): the active workbook, the active sheet
        /// and the extracted columns' addresses. Nulls when Excel cannot say.
        /// </summary>
        private static (Workbook Wb, Worksheet Ws, string Addresses) CurrentSelectionIdentity(
            SelectionService.SelectionResult selection)
        {
            try
            {
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                var addresses = selection?.Series == null ? null
                    : string.Join(",", selection.Series.Select(s => s.Address));
                return (app?.ActiveWorkbook, app?.ActiveSheet as Worksheet, addresses);
            }
            catch
            {
                return (null, null, null);
            }
        }

        /// <summary>
        /// Whether <paramref name="selection"/> is the one the Run view was filled from. The
        /// workbook and sheet are compared as objects, so a first save, a Save As or a sheet
        /// rename is no change; by name when the objects differ. Two unknowns are equal, so an
        /// unreadable selection never blocks a run on its own.
        /// </summary>
        private static bool IsPreviewedSelection((Workbook Wb, Worksheet Ws, string Addresses) selection)
        {
            return SameObject(selection.Wb, _previewedWorkbook, w => w.FullName) &&
                   SameObject(selection.Ws, _previewedSheet, s => s.Name) &&
                   string.Equals(selection.Addresses, _previewedAddresses, StringComparison.Ordinal);
        }

        private static bool SameObject<T>(T a, T b, Func<T, string> name) where T : class
        {
            if (a == null && b == null) return true;
            if (a == null || b == null) return false;
            if (ReferenceEquals(a, b)) return true;
            try { return string.Equals(name(a), name(b), StringComparison.OrdinalIgnoreCase); }
            catch { return false; }
        }

        private static string DescribeSelection(Workbook wb, Worksheet ws, string addresses)
        {
            string w = "(none)", s = "(none)";
            try { if (wb != null) w = wb.FullName; } catch { w = "(closed)"; }
            try { if (ws != null) s = ws.Name; } catch { s = "(gone)"; }
            return $"{w} | {s} | {addresses ?? "(none)"}";
        }

        private static void OnVisibleStateChange(CustomTaskPane pane)
        {
            Logger.Info($"Task pane visibility changed: {pane.Visible}");
        }

        /// <summary>
        /// True if the given Excel address (e.g. "A1:A11901") refers to the
        /// column identified by <paramref name="columnLetter"/> (e.g. "A").
        /// Case-insensitive. Used to match series rows against a detected
        /// time-index column so we can drop the dates out of the numeric
        /// payload sent to the engine.
        /// </summary>
        private static bool SeriesAddressStartsWithColumn(string address, string columnLetter)
        {
            if (string.IsNullOrEmpty(address) || string.IsNullOrEmpty(columnLetter))
                return false;

            // Grab the leading letters of the address (everything up to the first digit).
            int i = 0;
            while (i < address.Length && char.IsLetter(address[i])) i++;
            if (i == 0) return false;

            var leading = address.Substring(0, i);
            return string.Equals(leading, columnLetter, StringComparison.OrdinalIgnoreCase);
        }
    }
}
