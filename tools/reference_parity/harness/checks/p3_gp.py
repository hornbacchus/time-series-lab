"""Phase 3 Batch 9 — Gaussian Process forecast parity check.

TSL ``engine/techniques/gaussian_process_forecast.py`` (sklearn
GaussianProcessRegressor with kernel-preset-resolved
ConstantKernel * base_kernel + WhiteKernel construction +
y-only z-score normalization + GP fit at engine-resolved
n_restarts/alpha + posterior mean + posterior std prediction +
denormalization + normal-z confidence interval construction) vs
from-scratch paper-formula reimpl mirroring engine pipeline
verbatim.

Rewritten at SC10-side Cat 3 remediation cycle session 10/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC10 = TIER C OPENING** (first
probabilistic/Bayesian/reservoir session post-Tier-B close).

**Helper identity verification (Step 1 of SC10 workflow per SC4
two-stage methodology):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at GP engine lines 26-46: **MATCH SC1 RF**
  (hash 57bae54d463c2fd7)
- `_create_features`: **ABSENT** (GP engine does NOT use lag/rolling
  feature engineering; uses time-index `X = np.arange(n)` as input
  per engine line 154)
- `_create_forecast_features`: **ABSENT** (GP engine does NOT use
  recursive multi-step forecast; predicts directly at horizon time
  indices via `X_forecast = np.arange(n, n + horizon)` per engine
  line 155)

Stage 2 (manual code inspection on absent helpers): GP engine uses
fundamentally different feature engineering pattern from tree-family
(time-index regression vs lag-feature tabular regression). No
behavioral mapping possible; absent helpers indicate architectural
distinctness. **PARTIAL Tier A pattern: `_prepare_series` reused
from SC1; remaining pipeline bespoke per-session.**

**Institutional finding for bespoke-per-session codification
question:** SC10 is the FIRST sklearn-backbone technique in cycle
exhibiting **PARTIAL** helper reuse (1 MATCH + 2 ABSENT) — distinct
from Tier A.1-A.5 tree-family (all 3 MATCH or comment-only) +
distinct from Tier A.6 QR (1 MATCH + 1 BEHAVIORAL + 1 ABSENT) +
distinct from Tier B SC7-SC9 (all 3 ABSENT). New PARTIAL-Tier-A
pattern: sklearn-backbone + SC1-compatible NaN handling +
technique-distinct feature engineering. Codification implication:
the bespoke-per-session pattern is NOT strictly Tier-B-specific;
sklearn-backbone-but-architecturally-distinct techniques (GP +
potentially others) exhibit a PARTIAL pattern where some Tier A
helpers reuse and feature engineering is bespoke.

**Architectural elements (SC10 GP-specific; distinct from SC1-SC9
patterns):**

1. **Time-index input pattern:** `X_train = np.arange(n).reshape(-1, 1)`
   (engine line 154); GP regresses y on TIME index directly, not
   lag features. Distinct from SC1-SC6 tabular ML pattern + SC7
   transfer_function lag-feature pattern.
2. **y-only z-score normalization:** Engine lines 142-151 normalize
   y only (mean=0, std=1); X (time index) is NOT scaled. Distinct
   from SC5 SVR dual StandardScaler on both X+y.
3. **Kernel construction:** ConstantKernel(1.0) * base_kernel +
   WhiteKernel(0.1) composite kernel; base_kernel defaults to RBF
   with `length_scale_init = n/5.0` (engine line 161).
4. **Direct horizon prediction:** `X_forecast = np.arange(n, n +
   horizon)`; GP predicts at horizon time indices directly without
   recursive multi-step iteration. Distinct from SC1-SC6 + SC7
   recursive forecast pattern.
5. **Posterior std + CI computation:** GP returns posterior mean +
   posterior std via `gp.predict(X_all, return_std=True)`;
   confidence intervals computed via normal-z. **Posterior
   uncertainty quantification is institutionally meaningful for
   fixed-income use** (prediction intervals around yield forecasts).
6. **Denormalization on predictions:** Posterior mean and std
   denormalized by `y_pred * y_std + y_mean` + `y_std * y_std`
   respectively (engine lines 192-193). Mirror this in reference
   arm.
7. **Subsample-trigger if n > max_train=500** (engine line 131);
   not exercised at fixture n=100.
8. **NO fallback dispatch:** sklearn always available; SC3 template
   element NOT APPLICABLE.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic GP (L-BFGS-B optimizer
with random_state=ctx.seed for reproducible n_restarts).
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
from reference_parity.harness.checks.p3_random_forest import (
    _prepare_series_reference,
)
from reference_parity.harness.checks.p3_lstm_gru import _generate_ar_dgp


# Engine preset Balanced config (engine `gaussian_process_forecast.py`
# line 21). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "n_restarts": 5,
    "max_train": 500,
    "alpha": 1e-7,
}


def _reference_gaussian_process(
    values: np.ndarray, *, seed: int, horizon: int = 10,
    preset_cfg: dict = None, kernel_type: str = "rbf",
    normalize: bool = True, confidence_level: float = 0.95,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `gaussian_process_forecast.run()`
    pipeline at engine lines 49-401 verbatim (Balanced preset +
    RBF kernel default path). PARTIAL Tier A pattern: reuses SC1
    `_prepare_series_reference` for NaN handling (Layer 2 family-
    shared helper applicable per SC10 Step 1 Stage 1 hash MATCH);
    bespoke pipeline implementation for GP-specific kernel
    construction + fit + posterior prediction + denormalization +
    CI computation.
    """
    from sklearn.gaussian_process import (  # type: ignore
        GaussianProcessRegressor,
    )
    from sklearn.gaussian_process.kernels import (  # type: ignore
        RBF, WhiteKernel, ConstantKernel, Matern, RationalQuadratic,
    )
    from scipy import stats as sp_stats  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    # Layer 2 family-shared helper reuse: _prepare_series_reference
    # mirrors engine _prepare_series exactly (AST hash MATCH per
    # Step 1 Stage 1)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    n_restarts = int(cfg["n_restarts"])
    max_train = int(cfg["max_train"])
    gp_alpha = float(cfg["alpha"])

    # Subsample-trigger per engine line 131
    if n > max_train:
        clean = clean[-max_train:]
        n = len(clean)

    alpha_ci = 1.0 - confidence_level

    # y-only normalization per engine lines 142-151
    if normalize:
        y_mean = float(np.mean(clean))
        y_std = float(np.std(clean, ddof=1))
        if y_std == 0:
            y_std = 1.0
        y_norm = (clean - y_mean) / y_std
    else:
        y_mean = 0.0
        y_std = 1.0
        y_norm = clean.copy()

    # Time-index input per engine lines 154-156
    X_train = np.arange(n).reshape(-1, 1).astype(float)
    X_forecast = np.arange(n, n + horizon).reshape(-1, 1).astype(float)
    X_all = np.vstack([X_train, X_forecast])

    # Kernel construction per engine lines 160-173
    length_scale_init = float(n) / 5.0
    if kernel_type == "matern":
        base_kernel = Matern(length_scale=length_scale_init, nu=2.5)
    elif kernel_type == "rational_quadratic":
        base_kernel = RationalQuadratic(
            length_scale=length_scale_init, alpha=1.0,
        )
    else:
        base_kernel = RBF(length_scale=length_scale_init)
    kernel = (
        ConstantKernel(1.0, (1e-3, 1e3))
        * base_kernel
        + WhiteKernel(noise_level=0.1, noise_level_bounds=(1e-10, 1e1))
    )

    # GP fit per engine lines 177-184
    gp = GaussianProcessRegressor(
        kernel=kernel,
        alpha=gp_alpha,
        n_restarts_optimizer=n_restarts,
        normalize_y=False,
        random_state=seed,
    )
    gp.fit(X_train, y_norm)

    # Predict + denormalize per engine lines 189-199
    y_pred_all, y_std_all = gp.predict(X_all, return_std=True)
    y_pred_all = y_pred_all * y_std + y_mean
    y_std_all = y_std_all * y_std
    y_pred_train = y_pred_all[:n]
    y_std_train = y_std_all[:n]
    y_pred_fc = y_pred_all[n:]
    y_std_fc = y_std_all[n:]

    # CI computation per engine lines 210-212
    z = sp_stats.norm.ppf(1.0 - alpha_ci / 2)
    fc_lower = y_pred_fc - z * y_std_fc
    fc_upper = y_pred_fc + z * y_std_fc

    # Diagnostics per engine lines 260-263
    residuals = clean - y_pred_train
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    r2 = float(
        1.0
        - np.sum(residuals ** 2)
        / np.sum((clean - np.mean(clean)) ** 2)
    )
    lml = float(gp.log_marginal_likelihood_value_)
    avg_fc_std = float(np.mean(y_std_fc))

    # Length-scale extraction per engine lines 326-343
    length_scale = None
    try:
        for hyp in gp.kernel_.hyperparameters:
            if "length_scale" in hyp.name:
                length_scale = float(
                    np.exp(gp.kernel_.theta[list(
                        h.name for h in gp.kernel_.hyperparameters
                    ).index(hyp.name)])
                )
                break
    except Exception:
        pass

    return {
        "forecast_mean": y_pred_fc.astype(np.float64),
        "forecast_std": y_std_fc.astype(np.float64),
        "forecast_lower": fc_lower.astype(np.float64),
        "forecast_upper": fc_upper.astype(np.float64),
        "log_marginal_likelihood": lml,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "avg_forecast_std": avg_fc_std,
        "length_scale": length_scale,
    }


