using System;
using System.Diagnostics;
using System.IO;
using System.Management;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;
using Newtonsoft.Json;

namespace TSL.AddIn
{
    /// <summary>
    /// The engine records on disk, the facts read about live processes, and the
    /// orphan sweep that runs at AutoOpen (A2 Part 1). The rules themselves are in
    /// EngineIdentity; this class only gathers facts and acts on the verdicts. Free
    /// of ExcelDna, AddIn and Logger references (paths and a log callback are passed
    /// in), so it can run outside Excel.
    /// </summary>
    internal static class EngineRegistry
    {
        public const string RecordsFolder = "engines";
        public const string LegacyPidFileName = "engine.pid";

        public static string RecordFileName(int excelPid, long excelStartUtcTicks) =>
            $"{excelPid}-{excelStartUtcTicks}.json";

        // ── Records ──────────────────────────────────────────────────────

        /// <summary>Write a record through a temporary file, so a reader never sees half of one.</summary>
        public static void WriteRecord(string path, EngineRecord record)
        {
            Directory.CreateDirectory(Path.GetDirectoryName(path));
            var temp = path + ".tmp";
            File.WriteAllText(temp, JsonConvert.SerializeObject(record, Formatting.Indented));
            if (File.Exists(path))
                File.Replace(temp, path, null);
            else
                File.Move(temp, path);
        }

        public static EngineRecord ReadRecord(string path) =>
            JsonConvert.DeserializeObject<EngineRecord>(File.ReadAllText(path));

        public static void DeleteRecord(string path)
        {
            try { if (!string.IsNullOrEmpty(path) && File.Exists(path)) File.Delete(path); }
            catch { /* best-effort */ }
        }

        // ── Facts about processes ────────────────────────────────────────

        /// <summary>This process's PID and creation time (UTC ticks).</summary>
        public static void GetCurrentProcessIdentity(out int pid, out long startUtcTicks)
        {
            using (var me = Process.GetCurrentProcess())
            {
                pid = me.Id;
                long? ticks = null;
                using (var h = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION, false, pid))
                    ticks = NativeMethods.TryGetStartUtcTicks(h);
                startUtcTicks = ticks ?? me.StartTime.ToUniversalTime().Ticks;
            }
        }

        /// <summary>
        /// Is the Excel that owns a record still running? True only for the same PID with
        /// the same creation time; false when that PID is gone or now belongs to another
        /// process; null when it cannot be told.
        /// </summary>
        public static bool? IsOwnerAlive(int excelPid, long excelStartUtcTicks)
        {
            using (var h = NativeMethods.OpenProcess(
                NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION | NativeMethods.SYNCHRONIZE, false, excelPid))
            {
                if (h.IsInvalid)
                    return Marshal.GetLastWin32Error() == NativeMethods.ERROR_INVALID_PARAMETER ? false : (bool?)null;
                if (NativeMethods.WaitForSingleObject(h, 0) == NativeMethods.WAIT_OBJECT_0)
                    return false;
                var start = NativeMethods.TryGetStartUtcTicks(h);
                if (start == null) return null;
                return start.Value == excelStartUtcTicks;
            }
        }

        /// <summary>
        /// Open a process and read its facts. The returned handle (null when the process
        /// could not be opened) pins the process, so its PID cannot be reused between
        /// these reads and a kill through the same handle.
        /// </summary>
        public static ProcessFacts Observe(int pid, out SafeProcessHandle handle)
        {
            handle = NativeMethods.OpenProcess(
                NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION | NativeMethods.SYNCHRONIZE | NativeMethods.PROCESS_TERMINATE,
                false, pid);
            if (handle.IsInvalid)
            {
                var error = Marshal.GetLastWin32Error();
                handle.Dispose();
                handle = null;
                if (error == NativeMethods.ERROR_INVALID_PARAMETER)
                    return new ProcessFacts { Exists = false };
                if (error == NativeMethods.ERROR_ACCESS_DENIED)
                {
                    // Readable but not ours to end: gather the facts anyway (the kill will be refused).
                    handle = NativeMethods.OpenProcess(
                        NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION | NativeMethods.SYNCHRONIZE, false, pid);
                    if (handle.IsInvalid) { handle.Dispose(); handle = null; return new ProcessFacts { Exists = null }; }
                }
                else
                {
                    return new ProcessFacts { Exists = null };
                }
            }

            if (NativeMethods.WaitForSingleObject(handle, 0) == NativeMethods.WAIT_OBJECT_0)
                return new ProcessFacts { Exists = false };

            return new ProcessFacts
            {
                Exists = true,
                StartUtcTicks = NativeMethods.TryGetStartUtcTicks(handle),
                ImagePath = NativeMethods.TryGetImagePath(handle),
                CommandLine = TryReadCommandLine(pid),
            };
        }

