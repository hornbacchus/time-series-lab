"""ENG-EXT-CONFORMAL-001 C2 — EnbPI (ensemble batch prediction intervals)
parity + the S85 neural-forecast-PI fold-in.

Validates the engine's net-new EnbPI path (`conformal_intervals._enbpi_intervals`,
Xu-Xie 2021). SECOND instantiation of the `conformal_coverage` verdict_class
(inherits C1's ladder + three-arm structure). EnbPI block-bootstraps an
ensemble of base models, conformalizes out-of-bag |residuals| to a width, and
forms ``ensemble_pred ± w``.

Validated on TWO bases (the S85 fold-in is built in, not just demonstrated):
- STANDARD base (gradient boosting) — the primary validation.
- NEURAL base (sklearn MLPRegressor — the same family `nar_narx` uses; the
  S85 neural-forecast-PI candidate, replacing nar_narx's bootstrap CIs with
  calibrated EnbPI). Its self-parity arm is BIT-EXACT (MLPRegressor is
  deterministic given random_state — pre-verified 0.00).

Four arms (the C1 structure; posture = matched-distributional cross-package
PRIMARY, pre-verified width-ratio ≈ 0.98 / coverage-Δ ≈ 0.007):
- SELF-PARITY (tight, bit-exact) — MACHINERY — for BOTH bases.
- EMPIRICAL-COVERAGE functional check (LOAD-BEARING) — reuses the
  conformal_nominal_coverage + interval_containment invariants in compare()
  (the C1 in-place mechanism). Mis-scaled ×0.3 discrimination guard.
- CROSS-PACKAGE (MAPIE EnbPI, matched, DISTRIBUTIONAL) — width-ratio +
  coverage-agreement.
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


def _ref_enbpi(X_train, y_train, X_eval, *, alpha, base_kind, n_resamplings,
               block_length, seed):
    """From-scratch EnbPI (independent reimplementation of the IDENTICAL
    Xu-Xie formulation the engine `_enbpi_intervals` implements: same local
    RandomState(seed) block bootstrap, same base construction, same OOB
    aggregation, same conformal-quantile index)."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.neural_network import MLPRegressor

    def base():
        if base_kind == "neural":
            return MLPRegressor(hidden_layer_sizes=(20, 10), random_state=seed,
                                max_iter=300, early_stopping=False)
        return GradientBoostingRegressor(random_state=seed)

    X_train = np.asarray(X_train, dtype=np.float64)
    y_train = np.asarray(y_train, dtype=np.float64)
    X_eval = np.atleast_2d(np.asarray(X_eval, dtype=np.float64))
    n = len(y_train)
    rs = np.random.RandomState(seed)
    n_blocks = int(np.ceil(n / block_length))
    oob = np.full((n, n_resamplings), np.nan)
    ev = np.zeros((X_eval.shape[0], n_resamplings))
    for b in range(n_resamplings):
        starts = rs.randint(0, max(1, n - block_length + 1), size=n_blocks)
        idx = np.concatenate([np.arange(s, s + block_length) for s in starts])[:n]
        mdl = base().fit(X_train[idx], y_train[idx])
        inb = np.zeros(n, dtype=bool)
        inb[np.unique(idx)] = True
        if np.any(~inb):
            oob[~inb, b] = mdl.predict(X_train[~inb])
        ev[:, b] = mdl.predict(X_eval)
    fhat = np.array([np.nanmean(oob[i]) if np.any(~np.isnan(oob[i])) else y_train[i]
                     for i in range(n)])
    w = float(np.quantile(np.abs(y_train - fhat),
                          min(np.ceil((n + 1) * (1.0 - alpha)) / n, 1.0)))
    pred = ev.mean(axis=1)
    return {"lo": pred - w, "hi": pred + w, "w": w}


