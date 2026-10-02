using System;
using System.IO;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;
using TSL.UI;

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
            // House dialogs (docs/HOUSE_STYLE.md): owned by and centred on Excel's main
            // window, shown on this (Excel's) thread, one log line per dialog. First, so
            // even a failure below is reported through it.
            try
            {
                HouseDialog.Initialize(() => ExcelDnaUtil.WindowHandle, message => Logger.Info(message));
            }
            catch (Exception ex)
            {
                Logger.Error($"House dialog initialization failed: {ex.Message}");
            }

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

                // Clean up engines orphaned by an earlier Excel, on a background
                // thread so startup never waits. Each Excel runs its own engine
                // (per-instance pipe, kill-on-close job), so every Excel session
                // still gets a fresh engine that loads the latest technique code.
                _engineClient.StartOrphanSweep();

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
                // A failure inside the queued step is reported, not dropped: it runs after
                // AutoOpen has returned, so the catch below never sees it.
                ExcelAsyncUtil.QueueAsMacro(() =>
                {
                    try
                    {
                        ExcelComAddInHelper.LoadComAddIn(new Ribbon());
                    }
                    catch (Exception ex)
                    {
                        Logger.Error("Registering the Time Series Lab ribbon tab failed.", ex);
                        HouseDialog.ShowHouseAlert(
                            "Time Series Lab could not add its tab to the ribbon, so its commands are not available " +
                            "in this Excel session. Its worksheet functions may still work.\n\n" +
                            HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                            "Close Excel and start it again. If this message returns, tell Matthew Hornbach.",
                            HouseDialog.Title(), isError: true);
                    }
                });

                Logger.Info("Time Series Lab add-in loaded successfully.");
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to initialize Time Series Lab.", ex);
                HouseDialog.ShowHouseAlert(
                    "Time Series Lab did not finish starting, so it may not work in this Excel session.\n\n" +
                    HouseDialog.ErrorBlock(ex.Message) + "\n\n" +
                    "The log has the details:\n" + HouseDialog.Indent(Path.Combine(AppDataPath, "logs")) + "\n\n" +
                    "Close Excel and start it again. If this message returns, tell Matthew Hornbach.",
                    HouseDialog.Title(), isError: true);
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
