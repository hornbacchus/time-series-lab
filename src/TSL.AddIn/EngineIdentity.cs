using System;
using System.IO;
using System.Text;
using Newtonsoft.Json.Linq;

namespace TSL.AddIn
{
    /// <summary>
    /// What the add-in records about an engine it starts, so a later Excel start can
    /// tell a genuine orphan of this build from anything else. One file per Excel
    /// instance: %LOCALAPPDATA%\TimeSeriesLab\engines\&lt;ExcelPID&gt;-&lt;ExcelStartTicks&gt;.json
    /// (replaces the per-user engine.pid). Times are UTC ticks of process creation.
    /// </summary>
    internal sealed class EngineRecord
    {
        public int ExcelPid { get; set; }
        public long ExcelStartUtcTicks { get; set; }
        public int EnginePid { get; set; }
        public long EngineStartUtcTicks { get; set; }
        public string ExePath { get; set; }
        public string WorkerPath { get; set; }
        public string PipeName { get; set; }
        public string Stamp { get; set; }
        public string LayoutRoot { get; set; }
    }

    /// <summary>What could be observed about a process; null means it could not be read.</summary>
    internal sealed class ProcessFacts
    {
        public bool? Exists { get; set; }
        public long? StartUtcTicks { get; set; }
        public string ImagePath { get; set; }
        public string CommandLine { get; set; }
    }

    internal enum OrphanAction
    {
        /// <summary>Its Excel is still running: not an orphan. Keep the record.</summary>
        KeepOwnerRunning,
        /// <summary>A proven orphan of this build: kill it, then delete the record.</summary>
        Kill,
        /// <summary>Not proven: leave the process alone and keep the record.</summary>
        Refuse,
        /// <summary>The recorded engine no longer exists: delete the record.</summary>
        EngineGone,
        /// <summary>The record belongs to another build: leave it for that build.</summary>
        OtherBuild,
    }

    internal sealed class OrphanVerdict
    {
        public OrphanVerdict(OrphanAction action, string reason)
        {
            Action = action;
            Reason = reason;
        }

        public OrphanAction Action { get; }
        public string Reason { get; }

        public override string ToString() => $"{Action}: {Reason}";
    }

    /// <summary>
    /// The pure rules of engine identity (A2 Part 1): the per-instance pipe name, the
    /// decision whether a recorded engine may be killed, and the identity handshake's
    /// reply check and refusal text. No I/O and no ExcelDna,
    /// AddIn or Logger references, so every branch can be exercised outside Excel.
    /// </summary>
    internal static class EngineIdentity
    {
        /// <summary>The per-user pipe prefix every build before A2 used (TSL_ENGINE_PIPE_&lt;SID&gt;).</summary>
        public const string LegacyPipePrefix = "TSL_ENGINE_PIPE_";

        private const int MaxBuildTokenLength = 64;

        /// <summary>
        /// TSL_ENGINE_&lt;SID&gt;_&lt;ExcelPID&gt;_&lt;buildToken&gt;_&lt;nonce&gt;: one pipe per Excel
        /// instance and per build. The nonce (fresh per EngineClient) makes the name
        /// unguessable, so no other process can create it first.
        /// </summary>
        public static string BuildPipeName(string sid, int excelPid, string stamp, string nonce)
        {
            var sidPart = Keep(sid, 128);
            var noncePart = Keep(nonce, 32);
            return "TSL_ENGINE_" + (sidPart.Length > 0 ? sidPart : "nosid") + "_" + excelPid + "_" +
                   BuildToken(stamp) + "_" + (noncePart.Length > 0 ? noncePart : "0");
        }

        /// <summary>
        /// The describe part of a build stamp (the text before " / ", once the stamp
        /// carries a build time), reduced to [A-Za-z0-9-] and capped in length.
        /// </summary>
        public static string BuildToken(string stamp)
        {
            var describe = stamp ?? "";
            var cut = describe.IndexOf(" / ", StringComparison.Ordinal);
            if (cut >= 0) describe = describe.Substring(0, cut);
            var token = Keep(describe, MaxBuildTokenLength);
            return token.Length > 0 ? token : "unstamped";
        }

