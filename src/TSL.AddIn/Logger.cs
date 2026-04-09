using System;
using System.IO;

namespace TSL.AddIn
{
    /// <summary>
    /// Simple file logger for the add-in. Writes to %LOCALAPPDATA%\TimeSeriesLab\logs\.
    /// </summary>
    public static class Logger
    {
        private static readonly object _lock = new object();

        private static string LogFilePath
        {
            get
            {
                var dir = Path.Combine(AddIn.AppDataPath, "logs");
                Directory.CreateDirectory(dir);
                return Path.Combine(dir, $"tsl_{DateTime.Now:yyyyMMdd}.log");
            }
        }

        public static void Info(string message) => Log("INFO", message);
        public static void Warn(string message) => Log("WARN", message);
        public static void Error(string message) => Log("ERROR", message);

        public static void Error(string message, Exception ex)
        {
            Log("ERROR", $"{message} | {ex.GetType().Name}: {ex.Message}");
            Log("ERROR", $"  Stack: {ex.StackTrace}");
        }

        private static void Log(string level, string message)
        {
            var line = $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [{level}] {message}";
            lock (_lock)
            {
                try
                {
                    File.AppendAllText(LogFilePath, line + Environment.NewLine);
                }
                catch
                {
                    // Logging should never crash the add-in
                }
            }
        }
    }
}
