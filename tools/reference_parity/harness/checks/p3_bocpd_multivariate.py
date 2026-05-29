"""ENG-EXT-CHANGEPOINT-001 A1c — multivariate (joint) BOCPD parity check.

Compares TSL ``engine/techniques/bocpd.py`` MULTIVARIATE path
(auto-detected for >=2 input series) against a FROM-SCRATCH
reimplementation of the IDENTICAL multivariate Normal-Inverse-Wishart
(NIW) BOCPD. No library exists for multivariate BOCPD, so this is a
SELF-PARITY check (the S85/C3/A1b fallback): both arms implement the
same Adams-MacKay recursion with an NIW conjugate prior ->
multivariate-Student-t predictive (Cholesky-based, log-space), and the
same MAP-run-length-RESET change-point detection.

This is the LARGEST numerical surface of the three CHANGEPOINT-001
sub-builds (NIW hyperparameters + per-step rank-1 Ψ update + per-step
Cholesky logdet+solve + log-multivariate-t + log-space recursion +
MAP-reset detection) — the IDENTICAL-FORMULATION discipline is at its
most demanding. Deterministic → bit-exact joint change-point set.

Detection note: the engine multivariate path uses the STANDARD correct
BOCPD signal (MAP run-length reset), NOT S79's non-functional
cp_prob=R[t+1,0] threshold (R[t+1,0] == hazard, data-independent). The
fixture has a clear joint coordinated shift producing a NON-ZERO joint
change-point set — bit-exact on a non-zero set, stronger than S79's
bit-exact-on-empty.
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.special import gammaln
from scipy.linalg import solve_triangular

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_joint_shift_dgp(
    *, seed: int, n: int = 200, k: int = 3, shift: float = 3.0,
    sigma: float = 1.0,
) -> np.ndarray:
    """Multivariate (n, k) signal: all k curve points shift mean JOINTLY
    by ``shift`` at t = n/2 (a clear curve-wide coordinated regime shift,
    tuned to produce NON-ZERO joint detection)."""
    rng = np.random.default_rng(seed)
    X = rng.standard_normal((n, k)) * sigma
    X[n // 2:, :] += shift
    return X


def _ref_multivariate_bocpd(X, min_gap, hazard_lambda=200.0,
                            prior_kappa=0.01, prior_alpha=0.01,
                            prior_beta=0.01):
    """From-scratch NIW-BOCPD — mirrors engine ``_run_multivariate`` EXACTLY
    (same NIW hyperparams, rank-1 update, Cholesky log-mv-t, Adams-MacKay
    recursion, MAP-run-length-reset detection)."""
    n, k = X.shape
    hazard = 1.0 / hazard_lambda
    prior_mu = X.mean(axis=0)
    nu0 = (k - 1) + 2.0 * prior_alpha
    Psi0 = (2.0 * prior_beta) * np.eye(k)

    def mvt_logpdf(x, mu_r, kap, nuu, Psi_r):
        d = nuu - k + 1
        Sigma_t = Psi_r * (kap + 1.0) / (kap * d)
        L = np.linalg.cholesky(Sigma_t)
        diff = x - mu_r
        yv = solve_triangular(L, diff, lower=True)
        q = float(yv @ yv)
        logdet = 2.0 * float(np.sum(np.log(np.diag(L))))
        return (gammaln((d + k) / 2.0) - gammaln(d / 2.0)
                - (k / 2.0) * np.log(d * np.pi)
                - 0.5 * logdet
                - ((d + k) / 2.0) * np.log(1.0 + q / d))

    max_rl = n + 1
    kappa = np.zeros(max_rl); nu = np.zeros(max_rl)
    mu = np.zeros((max_rl, k)); Psi = np.zeros((max_rl, k, k))
    kappa[0] = prior_kappa; nu[0] = nu0; mu[0] = prior_mu; Psi[0] = Psi0
    R = np.zeros((n + 1, n + 1)); R[0, 0] = 1.0
    map_rl = np.zeros(n, dtype=int)

    for t in range(n):
        x = X[t]
        pred_logp = np.array([
            mvt_logpdf(x, mu[r], kappa[r], nu[r], Psi[r]) for r in range(t + 1)
        ])
        pred = np.exp(pred_logp - np.max(pred_logp))
        growth = R[t, :t + 1] * pred * (1 - hazard)
        cp = np.sum(R[t, :t + 1] * pred * hazard)
        R[t + 1, 1:t + 2] = growth
        R[t + 1, 0] = cp
        evidence = np.sum(R[t + 1, :t + 2])
        if evidence > 0:
            R[t + 1, :t + 2] /= evidence
        map_rl[t] = int(np.argmax(R[t + 1, :t + 2]))

        kappa_new = np.zeros(max_rl); nu_new = np.zeros(max_rl)
        mu_new = np.zeros((max_rl, k)); Psi_new = np.zeros((max_rl, k, k))
        kappa_new[0] = prior_kappa; nu_new[0] = nu0
        mu_new[0] = prior_mu; Psi_new[0] = Psi0
        for r in range(t + 1):
            kap = kappa[r]; kp = kap + 1.0
            kappa_new[r + 1] = kp
            mu_new[r + 1] = (kap * mu[r] + x) / kp
            nu_new[r + 1] = nu[r] + 1.0
            diff = x - mu[r]
            Psi_new[r + 1] = Psi[r] + (kap / kp) * np.outer(diff, diff)
        kappa, nu, mu, Psi = kappa_new, nu_new, mu_new, Psi_new

    reset_idx = [t for t in range(1, n) if (map_rl[t - 1] - map_rl[t]) > min_gap]
    filtered = []
    for t in reset_idx:
        if not filtered or (t - filtered[-1]) >= min_gap:
            filtered.append(int(t))
    return filtered


class BocpdMultivariateParity(P3ParityCheck):
    """Multivariate (joint) NIW-BOCPD parity (from-scratch self-test)."""

    technique_id = "p3_bocpd_multivariate"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Multivariate NIW-BOCPD (ENG-EXT-CHANGEPOINT-001 A1c) — "
        "deterministic closed-form recursive Bayesian detection (NIW "
        "conjugate -> multivariate-Student-t predictive, Cholesky-based, "
        "log-space; MAP-run-length-reset detection). No library exists, "
        "so the reference is a from-scratch reimplementation of the "
        "IDENTICAL formulation; bit-exact joint change-point set given "
        "identical input. Failure = a NIW-hyperparameter / rank-1-update "
        "/ Cholesky / log-mv-t / detection convention divergence."
    )

    DGP_N = 200
    DGP_K = 3
    MIN_GAP = 5  # Balanced preset min_gap

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"X": _generate_joint_shift_dgp(
            seed=seed, n=self.DGP_N, k=self.DGP_K,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        from techniques.bocpd import run as bocpd_run  # type: ignore

        X = np.asarray(fixture["X"], dtype=np.float64)
        n, k = X.shape
        ctx = RunContext({
            "run_id": "p3_bocpd_mv_tsl",
            "technique_id": "bocpd",
            "preset": "Balanced", "seed": 42, "frequency": "irregular",
            "time": list(range(n)),
            "series": [
                {"name": f"t{j}", "values": X[:, j].tolist()} for j in range(k)
            ],
            "params": {},
        })
        res = bocpd_run(ctx, lambda *a, **kw: None)
        if res.get("status") != "success":
            raise RuntimeError(f"TSL multivariate BOCPD failed: {res.get('error_message')}")
        a = res["audit_fields"]
        if a.get("mode") != "multivariate":
            raise RuntimeError(f"Expected multivariate mode, got {a.get('mode')!r}.")
        return {
            "change_points": sorted(int(x) for x in (a.get("change_point_indices") or [])),
            "n_change_points": int(a.get("n_change_points", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        X = np.asarray(fixture["X"], dtype=np.float64)
        cps = _ref_multivariate_bocpd(X, self.MIN_GAP)
        return {
            "change_points": sorted(int(x) for x in cps),
            "n_change_points": len(cps),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        primary["n_change_points"] = _compare_scalar(
            float(tsl["n_change_points"]), float(ref["n_change_points"]),
            ladder["primary"],
        )
        tsl_cps = set(tsl["change_points"])
        ref_cps = set(ref["change_points"])
        match = tsl_cps == ref_cps
        primary["joint_positions_set_match"] = {
            "status": "PASS" if match else "BLOCK",
            "tsl_only": sorted(tsl_cps - ref_cps),
            "ref_only": sorted(ref_cps - tsl_cps),
            "intersection_size": len(tsl_cps & ref_cps),
        }
        any_block = any(primary[k]["status"] == "BLOCK" for k in primary)
        any_caveat = any(primary[k]["status"] == "CAVEAT" for k in primary)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "n_features": int(self.DGP_K),
                "tsl_n_cp": int(tsl.get("n_change_points", 0)),
                "ref_n_cp": int(ref.get("n_change_points", 0)),
                "tsl_cps": list(tsl.get("change_points") or []),
                "ref_cps": list(ref.get("change_points") or []),
            },
        )