        private static string Keep(string text, int maxLength)
        {
            var sb = new StringBuilder();
            foreach (var ch in text ?? "")
            {
                if ((ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '-')
                    sb.Append(ch);
                if (sb.Length == maxLength) break;
            }
            return sb.ToString();
        }

        /// <summary>
        /// May the engine named by <paramref name="record"/> be killed? Only when its Excel
        /// is gone and the process is provably this build's engine: same start time
        /// (a reused PID fails), this build's interpreter as its image, and a command
        /// line that runs this build's engine_worker.py on the recorded pipe. Anything
        /// that cannot be read refuses.
        /// </summary>
        public static OrphanVerdict DecideOrphan(EngineRecord record, bool? ownerAlive, ProcessFacts engine,
            string expectedExe, string expectedWorker)
        {
            if (record == null)
                return new OrphanVerdict(OrphanAction.Refuse, "the record could not be read");

            var pid = record.EnginePid;

            if (ownerAlive == true)
                return new OrphanVerdict(OrphanAction.KeepOwnerRunning,
                    $"its Excel (PID {record.ExcelPid}) is still running");
            if (ownerAlive == null)
                return new OrphanVerdict(OrphanAction.Refuse,
                    $"could not tell whether its Excel (PID {record.ExcelPid}) is still running");

            if (engine == null || engine.Exists == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not tell whether engine PID {pid} is running");
            if (engine.Exists == false)
                return new OrphanVerdict(OrphanAction.EngineGone, $"engine PID {pid} is no longer running");

            if (engine.StartUtcTicks == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not read the start time of PID {pid}");
            if (engine.StartUtcTicks.Value != record.EngineStartUtcTicks)
                return new OrphanVerdict(OrphanAction.EngineGone,
                    $"PID {pid} now belongs to a different process (its start time differs), so the recorded engine is gone");

            if (string.IsNullOrEmpty(expectedExe) || string.IsNullOrEmpty(expectedWorker))
                return new OrphanVerdict(OrphanAction.Refuse,
                    "this build's interpreter or engine_worker.py could not be resolved");
            if (!SamePath(record.ExePath, expectedExe) || !SamePath(record.WorkerPath, expectedWorker))
                return new OrphanVerdict(OrphanAction.OtherBuild,
                    $"the record belongs to another build ({record.ExePath}; {record.WorkerPath})");

            if (engine.ImagePath == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not read the image path of PID {pid}");
            if (!SamePath(engine.ImagePath, expectedExe))
                return new OrphanVerdict(OrphanAction.Refuse,
                    $"PID {pid} runs {engine.ImagePath}, not this build's interpreter {expectedExe}");

            if (engine.CommandLine == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not read the command line of PID {pid}");
            if (!CommandLineRuns(engine.CommandLine, expectedWorker, record.PipeName))
                return new OrphanVerdict(OrphanAction.Refuse,
                    $"PID {pid}'s command line does not run {expectedWorker} with --pipe \"{record.PipeName}\"");

            return new OrphanVerdict(OrphanAction.Kill,
                $"PID {pid} is this build's engine (start time, image path and command line match) and its Excel is gone");
        }

        /// <summary>
        /// The one-time rule for a pre-A2 engine.pid, which recorded only a PID: kill only
        /// a process running this build's interpreter on this build's engine_worker.py
        /// with the old per-user pipe name. The file is deleted whatever the verdict.
        /// </summary>
        public static OrphanVerdict DecideLegacy(int pid, ProcessFacts engine, string expectedExe,
            string expectedWorker, string legacyPipeName)
        {
            if (engine == null || engine.Exists == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not tell whether PID {pid} is running");
            if (engine.Exists == false)
                return new OrphanVerdict(OrphanAction.EngineGone, $"PID {pid} is no longer running");

            if (string.IsNullOrEmpty(expectedExe) || string.IsNullOrEmpty(expectedWorker))
                return new OrphanVerdict(OrphanAction.Refuse,
                    "this build's interpreter or engine_worker.py could not be resolved");

            if (engine.ImagePath == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not read the image path of PID {pid}");
            if (!SamePath(engine.ImagePath, expectedExe))
                return new OrphanVerdict(OrphanAction.Refuse,
                    $"PID {pid} runs {engine.ImagePath}, not this build's interpreter {expectedExe}");

            if (engine.CommandLine == null)
                return new OrphanVerdict(OrphanAction.Refuse, $"could not read the command line of PID {pid}");
            if (!CommandLineRuns(engine.CommandLine, expectedWorker, legacyPipeName))
                return new OrphanVerdict(OrphanAction.Refuse,
                    $"PID {pid}'s command line does not run {expectedWorker} with --pipe \"{legacyPipeName}\"");

            return new OrphanVerdict(OrphanAction.Kill,
                $"PID {pid} is a pre-A2 engine of this build (image path and command line match)");
        }

        /// <summary>
        /// True when a command line runs the quoted worker script with the quoted pipe
        /// name, as EngineClient starts it: "&lt;python&gt;" "&lt;worker&gt;" --pipe "&lt;pipe&gt;".
        /// </summary>
        public static bool CommandLineRuns(string commandLine, string worker, string pipeName)
        {
            if (string.IsNullOrEmpty(commandLine) || string.IsNullOrEmpty(worker) || string.IsNullOrEmpty(pipeName))
                return false;
            return commandLine.IndexOf("\"" + worker + "\"", StringComparison.OrdinalIgnoreCase) >= 0 &&
                   commandLine.IndexOf("--pipe \"" + pipeName + "\"", StringComparison.Ordinal) >= 0;
        }

        // ── Identity handshake (A2 Part 1(c)) ───────────────────────────

        /// <summary>
        /// Read engine_versions.engine_version from the engine's reply to the identity
        /// probe. True only for a final (non-progress) JSON object that reports a
        /// non-empty engine_version string; anything else fails closed, with
        /// <paramref name="problem"/> saying why.
        /// </summary>
        public static bool TryParseHandshakeReply(string json, out string engineVersion, out string problem)
        {
            engineVersion = null;
            problem = null;
            if (string.IsNullOrWhiteSpace(json))
            {
                problem = "the engine's reply was empty";
                return false;
            }

            JObject reply;
            try
            {
                reply = JObject.Parse(json);
            }
            catch (Exception ex)
            {
                problem = "the engine's reply is not a JSON object (" + ex.Message + ")";
                return false;
            }

            if (IsProgress(reply))
            {
                problem = "the engine sent a progress event, not a reply";
                return false;
            }
            if (!(reply["engine_versions"] is JObject versions))
            {
                problem = "the engine's reply carries no engine_versions";
                return false;
            }
            var version = versions["engine_version"];
            if (version == null || version.Type != JTokenType.String || string.IsNullOrWhiteSpace((string)version))
            {
                problem = "the engine's reply carries no engine_version";
                return false;
            }

            engineVersion = ((string)version).Trim();
            return true;
        }

        /// <summary>True for a frame whose "type" is "progress" (skipped while waiting for a reply).</summary>
        public static bool IsProgressFrame(string json)
        {
            try { return IsProgress(JObject.Parse(json)); }
            catch { return false; }
        }

        private static bool IsProgress(JObject frame)
        {
            var type = frame["type"];
            return type != null && type.Type == JTokenType.String &&
                   string.Equals((string)type, "progress", StringComparison.OrdinalIgnoreCase);
        }

        /// <summary>
        /// The engine_version this add-in accepts. Installed layout: exactly the add-in's
        /// build stamp (build_pack writes it into the packed engine\VERSION.txt, which
        /// the engine reports). Development tree: the repository's engine\VERSION.txt
        /// (R6 keeps it 0.1.0; the server-PID check carries identity there). Anything
        /// else: null, which fails closed.
        /// </summary>
        public static string ExpectedEngineVersion(LayoutKind kind, string stamp, string devVersionFileText)
        {
            switch (kind)
            {
                case LayoutKind.Installed:
                    return string.IsNullOrWhiteSpace(stamp) ? null : stamp.Trim();
                case LayoutKind.Development:
                    return string.IsNullOrWhiteSpace(devVersionFileText) ? null : devVersionFileText.Trim();
                default:
                    return null;
            }
        }

        /// <summary>The refusal shown when the engine is not this add-in's (A2 Part 1(c), verbatim).</summary>
        public static string MismatchMessage(string addinBuild, string engineBuild) =>
            "The analysis engine does not match this add-in, so nothing was run.\n\n" +
            "Add-in build:\n    " + addinBuild + "\n" +
            "Engine build:\n    " + engineBuild + "\n\n" +
            "Close Excel and start it again. If this message returns, tell Matthew Hornbach.";

        /// <summary>
        /// The refusal shown when the engine stopped, or did not open its pipe or answer,
        /// while starting - a start failure, not an identity mismatch.
        /// </summary>
        public static string EngineStartMessage(bool engineStopped, string logsFolder) =>
            (engineStopped
                ? "The analysis engine stopped while it was starting, so nothing was run.\n\n"
                : "The analysis engine did not start in time, so nothing was run.\n\n") +
            "The log has the details:\n    " + logsFolder + "\n\n" +
            "Try again. If this message returns, tell Matthew Hornbach.";

        /// <summary>
        /// The refusal shown when the engine stayed busy with another run (e.g. other
        /// Time Series Lab formulas recalculating) for the whole connect budget.
        /// </summary>
        public static string EngineBusyMessage(int seconds) =>
            $"The analysis engine was busy with another run for {seconds} seconds, so this run was not started.\n\n" +
            "Try again when the current run has finished.";

        /// <summary>Full-path, case-insensitive comparison; false when either side is missing or invalid.</summary>
        public static bool SamePath(string a, string b)
        {
            if (string.IsNullOrEmpty(a) || string.IsNullOrEmpty(b)) return false;
            try
            {
                return string.Equals(Path.GetFullPath(a), Path.GetFullPath(b), StringComparison.OrdinalIgnoreCase);
            }
            catch
            {
                return false;
            }
        }
    }
}
