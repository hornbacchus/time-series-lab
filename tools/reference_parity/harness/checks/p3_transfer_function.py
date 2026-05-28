"""Phase 3 Batch 10 — Transfer function / distributed lag parity check.

TSL ``engine/techniques/transfer_function.py`` (Box-Jenkins finite
distributed lag (FDL) / rational transfer function model with
configurable max_lag + AR(r)-noise component + optional Almon
polynomial restriction + contemporaneous-effect toggle + multi-
input exogenous support; OLS via numpy lstsq with full residual
diagnostics + Durbin-Watson + Ljung-Box + Jarque-Bera) vs from-
scratch paper-formula reimpl mirroring engine pipeline exactly.
Reference uses identical numpy.linalg.lstsq primitive + identical
design-matrix construction + identical AR-term integration + identical
diagnostics so any divergence isolates engine wrapper orchestration
vs paper-formula reference.

Rewritten at SC7-side Cat 3 remediation cycle session 7/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC7 = TIER B OPENING** — first cross-
block specialized session post-Tier-A close (SC6 quantile_regression
commit 73a6fe4 + stub cleanup 743e69b). Tree-family Layer 2 helpers
NOT APPLICABLE per SC6 forward-instrumentation; bespoke per-session
reimplementation.

**Helper identity verification (Step 1 of SC7 workflow):** Engine
`transfer_function.py` exposes only `run` + `_almon_basis` +
`build_interpretation` functions — NO `_prepare_series` or
`_create_features` or `_create_forecast_features`. Tier B expected
outcome per SC6 forward-instrumentation: tree-family Layer 2 helper
imports from SC1 NOT APPLICABLE; bespoke `_reference_transfer_function`
pipeline reimplemented inline mirroring engine source verbatim.

**Pre-rewrite degeneracy (Cat 3 DEGENERATE-VACUOUS classification):**
Original harness used local helper `_fit_distributed_lag` implementing
plain OLS at hardcoded `n_lags=3` with NO AR(r)-noise component + NO
Almon polynomial + NO contemporaneous-flag handling + NO extra-exog
support + NO residual diagnostics. Engine implements substantially
richer Box-Jenkins transfer function model with all of these
components. Both arms called the same local helper — degenerate
self-parity bypassing engine code path. Surfaced at inventory
verification 12d3785 + Gate 2 finding + triage close confirmation.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic OLS (numpy.linalg.lstsq is
deterministic at fixed input + matrix conditioning).
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


# Engine preset Balanced config (engine `transfer_function.py`
# line 27). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "max_lag": 8,
    "ar_order": 1,
    "include_contemporaneous": True,
}


def _generate_transfer_dgp(
    *, seed: int, n: int = 200,
    betas: tuple = (0.5, 0.3, 0.1),
) -> tuple[np.ndarray, np.ndarray]:
    """Y_t = sum(betas[k] * X_{t-k}) + AR(1) noise on Y."""
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
        if t > 0:
            y[t] += 0.3 * y[t - 1]  # AR(1) noise component
        y[t] += 0.2 * rng.standard_normal()
    return x, y


def _almon_basis_reference(lag_indices, degree):
    """Reference reimpl of engine `_almon_basis` at engine lines
    466-475. Z[k, :] @ gamma yields w_k where gamma is (degree+1,)."""
    lags = np.array(lag_indices, dtype=np.float64)
    Z = np.column_stack([lags ** d for d in range(degree + 1)])
    return Z


def _reference_transfer_function(
    y: np.ndarray, x: np.ndarray, *, seed: int, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `transfer_function.run()`
    pipeline at engine lines 57-450 verbatim (unrestricted polynomial
    path at Balanced preset). Bespoke per-session implementation per
    SC7 Tier B opening — Layer 2 family helpers NOT APPLICABLE.

    Pipeline (engine lines referenced inline):
    - Validate inputs + drop aligned NaN (engine lines 70-81)
    - Resolve preset config + parameters (engine lines 85-90)
    - Build design matrix: intercept + X lag terms (k=0..max_lag if
      contemporaneous else 1..max_lag) + AR(1..ar_order) Y terms
      (engine lines 188-237)
    - OLS via np.linalg.lstsq (engine line 243)
    - Standard errors via (X^T X)^-1 * mse (engine lines 260-265)
    - t-stats + p-values via scipy.stats.t (engine lines 268-269)
    - Goodness of fit: R^2 + adjusted R^2 + AIC + BIC + RMSE
      (engine lines 272-277)
    - Distributed lag weights extraction (engine lines 280-283)
    - Residual diagnostics: Jarque-Bera + Durbin-Watson +
      Ljung-Box at lag 10 (engine lines 339-378)
    """
    from scipy import stats as sp_stats  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    # Drop NaN aligned (engine lines 78-79)
    valid = ~np.isnan(y) & ~np.isnan(x)
    y_clean = y[valid].astype(np.float64)
    x_clean = x[valid].astype(np.float64)
    n_orig = len(y_clean)

    max_lag = int(cfg["max_lag"])
    ar_order = int(cfg["ar_order"])
    include_contemp = bool(cfg["include_contemporaneous"])

    min_start = max(max_lag, ar_order)
    start_idx = min_start
    effective_n = n_orig - start_idx
    y_dep = y_clean[start_idx:]

    lag_start = 0 if include_contemp else 1
    lag_indices = list(range(lag_start, max_lag + 1))

    # Unrestricted polynomial path (engine lines 205-210); Almon
    # path NOT exercised at Balanced preset default
    X_poly = np.column_stack([
        x_clean[start_idx - k: n_orig - k] for k in lag_indices
    ])

    # AR terms on Y (engine lines 213-216)
    if ar_order > 0:
        Y_ar = np.column_stack([
            y_clean[start_idx - j: n_orig - j]
            for j in range(1, ar_order + 1)
        ])
    else:
        Y_ar = np.empty((effective_n, 0))

    # No extra exogenous at fixture scope; X_extra empty
    X_extra = np.empty((effective_n, 0))

    # Intercept
    ones = np.ones((effective_n, 1))
    X_full = np.hstack([ones, X_poly, Y_ar, X_extra])

    # OLS via lstsq (engine line 243)
    beta, _resid_arr, _rank, _sv = np.linalg.lstsq(
        X_full, y_dep, rcond=None,
    )
    y_hat = X_full @ beta
    resid = y_dep - y_hat

    k = len(beta)
    dof = effective_n - k
    sse = float(np.sum(resid ** 2))
    mse = sse / dof
    sigma = float(np.sqrt(mse))

    # Standard errors (engine lines 260-265)
    try:
        XtX_inv = np.linalg.inv(X_full.T @ X_full)
        se = np.sqrt(np.diag(XtX_inv) * mse)
    except np.linalg.LinAlgError:
        XtX_inv = np.linalg.pinv(X_full.T @ X_full)
        se = np.sqrt(np.abs(np.diag(XtX_inv) * mse))

    t_stats = beta / se
    p_values = 2 * sp_stats.t.sf(np.abs(t_stats), dof)

    # Goodness of fit (engine lines 272-277)
    ss_total = float(np.sum((y_dep - np.mean(y_dep)) ** 2))
    r_squared = 1 - sse / ss_total if ss_total > 0 else 0.0
    adj_r_squared = (
        1 - (1 - r_squared) * (effective_n - 1) / dof
        if dof > 0 else r_squared
    )
    aic = effective_n * np.log(sse / effective_n) + 2 * k
    bic = effective_n * np.log(sse / effective_n) + k * np.log(effective_n)
    rmse = float(np.sqrt(np.mean(resid ** 2)))

    # Distributed lag weights (unrestricted; engine line 283)
    lag_weights = beta[1:1 + len(lag_indices)]
    cum_weight = float(np.sum(lag_weights))

    # Residual diagnostics (engine lines 339-378)
    jb_p_val = None
    dw_val = None
    lb_p_val = None
    if len(resid) > 10:
        jb, jb_p = sp_stats.jarque_bera(resid)
        jb_p_val = float(jb_p)
        dw_val = float(
            np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2)
        )
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox  # type: ignore
            lb_lag = min(10, max(1, len(resid) // 5))
            lb_result = acorr_ljungbox(
                resid, lags=[lb_lag], return_df=True,
            )
            lb_p_val = float(lb_result["lb_pvalue"].iloc[0])
        except Exception:
            lb_p_val = None

    return {
        "betas": beta.astype(np.float64),
        "std_errors": se.astype(np.float64),
        "t_stats": t_stats.astype(np.float64),
        "p_values": p_values.astype(np.float64),
        "lag_weights": np.asarray(lag_weights, dtype=np.float64),
        "r_squared": float(r_squared),
        "adj_r_squared": float(adj_r_squared),
        "rmse": float(rmse),
        "aic": float(aic),
        "bic": float(bic),
        "residual_std_error": sigma,
        "long_run_multiplier": float(cum_weight),
        "jarque_bera_pvalue": jb_p_val,
        "durbin_watson": dw_val,
        "ljung_box_pvalue": lb_p_val,
        "n_effective": int(effective_n),
        "n_params": int(k),
    }


class TransferFunctionParity(P3ParityCheck):
    """Transfer function parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.transfer_function.run() via
    RunContext with TWO series (Y output + X transfer input) +
    Balanced preset (max_lag=8 + ar_order=1 + include_contemporaneous=
    True + polynomial='unrestricted'). Reference arm reimplements
    the same OLS-based Box-Jenkins transfer function pipeline
    bespoke per SC7 Tier B opening (Layer 2 family-shared helpers
    NOT APPLICABLE).
    """

    technique_id = "p3_transfer_function"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Transfer function model is closed-form OLS regression on "
        "design matrix [intercept + X lag terms + AR(Y) terms]. "
        "numpy.linalg.lstsq is deterministic at fixed input + "
        "matrix conditioning. Engine and reference reimpl follow "
        "identical pipeline (design matrix construction + lstsq + "
        "standard errors + t-stats + p-values + R^2 + adjusted "
        "R^2 + AIC + BIC + RMSE + residual diagnostics); outputs "
        "match at machine precision modulo engine 6-decimal "
        "rounding floor at coefficients + 4-decimal at goodness-"
        "of-fit metrics + 2-decimal at AIC/BIC. SC7 Tier B opening: "
        "first cross-block specialized session post-Tier-A close; "
        "bespoke per-session reimplementation."
    )

    DGP_N = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_transfer_dgp(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext with 2-series input
        + Balanced preset; extract coefficients + lag weights +
        goodness-of-fit + residual diagnostics from engine tables +
        audit_fields."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.transfer_function as tf_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        x = np.asarray(fixture["x"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_transfer_function_parity",
            "technique_id": "transfer_function",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [
                {"name": "y", "values": y.tolist()},
                {"name": "x", "values": x.tolist()},
            ],
            "params": {},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = tf_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL transfer_function failed: "
                f"{resp.get('error_message')}"
            )
        # Coefficients table: Parameter / Estimate / Std Error /
        # t-Stat / P-Value / Sig
        coef_table = next(
            (t for t in resp["tables"] if t.get("name") == "Coefficients"),
            None,
        )
        if coef_table is None:
            raise RuntimeError("engine missing 'Coefficients' table")
        betas = np.array(
            [float(row[1]) for row in coef_table["rows"]],
            dtype=np.float64,
        )
        std_errors = np.array(
            [float(row[2]) for row in coef_table["rows"]],
            dtype=np.float64,
        )
        t_stats = np.array(
            [float(row[3]) for row in coef_table["rows"]],
            dtype=np.float64,
        )
        p_values = np.array(
            [float(row[4]) for row in coef_table["rows"]],
            dtype=np.float64,
        )

        # Distributed Lag Weights table: Lag / Weight / Cumulative
        lag_table = next(
            (t for t in resp["tables"]
             if t.get("name") == "Distributed Lag Weights"),
            None,
        )
        if lag_table is None:
            raise RuntimeError(
                "engine missing 'Distributed Lag Weights' table"
            )
        lag_weights = np.array(
            [float(row[1]) for row in lag_table["rows"]],
            dtype=np.float64,
        )

        audit = resp.get("audit_fields", {})
        return {
            "betas": betas,
            "std_errors": std_errors,
            "t_stats": t_stats,
            "p_values": p_values,
            "lag_weights": lag_weights,
            "r_squared": float(audit.get("r_squared", float("nan"))),
            "adj_r_squared": float(audit.get("adj_r_squared", float("nan"))),
            "rmse": float(audit.get("rmse", float("nan"))),
            "aic": float(audit.get("aic", float("nan"))),
            "bic": float(audit.get("bic", float("nan"))),
            "long_run_multiplier": float(
                audit.get("long_run_multiplier", float("nan"))
            ),
            "jarque_bera_pvalue": (
                float(audit.get("jarque_bera_pvalue"))
                if audit.get("jarque_bera_pvalue") is not None
                else float("nan")
            ),
            "durbin_watson": (
                float(audit.get("durbin_watson"))
                if audit.get("durbin_watson") is not None
                else float("nan")
            ),
            "ljung_box_pvalue": (
                float(audit.get("ljung_box_lag10_pvalue"))
                if audit.get("ljung_box_lag10_pvalue") is not None
                else float("nan")
            ),
            "n_effective": int(audit.get("n_effective", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        x = np.asarray(fixture["x"], dtype=np.float64)
        np.random.seed(42)
        return _reference_transfer_function(
            y, x, seed=42, preset_cfg=_ENGINE_BALANCED_PRESET,
        )

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8:
        # - coefficients: 6-decimal (engine lines 293-296)
        # - lag weights: 6-decimal (engine line 311)
        # - r_squared / adj_r_squared / rmse: 4-decimal (engine 411-413)
        # - AIC / BIC: 2-decimal (engine lines 414-415)
        # - long_run_multiplier: 6-decimal (engine line 416)
        # - t-stat: 4-decimal (engine line 295)
        # - residual diagnostics: 4-decimal jb/dw + 6-decimal lb_p
        ref_betas_rounded = np.round(ref["betas"], 6)
        ref_se_rounded = np.round(ref["std_errors"], 6)
        ref_tstats_rounded = np.round(ref["t_stats"], 4)
        ref_pvals_rounded = np.round(ref["p_values"], 6)
        ref_lag_weights_rounded = np.round(ref["lag_weights"], 6)

        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["betas"] = _compare_vector(
            tsl["betas"], ref_betas_rounded, ladder["primary"],
        )
        statuses.append(primary["betas"]["status"])

        primary["std_errors"] = _compare_vector(
            tsl["std_errors"], ref_se_rounded, ladder["primary"],
        )
        statuses.append(primary["std_errors"]["status"])

        primary["t_stats"] = _compare_vector(
            tsl["t_stats"], ref_tstats_rounded, ladder["primary"],
        )
        statuses.append(primary["t_stats"]["status"])

        primary["p_values"] = _compare_vector(
            tsl["p_values"], ref_pvals_rounded, ladder["primary"],
        )
        statuses.append(primary["p_values"]["status"])

        primary["lag_weights"] = _compare_vector(
            tsl["lag_weights"], ref_lag_weights_rounded,
            ladder["primary"],
        )
        statuses.append(primary["lag_weights"]["status"])

        primary["r_squared"] = _compare_scalar(
            tsl["r_squared"], round(ref["r_squared"], 4),
            ladder["primary"],
        )
        statuses.append(primary["r_squared"]["status"])

        primary["adj_r_squared"] = _compare_scalar(
            tsl["adj_r_squared"], round(ref["adj_r_squared"], 4),
            ladder["primary"],
        )
        statuses.append(primary["adj_r_squared"]["status"])

        primary["rmse"] = _compare_scalar(
            tsl["rmse"], round(ref["rmse"], 4),
            ladder["primary"],
        )
        statuses.append(primary["rmse"]["status"])

        primary["aic"] = _compare_scalar(
            tsl["aic"], round(ref["aic"], 2),
            ladder["primary"],
        )
        statuses.append(primary["aic"]["status"])

        primary["bic"] = _compare_scalar(
            tsl["bic"], round(ref["bic"], 2),
            ladder["primary"],
        )
        statuses.append(primary["bic"]["status"])

        primary["long_run_multiplier"] = _compare_scalar(
            tsl["long_run_multiplier"],
            round(ref["long_run_multiplier"], 6),
            ladder["primary"],
        )
        statuses.append(primary["long_run_multiplier"]["status"])

        # Residual diagnostics: jb 4-decimal, dw 4-decimal, lb_p 6-decimal
        if not np.isnan(tsl["jarque_bera_pvalue"]):
            primary["jarque_bera_pvalue"] = _compare_scalar(
                tsl["jarque_bera_pvalue"],
                round(ref["jarque_bera_pvalue"], 6)
                if ref["jarque_bera_pvalue"] is not None else float("nan"),
                ladder["primary"],
            )
            statuses.append(primary["jarque_bera_pvalue"]["status"])

        if not np.isnan(tsl["durbin_watson"]):
            primary["durbin_watson"] = _compare_scalar(
                tsl["durbin_watson"],
                round(ref["durbin_watson"], 4)
                if ref["durbin_watson"] is not None else float("nan"),
                ladder["primary"],
            )
            statuses.append(primary["durbin_watson"]["status"])

        if not np.isnan(tsl["ljung_box_pvalue"]):
            primary["ljung_box_pvalue"] = _compare_scalar(
                tsl["ljung_box_pvalue"],
                round(ref["ljung_box_pvalue"], 6)
                if ref["ljung_box_pvalue"] is not None else float("nan"),
                ladder["primary"],
            )
            statuses.append(primary["ljung_box_pvalue"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = (
            "BLOCK" if any_block else
            ("CAVEAT" if any_caveat else "PASS")
        )
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "preset": "Balanced",
                "max_lag": int(_ENGINE_BALANCED_PRESET["max_lag"]),
                "ar_order": int(_ENGINE_BALANCED_PRESET["ar_order"]),
                "include_contemporaneous": bool(
                    _ENGINE_BALANCED_PRESET["include_contemporaneous"]
                ),
                "polynomial": "unrestricted",
                "n_effective_tsl": int(tsl.get("n_effective", 0)),
            },
        )
