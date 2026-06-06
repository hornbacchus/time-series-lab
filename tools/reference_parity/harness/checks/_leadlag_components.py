"""Shared parameterized cross-package reference helper for the lead-lag
(cross-correlation) family vs R ``stats::ccf``.

Phase 7+ deeper-validation, scope-extension UNIT 3 (ccf-family). Mirrors
``_stationarity_components.py``: one thin wrapper around the R reference,
invoked by every member arm of ``p3_ccf_family`` (cross_correlation_lag
component arm + the rolling reduction's R leg). The prewhitening filter is
a trusted-library primitive and does NOT get a reference wrapper.

``ccf_reference`` returns R's native ``ccf(x, y)`` over lags
``-max_lag..+max_lag`` as parallel ``lags`` / ``ccf`` arrays. R's
convention: ``ccf(x, y)$acf[k] = cor(x[t+k], y[t])`` — callers align the
engine lag axis to this (the engine's custom CCF uses the opposite-sign
lag index; the caller pins the alignment).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge


def ccf_reference(x: np.ndarray, y: np.ndarray, *, max_lag: int) -> dict[str, Any]:
    """R ``stats::ccf`` cross-correlation over lags -max_lag..+max_lag.

    Returns ``{"lags": np.ndarray, "ccf": np.ndarray, "argmax_lag": int,
    "peak": float}`` — argmax over |ccf| (R lag convention).
    """
    bridge = RBridge(Manifest.load())
    r_code = rf"""
        x <- as.numeric(read.csv("{{{{INPUT_x}}}}", header=FALSE)[, 1])
        y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
        res <- ccf(x, y, lag.max = {int(max_lag)}, plot = FALSE,
                   type = "correlation")
        out <- cbind(as.numeric(res$lag), as.numeric(res$acf))
        write.table(out, "{{{{OUTPUT_ccf}}}}", sep=",",
                    row.names=FALSE, col.names=FALSE)
    """
    outputs, versions = bridge.rscript_call(
        r_code=r_code,
        inputs={"x": np.asarray(x, dtype=np.float64).reshape(-1, 1),
                "y": np.asarray(y, dtype=np.float64).reshape(-1, 1)},
        output_names=["ccf"], timeout_sec=60, capture_versions_for=["urca"],
    )
    arr = np.atleast_2d(outputs["ccf"])
    lags = arr[:, 0].astype(int)
    ccf = arr[:, 1].astype(float)
    j = int(np.argmax(np.abs(ccf)))
    return {"lags": lags, "ccf": ccf, "argmax_lag": int(lags[j]),
            "peak": float(ccf[j]), "r_version": versions}


__all__ = ["ccf_reference"]
