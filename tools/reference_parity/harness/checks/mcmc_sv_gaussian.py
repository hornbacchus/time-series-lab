"""2b MCMC SV Gaussian-innovations parity check.

First slow-tier check in the harness. Validates TSL's
stochastic-volatility MCMC inference path (forced down the
Kim-Shephard-Chib Gibbs branch via the B6 g++-probe monkey-
patch) against R ``stochvol::svsample`` on a seeded synthetic
SV path.

Architectural decisions (locked in Session 4 design):

- **Q1.** Port the Phase 1 audit-2b fixture generator verbatim.
  T=500, mu=-10, phi=0.98, sigma_eta=0.2, Gaussian innovations,
  seed=42. SHA-256 verified via FixtureLoader (the fixture is
  pre-generated and stored as
  ``fixtures/2b_sv_gaussian.npz``).
- **Q2.** Three-outcome PASS/CAVEAT/BLOCK ladder driven by
  ``tolerances.TOLERANCE_LADDERS["2b_mcmc_sv_gaussian"]``. ESS
  threshold (>500 on mu / phi) is asserted in-check rather than
  schema-extending the ladder. ``sigma_eta`` is recorded as a
  diagnostic only — Phase 1 audit 2b documented prior-divergence-
  driven rel_diff up to 45%, expected.
- **Q3.** ``sigma_eta_posterior_mean`` rel_diff is reported in
  ``diagnostics`` but does not gate the outcome.
- **Q4.** This check supersedes the ad-hoc
  ``tools/parity_b6_sv_gibbs_vs_stochvol.py`` and
  ``tools/parity_b7_h_latent_vs_stochvol.py`` scripts.
  Deprecation flagged in the Session 4 commit message; legacy
  scripts retained at the path users may have wired into local
  habits but should be removed in a follow-up cleanup.

CAVEAT-reroll protocol: the runner re-runs with seed+1 if any
PASS/CAVEAT band is hit on the first run, per the standard
harness protocol. CAVEAT-on-retry escalates to BLOCK.

The check forces the Gibbs path so the result is deterministic
relative to the harness manifest's stochvol pin (3.2.9). NUTS
would require g++ on the runner — slow-tier CI may not have
one, and the Gibbs path is mathematically equivalent for this
parity comparison.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


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


def _pearson_corr(a: np.ndarray, b: np.ndarray) -> float:
    """Pearson correlation, location-invariant. Used for the
    h-posterior latent-series parity check (B7 Q5 protocol)."""
    a = np.asarray(a, dtype=np.float64).reshape(-1)
    b = np.asarray(b, dtype=np.float64).reshape(-1)
    if a.size == 0 or b.size == 0 or a.size != b.size:
        return float("nan")
    a_c = a - a.mean()
    b_c = b - b.mean()
    denom = float(np.sqrt(np.sum(a_c ** 2)) * np.sqrt(np.sum(b_c ** 2)))
    if denom < 1e-300:
        return float("nan")
    return float(np.sum(a_c * b_c) / denom)


def _rel_diff(a: float, b: float) -> float:
    """Symmetric relative difference: |a - b| / max(|a|, |b|, eps).

    Matches the metric used in B6/B7 ad-hoc parity scripts so
    historical baselines compare apples-to-apples."""
    denom = max(abs(float(a)), abs(float(b)), 1e-12)
    return abs(float(a) - float(b)) / denom


def _classify_three_outcome(
    metric_value: float,
    pass_threshold: float,
    caveat_threshold: float,
) -> str:
    """Three-outcome ladder for a "smaller is better" rel_diff
    metric: PASS if value <= PASS threshold; CAVEAT if value <=
    CAVEAT threshold; otherwise BLOCK."""
    if metric_value <= pass_threshold:
        return "PASS"
    if metric_value <= caveat_threshold:
        return "CAVEAT"
    return "BLOCK"


def _classify_correlation(
    corr_value: float,
    pass_threshold: float,
    caveat_threshold: float,
) -> str:
    """Three-outcome ladder for a "larger is better" correlation
    metric: PASS if corr >= PASS threshold; CAVEAT if corr >=
    CAVEAT threshold; otherwise BLOCK. NaN is treated as BLOCK
    (degenerate input — should not happen on valid posteriors)."""
    if not np.isfinite(corr_value):
        return "BLOCK"
    if corr_value >= pass_threshold:
        return "PASS"
    if corr_value >= caveat_threshold:
        return "CAVEAT"
    return "BLOCK"


def _aggregate_outcome(per_metric: list[str]) -> str:
    """Combine three-outcome statuses across the metric ladder.
    Worst outcome wins: BLOCK > CAVEAT > PASS."""
    if "BLOCK" in per_metric:
        return "BLOCK"
    if "CAVEAT" in per_metric:
        return "CAVEAT"
    return "PASS"


class McmcSvGaussianParity(ParityCheck):
    """MCMC SV Gaussian-innovations parity vs R ``stochvol::svsample``.

    First slow-tier check; validates the three-outcome PASS/
    CAVEAT/BLOCK protocol with seed+1 re-roll on CAVEAT.
    """

    technique_id = "2b_mcmc_sv_gaussian"
    tier = "slow"
    fixture_id = "2b_sv_gaussian"

    # Subprocess timeout (seconds). svsample on T=500 with
    # 10000 draws + 1000 burn typically completes in ~30s on
    # modern CPUs; 240s leaves headroom for slow CI runners.
    R_TIMEOUT_SEC = 240

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        """Fixture is loaded from disk by the runner; this hook
        records the seed used for the run so diagnostic
        messages can attribute the correct seed."""
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

        # Force B6 cascade → Gibbs path. Same pattern as the
        # ad-hoc parity_b6_sv_gibbs_vs_stochvol.py script. Cache-
        # clear first so the patch takes effect even if a prior
        # call cached True/False.
        sv_mcmc._check_c_compiler_available.cache_clear()
        with patch.object(
            sv_mcmc, "_check_c_compiler_available", return_value=False,
        ):
            ctx = RunContext({
                "run_id": f"parity_2b_seed{seed}",
                "technique_id": "stochastic_volatility",
                "preset": "Balanced",
                "seed": seed,
                "frequency": "daily",
                "time": list(range(T)),
                "series": [{"name": "y", "values": y.tolist()}],
                "params": {
                    "inference_method": "mcmc",
                    "mcmc_backend": None,  # auto → cascade to Gibbs
                },
            })
            res = sv_mod.run(ctx, lambda *a, **k: None)

        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL stochastic_volatility run failed: "
                f"{res.get('error_message')}"
            )
        a = res.get("audit_fields", {}) or {}
        # Sanity: cascade actually fired (B6 D10 path)
        if a.get("mcmc_backend_applied") != "gibbs":
            raise RuntimeError(
                f"Expected backend_applied='gibbs' (B6 cascade); "
                f"got {a.get('mcmc_backend_applied')!r}. The "
                f"monkey-patch did not take effect."
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
                "wiring failure. Check _sv_mcmc_gibbs.fit() return "
                "dict and stochastic_volatility.py audit-field "
                "population."
            )
        return {
            "mu": float(a["mu_posterior_mean"]),
            "phi": float(a["phi_posterior_mean"]),
            "sigma_eta": float(a["sigma_eta_posterior_mean"]),
            "h_post_mean": np.asarray(h_post_mean, dtype=np.float64),
            "ess_min": (
                float(a["ess_min"]) if a.get("ess_min") is not None
                else None
            ),
            "ess_min_param": a.get("ess_min_param"),
        }

    # -----------------------------------------------------------------
    # Reference side — R stochvol::svsample
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64).reshape(-1)
        seed = int(fixture.get("_seed", 42))

        # Priors aligned with Phase 1 audit 2b's stochvol call.
        # 10000 draws + 1000 burn-in matches the audit's
        # configuration so the Phase 1 baseline reproduces.
        # ``set.seed(...)`` is parameterized from the harness
        # seed so CAVEAT-reroll (seed+1) bumps both TSL and R
        # in lockstep. Without R-side seeding, stochvol MCMC
        # samples vary ~5-10% across invocations and defeat the
        # harness's reproducibility guarantee. Phase 1 audit 2b
        # used ``set.seed(42)`` (the seed=42 default).
        r_code = (
            "suppressPackageStartupMessages({ library(stochvol) })\n"
            f"set.seed({seed})\n"
        ) + r'''
            y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)$V1)
            fit <- svsample(
                y, draws=10000, burnin=1000,
                priormu=c(0, 100),
                priorphi=c(20, 1.5),
                priorsigma=1,
                quiet=TRUE
            )
            para <- fit$para[[1]]  # first chain (default 1 chain)
            means <- data.frame(
                mu        = mean(para[, "mu"]),
                phi       = mean(para[, "phi"]),
                sigma_eta = mean(para[, "sigma"])
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

        # Defensive parse: rscript_bridge may or may not retain
        # the header row depending on NA presence; the Phase 1
        # B2 fix typically yields a 1-row data array.
        means_arr = np.asarray(outputs["means"])
        if means_arr.ndim == 1:
            means_arr = means_arr.reshape(1, -1)
        if means_arr.shape[0] >= 2 and means_arr.shape[1] == 3:
            means_arr = means_arr[-1:, :]

        h_mean = np.asarray(outputs["h"]).reshape(-1).astype(np.float64)

        return {
            "mu": float(means_arr[0, 0]),
            "phi": float(means_arr[0, 1]),
            "sigma_eta": float(means_arr[0, 2]),
            "h_post_mean": h_mean,
            "stochvol_version": versions.get("stochvol", "unknown"),
        }

    # -----------------------------------------------------------------
    # Compare — three-outcome ladder
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        metrics: dict[str, Any] = {}
        per_metric_outcomes: list[str] = []

        # mu posterior mean — three-outcome rel_diff
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

        # phi posterior mean — three-outcome rel_diff
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

        # h posterior mean — Pearson correlation, three-outcome
        h_cfg = ladder["h_posterior_pearson_corr_vs_stochvol"]
        corr = _pearson_corr(tsl["h_post_mean"], ref["h_post_mean"])
        h_status = _classify_correlation(
            corr,
            float(h_cfg["thresholds"]["PASS"]),
            float(h_cfg["thresholds"]["CAVEAT"]),
        )
        # Supplementary diagnostics for h: mean-abs-diff + RMS rel.
        # Reported, not asserted (B7 Q5 refinement: priors differ
        # on mu, absolute level shift expected).
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
                "Q5 protocol — priors differ on mu, absolute "
                "level shift expected)."
            ),
        }
        per_metric_outcomes.append(h_status)

        # ESS in-check assertion: ESS_min < 500 on mu/phi → BLOCK.
        # If ess_min_param is sigma_eta or another non-gating
        # parameter, the breach is recorded but does not block.
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
                    # sigma_eta or other — record but do not gate.
                    ess_status = "INFO"
        metrics["ess_min_check"] = {
            "status": ess_status,
            "ess_min": ess_min,
            "ess_min_param": ess_param,
            "threshold": 500.0,
            "gates_outcome_for": ["mu", "phi"],
            "note": (
                "Phase 1 audit 2b: ESS<500 on mu or phi means MC "
                "noise dominates posterior-mean comparison and the "
                "audit should pause for re-run at higher draw count. "
                "Sigma_eta breaches recorded but non-gating "
                "(prior-divergence-driven posterior is expected)."
            ),
        }
        if ess_breach_blocks:
            per_metric_outcomes.append("BLOCK")

        # sigma_eta — record-only diagnostic (Q3). Phase 1 audit
        # 2b documented prior-divergence-driven divergence up to
        # 45%; reporting in diagnostics, not in metrics.
        sigma_rel = _rel_diff(tsl["sigma_eta"], ref["sigma_eta"])

        outcome = _aggregate_outcome(per_metric_outcomes)

        diagnostics = {
            "sigma_eta_rel_diff_record_only": {
                "rel_diff": sigma_rel,
                "tsl_value": tsl["sigma_eta"],
                "ref_value": ref["sigma_eta"],
                "note": (
                    "Record-only diagnostic. Phase 1 audit 2b "
                    "documented prior-divergence-driven divergence "
                    "up to 45%; not gated by tolerance ladder."
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
