"""
Time Series Lab - Python Engine Worker

A Windows Named Pipe server that receives JSON RunRequest messages from the
C# Excel add-in, dispatches to technique modules, streams progress events,
and returns a final RunResponse.

Usage:
    python engine_worker.py --pipe TSL_ENGINE_PIPE_<SID>

Protocol (little-endian):
    Client -> Server: [4-byte length][UTF-8 JSON RunRequest]
    Server -> Client: [4-byte length][UTF-8 JSON progress event]  (0..N times)
    Server -> Client: [4-byte length][UTF-8 JSON RunResponse]     (exactly once)

The server loops: after each request completes, it waits for a new connection.
NO network calls are made. All computation is local.
"""

import argparse
import hashlib
import importlib
import json
import logging
import os
import platform
import random
import struct
import sys
import time
import traceback

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="[TSL-Engine %(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)
log = logging.getLogger("tsl_engine")


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ENGINE_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(ENGINE_DIR, "VERSION.txt")
REQUIREMENTS_FILE = os.path.join(ENGINE_DIR, "requirements.lock.txt")

# Ensure engine directory is on the Python path so technique imports work
if ENGINE_DIR not in sys.path:
    sys.path.insert(0, ENGINE_DIR)


# ---------------------------------------------------------------------------
# Win32 Named Pipe helpers
# ---------------------------------------------------------------------------

def _create_named_pipe(pipe_name: str):
    """
    Create a Windows Named Pipe server instance.

    Returns a pipe handle (int). Raises OSError on failure.
    Uses the win32 API via ctypes to avoid pywin32 dependency.
    """
    import ctypes
    import ctypes.wintypes as wt

    PIPE_ACCESS_DUPLEX = 0x00000003
    PIPE_TYPE_BYTE = 0x00000000
    PIPE_READMODE_BYTE = 0x00000000
    PIPE_WAIT = 0x00000000
    PIPE_UNLIMITED_INSTANCES = 255
    BUFFER_SIZE = 65536
    NMPWAIT_WAIT_FOREVER = 0xFFFFFFFF
    INVALID_HANDLE_VALUE = -1

    full_name = f"\\\\.\\pipe\\{pipe_name}"

    kernel32 = ctypes.windll.kernel32
    kernel32.CreateNamedPipeW.restype = wt.HANDLE
    kernel32.CreateNamedPipeW.argtypes = [
        wt.LPCWSTR,  # lpName
        wt.DWORD,    # dwOpenMode
        wt.DWORD,    # dwPipeMode
        wt.DWORD,    # nMaxInstances
        wt.DWORD,    # nOutBufferSize
        wt.DWORD,    # nInBufferSize
        wt.DWORD,    # nDefaultTimeOut
        ctypes.c_void_p,  # lpSecurityAttributes
    ]

    handle = kernel32.CreateNamedPipeW(
        full_name,
        PIPE_ACCESS_DUPLEX,
        PIPE_TYPE_BYTE | PIPE_READMODE_BYTE | PIPE_WAIT,
        PIPE_UNLIMITED_INSTANCES,
        BUFFER_SIZE,
        BUFFER_SIZE,
        NMPWAIT_WAIT_FOREVER,
        None,
    )

    if handle == INVALID_HANDLE_VALUE or handle == wt.HANDLE(INVALID_HANDLE_VALUE).value:
        error_code = ctypes.GetLastError()
        raise OSError(
            f"CreateNamedPipeW failed for '{full_name}' (error {error_code}). "
            "Check that the pipe name is not already in use."
        )

    return handle


def _connect_named_pipe(handle):
    """Block until a client connects to the pipe."""
    import ctypes
    import ctypes.wintypes as wt

    kernel32 = ctypes.windll.kernel32
    kernel32.ConnectNamedPipe.restype = ctypes.c_bool
    kernel32.ConnectNamedPipe.argtypes = [wt.HANDLE, ctypes.c_void_p]

    success = kernel32.ConnectNamedPipe(handle, None)
    if not success:
        error_code = ctypes.GetLastError()
        # ERROR_PIPE_CONNECTED (535) means client connected between Create and Connect -- that is OK
        ERROR_PIPE_CONNECTED = 535
        if error_code != ERROR_PIPE_CONNECTED:
            raise OSError(f"ConnectNamedPipe failed (error {error_code}).")


def _disconnect_named_pipe(handle):
    """Disconnect the client from the pipe (reuse handle for next client)."""
    import ctypes
    import ctypes.wintypes as wt

    kernel32 = ctypes.windll.kernel32
    kernel32.DisconnectNamedPipe.restype = ctypes.c_bool
    kernel32.DisconnectNamedPipe.argtypes = [wt.HANDLE]
    kernel32.DisconnectNamedPipe(handle)


