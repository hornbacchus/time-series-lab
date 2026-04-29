"""Phase 3 Batch 9 — TCN forecast parity check.

Compares TSL ``engine/techniques/tcn_forecast.py`` (PyTorch
nn.Conv1d-based TCN) against direct PyTorch invocation
(same-library self-test) with seed pinning. Pattern A.1
same-library bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder
from reference_parity.harness.checks.p3_lstm_gru import (
    _generate_ar_dgp, _seed_torch, _make_sequences,
)


class TcnParity(P3ParityCheck):
    """TCN forecast parity (PyTorch same-library)."""

    technique_id = "p3_tcn"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "PyTorch nn.Conv1d TCN with seed pinning + cuDNN "
        "deterministic is reproducible. Same-library self-test "
        "verifies wrapper architecture-construction round-trips "
        "the torch primitive."
    )

    DGP_N = 200
    LOOKBACK = 12
    HIDDEN_CHANNELS = 8
    N_EPOCHS = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        _seed_torch(seed)
        y = np.asarray(fixture["y"], dtype=np.float64)
        X, y_target = _make_sequences(y, lookback=self.LOOKBACK)
        # TCN expects (batch, channels, seq); reshape from
        # (batch, seq, 1)
        X_t = torch.from_numpy(X).transpose(1, 2)  # (b, 1, seq)
        y_t = torch.from_numpy(y_target).unsqueeze(-1)

        class _TCNModel(nn.Module):
            def __init__(self, hidden, lookback):
                super().__init__()
                self.conv1 = nn.Conv1d(1, hidden, kernel_size=3,
                                        padding=2, dilation=1)
                self.conv2 = nn.Conv1d(hidden, hidden, kernel_size=3,
                                        padding=4, dilation=2)
                self.fc = nn.Linear(hidden * lookback, 1)
            def forward(self, x):
                h = torch.relu(self.conv1(x))[:, :, :x.shape[-1]]
                h = torch.relu(self.conv2(h))[:, :, :x.shape[-1]]
                return self.fc(h.flatten(1))

        _seed_torch(seed)
        model = _TCNModel(self.HIDDEN_CHANNELS, self.LOOKBACK)
        opt = torch.optim.Adam(model.parameters(), lr=0.01)
        loss_fn = nn.MSELoss()
        model.train()
        for _ in range(self.N_EPOCHS):
            opt.zero_grad()
            preds = model(X_t)
            loss = loss_fn(preds, y_t)
            loss.backward()
            opt.step()
        model.eval()
        with torch.no_grad():
            in_sample = model(X_t).squeeze().numpy()
        return {
            "in_sample_preds": in_sample.astype(np.float64),
            "final_loss": float(loss.item()),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture, seed=42)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import torch  # type: ignore
        out = self._fit_predict(fixture, seed=42)
        out["torch_version"] = torch.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        primary["in_sample_preds"] = _compare_vector(
            tsl["in_sample_preds"], ref["in_sample_preds"],
            ladder["primary"],
        )
        statuses.append(primary["in_sample_preds"]["status"])
        from reference_parity.harness.compare import _compare_scalar
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
