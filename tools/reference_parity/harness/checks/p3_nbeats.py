"""Phase 3 Batch 9 — N-BEATS (Neural Basis Expansion Analysis)
forecast parity check.

TSL ``engine/techniques/nbeats_forecast.py`` (PyTorch N-BEATS per
Oreshkin et al. 2019 "N-BEATS: Neural Basis Expansion Analysis for
Interpretable Time Series Forecasting" arXiv:1905.10437 with doubly-
residual stacking + 4-layer fully-connected blocks producing
backcast + forecast via theta projections + Adam optimizer + MSE
loss + gradient clipping + sliding-window sequence construction at
n_lags + direct multi-step (horizon-step) forecast + sklearn
ensemble fallback (Ridge + GBR + MLP) when PyTorch unavailable) vs
from-scratch paper-formula reimpl mirroring engine PyTorch primary
path verbatim.

Rewritten at SC16-side Cat 3 remediation cycle session 16/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC16 = Tier D.4** (fourth PyTorch-based
DL family session; first basis-expansion architecture after SC13
feed-forward MLP autoencoder + SC14 recurrent LSTM/GRU + SC15
convolutional TCN). PARTIAL Tier A pattern SEVENTH-INSTANCE
confirmation + Tier D DL family determinism profile inheritance
from SC13/SC14/SC15 (basis-expansion architecture cross-invocation
bit-exact at CPU PyTorch verified at Step 2 — extends feed-forward
+ recurrent + convolutional → basis-expansion generalization).

**Helper identity verification (Step 1 of SC16 workflow per SC4
two-stage methodology + SC10-SC15 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 47-66: **MATCH SC1 RF**
  `_prepare_series_reference` verbatim (strip-edge-NaN + interp-
  interior body identical modulo function-name token only).
- `_create_sequences` at engine lines 69-75: **MISMATCH SC14
  p3_lstm_gru** `_create_sequences_reference` — NBEATS signature
  `(data, lookback, horizon)` returns y of shape (n_samples,
  horizon) (horizon-step targets, direct multi-step prediction);
  SC14 signature `(data, seq_len)` returns y of shape (n_samples,)
  (1-step target, recursive multi-step prediction). DL-family-
  shared sequence helper pattern does NOT extend to basis-expansion
  architecture due to direct-multi-step vs recursive-multi-step
  architectural divergence. **Bespoke NBEATS-specific
  `_create_sequences_nbeats` reimpl required per-session.**
- `_create_lag_features` at engine lines 78-84: **ABSENT** (only
  exercised in sklearn ensemble fallback path; PyTorch primary
  path uses `_create_sequences` exclusively).

Stage 2: PARTIAL Tier A pattern SEVENTH-INSTANCE confirmation at
sustained n=7 cumulative observations (SC10 GP + SC11 prophet +
SC12 esn + SC13 autoencoder + SC14 lstm_gru + SC15 tcn + SC16
nbeats); A3 fourth-observation-tightening threshold satisfied
n=4-fold; **architecture-type-agnostic generalization SUSTAINED
across FOUR distinct DL architecture types** (feed-forward +
recurrent + convolutional + basis-expansion all exhibit PARTIAL
Tier A pattern under shared determinism profile). DL-family-
shared `_create_sequences` reuse pattern observed n=1 at SC15 tcn
(SC14→SC15 sustained); SC16 nbeats demonstrates that windowing-
helper reuse is architecture-type-conditional, not universal
within DL family — direct-multi-step architectures (NBEATS,
likely NHITS) require bespoke variant due to multi-horizon target
output shape.

**Cross-invocation reproducibility verification (Step 2 — inherits
SC13/SC14/SC15 DL family determinism profile + basis-expansion-
architecture verification):** Inherited determinism configuration
applied: `torch.manual_seed(seed) + torch.cuda.manual_seed_all(seed)`
if CUDA + `torch.use_deterministic_algorithms(True, warn_only=True)`
+ `torch.backends.cudnn.deterministic = True` +
`torch.backends.cudnn.benchmark = False`. Engine invoked TWICE as
separate Python computations at seed=42 → **max_abs_diff=0.0
(BIT-EXACT cross-invocation)** at CPU PyTorch NBEATS (Balanced
preset default n_stacks=2 + n_blocks=3 + hidden_size=128 +
theta_size=32). **CONFIRMS SC13/SC14/SC15 DL determinism profile
holds for basis-expansion architectures** (doubly-residual stack
composition deterministic at fixed seed; block stacking init order
deterministic; theta projection init deterministic; backcast/
forecast head split init deterministic).

**Tier D basis-expansion-architecture-specific parity risks (resolved
via Step 2):**
- Stack stacking order: engine `NBEATS` constructs
  `nn.ModuleList([NBEATSStack(...) for _ in range(n_stacks)])`
  where n_stacks=len(stack_types). For Balanced (stack_types=
  ["generic", "generic"]) constructs 2 stacks. Reference reimpl
  constructs in identical order.
- Block stacking within stack: engine `NBEATSStack` constructs
  `nn.ModuleList([NBEATSBlock(input_size, hidden, theta, theta)
  for _ in range(n_blocks)])`. For Balanced n_blocks=3, each stack
  contains 3 blocks. Reference matches exactly.
- Block FC init order: engine `NBEATSBlock` constructs `fc =
  nn.Sequential(Linear(input_size, hidden), ReLU, Linear(hidden,
  hidden), ReLU, Linear(hidden, hidden), ReLU, Linear(hidden,
  hidden), ReLU)` — 4-layer FC tower. Reference matches.
- Theta projection init order: within each block, `theta_b =
  Linear(hidden, theta_b_size, bias=False)` then `theta_f =
  Linear(hidden, theta_f_size, bias=False)` then `backcast_fc =
  Linear(theta_b_size, input_size)` then `forecast_fc =
  Linear(theta_f_size, horizon)`. Construction-order RNG-draw-
  preserving.
- Doubly-residual stacking: engine `NBEATSStack.forward` computes
  `residual = x; stack_forecast = 0; for block in blocks: backcast,
  forecast = block(residual); residual = residual - backcast;
  stack_forecast += forecast`. Engine `NBEATS.forward` computes
  `residual = x; total = 0; for stack in stacks: residual,
  forecast = stack(residual); total += forecast`. Reference
  implements identical residual subtraction wiring.
- Gradient clipping: engine applies
  `torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)` after
  `loss.backward()` and before `optimizer.step()`. Reference
  applies identical clip in identical order.
- "Generic" basis observation: ALL stack_types ("generic" / "trend"
  / "seasonality") instantiate identical `NBEATSBlock` architecture
  — engine implementation does NOT differentiate basis function
  initialization or basis structure across stack_types. Only the
  COUNT (`len(stack_types)`) matters; stack_types semantic content
  is recorded in audit_fields but not used in engine math.
  Document at §2.5 entry.
- cuDNN non-determinism: NOT exercised at audit environment (torch
  2.11.0+cpu); CPU FC ops deterministic.

**Fallback dispatch handling (SC3 template element EIGHTH-INSTANCE
application):** Engine `_has_torch()` at lines 20-25 + preset flag
`use_torch` at engine line 353 dispatches to PyTorch NBEATS primary
path when torch available + preset enables; sklearn ENSEMBLE
fallback (Ridge + GradientBoostingRegressor + MLPRegressor averaged
via `_train_sklearn_ensemble` at lines 198-229 + `_predict_sklearn_
ensemble` at lines 232-245) when torch unavailable (Fast preset
uses sklearn ensemble by default per engine line 32
`use_torch: False`).

**Mathematical equivalence assessment (primary vs fallback):
CATEGORICALLY DIFFERENT.** PyTorch NBEATS (basis-expansion
architecture with doubly-residual stacking + direct multi-step
forecast) vs sklearn ensemble of {Ridge linear model, gradient-
boosted tree ensemble, MLP feed-forward network} averaged via mean
(recursive single-step forecast). Outputs are NOT numerically
equivalent — fundamentally different architectures + different
ensembling + different forecast generation mode.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor at CPU PyTorch backend per SC13 + SC14 +
SC15 + SC16 determinism profile).
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


# Engine preset Balanced config (engine `nbeats_forecast.py` lines
# 35-38). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "stack_types": ["generic", "generic"],
    "n_blocks": 3,
    "hidden_size": 128,
    "theta_size": 32,
    "epochs": 150,
    "n_lags": 16,
    "lr": 0.005,
    "use_torch": True,
}


def _create_sequences_nbeats(
    data: np.ndarray, lookback: int, horizon: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Reference reimpl of engine `_create_sequences` lines 69-75.
    NBEATS uses horizon-step direct-multi-step targets — distinct
    from SC14 p3_lstm_gru's `_create_sequences_reference` 1-step
    recursive-multi-step variant. Bespoke per-session helper.
    """
    X, y = [], []
    for i in range(len(data) - lookback - horizon + 1):
        X.append(data[i:i + lookback])
        y.append(data[i + lookback:i + lookback + horizon])
    return np.array(X), np.array(y)


