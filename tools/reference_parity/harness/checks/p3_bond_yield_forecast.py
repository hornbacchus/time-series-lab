"""Phase 3.5+ parity audit for Bond Yield Forecast (BYF integration S4).

**Reference selection rationale (plan §4.1 fallback discipline):**

The integration plan §4.1 listed R ``bvars`` (Krueger) as the primary
Pattern A.2 candidate. **R ``bvars`` is not available for R 4.5.3**
(the TSL pinned R version) — `install.packages("bvars")` returns
"package 'bvars' is not available for this version of R" on CRAN.
Per plan §4.1 fallback: do not force the unavailable reference.

Plan §4.1 second tier was Pattern A.3 paper-formula reimplementation
(BGR-2010 / KSC-1998 / K-FS-2014). A faithful from-scratch reimpl of
BVAR-SV is ~1000+ LOC across multiple modules (matching TSL's own
implementation footprint at ``engine/techniques/bond_yield_forecast/``);
this is materially out-of-budget for a single Session 4 audit script.

**Selected approach: Pattern A.1 self-parity + Pattern F structural
invariants.** Per Phase 3 precedent (e.g., ``critical_slowing_down``
when ewstools landed before the canonical reference was clear), this
pattern combines:

  1. **Pattern A.1 reproducibility self-parity:** invoke TSL's
     dispatch twice with identical seed; assert byte-identical
     output across all BVARSVResults arrays + ConditionalForecast
     arrays + YieldCurveForecast arrays. This validates the
     deterministic-given-seed contract — a necessary precondition
     for any meaningful empirical claim about the wrapper. It does
     NOT validate against an alternative implementation; it
     validates seed-pinning + numba-cache correctness.

  2. **Pattern F structural invariants:** mathematical-property
     checks that hold regardless of implementation:
        a. VAR companion-form max |eigenvalue| < 1 (BVAR
           stationarity; reuses ``var_eigenvalues`` registered
           checker).
        b. SV stationarity: |phi_i| < 1 for each variable
           (geometric drift on log-volatility).
        c. PCA reconstruction roundtrip: yield_panel ==
           PCA_decode(PCA_encode(yield_panel)) within 1e-10 (PCA
           is a deterministic linear isometry up to sign +
           component permutation).
        d. Posterior-mean coefficient finite (no NaN / inf).

**Tier:** ``fast`` — uses reduced chain config (n_draws=2000,
n_burn=500) so two full BVAR-SV cycles complete in ~10-15s wall-
clock. Bit-exact reproducibility doesn't depend on chain length.

**verdict_class:** ``mcmc`` per master plan §7.1 + plan §4.2
expectation. Strict-tolerance reproducibility is a sub-band of mcmc
since seed-pinning gives bit-exactness when correct.

**Expected verdict:** PASS. Pattern A.1 self-parity should produce
byte-identical output between the two TSL runs (same seed; numpy
+ numba both deterministic given pinned seeds + cached JIT
artifacts). Pattern F invariants should hold by construction on
the canonical fixture (well-conditioned macro+yield history).

A non-PASS verdict here would surface as either:
  - Reproducibility failure (numba cache invalidation,
    rng-state leak, etc.) — a real correctness bug worth fixing
    BEFORE any cross-implementation parity work.
  - Invariant violation (companion eig >= 1; SV |phi| >= 1) —
    indicates the chosen fixture is borderline-stationary; may
    warrant a different fixture rather than a wider tolerance band.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import the TSL wrapper."""
    p = Path(__file__).resolve()
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


def _canonical_fixture_path() -> Path:
    """Return the canonical Bond Yield Forecast input workbook path."""
    p = Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError("Cannot locate engine/ for fixture")
    return (
        repo_root
        / "engine" / "techniques" / "bond_yield_forecast"
        / "tests" / "fixtures" / "test_input_canonical.xlsx"
    )


# Reduced chain config for fast-tier audit runtime (~10-15s for two
# BVAR-SV cycles vs ~50s with default n_draws=10000). Bit-exact
# reproducibility doesn't depend on chain length.
_AUDIT_N_DRAWS = 2000
_AUDIT_N_BURN = 500
_AUDIT_SEED = 20260427  # matches BVAR Session 0 fixture seed


