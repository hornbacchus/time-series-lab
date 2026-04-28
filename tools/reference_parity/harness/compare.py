"""Shared tolerance-application + verdict-aggregation helpers.

Phase 3 Session 5 abstraction: factored from the inline
copies in ``harness/checks/p3_arima.py`` (originally written
in Session 2; re-imported by p3_sarima / p3_arimax_sarimax /
p3_ets / p3_theta / p3_intermittent / p3_classical_decompose
/ p3_stl / p3_mstl / p3_tbats).

These helpers implement the **Session 2 manual harness pattern**
(documented in `docs/reference_parity/session_2_findings.md`):

- Three-state status per metric: PASS / CAVEAT / BLOCK.
- PASS iff ``max_abs <= abs_tol`` OR ``max_rel <= rel_tol``.
- CAVEAT iff PASS fails AND ``max_abs <= block_abs_tol`` OR
  ``max_rel <= block_rel_tol``. Block thresholds default to
  10× the PASS thresholds.
- BLOCK otherwise.
- ``aggregate_outcome`` reduces a list of per-metric statuses
  to a single overall outcome using the worst-of priority
  ladder.

Pre-Phase-3 checks (smoke, 1c..3f) define their own
comparison logic and do not migrate to this module.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _compare_scalar(
    a: float,
    b: float,
    tol: dict[str, float],
) -> dict[str, Any]:
    """Compare two scalars within an absolute/relative
    tolerance band.

    Parameters
    ----------
    a, b : float
        TSL-side and reference-side scalar values respectively.
    tol : dict
        Tolerance band with keys ``abs_tol``, ``rel_tol``,
        and optionally ``block_abs_tol`` / ``block_rel_tol``
        (defaulted to 10× the PASS thresholds when absent).

    Returns
    -------
    dict
        Metric dict with fields ``status`` (PASS / CAVEAT /
        BLOCK), ``abs_diff``, ``rel_diff``, ``tsl``, ``ref``.
    """
    abs_tol = float(tol.get("abs_tol", 1e-3))
    rel_tol = float(tol.get("rel_tol", 1e-2))
    block_abs_tol = float(tol.get("block_abs_tol", 10 * abs_tol))
    block_rel_tol = float(tol.get("block_rel_tol", 10 * rel_tol))
    a, b = float(a), float(b)
    diff = abs(a - b)
    denom = max(abs(a), abs(b), 1e-300)
    rel = diff / denom
    if diff <= abs_tol or rel <= rel_tol:
        status = "PASS"
    elif diff <= block_abs_tol or rel <= block_rel_tol:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "status": status,
        "abs_diff": diff,
        "rel_diff": rel,
        "tsl": a,
        "ref": b,
    }


def _compare_vector(
    a: np.ndarray,
    b: np.ndarray,
    tol: dict[str, float],
) -> dict[str, Any]:
    """Compare two 1-D vectors element-wise within an
    absolute/relative tolerance band.

    PASS iff every element passes (aggregate
    ``max_abs <= abs_tol`` OR ``max_rel <= rel_tol``);
    CAVEAT if any element CAVEATs but none BLOCK; BLOCK if
    any element BLOCKs.

    Returns
    -------
    dict
        Metric dict with fields ``status``,
        ``max_abs_diff``, ``max_rel_diff``, ``n_compared``,
        ``tsl_first``, ``ref_first``. On shape mismatch:
        ``status="BLOCK"`` and ``shape_mismatch=True``.
    """
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    if a.shape != b.shape:
        return {
            "status": "BLOCK",
            "shape_mismatch": True,
            "tsl_shape": list(a.shape),
            "ref_shape": list(b.shape),
        }
    if a.size == 0:
        return {
            "status": "PASS",
            "max_abs_diff": 0.0,
            "max_rel_diff": 0.0,
            "n_compared": 0,
        }
    abs_tol = float(tol.get("abs_tol", 1e-3))
    rel_tol = float(tol.get("rel_tol", 1e-2))
    block_abs_tol = float(tol.get("block_abs_tol", 10 * abs_tol))
    block_rel_tol = float(tol.get("block_rel_tol", 10 * rel_tol))
    diff = np.abs(a - b)
    denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-300)
    rel = diff / denom
    max_abs = float(np.max(diff))
    max_rel = float(np.max(rel))
    if max_abs <= abs_tol or max_rel <= rel_tol:
        status = "PASS"
    elif max_abs <= block_abs_tol or max_rel <= block_rel_tol:
        status = "CAVEAT"
    else:
        status = "BLOCK"
    return {
        "status": status,
        "max_abs_diff": max_abs,
        "max_rel_diff": max_rel,
        "n_compared": int(a.size),
        "tsl_first": float(a.flat[0]) if a.size > 0 else None,
        "ref_first": float(b.flat[0]) if b.size > 0 else None,
    }


# Status-priority ladder for per-check outcome aggregation.
# Worst status wins. Mirrors harness/base.py _OUTCOME_PRIORITY
# but operates on per-metric (not per-check) status strings.
_STATUS_PRIORITY: dict[str, int] = {
    "PASS": 0,
    "CAVEAT": 1,
    "BLOCK": 2,
}


def aggregate_metric_status(
    metric_dicts: list[dict[str, Any]],
) -> str:
    """Reduce per-metric status strings (PASS/CAVEAT/BLOCK)
    into the worst observed status.

    Empty input → PASS (vacuously true). Status keys not in
    the priority ladder (e.g. INFO from diagnostic-only
    metrics) are ignored.
    """
    seen = [
        m.get("status", "PASS")
        for m in metric_dicts
        if m.get("status") in _STATUS_PRIORITY
    ]
    if not seen:
        return "PASS"
    return max(seen, key=lambda s: _STATUS_PRIORITY[s])


__all__ = [
    "_compare_scalar",
    "_compare_vector",
    "aggregate_metric_status",
]
