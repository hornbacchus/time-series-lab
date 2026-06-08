"""Phase 3 Batch 6 / engine-improvement #2 — BOCPD detection validation.

TSL ``engine/techniques/bocpd.py`` (Adams-MacKay 2007, NIG conjugate prior).

★ S79 FIX (engine-improvement #2): the univariate detection criterion was
``cp_prob = R[t+1,0] > threshold``, which is NON-FUNCTIONAL — ``R[t+1,0]``
normalizes to EXACTLY ``hazard`` (data-independent), so it never crosses 0.5 ->
n_cps=0 on ANY input (a detector that detects nothing). The engine now uses the
MAP run-length RESET criterion (ported from the correct multivariate path).

★ THIS CHECK WAS THE §5.1 FOUNDING CASE — self-parity-COMPLICIT. The prior
``run_reference`` applied the SAME broken ``cp_prob>threshold`` criterion, so on
``_generate_mean_shift_dgp`` (a KNOWN change-point at t=150) BOTH the engine and
the reference returned n_cps=0 and the check PASSED with ZERO detections on an
obvious change-point. Self-parity validates match-not-correctness; for a
detector it is INSUFFICIENT. This is now a FUNCTIONAL DETECTION check with a
verified-discriminating negative control:
  - **recursion SENTINEL:** engine MAP run-length bit-exact vs the from-scratch
    reference (the recursion is UNCHANGED by the fix — only the detection
    read-off changed);
  - **criterion cross-validation:** engine n_cps == reference n_cps (both via
    MAP-reset);
  - **functional POSITIVE:** fires within ±15 of the true CP@150 (measured 153);
  - **★ functional NEGATIVE CONTROL:** n_cps=0 on a no-change-point series
    (catches a fires-on-everything fix — the discrimination the old check lacked).
"""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.special import gammaln

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_TRUE_CP = 150
_LOC_TOL = 15  # detected CP must be within ±15 of the true CP (measured 153)
_MIN_GAP = 5   # Balanced preset min_gap


def _generate_mean_shift_dgp(*, seed: int, n: int = 300) -> np.ndarray:
    """Two-segment mean-shift signal with a KNOWN CP at t=150 (the positive)."""
    rng = np.random.default_rng(seed)
    y = np.empty(n)
    y[:150] = 0.0 + rng.standard_normal(150)
    y[150:] = 3.0 + rng.standard_normal(n - 150)
    return y


def _generate_no_cp_dgp(*, seed: int, n: int = 300) -> np.ndarray:
    """Stationary series — NO change point (the negative control)."""
    rng = np.random.default_rng(seed + 777)
    return (rng.standard_normal(n) + 0.0).astype(float)


def _student_t_logpdf(x, mu, kappa, alpha, beta) -> float:
    """Posterior predictive Student-t log-pdf under NIG prior (identical to the
    engine's ``_student_t_logpdf``)."""
    df = 2.0 * alpha
    if alpha * kappa <= 0.0:
        scale2 = 1e10
    else:
        scale2 = beta * (kappa + 1.0) / (alpha * kappa)
    if scale2 <= 0:
        scale2 = 1e-10
    z = (x - mu) ** 2 / scale2
    return float(
        gammaln((df + 1) / 2) - gammaln(df / 2)
        - 0.5 * np.log(df * np.pi * scale2)
        - (df + 1) / 2 * np.log(1 + z / df)
    )