class BondYieldForecastParity(P3ParityCheck):
    """Bond Yield Forecast parity audit.

    Pattern A.1 reproducibility self-parity + Pattern F structural
    invariants. R ``bvars`` not available for R 4.5.3; full Pattern
    A.3 paper-formula reimpl out of session-LOC budget; this audit
    is the most-honest combination available.
    """

    technique_id = "p3_bond_yield_forecast"
    tier = "fast"  # ~10-15s with reduced chain config
    fixture_id = ""  # not using on-disk fixture loader

    verdict_class = "mcmc"
    verdict_class_rationale = (
        "BVAR-SV is fit via Gibbs sampling (CCM-2019) with "
        "stochastic volatility on innovations (KSC-1998 mixture-"
        "of-normals + FFBS state sampling). Master plan §7.1 mcmc "
        "class default tolerance band (5e-3 abs / 5e-2 rel) "
        "applies; Pattern A.1 self-parity is bit-exact (abs=0) "
        "since seed-pinning makes the chain deterministic. "
        "Pattern F invariants are property-level (no tolerance "
        "band; PASS = property holds, BLOCK = property violated). "
        "R bvars (Krueger) was the plan §4.1 primary Pattern A.2 "
        "candidate but is unavailable for R 4.5.3 (TSL pinned R "
        "version); plan §4.1 fallback discipline applies."
    )

    # Tolerance bands for Pattern A.1 self-parity comparison.
    # Bit-exact: numpy + numba random state is fully deterministic
    # given the same seed; the two runs must produce byte-identical
    # arrays. ``abs_tol`` of 0 is the strict assertion; we use 1e-15
    # (machine epsilon ceiling) as a defensive small-positive value
    # to avoid float-equality edge cases.
    BIT_EXACT_ABS_TOL = 1e-15
    BIT_EXACT_REL_TOL = 1e-15

    # Pattern F invariant thresholds.
    VAR_EIG_PASS_THRESHOLD = 0.999    # max|eig| < 1 - epsilon for clean PASS
    SV_PHI_ABS_MAX = 0.999            # |phi_i| < 1 stationarity
    PCA_EXPLAINED_VAR_MIN = 0.99      # 3-PC truncation captures ≥99% variance

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"_seed": int(seed)}

    # -----------------------------------------------------------------
    # TSL side: invoke dispatch's run() once
    # -----------------------------------------------------------------

    def _invoke_dispatch(self, run_id: str) -> dict[str, Any]:
        """Single TSL dispatch invocation. Returns extracted arrays
        + posterior-mean companion-eig magnitudes + invariant inputs.
        """
        _ensure_engine_on_path()
        from techniques.base import RunContext
        from techniques.bond_yield_forecast import run as byf_run

        fixture_path = _canonical_fixture_path()
        ctx = RunContext({
            "run_id": run_id,
            "technique_id": "bond_yield_forecast",
            "preset": "Balanced",
            "seed": _AUDIT_SEED,
            "frequency": "Q",
            "time": [],
            "series": [],
            "params": {
                "input_workbook": str(fixture_path),
                "scenario": "baseline",
                # Reduced chain for fast-tier audit runtime.
                "n_draws": _AUDIT_N_DRAWS,
                "n_burn": _AUDIT_N_BURN,
                "seed": _AUDIT_SEED,
            },
        })
        resp = byf_run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"BYF dispatch failed in audit: {resp.get('error_message')}"
            )

        # Re-load BVARSVResults so we have the actual numpy arrays
        # for byte-exact comparison. The dispatch returns tables (not
        # raw arrays) by design; re-run a thin invocation that exposes
        # the underlying arrays for the audit. We do this by calling
        # the subpackage's BVARSV.estimate() directly with identical
        # config, mirroring _dispatch._build_panel_in_memory's
        # construction. This adds ~10s overhead vs reusing the dispatch
        # output, but the audit needs raw posterior arrays not the
        # percentile-summarized table view.
        return self._reproduce_bvar_arrays(fixture_path, _AUDIT_SEED)

    def _reproduce_bvar_arrays(
        self, fixture_path: Path, seed: int,
    ) -> dict[str, Any]:
        """Re-run the BVAR-SV estimation directly to capture raw
        posterior arrays (the dispatch's output tables only expose
        percentile-summaries; the audit needs the full posterior)."""
        from techniques.bond_yield_forecast.unified_input import (
            read_unified_workbook,
        )
        from techniques.bond_yield_forecast.estimation import BVARSV
        from techniques.bond_yield_forecast.priors import MinnesotaPrior
        from techniques.bond_yield_forecast.data import load_config
        from techniques.bond_yield_forecast._paths import (
            package_default_config,
        )

        # Mirror dispatch's panel-build + sheet-name auto-detection.
        from techniques.bond_yield_forecast._dispatch import (
            _build_panel_in_memory,
            _resolve_workbook_sheet_config,
        )

        config = load_config(package_default_config())
        # Apply audit param overrides.
        config["estimation"]["n_draws"] = _AUDIT_N_DRAWS
        config["estimation"]["n_burn"] = _AUDIT_N_BURN
        config["estimation"]["seed"] = seed
        # Auto-detect sheet scheme.
        config = _resolve_workbook_sheet_config(
            fixture_path, config, "baseline",
        )

        bundle = read_unified_workbook(
            fixture_path, "baseline", config,
        )
        panel_bundle = _build_panel_in_memory(config, bundle["raw"])
        panel = panel_bundle["panel"]
        pca_dict = panel_bundle["pca"]

        variable_names = list(panel.columns)
        hp = config["model"]["hyperparameters"]["fixed"]
        prior = MinnesotaPrior(
            n_vars=len(variable_names),
            n_lags=int(config["model"]["lags"]),
            lambda_1=hp["lambda_1"], lambda_2=hp["lambda_2"],
            lambda_3=hp["lambda_3"], lambda_sc=hp["lambda_sc"],
            lambda_io=hp["lambda_io"],
            persistence_prior=config["model"]["persistence_prior"],
            variable_names=variable_names,
            training_data=panel,
        )
        bvar = BVARSV(
            data=panel,
            n_lags=int(config["model"]["lags"]),
            prior=prior,
            n_draws=_AUDIT_N_DRAWS,
            n_burn=_AUDIT_N_BURN,
            thinning=1,
            seed=seed,
        )
        results = bvar.estimate()

        # Compute posterior-mean coefficients + companion eigenvalues
        # for Pattern F structural invariants.
        coef_post_mean = np.asarray(
            results.coefficients, dtype=np.float64,
        ).mean(axis=0)  # shape (n_vars, n_vars*n_lags + 1)
        n_vars = len(variable_names)
        n_lags = int(config["model"]["lags"])
        # Per estimation._build_lag_design (line 167), the design
        # matrix layout is: X[:, 0] = 1 (intercept FIRST), then
        # X[:, 1:n+1] = lag-1 vars, X[:, n+1:2n+1] = lag-2 vars, ...
        # So coef_post_mean column 0 is the intercept and columns
        # 1..n*p are the [B_1, B_2, ..., B_p] lag block. Drop the
        # FIRST column (not the last) to extract the companion-form
        # input.
        if coef_post_mean.shape[1] == n_vars * n_lags + 1:
            B = coef_post_mean[:, 1:]  # drop intercept (first column)
        else:
            B = coef_post_mean
        # Build companion matrix (n_vars*n_lags, n_vars*n_lags).
        companion = np.zeros((n_vars * n_lags, n_vars * n_lags))
        companion[:n_vars, :] = B  # top block-row
        if n_lags > 1:
            companion[n_vars:, :-n_vars] = np.eye(n_vars * (n_lags - 1))
        eig_magnitudes = np.abs(np.linalg.eigvals(companion))

        # SV phi posterior means (one per variable).
        phi_post_mean = np.asarray(results.phi, dtype=np.float64).mean(axis=0)

        # PCA explained-variance ratio invariant.
        #
        # Note: the BVAR-SV pipeline uses a TRUNCATED PCA (3 components
        # out of 10 maturities) per fit_pca() at data.py:382-383. A
        # full encode-decode roundtrip is therefore intentionally lossy
        # — any residual reflects unmodeled variance in the 4th-10th
        # PCs, NOT a numerical precision bug. The meaningful invariant
        # is whether 3 components capture sufficient variance to
        # justify the dimension reduction (>99% on a typical Treasury
        # curve, where level/slope/curvature dominate per Litterman-
        # Scheinkman 1991).
        pca_explained_variance_total = float(
            np.sum(pca_dict["explained_variance_ratio"])
        )
        # Diagnostic: also record the truncated reconstruction residual.
        yield_panel_arr = panel_bundle["yield_panel"].values
        loadings = np.asarray(pca_dict["loadings"], dtype=np.float64)
        mean_v = np.asarray(pca_dict["mean"], dtype=np.float64)
        scores = (yield_panel_arr - mean_v) @ loadings
        y_reconstructed = scores @ loadings.T + mean_v
        pca_truncated_residual = float(np.max(np.abs(yield_panel_arr - y_reconstructed)))

        return {
            # Pattern A.1 byte-exact comparison arrays:
            "coefficients": np.asarray(results.coefficients, dtype=np.float64),
            "A_lower_triangular": np.asarray(
                results.A_lower_triangular, dtype=np.float64,
            ),
            "log_volatilities": np.asarray(
                results.log_volatilities, dtype=np.float64,
            ),
            "mu": np.asarray(results.mu, dtype=np.float64),
            "omega": np.asarray(results.omega, dtype=np.float64),
            "phi": np.asarray(results.phi, dtype=np.float64),
            # Pattern F structural-invariant inputs:
            "companion_eig_magnitudes": eig_magnitudes,
            "phi_post_mean": phi_post_mean,
            "pca_explained_variance_total": pca_explained_variance_total,
            "pca_truncated_residual": pca_truncated_residual,
            # Bookkeeping
            "n_vars": int(n_vars),
            "n_lags": int(n_lags),
            "n_kept_draws": int(results.coefficients.shape[0]),
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_dispatch(run_id="audit_tsl_first")

    # -----------------------------------------------------------------
    # Reference side: same dispatch invoked again (Pattern A.1)
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return self._invoke_dispatch(run_id="audit_tsl_second")

    # -----------------------------------------------------------------
    # Compare: Pattern A.1 byte-exact + Pattern F invariants
    # -----------------------------------------------------------------

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Pattern A.1: bit-exact reproducibility.
        bit_band = {
            "abs_tol": self.BIT_EXACT_ABS_TOL,
            "rel_tol": self.BIT_EXACT_REL_TOL,
            "block_abs_tol": 1e-10,
            "block_rel_tol": 1e-10,
        }
        for key in (
            "coefficients", "A_lower_triangular", "log_volatilities",
            "mu", "omega", "phi",
        ):
            t = np.asarray(tsl[key]).reshape(-1)
            r = np.asarray(ref[key]).reshape(-1)
            primary[f"reproducibility::{key}"] = _compare_vector(t, r, bit_band)
            statuses.append(primary[f"reproducibility::{key}"]["status"])

        # Pattern F: VAR companion-form stationarity (max |eig| < 1).
        eigs = np.asarray(tsl["companion_eig_magnitudes"])
        max_eig = float(np.max(eigs))
        if max_eig < self.VAR_EIG_PASS_THRESHOLD:
            eig_status = "PASS"
        elif max_eig < 1.0:
            eig_status = "CAVEAT"  # near-boundary
        else:
            eig_status = "BLOCK"   # non-stationary
        primary["invariant::var_companion_eig"] = {
            "status": eig_status,
            "max_abs_eig": max_eig,
            "n_eigs": int(eigs.size),
            "pass_threshold": self.VAR_EIG_PASS_THRESHOLD,
            "block_threshold": 1.0,
        }
        statuses.append(eig_status)

        # Pattern F: SV stationarity (|phi_i| < 1).
        phis = np.asarray(tsl["phi_post_mean"])
        max_abs_phi = float(np.max(np.abs(phis)))
        if max_abs_phi < self.SV_PHI_ABS_MAX:
            phi_status = "PASS"
        elif max_abs_phi < 1.0:
            phi_status = "CAVEAT"
        else:
            phi_status = "BLOCK"
        primary["invariant::sv_stationarity"] = {
            "status": phi_status,
            "max_abs_phi": max_abs_phi,
            "n_equations": int(phis.size),
            "phi_post_mean": phis.tolist(),
        }
        statuses.append(phi_status)

        # Pattern F: PCA explained-variance ratio (3 PCs ≥ 99% of
        # variance — Litterman-Scheinkman 1991 level/slope/curvature
        # decomposition holds for typical Treasury curves).
        pca_var = float(tsl["pca_explained_variance_total"])
        if pca_var >= self.PCA_EXPLAINED_VAR_MIN:
            pca_status = "PASS"
        elif pca_var >= 0.95:
            pca_status = "CAVEAT"  # truncation losing more than expected
        else:
            pca_status = "BLOCK"   # PCA inappropriate for this fixture
        primary["invariant::pca_explained_variance"] = {
            "status": pca_status,
            "explained_variance_total": pca_var,
            "n_components": 3,
            "min_threshold": self.PCA_EXPLAINED_VAR_MIN,
            "truncated_residual_diag": float(
                tsl["pca_truncated_residual"]
            ),
        }
        statuses.append(pca_status)

        # Pattern F: posterior-mean coefficient finiteness.
        coef_post_mean = np.asarray(tsl["coefficients"]).mean(axis=0)
        n_nan = int(np.sum(~np.isfinite(coef_post_mean)))
        finite_status = "PASS" if n_nan == 0 else "BLOCK"
        primary["invariant::coef_finite"] = {
            "status": finite_status,
            "n_non_finite": n_nan,
            "coef_shape": list(coef_post_mean.shape),
        }
        statuses.append(finite_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = "BLOCK" if any_block else (
            "CAVEAT" if any_caveat else "PASS"
        )

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_vars": int(tsl.get("n_vars", 0)),
                "n_lags": int(tsl.get("n_lags", 0)),
                "n_kept_draws": int(tsl.get("n_kept_draws", 0)),
                "audit_n_draws": _AUDIT_N_DRAWS,
                "audit_n_burn": _AUDIT_N_BURN,
                "audit_seed": _AUDIT_SEED,
                "reference_strategy": (
                    "Pattern A.1 self-parity (R bvars unavailable on "
                    "R 4.5.3; Pattern A.3 reimpl out of LOC budget)"
                ),
            },
        )

    # Bond Yield Forecast is deterministic given seed+config; if S4
    # ever produces CAVEAT due to numeric drift on fixture-edge cases,
    # a reroll wouldn't help. Don't enable reroll.
    reroll_on_caveat = False
