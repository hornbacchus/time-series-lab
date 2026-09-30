using System;
using System.IO;
using System.Security.AccessControl;
using System.Text;
using System.Threading;

namespace TSL.AddIn
{
    /// <summary>
    /// Simple file logger for the add-in. Writes to %LOCALAPPDATA%\TimeSeriesLab\logs\.
    /// </summary>
    public static class Logger
    {
        private static readonly object _lock = new object();

        // This Excel's PID on every line: each Excel instance runs its own engine (A2),
        // and all of them write to the same daily file.
        private static readonly int _excelPid = System.Diagnostics.Process.GetCurrentProcess().Id;

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
            var bytes = Encoding.UTF8.GetBytes(
                $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [{level}] [Excel {_excelPid}] {message}{Environment.NewLine}");
            lock (_lock)
            {
                for (var attempt = 1; ; attempt++)
                {
                    try
                    {
                        // Append-only access, shared: another Excel appending at the same
                        // moment neither blocks this line nor is overwritten by it - each
                        // write lands at the end of the file.
                        using (var stream = new FileStream(LogFilePath, FileMode.Append, FileSystemRights.AppendData,
                                   FileShare.ReadWrite | FileShare.Delete, 4096, FileOptions.None))
                            stream.Write(bytes, 0, bytes.Length);
                        return;
                    }
                    catch (IOException) when (attempt < 3)
                    {
                        Thread.Sleep(15);
                    }
                    catch
                    {
                        // Logging should never crash the add-in
                        return;
                    }
                }
            }
        }
    }
}
