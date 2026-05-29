"""ENG-EXT-MULTIVARIATE-001 M1 — VAR IRF confidence-band parity check.

The FIRST interval/band validation in the audit (Q1 was point-estimate
only). Validates the bootstrap confidence bands that ``var_model.py`` now
puts around the orthogonalized point IRF, via a NEW three-arm
``bootstrap_band`` pattern (verdict_class ``bootstrap_band``; tier concept
``II.interval-band`` — the metric is band width-ratio + coverage, NOT point
max_abs_diff). The pattern is general and is reused by ENG-EXT-CONFORMAL-001
(prediction-interval coverage) via an ``empirical_coverage`` sibling.

Why three arms (the A1c lesson designed in — each validates a DIFFERENT
thing, BOTH load-bearing arms required):

- ARM 1 — SELF-PARITY (tight, in-engine) — validates the band MACHINERY
  (implementation-correctness). The engine helper ``_mc_irf_bands`` vs a
  from-scratch reimplementation of the IDENTICAL Monte-Carlo formulation
  (same distinct-per-replication-seed scheme, same percentile indices) →
  near-bit-exact band endpoints. Catches engine bootstrap IMPLEMENTATION
  bugs (the A1b/A1c self-parity discipline applied to intervals).

- ARM 2 — CROSS-PACKAGE (load-bearing, distributional) — validates the
  FORMULATION (formulation-correctness). vs R ``vars::irf(boot=TRUE)``.
  Compared on band GEOMETRY (width-ratio + containment), NOT endpoint
  equality. THIS ARM GATES — a width-ratio or containment failure is a
  finding, NOT a soft diagnostic. Without a load-bearing cross-package arm
  this would be the S79 trap (self-parity validates match, not
  correctness) with cosmetic garnish.

- ARM 3 — POINT ANCHOR (existing pattern) — the band center (engine
  orthogonalized point IRF) vs R ``vars::irf`` point IRF (~1e-6). The bands
  wrap an already-1c/p3_var-validated point estimate.

Method-difference note (shapes the cross-package tolerance): the engine
band is a PARAMETRIC Gaussian Monte-Carlo bootstrap (simulate from the
fitted VAR, refit, percentile); R ``vars::irf`` is a RESIDUAL-RESAMPLING
bootstrap. Different methods → endpoints can never match → the
cross-package arm is inherently distributional (width/coverage). The DGP
uses GAUSSIAN innovations so the two methods CONVERGE (residual-resampling
of ~Gaussian residuals ≈ parametric-Gaussian MC), making the width-ratio
tolerance meaningful. The width-ratio tolerance is calibrated UNDER THE
GAUSSIAN-INNOVATION ASSUMPTION; on a non-Gaussian DGP the methods would
legitimately diverge and the tolerance would need widening.

Upstream-bug note: statsmodels ``IRAnalysis.errband_mc`` / ``irf_resim``
passes the SAME fixed seed to ``util.varsim`` on every replication, so all
replications are identical → a ZERO-WIDTH degenerate band; ``seed=None``
restores variance but is non-deterministic. The engine therefore uses its
own ``_mc_irf_bands`` (distinct per-replication seeds derived from
ctx.seed) — proper variance AND determinism. Banked as an upstream finding.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_gaussian_var1_dgp(
    *, seed: int, n: int = 500, k: int = 2, burn: int = 200,
) -> np.ndarray:
    """Stationary bivariate VAR(1) with GAUSSIAN innovations (Sigma = I).

    Gaussian innovations are load-bearing: they make the engine's
    parametric-Gaussian-MC bootstrap and R's residual-resampling bootstrap
    converge, so the cross-package width-ratio tolerance is meaningful.
    Companion eigenvalues well inside the unit circle.
    """
    rng = np.random.default_rng(seed)
    A1 = np.array([[0.5, 0.1], [0.2, 0.4]])
    n_total = n + burn
    Y = np.zeros((n_total, k))
    eps = rng.standard_normal((n_total, k))
    for t in range(1, n_total):
        Y[t] = A1 @ Y[t - 1] + eps[t]
    return Y[burn:]


def _ref_mc_irf_bands_from_scratch(
    Y, p, steps, repl, signif, seed, orth=True, burn=100,
):
    """ARM 1 reference: from-scratch reimplementation of the IDENTICAL
    Monte-Carlo IRF-band formulation the engine ``_mc_irf_bands`` helper
    implements — INDEPENDENT of the engine code, mirroring the spec
    exactly (master ``RandomState(seed)`` → ``repl`` distinct child seeds →
    per-replication ``util.varsim`` simulation → refit → orth_ma_rep →
    signif/2 & 1-signif/2 percentiles). Bit-exact agreement confirms the
    engine implements this exact formulation correctly.
    """
    from statsmodels.tsa.api import VAR
    from statsmodels.tsa.vector_ar import util

    Y = np.asarray(Y, dtype=np.float64)
    fit = VAR(Y).fit(p, trend="c")
    coefs = fit.coefs
    intercept = fit.intercept
    sigma_u = fit.sigma_u
    k_ar = fit.k_ar
    neqs = fit.neqs
    nobs = fit.nobs
    trend = fit.trend
    exog = getattr(fit, "exog", None)
    nobs_original = nobs + k_ar

    master = np.random.RandomState(seed)
    child_seeds = master.randint(0, 2 ** 31 - 1, size=repl)

    ma_coll = np.zeros((repl, steps + 1, neqs, neqs))
    for i in range(repl):
        sim = util.varsim(
            coefs, intercept, sigma_u,
            seed=int(child_seeds[i]), steps=nobs_original + burn,
        )[burn:]
        refit = VAR(sim, exog=exog).fit(maxlags=k_ar, trend=trend)
        ma = refit.orth_ma_rep(maxn=steps) if orth else refit.ma_rep(maxn=steps)
        ma_coll[i, :, :, :] = ma

    ma_sort = np.sort(ma_coll, axis=0)
    low_idx = int(round(signif / 2 * repl) - 1)
    upp_idx = int(round((1 - signif / 2) * repl) - 1)
    return ma_sort[low_idx, :, :, :], ma_sort[upp_idx, :, :, :]


class VarIrfBandsParity(P3ParityCheck):
    """VAR IRF confidence-band parity — the bootstrap_band three-arm
    interval-validation pattern (ENG-EXT-MULTIVARIATE-001 M1)."""

    technique_id = "p3_var_irf_bands"
    tier = "fast"
    fixture_id = ""

    # First INSTANTIATION of the reserved ``bootstrap_distributional``
    # verdict_class (registered since Batch 10 but never used). M1 is the
    # audit's first interval/band validation; its sibling
    # ``conformal_coverage`` is reserved for ENG-EXT-CONFORMAL-001's
    # prediction-interval coverage.
    verdict_class = "bootstrap_distributional"
    verdict_class_rationale = (
        "VAR IRF confidence bands (ENG-EXT-MULTIVARIATE-001 M1) — the FIRST "
        "use of the reserved bootstrap_distributional class and the audit's "
        "first interval/band validation. Bands are bootstrap percentile "
        "ENVELOPES, not points, so a three-arm pattern is used: ARM 1 "
        "self-parity (engine _mc_irf_bands vs from-scratch identical MC → "
        "near-bit-exact endpoints; band MACHINERY / implementation-"
        "correctness); ARM 2 cross-package vs R vars::irf (band width-ratio "
        "+ containment, LOAD-BEARING, distributional — FORMULATION-"
        "correctness, the A1c lesson that self-parity validates "
        "match-not-correctness); ARM 3 point anchor (band center vs R point "
        "IRF, ~1e-6). The cross-package arm is inherently distributional "
        "(engine parametric-Gaussian-MC vs R residual-resampling — different "
        "methods); the Gaussian-innovation DGP makes them converge so the "
        "width-ratio tolerance is meaningful. Pattern generalizes to "
        "CONFORMAL-001 (the conformal_coverage sibling)."
    )

    DGP_N = 500
    DGP_K = 2
    P_FIT = 1
    STEPS = 10
    REPL = 500
    SIGNIF = 0.05
    SEED = 42

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "Y": _generate_gaussian_var1_dgp(
                seed=seed, n=self.DGP_N, k=self.DGP_K,
            ),
        }

    # ---------------------------------------------------------------- TSL
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.api import VAR  # type: ignore
        from techniques.var_model import _mc_irf_bands  # type: ignore
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            fit = VAR(Y).fit(self.P_FIT, trend="c")
            lower, upper = _mc_irf_bands(
                fit, self.STEPS, self.REPL, self.SIGNIF, self.SEED, orth=True,
            )
            point = np.asarray(fit.irf(self.STEPS).orth_irfs, dtype=np.float64)
        return {
            "band_lower": np.asarray(lower, dtype=np.float64),
            "band_upper": np.asarray(upper, dtype=np.float64),
            "point": point,
        }

    # ---------------------------------------------------------- Reference
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import warnings as _w

        Y = np.asarray(fixture["Y"], dtype=np.float64)

        # ARM 1 — self-parity (from-scratch identical MC).
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            sp_lower, sp_upper = _ref_mc_irf_bands_from_scratch(
                Y, self.P_FIT, self.STEPS, self.REPL, self.SIGNIF, self.SEED,
                orth=True,
            )

        # ARM 2 + ARM 3 — cross-package R vars::irf (residual-resampling
        # bootstrap bands + orthogonalized point IRF).
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        r_code = rf"""
            suppressPackageStartupMessages({{ library(vars) }})
            Y <- as.matrix(read.csv("{{{{INPUT_Y}}}}", header=FALSE))
            k <- ncol(Y)
            H <- {self.STEPS} + 1
            fit <- VAR(Y, p = {self.P_FIT}, type = "const")
            ir <- vars::irf(fit, n.ahead = {self.STEPS}, ortho = TRUE,
                            boot = TRUE, ci = {1 - self.SIGNIF},
                            runs = {self.REPL}, seed = {self.SEED})
            # ir$irf / ir$Lower / ir$Upper are lists indexed by impulse
            # variable; each element is an (H x k) matrix (rows = horizon
            # 0..n.ahead, cols = response). Build arr[h, resp, imp].
            to_arr <- function(comp) {{
                arr <- array(0, dim = c(H, k, k))
                for (imp in 1:k) {{
                    arr[, , imp] <- as.matrix(comp[[imp]])
                }}
                arr
            }}
            pt <- to_arr(ir$irf)
            lo <- to_arr(ir$Lower)
            up <- to_arr(ir$Upper)
            write.table(matrix(as.numeric(pt), ncol = 1),
                        "{{{{OUTPUT_point}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(lo), ncol = 1),
                        "{{{{OUTPUT_lower}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(up), ncol = 1),
                        "{{{{OUTPUT_upper}}}}", sep = ",",
                        row.names = FALSE, col.names = FALSE)
        """
        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"Y": Y},
            output_names=["point", "lower", "upper"],
            timeout_sec=180,
            capture_versions_for=["vars"],
        )
        H = self.STEPS + 1
        k = self.DGP_K
        shape = (H, k, k)
        r_point = np.atleast_1d(outputs["point"]).astype(np.float64).reshape(shape, order="F")
        r_lower = np.atleast_1d(outputs["lower"]).astype(np.float64).reshape(shape, order="F")
        r_upper = np.atleast_1d(outputs["upper"]).astype(np.float64).reshape(shape, order="F")
        return {
            "sp_lower": sp_lower,
            "sp_upper": sp_upper,
            "r_point": r_point,
            "r_lower": r_lower,
            "r_upper": r_upper,
            "vars_version": versions.get("vars", "unknown"),
        }

    # ------------------------------------------------------------ Compare
    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        tsl_lower = np.asarray(tsl["band_lower"], dtype=np.float64)
        tsl_upper = np.asarray(tsl["band_upper"], dtype=np.float64)
        tsl_point = np.asarray(tsl["point"], dtype=np.float64)

        # --- ARM 1: self-parity endpoints (tight) ---
        sp_concat_tsl = np.concatenate([tsl_lower.reshape(-1), tsl_upper.reshape(-1)])
        sp_concat_ref = np.concatenate([
            np.asarray(ref["sp_lower"]).reshape(-1),
            np.asarray(ref["sp_upper"]).reshape(-1),
        ])
        primary["selfparity_endpoint"] = _compare_vector(
            sp_concat_tsl, sp_concat_ref, ladder["selfparity_endpoint"],
        )
        statuses.append(primary["selfparity_endpoint"]["status"])

        # --- ARM 3: point anchor (band center vs R point IRF) ---
        primary["point_anchor"] = _compare_vector(
            tsl_point.reshape(-1),
            np.asarray(ref["r_point"]).reshape(-1),
            ladder["point_anchor"],
        )
        statuses.append(primary["point_anchor"]["status"])

        # --- ARM 2: cross-package band geometry (load-bearing) ---
        r_lower = np.asarray(ref["r_lower"], dtype=np.float64)
        r_upper = np.asarray(ref["r_upper"], dtype=np.float64)
        r_point = np.asarray(ref["r_point"], dtype=np.float64)

        w_eng = tsl_upper - tsl_lower
        w_r = r_upper - r_lower
        # Exclude structurally-zero-width cells (e.g. h=0 upper triangle of
        # the orthogonalized IRF, exactly 0 in every replication) so the
        # width-ratio is not 0/0.
        active = np.maximum(np.abs(w_eng), np.abs(w_r)) > 1e-8
        wt = ladder["crosspkg_width_ratio"]
        if np.any(active):
            ratios = w_eng[active] / np.maximum(w_r[active], 1e-300)
            median_ratio = float(np.median(ratios))
        else:
            median_ratio = 1.0
        if wt["pass_lo"] <= median_ratio <= wt["pass_hi"]:
            width_status = "PASS"
        elif wt["block_lo"] <= median_ratio <= wt["block_hi"]:
            width_status = "CAVEAT"
        else:
            width_status = "BLOCK"
        primary["crosspkg_width_ratio"] = {
            "status": width_status,
            "median_width_ratio": median_ratio,
            "n_active_cells": int(np.sum(active)),
        }
        statuses.append(width_status)

        # Containment concordance: engine band contains R's point IRF AND
        # R band contains engine's point IRF (both points bit-close via
        # Arm 3 → this gates band shape/shift).
        eng_contains_r = (tsl_lower <= r_point) & (r_point <= tsl_upper)
        r_contains_eng = (r_lower <= tsl_point) & (tsl_point <= r_upper)
        both = eng_contains_r & r_contains_eng
        containment_frac = float(np.mean(both))
        ct = ladder["crosspkg_containment"]
        if containment_frac >= ct["pass_min"]:
            cov_status = "PASS"
        elif containment_frac >= ct["block_min"]:
            cov_status = "CAVEAT"
        else:
            cov_status = "BLOCK"
        primary["crosspkg_containment"] = {
            "status": cov_status,
            "containment_frac": containment_frac,
        }
        statuses.append(cov_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "vars_version": ref.get("vars_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_vars": int(self.DGP_K),
                "steps": int(self.STEPS),
                "repl": int(self.REPL),
                "signif": float(self.SIGNIF),
                "selfparity_max_abs": primary["selfparity_endpoint"].get("max_abs_diff"),
                "point_anchor_max_abs": primary["point_anchor"].get("max_abs_diff"),
                "median_width_ratio": round(median_ratio, 4),
                "containment_frac": round(containment_frac, 4),
            },
        )
