using System;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Threading.Tasks;
using System.Windows;
using Microsoft.Win32;

namespace TSL.Installer
{
    public partial class MainWindow : Window
    {
        private static readonly string InstallBase = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
            "TimeSeriesLab");

        public MainWindow()
        {
            InitializeComponent();
            InstallPathText.Text = $"Install path: {InstallBase}";
        }

        private async void OnInstall(object sender, RoutedEventArgs e)
        {
            InstallButton.IsEnabled = false;
            UninstallButton.IsEnabled = false;
            ProgressBar.Visibility = Visibility.Visible;
            ProgressText.Visibility = Visibility.Visible;

            try
            {
                await Task.Run(() => RunInstall());
                StatusText.Text = "Installation complete! Restart Excel to load Time Series Lab.";
                MessageBox.Show(
                    "Time Series Lab installed successfully.\n\nRestart Excel to see the Time Series Lab ribbon tab.",
                    "Installation Complete",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                StatusText.Text = $"Installation failed: {ex.Message}";
                MessageBox.Show(
                    $"Installation failed:\n\n{ex.Message}\n\n{ex.StackTrace}",
                    "Installation Error",
                    MessageBoxButton.OK,
                    MessageBoxImage.Error);
            }
            finally
            {
                InstallButton.IsEnabled = true;
                UninstallButton.IsEnabled = true;
            }
        }

        private void RunInstall()
        {
            UpdateProgress(0, "Creating directories...");

            // Create directory structure
            Directory.CreateDirectory(InstallBase);
            Directory.CreateDirectory(Path.Combine(InstallBase, "addin"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "engine"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "engine", "runtime"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "engine", "techniques"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "resources", "catalog"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "resources", "techniques_md"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "docs"));
            Directory.CreateDirectory(Path.Combine(InstallBase, "logs"));

            UpdateProgress(10, "Copying add-in files...");

            // Copy add-in files from source directory (alongside installer)
            var sourceDir = AppDomain.CurrentDomain.BaseDirectory;
            var addinSource = Path.Combine(sourceDir, "addin");
            if (Directory.Exists(addinSource))
            {
                CopyDirectory(addinSource, Path.Combine(InstallBase, "addin"));
            }

            UpdateProgress(30, "Copying engine files...");

            // Copy engine files
            var engineSource = Path.Combine(sourceDir, "engine");
            if (Directory.Exists(engineSource))
            {
                CopyDirectory(engineSource, Path.Combine(InstallBase, "engine"));
            }

            UpdateProgress(50, "Copying resources...");

            // Copy resources
            var resourcesSource = Path.Combine(sourceDir, "resources");
            if (Directory.Exists(resourcesSource))
            {
                CopyDirectory(resourcesSource, Path.Combine(InstallBase, "resources"));
            }

            UpdateProgress(60, "Copying documentation...");

            // Copy docs
            var docsSource = Path.Combine(sourceDir, "docs");
            if (Directory.Exists(docsSource))
            {
                CopyDirectory(docsSource, Path.Combine(InstallBase, "docs"));
            }

            UpdateProgress(70, "Extracting Python runtime...");

            // Extract Python runtime if zip exists
            var runtimeZip = Path.Combine(sourceDir, "python_runtime.zip");
            if (File.Exists(runtimeZip))
            {
                var runtimeDir = Path.Combine(InstallBase, "engine", "runtime");
                if (!File.Exists(Path.Combine(runtimeDir, "python.exe")))
                {
                    ZipFile.ExtractToDirectory(runtimeZip, runtimeDir);
                }
            }

            UpdateProgress(85, "Registering Excel auto-load...");

            // Register XLL in Excel
            RegisterExcelAutoLoad();

            UpdateProgress(100, "Done!");
        }

        private void RegisterExcelAutoLoad()
        {
            var xllPath = Path.Combine(InstallBase, "addin", "TimeSeriesLab-AddIn64.xll");

            // Find the path - Excel-DNA packs to -AddIn64.xll for 64-bit
            if (!File.Exists(xllPath))
            {
                xllPath = Path.Combine(InstallBase, "addin", "TSL.AddIn-AddIn64.xll");
            }
            if (!File.Exists(xllPath))
            {
                // Try any .xll file
                var xllFiles = Directory.GetFiles(Path.Combine(InstallBase, "addin"), "*.xll");
                if (xllFiles.Length > 0)
                    xllPath = xllFiles[0];
            }

            var openValue = $"/R \"{xllPath}\"";

            try
            {
                using (var key = Registry.CurrentUser.CreateSubKey(
                    @"Software\Microsoft\Office\16.0\Excel\Options"))
                {
                    if (key == null) return;

                    // Find first unused OPEN slot
                    string openName = "OPEN";
                    for (int i = 0; i < 20; i++)
                    {
                        var name = i == 0 ? "OPEN" : $"OPEN{i}";
                        var existing = key.GetValue(name) as string;

                        if (existing == null)
                        {
                            openName = name;
                            break;
                        }

                        // If already registered, update it
                        if (existing.Contains("TimeSeriesLab") || existing.Contains("TSL.AddIn"))
                        {
                            openName = name;
                            break;
                        }
                    }

                    key.SetValue(openName, openValue);
                }
            }
            catch (Exception ex)
            {
                throw new Exception($"Failed to register auto-load in registry: {ex.Message}", ex);
            }
        }

        private void UnregisterExcelAutoLoad()
        {
            try
            {
                using (var key = Registry.CurrentUser.OpenSubKey(
                    @"Software\Microsoft\Office\16.0\Excel\Options", true))
                {
                    if (key == null) return;

                    foreach (var name in key.GetValueNames())
                    {
                        if (!name.StartsWith("OPEN")) continue;
                        var val = key.GetValue(name) as string;
                        if (val != null && (val.Contains("TimeSeriesLab") || val.Contains("TSL.AddIn")))
                        {
                            key.DeleteValue(name);
                            break;
                        }
                    }
                }
            }
            catch { }
        }

        private async void OnUninstall(object sender, RoutedEventArgs e)
        {
            var result = MessageBox.Show(
                "This will remove Time Series Lab from your computer.\n\nContinue?",
                "Uninstall Time Series Lab",
                MessageBoxButton.YesNo,
                MessageBoxImage.Question);

            if (result != MessageBoxResult.Yes) return;

            try
            {
                await Task.Run(() =>
                {
                    UnregisterExcelAutoLoad();

                    if (Directory.Exists(InstallBase))
                    {
                        try { Directory.Delete(InstallBase, true); }
                        catch { }
                    }
                });

                StatusText.Text = "Uninstalled. Restart Excel to complete removal.";
                MessageBox.Show(
                    "Time Series Lab has been uninstalled.\nRestart Excel to complete removal.",
                    "Uninstall Complete",
                    MessageBoxButton.OK,
                    MessageBoxImage.Information);
            }
            catch (Exception ex)
            {
                MessageBox.Show($"Uninstall error: {ex.Message}", "Error",
                    MessageBoxButton.OK, MessageBoxImage.Error);
            }
        }

        private void OnClose(object sender, RoutedEventArgs e)
        {
            Close();
        }

        private void UpdateProgress(int pct, string message)
        {
            Dispatcher.Invoke(() =>
            {
                ProgressBar.Value = pct;
                ProgressText.Text = message;
            });
        }

        private static void CopyDirectory(string source, string destination)
        {
            Directory.CreateDirectory(destination);

            foreach (var file in Directory.GetFiles(source))
            {
                var destFile = Path.Combine(destination, Path.GetFileName(file));
                File.Copy(file, destFile, true);
            }

            foreach (var dir in Directory.GetDirectories(source))
            {
                var destDir = Path.Combine(destination, Path.GetFileName(dir));
                CopyDirectory(dir, destDir);
            }
        }
    }
}
