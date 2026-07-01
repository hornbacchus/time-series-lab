"""3d Johansen Bartlett/Reimers correction parity check.

Validates TSL's Johansen cointegration test (with Reimers 1992
finite-sample Bartlett correction) against:

- **R urca::ca.jo** — primary reference. Phase 1 audit 3d's
  baseline. urca uses a different reduced-rank regression
  parametrization than statsmodels; documented Phase 1 finding
  is that small cross-package divergence (10-30%% on small T)
  exists between urca and statsmodels. Tolerance accommodates.
- **Python statsmodels.tsa.vector_ar.vecm.coint_johansen**
  (Q4 triangulation) — TSL wraps statsmodels internally, so
  TSL vs statsmodels should agree at machine precision. Adding
  the cross-reference urca-vs-statsmodels detects package-level
  divergences independent of TSL.

Architectural decisions (locked in Session 3a design):

- **Q1.** Skip critical-value comparison entirely. CVs are a
  methodology choice between Osterwald-Lenum (statsmodels) and
  urca's tables — not a TSL correctness question.
- **Q4.** Triple-reference: TSL vs urca, TSL vs statsmodels,
  urca vs statsmodels.

**TSL audit-field gaps.** TSL's audit_fields exposes:
- ``trace_stat_at_decision`` (scalar at boundary rank, not full
  vector)
- ``bartlett_factor`` (rounded to 6 decimals)
- ``trace_stat_corrected`` (rounded to 4 decimals)
- ``eigenvalues`` (rounded to 6 decimals)

The full raw trace-stat vector is NOT exposed. Per Phase 1 audit
3d's pattern, this check calls ``statsmodels.coint_johansen``
directly inside ``run_tsl`` to obtain the full-precision raw
trace stats — which is what TSL's wrapper uses internally.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.structural_invariants import StructuralInvariant
from reference_parity.harness.tolerances import get_ladder


_DET_ORDER_D = {-1: 0, 0: 1, 1: 2}


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import TSL helpers."""
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


