using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Security.Principal;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
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

        public event Action<ProgressEvent> ProgressReceived;

        public EngineClient()
        {
            var sid = WindowsIdentity.GetCurrent().User?.Value ?? "default";
            _pipeName = $"TSL_ENGINE_PIPE_{sid}";
        }

        private string EnginePath => Path.Combine(AddIn.AppDataPath, "engine");
        private string PythonExePath => Path.Combine(EnginePath, "runtime", "python.exe");
        private string WorkerScriptPath => Path.Combine(EnginePath, "engine_worker.py");

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
            var workerScript = File.Exists(WorkerScriptPath)
                ? WorkerScriptPath
                : Path.Combine(
                    Path.GetDirectoryName(typeof(EngineClient).Assembly.Location) ?? "",
                    "..", "..", "..", "..", "engine", "engine_worker.py");

            if (!File.Exists(workerScript))
            {
                throw new FileNotFoundException(
                    $"Engine worker script not found. Expected at:\n{WorkerScriptPath}\nor\n{workerScript}\n\n" +
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

            // Give engine a moment to create pipe server
            Thread.Sleep(500);

            Logger.Info($"Engine process started (PID={_engineProcess.Id}), pipe={_pipeName}");
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
                    var msgLenBuf = new byte[4];
                    var bytesRead = await ReadFullAsync(pipe, msgLenBuf, 0, 4, ct);
                    if (bytesRead < 4) break;

                    var msgLen = BitConverter.ToInt32(msgLenBuf, 0);
                    var msgBuf = new byte[msgLen];
                    bytesRead = await ReadFullAsync(pipe, msgBuf, 0, msgLen, ct);
                    if (bytesRead < msgLen) break;

                    var msg = Encoding.UTF8.GetString(msgBuf);

                    // Try to parse as progress event first
                    if (msg.Contains("\"type\":\"progress\""))
                    {
                        try
                        {
                            var evt = JsonConvert.DeserializeObject<ProgressEvent>(msg);
                            ProgressReceived?.Invoke(evt);
                        }
                        catch { }
                    }
                    else
                    {
                        // Final response
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

        public void Shutdown()
        {
            CancelCurrentRun();
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
