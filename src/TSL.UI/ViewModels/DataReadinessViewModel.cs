using System;
using System.Collections.ObjectModel;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// A single check result in the data readiness report.
    /// </summary>
    public class ReadinessCheckItem : ViewModelBase
    {
        public string CheckName { get; set; }
        public string Status { get; set; }  // "Pass", "Warning", "Fail"
        public string Detail { get; set; }
        public string Suggestion { get; set; }

        public string StatusIcon
        {
            get
            {
                switch (Status)
                {
                    case "Pass": return "OK";
                    case "Warning": return "!!";
                    case "Fail": return "X";
                    default: return "?";
                }
            }
        }
    }

    /// <summary>
    /// ViewModel for the Data Readiness view. Runs a set of quality checks on
    /// the current Excel selection and computes an overall readiness score.
    /// </summary>
    public class DataReadinessViewModel : ViewModelBase
    {
        // ── Collections ─────────────────────────────────────────────────

        public ObservableCollection<ReadinessCheckItem> Checks { get; }
            = new ObservableCollection<ReadinessCheckItem>();

        // ── Properties ──────────────────────────────────────────────────

        private int _overallScore;
        public int OverallScore
        {
            get => _overallScore;
            set
            {
                if (SetProperty(ref _overallScore, value))
                {
                    OnPropertyChanged(nameof(ScoreDisplay));
                    OnPropertyChanged(nameof(ScoreGrade));
                    OnPropertyChanged(nameof(ScoreColor));
                }
            }
        }

        public string ScoreDisplay => $"{_overallScore}/100";

        public string ScoreGrade
        {
            get
            {
                if (_overallScore >= 90) return "Excellent";
                if (_overallScore >= 75) return "Good";
                if (_overallScore >= 50) return "Fair";
                return "Poor";
            }
        }

        public string ScoreColor
        {
            get
            {
                if (_overallScore >= 90) return "#4CAF50";
                if (_overallScore >= 75) return "#8BC34A";
                if (_overallScore >= 50) return "#FF9800";
                return "#F44336";
            }
        }

        private bool _hasRun;
        public bool HasRun
        {
            get => _hasRun;
            set
            {
                if (SetProperty(ref _hasRun, value))
                    OnPropertyChanged(nameof(ShowPlaceholder));
            }
        }

        public bool ShowPlaceholder => !_hasRun;

        private bool _isAnalysing;
        public bool IsAnalysing
        {
            get => _isAnalysing;
            set => SetProperty(ref _isAnalysing, value);
        }

        private int _seriesCount;
        public int SeriesCount
        {
            get => _seriesCount;
            set => SetProperty(ref _seriesCount, value);
        }

        private int _totalPoints;
        public int TotalPoints
        {
            get => _totalPoints;
            set => SetProperty(ref _totalPoints, value);
        }

        private string _summaryText = "";
        public string SummaryText
        {
            get => _summaryText;
            set => SetProperty(ref _summaryText, value);
        }

        // ── Commands ────────────────────────────────────────────────────

        public ICommand RunChecksCommand { get; }
        public ICommand RefreshCommand { get; }

        /// <summary>
        /// Raised to ask the AddIn layer to extract the selection and run checks.
        /// </summary>
        public event Action RunChecksRequested;

        // ── Constructor ─────────────────────────────────────────────────

        public DataReadinessViewModel()
        {
            RunChecksCommand = new RelayCommand(
                () => RunChecksRequested?.Invoke(),
                () => !IsAnalysing);

            RefreshCommand = new RelayCommand(
                () => RunChecksRequested?.Invoke(),
                () => !IsAnalysing);
        }

        // ── Public API (called from AddIn layer) ────────────────────────

        /// <summary>
        /// Populate the readiness report from externally-computed checks.
        /// </summary>
        public void ShowResults(int seriesCount, int totalPoints,
            System.Collections.Generic.IEnumerable<ReadinessCheckItem> checks)
        {
            SeriesCount = seriesCount;
            TotalPoints = totalPoints;
            Checks.Clear();

            int totalWeight = 0;
            int earnedWeight = 0;

            foreach (var check in checks)
            {
                Checks.Add(check);
                int weight = 1;
                totalWeight += weight;
                switch (check.Status)
                {
                    case "Pass": earnedWeight += weight; break;
                    case "Warning": earnedWeight += (int)(weight * 0.5); break;
                }
            }

            OverallScore = totalWeight > 0 ? (int)Math.Round(100.0 * earnedWeight / totalWeight) : 0;
            HasRun = true;
            IsAnalysing = false;

            SummaryText = $"{seriesCount} series, {totalPoints} total points. " +
                          $"{Checks.Count} checks performed.";
        }

        /// <summary>
        /// Run a simple built-in assessment (for when the AddIn layer is not connected).
        /// </summary>
        public void RunBuiltInChecks()
        {
            IsAnalysing = true;

            var checks = new System.Collections.Generic.List<ReadinessCheckItem>
            {
                new ReadinessCheckItem
                {
                    CheckName = "Selection exists",
                    Status = "Warning",
                    Detail = "No Excel selection detected.",
                    Suggestion = "Select data columns in Excel, then click Refresh."
                },
                new ReadinessCheckItem
                {
                    CheckName = "Minimum length",
                    Status = "Warning",
                    Detail = "Need at least 20 observations for most techniques.",
                    Suggestion = "Select a range with at least 20 numeric rows."
                },
                new ReadinessCheckItem
                {
                    CheckName = "Missing data",
                    Status = "Pass",
                    Detail = "No missing data check can be performed without a selection.",
                    Suggestion = ""
                },
                new ReadinessCheckItem
                {
                    CheckName = "Numeric content",
                    Status = "Warning",
                    Detail = "Unable to verify numeric content without selection.",
                    Suggestion = "Ensure selected columns contain numeric values."
                },
                new ReadinessCheckItem
                {
                    CheckName = "Constant series",
                    Status = "Pass",
                    Detail = "Cannot check for constant series without data.",
                    Suggestion = ""
                },
                new ReadinessCheckItem
                {
                    CheckName = "Time index available",
                    Status = "Warning",
                    Detail = "No time index column detected adjacent to selection.",
                    Suggestion = "Place a date/time column immediately left of your data."
                },
            };

            ShowResults(0, 0, checks);
        }
    }
}
