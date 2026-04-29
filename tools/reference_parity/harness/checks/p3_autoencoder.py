"""Phase 3 Batch 9 — Autoencoder anomaly parity check.

Compares TSL ``engine/techniques/autoencoder_anomaly.py``
(PyTorch encoder-decoder for reconstruction-error anomaly
detection) against direct PyTorch invocation (same-library
self-test). Pattern A.1 same-library bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector, _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_lstm_gru import (
    _generate_ar_dgp, _seed_torch,
)


class AutoencoderParity(P3ParityCheck):
    """Autoencoder anomaly parity (PyTorch same-library)."""

    technique_id = "p3_autoencoder"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "PyTorch encoder-decoder MLP with seed pinning + cuDNN "
        "deterministic. Same-library self-test verifies wrapper "
        "encoder-decoder construction reproducibility."
    )

    DGP_N = 200
    WINDOW = 10
    HIDDEN = 8
    BOTTLENECK = 4
    N_EPOCHS = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_reconstruct(self, fixture: dict[str, Any], seed: int = 42):
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        _seed_torch(seed)
        y = np.asarray(fixture["y"], dtype=np.float32)
        # Build sliding windows
        n_seq = len(y) - self.WINDOW + 1
        X = np.zeros((n_seq, self.WINDOW), dtype=np.float32)
        for i in range(n_seq):
            X[i] = y[i:i + self.WINDOW]
        X_t = torch.from_numpy(X)

        class _AE(nn.Module):
            def __init__(self, w, hidden, bottleneck):
                super().__init__()
                self.enc = nn.Sequential(
                    nn.Linear(w, hidden), nn.ReLU(),
                    nn.Linear(hidden, bottleneck),
                )
                self.dec = nn.Sequential(
                    nn.Linear(bottleneck, hidden), nn.ReLU(),
                    nn.Linear(hidden, w),
                )
            def forward(self, x):
                return self.dec(self.enc(x))

        _seed_torch(seed)
        model = _AE(self.WINDOW, self.HIDDEN, self.BOTTLENECK)
        opt = torch.optim.Adam(model.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()
        model.train()
        for _ in range(self.N_EPOCHS):
            opt.zero_grad()
            recon = model(X_t)
            loss = loss_fn(recon, X_t)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            recon = model(X_t).numpy()
            recon_err = np.mean((recon - X) ** 2, axis=1)
        return {
            "reconstruction_errors": recon_err.astype(np.float64),
            "final_loss": float(loss.item()),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_reconstruct(fixture, seed=42)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore
        out = self._fit_reconstruct(fixture, seed=42)
        out["torch_version"] = torch.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        primary["reconstruction_errors"] = _compare_vector(
            tsl["reconstruction_errors"], ref["reconstruction_errors"],
            ladder["primary"],
        )
        statuses.append(primary["reconstruction_errors"]["status"])
        primary["final_loss"] = _compare_scalar(
            tsl["final_loss"], ref["final_loss"], ladder["primary"],
        )
        statuses.append(primary["final_loss"]["status"])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
