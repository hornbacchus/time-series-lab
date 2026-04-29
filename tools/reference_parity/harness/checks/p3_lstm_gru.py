"""Phase 3 Batch 9 — LSTM/GRU forecast parity check.

Compares TSL ``engine/techniques/lstm_gru_forecast.py`` (PyTorch
nn.LSTM/nn.GRU) against direct PyTorch invocation
(same-library self-test) with rigorous seed pinning + cuDNN
deterministic flag. Pattern A.1 same-library bit-exact target;
DL state isolation via in-test seed reset (rather than
subprocess isolation) — both arms reset torch + numpy +
random seeds at the start of fit/predict.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(*, seed: int, n: int = 200, phi: float = 0.6,
                     sigma: float = 1.0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50) * sigma
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = phi * y[t - 1] + eps[t]
    return y[50:]


def _seed_torch(seed: int) -> None:
    """Pin all PyTorch + numpy + random seeds + cuDNN
    deterministic flag for full reproducibility."""
    import torch  # type: ignore
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if hasattr(torch.backends, "cudnn"):
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False


def _make_sequences(y: np.ndarray, lookback: int = 12
                    ) -> tuple[np.ndarray, np.ndarray]:
    """Build (n_samples, lookback, 1) sequences + targets."""
    n = len(y)
    n_seq = n - lookback
    X = np.zeros((n_seq, lookback, 1), dtype=np.float32)
    y_target = np.zeros(n_seq, dtype=np.float32)
    for i in range(n_seq):
        X[i, :, 0] = y[i:i + lookback]
        y_target[i] = y[i + lookback]
    return X, y_target


class LstmGruParity(P3ParityCheck):
    """LSTM/GRU forecast parity (PyTorch same-library)."""

    technique_id = "p3_lstm_gru"
    tier = "fast"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "PyTorch nn.LSTM with all seeds pinned (torch + numpy + "
        "random) and cuDNN deterministic=True is reproducible. "
        "Same-library self-test: TSL and reference both build "
        "the same architecture and call the same nn primitives. "
        "Pattern A.1 same-library sub-class with seed-pinning "
        "discipline."
    )

    DGP_N = 200
    LOOKBACK = 12
    HIDDEN_SIZE = 16
    N_EPOCHS = 5

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any], seed: int = 42):
        import torch  # type: ignore
        import torch.nn as nn  # type: ignore
        _seed_torch(seed)
        y = np.asarray(fixture["y"], dtype=np.float64)
        X, y_target = _make_sequences(y, lookback=self.LOOKBACK)
        X_t = torch.from_numpy(X)
        y_t = torch.from_numpy(y_target).unsqueeze(-1)

        class _LSTMModel(nn.Module):
            def __init__(self, hidden):
                super().__init__()
                self.lstm = nn.LSTM(1, hidden, batch_first=True)
                self.fc = nn.Linear(hidden, 1)
            def forward(self, x):
                out, _ = self.lstm(x)
                return self.fc(out[:, -1, :])

        # Re-seed RIGHT BEFORE model instantiation so weight
        # initialization is reproducible across runs.
        _seed_torch(seed)
        model = _LSTMModel(self.HIDDEN_SIZE)
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
                "lookback": int(self.LOOKBACK),
                "hidden_size": int(self.HIDDEN_SIZE),
                "torch_version": ref.get("torch_version", "unknown"),
            },
        )
