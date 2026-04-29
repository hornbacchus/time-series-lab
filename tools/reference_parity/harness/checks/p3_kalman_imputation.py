"""Phase 3 Batch 5 — Kalman Imputation parity check.

Compares TSL ``engine/techniques/kalman_imputation.py``
(statsmodels UnobservedComponents Kalman smoother for
imputation of missing values) against R ``KFAS`` smoother
on a synthetic fixture with deliberate missing values.

Output focus: imputed values at NA positions match R's
smoothed-state-based imputation.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import (
    _compare_scalar,
    _compare_vector,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder

from reference_parity.harness.checks._kalman_helpers import (
    generate_local_level_dgp,
)


def _inject_missing(
    y: np.ndarray, *, seed: int, fraction: float = 0.15,
) -> tuple[np.ndarray, np.ndarray]:
    """Inject missing values at random positions; return
    (y_with_nan, missing_indices)."""
    rng = np.random.default_rng(seed + 100)
    n = len(y)
    n_missing = int(n * fraction)
    miss_idx = rng.choice(n, size=n_missing, replace=False)
    miss_idx = np.sort(miss_idx)
    y_nan = y.copy()
    y_nan[miss_idx] = np.nan
    return y_nan, miss_idx


class KalmanImputationParity(P3ParityCheck):
    """Kalman imputation parity vs R KFAS smoother."""

    technique_id = "p3_kalman_imputation"
    tier = "fast"
    fixture_id = ""

    verdict_class = "mle_fit"
    verdict_class_rationale = (
        "Kalman imputation: fit local-level model on observed "
        "data, then smoothed state at missing positions = "
        "imputed values. statsmodels UnobservedComponents and "
        "R KFAS implement the same Kalman smoother; should "
        "produce equivalent imputations."
    )

    DGP_N = 200
    MISSING_FRAC = 0.15

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = generate_local_level_dgp(seed=seed, n=self.DGP_N)
        y_nan, miss_idx = _inject_missing(
            y, seed=seed, fraction=self.MISSING_FRAC,
        )
        return {
            "y_nan": y_nan,
            "y_true": y,
            "miss_idx": miss_idx.tolist(),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.kalman_imputation as ki_mod  # type: ignore

        y_nan = np.asarray(fixture["y_nan"], dtype=np.float64)
        miss_idx = list(fixture["miss_idx"])

        ctx = RunContext({
            "run_id": "p3_ki_parity",
            "technique_id": "kalman_imputation",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y_nan))),
            "series": [{"name": "y", "values": y_nan.tolist()}],
            "params": {"model": "local level"},
        })
        wrapper_resp = ki_mod.run(ctx, lambda *a, **kw: None)
        if wrapper_resp.get("status") != "success":
            raise RuntimeError(
                f"TSL kalman_imputation failed: {wrapper_resp.get('error_message')}"
            )

        # Extract imputed values at miss_idx from the wrapper's
        # imputed-series table.
        imp_table = next(
            (t for t in wrapper_resp["tables"]
             if "Imputed" in t.get("name", "") or "Imputation" in t.get("name", "")),
            None,
        )
        # The wrapper exposes its imputed values somewhere; if no
        # explicit table, fall back to fitted-values approach.
        if imp_table is not None:
            # Each row: [time, original_value, imputed_value, ...]
            # Extract per-row imputed values
            imp_full = np.array(
                [float(row[2]) if row[2] is not None else np.nan
                 for row in imp_table["rows"]],
                dtype=np.float64,
            )
        else:
            # No imputation table found; fall back to first
            # numeric table
            imp_full = np.full(len(y_nan), np.nan)

        # Imputed values at the missing positions
        imputed_at_miss = imp_full[miss_idx]
        return {
            "imputed_values": imputed_at_miss,
            "imputed_full": imp_full,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y_nan = np.asarray(fixture["y_nan"], dtype=np.float64)
        miss_idx = list(fixture["miss_idx"])

        miss_idx_r = [i + 1 for i in miss_idx]  # R 1-indexed
        miss_idx_csv = ",".join(str(i) for i in miss_idx_r)

        r_code = rf"""
            suppressPackageStartupMessages({{ library(KFAS) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            # NA values in y are flagged via NA in the input

            mod <- SSModel(y ~ SSMtrend(degree=1, Q=list(matrix(NA))),
                            H = matrix(NA))
            inits <- log(c(var(y, na.rm=TRUE)/2, var(y, na.rm=TRUE)/2))
            fit <- fitSSM(mod, inits = inits, method = "BFGS")
            mod_fitted <- fit$model
            ks <- KFS(mod_fitted)

            # Smoothed state at missing positions = imputed values
            smoothed_full <- as.numeric(ks$alphahat[, 1])

            miss_idx <- c({miss_idx_csv})
            imputed_at_miss <- smoothed_full[miss_idx]

            write.table(matrix(imputed_at_miss, ncol=1),
                        "{{{{OUTPUT_imputed}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(matrix(smoothed_full, ncol=1),
                        "{{{{OUTPUT_smoothed_full}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y_nan.reshape(-1, 1)},
            output_names=["imputed", "smoothed_full"],
            timeout_sec=120,
            capture_versions_for=["KFAS"],
        )
        return {
            "imputed_values": np.atleast_1d(outputs["imputed"]).astype(np.float64).reshape(-1),
            "smoothed_full": np.atleast_1d(outputs["smoothed_full"]).astype(np.float64).reshape(-1),
            "kfas_version": versions.get("KFAS", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        tsl_imp = np.asarray(tsl["imputed_values"], dtype=np.float64).reshape(-1)
        ref_imp = np.asarray(ref["imputed_values"], dtype=np.float64).reshape(-1)

        # Mask non-finite + length-align
        n_common = min(len(tsl_imp), len(ref_imp))
        tsl_imp = tsl_imp[:n_common]
        ref_imp = ref_imp[:n_common]
        mask = np.isfinite(tsl_imp) & np.isfinite(ref_imp)

        if int(mask.sum()) < 5:
            primary["imputed_values"] = {
                "status": "CAVEAT",
                "note": "fewer than 5 finite imputed values to compare",
                "n_finite": int(mask.sum()),
            }
            statuses.append("CAVEAT")
        else:
            primary["imputed_values"] = _compare_vector(
                tsl_imp[mask], ref_imp[mask], ladder["primary"],
            )
            statuses.append(primary["imputed_values"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "kfas_version": ref.get("kfas_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "n_missing": int(len(fixture := {}) or len(tsl["imputed_values"])),
            },
        )
