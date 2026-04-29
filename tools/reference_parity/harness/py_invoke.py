"""PyBridge — Python-import reference invocation utility.

Phase 3 Session 5 abstraction: parallel to ``RBridge`` for
the Python references that Phase 3 Batches 7–9 will need
(scipy, sklearn, xgboost, lightgbm, statsmodels, PyTorch,
neuralforecast, prophet, GPyTorch, reservoirpy, MAPIE).

**Hybrid architecture (user-locked).** Asymmetric problem
distribution motivated this:

- **Batches 7–8** (scipy, sklearn, xgboost, lightgbm,
  statsmodels): pure compute, no global state. In-process
  imports cost ~0 overhead. Subprocess symmetry with
  RBridge would impose ~300–500ms subprocess startup +
  CSV/pickle roundtrip per call, ~30× slowdown on cheap
  closed-form refs. → ``isolate=False`` (default).
- **Batch 9** (PyTorch, neuralforecast, Prophet, GPyTorch,
  reservoirpy, MAPIE): PyTorch sets process-global state
  (``torch.manual_seed``, ``cudnn.deterministic``,
  ``cudnn.benchmark``). In-process means check-1's
  settings leak into check-2's seed-pinning, producing
  coupled (non-independent) audit results. → opt-in
  ``isolate=True``.

Per user-locked refinement: do NOT speculatively build
Batch 9 DL-specific seed-pinning features beyond the
``torch.manual_seed`` + cuDNN deterministic flag in the
subprocess entry point. Extend at Batch 9 (Sessions
19–21) per master plan §11 escalation if observed
insufficient.

Public surface
--------------

::

    class PyBridge:
        def py_invoke(
            self,
            reference_callable,
            fixture,
            *,
            extract_fields=None,
            version_packages=None,
            isolate=False,
            isolate_seed=None,
            timeout_sec=120,
        ) -> tuple[dict, dict]:
            '''Invoke a Python reference; return (outputs,
            version_metadata).'''

Exception hierarchy
-------------------

- ``PyBridgeError`` (base)
  - ``PyImportError`` — reference package not installed →
    runner translates to SKIP outcome
  - ``PySubprocessTimeoutError`` — only raised in
    ``isolate=True`` mode
  - ``PySubprocessExecutionError`` — subprocess exited
    non-zero (isolate=True only)
"""

from __future__ import annotations

import importlib
import importlib.metadata as _md
import json
import os
import pathlib
import pickle
import sys
import textwrap
import time
from typing import Any, Callable, Sequence

import numpy as np

from reference_parity.harness.manifest import Manifest
from reference_parity.harness.subprocess_runner import (
    SubprocessTimeoutError,
    log_call_metadata,
    run_subprocess,
    unique_tmpfile,
)


# ---------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------


class PyBridgeError(RuntimeError):
    """Base for all PyBridge errors."""


class PyImportError(PyBridgeError):
    """Reference package not installed. Runner translates to
    SKIP outcome (mirrors RBridge ``RPackageMissingError``)."""


class PySubprocessTimeoutError(PyBridgeError, SubprocessTimeoutError):
    """Subprocess exceeded its timeout in ``isolate=True``
    mode. Inherits both the PyBridge error hierarchy and the
    shared subprocess-runner timeout type so harness-level
    handlers can catch either."""


