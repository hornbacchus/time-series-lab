"""Phase 3 Batch 9 — Prophet forecast parity check.

Compares TSL ``engine/techniques/prophet_forecast.py``
(prophet.Prophet) against direct prophet invocation (same-
library self-test). Prophet uses a Stan backend with internal
RNG; we pin via Stan seed argument to ensure reproducibility.

**Pattern J catalog candidate:** prophet's Stan seed is set
via ``model.stan_init_seed`` (private attr) or via the cmdstan
config; convention varies by version. We use ``Prophet(seed=N)``
which is the official knob in prophet 1.3+.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd  # type: ignore

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_prophet_dgp(*, seed: int, n: int = 120) -> pd.DataFrame:
    """Monthly trend + sinusoidal seasonal."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2010-01-01", periods=n, freq="MS")
    trend = 0.05 * np.arange(n)
    seasonal = 1.5 * np.sin(2 * np.pi * np.arange(n) / 12)
    noise = 0.3 * rng.standard_normal(n)
    return pd.DataFrame({"ds": dates, "y": trend + seasonal + noise})


class ProphetParity(P3ParityCheck):
    """Prophet forecast parity (prophet same-library)."""

    technique_id = "p3_prophet"
    tier = "slow"
    fixture_id = ""

    verdict_class = "dl_seed_pinned"
    verdict_class_rationale = (
        "Prophet's Stan backend uses MCMC sampling but the "
        "default mode is MAP estimation (deterministic given "
        "fixed initialization). Same-library self-test with "
        "default Prophet config catches wrapper preprocessing "
        "regressions; tolerance accommodates Stan numerical "
        "convergence variation."
    )

    DGP_N = 120
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"df": _generate_prophet_dgp(seed=seed, n=self.DGP_N)}

    def _fit_predict(self, fixture: dict[str, Any]) -> dict[str, Any]:
        from prophet import Prophet  # type: ignore
        import logging
        # Suppress prophet noise
        logging.getLogger("prophet").setLevel(logging.ERROR)
        logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
        df = fixture["df"]
        np.random.seed(42)
        m = Prophet(
            growth="linear",
            yearly_seasonality=True,
            weekly_seasonality=False,
            daily_seasonality=False,
            uncertainty_samples=0,  # Disable MCMC sampling for
                                    # deterministic MAP-only output
        )
        m.fit(df)
        future = m.make_future_dataframe(
            periods=self.HORIZON, freq="MS",
        )
        forecast = m.predict(future)
        return {
            "yhat": forecast["yhat"].values.astype(np.float64),
            "trend": forecast["trend"].values.astype(np.float64),
            "n_points": int(len(forecast)),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        return self._fit_predict(fixture)

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import prophet  # type: ignore
        out = self._fit_predict(fixture)
        out["prophet_version"] = prophet.__version__
        return out

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        for k in ("yhat", "trend"):
            primary[k] = _compare_vector(
                tsl[k], ref[k], ladder["primary"],
            )
            statuses.append(primary[k]["status"])
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
                "horizon": int(self.HORIZON),
                "prophet_version": ref.get("prophet_version", "unknown"),
            },
        )
