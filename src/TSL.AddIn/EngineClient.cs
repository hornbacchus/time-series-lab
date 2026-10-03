using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using ExcelDna.Integration;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using TSL.AddIn.Models;
using TSL.UI;

namespace TSL.AddIn
{
    /// <summary>
    /// Manages the Python engine worker process and communicates via Named Pipes.
    /// </summary>
    public class EngineClient : IDisposable
    {
        /// <summary>
        /// One started engine: its process, the pipe name made for this start alone, and
        /// the engine_version it proved at the identity handshake (null until then).
        /// </summary>
        private sealed class EngineSession
        {
            public EngineSession(Process process, string pipeName)
            {
                Process = process;
                Pid = process.Id;
                PipeName = pipeName;
            }

            public Process Process { get; }
            public int Pid { get; }
            public string PipeName { get; }
            public string Version { get; set; }

            public bool IsAlive
            {
                get
                {
                    try { return !Process.HasExited; }
                    catch { return false; }
                }
            }
        }

        private readonly string _sid;
        private readonly string _legacyPipeName;
        private readonly int _excelPid;
        private readonly long _excelStartUtcTicks;
        private EngineJob _job;
        private string _recordPath;
        private CancellationTokenSource _currentRunCts;
        private readonly object _lock = new object();
        private bool _disposed;

        // The engine this client started most recently (starting or running); cleared
        // when it is stopped. Read without the lock (About, Cancel).
        private EngineSession _session;

        // The same engine once it has passed the identity handshake. Runs connect only
        // to this one, and check every connect and every response against it.
        private EngineSession _verified;

        // Incremented by every cancel. A start that sees it change was cancelled.
        private int _cancelGeneration;

        // Runs between RunAsync's start and its return (task pane and worksheet functions
        // alike), so the ribbon's Cancel can tell "something is running" from "nothing is".
        private int _runsInFlight;

        /// <summary>
        /// True while any run (task pane or worksheet function) is in RunAsync, or an engine
        /// is starting and not yet verified (a worksheet function starts the engine before
        /// it calls RunAsync).
        /// </summary>
        internal bool HasRunsInFlight
        {
            get
            {
                if (Volatile.Read(ref _runsInFlight) > 0) return true;
                var starting = Volatile.Read(ref _session);
                return starting != null && starting.IsAlive && !ReferenceEquals(starting, Volatile.Read(ref _verified));
            }
        }

        // Inter-message (heartbeat) timeout for the response read. It is RESET by
        // EVERY message the engine sends (each progress event proves liveness),
        // so total runtime is unbounded as long as progress keeps flowing — long
        // MCMC / DL runs are fine. Only a SILENT engine (no progress AND no
        // completion) for this whole window is treated as a stall: the engine is
        // killed (so a wedged process is not reused by EnsureRunning) and the run
        // fails cleanly instead of hanging Excel forever with a dead Cancel.
        // This hardens the exact failure mode behind the BVAR 95% completion-
        // handoff deadlock; the BeginInvoke progress-marshal fix removes the known
        // cause, this watchdog bounds any future handoff stall.
        private const int HeartbeatTimeoutMs = 300_000; // 5 minutes

        // How long a run's connect waits for the (already verified) engine's pipe to
        // accept (as before A2). The wait is polled and retried while the single
        // instance is busy or re-arming between requests (EngineHandshake.Connect).
        private const int ConnectTimeoutMs = 10_000;

        // How long an engine START may take to open its pipe (interpreter start-up and
        // imports). Generous, because a cold start competes with Excel's own
        // recalculation; the wait still ends at once if the engine exits or the start
        // is cancelled. An engine that cannot open its pipe in this time is stopped.
        private const int StartConnectTimeoutMs = 60_000;

        public event Action<ProgressEvent> ProgressReceived;

        /// <summary>
        /// One engine per Excel instance and per build (A2 Part 1). Each engine start gets
        /// its own pipe name - this Excel's PID, the build token and a fresh nonce - so a
        /// second Excel, an older build, any other process, or a run still waiting on a
        /// previous engine of this Excel can never reach it.
        /// </summary>
        public EngineClient()
        {
            _sid = WindowsIdentity.GetCurrent().User?.Value ?? "default";
            EngineRegistry.GetCurrentProcessIdentity(out _excelPid, out _excelStartUtcTicks);
            _legacyPipeName = EngineIdentity.LegacyPipePrefix + _sid;
        }

