"""R subprocess bridge — harness-grade promotion of the Phase 1
``tools/reference_parity/scripts/rscript_bridge.py`` utility.

What carries over from the Phase 1 bridge (do NOT re-derive):
- numpy ↔ R CSV roundtrip via ``np.savetxt(fmt='%.18e')``
- ``{{INPUT_<name>}}`` / ``{{OUTPUT_<name>}}`` placeholder syntax
- ``.libPaths`` prolog injection
- B2 NA-header bug fix (``_count_header_rows`` consumes
  post-substitution text where R "NA" tokens have already been
  replaced with "nan")
- per-call JSONL logging (audit trail preserved)

What's new in the harness promotion:
- Class-based ``RBridge`` with manifest-driven Rscript exe and
  libs path
- ``check_environment()`` returns a dict of installed R + R
  package versions, raises ``RNotAvailableError`` if R is
  missing
- ``rscript_call`` (instance method) returns ``(outputs, version_metadata)``
  tuple so callers capture which versions of which R packages
  produced the output
- Exception hierarchy:
    RBridgeError                 (base — common to all)
      RNotAvailableError         (R / Rscript not on PATH)
      RPackageMissingError       (a referenced package isn't
                                  installed in the libs_user
                                  tree)
      RSubprocessTimeoutError    (timeout exceeded)
      RScriptExecutionError      (R returned non-zero)
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import os
import pathlib
import re
import subprocess
import time
import uuid
from typing import Any, Mapping, Sequence

import numpy as np

from reference_parity.harness.manifest import Manifest


# ---------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------

class RBridgeError(RuntimeError):
    """Base class for all R-bridge errors."""

    def __init__(
        self,
        message: str,
        *,
        stdout: str = "",
        stderr: str = "",
        returncode: int = -1,
        tempfile_paths: Sequence[str] = (),
        r_code: str = "",
    ) -> None:
        super().__init__(message)
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode
        self.tempfile_paths = list(tempfile_paths)
        self.r_code = r_code

    def __str__(self) -> str:  # noqa: D401
        base = super().__str__()
        parts = [base]
        if self.returncode != -1:
            parts.append(f"returncode={self.returncode}")
        if self.stderr:
            parts.append(f"stderr=\n{self.stderr.strip()}")
        if self.tempfile_paths:
            parts.append(
                "tempfiles preserved at:\n  "
                + "\n  ".join(self.tempfile_paths)
            )
        return "\n".join(parts)


class RNotAvailableError(RBridgeError):
    """R / Rscript executable not found on the machine. Runner
    translates this to a SKIP outcome rather than failing the
    whole tier sweep."""


class RPackageMissingError(RBridgeError):
    """A required R package is not installed in libs_user."""


class RSubprocessTimeoutError(RBridgeError):
    """Subprocess exceeded its timeout budget."""


class RScriptExecutionError(RBridgeError):
    """Rscript returned a non-zero exit code."""


# ---------------------------------------------------------------------
# Internal helpers (lifted verbatim from Phase 1 bridge — preserves
# the B2 NA-header bug fix)
# ---------------------------------------------------------------------

def _posix_path(p: os.PathLike | str) -> str:
    return str(pathlib.Path(p).resolve()).replace("\\", "/")


def _save_input_csv(path: pathlib.Path, arr: np.ndarray) -> None:
    arr = np.asarray(arr, dtype=np.float64)
    if arr.ndim > 2:
        raise ValueError(
            f"r_bridge supports 1-D and 2-D arrays only; "
            f"got ndim={arr.ndim}"
        )
    np.savetxt(path, arr, fmt="%.18e", delimiter=",")


def _count_header_rows(text: str, delim: str | None) -> int:
    """B2-fixed header detection: consumes POST-substitution text
    where R 'NA' tokens have already become 'nan' (so all-NA rows
    parse as numeric and aren't mis-classified as headers)."""
    first_line = text.split("\n", 1)[0].strip()
    if not first_line:
        return 0
    tokens = first_line.split(delim) if delim else first_line.split()
    for tok in tokens:
        t = tok.strip().strip('"').strip("'")
        if not t:
            continue
        try:
            float(t)
        except ValueError:
            return 1
    return 0


def _load_output_csv(path: pathlib.Path) -> np.ndarray:
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    text = content.strip()
    if not text:
        return np.array([])
    substituted = (
        text.replace("NaN", "nan")
        .replace("NA", "nan")
        .replace("Inf", "inf")
    )
    buf = io.StringIO(substituted)
    try:
        buf.seek(0)
        return np.loadtxt(
            buf,
            delimiter=",",
            skiprows=_count_header_rows(substituted, delim=","),
        )
    except ValueError:
        pass
    buf = io.StringIO(substituted)
    return np.loadtxt(
        buf,
        skiprows=_count_header_rows(substituted, delim=None),
    )


def _substitute_placeholders(
    r_code: str,
    input_paths: Mapping[str, str],
    output_paths: Mapping[str, str],
) -> str:
    out = r_code
    for name, path in input_paths.items():
        out = out.replace(f"{{{{INPUT_{name}}}}}", path)
    for name, path in output_paths.items():
        out = out.replace(f"{{{{OUTPUT_{name}}}}}", path)
    if "{{INPUT_" in out or "{{OUTPUT_" in out:
        leftovers = re.findall(
            r"\{\{(?:INPUT|OUTPUT)_[A-Za-z0-9_]+\}\}", out,
        )
        raise ValueError(
            f"Unsubstituted placeholders in r_code: {leftovers}"
        )
    return out


# ---------------------------------------------------------------------
# RBridge class
# ---------------------------------------------------------------------

class RBridge:
    """Class-based R subprocess bridge driven by the harness
    manifest.

    Parameters
    ----------
    manifest : Manifest
        Loaded manifest providing rscript_exe + libs_user.
    log_path : pathlib.Path or None
        Destination for per-call JSONL audit trail. Defaults
        to ``tools/reference_parity/reports/_rscript_call_log.jsonl``.
    tmp_dir : pathlib.Path or None
        Tempfile root. Defaults to
        ``tools/reference_parity/fixtures/_tmp/``.
    """

    def __init__(
        self,
        manifest: Manifest,
        *,
        log_path: pathlib.Path | None = None,
        tmp_dir: pathlib.Path | None = None,
    ) -> None:
        self.manifest = manifest
        parity_root = pathlib.Path(__file__).resolve().parent.parent
        self.tmp_dir = tmp_dir or (parity_root / "fixtures" / "_tmp")
        self.log_path = log_path or (
            parity_root / "reports" / "_rscript_call_log.jsonl"
        )
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        # Cache the libs_user resolution so the diagnostic stderr
        # line fires at most once per RBridge instance lifetime.
        self._libs_user_warned: bool = False

    def _resolve_libs_user(self) -> tuple[str | None, bool]:
        """Resolve manifest's R libs_user against the running
        environment.

        Returns
        -------
        (manifest_libs, valid) : tuple
            ``manifest_libs`` is the manifest's configured value
            (may be empty string or None). ``valid`` is True iff
            the path is non-empty AND exists on disk.

        When ``valid`` is False we deliberately do NOT export
        ``R_LIBS_USER`` and do NOT prepend the manifest path to
        ``.libPaths()`` in the R prolog — letting the runner's own
        ``R_LIBS_USER`` (set by ``r-lib/setup-r`` on CI, system
        default elsewhere) take effect. This unblocks CI runners
        and other environments where the developer-local
        ``C:/Users/matth/R-library`` doesn't exist while
        preserving the manifest-pinned behavior on the dev machine.

        Logs the fallback decision to stderr at most once per
        RBridge instance for debuggability.
        """
        manifest_libs = self.manifest.r.libs_user
        valid = bool(manifest_libs) and pathlib.Path(
            manifest_libs,
        ).exists()
        if not valid and not self._libs_user_warned:
            import sys
            if manifest_libs:
                print(
                    f"[r_bridge] manifest libs_user "
                    f"{manifest_libs!r} does not exist; "
                    f"using runner R_LIBS_USER instead.",
                    file=sys.stderr,
                )
            else:
                print(
                    "[r_bridge] manifest libs_user empty; "
                    "using runner R_LIBS_USER.",
                    file=sys.stderr,
                )
            self._libs_user_warned = True
        return manifest_libs, valid

    # -----------------------------------------------------------------
    # Environment probe
    # -----------------------------------------------------------------

    def check_environment(self) -> dict[str, Any]:
        """Probe the R environment and return a dict of installed
        versions plus per-package divergences from the manifest.

        Raises
        ------
        RNotAvailableError
            If Rscript cannot be found / invoked.
        """
        if not pathlib.Path(self.manifest.r.rscript_exe).exists():
            raise RNotAvailableError(
                f"Rscript not found at "
                f"{self.manifest.r.rscript_exe}; manifest pin "
                f"is incorrect for this machine OR R is not "
                f"installed."
            )
        # Build a tiny R script that prints package versions
        manifest_libs, libs_valid = self._resolve_libs_user()
        pkgs = list(self.manifest.r.packages.keys())
        if libs_valid:
            libs_arg = f'c("{manifest_libs}", .libPaths())'
        else:
            libs_arg = '.libPaths()'  # keep current paths
        r_lines = [
            f'.libPaths({libs_arg})',
            f'cat(sprintf("R=%s.%s\\n", '
            f'R.version[["major"]], R.version[["minor"]]))',
        ]
        for p in pkgs:
            r_lines.append(
                f'cat(sprintf("{p}=%s\\n", '
                f'tryCatch(as.character(packageVersion("{p}")), '
                f'error = function(e) "MISSING")))'
            )
        script = "\n".join(r_lines)
        script_path = self._unique_tmpfile("envcheck", ".R")
        script_path.write_text(script, encoding="utf-8")
        env = os.environ.copy()
        if libs_valid:
            env["R_LIBS_USER"] = manifest_libs
        # else: inherit runner R_LIBS_USER unchanged
        try:
            result = subprocess.run(
                [self.manifest.r.rscript_exe, str(script_path)],
                capture_output=True, text=True, timeout=30, env=env,
            )
        except FileNotFoundError as e:
            raise RNotAvailableError(
                f"Rscript executable not invokable: {e}"
            ) from e
        if result.returncode != 0:
            raise RScriptExecutionError(
                f"check_environment script failed: "
                f"{result.stderr.strip()}",
                stdout=result.stdout, stderr=result.stderr,
                returncode=result.returncode,
            )
        installed: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if "=" in line:
                k, _, v = line.partition("=")
                installed[k.strip()] = v.strip()
        # Compare to manifest
        divergences: dict[str, dict[str, str]] = {}
        for p, pinned in self.manifest.r.packages.items():
            actual = installed.get(p, "MISSING")
            if actual == "MISSING":
                divergences[p] = {"pinned": pinned, "actual": "MISSING"}
            elif actual != pinned:
                divergences[p] = {"pinned": pinned, "actual": actual}
        try:
            script_path.unlink()
        except Exception:
            pass
        return {
            "r_version": installed.get("R", "unknown"),
            "r_packages_installed": {
                k: v for k, v in installed.items() if k != "R"
            },
            "r_packages_divergences": divergences,
        }

    # -----------------------------------------------------------------
    # Core call interface
    # -----------------------------------------------------------------

    def rscript_call(
        self,
        r_code: str,
        inputs: Mapping[str, np.ndarray] | None = None,
        output_names: Sequence[str] = (),
        *,
        keep_tempfiles: bool = False,
        timeout_sec: int = 120,
        capture_versions_for: Sequence[str] = (),
    ) -> tuple[dict[str, np.ndarray], dict[str, str]]:
        """Invoke R via Rscript subprocess. Returns
        ``(outputs, version_metadata)``.

        ``capture_versions_for`` lists R package names whose
        versions the caller wants snapshotted into
        ``version_metadata``. The bridge inserts a small prolog
        that prints these versions to stdout and parses them
        out before returning.
        """
        inputs = dict(inputs or {})
        output_names = list(output_names)
        capture_pkgs = list(capture_versions_for)

        # Allocate tempfiles
        input_paths: dict[str, str] = {}
        input_files: list[pathlib.Path] = []
        for name, arr in inputs.items():
            p = self._unique_tmpfile(f"in_{name}", ".csv")
            _save_input_csv(p, np.asarray(arr))
            input_paths[name] = _posix_path(p)
            input_files.append(p)

        output_paths: dict[str, str] = {}
        output_files: list[pathlib.Path] = []
        for name in output_names:
            p = self._unique_tmpfile(f"out_{name}", ".csv")
            output_paths[name] = _posix_path(p)
            output_files.append(p)

        r_code_sub = _substitute_placeholders(
            r_code, input_paths, output_paths,
        )

        # Prolog: libpaths + version-capture lines.
        # Conditional on whether manifest libs_user is valid on
        # this machine (defensive fallback for CI / non-dev envs).
        manifest_libs, libs_valid = self._resolve_libs_user()
        if libs_valid:
            libs_arg = f'c("{manifest_libs}", .libPaths())'
        else:
            libs_arg = '.libPaths()'  # keep current paths
        prolog_lines = [
            f'.libPaths({libs_arg})',
            'options(warn = 1)',
        ]
        for p in capture_pkgs:
            prolog_lines.append(
                f'cat(sprintf("__PARITY_VERSION__{p}=%s\\n", '
                f'tryCatch(as.character(packageVersion("{p}")), '
                f'error = function(e) "MISSING")))'
            )
        prolog = "\n".join(prolog_lines) + "\n"
        r_code_full = prolog + r_code_sub

        script_path = self._unique_tmpfile("script", ".R")
        script_path.write_text(r_code_full, encoding="utf-8")
        all_tempfiles = input_files + output_files + [script_path]

        env = os.environ.copy()
        if libs_valid:
            env["R_LIBS_USER"] = manifest_libs
        # else: inherit runner R_LIBS_USER unchanged

        t0 = time.monotonic()
        try:
            result = subprocess.run(
                [self.manifest.r.rscript_exe, str(script_path)],
                capture_output=True, text=True,
                timeout=timeout_sec, env=env,
            )
        except subprocess.TimeoutExpired as e:
            self._log_call(
                r_code_full=r_code_full,
                duration_sec=time.monotonic() - t0,
                inputs=inputs, outputs={}, returncode=-1,
                tempfiles=[str(p) for p in all_tempfiles],
            )
            raise RSubprocessTimeoutError(
                f"Rscript timed out after {timeout_sec}s",
                stdout=e.stdout or "", stderr=e.stderr or "",
                tempfile_paths=[str(p) for p in all_tempfiles],
                r_code=r_code_full,
            ) from e
        except FileNotFoundError as e:
            raise RNotAvailableError(
                f"Rscript executable not found: {e}"
            ) from e
        duration = time.monotonic() - t0

        # Parse version-capture lines from stdout
        version_metadata: dict[str, str] = {}
        for line in result.stdout.splitlines():
            if line.startswith("__PARITY_VERSION__"):
                _, _, kv = line.partition("__PARITY_VERSION__")
                k, _, v = kv.partition("=")
                version_metadata[k.strip()] = v.strip()
                if v.strip() == "MISSING":
                    raise RPackageMissingError(
                        f"R package '{k.strip()}' missing from "
                        f"libs_user. Manifest expected: "
                        f"{self.manifest.r.packages.get(k.strip(), '?')}"
                    )

        if result.returncode != 0:
            self._log_call(
                r_code_full=r_code_full, duration_sec=duration,
                inputs=inputs, outputs={},
                returncode=result.returncode,
                tempfiles=[str(p) for p in all_tempfiles],
            )
            raise RScriptExecutionError(
                f"Rscript returned non-zero exit code "
                f"{result.returncode}",
                stdout=result.stdout, stderr=result.stderr,
                returncode=result.returncode,
                tempfile_paths=[str(p) for p in all_tempfiles],
                r_code=r_code_full,
            )

        outputs: dict[str, np.ndarray] = {}
        for name, p_str in output_paths.items():
            p = pathlib.Path(p_str)
            if not p.exists():
                self._log_call(
                    r_code_full=r_code_full, duration_sec=duration,
                    inputs=inputs, outputs={},
                    returncode=result.returncode,
                    tempfiles=[str(x) for x in all_tempfiles],
                )
                raise RScriptExecutionError(
                    f"R returned 0 but did not create output "
                    f"file '{name}' at {p}",
                    stdout=result.stdout, stderr=result.stderr,
                    returncode=result.returncode,
                    tempfile_paths=[str(x) for x in all_tempfiles],
                    r_code=r_code_full,
                )
            outputs[name] = _load_output_csv(p)

        self._log_call(
            r_code_full=r_code_full, duration_sec=duration,
            inputs=inputs, outputs=outputs,
            returncode=result.returncode,
            tempfiles=[str(p) for p in all_tempfiles],
        )
        if not keep_tempfiles:
            for p in all_tempfiles:
                try:
                    p.unlink()
                except Exception:
                    pass
        return outputs, version_metadata

    # -----------------------------------------------------------------
    # Internal helpers
    # -----------------------------------------------------------------

    def _unique_tmpfile(
        self, prefix: str, suffix: str,
    ) -> pathlib.Path:
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        token = uuid.uuid4().hex[:8]
        return self.tmp_dir / f"{prefix}_{stamp}_{token}{suffix}"

    def _log_call(
        self,
        *,
        r_code_full: str,
        duration_sec: float,
        inputs: Mapping[str, np.ndarray],
        outputs: Mapping[str, np.ndarray],
        returncode: int,
        tempfiles: Sequence[str],
    ) -> None:
        entry = {
            "ts": datetime.datetime.now().isoformat(timespec="seconds"),
            "harness": "parity-v1",
            "r_code_sha": hashlib.sha256(
                r_code_full.encode("utf-8"),
            ).hexdigest()[:16],
            "r_code_len": len(r_code_full),
            "duration_sec": round(duration_sec, 4),
            "returncode": int(returncode),
            "input_shapes": {
                k: list(np.asarray(v).shape) for k, v in inputs.items()
            },
            "output_shapes": {
                k: list(np.asarray(v).shape) for k, v in outputs.items()
            },
            "tempfile_count": len(tempfiles),
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


__all__ = [
    "RBridge",
    "RBridgeError",
    "RNotAvailableError",
    "RPackageMissingError",
    "RSubprocessTimeoutError",
    "RScriptExecutionError",
]
