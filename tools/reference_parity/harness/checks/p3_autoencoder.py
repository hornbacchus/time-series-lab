"""Phase 3 Batch 9 — Autoencoder anomaly detection parity check.

TSL ``engine/techniques/autoencoder_anomaly.py`` (PyTorch MLP
autoencoder with 2-hidden-layer encoder/decoder + Adam optimizer
+ MSE loss + sliding window construction + per-point reconstruction
error aggregation + percentile-of-training-error threshold for
contamination-based anomaly identification + sklearn PCA fallback
when PyTorch unavailable) vs from-scratch paper-formula reimpl
mirroring engine PyTorch primary path verbatim.

Rewritten at SC13-side Cat 3 remediation cycle session 13/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC13 = TIER D OPENING** (first
PyTorch-based DL family session). PARTIAL Tier A pattern FOURTH-
INSTANCE confirmation (SC10 + SC11 + SC12 + SC13 all 1 MATCH + 2
ABSENT; codification ROBUSTLY GROUNDED at n=4 sustained observations
across two distinct cohorts Tier C + Tier D opening).

**Helper identity verification (Step 1 of SC13 workflow per SC4
two-stage methodology + SC10-SC12 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 48-68: **MATCH SC1 RF** (hash
  57bae54d463c2fd7)
- `_create_features`: **ABSENT** (autoencoder uses sliding windows
  via `_create_windows` not lag features)
- `_create_forecast_features`: **ABSENT** (autoencoder is anomaly
  detection technique, not forecast)

Stage 2: ABSENT helpers indicate architectural distinctness
(autoencoder pipeline distinct from tree-family). PARTIAL Tier A
pattern FOURTH-INSTANCE confirmation: `_prepare_series_reference`
reused from SC1; sliding-window construction + autoencoder training
+ point-error aggregation + threshold computation all bespoke.

**Cross-invocation reproducibility verification (Step 2 of SC13
workflow per SC11 prophet within-process-vs-cross-invocation
finding + SC12 esn cross-invocation bit-exact precedent):**

CRITICAL DL family determinism question: is PyTorch cross-
invocation bit-exact (like numpy) or mle-band (like Stan)?
Empirical Step 2 verification: invoked engine TWICE as separate
Python computations at seed=42 with full DL determinism
configuration (torch.manual_seed + torch.use_deterministic_
algorithms + cuDNN flags) → **max_abs_diff=0.0 (BIT-EXACT cross-
invocation)** at CPU PyTorch backend.

**Tier D DL family determinism profile (ESTABLISHED at SC13;
inherited by SC14-SC17):**
- CPU PyTorch with `torch.manual_seed(seed)` is cross-invocation
  BIT-EXACT deterministic (distinct from Stan-MAP mle-band cross-
  invocation)
- Audit environment: torch 2.11.0+cpu (CPU-only); CUDA/cuDNN paths
  not exercised + therefore not validated
- Tier II.bit-exact viable for CPU PyTorch DL family (Tier II.mle-
  band fallback NOT REQUIRED at SC13 audit)
- SC14-SC17 sessions inherit this determinism profile + cross-
  invocation expectation; verify Step 2 at each session for any
  architecture-specific non-determinism (e.g., dropout in eval
  mode, batch_norm running stats accumulation, attention
  randomization)

**Fallback dispatch handling (SC3 template element FIFTH-INSTANCE
application):** Engine `_has_torch()` at lines 21-26 + preset flag
`use_torch` at engine line 231 dispatches to PyTorch autoencoder
primary path when torch available + preset enables. Engine line 234
emits warning when PyTorch unavailable but preset enables; falls
back to sklearn PCA reconstruction error via `_train_pca_anomaly`
at engine lines 135-152.

**Mathematical equivalence assessment (primary vs fallback):
CATEGORICALLY DIFFERENT.** PyTorch autoencoder (nonlinear
dimensionality reduction via deep MLP with ReLU activations) vs
sklearn PCA (linear dimensionality reduction via SVD). Outputs are
NOT numerically equivalent — fundamentally different algorithms
sharing only the "reconstruction-error-based anomaly detection"
output convention. Users in non-torch environments receive
algorithmically distinct output covered by wrapper-layer 3-check
only.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor at CPU PyTorch backend per Step 2 cross-
invocation verification).
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
    _generate_ar_dgp,
)


# Engine preset Balanced config (engine `autoencoder_anomaly.py`
# lines 35-39). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "hidden_dim": 16,
    "window_size": 10,
    "epochs": 30,
    "lr": 0.005,
    "use_torch": True,
    "n_pca_components": 5,
}


def _setup_dl_determinism(seed: int):
    """Tier D family determinism configuration per SC13 Step 2
    verification + SC11/SC12 cross-invocation precedent. All DL
    sessions in cycle (SC13-SC17) inherit this config."""
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


def _create_windows_reference(data, window_size):
    """Reference reimpl of engine `_create_windows` lines 71-76."""
    windows = []
    for i in range(len(data) - window_size + 1):
        windows.append(data[i:i + window_size])
    return np.array(windows)


def _reference_autoencoder_anomaly(
    values: np.ndarray, *, seed: int,
    preset_cfg: dict = None, contamination: float = 0.05,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `autoencoder_anomaly.run()`
    primary PyTorch path at engine lines 155-418 verbatim including
    sliding window construction + PyTorch autoencoder training +
    per-point reconstruction error aggregation + percentile threshold
    + anomaly identification.
    """
    import torch  # type: ignore
    import torch.nn as nn  # type: ignore

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # SC1 helper reuse (PARTIAL Tier A fourth-instance)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    hidden_dim = int(cfg["hidden_dim"])
    window_size = int(cfg["window_size"])
    epochs = int(cfg["epochs"])
    lr = float(cfg["lr"])

    # Cap window per engine line 211
    window_size = max(2, min(window_size, n // 3))

    # Normalize per engine lines 214-218
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Create windows per engine line 222
    windows = _create_windows_reference(normalized, window_size)

    # ===== _train_torch_autoencoder reimpl per engine lines 79-132 =====
    torch.manual_seed(seed)

    input_dim = windows.shape[1]

    class Autoencoder(nn.Module):
        def __init__(self, input_dim, hidden_dim):
            super().__init__()
            mid_dim = max(hidden_dim + 4, (input_dim + hidden_dim) // 2)
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, mid_dim),
                nn.ReLU(),
                nn.Linear(mid_dim, hidden_dim),
                nn.ReLU(),
            )
            self.decoder = nn.Sequential(
                nn.Linear(hidden_dim, mid_dim),
                nn.ReLU(),
                nn.Linear(mid_dim, input_dim),
            )

        def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

    X_tensor = torch.FloatTensor(windows)
    model = Autoencoder(input_dim, hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for _epoch in range(epochs):
        optimizer.zero_grad()
        reconstructed = model(X_tensor)
        loss = loss_fn(reconstructed, X_tensor)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    with torch.no_grad():
        reconstructed = model(X_tensor).numpy()
    recon_errors = np.mean((windows - reconstructed) ** 2, axis=1)
    final_loss = losses[-1] if losses else float("inf")

    # Map window-level errors to point-level errors per engine
    # lines 262-269
    point_errors = np.zeros(n)
    point_counts = np.zeros(n)
    for i, err in enumerate(recon_errors):
        for j in range(window_size):
            idx = i + j
            if idx < n:
                point_errors[idx] = max(point_errors[idx], err)
                point_counts[idx] += 1

    # Threshold per engine line 272
    threshold = float(
        np.percentile(point_errors, 100 * (1 - contamination))
    )
    is_anomaly = point_errors > threshold
    anomaly_indices = np.where(is_anomaly)[0]
    n_anomalies = int(len(anomaly_indices))

    mean_recon_error = float(np.mean(point_errors))
    max_recon_error = float(np.max(point_errors))
    most_extreme_idx = (
        int(np.argmax(point_errors)) if len(point_errors) else None
    )
    most_extreme_error = (
        float(np.max(point_errors)) if len(point_errors) else None
    )

    return {
        "threshold": threshold,
        "n_anomalies": n_anomalies,
        "mean_recon_error": mean_recon_error,
        "max_recon_error": max_recon_error,
        "most_extreme_idx": most_extreme_idx,
        "most_extreme_error": most_extreme_error,
        "anomaly_indices": [int(i) for i in anomaly_indices],
        "final_loss": float(final_loss),
        "anomaly_rate": float(n_anomalies / n) if n > 0 else 0.0,
    }


class AutoencoderParity(P3ParityCheck):
    """Autoencoder anomaly parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.autoencoder_anomaly.run() via
    RunContext at Balanced preset (hidden_dim=16 + window_size=10 +
    epochs=30 + lr=0.005 + use_torch=True); reference arm reimplements
    full engine PyTorch primary-path pipeline bespoke with SC1
    `_prepare_series_reference` Layer 2 family-shared helper reuse
    (PARTIAL Tier A pattern FOURTH-INSTANCE). PCA fallback path
    (sklearn when PyTorch unavailable) NOT validated at math layer.
    SC13 establishes Tier D DL family determinism profile (CPU
    PyTorch + torch.manual_seed = cross-invocation BIT-EXACT).
    """

    technique_id = "p3_autoencoder"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "PyTorch autoencoder at CPU backend with torch.manual_seed + "
        "deterministic algorithms is cross-invocation BIT-EXACT "
        "(SC13 Step 2 empirical verification; distinct from SC11 "
        "Stan-MAP mle-band cross-invocation). Engine and reference "
        "reimpl follow identical pipeline (NaN drop via SC1 helper "
        "+ normalize + sliding windows + Autoencoder construction "
        "with deterministic weight init + Adam optimization + MSE "
        "loss + epochs + reconstruction errors + point-level error "
        "aggregation + percentile threshold + anomaly identification); "
        "outputs match at machine precision modulo engine 6-decimal "
        "rounding. SC13 Tier D opening establishes DL family "
        "determinism profile for SC14-SC17 inheritance."
    )

    DGP_N = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.autoencoder_anomaly as ae_mod  # type: ignore

        _setup_dl_determinism(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_autoencoder_parity",
            "technique_id": "autoencoder_anomaly",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = ae_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL autoencoder_anomaly failed: "
                f"{resp.get('error_message')}"
            )
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "pytorch_autoencoder":
            raise RuntimeError(
                f"TSL autoencoder dispatched to backend='{backend}' "
                f"not 'pytorch_autoencoder'; primary path validation "
                f"requires torch installed in audit environment"
            )
        audit = resp.get("audit_fields", {})
        return {
            "threshold": float(audit.get("threshold", float("nan"))),
            "n_anomalies": int(audit.get("n_anomalies", 0)),
            "mean_recon_error": float(
                audit.get("mean_recon_error", float("nan"))
            ),
            "max_recon_error": float(
                audit.get("max_recon_error", float("nan"))
            ),
            "most_extreme_idx": (
                int(audit.get("most_extreme_idx"))
                if audit.get("most_extreme_idx") is not None else None
            ),
            "most_extreme_error": (
                float(audit.get("most_extreme_error"))
                if audit.get("most_extreme_error") is not None else None
            ),
            "anomaly_indices": [
                int(i) for i in audit.get("anomaly_indices", [])
            ],
            "final_loss": float(audit.get("final_loss", float("nan"))),
            "anomaly_rate": float(
                audit.get("anomaly_rate", float("nan"))
            ),
            "backend": backend,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        _setup_dl_determinism(42)
        out = _reference_autoencoder_anomaly(
            y, seed=42, preset_cfg=_ENGINE_BALANCED_PRESET,
            contamination=0.05,
        )
        out["torch_version"] = torch.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8: threshold +
        # mean_recon_error + max_recon_error + most_extreme_error +
        # final_loss + anomaly_rate at 6-decimal; integer counts
        # exact match.
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["threshold"] = _compare_scalar(
            tsl["threshold"], round(ref["threshold"], 6),
            ladder["primary"],
        )
        statuses.append(primary["threshold"]["status"])

        primary["mean_recon_error"] = _compare_scalar(
            tsl["mean_recon_error"], round(ref["mean_recon_error"], 6),
            ladder["primary"],
        )
        statuses.append(primary["mean_recon_error"]["status"])

        primary["max_recon_error"] = _compare_scalar(
            tsl["max_recon_error"], round(ref["max_recon_error"], 6),
            ladder["primary"],
        )
        statuses.append(primary["max_recon_error"]["status"])

        primary["final_loss"] = _compare_scalar(
            tsl["final_loss"], round(ref["final_loss"], 6),
            ladder["primary"],
        )
        statuses.append(primary["final_loss"]["status"])

        primary["anomaly_rate"] = _compare_scalar(
            tsl["anomaly_rate"], round(ref["anomaly_rate"], 6),
            ladder["primary"],
        )
        statuses.append(primary["anomaly_rate"]["status"])

        primary["n_anomalies"] = {
            "status": (
                "PASS" if tsl["n_anomalies"] == ref["n_anomalies"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_anomalies"]),
            "ref": int(ref["n_anomalies"]),
        }
        statuses.append(primary["n_anomalies"]["status"])

        primary["most_extreme_idx"] = {
            "status": (
                "PASS" if tsl["most_extreme_idx"] == ref["most_extreme_idx"]
                else "BLOCK"
            ),
            "tsl": tsl["most_extreme_idx"],
            "ref": ref["most_extreme_idx"],
        }
        statuses.append(primary["most_extreme_idx"]["status"])

        if (tsl["most_extreme_error"] is not None
                and ref["most_extreme_error"] is not None):
            primary["most_extreme_error"] = _compare_scalar(
                tsl["most_extreme_error"],
                round(ref["most_extreme_error"], 6),
                ladder["primary"],
            )
            statuses.append(primary["most_extreme_error"]["status"])

        primary["anomaly_indices"] = {
            "status": (
                "PASS"
                if list(tsl["anomaly_indices"])
                == list(ref["anomaly_indices"])
                else "BLOCK"
            ),
            "tsl_count": len(tsl["anomaly_indices"]),
            "ref_count": len(ref["anomaly_indices"]),
        }
        statuses.append(primary["anomaly_indices"]["status"])

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
                "backend": str(tsl.get("backend", "?")),
                "hidden_dim": int(_ENGINE_BALANCED_PRESET["hidden_dim"]),
                "window_size": int(_ENGINE_BALANCED_PRESET["window_size"]),
                "epochs": int(_ENGINE_BALANCED_PRESET["epochs"]),
                "lr": float(_ENGINE_BALANCED_PRESET["lr"]),
                "contamination": 0.05,
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
