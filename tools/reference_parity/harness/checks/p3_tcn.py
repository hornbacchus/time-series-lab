"""Phase 3 Batch 9 — TCN (Temporal Convolutional Network) forecast
parity check.

TSL ``engine/techniques/tcn_forecast.py`` (PyTorch dilated causal
convolutional network with residual blocks per Bai-Kolter-Koltun 2018
"An Empirical Evaluation of Generic Convolutional and Recurrent
Networks for Sequence Modeling" arXiv:1803.01271 + Adam optimizer +
MSE loss + sliding-window sequence construction at n_lags + recursive
multi-step forecast + sklearn MLPRegressor fallback when PyTorch
unavailable) vs from-scratch paper-formula reimpl mirroring engine
PyTorch primary path verbatim.

Rewritten at SC15-side Cat 3 remediation cycle session 15/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC15 = Tier D.3** (third PyTorch-based
DL family session; first convolutional architecture after SC13
feed-forward MLP autoencoder + SC14 recurrent LSTM/GRU). PARTIAL
Tier A pattern SIXTH-INSTANCE confirmation + Tier D DL family
determinism profile inheritance from SC13/SC14 (convolutional
architecture cross-invocation bit-exact at CPU PyTorch verified at
Step 2 — extends feed-forward + recurrent → convolutional
generalization).

**Helper identity verification (Step 1 of SC15 workflow per SC4
two-stage methodology + SC10-SC14 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 43-63: **MATCH SC1 RF**
  `_prepare_series_reference` verbatim (strip-edge-NaN + interp-
  interior body identical modulo function-name token only).
- `_create_sequences` at engine lines 66-72: **MATCH SC14 p3_lstm_gru**
  `_create_sequences_reference` verbatim (sliding-window 2D output
  body identical; TCN engine path applies `.unsqueeze(1)` AFTER to
  reshape to conv-expected (batch, channels=1, seq_len)).
- `_create_lag_features` at engine lines 75-82: **ABSENT** (only
  exercised in sklearn MLP fallback path; PyTorch primary path uses
  `_create_sequences` exclusively).

Stage 2: ABSENT helpers indicate fallback-only feature path; primary
path uses shared sequence builder. PARTIAL Tier A pattern SIXTH-
INSTANCE confirmation at sustained n=6 cumulative observations
(SC10 GP + SC11 prophet + SC12 esn + SC13 autoencoder + SC14
lstm_gru + SC15 tcn); A3 fourth-observation-tightening threshold
satisfied n=2-fold; codification candidate at absorption #6+ for
"PARTIAL Tier A pattern as sklearn/PyTorch/Stan-backbone sub-cohort
convention" EMPIRICALLY ROBUSTLY GROUNDED. Cross-architectural
generalization confirmed Tier-agnostic + architecture-type-agnostic
within DL family (feed-forward + recurrent + convolutional all
exhibit PARTIAL Tier A pattern under shared determinism profile).

**Cross-invocation reproducibility verification (Step 2 — inherits
SC13/SC14 DL family determinism profile + convolutional-architecture
verification):** Inherited determinism configuration applied:
`torch.manual_seed(seed) + torch.cuda.manual_seed_all(seed)` if
CUDA + `torch.use_deterministic_algorithms(True, warn_only=True)`
+ `torch.backends.cudnn.deterministic = True` +
`torch.backends.cudnn.benchmark = False`. Engine invoked TWICE as
separate Python computations at seed=42 → **max_abs_diff=0.0
(BIT-EXACT cross-invocation)** at CPU PyTorch TCN (Balanced preset
default n_channels=[32, 32] + kernel_size=3). **CONFIRMS SC13/SC14
DL determinism profile holds for convolutional architectures**
(stacked dilated conv layer weight init order deterministic at fixed
seed; ResidualBlock construction sequence deterministic;
downsample 1x1 conv conditional construction deterministic).

**Tier D convolutional-specific parity risks (resolved via Step 2):**
- Conv layer weight init order: engine `_build_tcn_model` constructs
  blocks in deterministic order — for each level i in 0..num_levels:
  ResidualBlock(in_ch, out_ch, kernel_size, dilation=2**i) where
  in_ch=input_size if i==0 else n_channels[i-1] and out_ch=
  n_channels[i]. Within each block: conv1 (CausalConv1d in→out) then
  conv2 (CausalConv1d out→out) then downsample (nn.Conv1d in→out 1x1
  ONLY IF in_ch != out_ch). Reference reimpl constructs in identical
  order — RNG consumption order-preserving.
- Dilation factor handling: engine uses dilation=2**i (exponential
  growth). For Balanced (n_channels=[32,32]) dilations are [1, 2].
  Padding `(kernel_size-1)*dilation` then right-crop
  `out[:, :, :-padding]` enforces causal convolution. Reference
  reimpl applies identical formula.
- Residual connection init: engine `ResidualBlock.forward` computes
  `residual = x if downsample is None else downsample(x)` then
  `relu(out + residual)`. Reference reimpl applies identical
  residual wiring.
- Receptive field: engine formula
  `sum((k-1) * 2**i for i in range(len(n_channels))) + 1`. For
  Balanced (k=3, levels=2): 2*1 + 2*2 + 1 = 7. Reference matches.
- Dropout in eval mode: engine + reference both call `model.eval()`
  before in-sample predictions + forecast generation; dropout
  becomes identity.
- cuDNN convolution non-determinism: NOT exercised at audit
  environment (torch 2.11.0+cpu); CPU conv ops deterministic.

**Fallback dispatch handling (SC3 template element SEVENTH-INSTANCE
application):** Engine `_has_torch()` at lines 19-24 + preset flag
`use_torch` at engine line 252 dispatches to PyTorch TCN primary path
when torch available + preset enables; sklearn `MLPRegressor`
fallback via lines 305-340 when torch unavailable (Fast preset uses
sklearn by default per engine line 30 `use_torch: False`).

**Mathematical equivalence assessment (primary vs fallback):
CATEGORICALLY DIFFERENT.** PyTorch TCN (dilated causal convolutional
network with residual blocks; receptive field grows exponentially
with depth) vs sklearn MLPRegressor (feed-forward multi-layer
perceptron with lag features). Outputs are NOT numerically
equivalent — fundamentally different architectures with different
inductive biases.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor at CPU PyTorch backend per SC13 + SC14 + SC15
determinism profile).
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
    _create_sequences_reference,
    _setup_dl_determinism,
    _generate_ar_dgp,
)


# Engine preset Balanced config (engine `tcn_forecast.py` lines
# 32-35). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "n_channels": [32, 32],
    "kernel_size": 3,
    "epochs": 100,
    "n_lags": 16,
    "lr": 0.005,
    "use_torch": True,
}


def _reference_tcn_forecast(
    values: np.ndarray, *, seed: int, horizon: int = 10,
    preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `tcn_forecast.run()` primary
    PyTorch path at engine lines 261-294 verbatim including
    `_train_torch_tcn` at engine lines 141-167 (CausalConv1d +
    ResidualBlock + TCN classes + Adam + MSE + epochs training loop)
    + `_predict_torch_tcn` at engine lines 170-185 (recursive
    multi-step forecast with (1, 1, n_lags) input shape) + engine
    receptive-field formula at line 293.

    Construction order RNG-determinism: levels 0..N constructed in
    order; within each level: CausalConv1d(in→out, dil) then
    CausalConv1d(out→out, dil) then (conditional) downsample
    nn.Conv1d(in→out, 1). Mirrors engine `_build_tcn_model` exactly.
    """
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # SC1 helper reuse (PARTIAL Tier A sixth-instance)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    n_channels = list(cfg["n_channels"])
    kernel_size = int(cfg["kernel_size"])
    epochs = int(cfg["epochs"])
    n_lags = int(cfg["n_lags"])
    lr = float(cfg["lr"])

    # Cap n_lags per engine line 243
    n_lags = min(n_lags, n // 3)

    # Normalize per engine lines 246-250
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Create sequences per engine line 263 (SC14 helper reuse —
    # 2D output as engine expects, before `.unsqueeze(1)` to add
    # channel dim).
    X, y = _create_sequences_reference(normalized, n_lags)

    # ===== _train_torch_tcn reimpl per engine lines 141-167 =====
    torch.manual_seed(seed)

    class CausalConv1d(nn.Module):
        """Mirrors engine `_build_tcn_model.CausalConv1d` lines
        90-103 verbatim."""
        def __init__(self, in_ch, out_ch, kernel_size, dilation):
            super().__init__()
            self.padding = (kernel_size - 1) * dilation
            self.conv = nn.Conv1d(
                in_ch, out_ch, kernel_size,
                padding=self.padding, dilation=dilation,
            )
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.1)

        def forward(self, x):
            out = self.conv(x)
            if self.padding > 0:
                out = out[:, :, :-self.padding]
            return self.dropout(self.relu(out))

    class ResidualBlock(nn.Module):
        """Mirrors engine `_build_tcn_model.ResidualBlock` lines
        105-117 verbatim. Construction order: conv1 → conv2 →
        downsample (conditional) — RNG-draw-order-preserving."""
        def __init__(self, in_ch, out_ch, kernel_size, dilation):
            super().__init__()
            self.conv1 = CausalConv1d(
                in_ch, out_ch, kernel_size, dilation,
            )
            self.conv2 = CausalConv1d(
                out_ch, out_ch, kernel_size, dilation,
            )
            self.downsample = (
                nn.Conv1d(in_ch, out_ch, 1)
                if in_ch != out_ch else None
            )
            self.relu = nn.ReLU()

        def forward(self, x):
            residual = (
                x if self.downsample is None else self.downsample(x)
            )
            out = self.conv1(x)
            out = self.conv2(out)
            return self.relu(out + residual)

    class TCN(nn.Module):
        """Mirrors engine `_build_tcn_model.TCN` lines 119-136
        verbatim. Constructs ResidualBlocks in level order with
        dilation=2**i — RNG-draw-order-preserving across all levels.
        """
        def __init__(self, input_size, n_channels, kernel_size):
            super().__init__()
            layers = []
            num_levels = len(n_channels)
            for i in range(num_levels):
                dilation = 2 ** i
                in_ch = input_size if i == 0 else n_channels[i - 1]
                out_ch = n_channels[i]
                layers.append(
                    ResidualBlock(in_ch, out_ch, kernel_size, dilation),
                )
            self.network = nn.Sequential(*layers)
            self.fc = nn.Linear(n_channels[-1], 1)

        def forward(self, x):
            # x: (batch, channels, seq_len)
            out = self.network(x)
            # Take the last time step
            return self.fc(out[:, :, -1]).squeeze(-1)

    # Engine `_train_torch_tcn` line 149: X.unsqueeze(1) to add
    # channel dim → (n_samples, 1, seq_len).
    X_tensor = torch.FloatTensor(X).unsqueeze(1)
    y_tensor = torch.FloatTensor(y)

    # Engine `_build_tcn_model(1, n_channels, kernel_size, X.shape[1])`
    # at line 152 — input_size=1 (single channel).
    model = TCN(1, n_channels, kernel_size)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for _epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(X_tensor)
        loss = loss_fn(pred, y_tensor)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    final_loss = losses[-1] if losses else float("inf")
    initial_loss = losses[0] if losses else None

    # Parameter count per engine lines 277-280
    try:
        n_params = int(sum(p.numel() for p in model.parameters()))
    except Exception:
        n_params = None

    # Recursive forecast per engine lines 283-284 + _predict_torch_tcn
    # (lines 170-185). Input shape (1, 1, n_lags) via
    # `seq.unsqueeze(0).unsqueeze(0)` — last_seq is 1D length n_lags.
    last_seq = normalized[-n_lags:].copy()
    forecasts = []
    with torch.no_grad():
        for _ in range(horizon):
            x = torch.FloatTensor(last_seq).unsqueeze(0).unsqueeze(0)
            pred = float(model(x).item())
            forecasts.append(pred)
            last_seq = np.append(last_seq[1:], pred)
    fc_norm = np.array(forecasts)

    # In-sample predictions per engine lines 287-291
    with torch.no_grad():
        X_full = torch.FloatTensor(X).unsqueeze(1)
        y_pred_norm = model(X_full).numpy()

    # Denormalize per engine lines 343-345
    fc_values = fc_norm * y_std + y_mean
    y_actual = y * y_std + y_mean
    y_pred = y_pred_norm * y_std + y_mean

    # Metrics per engine lines 348-351
    residuals = y_actual - y_pred
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    mae = float(np.mean(np.abs(residuals)))
    ss_res = float(np.sum(residuals ** 2))
    ss_tot = float(np.sum((y_actual - np.mean(y_actual)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

    # Receptive field per engine line 293
    receptive_field = sum(
        (kernel_size - 1) * 2 ** i for i in range(len(n_channels))
    ) + 1

    return {
        "forecast": fc_values.astype(np.float64),
        "final_loss": final_loss,
        "initial_loss": initial_loss,
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "n_params": n_params,
        "n_train": int(len(X)),
        "receptive_field": int(receptive_field),
        "forecast_end_value": (
            float(fc_values[-1]) if len(fc_values) else 0.0
        ),
        "last_observed_value": float(clean[-1]),
    }


class TcnParity(P3ParityCheck):
    """TCN forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.tcn_forecast.run() via
    RunContext at Balanced preset (n_channels=[32, 32] + kernel_size=3
    + epochs=100 + n_lags=16 + lr=0.005 + use_torch=True); reference
    arm reimplements full engine PyTorch primary-path pipeline
    bespoke with SC1 `_prepare_series_reference` + SC14
    `_create_sequences_reference` Layer 2 family-shared helper reuse
    (PARTIAL Tier A pattern SIXTH-INSTANCE per SC10+SC11+SC12+SC13+
    SC14 precedent). Sklearn MLP fallback NOT validated at math
    layer. SC15 inherits SC13/SC14 DL family determinism profile +
    verifies convolutional-architecture cross-invocation bit-exact
    at CPU PyTorch.
    """

    technique_id = "p3_tcn"
    tier = "slow"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PyTorch TCN (dilated causal convolutions + residual blocks) "
        "at CPU backend with torch.manual_seed + deterministic "
        "algorithms + cuDNN deterministic flags is cross-invocation "
        "BIT-EXACT (SC15 Step 2 empirical verification inherits "
        "SC13/SC14 DL family determinism profile; confirms "
        "convolutional architecture preserves bit-exact "
        "reproducibility). Engine and reference reimpl follow "
        "identical pipeline (NaN drop via SC1 helper + normalize + "
        "sequence construction via SC14 helper + CausalConv1d + "
        "ResidualBlock + TCN construction with deterministic conv "
        "weight init order across blocks + Adam + MSE + epochs + "
        "recursive multi-step forecast + denormalization + metrics); "
        "outputs match at machine precision modulo engine 6-decimal "
        "forecast rounding + 6-decimal loss + 4-decimal audit metric "
        "rounding. SC15 Tier D.3 convolutional + bespoke per-session "
        "reimpl with PARTIAL Tier A helper reuse."
    )

    DGP_N = 200
    HORIZON = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.tcn_forecast as tcn_mod  # type: ignore

        _setup_dl_determinism(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_tcn_parity",
            "technique_id": "tcn_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = tcn_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL tcn_forecast failed: "
                f"{resp.get('error_message')}"
            )
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "pytorch":
            raise RuntimeError(
                f"TSL tcn dispatched to backend='{backend}' "
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
            "receptive_field": int(audit.get("receptive_field", 0)),
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
        out = _reference_tcn_forecast(
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

        primary["receptive_field"] = {
            "status": (
                "PASS" if tsl["receptive_field"] == ref["receptive_field"]
                else "BLOCK"
            ),
            "tsl": int(tsl["receptive_field"]),
            "ref": int(ref["receptive_field"]),
        }
        statuses.append(primary["receptive_field"]["status"])

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
                "n_channels": list(_ENGINE_BALANCED_PRESET["n_channels"]),
                "kernel_size": int(_ENGINE_BALANCED_PRESET["kernel_size"]),
                "epochs": int(_ENGINE_BALANCED_PRESET["epochs"]),
                "n_lags": int(_ENGINE_BALANCED_PRESET["n_lags"]),
                "lr": float(_ENGINE_BALANCED_PRESET["lr"]),
                "receptive_field": int(tsl.get("receptive_field", 0)),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
