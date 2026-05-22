"""Phase 3 Batch 9 — Conformal intervals parity check.

TSL ``engine/techniques/conformal_intervals.py`` (split conformal
prediction wrapping pmdarima.auto_arima base forecaster per Vovk-
Gammerman-Shafer 2005 + Papadopoulos et al. 2002) vs from-scratch
paper-formula reimplementation that mirrors the engine's exact
pipeline (auto_arima base + one-step-ahead calibration residuals
via rolling refit + conformal quantile + interval construction).
Reference arm uses identical auto_arima parameters so any
divergence isolates the engine wrapper's orchestration vs the
paper-formula reference.

Rewritten at S62-side audit-hygiene session per surface that the
original harness implemented naive last-value forecast as base
predictor in a degenerate self-parity loop (both arms calling the
same local helper); engine uses pmdarima.auto_arima. Category 3
DEGENERATE-VACUOUS → Category 1 LEGITIMATE rewrite per established
p3_rolling_origin_cv precedent at hygiene commits e72d6f5 + 2f46381.

Pattern A.3 paper-formula self-parity (Tier IV) at deterministic
seed; bit-exact target on interval bounds + conformal quantile
modulo engine 6-decimal output-rounding floor at engine lines 267-
271 (compare() rounds REF interval bounds to match).
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_lstm_gru import _generate_ar_dgp


def _reference_split_conformal(
    y: np.ndarray, *, horizon: int, cal_frac: float, conf_level: float,
    max_p: int, max_q: int, stepwise: bool,
) -> dict[str, Any]:
    """Reference split conformal per VGS 2005 + Papadopoulos 2002,
    mirroring engine `conformal_intervals.run()` pipeline at engine
    lines 170-260: auto_arima fit on training split + one-step-ahead
    calibration residuals via rolling refit (model.update()) + conformal
    quantile + point forecast +/- quantile. Identical hyperparameters
    to engine arm so per-step interval bounds match at machine precision.
    """
    import pmdarima as pm  # type: ignore
    n = len(y)
    alpha = 1.0 - conf_level
    n_cal = max(10, int(n * cal_frac))
    n_train = n - n_cal
    if n_train < 15:
        n_train = 15
        n_cal = n - n_train
    train = y[:n_train]
    cal = y[n_train:]

    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        model = pm.auto_arima(
            train, seasonal=False, m=1,
            stepwise=stepwise,
            max_p=max_p, max_q=max_q,
            suppress_warnings=True, error_action="ignore", trace=False,
        )
    # One-step-ahead calibration residuals via rolling refit
    cal_residuals = []
    for i in range(n_cal):
        fc_one = model.predict(n_periods=1)
        resid = abs(cal[i] - fc_one[0])
        cal_residuals.append(resid)
        model.update(np.array([cal[i]]))
    cal_residuals = np.array(cal_residuals)

    # Conformal quantile per engine lines 247-251
    q_level = np.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal
    q_level = min(q_level, 1.0)
    conformal_q = float(np.quantile(cal_residuals, q_level))

    # Point forecast + conformal intervals
    fc = model.predict(n_periods=horizon)
    fc = np.asarray(fc, dtype=np.float64)
    conf_lower = fc - conformal_q
    conf_upper = fc + conformal_q
    return {
        "point_forecast": fc,
        "conf_lower": conf_lower,
        "conf_upper": conf_upper,
        "conformal_q": conformal_q,
        "n_cal": int(n_cal),
        "n_train": int(n_train),
    }


class ConformalParity(P3ParityCheck):
    """Conformal intervals parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.conformal_intervals.run()
    via RunContext + extracts point forecast + conformal lower +
    conformal upper from "Forecast with Conformal Intervals" table.
    Reference arm reimplements the same pipeline (auto_arima base +
    one-step-ahead calibration residuals + conformal quantile).
    """

    technique_id = "p3_conformal"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Split conformal prediction with auto_arima base forecaster. "
        "auto_arima is deterministic at fixed seed; engine and "
        "reference reimpl follow identical pipeline (auto_arima fit + "
        "rolling-refit one-step-ahead calibration residuals + "
        "conformal quantile + interval construction); per-step "
        "interval bounds match at machine precision modulo engine "
        "6-decimal output-rounding floor."
    )

    DGP_N = 400
    HORIZON = 5
    CAL_FRAC = 0.25  # Balanced preset
    CONF_LEVEL = 0.95
    # Match engine Balanced preset auto_arima params (engine line 144)
    MAX_P = 5
    MAX_Q = 5
    STEPWISE = True

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext; extract conformal
        interval bounds from "Forecast with Conformal Intervals"
        table columns 1/2/3 (Point Forecast / Conformal Lower /
        Conformal Upper)."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.conformal_intervals as conf_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_conformal_parity",
            "technique_id": "conformal_intervals",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "horizon": self.HORIZON,
                "confidence_level": self.CONF_LEVEL,
                "cal_fraction": self.CAL_FRAC,
                "seasonal": False,
            },
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = conf_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL conformal_intervals failed: {resp.get('error_message')}"
            )
        fc_table = next(
            (t for t in resp["tables"]
             if t.get("name") == "Forecast with Conformal Intervals"),
            None,
        )
        if fc_table is None:
            raise RuntimeError(
                "engine output missing 'Forecast with Conformal Intervals' table"
            )
        # Cols: [0]=Step, [1]=Point Forecast, [2]=Conformal Lower,
        # [3]=Conformal Upper, [4]=Parametric Lower, [5]=Parametric Upper
        rows = fc_table["rows"]
        point_forecast = np.array(
            [float(row[1]) for row in rows], dtype=np.float64,
        )
        conf_lower = np.array(
            [float(row[2]) for row in rows], dtype=np.float64,
        )
        conf_upper = np.array(
            [float(row[3]) for row in rows], dtype=np.float64,
        )
        # Extract conformal_q from Diagnostics table
        diag_table = next(
            (t for t in resp["tables"] if t.get("name") == "Diagnostics"),
            None,
        )
        conformal_q = None
        if diag_table is not None:
            for row in diag_table["rows"]:
                if row and "Conformal Quantile" in str(row[0]):
                    conformal_q = float(row[1])
                    break
        return {
            "point_forecast": point_forecast,
            "conf_lower": conf_lower,
            "conf_upper": conf_upper,
            "conformal_q": conformal_q if conformal_q is not None else float("nan"),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        # Reset numpy global RNG to match engine seed at line 115
        np.random.seed(42)
        return _reference_split_conformal(
            y, horizon=self.HORIZON, cal_frac=self.CAL_FRAC,
            conf_level=self.CONF_LEVEL, max_p=self.MAX_P,
            max_q=self.MAX_Q, stepwise=self.STEPWISE,
        )

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounds interval bounds + conformal_q to 6 decimals
        # at engine lines 267-271 + 286 (`round(..., 6)`). Round REF
        # to match display precision per Phase 1 finding B8 precedent
        # (p3_har_rv + p3_rolling_origin_cv hygiene precedent).
        ref_point_rounded = np.round(ref["point_forecast"], 6)
        ref_lower_rounded = np.round(ref["conf_lower"], 6)
        ref_upper_rounded = np.round(ref["conf_upper"], 6)
        ref_q_rounded = round(ref["conformal_q"], 6)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        primary["point_forecast"] = _compare_vector(
            tsl["point_forecast"], ref_point_rounded, ladder["primary"],
        )
        statuses.append(primary["point_forecast"]["status"])
        primary["conf_lower"] = _compare_vector(
            tsl["conf_lower"], ref_lower_rounded, ladder["primary"],
        )
        statuses.append(primary["conf_lower"]["status"])
        primary["conf_upper"] = _compare_vector(
            tsl["conf_upper"], ref_upper_rounded, ladder["primary"],
        )
        statuses.append(primary["conf_upper"]["status"])
        primary["conformal_q"] = _compare_scalar(
            tsl["conformal_q"], ref_q_rounded, ladder["primary"],
        )
        statuses.append(primary["conformal_q"]["status"])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "horizon": int(self.HORIZON),
                "cal_frac": float(self.CAL_FRAC),
                "conf_level": float(self.CONF_LEVEL),
            },
        )