def _close_handle(handle):
    """Close a Win32 handle."""
    import ctypes
    import ctypes.wintypes as wt

    kernel32 = ctypes.windll.kernel32
    kernel32.CloseHandle.restype = ctypes.c_bool
    kernel32.CloseHandle.argtypes = [wt.HANDLE]
    kernel32.CloseHandle(handle)


def _read_bytes(handle, num_bytes: int) -> bytes:
    """Read exactly num_bytes from the pipe handle. Raises on failure."""
    import ctypes
    import ctypes.wintypes as wt

    kernel32 = ctypes.windll.kernel32
    kernel32.ReadFile.restype = ctypes.c_bool
    kernel32.ReadFile.argtypes = [
        wt.HANDLE,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
        ctypes.c_void_p,
    ]

    buf = ctypes.create_string_buffer(num_bytes)
    total_read = 0

    while total_read < num_bytes:
        bytes_read = wt.DWORD(0)
        chunk_size = num_bytes - total_read
        success = kernel32.ReadFile(
            handle,
            ctypes.byref(buf, total_read),
            wt.DWORD(chunk_size),
            ctypes.byref(bytes_read),
            None,
        )
        if not success or bytes_read.value == 0:
            error_code = ctypes.GetLastError()
            raise OSError(f"ReadFile failed (error {error_code}, read {total_read}/{num_bytes}).")
        total_read += bytes_read.value

    return buf.raw[:num_bytes]


def _write_bytes(handle, data: bytes):
    """Write all bytes to the pipe handle."""
    import ctypes
    import ctypes.wintypes as wt

    kernel32 = ctypes.windll.kernel32
    kernel32.WriteFile.restype = ctypes.c_bool
    kernel32.WriteFile.argtypes = [
        wt.HANDLE,
        ctypes.c_void_p,
        wt.DWORD,
        ctypes.POINTER(wt.DWORD),
        ctypes.c_void_p,
    ]
    kernel32.FlushFileBuffers.restype = ctypes.c_bool
    kernel32.FlushFileBuffers.argtypes = [wt.HANDLE]

    total_written = 0
    while total_written < len(data):
        bytes_written = wt.DWORD(0)
        chunk = data[total_written:]
        success = kernel32.WriteFile(
            handle,
            chunk,
            wt.DWORD(len(chunk)),
            ctypes.byref(bytes_written),
            None,
        )
        if not success:
            error_code = ctypes.GetLastError()
            raise OSError(f"WriteFile failed (error {error_code}).")
        total_written += bytes_written.value

    kernel32.FlushFileBuffers(handle)


# ---------------------------------------------------------------------------
# Framed message I/O (4-byte little-endian length prefix + UTF-8 JSON body)
# ---------------------------------------------------------------------------

def read_message(handle) -> dict:
    """Read a length-prefixed JSON message from the pipe."""
    length_bytes = _read_bytes(handle, 4)
    msg_len = struct.unpack("<I", length_bytes)[0]

    if msg_len == 0:
        return {}
    if msg_len > 100_000_000:  # 100 MB sanity limit
        raise ValueError(f"Message length {msg_len} exceeds 100 MB limit.")

    body_bytes = _read_bytes(handle, msg_len)
    return json.loads(body_bytes.decode("utf-8"))


def write_message(handle, obj: dict):
    """Write a length-prefixed JSON message to the pipe."""
    body = json.dumps(obj, ensure_ascii=False, default=_json_default)
    body_bytes = body.encode("utf-8")
    length_bytes = struct.pack("<I", len(body_bytes))
    _write_bytes(handle, length_bytes + body_bytes)


def _json_default(o):
    """JSON serializer fallback for numpy types etc."""
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        if np.isnan(o) or np.isinf(o):
            return None
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


# ---------------------------------------------------------------------------
# Engine version info
# ---------------------------------------------------------------------------

def _get_engine_versions() -> dict:
    """Build the EngineVersions dict."""
    # Engine version from VERSION.txt
    engine_version = "0.0.0"
    if os.path.isfile(VERSION_FILE):
        with open(VERSION_FILE, "r") as f:
            engine_version = f.read().strip()

    # Packages hash from requirements.lock.txt
    packages_hash = ""
    packages_freeze = ""
    if os.path.isfile(REQUIREMENTS_FILE):
        with open(REQUIREMENTS_FILE, "r") as f:
            content = f.read()
            packages_freeze = content.strip()
            packages_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]

    return {
        "python_version": platform.python_version(),
        "engine_version": engine_version,
        "packages_hash": packages_hash,
        "packages_freeze": packages_freeze,
    }


# ---------------------------------------------------------------------------
# Seed management
# ---------------------------------------------------------------------------

