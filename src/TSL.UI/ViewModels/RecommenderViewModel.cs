using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// A single question in the recommender wizard.
    /// </summary>
    public class RecommenderQuestion
    {
        public int StepNumber { get; set; }
        public string QuestionText { get; set; }
        public string HelpText { get; set; }
        public List<RecommenderOption> Options { get; set; } = new List<RecommenderOption>();
    }

    /// <summary>
    /// An answer option for a recommender question.
    /// </summary>
    public class RecommenderOption
    {
        public string Label { get; set; }
        public string Value { get; set; }
        public string Description { get; set; }
    }

    /// <summary>
    /// A technique recommendation produced by the wizard.
    /// </summary>
    public class RecommendationResult : ViewModelBase
    {
        public int Rank { get; set; }
        public string TechniqueId { get; set; }
        public string TechniqueName { get; set; }
        public string Reason { get; set; }
        public int MatchScore { get; set; }

        public string RankDisplay => $"#{Rank}";
        public string ScoreDisplay => $"{MatchScore}% match";
    }

    /// <summary>
    /// ViewModel for the 5-7 question recommender wizard. Each step presents
    /// a question with radio-button options. After all questions, the top 3
    /// techniques are displayed with explanations.
    /// </summary>
    public class RecommenderViewModel : ViewModelBase
    {
        // ── Events ──────────────────────────────────────────────────────

        public event Action<string> OpenTechniqueRequested;

        // ── Collections ─────────────────────────────────────────────────

        public ObservableCollection<RecommendationResult> Recommendations { get; }
            = new ObservableCollection<RecommendationResult>();

        // ── Wizard state ────────────────────────────────────────────────

        private readonly List<RecommenderQuestion> _questions;
        private readonly Dictionary<int, string> _answers = new Dictionary<int, string>();

        private int _currentStep;
        public int CurrentStep
        {
            get => _currentStep;
            set
            {
                if (SetProperty(ref _currentStep, value))
                {
                    OnPropertyChanged(nameof(CurrentQuestion));
                    OnPropertyChanged(nameof(StepDisplay));
                    OnPropertyChanged(nameof(CanGoBack));
                    OnPropertyChanged(nameof(IsOnResults));
                    OnPropertyChanged(nameof(IsOnQuestion));
                    OnPropertyChanged(nameof(NextButtonText));
                    OnPropertyChanged(nameof(SelectedOption));
                }
            }
        }

        public int TotalSteps => _questions.Count;

        public RecommenderQuestion CurrentQuestion =>
            _currentStep >= 0 && _currentStep < _questions.Count ? _questions[_currentStep] : null;

        public string StepDisplay => IsOnResults
            ? "Results"
            : $"Step {_currentStep + 1} of {TotalSteps}";

        public bool CanGoBack => _currentStep > 0;
        public bool IsOnResults => _currentStep >= _questions.Count;
        public bool IsOnQuestion => !IsOnResults;

        public string NextButtonText =>
            _currentStep >= _questions.Count - 1 ? "Get Recommendations" : "Next";

        public string SelectedOption
        {
            get => _answers.ContainsKey(_currentStep) ? _answers[_currentStep] : null;
            set
            {
                if (value != null)
                {
                    _answers[_currentStep] = value;
                    OnPropertyChanged();
                }
            }
        }

        // ── Commands ────────────────────────────────────────────────────

        public ICommand NextCommand { get; }
        public ICommand BackCommand { get; }
        public ICommand RestartCommand { get; }
        public ICommand OpenTechniqueCommand { get; }
        public ICommand SelectOptionCommand { get; }

        // ── Constructor ─────────────────────────────────────────────────

        public RecommenderViewModel()
        {
            _questions = BuildQuestions();

            NextCommand = new RelayCommand(OnNext, () => SelectedOption != null || IsOnResults);
            BackCommand = new RelayCommand(OnBack, () => CanGoBack);
            RestartCommand = new RelayCommand(OnRestart);
            OpenTechniqueCommand = new RelayCommand(
                (param) => OpenTechniqueRequested?.Invoke(param as string),
                (param) => param is string s && !string.IsNullOrEmpty(s));
            SelectOptionCommand = new RelayCommand(
                (param) => { if (param is string s) SelectedOption = s; });

            _currentStep = 0;
        }

        // ── Navigation ──────────────────────────────────────────────────

        private void OnNext()
        {
            if (IsOnResults) return;

            if (_currentStep >= _questions.Count - 1)
            {
                // Compute recommendations
                ComputeRecommendations();
                CurrentStep = _questions.Count; // move to results
            }
            else
            {
                CurrentStep++;
            }
        }

        private void OnBack()
        {
            if (_currentStep > 0)
            {
                if (IsOnResults)
                    CurrentStep = _questions.Count - 1;
                else
                    CurrentStep--;
            }
        }

        private void OnRestart()
        {
            _answers.Clear();
            Recommendations.Clear();
            CurrentStep = 0;
        }

        // ── Recommendation engine ───────────────────────────────────────

        private void ComputeRecommendations()
        {
            Recommendations.Clear();

            string goal = GetAnswer(0, "describe");
            string seasonality = GetAnswer(1, "unknown");
            string missingness = GetAnswer(2, "none");
            string irregularTime = GetAnswer(3, "no");
            string interpretability = GetAnswer(4, "high");
            string multivariate = GetAnswer(5, "no");
            string dataLength = GetAnswer(6, "medium");

            // Score each built-in technique against the answers.
            // This is a simple rule-based scoring system.
            var candidates = new List<(string id, string name, int score, string reason)>();

            // STL Decomposition
            {
                int score = 50;
                string reason = "Good default for understanding series structure.";
                if (goal == "describe" || goal == "decompose") { score += 30; reason = "Ideal for decomposition into trend + seasonal + residual."; }
                if (seasonality == "yes" || seasonality == "unknown") score += 10;
                if (interpretability == "high") score += 10;
                if (multivariate == "no") score += 5;
                candidates.Add(("stl_decompose", "STL Decomposition", Math.Min(score, 100), reason));
            }

            // Auto ARIMA
            {
                int score = 40;
                string reason = "Versatile forecasting with automatic model selection.";
                if (goal == "forecast") { score += 35; reason = "Best-in-class automatic forecasting model."; }
                if (seasonality == "yes") score += 10;
                if (dataLength == "long" || dataLength == "medium") score += 5;
                if (multivariate == "no") score += 5;
                candidates.Add(("auto_arima", "Auto ARIMA Forecast", Math.Min(score, 100), reason));
            }

            // ETS
            {
                int score = 35;
                string reason = "Exponential smoothing family for straightforward forecasting.";
                if (goal == "forecast") { score += 30; reason = "Excellent for seasonal and trended forecasting."; }
                if (seasonality == "yes") score += 10;
                if (dataLength == "short") score += 10;
                if (interpretability == "high") score += 5;
                if (multivariate == "no") score += 5;
                candidates.Add(("ets_forecast", "Exponential Smoothing (ETS)", Math.Min(score, 100), reason));
            }

            // Granger Causality
            {
                int score = 30;
                string reason = "Tests whether one series helps predict another.";
                if (goal == "causality" || goal == "relationship") { score += 35; reason = "Directly tests predictive causality between two series."; }
                if (multivariate == "yes") score += 15;
                if (dataLength == "long") score += 5;
                candidates.Add(("granger_causality", "Granger Causality Test", Math.Min(score, 100), reason));
            }

            // Lead-Lag Finder
            {
                int score = 30;
                string reason = "Identifies which series leads or lags.";
                if (goal == "relationship" || goal == "causality") { score += 30; reason = "Pinpoints the lead-lag timing between series."; }
                if (multivariate == "yes") score += 15;
                candidates.Add(("prewhitened_ccf_lag", "Lead-Lag Finder (CCF)", Math.Min(score, 100), reason));
            }

            // STL+ESD Anomaly
            {
                int score = 30;
                string reason = "Detects unusual observations in your data.";
                if (goal == "anomaly") { score += 40; reason = "Purpose-built for anomaly and outlier detection."; }
                if (seasonality == "yes") score += 10;
                if (multivariate == "no") score += 5;
                candidates.Add(("stl_esd_anomaly", "STL + ESD Anomaly Detection", Math.Min(score, 100), reason));
            }

            // Stationarity Tests
            {
                int score = 25;
                string reason = "Prerequisite test for many time series methods.";
                if (goal == "describe" || goal == "test") { score += 25; reason = "Essential diagnostic to check data properties."; }
                if (interpretability == "high") score += 10;
                candidates.Add(("adf_kpss_stationarity", "Stationarity Tests (ADF + KPSS)", Math.Min(score, 100), reason));
            }

            // Rolling Correlation
            {
                int score = 25;
                string reason = "Shows how correlation changes over time.";
                if (goal == "relationship") { score += 25; reason = "Reveals time-varying relationships between series."; }
                if (multivariate == "yes") score += 15;
                candidates.Add(("rolling_correlation", "Rolling Correlation", Math.Min(score, 100), reason));
            }

            // Sort by score descending, take top 3
            var top3 = candidates
                .OrderByDescending(c => c.score)
                .Take(3)
                .ToList();

            for (int i = 0; i < top3.Count; i++)
            {
                Recommendations.Add(new RecommendationResult
                {
                    Rank = i + 1,
                    TechniqueId = top3[i].id,
                    TechniqueName = top3[i].name,
                    MatchScore = top3[i].score,
                    Reason = top3[i].reason,
                });
            }
        }

        private string GetAnswer(int step, string fallback)
        {
            return _answers.ContainsKey(step) ? _answers[step] : fallback;
        }

        // ── Question definitions ────────────────────────────────────────

        private static List<RecommenderQuestion> BuildQuestions()
        {
            return new List<RecommenderQuestion>
            {
                new RecommenderQuestion
                {
                    StepNumber = 1,
                    QuestionText = "What is your primary goal?",
                    HelpText = "This helps us narrow down the right family of techniques.",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "Forecast future values", Value = "forecast", Description = "Predict what comes next in the series" },
                        new RecommenderOption { Label = "Describe / decompose the series", Value = "describe", Description = "Understand trend, seasonality, and patterns" },
                        new RecommenderOption { Label = "Detect anomalies / outliers", Value = "anomaly", Description = "Find unusual observations" },
                        new RecommenderOption { Label = "Test causality / relationships", Value = "causality", Description = "Does one series drive another?" },
                        new RecommenderOption { Label = "Explore relationships", Value = "relationship", Description = "Correlations and lead-lag dynamics" },
                        new RecommenderOption { Label = "Statistical testing", Value = "test", Description = "Unit root, stationarity, structural breaks" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 2,
                    QuestionText = "Does your data have seasonality?",
                    HelpText = "Seasonality means a repeating pattern at a fixed interval (e.g. monthly, weekly).",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "Yes, clear seasonal pattern", Value = "yes", Description = "The pattern repeats at a known interval" },
                        new RecommenderOption { Label = "Not sure / possibly", Value = "unknown", Description = "Let the technique auto-detect" },
                        new RecommenderOption { Label = "No seasonality", Value = "no", Description = "No repeating pattern" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 3,
                    QuestionText = "How much missing data does your series have?",
                    HelpText = "Missing values (blanks, #N/A) affect which methods are appropriate.",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "None or very little (<1%)", Value = "none", Description = "Data is essentially complete" },
                        new RecommenderOption { Label = "Some missing (1-10%)", Value = "some", Description = "Scattered gaps" },
                        new RecommenderOption { Label = "Significant missing (>10%)", Value = "significant", Description = "Large gaps or many missing values" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 4,
                    QuestionText = "Is your time index irregular?",
                    HelpText = "Irregular means observations are not equally spaced (e.g. business days only, event-driven).",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "No, regular spacing", Value = "no", Description = "Equal intervals between observations" },
                        new RecommenderOption { Label = "Yes, irregular spacing", Value = "yes", Description = "Unequal time gaps" },
                        new RecommenderOption { Label = "Not sure", Value = "unknown", Description = "Let the tool decide" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 5,
                    QuestionText = "How important is interpretability?",
                    HelpText = "Some methods produce easy-to-explain results; others are more of a black box.",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "Very important", Value = "high", Description = "I need to explain results to others" },
                        new RecommenderOption { Label = "Moderate", Value = "medium", Description = "A balance of accuracy and clarity" },
                        new RecommenderOption { Label = "Not important", Value = "low", Description = "Just give me the best accuracy" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 6,
                    QuestionText = "Do you have multiple related series?",
                    HelpText = "Some techniques can analyse relationships between two or more series simultaneously.",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "Just one series", Value = "no", Description = "Single univariate series" },
                        new RecommenderOption { Label = "Two series", Value = "yes", Description = "Bivariate analysis" },
                        new RecommenderOption { Label = "Three or more series", Value = "multi", Description = "Multivariate analysis" },
                    }
                },
                new RecommenderQuestion
                {
                    StepNumber = 7,
                    QuestionText = "How long is your time series?",
                    HelpText = "Series length affects which methods are statistically reliable.",
                    Options = new List<RecommenderOption>
                    {
                        new RecommenderOption { Label = "Short (< 50 observations)", Value = "short", Description = "Limited data" },
                        new RecommenderOption { Label = "Medium (50-500)", Value = "medium", Description = "Typical length" },
                        new RecommenderOption { Label = "Long (500+)", Value = "long", Description = "Plenty of data" },
                    }
                },
            };
        }
    }
}
