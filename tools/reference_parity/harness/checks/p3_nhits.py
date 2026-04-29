"""Phase 3 Batch 9 — NHITS forecast parity check.

Compares TSL ``engine/techniques/nhits_forecast.py`` against
direct PyTorch invocation (same-library self-test). Same
rationale as p3_nbeats: TSL uses direct torch.nn (NOT
neuralforecast); neuralforecast unusable on Python 3.14.
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


class NhitsParity(P3ParityCheck):
    """NHITS forecast parity (PyTorch same-library self-parity)."""

    technique_id = "p3_nhits"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "Custom PyTorch NHITS architecture (NBEATS variant with "
        "multi-rate hierarchical sampling via 1-D pooling). "
        "Seed-pinned same-library self-test."
    )

    DGP_N = 200
    LOOKBACK = 12
    HIDDEN = 16
    N_EPOCHS = 3

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        _seed_torch(seed)
        y = np.asarray(fixture["y"], dtype=np.float32)
        n_seq = len(y) - self.LOOKBACK
        X = np.zeros((n_seq, self.LOOKBACK), dtype=np.float32)
        target = np.zeros(n_seq, dtype=np.float32)
        for i in range(n_seq):
            X[i] = y[i:i + self.LOOKBACK]
            target[i] = y[i + self.LOOKBACK]
        X_t = torch.from_numpy(X)
        y_t = torch.from_numpy(target).unsqueeze(-1)

        class _NHitsBlock(nn.Module):
            def __init__(self, lookback, hidden, pool_size=2):
                super().__init__()
                self.pool = nn.MaxPool1d(pool_size, ceil_mode=True)
                # After pool, length is ceil(lookback/pool_size)
                pooled_len = (lookback + pool_size - 1) // pool_size
                self.fc1 = nn.Linear(pooled_len, hidden)
                self.fc2 = nn.Linear(hidden, hidden)
                self.backcast = nn.Linear(hidden, lookback)
                self.forecast = nn.Linear(hidden, 1)
            def forward(self, x):
                # x: (b, lookback) -> (b, 1, lookback) for pool
                h = self.pool(x.unsqueeze(1)).squeeze(1)
                h = torch.relu(self.fc1(h))
                h = torch.relu(self.fc2(h))
                return self.backcast(h), self.forecast(h)

        class _NHits(nn.Module):
            def __init__(self, lookback, hidden, n_blocks=2):
                super().__init__()
                self.blocks = nn.ModuleList([
                    _NHitsBlock(lookback, hidden, pool_size=p)
                    for p in [2, 4][:n_blocks]
                ])
            def forward(self, x):
                forecast = torch.zeros(x.shape[0], 1)
                residual = x
                for block in self.blocks:
                    backcast, fcast = block(residual)
                    residual = residual - backcast
                    forecast = forecast + fcast
                return forecast

        _seed_torch(seed)
        model = _NHits(self.LOOKBACK, self.HIDDEN, n_blocks=2)
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
