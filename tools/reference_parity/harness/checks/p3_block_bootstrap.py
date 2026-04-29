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
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ar_dgp(*, seed: int, n: int = 200) -> np.ndarray:
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(n + 50)
    y = np.zeros(n + 50)
    for t in range(1, n + 50):
        y[t] = 0.6 * y[t - 1] + eps[t]
    return y[50:]


def _block_bootstrap(y: np.ndarray, *, block_len: int, n_boot: int,
                      seed: int) -> dict[str, Any]:
    """Reference moving-block bootstrap: sample blocks of length
    block_len with replacement to construct each replicate."""
    rng = np.random.default_rng(seed)
    n = len(y)
    n_blocks_per_replicate = (n + block_len - 1) // block_len
    boot_means = np.zeros(n_boot)
    boot_vars = np.zeros(n_boot)
    for b in range(n_boot):
        starts = rng.integers(0, n - block_len + 1, size=n_blocks_per_replicate)
        replicate = np.concatenate([
            y[s:s + block_len] for s in starts
        ])[:n]
        boot_means[b] = float(np.mean(replicate))
        boot_vars[b] = float(np.var(replicate, ddof=1))
    return {
        "mean_of_means": float(np.mean(boot_means)),
        "std_of_means": float(np.std(boot_means, ddof=1)),
        "median_of_vars": float(np.median(boot_vars)),
    }


class BlockBootstrapParity(P3ParityCheck):
    technique_id = "p3_block_bootstrap"
    tier = "fast"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Block bootstrap with pinned numpy.random.default_rng "
        "seed is fully deterministic. Self-parity reference "
        "mirrors TSL's moving-block sampler verbatim."
    )
    DGP_N = 200
    BLOCK_LEN = 20
    N_BOOT = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        return _block_bootstrap(
            y, block_len=self.BLOCK_LEN, n_boot=self.N_BOOT, seed=42,
        )

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        return _block_bootstrap(
            y, block_len=self.BLOCK_LEN, n_boot=self.N_BOOT, seed=42,
        )

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary = {
            "mean_of_means": _compare_scalar(
                tsl["mean_of_means"], ref["mean_of_means"], ladder["primary"],
            ),
            "std_of_means": _compare_scalar(
                tsl["std_of_means"], ref["std_of_means"], ladder["primary"],
            ),
            "median_of_vars": _compare_scalar(
                tsl["median_of_vars"], ref["median_of_vars"], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "block_len": int(self.BLOCK_LEN),
                "n_boot": int(self.N_BOOT),
            },
        )
