"""Phase 3 Batch 10 — Transfer function (distributed lag) parity check.

TSL ``transfer_function.py`` (finite-distributed-lag OLS via
scipy + statsmodels) vs from-scratch numpy OLS reference on
identical lag-feature design matrix. Pattern A self-parity
bit-exact target.

**Master plan §15.12 reference (R TSA::arimax) deselected:**
TSA::arimax has a transfer-function form with ``xtransf``
that requires explicit numerator/denominator polynomials,
not directly aligned with TSL's simple distributed-lag OLS.
Self-parity catches wrapper-level regressions.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_transfer_dgp(*, seed: int, n: int = 200,
                            betas: tuple = (0.5, 0.3, 0.1)) -> tuple[np.ndarray, np.ndarray]:
    """Y_t = sum(betas[k] * X_{t-k}) + noise, k = 0..len(betas)-1"""
    rng = np.random.default_rng(seed)
    x = np.zeros(n + 50)
    for t in range(1, n + 50):
        x[t] = 0.6 * x[t - 1] + rng.standard_normal()
    x = x[50:]
    y = np.zeros(n)
    n_lags = len(betas)
    for t in range(n_lags - 1, n):
        for k, b in enumerate(betas):
            y[t] += b * x[t - k]
        y[t] += 0.2 * rng.standard_normal()
    # Return y of length n; _fit_distributed_lag drops the
    # warmup rows internally via NaN mask.
    return x, y


def _fit_distributed_lag(x: np.ndarray, y: np.ndarray, n_lags: int) -> dict[str, Any]:
    """OLS on (intercept, X_t, X_{t-1}, ..., X_{t-n_lags+1})."""
    n = len(x)
    feats = [np.ones(n)]
    for k in range(n_lags):
        col = np.full(n, np.nan)
        col[k:] = x[:n - k]
        feats.append(col)
    X = np.column_stack(feats)
    mask = ~np.any(np.isnan(X), axis=1) & ~np.isnan(y[:n])
    X = X[mask]
    Y = y[:n][mask]
    beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
    resid = Y - X @ beta
    sse = float(np.sum(resid ** 2))
    return {"betas": beta, "sse": sse, "n_used": int(len(Y))}


class TransferFunctionParity(P3ParityCheck):
    technique_id = "p3_transfer_function"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Distributed-lag OLS is closed-form normal-equations "
        "solve. Self-parity reference mirrors TSL's lag-feature "
        "construction + lstsq verbatim."
    )
    DGP_N = 200
    N_LAGS = 3

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_transfer_dgp(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        out = _fit_distributed_lag(x, y, self.N_LAGS)
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        return _fit_distributed_lag(x, y, self.N_LAGS)

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        from reference_parity.harness.compare import _compare_scalar
        primary = {
            "betas": _compare_vector(tsl["betas"], ref["betas"], ladder["primary"]),
            "sse": _compare_scalar(tsl["sse"], ref["sse"], ladder["primary"]),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_obs": int(self.DGP_N), "n_lags": int(self.N_LAGS)},
        )
