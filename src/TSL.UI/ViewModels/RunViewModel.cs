using System;
using System.Collections.ObjectModel;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// Represents one series in the selection preview on the Run screen.
    /// </summary>
    public class SeriesPreviewItem : ViewModelBase
    {
        public string Name { get; set; }
        public string Address { get; set; }
        public int Length { get; set; }
        public double MissingPct { get; set; }
        public string MissingDisplay => MissingPct > 0 ? $"{MissingPct:F1}% missing" : "Complete";
    }

    /// <summary>
    /// Represents a log entry in the run progress log.
    /// </summary>
    public class ProgressLogEntry
    {
        public DateTime Timestamp { get; set; }
        public string Stage { get; set; }
        public string Message { get; set; }
        public string Display => $"[{Timestamp:HH:mm:ss}] {Stage}: {Message}";
    }

    /// <summary>
    /// Represents a link to a created output sheet.
    /// </summary>
    public class OutputSheetLink
    {
        public string SheetName { get; set; }
        public string TableName { get; set; }
    }

    // NOTE: TechniqueParameterItem is defined once in TechniqueExplorerViewModel.cs
    // and reused here so the Explorer's "technique details" panel and the Run
    // pane share a single parameter object model.

    /// <summary>
    /// ViewModel for the Run configuration and progress view.
    /// Shows selection preview, time index / frequency selectors, a progress log,
    /// and links to output sheets once the run completes.
    /// </summary>
    public class RunViewModel : ViewModelBase
    {
        // ── Observable collections ──────────────────────────────────────

        public ObservableCollection<SeriesPreviewItem> SeriesPreviews { get; }
            = new ObservableCollection<SeriesPreviewItem>();

        public ObservableCollection<ProgressLogEntry> ProgressLog { get; }
            = new ObservableCollection<ProgressLogEntry>();

        public ObservableCollection<OutputSheetLink> OutputSheets { get; }
            = new ObservableCollection<OutputSheetLink>();

        public ObservableCollection<string> AvailableFrequencies { get; }
            = new ObservableCollection<string>
            {
                "Auto-detect",
                "Daily",
                "Weekly",
                "Monthly",
                "Quarterly",
                "Annual",
                "Hourly",
                "Minutely",
                "Custom"
            };

        /// <summary>
        /// Technique-specific parameters, rendered as controls in the Run
        /// pane. Populated from the technique catalog when a technique is
        /// selected.
        /// </summary>
        public ObservableCollection<TechniqueParameterItem> Parameters { get; }
            = new ObservableCollection<TechniqueParameterItem>();

        public bool HasParameters => Parameters != null && Parameters.Count > 0;

        // ── Properties ──────────────────────────────────────────────────

        private string _techniqueId;
        public string TechniqueId
        {
            get => _techniqueId;
            set
            {
                if (SetProperty(ref _techniqueId, value))
                    OnPropertyChanged(nameof(TechniqueDisplayName));
            }
        }

        private string _techniqueName;
        /// <summary>
        /// Human-readable technique name (e.g. "Principal Component Analysis").
        /// Set by the AddIn layer from the catalog. Falls back to prettified ID
        /// when not set.
        /// </summary>
        public string TechniqueName
        {
            get => _techniqueName;
            set
            {
                if (SetProperty(ref _techniqueName, value))
                    OnPropertyChanged(nameof(TechniqueDisplayName));
            }
        }

        public string TechniqueDisplayName
        {
            get
            {
                if (!string.IsNullOrEmpty(_techniqueName)) return _techniqueName;
                if (string.IsNullOrEmpty(_techniqueId)) return "No technique selected";
                // Fallback: prettify the ID (e.g. "pca_analysis" -> "Pca Analysis")
                var spaced = _techniqueId.Replace("_", " ");
                var parts = spaced.Split(' ');
                for (int i = 0; i < parts.Length; i++)
                {
                    if (parts[i].Length > 0)
                        parts[i] = char.ToUpper(parts[i][0]) + parts[i].Substring(1);
                }
                return string.Join(" ", parts);
            }
        }

        private string _preset = "Balanced";
        public string Preset
        {
            get => _preset;
            set => SetProperty(ref _preset, value);
        }

        private string _selectedFrequency = "Auto-detect";
        public string SelectedFrequency
        {
            get => _selectedFrequency;
            set => SetProperty(ref _selectedFrequency, value);
        }

        private string _detectedFrequency = "Not yet detected";
        public string DetectedFrequency
        {
            get => _detectedFrequency;
            set => SetProperty(ref _detectedFrequency, value);
        }

        private string _timeIndexAddress = "";
        public string TimeIndexAddress
        {
            get => _timeIndexAddress;
            set => SetProperty(ref _timeIndexAddress, value);
        }

        private bool _useTimeIndex;
        public bool UseTimeIndex
        {
            get => _useTimeIndex;
            set => SetProperty(ref _useTimeIndex, value);
        }

        private bool _isRunning;
        public bool IsRunning
        {
            get => _isRunning;
            set
            {
                if (SetProperty(ref _isRunning, value))
                {
                    OnPropertyChanged(nameof(CanRun));
                    OnPropertyChanged(nameof(ShowProgress));
                }
            }
        }

        public bool CanRun => !_isRunning && SeriesPreviews.Count > 0;
        public bool ShowProgress => _isRunning || ProgressLog.Count > 0;

        private int _progressPercent;
        public int ProgressPercent
        {
            get => _progressPercent;
            set => SetProperty(ref _progressPercent, value);
        }

        private string _progressStage = "";
        public string ProgressStage
        {
            get => _progressStage;
            set => SetProperty(ref _progressStage, value);
        }

        private bool _isComplete;
        public bool IsComplete
        {
            get => _isComplete;
            set => SetProperty(ref _isComplete, value);
        }

        private string _resultSummary = "";
        public string ResultSummary
        {
            get => _resultSummary;
            set => SetProperty(ref _resultSummary, value);
        }

        private string _errorMessage = "";
        public string ErrorMessage
        {
            get => _errorMessage;
            set
            {
                if (SetProperty(ref _errorMessage, value))
                    OnPropertyChanged(nameof(HasError));
            }
        }

        public bool HasError => !string.IsNullOrEmpty(_errorMessage);

        // ── Commands ────────────────────────────────────────────────────

        public ICommand RunCommand { get; }
        public ICommand CancelCommand { get; }
        public ICommand GoToSheetCommand { get; }
        public ICommand ResetCommand { get; }

        /// <summary>
        /// Raised when the user clicks Run. The AddIn layer subscribes to
        /// this and performs the actual engine call.
        /// </summary>
        public event Action RunExecuteRequested;

        /// <summary>
        /// Raised when the user clicks Cancel.
        /// </summary>
        public event Action CancelRequested;

        /// <summary>
        /// Raised when the user clicks an output sheet link.
        /// </summary>
        public event Action<string> GoToSheetRequested;

        // ── Constructor ─────────────────────────────────────────────────

        public RunViewModel()
        {
            RunCommand = new RelayCommand(
                () => RunExecuteRequested?.Invoke(),
                () => CanRun);

            CancelCommand = new RelayCommand(
                () => CancelRequested?.Invoke(),
                () => IsRunning);

            GoToSheetCommand = new RelayCommand(
                (param) => GoToSheetRequested?.Invoke(param as string),
                (param) => param is string s && !string.IsNullOrEmpty(s));

            ResetCommand = new RelayCommand(OnReset);
        }

        // ── Public API (called from AddIn layer) ────────────────────────

        /// <summary>
        /// Populate series preview from the current Excel selection.
        /// </summary>
        public void SetSeriesPreviews(System.Collections.Generic.IEnumerable<SeriesPreviewItem> items)
        {
            SeriesPreviews.Clear();
            foreach (var item in items)
                SeriesPreviews.Add(item);
            OnPropertyChanged(nameof(CanRun));
        }

        /// <summary>
        /// Append a progress event from the engine.
        /// </summary>
        public void ReportProgress(string stage, int? pct, string message)
        {
            ProgressStage = stage;
            if (pct.HasValue)
                ProgressPercent = pct.Value;

            ProgressLog.Add(new ProgressLogEntry
            {
                Timestamp = DateTime.Now,
                Stage = stage,
                Message = message
            });
            OnPropertyChanged(nameof(ShowProgress));
        }

        /// <summary>
        /// Mark the run as completed successfully.
        /// </summary>
        public void CompleteRun(string summary, System.Collections.Generic.IEnumerable<OutputSheetLink> sheets)
        {
            IsRunning = false;
            IsComplete = true;
            ProgressPercent = 100;
            ResultSummary = summary;
            ErrorMessage = "";

            OutputSheets.Clear();
            if (sheets != null)
            {
                foreach (var s in sheets)
                    OutputSheets.Add(s);
            }
        }

        /// <summary>
        /// Mark the run as failed.
        /// </summary>
        public void FailRun(string errorMessage)
        {
            IsRunning = false;
            IsComplete = false;
            ErrorMessage = errorMessage;
        }

        private void OnReset()
        {
            IsRunning = false;
            IsComplete = false;
            ProgressPercent = 0;
            ProgressStage = "";
            ResultSummary = "";
            ErrorMessage = "";
            ProgressLog.Clear();
            OutputSheets.Clear();
            OnPropertyChanged(nameof(ShowProgress));
        }

        /// <summary>
        /// Populate the Parameters collection from a catalog parameter list.
        /// Call this whenever the selected technique changes so the Run pane
        /// shows the right controls with their default values.
        /// </summary>
        public void SetParameters(
            System.Collections.Generic.IEnumerable<(string Name, string Label, string Type,
                string Description, System.Collections.Generic.List<string> Options,
                object Default)> paramSpecs)
        {
            Parameters.Clear();
            if (paramSpecs == null) { OnPropertyChanged(nameof(HasParameters)); return; }
            foreach (var p in paramSpecs)
            {
                var item = new TechniqueParameterItem
                {
                    Name = p.Name,
                    Label = string.IsNullOrEmpty(p.Label) ? p.Name : p.Label,
                    Type = p.Type ?? "string",
                    Description = p.Description ?? "",
                    Options = p.Options,
                };
                if (item.IsBool)
                {
                    item.BoolValue = p.Default is bool b && b;
                }
                else
                {
                    item.StringValue = p.Default?.ToString() ?? "";
                }
                Parameters.Add(item);
            }
            OnPropertyChanged(nameof(HasParameters));
        }

        /// <summary>
        /// Serialize current parameter values into a Dictionary suitable for
        /// the RunRequest.Params field the engine consumes.
        /// </summary>
        public System.Collections.Generic.Dictionary<string, object> GetParametersDict()
        {
            var d = new System.Collections.Generic.Dictionary<string, object>();
            foreach (var p in Parameters)
            {
                if (!string.IsNullOrEmpty(p.Name))
                    d[p.Name] = p.OutputValue;
            }
            return d;
        }
    }
}
