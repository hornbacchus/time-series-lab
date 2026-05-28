"""Phase 3 Batch 9 — LSTM/GRU forecast parity check.

TSL ``engine/techniques/lstm_gru_forecast.py`` (PyTorch nn.LSTM or
nn.GRU with batch_first=True + Linear readout layer + Adam optimizer
+ MSE loss + sliding-window sequence construction at n_lags +
recursive multi-step forecast + sklearn MLPRegressor fallback when
PyTorch unavailable) vs from-scratch paper-formula reimpl mirroring
engine PyTorch primary path verbatim.

Rewritten at SC14-side Cat 3 remediation cycle session 14/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC14 = Tier D.2** (second PyTorch-
based DL family session). PARTIAL Tier A pattern FIFTH-INSTANCE
confirmation + Tier D DL family determinism profile inheritance
from SC13 (recurrent architecture cross-invocation bit-exact at
CPU PyTorch verified at Step 2).

**Helper identity verification (Step 1 of SC14 workflow per SC4
two-stage methodology + SC10-SC13 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 43-63: **MATCH SC1 RF** (hash
  57bae54d463c2fd7)
- `_create_features`: **ABSENT**
- `_create_forecast_features`: **ABSENT**

Stage 2: ABSENT helpers indicate architectural distinctness
(recurrent network pipeline distinct from tree-family). PARTIAL
Tier A pattern FIFTH-INSTANCE confirmation per SC10-SC13 sustained
pattern; codification candidate at absorption #6+ for "PARTIAL
Tier A pattern as sklearn/PyTorch/Stan-backbone sub-cohort
convention" EMPIRICALLY ROBUSTLY GROUNDED.

**Cross-invocation reproducibility verification (Step 2 — inherits
SC13 DL family determinism profile + recurrent-architecture
verification):** Inherited determinism configuration applied:
`torch.manual_seed(seed) + torch.cuda.manual_seed_all(seed)` if
CUDA + `torch.use_deterministic_algorithms(True, warn_only=True)`
+ `torch.backends.cudnn.deterministic = True` +
`torch.backends.cudnn.benchmark = False`. Engine invoked TWICE as
separate Python computations at seed=42 → **max_abs_diff=0.0
(BIT-EXACT cross-invocation)** at CPU PyTorch LSTM (model_type=
"lstm" Balanced preset default). **CONFIRMS SC13 DL determinism
profile holds for recurrent architectures** (hidden state init +
recurrent state evolution + gate weight init deterministic at
fixed seed).

**Tier D recurrent-specific parity risks (resolved via Step 2):**
- Hidden state init (h0, c0 for LSTM): engine relies on PyTorch
  default zero init (no explicit h0/c0 in forward); reference uses
  same convention. Bit-exact.
- Gate weight init order (LSTM has 4 gates input/forget/cell/
  output; GRU has 3 reset/update/new): PyTorch nn.LSTM/nn.GRU
  consume RNG in deterministic order during construction. Both
  arms construct identical layers in identical order.
- Dropout in eval mode: engine + reference both call `model.eval()`
  before in-sample predictions + forecast generation.
- cuDNN recurrent non-determinism: NOT exercised at audit
  environment (torch 2.11.0+cpu); CPU recurrent ops deterministic.

**Fallback dispatch handling (SC3 template element SIXTH-INSTANCE
application):** Engine `_has_torch()` at lines 19-24 + preset flag
`use_torch` at engine line 272 dispatches to PyTorch LSTM/GRU
primary path when torch available + preset enables; sklearn
`MLPRegressor` fallback via `_train_sklearn_mlp` at engine lines
157-171 when torch unavailable (Fast preset uses sklearn by
default per engine line 30 `use_torch: False`).

**Mathematical equivalence assessment (primary vs fallback):
CATEGORICALLY DIFFERENT.** PyTorch LSTM/GRU (recurrent neural
network with gated memory cells) vs sklearn MLPRegressor (feed-
forward multi-layer perceptron with lag features). Outputs are NOT
numerically equivalent — fundamentally different architectures.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor at CPU PyTorch backend per SC13 + SC14
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


# Engine preset Balanced config (engine `lstm_gru_forecast.py` lines
# 32-35). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "hidden_size": 64,
    "n_layers": 2,
    "epochs": 100,
    "n_lags": 12,
    "lr": 0.005,
    "use_torch": True,
}


def _generate_ar_dgp(
    *, seed: int, n: int = 200, phi: float = 0.6,
    sigma: float = 1.0,
) -> np.ndarray:
    """AR(1) DGP — preserved from pre-rewrite scope; widely reused
    across DL family harnesses (p3_autoencoder + p3_gp imports
    this)."""
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50) * sigma
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = phi * y[t - 1] + eps[t]
    return y[50:]


def _seed_torch(seed: int) -> None:
    """Legacy DL determinism helper preserved for back-compat with
    p3_autoencoder + p3_gp imports. SC13 introduced standardized
    `_setup_dl_determinism` (per p3_autoencoder); this legacy helper
    has SAME behavior (back-compat preserved for institutional
    import-stability)."""
    import torch  # type: ignore
    import random  # type: ignore
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def _setup_dl_determinism(seed: int):
    """Tier D family determinism configuration per SC13 establishment
    + SC14 recurrent-architecture verification (Step 2 cross-
    invocation bit-exact confirmed)."""
    import torch  # type: ignore
    import random  # type: ignore
    np.random.seed(seed)
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
    try:
        torch.use_deterministic_algorithms(True, warn_only=True)
    except (AttributeError, RuntimeError):
        pass
    try:
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False
    except AttributeError:
        pass


def _create_sequences_reference(data, seq_len):
    """Reference reimpl of engine `_create_sequences` lines 66-72."""
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i + seq_len])
        y.append(data[i + seq_len])
    return np.array(X), np.array(y)


def _make_sequences(
    y: np.ndarray, lookback: int = 12,
) -> tuple[np.ndarray, np.ndarray]:
    """Legacy DL-family sequence builder retained for back-compat —
    p3_tcn + p3_nbeats + p3_nhits still import this symbol pending
    their respective Cat 3 → Cat 1 remediation sessions per triage
    close ordering (Tier D sessions SC15-SC17). Returns (X, y_target)
    where X shape is `(n_samples, lookback, 1)` — 3D as required by
    PyTorch recurrent/conv input convention. Mirrors the pre-rewrite
    scope; once dependent harnesses are remediated the import
    dependencies fall away and this stub can be removed.
    """
    n_seq = len(y) - lookback
    X = np.zeros((n_seq, lookback, 1), dtype=np.float32)
    target = np.zeros(n_seq, dtype=np.float32)
    for i in range(n_seq):
        X[i, :, 0] = y[i:i + lookback]
        target[i] = y[i + lookback]
    return X, target


def _reference_lstm_gru_forecast(
    values: np.ndarray, *, seed: int, horizon: int = 10,
    preset_cfg: dict = None, model_type: str = "lstm",
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `lstm_gru_forecast.run()`
    primary PyTorch path at engine lines 281-313 verbatim including
    `_train_torch_model` at engine lines 86-136 (LSTMModel/GRUModel
    classes + Adam + MSE + epochs training loop) + `_predict_torch`
    at engine lines 139-154 (recursive multi-step forecast).
    """
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # SC1 helper reuse (PARTIAL Tier A fifth-instance)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    hidden_size = int(cfg["hidden_size"])
    n_layers = int(cfg["n_layers"])
    epochs = int(cfg["epochs"])
    n_lags = int(cfg["n_lags"])
    lr = float(cfg["lr"])

    # Cap n_lags per engine line 263
    n_lags = min(n_lags, n // 3)

    # Normalize per engine lines 266-270
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Create sequences per engine line 283
    X, y = _create_sequences_reference(normalized, n_lags)

    # ===== _train_torch_model reimpl per engine lines 86-136 =====
    torch.manual_seed(seed)

    class LSTMModel(nn.Module):
        def __init__(self, input_size, hidden_size, n_layers):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size, hidden_size, n_layers, batch_first=True,
            )
            self.fc = nn.Linear(hidden_size, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :]).squeeze(-1)

    class GRUModel(nn.Module):
        def __init__(self, input_size, hidden_size, n_layers):
            super().__init__()
            self.gru = nn.GRU(
                input_size, hidden_size, n_layers, batch_first=True,
            )
            self.fc = nn.Linear(hidden_size, 1)

        def forward(self, x):
            out, _ = self.gru(x)
            return self.fc(out[:, -1, :]).squeeze(-1)

    X_tensor = torch.FloatTensor(X).unsqueeze(-1)
    y_tensor = torch.FloatTensor(y)

    if model_type == "gru":
        model = GRUModel(1, hidden_size, n_layers)
    else:
        model = LSTMModel(1, hidden_size, n_layers)

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

    # Parameter count per engine lines 297-300
    try:
        n_params = int(sum(p.numel() for p in model.parameters()))
    except Exception:
        n_params = None

    # Recursive forecast per engine line 304 + _predict_torch (lines
    # 139-154)
    last_seq = normalized[-n_lags:].copy()
    forecasts = []
    with torch.no_grad():
        for _ in range(horizon):
            x = torch.FloatTensor(last_seq).unsqueeze(0).unsqueeze(-1)
            pred = float(model(x).item())
            forecasts.append(pred)
            last_seq = np.append(last_seq[1:], pred)
    fc_norm = np.array(forecasts)

    # In-sample predictions per engine lines 307-311
    with torch.no_grad():
        X_full = torch.FloatTensor(X).unsqueeze(-1)
        y_pred_norm = model(X_full).numpy()

    # Denormalize per engine lines 350-352
    fc_values = fc_norm * y_std + y_mean
    y_actual = y * y_std + y_mean
    y_pred = y_pred_norm * y_std + y_mean

    # Metrics per engine lines 355-358
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
        "forecast_end_value": float(fc_values[-1]) if len(fc_values) else 0.0,
        "last_observed_value": float(clean[-1]),
    }


