using System;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using ExcelDna.Integration;
using ExcelDna.Integration.CustomUI;
using Microsoft.Office.Interop.Excel;
using Application = Microsoft.Office.Interop.Excel.Application;

namespace TSL.AddIn
{
    /// <summary>
    /// Office IRibbonExtensibility COM interface.
    /// Defined locally to avoid depending on the Office PIA (office.dll).
    /// </summary>
    [ComImport]
    [Guid("000C0396-0000-0000-C000-000000000046")]
    [InterfaceType(ComInterfaceType.InterfaceIsIDispatch)]
    internal interface IRibbonExtensibility
    {
        [DispId(1)]
        string GetCustomUI(string ribbonId);
    }

    /// <summary>
    /// Ribbon controller for the "Time Series Lab" tab.
    /// Uses ExcelComAddIn (not ExcelRibbon) to avoid Excel-DNA auto-discovery,
    /// which would register the ribbon before external COM add-ins (e.g. Acrobat).
    /// Manually registered via ExcelComAddInHelper.LoadComAddIn() in AddIn.AutoOpen().
    /// </summary>
    [ComVisible(true)]
    public class Ribbon : ExcelComAddIn, IRibbonExtensibility
    {
        private ExcelDna.Integration.CustomUI.IRibbonUI _ribbonUi;

        public string GetCustomUI(string ribbonId)
        {
            return RibbonXml.GetXml();
        }

        #region Callbacks

        public void OnRibbonLoad(IRibbonUI ribbonUi)
        {
            _ribbonUi = ribbonUi;
        }

        // ── Quick Actions ──────────────────────────────────────────────

        public void OnSeasonalAdjustment(IRibbonControl control)
        {
            TaskPaneManager.ShowAndSelect("stl_decompose");
        }

        public void OnGrangerCausality(IRibbonControl control)
        {
            TaskPaneManager.ShowAndSelect("granger_causality");
        }

        public void OnLeadLagFinder(IRibbonControl control)
        {
            TaskPaneManager.ShowAndSelect("prewhitened_ccf_lag");
        }

        public void OnForecast(IRibbonControl control)
        {
            TaskPaneManager.ShowAndSelect("auto_arima");
        }

        public void OnAnomalyScan(IRibbonControl control)
        {
            TaskPaneManager.ShowAndSelect("stl_esd_anomaly");
        }

        // ── Explore ────────────────────────────────────────────────────

        public void OnTechniqueExplorer(IRibbonControl control)
        {
            TaskPaneManager.ShowExplorer();
        }

        public void OnRecommenderWizard(IRibbonControl control)
        {
            TaskPaneManager.ShowRecommender();
        }

        public void OnRecommenderGoal(IRibbonControl control)
        {
            TaskPaneManager.ShowRecommenderWithGoal(control.Tag);
        }

        public void OnExplorerCategory(IRibbonControl control)
        {
            TaskPaneManager.ShowExplorerWithCategory(control.Tag);
        }

        public void OnDataReadiness(IRibbonControl control)
        {
            TaskPaneManager.ShowDataReadiness();
        }

        // ── Run ────────────────────────────────────────────────────────

        public void OnPresetChange(IRibbonControl control, string selectedId, int selectedIndex)
        {
            var preset = selectedId.Replace("preset_", "");
            AddIn.Settings.SetGlobalPreset(preset);
            TaskPaneManager.UpdatePreset(preset);
        }

        public int OnPresetGetSelectedIndex(IRibbonControl control)
        {
            var preset = AddIn.Settings.GetGlobalPreset();
            switch (preset)
            {
                case "Fast": return 0;
                case "Thorough": return 2;
                default: return 1; // Balanced
            }
        }

        public int OnPresetGetItemCount(IRibbonControl control) => 3;

        public string OnPresetGetItemLabel(IRibbonControl control, int index)
        {
            switch (index)
            {
                case 0: return "Fast";
                case 1: return "Balanced";
                case 2: return "Thorough";
                default: return "Balanced";
            }
        }

        public string OnPresetGetItemId(IRibbonControl control, int index)
        {
            switch (index)
            {
                case 0: return "preset_Fast";
                case 1: return "preset_Balanced";
                case 2: return "preset_Thorough";
                default: return "preset_Balanced";
            }
        }

        public void OnRun(IRibbonControl control)
        {
            TaskPaneManager.RunCurrent();
        }

        public void OnCancel(IRibbonControl control)
        {
            AddIn.Engine?.CancelCurrentRun();
        }

        public void OnRerunThorough(IRibbonControl control)
        {
            TriggerManager.IncrementTrigger();
            _ribbonUi?.Invalidate();
        }

        public void OnSettings(IRibbonControl control)
        {
            TaskPaneManager.ShowSettings();
        }

        // ── Help ───────────────────────────────────────────────────────

        public void OnUdfGuide(IRibbonControl control)
        {
            TaskPaneManager.ShowUdfBrowser();
        }