def _reference_nbeats_forecast(
    values: np.ndarray, *, seed: int, horizon: int = 10,
    preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `nbeats_forecast.run()`
    primary PyTorch path at engine lines 362-398 verbatim including
    `_train_torch_nbeats` at engine lines 153-183 (NBEATSBlock +
    NBEATSStack + NBEATS classes + Adam + MSE + grad clip + epochs
    training loop) + `_predict_torch_nbeats` at engine lines 186-195
    (direct multi-step forecast — single forward pass returns full
    horizon).

    Construction order RNG-determinism: stacks 0..n_stacks
    constructed in order; within each stack, blocks 0..n_blocks
    constructed in order; within each block: fc Sequential (L1, L2,
    L3, L4 with intervening ReLU) then theta_b (no bias) then
    theta_f (no bias) then backcast_fc then forecast_fc. Mirrors
    engine `_build_nbeats_model` exactly.
    """
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # SC1 helper reuse (PARTIAL Tier A seventh-instance)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    stack_types = list(cfg["stack_types"])
    n_blocks = int(cfg["n_blocks"])
    hidden_size = int(cfg["hidden_size"])
    theta_size = int(cfg["theta_size"])
    epochs = int(cfg["epochs"])
    n_lags = int(cfg["n_lags"])
    lr = float(cfg["lr"])

    # Cap n_lags per engine line 344
    n_lags = min(n_lags, n // 3)

    # Normalize per engine lines 347-351
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Create sequences per engine line 364 (NBEATS-specific multi-
    # horizon target).
    X, y_seq = _create_sequences_nbeats(normalized, n_lags, horizon)

    # ===== _train_torch_nbeats reimpl per engine lines 153-183 =====
    torch.manual_seed(seed)
    lookback = X.shape[1]

    class NBEATSBlock(nn.Module):
        """Mirrors engine `_build_nbeats_model.NBEATSBlock` lines
        92-114 verbatim."""
        def __init__(self, input_size, hidden_size, theta_b_size,
                     theta_f_size):
            super().__init__()
            self.fc = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
            )
            self.theta_b = nn.Linear(
                hidden_size, theta_b_size, bias=False,
            )
            self.theta_f = nn.Linear(
                hidden_size, theta_f_size, bias=False,
            )
            self.backcast_fc = nn.Linear(theta_b_size, input_size)
            self.forecast_fc = nn.Linear(theta_f_size, horizon)

        def forward(self, x):
            h = self.fc(x)
            backcast = self.backcast_fc(self.theta_b(h))
            forecast = self.forecast_fc(self.theta_f(h))
            return backcast, forecast

    class NBEATSStack(nn.Module):
        """Mirrors engine `_build_nbeats_model.NBEATSStack` lines
        116-131 verbatim. Doubly-residual stacking via
        `residual = residual - backcast` accumulation."""
        def __init__(self, input_size, n_blocks, hidden_size,
                     theta_size):
            super().__init__()
            self.blocks = nn.ModuleList([
                NBEATSBlock(
                    input_size, hidden_size, theta_size, theta_size,
                )
                for _ in range(n_blocks)
            ])

        def forward(self, x):
            residual = x
            stack_forecast = 0
            for block in self.blocks:
                backcast, forecast = block(residual)
                residual = residual - backcast
                stack_forecast = stack_forecast + forecast
            return residual, stack_forecast

    class NBEATS(nn.Module):
        """Mirrors engine `_build_nbeats_model.NBEATS` lines 133-147
        verbatim. Outer doubly-residual stacking across stacks."""
        def __init__(self, input_size, n_stacks, n_blocks,
                     hidden_size, theta_size):
            super().__init__()
            self.stacks = nn.ModuleList([
                NBEATSStack(
                    input_size, n_blocks, hidden_size, theta_size,
                )
                for _ in range(n_stacks)
            ])

        def forward(self, x):
            residual = x
            total_forecast = 0
            for stack in self.stacks:
                residual, forecast = stack(residual)
                total_forecast = total_forecast + forecast
            return total_forecast

    n_stacks = len(stack_types)
    model = NBEATS(
        lookback, n_stacks, n_blocks, hidden_size, theta_size,
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

    # Parameter count per engine line 394
    try:
        n_params = int(sum(p.numel() for p in model.parameters()))
    except Exception:
        n_params = None

    # Direct multi-step forecast per engine lines 380-381 +
    # _predict_torch_nbeats (lines 186-195). Input shape (1,
    # n_lags) via `last_sequence.unsqueeze(0)`.
    last_seq = normalized[-n_lags:].copy()
    with torch.no_grad():
        x = torch.FloatTensor(last_seq).unsqueeze(0)
        fc_norm = model(x).squeeze(0).numpy()[:horizon]

    # In-sample predictions per engine lines 384-392 (first-step
    # only for in-sample metric).
    with torch.no_grad():
        X_full = torch.FloatTensor(X)
        y_pred_all = model(X_full).numpy()
    y_pred_norm = y_pred_all[:, 0]
    y_actual_norm = y_seq[:, 0]

    # Denormalize per engine lines 436-438
    fc_values = fc_norm * y_std + y_mean
    y_actual = y_actual_norm * y_std + y_mean
    y_pred = y_pred_norm * y_std + y_mean

    # Metrics per engine lines 441-446
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


class NbeatsParity(P3ParityCheck):
    """N-BEATS forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.nbeats_forecast.run() via
    RunContext at Balanced preset (stack_types=["generic", "generic"]
    + n_blocks=3 + hidden_size=128 + theta_size=32 + epochs=150 +
    n_lags=16 + lr=0.005 + use_torch=True); reference arm
    reimplements full engine PyTorch primary-path pipeline bespoke
    with SC1 `_prepare_series_reference` Layer 2 family-shared
    helper reuse (PARTIAL Tier A pattern SEVENTH-INSTANCE per
    SC10+SC11+SC12+SC13+SC14+SC15 precedent) + bespoke
    `_create_sequences_nbeats` (NBEATS multi-horizon variant).
    Sklearn ensemble fallback NOT validated at math layer. SC16
    inherits SC13/SC14/SC15 DL family determinism profile + verifies
    basis-expansion-architecture cross-invocation bit-exact at CPU
    PyTorch.
    """

    technique_id = "p3_nbeats"
    tier = "slow"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PyTorch N-BEATS (doubly-residual stacking + 4-layer FC "
        "blocks + theta projections + backcast/forecast split) at "
        "CPU backend with torch.manual_seed + deterministic "
        "algorithms + cuDNN deterministic flags is cross-invocation "
        "BIT-EXACT (SC16 Step 2 empirical verification inherits "
        "SC13/SC14/SC15 DL family determinism profile; confirms "
        "basis-expansion architecture preserves bit-exact "
        "reproducibility). Engine and reference reimpl follow "
        "identical pipeline (NaN drop via SC1 helper + normalize + "
        "NBEATS-specific multi-horizon sequence construction + "
        "NBEATSBlock + NBEATSStack + NBEATS construction with "
        "deterministic linear layer init order across all stacks + "
        "blocks + theta projections + backcast/forecast heads + "
        "Adam + MSE + grad clip + epochs + direct multi-step "
        "forecast + denormalization + metrics); outputs match at "
        "machine precision modulo engine 6-decimal forecast "
        "rounding + 6-decimal loss + 4-decimal audit metric "
        "rounding. SC16 Tier D.4 basis-expansion + bespoke per-"
        "session reimpl with PARTIAL Tier A helper reuse."
    )

    DGP_N = 200
    HORIZON = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.nbeats_forecast as nb_mod  # type: ignore

        _setup_dl_determinism(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_nbeats_parity",
            "technique_id": "nbeats_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = nb_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL nbeats_forecast failed: "
                f"{resp.get('error_message')}"
            )
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "pytorch":
            raise RuntimeError(
                f"TSL nbeats dispatched to backend='{backend}' "
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
        out = _reference_nbeats_forecast(
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
                "stack_types": list(
                    _ENGINE_BALANCED_PRESET["stack_types"]
                ),
                "n_blocks": int(_ENGINE_BALANCED_PRESET["n_blocks"]),
                "hidden_size": int(
                    _ENGINE_BALANCED_PRESET["hidden_size"]
                ),
                "theta_size": int(
                    _ENGINE_BALANCED_PRESET["theta_size"]
                ),
                "epochs": int(_ENGINE_BALANCED_PRESET["epochs"]),
                "n_lags": int(_ENGINE_BALANCED_PRESET["n_lags"]),
                "lr": float(_ENGINE_BALANCED_PRESET["lr"]),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
