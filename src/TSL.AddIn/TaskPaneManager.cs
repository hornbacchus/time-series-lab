using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading.Tasks;
using System.Windows.Forms;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;
using Microsoft.Office.Interop.Excel;
using TSL.AddIn.Models;
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

        /// <summary>
        /// Show the task pane (create if needed) and open the Technique
        /// Explorer pre-selected to <paramref name="techniqueId"/>. Used by
        /// Task Pane navigation flows that want the user to read the
        /// description before running.
        /// </summary>
        public static void ShowAndSelect(string techniqueId)
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToTechnique(techniqueId);
        }

        /// <summary>
        /// Show the task pane, navigate directly to the Run view for
        /// <paramref name="techniqueId"/>, and immediately kick off the
        /// analysis against the current Excel selection. This is the
        /// "one-click" path used by the ribbon's Quick Action buttons —
        /// users expect Seasonal Adjustment / PCA / Granger / etc. to
        /// execute, not to land on a description page.
        /// </summary>
        public static void RunTechnique(string techniqueId)
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            // OnRunRequested does everything: extracts the Excel selection,
            // populates the Run view, builds the RunRequest, and calls the
            // engine. Going through the same event path that the Explorer's
            // "Run on Selection" button uses keeps behavior consistent.
            OnRunRequested(techniqueId, AddIn.Settings?.GetGlobalPreset() ?? "Balanced");
        }

        public static void ShowExplorer()
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToExplorer();
        }

        public static void ShowRecommender()
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToRecommender();
        }

        public static void ShowRecommenderWithGoal(string goal)
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToRecommenderWithGoal(goal);
        }

        public static void ShowExplorerWithCategory(string category)
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToExplorerWithCategory(category);
        }

        public static void ShowDataReadiness()
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToDataReadiness();
        }

        public static void ShowSettings()
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToSettings();
        }

        public static void ShowUdfBrowser()
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToUdfBrowser();
        }

        public static void RunCurrent()
        {
            _hostControl?.RunCurrentTechnique();
        }

        public static void UpdatePreset(string preset)
        {
            _hostControl?.SetPreset(preset);
        }

        private static void EnsureTaskPane()
        {
            if (_taskPane != null) return;

            try
            {
                _hostControl = new TSL.UI.TaskPaneHostControl();

                // Wire the RunRequested event to extract selection and run the engine
                _hostControl.ViewModel.RunRequested += OnRunRequested;

                // Wire the Data Readiness checks request
                _hostControl.ViewModel.DataReadinessChecksRequested += OnDataReadinessChecksRequested;

                // Push the real technique catalog into the Explorer VM, replacing
                // the 9-item dev stub that it loads at construction.
                try
                {
                    var catalog = TechniqueCatalogService.GetCatalog();
                    var items = catalog?.Techniques?.Select(ConvertCatalogEntry).ToList();
                    if (items != null && items.Count > 0)
                    {
                        _hostControl.LoadTechniqueCatalog(items);
                        Logger.Info($"Pushed {items.Count} techniques into Explorer VM.");
                    }
                    else
                    {
                        Logger.Warn("Technique catalog is empty; Explorer will fall back to built-in stub.");
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
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to create task pane.", ex);
                MessageBox.Show(
                    $"Failed to create Task Pane:\n{ex.Message}",
                    "Time Series Lab",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        /// <summary>
        /// Handles the RunRequested event from the Task Pane.
        /// Extracts data from the current Excel selection (including non-adjacent ranges),
        /// detects a time index, validates series lengths, and dispatches to the engine.
        /// </summary>
        private static void OnRunRequested(string techniqueId, string preset)
        {
            if (string.IsNullOrEmpty(techniqueId)) return;

            // Extract series from current selection (handles non-adjacent via selection.Areas)
            var selectionResult = _selectionService.ExtractFromSelection();
            if (!selectionResult.Success || selectionResult.Series.Count == 0)
            {
                var msg = selectionResult.ErrorMessage
                    ?? "No data selected. Please select one or more data columns in Excel first.";
                MessageBox.Show(msg, "Time Series Lab", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // Validate all series have the same length
            var lengths = selectionResult.Series.Select(s => s.Length).Distinct().ToList();
            if (lengths.Count > 1)
            {
                MessageBox.Show(
                    $"Selected columns have different lengths ({string.Join(", ", lengths)}). " +
                    "All series must have the same number of rows. Please reselect.",
                    "Time Series Lab", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

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

            // Navigate to Run view and populate series previews
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

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

                bool techniqueChanged = !string.Equals(runVm.TechniqueId, techniqueId,
                    StringComparison.OrdinalIgnoreCase);
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

            runVm.IsRunning = true;

            // Build the RunRequest. Pull per-technique parameter values from
            // the Run pane so the engine sees the user's current settings
            // (e.g. covid_outliers checkbox, fit_window_obs text box) instead
            // of running with nothing but defaults.
            var paramsDict = runVm.GetParametersDict() ?? new Dictionary<string, object>();
            var request = new RunRequest
            {
                RunId = $"pane_{Guid.NewGuid():N}",
                TechniqueId = techniqueId,
                Preset = preset ?? "Balanced",
                Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                Time = timeArray,
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
            Task.Run(async () =>
            {
                Action<ProgressEvent> progressHandler = (evt) =>
                {
                    _hostControl?.Invoke((System.Action)(() =>
                    {
                        runVm.ReportProgress(evt.Stage, evt.Pct, evt.Message ?? evt.Stage);
                    }));
                };

                try
                {
                    AddIn.Engine.EnsureRunning();
                    AddIn.Engine.ProgressReceived += progressHandler;

                    var response = await AddIn.Engine.RunAsync(request);

                    AddIn.Engine.ProgressReceived -= progressHandler;

                    if (response.Status == "failure")
                    {
                        _hostControl?.Invoke((System.Action)(() =>
                        {
                            runVm.FailRun(response.ErrorMessage ?? "Unknown error from engine.");
                        }));
                    }
                    else
                    {
                        // Write results to Excel on the main thread (COM calls require it),
                        // then update the VM on the WinForms UI thread with the resulting
                        // sheet names so the "Go to Sheet" links have real targets.
                        ExcelAsyncUtil.QueueAsMacro(() =>
                        {
                            ExcelWriter.WriteResult writeResult = null;
                            try
                            {
                                writeResult = ExcelWriter.WriteRunResult(request, response);
                            }
                            catch (Exception writeEx)
                            {
                                Logger.Error("ExcelWriter.WriteRunResult threw on main thread.", writeEx);
                            }

                            _hostControl?.Invoke((System.Action)(() =>
                            {
                                var sheets = new List<OutputSheetLink>();
                                if (writeResult != null && writeResult.Success)
                                {
                                    if (!string.IsNullOrEmpty(writeResult.ResultSheetName))
                                        sheets.Add(new OutputSheetLink
                                        {
                                            TableName = "Results",
                                            SheetName = writeResult.ResultSheetName,
                                        });
                                    if (!string.IsNullOrEmpty(writeResult.AuditSheetName))
                                        sheets.Add(new OutputSheetLink
                                        {
                                            TableName = "Audit",
                                            SheetName = writeResult.AuditSheetName,
                                        });
                                }

                                // Also list the logical tables from the engine response
                                // (even if ExcelWriter bundled them into the single results sheet,
                                // this gives the user a map of what's there).
                                if (response.Tables != null)
                                {
                                    foreach (var t in response.Tables)
                                    {
                                        sheets.Add(new OutputSheetLink
                                        {
                                            TableName = t.Name,
                                            SheetName = writeResult?.ResultSheetName,
                                        });
                                    }
                                }

                                var summary = response.PlainEnglishSummary ?? "Run completed.";
                                if (writeResult != null && !writeResult.Success
                                    && !string.IsNullOrEmpty(writeResult.ErrorMessage))
                                {
                                    summary += $"\n\nWarning: {writeResult.ErrorMessage}";
                                }

                                runVm.CompleteRun(summary, sheets);
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
                        runVm.FailRun($"Run failed: {ex.Message}");
                    }));
                }
            });
        }

        /// <summary>
        /// Handle the Analyse Selection click from the Data Readiness view.
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
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Selection",
                        Status = "Fail",
                        Detail = selectionResult.ErrorMessage
                                 ?? "No numeric data found in the current Excel selection.",
                        Suggestion = "Select one or more data columns in Excel, then click Refresh."
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
                        Detail = $"Shortest series has {minLen} observations. OK for basic analysis but some techniques (VAR, GARCH, ML) need ≥50.",
                        Suggestion = "For volatility or multivariate models, aim for at least 50 points."
                    });
                }
                else
                {
                    checks.Add(new ReadinessCheckItem
                    {
                        CheckName = "Minimum length",
                        Status = "Fail",
                        Detail = $"Shortest series has only {minLen} observations. Most techniques require ≥20.",
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
                        Detail = $"{overallMissingPct:F1}% missing overall — high. Worst: '{worstMissing.Name}' at {worstMissing.MissingPct:F1}%.",
                        Suggestion = "Investigate gaps before modelling; consider a shorter window with complete data."
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
                        Suggestion = "Remove constant columns — time series techniques require variation."
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
                        Detail = $"Readiness check failed: {ex.Message}",
                        Suggestion = "Check the add-in log for details."
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
