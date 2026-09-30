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

namespace TSL.AddIn
{
    /// <summary>
    /// Manages the Python engine worker process and communicates via Named Pipes.
    /// </summary>
    public class EngineClient : IDisposable
    {
        private Process _engineProcess;
        private readonly string _pipeName;
        private readonly string _legacyPipeName;
        private readonly int _excelPid;
        private readonly long _excelStartUtcTicks;
        private EngineJob _job;
        private string _recordPath;
        private CancellationTokenSource _currentRunCts;
        private readonly object _lock = new object();
        private bool _disposed;

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

        public event Action<ProgressEvent> ProgressReceived;

        /// <summary>
        /// One engine per Excel instance and per build (A2 Part 1): the pipe name carries
        /// this Excel's PID, the build token and a fresh nonce, so a second Excel, an
        /// older build or any other process can never share or pre-create it.
        /// </summary>
        public EngineClient()
        {
            var sid = WindowsIdentity.GetCurrent().User?.Value ?? "default";
            EngineRegistry.GetCurrentProcessIdentity(out _excelPid, out _excelStartUtcTicks);
            var nonce = Guid.NewGuid().ToString("N").Substring(0, 8);
            _pipeName = EngineIdentity.BuildPipeName(sid, _excelPid, BuildInfo.Stamp, nonce);
            _legacyPipeName = EngineIdentity.LegacyPipePrefix + sid;
        }

