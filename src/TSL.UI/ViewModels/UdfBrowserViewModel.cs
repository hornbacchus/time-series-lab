using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// A single UDF entry displayed in the browser.
    /// </summary>
    public class UdfEntry
    {
        public string Name { get; set; }
        public string Category { get; set; }
        public string Signature { get; set; }
        public string Description { get; set; }
        public string Example { get; set; }
        public string ReturnType { get; set; }
        public List<UdfParameterInfo> Parameters { get; set; } = new List<UdfParameterInfo>();
    }

    /// <summary>
    /// Parameter information for a UDF.
    /// </summary>
    public class UdfParameterInfo
    {
        public string Name { get; set; }
        public string Type { get; set; }
        public string Description { get; set; }
        public bool Optional { get; set; }
    }

    /// <summary>
    /// ViewModel for the UDF Browser view. Displays a searchable list of all
    /// TSL UDFs with signatures, descriptions, examples, and an Insert button.
    /// </summary>
    public class UdfBrowserViewModel : ViewModelBase
    {
        // ── Collections ─────────────────────────────────────────────────

        private List<UdfEntry> _allUdfs = new List<UdfEntry>();

        public ObservableCollection<UdfEntry> FilteredUdfs { get; }
            = new ObservableCollection<UdfEntry>();

        public ObservableCollection<string> Categories { get; }
            = new ObservableCollection<string>();

        // ── Properties ──────────────────────────────────────────────────

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

        private string _selectedCategory;
        public string SelectedCategory
        {
            get => _selectedCategory;
            set
            {
                if (SetProperty(ref _selectedCategory, value))
                    ApplyFilter();
            }
        }

        private UdfEntry _selectedUdf;
        public UdfEntry SelectedUdf
        {
            get => _selectedUdf;
            set
            {
                if (SetProperty(ref _selectedUdf, value))
                {
                    OnPropertyChanged(nameof(HasSelectedUdf));
                    OnPropertyChanged(nameof(SelectedUdfDescription));
                    OnPropertyChanged(nameof(SelectedUdfExample));
                    OnPropertyChanged(nameof(SelectedUdfSignature));
                }
            }
        }

        public bool HasSelectedUdf => _selectedUdf != null;
        public string SelectedUdfDescription => _selectedUdf?.Description ?? string.Empty;
        public string SelectedUdfExample => _selectedUdf?.Example ?? string.Empty;
        public string SelectedUdfSignature => _selectedUdf?.Signature ?? string.Empty;

        // ── Commands ────────────────────────────────────────────────────

        public ICommand InsertFormulaCommand { get; }
        public ICommand CopyFormulaCommand { get; }
        public ICommand ClearSearchCommand { get; }
        public ICommand ShowAllCommand { get; }
        public ICommand SelectCategoryCommand { get; }

        /// <summary>
        /// Raised when the user clicks Insert. The AddIn layer inserts the formula
        /// into the active cell.
        /// </summary>
        public event Action<string> InsertFormulaRequested;

        /// <summary>
        /// Raised to copy a formula to the clipboard.
        /// </summary>
        public event Action<string> CopyFormulaRequested;

        // ── Constructor ─────────────────────────────────────────────────

        public UdfBrowserViewModel()
        {
            InsertFormulaCommand = new RelayCommand(
                () =>
                {
                    if (_selectedUdf != null)
                        InsertFormulaRequested?.Invoke(_selectedUdf.Example);
                },
                () => _selectedUdf != null);

            CopyFormulaCommand = new RelayCommand(
                () =>
                {
                    if (_selectedUdf != null)
                        CopyFormulaRequested?.Invoke(_selectedUdf.Example);
                },
                () => _selectedUdf != null);

            ClearSearchCommand = new RelayCommand(() => SearchQuery = string.Empty);

            ShowAllCommand = new RelayCommand(() => SelectedCategory = null);

            SelectCategoryCommand = new RelayCommand(
                (param) => SelectedCategory = param as string);

            LoadBuiltInUdfs();
        }

        // ── Public API ──────────────────────────────────────────────────

        /// <summary>
        /// Load UDFs from the AddIn layer (replaces built-in list).
        /// </summary>
        public void LoadUdfs(IEnumerable<UdfEntry> udfs)
        {
            _allUdfs = udfs.ToList();
            RebuildCategories();
            ApplyFilter();
        }

        // ── Private helpers ─────────────────────────────────────────────

        private void RebuildCategories()
        {
            Categories.Clear();
            Categories.Add("All");
            foreach (var cat in _allUdfs.Select(u => u.Category).Distinct().OrderBy(c => c))
            {
                Categories.Add(cat);
            }
        }

        private void ApplyFilter()
        {
            FilteredUdfs.Clear();

            IEnumerable<UdfEntry> source = _allUdfs;

            if (!string.IsNullOrEmpty(_selectedCategory) && _selectedCategory != "All")
            {
                source = source.Where(u =>
                    string.Equals(u.Category, _selectedCategory, StringComparison.OrdinalIgnoreCase));
            }

            if (!string.IsNullOrWhiteSpace(_searchQuery))
            {
                var q = _searchQuery.ToLowerInvariant();
                source = source.Where(u =>
                    (u.Name?.ToLowerInvariant().Contains(q) ?? false) ||
                    (u.Description?.ToLowerInvariant().Contains(q) ?? false) ||
                    (u.Signature?.ToLowerInvariant().Contains(q) ?? false));
            }

            foreach (var u in source)
                FilteredUdfs.Add(u);

            if (_selectedUdf != null && !FilteredUdfs.Contains(_selectedUdf))
                SelectedUdf = FilteredUdfs.FirstOrDefault();
            else if (_selectedUdf == null && FilteredUdfs.Count > 0)
                SelectedUdf = FilteredUdfs.First();
        }

        private void LoadBuiltInUdfs()
        {
            _allUdfs = new List<UdfEntry>
            {
                new UdfEntry
                {
                    Name = "TSL.AUTO",
                    Category = "Auto Functions",
                    Signature = "TSL.AUTO(technique_id, data_range, [options])",
                    Description = "Run any technique in AUTO mode. Uses sensible defaults and automatic parameter selection. " +
                                  "Results spill into adjacent cells. Fast and suitable for most use cases.",
                    Example = "=TSL.AUTO(\"stl_decompose\", A2:A100)",
                    ReturnType = "Dynamic array",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "technique_id", Type = "String", Description = "Technique identifier (e.g. \"auto_arima\")", Optional = false },
                        new UdfParameterInfo { Name = "data_range", Type = "Range", Description = "One or more columns of numeric data", Optional = false },
                        new UdfParameterInfo { Name = "options", Type = "String", Description = "Optional JSON parameter overrides", Optional = true },
                    }
                },
                new UdfEntry
                {
                    Name = "TSL.THOROUGH",
                    Category = "Thorough Functions",
                    Signature = "TSL.THOROUGH(technique_id, data_range, [options], [trigger])",
                    Description = "Run any technique in THOROUGH mode. Performs exhaustive parameter search, cross-validation, " +
                                  "and additional diagnostics. Slower but more rigorous. Use the trigger parameter to force recalculation.",
                    Example = "=TSL.THOROUGH(\"auto_arima\", A2:A100, , TSL.TRIGGER())",
                    ReturnType = "Dynamic array",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "technique_id", Type = "String", Description = "Technique identifier", Optional = false },
                        new UdfParameterInfo { Name = "data_range", Type = "Range", Description = "One or more columns of numeric data", Optional = false },
                        new UdfParameterInfo { Name = "options", Type = "String", Description = "Optional JSON parameter overrides", Optional = true },
                        new UdfParameterInfo { Name = "trigger", Type = "Any", Description = "Volatile trigger to force recalculation (use TSL.TRIGGER())", Optional = true },
                    }
                },
                new UdfEntry
                {
                    Name = "TSL.TRIGGER",
                    Category = "Utility Functions",
                    Signature = "TSL.TRIGGER()",
                    Description = "Returns a volatile trigger value that increments each time the ribbon Re-run button is pressed. " +
                                  "Pass this as the last argument to TSL.THOROUGH to control when recalculation happens.",
                    Example = "=TSL.TRIGGER()",
                    ReturnType = "Integer",
                    Parameters = new List<UdfParameterInfo>()
                },
                new UdfEntry
                {
                    Name = "TSL.VERSION",
                    Category = "Utility Functions",
                    Signature = "TSL.VERSION()",
                    Description = "Returns the current version of the Time Series Lab add-in and engine.",
                    Example = "=TSL.VERSION()",
                    ReturnType = "String",
                    Parameters = new List<UdfParameterInfo>()
                },
                new UdfEntry
                {
                    Name = "TSL.AUTO.STL",
                    Category = "Auto Functions",
                    Signature = "TSL.AUTO.STL(data_range, [period])",
                    Description = "Shorthand for TSL.AUTO(\"stl_decompose\", ...). Decomposes a series into trend, seasonal, and residual components.",
                    Example = "=TSL.AUTO.STL(B2:B200)",
                    ReturnType = "Dynamic array (Trend, Seasonal, Residual columns)",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "data_range", Type = "Range", Description = "Single column of numeric data", Optional = false },
                        new UdfParameterInfo { Name = "period", Type = "Integer", Description = "Seasonal period (0 = auto-detect)", Optional = true },
                    }
                },
                new UdfEntry
                {
                    Name = "TSL.AUTO.ARIMA",
                    Category = "Auto Functions",
                    Signature = "TSL.AUTO.ARIMA(data_range, [horizon], [seasonal])",
                    Description = "Shorthand for TSL.AUTO(\"auto_arima\", ...). Produces forecasts with confidence intervals.",
                    Example = "=TSL.AUTO.ARIMA(B2:B200, 12)",
                    ReturnType = "Dynamic array (Forecast, Lower CI, Upper CI columns)",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "data_range", Type = "Range", Description = "Single column of numeric data", Optional = false },
                        new UdfParameterInfo { Name = "horizon", Type = "Integer", Description = "Forecast horizon (default 12)", Optional = true },
                        new UdfParameterInfo { Name = "seasonal", Type = "Boolean", Description = "Include seasonal component (default TRUE)", Optional = true },
                    }
                },
                new UdfEntry
                {
                    Name = "TSL.AUTO.GRANGER",
                    Category = "Auto Functions",
                    Signature = "TSL.AUTO.GRANGER(x_range, y_range, [max_lag])",
                    Description = "Shorthand for TSL.AUTO(\"granger_causality\", ...). Tests whether X Granger-causes Y.",
                    Example = "=TSL.AUTO.GRANGER(A2:A100, B2:B100)",
                    ReturnType = "Dynamic array (Lag, F-statistic, p-value columns)",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "x_range", Type = "Range", Description = "Potential cause series", Optional = false },
                        new UdfParameterInfo { Name = "y_range", Type = "Range", Description = "Potential effect series", Optional = false },
                        new UdfParameterInfo { Name = "max_lag", Type = "Integer", Description = "Maximum lag to test (default 4)", Optional = true },
                    }
                },
                new UdfEntry
                {
                    Name = "TSL.AUTO.ANOMALY",
                    Category = "Auto Functions",
                    Signature = "TSL.AUTO.ANOMALY(data_range, [alpha])",
                    Description = "Shorthand for TSL.AUTO(\"stl_esd_anomaly\", ...). Detects anomalies using STL + ESD method.",
                    Example = "=TSL.AUTO.ANOMALY(B2:B200)",
                    ReturnType = "Dynamic array (Index, Value, IsAnomaly columns)",
                    Parameters = new List<UdfParameterInfo>
                    {
                        new UdfParameterInfo { Name = "data_range", Type = "Range", Description = "Single column of numeric data", Optional = false },
                        new UdfParameterInfo { Name = "alpha", Type = "Number", Description = "Significance level (default 0.05)", Optional = true },
                    }
                },
            };

            RebuildCategories();
            ApplyFilter();
        }
    }
}
