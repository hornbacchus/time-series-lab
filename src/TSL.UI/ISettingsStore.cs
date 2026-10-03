namespace TSL.UI
{
    /// <summary>
    /// The per-user settings the task pane's Settings view reads and writes (A2 U7).
    /// TSL.AddIn passes an adapter over its SettingsManager (config.json) when it creates
    /// the pane; TSL.UI never touches the file itself.
    /// </summary>
    public interface ISettingsStore
    {
        /// <summary>The preset: Fast, Balanced or Thorough.</summary>
        string GetPreset();

        /// <summary>Save the preset and bring the ribbon's Preset menu and the pane in step.</summary>
        void SetPreset(string preset);

        /// <summary>One of <see cref="ResultsDestinations"/>.</summary>
        string GetResultsDestination();

        /// <summary>Save one of <see cref="ResultsDestinations"/>.</summary>
        void SetResultsDestination(string destination);
    }

    /// <summary>The values of the resultsDestination setting in config.json (A2 U7).</summary>
    public static class ResultsDestinations
    {
        /// <summary>A new workbook saved next to the data workbook (the default).</summary>
        public const string NewWorkbook = "NewWorkbook";

        /// <summary>The workbook that holds the data; it is not saved.</summary>
        public const string SameWorkbook = "SameWorkbook";
    }
}
