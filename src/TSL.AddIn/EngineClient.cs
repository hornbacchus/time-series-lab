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

        public EngineClient()
        {
            var sid = WindowsIdentity.GetCurrent().User?.Value ?? "default";
            _pipeName = $"TSL_ENGINE_PIPE_{sid}";
        }

        private string EnginePath => Path.Combine(AddIn.AppDataPath, "engine");
        private string PythonExePath => Path.Combine(EnginePath, "runtime", "python.exe");
        private string WorkerScriptPath => Path.Combine(EnginePath, "engine_worker.py");
        private string PidFilePath => Path.Combine(AddIn.AppDataPath, "engine.pid");

        /// <summary>
        /// Kill any engine process left over from a prior session (e.g. Excel
        /// crashed before AutoClose could fire, or a developer rebuilt the
        /// engine while Excel was open).
        ///
        /// This is critical for development iteration: the Python engine
        /// caches imported technique modules in-process, so updates to
        /// pca_analysis.py / etc. are NOT picked up unless the engine
        /// process restarts. Calling this from AddIn.AutoOpen guarantees
        /// every Excel session starts with a fresh engine that re-imports
        /// the latest code on first request.
        /// </summary>
        public void KillStaleEngineProcess()
        {
            try
            {
                if (!File.Exists(PidFilePath)) return;

                var pidStr = File.ReadAllText(PidFilePath).Trim();
                if (!int.TryParse(pidStr, out var pid))
                {
                    SafeDeletePidFile();
                    return;
                }

                try
                {
                    var proc = Process.GetProcessById(pid);
                    // Defensive: only kill if it's actually a Python process,
                    // never a random PID that's been reused by Windows.
                    if (proc.ProcessName.StartsWith("python", StringComparison.OrdinalIgnoreCase))
                    {
                        proc.Kill();
                        proc.WaitForExit(2000);
                        Logger.Info($"Killed stale engine process PID={pid} (so the engine reloads updated Python modules).");
                    }
                }
                catch (ArgumentException)
                {
                    // PID is not a running process — already gone, nothing to do.
                }
                catch (InvalidOperationException)
                {
                    // Process exited between the lookup and the Kill call.
                }

                SafeDeletePidFile();
            }
            catch (Exception ex)
            {
                Logger.Info($"Stale engine cleanup skipped: {ex.Message}");
            }
        }

        private void SafeDeletePidFile()
        {
            try { if (File.Exists(PidFilePath)) File.Delete(PidFilePath); }
            catch { /* best-effort */ }
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
            // For development: try system Python if embedded runtime not yet installed
            var pythonExe = File.Exists(PythonExePath) ? PythonExePath : "python";
            var workerScript = ResolveWorkerScript();

            if (string.IsNullOrEmpty(workerScript) || !File.Exists(workerScript))
            {
                throw new FileNotFoundException(
                    $"Engine worker script not found. Searched:\n" +
                    string.Join("\n", GetWorkerScriptSearchPaths()) + "\n\n" +
                    "Please ensure the engine is installed correctly.");
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

            _engineProcess.PriorityClass = ProcessPriorityClass.BelowNormal;

            // Persist the PID so KillStaleEngineProcess() on a future
            // AutoOpen can clean up if Excel crashes before AutoClose fires.
            try
            {
                File.WriteAllText(PidFilePath, _engineProcess.Id.ToString());
            }
            catch (Exception ex)
            {
                Logger.Info($"Could not write engine PID file: {ex.Message}");
            }

            // Give engine a moment to create pipe server
            Thread.Sleep(500);

            Logger.Info($"Engine process started (PID={_engineProcess.Id}), pipe={_pipeName}");
        }

        /// <summary>
        /// Resolve the path to engine_worker.py, trying several candidate locations.
        /// Returns the first one that exists, or null if none found.
        /// </summary>
        private string ResolveWorkerScript()
        {
            foreach (var candidate in GetWorkerScriptSearchPaths())
            {
                if (!string.IsNullOrEmpty(candidate) && File.Exists(candidate))
                    return candidate;
            }
            return null;
        }

        private System.Collections.Generic.List<string> GetWorkerScriptSearchPaths()
        {
            var paths = new System.Collections.Generic.List<string>();

            // Installed location (%LOCALAPPDATA%\TimeSeriesLab\engine\engine_worker.py)
            paths.Add(WorkerScriptPath);

            // Relative to the loaded XLL (most reliable when running packed).
            try
            {
                var xllPath = ExcelDnaUtil.XllPath;
                if (!string.IsNullOrEmpty(xllPath))
                {
                    var xllDir = Path.GetDirectoryName(xllPath);
                    if (!string.IsNullOrEmpty(xllDir))
                    {
                        // Co-located engine
                        paths.Add(Path.Combine(xllDir, "engine", "engine_worker.py"));
                        // Dev build: src\TSL.AddIn\bin\x64\Release\net48\publish\ -> project root
                        paths.Add(Path.Combine(xllDir, "..", "..", "..", "..", "..", "..", "engine", "engine_worker.py"));
                        // Dev build: src\TSL.AddIn\bin\x64\Release\net48\ -> project root
                        paths.Add(Path.Combine(xllDir, "..", "..", "..", "..", "..", "engine", "engine_worker.py"));
                    }
                }
            }
            catch { /* ExcelDnaUtil unavailable at design-time */ }

            // Dev location (relative to assembly). Assembly.Location can throw
            // "The path is not of a legal form" when loaded from a packed XLL.
            try
            {
                var asmLoc = typeof(EngineClient).Assembly.Location;
                if (!string.IsNullOrEmpty(asmLoc))
                {
                    var asmDir = Path.GetDirectoryName(asmLoc);
                    if (!string.IsNullOrEmpty(asmDir))
                    {
                        paths.Add(Path.Combine(asmDir, "..", "..", "..", "..", "engine", "engine_worker.py"));
                        paths.Add(Path.Combine(asmDir, "engine", "engine_worker.py"));
                    }
                }
            }
            catch { /* Assembly.Location may throw for embedded assemblies */ }

            return paths;
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
            var responseJson = await SendAndReceiveAsync(requestJson, _currentRunCts.Token);

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

                while (!ct.IsCancellationRequested)
                {
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
                            if (bytesRead < 4) break;

                            var msgLen = BitConverter.ToInt32(msgLenBuf, 0);
                            msgBuf = new byte[msgLen];
                            bytesRead = await ReadFullAsync(pipe, msgBuf, 0, msgLen, hbToken);
                            if (bytesRead < msgLen) break;
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
                            ProgressReceived?.Invoke(evt);
                        }
                        catch (Exception ex)
                        {
                            Logger.Info($"Failed to parse progress event: {ex.Message}");
                        }
                    }
                    else
                    {
                        // Final RunResponse frame
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
            // Clean up PID file on graceful shutdown so the next AutoOpen
            // doesn't try to kill a PID that's already been recycled.
            SafeDeletePidFile();
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