def _bocpd_reference(y, *, hazard_lambda, prior_mu, prior_kappa,
                     prior_alpha, prior_beta):
    """Reference Adams-MacKay 2007. Returns (cp_prob, map_rl) — mirrors the
    engine recursion verbatim so the comparison isolates wrapper bugs."""
    n = len(y)
    hazard = 1.0 / hazard_lambda
    max_rl = n + 1
    kappa = np.zeros(max_rl); mu = np.zeros(max_rl)
    alpha = np.zeros(max_rl); beta = np.zeros(max_rl)
    kappa[0], mu[0], alpha[0], beta[0] = prior_kappa, prior_mu, prior_alpha, prior_beta
    R = np.zeros((n + 1, n + 1)); R[0, 0] = 1.0
    cp_prob = np.zeros(n); map_rl = np.zeros(n, dtype=int)
    for t in range(n):
        x = y[t]
        pred_logp = np.empty(t + 1)
        for r in range(t + 1):
            pred_logp[r] = _student_t_logpdf(x, mu[r], kappa[r], alpha[r], beta[r])
        pred_p = np.exp(pred_logp - float(np.max(pred_logp)))
        R[t + 1, 1:t + 2] = R[t, :t + 1] * pred_p * (1 - hazard)
        R[t + 1, 0] = float(np.sum(R[t, :t + 1] * pred_p * hazard))
        evidence = float(np.sum(R[t + 1, :t + 2]))
        if evidence > 0:
            R[t + 1, :t + 2] /= evidence
        cp_prob[t] = float(R[t + 1, 0])
        map_rl[t] = int(np.argmax(R[t + 1, :t + 2]))
        kappa_new = np.zeros(max_rl); mu_new = np.zeros(max_rl)
        alpha_new = np.zeros(max_rl); beta_new = np.zeros(max_rl)
        kappa_new[0], mu_new[0], alpha_new[0], beta_new[0] = (
            prior_kappa, prior_mu, prior_alpha, prior_beta)
        for r in range(t + 1):
            kappa_new[r + 1] = kappa[r] + 1
            mu_new[r + 1] = (kappa[r] * mu[r] + x) / kappa_new[r + 1]
            alpha_new[r + 1] = alpha[r] + 0.5
            beta_new[r + 1] = beta[r] + 0.5 * kappa[r] * (x - mu[r]) ** 2 / kappa_new[r + 1]
        kappa, mu, alpha, beta = kappa_new, mu_new, alpha_new, beta_new
    return cp_prob, map_rl


def _detect_map_reset(map_rl, min_gap=_MIN_GAP):
    """The CORRECT BOCPD detection: change point where the MAP run length
    drops sharply (posterior mass resets to a fresh run)."""
    reset = [t for t in range(1, len(map_rl)) if (map_rl[t - 1] - map_rl[t]) > min_gap]
    filt = []
    for t in reset:
        if not filt or (t - filt[-1]) >= min_gap:
            filt.append(int(t))
    return filt


