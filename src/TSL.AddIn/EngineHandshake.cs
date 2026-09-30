using System;
using System.Diagnostics;
using System.IO;
using System.IO.Pipes;
using System.Text;
using System.Threading;

namespace TSL.AddIn
{
    /// <summary>What the identity probe found. Problem is null only when a reply with an engine_version came back.</summary>
    internal sealed class HandshakeResult
    {
        /// <summary>The process serving the pipe; 0 when it could not be identified.</summary>
        public uint ServerPid { get; set; }

        /// <summary>The engine_version the engine reported; null when none was reported.</summary>
        public string EngineVersion { get; set; }

        public string Problem { get; set; }

        /// <summary>The engine never opened its pipe in time, or stopped first (not an identity failure).</summary>
        public bool NeverConnected { get; set; }

        /// <summary>The engine was connected but did not answer in time, or stopped first (not an identity failure).</summary>
        public bool TimedOut { get; set; }
    }

    /// <summary>How a connect attempt ended when it did not connect.</summary>
    internal enum ConnectOutcome
    {
        Connected,
        /// <summary>The pipe did not appear within the budget.</summary>
        NeverAppeared,
        /// <summary>The pipe exists but its instance stayed busy for the whole budget.</summary>
        Busy,
        /// <summary>The caller's condition said to stop waiting (engine gone, replaced, or cancelled).</summary>
        StoppedWaiting,
    }

    /// <summary>A run refused before it reached the engine; the message is complete house text.</summary>
    internal class EngineRefusalException : Exception
    {
        public EngineRefusalException(string message) : base(message) { }
    }

    /// <summary>The engine is not this add-in's (EngineIdentity.MismatchMessage).</summary>
    internal sealed class EngineIdentityException : EngineRefusalException
    {
        public EngineIdentityException(string message) : base(message) { }
    }

    /// <summary>The engine stopped, or did not open its pipe or answer, while starting (EngineIdentity.EngineStartMessage).</summary>
    internal sealed class EngineStartException : EngineRefusalException
    {
        public EngineStartException(string message) : base(message) { }
    }

    /// <summary>The engine stayed busy with another run for the whole connect budget (EngineIdentity.EngineBusyMessage).</summary>
    internal sealed class EngineBusyException : EngineRefusalException
    {
        public EngineBusyException(string message) : base(message) { }
    }

    /// <summary>
    /// The engine pipe's connect and identity handshake (A2 Part 1(c)): confirm who
    /// serves the pipe, then ask the engine what it is. Free of ExcelDna, AddIn and
    /// Logger references, so it can be driven against a real engine outside Excel.
    ///
    /// The probe relies on the engine's existing reply to a request with no
    /// technique_id: engine_worker.handle_request answers it with a failure frame
    /// ("No technique_id provided in the request.") that carries engine_versions. No
    /// engine change was needed. An explicit engine "hello" verb is banked for the
    /// next time engine_worker.py is touched for another reason (A2 ratification, Q1).
    /// </summary>
    internal static class EngineHandshake
    {
        private const int MaxFrameBytes = 64 * 1024 * 1024;

        // Connects are polled: a 1 ms attempt, then a short sleep. On .NET Framework a
        // longer Connect busy-spins while the pipe does not exist yet, which would take
        // a core from the (lower-priority) engine it is waiting for. Polling also lets
        // the caller's stop condition (engine exited, replaced, cancelled) end the wait
        // at once instead of after the budget.
        private const int ConnectAttemptMs = 1;
        private const int ConnectPollMs = 50;

        // How often the probe re-checks its stop condition while waiting for the reply.
        private const int ReplyPollMs = 100;

        private const int ERROR_SEM_TIMEOUT = 121;
        private const int ERROR_PIPE_BUSY = 231;

        /// <summary>The probe request: a run with no technique_id.</summary>
        public static string ProbeJson(string runId) =>
            "{\"run_id\":\"" + runId + "\",\"technique_id\":\"\"}";

        /// <summary>The process serving a connected pipe, via GetNamedPipeServerProcessId.</summary>
        public static bool TryGetServerPid(PipeStream pipe, out uint serverPid)
        {
            serverPid = 0;
            try
            {
                return NativeMethods.GetNamedPipeServerProcessId(pipe.SafePipeHandle, out serverPid) && serverPid != 0;
            }
            catch
            {
                return false;
            }
        }