        private static string LogsFolder => Path.Combine(AddIn.AppDataPath, "logs");

        /// <summary>This Excel's engine, for About: "Running (PID n)" or "Not running".</summary>
        public string StatusText
        {
            get
            {
                // No lock: About runs on Excel's thread and must not wait on a start in progress.
                var session = Volatile.Read(ref _session);
                return session != null && session.IsAlive ? $"Running (PID {session.Pid})" : "Not running";
            }
        }

        /// <summary>
        /// THE ONE place the engine interpreter is chosen. Nothing else in the add-in
        /// builds an engine\runtime path (About asks this method; a later side-by-side
        /// update unit relies on that). Installed layout: the bundled runtime
        /// &lt;root&gt;\engine\runtime\python.exe, which MUST exist - a missing runtime
        /// is an error naming the path, never a silent switch to another Python.
        /// Development tree: "python" from PATH (the developer's interpreter), never an
        /// installed runtime. Unrecognised layout: an error naming what was probed.
        /// </summary>
        public static string ResolvePythonExe()
        {
            switch (AddInLayout.Kind)
            {
                case LayoutKind.Installed:
                    var bundled = AddInLayout.PathOf("engine", "runtime", "python.exe");
                    if (!File.Exists(bundled))
                        throw new FileNotFoundException(
                            AddInLayout.MissingMessage("bundled Python runtime", bundled), bundled);
                    return bundled;

                case LayoutKind.Development:
                    return "python";

                default:
                    AddInLayout.FindFile(out var tried, "engine", "runtime", "python.exe");
                    throw new FileNotFoundException(
                        AddInLayout.MissingMessage("engine's Python runtime", tried));
            }
        }

        /// <summary>
        /// The full path of the interpreter this build runs the engine with: the bundled
        /// runtime when installed, or "python" resolved through Windows' search order in
        /// a development tree. Null when it cannot be resolved. The orphan sweep kills
        /// only processes whose image is this path.
        /// </summary>
        internal static string ResolvePythonExeFullPath()
        {
            try
            {
                var exe = ResolvePythonExe();
                return Path.IsPathRooted(exe) ? Path.GetFullPath(exe) : EngineRegistry.SearchExecutable(exe + ".exe");
            }
            catch (FileNotFoundException)
            {
                return null;
            }
        }

        /// <summary>
        /// Clean up engines orphaned by an earlier Excel (one that crashed, or a build
        /// before A2) on a background thread, so Excel's startup never waits for it:
        /// WMI can take seconds on managed machines, and this Excel's pipe names are new,
        /// so nothing depends on the cleanup. Only a proven orphan of this build is
        /// killed (EngineIdentity.DecideOrphan). Every Excel session still starts with a
        /// fresh engine - this instance's own - so updated technique modules load.
        /// </summary>
        public void StartOrphanSweep()
        {
            // Resolve the layout here, on Excel's thread, before handing off.
            var expectedExe = ResolvePythonExeFullPath();
            var expectedWorker = AddInLayout.PathOf("engine", "engine_worker.py");
            var stateDir = AddIn.AppDataPath;
            var legacyPipe = _legacyPipeName;

            var sweep = new Thread(() =>
            {
                try
                {
                    Logger.Info($"[orphan sweep] started (interpreter={expectedExe ?? "(unresolved)"}, " +
                                $"worker={expectedWorker ?? "(unresolved)"}).");
                    EngineRegistry.Sweep(stateDir, legacyPipe, expectedExe, expectedWorker,
                        message => Logger.Info("[orphan sweep] " + message));
                    Logger.Info("[orphan sweep] finished.");
                }
                catch (Exception ex)
                {
                    Logger.Error("[orphan sweep] failed.", ex);
                }
            })
            {
                IsBackground = true,
                Name = "TSL orphan engine sweep",
            };
            sweep.Start();
        }

        /// <summary>
        /// Ensures a verified engine is running. Starts one (and runs its identity
        /// handshake) if not. Never called on Excel's thread.
        /// </summary>
        public void EnsureRunning()
        {
            lock (_lock)
            {
                var verified = Volatile.Read(ref _verified);
                if (verified != null && verified.IsAlive)
                    return;

                StartEngine();
            }
        }

