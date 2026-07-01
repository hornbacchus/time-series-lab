"""ENG-EXT-MULTIVARIATE-001 M3c — Proxy / IV-SVAR parity check.

Validates the engine's net-new proxy / external-instrument SVAR
identification (`var_model._proxy_svar`). statsmodels SVAR is A/B/AB
short-run only and NO usable cross-package R package exists (the svars
finding: svars covers heteroskedasticity ID, not proxy-SVAR), so this is a
SELF-PARITY check (the A1b/A1c/C3 fallback) PLUS a LOAD-BEARING
instrument-relevance functional check.

Two complementary arms (each validates a DIFFERENT thing — the A1c lesson):

- SELF-PARITY (tight, bit-exact) — the band MACHINERY / implementation-
  correctness: engine `_proxy_svar` vs a from-scratch reimplementation of the
  IDENTICAL formulation (same Cov(u,z) estimator, same normalize-to-reference-
  variable, same GLS projection) → bit-exact impact vector + structural IRF.

- INSTRUMENT-RELEVANCE FUNCTIONAL CHECK (load-bearing) — FORMULATION-
  correctness, the substitute for the absent cross-package arm: the scheme-
  DEFINING property of proxy identification is that the identified shock
  CORRELATES with the instrument (instrument relevance / first stage). A
  formulation bug producing a shock NOT correlated with the instrument FAILS
  this check. RECOMPUTED IN-CHECK from the emitted shock series (Flag A
  deep-confirm) — the engine-reported relevance scalar is a cross-checked
  diagnostic, never a gate input (closes the self-report tautology). Plus a
  GATED negative control (the shock must NOT correlate with the irrelevant
  instrument — catches vacuous relevance) and a DGP-RECOVERY known-answer arm
  (b1 must recover B_true's target column [1.0, 0.5] — correctness, beyond
  self-parity's match-not-correctness). Discrimination DEMONSTRATED at output
  level (corrupted eps_hat / eps_hat_irrel / b1 each BLOCK). NOT soft
  diagnostics.

This is the FIRST self-parity SVAR (M3a was cross-package); it establishes the
self-parity-SVAR pattern + the load-bearing-functional-check discipline that
M3b (sign-restriction) extends.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_proxy_dgp(*, seed: int, n: int = 600):
    """VAR(1) with known structural B (u = B ε) + a RELEVANT external
    instrument z = ε[:,0] + noise (correlated with the target shock 1,
    uncorrelated with the others). The proxy-SVAR recovers the target
    column AND the instrument-relevance check passes by construction.
    Returns (Y, z, z_irrelevant)."""
    rng = np.random.default_rng(seed)
    k = 2
    B_true = np.array([[1.0, 0.4], [0.5, 1.0]])
    A = np.array([[0.5, 0.1], [0.2, 0.4]])
    eps = rng.standard_normal((n, k))
    u = eps @ B_true.T
    Y = np.zeros((n, k))
    for t in range(1, n):
        Y[t] = A @ Y[t - 1] + u[t]
    z = eps[:, 0] + 0.5 * rng.standard_normal(n)     # relevant for shock 1
    z_irrel = rng.standard_normal(n)                  # irrelevant control
    return Y, z, z_irrel


def _ref_proxy_svar(Y, p, instrument, steps, normalize_var=0):
    """From-scratch reimplementation of the IDENTICAL proxy-SVAR formulation
    the engine `_proxy_svar` implements (same Cov(u,z) estimator, same
    normalize-to-reference-variable, same GLS-projected shock). Bit-exact
    agreement confirms the engine implements this exact formulation."""
    from statsmodels.tsa.api import VAR
    Y = np.asarray(Y, dtype=np.float64)
    fit = VAR(Y).fit(p, trend="c")
    u = np.asarray(fit.resid, dtype=np.float64)
    nobs = u.shape[0]
    z = np.asarray(instrument, dtype=np.float64).reshape(-1)[-nobs:]
    z = z - z.mean()
    cov_uz = (u * z[:, None]).mean(axis=0)
    b1 = cov_uz / cov_uz[normalize_var]
    Sinv = np.linalg.inv(np.asarray(fit.sigma_u, dtype=np.float64))
    eps_hat = (u @ Sinv @ b1) / float(b1 @ Sinv @ b1)
    relevance = float(np.corrcoef(eps_hat, z)[0, 1])
    Phi = np.asarray(fit.ma_rep(maxn=steps), dtype=np.float64)
    sirf = np.array([Phi[h] @ b1 for h in range(Phi.shape[0])])  # (steps+1, k)
    return b1, sirf, relevance


class VarProxySvarParity(P3ParityCheck):
    """Proxy / IV-SVAR self-parity + instrument-relevance functional check
    (ENG-EXT-MULTIVARIATE-001 M3c)."""

    technique_id = "p3_var_proxy_svar"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Proxy/IV-SVAR identification (ENG-EXT-MULTIVARIATE-001 M3c) is "
        "deterministic closed-form covariance algebra (b1 ∝ Cov(u,z) "
        "normalized; GLS-projected shock; structural IRF = ma_rep @ b1). No "
        "usable cross-package library exists (svars is the wrong family), so "
        "the reference is a from-scratch reimplementation of the IDENTICAL "
        "formulation → bit-exact impact vector + structural IRF (machinery). "
        "The LOAD-BEARING instrument-relevance functional check (corr of the "
        "identified shock with the instrument > 0.2 — the scheme-defining "
        "property) is the formulation-correctness substitute for the absent "
        "cross-package arm (A1c self-parity-validates-match-not-correctness). "
        "Flag A deep-confirm: the relevance gate is RECOMPUTED in-check from "
        "the emitted shock series (engine scalars cross-checked, never gated "
        "on); the irrelevant-instrument negative control is GATED; and a "
        "DGP-recovery known-answer arm (b1 vs the known [1.0, 0.5]) validates "
        "correctness beyond match. All demonstrated discriminating at output "
        "level."
    )

    DGP_N = 600
    P_FIT = 1
    STEPS = 10
    NORMALIZE_VAR = 0
    # DGP truth for the recovery arm: B_true[:, 0] / B_true[NORMALIZE_VAR, 0]
    # (see _generate_proxy_dgp) — the known answer the proxy-SVAR must recover.
    B0_TARGET = (1.0, 0.5)

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        Y, z, z_irrel = _generate_proxy_dgp(seed=seed, n=self.DGP_N)
        return {"Y": Y, "z": z, "z_irrel": z_irrel}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.api import VAR  # type: ignore
        from techniques.var_model import _proxy_svar  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        z = np.asarray(fixture["z"], dtype=np.float64)
        z_irrel = np.asarray(fixture["z_irrel"], dtype=np.float64)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = VAR(Y).fit(self.P_FIT, trend="c")
            b1, eps_hat, relevance = _proxy_svar(
                fit, z, normalize_var=self.NORMALIZE_VAR)
            Phi = np.asarray(fit.ma_rep(maxn=self.STEPS), dtype=np.float64)
            sirf = np.array([Phi[h] @ b1 for h in range(Phi.shape[0])])
            # control: the identified shock on the irrelevant instrument.
            # The shock SERIES (not just the engine's relevance scalars) are
            # emitted so compare() recomputes both relevance gates in-check
            # from the outputs — the engine-reported scalars are cross-checked
            # diagnostics, never gate inputs (the self-report-tautology fix).
            _, eps_hat_irrel, rel_irrel = _proxy_svar(
                fit, z_irrel, normalize_var=self.NORMALIZE_VAR)
        return {"b1": b1, "sirf": sirf, "relevance": float(relevance),
                "relevance_irrelevant": float(rel_irrel),
                "eps_hat": np.asarray(eps_hat, dtype=np.float64),
                "eps_hat_irrel": np.asarray(eps_hat_irrel, dtype=np.float64),
                "z": z, "z_irrel": z_irrel}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        b1, sirf, relevance = _ref_proxy_svar(
            fixture["Y"], self.P_FIT, fixture["z"], self.STEPS,
            normalize_var=self.NORMALIZE_VAR)
        return {"b1": b1, "sirf": sirf, "relevance": float(relevance)}

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # --- self-parity arms (machinery, bit-exact) ---
        primary["b1_selfparity"] = _compare_vector(
            np.asarray(tsl["b1"]).reshape(-1),
            np.asarray(ref["b1"]).reshape(-1), ladder["b1_selfparity"])
        primary["struct_irf_selfparity"] = _compare_vector(
            np.asarray(tsl["sirf"]).reshape(-1),
            np.asarray(ref["sirf"]).reshape(-1), ladder["struct_irf_selfparity"])
        statuses.append(primary["b1_selfparity"]["status"])
        statuses.append(primary["struct_irf_selfparity"]["status"])

        # --- LOAD-BEARING instrument-relevance functional check, RECOMPUTED
        # in-check from the emitted shock series (output-level; the engine-
        # reported scalar is cross-checked below, never gated on) ---
        min_corr = float(ladder["instrument_relevance"]["min_corr"])
        eps = np.asarray(tsl["eps_hat"], dtype=np.float64).reshape(-1)
        z = np.asarray(tsl["z"], dtype=np.float64).reshape(-1)[-eps.shape[0]:]
        corr = float(abs(np.corrcoef(eps, z)[0, 1]))
        rel_status = "PASS" if corr >= min_corr else "BLOCK"
        primary["instrument_relevance"] = {
            "status": rel_status,
            "corr": round(corr, 6),
            "min_corr": min_corr,
        }
        statuses.append(rel_status)

        # --- negative-control gate: the identified shock must NOT correlate
        # with the IRRELEVANT instrument (a vacuous-relevance bug — a shock
        # correlating with EVERY instrument — passes the relevant arm but
        # fails this one) ---
        eps_i = np.asarray(tsl["eps_hat_irrel"], dtype=np.float64).reshape(-1)
        z_i = np.asarray(
            tsl["z_irrel"], dtype=np.float64).reshape(-1)[-eps_i.shape[0]:]
        ctrl = float(abs(np.corrcoef(eps_i, z_i)[0, 1]))
        ctrl_status = "PASS" if ctrl < min_corr else "BLOCK"
        primary["irrelevant_control"] = {
            "status": ctrl_status,
            "corr": round(ctrl, 6),
            "max_corr": min_corr,
        }
        statuses.append(ctrl_status)

        # --- DGP-recovery known-answer arm: b1 must recover the DGP truth
        # B_true[:, 0] normalized to the reference variable = [1.0, 0.5]
        # (CORRECTNESS, beyond self-parity's match-not-correctness; tol
        # calibrated across seeds — see the ladder justification) ---
        rec_tol = float(ladder["b0_recovery"]["abs_tol"])
        target = np.asarray(self.B0_TARGET, dtype=np.float64)
        rec_dist = float(np.max(np.abs(
            np.asarray(tsl["b1"], dtype=np.float64).reshape(-1) - target)))
        rec_status = "PASS" if rec_dist <= rec_tol else "BLOCK"
        primary["b0_recovery"] = {
            "status": rec_status,
            "max_abs_dist": round(rec_dist, 6),
            "abs_tol": rec_tol,
        }
        statuses.append(rec_status)

        # --- consistency: the recomputed gate values vs the engine-reported
        # scalars (material divergence on a real build = a live engine bug or
        # a convention mismatch — surfaced, never papered over) ---
        cons_tol = float(ladder["engine_scalar_consistency"]["abs_tol"])
        d_rel = abs(corr - abs(float(tsl["relevance"])))
        d_ctrl = abs(ctrl - abs(float(tsl["relevance_irrelevant"])))
        cons_status = "PASS" if max(d_rel, d_ctrl) <= cons_tol else "BLOCK"
        primary["engine_scalar_consistency"] = {
            "status": cons_status,
            "relevance_diff": d_rel,
            "control_diff": d_ctrl,
            "abs_tol": cons_tol,
        }
        statuses.append(cons_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "b1_max_abs": primary["b1_selfparity"].get("max_abs_diff"),
                "sirf_max_abs": primary["struct_irf_selfparity"].get("max_abs_diff"),
                "relevance_corr": round(corr, 6),
                "relevance_corr_reported": round(float(tsl["relevance"]), 6),
                "irrelevant_control": round(ctrl, 6),
                "irrelevant_control_reported": round(float(tsl.get("relevance_irrelevant", 0.0)), 6),
                "b0_recovery_dist": round(rec_dist, 6),
            },
        )