def _set_deterministic_seeds(seed: int):
    """Set seeds for reproducibility across all RNG sources."""
    random.seed(seed)
    np.random.seed(seed)

    # PyTorch (optional)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Technique dispatch
# ---------------------------------------------------------------------------

# Cache imported modules
_module_cache = {}


def _load_technique(technique_id: str):
    """
    Import the technique module for the given technique_id.
    Returns the module's ``run`` function.
    """
    from techniques.registry import TECHNIQUE_REGISTRY

    module_path = TECHNIQUE_REGISTRY.get(technique_id)
    if module_path is None:
        raise ValueError(
            f"Unknown technique '{technique_id}'. "
            f"Available techniques: {', '.join(sorted(TECHNIQUE_REGISTRY.keys()))}"
        )

    if module_path not in _module_cache:
        _module_cache[module_path] = importlib.import_module(module_path)

    mod = _module_cache[module_path]
    if not hasattr(mod, "run"):
        raise ValueError(f"Technique module '{module_path}' has no 'run' function.")

    return mod.run


# ---------------------------------------------------------------------------
# Request handler
# ---------------------------------------------------------------------------

def handle_request(handle, raw_request: dict):
    """
    Process a single RunRequest and send progress events + final RunResponse.
    """
    from techniques.base import RunContext, make_error_response

    engine_versions = _get_engine_versions()

    # Validate minimal fields
    run_id = raw_request.get("run_id", "unknown")
    technique_id = raw_request.get("technique_id", "")

    if not technique_id:
        resp = {
            "run_id": run_id,
            "status": "failure",
            "error_message": "No technique_id provided in the request.",
            "error_fixes": ["Ensure the add-in sends a valid technique_id."],
            "tables": [],
            "warnings": [],
            "audit_fields": {},
            "artifacts": {},
            "engine_versions": engine_versions,
        }
        write_message(handle, resp)
        return

    log.info(f"Run {run_id}: technique={technique_id}, preset={raw_request.get('preset', '?')}")

    # Build context
    ctx = RunContext(raw_request)

    # Set seeds
    _set_deterministic_seeds(ctx.seed)

    # Progress callback: sends a progress event over the pipe
    def send_progress(stage: str, pct: int, message: str = None):
        evt = {
            "type": "progress",
            "stage": stage,
            "pct": pct,
            "message": message or stage,
        }
        try:
            write_message(handle, evt)
        except Exception as e:
            log.warning(f"Failed to send progress event: {e}")

    # Load and run technique
    try:
        send_progress("Loading technique", 2)
        run_fn = _load_technique(technique_id)

        send_progress("Starting analysis", 5)
        start_time = time.perf_counter()

        response = run_fn(ctx, send_progress)

        elapsed = time.perf_counter() - start_time
        log.info(f"Run {run_id}: completed in {elapsed:.2f}s, status={response.get('status', '?')}")

        # Attach engine_versions and timing
        response["engine_versions"] = engine_versions
        if "audit_fields" not in response:
            response["audit_fields"] = {}
        response["audit_fields"]["elapsed_seconds"] = round(elapsed, 3)

        # If we flipped the input to chronological order, flip the output
        # table rows back so the user's original orientation (typically
        # newest-first from the CSVs we ship) is preserved. Techniques
        # all produce rows in internal chronological order; this undoes
        # that at the display boundary.
        if getattr(ctx, "input_was_reversed", False):
            for tbl in response.get("tables") or []:
                # Only reverse time-ordered tables — identified by a "Time"
                # (or "Date") column among the first two positions. Non-
                # time tables (e.g. "Diagnostics", "Coefficients") should
                # keep their natural ordering.
                cols = tbl.get("columns") or []
                if not cols:
                    continue
                first_two = [str(c).lower() for c in cols[:2]]
                if any(c in ("time", "date", "timestamp") for c in first_two):
                    rows = tbl.get("rows")
                    if isinstance(rows, list):
                        tbl["rows"] = list(reversed(rows))

    except ValueError as e:
        log.warning(f"Run {run_id}: ValueError: {e}")
        response = make_error_response(
            ctx,
            str(e),
            engine_versions=engine_versions,
        )
    except Exception as e:
        log.error(f"Run {run_id}: unhandled exception: {e}\n{traceback.format_exc()}")
        response = make_error_response(
            ctx,
            f"An unexpected error occurred: {e}",
            error_fixes=[
                "Check your data for unexpected formats or values.",
                "Try a different preset (Fast/Balanced/Thorough).",
                "If the problem persists, please report the issue.",
            ],
            engine_versions=engine_versions,
        )

    # Send final response
    write_message(handle, response)


# ---------------------------------------------------------------------------
# Main server loop
# ---------------------------------------------------------------------------

