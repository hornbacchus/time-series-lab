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
        /// Show the task pane (create if needed) and optionally pre-select a technique.
        /// </summary>
        public static void ShowAndSelect(string techniqueId)
        {
            EnsureTaskPane();
            _taskPane.Visible = true;
            _hostControl?.NavigateToTechnique(techniqueId);
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

                _taskPane = CustomTaskPaneFactory.CreateCustomTaskPane(
                    _hostControl, "Time Series Lab");

                _taskPane.DockPosition = MsoCTPDockPosition.msoCTPDockPositionRight;
                _taskPane.Width = 420;
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

            // Detect time index using TimeIndexDetector
            string[] timeArray = null;
            try
            {
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                var selection = app.Selection as Range;
                if (selection?.Areas.Count > 0)
                {
                    var firstArea = selection.Areas[1];
                    var detection = _timeDetector.Detect(firstArea, firstArea.Row, firstArea.Rows.Count);
                    if (detection.BestCandidate != null && detection.ParsedDates != null)
                        timeArray = detection.ParsedDates;
                }
            }
            catch (Exception ex)
            {
                Logger.Info($"Time index detection skipped: {ex.Message}");
            }

            // Navigate to Run view and populate series previews
            _hostControl.ViewModel.NavigateToRun(techniqueId);
            var runVm = _hostControl.ViewModel.CurrentView as RunViewModel;
            if (runVm == null) return;

            runVm.SetSeriesPreviews(selectionResult.Series.Select(s => new SeriesPreviewItem
            {
                Name = s.Name,
                Address = s.Address,
                Length = s.Length,
                MissingPct = s.MissingPct,
            }));
            runVm.IsRunning = true;

            // Build the RunRequest
            var request = new RunRequest
            {
                RunId = $"pane_{Guid.NewGuid():N}",
                TechniqueId = techniqueId,
                Preset = preset ?? "Balanced",
                Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                Time = timeArray,
                Series = selectionResult.Series.Select(s => new SeriesData
                {
                    Name = s.Name,
                    Values = s.Values,
                }).ToList(),
                Params = new Dictionary<string, object>(),
                FillConfig = new FillConfig(),
            };

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

                    _hostControl?.Invoke((System.Action)(() =>
                    {
                        if (response.Status == "failure")
                        {
                            runVm.FailRun(response.ErrorMessage ?? "Unknown error from engine.");
                        }
                        else
                        {
                            var sheets = response.Tables?
                                .Select(t => new OutputSheetLink { TableName = t.Name })
                                .ToList() ?? new List<OutputSheetLink>();
                            runVm.CompleteRun(
                                response.PlainEnglishSummary ?? "Run completed.",
                                sheets);
                        }
                    }));
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

        private static void OnVisibleStateChange(CustomTaskPane pane)
        {
            Logger.Info($"Task pane visibility changed: {pane.Visible}");
        }
    }
}