        /// <summary>
        /// Connect to a pipe within <paramref name="budgetMs"/>, retrying while the pipe
        /// does not exist yet (TimeoutException) or its single instance is busy or
        /// re-arming between requests (on .NET Framework an IOException with
        /// ERROR_SEM_TIMEOUT or ERROR_PIPE_BUSY - not a TimeoutException). Each attempt
        /// uses a fresh stream, disposed if it fails. Stops early, with StoppedWaiting,
        /// when <paramref name="keepWaiting"/> turns false or <paramref name="ct"/> is
        /// cancelled. Any other connect error is thrown.
        /// </summary>
        public static NamedPipeClientStream Connect(string pipeName, int budgetMs, Func<bool> keepWaiting,
            CancellationToken ct, out ConnectOutcome outcome)
        {
            var waited = Stopwatch.StartNew();
            var sawBusy = false;
            while (true)
            {
                if (ct.IsCancellationRequested || (keepWaiting != null && !keepWaiting()))
                {
                    outcome = ConnectOutcome.StoppedWaiting;
                    return null;
                }

                var remaining = budgetMs - (int)waited.ElapsedMilliseconds;
                if (remaining <= 0)
                {
                    outcome = sawBusy ? ConnectOutcome.Busy : ConnectOutcome.NeverAppeared;
                    return null;
                }

                var attempt = new NamedPipeClientStream(".", pipeName, PipeDirection.InOut, PipeOptions.Asynchronous);
                try
                {
                    attempt.Connect(ConnectAttemptMs);
                    outcome = ConnectOutcome.Connected;
                    return attempt;
                }
                catch (TimeoutException)
                {
                    attempt.Dispose();
                }
                catch (IOException ex) when (IsBusy(ex))
                {
                    attempt.Dispose();
                    sawBusy = true;
                }
                catch
                {
                    attempt.Dispose();
                    throw;
                }
                Thread.Sleep(Math.Min(ConnectPollMs, Math.Max(1, remaining)));
            }
        }

        /// <summary>A process's image path for diagnostics, or "image unreadable".</summary>
        private static string ImageOf(uint pid)
        {
            try
            {
                using (var h = NativeMethods.OpenProcess(NativeMethods.PROCESS_QUERY_LIMITED_INFORMATION, false, (int)pid))
                    return NativeMethods.TryGetImagePath(h) ?? "image unreadable";
            }
            catch
            {
                return "image unreadable";
            }
        }

        private static bool IsBusy(IOException ex)
        {
            var code = ex.HResult & 0xFFFF;
            return code == ERROR_SEM_TIMEOUT || code == ERROR_PIPE_BUSY;
        }

        /// <summary>
        /// Connect, check the server is <paramref name="expectedServerPid"/> (nothing is
        /// sent to any other process), send the probe and read the reply. Never throws.
        /// <paramref name="keepWaiting"/> (optional; false once the engine has exited or
        /// the start was cancelled) ends both the connect wait and the reply wait early.
        /// </summary>
        public static HandshakeResult Probe(string pipeName, int expectedServerPid, int connectTimeoutMs,
            int replyTimeoutMs, Func<bool> keepWaiting = null)
        {
            var result = new HandshakeResult();
            NamedPipeClientStream connected = null;
            try
            {
                connected = Connect(pipeName, connectTimeoutMs, keepWaiting, CancellationToken.None, out var outcome);
                if (connected == null)
                {
                    result.NeverConnected = true;
                    result.Problem =
                        outcome == ConnectOutcome.StoppedWaiting ? "the engine stopped (or the start was cancelled) before its pipe opened" :
                        outcome == ConnectOutcome.Busy ? $"the engine's pipe stayed busy for {connectTimeoutMs / 1000} s" :
                        $"the engine's pipe did not open within {connectTimeoutMs / 1000} s";
                    return result;
                }

                using (var pipe = connected)
                {
                    if (!TryGetServerPid(pipe, out var serverPid))
                    {
                        result.Problem = "the process serving the pipe could not be identified";
                        return result;
                    }
                    result.ServerPid = serverPid;
                    if (serverPid != (uint)expectedServerPid)
                    {
                        result.Problem = $"the pipe was answered by process {serverPid} ({ImageOf(serverPid)}), " +
                                         $"not the engine this Excel started (PID {expectedServerPid})";
                        return result;
                    }

                    var reply = Exchange(pipe, ProbeJson("handshake-" + Guid.NewGuid().ToString("N")),
                        replyTimeoutMs, keepWaiting, out var readProblem, out var gaveUp);
                    if (reply == null)
                    {
                        result.Problem = readProblem;
                        result.TimedOut = gaveUp;
                        return result;
                    }

                    if (EngineIdentity.TryParseHandshakeReply(reply, out var version, out var parseProblem))
                        result.EngineVersion = version;
                    else
                        result.Problem = parseProblem;
                }
            }
            catch (Exception ex)
            {
                connected?.Dispose();
                result.Problem = $"the identity check could not complete ({ex.GetType().Name}: {ex.Message})";
            }
            return result;
        }