def serve(pipe_name: str):
    """
    Main server loop: create a Named Pipe, accept connections, handle requests.
    Loops forever (process is killed by the C# add-in on shutdown).
    """
    log.info(f"Engine worker starting. Pipe: {pipe_name}, PID: {os.getpid()}")
    log.info(f"Python: {platform.python_version()}, Platform: {platform.platform()}")
    log.info(f"Engine dir: {ENGINE_DIR}")

    # Verify no network access
    if os.environ.get("TSL_NO_NETWORK") == "1":
        log.info("TSL_NO_NETWORK=1: network access is disabled by policy.")

    # Create the named pipe FIRST — before warming JIT — so the C# client's
    # connect (NamedPipeClientStream.ConnectAsync, ~10s timeout) succeeds
    # immediately on a cold engine instead of racing the ~10s JIT warm that
    # used to delay pipe creation (the diagnosed cold-start connect race). A
    # client may connect — and buffer its small request — while we warm below;
    # the accept loop's ConnectNamedPipe then returns ERROR_PIPE_CONNECTED,
    # which _connect_named_pipe already treats as success. This decouples
    # connection establishment from warm-up time entirely.
    pipe_handle = _create_named_pipe(pipe_name)
    log.info(f"Named pipe created: \\\\.\\pipe\\{pipe_name}")
    log.info("Pipe open; client may connect now while JIT caches warm.")

    # Bond Yield Forecast Session 5 (§5.3) — eager numba JIT warming.
    # The bond_yield_forecast subpackage uses @jit(cache=True) on FFBS
    # state sampling and conditional-forecast inner loops. First-call
    # JIT compilation costs ~5-8s; warming once at process startup
    # amortizes that against all subsequent requests and avoids a
    # surprise latency spike on the first BYF run. The warmer runs
    # representative trace inputs through each @jit-decorated function
    # to populate the on-disk cache.
    #
    # Defensive: wrapped in broad try/except so a missing subpackage
    # (e.g., a future stripped-build profile) cannot crash engine
    # startup. Failure mode is graceful — first BYF call pays the
    # JIT cost instead.
    #
    # Lazy-warming alternative: if measured warming exceeds 10s on
    # field hardware, move this hook into the bond_yield_forecast
    # dispatch path so warming only fires when the technique is
    # actually invoked. Current measurement on dev hardware: <2s.
    try:
        _t_warm = time.time()
        from techniques.bond_yield_forecast._jit_warmer import (
            warm_jit_caches,
        )
        warm_jit_caches()
        _warm_dur = time.time() - _t_warm
        log.info(
            f"JIT caches warmed (bond_yield_forecast): {_warm_dur:.2f}s"
        )
    except Exception as e:
        # Non-fatal — first BYF call will pay the JIT cost on demand.
        log.warning(
            f"JIT warming skipped (non-fatal): {type(e).__name__}: {e}"
        )

    try:
        while True:
            log.info("Waiting for client connection...")
            _connect_named_pipe(pipe_handle)
            log.info("Client connected.")

            try:
                raw_request = read_message(pipe_handle)
                handle_request(pipe_handle, raw_request)
            except OSError as e:
                log.warning(f"Pipe I/O error during request: {e}")
            except json.JSONDecodeError as e:
                log.warning(f"Invalid JSON from client: {e}")
                try:
                    err_resp = {
                        "run_id": "unknown",
                        "status": "failure",
                        "error_message": f"Invalid JSON in request: {e}",
                        "error_fixes": ["Ensure the add-in sends valid JSON."],
                        "tables": [],
                        "warnings": [],
                        "audit_fields": {},
                        "artifacts": {},
                        "engine_versions": _get_engine_versions(),
                    }
                    write_message(pipe_handle, err_resp)
                except Exception:
                    pass
            except Exception as e:
                log.error(f"Unexpected error handling request: {e}\n{traceback.format_exc()}")
            finally:
                _disconnect_named_pipe(pipe_handle)
                log.info("Client disconnected. Ready for next connection.")

    except KeyboardInterrupt:
        log.info("Shutting down (KeyboardInterrupt).")
    finally:
        _close_handle(pipe_handle)
        log.info("Pipe handle closed. Engine worker exiting.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Time Series Lab Python Engine Worker (Named Pipe Server)"
    )
    parser.add_argument(
        "--pipe",
        required=True,
        help="Name of the Windows Named Pipe (without \\\\.\\pipe\\ prefix).",
    )
    args = parser.parse_args()

    # Validate platform
    if sys.platform != "win32":
        log.error("This engine worker requires Windows (Named Pipes). Exiting.")
        sys.exit(1)

    serve(args.pipe)


if __name__ == "__main__":
    main()