class JohansenBartlettParity(P3ParityCheck):
    """Johansen test + Reimers correction triangulation."""

    technique_id = "3d_johansen_bartlett"
    tier = "fast"
    fixture_id = "3d_johansen"

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Johansen trace statistic is closed-form generalized "
        "eigenvalue problem on residual covariance. urca::ca.jo "
        "vs statsmodels coint_johansen agree at machine precision "
        "modulo small reduced-rank-regression parameterization "
        "differences (documented Pattern J at 50.0 abs). Reimers "
        "correction (T-n*p)/T is pure arithmetic; bit-exact."
    )

    # Phase 4 Session 9 (P4-1.3, 2026-05-02) — declare the
    # vecm_cointegration_rank structural invariant. Engine
    # audit-field surface (cointegrating_rank + determined_rank_trace
    # aliases) was added at S8; structural-invariants registry
    # checker was registered at Phase 3 Session 7. tolerance=0
    # → strict integer match expected.
    structural_invariants = (
        StructuralInvariant(
            name="vecm_cointegration_rank",
            invariant_type="vecm_cointegration_rank",
            tolerance=0.0,
            tolerance_type="absolute",
        ),
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # On-disk fixture supplies y, rank_true, T, n, lag_order_p.
        return {}

    # -----------------------------------------------------------------
    # TSL side
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        # Use statsmodels.coint_johansen directly (matches what
        # TSL's wrapper does internally on the same data) to
        # access full-precision raw trace stats — the wrapper's
        # audit_fields rounds them.
        from statsmodels.tsa.vector_ar.vecm import coint_johansen
        from techniques.johansen_cointegration import _bartlett_factor

        y = np.asarray(fixture["y"], dtype=np.float64)
        T = int(np.asarray(fixture["T"]))
        n = int(np.asarray(fixture["n"]))
        p = int(np.asarray(fixture["lag_order_p"]))
        det_order = 0  # standard local-level VECM with constant

        # statsmodels k_ar_diff is the VECM lag order; matches
        # TSL's "p" and is the same value passed to the wrapper.
        # Phase 1 audit 3d's pattern: pass det_order=0,
        # k_ar_diff=p directly.
        result = coint_johansen(y, det_order=det_order, k_ar_diff=p - 1)
        trace_raw = np.asarray(result.lr1, dtype=np.float64)
        eigenvalues = np.asarray(result.eig, dtype=np.float64)

        # TSL's bartlett_factor formula: (T - n*p - d) / T.
        # statsmodels k_ar_diff = p - 1 (urca K = p maps to
        # statsmodels k_ar_diff = K - 1). Use TSL's helper to
        # compute the expected value with TSL's exact formula.
        expected_bartlett = _bartlett_factor(
            T=T, n=n, p=p - 1, det_order=det_order,
        )

        # Run TSL wrapper proper to capture its rounded
        # bartlett_factor + trace_stat_corrected fields.
        from techniques.base import RunContext
        from techniques import johansen_cointegration as jc
        ctx = RunContext({
            "run_id": "parity_3d",
            "technique_id": "johansen_cointegration",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "daily",
            "time": [f"d{i}" for i in range(T)],
            "series": [
                {"name": "y1", "values": y[:, 0].tolist()},
                {"name": "y2", "values": y[:, 1].tolist()},
            ],
            "params": {
                # k_ar_diff = p - 1 (urca K=p <-> statsmodels k_ar_diff=p-1) so the
                # wrapper's rank invariant runs at the SAME lag as the direct
                # statsmodels arm (k_ar_diff=p-1) and urca (K=p). This was the INERT
                # `lag_order` -- the engine reads `lag`/`k_ar_diff`, NEVER `lag_order`,
                # so the wrapper had been auto-selecting the lag; it coincided with
                # p-1 on this fixture (rank 1, lag 1 either way), but the intended
                # matched spec is now enforced rather than left to the coincidence.
                "k_ar_diff": p - 1,
                "det_order": det_order,
                "finite_sample_correction": True,
            },
        })
        wrapper_res = jc.run(ctx, lambda *a, **k: None)
        wrapper_audit = wrapper_res.get("audit_fields", {})

        return {
            "trace_raw": trace_raw,
            "eigenvalues": eigenvalues,
            "expected_bartlett": float(expected_bartlett),
            "wrapper_bartlett": wrapper_audit.get("bartlett_factor"),
            "wrapper_trace_corrected": wrapper_audit.get(
                "trace_stat_corrected",
            ),
            "wrapper_status": wrapper_res.get("status"),
            # Phase 5 S2-α-2-redux: expose cointegrating_rank for
            # vecm_cointegration_rank structural invariant
            # (engine wrapper audit_fields["cointegrating_rank"]
            # populated per Phase 4 S8 P4-1.2; Q-Field-α-2=(b)
            # per-session scope: ONLY rank field; Q-Field-α-3=(b)
            # NO try/except — engine API change → loud failure).
            "cointegrating_rank": wrapper_audit.get(
                "cointegrating_rank",
            ),
        }

    # -----------------------------------------------------------------
    # Reference side: R urca + Python statsmodels triangulation
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        p = int(np.asarray(fixture["lag_order_p"]))
        n = int(np.asarray(fixture["n"]))

        # urca::ca.jo: K is the number of lags in the LEVELS VAR,
        # which equals statsmodels k_ar_diff + 1. The fixture's
        # lag_order_p IS the urca K.
        K_urca = p

        r_code = rf'''
            suppressPackageStartupMessages({{ library(urca) }})
            y <- as.matrix(read.csv("{{{{INPUT_y}}}}", header=FALSE))
            colnames(y) <- c("y1", "y2")
            fit <- ca.jo(y, type = "trace", ecdet = "none",
                         K = {K_urca}, spec = "longrun")
            trace_stats <- as.numeric(fit@teststat)
            eigvals <- as.numeric(fit@lambda)
            cvals_5pct <- as.numeric(fit@cval[, 2])
            write.csv(data.frame(trace = trace_stats),
                      "{{{{OUTPUT_trace_raw}}}}", row.names = FALSE)
            write.csv(data.frame(lambda = eigvals),
                      "{{{{OUTPUT_eigvals}}}}", row.names = FALSE)
            write.csv(data.frame(cv = cvals_5pct),
                      "{{{{OUTPUT_cvals_5pct}}}}", row.names = FALSE)
        '''

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y},
            output_names=["trace_raw", "eigvals", "cvals_5pct"],
            timeout_sec=60,
            capture_versions_for=["urca"],
        )
        # urca returns trace stats in REVERSE order (r=n-1, ..., r=0)
        # while statsmodels returns r=0, ..., r=n-1. Reverse to align.
        urca_trace_raw = np.asarray(outputs["trace_raw"]).reshape(-1)[::-1]
        urca_eigvals = np.asarray(outputs["eigvals"]).reshape(-1)
        # urca cval matrix rows are also in REVERSE order; reverse
        # to align with trace_raw (r=0, ..., r=n-1 ordering).
        urca_cvals_5pct = np.asarray(outputs["cvals_5pct"]).reshape(-1)[::-1]

        # statsmodels triangulation
        from statsmodels.tsa.vector_ar.vecm import coint_johansen
        sm_result = coint_johansen(y, det_order=0, k_ar_diff=p - 1)
        sm_trace_raw = np.asarray(sm_result.lr1, dtype=np.float64)
        sm_eigvals = np.asarray(sm_result.eig, dtype=np.float64)

        # Phase 5 S2-α-2-redux: compute cointegrating_rank from
        # urca trace stats vs 5% critical values for
        # vecm_cointegration_rank structural invariant. Rank =
        # count of trace_stats[i] > cvals_5pct[i] (Johansen
        # convention: rejecting H0: r ≤ i implies rank > i).
        rank_5pct = int(np.sum(urca_trace_raw > urca_cvals_5pct))

        return {
            "urca_trace_raw": urca_trace_raw.astype(np.float64),
            "urca_eigvals": urca_eigvals.astype(np.float64),
            "urca_cvals_5pct": urca_cvals_5pct.astype(np.float64),
            "sm_trace_raw": sm_trace_raw,
            "sm_eigvals": sm_eigvals,
            "urca_version": versions.get("urca", "unknown"),
            "cointegrating_rank": rank_5pct,
        }

    # -----------------------------------------------------------------
    # Compare
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        metrics: dict[str, Any] = {}
        any_block = False

        # TSL vs urca raw trace stats
        any_block |= self._compare_arrays(
            tsl["trace_raw"], ref["urca_trace_raw"],
            ladder["trace_stat_raw_vs_urca"]["abs_tol"],
            ladder["trace_stat_raw_vs_urca"]["rel_tol"],
            "trace_stat_raw_vs_urca", metrics,
        )

        # TSL vs statsmodels (bitwise; same code)
        any_block |= self._compare_arrays(
            tsl["trace_raw"], ref["sm_trace_raw"],
            ladder["trace_stat_raw_vs_statsmodels"]["abs_tol"],
            ladder["trace_stat_raw_vs_statsmodels"]["rel_tol"],
            "trace_stat_raw_vs_statsmodels", metrics,
        )

        # urca vs statsmodels cross-reference
        xref_tol = float(
            ladder["urca_vs_statsmodels_xref"]["abs_tol"]
        )
        urca_sm_diff = float(
            np.max(np.abs(ref["urca_trace_raw"] - ref["sm_trace_raw"]))
        )
        urca_sm_ok = urca_sm_diff <= xref_tol
        metrics["urca_vs_statsmodels_xref"] = {
            "status": "PASS" if urca_sm_ok else "BLOCK",
            "max_abs_diff": urca_sm_diff,
            "tolerance": xref_tol,
            "note": (
                "documented cross-package divergence; threshold "
                "accommodates Phase 1 finding"
            ),
        }
        if not urca_sm_ok:
            any_block = True

        # Bartlett factor arithmetic check
        bf_tol = float(
            ladder["bartlett_factor_arithmetic"]["abs_tol"]
        )
        wrapper_bf = tsl.get("wrapper_bartlett")
        expected_bf = float(tsl["expected_bartlett"])
        if wrapper_bf is None:
            metrics["bartlett_factor_arithmetic"] = {
                "status": "BLOCK",
                "note": "TSL wrapper did not report bartlett_factor",
                "wrapper_status": tsl.get("wrapper_status"),
            }
            any_block = True
        else:
            bf_diff = abs(float(wrapper_bf) - expected_bf)
            bf_ok = bf_diff <= bf_tol
            metrics["bartlett_factor_arithmetic"] = {
                "status": "PASS" if bf_ok else "BLOCK",
                "tsl_reported": float(wrapper_bf),
                "formula_expected": expected_bf,
                "abs_diff": bf_diff,
                "tolerance": bf_tol,
                "note": (
                    "TSL audit field rounds to 6 decimals; floor "
                    "matches"
                ),
            }
            if not bf_ok:
                any_block = True

        # Corrected stat consistency: TSL's rounded
        # trace_stat_corrected vs (raw * bartlett_factor),
        # asserting TSL's reported value equals the formula
        # within rounding precision.
        cs_tol = float(
            ladder["trace_stat_corrected_consistency"]["abs_tol"]
        )
        wrapper_corrected = tsl.get("wrapper_trace_corrected")
        if wrapper_corrected is None:
            metrics["trace_stat_corrected_consistency"] = {
                "status": "BLOCK",
                "note": "TSL wrapper did not report trace_stat_corrected",
            }
            any_block = True
        else:
            corrected_arr = np.asarray(
                wrapper_corrected, dtype=np.float64,
            )
            expected_corrected = (
                tsl["trace_raw"] * expected_bf
            ).astype(np.float64)
            if corrected_arr.shape != expected_corrected.shape:
                metrics["trace_stat_corrected_consistency"] = {
                    "status": "shape_mismatch",
                    "tsl_shape": list(corrected_arr.shape),
                    "expected_shape": list(expected_corrected.shape),
                }
                any_block = True
            else:
                cs_diff = float(
                    np.max(np.abs(corrected_arr - expected_corrected))
                )
                cs_ok = cs_diff <= cs_tol
                metrics["trace_stat_corrected_consistency"] = {
                    "status": "PASS" if cs_ok else "BLOCK",
                    "max_abs_diff": cs_diff,
                    "tolerance": cs_tol,
                    "note": (
                        "TSL audit field rounds to 4 decimals; "
                        "floor matches"
                    ),
                }
                if not cs_ok:
                    any_block = True

        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics={
                "urca_version": ref.get("urca_version", "unknown"),
                "T": int(np.asarray(tsl.get("trace_raw")).shape[0])
                if "trace_raw" in tsl else None,
            },
        )

    @staticmethod
    def _compare_arrays(
        a: np.ndarray, b: np.ndarray,
        abs_tol: float, rel_tol: float,
        label: str, metrics: dict[str, Any],
    ) -> bool:
        a = np.asarray(a, dtype=np.float64).flatten()
        b = np.asarray(b, dtype=np.float64).flatten()
        if a.shape != b.shape:
            metrics[label] = {
                "status": "shape_mismatch",
                "a_shape": list(a.shape),
                "b_shape": list(b.shape),
            }
            return True
        diff = np.abs(a - b)
        denom = np.maximum(np.abs(a), np.abs(b))
        denom = np.where(denom < 1e-300, 1.0, denom)
        mx_abs = float(np.max(diff))
        mx_rel = float(np.max(diff / denom))
        ok = mx_abs <= float(abs_tol) or mx_rel <= float(rel_tol)
        metrics[label] = {
            "status": "PASS" if ok else "BLOCK",
            "max_abs_diff": mx_abs,
            "max_rel_diff": mx_rel,
            "rms_diff": float(np.sqrt(np.mean(diff ** 2))),
        }
        return not ok
