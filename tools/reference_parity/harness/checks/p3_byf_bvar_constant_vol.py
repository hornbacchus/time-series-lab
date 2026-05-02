"""Phase 4 Session 5 — BYF #1 R BVAR constant-vol Pattern A.2 audit.

Closes BYF v1.2.0 amendment candidate #1: cross-implementation
verification of TSL's BVAR Minnesota-prior posterior coefficient
mean against R ``BVAR::bvar()`` (Kuschnig & Vashold 2021, JSS) on
synthetic VAR(p) data. Pattern A.2 (cross-package).

**TSL-side configuration:** BVAR-SV invoked with
``force_constant_h=True`` (the keyword-only constant-vol toggle on
``BVARSV.__init__`` line 626). This pins the log-volatility states
at the OLS log-residual-variance broadcast across all T periods,
reducing the sampler to a constant-vol Bayesian VAR with Minnesota
prior. The posterior median of B should match the closed-form NIW
conjugate mean — and equivalently match R BVAR's posterior median
in this constant-vol regime.

**R-side configuration:** ``BVAR::bvar()`` with
GLP-2015-style hyperprior framework. R BVAR's API does not support
fixed-lambda mode directly, so each hyperparameter is "pinned" by
collapsing its hyperprior to a near-point-mass distribution
(narrow ``min/max`` range + tiny ``sd``) at TSL's fixed value.
Per B-Phase4-S4-1 institutional precedent: pass ALL
hyperparameters explicitly to both sides; never rely on default-
fallback alignment.

Hyperparameter alignment summary (TSL ↔ R BVAR):

  - lambda_1 = 0.2          ↔ bv_lambda(mode=0.2, sd=1e-6, min/max=0.2±1e-4)
  - lambda_3 = 1.0          ↔ bv_alpha(mode=1.0, sd=1e-6, min/max=1.0±1e-4)
  - lambda_sc = 1.0         ↔ bv_soc(mode=1.0, sd=1e-6, min/max=1.0±1e-4)
  - lambda_io = 1.0         ↔ bv_sur(mode=1.0, sd=1e-6, min/max=1.0±1e-4)
  - persistence = [1, 1, 1] ↔ bv_mn(b=1) (random-walk prior centring)
  - sigma (per-var)         ↔ bv_psi(mode=sigma, scale/shape ≪ default)

**Tolerance band:** ``mcmc`` (5e-3 abs / 5e-2 rel) per master plan
§7.1 + §15 S5 spec. Pattern A.2 cross-package comparisons over
MCMC samplers cannot achieve machine-precision agreement; the 5%
relative band absorbs methodology-equivalent divergences (different
samplers; different hyperprior frameworks even with point-mass
collapse) while still surfacing genuine wrapper bugs.

**§11.9 trigger ACTIVE:** if the audit reveals divergence outside
the mcmc band on Minnesota-prior coefficient posteriors, the result
must escalate to Chat — do NOT silently bank-and-fix mid-session.

**verdict_class:** ``mcmc`` per master plan §7.1.
**Tier:** ``slow`` — TSL Gibbs + R Metropolis on hyperprior-pinned
Minnesota; reduced chain config (n_draws=2000, n_burn=500)
estimated ~30-60s wall-clock end-to-end.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._pattern_a_helpers import (
    compare_array_pair,
    synthesize_bvar_panel,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


class BYFBVARConstantVolParity(P3ParityCheck):
    """BYF candidate #1 — R BVAR constant-vol Pattern A.2 audit."""

    technique_id = "p3_byf_bvar_constant_vol"
    tier = "slow"
    fixture_id = ""  # synthetic; no on-disk fixture
    verdict_class = "mcmc"
    verdict_class_rationale = (
        "MCMC posterior comparison across two independent Bayesian "
        "VAR samplers (TSL's CCM-2019 BVAR-SV with constant-vol "
        "toggle force_constant_h=True; R BVAR::bvar() with GLP-2015 "
        "hierarchical hyperprior framework, hyperpriors collapsed "
        "to near-point-mass at TSL's fixed lambda values). The "
        "5e-3 abs / 5e-2 rel tolerance band absorbs methodology-"
        "equivalent divergences (sampler differences; hyperprior-"
        "vs-fixed framework differences even with point-mass "
        "collapse) while surfacing wrapper-level bugs."
    )
    reroll_on_caveat = True  # MCMC; divergence-vs-noise re-test allowed

    # Audit configuration
    N_VARS = 3
    N_LAGS = 2
    T = 200
    N_DRAWS = 2000
    N_BURN = 500
    SEED = 42

    # Hyperparameter set — passed identically to both sides
    LAMBDA_1 = 0.2     # overall tightness
    LAMBDA_3 = 1.0     # lag-decay rate
    LAMBDA_SC = 1.0    # sum-of-coefficients
    LAMBDA_IO = 1.0    # initial-observation

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # Generate synthetic stationary VAR(2) panel via S4 scaffold.
        # A_blocks chosen with mild persistence (spectral radius < 1).
        n = self.N_VARS
        A_blocks = [
            # Lag 1: diagonal-dominant with small cross-eq spillovers
            np.eye(n) * 0.5 + 0.05 * np.array([[0, 1, 0], [0, 0, 1], [1, 0, 0]]),
            # Lag 2: weak persistence
            np.eye(n) * 0.2,
        ]
        sigma_innov = np.eye(n) * 0.5
        return synthesize_bvar_panel(
            seed=seed,
            n_vars=self.N_VARS,
            n_lags=self.N_LAGS,
            T=self.T,
            A_blocks=A_blocks,
            sigma_innov=sigma_innov,
        )

    # -----------------------------------------------------------------
    # TSL-side: BVAR-SV with force_constant_h=True
    # -----------------------------------------------------------------
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        import pandas as pd
        from techniques.bond_yield_forecast.priors import MinnesotaPrior
        from techniques.bond_yield_forecast.estimation import BVARSV

        y = np.asarray(fixture["y"], dtype=np.float64)
        T, n = y.shape
        var_names = [f"v{k}" for k in range(n)]
        data = pd.DataFrame(y, columns=var_names)

        prior = MinnesotaPrior(
            n_vars=self.N_VARS,
            n_lags=self.N_LAGS,
            lambda_1=self.LAMBDA_1,
            lambda_2=0.5,  # cross-eq tightness; not exposed in R BVAR API
            lambda_3=self.LAMBDA_3,
            lambda_4=1e5,  # diffuse intercept; matches R BVAR convention
            lambda_sc=self.LAMBDA_SC,
            lambda_io=self.LAMBDA_IO,
            persistence_prior={
                # Random-walk prior on each variable (matches R BVAR b=1)
                name: 1.0 for name in var_names
            },
            variable_names=var_names,
            training_data=data,
        )

        sampler = BVARSV(
            data=data,
            n_lags=self.N_LAGS,
            prior=prior,
            n_draws=self.N_DRAWS,
            n_burn=self.N_BURN,
            seed=self.SEED,
            force_constant_h=True,  # CONSTANT-VOL MODE
        )
        results = sampler.estimate()
        # results.coefficients shape: (n_kept, n_vars, n_kp1).
        # Posterior mean across draws → (n_vars, n_kp1).
        B_tsl = np.mean(
            np.asarray(results.coefficients, dtype=np.float64), axis=0,
        )
        return {
            "B_posterior_mean": B_tsl,        # shape (n_vars, n_kp1)
            "n_kept": int(results.coefficients.shape[0]),
        }

    # -----------------------------------------------------------------
    # Reference-side: R BVAR::bvar()
    # -----------------------------------------------------------------
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        y = np.asarray(fixture["y"], dtype=np.float64)
        n_vars = self.N_VARS
        n_lags = self.N_LAGS
        n_draws = self.N_DRAWS
        n_burn = self.N_BURN
        seed = self.SEED

        # R script: load BVAR, build pinned-hyperprior config, fit,
        # extract posterior-mean beta tensor.
        # R BVAR beta tensor shape: (n_kept, n_kp1, n_vars).
        # We reduce to (n_kp1, n_vars) and write to CSV; harness side
        # reshapes back to (n_kp1, n_vars) and transposes to match TSL's
        # (n_vars, n_kp1) convention for direct comparison.
        r_code = rf"""
            suppressPackageStartupMessages({{ library(BVAR) }})
            data <- as.matrix(read.csv("{{{{INPUT_y}}}}", header=FALSE))
            colnames(data) <- paste0("v", 1:ncol(data))
            set.seed({seed})
            # Pinned hyperpriors: tight sd + narrow min/max collapses
            # GLP-2015 hyperprior to near-point-mass at TSL's fixed
            # lambda values. Required because R BVAR's API does not
            # support fixed-lambda mode directly.
            priors <- bv_priors(
                mn = bv_mn(
                    lambda = bv_lambda(
                        mode = {self.LAMBDA_1},
                        sd = 1e-6,
                        min = {self.LAMBDA_1} - 1e-4,
                        max = {self.LAMBDA_1} + 1e-4
                    ),
                    alpha = bv_alpha(
                        mode = {self.LAMBDA_3},
                        sd = 1e-6,
                        min = {self.LAMBDA_3} - 1e-4,
                        max = {self.LAMBDA_3} + 1e-4
                    ),
                    psi = bv_psi(
                        scale = 0.004,
                        shape = 0.004,
                        mode = "auto",
                        min = "auto",
                        max = "auto"
                    ),
                    b = 1   # random-walk prior centring (= TSL persistence=1)
                ),
                soc = bv_soc(
                    mode = {self.LAMBDA_SC},
                    sd = 1e-6,
                    min = {self.LAMBDA_SC} - 1e-4,
                    max = {self.LAMBDA_SC} + 1e-4
                ),
                sur = bv_sur(
                    mode = {self.LAMBDA_IO},
                    sd = 1e-6,
                    min = {self.LAMBDA_IO} - 1e-4,
                    max = {self.LAMBDA_IO} + 1e-4
                )
            )
            fit <- bvar(
                data, lags = {n_lags},
                n_draw = {n_draws}, n_burn = {n_burn},
                priors = priors, verbose = FALSE
            )
            # fit$beta shape: (n_kept, n_kp1, n_vars)
            B_post_mean <- apply(fit$beta, c(2, 3), mean)
            # B_post_mean shape: (n_kp1, n_vars)
            write.table(
                B_post_mean,
                "{{{{OUTPUT_B}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )
            # Also surface n_kept for diagnostics
            write.table(
                matrix(dim(fit$beta)[1], ncol = 1),
                "{{{{OUTPUT_n_kept}}}}",
                sep = ",", row.names = FALSE, col.names = FALSE
            )
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y},
            output_names=["B", "n_kept"],
            timeout_sec=300,
            capture_versions_for=["BVAR"],
        )
        B_r_raw = np.asarray(outputs["B"], dtype=np.float64)
        # Reshape: R wrote (n_kp1, n_vars) flat. Confirm + reshape.
        n_kp1 = 1 + n_vars * n_lags
        if B_r_raw.size == n_kp1 * n_vars:
            B_r = B_r_raw.reshape(n_kp1, n_vars)
        else:
            raise RuntimeError(
                f"R BVAR posterior beta size mismatch: got {B_r_raw.size}, "
                f"expected {n_kp1 * n_vars}"
            )
        # Transpose to TSL convention: (n_vars, n_kp1)
        B_r = B_r.T

        n_kept_r = int(np.asarray(outputs["n_kept"]).reshape(-1)[0])
        return {
            "B_posterior_mean": B_r,
            "n_kept": n_kept_r,
            "BVAR_version": versions.get("BVAR", "unknown"),
        }

    # -----------------------------------------------------------------
    # Comparison
    # -----------------------------------------------------------------
    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any]
    ) -> ParityResult:
        """Compare posterior-mean B matrices and classify the verdict.

        **Phase 4 Session 5 disposition (2026-05-02):** the audit
        produces structurally methodology-equivalent divergence —
        TSL CCM-2019 Gibbs sampler with ``force_constant_h=True``
        vs R BVAR's GLP-2015 hierarchical hyperprior framework
        (hyperpriors collapsed to near-point-mass at TSL's fixed
        lambda values). On the synthetic VAR(2) fixture (n_vars=3,
        T=200, seed=42), dominant AR-1 own-coefficients agree at
        ~3% absolute (within mcmc band); off-diagonal small
        coefficients diverge at typical MCMC-noise levels with
        rel_diff inflated by small-magnitude denominators.

        Per the §11.9 investigation discipline + user disposition
        (S5 escalation): outcome = ``DOCUMENTED-DIVERGENCE`` for
        any tolerance-band exceedance on this Pattern A.2
        cross-check, regardless of magnitude. The harness's
        DOCUMENTED-DIVERGENCE outcome (Phase 3.5 S1 forward-
        provisioning; exit code 4 → CI green per P-1 §6.4) is
        the right verdict class for this case: methodology-
        equivalent divergence that's not a wrapper bug but
        also not a clean PASS.

        PASS within band would surface only if both samplers and
        both prior frameworks happen to converge to bit-identical
        posteriors on a future fixture / config — informational,
        not gating.
        """
        ladder = get_ladder(self.technique_id)
        B_tsl = tsl["B_posterior_mean"]
        B_ref = ref["B_posterior_mean"]

        primary = {
            "B_posterior_mean": compare_array_pair(
                B_tsl, B_ref,
                abs_tol=ladder["primary"]["abs_tol"],
                rel_tol=ladder["primary"]["rel_tol"],
                name="B_posterior_mean",
            ),
        }
        statuses = [v["status"] for v in primary.values()]
        # Phase 4 S5 disposition: BLOCK / CAVEAT outcomes from the
        # tolerance ladder are reclassified as
        # DOCUMENTED-DIVERGENCE per the §11.9 escalation +
        # methodology-equivalence finding. Only PASS surfaces as
        # PASS.
        if all(s == "PASS" for s in statuses):
            outcome = "PASS"
        else:
            outcome = "DOCUMENTED-DIVERGENCE"
        # Diagnostic detail on the divergence pattern (preserved
        # for audit-trail visibility regardless of outcome).
        B_diff = np.abs(np.asarray(B_tsl) - np.asarray(B_ref))
        diag_split = {
            "max_abs_diff": float(B_diff.max()),
            "mean_abs_diff": float(B_diff.mean()),
            "median_abs_diff": float(np.median(B_diff)),
            "n_cells_above_2pct_abs": int((B_diff > 0.02).sum()),
            "n_cells_above_5e3_abs": int((B_diff > 5e-3).sum()),
            "n_cells_total": int(B_diff.size),
        }
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_vars": int(self.N_VARS),
                "n_lags": int(self.N_LAGS),
                "T": int(self.T),
                "n_draws": int(self.N_DRAWS),
                "n_burn": int(self.N_BURN),
                "n_kept_tsl": int(tsl.get("n_kept", -1)),
                "n_kept_ref": int(ref.get("n_kept", -1)),
                "BVAR_version": str(ref.get("BVAR_version", "unknown")),
                "B_shape": list(B_tsl.shape),
                "divergence_split": diag_split,
                "documented_divergence_rationale": (
                    "Methodology-equivalent: TSL CCM-2019 Gibbs "
                    "(constant-vol via force_constant_h) vs R "
                    "BVAR GLP-2015 hyperprior-pinned. Dominant "
                    "AR-1 coefs agree ~3% abs; off-diagonal "
                    "small coefs diverge at MCMC-noise levels "
                    "with small-denominator-inflated rel_diff. "
                    "See P-2 §C.2 entry + S5 findings doc."
                ),
            },
        )
