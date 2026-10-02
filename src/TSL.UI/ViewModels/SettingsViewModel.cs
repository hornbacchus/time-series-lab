using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// ViewModel for the Settings view. Exposes engine path, preset default,
    /// and other configuration that persists via SettingsManager on the AddIn side.
    /// </summary>
    public class SettingsViewModel : ViewModelBase
    {
        private string _enginePath = "";
        public string EnginePath
        {
            get => _enginePath;
            set => SetProperty(ref _enginePath, value);
        }

        private string _defaultPreset = "Balanced";
        public string DefaultPreset
        {
            get => _defaultPreset;
            set => SetProperty(ref _defaultPreset, value);
        }

        private bool _autoDetectFrequency = true;
        public bool AutoDetectFrequency
        {
            get => _autoDetectFrequency;
            set => SetProperty(ref _autoDetectFrequency, value);
        }

        private bool _showFormulaHints = true;
        public bool ShowFormulaHints
        {
            get => _showFormulaHints;
            set => SetProperty(ref _showFormulaHints, value);
        }

        private bool _createSeparateSheets = true;
        public bool CreateSeparateSheets
        {
            get => _createSeparateSheets;
            set => SetProperty(ref _createSeparateSheets, value);
        }

        private string _engineVersion = "Checking...";
        public string EngineVersion
        {
            get => _engineVersion;
            set => SetProperty(ref _engineVersion, value);
        }

        private string _statusMessage = "";
        public string StatusMessage
        {
            get => _statusMessage;
            set => SetProperty(ref _statusMessage, value);
        }

        public ICommand BrowseEnginePathCommand { get; }
        public ICommand ResetDefaultsCommand { get; }
        public ICommand CheckEngineCommand { get; }

        public SettingsViewModel()
        {
            BrowseEnginePathCommand = new RelayCommand(OnBrowseEnginePath);
            ResetDefaultsCommand = new RelayCommand(OnResetDefaults);
            CheckEngineCommand = new RelayCommand(OnCheckEngine);
        }

        // These three controls change nothing outside this page (A2 N8; the Settings view is
        // rebuilt around real settings in A2 U7). Until then each says what is actually true
        // (house style: nothing reads as an action that did not happen).
        private void OnBrowseEnginePath()
        {
            StatusMessage = "Time Series Lab finds its engine by itself, so there is no path to set. " +
                            "Help > About shows the engine in use.";
        }

        private void OnResetDefaults()
        {
            DefaultPreset = "Balanced";
            AutoDetectFrequency = true;
            ShowFormulaHints = true;
            CreateSeparateSheets = true;
            StatusMessage = "This page shows its default values again. Nothing was saved: these settings do not " +
                            "change how runs work yet. To choose the preset, use the Preset menu in the Run group.";
        }

        private void OnCheckEngine()
        {
            StatusMessage = "Nothing was checked: the engine is checked each time a run starts. " +
                            "Help > About shows whether it is running.";
        }
    }
}
