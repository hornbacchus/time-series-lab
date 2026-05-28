"""Phase 3 Batch 9 — N-HiTS (Neural Hierarchical Interpolation for
Time Series) forecast parity check.

TSL ``engine/techniques/nhits_forecast.py`` (PyTorch N-HiTS per
Challu et al. 2022 "N-HiTS: Neural Hierarchical Interpolation for
Time Series Forecasting" arXiv:2201.12886 with multi-rate signal
sampling via MaxPool1d + hierarchical interpolation via linear
upsampling + 3-layer fully-connected blocks producing backcast +
forecast at multi-rate resolutions + doubly-residual stacking +
Adam optimizer + MSE loss + gradient clipping + sliding-window
sequence construction at n_lags + direct multi-step (horizon-step)
forecast + sklearn ensemble fallback (Ridge + GBR + MLP) when
PyTorch unavailable) vs from-scratch paper-formula reimpl mirroring
engine PyTorch primary path verbatim.

Rewritten at SC17-side Cat 3 remediation cycle session 17/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC17 = Tier D.5** (fifth PyTorch-based
DL family session; first hierarchical-interpolation architecture
after SC13 feed-forward MLP autoencoder + SC14 recurrent LSTM/GRU +
SC15 convolutional TCN + SC16 basis-expansion NBEATS).
**SC17 CLOSES the Cat 3 remediation cycle.** PARTIAL Tier A pattern
EIGHTH-INSTANCE confirmation + Tier D DL family determinism profile
inheritance from SC13/SC14/SC15/SC16 (hierarchical-interpolation
architecture cross-invocation bit-exact at CPU PyTorch verified at
Step 2 — extends feed-forward + recurrent + convolutional + basis-
expansion → hierarchical-interpolation generalization at n=5
distinct DL architecture types).

**Helper identity verification (Step 1 of SC17 workflow per SC4
two-stage methodology + SC10-SC16 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 50-70: **MATCH SC1 RF**
  `_prepare_series_reference` verbatim (strip-edge-NaN + interp-
  interior body identical modulo function-name token only).
- `_create_sequences` at engine lines 73-79: **MATCH SC16 p3_nbeats**
  `_create_sequences_nbeats` verbatim (multi-horizon target
  variant; signature `(data, lookback, horizon)` returning (X, y)
  with y shape (n_samples, horizon)). **SC16 reuse-conditionality
  sub-pattern SECOND-OBSERVATION TIGHTENING** confirmed at SC17:
  direct-multi-step architectures (NBEATS SC16 + NHITS SC17) share
  the multi-horizon variant; recursive-multi-step (LSTM SC14 +
  TCN SC15) share the 1-step variant. **DL-family-shared sequence-
  helper reuse is architecture-type-conditional with TWO sub-cohorts
  confirmed empirically (1-step recursive ×2 + multi-horizon direct
  ×2).**
- `_create_lag_features` at engine lines 82-89: **ABSENT** (only
  exercised in sklearn ensemble fallback path; PyTorch primary
  path uses `_create_sequences` exclusively).

Stage 2: PARTIAL Tier A pattern EIGHTH-INSTANCE confirmation at
sustained n=8 cumulative observations (SC10 GP + SC11 prophet +
SC12 esn + SC13 autoencoder + SC14 lstm_gru + SC15 tcn + SC16
nbeats + SC17 nhits); A3 fourth-observation-tightening threshold
satisfied n=5-fold post-SC17; **architecture-type-agnostic
generalization SUSTAINED across FIVE distinct DL architecture
types** (feed-forward + recurrent + convolutional + basis-expansion
+ hierarchical-interpolation all exhibit PARTIAL Tier A pattern
under shared determinism profile). **Reuse-conditionality sub-
pattern A3 SECOND-OBSERVATION TIGHTENING at SC17** (SC16 first-
instance + SC17 second-instance; codification candidate at
absorption #6+ EMPIRICALLY GROUNDED at n=2 distinct architecture-
cohort observations within sustained n=8 PARTIAL Tier A scope).

**Cross-invocation reproducibility verification (Step 2 — inherits
SC13/SC14/SC15/SC16 DL family determinism profile + hierarchical-
interpolation-architecture verification):** Inherited determinism
configuration applied. Engine invoked TWICE as separate Python
computations at seed=42 → **max_abs_diff=0.0 (BIT-EXACT cross-
invocation)** at CPU PyTorch NHITS (Balanced preset default
n_stacks=3 + n_blocks=3 + hidden_size=128 + pooling_sizes=[4, 2, 1]).
**CONFIRMS SC13/SC14/SC15/SC16 DL determinism profile holds for
hierarchical-interpolation architectures** (multi-rate MaxPool1d
deterministic at fixed input; linear interpolation upsampling
deterministic with align_corners=False; per-stack pool_size
schedule deterministic; doubly-residual composition deterministic).

**Tier D hierarchical-interpolation-architecture-specific parity
risks (resolved via Step 2):**
- Per-stack pool_size schedule: engine `NHiTS` constructs
  `nn.ModuleList([NHiTSStack(input_size, n_blocks, hidden_size,
  horizon, pooling_sizes[i] if i < len(pooling_sizes) else 1) for
  i in range(n_stacks)])`. For Balanced (n_stacks=3,
  pooling_sizes=[4, 2, 1]) stacks consume pool_sizes [4, 2, 1] in
  order. Reference matches.
- MaxPool1d determinism: engine `NHiTSBlock.forward` applies
  `nn.functional.max_pool1d(x_pool, kernel_size=pool_size,
  stride=pool_size, ceil_mode=True)` only when `pool_size > 1` AND
  `x.shape[-1] > pool_size`. MaxPool1d on CPU is deterministic at
  fixed input (no randomness; arg-max ties broken deterministically
  by index ordering). Reference matches.
- Linear interpolation upsampling: engine applies
  `nn.functional.interpolate(..., size=horizon, mode="linear",
  align_corners=False)` to upsample forecast_coeff (length
  `horizon // pool_size`) to horizon length; SAME function applied
  in NHiTSStack to upsample backcast (length `pooled_input`) to
  residual.shape[-1]. align_corners=False fixes the upsampling
  formula deterministically. Reference matches exactly.
- Block FC init order: engine `NHiTSBlock` constructs `fc =
  nn.Sequential(Linear(pooled_input, hidden), ReLU, Linear(hidden,
  hidden), ReLU, Linear(hidden, hidden), ReLU)` — 3-layer FC tower
  (DISTINCT from NBEATS 4-layer SC16). Reference matches.
- Block heads init order: within each block, `backcast_fc =
  Linear(hidden, pooled_input)` then `forecast_fc = Linear(hidden,
  n_coeff)` where pooled_input = `max(1, input_size // pool_size)`
  and n_coeff = `max(1, horizon // pool_size)`. Construction-order
  RNG-draw-preserving.
- Doubly-residual stacking with cross-resolution interpolation:
  engine `NHiTSStack.forward` upsamples backcast back to
  residual.shape[-1] via linear interpolation BEFORE subtracting
  (residual -= backcast). Engine `NHiTS.forward` accumulates total
  forecast across stacks. Reference implements identical residual
  + interpolation wiring.
- Gradient clipping: engine applies
  `torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)` per
  NBEATS lineage. Reference matches.
- cuDNN non-determinism: NOT exercised at audit environment
  (torch 2.11.0+cpu); CPU FC + MaxPool1d + linear interpolation
  ops all deterministic.

**Fallback dispatch handling (SC3 template element NINTH-INSTANCE
application):** Engine `_has_torch()` at lines 23-28 + preset flag
`use_torch` at engine line 387 dispatches to PyTorch NHITS primary
path when torch available + preset enables; sklearn ENSEMBLE
fallback (Ridge + GradientBoostingRegressor + MLPRegressor averaged
via `_train_sklearn_ensemble` at lines 241-269 + `_predict_sklearn_
ensemble` at lines 272-284) when torch unavailable (Fast preset
uses sklearn ensemble by default per engine line 35
`use_torch: False`).

**Mathematical equivalence assessment (primary vs fallback):
CATEGORICALLY DIFFERENT.** PyTorch NHITS (hierarchical-interpolation
architecture with multi-rate MaxPool1d + linear interpolation
upsampling + doubly-residual stacking + direct multi-step forecast)
vs sklearn ensemble of {Ridge linear model, gradient-boosted tree
ensemble, MLP feed-forward network} averaged via mean (recursive
single-step forecast). Outputs are NOT numerically equivalent —
fundamentally different architectures + different ensembling +
different forecast generation mode. SAME ensemble-based fallback
pattern as SC16 nbeats (both NBEATS-lineage techniques use 3-model
sklearn ensemble fallback).

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor at CPU PyTorch backend per SC13 + SC14 +
SC15 + SC16 + SC17 determinism profile).
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
from reference_parity.harness.checks.p3_lstm_gru import (
    _setup_dl_determinism,
    _generate_ar_dgp,
)
from reference_parity.harness.checks.p3_nbeats import (
    _create_sequences_nbeats,
)


# Engine preset Balanced config (engine `nhits_forecast.py` lines
# 37-41). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "n_stacks": 3,
    "n_blocks": 3,
    "hidden_size": 128,
    "pooling_sizes": [4, 2, 1],
    "epochs": 50,
    "n_lags": 16,
    "lr": 0.005,
    "use_torch": True,
}


def _reference_nhits_forecast(
    values: np.ndarray, *, seed: int, horizon: int = 12,
    preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `nhits_forecast.run()`
    primary PyTorch path at engine lines 396-432 verbatim including
    `_train_torch_nhits` at engine lines 196-226 (NHiTSBlock +
    NHiTSStack + NHiTS classes with multi-rate MaxPool1d +
    hierarchical linear interpolation upsampling + 3-layer FC blocks
    + backcast/forecast heads + Adam + MSE + grad clip + epochs
    training loop) + `_predict_torch_nhits` at engine lines 229-238
    (direct multi-step forecast).

    Construction order RNG-determinism: stacks 0..n_stacks
    constructed in order with pool_size = pooling_sizes[i]; within
    each stack, blocks 0..n_blocks constructed in order (all
    sharing stack's pool_size); within each block: fc Sequential
    (L1(pooled_in, h), R, L2(h, h), R, L3(h, h), R) then backcast_fc
    Linear(h, pooled_in) then forecast_fc Linear(h, n_coeff).
    Mirrors engine `_build_nhits_model` exactly.
    """
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # SC1 helper reuse (PARTIAL Tier A eighth-instance)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    n_stacks = int(cfg["n_stacks"])
    n_blocks = int(cfg["n_blocks"])
    hidden_size = int(cfg["hidden_size"])
    pooling_sizes = list(cfg["pooling_sizes"])
    epochs = int(cfg["epochs"])
    n_lags = int(cfg["n_lags"])
    lr = float(cfg["lr"])

    # Cap n_lags per engine line 378
    n_lags = min(n_lags, n // 3)

    # Normalize per engine lines 381-385
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Create sequences per engine line 398 (SC16 multi-horizon
    # helper reuse — DL-family-shared sub-cohort for direct-multi-
    # step architectures; SECOND-OBSERVATION TIGHTENING).
    X, y_seq = _create_sequences_nbeats(normalized, n_lags, horizon)

    # ===== _train_torch_nhits reimpl per engine lines 196-226 =====
    torch.manual_seed(seed)
    lookback = X.shape[1]

    class NHiTSBlock(nn.Module):
        """Mirrors engine `_build_nhits_model.NHiTSBlock` lines
        97-145 verbatim."""
        def __init__(self, input_size, hidden_size, horizon, pool_size):
            super().__init__()
            self.pool_size = pool_size
            pooled_input = max(1, input_size // pool_size)
            # Interpolation coefficients (smaller than horizon)
            self.n_coeff = max(1, horizon // pool_size)

            self.fc = nn.Sequential(
                nn.Linear(pooled_input, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
            )
            self.backcast_fc = nn.Linear(hidden_size, pooled_input)
            self.forecast_fc = nn.Linear(hidden_size, self.n_coeff)
            self.horizon = horizon

        def forward(self, x):
            # MaxPool1d for multi-rate sampling per engine 118-128
            if self.pool_size > 1 and x.shape[-1] > self.pool_size:
                x_pool = x.unsqueeze(1)
                x_pool = nn.functional.max_pool1d(
                    x_pool, kernel_size=self.pool_size,
                    stride=self.pool_size, ceil_mode=True,
                )
                x_pool = x_pool.squeeze(1)
            else:
                x_pool = x

            h = self.fc(x_pool)
            backcast = self.backcast_fc(h)
            forecast_coeff = self.forecast_fc(h)

            # Hierarchical linear interpolation per engine 134-143
            if forecast_coeff.shape[-1] < self.horizon:
                forecast = nn.functional.interpolate(
                    forecast_coeff.unsqueeze(1),
                    size=self.horizon,
                    mode="linear",
                    align_corners=False,
                ).squeeze(1)
            else:
                forecast = forecast_coeff[:, :self.horizon]

            return backcast, forecast

    class NHiTSStack(nn.Module):
        """Mirrors engine `_build_nhits_model.NHiTSStack` lines
        147-174 verbatim. Doubly-residual stacking with cross-
        resolution backcast interpolation."""
        def __init__(self, input_size, n_blocks, hidden_size, horizon,
                     pool_size):
            super().__init__()
            self.blocks = nn.ModuleList([
                NHiTSBlock(input_size, hidden_size, horizon, pool_size)
                for _ in range(n_blocks)
            ])
            self.pool_size = pool_size

        def forward(self, x):
            residual = x
            stack_forecast = 0
            for block in self.blocks:
                backcast, forecast = block(residual)
                # Upsample backcast back to residual size if needed
                # per engine 162-171
                if backcast.shape[-1] < residual.shape[-1]:
                    backcast = nn.functional.interpolate(
                        backcast.unsqueeze(1),
                        size=residual.shape[-1],
                        mode="linear",
                        align_corners=False,
                    ).squeeze(1)
                elif backcast.shape[-1] > residual.shape[-1]:
                    backcast = backcast[:, :residual.shape[-1]]
                residual = residual - backcast
                stack_forecast = stack_forecast + forecast
            return residual, stack_forecast

    class NHiTS(nn.Module):
        """Mirrors engine `_build_nhits_model.NHiTS` lines 176-191
        verbatim. Multi-rate hierarchical stacking via per-stack
        pool_size from pooling_sizes schedule."""
        def __init__(self, input_size, n_stacks, n_blocks, hidden_size,
                     horizon, pooling_sizes):
            super().__init__()
            self.stacks = nn.ModuleList([
                NHiTSStack(
                    input_size, n_blocks, hidden_size, horizon,
                    pooling_sizes[i] if i < len(pooling_sizes) else 1,
                )
                for i in range(n_stacks)
            ])

        def forward(self, x):
            residual = x
            total_forecast = 0
            for stack in self.stacks:
                residual, forecast = stack(residual)
                total_forecast = total_forecast + forecast
            return total_forecast

    model = NHiTS(
        lookback, n_stacks, n_blocks, hidden_size, horizon,
        pooling_sizes,
    )

    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.FloatTensor(y_seq)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for _epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(X_tensor)
        loss = loss_fn(pred, y_tensor)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    final_loss = losses[-1] if losses else float("inf")
    initial_loss = losses[0] if losses else None

    # Parameter count per engine line 428
    try:
        n_params = int(sum(p.numel() for p in model.parameters()))
    except Exception:
        n_params = None

    # Direct multi-step forecast per engine lines 414-415 +
    # _predict_torch_nhits (lines 229-238). Input shape (1, n_lags).
    last_seq = normalized[-n_lags:].copy()
    with torch.no_grad():
        x = torch.FloatTensor(last_seq).unsqueeze(0)
        fc_norm = model(x).squeeze(0).numpy()[:horizon]

    # In-sample predictions per engine lines 419-426 (first-step
    # only for in-sample metric).
    with torch.no_grad():
        X_full = torch.FloatTensor(X)
        y_pred_all = model(X_full).numpy()
    y_pred_norm = y_pred_all[:, 0]
    y_actual_norm = y_seq[:, 0]

    # Denormalize per engine lines 471-473
    fc_values = fc_norm * y_std + y_mean
    y_actual = y_actual_norm * y_std + y_mean
    y_pred = y_pred_norm * y_std + y_mean

    # Metrics per engine lines 476-481
    residuals = y_actual - y_pred
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y_actual - np.mean(y_actual)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return {
        "forecast": fc_values.astype(np.float64),
        "final_loss": final_loss,
        "initial_loss": initial_loss,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "n_params": n_params,
        "n_train": int(len(X)),
        "forecast_end_value": (
            float(fc_values[-1]) if len(fc_values) else 0.0
        ),
        "last_observed_value": float(clean[-1]),
    }


class NhitsParity(P3ParityCheck):
    """N-HiTS forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.nhits_forecast.run() via
    RunContext at Balanced preset (n_stacks=3 + n_blocks=3 +
    hidden_size=128 + pooling_sizes=[4, 2, 1] + epochs=50 +
    n_lags=16 + lr=0.005 + use_torch=True); reference arm
    reimplements full engine PyTorch primary-path pipeline bespoke
    with SC1 `_prepare_series_reference` + SC16
    `_create_sequences_nbeats` Layer 2 family-shared helper reuse
    (PARTIAL Tier A pattern EIGHTH-INSTANCE per SC10+SC11+SC12+SC13+
    SC14+SC15+SC16 precedent; SC16 reuse-conditionality SECOND-
    OBSERVATION TIGHTENING). Sklearn ensemble fallback NOT validated
    at math layer. SC17 inherits SC13/SC14/SC15/SC16 DL family
    determinism profile + verifies hierarchical-interpolation-
    architecture cross-invocation bit-exact at CPU PyTorch. **SC17
    CLOSES Cat 3 remediation cycle.**
    """

    technique_id = "p3_nhits"
    tier = "slow"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PyTorch N-HiTS (multi-rate MaxPool1d + hierarchical linear "
        "interpolation upsampling + doubly-residual stacking + "
        "3-layer FC blocks + backcast/forecast split) at CPU backend "
        "with torch.manual_seed + deterministic algorithms + cuDNN "
        "deterministic flags is cross-invocation BIT-EXACT (SC17 "
        "Step 2 empirical verification inherits SC13/SC14/SC15/SC16 "
        "DL family determinism profile; confirms hierarchical-"
        "interpolation architecture preserves bit-exact "
        "reproducibility). Engine and reference reimpl follow "
        "identical pipeline (NaN drop via SC1 helper + normalize + "
        "SC16 multi-horizon sequence construction reuse + NHiTSBlock "
        "+ NHiTSStack + NHiTS construction with deterministic linear "
        "layer init order across all stacks + blocks + heads + "
        "per-stack pool_size schedule + MaxPool1d + linear "
        "interpolation align_corners=False + Adam + MSE + grad clip "
        "+ epochs + direct multi-step forecast + denormalization + "
        "metrics); outputs match at machine precision modulo engine "
        "6-decimal forecast rounding + 6-decimal loss + 4-decimal "
        "audit metric rounding. SC17 Tier D.5 hierarchical-"
        "interpolation + bespoke per-session reimpl with PARTIAL "
        "Tier A helper reuse. **CYCLE CLOSE.**"
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.nhits_forecast as nh_mod  # type: ignore

        _setup_dl_determinism(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_nhits_parity",
            "technique_id": "nhits_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = nh_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL nhits_forecast failed: "
                f"{resp.get('error_message')}"
            )
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "pytorch":
            raise RuntimeError(
                f"TSL nhits dispatched to backend='{backend}' "
                f"not 'pytorch'; primary path validation requires "
                f"torch installed"
            )

        # Forecast table
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        audit = resp.get("audit_fields", {})
        return {
            "forecast": forecast,
            "final_loss": float(audit.get("final_loss", float("nan"))),
            "initial_loss": (
                float(audit.get("initial_loss"))
                if audit.get("initial_loss") is not None else None
            ),
            "rmse": float(audit.get("rmse", float("nan"))),
            "mae": float(audit.get("mae", float("nan"))),
            "r2": float(audit.get("r2", float("nan"))),
            "n_params": (
                int(audit.get("n_params"))
                if audit.get("n_params") is not None else None
            ),
            "n_train": int(audit.get("n_train", 0)),
            "forecast_end_value": float(
                audit.get("forecast_end_value", float("nan"))
            ),
            "last_observed_value": float(
                audit.get("last_observed_value", float("nan"))
            ),
            "backend": backend,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        _setup_dl_determinism(42)
        out = _reference_nhits_forecast(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["torch_version"] = torch.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        ref_forecast_rounded = np.round(ref["forecast"], 6)

        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref_forecast_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast"]["status"])

        primary["final_loss"] = _compare_scalar(
            tsl["final_loss"], round(ref["final_loss"], 6),
            ladder["primary"],
        )
        statuses.append(primary["final_loss"]["status"])

        if (tsl["initial_loss"] is not None
                and ref["initial_loss"] is not None):
            primary["initial_loss"] = _compare_scalar(
                tsl["initial_loss"], round(ref["initial_loss"], 6),
                ladder["primary"],
            )
            statuses.append(primary["initial_loss"]["status"])

        primary["rmse"] = _compare_scalar(
            tsl["rmse"], round(ref["rmse"], 4), ladder["primary"],
        )
        statuses.append(primary["rmse"]["status"])

        primary["mae"] = _compare_scalar(
            tsl["mae"], round(ref["mae"], 4), ladder["primary"],
        )
        statuses.append(primary["mae"]["status"])

        primary["r2"] = _compare_scalar(
            tsl["r2"], round(ref["r2"], 4), ladder["primary"],
        )
        statuses.append(primary["r2"]["status"])

        if (tsl["n_params"] is not None
                and ref["n_params"] is not None):
            primary["n_params"] = {
                "status": (
                    "PASS" if tsl["n_params"] == ref["n_params"]
                    else "BLOCK"
                ),
                "tsl": int(tsl["n_params"]),
                "ref": int(ref["n_params"]),
            }
            statuses.append(primary["n_params"]["status"])

        primary["n_train"] = {
            "status": (
                "PASS" if tsl["n_train"] == ref["n_train"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_train"]),
            "ref": int(ref["n_train"]),
        }
        statuses.append(primary["n_train"]["status"])

        primary["forecast_end_value"] = _compare_scalar(
            tsl["forecast_end_value"],
            round(ref["forecast_end_value"], 6),
            ladder["primary"],
        )
        statuses.append(primary["forecast_end_value"]["status"])

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
                "backend": str(tsl.get("backend", "?")),
                "n_stacks": int(_ENGINE_BALANCED_PRESET["n_stacks"]),
                "n_blocks": int(_ENGINE_BALANCED_PRESET["n_blocks"]),
                "hidden_size": int(
                    _ENGINE_BALANCED_PRESET["hidden_size"]
                ),
                "pooling_sizes": list(
                    _ENGINE_BALANCED_PRESET["pooling_sizes"]
                ),
                "epochs": int(_ENGINE_BALANCED_PRESET["epochs"]),
                "n_lags": int(_ENGINE_BALANCED_PRESET["n_lags"]),
                "lr": float(_ENGINE_BALANCED_PRESET["lr"]),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
