using System;
using System.Collections.Generic;
using System.Windows.Input;
using TSL.UI.Helpers;

namespace TSL.UI.ViewModels
{
    /// <summary>
    /// ViewModel for the Settings view (A2 U7, ratification Q7): only the settings that
    /// change how Time Series Lab works - the preset and where results go - read from and
    /// saved to the per-user settings through <see cref="ISettingsStore"/>.
    /// </summary>
    public class SettingsViewModel : ViewModelBase
    {
        private readonly ISettingsStore _store;
        private bool _loading;

        /// <summary>
        /// The opt-in question for "Same workbook" (ShowChoice2: 1 = first button, 2 =
        /// second, 0 = Cancel). Replaceable so the logic can be exercised without a dialog.
        /// </summary>
        public Func<string, string, string, string, int> AskChoice2 { get; set; } = HouseDialog.ShowChoice2;

        // Shown when "Same workbook" is chosen (A2 Part 4(iv), ratified wording).
        internal const string SameWorkbookQuestion =
            "Results can be added to the workbook that holds the data instead of a new workbook.\n\n" +
            "If AutoSave is on for that workbook, Excel saves the new Results, Audit and hidden " +
            "run-record sheets into the file at once, and Undo cannot remove them.\n\n" +
            "New workbook = keep the data workbook unchanged (the default)\n" +
            "Same workbook = add the results to the data workbook";

        public IReadOnlyList<string> Presets { get; } = new[] { "Fast", "Balanced", "Thorough" };

        public ICommand ChooseNewWorkbookCommand { get; }
        public ICommand ChooseSameWorkbookCommand { get; }

        /// <summary>Design-time constructor: no store, nothing is saved.</summary>
        public SettingsViewModel() : this(null) { }

        public SettingsViewModel(ISettingsStore store)
        {
            _store = store;
            ChooseNewWorkbookCommand = new RelayCommand(() => ChooseDestination(sameWorkbook: false));
            ChooseSameWorkbookCommand = new RelayCommand(() => ChooseDestination(sameWorkbook: true));
            Reload();
        }

        private string _preset = "Balanced";
        /// <summary>The preset; a change made here is saved and shown on the ribbon.</summary>
        public string Preset
        {
            get => _preset;
            set
            {
                if (string.IsNullOrEmpty(value)) return;
                if (SetProperty(ref _preset, value) && !_loading)
                    _store?.SetPreset(value);
            }
        }

        private bool _sameWorkbook;
        public bool UseNewWorkbook => !_sameWorkbook;
        public bool UseSameWorkbook => _sameWorkbook;

        /// <summary>Read both settings again (each time the view is shown).</summary>
        public void Reload()
        {
            _loading = true;
            try
            {
                Preset = _store?.GetPreset() ?? "Balanced";
                _sameWorkbook = string.Equals(_store?.GetResultsDestination(), ResultsDestinations.SameWorkbook,
                    StringComparison.Ordinal);
            }
            finally
            {
                _loading = false;
            }
            RaiseDestination();
        }

        /// <summary>The preset changed elsewhere (the ribbon): show it, save nothing.</summary>
        public void SyncPreset(string preset)
        {
            _loading = true;
            try { Preset = preset; }
            finally { _loading = false; }
        }

        /// <summary>
        /// A radio button was clicked. "Same workbook" is saved only after the opt-in
        /// question is answered "Same workbook"; any other answer keeps "New workbook".
        /// </summary>
        private void ChooseDestination(bool sameWorkbook)
        {
            if (sameWorkbook && !_sameWorkbook)
            {
                int answer = AskChoice2(SameWorkbookQuestion, HouseDialog.Title("Settings"),
                    "New workbook", "Same workbook");
                if (answer != 2) sameWorkbook = false;
            }
            if (sameWorkbook != _sameWorkbook)
            {
                _sameWorkbook = sameWorkbook;
                _store?.SetResultsDestination(sameWorkbook ? ResultsDestinations.SameWorkbook : ResultsDestinations.NewWorkbook);
            }
            // Always: a radio button the question turned down snaps back.
            RaiseDestination();
        }

        private void RaiseDestination()
        {
            OnPropertyChanged(nameof(UseNewWorkbook));
            OnPropertyChanged(nameof(UseSameWorkbook));
        }
    }
}
