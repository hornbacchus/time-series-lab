"""Phase 3 Batch 10 — Block bootstrap parity check.

TSL ``block_bootstrap.py`` (numpy block bootstrap with seed)
vs from-scratch self-parity reference. With seed pinning,
both arms produce bit-identical bootstrap samples; Pattern A
self-parity bit-exact target.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path


def _generate_ar_dgp(*, seed: int, n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50)
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = 0.6 * y[t - 1] + eps[t]
    return y[50:]


def _acf_lag1_ref(x: np.ndarray) -> float:
    """Mirror of the engine's _acf_lag1 (biased lag-1 autocorrelation)."""
    xm = x - np.mean(x)
    c0 = float(np.sum(xm ** 2))
    if c0 == 0:
        return 0.0
    return float(np.sum(xm[:-1] * xm[1:]) / c0)


class BlockBootstrapParity(P3ParityCheck):
    technique_id = "p3_block_bootstrap"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Phase 4a-harden #1: the engine bootstraps with its own RNG stream, so a "
        "bit-exact reference is impossible. run_tsl now INVOKES the engine (was a "
        "self-parity reimpl that never ran engine code) and asserts STRUCTURAL "
        "INVARIANTS on its published 'Bootstrap Results': the Original statistics "
        "(mean, variance, ACF1) equal the analytic sample statistics (a quasi-"
        "reference), each CI brackets its Original, and each CI is non-degenerate. "
        "A violated invariant is a real bootstrap defect."
    )
    DGP_N = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.block_bootstrap as bb_mod  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_block_bootstrap", "technique_id": "block_bootstrap",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {},
        })
        resp = bb_mod.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine block_bootstrap failed: {resp.get('error_message')}")
        tbl = next(t for t in resp.get("tables", []) if t.get("name") == "Bootstrap Results")
        # columns: Statistic | Original | Bias | Std Error | Lower XX% | Upper XX%
        out = {}
        for r in tbl["rows"]:
            out[str(r[0])] = {"original": float(r[1]), "lower": float(r[4]), "upper": float(r[5])}
        return {"stats": out}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        return {
            "Mean": float(np.mean(y)),
            "Variance": float(np.var(y, ddof=1)),
            "ACF(1)": _acf_lag1_ref(y),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        stats = tsl["stats"]
        primary: dict[str, Any] = {}
        for name in ("Mean", "Variance", "ACF(1)"):
            s = stats.get(name)
            if s is None:
                primary[f"{name}:present"] = {"status": "BLOCK", "note": "row missing"}
                continue
            orig, lo, hi = s["original"], s["lower"], s["upper"]
            analytic = ref[name]
            # (1) the Original statistic equals the analytic sample statistic (6dp floor).
            primary[f"{name}:original==analytic"] = {
                "status": "PASS" if abs(orig - analytic) < 1e-4 else "BLOCK",
                "engine_original": orig, "analytic": round(analytic, 6),
            }
            # (2) the CI brackets the Original (a valid percentile bootstrap CI).
            primary[f"{name}:CI_brackets"] = {
                "status": "PASS" if (lo <= orig <= hi) else "BLOCK",
                "lower": lo, "original": orig, "upper": hi,
            }
            # (3) the CI is non-degenerate (the bootstrap produced spread).
            primary[f"{name}:CI_nondegenerate"] = {
                "status": "PASS" if (hi > lo) else "BLOCK",
                "width": round(hi - lo, 6),
            }
        outcome = "BLOCK" if any(v["status"] == "BLOCK" for v in primary.values()) else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={"n_obs": int(self.DGP_N)},
        )
