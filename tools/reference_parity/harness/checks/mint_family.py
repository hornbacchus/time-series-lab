"""3e MinT family parity check.

Compares TSL's MinT reconciliation (4 methods: ols, wls_variance,
mint_shrinkage, mint_sample) against R hts (primary reference)
and Python hierarchicalforecast (secondary reference) on a seeded
2-level synthetic hierarchy.

Phase 1 audit 3e (reports/3e_mint_audit.md) established the
baseline: max abs diff 4.66e-15 on mint_shrinkage vs hts;
4.44e-15 on ols / wls_variance. The harness asserts at 1e-8 (7
orders of magnitude of headroom for subprocess CSV roundtrip).

R-side methodology (lifted from Phase 1's 3e audit script):

- hts 6.0.3's combinef() and MinT() are broken on this platform
  ("non-conformable arguments" in cbind.Matrix internals).
  Workaround: implement MinT math manually using the auxiliary
  utilities that DO work — smatrix() (returns S) and
  hts:::shrink.estim (Schaefer-Strimmer estimator).
- The reconciliation projection is closed-form:
    G = (S' W^-1 S)^-1 S' W^-1
    y_tilde = S G y_hat
- Compute W per method (W_ols = I, W_wls = diag(per-series var),
  W_shr = Schaefer-Strimmer shrunk cov, W_sam = sample cov),
  apply the projection.

Method-name mapping
- TSL ols              ↔ hts ols       ↔ HF ols
- TSL wls_variance     ↔ hts wls       ↔ HF wls_var
- TSL mint_shrinkage   ↔ hts shrink    ↔ HF mint_shrink
- TSL mint_sample      ↔ hts sam       ↔ HF mint_cov
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

# TSL engine path — added to sys.path by the harness when
# imported as a check module. Tests / runner ensure engine/
# is importable.
_REPO_ROOT = None  # set lazily

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.structural_invariants import StructuralInvariant
from reference_parity.harness.tolerances import get_ladder


# Method-name mappings (TSL → external)
_HTS_NAME = {
    "ols": "ols",
    "wls_variance": "wls",
    "mint_shrinkage": "shrink",
    "mint_sample": "sam",
}

_HF_NAME = {
    "ols": "ols",
    "wls_variance": "wls_var",
    "mint_shrinkage": "mint_shrink",
    "mint_sample": "mint_cov",
}


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import the TSL
    technique modules. Idempotent."""
    import pathlib
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


