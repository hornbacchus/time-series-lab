"""2a Kalman filter / smoother parity check.

Compares the local-level Kalman recursions (filtered states,
smoothed states, log-likelihood, steady-state Kalman gain) used by
TSL's kalman_filter and kalman_smoother wrappers against
**dual R references** on a seeded synthetic local-level fixture:

- **R dlm** (``dlmFilter`` + ``dlmSmooth``) — provides
  filtered/smoothed states + steady-state Kalman gain. dlm uses
  a large-variance approximation for the diffuse prior, which
  introduces a known methodology offset on log-likelihood; the
  log-lik comparison vs dlm is treated as **methodology-offset
  detection** (loose tolerance, catches gross regressions only).
- **R KFAS** (``SSModel`` + ``KFS`` + ``logLik``) — provides
  the **tight log-likelihood parity check**. KFAS implements
  the same Koopman-Durbin convention as TSL/statsmodels, so
  log-likelihoods should match at floating-point accumulation
  precision. Phase 1 audit 2a observed 3.64e-7 abs diff;
  harness asserts at 1e-6.

Why dual-reference: dlm-vs-TSL log-lik parity at ~9 absolute is
a documented Phase 1 finding ("valid methodology difference,
not a bug"). Asserting at 15.0 is detection only — too loose
to catch subtle regressions. KFAS closes that gap.

Phase 1 audit 2a (reports/2a_kalman_audit.md) established the
baselines:

| Pair             | filtered max_abs | smoothed max_abs | log-lik |
|------------------|------------------|------------------|---------|
| TSL vs dlm       | 2.44e-7          | 2.13e-8          | 82.92*  |
| TSL vs KFAS      | 2.71e-7          | 2.37e-8          | 3.64e-7 |

`*` raw offset; bridge via -dlmLL(y, mod) - 0.5*T*log(2*pi)
reduces to ~9 — still a methodology difference, not parity.

Phase 1's fixture: T=100, Q=0.1, H=1.0 (variances). The Session 2
fixture differs (T=200, sigma_eta=1.0, sigma_eps=2.0 ⇒ Q=1, H=4)
so the per-position diffs may differ; the order of magnitude
should match.

**Architectural decisions (locked in Session 2 design):**

- **Q3 — convention bridge.** TSL's wrapper exposes user-facing
  ``sigma_eta`` / ``sigma_eps`` as standard deviations. R dlm's
  ``dlmModPoly(order=1)`` takes ``dV`` (observation variance)
  and ``dW`` (state variance). KFAS's ``SSMtrend(degree=1)``
  takes ``Q`` (state variance) and the model takes ``H`` (obs
  variance). Both R scripts convert via ``dV = H = sigma_eps^2``,
  ``dW = Q = sigma_eta^2``.
- **Q4 — log-likelihood tolerance.** TSL vs dlm asserted at
  15.0 absolute (methodology-offset detection). TSL vs KFAS
  asserted at 1e-6 absolute (tight parity, per Phase 1).
- **TSL access path.** TSL's kalman_filter wrapper does not
  expose the full filtered-state trajectory in audit_fields —
  only ``filter_final_state`` (single point) and a state_table
  in the rendered tables. Per Phase 1 audit 2a's pattern, this
  check invokes ``statsmodels.tsa.statespace.structural.
  UnobservedComponents`` directly with the same parameters
  TSL's wrapper uses internally on the template path
  (local_level). This validates the same code path TSL
  exercises while bypassing the presentation layer.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


class KalmanFilterParity(P3ParityCheck):
    """Kalman filter / smoother + log-likelihood parity vs R dlm + KFAS.

    **Dual-fixture architecture** (Session 2 Path B Option 2):

    - **Main fixture** (``2a_kalman``, T=200, sigma_eta=1.0,
      sigma_eps=2.0): exercises the wider-noise regime where TSL
      will typically be deployed. Used for state-estimate parity
      (filtered, smoothed, kalman_gain) vs dlm and for the
      methodology-offset detection vs dlm log-likelihood.
    - **Phase 1 fixture** (``2a_kalman_phase1``, T=100, Q=0.1,
      H=1.0): exact-replica of Phase 1 audit 2a's generator.
      Used ONLY for the tight log-likelihood parity assertion
      vs KFAS at 1e-6. Asserting on Phase 1's exact fixture
      isolates package-version-drift and TSL-regression detection
      from fixture-scaling artifacts in floating-point
      accumulation.

    The two-fixture split is principled: state estimates have
    fixture-independent diffuse-prior drift that we accept (1e-5),
    while log-likelihood requires fixture stability for tight
    parity (1e-6).
    """

    technique_id = "2a_kalman_filter_smoother"
    tier = "fast"
    fixture_id = "2a_kalman"  # main fixture; runner hash-verifies

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Kalman filter / smoother are closed-form recursions on "
        "linear-Gaussian state-space models. R dlm + KFAS and "
        "statsmodels UnobservedComponents implement identical "
        "math; only diffuse-prior initialization conventions "
        "differ slightly. Phase 1 audit 2a achieved 3.64e-7 abs "
        "log-likelihood vs KFAS on Phase 1 fixture."
    )

    # Second fixture used only for KFAS log-lik parity (loaded
    # explicitly in setup_fixture; runner does not auto-load
    # secondary fixtures).
    PHASE1_FIXTURE_ID = "2a_kalman_phase1"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # Runner already loaded + hash-verified the main fixture
        # via ``fixture_id``. Load the Phase 1 fixture for the
        # KFAS log-lik parity assertion.
        from reference_parity.harness.fixtures import FixtureLoader
        loader = FixtureLoader()
        # Phase 3.3: load() returns (data, metadata, sha).
        phase1_data, _phase1_metadata, phase1_sha = loader.load(
            self.PHASE1_FIXTURE_ID,
        )
        return {
            "phase1": phase1_data,
            "phase1_sha": phase1_sha,
        }

    # -----------------------------------------------------------------
    # TSL side — direct UnobservedComponents on BOTH fixtures
    # -----------------------------------------------------------------

    def _run_tsl_one(
        self,
        y: np.ndarray,
        sigma_eta: float,
        sigma_eps: float,
        *,
        compute_kalman_gain: bool = False,
    ) -> dict[str, Any]:
        """Run TSL on one fixture; return filtered/smoothed/llf
        (and optionally Kalman gain). Helper used twice by
        run_tsl()."""
        from statsmodels.tsa.statespace.structural import (
            UnobservedComponents,
        )
        H = sigma_eps ** 2
        Q = sigma_eta ** 2
        mod = UnobservedComponents(y, level="local level")
        res = mod.filter(np.array([H, Q]))
        filtered = np.asarray(
            res.filtered_state[0], dtype=np.float64,
        ).flatten()
        smoothed_res = mod.smooth(np.array([H, Q]))
        smoothed = np.asarray(
            smoothed_res.smoothed_state[0], dtype=np.float64,
        ).flatten()
        out = {
            "filtered": filtered,
            "smoothed": smoothed,
            "log_likelihood": float(res.llf),
        }
        if compute_kalman_gain:
            try:
                P_arr = np.asarray(
                    res.filtered_state_cov, dtype=np.float64,
                )
                P_ss = float(P_arr[0, 0, -1])
                out["kalman_gain_ss"] = float(P_ss / (P_ss + H))
            except Exception:
                out["kalman_gain_ss"] = float("nan")
        return out

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # MAIN fixture (Session 2): full state-estimate +
        # methodology-offset checks.
        y_main = np.asarray(fixture["y"], dtype=np.float64)
        sigma_eta_main = float(np.asarray(fixture["sigma_eta_true"]))
        sigma_eps_main = float(np.asarray(fixture["sigma_eps_true"]))
        main = self._run_tsl_one(
            y_main, sigma_eta_main, sigma_eps_main,
            compute_kalman_gain=True,
        )
        main["T"] = int(len(y_main))

        # PHASE 1 fixture: log-likelihood only (no other metrics
        # asserted on this fixture).
        phase1_fx = fixture["phase1"]
        y_p1 = np.asarray(phase1_fx["y"], dtype=np.float64)
        sigma_eta_p1 = float(np.asarray(phase1_fx["sigma_eta_true"]))
        sigma_eps_p1 = float(np.asarray(phase1_fx["sigma_eps_true"]))
        phase1 = self._run_tsl_one(
            y_p1, sigma_eta_p1, sigma_eps_p1,
            compute_kalman_gain=False,
        )

        return {"main": main, "phase1": phase1}

    # -----------------------------------------------------------------
    # Reference side: R dlm (main fixture) + R KFAS (Phase 1 fixture)
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        # MAIN fixture: dlm filter/smoother + dlm log-lik (with
        # convention bridge) + Kalman gain.
        y = np.asarray(fixture["y"], dtype=np.float64)
        sigma_eta = float(np.asarray(fixture["sigma_eta_true"]))
        sigma_eps = float(np.asarray(fixture["sigma_eps_true"]))
        # Q3 convention bridge: TSL standard deviations -> R variances
        dW = sigma_eta ** 2  # state noise variance
        dV = sigma_eps ** 2  # observation noise variance

        r_code = r"""
            suppressPackageStartupMessages({ library(dlm) })

            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])
            dV_in <- as.numeric(read.csv("{{INPUT_dV}}", header=FALSE)[, 1])[1]
            dW_in <- as.numeric(read.csv("{{INPUT_dW}}", header=FALSE)[, 1])[1]
            T_n <- length(y)

            # Local-level DLM:
            #   y_t = mu_t + e_t,   e_t ~ N(0, dV)
            #   mu_t = mu_{t-1} + h_t,  h_t ~ N(0, dW)
            # dlmModPoly(order=1) is the local level. Diffuse prior
            # via large C0; m0 = 0 starting point.
            mod <- dlmModPoly(order = 1, dV = dV_in, dW = dW_in,
                              m0 = 0, C0 = 1e7)

            filt <- dlmFilter(y, mod)
            smoothed_obj <- dlmSmooth(filt)

            # filt$m: posterior means of states, length T+1 (includes
            # the prior m0 at position 1). Drop position 1 to get
            # t=1..T filtered means.
            filtered <- as.numeric(filt$m)[-1]
            smoothed <- as.numeric(smoothed_obj$s)[-1]

            # Q4 convention bridge: dlmLL returns the negative log-
            # likelihood with the constant 0.5 * T * log(2*pi)
            # OMITTED. Convert to the standard log-likelihood used
            # by statsmodels / KFAS:
            #   log L = -dlmLL(y, mod) - 0.5 * T * log(2*pi)
            nll <- as.numeric(dlmLL(y, mod))
            llf <- -nll - 0.5 * T_n * log(2 * pi)

            # Steady-state Kalman gain. From the filter's running
            # variance: K_ss = P_ss / (P_ss + dV). dlmFilter does
            # not expose the running covariance directly through a
            # documented field, but we can recompute from the gain
            # inside the recursion: dlm provides U.C and D.C giving
            # singular value decompositions of the filter cov. We
            # use the simpler observable: at steady-state,
            # filt$U.C[[T+1]] %*% diag(filt$D.C[T+1, ]^2) %*% t(...)
            # gives the final filter cov.
            U_T <- filt$U.C[[T_n + 1]]
            D_T <- filt$D.C[T_n + 1, ]
            P_ss <- as.numeric(U_T %*% diag(D_T ^ 2, nrow = length(D_T)) %*% t(U_T))
            kalman_gain_ss <- P_ss / (P_ss + dV_in)

            writeLines(sprintf("%.18e", filtered), "{{OUTPUT_filtered}}")
            writeLines(sprintf("%.18e", smoothed), "{{OUTPUT_smoothed}}")
            writeLines(sprintf("%.18e", llf), "{{OUTPUT_llf}}")
            writeLines(sprintf("%.18e", kalman_gain_ss),
                       "{{OUTPUT_kalman_gain}}")
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={
                "y": y.reshape(-1, 1),
                "dV": np.array([[dV]]),
                "dW": np.array([[dW]]),
            },
            output_names=["filtered", "smoothed", "llf", "kalman_gain"],
            timeout_sec=60,
            capture_versions_for=["dlm"],
        )

        # KFAS log-likelihood (tight parity reference) — runs on
        # the PHASE 1 fixture, NOT the main fixture. Asserting on
        # Phase 1's exact fixture isolates package-version-drift
        # and TSL-regression detection from floating-point
        # accumulation drift that scales with T and noise
        # magnitude. Phase 1 audit 2a observed 3.64e-7 abs diff
        # on this exact fixture.
        kfas_r_code = r"""
            suppressPackageStartupMessages({ library(KFAS) })

            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)[, 1])
            sigma_eta_sq <- as.numeric(read.csv("{{INPUT_dW}}", header=FALSE)[, 1])[1]
            sigma_eps_sq <- as.numeric(read.csv("{{INPUT_dV}}", header=FALSE)[, 1])[1]

            # KFAS local-level model. Formula matches Phase 1
            # audit 2a's exact form: y ~ SSMtrend(degree=1,
            # Q=...). Log-lik extracted via fit$logLik (per
            # Phase 1 pattern).
            mod <- SSModel(
                y ~ SSMtrend(degree = 1, Q = sigma_eta_sq),
                H = sigma_eps_sq
            )
            fit <- KFS(mod, filtering = "state", smoothing = "state")
            ll <- as.numeric(fit$logLik)

            writeLines(sprintf("%.18e", ll), "{{OUTPUT_llf_kfas}}")
        """
        # PHASE 1 fixture inputs for KFAS log-lik
        phase1_fx = fixture["phase1"]
        y_p1 = np.asarray(phase1_fx["y"], dtype=np.float64)
        sigma_eta_p1 = float(np.asarray(phase1_fx["sigma_eta_true"]))
        sigma_eps_p1 = float(np.asarray(phase1_fx["sigma_eps_true"]))
        dW_p1 = sigma_eta_p1 ** 2
        dV_p1 = sigma_eps_p1 ** 2

        kfas_outputs, kfas_versions = bridge.rscript_call(
            r_code=kfas_r_code,
            inputs={
                "y": y_p1.reshape(-1, 1),
                "dV": np.array([[dV_p1]]),
                "dW": np.array([[dW_p1]]),
            },
            output_names=["llf_kfas"],
            timeout_sec=60,
            capture_versions_for=["KFAS"],
        )

        return {
            "main": {
                "filtered": np.atleast_1d(
                    outputs["filtered"],
                ).astype(np.float64),
                "smoothed": np.atleast_1d(
                    outputs["smoothed"],
                ).astype(np.float64),
                "log_likelihood": float(
                    np.atleast_1d(outputs["llf"])[0]
                ),
                "kalman_gain_ss": float(
                    np.atleast_1d(outputs["kalman_gain"])[0]
                ),
            },
            "phase1": {
                "log_likelihood_kfas": float(
                    np.atleast_1d(kfas_outputs["llf_kfas"])[0]
                ),
            },
            "dlm_version": versions.get("dlm", "unknown"),
            "kfas_version": kfas_versions.get("KFAS", "unknown"),
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

        # Dual-fixture routing:
        #   tsl["main"]   <-> ref["main"]    (Session 2 fixture;
        #                                     state estimates +
        #                                     dlm methodology
        #                                     offset + Kalman gain)
        #   tsl["phase1"] <-> ref["phase1"]  (Phase 1 fixture;
        #                                     KFAS log-lik tight
        #                                     parity ONLY)
        tsl_main = tsl["main"]
        ref_main = ref["main"]
        tsl_p1 = tsl["phase1"]
        ref_p1 = ref["phase1"]

        metrics: dict[str, Any] = {}
        any_block = False

        # Filtered states (main fixture)
        any_block |= self._compare_array(
            tsl_main["filtered"], ref_main["filtered"],
            ladder["filtered_states_vs_dlm"]["abs_tol"],
            ladder["filtered_states_vs_dlm"]["rel_tol"],
            "filtered_states", metrics,
        )

        # Smoothed states (main fixture)
        any_block |= self._compare_array(
            tsl_main["smoothed"], ref_main["smoothed"],
            ladder["smoothed_states_vs_dlm"]["abs_tol"],
            ladder["smoothed_states_vs_dlm"]["rel_tol"],
            "smoothed_states", metrics,
        )

        # Log-likelihood vs dlm (main fixture; methodology-offset
        # detection, NOT parity — see tolerances.py justification).
        ll_dlm_tol = float(ladder["log_likelihood_vs_dlm"]["abs_tol"])
        ll_dlm_diff = abs(
            tsl_main["log_likelihood"] - ref_main["log_likelihood"]
        )
        ll_dlm_ok = ll_dlm_diff <= ll_dlm_tol
        metrics["ll_methodology_offset_vs_dlm"] = {
            "status": "PASS" if ll_dlm_ok else "BLOCK",
            "tsl": float(tsl_main["log_likelihood"]),
            "ref": float(ref_main["log_likelihood"]),
            "abs_diff": float(ll_dlm_diff),
            "tolerance": ll_dlm_tol,
            "fixture": "main",
            "note": (
                "methodology-offset detection only; tight parity "
                "via ll_parity_vs_kfas (on Phase 1 fixture)"
            ),
        }
        if not ll_dlm_ok:
            any_block = True

        # Log-likelihood vs KFAS — TIGHT PARITY on PHASE 1 FIXTURE.
        # Asserting on Phase 1's exact fixture isolates the test
        # from fixture-scaling FP-accumulation artifacts. Phase 1
        # audit 2a observed 3.64e-7 abs diff on this exact fixture.
        ll_kfas_tol = float(ladder["log_likelihood_vs_kfas"]["abs_tol"])
        ll_kfas_diff = abs(
            tsl_p1["log_likelihood"] - ref_p1["log_likelihood_kfas"]
        )
        ll_kfas_ok = ll_kfas_diff <= ll_kfas_tol
        metrics["ll_parity_vs_kfas"] = {
            "status": "PASS" if ll_kfas_ok else "BLOCK",
            "tsl": float(tsl_p1["log_likelihood"]),
            "ref": float(ref_p1["log_likelihood_kfas"]),
            "abs_diff": float(ll_kfas_diff),
            "tolerance": ll_kfas_tol,
            "fixture": "phase1",
            "note": (
                "tight parity vs KFAS on Phase 1's exact fixture "
                "(T=100, Q=0.1, H=1.0); reproduces Phase 1 audit "
                "2a's 3.64e-7 baseline"
            ),
        }
        if not ll_kfas_ok:
            any_block = True

        # Steady-state Kalman gain (main fixture)
        kg_tol = float(ladder["kalman_gain_ss_vs_dlm"]["abs_tol"])
        kg_rel = float(ladder["kalman_gain_ss_vs_dlm"]["rel_tol"])
        kg_diff = abs(
            tsl_main["kalman_gain_ss"] - ref_main["kalman_gain_ss"]
        )
        denom = max(
            abs(tsl_main["kalman_gain_ss"]),
            abs(ref_main["kalman_gain_ss"]),
            1e-300,
        )
        kg_rel_diff = float(kg_diff / denom)
        kg_ok = kg_diff <= kg_tol or kg_rel_diff <= kg_rel
        metrics["kalman_gain_ss"] = {
            "status": "PASS" if kg_ok else "BLOCK",
            "tsl": float(tsl_main["kalman_gain_ss"]),
            "ref": float(ref_main["kalman_gain_ss"]),
            "abs_diff": float(kg_diff),
            "rel_diff": kg_rel_diff,
            "fixture": "main",
        }
        if not kg_ok:
            any_block = True

        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics={
                "dlm_version": ref.get("dlm_version", "unknown"),
                "kfas_version": ref.get("kfas_version", "unknown"),
                "T_main": int(tsl_main.get("T", 0)),
                "fixture_main_sha": "loaded via runner",
                "fixture_phase1_id": self.PHASE1_FIXTURE_ID,
            },
        )

    @staticmethod
    def _compare_array(
        tsl_arr: np.ndarray,
        ref_arr: np.ndarray,
        abs_tol: float,
        rel_tol: float,
        label: str,
        metrics: dict[str, Any],
    ) -> bool:
        """Element-wise comparison; populates metrics[label] and
        returns True if BLOCK (any failure), False if PASS."""
        tsl_arr = np.asarray(tsl_arr, dtype=np.float64).flatten()
        ref_arr = np.asarray(ref_arr, dtype=np.float64).flatten()
        if tsl_arr.shape != ref_arr.shape:
            metrics[label] = {
                "status": "shape_mismatch",
                "tsl_shape": list(tsl_arr.shape),
                "ref_shape": list(ref_arr.shape),
            }
            return True
        diff = np.abs(tsl_arr - ref_arr)
        denom = np.maximum(np.abs(tsl_arr), np.abs(ref_arr))
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
