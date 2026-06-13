using System;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// Top-level ViewModel for the task pane. Owns navigation state, the selection
    /// status bar, and the current preset. Child ViewModels are created on demand
    /// and cached for the lifetime of the pane.
    /// </summary>
    public class MainViewModel : ViewModelBase
    {
        // ── Child ViewModels (lazy-created, cached) ─────────────────────

        private TechniqueExplorerViewModel _explorerVm;
        private RunViewModel _runVm;
        private RecommenderViewModel _recommenderVm;
        private DataReadinessViewModel _dataReadinessVm;
        private SettingsViewModel _settingsVm;
        private UdfBrowserViewModel _udfBrowserVm;

        // ── Observable properties ───────────────────────────────────────

        private ViewModelBase _currentView;
        public ViewModelBase CurrentView
        {
            get => _currentView;
            set => SetProperty(ref _currentView, value);
        }

        private string _currentViewTitle = "Technique Explorer";
        public string CurrentViewTitle
        {
            get => _currentViewTitle;
            set => SetProperty(ref _currentViewTitle, value);
        }

        private string _selectionStatus = "No selection";
        public string SelectionStatus
        {
            get => _selectionStatus;
            set => SetProperty(ref _selectionStatus, value);
        }

        private int _selectionSeriesCount;
        public int SelectionSeriesCount
        {
            get => _selectionSeriesCount;
            set => SetProperty(ref _selectionSeriesCount, value);
        }

        private int _selectionPointCount;
        public int SelectionPointCount
        {
            get => _selectionPointCount;
            set => SetProperty(ref _selectionPointCount, value);
        }

        private string _selectionFrequency = "Unknown";
        public string SelectionFrequency
        {
            get => _selectionFrequency;
            set => SetProperty(ref _selectionFrequency, value);
        }

        private string _preset = "Balanced";
        public string Preset
        {
            get => _preset;
            set
            {
                if (SetProperty(ref _preset, value))
                {
                    // Propagate to child VMs that care
                    if (_runVm != null) _runVm.Preset = value;
                    if (_explorerVm != null) _explorerVm.CurrentPreset = value;
                }
            }
        }

        private bool _isEngineRunning;
        public bool IsEngineRunning
        {
            get => _isEngineRunning;
            set => SetProperty(ref _isEngineRunning, value);
        }

        // ── Navigation commands ─────────────────────────────────────────

        public ICommand NavigateExplorerCommand { get; }
        public ICommand NavigateRecommenderCommand { get; }
        public ICommand NavigateDataReadinessCommand { get; }
        public ICommand NavigateSettingsCommand { get; }
        public ICommand NavigateUdfBrowserCommand { get; }

        // ── Events ──────────────────────────────────────────────────────

        /// <summary>
        /// Raised when the user clicks Run in the explorer. The AddIn layer
        /// subscribes to this to perform the actual engine call.
        /// </summary>
        public event Action<string, string> RunRequested; // techniqueId, preset

        /// <summary>
        /// Raised when the user clicks Run in the Run view for a WORKBOOK-INPUT
        /// technique (RunViewModel.WorkbookInputMode == true). The AddIn layer
        /// dispatches the workbook-input flow rather than the selection flow.
        /// </summary>
        public event Action<string> WorkbookRunRequested; // techniqueId

        /// <summary>
        /// Raised when the user clicks Cancel in the Run view. The AddIn layer
        /// hard-stops the engine and returns the view to ready.
        /// </summary>
        public event Action RunCancelRequested;

        /// <summary>
        /// Raised when the user clicks "Insert =TSL.AUTO..." in the explorer.
        /// </summary>
        public event Action<string> InsertAutoFormulaRequested; // techniqueId

        /// <summary>
        /// Raised when the user clicks "Insert =TSL.THOROUGH..." in the explorer.
        /// </summary>
        public event Action<string> InsertThoroughFormulaRequested; // techniqueId

        /// <summary>
        /// Raised when the user clicks "Analyse Selection" in the Data Readiness view.
        /// The AddIn layer subscribes to this, extracts the current Excel selection,
        /// runs the quality checks, and calls ShowResults on the passed VM.
        /// </summary>
        public event Action<DataReadinessViewModel> DataReadinessChecksRequested;

        // ── Constructor ─────────────────────────────────────────────────

        public MainViewModel()
        {
            NavigateExplorerCommand = new RelayCommand(NavigateToExplorer);
            NavigateRecommenderCommand = new RelayCommand(NavigateToRecommender);
            NavigateDataReadinessCommand = new RelayCommand(NavigateToDataReadiness);
            NavigateSettingsCommand = new RelayCommand(NavigateToSettings);
            NavigateUdfBrowserCommand = new RelayCommand(NavigateToUdfBrowser);

            // Start on the technique explorer
            NavigateToExplorer();
        }

        // ── Public navigation methods (called from TaskPaneHostControl) ──

        public void NavigateToTechnique(string techniqueId)
        {
            var vm = GetOrCreateExplorer();
            vm.SelectTechniqueById(techniqueId);
            CurrentView = vm;
            CurrentViewTitle = "Technique Explorer";
        }

        public void NavigateToExplorer()
        {
            CurrentView = GetOrCreateExplorer();
            CurrentViewTitle = "Technique Explorer";
        }

        public void NavigateToExplorerWithCategory(string category)
        {
            var vm = GetOrCreateExplorer();
            vm.SearchQuery = string.Empty;
            // Find matching category by name
            TechniqueCategory match = null;
            foreach (var cat in vm.Categories)
            {
                if (string.Equals(cat.Name, category, StringComparison.OrdinalIgnoreCase))
                {
                    match = cat;
                    break;
                }
            }
            vm.SelectedCategory = match;
            CurrentView = vm;
            CurrentViewTitle = "Technique Explorer";
        }

        public void NavigateToRecommender()
        {
            CurrentView = GetOrCreateRecommender();
            CurrentViewTitle = "Recommender";
        }

        public void NavigateToRecommenderWithGoal(string goal)
        {
            var vm = GetOrCreateRecommender();
            vm.RestartCommand.Execute(null);
            vm.SelectedOption = goal;
            CurrentView = vm;
            CurrentViewTitle = "Recommender";
        }

        public void NavigateToDataReadiness()
        {
            CurrentView = GetOrCreateDataReadiness();
            CurrentViewTitle = "Data Readiness";
        }

        public void NavigateToSettings()
        {
            CurrentView = GetOrCreateSettings();
            CurrentViewTitle = "Settings";
        }

        public void NavigateToUdfBrowser()
        {
            CurrentView = GetOrCreateUdfBrowser();
            CurrentViewTitle = "UDF Browser";
        }

        /// <summary>
        /// The technique id the (singleton) Run view is currently bound to, read
        /// BEFORE a NavigateToRun overwrites it. LaunchTechnique uses this to
        /// decide whether to (re)populate the parameter controls: NavigateToRun
        /// sets <see cref="RunViewModel.TechniqueId"/> up front, so a gate that
        /// compares the post-navigation id is always equal and never repopulates
        /// (the dead-gate that left every selection technique with zero param
        /// controls). Comparing against this pre-navigation id restores the
        /// "populate on change, preserve user edits on same-technique re-run"
        /// behavior the gate intended.
        /// </summary>
        public string CurrentRunTechniqueId => _runVm?.TechniqueId;

        public void NavigateToRun(string techniqueId)
        {
            var vm = GetOrCreateRun();
            vm.TechniqueId = techniqueId;
            vm.Preset = Preset;
            CurrentView = vm;
            CurrentViewTitle = "Run";
        }

        public void RunCurrentTechnique()
        {
            var explorer = _explorerVm;
            if (explorer?.SelectedTechnique != null)
            {
                RunRequested?.Invoke(explorer.SelectedTechnique.Id, Preset);
            }
        }

        /// <summary>
        /// Called by the AddIn layer to replace the built-in stub catalog with the
        /// real catalog loaded from techniques_catalog.json. Creates the explorer
        /// VM if it doesn't exist yet so the data is ready on first navigation.
        /// </summary>
        public void LoadTechniqueCatalog(System.Collections.Generic.IEnumerable<TechniqueItem> techniques)
        {
            if (techniques == null) return;
            var vm = GetOrCreateExplorer();
            vm.LoadTechniques(techniques);
        }

        /// <summary>
        /// Called by the AddIn layer when the Excel selection changes.
        /// </summary>
        public void UpdateSelectionStatus(int seriesCount, int pointCount, string frequency)
        {
            SelectionSeriesCount = seriesCount;
            SelectionPointCount = pointCount;
            SelectionFrequency = frequency ?? "Unknown";

            if (seriesCount == 0)
            {
                SelectionStatus = "No selection";
            }
            else
            {
                SelectionStatus = $"{seriesCount} series, {pointCount} pts, freq: {SelectionFrequency}";
            }
        }

        // ── Factory helpers ─────────────────────────────────────────────

        private TechniqueExplorerViewModel GetOrCreateExplorer()
        {
            if (_explorerVm == null)
            {
                _explorerVm = new TechniqueExplorerViewModel();
                _explorerVm.CurrentPreset = Preset;
                _explorerVm.RunRequested += (id) => RunRequested?.Invoke(id, Preset);
                _explorerVm.InsertAutoFormulaRequested += (id) => InsertAutoFormulaRequested?.Invoke(id);
                _explorerVm.InsertThoroughFormulaRequested += (id) => InsertThoroughFormulaRequested?.Invoke(id);
                _explorerVm.NavigateToRunRequested += (id) => NavigateToRun(id);
            }
            return _explorerVm;
        }

        private RunViewModel GetOrCreateRun()
        {
            if (_runVm == null)
            {
                _runVm = new RunViewModel();
                // When the user clicks the "Run" button inside the Run view itself,
                // re-trigger the main run pipeline (selection extraction + engine call)
                // using the current technique.
                _runVm.RunExecuteRequested += () =>
                {
                    if (!string.IsNullOrEmpty(_runVm.TechniqueId))
                        RunRequested?.Invoke(_runVm.TechniqueId, Preset);
                };
                // Workbook-input techniques (e.g. Bond Yield Forecast) route the
                // Run button here instead, so the AddIn layer resolves the active
                // workbook rather than a cell selection.
                _runVm.WorkbookRunRequested += () =>
                {
                    if (!string.IsNullOrEmpty(_runVm.TechniqueId))
                        WorkbookRunRequested?.Invoke(_runVm.TechniqueId);
                };
                _runVm.CancelRequested += () => RunCancelRequested?.Invoke();
            }
            return _runVm;
        }

        private RecommenderViewModel GetOrCreateRecommender()
        {
            if (_recommenderVm == null)
            {
                _recommenderVm = new RecommenderViewModel();
                _recommenderVm.OpenTechniqueRequested += (id) => NavigateToTechnique(id);
            }
            return _recommenderVm;
        }

        private DataReadinessViewModel GetOrCreateDataReadiness()
        {
            if (_dataReadinessVm == null)
            {
                _dataReadinessVm = new DataReadinessViewModel();
                _dataReadinessVm.RunChecksRequested += () =>
                    DataReadinessChecksRequested?.Invoke(_dataReadinessVm);
            }
            return _dataReadinessVm;
        }

        private SettingsViewModel GetOrCreateSettings()
        {
            if (_settingsVm == null)
            {
                _settingsVm = new SettingsViewModel();
            }
            return _settingsVm;
        }

        private UdfBrowserViewModel GetOrCreateUdfBrowser()
        {
            if (_udfBrowserVm == null)
            {
                _udfBrowserVm = new UdfBrowserViewModel();
            }
            return _udfBrowserVm;
        }
    }
}
