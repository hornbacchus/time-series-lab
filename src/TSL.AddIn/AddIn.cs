using System;
using System.IO;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;

namespace TSL.AddIn
{
    /// <summary>
    /// Excel-DNA add-in entry point. Initializes engine client, ribbon, and task pane factory.
    /// </summary>
    public class AddIn : IExcelAddIn
    {
        private static EngineClient _engineClient;
        private static ResultStore _resultStore;
        private static SettingsManager _settings;

        public static EngineClient Engine => _engineClient;
        public static ResultStore Results => _resultStore;
        public static SettingsManager Settings => _settings;

        public static string AppDataPath => Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TimeSeriesLab");

        public void AutoOpen()
        {
            try
            {
                // Ensure app data directory exists
                Directory.CreateDirectory(AppDataPath);
                Directory.CreateDirectory(Path.Combine(AppDataPath, "logs"));

                // Initialize settings
                _settings = new SettingsManager(Path.Combine(AppDataPath, "config.json"));

                // Initialize result store
                _resultStore = new ResultStore();

                // Initialize engine client (will start engine process on first request)
                _engineClient = new EngineClient();

                // Register IntelliSense if available
                try
                {
                    ExcelDna.IntelliSense.IntelliSenseServer.Install();
                }
                catch
                {
                    // IntelliSense is optional - don't fail add-in load
                }

                // Delay ribbon COM add-in registration so TSL tab appears
                // after external COM add-ins (e.g. Acrobat) in the ribbon.
                ExcelAsyncUtil.QueueAsMacro(() =>
                {
                    ExcelComAddInHelper.LoadComAddIn(new Ribbon());
                });

                Logger.Info("Time Series Lab add-in loaded successfully.");
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to initialize Time Series Lab: {ex.Message}");
                System.Windows.Forms.MessageBox.Show(
                    $"Time Series Lab failed to initialize:\n\n{ex.Message}\n\nCheck logs at: {Path.Combine(AppDataPath, "logs")}",
                    "Time Series Lab - Error",
                    System.Windows.Forms.MessageBoxButtons.OK,
                    System.Windows.Forms.MessageBoxIcon.Error);
            }
        }

        public void AutoClose()
        {
            try
            {
                _engineClient?.Shutdown();
                ExcelDna.IntelliSense.IntelliSenseServer.Uninstall();
            }
            catch
            {
                // Best-effort cleanup
            }

            Logger.Info("Time Series Lab add-in unloaded.");
        }
    }
}
