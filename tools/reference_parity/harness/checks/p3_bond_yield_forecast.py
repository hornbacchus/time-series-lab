"""Phase 3.5+ parity audit for Bond Yield Forecast.

**Coverage:** TWO canonical fixtures (BYF-Mod-2 extension, 2026-05-01):

  - ``test_input_canonical.xlsx`` — 10-maturity grid (3M, 6M, 1Y, 2Y,
    3Y, 5Y, 7Y, 10Y, 20Y, 30Y); legacy fixture preserved unchanged
    from BYF integration Session 4. Anchors backward-compatibility:
    sparse-column auto-detection (BYF-Mod-1) on this 10-mat input
    must produce the same numerical output as the pre-Mod-1
    fixed-10 implementation.

  - ``test_input_canonical_34mat.xlsx`` — 34-maturity grid (1M, 3M,
    6M, 9M, 1Y, 2Y, 3Y, 4Y, 5Y, 6Y, 7Y, 8Y, 9Y, 10Y, 11Y..30Y);
    pinned at BYF-Mod-2 from the regenerated sample input template
    (24 inserted maturities linearly interpolated in maturity-years
    space; 10 anchor maturities preserved verbatim from the 10-mat
    fixture; per BYF-Mod-1 README addendum). Exercises the full
    declarative grid through PCA + BVAR-SV + conditioning end-to-end.

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
this is materially out-of-budget for a single audit script.

**Selected approach: Pattern A.1 self-parity + Pattern F structural
invariants.** Per Phase 3 precedent (e.g., ``critical_slowing_down``
when ewstools landed before the canonical reference was clear), this
pattern combines:

  1. **Pattern A.1 reproducibility self-parity:** invoke TSL's
     dispatch twice with identical seed; assert byte-identical
     output across all BVARSVResults arrays. Validates the
     deterministic-given-seed contract — necessary precondition
     for any meaningful empirical claim about the wrapper.

  2. **Pattern F structural invariants:** mathematical-property
     checks that hold regardless of implementation:
        a. VAR companion-form max |eigenvalue| < 1 (BVAR
           stationarity).
        b. SV stationarity: |phi_i| < 1 per variable.
        c. PCA explained-variance ratio: 3-PC truncation captures
           >= 99% of yield-curve variance (Litterman-Scheinkman
           1991 level/slope/curvature decomposition).

           BYF-Mod-2 (B-Mod1-2) measurement: 99.91% on 10-mat,
           99.92% on 34-mat — denser maturity grid does NOT
           materially weaken the 3-PC factor structure because
           the 24 inserted maturities (linear interpolation in
           BYF-Mod-1) track the same level/slope/curvature signal
           the 10 anchors already capture. **Threshold preserved
           at 99% for both fixtures** per BYF-Mod-2 §2.5 decision
           tree (>=99% measured -> keep 99% threshold).

        d. Posterior-mean coefficient finite (no NaN / inf).

**Tier:** ``fast`` — uses reduced chain config (n_draws=2000,
n_burn=500). Two BVAR-SV cycles per fixture x 2 fixtures =
four cycles total; ~25-30s wall-clock end-to-end. Fits the
fast-tier ceiling per BYF-Mod-1 §5.2 measurement.

**verdict_class:** ``mcmc`` per master plan §7.1 + plan §4.2.

**Expected verdict:** PASS on both fixtures. Pattern A.1 self-parity
should be byte-identical between two same-seed runs (numpy + numba
both deterministic given pinned seed + cached JIT). Pattern F
invariants should hold by construction on both well-conditioned
fixtures.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.structural_invariants import StructuralInvariant


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


def _repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / "engine").is_dir():
            return parent
    raise RuntimeError("Cannot locate engine/ for fixture")


# BYF-Mod-2: two canonical fixtures, both pinned via
# tools/reference_parity/harness/MANIFEST.toml entries (sha256 also
# recorded in the audit report for documentation).
_FIXTURES = (
    (
        "fixture_10mat",
        "engine/techniques/bond_yield_forecast/tests/fixtures/"
        "test_input_canonical.xlsx",
    ),
    (
        "fixture_34mat",
        "engine/techniques/bond_yield_forecast/tests/fixtures/"
        "test_input_canonical_34mat.xlsx",
    ),
)


# Reduced chain config for fast-tier audit runtime. Two BVAR-SV cycles
# per fixture x 2 fixtures = four cycles total.
#
# mcmc_convergence B' activation: n_draws bumped 2000 -> 3000 so the
# B_* (VAR-coefficient) ESS>=500 gate clears with MARGIN on BOTH fixtures.
# Measured B_* ess_min at 3000: 1089 (34mat) / 1068 (10mat) — ~570-590
# over the 500 floor; at 2000 the 10mat was 498 (sub-floor). ~35-45s
# end-to-end (still within the fast-tier ceiling).
_AUDIT_N_DRAWS = 3000
_AUDIT_N_BURN = 500
_AUDIT_SEED = 20260427  # matches BVAR Session 0 fixture seed


class BondYieldForecastParity(P3ParityCheck):
    """Bond Yield Forecast parity audit (BYF-Mod-2: two-fixture coverage).

    Pattern A.1 reproducibility self-parity + Pattern F structural
    invariants on BOTH the legacy 10-maturity fixture and the BYF-Mod-1
    34-maturity fixture. R ``bvars`` not available for R 4.5.3; full
    Pattern A.3 paper-formula reimpl out of session-LOC budget; this
    audit is the most-honest combination available.
    """

    technique_id = "p3_bond_yield_forecast"
    tier = "fast"  # ~25-30s with two fixtures x reduced chain config
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
        "version); plan §4.1 fallback discipline applies. "
        "BYF-Mod-2 (2026-05-01): coverage extended from one to "
        "two canonical fixtures (10-mat legacy + 34-mat BYF-Mod-1)."
    )

    # Pattern A.1 self-parity tolerance bands (bit-exact).
    BIT_EXACT_ABS_TOL = 1e-15
    BIT_EXACT_REL_TOL = 1e-15

    # Pattern F invariant thresholds (per master plan §3.1).
    #
    # Phase 4 Session 9 (P4-1.3 Category 2 / O-2 tightening,
    # 2026-05-02) — VAR_EIG_PASS_THRESHOLD tightened from 0.999
    # to 0.9995 per master plan Decision 11. The 34-maturity
    # fixture's measured companion eigenvalue is 0.9988, leaving
    # a 7e-4 margin — acceptable per Decision 11. Future fixture
    # drift past 0.9995 will trigger BLOCK; that's the desired
    # early-warning behaviour. The strict-instability threshold
    # (BLOCK at >= 1.0) is preserved per Pattern F semantics
    # (eigenvalue < 1 means stationary VAR; >= 1 means unit-root
    # / explosive — non-negotiable).
    #
    # SV_PHI_ABS_MAX preserved at 0.999 per Phase 1 measurement
    # (S4 audit observed max |phi| = 0.996; 3e-3 margin).
    # PCA_EXPLAINED_VAR_MIN preserved at 0.99 per BYF-Mod-2 §2.5
    # measurement (99.91% on 10-mat; 99.92% on 34-mat).
    VAR_EIG_PASS_THRESHOLD = 0.9995
    SV_PHI_ABS_MAX = 0.999
    PCA_EXPLAINED_VAR_MIN = 0.99

    # mcmc_convergence B' gate threshold: B_* (VAR-coefficient) ESS_min.
    # GATE SCOPE = VAR coefficients ONLY — the forecast-point dynamics that
    # converge robustly at CI scale (measured B_* ess_min 1089/1068 at the
    # bumped audit config). SV params are EXCLUDED from the gate, with a
    # documented three-part rationale (see _compare_one_fixture + §2.5).
    # This is a NARROWED activation of the dormant mcmc_convergence
    # invariant: the full-system SV ESS-200 gate is NOT passable at the
    # fast-tier draw count (the slow NCP-sampled SV `mu` group needs ~30k+
    # draws; at production yield-PC mu[pc2]=198.6 marginal, macro mu 11-56),
    # and band-stability (10k vs 50k: mean width -0.9%, max 3.0%) shows SV
    # `mu` mixing does not compromise the forecast bands.
    MCMC_B_COEF_ESS_MIN = 500.0

    # Declarative mcmc_convergence invariant. enabled=False: the registry
    # omnibus checker (_check_mcmc_convergence) gates on a FLAT GLOBAL
    # ess_min with single-parameter exclusion, which cannot express the
    # B_*-group-scoped gate + whole-SV-group exclusion this check requires
    # (and BYF's run_tsl is multi-fixture, so a flat ess_min field is absent
    # -> the registry path emits INFO anyway). The ACTIVE gate is enforced
    # INLINE in compare()/_compare_one_fixture (B_* ESS >= MCMC_B_COEF_ESS_MIN
    # per fixture, contributing to the outcome). The declaration is retained
    # (disabled) as the registry cross-reference; tolerance records the B_*
    # threshold. Full ess_min/geweke (incl. SV) remain in the production
    # Audit (engine-side) and in this check's diagnostics for disclosure.
    structural_invariants = (
        StructuralInvariant(
            name="mcmc_convergence_var_coef",
            invariant_type="mcmc_convergence",
            tolerance=500.0,  # B_* (VAR-coef) ESS_min PASS threshold
            tolerance_type="absolute",
            enabled=False,
        ),
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"_seed": int(seed)}

    # -----------------------------------------------------------------
    # TSL side: invoke the BVAR estimation directly per fixture
    # -----------------------------------------------------------------

    def _reproduce_bvar_arrays(
        self, fixture_path: Path, seed: int,
    ) -> dict[str, Any]:
        """Re-run the BVAR-SV estimation directly to capture raw
        posterior arrays (the dispatch's output tables only expose
        percentile-summaries; the audit needs the full posterior)."""
        _ensure_engine_on_path()

        from techniques.bond_yield_forecast.unified_input import (
            read_unified_workbook,
        )
        from techniques.bond_yield_forecast.estimation import BVARSV
        from techniques.bond_yield_forecast.priors import MinnesotaPrior
        from techniques.bond_yield_forecast.data import load_config
        from techniques.bond_yield_forecast._paths import (
            package_default_config,
        )
        from techniques.bond_yield_forecast._dispatch import (
            _build_panel_in_memory,
            _resolve_workbook_sheet_config,
        )

        config = load_config(package_default_config())
        config["estimation"]["n_draws"] = _AUDIT_N_DRAWS
        config["estimation"]["n_burn"] = _AUDIT_N_BURN
        config["estimation"]["seed"] = seed
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

        # mcmc_convergence (B' scope): per-group ESS from the BVAR-SV
        # convergence diagnostics. The GATE uses the VAR-coefficient (B_*)
        # ess_min; the full-system min + SV breakdown are returned for
        # DISCLOSURE only (not gated — see _compare_one_fixture).
        _diag = results.convergence_diagnostics()
        _grp = _diag["parameter_group"]
        _b_mask = _grp.str.startswith("B_")
        b_coef_ess_min = float(_diag.loc[_b_mask, "ess"].min())
        b_coef_ess_min_param = str(_diag.loc[_b_mask, "ess"].idxmin())
        global_ess_min = float(_diag["ess"].min())
        global_ess_min_param = str(_diag["ess"].idxmin())
        geweke_max_abs_z = float(_diag["geweke_z"].abs().max())
        _sv_mask = _grp.isin(["omega", "phi", "mu", "h_time_mean"])
        _macro_names = ("real_gdp_growth", "headline_cpi", "fed_funds_rate")
        _is_macro = _diag.index.to_series().apply(
            lambda p: any(m in p for m in _macro_names)
        )
        sv_macro_ess_min = float(
            _diag.loc[_sv_mask & _is_macro, "ess"].min()
        )
        sv_yield_pc_ess_min = float(
            _diag.loc[_sv_mask & ~_is_macro, "ess"].min()
        )

        # Pattern F input: posterior-mean companion eigenvalues.
        coef_post_mean = np.asarray(
            results.coefficients, dtype=np.float64,
        ).mean(axis=0)
        n_vars = len(variable_names)
        n_lags = int(config["model"]["lags"])
        if coef_post_mean.shape[1] == n_vars * n_lags + 1:
            B = coef_post_mean[:, 1:]  # drop intercept (first column)
        else:
            B = coef_post_mean
        companion = np.zeros((n_vars * n_lags, n_vars * n_lags))
        companion[:n_vars, :] = B
        if n_lags > 1:
            companion[n_vars:, :-n_vars] = np.eye(n_vars * (n_lags - 1))
        eig_magnitudes = np.abs(np.linalg.eigvals(companion))

        phi_post_mean = np.asarray(
            results.phi, dtype=np.float64,
        ).mean(axis=0)

        pca_explained_variance_total = float(
            np.sum(pca_dict["explained_variance_ratio"])
        )
        # Diagnostic: truncated reconstruction residual (intentionally
        # nonzero per Litterman-Scheinkman 1991 truncated-PCA).
        yield_panel_arr = panel_bundle["yield_panel"].values
        loadings = np.asarray(pca_dict["loadings"], dtype=np.float64)
        mean_v = np.asarray(pca_dict["mean"], dtype=np.float64)
        scores = (yield_panel_arr - mean_v) @ loadings
        y_reconstructed = scores @ loadings.T + mean_v
        pca_truncated_residual = float(
            np.max(np.abs(yield_panel_arr - y_reconstructed))
        )

        n_maturities = len(pca_dict["yield_names"])

        return {
            # Pattern A.1 byte-exact comparison arrays:
            "coefficients": np.asarray(
                results.coefficients, dtype=np.float64,
            ),
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
            # mcmc_convergence (B' gate input + disclosure):
            "b_coef_ess_min": b_coef_ess_min,
            "b_coef_ess_min_param": b_coef_ess_min_param,
            "global_ess_min": global_ess_min,
            "global_ess_min_param": global_ess_min_param,
            "geweke_max_abs_z": geweke_max_abs_z,
            "sv_macro_ess_min": sv_macro_ess_min,
            "sv_yield_pc_ess_min": sv_yield_pc_ess_min,
            # Bookkeeping
            "n_vars": int(n_vars),
            "n_lags": int(n_lags),
            "n_maturities": int(n_maturities),
            "n_kept_draws": int(results.coefficients.shape[0]),
        }

    def _run_all_fixtures(self, run_tag: str) -> dict[str, Any]:
        """Invoke ``_reproduce_bvar_arrays`` once per fixture; return
        a dict keyed by fixture name."""
        out: dict[str, Any] = {}
        for fixture_name, rel_path in _FIXTURES:
            fpath = _repo_root() / rel_path
            if not fpath.exists():
                raise RuntimeError(
                    f"Audit fixture missing: {fpath} (tag={run_tag})"
                )
            out[fixture_name] = self._reproduce_bvar_arrays(
                fpath, _AUDIT_SEED,
            )
        return out

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return self._run_all_fixtures("tsl_first")

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        return self._run_all_fixtures("tsl_second")

    # -----------------------------------------------------------------
    # Compare: Pattern A.1 byte-exact + Pattern F invariants per fixture
    # -----------------------------------------------------------------

    def _compare_one_fixture(
        self,
        fixture_name: str,
        tsl: dict[str, Any],
        ref: dict[str, Any],
        primary: dict[str, Any],
        statuses: list[str],
    ) -> None:
        """Append per-fixture Pattern A.1 + Pattern F metrics into
        ``primary``, prefixed with the fixture name."""
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
            metric_key = f"{fixture_name}::reproducibility::{key}"
            primary[metric_key] = _compare_vector(t, r, bit_band)
            statuses.append(primary[metric_key]["status"])

        # Pattern F: VAR companion-form stationarity.
        eigs = np.asarray(tsl["companion_eig_magnitudes"])
        max_eig = float(np.max(eigs))
        if max_eig < self.VAR_EIG_PASS_THRESHOLD:
            eig_status = "PASS"
        elif max_eig < 1.0:
            eig_status = "CAVEAT"
        else:
            eig_status = "BLOCK"
        primary[f"{fixture_name}::invariant::var_companion_eig"] = {
            "status": eig_status,
            "max_abs_eig": max_eig,
            "n_eigs": int(eigs.size),
            "pass_threshold": self.VAR_EIG_PASS_THRESHOLD,
            "block_threshold": 1.0,
        }
        statuses.append(eig_status)

        # Pattern F: SV stationarity.
        phis = np.asarray(tsl["phi_post_mean"])
        max_abs_phi = float(np.max(np.abs(phis)))
        if max_abs_phi < self.SV_PHI_ABS_MAX:
            phi_status = "PASS"
        elif max_abs_phi < 1.0:
            phi_status = "CAVEAT"
        else:
            phi_status = "BLOCK"
        primary[f"{fixture_name}::invariant::sv_stationarity"] = {
            "status": phi_status,
            "max_abs_phi": max_abs_phi,
            "n_equations": int(phis.size),
            "phi_post_mean": phis.tolist(),
        }
        statuses.append(phi_status)

        # Pattern F: PCA explained-variance ratio.
        pca_var = float(tsl["pca_explained_variance_total"])
        if pca_var >= self.PCA_EXPLAINED_VAR_MIN:
            pca_status = "PASS"
        elif pca_var >= 0.95:
            pca_status = "CAVEAT"
        else:
            pca_status = "BLOCK"
        primary[f"{fixture_name}::invariant::pca_explained_variance"] = {
            "status": pca_status,
            "explained_variance_total": pca_var,
            "n_components": 3,
            "n_maturities": int(tsl.get("n_maturities", 0)),
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
        primary[f"{fixture_name}::invariant::coef_finite"] = {
            "status": finite_status,
            "n_non_finite": n_nan,
            "coef_shape": list(coef_post_mean.shape),
        }
        statuses.append(finite_status)

        # Pattern F: mcmc_convergence (B' scope) — VAR-coefficient ESS gate.
        # GATE: B_* (VAR-coefficient) ess_min >= MCMC_B_COEF_ESS_MIN (500).
        # SV params are EXCLUDED from the gate, three-part rationale:
        #   (1) the fast-tier audit draw count cannot reach SV ESS-200 — the
        #       slow NCP-sampled SV `mu` group needs ~30k+ draws;
        #   (2) the binder is SV `mu` (unconditional log-vol mean), slow for
        #       ALL equations (at production: yield-PC mu[pc2_slope]=198.6
        #       marginal; macro mu 11-56), not a macro-only effect;
        #   (3) band-stability (10k vs 50k: mean width -0.9%, max 3.0%) shows
        #       SV `mu` mixing does NOT compromise the forecast bands.
        # The full-system ess_min/geweke (incl. SV) are recorded below for
        # DISCLOSURE (scoped gate, complete disclosure — not a masked
        # finding); the production Audit shows them too (engine-side).
        b_ess = float(tsl["b_coef_ess_min"])
        if b_ess >= self.MCMC_B_COEF_ESS_MIN:
            mcmc_status = "PASS"
        elif b_ess >= self.MCMC_B_COEF_ESS_MIN / 2.0:
            mcmc_status = "CAVEAT"
        else:
            mcmc_status = "BLOCK"
        primary[f"{fixture_name}::invariant::mcmc_convergence_var_coef"] = {
            "status": mcmc_status,
            "gate_scope": "VAR coefficients (B_*) only; SV params excluded",
            "b_coef_ess_min": b_ess,
            "b_coef_ess_min_param": tsl.get("b_coef_ess_min_param"),
            "gate_threshold": self.MCMC_B_COEF_ESS_MIN,
            # Disclosure (NOT gated):
            "disclosure_global_ess_min": tsl.get("global_ess_min"),
            "disclosure_global_ess_min_param": tsl.get(
                "global_ess_min_param"
            ),
            "disclosure_geweke_max_abs_z": tsl.get("geweke_max_abs_z"),
            "disclosure_sv_macro_ess_min": tsl.get("sv_macro_ess_min"),
            "disclosure_sv_yield_pc_ess_min": tsl.get("sv_yield_pc_ess_min"),
            "sv_exclusion_rationale": (
                "fast-tier draw count cannot reach SV ESS-200 (slow NCP-mu "
                "needs ~30k+ draws); binder is SV mu (slow for all "
                "equations); band-stability (-0.9% mean / 3.0% max width at "
                "10k-vs-50k) shows SV mu mixing does not compromise the "
                "forecast bands"
            ),
        }
        statuses.append(mcmc_status)

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Iterate the two fixtures in declaration order.
        for fixture_name, _rel_path in _FIXTURES:
            self._compare_one_fixture(
                fixture_name, tsl[fixture_name], ref[fixture_name],
                primary, statuses,
            )

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = "BLOCK" if any_block else (
            "CAVEAT" if any_caveat else "PASS"
        )

        # Aggregate diagnostics from the first-run side (TSL); both
        # runs produce identical diagnostic values at Pattern A.1 PASS.
        diag = {
            "audit_n_draws": _AUDIT_N_DRAWS,
            "audit_n_burn": _AUDIT_N_BURN,
            "audit_seed": _AUDIT_SEED,
            "fixtures_covered": [name for name, _ in _FIXTURES],
            "reference_strategy": (
                "Pattern A.1 self-parity (R bvars unavailable on "
                "R 4.5.3; Pattern A.3 reimpl out of LOC budget). "
                "BYF-Mod-2: extended to two-fixture coverage "
                "(10-mat legacy + 34-mat BYF-Mod-1)."
            ),
        }
        for fixture_name in (n for n, _ in _FIXTURES):
            f = tsl.get(fixture_name, {})
            diag[f"{fixture_name}::n_vars"] = int(f.get("n_vars", 0))
            diag[f"{fixture_name}::n_lags"] = int(f.get("n_lags", 0))
            diag[f"{fixture_name}::n_maturities"] = int(
                f.get("n_maturities", 0)
            )
            diag[f"{fixture_name}::n_kept_draws"] = int(
                f.get("n_kept_draws", 0)
            )

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics=diag,
        )

    # Bond Yield Forecast is deterministic given seed+config; if the
    # audit ever produces CAVEAT due to numeric drift on fixture-edge
    # cases, a reroll wouldn't help. Don't enable reroll.
    reroll_on_caveat = False
