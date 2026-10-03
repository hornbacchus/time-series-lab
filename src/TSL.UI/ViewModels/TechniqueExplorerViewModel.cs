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

        /// <summary>The AUTO worksheet function as a formula to fill in, from the function
        /// catalog (e.g. "=TSL_ADF(value_range)"); empty when the technique has none.</summary>
        public string AutoUdfExample { get; set; } = "";
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

        public event Action<string> NavigateToRunRequested;

        /// <summary>The "Show formulas" link: open the UDF Formula Guide (A2 U8, Q7).</summary>
        public event Action ShowFormulasRequested;

        // ── Collections ─────────────────────────────────────────────────

        public ObservableCollection<TechniqueCategory> Categories { get; }
            = new ObservableCollection<TechniqueCategory>();

        public ObservableCollection<TechniqueItem> FilteredTechniques { get; }
            = new ObservableCollection<TechniqueItem>();

        // Master list loaded from catalog
        private List<TechniqueItem> _allTechniques = new List<TechniqueItem>();

        /// <summary>
        /// Maps every known technique id -> its display Name. Bound to
        /// MarkdownBehavior.IdNameMap so a backtick id-span in a "Related
        /// Techniques" section renders as a clickable cross-reference showing the
        /// display name (matching the Explorer list, which also binds Name) while
        /// navigating by id. Refreshed whenever the catalog loads.
        /// </summary>
        public IReadOnlyDictionary<string, string> TechniqueIdNameMap
        {
            get
            {
                var map = new Dictionary<string, string>(StringComparer.OrdinalIgnoreCase);
                foreach (var t in _allTechniques)
                    if (!string.IsNullOrEmpty(t.Id) && !map.ContainsKey(t.Id))
                        map[t.Id] = t.Name;
                return map;
            }
        }

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
                    OnPropertyChanged(nameof(HasAutoUdfExample));
                    OnPropertyChanged(nameof(AutoUdfExample));
                    OnPropertyChanged(nameof(ThoroughUdfExample));
                    OnPropertyChanged(nameof(SelectedTechniqueSeriesInfo));
                    OnPropertyChanged(nameof(SelectedTechniqueOutputInfo));
                }
            }
        }

        public bool HasSelectedTechnique => _selectedTechnique != null;

        private string _catalogMessage = "";
        /// <summary>Why the Explorer is empty (A2 R8), or "" when the catalog loaded.</summary>
        public string CatalogMessage
        {
            get => _catalogMessage;
            private set
            {
                if (SetProperty(ref _catalogMessage, value ?? ""))
                    OnPropertyChanged(nameof(HasCatalogMessage));
            }
        }

        public bool HasCatalogMessage => !string.IsNullOrEmpty(_catalogMessage);

        /// <summary>The catalog did not load: show <paramref name="message"/> in place of the list.</summary>
        public void ShowCatalogMessage(string message) => CatalogMessage = message;

        public string SelectedTechniqueDescription =>
            _selectedTechnique?.Description ?? string.Empty;

        // The real worksheet forms (A2 E2b ruling 1(d); the examples used to show =TSL.AUTO and
        // =TSL.THOROUGH, which do not exist): the technique's AUTO function, when it has one,
        // and TSL_RUN_THR, which runs any technique.
        public bool HasAutoUdfExample =>
            _selectedTechnique?.SupportsAutoUdf == true && !string.IsNullOrEmpty(_selectedTechnique.AutoUdfExample);

        public string AutoUdfExample =>
            HasAutoUdfExample ? _selectedTechnique.AutoUdfExample : string.Empty;

        public string ThoroughUdfExample
        {
            get
            {
                if (_selectedTechnique == null) return string.Empty;
                return $"=TSL_RUN_THR(\"{_selectedTechnique.Id}\", <dates>, <values>, TSL_TRIGGER())";
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

        public ICommand ShowFormulasCommand { get; }
        public ICommand OpenRunViewCommand { get; }
        public ICommand ClearSearchCommand { get; }
        public ICommand ShowAllCategoriesCommand { get; }
        public ICommand ToggleAdvancedCommand { get; }

        // Cross-reference navigation: a clickable related-technique id (rendered
        // by MarkdownBehavior as a Hyperlink) invokes this with the id string.
        public ICommand NavigateToRelatedCommand { get; }

        // ── Constructor ─────────────────────────────────────────────────

        public TechniqueExplorerViewModel()
        {
            // No Run command here (A2 U6 removed the dormant one): the Explorer's
            // primary action is OpenRunViewCommand (configure-then-wait); execution
            // happens only when the user clicks Run on the Run view itself, or the
            // ribbon's Run, which runs that same command.
            // Replaces the Insert AUTO and Insert THOROUGH buttons, which nothing handled
            // (A2 N4; ratification Q7): the worksheet functions are in the UDF Formula Guide.
            ShowFormulasCommand = new RelayCommand(() => ShowFormulasRequested?.Invoke());

            OpenRunViewCommand = new RelayCommand(
                () => { if (_selectedTechnique != null) NavigateToRunRequested?.Invoke(_selectedTechnique.Id); },
                () => _selectedTechnique != null);

            ClearSearchCommand = new RelayCommand(() => SearchQuery = string.Empty);

            ShowAllCategoriesCommand = new RelayCommand(() => SelectedCategory = null);

            ToggleAdvancedCommand = new RelayCommand(() => ShowAdvancedParams = !ShowAdvancedParams);

            // A clicked related-technique cross-reference passes its id here.
            NavigateToRelatedCommand = new RelayCommand(param =>
            {
                var id = param as string;
                if (!string.IsNullOrEmpty(id)) SelectTechniqueById(id);
            });

            // No built-in stub: the real catalog is pushed in via LoadTechniques
            // (TaskPaneManager.EnsureTaskPane) BEFORE the pane is shown. Until
            // then _allTechniques is empty (handled gracefully by the null-safe
            // Selected* properties); at design-time the preview is simply blank.
        }

        // ── Public API ──────────────────────────────────────────────────

        /// <summary>
        /// Load techniques from the AddIn catalog. Called by the AddIn layer
        /// after TechniqueCatalogService is ready.
        /// </summary>
        public void LoadTechniques(IEnumerable<TechniqueItem> techniques)
        {
            _allTechniques = techniques.ToList();
            CatalogMessage = "";
            // Refresh the cross-reference id->name map BEFORE ApplyFilter selects
            // the first technique (whose description renders the related links).
            OnPropertyChanged(nameof(TechniqueIdNameMap));
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
    }
}