class LstmGruParity(P3ParityCheck):
    """LSTM/GRU forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.lstm_gru_forecast.run() via
    RunContext at Balanced preset (hidden_size=64 + n_layers=2 +
    epochs=100 + n_lags=12 + lr=0.005 + use_torch=True + model_type
    ="lstm" default); reference arm reimplements full engine
    PyTorch primary-path pipeline bespoke with SC1
    `_prepare_series_reference` Layer 2 family-shared helper reuse
    (PARTIAL Tier A pattern FIFTH-INSTANCE per SC10+SC11+SC12+SC13
    precedent). Sklearn MLP fallback NOT validated at math layer.
    SC14 inherits SC13 DL family determinism profile + verifies
    recurrent-architecture cross-invocation bit-exact at CPU PyTorch.
    """

    technique_id = "p3_lstm_gru"
    tier = "slow"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PyTorch LSTM/GRU at CPU backend with torch.manual_seed + "
        "deterministic algorithms + cuDNN deterministic flags is "
        "cross-invocation BIT-EXACT (SC14 Step 2 empirical "
        "verification inherits SC13 DL family determinism profile; "
        "confirms recurrent architecture preserves bit-exact "
        "reproducibility). Engine and reference reimpl follow "
        "identical pipeline (NaN drop via SC1 helper + normalize + "
        "sequence construction + LSTMModel/GRUModel construction "
        "with deterministic gate weight init order + Adam + MSE + "
        "epochs + recursive multi-step forecast + denormalization + "
        "metrics); outputs match at machine precision modulo engine "
        "6-decimal forecast rounding + 6-decimal loss + 4-decimal "
        "audit metric rounding. SC14 Tier D.2 recurrent + bespoke "
        "per-session reimpl with PARTIAL Tier A helper reuse."
    )

    DGP_N = 200
    HORIZON = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.lstm_gru_forecast as lg_mod  # type: ignore

        _setup_dl_determinism(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_lstm_gru_parity",
            "technique_id": "lstm_gru_forecast",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = lg_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL lstm_gru_forecast failed: "
                f"{resp.get('error_message')}"
            )
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "pytorch":
            raise RuntimeError(
                f"TSL lstm_gru dispatched to backend='{backend}' "
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
            "model_type": str(audit.get("model_type", "")),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        _setup_dl_determinism(42)
        out = _reference_lstm_gru_forecast(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
            model_type="lstm",
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
                "model_type": str(tsl.get("model_type", "")),
                "hidden_size": int(_ENGINE_BALANCED_PRESET["hidden_size"]),
                "n_layers": int(_ENGINE_BALANCED_PRESET["n_layers"]),
                "epochs": int(_ENGINE_BALANCED_PRESET["epochs"]),
                "n_lags": int(_ENGINE_BALANCED_PRESET["n_lags"]),
                "lr": float(_ENGINE_BALANCED_PRESET["lr"]),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
