using TSL.UI;

namespace TSL.AddIn
{
    /// <summary>
    /// The task pane's Settings view reads and writes the per-user settings through this
    /// (A2 U7): config.json, by way of SettingsManager. A preset chosen there also moves the
    /// ribbon's Preset menu and the pane, exactly as the ribbon's own Preset menu does.
    /// </summary>
    internal sealed class SettingsStoreAdapter : ISettingsStore
    {
        public string GetPreset() => AddIn.Settings?.GetGlobalPreset() ?? "Balanced";

        public void SetPreset(string preset)
        {
            if (string.IsNullOrEmpty(preset)) return;
            AddIn.Settings?.SetGlobalPreset(preset);
            TaskPaneManager.UpdatePreset(preset);
            Ribbon.RefreshPresetControls();
        }

        public string GetResultsDestination() =>
            AddIn.Settings?.GetResultsDestination() ?? ResultsDestinations.NewWorkbook;

        public void SetResultsDestination(string destination) =>
            AddIn.Settings?.SetResultsDestination(destination);
    }
}
