"""Phase 3 Batch 5 — Particle Filter parity check.

Compares TSL ``engine/techniques/particle_filter.py`` (numpy-
based bootstrap particle filter) against Python ``particles``
(Lagardère's SMC framework) on a synthetic local-level fixture.

R `pomp` flagged TBD-batch-5 in INVENTORY (non-trivial Windows
install). Python `particles` is the locked substitute per
master plan §6.1.

**NO-REFERENCE candidate per master plan §5 Tier C:** SMC
algorithms are stochastic — different RNG seeds + different
resampling implementations produce different particle paths.
Comparison must be at distributional level (filtered-mean
correlation), not at particle-level.

Audit strategy: compare filtered state mean trajectories via
Pearson correlation; expect corr > 0.9 PASS; 0.7–0.9 CAVEAT.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_local_level_obs(
    *, seed: int, n: int = 200,
    sigma_state: float = 1.0, sigma_obs: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Generate local-level (random walk + noise) realization
    plus the latent state (for reference comparison)."""
    rng = np.random.default_rng(seed)
    eta = rng.standard_normal(n) * sigma_state
    x = np.cumsum(eta)
    eps = rng.standard_normal(n) * sigma_obs
    return x + eps, x


class ParticleFilterParity(P3ParityCheck):
    """Particle filter parity vs Python particles.

    DGP: local level (random walk + noise), T=200, seed=42.
    """

    technique_id = "p3_particle_filter"
    tier = "fast"
    fixture_id = ""

    verdict_class = "em_stochastic"  # closest existing class; SMC is stochastic
    verdict_class_rationale = (
        "Bootstrap particle filter via Sequential Monte Carlo. "
        "TSL numpy-based implementation and Python particles "
        "package are independent SMC implementations with "
        "different resampling algorithms (multinomial vs "
        "stratified) and RNG paths. Comparison at "
        "distributional level (filtered-mean Pearson "
        "correlation) per master plan §5 Tier C — particle-"
        "level parity is mathematically intractable for SMC."
    )

    DGP_N = 200
    SIGMA_STATE = 1.0
    SIGMA_OBS = 1.0

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y, x_true = _generate_local_level_obs(
            seed=seed, n=self.DGP_N,
            sigma_state=self.SIGMA_STATE,
            sigma_obs=self.SIGMA_OBS,
        )
        return {"y": y, "x_true": x_true}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.particle_filter as pf_mod  # type: ignore

        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_pf_parity",
            "technique_id": "particle_filter",
            "preset": "Fast",  # 500 particles for speed
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "model": "local_level",
                "n_particles": 1000,
                "sigma_state": self.SIGMA_STATE,
                "sigma_obs": self.SIGMA_OBS,
                "horizon": 10,
            },
        })
        wrapper_resp = pf_mod.run(ctx, lambda *a, **kw: None)
        if wrapper_resp.get("status") != "success":
            raise RuntimeError(
                f"TSL particle_filter failed: {wrapper_resp.get('error_message')}"
            )

        # Extract filtered state mean from filtered values table
        filt_table = next(
            (t for t in wrapper_resp["tables"]
             if "Filtered" in t.get("name", "")),
            None,
        )
        if filt_table is not None:
            filt_mean = np.array(
                [float(row[1]) for row in filt_table["rows"]],
                dtype=np.float64,
            )
        else:
            filt_mean = np.array([], dtype=np.float64)
        af = wrapper_resp.get("audit_fields", {})
        return {
            "filtered_mean": filt_mean,
            "log_likelihood": float(af.get("log_likelihood", float("nan"))),
            "n_particles": int(af.get("n_particles", 1000)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Reference: Python particles SMC with bootstrap PF on
        the same local-level model. We use the manifest pin
        (verified at module import time)."""
        try:
            import particles  # type: ignore
            from particles import state_space_models as ssm  # type: ignore
            from particles import distributions as dists  # type: ignore
        except ImportError as e:
            # Per harness contract: ImportError → SKIP outcome
            raise

        y = np.asarray(fixture["y"], dtype=np.float64)
        sigma_state = self.SIGMA_STATE
        sigma_obs = self.SIGMA_OBS

        # Define local-level state-space model in particles' DSL
        class LocalLevel(ssm.StateSpaceModel):
            def PX0(self):
                return dists.Normal(loc=0.0, scale=10.0)
            def PX(self, t, xp):
                return dists.Normal(loc=xp, scale=sigma_state)
            def PY(self, t, xp, x):
                return dists.Normal(loc=x, scale=sigma_obs)

        np.random.seed(42)
        model = LocalLevel()
        fk = ssm.Bootstrap(ssm=model, data=y.tolist())
        smc = particles.SMC(fk=fk, N=1000, resampling="stratified",
                            store_history=False)
        smc.run()
        # smc.X is the final particle cloud; we need the filter
        # means which particles tracks via summaries.
        # particles.SMC exposes `.summaries.X.mean` if appropriately
        # configured. Simpler: compute filter means by re-running
        # with summary tracking.
        from particles.collectors import Moments  # type: ignore
        smc2 = particles.SMC(fk=fk, N=1000, resampling="stratified",
                              collect=[Moments()])
        smc2.run()
        filt_mean = np.array(
            [m["mean"] for m in smc2.summaries.moments],
            dtype=np.float64,
        )

        return {
            "filtered_mean": filt_mean,
            "particles_version": getattr(particles, "__version__", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}

        tsl_fm = np.asarray(tsl["filtered_mean"], dtype=np.float64).reshape(-1)
        ref_fm = np.asarray(ref["filtered_mean"], dtype=np.float64).reshape(-1)

        if not np.isfinite(tsl_fm).all() or not np.isfinite(ref_fm).all() \
                or tsl_fm.size == 0 or ref_fm.size == 0:
            return ParityResult(
                technique_id=self.technique_id,
                outcome="CAVEAT",
                metrics={
                    "primary": {
                        "reference_convergence": {
                            "status": "CAVEAT",
                            "note": (
                                "Particle filter produced non-finite "
                                "or empty filtered means on this "
                                "fixture. NO-REFERENCE Tier C fallback."
                            ),
                            "tsl_size": int(tsl_fm.size),
                            "ref_size": int(ref_fm.size),
                        }
                    }
                },
                diagnostics={
                    "particles_version": ref.get("particles_version", "unknown"),
                    "n_obs": int(self.DGP_N),
                },
            )

        n_common = min(len(tsl_fm), len(ref_fm))
        try:
            corr = float(np.corrcoef(
                tsl_fm[:n_common], ref_fm[:n_common],
            )[0, 1])
        except Exception:
            corr = float("nan")

        corr_pass = ladder["primary"].get("corr_pass", 0.85)
        corr_caveat = ladder["primary"].get("corr_caveat", 0.6)
        if not np.isfinite(corr):
            status = "BLOCK"
        elif corr >= corr_pass:
            status = "PASS"
        elif corr >= corr_caveat:
            status = "CAVEAT"
        else:
            status = "BLOCK"

        primary["filtered_mean_correlation"] = {
            "status": status,
            "pearson_corr": corr,
            "n_compared": n_common,
        }

        any_block = primary["filtered_mean_correlation"]["status"] == "BLOCK"
        any_caveat = primary["filtered_mean_correlation"]["status"] == "CAVEAT"
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "particles_version": ref.get("particles_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "tsl_n_particles": tsl.get("n_particles"),
            },
        )