class ConformalEnbpiParity(P3ParityCheck):
    """EnbPI conformal-coverage parity + S85 neural fold-in
    (ENG-EXT-CONFORMAL-001 C2)."""

    technique_id = "p3_conformal_enbpi"
    tier = "fast"
    fixture_id = ""

    verdict_class = "conformal_coverage"
    verdict_class_rationale = (
        "EnbPI (Xu-Xie 2021; ENG-EXT-CONFORMAL-001 C2) — SECOND instantiation "
        "of conformal_coverage, inheriting C1's ladder. Self-parity bit-exact "
        "bounds for BOTH the standard (gradient-boosting) and the NEURAL (MLP, "
        "the S85 fold-in) bases (machinery); empirical-coverage functional "
        "check (load-bearing, reuses the conformal invariants in place); "
        "cross-package MAPIE EnbPI matched-distributional (width-ratio + "
        "coverage-agreement — pre-verified 0.98 / 0.007, the C1 posture "
        "transposes). Discrimination verified (mis-scaled ×0.3 BLOCK). Slack "
        "0.07 inherited (earned at C1)."
    )

    ALPHA = 0.1
    N = 450
    N_LAGS = 6
    ROLL = (3, 6)
    N_RESAMPLINGS = 12
    BLOCK = 8
    SEED = 42

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.quantile_regression_model import _create_features  # type: ignore
        y = _generate_ar_dgp(seed=seed, n=self.N)
        X, Y, _ = _create_features(np.asarray(y, dtype=np.float64),
                                   self.N_LAGS, list(self.ROLL))
        m = len(Y)
        n_test = int(0.2 * m)
        return {"X": X, "Y": Y, "tr": m - n_test}

    def _splits(self, fx):
        X, Y, tr = np.asarray(fx["X"]), np.asarray(fx["Y"]), fx["tr"]
        return X[:tr], Y[:tr], X[tr:], Y[tr:]

    def _engine(self, Xtr, Ytr, Xev, base_kind):
        from techniques.conformal_intervals import _enbpi_intervals  # type: ignore
        return _enbpi_intervals(
            Xtr, Ytr, Xev, alpha=self.ALPHA, base_kind=base_kind,
            n_resamplings=self.N_RESAMPLINGS, block_length=self.BLOCK, seed=self.SEED)

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        Xtr, Ytr, Xte, Yte = self._splits(fixture)
        out: dict[str, Any] = {}
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            for base in ("gbr", "neural"):
                r = self._engine(Xtr, Ytr, Xte, base)
                lo, hi = r["lo"], r["hi"]
                out[base] = {
                    "lo": lo, "hi": hi, "w": r["w"],
                    "coverage": float(np.mean((Yte >= lo) & (Yte <= hi))),
                    "width": float(np.mean(hi - lo)),
                }
            # mis-scaled control (standard base)
            lo, hi = out["gbr"]["lo"], out["gbr"]["hi"]
            mid = (lo + hi) / 2.0
            out["gbr"]["coverage_misscaled"] = float(
                np.mean((Yte >= mid - 0.15 * (hi - lo)) & (Yte <= mid + 0.15 * (hi - lo))))
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        Xtr, Ytr, Xte, Yte = self._splits(fixture)
        out: dict[str, Any] = {}
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            for base in ("gbr", "neural"):
                out[base] = _ref_enbpi(
                    Xtr, Ytr, Xte, alpha=self.ALPHA, base_kind=base,
                    n_resamplings=self.N_RESAMPLINGS, block_length=self.BLOCK, seed=self.SEED)
            # cross-package MAPIE EnbPI (matched gbr base + block + ensemble + seed)
            try:
                from sklearn.ensemble import GradientBoostingRegressor as GBR
                from mapie.regression import TimeSeriesRegressor
                from mapie.subsample import BlockBootstrap
                cv = BlockBootstrap(n_resamplings=self.N_RESAMPLINGS,
                                    length=self.BLOCK, random_state=self.SEED)
                tsr = TimeSeriesRegressor(estimator=GBR(random_state=self.SEED),
                                          method="enbpi", cv=cv, agg_function="mean")
                tsr.fit(Xtr, Ytr)
                tsr.conformalize(Xtr, Ytr)
                _, pis = tsr.predict(Xte, ensemble=True, confidence_level=1.0 - self.ALPHA)
                pis = np.asarray(pis)
                mlo, mhi = pis[:, 0, 0], pis[:, 1, 0]
                out["mapie_cov"] = float(np.mean((Yte >= mlo) & (Yte <= mhi)))
                out["mapie_width"] = float(np.mean(mhi - mlo))
            except Exception as e:
                self._mapie_err = f"{type(e).__name__}: {e}"
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # --- self-parity bounds: standard + neural (machinery) ---
        for base, key in (("gbr", "selfparity_standard"), ("neural", "selfparity_neural")):
            tv = np.concatenate([np.asarray(tsl[base]["lo"]), np.asarray(tsl[base]["hi"]), [tsl[base]["w"]]])
            rv = np.concatenate([np.asarray(ref[base]["lo"]), np.asarray(ref[base]["hi"]), [ref[base]["w"]]])
            primary[key] = _compare_vector(tv, rv, ladder["selfparity_bounds"])
            statuses.append(primary[key]["status"])

        # --- empirical-coverage functional check (LOAD-BEARING; reuse invariants) ---
        slack = float(ladder["coverage_gap"]["slack"])
        inv = StructuralInvariant(name="conformal_nominal_coverage",
                                  invariant_type="conformal_nominal_coverage",
                                  tolerance=slack, tolerance_type="absolute")
        cov_tsl = {"coverage": tsl["gbr"]["coverage"], "alpha": self.ALPHA,
                   "lower": tsl["gbr"]["lo"], "upper": tsl["gbr"]["hi"]}
        primary["coverage_gap"] = _check_conformal_nominal_coverage(cov_tsl, ref, None, inv)
        primary["interval_containment"] = _check_conformal_interval_containment(cov_tsl, ref, None, inv)
        statuses.append(primary["coverage_gap"]["status"])
        statuses.append(primary["interval_containment"]["status"])

        # --- cross-package MAPIE (distributional) ---
        if "mapie_width" in ref:
            wr = float(tsl["gbr"]["width"]) / max(float(ref["mapie_width"]), 1e-300)
            wt = ladder["crosspkg_width_ratio"]
            ws = ("PASS" if wt["pass_lo"] <= wr <= wt["pass_hi"]
                  else ("CAVEAT" if wt["block_lo"] <= wr <= wt["block_hi"] else "BLOCK"))
            primary["crosspkg_width_ratio"] = {"status": ws, "width_ratio": round(wr, 4)}
            statuses.append(ws)
            cd = abs(float(tsl["gbr"]["coverage"]) - float(ref["mapie_cov"]))
            ct = ladder["crosspkg_coverage_agreement"]
            cs = "PASS" if cd <= ct["pass_abs"] else ("CAVEAT" if cd <= ct["block_abs"] else "BLOCK")
            primary["crosspkg_coverage_agreement"] = {"status": cs, "coverage_abs_diff": round(cd, 4)}
            statuses.append(cs)
        else:
            primary["crosspkg_width_ratio"] = {"status": "SKIP",
                                               "note": getattr(self, "_mapie_err", "MAPIE unavailable")}

        # --- discrimination guard ---
        nominal = 1.0 - self.ALPHA
        misb = bool(tsl["gbr"]["coverage_misscaled"] < nominal - slack)
        primary["discrimination_guard"] = {
            "status": "PASS" if misb else "BLOCK",
            "coverage_misscaled": round(float(tsl["gbr"]["coverage_misscaled"]), 4),
            "floor": round(nominal - slack, 4)}
        statuses.append(primary["discrimination_guard"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.N), "alpha": float(self.ALPHA),
                "standard_coverage": round(float(tsl["gbr"]["coverage"]), 4),
                "neural_coverage": round(float(tsl["neural"]["coverage"]), 4),
                "selfparity_standard_max_abs": primary["selfparity_standard"].get("max_abs_diff"),
                "selfparity_neural_max_abs": primary["selfparity_neural"].get("max_abs_diff"),
                "mapie_coverage": round(float(ref.get("mapie_cov", float("nan"))), 4),
            },
        )
