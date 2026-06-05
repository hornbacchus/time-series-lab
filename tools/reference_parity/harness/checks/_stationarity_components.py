"""Shared parameterized cross-package reference helpers for the
stationarity-test components (ADF / KPSS / PP) vs R ``urca``.

Phase 7+ deeper-validation, scope-extension PILOT (``adf_test`` joint
triage). Each function runs the ``urca`` reference for ONE component at
**caller-supplied** ``(lag, regression)`` params, so the same plumbing
serves multiple units:

- ``p3_adf_triage`` invokes them at the engine's **realized** triage
  params — the library-selected lags (statsmodels AIC autolag, KPSS
  ``nlags="auto"``, PP Schwert) read back from the engine helpers — to
  validate the statistic *given* the selected lag (a trusted-library
  primitive; the selection rule itself is not re-validated).
- the future ``kpss`` scope-extension unit can invoke ``kpss_reference``
  at its **standalone** pinned params.

One implementation of the urca plumbing + the ``regression`` → urca
``type``/``model`` mapping; no duplication across sibling units. These
are three thin wrappers, NOT a generic framework.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge

# regression-family -> urca type/model per component.
_ADF_TYPE = {"c": "drift", "ct": "trend", "n": "none", "nc": "none"}
_KPSS_TYPE = {"c": "mu", "ct": "tau"}
_PP_MODEL = {"c": "constant", "ct": "trend"}


def _rcall(r_code: str, y: np.ndarray) -> tuple[float, float, str]:
    """Run one urca script via RBridge; return (stat, cv5, urca_version)."""
    bridge = RBridge(Manifest.load())
    outputs, versions = bridge.rscript_call(
        r_code=r_code,
        inputs={"y": np.asarray(y, dtype=np.float64).reshape(-1, 1)},
        output_names=["scalars"], timeout_sec=60,
        capture_versions_for=["urca"],
    )
    sc = np.atleast_1d(outputs["scalars"]).reshape(-1)
    return float(sc[0]), float(sc[1]), versions.get("urca", "unknown")


def adf_reference(y: np.ndarray, *, lag: int, regression: str = "c") -> dict[str, Any]:
    """R ``urca::ur.df`` tau statistic at caller-supplied lag."""
    rtype = _ADF_TYPE.get(regression, "drift")
    r_code = rf"""
        suppressPackageStartupMessages({{ library(urca) }})
        y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
        test <- ur.df(y, type = "{rtype}", lags = {int(lag)})
        stat <- as.numeric(test@teststat[1])
        cv5 <- as.numeric(test@cval[1, "5pct"])
        scalars <- c(test_statistic = stat, cv5 = cv5)
        write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                    sep=",", row.names=FALSE, col.names=FALSE)
    """
    stat, cv5, ver = _rcall(r_code, y)
    return {"test_statistic": stat, "cv5": cv5, "urca_version": ver,
            "lag": int(lag), "type": rtype}


def kpss_reference(y: np.ndarray, *, lag: int, regression: str = "c") -> dict[str, Any]:
    """R ``urca::ur.kpss`` eta statistic at caller-supplied bandwidth."""
    rtype = _KPSS_TYPE.get(regression, "mu")
    r_code = rf"""
        suppressPackageStartupMessages({{ library(urca) }})
        y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
        test <- ur.kpss(y, type = "{rtype}", use.lag = {int(lag)})
        stat <- as.numeric(test@teststat[1])
        cv5 <- as.numeric(test@cval[1, "5pct"])
        scalars <- c(test_statistic = stat, cv5 = cv5)
        write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                    sep=",", row.names=FALSE, col.names=FALSE)
    """
    stat, cv5, ver = _rcall(r_code, y)
    return {"test_statistic": stat, "cv5": cv5, "urca_version": ver,
            "lag": int(lag), "type": rtype}


def pp_reference(y: np.ndarray, *, lag: int, regression: str = "c") -> dict[str, Any]:
    """R ``urca::ur.pp`` Z-tau statistic at caller-supplied bandwidth.

    PP is the Pattern-J component (kernel/divisor convention divergence);
    callers should compare it against a widened band, not bit-exact.
    """
    model = _PP_MODEL.get(regression, "constant")
    r_code = rf"""
        suppressPackageStartupMessages({{ library(urca) }})
        y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
        test <- ur.pp(y, type = "Z-tau", model = "{model}", use.lag = {int(lag)})
        stat <- as.numeric(test@teststat[1])
        cv5 <- as.numeric(test@cval[1, "5pct"])
        scalars <- c(test_statistic = stat, cv5 = cv5)
        write.table(matrix(scalars, ncol=1), "{{{{OUTPUT_scalars}}}}",
                    sep=",", row.names=FALSE, col.names=FALSE)
    """
    stat, cv5, ver = _rcall(r_code, y)
    return {"test_statistic": stat, "cv5": cv5, "urca_version": ver,
            "lag": int(lag), "model": model}


__all__ = ["adf_reference", "kpss_reference", "pp_reference"]