class PySubprocessExecutionError(PyBridgeError):
    """Subprocess returned non-zero in ``isolate=True``
    mode."""

    def __init__(
        self,
        message: str,
        *,
        stdout: str = "",
        stderr: str = "",
        returncode: int = -1,
        tempfile_paths: Sequence[str] = (),
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.tempfile_paths = list(tempfile_paths)


# ---------------------------------------------------------------------
# Version snapshotting (in-process; mirrors runner.py:_python_versions)
# ---------------------------------------------------------------------


def _capture_versions(packages: Sequence[str]) -> dict[str, str]:
    """Snapshot installed versions of named packages via
    ``importlib.metadata.version``. Missing packages map to
    ``"MISSING"`` (mirrors ``runner.py:_python_versions``).
    """
    out: dict[str, str] = {}
    for pkg in packages or ():
        try:
            out[pkg] = _md.version(pkg)
        except Exception:
            out[pkg] = "MISSING"
    return out


# ---------------------------------------------------------------------
# PyBridge class
# ---------------------------------------------------------------------


class PyBridge:
    """Class-based Python-import bridge.

    Parameters
    ----------
    manifest : Manifest or None
        Loaded manifest; defaults to ``Manifest.load()``.
        Used for version-pin reconciliation (deferred —
        snapshot-only this session).
    log_path : pathlib.Path or None
        Destination for per-call JSONL audit trail in
        ``isolate=True`` mode. Defaults to
        ``tools/reference_parity/reports/_pyscript_call_log.jsonl``.
    tmp_dir : pathlib.Path or None
        Tempfile root for ``isolate=True`` subprocess I/O.
        Defaults to ``tools/reference_parity/fixtures/_tmp/``.
    """

    def __init__(
        self,
        manifest: Manifest | None = None,
        *,
        log_path: pathlib.Path | None = None,
        tmp_dir: pathlib.Path | None = None,
    ) -> None:
        self.manifest = manifest if manifest is not None else Manifest.load()
        parity_root = pathlib.Path(__file__).resolve().parent.parent
        self.tmp_dir = tmp_dir or (parity_root / "fixtures" / "_tmp")
        self.log_path = log_path or (
            parity_root / "reports" / "_pyscript_call_log.jsonl"
        )
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # Public dispatch
    # -----------------------------------------------------------------

    def py_invoke(
        self,
        reference_callable: Callable[[dict[str, Any]], dict[str, Any]],
        fixture: dict[str, Any],
        *,
        extract_fields: Sequence[str] | None = None,
        version_packages: Sequence[str] | None = None,
        isolate: bool = False,
        isolate_seed: int | None = None,
        timeout_sec: int = 120,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Invoke a Python reference and return
        ``(outputs, version_metadata)``.

        Parameters
        ----------
        reference_callable : callable
            Function that accepts the fixture dict and
            returns a dict of extracted fields. In
            ``isolate=True`` mode, the callable must be
            importable by dotted-path
            (``module.submodule.function_name``) so the
            subprocess entry point can locate it.
        fixture : dict
            Reference input; passed verbatim to the
            callable (in-process) or pickled to disk and
            loaded by the subprocess (isolate=True).
        extract_fields : sequence of str or None
            Optional whitelist; when provided, only these
            keys are extracted from the callable's return
            dict. None → return all keys.
        version_packages : sequence of str or None
            Packages whose installed version to snapshot
            into ``version_metadata``.
        isolate : bool
            Whether to run in a subprocess with state
            isolation. Default False (in-process direct
            import).
        isolate_seed : int or None
            Random seed for subprocess state pinning.
            ``isolate=True`` calls
            ``np.random.default_rng(isolate_seed)``,
            ``random.seed(isolate_seed)``, and (if torch
            is importable) ``torch.manual_seed`` +
            ``cudnn.deterministic=True``. Ignored when
            ``isolate=False``.
        timeout_sec : int
            Subprocess timeout in ``isolate=True`` mode.
        """
        # Phase 3 Session 13 (per check-in 1.5 act-now decision #3):
        # ``isolate=False`` shim retired. Empirical evidence across
        # Batches 7+8 (14 wrappers): 0/14 used the in-process shim.
        # All in-process Python references go through direct import
        # (the p3_pca / p3_dfm / p3_random_forest / etc. precedent).
        # PyBridge is now subprocess-isolation-only.
        if not isolate:
            raise PyBridgeError(
                "PyBridge.py_invoke now requires isolate=True. "
                "The in-process shim was retired in Session 13 "
                "(0/14 wrappers used it across Batches 7+8). "
                "For in-process Python references, use direct "
                "import: ``import sklearn; ref = sklearn.X(...)``."
            )
        return self._py_invoke_subprocess(
            reference_callable, fixture,
            extract_fields=list(extract_fields or ()),
            version_packages=list(version_packages or ()),
            isolate_seed=isolate_seed,
            timeout_sec=timeout_sec,
        )

    # -----------------------------------------------------------------
    # Subprocess path (Batch 9)
    # -----------------------------------------------------------------

    def _py_invoke_subprocess(
        self,
        reference_callable: Callable[..., Any],
        fixture: dict[str, Any],
        *,
        extract_fields: list[str],
        version_packages: list[str],
        isolate_seed: int | None,
        timeout_sec: int,
    ) -> tuple[dict[str, Any], dict[str, str]]:
        """Spawn Python subprocess; pickle fixture + callable
        spec; run; pickle outputs back.

        The callable must be addressable by dotted-path
        ``module.func_name`` so the subprocess entry point
        can re-import it. Lambdas / closures cannot be
        isolate=True'd.

        Suitable for stateful references (PyTorch,
        neuralforecast, etc.) where global RNG / cuDNN
        flags would otherwise leak across checks.
        """
        if not callable(reference_callable):
            raise PyBridgeError(
                "isolate=True requires a top-level function "
                "(addressable by module.func_name); got "
                f"{reference_callable!r}"
            )
        module_name = getattr(reference_callable, "__module__", None)
        func_name = getattr(reference_callable, "__qualname__", None)
        if module_name is None or func_name is None or "<lambda>" in (func_name or ""):
            raise PyBridgeError(
                "isolate=True requires a top-level function with "
                "stable __module__ + __qualname__; got "
                f"module={module_name!r} qualname={func_name!r}"
            )

        # Allocate fixture-input + outputs tempfiles
        fixture_path = unique_tmpfile(self.tmp_dir, "py_in", ".pkl")
        outputs_path = unique_tmpfile(self.tmp_dir, "py_out", ".pkl")
        script_path = unique_tmpfile(self.tmp_dir, "py_script", ".py")

        with open(fixture_path, "wb") as f:
            pickle.dump(
                {
                    "fixture": fixture,
                    "extract_fields": extract_fields,
                    "isolate_seed": isolate_seed,
                    "module_name": module_name,
                    "func_name": func_name,
                },
                f,
            )

        # Build entry-point script. Receives:
        #   1) fixture pickle path (argv[1])
        #   2) outputs pickle path (argv[2])
        # Side effects:
        #   - Pin numpy/random/torch seeds when isolate_seed given
        #   - Re-import the callable by dotted-path
        #   - Invoke with fixture
        #   - Pickle the outputs dict
        entry_script = textwrap.dedent("""
            import importlib
            import pickle
            import random
            import sys

            import numpy as np

            with open(sys.argv[1], "rb") as f:
                spec = pickle.load(f)

            seed = spec.get("isolate_seed")
            if seed is not None:
                random.seed(seed)
                np.random.seed(seed)
                try:
                    import torch
                    torch.manual_seed(seed)
                    if hasattr(torch, "cuda") and torch.cuda.is_available():
                        torch.cuda.manual_seed_all(seed)
                    if hasattr(torch.backends, "cudnn"):
                        torch.backends.cudnn.deterministic = True
                        torch.backends.cudnn.benchmark = False
                except ImportError:
                    pass

            module = importlib.import_module(spec["module_name"])
            # Resolve qualname (handle Class.method-style nesting)
            obj = module
            for part in spec["func_name"].split("."):
                obj = getattr(obj, part)

            outputs = obj(spec["fixture"])
            if not isinstance(outputs, dict):
                raise TypeError(
                    f"reference_callable must return a dict; "
                    f"got {type(outputs).__name__}"
                )
            extract = spec.get("extract_fields") or []
            if extract:
                outputs = {k: outputs[k] for k in extract if k in outputs}

            with open(sys.argv[2], "wb") as f:
                pickle.dump(outputs, f)
        """).strip()
        script_path.write_text(entry_script, encoding="utf-8")

        argv = [sys.executable, str(script_path),
                str(fixture_path), str(outputs_path)]
        env = os.environ.copy()
        # Inherit harness PYTHONPATH so the subprocess can locate
        # the reference module if it lives under tools/.
        env.setdefault("PYTHONPATH", os.environ.get("PYTHONPATH", ""))

        all_tempfiles = [fixture_path, outputs_path, script_path]
        t0 = time.monotonic()
        try:
            result = run_subprocess(
                argv, env=env, timeout_sec=timeout_sec,
            )
        except SubprocessTimeoutError as e:
            log_call_metadata(
                self.log_path,
                script_full=entry_script,
                duration_sec=time.monotonic() - t0,
                inputs={"fixture": fixture},
                outputs={},
                returncode=-1,
                tempfiles=[str(p) for p in all_tempfiles],
                harness_tag="parity-v1-py-isolate",
            )
            raise PySubprocessTimeoutError(
                f"PyBridge subprocess timed out after {timeout_sec}s",
                stdout=e.stdout, stderr=e.stderr,
                tempfile_paths=[str(p) for p in all_tempfiles],
            ) from e
        duration = time.monotonic() - t0

        if result.returncode != 0:
            log_call_metadata(
                self.log_path,
                script_full=entry_script,
                duration_sec=duration,
                inputs={"fixture": fixture},
                outputs={},
                returncode=result.returncode,
                tempfiles=[str(p) for p in all_tempfiles],
                harness_tag="parity-v1-py-isolate",
            )
            raise PySubprocessExecutionError(
                f"PyBridge subprocess returned non-zero exit "
                f"code {result.returncode}",
                stdout=result.stdout, stderr=result.stderr,
                returncode=result.returncode,
                tempfile_paths=[str(p) for p in all_tempfiles],
            )

        with open(outputs_path, "rb") as f:
            outputs = pickle.load(f)

        log_call_metadata(
            self.log_path,
            script_full=entry_script,
            duration_sec=duration,
            inputs={"fixture": fixture},
            outputs=outputs if isinstance(outputs, dict) else {},
            returncode=result.returncode,
            tempfiles=[str(p) for p in all_tempfiles],
            harness_tag="parity-v1-py-isolate",
        )

        # Cleanup tempfiles on success (preserve on failure for
        # post-mortem)
        for p in all_tempfiles:
            try:
                p.unlink()
            except Exception:
                pass

        return outputs, _capture_versions(version_packages)


__all__ = [
    "PyBridge",
    "PyBridgeError",
    "PyImportError",
    "PySubprocessTimeoutError",
    "PySubprocessExecutionError",
]
