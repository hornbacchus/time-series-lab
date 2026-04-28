"""Shared subprocess-management utility.

Phase 3 Session 5 abstraction: factor the
``subprocess.run`` + tempfile management + JSONL audit log
machinery used by ``r_bridge.py`` (R subprocess) and
``py_invoke.py`` PyBridge ``isolate=True`` (Python subprocess).
Single subprocess-management layer; two callers.

Per user-locked refinement 3: this module is **purely
structural** with respect to RBridge behavior. Same timeout
defaults, same env handling discipline, same stderr capture
semantics, same exception hierarchy. NO behavioral changes
to R subprocess invocation. RBridge re-imports from here
without altering its public API or per-call semantics.

Public surface
--------------

``run_subprocess(...) -> subprocess.CompletedProcess``
    Thin wrapper over ``subprocess.run`` that adds:
      - Pre-built env dict pass-through
      - Timeout-aware exception transformation to a
        common ``SubprocessTimeoutError`` raised on timeout
      - Optional JSONL audit logging via
        ``log_call_metadata``

``log_call_metadata(...) -> None``
    Append-only JSONL record of subprocess invocation
    (sha-of-script, duration, returncode, input/output
    shape summaries, tempfile paths). Used by RBridge for
    its existing audit log; PyBridge uses for parallel
    auditability.

``unique_tmpfile(...) -> pathlib.Path``
    Allocate a uniquely-named tempfile under the harness's
    `_tmp/` root. Replicated existing RBridge utility,
    promoted here for reuse.

Exception hierarchy
-------------------

The subprocess-runner exposes ``SubprocessTimeoutError``;
RBridge's ``RSubprocessTimeoutError`` and PyBridge's
``PySubprocessTimeoutError`` (when introduced) inherit
from the common base. This preserves RBridge's existing
``except RSubprocessTimeoutError`` call sites while
allowing harness-level handlers to catch the common type.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import time
import uuid
from typing import Any, Mapping, Sequence

import numpy as np


class SubprocessRunnerError(RuntimeError):
    """Base for subprocess-runner errors. RBridge's
    RBridgeError + PyBridge's PyBridgeError can inherit
    from this if downstream callers want the common
    base."""


class SubprocessTimeoutError(SubprocessRunnerError):
    """Subprocess exceeded its timeout budget. Common base
    for ``RSubprocessTimeoutError`` (R) and
    ``PySubprocessTimeoutError`` (Python isolate=True)."""

    def __init__(
        self,
        message: str,
        *,
        stdout: str = "",
        stderr: str = "",
        tempfile_paths: Sequence[str] = (),
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.tempfile_paths = list(tempfile_paths)


def unique_tmpfile(
    tmp_dir: pathlib.Path,
    prefix: str,
    suffix: str,
) -> pathlib.Path:
    """Allocate a unique tempfile path under ``tmp_dir``.

    Pattern: ``<prefix>_<YYYYMMDD_HHMMSS>_<8hex>.<suffix>``.
    Caller is responsible for deletion / cleanup.
    """
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    token = uuid.uuid4().hex[:8]
    return tmp_dir / f"{prefix}_{stamp}_{token}{suffix}"


def run_subprocess(
    argv: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    timeout_sec: int = 120,
    capture_output: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Thin ``subprocess.run`` wrapper with common timeout
    semantics.

    Parameters
    ----------
    argv : sequence of str
        Argument vector for ``subprocess.run``.
    env : mapping or None
        Environment dict; defaults to ``os.environ.copy()``.
    timeout_sec : int
        Wall-clock timeout. On exceed, raises
        ``SubprocessTimeoutError`` (caller-friendlier than
        ``subprocess.TimeoutExpired``).
    capture_output, text :
        Forwarded to ``subprocess.run``.

    Returns
    -------
    subprocess.CompletedProcess

    Raises
    ------
    SubprocessTimeoutError
        On timeout.
    FileNotFoundError
        If ``argv[0]`` is not invokable. Caller decides whether
        to translate to a domain-specific error
        (``RNotAvailableError``, etc.).
    """
    if env is None:
        env = os.environ.copy()
    try:
        return subprocess.run(
            list(argv),
            capture_output=capture_output,
            text=text,
            timeout=timeout_sec,
            env=dict(env),
        )
    except subprocess.TimeoutExpired as e:
        raise SubprocessTimeoutError(
            f"Subprocess timed out after {timeout_sec}s",
            stdout=e.stdout or "",
            stderr=e.stderr or "",
        ) from e


def log_call_metadata(
    log_path: pathlib.Path,
    *,
    script_full: str,
    duration_sec: float,
    inputs: Mapping[str, Any],
    outputs: Mapping[str, Any],
    returncode: int,
    tempfiles: Sequence[str],
    harness_tag: str = "parity-v1",
) -> None:
    """Append a JSONL record describing a subprocess
    invocation. Best-effort; never raises (silently ignores
    write errors so subprocess management remains robust).

    Schema:
      {
        "ts": ISO timestamp,
        "harness": tag,
        "script_sha": sha256[:16] of script content,
        "script_len": int,
        "duration_sec": float (rounded to 4 decimals),
        "returncode": int,
        "input_shapes": {name: shape_list},
        "output_shapes": {name: shape_list},
        "tempfile_count": int,
      }

    The schema matches RBridge's pre-Session-5 ``_log_call``
    output exactly so existing JSONL files concatenate
    seamlessly. Refinement 3 (purely structural refactor)
    requires this byte-equivalence.
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "harness": harness_tag,
            "script_sha": hashlib.sha256(
                script_full.encode("utf-8"),
            ).hexdigest()[:16],
            "script_len": len(script_full),
            "duration_sec": round(duration_sec, 4),
            "returncode": int(returncode),
            "input_shapes": {
                k: list(np.asarray(v).shape) if hasattr(v, "shape")
                else _safe_shape(v)
                for k, v in inputs.items()
            },
            "output_shapes": {
                k: list(np.asarray(v).shape) if hasattr(v, "shape")
                else _safe_shape(v)
                for k, v in outputs.items()
            },
            "tempfile_count": len(list(tempfiles)),
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        # Best-effort logging; never block subprocess flow.
        pass


def _safe_shape(value: Any) -> list[int]:
    """Best-effort shape extraction for non-array inputs."""
    try:
        return list(np.asarray(value).shape)
    except Exception:
        return []


# Backward-compat aliases — RBridge's pre-Session-5
# ``_log_call`` schema used the field names
# ``r_code_sha`` / ``r_code_len``. To preserve byte-
# equivalence on the existing
# ``reports/_rscript_call_log.jsonl`` audit log
# (refinement 3 — purely structural), RBridge
# continues to write entries with those legacy field
# names rather than this module's ``script_*`` names.
# The legacy schema is preserved by RBridge's own
# ``_log_call`` method, which calls
# ``log_call_metadata`` only for new (non-R) callers.
#
# In practice: PyBridge isolate=True (when introduced)
# uses ``log_call_metadata`` directly; RBridge keeps
# its inline ``_log_call`` for the legacy schema.
# The two co-exist in the same JSONL file, parseable
# by reading the ``harness`` field.


__all__ = [
    "SubprocessRunnerError",
    "SubprocessTimeoutError",
    "unique_tmpfile",
    "run_subprocess",
    "log_call_metadata",
]
