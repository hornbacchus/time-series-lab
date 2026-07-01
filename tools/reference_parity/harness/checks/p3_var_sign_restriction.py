"""ENG-EXT-MULTIVARIATE-001 M3b — Sign-restriction SVAR parity check.

Validates the engine's net-new sign-restriction SVAR identification
(`var_model._sign_restriction_svar`). This is the commission's HARDEST
sub-build and the A-phase's THIRD novel validation kind: SET-IDENTIFICATION
(vs point-parity for M3a/M3c, and M1's band-around-a-point). Sign-restriction
SVAR is SET-identified — it admits a SET of structural impact matrices,
explored by Haar rotation sampling and summarized by the median-target +
16/84 percentile bands over admissible rotations.

statsmodels has no sign-restriction and NO usable cross-package R package
exists (svars is the wrong family; VARsignR is CRAN-archived), so this is a
SELF-PARITY check (the A1b/A1c/C3/M3c fallback) PLUS LOAD-BEARING functional
checks — the A1c blind-spot mitigation at its sharpest (set-identified +
self-parity-only). Two complementary arms (each validates a DIFFERENT thing):

- SELF-PARITY (tight) — the set MACHINERY / implementation-correctness: engine
  `_sign_restriction_svar` vs a from-scratch reimplementation of the IDENTICAL
  rotation sampling (same seed, draw count, QR sign-normalization, diagonal-
  normalization, retention rule) → the SAME retained set → bit-exact set
  summary (median impact + median/lo16/hi84 IRF bands).

- LOAD-BEARING functional checks — FORMULATION-correctness (the substitute for
  the absent cross-package arm), set-identification has CHECKABLE INVARIANTS.
  Flag A deep-confirm: RECOMPUTED IN-CHECK from the emitted outputs (the
  retained set + sigma_u) with an INDEPENDENTLY re-expressed predicate — the
  engine-reported scalars are cross-checked diagnostics, never gate inputs
  (closes the self-report tautology: rotations retained BY the engine's
  predicate trivially satisfied the engine's predicate):
  * sign_satisfaction == 1.0 (every retained rotation satisfies the signs;
    a retention/predicate bug → < 1.0). Demonstrated at output level.
  * factorization_preservation (every retained B0 satisfies B0·B0' == Σ̂ to
    float-tight tolerance — the genuine set-construction invariant; with
    sign_satisfaction it enforces BOTH halves of set-membership
    {B0 : B0B0' = Σ, signs hold}). Demonstrated at output level. This is the
    Flag A SWAP for the cholesky_in_set gate, which was found VACUOUS on this
    fixture (lower-triangular Cholesky + R restricting only row 0 + diag ⟹
    the predicate can never fire — ~485k adversarial sigma_u probes, 0
    BLOCKs); cholesky_admissible is demoted to a consistency-cross-checked
    diagnostic.
  * economic_sign (the median impact's restricted entries have the correct
    restricted sign). Demonstrated at output level.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_sign_dgp(*, seed: int, n: int = 500):
    """VAR(1) with a known structural B whose impact signs match the test
    restriction (shock 1 has a negative impact on variable 0)."""
    rng = np.random.default_rng(seed)
    k = 2
    B_true = np.array([[1.0, -0.5], [0.4, 1.0]])
    A = np.array([[0.5, 0.1], [0.2, 0.4]])
    eps = rng.standard_normal((n, k))
    u = eps @ B_true.T
    Y = np.zeros((n, k))
    for t in range(1, n):
        Y[t] = A @ Y[t - 1] + u[t]
    return Y


def _ref_sign_restriction(Y, p, R, n_draws, seed, steps):
    """From-scratch reimplementation of the IDENTICAL rotation-sampling
    formulation the engine `_sign_restriction_svar` implements (same Haar QR
    + sign-normalization, diagonal-normalization, retention, set summary).
    Bit-exact agreement confirms the engine implements this exact formulation.
    """
    from statsmodels.tsa.api import VAR
    Y = np.asarray(Y, dtype=np.float64)
    fit = VAR(Y).fit(p, trend="c")
    P = np.linalg.cholesky(np.asarray(fit.sigma_u, dtype=np.float64))
    k = P.shape[0]
    R = np.asarray(R, dtype=np.float64)
    Phi = np.asarray(fit.ma_rep(maxn=steps), dtype=np.float64)

    def diag_norm(B0):
        for j in range(k):
            if B0[j, j] < 0:
                B0[:, j] = -B0[:, j]
        return B0

    def ok(B0):
        for i in range(k):
            for j in range(k):
                if R[i, j] > 0 and B0[i, j] < -1e-12:
                    return False
                if R[i, j] < 0 and B0[i, j] > 1e-12:
                    return False
        return True

    rs = np.random.RandomState(seed)
    kept = []
    for _ in range(n_draws):
        Q, Rqr = np.linalg.qr(rs.standard_normal((k, k)))
        Q = Q @ np.diag(np.sign(np.diag(Rqr)))
        B0 = diag_norm((P @ Q).copy())
        if ok(B0):
            kept.append(B0)
    K = np.array(kept)
    Theta = np.array([np.einsum("hrs,sc->hrc", Phi, B0) for B0 in kept])
    return {
        "median_b0": np.median(K, axis=0),
        "median_irf": np.median(Theta, axis=0),
        "lo16": np.percentile(Theta, 16, axis=0),
        "hi84": np.percentile(Theta, 84, axis=0),
    }


class VarSignRestrictionParity(P3ParityCheck):
    """Sign-restriction SVAR set-identification: self-parity + load-bearing
    functional checks (ENG-EXT-MULTIVARIATE-001 M3b)."""

    technique_id = "p3_var_sign_restriction"
    tier = "fast"
    fixture_id = ""

    verdict_class = "bootstrap_distributional"
    verdict_class_rationale = (
        "Sign-restriction SVAR (ENG-EXT-MULTIVARIATE-001 M3b) is "
        "SET-identified — the third validation kind. The admissible set "
        "(over Haar rotations) is summarized by median-target + 16/84 bands, "
        "the same percentile-band structure as M1's bootstrap_distributional "
        "(rotation sampling ≈ bootstrap resampling), so the class is reused. "
        "No usable cross-package library → self-parity (matched rotation "
        "sampling → bit-exact set summary) + LOAD-BEARING functional checks "
        "(sign-satisfaction == 1.0; factorization preservation B0·B0' == Σ̂ "
        "over every retained draw — the genuine set-construction invariant; "
        "economic sign) as the formulation-correctness substitute (A1c). "
        "Flag A deep-confirm: all three gates recomputed in-check from the "
        "emitted outputs with an independently re-expressed predicate (the "
        "engine scalars are cross-checked diagnostics, never gate inputs) "
        "and DEMONSTRATED discriminating at output level."
    )

    DGP_N = 500
    P_FIT = 1
    STEPS = 8
    N_DRAWS = 2000
    SEED = 42

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # R: diagonal +1 (normalization) + shock1→var0 ≤ 0 (the discriminating
        # restriction; matches B_true[0,1] = -0.5).
        R = np.array([[1.0, -1.0], [0.0, 1.0]])
        return {"Y": _generate_sign_dgp(seed=seed, n=self.DGP_N), "R": R}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.api import VAR  # type: ignore
        from techniques.var_model import _sign_restriction_svar  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        R = np.asarray(fixture["R"], dtype=np.float64)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = VAR(Y).fit(self.P_FIT, trend="c")
            sr = _sign_restriction_svar(fit, R, self.N_DRAWS, self.SEED, self.STEPS)
        return {
            "median_b0": sr["median_b0"], "median_irf": sr["median_irf"],
            "lo16": sr["lo16"], "hi84": sr["hi84"],
            "n_retained": sr["n_retained"],
            "sign_satisfaction": sr["sign_satisfaction"],
            "cholesky_admissible": sr["cholesky_admissible"],
            # the retained SET + reduced-form covariance are emitted so
            # compare() recomputes the functional gates in-check from the
            # outputs — the engine-reported scalars are cross-checked
            # diagnostics, never gate inputs (the self-report-tautology fix)
            "kept": np.asarray(sr["kept"], dtype=np.float64),
            "sigma_u": np.asarray(fit.sigma_u, dtype=np.float64),
            "R": R,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return _ref_sign_restriction(
            fixture["Y"], self.P_FIT, fixture["R"], self.N_DRAWS, self.SEED, self.STEPS)

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # --- self-parity set-summary arm (bit-exact) ---
        tsl_vec = np.concatenate([
            np.asarray(tsl[kk]).reshape(-1)
            for kk in ("median_b0", "median_irf", "lo16", "hi84")])
        ref_vec = np.concatenate([
            np.asarray(ref[kk]).reshape(-1)
            for kk in ("median_b0", "median_irf", "lo16", "hi84")])
        primary["set_summary_selfparity"] = _compare_vector(
            tsl_vec, ref_vec, ladder["set_summary_selfparity"])
        statuses.append(primary["set_summary_selfparity"]["status"])

        # --- LOAD-BEARING functional checks, RECOMPUTED in-check from the
        # emitted outputs (output-level; the engine-reported scalars are
        # cross-checked below, never gated on). The predicate is re-expressed
        # INDEPENDENTLY (vectorized elementwise vs R's nonzero entries, own
        # diag-normalization, library cholesky) — NOT imported from the
        # engine, so a shared-predicate bug cannot self-certify. The ±1e-12
        # slack matches the scheme's retention convention (same spec,
        # independent implementation). ---
        R = np.asarray(tsl["R"], dtype=np.float64)

        def _violates(B0: np.ndarray) -> bool:
            return bool((((R > 0) & (B0 < -1e-12)) |
                         ((R < 0) & (B0 > 1e-12))).any())

        kept = np.asarray(tsl["kept"], dtype=np.float64)
        n_kept = int(kept.shape[0]) if kept.ndim == 3 else 0
        ss = (float(np.mean([0.0 if _violates(B0) else 1.0 for B0 in kept]))
              if n_kept else 0.0)
        min_frac = float(ladder["sign_satisfaction"]["min_frac"])
        ss_status = "PASS" if ss >= min_frac - 1e-12 else "BLOCK"
        primary["sign_satisfaction"] = {"status": ss_status, "fraction": round(ss, 6)}
        statuses.append(ss_status)

        # --- factorization preservation — the genuine set-construction
        # invariant (the Flag A swap for the fixture-vacuous cholesky gate):
        # every retained B0 = chol(Σ)·Q (diag-normalized) must satisfy
        # B0 @ B0.T == Σ̂ (Q orthogonal ⟹ B0B0' = PP' = Σ̂; the column sign
        # flips preserve it). With recomputed sign_satisfaction this enforces
        # BOTH halves of set-membership {B0 : B0B0' = Σ, signs hold} on every
        # retained draw — guarding the chol/QR/orthogonality/diag-normalize/
        # retention pipeline. Recomputed in-check from the emitted set;
        # PASS iff residual <= tol, so a NaN-bearing corruption lands BLOCK
        # (NaN fails the comparison), not a silent PASS. ---
        sigma_u = np.asarray(tsl["sigma_u"], dtype=np.float64)
        fact_tol = float(ladder["factorization_preservation"]["abs_tol"])
        fact_resid = (float(np.abs(np.einsum("mij,mkj->mik", kept, kept)
                                   - sigma_u[None]).max())
                      if n_kept else float("nan"))
        fact_status = "PASS" if fact_resid <= fact_tol else "BLOCK"
        primary["factorization_preservation"] = {
            "status": fact_status,
            "max_abs_resid": fact_resid,
            "abs_tol": fact_tol,
        }
        statuses.append(fact_status)

        # Cholesky admissibility — DEMOTED to a consistency-cross-checked
        # diagnostic (the Flag A vacuity finding: lower-triangular chol +
        # this fixture's R can never violate the predicate, so as a GATE it
        # had no discrimination power). Still recomputed here and
        # cross-checked vs the engine-reported scalar below; NOT gated.
        P = np.linalg.cholesky(sigma_u)
        Pn = P * np.where(np.diag(P) < 0.0, -1.0, 1.0)[None, :]
        chol_ok = bool(not _violates(Pn))

        # economic sign: median impact's restricted entries match R's sign
        mb = np.asarray(tsl["median_b0"], dtype=np.float64)
        econ_ok = True
        for i in range(R.shape[0]):
            for j in range(R.shape[1]):
                if R[i, j] > 0 and mb[i, j] < -1e-9:
                    econ_ok = False
                if R[i, j] < 0 and mb[i, j] > 1e-9:
                    econ_ok = False
        econ_status = "PASS" if econ_ok else "BLOCK"
        primary["economic_sign"] = {"status": econ_status, "median_b0_ok": econ_ok}
        statuses.append(econ_status)

        # --- consistency: the recomputed gate values vs the engine-reported
        # scalars (material divergence on a real build = a live engine bug or
        # a predicate-convention mismatch — surfaced, never papered over) ---
        cons_tol = float(ladder["engine_scalar_consistency"]["abs_tol"])
        d_ss = abs(ss - float(tsl["sign_satisfaction"]))
        chol_match = bool(chol_ok == bool(tsl["cholesky_admissible"]))
        cons_status = "PASS" if (d_ss <= cons_tol and chol_match) else "BLOCK"
        primary["engine_scalar_consistency"] = {
            "status": cons_status,
            "sign_satisfaction_diff": d_ss,
            "cholesky_match": chol_match,
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
                "n_obs": int(self.DGP_N), "n_draws": int(self.N_DRAWS),
                "n_retained": int(tsl["n_retained"]),
                "n_kept_emitted": n_kept,
                "retention_frac": round(tsl["n_retained"] / self.N_DRAWS, 4),
                "sign_satisfaction": round(ss, 6),
                "sign_satisfaction_reported": round(float(tsl["sign_satisfaction"]), 6),
                "factorization_max_resid": fact_resid,
                "cholesky_admissible": chol_ok,
                "cholesky_admissible_reported": bool(tsl["cholesky_admissible"]),
                "set_summary_max_abs": primary["set_summary_selfparity"].get("max_abs_diff"),
            },
        )