        public void OnOpenUserGuide(IRibbonControl control)
        {
            // Check installed location first
            var guidePath = Path.Combine(AddIn.AppDataPath, "docs", "TimeSeriesLab_UserGuide.docx");

            // Fallback: dev/project location (navigate up from XLL output dir)
            // XLL is at: src/TSL.AddIn/bin/x64/Release/net48/ — 6 levels up to project root
            if (!File.Exists(guidePath))
            {
                var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                guidePath = Path.Combine(projectRoot, "docs", "TimeSeriesLab_UserGuide.docx");
            }

            if (File.Exists(guidePath))
            {
                Process.Start(guidePath);
            }
            else
            {
                // Offer to generate it
                var result = MessageBox.Show(
                    "User Guide has not been generated yet.\n\n" +
                    "Would you like to generate it now?\n" +
                    "(Requires Python with python-docx installed)",
                    "Time Series Lab",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Question);

                if (result == DialogResult.Yes)
                {
                    try
                    {
                        var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                        var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                        var script = Path.Combine(projectRoot, "tools", "generate_user_guide.py");
                        if (File.Exists(script))
                        {
                            var psi = new ProcessStartInfo
                            {
                                FileName = "python",
                                Arguments = $"\"{script}\"",
                                WorkingDirectory = projectRoot,
                                UseShellExecute = false,
                                CreateNoWindow = true,
                            };
                            using (var proc = Process.Start(psi))
                            {
                                proc?.WaitForExit(30000);
                            }

                            var generated = Path.Combine(projectRoot, "docs", "TimeSeriesLab_UserGuide.docx");
                            if (File.Exists(generated))
                                Process.Start(generated);
                            else
                                MessageBox.Show("Generation completed but the file was not created.\nCheck the tools/generate_user_guide.py script.",
                                    "Time Series Lab", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        }
                        else
                        {
                            MessageBox.Show($"Generator script not found at:\n{script}",
                                "Time Series Lab", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                        }
                    }
                    catch (Exception ex)
                    {
                        MessageBox.Show($"Failed to generate User Guide:\n{ex.Message}",
                            "Time Series Lab", MessageBoxButtons.OK, MessageBoxIcon.Error);
                    }
                }
            }
        }

        public void OnOpenUserGuideHtml(IRibbonControl control)
        {
            // Check installed location first
            var guidePath = Path.Combine(AddIn.AppDataPath, "docs", "TimeSeriesLab_UserGuide.html");

            // Fallback: dev/project location
            if (!File.Exists(guidePath))
            {
                var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                guidePath = Path.Combine(projectRoot, "docs", "TimeSeriesLab_UserGuide.html");
            }

            if (File.Exists(guidePath))
            {
                Process.Start(guidePath);
            }
            else
            {
                MessageBox.Show(
                    "HTML User Guide not found.\n\n" +
                    "Run tools\\generate_user_guide.py to generate it.",
                    "Time Series Lab",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Warning);
            }
        }

        public void OnSaveInstaller(IRibbonControl control)
        {
            try
            {
                // Locate the installer pack directory
                // Installed: %LOCALAPPDATA%\TimeSeriesLab  (the install itself IS the pack)
                // Dev: <project_root>\build\pack
                string packDir = null;

                // Try dev/project location first
                var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                var devPack = Path.Combine(projectRoot, "build", "pack");
                if (Directory.Exists(devPack) && File.Exists(Path.Combine(devPack, "TSL.Installer.exe")))
                {
                    packDir = devPack;
                }

                // Fallback: installed location (AppData has the same structure)
                if (packDir == null && Directory.Exists(AddIn.AppDataPath)
                    && File.Exists(Path.Combine(AddIn.AppDataPath, "TSL.Installer.exe")))
                {
                    packDir = AddIn.AppDataPath;
                }

                if (packDir == null)
                {
                    MessageBox.Show(
                        "Installer package not found.\n\n" +
                        "Run tools\\build_pack.ps1 from the project root to create it,\n" +
                        "or reinstall Time Series Lab to restore the installer files.",
                        "Time Series Lab",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Warning);
                    return;
                }

                // Open a folder browser so the user picks a destination
                using (var dialog = new FolderBrowserDialog())
                {
                    dialog.Description = "Choose a folder to save the Time Series Lab installer package.";
                    dialog.ShowNewFolderButton = true;

                    if (dialog.ShowDialog() != DialogResult.OK)
                        return;

                    var destDir = Path.Combine(dialog.SelectedPath, "TimeSeriesLab_Installer");

                    if (Directory.Exists(destDir))
                    {
                        var overwrite = MessageBox.Show(
                            $"'{destDir}' already exists.\n\nOverwrite it?",
                            "Time Series Lab",
                            MessageBoxButtons.YesNo,
                            MessageBoxIcon.Question);
                        if (overwrite != DialogResult.Yes)
                            return;
                        Directory.Delete(destDir, true);
                    }

                    // Recursive copy
                    CopyDirectory(packDir, destDir);

                    MessageBox.Show(
                        $"Installer package saved to:\n{destDir}\n\n" +
                        "To install on another PC, copy this folder and run TSL.Installer.exe.",
                        "Time Series Lab",
                        MessageBoxButtons.OK,
                        MessageBoxIcon.Information);

                    // Open the destination folder in Explorer
                    Process.Start("explorer.exe", destDir);
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"Failed to save installer package:\n{ex.Message}",
                    "Time Series Lab",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        private static void CopyDirectory(string sourceDir, string destDir)
        {
            Directory.CreateDirectory(destDir);

            foreach (var file in Directory.GetFiles(sourceDir))
            {
                var destFile = Path.Combine(destDir, Path.GetFileName(file));
                File.Copy(file, destFile, true);
            }

            foreach (var dir in Directory.GetDirectories(sourceDir))
            {
                var destSub = Path.Combine(destDir, Path.GetFileName(dir));
                CopyDirectory(dir, destSub);
            }
        }

        public void OnAbout(IRibbonControl control)
        {
            var addinVersion = typeof(Ribbon).Assembly.GetName().Version;

            // Read engine version from VERSION.txt (try project dir first, then AppData)
            var engineVersion = "Unknown";
            try
            {
                var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                var versionFile = Path.Combine(projectRoot, "engine", "VERSION.txt");
                if (!File.Exists(versionFile))
                    versionFile = Path.Combine(AddIn.AppDataPath, "engine", "VERSION.txt");
                if (File.Exists(versionFile))
                    engineVersion = File.ReadAllText(versionFile).Trim();
            }
            catch { }

            // Count techniques from catalog
            var techniqueCount = 0;
            var categoryCount = 0;
            try
            {
                var xllDir = Path.GetDirectoryName(ExcelDnaUtil.XllPath);
                var projectRoot = Path.GetFullPath(Path.Combine(xllDir, "..", "..", "..", "..", "..", ".."));
                var catalogPath = Path.Combine(projectRoot, "resources", "catalog", "techniques_catalog.json");
                if (File.Exists(catalogPath))
                {
                    var json = File.ReadAllText(catalogPath);
                    // Simple count: occurrences of "\"id\":" for techniques
                    techniqueCount = System.Text.RegularExpressions.Regex.Matches(json, "\"id\"\\s*:").Count;
                    // Count unique categories
                    var catMatches = System.Text.RegularExpressions.Regex.Matches(json, "\"category\"\\s*:\\s*\"([^\"]+)\"");
                    var cats = new System.Collections.Generic.HashSet<string>();
                    foreach (System.Text.RegularExpressions.Match m in catMatches)
                        cats.Add(m.Groups[1].Value);
                    categoryCount = cats.Count;
                }
            }
            catch { }

            var techniqueInfo = techniqueCount > 0
                ? $"{techniqueCount} techniques across {categoryCount} categories"
                : "Technique catalog not found";

            // Detect Python version
            var pythonVersion = "Not detected";
            try
            {
                var psi = new ProcessStartInfo
                {
                    FileName = "python",
                    Arguments = "--version",
                    UseShellExecute = false,
                    RedirectStandardOutput = true,
                    CreateNoWindow = true,
                };
                using (var proc = Process.Start(psi))
                {
                    if (proc != null)
                    {
                        pythonVersion = proc.StandardOutput.ReadToEnd().Trim();
                        proc.WaitForExit(3000);
                    }
                }
            }
            catch { }

            // Check if engine pipe exists (engine is running)
            var engineStatus = "Not running";
            try
            {
                var sid = System.Security.Principal.WindowsIdentity.GetCurrent().User?.Value ?? "default";
                var pipeName = $"TSL_ENGINE_PIPE_{sid}";
                if (File.Exists($@"\\.\pipe\{pipeName}"))
                    engineStatus = "Running";
            }
            catch { }

            MessageBox.Show(
                $"Time Series Lab\n" +
                $"Created by Matthew T. Hornbach\n\n" +
                $"Add-in version:    {addinVersion}\n" +
                $"Engine version:    {engineVersion}\n" +
                $"Engine status:     {engineStatus}\n" +
                $"Technique library: {techniqueInfo}\n\n" +
                $"Platform:          .NET Framework 4.8 + Excel-DNA\n" +
                $"Runtime:           {pythonVersion}\n" +
                $"Compute:           100% local (no cloud, no telemetry)\n\n" +
                $"Project:           {Path.GetDirectoryName(Path.GetDirectoryName(Path.GetDirectoryName(Path.GetDirectoryName(Path.GetDirectoryName(Path.GetDirectoryName(ExcelDnaUtil.XllPath))))))}\n" +
                $"Settings:          {Path.Combine(AddIn.AppDataPath, "config.json")}\n" +
                $"Logs:              {Path.Combine(AddIn.AppDataPath, "logs")}",
                "About Time Series Lab",
                MessageBoxButtons.OK,
                MessageBoxIcon.Information);
        }

        #endregion
    }
}