        /// <summary>
        /// Send one request frame and return the first non-progress reply frame, or null
        /// with <paramref name="problem"/>. The write and read run on a dedicated thread
        /// (not the thread pool, which a burst of worksheet recalculations can exhaust
        /// while the caller holds the engine lock). The caller waits at most
        /// <paramref name="timeoutMs"/> and stops at once when <paramref name="keepWaiting"/>
        /// turns false; its using-block then closes the pipe, which ends the worker's I/O.
        /// No Flush: on a pipe it waits (FlushFileBuffers) until the server has read
        /// everything, and a small frame is delivered by Write alone.
        /// <paramref name="gaveUp"/> is true when the wait ended by timeout or stop.
        /// </summary>
        private static string Exchange(Stream pipe, string requestJson, int timeoutMs, Func<bool> keepWaiting,
            out string problem, out bool gaveUp)
        {
            problem = null;
            gaveUp = false;
            string reply = null;
            Exception failure = null;
            var done = new ManualResetEventSlim(false); // never disposed: the worker may Set it after we return

            var worker = new Thread(() =>
            {
                try
                {
                    var request = Encoding.UTF8.GetBytes(requestJson);
                    pipe.Write(BitConverter.GetBytes(request.Length), 0, 4);
                    pipe.Write(request, 0, request.Length);

                    while (true)
                    {
                        var length = new byte[4];
                        if (!ReadExactly(pipe, length)) break;
                        var size = BitConverter.ToInt32(length, 0);
                        if (size <= 0 || size > MaxFrameBytes) break;
                        var body = new byte[size];
                        if (!ReadExactly(pipe, body)) break;
                        var text = Encoding.UTF8.GetString(body);
                        if (!EngineIdentity.IsProgressFrame(text)) { reply = text; break; }
                    }
                }
                catch (Exception ex)
                {
                    failure = ex;
                }
                finally
                {
                    done.Set();
                }
            })
            {
                IsBackground = true,
                Name = "TSL engine identity probe",
            };
            worker.Start();

            var waited = Stopwatch.StartNew();
            while (!done.Wait(ReplyPollMs))
            {
                if (keepWaiting != null && !keepWaiting())
                {
                    problem = "the engine stopped (or the start was cancelled) before it answered the identity probe";
                    gaveUp = true;
                    return null;
                }
                if (waited.ElapsedMilliseconds >= timeoutMs)
                {
                    problem = $"the engine did not answer the identity probe within {timeoutMs / 1000} s";
                    gaveUp = true;
                    return null;
                }
            }

            if (failure != null)
            {
                problem = $"the exchange with the engine failed ({failure.GetType().Name}: {failure.Message})";
                return null;
            }
            if (reply == null)
                problem = "the engine closed the pipe before answering the identity probe";
            return reply;
        }

        private static bool ReadExactly(Stream stream, byte[] buffer)
        {
            var total = 0;
            while (total < buffer.Length)
            {
                var n = stream.Read(buffer, total, buffer.Length - total);
                if (n == 0) return false;
                total += n;
            }
            return true;
        }
    }
}
