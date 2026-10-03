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

        /// <summary>Whether the function takes any argument (Insert opens Excel's Function
        /// Arguments dialog for it either way).</summary>
        public bool HasArguments => Parameters != null && Parameters.Count > 0;
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
    /// ViewModel for the UDF Browser view (Help &gt; UDF Formula Guide). Lists the add-in's
    /// worksheet functions from the generated catalog (resources\catalog\udf_catalog.json,
    /// loaded by the AddIn layer when it creates the pane: A2 E2b ruling 1(a)). With no
    /// catalog the view shows <see cref="CatalogMessage"/> instead of a list.
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
                    StatusMessage = "";
                }
            }
        }

        public bool HasSelectedUdf => _selectedUdf != null;
        public string SelectedUdfDescription => _selectedUdf?.Description ?? string.Empty;
        public string SelectedUdfExample => _selectedUdf?.Example ?? string.Empty;
        public string SelectedUdfSignature => _selectedUdf?.Signature ?? string.Empty;

        private string _catalogMessage = "";
        /// <summary>Why the guide is empty (a house message), or "" when the catalog loaded.</summary>
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

        private string _statusMessage = "";
        /// <summary>What the last Copy did (A2 E2b ruling 1(c)); "" when nothing to say.</summary>
        public string StatusMessage
        {
            get => _statusMessage;
            set
            {
                if (SetProperty(ref _statusMessage, value ?? ""))
                    OnPropertyChanged(nameof(HasStatusMessage));
            }
        }

        public bool HasStatusMessage => !string.IsNullOrEmpty(_statusMessage);

        /// <summary>
        /// Puts text on the clipboard. Replaceable so Copy can be exercised without one.
        /// </summary>
        public Action<string> SetClipboardText { get; set; } = text => System.Windows.Clipboard.SetText(text);

        // ── Commands ────────────────────────────────────────────────────

        public ICommand InsertFormulaCommand { get; }
        public ICommand CopyFormulaCommand { get; }
        public ICommand ClearSearchCommand { get; }
        public ICommand ShowAllCommand { get; }
        public ICommand SelectCategoryCommand { get; }

        /// <summary>
        /// Raised when the user clicks Insert. The AddIn layer opens Excel's Function
        /// Arguments dialog for the function in the active cell (A2 E2b ruling 1(b)).
        /// </summary>
        public event Action<UdfEntry> InsertFormulaRequested;

        // ── Constructor ─────────────────────────────────────────────────

        public UdfBrowserViewModel()
        {
            InsertFormulaCommand = new RelayCommand(
                () =>
                {
                    if (_selectedUdf != null)
                    {
                        StatusMessage = "";
                        InsertFormulaRequested?.Invoke(_selectedUdf);
                    }
                },
                () => _selectedUdf != null);

            CopyFormulaCommand = new RelayCommand(CopySelected, () => _selectedUdf != null);

            ClearSearchCommand = new RelayCommand(() => SearchQuery = string.Empty);

            ShowAllCommand = new RelayCommand(() => SelectedCategory = null);

            SelectCategoryCommand = new RelayCommand(
                (param) => SelectedCategory = param as string);

            // No built-in list: until the AddIn layer loads the catalog the guide is empty
            // (the placeholder list of functions that do not exist is gone - A2 E2b ruling 1(a)).
        }

        // ── Public API ──────────────────────────────────────────────────

        /// <summary>
        /// Load the worksheet functions from the catalog (called by the AddIn layer).
        /// </summary>
        public void LoadUdfs(IEnumerable<UdfEntry> udfs)
        {
            _allUdfs = (udfs ?? Enumerable.Empty<UdfEntry>()).ToList();
            CatalogMessage = "";
            RebuildCategories();
            ApplyFilter();
        }

        /// <summary>
        /// The catalog could not be loaded: the guide is empty and shows
        /// <paramref name="message"/> instead.
        /// </summary>
        public void ShowCatalogMessage(string message)
        {
            _allUdfs = new List<UdfEntry>();
            RebuildCategories();
            ApplyFilter();
            CatalogMessage = message;
        }

        // ── Private helpers ─────────────────────────────────────────────

        /// <summary>Copy: the function with its required arguments, as a formula to fill in.</summary>
        private void CopySelected()
        {
            if (_selectedUdf == null) return;
            var formula = _selectedUdf.Example ?? "";
            try
            {
                SetClipboardText(formula);
                StatusMessage = "Copied to the clipboard:\n" + HouseDialog.Indent(formula);
            }
            catch (Exception ex)
            {
                StatusMessage = "Time Series Lab could not copy the formula to the clipboard. Nothing was copied.\n\n" +
                                HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                                "Click Copy again.";
            }
        }

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
    }
}