        private void StartEngine()
        {
            var generation = Volatile.Read(ref _cancelGeneration);
            Volatile.Write(ref _verified, null);

            // A missing runtime or worker is a complete house refusal (shown as it is):
            // what was missing and where it looked, then the state and who to tell.
            string pythonExe;
            try
            {
                pythonExe = ResolvePythonExe();
            }
            catch (FileNotFoundException ex)
            {
                throw new EngineStartException(ex.Message + "\n\nNothing was run. " + HouseDialog.TellMatthew);
            }

            // ONE location, from the add-in's layout (AddInLayout): <root>\engine\engine_worker.py.
            var workerScript = AddInLayout.FindFile(out var workerTried, "engine", "engine_worker.py");
            if (workerScript == null)
            {
                throw new EngineStartException(
                    AddInLayout.MissingMessage("engine worker script (engine_worker.py)", workerTried) +
                    "\n\nNothing was run. " + HouseDialog.TellMatthew);
            }

            // A pipe name for this start alone (see the constructor).
            var pipeName = EngineIdentity.BuildPipeName(_sid, _excelPid, BuildInfo.Stamp,
                Guid.NewGuid().ToString("N").Substring(0, 8));

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{workerScript}\" --pipe \"{pipeName}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                WorkingDirectory = Path.GetDirectoryName(workerScript),
            };

            // Set environment to prevent network access
            psi.EnvironmentVariables["TSL_NO_NETWORK"] = "1";
            psi.EnvironmentVariables["TSL_PIPE_NAME"] = pipeName;

            var process = Process.Start(psi);
            if (process == null)
                throw new InvalidOperationException("Failed to start engine process.");
            var session = new EngineSession(process, pipeName);
            Volatile.Write(ref _session, session);

            try
            {
                // Drain the engine's stdout/stderr continuously. Two reasons:
                //  1. CORRECTNESS: both streams are redirected (above); if we never
                //     read them, the OS pipe buffer (~4 KB) fills and the engine
                //     BLOCKS on its next write. A chatty run (e.g. BVAR's per-iter
                //     MCMC logging on stderr) can therefore deadlock mid/late-run —
                //     a second undrained-pipe deadlock distinct from the response
                //     pipe. Draining removes it.
                //  2. DIAGNOSTICS: the engine's own log lines now land in the TSL log
                //     file, so a stalled run reveals the engine's last action (did it
                //     reach "Run … completed"? did it start returning the response?).
                // Tagged with the engine's PID: several Excel instances (each with its
                // own engine) can write to the same daily log.
                var tag = $"[engine {session.Pid}] ";
                process.OutputDataReceived += (s, e) =>
                {
                    if (e.Data != null) Logger.Info(tag + e.Data);
                };
                process.ErrorDataReceived += (s, e) =>
                {
                    if (e.Data != null) Logger.Info(tag + e.Data);
                };
                process.BeginOutputReadLine();
                process.BeginErrorReadLine();
            }
            catch (InvalidOperationException ex)
            {
                // The process ended before these steps: a cancel, or a crash at launch.
                throw FailStart(session, generation, $"the engine process ended at launch ({ex.Message})",
                    startFailure: true, reportedVersion: null);
            }

            // The engine ends when this Excel ends, however it ends.
            ContainInJob(process);

            // Record who this engine is, so a later Excel start can clean it up if
            // the job object could not hold it (EngineRegistry.Sweep).
            WriteEngineRecord(session, workerScript);

            Logger.Info($"Engine process started (PID={session.Pid}), pipe={pipeName}, " +
                        $"interpreter={pythonExe} ({AddInLayout.KindLabel} layout)");

            // No fixed wait for the pipe: the handshake's connect waits for it.
            VerifyEngineIdentity(session, generation);
        }