class BocpdParity(P3ParityCheck):
    """BOCPD functional detection check (S79 MAP-reset fix) with a
    verified-discriminating negative control."""

    technique_id = "p3_bocpd"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Adams-MacKay 2007 BOCPD (NIG conjugate, closed-form recursive). The "
        "recursion is validated bit-exact vs a from-scratch reference (the "
        "regression sentinel — unchanged by the S79 detection fix). The "
        "DETECTION (MAP run-length reset) is validated FUNCTIONALLY with a "
        "verified-discriminating negative control: fires on a known change-"
        "point, stays quiet on a no-change-point series. NOT self-parity — the "
        "prior self-parity check passed a detector that detected nothing (the "
        "§5.1 founding case)."
    )

    DGP_N = 300

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_mean_shift_dgp(seed=seed, n=self.DGP_N),
                "y_nocp": _generate_no_cp_dgp(seed=seed, n=self.DGP_N)}

    def _run_engine(self, y) -> dict[str, Any]:
        from techniques.base import RunContext  # type: ignore
        from techniques.bocpd import run as bocpd_run  # type: ignore
        y = np.asarray(y, dtype=np.float64)
        prior_mu = float(np.mean(y))
        ctx = RunContext({
            "run_id": "p3_bocpd_tsl", "technique_id": "bocpd",
            "preset": "Balanced", "seed": 42, "frequency": "irregular",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"hazard_lambda": 200.0, "prior_mu": prior_mu,
                       "prior_kappa": 0.01, "prior_alpha": 0.01,
                       "prior_beta": 0.01, "threshold": 0.5},
        })
        res = bocpd_run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(f"TSL BOCPD failed: {res.get('error_message')}")
        a = res["audit_fields"]
        ts = next((t for t in res["tables"]
                   if "MAP Run Length" in t.get("columns", [])), None)
        if ts is None:
            raise RuntimeError("engine missing the MAP-run-length time-series table")
        cols = ts["columns"]
        mi, ci = cols.index("MAP Run Length"), cols.index("Change Point Prob")
        map_rl = np.array([int(r[mi]) for r in ts["rows"]], dtype=int)
        cp_prob = np.array([float(r[ci]) for r in ts["rows"]], dtype=float)
        return {"n_cps": int(a.get("n_change_points", 0)),
                "cp_indices": [int(x) for x in (a.get("change_point_indices") or [])],
                "map_rl": map_rl, "cp_prob": cp_prob,
                "detection": a.get("detection")}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        known = self._run_engine(fixture["y"])
        nocp = self._run_engine(fixture["y_nocp"])
        return {"known": known, "nocp_n_cps": int(nocp["n_cps"])}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        prior_mu = float(np.mean(y))
        cp_prob, map_rl = _bocpd_reference(
            y, hazard_lambda=200.0, prior_mu=prior_mu,
            prior_kappa=0.01, prior_alpha=0.01, prior_beta=0.01)
        cps = _detect_map_reset(map_rl, min_gap=_MIN_GAP)
        return {"map_rl": map_rl, "cp_prob": cp_prob,
                "n_cps": len(cps), "cp_indices": cps}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        k = tsl["known"]
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        m = min(len(k["map_rl"]), len(ref["map_rl"]))

        # (a) Recursion SENTINEL — engine MAP run-length bit-exact vs reference.
        primary["recursion_map_rl"] = _compare_vector(
            k["map_rl"][:m].astype(float), ref["map_rl"][:m].astype(float), ladder["map_rl"])
        statuses.append(primary["recursion_map_rl"]["status"])
        primary["recursion_cp_prob"] = _compare_vector(
            k["cp_prob"][:m], ref["cp_prob"][:m], ladder["cp_prob"])
        statuses.append(primary["recursion_cp_prob"]["status"])

        # (b) Criterion cross-validation — engine n_cps == reference n_cps.
        primary["n_cps_vs_reference"] = _compare_scalar(
            float(k["n_cps"]), float(ref["n_cps"]), ladder["primary"])
        statuses.append(primary["n_cps_vs_reference"]["status"])

        # (c) Functional POSITIVE — fires within ±tol of the true CP@150.
        locs = list(k["cp_indices"])
        nearest = min((abs(x - _TRUE_CP) for x in locs), default=None)
        pos_ok = (k["n_cps"] >= 1) and (nearest is not None and nearest <= _LOC_TOL)
        primary["functional_positive"] = {
            "status": "PASS" if pos_ok else "BLOCK",
            "n_cps": k["n_cps"], "cp_indices": locs, "true_cp": _TRUE_CP,
            "nearest_dist": nearest}
        statuses.append(primary["functional_positive"]["status"])

        # (d) ★ Functional NEGATIVE CONTROL — no-CP series must stay quiet.
        neg_ok = tsl["nocp_n_cps"] == 0
        primary["functional_negative_control"] = {
            "status": "PASS" if neg_ok else "BLOCK",
            "nocp_n_cps": tsl["nocp_n_cps"],
            "note": "stationary no-change-point series must detect 0 (catches fire-on-everything)"}
        statuses.append(primary["functional_negative_control"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N), "true_cp_index": _TRUE_CP,
                "engine_detection": k.get("detection"),
                "known_n_cps": k["n_cps"], "known_cps": locs,
                "nocp_n_cps": tsl["nocp_n_cps"],
                "ref_n_cps": ref["n_cps"], "ref_cps": ref["cp_indices"],
                "map_rl_max_abs_diff": primary["recursion_map_rl"].get("max_abs_diff"),
            },
        )