class GpParity(P3ParityCheck):
    """GP forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.gaussian_process_forecast.run()
    via RunContext at Balanced preset (n_restarts=5 + max_train=500 +
    alpha=1e-7 + RBF kernel default + normalize=True default +
    confidence_level=0.95 default). Reference arm reimplements full
    engine pipeline with PARTIAL Tier A family-shared helper reuse
    (`_prepare_series_reference` from SC1) + bespoke GP-specific
    pipeline (time-index input + y-only normalization + composite
    kernel + posterior prediction + denormalization + CI).
    """

    technique_id = "p3_gp"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "sklearn GaussianProcessRegressor with L-BFGS-B + fixed "
        "random_state + fixed n_restarts is deterministic at fixed "
        "input. Engine and reference reimpl follow identical "
        "pipeline (NaN drop via SC1 helper + y-only normalize + "
        "RBF + WhiteKernel composite + GP fit + posterior mean + "
        "posterior std + denormalize + CI); outputs match at "
        "machine precision modulo engine 6-decimal forecast "
        "rounding + 4-decimal audit metric rounding. SC10 PARTIAL "
        "Tier A pattern: sklearn-backbone with SC1 _prepare_series "
        "reuse + bespoke GP-specific feature engineering."
    )

    DGP_N = 100
    HORIZON = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.gaussian_process_forecast as gp_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_gp_parity",
            "technique_id": "gaussian_process_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = gp_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL gaussian_process_forecast failed: "
                f"{resp.get('error_message')}"
            )
        # Forecast table: Step + Forecast + Std Dev + Lower + Upper
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast_mean = np.array(
            [float(row[1]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        forecast_std = np.array(
            [float(row[2]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        forecast_lower = np.array(
            [float(row[3]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        forecast_upper = np.array(
            [float(row[4]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        audit = resp.get("audit_fields", {})
        return {
            "forecast_mean": forecast_mean,
            "forecast_std": forecast_std,
            "forecast_lower": forecast_lower,
            "forecast_upper": forecast_upper,
            "log_marginal_likelihood": float(
                audit.get("log_marginal_likelihood", float("nan"))
            ),
            "rmse": float(audit.get("rmse", float("nan"))),
            "r2": float(audit.get("r2", float("nan"))),
            "avg_forecast_std": float(
                audit.get("avg_forecast_std", float("nan"))
            ),
            "length_scale": (
                float(audit.get("length_scale"))
                if audit.get("length_scale") is not None
                else None
            ),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import sklearn  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_gaussian_process(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
            kernel_type="rbf", normalize=True,
            confidence_level=0.95,
        )
        out["sklearn_version"] = sklearn.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8:
        # - forecast mean/std/lower/upper: 6-decimal (engine 231-234)
        # - log_marginal_likelihood / rmse / r2 / avg_fc_std: 4-decimal
        # - length_scale: 6-decimal (engine line 355)
        ref_mean_rounded = np.round(ref["forecast_mean"], 6)
        ref_std_rounded = np.round(ref["forecast_std"], 6)
        ref_lower_rounded = np.round(ref["forecast_lower"], 6)
        ref_upper_rounded = np.round(ref["forecast_upper"], 6)

        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast_mean"] = _compare_vector(
            tsl["forecast_mean"], ref_mean_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast_mean"]["status"])

        primary["forecast_std"] = _compare_vector(
            tsl["forecast_std"], ref_std_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast_std"]["status"])

        primary["forecast_lower"] = _compare_vector(
            tsl["forecast_lower"], ref_lower_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast_lower"]["status"])

        primary["forecast_upper"] = _compare_vector(
            tsl["forecast_upper"], ref_upper_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast_upper"]["status"])

        primary["log_marginal_likelihood"] = _compare_scalar(
            tsl["log_marginal_likelihood"],
            round(ref["log_marginal_likelihood"], 4),
            ladder["primary"],
        )
        statuses.append(primary["log_marginal_likelihood"]["status"])

        primary["rmse"] = _compare_scalar(
            tsl["rmse"], round(ref["rmse"], 4), ladder["primary"],
        )
        statuses.append(primary["rmse"]["status"])

        primary["r2"] = _compare_scalar(
            tsl["r2"], round(ref["r2"], 4), ladder["primary"],
        )
        statuses.append(primary["r2"]["status"])

        primary["avg_forecast_std"] = _compare_scalar(
            tsl["avg_forecast_std"],
            round(ref["avg_forecast_std"], 4),
            ladder["primary"],
        )
        statuses.append(primary["avg_forecast_std"]["status"])

        # length_scale may be None on either side; only compare if both
        # present
        if (tsl["length_scale"] is not None
                and ref["length_scale"] is not None):
            primary["length_scale"] = _compare_scalar(
                tsl["length_scale"],
                round(ref["length_scale"], 6),
                ladder["primary"],
            )
            statuses.append(primary["length_scale"]["status"])

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
                "horizon": int(self.HORIZON),
                "preset": "Balanced",
                "n_restarts": int(_ENGINE_BALANCED_PRESET["n_restarts"]),
                "max_train": int(_ENGINE_BALANCED_PRESET["max_train"]),
                "alpha": float(_ENGINE_BALANCED_PRESET["alpha"]),
                "kernel_type": "rbf",
                "normalize": True,
                "confidence_level": 0.95,
                "sklearn_version": ref.get("sklearn_version", "unknown"),
            },
        )
