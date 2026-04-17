using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    // ── Lightweight models local to the UI layer ────────────────────────

    public class TechniqueCategory
    {
        public string Name { get; set; }
        public int Count { get; set; }
    }

    public class TechniqueItem
    {
        public string Id { get; set; }
        public string Name { get; set; }
        public string Category { get; set; }
        public string Summary { get; set; }
        public string Description { get; set; }
        public bool SupportsAutoUdf { get; set; }
        public string AutoUdfName { get; set; }
        public int MinSeries { get; set; }
        public int? MaxSeries { get; set; }
        public List<string> Tags { get; set; } = new List<string>();
        public List<string> Presets { get; set; } = new List<string>();
        public List<TechniqueParameterItem> Parameters { get; set; } = new List<TechniqueParameterItem>();
        public List<string> OutputTables { get; set; } = new List<string>();
    }

    public class TechniqueParameterItem : ViewModelBase
    {
        public string Name { get; set; }
        public string Label { get; set; }
        public string Type { get; set; }
        public object Default { get; set; }
        public bool Required { get; set; }
        public bool Advanced { get; set; }
        public string Description { get; set; }
        public List<string> Options { get; set; }

        private object _currentValue;
        public object CurrentValue
        {
            get => _currentValue ?? Default;
            set => _currentValue = value;
        }

        // ── Typed accessors used by the Run pane XAML ───────────────────
        // The RunView binds BoolValue / StringValue to its CheckBox /
        // ComboBox / TextBox controls, and selects which control to show
        // based on IsBool / IsDropdown / IsTextInput.

        private bool _boolValue;
        public bool BoolValue
        {
            get => _boolValue;
            set => SetProperty(ref _boolValue, value);
        }

        private string _stringValue = "";
        public string StringValue
        {
            get => _stringValue;
            set => SetProperty(ref _stringValue, value);
        }

        public bool IsBool =>
            string.Equals(Type, "bool", StringComparison.OrdinalIgnoreCase);
        public bool IsDropdown =>
            Options != null && Options.Count > 0 && !IsBool;
        public bool IsTextInput =>
            !IsBool && (Options == null || Options.Count == 0);

        /// <summary>
        /// Current parameter value packed into the object the engine's
        /// RunRequest.Params dictionary expects.
        /// </summary>
        public object OutputValue
        {
            get
            {
                if (IsBool) return _boolValue;
                if (string.Equals(Type, "int", StringComparison.OrdinalIgnoreCase))
                {
                    if (int.TryParse(_stringValue, out var i)) return i;
                    return _stringValue;
                }
                if (string.Equals(Type, "float", StringComparison.OrdinalIgnoreCase) ||
                    string.Equals(Type, "double", StringComparison.OrdinalIgnoreCase))
                {
                    if (double.TryParse(_stringValue, out var d)) return d;
                    return _stringValue;
                }
                return _stringValue;
            }
        }
    }

    /// <summary>
    /// ViewModel for the Technique Explorer view. Manages categories, search/filtering,
    /// technique details, and run/insert commands.
    /// </summary>
    public class TechniqueExplorerViewModel : ViewModelBase
    {
        // ── Events ──────────────────────────────────────────────────────

        public event Action<string> RunRequested;
        public event Action<string> InsertAutoFormulaRequested;
        public event Action<string> InsertThoroughFormulaRequested;
        public event Action<string> NavigateToRunRequested;

        // ── Collections ─────────────────────────────────────────────────

        public ObservableCollection<TechniqueCategory> Categories { get; }
            = new ObservableCollection<TechniqueCategory>();

        public ObservableCollection<TechniqueItem> FilteredTechniques { get; }
            = new ObservableCollection<TechniqueItem>();

        // Master list loaded from catalog
        private List<TechniqueItem> _allTechniques = new List<TechniqueItem>();

        // ── Selected state ──────────────────────────────────────────────

        private TechniqueCategory _selectedCategory;
        public TechniqueCategory SelectedCategory
        {
            get => _selectedCategory;
            set
            {
                if (SetProperty(ref _selectedCategory, value))
                    ApplyFilter();
            }
        }

        private TechniqueItem _selectedTechnique;
        public TechniqueItem SelectedTechnique
        {
            get => _selectedTechnique;
            set
            {
                if (SetProperty(ref _selectedTechnique, value))
                {
                    OnPropertyChanged(nameof(HasSelectedTechnique));
                    OnPropertyChanged(nameof(SelectedTechniqueDescription));
                    OnPropertyChanged(nameof(CanInsertAuto));
                    OnPropertyChanged(nameof(AutoUdfExample));
                    OnPropertyChanged(nameof(ThoroughUdfExample));
                    OnPropertyChanged(nameof(SelectedTechniqueSeriesInfo));
                    OnPropertyChanged(nameof(SelectedTechniqueOutputInfo));
                }
            }
        }

        public bool HasSelectedTechnique => _selectedTechnique != null;

        public string SelectedTechniqueDescription =>
            _selectedTechnique?.Description ?? string.Empty;

        public bool CanInsertAuto =>
            _selectedTechnique?.SupportsAutoUdf == true;

        public string AutoUdfExample
        {
            get
            {
                if (_selectedTechnique == null || !_selectedTechnique.SupportsAutoUdf)
                    return string.Empty;
                return $"=TSL.AUTO(\"{_selectedTechnique.Id}\", A2:A100)";
            }
        }

        public string ThoroughUdfExample
        {
            get
            {
                if (_selectedTechnique == null) return string.Empty;
                return $"=TSL.THOROUGH(\"{_selectedTechnique.Id}\", A2:A100)";
            }
        }

        public string SelectedTechniqueSeriesInfo
        {
            get
            {
                if (_selectedTechnique == null) return string.Empty;
                var min = _selectedTechnique.MinSeries;
                var max = _selectedTechnique.MaxSeries;
                if (max.HasValue)
                    return $"Requires {min}-{max.Value} series";
                return min == 1 ? "Single or multiple series" : $"Requires at least {min} series";
            }
        }

        public string SelectedTechniqueOutputInfo
        {
            get
            {
                if (_selectedTechnique == null || _selectedTechnique.OutputTables.Count == 0)
                    return string.Empty;
                return "Output: " + string.Join(", ", _selectedTechnique.OutputTables);
            }
        }

        private string _searchQuery = string.Empty;
        public string SearchQuery
        {
            get => _searchQuery;
            set
            {
                if (SetProperty(ref _searchQuery, value))
                    ApplyFilter();
            }
        }

        private string _currentPreset = "Balanced";
        public string CurrentPreset
        {
            get => _currentPreset;
            set => SetProperty(ref _currentPreset, value);
        }

        private bool _showAdvancedParams;
        public bool ShowAdvancedParams
        {
            get => _showAdvancedParams;
            set => SetProperty(ref _showAdvancedParams, value);
        }

        // ── Commands ────────────────────────────────────────────────────

        public ICommand RunCommand { get; }
        public ICommand InsertAutoFormulaCommand { get; }
        public ICommand InsertThoroughFormulaCommand { get; }
        public ICommand OpenRunViewCommand { get; }
        public ICommand ClearSearchCommand { get; }
        public ICommand ShowAllCategoriesCommand { get; }
        public ICommand ToggleAdvancedCommand { get; }

        // ── Constructor ─────────────────────────────────────────────────

        public TechniqueExplorerViewModel()
        {
            RunCommand = new RelayCommand(
                () => { if (_selectedTechnique != null) RunRequested?.Invoke(_selectedTechnique.Id); },
                () => _selectedTechnique != null);

            InsertAutoFormulaCommand = new RelayCommand(
                () => { if (_selectedTechnique != null) InsertAutoFormulaRequested?.Invoke(_selectedTechnique.Id); },
                () => _selectedTechnique?.SupportsAutoUdf == true);

            InsertThoroughFormulaCommand = new RelayCommand(
                () => { if (_selectedTechnique != null) InsertThoroughFormulaRequested?.Invoke(_selectedTechnique.Id); },
                () => _selectedTechnique != null);

            OpenRunViewCommand = new RelayCommand(
                () => { if (_selectedTechnique != null) NavigateToRunRequested?.Invoke(_selectedTechnique.Id); },
                () => _selectedTechnique != null);

            ClearSearchCommand = new RelayCommand(() => SearchQuery = string.Empty);

            ShowAllCategoriesCommand = new RelayCommand(() => SelectedCategory = null);

            ToggleAdvancedCommand = new RelayCommand(() => ShowAdvancedParams = !ShowAdvancedParams);

            // Load built-in sample catalog for design-time / standalone
            LoadBuiltInCatalog();
        }

        // ── Public API ──────────────────────────────────────────────────

        /// <summary>
        /// Load techniques from the AddIn catalog. Called by the AddIn layer
        /// after TechniqueCatalogService is ready.
        /// </summary>
        public void LoadTechniques(IEnumerable<TechniqueItem> techniques)
        {
            _allTechniques = techniques.ToList();
            RebuildCategories();
            ApplyFilter();
        }

        /// <summary>
        /// Select a technique by its ID (used for NavigateToTechnique).
        /// </summary>
        public void SelectTechniqueById(string techniqueId)
        {
            if (string.IsNullOrEmpty(techniqueId)) return;

            var match = _allTechniques.FirstOrDefault(
                t => string.Equals(t.Id, techniqueId, StringComparison.OrdinalIgnoreCase));

            if (match != null)
            {
                // Clear category filter so the technique is visible
                SelectedCategory = null;
                SearchQuery = string.Empty;
                ApplyFilter();
                SelectedTechnique = FilteredTechniques.FirstOrDefault(
                    t => string.Equals(t.Id, techniqueId, StringComparison.OrdinalIgnoreCase));
            }
        }

        // ── Private helpers ─────────────────────────────────────────────

        private void RebuildCategories()
        {
            Categories.Clear();
            var groups = _allTechniques
                .GroupBy(t => t.Category ?? "Other")
                .OrderBy(g => g.Key);

            foreach (var g in groups)
            {
                Categories.Add(new TechniqueCategory { Name = g.Key, Count = g.Count() });
            }
        }

        private void ApplyFilter()
        {
            FilteredTechniques.Clear();

            IEnumerable<TechniqueItem> source = _allTechniques;

            // Category filter
            if (_selectedCategory != null)
            {
                source = source.Where(t =>
                    string.Equals(t.Category, _selectedCategory.Name, StringComparison.OrdinalIgnoreCase));
            }

            // Search filter
            if (!string.IsNullOrWhiteSpace(_searchQuery))
            {
                var q = _searchQuery.ToLowerInvariant();
                source = source.Where(t =>
                    (t.Name?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Summary?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Id?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Tags?.Any(tag => tag.ToLowerInvariant().Contains(q)) ?? false));
            }

            foreach (var t in source)
            {
                FilteredTechniques.Add(t);
            }

            // Preserve selection if still in filtered list, otherwise select first
            if (_selectedTechnique != null && !FilteredTechniques.Contains(_selectedTechnique))
            {
                SelectedTechnique = FilteredTechniques.FirstOrDefault();
            }
            else if (_selectedTechnique == null && FilteredTechniques.Count > 0)
            {
                SelectedTechnique = FilteredTechniques.First();
            }
        }

        /// <summary>
        /// Provides a built-in sample catalog so the UI is usable before the
        /// AddIn layer loads the real catalog from disk.
        /// </summary>
        private void LoadBuiltInCatalog()
        {
            _allTechniques = new List<TechniqueItem>
            {
                new TechniqueItem
                {
                    Id = "stl_decompose",
                    Name = "STL Decomposition",
                    Category = "Decomposition",
                    Summary = "Seasonal-Trend decomposition using LOESS. Separates a time series into trend, seasonal, and residual components.",
                    Description = "STL (Seasonal and Trend decomposition using LOESS) is a robust method for decomposing a time series into three components:\n\n" +
                                  "- Trend: The long-term progression of the series\n" +
                                  "- Seasonal: The repeating short-term cycle\n" +
                                  "- Residual: The remainder after removing trend and seasonality\n\n" +
                                  "AUTO mode: Uses automatic period detection and default LOESS windows.\n" +
                                  "THOROUGH mode: Optimises LOESS bandwidths and tests multiple seasonal periods.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.STL",
                    MinSeries = 1,
                    MaxSeries = 1,
                    Tags = new List<string> { "decomposition", "seasonal", "trend" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "Components", "Diagnostics" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "period", Label = "Seasonal Period", Type = "int", Default = 0, Required = false, Description = "0 = auto-detect" },
                        new TechniqueParameterItem { Name = "robust", Label = "Robust Fitting", Type = "bool", Default = true, Required = false, Description = "Use robust (outlier-resistant) fitting" },
                    }
                },
                new TechniqueItem
                {
                    Id = "auto_arima",
                    Name = "Auto ARIMA Forecast",
                    Category = "Forecasting",
                    Summary = "Automatic ARIMA model selection and forecasting with confidence intervals.",
                    Description = "Auto ARIMA automatically selects the best ARIMA(p,d,q)(P,D,Q)m model by searching over possible orders and choosing the model with the lowest information criterion (AICc).\n\n" +
                                  "AUTO mode: Fast stepwise search with default parameters.\n" +
                                  "THOROUGH mode: Exhaustive grid search over a wider parameter space, includes cross-validation.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.ARIMA",
                    MinSeries = 1,
                    MaxSeries = 1,
                    Tags = new List<string> { "forecasting", "arima", "prediction" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "Forecast", "ModelSummary", "Residuals" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "horizon", Label = "Forecast Horizon", Type = "int", Default = 12, Required = false, Description = "Number of periods to forecast" },
                        new TechniqueParameterItem { Name = "seasonal", Label = "Seasonal", Type = "bool", Default = true, Required = false, Description = "Include seasonal component" },
                        new TechniqueParameterItem { Name = "ci_level", Label = "Confidence Level", Type = "float", Default = 0.95, Required = false, Advanced = true, Description = "Confidence interval level (0-1)" },
                    }
                },
                new TechniqueItem
                {
                    Id = "granger_causality",
                    Name = "Granger Causality Test",
                    Category = "Causality & Correlation",
                    Summary = "Tests whether one time series is useful in forecasting another.",
                    Description = "The Granger Causality test determines whether lagged values of one series (X) contain information that helps predict another series (Y), beyond what is contained in lagged values of Y alone.\n\n" +
                                  "AUTO mode: Tests a default range of lags (1-4) with standard F-test.\n" +
                                  "THOROUGH mode: Uses BIC to select optimal lag length, includes Toda-Yamamoto procedure for non-stationary data.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.GRANGER",
                    MinSeries = 2,
                    MaxSeries = 2,
                    Tags = new List<string> { "causality", "granger", "bivariate" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "TestResults", "LagSelection" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "max_lag", Label = "Max Lag", Type = "int", Default = 4, Required = false, Description = "Maximum lag order to test" },
                    }
                },
                new TechniqueItem
                {
                    Id = "prewhitened_ccf_lag",
                    Name = "Lead-Lag Finder (CCF)",
                    Category = "Causality & Correlation",
                    Summary = "Finds the lead-lag relationship between two series using prewhitened cross-correlation.",
                    Description = "Uses prewhitened cross-correlation to identify which series leads or lags the other and by how many periods. Prewhitening removes autocorrelation first, producing more reliable CCF estimates.\n\n" +
                                  "AUTO mode: Uses auto.arima prewhitening filter.\n" +
                                  "THOROUGH mode: Compares multiple prewhitening approaches and provides bootstrap confidence bands.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.CCF",
                    MinSeries = 2,
                    MaxSeries = 2,
                    Tags = new List<string> { "correlation", "cross-correlation", "lead-lag", "ccf" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "CCFValues", "PeakLags" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "max_lag", Label = "Max Lag", Type = "int", Default = 20, Required = false, Description = "Maximum lag to compute CCF for" },
                    }
                },
                new TechniqueItem
                {
                    Id = "stl_esd_anomaly",
                    Name = "STL + ESD Anomaly Detection",
                    Category = "Anomaly Detection",
                    Summary = "Detects anomalies by combining STL decomposition with Extreme Studentized Deviate test.",
                    Description = "First decomposes the series via STL to remove trend and seasonality, then applies the Generalized ESD test on the residual component to flag statistical outliers.\n\n" +
                                  "AUTO mode: Uses default STL settings and ESD alpha = 0.05.\n" +
                                  "THOROUGH mode: Tunes STL bandwidths, tests multiple significance levels, and cross-validates anomaly thresholds.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.ANOMALY",
                    MinSeries = 1,
                    MaxSeries = 1,
                    Tags = new List<string> { "anomaly", "outlier", "esd" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "Anomalies", "Components" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "alpha", Label = "Significance Level", Type = "float", Default = 0.05, Required = false, Description = "ESD test significance level" },
                        new TechniqueParameterItem { Name = "max_anomalies_pct", Label = "Max Anomaly %", Type = "float", Default = 0.10, Required = false, Advanced = true, Description = "Max fraction of points that can be anomalies" },
                    }
                },
                new TechniqueItem
                {
                    Id = "adf_kpss_stationarity",
                    Name = "Stationarity Tests (ADF + KPSS)",
                    Category = "Statistical Tests",
                    Summary = "Joint ADF and KPSS testing to determine stationarity and required differencing.",
                    Description = "Runs both the Augmented Dickey-Fuller (ADF) test and the Kwiatkowski-Phillips-Schmidt-Shin (KPSS) test. Interpreting them jointly resolves ambiguity:\n\n" +
                                  "- Both conclude stationary: series is stationary\n" +
                                  "- Both conclude non-stationary: series has a unit root\n" +
                                  "- ADF rejects but KPSS does not: trend-stationary\n" +
                                  "- ADF fails but KPSS rejects: difference-stationary\n\n" +
                                  "AUTO mode: Standard ADF + KPSS with automatic lag selection.\n" +
                                  "THOROUGH mode: Includes Phillips-Perron, Zivot-Andrews breakpoint test, and HEGY seasonal unit root test.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.STATIONARY",
                    MinSeries = 1,
                    MaxSeries = null,
                    Tags = new List<string> { "stationarity", "unit-root", "adf", "kpss" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "TestResults" },
                    Parameters = new List<TechniqueParameterItem>()
                },
                new TechniqueItem
                {
                    Id = "ets_forecast",
                    Name = "Exponential Smoothing (ETS)",
                    Category = "Forecasting",
                    Summary = "Error-Trend-Seasonal (ETS) framework with automatic model selection.",
                    Description = "ETS models cover a family of exponential smoothing methods including simple, Holt's linear, and Holt-Winters seasonal smoothing. Model selection is automatic based on information criteria.\n\n" +
                                  "AUTO mode: Automatic model selection from the ETS family.\n" +
                                  "THOROUGH mode: Full ETS grid search including damped trends and multiplicative components.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.ETS",
                    MinSeries = 1,
                    MaxSeries = 1,
                    Tags = new List<string> { "forecasting", "ets", "exponential-smoothing" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "Forecast", "ModelSummary" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "horizon", Label = "Forecast Horizon", Type = "int", Default = 12, Required = false, Description = "Number of periods to forecast" },
                    }
                },
                new TechniqueItem
                {
                    Id = "rolling_correlation",
                    Name = "Rolling Correlation",
                    Category = "Causality & Correlation",
                    Summary = "Computes time-varying correlation between two series using a rolling window.",
                    Description = "Calculates the Pearson correlation coefficient over a rolling window, revealing how the relationship between two series changes over time.\n\n" +
                                  "AUTO mode: Default window size based on data length.\n" +
                                  "THOROUGH mode: Tests multiple window sizes and includes DCC-GARCH dynamic correlation.",
                    SupportsAutoUdf = true,
                    AutoUdfName = "TSL.AUTO.ROLLCORR",
                    MinSeries = 2,
                    MaxSeries = 2,
                    Tags = new List<string> { "correlation", "rolling", "time-varying" },
                    Presets = new List<string> { "Fast", "Balanced", "Thorough" },
                    OutputTables = new List<string> { "RollingCorrelation" },
                    Parameters = new List<TechniqueParameterItem>
                    {
                        new TechniqueParameterItem { Name = "window", Label = "Window Size", Type = "int", Default = 30, Required = false, Description = "Rolling window size in periods" },
                    }
                },
            };

            RebuildCategories();
            ApplyFilter();
        }
    }
}
