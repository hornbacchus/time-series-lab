"""2c MCMC SV Student-t-innovations parity check.

Second slow-tier check. Validates TSL's stochastic-volatility
MCMC inference path with Student-t innovations (forced down
the Kim-Shephard-Chib Gibbs branch via the B6 g++-probe
monkey-patch) against R ``stochvol::svtsample`` on a seeded
synthetic SV-t path.

Architectural decisions (locked in Session 4 design):

- **Q1.** Port the Phase 1 audit-2c fixture generator verbatim.
  T=500, mu=-10, phi=0.98, sigma_eta=0.2, nu=5, Student-t
  innovations, **seed=43** (different seed than 2b; matches
  Phase 1 audit 2c). SHA-256 verified via FixtureLoader.
- **Q2.** Same three-outcome PASS/CAVEAT/BLOCK ladder as 2b
  plus an additional ``nu_posterior_mean_vs_stochvol`` metric
  with PASS=0.05, CAVEAT=0.10. Phase 1 audit 2c documented
  ~13% rel_diff on nu attributed to different prior families
  (TSL TruncatedNormal vs stochvol's wider uninformative
  prior). The harness will BLOCK on nu if the Phase 1
  baseline reproduces; this is the **intended** behavior
  per the locked tolerance ladder, and the failure-mode
  protocol (CAVEAT re-roll, then escalate) handles it.
- **Q3.** ``sigma_eta_posterior_mean`` rel_diff is reported
  in ``diagnostics`` but does not gate the outcome. Phase 1
  audit 2c documented ~26% sigma_eta divergence (prior-
  driven).
- **Q4.** Supersedes ad-hoc parity scripts (none exist for 2c
  pre-Session 4; this is the first formal 2c parity check).

CAVEAT-reroll protocol: standard harness behavior (seed+1).
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

# Reuse the helpers from the 2b sibling module so the two checks
# share their three-outcome classification + Pearson logic.
from reference_parity.harness.checks.mcmc_sv_gaussian import (
    _aggregate_outcome,
    _classify_correlation,
    _classify_three_outcome,
    _ensure_engine_on_path,
    _pearson_corr,
    _rel_diff,
)


class McmcSvStudentTParity(P3ParityCheck):
    """MCMC SV Student-t-innovations parity vs R ``stochvol::svtsample``.

    Same protocol as the Gaussian sibling (2b) plus a nu (degrees
    of freedom) parity check. Phase 1 audit 2c established that
    nu posteriors diverge under different prior parameterizations;
    the harness preserves the Stage B 5%/10% ladder and lets the
    Phase 5 review process classify methodology vs bug.
    """

    technique_id = "2c_mcmc_sv_student_t"
    tier = "slow"
    fixture_id = "2c_sv_student_t"

    # Phase 3.5 Session 2 (Item 8): migrated to P3ParityCheck.
    verdict_class = "mcmc"
    verdict_class_rationale = (
        "MCMC posterior means + nu (df) inference under Student-t "
        "innovations. Phase 1 audit 2c documented nu divergence "
        "as methodology (different priors), NOT bug — TSL uses "
        "TruncatedNormal vs stochvol's Exponential rate. "
        "Three-outcome ladder per Phase 1 Stage B; nu band widened "
        "to 10%%/20%% per nu noise floor at T=500."
    )

    reroll_on_caveat = True

    # Phase 4 Session 9 (P4-1.3, 2026-05-02) — declare the
    # mcmc_convergence omnibus invariant. Same as the 2b Gaussian
    # sibling: stochastic_volatility.py exposes ess_min + rhat_max;
    # geweke is None per S8 catalog.
    #
    # Phase 6+ Session 1 (B-Phase6-S1-STRUCTURAL-INVARIANT-
    # PARAMETER-AWARE-EXCLUSION) — non_gating_params=("sigma_eta",)
    # mirrors parity-side `ess_min_check` `gates_outcome_for`
    # exclusion wisdom. Same Phase 1 audit 2b discipline as 2b
    # Gaussian sibling: sigma_eta-only ess breach downgraded for
    # omnibus aggregation. Note: 2c Student-t may also surface
    # ess_min on `nu` parameter at slow chain mixing; current
    # observation is sigma_eta only per S3 pre-flight findings;
    # extension to nu deferred to second empirical observation
    # per YAGNI discipline.
    structural_invariants = (
        StructuralInvariant(
            name="mcmc_convergence",
            invariant_type="mcmc_convergence",
            tolerance=200.0,
            tolerance_type="absolute",
            non_gating_params=("sigma_eta",),
        ),
    )

    R_TIMEOUT_SEC = 240

    # Phase 3.3: canonical seed=43 is now stored in the fixture
    # metadata (``_canonical_seed`` array inside the .npz). The
    # runner extracts it during load and passes it as the
    # effective seed to setup_fixture; CAVEAT-reroll bumps the
    # effective seed by +1 (canonical+1 = 44 here). This
    # replaces the prior SEED_OFFSET=1 class-attribute
    # workaround. setup_fixture is the same shape as 2b's
    # (just stash _seed for downstream TSL/R use).
    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"_seed": int(seed)}

    # -----------------------------------------------------------------
    # TSL side — force Gibbs cascade via B6 monkey-patch
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from unittest.mock import patch

        from techniques.base import RunContext
        from techniques import stochastic_volatility as sv_mod
        from techniques import _sv_mcmc as sv_mcmc

        y = np.asarray(fixture["y"], dtype=np.float64).reshape(-1)
        T = int(np.asarray(fixture.get("T", len(y))))
        seed = int(fixture.get("_seed", 42))

        sv_mcmc._check_c_compiler_available.cache_clear()
        with patch.object(
            sv_mcmc, "_check_c_compiler_available", return_value=False,
        ):
            ctx = RunContext({
                "run_id": f"parity_2c_seed{seed}",
                "technique_id": "stochastic_volatility",
                "preset": "Balanced",
                "seed": seed,
                "frequency": "daily",
                "time": list(range(T)),
                "series": [{"name": "y", "values": y.tolist()}],
                "params": {
                    "inference_method": "mcmc",
                    "mcmc_backend": None,
                    # Innovations: Student-t (the 2c branch). The
                    # SV wrapper accepts an "innovations" param;
                    # sanity-checked via Phase 1 2c audit.
                    "innovations": "student_t",
                },
            })
            res = sv_mod.run(ctx, lambda *a, **k: None)

        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL stochastic_volatility run failed: "
                f"{res.get('error_message')}"
            )
        a = res.get("audit_fields", {}) or {}
        if a.get("mcmc_backend_applied") != "gibbs":
            raise RuntimeError(
                f"Expected backend_applied='gibbs' (B6 cascade); "
                f"got {a.get('mcmc_backend_applied')!r}."
            )
        if a.get("mcmc_backend_fallback_reason") != "c_compiler_unavailable":
            raise RuntimeError(
                f"Expected fallback_reason='c_compiler_unavailable'; "
                f"got {a.get('mcmc_backend_fallback_reason')!r}."
            )
        h_post_mean = a.get("h_posterior_mean")
        if h_post_mean is None:
            raise RuntimeError(
                "h_posterior_mean is None on the MCMC path — B7 "
                "wiring failure."
            )
        nu_post = a.get("nu_posterior_mean")
        if nu_post is None:
            raise RuntimeError(
                "nu_posterior_mean is None on the Student-t MCMC "
                "path — wrapper did not populate the nu field. "
                "Check 2c (Student-t SV) wiring in "
                "stochastic_volatility.py / _sv_mcmc_gibbs.py."
            )
        return {
            "mu": float(a["mu_posterior_mean"]),
            "phi": float(a["phi_posterior_mean"]),
            "sigma_eta": float(a["sigma_eta_posterior_mean"]),
            "nu": float(nu_post),
            "h_post_mean": np.asarray(h_post_mean, dtype=np.float64),
            "ess_min": (
                float(a["ess_min"]) if a.get("ess_min") is not None
                else None
            ),
            "ess_min_param": a.get("ess_min_param"),
        }

    # -----------------------------------------------------------------
    # Reference side — R stochvol::svtsample
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64).reshape(-1)
        seed = int(fixture.get("_seed", 43))

        # Priors aligned with Phase 1 audit 2c (per
        # ``tools/reference_parity/scripts/audit_2c_student_t_sv.py``
        # which is what produced the Phase 1 baseline). Note:
        # ``svtsample`` (stochvol 3.2.9) takes ``priornu`` as a
        # SCALAR exponential rate parameter, NOT the 2-element
        # vector documented in the Phase 1 markdown report. The
        # markdown report's ``c(2, 100)`` annotation is incorrect;
        # the actual baseline used ``priornu = 0.1`` (per the
        # audit script source — authoritative).
        # ``set.seed(...)`` matches Phase 1 audit 2c script
        # ``audit_2c_student_t_sv.py`` (seed=43) so the harness
        # reproduces the Phase 1 baseline; parameterized from the
        # harness seed so CAVEAT-reroll bumps both TSL and R in
        # lockstep. Without R-side seeding, stochvol MCMC samples
        # vary materially across invocations (Session 4 first
        # measurement saw nu rel_diff bouncing 16-23% across
        # three unseeded invocations; with seed=43 the result is
        # deterministic at ~13% — the Phase 1 baseline).
        r_code = (
            "suppressPackageStartupMessages({ library(stochvol) })\n"
            f"set.seed({seed})\n"
        ) + r'''
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)$V1)
            fit <- svtsample(
                y, draws=10000, burnin=1000,
                priormu=c(0, 100),
                priorphi=c(20, 1.5),
                priorsigma=1,
                priornu=0.1,
                quiet=TRUE
            )
            para <- fit$para[[1]]  # first chain
            # svtsample posterior includes a "nu" column
            means <- data.frame(
                mu        = mean(para[, "mu"]),
                phi       = mean(para[, "phi"]),
                sigma_eta = mean(para[, "sigma"]),
                nu        = mean(para[, "nu"])
            )
            write.csv(means, "{{OUTPUT_means}}", row.names=FALSE)
            latent <- as.matrix(fit$latent)
            if (nrow(latent) != length(y)) latent <- t(latent)
            h_mean <- rowMeans(latent)
            write.csv(
                data.frame(h=h_mean),
                "{{OUTPUT_h}}",
                row.names=FALSE
            )
        '''

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["means", "h"],
            timeout_sec=self.R_TIMEOUT_SEC,
            capture_versions_for=["stochvol"],
        )

        means_arr = np.asarray(outputs["means"])
        if means_arr.ndim == 1:
            means_arr = means_arr.reshape(1, -1)
        if means_arr.shape[0] >= 2 and means_arr.shape[1] == 4:
            means_arr = means_arr[-1:, :]

        h_mean = np.asarray(outputs["h"]).reshape(-1).astype(np.float64)

        return {
            "mu": float(means_arr[0, 0]),
            "phi": float(means_arr[0, 1]),
            "sigma_eta": float(means_arr[0, 2]),
            "nu": float(means_arr[0, 3]),
            "h_post_mean": h_mean,
            "stochvol_version": versions.get("stochvol", "unknown"),
        }

    # -----------------------------------------------------------------
    # Compare — three-outcome ladder + nu metric
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        metrics: dict[str, Any] = {}
        per_metric_outcomes: list[str] = []

        # mu
        mu_cfg = ladder["mu_posterior_mean_vs_stochvol"]
        mu_rel = _rel_diff(tsl["mu"], ref["mu"])
        mu_status = _classify_three_outcome(
            mu_rel,
            float(mu_cfg["thresholds"]["PASS"]),
            float(mu_cfg["thresholds"]["CAVEAT"]),
        )
        metrics["mu_posterior_mean_vs_stochvol"] = {
            "status": mu_status,
            "rel_diff": mu_rel,
            "tsl_value": tsl["mu"],
            "ref_value": ref["mu"],
            "thresholds": dict(mu_cfg["thresholds"]),
        }
        per_metric_outcomes.append(mu_status)

        # phi
        phi_cfg = ladder["phi_posterior_mean_vs_stochvol"]
        phi_rel = _rel_diff(tsl["phi"], ref["phi"])
        phi_status = _classify_three_outcome(
            phi_rel,
            float(phi_cfg["thresholds"]["PASS"]),
            float(phi_cfg["thresholds"]["CAVEAT"]),
        )
        metrics["phi_posterior_mean_vs_stochvol"] = {
            "status": phi_status,
            "rel_diff": phi_rel,
            "tsl_value": tsl["phi"],
            "ref_value": ref["phi"],
            "thresholds": dict(phi_cfg["thresholds"]),
        }
        per_metric_outcomes.append(phi_status)

        # nu — additional Student-t metric
        nu_cfg = ladder["nu_posterior_mean_vs_stochvol"]
        nu_rel = _rel_diff(tsl["nu"], ref["nu"])
        nu_status = _classify_three_outcome(
            nu_rel,
            float(nu_cfg["thresholds"]["PASS"]),
            float(nu_cfg["thresholds"]["CAVEAT"]),
        )
        metrics["nu_posterior_mean_vs_stochvol"] = {
            "status": nu_status,
            "rel_diff": nu_rel,
            "tsl_value": tsl["nu"],
            "ref_value": ref["nu"],
            "thresholds": dict(nu_cfg["thresholds"]),
            "note": (
                "Phase 1 audit 2c documented prior-divergence-"
                "driven nu rel_diff ~13% (TSL TruncatedNormal vs "
                "stochvol uniform-ish prior). The locked Stage B "
                "5%/10% ladder may BLOCK on nu; classify as "
                "methodology, not bug, in Phase 5 review."
            ),
        }
        per_metric_outcomes.append(nu_status)

        # h posterior mean — Pearson correlation
        h_cfg = ladder["h_posterior_pearson_corr_vs_stochvol"]
        corr = _pearson_corr(tsl["h_post_mean"], ref["h_post_mean"])
        h_status = _classify_correlation(
            corr,
            float(h_cfg["thresholds"]["PASS"]),
            float(h_cfg["thresholds"]["CAVEAT"]),
        )
        h_diff = (
            np.asarray(tsl["h_post_mean"], dtype=np.float64)
            - np.asarray(ref["h_post_mean"], dtype=np.float64)
        )
        h_mad = float(np.mean(np.abs(h_diff)))
        h_rms = float(np.sqrt(np.mean(h_diff ** 2)))
        sv_rms = float(np.sqrt(np.mean(
            np.asarray(ref["h_post_mean"], dtype=np.float64) ** 2,
        )))
        h_rms_rel = h_rms / max(sv_rms, 1e-12)
        metrics["h_posterior_pearson_corr_vs_stochvol"] = {
            "status": h_status,
            "pearson_corr": corr,
            "mean_abs_diff": h_mad,
            "rms_rel_diff": h_rms_rel,
            "thresholds": dict(h_cfg["thresholds"]),
            "note": (
                "mean_abs_diff and rms_rel_diff are supplementary "
                "diagnostics; correlation gates the outcome (B7 "
                "Q5 protocol)."
            ),
        }
        per_metric_outcomes.append(h_status)

        # ESS in-check assertion
        ess_min = tsl.get("ess_min")
        ess_param = tsl.get("ess_min_param")
        ess_status = "PASS"
        ess_breach_blocks = False
        if ess_min is not None:
            ess_min_f = float(ess_min)
            if ess_min_f < 500.0:
                if ess_param in ("mu", "phi"):
                    ess_status = "BLOCK"
                    ess_breach_blocks = True
                else:
                    ess_status = "INFO"
        metrics["ess_min_check"] = {
            "status": ess_status,
            "ess_min": ess_min,
            "ess_min_param": ess_param,
            "threshold": 500.0,
            "gates_outcome_for": ["mu", "phi"],
            "note": (
                "Phase 1 audit 2c noted ess_min on nu typically "
                "<500 even when mu/phi mix well. Sigma_eta and nu "
                "ESS breaches recorded but non-gating "
                "(prior-divergence-driven posteriors expected to "
                "mix less efficiently)."
            ),
        }
        if ess_breach_blocks:
            per_metric_outcomes.append("BLOCK")

        # sigma_eta — record-only
        sigma_rel = _rel_diff(tsl["sigma_eta"], ref["sigma_eta"])

        outcome = _aggregate_outcome(per_metric_outcomes)

        diagnostics = {
            "sigma_eta_rel_diff_record_only": {
                "rel_diff": sigma_rel,
                "tsl_value": tsl["sigma_eta"],
                "ref_value": ref["sigma_eta"],
                "note": (
                    "Record-only diagnostic. Phase 1 audit 2c "
                    "documented prior-divergence-driven divergence "
                    "~26%; not gated by tolerance ladder."
                ),
            },
            "stochvol_version": ref.get("stochvol_version", "unknown"),
            "h_post_mean_T": int(np.asarray(
                tsl.get("h_post_mean", []),
            ).size),
            "ess_min_value": ess_min,
            "ess_min_param": ess_param,
        }

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics=diagnostics,
        )
