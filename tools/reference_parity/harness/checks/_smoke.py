"""Smoke-test parity check.

R base ``mean`` vs numpy ``mean`` on a length-100 standard normal
sample. Validates the harness end-to-end without exercising any
domain technique. Should run in well under one second.

Used in CI as the first check — if this fails, the harness
architecture is broken and downstream checks won't have meaningful
results.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


class SmokeTestParity(ParityCheck):
    """Trivial mean-of-100-normals parity. End-to-end harness probe."""

    technique_id = "_smoke_test"
    tier = "fast"
    fixture_id = ""  # generated at runtime; no on-disk hash

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        rng = np.random.default_rng(seed)
        return {"y": rng.standard_normal(100)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # "TSL" side here is just numpy. The smoke test doesn't
        # exercise a TSL wrapper — it's a harness validator.
        y = np.asarray(fixture["y"], dtype=np.float64)
        return {"mean": float(np.mean(y))}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        r_code = r"""
        y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])
        m <- mean(y)
        write.table(
            m, "{{OUTPUT_mean}}",
            row.names=FALSE, col.names=FALSE
        )
        """
        outputs, _versions = bridge.rscript_call(
            r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["mean"],
            timeout_sec=30,
        )
        m = float(np.asarray(outputs["mean"]).reshape(-1)[0])
        return {"mean": m}

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        diff = abs(tsl["mean"] - ref["mean"])
        rel = diff / max(abs(ref["mean"]), 1e-300)
        ok = (
            diff <= ladder["abs_tol"]
            or rel <= ladder["rel_tol"]
        )
        return ParityResult(
            technique_id=self.technique_id,
            outcome="PASS" if ok else "BLOCK",
            metrics={
                "max_abs_diff": float(diff),
                "max_rel_diff": float(rel),
                "tsl_mean": float(tsl["mean"]),
                "ref_mean": float(ref["mean"]),
            },
        )