        /// <summary>This Excel's engine, for About: "Running (PID n)" or "Not running".</summary>
        public string StatusText
        {
            get
            {
                // No lock: About runs on Excel's thread and must not wait on a start in progress.
                var engine = _engineProcess;
                try
                {
                    return engine != null && !engine.HasExited ? $"Running (PID {engine.Id})" : "Not running";
                }
                catch
                {
                    return "Not running";
                }
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
        /// WMI can take seconds on managed machines, and this Excel's pipe name is new,
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
        /// Ensures the engine process is running. Starts it if not.
        /// </summary>
        public void EnsureRunning()
        {
            lock (_lock)
            {
                if (_engineProcess != null && !_engineProcess.HasExited)
                    return;

                StartEngine();
            }
        }

        private void StartEngine()
        {
            var pythonExe = ResolvePythonExe();

            // ONE location, from the add-in's layout (AddInLayout): <root>\engine\engine_worker.py.
            var workerScript = AddInLayout.FindFile(out var workerTried, "engine", "engine_worker.py");
            if (workerScript == null)
            {
                throw new FileNotFoundException(
                    AddInLayout.MissingMessage("engine worker script (engine_worker.py)", workerTried));
            }

            var psi = new ProcessStartInfo
            {
                FileName = pythonExe,
                Arguments = $"\"{workerScript}\" --pipe \"{_pipeName}\"",
                UseShellExecute = false,
                CreateNoWindow = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                WorkingDirectory = Path.GetDirectoryName(workerScript),
            };

            // Set environment to prevent network access
            psi.EnvironmentVariables["TSL_NO_NETWORK"] = "1";
            psi.EnvironmentVariables["TSL_PIPE_NAME"] = _pipeName;

            _engineProcess = Process.Start(psi);
            if (_engineProcess == null)
                throw new InvalidOperationException("Failed to start engine process.");

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
            _engineProcess.OutputDataReceived += (s, e) =>
            {
                if (e.Data != null) Logger.Info("[engine] " + e.Data);
            };
            _engineProcess.ErrorDataReceived += (s, e) =>
            {
                if (e.Data != null) Logger.Info("[engine] " + e.Data);
            };
            _engineProcess.BeginOutputReadLine();
            _engineProcess.BeginErrorReadLine();

            _engineProcess.PriorityClass = ProcessPriorityClass.BelowNormal;

            // The engine ends when this Excel ends, however it ends.
            ContainInJob(_engineProcess);

            // Record who this engine is, so a later Excel start can clean it up if
            // the job object could not hold it (EngineRegistry.Sweep).
            WriteEngineRecord(_engineProcess, workerScript);

            // Give engine a moment to create pipe server
            Thread.Sleep(500);

            Logger.Info($"Engine process started (PID={_engineProcess.Id}), pipe={_pipeName}, " +
                        $"interpreter={pythonExe} ({AddInLayout.KindLabel} layout)");
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
        private void WriteEngineRecord(Process engine, string workerScript)
        {
            try
            {
                long? engineStart = null;
                string imagePath = null;
                using (var h = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION, false, engine.Id))
                {
                    engineStart = NativeMethods.TryGetStartUtcTicks(h);
                    imagePath = NativeMethods.TryGetImagePath(h);
                }

                var record = new EngineRecord
                {
                    ExcelPid = _excelPid,
                    ExcelStartUtcTicks = _excelStartUtcTicks,
                    EnginePid = engine.Id,
                    EngineStartUtcTicks = engineStart ?? 0,
                    ExePath = imagePath,
                    WorkerPath = Path.GetFullPath(workerScript),
                    PipeName = _pipeName,
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
            _currentRunCts = CancellationTokenSource.CreateLinkedTokenSource(ct);

            EnsureRunning();

            var requestJson = JsonConvert.SerializeObject(request);

            string responseJson;
            try
            {
                responseJson = await SendAndReceiveAsync(requestJson, _currentRunCts.Token);
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
                    PlainEnglishSummary = "Run was canceled by user.",
                    Warnings = new System.Collections.Generic.List<string> { "Run canceled." }
                };
            }

            if (_currentRunCts.Token.IsCancellationRequested)
            {
                return new RunResponse
                {
                    RunId = request.RunId,
                    Status = "canceled",
                    PlainEnglishSummary = "Run was canceled by user.",
                    Warnings = new System.Collections.Generic.List<string> { "Run canceled." }
                };
            }

            var result = JsonConvert.DeserializeObject<RunResponse>(responseJson);
            if (result == null)
            {
                return new RunResponse
                {
                    RunId = request.RunId,
                    Status = "failure",
                    ErrorMessage = "Invalid response format from engine.",
                };
            }
            return result;
        }

        private async Task<string> SendAndReceiveAsync(string requestJson, CancellationToken ct)
        {
            using (var pipe = new NamedPipeClientStream(".", _pipeName, PipeDirection.InOut, PipeOptions.Asynchronous))
            {
                await pipe.ConnectAsync(10000, ct);

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
                    Logger.Info($"[readloop] frame #{msgIndex}: awaiting length prefix...");
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
                                Logger.Info($"[readloop] frame #{msgIndex}: EOF/short length read ({bytesRead}/4) — engine closed pipe.");
                                break;
                            }

                            var msgLen = BitConverter.ToInt32(msgLenBuf, 0);
                            Logger.Info($"[readloop] frame #{msgIndex}: length prefix = {msgLen} bytes; reading body...");
                            msgBuf = new byte[msgLen];
                            bytesRead = await ReadFullAsync(pipe, msgBuf, 0, msgLen, hbToken);
                            if (bytesRead < msgLen)
                            {
                                Logger.Info($"[readloop] frame #{msgIndex}: short body read ({bytesRead}/{msgLen}) — engine closed pipe mid-frame.");
                                break;
                            }
                            Logger.Info($"[readloop] frame #{msgIndex}: body read {bytesRead} bytes.");
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
                        KillEngineProcess("response heartbeat timeout");
                        return BuildStallFailureJson();
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
                            Logger.Info($"[readloop] frame #{msgIndex}: progress \"{evt.Stage}\" {evt.Pct}% — dispatching to UI.");
                            ProgressReceived?.Invoke(evt);
                            Logger.Info($"[readloop] frame #{msgIndex}: progress dispatched; looping for next frame.");
                        }
                        catch (Exception ex)
                        {
                            Logger.Info($"Failed to parse progress event: {ex.Message}");
                        }
                    }
                    else
                    {
                        // Final RunResponse frame
                        Logger.Info($"[readloop] frame #{msgIndex}: FINAL response received ({msgBuf.Length} bytes). Read loop complete.");
                        finalResponse = msg;
                        break;
                    }
                }

                return finalResponse ?? "{\"status\":\"failure\",\"error_message\":\"No response from engine.\"}";
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
        /// </summary>
        public void CancelCurrentRun()
        {
            _currentRunCts?.Cancel();

            lock (_lock)
            {
                if (_engineProcess != null && !_engineProcess.HasExited)
                {
                    try
                    {
                        _engineProcess.Kill();
                        Logger.Info("Engine process killed for cancel.");
                    }
                    catch (Exception ex)
                    {
                        Logger.Error("Failed to kill engine process.", ex);
                    }
                }
                _engineProcess = null;
            }
        }

        /// <summary>
        /// Kill the engine process WITHOUT cancelling the current run token
        /// (unlike <see cref="CancelCurrentRun"/>, which is a user-initiated
        /// cancel). Used by the response heartbeat watchdog when the engine has
        /// gone silent: clearing <c>_engineProcess</c> makes the next
        /// <see cref="EnsureRunning"/> relaunch a fresh engine rather than reuse
        /// the wedged one.
        /// </summary>
        private void KillEngineProcess(string reason)
        {
            lock (_lock)
            {
                if (_engineProcess != null && !_engineProcess.HasExited)
                {
                    try
                    {
                        _engineProcess.Kill();
                        Logger.Info($"Engine process killed ({reason}).");
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to kill engine process ({reason}).", ex);
                    }
                }
                _engineProcess = null;
            }
        }

        /// <summary>
        /// The failure RunResponse (as JSON) returned when the response heartbeat
        /// watchdog fires — surfaced in the Task Pane via the normal failure path
        /// instead of hanging Excel indefinitely.
        /// </summary>
        private static string BuildStallFailureJson()
        {
            return
                "{\"status\":\"failure\","
                + "\"error_message\":\"The engine stopped responding while returning results "
                + "(no progress for over " + (HeartbeatTimeoutMs / 1000) + " seconds) and was "
                + "stopped. The run did not complete.\","
                + "\"error_fixes\":[\"Run the technique again \\u2014 the engine relaunches "
                + "automatically.\",\"If this keeps happening, restart Excel.\"]}";
        }

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
