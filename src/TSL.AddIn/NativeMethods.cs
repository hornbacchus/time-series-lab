using System;
using System.Runtime.InteropServices;
using System.Text;
using Microsoft.Win32.SafeHandles;

namespace TSL.AddIn
{
    /// <summary>
    /// The Win32 calls the add-in uses to identify, contain and clean up its engine
    /// process (A2 Part 1). Kept free of ExcelDna, AddIn and Logger references so the
    /// helpers can be exercised outside Excel.
    /// </summary>
    internal static class NativeMethods
    {
        internal const uint PROCESS_TERMINATE = 0x0001;
        internal const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
        internal const uint SYNCHRONIZE = 0x00100000;

        internal const int ERROR_ACCESS_DENIED = 5;
        internal const int ERROR_INVALID_PARAMETER = 87;

        internal const uint WAIT_OBJECT_0 = 0x00000000;
        internal const uint WAIT_TIMEOUT = 0x00000102;

        internal const int JobObjectExtendedLimitInformation = 9;
        internal const uint JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000;

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern SafeProcessHandle OpenProcess(uint desiredAccess, bool inheritHandle, int processId);

        // FILETIME is two DWORDs; marshalled as a little-endian 64-bit value.
        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool GetProcessTimes(SafeProcessHandle process,
            out long creationTime, out long exitTime, out long kernelTime, out long userTime);

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "QueryFullProcessImageNameW")]
        internal static extern bool QueryFullProcessImageName(SafeProcessHandle process, int flags,
            StringBuilder exeName, ref int size);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern uint WaitForSingleObject(SafeProcessHandle handle, uint milliseconds);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool TerminateProcess(SafeProcessHandle process, uint exitCode);

        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "CreateJobObjectW")]
        internal static extern SafeJobHandle CreateJobObject(IntPtr jobAttributes, string name);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool SetInformationJobObject(SafeJobHandle job, int infoClass,
            ref JOBOBJECT_EXTENDED_LIMIT_INFORMATION info, int length);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool AssignProcessToJobObject(SafeJobHandle job, SafeProcessHandle process);

        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool CloseHandle(IntPtr handle);

        // The process that created the server end of a connected pipe (Vista and later).
        [DllImport("kernel32.dll", SetLastError = true)]
        internal static extern bool GetNamedPipeServerProcessId(SafePipeHandle pipe, out uint serverProcessId);

        // Resolves a bare executable name the way Windows' process search order does
        // (application folder, system folders, PATH). Returns 0 when not found.
        [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode, EntryPoint = "SearchPathW")]
        internal static extern int SearchPath(string path, string fileName, string extension,
            int bufferLength, StringBuilder buffer, IntPtr filePart);

        [StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        internal struct JOBOBJECT_BASIC_LIMIT_INFORMATION
        {
            public long PerProcessUserTimeLimit;
            public long PerJobUserTimeLimit;
            public uint LimitFlags;
            public UIntPtr MinimumWorkingSetSize;
            public UIntPtr MaximumWorkingSetSize;
            public uint ActiveProcessLimit;
            public UIntPtr Affinity;
            public uint PriorityClass;
            public uint SchedulingClass;
        }

        [StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        internal struct IO_COUNTERS
        {
            public ulong ReadOperationCount;
            public ulong WriteOperationCount;
            public ulong OtherOperationCount;
            public ulong ReadTransferCount;
            public ulong WriteTransferCount;
            public ulong OtherTransferCount;
        }

        [StructLayout(System.Runtime.InteropServices.LayoutKind.Sequential)]
        internal struct JOBOBJECT_EXTENDED_LIMIT_INFORMATION
        {
            public JOBOBJECT_BASIC_LIMIT_INFORMATION BasicLimitInformation;
            public IO_COUNTERS IoInfo;
            public UIntPtr ProcessMemoryLimit;
            public UIntPtr JobMemoryLimit;
            public UIntPtr PeakProcessMemoryUsed;
            public UIntPtr PeakJobMemoryUsed;
        }

        /// <summary>A process's creation time as UTC ticks, or null if it cannot be read.</summary>
        internal static long? TryGetStartUtcTicks(SafeProcessHandle process)
        {
            if (process == null || process.IsInvalid) return null;
            if (!GetProcessTimes(process, out var creation, out _, out _, out _)) return null;
            try { return DateTime.FromFileTimeUtc(creation).Ticks; }
            catch { return null; }
        }

        /// <summary>A process's full image path, or null if it cannot be read.</summary>
        internal static string TryGetImagePath(SafeProcessHandle process)
        {
            if (process == null || process.IsInvalid) return null;
            var buffer = new StringBuilder(1024);
            int size = buffer.Capacity;
            return QueryFullProcessImageName(process, 0, buffer, ref size) ? buffer.ToString(0, size) : null;
        }
    }

    /// <summary>A job-object handle; closing it ends every process in a kill-on-close job.</summary>
    internal sealed class SafeJobHandle : SafeHandleZeroOrMinusOneIsInvalid
    {
        private SafeJobHandle() : base(true) { }

        protected override bool ReleaseHandle() => NativeMethods.CloseHandle(handle);
    }
}