        /// <summary>
        /// THE IDENTITY HANDSHAKE (A2 Part 1(c)), run once per engine start, before any
        /// request. (1) The pipe must be served by the process this Excel just started
        /// (GetNamedPipeServerProcessId); nothing is sent to any other process. (2) The
        /// engine's engine_version must be the one this add-in expects: its build stamp
        /// when installed, the repository's engine\VERSION.txt in a development tree.
        /// A reply without an engine_version fails closed. On any failure the engine is
        /// killed and the run is refused with the house mismatch message.
        ///
        /// The probe relies on the engine's existing reply to a request with no
        /// technique_id: engine_worker.handle_request answers it with a failure frame
        /// that carries engine_versions ("No technique_id provided in the request.").
        /// An explicit engine "hello" verb is banked for the next time engine_worker.py
        /// is touched for another reason (A2 ratification, Q1). See EngineHandshake.
        /// </summary>
        private void VerifyEngineIdentity(EngineSession session, int generation)
        {
            var probe = EngineHandshake.Probe(session.PipeName, session.Pid, StartConnectTimeoutMs, HeartbeatTimeoutMs,
                () => session.IsAlive && Volatile.Read(ref _cancelGeneration) == generation);

            string expected = null;
            string expectedProblem = null;
            try
            {
                string devVersionText = null;
                if (AddInLayout.Kind == LayoutKind.Development)
                {
                    var versionFile = AddInLayout.FindFile(out var tried, "engine", "VERSION.txt");
                    if (versionFile != null) devVersionText = File.ReadAllText(versionFile);
                    else expectedProblem = $"the development engine\\VERSION.txt was not found ({tried})";
                }
                expected = EngineIdentity.ExpectedEngineVersion(AddInLayout.Kind, BuildInfo.Stamp, devVersionText);
            }
            catch (Exception ex)
            {
                expectedProblem = $"the expected engine version could not be read ({ex.Message})";
            }

            var problem = probe.Problem;
            if (problem == null && expected == null)
                problem = expectedProblem ?? $"no expected engine version for the {AddInLayout.KindLabel} layout";
            if (problem == null && !string.Equals(probe.EngineVersion, expected, StringComparison.Ordinal))
                problem = $"the engine reports engine_version '{probe.EngineVersion}', but this add-in expects '{expected}'";

            if (problem != null)
                throw FailStart(session, generation, problem, probe.NeverConnected || probe.TimedOut, probe.EngineVersion);

            // Start-up ran at normal priority so a cold start is not starved by Excel's
            // own recalculation; the engine's analysis work runs below normal, as before.
            try { session.Process.PriorityClass = ProcessPriorityClass.BelowNormal; }
            catch (Exception ex) { Logger.Info($"Could not lower engine PID={session.Pid} priority: {ex.Message}"); }

            session.Version = probe.EngineVersion;
            Volatile.Write(ref _verified, session);
            Logger.Info($"Engine identity verified: pipe {session.PipeName} is served by PID={session.Pid}, " +
                        $"engine_version={probe.EngineVersion} (expected {expected}).");
        }

        /// <summary>
        /// A start that did not produce a verified engine: stop that engine and return
        /// the exception to throw. A cancel during the start is a cancel. An engine that exited,
        /// never opened its pipe or never answered is a start failure. Only an engine
        /// that answered wrongly (or a pipe served by another process) is an identity
        /// mismatch.
        /// </summary>
        private Exception FailStart(EngineSession session, int generation, string problem, bool startFailure,
            string reportedVersion)
        {
            var stopped = !session.IsAlive;
            Logger.Error($"Engine start or identity check FAILED for PID={session.Pid} on pipe {session.PipeName}: {problem}" +
                         (stopped ? " (the engine process has exited)" : "") +
                         ". The engine is being stopped and the run refused.");
            KillSession(session, "start or identity check failed");

            if (Volatile.Read(ref _cancelGeneration) != generation)
                return new OperationCanceledException("The run was canceled while the engine was starting.");
            if (stopped || startFailure)
                return new EngineStartException(EngineIdentity.EngineStartMessage(stopped, LogsFolder));
            return new EngineIdentityException(
                EngineIdentity.MismatchMessage(BuildInfo.Stamp, reportedVersion ?? "(not reported)"));
        }