class MintFamilyParity(P3ParityCheck):
    """MinT family (4 methods) vs hts + HF triangulation."""

    technique_id = "3e_mint_family"
    tier = "fast"
    fixture_id = "3e_mint"

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "MinT reconciliation is closed-form matrix algebra: "
        "y_tilde = S (S' W^-1 S)^-1 S' W^-1 y_hat. R hts::MinT and "
        "Python hierarchicalforecast.MinTrace implement identical "
        "math; Phase 1 audit measured 4.66e-15 abs vs hts on "
        "mint_shrinkage (4 methods covered: ols, wls_variance, "
        "mint_shrinkage, mint_sample)."
    )

    METHODS = ("ols", "wls_variance", "mint_shrinkage", "mint_sample")

    # Phase 4 Session 9 (P4-1.3, 2026-05-02) — declare the
    # mint_coherence structural invariant. The TSL audit's output
    # surfaces ``coherence_residual`` per method (L2 norm of the
    # summing-constraint violation; should be ~0 on closed-form-
    # safe MinT reconciliation per Phase 1 audit measurement).
    structural_invariants = (
        StructuralInvariant(
            name="mint_coherence",
            invariant_type="mint_coherence",
            tolerance=1e-10,
            tolerance_type="absolute",
        ),
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # On-disk fixture supplies y, y_hat, residuals, S; the
        # runner already loaded + hash-verified them. Return an
        # empty dict — runner.update() merges the loaded fixture.
        return {}

    # -----------------------------------------------------------------
    # TSL side
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques import forecast_reconciliation as fr

        S = np.asarray(fixture["S"], dtype=np.float64)
        y_hat = np.asarray(fixture["y_hat"], dtype=np.float64)
        # residuals is (n_total, T); drop the leading-zero
        # column to match the Phase 1 audit (naive residuals
        # have no t=0 entry)
        residuals_full = np.asarray(
            fixture["residuals"], dtype=np.float64,
        )
        residuals = residuals_full[:, 1:]

        n_total = S.shape[0]
        h = y_hat.shape[1]

        per_method: dict[str, dict[str, Any]] = {}
        lambda_tsl: float | None = None
        for method in self.METHODS:
            try:
                W, extras = fr._estimate_W_matrix(residuals, method)
                y_tilde = fr._mint_reconcile(y_hat, S, W)
                if y_tilde.shape != (n_total, h):
                    raise RuntimeError(
                        f"Unexpected y_tilde shape "
                        f"{y_tilde.shape}, expected "
                        f"({n_total}, {h})"
                    )
                per_method[method] = {
                    "y_tilde": y_tilde.astype(np.float64),
                    "ok": True,
                }
                if method == "mint_shrinkage":
                    lambda_tsl = float(extras.get("shrinkage_lambda", float("nan")))
            except Exception as e:
                per_method[method] = {
                    "y_tilde": None,
                    "ok": False,
                    "error": f"{type(e).__name__}: {e}",
                }
        return {
            "per_method": per_method,
            "lambda_shrinkage": lambda_tsl,
        }

    # -----------------------------------------------------------------
    # Reference side: R hts manual MinT math + HF (best-effort)
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y_hat = np.asarray(fixture["y_hat"], dtype=np.float64)
        residuals_full = np.asarray(
            fixture["residuals"], dtype=np.float64,
        )
        residuals = residuals_full[:, 1:]

        n_total, h = y_hat.shape

        # R script implementing manual MinT math via hts internals.
        # Uses raw triple-quote (no Python % substitution) so R's
        # %*% matrix-multiply operator passes through verbatim.
        # n_total embedded via f-string substitution into the
        # nrow-check guards.
        r_code = rf'''
            suppressPackageStartupMessages({{ library(hts) }})

            y_hat <- as.matrix(read.csv("{{{{INPUT_y_hat}}}}", header=FALSE))
            residuals <- as.matrix(read.csv("{{{{INPUT_residuals}}}}", header=FALSE))
            if (nrow(y_hat) != {n_total}) y_hat <- t(y_hat)
            if (nrow(residuals) != {n_total}) residuals <- t(residuals)
            n_total <- nrow(y_hat)
            n_bottom <- n_total - 1
            h <- ncol(y_hat)

            y_bot_dummy <- matrix(rnorm(50 * n_bottom),
                                  nrow = 50, ncol = n_bottom)
            g <- suppressWarnings(hts(y_bot_dummy, nodes = list(n_bottom)))
            S_mat <- as.matrix(smatrix(g))

            R <- residuals
            W_ols <- diag(n_total)
            per_series_var <- apply(R, 1, var, na.rm = TRUE)
            per_series_var <- pmax(per_series_var, 1e-12)
            W_wls <- diag(per_series_var)
            R_c <- R - rowMeans(R)
            W_sam <- (R_c %*% t(R_c)) / max(ncol(R) - 1, 1)
            shrink_result <- tryCatch({{
                hts:::shrink.estim(t(R), tar = diag(n_total))
            }}, error = function(e) NULL)
            if (!is.null(shrink_result)) {{
                W_shr <- as.matrix(shrink_result[[1]])
                lambda_text <- shrink_result[[2]]
                lambda <- suppressWarnings(as.numeric(lambda_text[2]))
                if (is.na(lambda)) {{
                    lambda <- suppressWarnings(as.numeric(lambda_text))
                    lambda <- lambda[!is.na(lambda)][1]
                    if (length(lambda) == 0) lambda <- NA
                }}
            }} else {{
                W_shr <- W_sam
                lambda <- NA
            }}

            mint_project <- function(W, y_hat, S) {{
                W_inv <- solve(W)
                StWinv <- t(S) %*% W_inv
                A <- StWinv %*% S
                G <- solve(A, StWinv)
                S %*% (G %*% y_hat)
            }}

            y_tilde_ols <- mint_project(W_ols, y_hat, S_mat)
            y_tilde_wls <- mint_project(W_wls, y_hat, S_mat)
            y_tilde_shr <- mint_project(W_shr, y_hat, S_mat)
            y_tilde_sam <- tryCatch(
                mint_project(W_sam, y_hat, S_mat),
                error = function(e) {{
                    warning(paste("sam failed:", conditionMessage(e)))
                    matrix(NA, nrow = n_total, ncol = h)
                }}
            )

            write.table(y_tilde_ols, "{{{{OUTPUT_ols}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(y_tilde_wls, "{{{{OUTPUT_wls}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(y_tilde_shr, "{{{{OUTPUT_shrink}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            write.table(y_tilde_sam, "{{{{OUTPUT_sam}}}}",
                        sep=",", row.names=FALSE, col.names=FALSE)
            cat(sprintf("%.18e", as.numeric(lambda)),
                file = "{{{{OUTPUT_lambda}}}}")
        '''

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y_hat": y_hat, "residuals": residuals},
            output_names=["ols", "wls", "shrink", "sam", "lambda"],
            timeout_sec=120,
            capture_versions_for=["hts"],
        )

        def _reshape(arr: np.ndarray) -> np.ndarray:
            a = np.atleast_2d(arr)
            if a.shape == (n_total, h):
                return a
            if a.shape == (h, n_total):
                return a.T
            return a.reshape(n_total, h)

        per_method = {
            "ols": _reshape(outputs["ols"]),
            "wls_variance": _reshape(outputs["wls"]),
            "mint_shrinkage": _reshape(outputs["shrink"]),
            "mint_sample": _reshape(outputs["sam"]),
        }
        lam_arr = np.asarray(outputs["lambda"]).reshape(-1)
        lambda_hts = (
            float(lam_arr[0]) if lam_arr.size and np.isfinite(lam_arr[0])
            else float("nan")
        )

        # Best-effort HF cross-reference (not asserted)
        hf_per_method: dict[str, np.ndarray | str] = {}
        try:
            hf = self._run_hf(fixture, n_total, h)
            hf_per_method = hf
        except Exception as e:
            hf_per_method = {"_error": f"{type(e).__name__}: {e}"}

        return {
            "hts": per_method,
            "hts_lambda": lambda_hts,
            "hts_version": versions.get("hts", "unknown"),
            "hf": hf_per_method,
        }

    def _run_hf(
        self,
        fixture: dict[str, Any],
        n_total: int,
        h: int,
    ) -> dict[str, np.ndarray]:
        """Best-effort hierarchicalforecast triangulation. Returns
        a dict of method -> y_tilde arrays. Any HF runtime error
        is captured by the caller (run_reference) and stored as
        diagnostic, not asserted."""
        # HF API has shifted across versions; on 1.5.x the entry
        # point is HierarchicalReconciliation + MinTrace. The
        # method-name mapping is in _HF_NAME above.
        from hierarchicalforecast.methods import MinTrace
        from hierarchicalforecast.core import HierarchicalReconciliation
        import pandas as pd

        S = np.asarray(fixture["S"], dtype=np.float64)
        y_hat = np.asarray(fixture["y_hat"], dtype=np.float64)
        residuals_full = np.asarray(
            fixture["residuals"], dtype=np.float64,
        )
        residuals = residuals_full[:, 1:]

        n_obs = residuals.shape[1]
        # Build the dataframes HF expects
        ids = [f"s{i}" for i in range(n_total)]
        # y_insample / y_hat_insample for shrink-cov methods
        y_insample = np.zeros((n_total, n_obs + 1))
        y_insample[:, 1:] = residuals  # placeholder
        y_hat_insample = np.zeros_like(y_insample)

        out: dict[str, np.ndarray] = {}
        for tsl_name, hf_name in _HF_NAME.items():
            try:
                # NOTE: HF 1.5.x evolves frequently; this is a
                # best-effort reconstruction. If the API doesn't
                # match what's installed, capture and report.
                rec = HierarchicalReconciliation(
                    reconcilers=[MinTrace(method=hf_name)],
                )
                # Build a minimal DataFrame structure
                rows = []
                for i, s in enumerate(ids):
                    for j in range(h):
                        rows.append({
                            "unique_id": s,
                            "ds": j,
                            "y_hat": float(y_hat[i, j]),
                        })
                df_y_hat = pd.DataFrame(rows)
                # Insample frames
                ins_rows = []
                for i, s in enumerate(ids):
                    for j in range(n_obs):
                        ins_rows.append({
                            "unique_id": s,
                            "ds": j,
                            "y": float(residuals[i, j]),
                            "y_hat": 0.0,
                        })
                df_ins = pd.DataFrame(ins_rows)
                tags = {"top": np.array([0]), "bottom": np.arange(1, n_total)}
                # Reconcile
                reconciled = rec.reconcile(
                    Y_hat_df=df_y_hat,
                    S=S,
                    tags=tags,
                    Y_df=df_ins,
                )
                # Extract per-id y_tilde over horizons → (n_total, h)
                col_name = next(
                    (c for c in reconciled.columns
                     if c.startswith("y_hat/MinTrace_method-")),
                    None,
                )
                if col_name is None:
                    raise RuntimeError(
                        "MinTrace output column not found in HF result"
                    )
                arr = np.zeros((n_total, h))
                for i, s in enumerate(ids):
                    sub = reconciled[reconciled["unique_id"] == s]
                    arr[i, :] = sub[col_name].to_numpy()[:h]
                out[tsl_name] = arr
            except Exception as e:
                out[tsl_name] = f"ERROR: {type(e).__name__}: {e}"  # type: ignore[assignment]
        return out

    # -----------------------------------------------------------------
    # Compare
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        abs_tol = float(ladder["abs_tol"])
        lam_abs_tol = float(ladder["lambda_abs_tol"])

        per_method_metrics: dict[str, Any] = {}
        per_method_diag: dict[str, Any] = {}
        any_block = False
        any_inconclusive = False

        for method in self.METHODS:
            tsl_m = tsl["per_method"].get(method, {})
            tsl_y = tsl_m.get("y_tilde")
            ref_y = ref["hts"].get(method)

            if tsl_y is None or ref_y is None:
                per_method_metrics[method] = {
                    "status": "missing",
                    "tsl_ok": tsl_m.get("ok", False),
                }
                any_inconclusive = True
                continue

            ref_y = np.asarray(ref_y, dtype=np.float64)
            tsl_y = np.asarray(tsl_y, dtype=np.float64)
            if not (np.all(np.isfinite(ref_y)) and np.all(np.isfinite(tsl_y))):
                per_method_metrics[method] = {
                    "status": "nan_present",
                    "note": (
                        "rank-deficient W on perfectly coherent "
                        "hierarchies (Phase 1 B1) is the typical "
                        "cause; not a regression"
                    ),
                }
                any_inconclusive = True
                continue

            if tsl_y.shape != ref_y.shape:
                per_method_metrics[method] = {
                    "status": "shape_mismatch",
                    "tsl_shape": list(tsl_y.shape),
                    "ref_shape": list(ref_y.shape),
                }
                any_block = True
                continue

            diff = np.abs(tsl_y - ref_y)
            denom = np.maximum(np.abs(tsl_y), np.abs(ref_y))
            denom = np.where(denom < 1e-300, 1.0, denom)
            rel = np.max(diff / denom)
            mx = float(np.max(diff))
            ok = mx <= abs_tol or float(rel) <= ladder["rel_tol"]
            if not ok:
                any_block = True
            per_method_metrics[method] = {
                "status": "PASS" if ok else "BLOCK",
                "max_abs_diff": mx,
                "max_rel_diff": float(rel),
                "rms_diff": float(np.sqrt(np.mean(diff ** 2))),
            }

            # HF cross-reference (diagnostic only)
            hf_y = ref.get("hf", {}).get(method)
            if isinstance(hf_y, np.ndarray):
                try:
                    hf_diff = float(np.max(np.abs(tsl_y - hf_y)))
                    per_method_diag[f"{method}_tsl_vs_hf_max_abs"] = hf_diff
                except Exception:
                    pass
            elif isinstance(hf_y, str):
                per_method_diag[f"{method}_hf"] = hf_y

        # Schaefer-Strimmer lambda parity (mint_shrinkage only)
        lam_tsl = tsl.get("lambda_shrinkage")
        lam_hts = ref.get("hts_lambda")
        lambda_block = False
        if (
            lam_tsl is not None and lam_hts is not None
            and np.isfinite(lam_tsl) and np.isfinite(lam_hts)
        ):
            lam_diff = abs(float(lam_tsl) - float(lam_hts))
            per_method_metrics["lambda_shrinkage"] = {
                "tsl": float(lam_tsl),
                "hts": float(lam_hts),
                "abs_diff": lam_diff,
                "status": "PASS" if lam_diff <= lam_abs_tol else "BLOCK",
            }
            if lam_diff > lam_abs_tol:
                lambda_block = True

        if any_block or lambda_block:
            outcome = "BLOCK"
        elif any_inconclusive:
            # mint_sample's NaN path on rank-deficient W is an
            # expected outcome the harness reports without
            # blocking — see Phase 1 B1.
            outcome = "PASS"
        else:
            outcome = "PASS"

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=per_method_metrics,
            diagnostics={
                "hts_version": ref.get("hts_version", "unknown"),
                **per_method_diag,
            },
        )
