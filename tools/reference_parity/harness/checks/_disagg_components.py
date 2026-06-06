"""Shared parameterized cross-package reference helper for temporal
disaggregation vs R ``tempdisagg::td``.

Phase 7+ deeper-validation, scope-extension UNIT 4 (denton_chowlin). Mirrors
``_stationarity_components.py`` / ``_leadlag_components.py``: one thin wrapper
around the R reference, invoked by both method arms of
``p3_denton_chowlin_methods`` (Denton + Chow-Lin), parameterized by
method/conversion/ratio/fixed_rho and the regressor design (intercept/trend).

Returns the disaggregated high-frequency series + the model's rho (for
chow-lin methods; used to measure the engine's grid-ML rho gap vs tempdisagg's
continuous-ML rho). The 1/(1-rho^2) AR(1) scaling cancels in the BLUE
distribution, so a chow-lin-fixed match at a pinned rho is expected bit-exact.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge


def tempdisagg_reference(
    agg: np.ndarray, ind: np.ndarray, *, method: str, ratio: int,
    conversion: str = "sum", fixed_rho: float | None = None,
    intercept: bool = True, trend: bool = False,
) -> dict[str, Any]:
    """R ``tempdisagg::td`` disaggregated series + estimated rho.

    Parameters
    ----------
    method : e.g. "denton-cholette", "chow-lin-fixed", "chow-lin-maxlog".
    ratio : high/low frequency ratio (the ts() frequency of the RHS regressors).
    intercept / trend : regressor design — Denton uses ``~ 0 + ind`` (no
        intercept, no trend); the engine's Chow-Lin uses ``~ trend + ind``
        (intercept automatic) to match its [1, trend, indicator] design.
    fixed_rho : passed as ``fixed.rho`` for chow-lin-fixed.
    """
    bridge = RBridge(Manifest.load())
    rhs_terms = []
    if not intercept:
        rhs_terms.append("0")
    if trend:
        rhs_terms.append("trend_ts")
    rhs_terms.append("ind_ts")
    rhs = " + ".join(rhs_terms)
    trend_line = ("trend_ts <- ts(seq_len(n_high), frequency = %d)" % ratio
                  if trend else "")
    rho_arg = ("" if fixed_rho is None else ", fixed.rho = %r" % float(fixed_rho))
    r_code = rf"""
        suppressPackageStartupMessages({{ library(tempdisagg) }})
        agg <- as.numeric(read.csv("{{{{INPUT_agg}}}}", header=FALSE)[, 1])
        ind <- as.numeric(read.csv("{{{{INPUT_ind}}}}", header=FALSE)[, 1])
        n_high <- length(ind)
        agg_ts <- ts(agg, frequency = 1)
        ind_ts <- ts(ind, frequency = {ratio})
        {trend_line}
        res <- td(agg_ts ~ {rhs}, conversion = "{conversion}",
                  method = "{method}"{rho_arg})
        disagg <- as.numeric(predict(res))
        rho_out <- if (!is.null(res$rho)) as.numeric(res$rho) else NA_real_
        write.table(matrix(disagg, ncol=1), "{{{{OUTPUT_disagg}}}}",
                    sep=",", row.names=FALSE, col.names=FALSE)
        write.table(matrix(rho_out, ncol=1), "{{{{OUTPUT_rho}}}}",
                    sep=",", row.names=FALSE, col.names=FALSE)
    """
    outputs, versions = bridge.rscript_call(
        r_code=r_code,
        inputs={"agg": np.asarray(agg, float).reshape(-1, 1),
                "ind": np.asarray(ind, float).reshape(-1, 1)},
        output_names=["disagg", "rho"], timeout_sec=90,
        capture_versions_for=["tempdisagg"],
    )
    disagg = np.atleast_1d(outputs["disagg"]).reshape(-1).astype(float)
    rho_arr = np.atleast_1d(outputs["rho"]).reshape(-1).astype(float)
    rho = float(rho_arr[0]) if rho_arr.size else float("nan")
    return {"disagg": disagg, "rho": rho,
            "tempdisagg_version": versions.get("tempdisagg", "unknown")}


__all__ = ["tempdisagg_reference"]