        /// <summary>
        /// Place the engine in this Excel's kill-on-close job object (created on first
        /// use and held for the life of this EngineClient). When Excel exits - normally,
        /// from Task Manager or by crashing - Windows closes the handle and ends the
        /// engine. If Windows refuses (e.g. Excel already runs inside a job that forbids
        /// nesting), the engine still runs and the next start's orphan sweep covers it.
        /// </summary>
        private void ContainInJob(Process engine)
        {
            try
            {
                if (_job == null)
                {
                    _job = EngineJob.Create(out var createProblem);
                    if (_job == null)
                    {
                        Logger.Warn($"Engine job object could not be created ({createProblem}); " +
                                    "the engine will not end automatically with Excel. The next Excel start's orphan sweep covers it.");
                        return;
                    }
                }

                if (_job.TryAssign(engine, out var assignProblem))
                    Logger.Info($"Engine PID={engine.Id} placed in this Excel's kill-on-close job object.");
                else
                    Logger.Warn($"Engine PID={engine.Id} could not be placed in the job object ({assignProblem}); " +
                                "it will not end automatically with Excel. The next Excel start's orphan sweep covers it.");
            }
            catch (Exception ex)
            {
                Logger.Warn($"Engine job object step failed ({ex.GetType().Name}: {ex.Message}).");
            }
        }