        /// <summary>A process's command line through WMI, or null if it cannot be read.</summary>
        public static string TryReadCommandLine(int pid)
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher(
                    "SELECT CommandLine FROM Win32_Process WHERE ProcessId = " + pid))
                using (var results = searcher.Get())
                {
                    foreach (ManagementObject mo in results)
                        using (mo)
                            return mo["CommandLine"] as string;
                }
            }
            catch
            {
                // WMI unavailable or access denied: unreadable.
            }
            return null;
        }

        /// <summary>A bare executable name resolved through Windows' search order, or null.</summary>
        public static string SearchExecutable(string fileName)
        {
            var buffer = new StringBuilder(1024);
            var length = NativeMethods.SearchPath(null, fileName, null, buffer.Capacity, buffer, IntPtr.Zero);
            return length > 0 && length < buffer.Capacity ? buffer.ToString(0, length) : null;
        }

        private static bool TryKill(SafeProcessHandle handle, out string problem)
        {
            problem = null;
            if (handle == null || handle.IsInvalid) { problem = "no handle"; return false; }
            if (!NativeMethods.TerminateProcess(handle, 1))
            {
                problem = "TerminateProcess failed (error " + Marshal.GetLastWin32Error() + ")";
                return false;
            }
            NativeMethods.WaitForSingleObject(handle, 2000);
            return true;
        }

        // ── The sweep ────────────────────────────────────────────────────

        /// <summary>
        /// Visit every engine record (and a pre-A2 engine.pid, once) and act on the
        /// verdict: kill only a proven orphan of this build; otherwise leave the process
        /// alone. A record is deleted only when its engine is gone (or was just killed).
        /// Runs on a background thread started at AutoOpen; never throws.
        /// </summary>
        public static void Sweep(string stateDir, string legacyPipeName, string expectedExe,
            string expectedWorker, Action<string> log)
        {
            log = log ?? (_ => { });
            var recordsDir = Path.Combine(stateDir, RecordsFolder);
            try
            {
                if (Directory.Exists(recordsDir))
                {
                    foreach (var file in Directory.GetFiles(recordsDir, "*.json"))
                        SweepRecord(file, expectedExe, expectedWorker, log);
                }
            }
            catch (Exception ex)
            {
                log($"record sweep stopped: {ex.GetType().Name}: {ex.Message}");
            }

            try
            {
                var legacy = Path.Combine(stateDir, LegacyPidFileName);
                if (File.Exists(legacy))
                    SweepLegacy(legacy, legacyPipeName, expectedExe, expectedWorker, log);
            }
            catch (Exception ex)
            {
                log($"legacy engine.pid check stopped: {ex.GetType().Name}: {ex.Message}");
            }
        }

        private static void SweepRecord(string file, string expectedExe, string expectedWorker, Action<string> log)
        {
            var name = Path.GetFileName(file);
            EngineRecord record;
            try
            {
                record = ReadRecord(file);
            }
            catch (Exception ex)
            {
                log($"{name}: unreadable ({ex.Message}); deleted, nothing killed.");
                DeleteRecord(file);
                return;
            }
            if (record == null || record.EnginePid <= 0)
            {
                log($"{name}: empty record; deleted, nothing killed.");
                DeleteRecord(file);
                return;
            }

            var ownerAlive = IsOwnerAlive(record.ExcelPid, record.ExcelStartUtcTicks);
            if (ownerAlive == true)
            {
                log($"{name}: kept - {EngineIdentity.DecideOrphan(record, true, null, expectedExe, expectedWorker).Reason}.");
                return;
            }

            SafeProcessHandle handle = null;
            try
            {
                var facts = Observe(record.EnginePid, out handle);
                var verdict = EngineIdentity.DecideOrphan(record, ownerAlive, facts, expectedExe, expectedWorker);
                switch (verdict.Action)
                {
                    case OrphanAction.Kill:
                        if (TryKill(handle, out var problem))
                        {
                            log($"{name}: KILLED engine PID {record.EnginePid} - {verdict.Reason}.");
                            DeleteRecord(file);
                        }
                        else
                        {
                            log($"{name}: kill of PID {record.EnginePid} failed ({problem}); record kept.");
                        }
                        break;
                    case OrphanAction.EngineGone:
                        log($"{name}: deleted, nothing killed - {verdict.Reason}.");
                        DeleteRecord(file);
                        break;
                    default:
                        log($"{name}: NOT killed ({verdict.Action}) - {verdict.Reason}; record kept.");
                        break;
                }
            }
            finally
            {
                handle?.Dispose();
            }
        }

        private static void SweepLegacy(string file, string legacyPipeName, string expectedExe,
            string expectedWorker, Action<string> log)
        {
            string text = null;
            try { text = File.ReadAllText(file).Trim(); } catch { }
            if (!int.TryParse(text, out var pid) || pid <= 0)
            {
                log($"engine.pid: unreadable ('{text}'); deleted, nothing killed.");
                DeleteRecord(file);
                return;
            }

            SafeProcessHandle handle = null;
            try
            {
                var facts = Observe(pid, out handle);
                var verdict = EngineIdentity.DecideLegacy(pid, facts, expectedExe, expectedWorker, legacyPipeName);
                if (verdict.Action == OrphanAction.Kill)
                {
                    if (TryKill(handle, out var problem))
                        log($"engine.pid: KILLED PID {pid} - {verdict.Reason}.");
                    else
                        log($"engine.pid: kill of PID {pid} failed ({problem}).");
                }
                else
                {
                    log($"engine.pid: PID {pid} NOT killed ({verdict.Action}) - {verdict.Reason}.");
                }
            }
            finally
            {
                handle?.Dispose();
                // Handled once: a pre-A2 PID file is never consulted again.
                DeleteRecord(file);
            }
        }
    }

    /// <summary>
    /// A Windows job object with kill-on-close: every process assigned to it ends when
    /// the last handle closes - when this Excel exits for any reason (normal close,
    /// Task Manager, crash), or when the add-in disposes it.
    /// </summary>
    internal sealed class EngineJob : IDisposable
    {
        private readonly SafeJobHandle _handle;

        private EngineJob(SafeJobHandle handle)
        {
            _handle = handle;
        }

        /// <summary>Create the job; null (with <paramref name="problem"/>) if Windows refuses.</summary>
        public static EngineJob Create(out string problem)
        {
            problem = null;
            var handle = NativeMethods.CreateJobObject(IntPtr.Zero, null);
            if (handle.IsInvalid)
            {
                problem = "CreateJobObject failed (error " + Marshal.GetLastWin32Error() + ")";
                handle.Dispose();
                return null;
            }

            var info = new NativeMethods.JOBOBJECT_EXTENDED_LIMIT_INFORMATION();
            info.BasicLimitInformation.LimitFlags = NativeMethods.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE;
            if (!NativeMethods.SetInformationJobObject(handle, NativeMethods.JobObjectExtendedLimitInformation,
                    ref info, Marshal.SizeOf(typeof(NativeMethods.JOBOBJECT_EXTENDED_LIMIT_INFORMATION))))
            {
                problem = "SetInformationJobObject failed (error " + Marshal.GetLastWin32Error() + ")";
                handle.Dispose();
                return null;
            }
            return new EngineJob(handle);
        }

        public bool TryAssign(Process process, out string problem)
        {
            problem = null;
            if (NativeMethods.AssignProcessToJobObject(_handle, process.SafeHandle))
                return true;
            problem = "AssignProcessToJobObject failed (error " + Marshal.GetLastWin32Error() + ")";
            return false;
        }

        public void Dispose() => _handle.Dispose();
    }
}
