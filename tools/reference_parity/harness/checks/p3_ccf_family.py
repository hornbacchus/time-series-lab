"""Phase 7+ deeper-validation, scope-extension UNIT 3 — the ccf-family
(cross_correlation_lag / prewhitened_ccf_lag / rolling_ccf_lag) parity
check (additive; ``p3_ccf`` unchanged).

★ COVERAGE CORRECTION, not just an extension. ``p3_ccf`` validates
``statsmodels.ccf`` vs R ``stats::ccf`` — but the engine does NOT use
statsmodels for CCF; all three members compute a CUSTOM inline numpy CCF
(three independent implementations), which is currently UNVALIDATED vs any
reference. So ``p3_ccf`` is ORTHOGONAL to the emitted engine surface; this
check is the engine CCF's FIRST real parity evidence.

ONE consolidated check, three member arms + two defining-invariant arms,
worst-of rollup. Engine wrappers invoked via ``RunContext`` (the p3_dtw
pattern). The CCF reference is the shared ``_leadlag_components.ccf_reference``
(R stats::ccf). Empirically-pinned alignment: the engine's custom CCF lag
axis is the SIGN-FLIP of R's, i.e. ``engine_ccf[k] == R_ccf[-k]`` and
``engine optimal_lag == -R argmax``.

Arms:
  - cross_correlation_lag (B.i): engine CCF vector + optimal_lag vs R
    stats::ccf, bit-exact at the emitted 6-dp precision. Bartlett band
    DISCLOSED (no arm: naive z/sqrt(n) trivial, AC-corrected engine-specific).
  - prewhitened_ccf_lag (B.i + WHITENESS invariant): the defining property —
    the prewhitened input is white. Ljung-Box (min-p over lags 1..10) on the
    engine's X-side prewhitening (pmdarima.auto_arima(x).resid(), the engine's
    Path-B resid_x) must PASS (min-p>0.05); the raw un-prewhitened input is
    the negative control (must be not-white). Prewhitening filter =
    trusted-library primitive, disclosed. CCF-on-residuals = same formula,
    transitively covered by the cross_correlation arm.
  - rolling_ccf_lag (B.i + REDUCTION invariant): the rolling windowing CCF is
    an INDEPENDENT impl; its first-window CCF must equal the static engine CCF
    on the same slice (non-tautological cross-implementation check, transitively
    cross-packaging rolling vs R). Negative control = static on a WRONG slice.

Two engine gaps were BANKED during design (NOT fixed here, per S5.7): the
Y-side _apply_arima_filter weak fallback, and the residual_ljung_box_p None
placeholder. See the trust-inventory amendment.
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._leadlag_components import ccf_reference
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_DGP_N = 200
_DGP_LAG = 3  # Y/X lead-lag built into the fixture; engine optimal_lag must == 3
_LB_LAGS = 10  # joint Ljung-Box portmanteau lag (standard whiteness test)
_LB_ALPHA = 0.05
_WHITE_N = 300   # dedicated AR(2) series for the whiteness invariant
_WHITE_SEED = 7  # pinned; prewhitened resid joint-LB@10 ~0.84 (clear margin)


def _dgp(seed: int, n: int = _DGP_N, lag: int = _DGP_LAG):
    rng = np.random.default_rng(seed)
    base = np.cumsum(rng.standard_normal(n + lag + 50))
    x = base[lag:lag + n] + 0.1 * rng.standard_normal(n)
    y = base[:n] + 0.1 * rng.standard_normal(n)
    return np.asarray(x, float), np.asarray(y, float)


def _ar2(seed: int, n: int = _WHITE_N, a1: float = 0.6, a2: float = 0.25,
         burn: int = 200):
    """Autocorrelated AR(2) series for the whiteness invariant: prewhitening
    must whiten it; the raw series is the (autocorrelated) negative control."""
    rng = np.random.default_rng(seed)
    e = rng.standard_normal(n + burn)
    y = np.zeros(n + burn)
    for t in range(2, n + burn):
        y[t] = a1 * y[t - 1] + a2 * y[t - 2] + e[t]
    return np.asarray(y[burn:], float)


def _run_engine(tech: str, x, y, params: dict):
    from techniques.base import RunContext  # type: ignore
    import importlib
    mod = importlib.import_module(f"techniques.{tech}")
    ctx = RunContext({
        "run_id": f"p3_ccf_family_{tech}", "technique_id": tech,
        "preset": "Balanced", "seed": 42, "frequency": "",
        "time": list(range(len(x))),
        "series": [{"name": "x", "values": list(map(float, x))},
                   {"name": "y", "values": list(map(float, y))}],
        "params": params,
    })
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        resp = mod.run(ctx, lambda *a, **k: None)
    if resp.get("status") != "success":
        raise RuntimeError(f"{tech} failed: {resp.get('error_message')}")
    return resp


def _ccf_vec(resp) -> dict[int, float]:
    """{lag: ccf} from the engine 'Cross-Correlation Function' table (6-dp)."""
    t = next(t for t in resp["tables"] if t["name"] == "Cross-Correlation Function")
    return {int(r[0]): float(r[1]) for r in t["rows"]}


def _heatmap_win0(resp) -> dict[int, float]:
    """{lag: ccf} for the first rolling window from 'CCF Heatmap Data' (4-dp)."""
    t = next(t for t in resp["tables"] if t["name"] == "CCF Heatmap Data")
    lag_cols = [int(c) for c in t["columns"][1:]]
    row0 = t["rows"][0]
    return {lag_cols[i]: float(row0[1 + i]) for i in range(len(lag_cols))}


def _ljung_p(series) -> float:
    """Standard joint Ljung-Box portmanteau p-value up to lag _LB_LAGS
    (a single joint test — NOT min-over-lags, which inflates rejection)."""
    from statsmodels.stats.diagnostic import acorr_ljungbox  # type: ignore
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        df = acorr_ljungbox(np.asarray(series, float), lags=[_LB_LAGS],
                            return_df=True)
    return float(df["lb_pvalue"].iloc[0])


def _prewhiten_resid(x):
    """Engine Path-B X-side prewhitening: pmdarima.auto_arima(x).resid()."""
    import pmdarima as pm  # type: ignore
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        m = pm.auto_arima(np.asarray(x, float), max_p=5, max_q=5, max_d=2,
                          stepwise=True, suppress_warnings=True,
                          error_action="ignore")
    return np.asarray(m.resid(), float)


class CcfFamilyParity(P3ParityCheck):
    """Lead-lag CCF family scope-extension (cross_correlation / prewhitened /
    rolling), engine CCF vs R stats::ccf + whiteness & reduction invariants."""

    technique_id = "p3_ccf_family"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Engine custom-numpy CCF is closed-form Pearson cross-correlation; "
        "validated vs R stats::ccf at the emitted 6-dp precision (sign-flip "
        "lag alignment). The two invariant arms are defining mathematical "
        "properties (prewhitening => whiteness; rolling => reduction-to-static), "
        "verified-discriminating functional checks (T3-flavored, NOT bit-exact). "
        "B.i pure parameter/topology coverage over the SAME CCF primitive — no "
        "orchestration verdict. This is the engine CCF's first real parity "
        "evidence (p3_ccf validates statsmodels, which the engine does not use)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _dgp(seed)
        return {"x": x, "y": y, "lag": _DGP_LAG, "white": _ar2(_WHITE_SEED)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        x, y = fixture["x"], fixture["y"]
        n = len(x)

        # --- arm 1: cross_correlation_lag engine CCF + optimal_lag ---
        r_cc = _run_engine("cross_correlation_lag", x, y, {})
        cc_vec = _ccf_vec(r_cc)
        cc_lag = int(r_cc["audit_fields"]["optimal_lag"])
        ml = int(r_cc["audit_fields"]["max_lag"])

        # --- arm 2: whiteness invariant (engine X-side prewhitening on a
        # dedicated AR(2) series; joint Ljung-Box portmanteau) ---
        white_x = fixture["white"]
        resid = _prewhiten_resid(white_x)
        pw_minp = _ljung_p(resid)
        raw_minp = _ljung_p(white_x)  # negative control: un-prewhitened input

        # --- arm 3: rolling reduction invariant ---
        w = n - 10  # largest window the engine allows (needs n >= window + 10)
        r_roll = _run_engine("rolling_ccf_lag", x, y, {"window": w, "step": 1})
        roll_ml = int(r_roll["audit_fields"]["max_lag"])
        roll_meanlag = float(r_roll["audit_fields"]["mean_lag_ex_boundary"])
        roll_vec = _heatmap_win0(r_roll)
        r_stat = _run_engine("cross_correlation_lag", x[:w], y[:w],
                             {"max_lag": roll_ml})
        stat_vec = _ccf_vec(r_stat)
        stat_lag = int(r_stat["audit_fields"]["optimal_lag"])
        r_wrong = _run_engine("cross_correlation_lag", x[10:10 + w], y[10:10 + w],
                             {"max_lag": roll_ml})
        wrong_vec = _ccf_vec(r_wrong)

        return {
            "cc_vec": cc_vec, "cc_lag": cc_lag, "ml": ml,
            "pw_minp": pw_minp, "raw_minp": raw_minp,
            "roll_vec": roll_vec, "stat_vec": stat_vec, "wrong_vec": wrong_vec,
            "roll_meanlag": roll_meanlag, "stat_lag": stat_lag,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        x, y = fixture["x"], fixture["y"]
        r_cc = _run_engine("cross_correlation_lag", x, y, {})
        ml = int(r_cc["audit_fields"]["max_lag"])
        ref = ccf_reference(x, y, max_lag=ml)
        return {"R_ccf": {int(l): float(v) for l, v in zip(ref["lags"], ref["ccf"])},
                "R_argmax": int(ref["argmax_lag"]), "dgp_lag": int(fixture["lag"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        R = ref["R_ccf"]

        # --- arm 1a: engine CCF vector vs R (FLIP: engine[k] == R[-k]) ---
        cc = tsl["cc_vec"]
        keys = sorted(k for k in cc if -k in R)
        eng_arr = np.array([cc[k] for k in keys])
        ref_arr = np.array([R[-k] for k in keys])
        primary["ccf_vector"] = _compare_vector(eng_arr, ref_arr, ladder["ccf_vector"])
        statuses.append(primary["ccf_vector"]["status"])

        # --- arm 1b: optimal_lag == -R_argmax == known DGP lag ---
        lag_ok = (tsl["cc_lag"] == -ref["R_argmax"] == ref["dgp_lag"])
        primary["ccf_optimal_lag"] = {"status": "PASS" if lag_ok else "BLOCK",
            "engine": tsl["cc_lag"], "neg_R_argmax": -ref["R_argmax"],
            "dgp_lag": ref["dgp_lag"]}
        statuses.append(primary["ccf_optimal_lag"]["status"])

        # --- arm 2: WHITENESS invariant + discrimination ---
        white = tsl["pw_minp"] > _LB_ALPHA
        disc_w = tsl["raw_minp"] < _LB_ALPHA   # negative control must reject
        w_status = "PASS" if (white and disc_w) else "BLOCK"
        primary["whiteness"] = {"status": w_status,
            "prewhitened_min_p": round(tsl["pw_minp"], 6),
            "raw_control_min_p": tsl["raw_minp"], "discriminates": bool(disc_w)}
        statuses.append(w_status)

        # --- arm 3: REDUCTION invariant + discrimination ---
        rv, sv, wv = tsl["roll_vec"], tsl["stat_vec"], tsl["wrong_vec"]
        common = sorted(k for k in rv if k in sv)
        red_diff = max(abs(rv[k] - sv[k]) for k in common)
        wrong_diff = max(abs(rv[k] - wv[k]) for k in common if k in wv)
        band = ladder["reduction"]
        red_ok = red_diff <= band["block_abs_tol"]
        red_pass = red_diff <= band["abs_tol"]
        disc_r = wrong_diff > 10 * band["abs_tol"]  # control must diverge
        lag_red_ok = (round(tsl["roll_meanlag"]) == tsl["stat_lag"] == ref["dgp_lag"])
        if red_pass and disc_r and lag_red_ok:
            r_status = "PASS"
        elif red_ok and disc_r and lag_red_ok:
            r_status = "CAVEAT"
        else:
            r_status = "BLOCK"
        primary["reduction"] = {"status": r_status,
            "rolling_vs_static_same_slice": red_diff,
            "rolling_vs_wrong_slice_control": round(wrong_diff, 6),
            "discriminates": bool(disc_r),
            "roll_mean_lag": tsl["roll_meanlag"], "static_lag": tsl["stat_lag"]}
        statuses.append(r_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "r_version": "stats::ccf (base R)",
                "lag_alignment": "FLIP (engine[k]==R[-k])",
                "ccf_max_abs_diff": primary["ccf_vector"].get("max_abs_diff"),
                "engine_max_lag": tsl["ml"],
                "whiteness_prewhitened_min_p": round(tsl["pw_minp"], 6),
                "whiteness_raw_control_min_p": tsl["raw_minp"],
                "reduction_same_slice_diff": tsl and red_diff,
                "reduction_wrong_slice_control": round(wrong_diff, 6),
                "banked_engine_gaps": (
                    "Y-side _apply_arima_filter weak fallback; "
                    "residual_ljung_box_p None placeholder (both BANKED, not fixed)"),
            },
        )
