"""Phase 3 Batch 10 — Rolling-origin CV parity check.

TSL ``engine/techniques/rolling_origin_cv.py`` (expanding-window
CV with ``pmdarima.auto_arima`` base forecaster) vs from-scratch
paper-formula reimplementation per Tashman 2000 specification.
Reference arm mirrors the engine's CV loop (evenly-spaced fold
origins + auto_arima fit at each fold + per-fold MAE) so the
parity comparison isolates engine wrapper orchestration vs the
paper-formula reference.

Rewritten at S59-S61 audit-hygiene session per Code finding that
the original harness implemented naive last-value forecasting in
a degenerate self-parity loop (both arms calling the same local
helper) which never exercised the engine's auto_arima math.
Category (3) DEGENERATE-VACUOUS → Category (1) LEGITIMATE rewrite
per ratified plan.

Pattern A.3 paper-formula self-parity (Tier IV); auto_arima is
deterministic at fixed ctx.seed so bit-exact target on per-fold
MAE is achievable.
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(*, seed: int, n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50)
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = 0.6 * y[t - 1] + eps[t]
    return y[50:]


def _reference_rolling_origin_cv(
    y: np.ndarray, *, n_folds: int, horizon: int, seasonal: bool = False,
    m: int = 1,
) -> dict[str, Any]:
    """Reference expanding-window CV per Tashman 2000.

    Mirrors engine `rolling_origin_cv.run()` orchestration logic
    (lines 141-216) but invoked directly without wrapper plumbing:
    - Evenly-spaced fold origins from min_train = max(20, n//3) +
      step = (n - min_train - horizon) / (n_folds - 1)
    - auto_arima fit at each fold; MAE per fold
    - Returns per-fold MAE vector for parity comparison
    """
    import pmdarima as pm  # type: ignore
    n = len(y)
    min_train = max(20, n // 3)
    available = n - min_train - horizon
    if available < 1:
        raise ValueError(f"series too short ({n}) for {n_folds} folds")
    if n_folds > available:
        n_folds = available
    if n_folds == 1:
        origins = [min_train]
    else:
        step = available / (n_folds - 1)
        origins = [min_train + int(round(i * step)) for i in range(n_folds)]

    all_mae: list[float] = []
    for origin in origins:
        train = y[:origin]
        actual_end = min(origin + horizon, n)
        actual = y[origin:actual_end]
        h = len(actual)
        if h == 0:
            continue
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            model = pm.auto_arima(
                train, seasonal=seasonal, m=m if seasonal else 1,
                stepwise=True, suppress_warnings=True,
                error_action="ignore", trace=False,
                max_p=3, max_q=3, max_d=2,
            )
        fc = model.predict(n_periods=h)
        fc = np.asarray(fc)
        all_mae.append(float(np.mean(np.abs(actual - fc))))
    return {"per_fold_mae": np.asarray(all_mae, dtype=np.float64)}


class RollingOriginCvParity(P3ParityCheck):
    """Rolling-origin CV parity vs from-scratch reference.

    Engine arm invokes `engine.techniques.rolling_origin_cv.run()`
    via RunContext + extracts per-fold MAE from the "Fold Results"
    output table. Reference arm reimplements the same expanding-
    window CV loop with auto_arima base forecaster.
    """

    technique_id = "p3_rolling_origin_cv"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Rolling-origin CV with auto_arima base forecaster. "
        "auto_arima is deterministic at fixed ctx.seed; engine "
        "and reference reimpl follow identical fold-origin "
        "construction + identical base-forecaster fit + identical "
        "MAE computation, so per-fold MAE matches at machine "
        "precision."
    )
    DGP_N = 200
    HORIZON = 5
    N_FOLDS = 3

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext; extract per-fold
        MAE from the "Fold Results" output table column index 4."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.rolling_origin_cv as rocv_mod  # type: ignore

        # Reset numpy global RNG for symmetry with run_reference;
        # engine itself re-seeds at run() entry, so this is
        # defense-in-depth against runner-ordering effects.
        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_rocv_parity",
            "technique_id": "rolling_origin_cv",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "horizon": self.HORIZON,
                "folds": self.N_FOLDS,
                "seasonal": False,
                "confidence_level": 0.95,
            },
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = rocv_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL rolling_origin_cv failed: {resp.get('error_message')}"
            )
        fold_table = next(
            (t for t in resp["tables"] if t.get("name") == "Fold Results"),
            None,
        )
        if fold_table is None:
            raise RuntimeError("engine output missing 'Fold Results' table")
        # Column index 4 = MAE per engine line 232 column header
        per_fold_mae = np.array(
            [float(row[4]) for row in fold_table["rows"]],
            dtype=np.float64,
        )
        return {"per_fold_mae": per_fold_mae}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Reset numpy global RNG to the same seed the engine uses at
        # `engine/techniques/rolling_origin_cv.py:112` so per-fold
        # auto_arima stepwise-search consumes identical RNG state.
        np.random.seed(42)
        return _reference_rolling_origin_cv(
            y, n_folds=self.N_FOLDS, horizon=self.HORIZON,
            seasonal=False, m=1,
        )

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "per_fold_mae": _compare_vector(
                tsl["per_fold_mae"], ref["per_fold_mae"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "horizon": int(self.HORIZON),
                "n_folds": int(self.N_FOLDS),
                "n_folds_completed": int(len(tsl["per_fold_mae"])),
            },
        )
