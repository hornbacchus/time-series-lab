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

        private void OnBrowseEnginePath()
        {
            // In a real implementation the AddIn layer would show a FolderBrowserDialog.
            // The ViewModel exposes a callback/event for this; the View or AddIn wires it.
            StatusMessage = "Use the AddIn ribbon to configure the engine path.";
        }

        private void OnResetDefaults()
        {
            DefaultPreset = "Balanced";
            AutoDetectFrequency = true;
            ShowFormulaHints = true;
            CreateSeparateSheets = true;
            StatusMessage = "Settings reset to defaults.";
        }

        private void OnCheckEngine()
        {
            StatusMessage = "Engine check requested. See ribbon status.";
        }
    }
}
