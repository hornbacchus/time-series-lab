"""Phase 2 — X-13 SEATS-mode seasonal adjustment parity check (mode-switch build).

The new SEATS path on ``x13_seasonal_adjust`` (the ``method="seats"`` branch:
a ``seats{ save=(s10 s11 s12 s13) }`` spec + S-table extraction) must produce a
CORRECT decomposition, not the X-11 output and not an empty read.

★ Validation tier — same-binary cross-wrapper (honest disclosure). TSL invokes
the Census X-13ARIMA-SEATS binary directly; R ``seasonal::seas`` (which defaults
to SEATS) wraps the *same* binary. So this validates that the engine correctly
DRIVES and READS the trusted Census SEATS implementation -- plumbing correctness
(valid seats{} spec + correct S-table extraction) against the reference standard
-- NOT an independent re-derivation of the SEATS algorithm (no such independent
implementation is available; all wrap the Census binary). With aligned specs the
two arms agree to machine precision (measured rel 0.0 on airline + the DGP).

Two layers:
  1. ALWAYS-ON invariants (enforced in run_tsl, independent of R availability):
     S-tables read (SA/trend/seasonal/irregular finite, length n); reconstruction
     identity (SA x seasonal == original, multiplicative; or SA + seasonal ==
     original, additive); and SEATS materially differs from X-11 on the same
     series (proves the method branch actually switched). A broken extraction
     (D-tables read in SEATS mode -> empty; or s10 mis-mapped to trend) violates
     these -> hard failure.
  2. CROSS-WRAPPER agreement (compare, SKIP-graceful when ``seasonal`` absent):
     engine SEATS SA + trend vs R ``seas()`` SEATS on the p3_x13 ladder.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_seasonal_dgp(*, seed: int, n: int = 120,
                            period: int = 12) -> np.ndarray:
    """Monthly trend + seasonal + noise (matches p3_x13's DGP)."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    trend = 100 + 0.5 * t
    seasonal = 5 * np.sin(2 * np.pi * t / period)
    return trend + seasonal + 2 * rng.standard_normal(n)


def _run_engine(method: str, y: np.ndarray, period: int) -> dict[str, Any]:
    from techniques.base import RunContext  # type: ignore
    from techniques.x13_seasonal_adjust import run as tsl_x13_run  # type: ignore

    time_col = [f"{2010 + i // 12}-{(i % 12) + 1:02d}-01T00:00:00"
                for i in range(len(y))]
    ctx = RunContext({
        "run_id": f"p3_x13_seats_{method}",
        "technique_id": "x13_seasonal_adjust",
        "preset": "Balanced",
        "seed": 42,
        "frequency": "MS",
        "time": time_col,
        "series": [{"name": "y", "values": y.tolist()}],
        # fixed start (deterministic audit) + fit_window_obs=0 (use every
        # observation, so the fit span matches the R reference's full series).
        "params": {"method": method, "start_year": 2010, "start_period": 1,
                   "fit_window_obs": 0},
    })
    res = tsl_x13_run(ctx, lambda *a, **k: None)
    if res.get("status") != "success":
        err = res.get("error_message") or "unknown"
        if "binary not found" in err.lower():
            raise ImportError(f"X-13 binary not found; p3_x13_seats SKIPped: {err}")
        raise RuntimeError(f"TSL x13_seasonal_adjust method={method} failed: {err}")
    decomp = next((t for t in res.get("tables", [])
                   if t.get("name") == "X-13 Decomposition"), None)
    if decomp is None:
        raise RuntimeError("x13_seasonal_adjust produced no 'X-13 Decomposition' table.")
    rows = decomp["rows"]
    col = lambda j: np.asarray([r[j] for r in rows], dtype=np.float64)
    return {"original": col(1), "seasadj": col(2), "trend": col(3),
            "seasonal": col(4), "irregular": col(5),
            "method": res.get("audit_fields", {}).get("method")}


class X13SeatsParity(P3ParityCheck):
    technique_id = "p3_x13_seats"
    tier = "slow"
    fixture_id = ""
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "SEATS seasonal adjustment: TSL and R seasonal both drive the same "
        "Census X-13ARIMA-SEATS binary, so output is deterministic given an "
        "identical spec. This is a plumbing-correctness check (valid seats{} "
        "spec + correct S-table extraction) against the reference standard, NOT "
        "an independent algorithm re-derivation. SKIP-graceful when the binary "
        "or R seasonal is unavailable; the run_tsl invariants still enforce a "
        "correct decomposition R-independently."
    )
    DGP_N = 120
    PERIOD = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_seasonal_dgp(seed=seed, n=self.DGP_N, period=self.PERIOD)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        y = np.asarray(fixture["y"], dtype=np.float64)
        seats = _run_engine("seats", y, self.PERIOD)
        x11 = _run_engine("x11", y, self.PERIOD)

        sa, tr = seats["seasadj"], seats["trend"]
        se, ir, orig = seats["seasonal"], seats["irregular"], seats["original"]

        # --- ALWAYS-ON invariants (R-independent; a broken S-table extraction
        # fails here loudly rather than SKIPping). ---
        comps = {"seasadj": sa, "trend": tr, "seasonal": se, "irregular": ir}
        for nm, v in comps.items():
            if v.size != orig.size or v.size == 0 or not np.all(np.isfinite(v)):
                raise RuntimeError(
                    f"SEATS extraction invariant failed: '{nm}' is empty/short/"
                    f"non-finite (size {v.size} vs original {orig.size}) -- the "
                    f"S-table was not read correctly."
                )
        # Reconstruction identity, mode-agnostic: multiplicative SA*seasonal or
        # additive SA+seasonal must reproduce the original.
        with np.errstate(all="ignore"):
            rel_mult = np.nanmax(np.abs(sa * se - orig) / np.maximum(np.abs(orig), 1e-9))
            rel_add = np.nanmax(np.abs(sa + se - orig) / np.maximum(np.abs(orig), 1e-9))
        recon_rel = float(min(rel_mult, rel_add))
        if recon_rel > 1e-3:
            raise RuntimeError(
                f"SEATS reconstruction invariant failed: neither SA*seasonal "
                f"(rel {rel_mult:.2e}) nor SA+seasonal (rel {rel_add:.2e}) "
                f"reproduces the original -- S-tables likely mis-mapped."
            )
        # SEATS must materially differ from X-11 on the same series (the method
        # branch actually switched, not silently still writing x11{}).
        seats_vs_x11 = float(np.nanmax(np.abs(sa - x11["seasadj"])))
        scale = float(np.nanmean(np.abs(x11["seasadj"]))) or 1.0
        if seats_vs_x11 / scale < 1e-4:
            raise RuntimeError(
                f"SEATS == X-11 invariant failed: SA differs by only "
                f"{seats_vs_x11:.3e} (rel {seats_vs_x11/scale:.2e}) -- the method "
                f"branch did not switch to SEATS."
            )
        return {
            "seasadj": sa, "trend": tr,
            "method_used": seats.get("method"),
            "recon_rel": recon_rel,
            "seats_vs_x11_rel": seats_vs_x11 / scale,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        # seas() defaults to SEATS adjustment. RPackageMissingError -> SKIP.
        r_code = rf"""
            suppressPackageStartupMessages({{ library(seasonal) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            y_ts <- ts(y, start = c(2010, 1), frequency = {self.PERIOD})
            res <- seas(y_ts)
            seasadj <- as.numeric(final(res))
            trend <- as.numeric(trend(res))
            write.table(matrix(seasadj, ncol=1), "{{{{OUTPUT_seasadj}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(trend, ncol=1), "{{{{OUTPUT_trend}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code, inputs={"y": y.reshape(-1, 1)},
            output_names=["seasadj", "trend"], timeout_sec=120,
            capture_versions_for=["seasonal"],
        )
        return {
            "seasadj": np.asarray(outputs["seasadj"], dtype=np.float64).reshape(-1),
            "trend": np.asarray(outputs["trend"], dtype=np.float64).reshape(-1),
            "seasonal_version": versions.get("seasonal", "unknown"),
        }

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        n_common = min(len(tsl["seasadj"]), len(ref["seasadj"]))
        primary = {
            "seasadj": _compare_vector(
                tsl["seasadj"][:n_common], ref["seasadj"][:n_common], ladder["primary"],
            ),
            "trend": _compare_vector(
                tsl["trend"][:n_common], ref["trend"][:n_common], ladder["primary"],
            ),
        }
        statuses = [primary[k]["status"] for k in primary]
        outcome = ("BLOCK" if "BLOCK" in statuses else
                   ("CAVEAT" if "CAVEAT" in statuses else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "period": int(self.PERIOD),
                "method_used": tsl.get("method_used"),
                "recon_rel": tsl.get("recon_rel"),
                "seats_vs_x11_rel": tsl.get("seats_vs_x11_rel"),
                "seasonal_version": ref.get("seasonal_version", "unknown"),
            },
        )