        /// <summary>
        /// Write this Excel's engine record (%LOCALAPPDATA%\TimeSeriesLab\engines\&lt;ExcelPID&gt;-&lt;ticks&gt;.json).
        /// One file per Excel instance, overwritten when the engine restarts.
        /// </summary>
        private void WriteEngineRecord(EngineSession session, string workerScript)
        {
            try
            {
                long? engineStart = null;
                string imagePath = null;
                using (var h = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION, false, session.Pid))
                {
                    engineStart = NativeMethods.TryGetStartUtcTicks(h);
                    imagePath = NativeMethods.TryGetImagePath(h);
                }

                var record = new EngineRecord
                {
                    ExcelPid = _excelPid,
                    ExcelStartUtcTicks = _excelStartUtcTicks,
                    EnginePid = session.Pid,
                    EngineStartUtcTicks = engineStart ?? 0,
                    ExePath = imagePath,
                    WorkerPath = Path.GetFullPath(workerScript),
                    PipeName = session.PipeName,
                    Stamp = BuildInfo.Stamp,
                    LayoutRoot = AddInLayout.Root,
                };

                _recordPath = Path.Combine(AddIn.AppDataPath, EngineRegistry.RecordsFolder,
                    EngineRegistry.RecordFileName(_excelPid, _excelStartUtcTicks));
                EngineRegistry.WriteRecord(_recordPath, record);
                Logger.Info($"Engine record written: {_recordPath} (engine image {imagePath ?? "(unreadable)"}).");
            }
            catch (Exception ex)
            {
                Logger.Warn($"Could not write the engine record ({ex.GetType().Name}: {ex.Message}).");
            }
        }

        /// <summary>
        /// Sends a RunRequest to the engine and returns the RunResponse.
        /// Streams progress events via the ProgressReceived event.
        /// </summary>
        public async Task<RunResponse> RunAsync(RunRequest request, CancellationToken ct = default)
        {
            Interlocked.Increment(ref _runsInFlight);
            try
            {
                return await RunCoreAsync(request, ct);
            }
            finally
            {
                Interlocked.Decrement(ref _runsInFlight);
            }
        }

        private async Task<RunResponse> RunCoreAsync(RunRequest request, CancellationToken ct)
        {
            _currentRunCts = CancellationTokenSource.CreateLinkedTokenSource(ct);

            EnsureRunning();

            var requestJson = JsonConvert.SerializeObject(request);

            string responseJson;
            bool fromEngine;
            EngineSession served;
            try
            {
                (responseJson, fromEngine, served) = await SendAndReceiveAsync(requestJson, _currentRunCts.Token);
            }
            catch (OperationCanceledException)
            {
                // User cancel surfaced as a cancellation of the read — return a
                // clean canceled response instead of throwing, so the dispatch
                // tail can skip result-writing without an error banner.
                return new RunResponse
                {
                    RunId = request.RunId,
                    Status = "canceled",
                    PlainEnglishSummary = CanceledMessage,
                    Warnings = new System.Collections.Generic.List<string> { "Run canceled." }
                };
            }

            if (_currentRunCts.Token.IsCancellationRequested)
            {
                return new RunResponse
                {
                    RunId = request.RunId,
                    Status = "canceled",
                    PlainEnglishSummary = CanceledMessage,
                    Warnings = new System.Collections.Generic.List<string> { "Run canceled." }
                };
            }

            RunResponse result;
            try
            {
                result = JsonConvert.DeserializeObject<RunResponse>(responseJson);
            }
            catch (JsonException ex)
            {
                Logger.Error($"Run {request.RunId}: the engine's reply could not be read ({ex.Message}).");
                result = null;
            }
            if (result == null)
            {
                return new RunResponse
                {
                    RunId = request.RunId,
                    Status = "failure",
                    ErrorMessage = UnreadableReplyMessage,
                    FromAddIn = true,
                };
            }
            // The add-in's own stall and no-reply failures are complete house messages.
            result.FromAddIn = !fromEngine;

            // Every final response the engine sends must carry the engine_version that
            // engine proved at its handshake; a missing or different one is refused,
            // never written. Checked against the engine that served THIS request.
            if (fromEngine)
            {
                var reported = result.EngineVersions?.EngineVersion?.Trim();
                var verified = served?.Version;
                if (string.IsNullOrEmpty(reported) || !string.Equals(reported, verified, StringComparison.Ordinal))
                {
                    Logger.Error($"Run {request.RunId} refused: its response reports engine_version " +
                                 $"'{reported ?? "(none)"}', but engine PID={served?.Pid} proved '{verified ?? "(none)"}'.");
                    KillSession(served, "engine_version differs from the handshake");
                    return new RunResponse
                    {
                        RunId = request.RunId,
                        Status = "failure",
                        ErrorMessage = EngineIdentity.MismatchMessage(BuildInfo.Stamp,
                            string.IsNullOrEmpty(reported) ? "(not reported)" : reported),
                        FromAddIn = true,
                    };
                }
            }
            return result;
        }

        /// <summary>
        /// One request over the pipe of the verified engine. Returns the final response
        /// JSON, whether it came from the engine (false for the add-in's own stall and
        /// no-response failures), and the engine that served it.
        /// </summary>
        private async Task<(string Json, bool FromEngine, EngineSession Served)> SendAndReceiveAsync(
            string requestJson, CancellationToken ct)
        {
            // Connect to the VERIFIED engine's own pipe. If that engine stopped or was
            // replaced since this run's EnsureRunning (a cancel, a crash), wait for the
            // new one instead of reaching an engine that has not passed its handshake.
            NamedPipeClientStream connected = null;
            EngineSession session = null;
            for (var attempt = 0; connected == null; attempt++)
            {
                ct.ThrowIfCancellationRequested();
                session = Volatile.Read(ref _verified);
                if (session == null || !session.IsAlive)
                {
                    if (attempt >= 2)
                        throw new EngineStartException(EngineIdentity.EngineStartMessage(true, LogsFolder));
                    EnsureRunning();
                    continue;
                }

                var target = session;
                connected = EngineHandshake.Connect(target.PipeName, ConnectTimeoutMs,
                    () => ReferenceEquals(Volatile.Read(ref _verified), target) && target.IsAlive,
                    ct, out var outcome);
                if (connected != null)
                    break;

                ct.ThrowIfCancellationRequested();
                if (outcome == ConnectOutcome.StoppedWaiting && attempt < 2)
                    continue; // the engine was replaced or stopped: go again with the new one
                if (outcome == ConnectOutcome.Busy)
                    throw new EngineBusyException(EngineIdentity.EngineBusyMessage(ConnectTimeoutMs / 1000));
                throw new EngineStartException(EngineIdentity.EngineStartMessage(!target.IsAlive, LogsFolder));
            }

            using (var pipe = connected)
            {
                // Every connect: the pipe must be served by the engine that passed the
                // handshake. Checked before a byte of the request is written.
                if (!EngineHandshake.TryGetServerPid(pipe, out var serverPid) || serverPid != (uint)session.Pid)
                {
                    Logger.Error($"Run refused before sending: pipe {session.PipeName} is served by process {serverPid}, " +
                                 $"not the verified engine (PID {session.Pid}).");
                    throw new EngineIdentityException(EngineIdentity.MismatchMessage(BuildInfo.Stamp, "(not reported)"));
                }

                // Write request
                var requestBytes = Encoding.UTF8.GetBytes(requestJson);
                var lengthBytes = BitConverter.GetBytes(requestBytes.Length);
                await pipe.WriteAsync(lengthBytes, 0, 4, ct);
                await pipe.WriteAsync(requestBytes, 0, requestBytes.Length, ct);
                await pipe.FlushAsync(ct);

                // Read responses (progress events followed by final response)
                string finalResponse = null;

                // [readloop] instrumentation: per-frame trace to the log file so a
                // stalled run localizes the exact step that blocks — awaiting the
                // length prefix (engine hasn't sent), mid-body, parse, dispatch, or
                // final detection. (The Logger timestamps each line.)
                int msgIndex = 0;

                while (!ct.IsCancellationRequested)
                {
                    msgIndex++;
                    Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: awaiting length prefix...");
                    byte[] msgBuf = null;
                    try
                    {
                        // Heartbeat-bounded read: a FRESH timeout window per
                        // message, so every progress event the engine sends resets
                        // the watchdog and a legitimately long run (MCMC/DL) never
                        // trips it. A silent engine — no message at all within
                        // HeartbeatTimeoutMs — is treated as a stall (handled below).
                        using (var hbCts = CancellationTokenSource.CreateLinkedTokenSource(ct))
                        {
                            hbCts.CancelAfter(HeartbeatTimeoutMs);
                            var hbToken = hbCts.Token;

                            var msgLenBuf = new byte[4];
                            var bytesRead = await ReadFullAsync(pipe, msgLenBuf, 0, 4, hbToken);
                            if (bytesRead < 4)
                            {
                                Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: EOF/short length read ({bytesRead}/4) — engine closed pipe.");
                                break;
                            }

                            var msgLen = BitConverter.ToInt32(msgLenBuf, 0);
                            Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: length prefix = {msgLen} bytes; reading body...");
                            msgBuf = new byte[msgLen];
                            bytesRead = await ReadFullAsync(pipe, msgBuf, 0, msgLen, hbToken);
                            if (bytesRead < msgLen)
                            {
                                Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: short body read ({bytesRead}/{msgLen}) — engine closed pipe mid-frame.");
                                break;
                            }
                            Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: body read {bytesRead} bytes.");
                        }
                    }
                    catch (OperationCanceledException) when (!ct.IsCancellationRequested)
                    {
                        // Heartbeat expired while the run's own token is NOT
                        // cancelled => the engine went silent (wedged at the
                        // handoff or mid-compute), this is NOT a user cancel. Kill
                        // the wedged process so EnsureRunning relaunches a fresh
                        // engine next run, and fail cleanly instead of hanging.
                        Logger.Error(
                            $"Engine response stalled: no message for {HeartbeatTimeoutMs / 1000}s. " +
                            "Killing the engine so a wedged process is not reused.");
                        KillSession(session, "response heartbeat timeout");
                        return (BuildStallFailureJson(), false, session);
                    }

                    var msg = Encoding.UTF8.GetString(msgBuf);

                    // Robustly distinguish progress events from the final response
                    // by parsing the JSON and inspecting the "type" field. The old
                    // substring check (msg.Contains("\"type\":\"progress\"")) was
                    // whitespace-sensitive and misfired against Python's default
                    // json.dumps output ("type": "progress" with a space), causing
                    // the first progress event to be mistaken for the final
                    // RunResponse (yielding empty Tables + null summary).
                    JObject parsed = null;
                    try
                    {
                        parsed = JObject.Parse(msg);
                    }
                    catch (JsonException)
                    {
                        // Malformed JSON — treat as final response to surface the error
                        finalResponse = msg;
                        break;
                    }

                    var msgType = (string)parsed["type"];
                    if (string.Equals(msgType, "progress", StringComparison.OrdinalIgnoreCase))
                    {
                        try
                        {
                            var evt = parsed.ToObject<ProgressEvent>();
                            Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: progress \"{evt.Stage}\" {evt.Pct}% — dispatching to UI.");
                            ProgressReceived?.Invoke(evt);
                            Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: progress dispatched; looping for next frame.");
                        }
                        catch (Exception ex)
                        {
                            Logger.Info($"Failed to parse progress event: {ex.Message}");
                        }
                    }
                    else
                    {
                        // Final RunResponse frame
                        Logger.Info($"[readloop {session.Pid}] frame #{msgIndex}: FINAL response received ({msgBuf.Length} bytes). Read loop complete.");
                        finalResponse = msg;
                        break;
                    }
                }

                return finalResponse != null
                    ? (finalResponse, true, session)
                    : (FailureJson(NoReplyMessage), false, session);
            }
        }

        private static async Task<int> ReadFullAsync(Stream stream, byte[] buffer, int offset, int count, CancellationToken ct)
        {
            int totalRead = 0;
            while (totalRead < count && !ct.IsCancellationRequested)
            {
                int read = await stream.ReadAsync(buffer, offset + totalRead, count - totalRead, ct);
                if (read == 0) break;
                totalRead += read;
            }
            return totalRead;
        }

        /// <summary>
        /// Hard cancel: terminates the engine process immediately.
        /// Never takes the lock: this runs on Excel's thread, and an engine start holds
        /// the lock through its identity handshake (seconds while the engine warms up).
        /// Killing the engine ends that handshake's wait; the start then sees the cancel
        /// count change and reports a cancel. A start that has not yet published its
        /// engine checks the count after Process.Start and stops its own engine.
        /// </summary>
        public void CancelCurrentRun()
        {
            _currentRunCts?.Cancel();
            Interlocked.Increment(ref _cancelGeneration);
            KillSession(Volatile.Read(ref _session), "cancel");
        }

        /// <summary>
        /// Stop one engine and forget it - only it, never an engine started since
        /// (compare-and-clear, no lock). Used by cancel, the response heartbeat watchdog
        /// and the identity checks; the next EnsureRunning then starts a fresh engine
        /// with a fresh pipe and handshake.
        /// </summary>
        private void KillSession(EngineSession session, string reason)
        {
            if (session == null) return;
            try
            {
                if (session.IsAlive)
                {
                    session.Process.Kill();
                    Logger.Info($"Engine process PID={session.Pid} killed ({reason}).");
                }
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to kill engine process PID={session.Pid} ({reason}).", ex);
            }
            Interlocked.CompareExchange(ref _verified, null, session);
            Interlocked.CompareExchange(ref _session, null, session);
        }

        // The add-in's own run failures (house style: what happened and the state, then
        // what to do). They reach the task pane as they are (RunResponse.FromAddIn) and
        // worksheet functions as "ERROR: <text>".
        private const string CanceledMessage = "The run was canceled. Nothing was written.";

        private const string NoReplyMessage =
            "The analysis engine closed the connection without a result, so the run did not complete. " +
            "Nothing was written.\n\n" +
            "Try again. If this message returns, tell Matthew Hornbach.";

        private const string UnreadableReplyMessage =
            "The analysis engine sent a reply that Time Series Lab could not read, so the run did not complete. " +
            "Nothing was written.\n\n" +
            "Try again. If this message returns, tell Matthew Hornbach.";

        private static readonly string StallMessage =
            $"The analysis engine stopped responding (no progress for over {HeartbeatTimeoutMs / 1000} seconds) " +
            "and was stopped, so the run did not complete. Nothing was written.\n\n" +
            "Try again; the engine restarts by itself. If this keeps happening, close Excel and start it again, " +
            "then tell Matthew Hornbach.";

        private static string FailureJson(string message) =>
            new JObject { ["status"] = "failure", ["error_message"] = message }.ToString(Formatting.None);

        /// <summary>
        /// The failure RunResponse (as JSON) returned when the response heartbeat
        /// watchdog fires — surfaced in the Task Pane via the normal failure path
        /// instead of hanging Excel indefinitely.
        /// </summary>
        private static string BuildStallFailureJson() => FailureJson(StallMessage);

        public void Shutdown()
        {
            CancelCurrentRun();
            // Closing the job ends anything still in it; then remove this Excel's own
            // record only - other Excel instances' records are theirs.
            try { _job?.Dispose(); } catch { /* best-effort */ }
            _job = null;
            EngineRegistry.DeleteRecord(_recordPath);
        }

        public void Dispose()
        {
            if (!_disposed)
            {
                _disposed = true;
                Shutdown();
            }
        }
    }
}
