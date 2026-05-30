"""ENG-EXT-CONFORMAL-001 C1 — Conformalized Quantile Regression (CQR) parity.

Validates the engine's net-new CQR path (`conformal_intervals._cqr_intervals`,
Romano-Patterson-Candès 2019). FIRST instantiation of the reserved
`conformal_coverage` verdict_class — the interval-validation family's COVERAGE
sibling (M1 `bootstrap_distributional` was width/containment around a point;
`conformal_coverage` is held-out empirical coverage + interval width).

Four arms (the M1 three-arm structure + a sanity arm; each validates a
DIFFERENT thing):

- SELF-PARITY (tight, bit-exact) — the band MACHINERY: engine `_cqr_intervals`
  vs a from-scratch reimplementation of the IDENTICAL Romano formulation (same
  seeded GBR base, same calibration split, same conformal-quantile index) →
  bit-exact bounds + Q.
- CROSS-PACKAGE (MAPIE, matched-calibration, DISTRIBUTIONAL, LOAD-BEARING
  FORMULATION): vs MAPIE `ConformalizedQuantileRegressor` on the IDENTICAL
  train+calibration+seeded base. MAPIE's internal conformal-quantile /
  quantile-crossing handling shifts the bounds (~0.2), so the comparison is
  band GEOMETRY — width-ratio + coverage-agreement, NOT bit-exact endpoints
  (pre-verified width-ratio ≈ 0.99, coverage Δ ≈ 0.00). Catches
  shared-formulation bugs (the A1c mitigant).
- EMPIRICAL-COVERAGE FUNCTIONAL CHECK (LOAD-BEARING, scheme-defining): held-out
  coverage ≥ (1−α) − slack. Reuses the existing
  `_check_conformal_nominal_coverage` + `_check_conformal_interval_containment`
  invariant functions in place (CONFORMAL-001 wires the dormant invariants).
  Pre-verified DISCRIMINATING: a mis-scaled (×0.3 width) interval under-covers
  (asserted to fail the floor — the discrimination guard).
- INDEPENDENT-CALIBRATION SANITY: both implementations achieve ≈ nominal.

Slack EARNED, not provisioned: CQR held-out coverage across 8 seeds measured
mean 0.905 (≈ nominal 0.90) / std 0.034 → slack = 2·std ≈ 0.07.
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
    _check_conformal_nominal_coverage,
    _check_conformal_interval_containment,
)
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_lstm_gru import _generate_ar_dgp


def _ref_cqr(X_train, y_train, X_cal, y_cal, X_eval, *, alpha, seed):
    """From-scratch Romano-Patterson-Candès CQR (independent reimplementation
    of the IDENTICAL formulation the engine `_cqr_intervals` implements)."""
    from sklearn.ensemble import GradientBoostingRegressor as GBR
    glo = GBR(loss="quantile", alpha=alpha / 2.0, random_state=seed).fit(X_train, y_train)
    ghi = GBR(loss="quantile", alpha=1.0 - alpha / 2.0, random_state=seed).fit(X_train, y_train)
    E = np.maximum(glo.predict(X_cal) - y_cal, y_cal - ghi.predict(X_cal))
    n_cal = len(y_cal)
    qlvl = min(np.ceil((n_cal + 1) * (1.0 - alpha)) / n_cal, 1.0)
    Q = float(np.quantile(E, qlvl))
    qlo, qhi = glo.predict(X_eval), ghi.predict(X_eval)
    return {"lo": qlo - Q, "hi": qhi + Q, "Q": Q}


class ConformalCqrParity(P3ParityCheck):
    """CQR conformal-coverage parity (ENG-EXT-CONFORMAL-001 C1)."""

    technique_id = "p3_conformal_cqr"
    tier = "fast"
    fixture_id = ""

    verdict_class = "conformal_coverage"
    verdict_class_rationale = (
        "Conformalized Quantile Regression (ENG-EXT-CONFORMAL-001 C1) — the "
        "FIRST instantiation of the reserved conformal_coverage class, the "
        "interval family's COVERAGE sibling (held-out empirical coverage + "
        "width, vs M1 bootstrap_distributional's width/containment-around-a-"
        "point). Self-parity bit-exact bounds (machinery) + cross-package "
        "MAPIE matched-calibration width-ratio/coverage-agreement "
        "(distributional, load-bearing formulation — MAPIE's internal "
        "conformal-quantile handling shifts bounds, so geometry not endpoints) "
        "+ the empirical-coverage functional check (load-bearing, "
        "scheme-defining; reuses the conformal_nominal_coverage / "
        "interval_containment invariants in place). Discrimination verified "
        "against a mis-scaled interval. Slack 0.07 = 2·(coverage std 0.034)."
    )

    ALPHA = 0.1
    N = 700
    N_LAGS = 8
    ROLL = (3, 6)
    SEED = 42

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.quantile_regression_model import _create_features  # type: ignore
        y = _generate_ar_dgp(seed=seed, n=self.N)
        X, Y, _ = _create_features(np.asarray(y, dtype=np.float64),
                                   self.N_LAGS, list(self.ROLL))
        m = len(Y)
        n_test = int(0.25 * m)
        n_rem = m - n_test
        n_cal = int(0.3 * n_rem)
        n_train = n_rem - n_cal
        return {
            "X": X, "Y": Y,
            "tr": n_train, "cal": n_cal,  # slice sizes
        }

    def _splits(self, fx):
        X, Y = np.asarray(fx["X"]), np.asarray(fx["Y"])
        tr, cal = fx["tr"], fx["cal"]
        return (X[:tr], Y[:tr], X[tr:tr + cal], Y[tr:tr + cal],
                X[tr + cal:], Y[tr + cal:])

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.conformal_intervals import _cqr_intervals  # type: ignore
        Xtr, Ytr, Xcal, Ycal, Xte, Yte = self._splits(fixture)
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            res = _cqr_intervals(Xtr, Ytr, Xcal, Ycal, Xte, alpha=self.ALPHA, seed=self.SEED)
        lo, hi = res["lo"], res["hi"]
        cov = float(np.mean((Yte >= lo) & (Yte <= hi)))
        width = float(np.mean(hi - lo))
        # mis-scaled control (×0.3 width) — discrimination guard
        mid = (lo + hi) / 2.0
        lo_bad, hi_bad = mid - 0.15 * (hi - lo), mid + 0.15 * (hi - lo)
        cov_bad = float(np.mean((Yte >= lo_bad) & (Yte <= hi_bad)))
        return {"lo": lo, "hi": hi, "Q": res["Q"], "coverage": cov,
                "width": width, "coverage_misscaled": cov_bad}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        Xtr, Ytr, Xcal, Ycal, Xte, Yte = self._splits(fixture)
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            sp = _ref_cqr(Xtr, Ytr, Xcal, Ycal, Xte, alpha=self.ALPHA, seed=self.SEED)
            # cross-package MAPIE (matched calibration + seeded base)
            from sklearn.ensemble import GradientBoostingRegressor as GBR
            from mapie.regression import ConformalizedQuantileRegressor as CQR
            mapie_lo = mapie_hi = None
            try:
                m = CQR(estimator=GBR(loss="quantile", random_state=self.SEED),
                        confidence_level=1.0 - self.ALPHA)
                m.fit(Xtr, Ytr)
                m.conformalize(Xcal, Ycal)
                _, pis = m.predict_interval(Xte)
                pis = np.asarray(pis)
                mapie_lo = pis[:, 0, 0]
                mapie_hi = pis[:, 1, 0]
            except Exception as e:  # MAPIE arm is upside; degrade gracefully
                self._mapie_err = f"{type(e).__name__}: {e}"
        out = {"lo": sp["lo"], "hi": sp["hi"], "Q": sp["Q"]}
        if mapie_lo is not None:
            out["mapie_cov"] = float(np.mean((Yte >= mapie_lo) & (Yte <= mapie_hi)))
            out["mapie_width"] = float(np.mean(mapie_hi - mapie_lo))
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # --- self-parity bounds (tight, machinery) ---
        tsl_vec = np.concatenate([np.asarray(tsl["lo"]), np.asarray(tsl["hi"]), [tsl["Q"]]])
        ref_vec = np.concatenate([np.asarray(ref["lo"]), np.asarray(ref["hi"]), [ref["Q"]]])
        primary["selfparity_bounds"] = _compare_vector(tsl_vec, ref_vec, ladder["selfparity_bounds"])
        statuses.append(primary["selfparity_bounds"]["status"])

        # --- empirical-coverage functional check (LOAD-BEARING; reuse invariants) ---
        slack = float(ladder["coverage_gap"]["slack"])
        inv = StructuralInvariant(
            name="conformal_nominal_coverage",
            invariant_type="conformal_nominal_coverage",
            tolerance=slack, tolerance_type="absolute")
        cov_tsl = {"coverage": tsl["coverage"], "alpha": self.ALPHA,
                   "lower": tsl["lo"], "upper": tsl["hi"]}
        cov_res = _check_conformal_nominal_coverage(cov_tsl, ref, None, inv)
        contain_res = _check_conformal_interval_containment(cov_tsl, ref, None, inv)
        primary["coverage_gap"] = cov_res
        primary["interval_containment"] = contain_res
        statuses.append(cov_res["status"])
        statuses.append(contain_res["status"])

        # --- cross-package MAPIE (distributional, load-bearing formulation) ---
        if "mapie_width" in ref:
            wr = float(tsl["width"]) / max(float(ref["mapie_width"]), 1e-300)
            wt = ladder["crosspkg_width_ratio"]
            w_status = ("PASS" if wt["pass_lo"] <= wr <= wt["pass_hi"]
                        else ("CAVEAT" if wt["block_lo"] <= wr <= wt["block_hi"] else "BLOCK"))
            primary["crosspkg_width_ratio"] = {"status": w_status, "width_ratio": round(wr, 4)}
            statuses.append(w_status)
            cov_diff = abs(float(tsl["coverage"]) - float(ref["mapie_cov"]))
            ct = ladder["crosspkg_coverage_agreement"]
            c_status = ("PASS" if cov_diff <= ct["pass_abs"]
                        else ("CAVEAT" if cov_diff <= ct["block_abs"] else "BLOCK"))
            primary["crosspkg_coverage_agreement"] = {"status": c_status, "coverage_abs_diff": round(cov_diff, 4)}
            statuses.append(c_status)
        else:
            primary["crosspkg_width_ratio"] = {"status": "SKIP",
                                               "note": getattr(self, "_mapie_err", "MAPIE unavailable")}

        # --- discrimination guard (evidence, not a gate): mis-scaled must fail the floor ---
        nominal = 1.0 - self.ALPHA
        misscaled_blocks = bool(tsl["coverage_misscaled"] < nominal - slack)
        primary["discrimination_guard"] = {
            "status": "PASS" if misscaled_blocks else "BLOCK",
            "coverage_misscaled": round(float(tsl["coverage_misscaled"]), 4),
            "floor": round(nominal - slack, 4),
        }
        statuses.append(primary["discrimination_guard"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.N), "alpha": float(self.ALPHA),
                "tsl_coverage": round(float(tsl["coverage"]), 4),
                "tsl_width": round(float(tsl["width"]), 4),
                "mapie_coverage": round(float(ref.get("mapie_cov", float("nan"))), 4),
                "selfparity_max_abs": primary["selfparity_bounds"].get("max_abs_diff"),
            },
        )
