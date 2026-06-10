"""Tolerance ladders for the reference-parity harness.

Each entry in ``TOLERANCE_LADDERS`` is a per-technique
configuration consumed by the corresponding ``ParityCheck``
subclass. Centralising here keeps tolerance review surface
small (a single file to audit) and lets the harness itself
print the ladder when ``--check-environment`` runs.

Three ladder types:

- **absolute**: simple ``abs_tol`` / ``rel_tol`` floor for
  closed-form computations. Outcome PASS iff
  ``max_abs_diff <= abs_tol`` OR ``max_rel_diff <= rel_tol``;
  otherwise BLOCK.
- **three_outcome**: the B6 / B7 ladder. Two thresholds split
  the metric into PASS / CAVEAT / BLOCK bands; CAVEAT triggers
  a single re-roll with seed+1.
- **correlation**: Pearson-correlation-driven (B7-style).
  Two thresholds: ``corr_pass_threshold`` and
  ``corr_block_threshold``. Above pass → PASS; in between →
  CAVEAT; below block → BLOCK.

Each entry MUST include a ``justification`` field tying back
to a Phase 1 audit report under
``tools/reference_parity/reports/`` so future reviewers can
trace where the tolerance came from.
"""

from __future__ import annotations

from typing import Any


# Public mapping consumed by check modules. Keys are the
# ``technique_id`` attribute of the corresponding ParityCheck.
TOLERANCE_LADDERS: dict[str, dict[str, Any]] = {

    "_smoke_test": {
        "type": "absolute",
        "abs_tol": 1e-12,
        "rel_tol": 1e-12,
        "justification": (
            "Smoke test computes mean of 100 standard normals via "
            "R base mean() and numpy mean. Both paths use IEEE 754 "
            "double-precision floating point with identical input; "
            "result should agree to machine precision. 1e-12 leaves "
            "12 orders of magnitude of headroom for any future "
            "subprocess CSV roundtrip noise."
        ),
    },

    # Breakeven Payrolls (Bespoke technique port). CROSS-SOURCE
    # reproduction: the TSL workbook-path output is asserted against
    # the authoritative Breakeven Payrolls repo's reconciled fixture
    # (tests/fixtures/fed_reference_path.csv @ 826d1d0) — analogous to
    # the cross-package R checks, but the reference is the source
    # repo's frozen output. Closed-form deterministic arithmetic.
    "p3_breakeven_payroll": {
        "type": "absolute",
        # TIGHT full quarterly path, MA-stable region (1962Q1+; the
        # 1960Q1-1961Q1 13-month-MA edge is excluded — the template
        # bakes HPLFS from 1960, no anchor falls there).
        "path": {"abs_tol": 5.0, "rel_tol": 1e-5},
        # TIGHT scenario grid (10 rows, breakeven k/mo). Both the port
        # and the source compute it from identical frozen literals (D1)
        # + the same reconciled 2026 anchor, so they agree to ~1e-12.
        "grid": {"abs_tol": 1e-3, "rel_tol": 1e-6},
        # LOOSE round-target anchors (the repo's reconciliation
        # sanity; intentionally generous, reported not gated).
        "anchor_abs_tol": 15000.0,
        "justification": (
            "Cross-source reproduction of the Breakeven Payrolls repo "
            "(826d1d0). The breakeven path is closed-form arithmetic "
            "(population diff-splice + product-rule decomposition + "
            "be = delta_lf*(1-u*) + 5q centered MA) over CBO-quarterly "
            "potential-LFPR/u* and the CNP16OV-bridged population; the "
            "scenario grid is a closed-form migration-surprise identity "
            "over frozen literals. Session-3 standalone MEASURED: the "
            "TSL workbook path reproduces the committed fed_reference_"
            "path.csv to max abs diff 0.19 jobs/mo across all 256 "
            "quarters of the MA-stable region (1962Q1-2026Q4), once the "
            "CNP16OV append segment carries its May-2025 (HPLFS-handoff) "
            "anchor as the diff-splice base; the scenario grid matches "
            "the source sensitivity_grid to ~1e-12 (Brookings-mid/Fed "
            "7.2386, MS-house 50.6638). The 5.0 jobs/mo path floor "
            "leaves ~26x headroom over the measured 0.19 while a real "
            "reader bug (a dropped population month shifts 2025Q1 by "
            "~1,779; a perturbed CBO value shifts the path by hundreds-"
            "to-thousands) BLOCKs decisively — verified by negative "
            "control. The 1e-3 k/mo grid floor catches any frozen-"
            "literal perturbation (which moves the grid by >> 1e-3)."
        ),
    },

    "3e_mint_family": {
        "type": "absolute",
        "abs_tol": 1e-8,
        "rel_tol": 1e-8,
        "lambda_abs_tol": 1e-4,
        "lambda_rel_tol": 1e-4,
        "justification": (
            "MinT reconciliation closed-form algebra: y_tilde = "
            "S (S' W^-1 S)^-1 S' W^-1 y_hat. Phase 1 audit 3e "
            "(reports/3e_mint_audit.md) measured TSL vs R hts "
            "max abs diff 4.66e-15 on mint_shrinkage, 4.44e-15 on "
            "ols and wls_variance. The 1e-8 floor leaves seven "
            "orders of magnitude of headroom for harness-level "
            "subprocess CSV roundtrip noise without sacrificing "
            "regression detection. Schaefer-Strimmer lambda is "
            "reported to 4 decimal places by hts (printed character "
            "vector); 1e-4 is the precision the reference exposes."
        ),
    },

    # Phase 2 Session 2 — 1c BVAR IRF/FEVD parity. Multi-component
    # ladder: per-horizon IRF, FEVD at horizon 10, FEVD row-sum-to-one
    # invariant.
    "1c_bvar_irf_fevd": {
        "type": "absolute",
        "irf_vs_vars": {
            "ladder": "absolute",
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "justification": (
                "Phase 1 audit 1c "
                "(reports/1c_bvar_irf_audit.md): closed-form matrix "
                "algebra given coefficients. R vars::Phi and the "
                "TSL VMA recursion both implement the standard "
                "Vector MA representation Phi_h = sum_{j=1..min(h,p)} "
                "A_j Phi_{h-j}; bitwise-equivalent given identical "
                "inputs. Phase 1 measured max abs diff 4.58e-16 on "
                "the IRF tensor across horizons 0..10. The 1e-8 "
                "floor leaves seven orders of magnitude of headroom "
                "for harness-level subprocess CSV roundtrip noise."
            ),
        },
        "fevd_vs_vars": {
            "ladder": "absolute",
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "justification": (
                "Same closed-form math; FEVD proportions are "
                "normalized contributions from cumulative squared "
                "orthogonalized IRF. Phase 1 audit 1c measured max "
                "abs diff 2.22e-16 on FEVD at horizon 10. 1e-8 floor "
                "for subprocess noise headroom."
            ),
        },
        "fevd_sum_to_one": {
            "ladder": "absolute",
            "abs_tol": 1e-10,
            "justification": (
                "Phase 1 audit 1c: row-sum-to-one is a structural "
                "FEVD invariant (each row of FEVD partitions 100% "
                "of forecast-error variance among shocks). Tighter "
                "than parity tolerance because this is an arithmetic "
                "identity, not a cross-implementation comparison."
            ),
        },
    },

    # Phase 2 Session 2 — 2a Kalman filter / smoother parity. Three-
    # component ladder: filtered states, smoothed states, log-
    # likelihood. Log-likelihood tolerance relaxed because dlmLL
    # uses a different normalization convention than statsmodels /
    # KFAS — the R-side script must add 0.5*T*log(2*pi) back to
    # bridge dlm's "negative log-likelihood without constant" form
    # to the standard log-likelihood. Even after the bridge,
    # accumulated floating-point drift over T=200 steps can leave
    # residual differences in the 1e-7 to 1e-6 band.
    "2a_kalman_filter_smoother": {
        "type": "absolute",
        "filtered_states_vs_dlm": {
            "ladder": "absolute",
            "abs_tol": 1e-5,
            "rel_tol": 1e-5,
            "justification": (
                "Phase 1 audit 2a (reports/2a_kalman_audit.md): "
                "closed-form Kalman recursions. R dlm::dlmFilter "
                "and statsmodels UnobservedComponents both "
                "implement the standard linear-Gaussian Kalman "
                "filter, but their diffuse-prior initialization "
                "conventions differ (dlm uses large-variance "
                "approximation C0=1e7; statsmodels uses Koopman-"
                "Durbin exact diffuse). The transient near t=0 "
                "produces a per-position drift that scales with T "
                "and noise magnitude. Phase 1 fixture (T=100, "
                "Q=0.1, H=1.0) measured max abs diff 2.44e-7 "
                "filtered. Session 2 fixture (T=200, Q=1.0, H=4.0) "
                "measured 3.5e-6 — same order of magnitude, "
                "scaled by ~10x for larger T+noise. The 1e-5 "
                "floor accommodates the empirically observed "
                "drift while still detecting any new methodology "
                "regression an order of magnitude bigger."
            ),
        },
        "smoothed_states_vs_dlm": {
            "ladder": "absolute",
            "abs_tol": 1e-5,
            "rel_tol": 1e-5,
            "justification": (
                "RTS smoother is a closed-form backward pass over "
                "filtered states; inherits the diffuse-init drift. "
                "Phase 1: 2.13e-8. Session 2: 7.8e-7. 1e-5 floor."
            ),
        },
        "log_likelihood_vs_dlm": {
            "ladder": "absolute",
            "abs_tol": 15.0,
            "justification": (
                "Methodology-offset detection (NOT parity). dlm "
                "and statsmodels handle the diffuse-prior log-"
                "likelihood contribution differently; Phase 1 "
                "audit 2a confirmed this as a valid methodology "
                "difference (TSL=-152.82 vs dlm=-69.90 on Phase 1 "
                "T=100 fixture = 82.92 raw offset; -dlmLL - "
                "0.5*T*log(2*pi) bridge reduces residual to ~9). "
                "Session 2 empirical observation: 8.98 absolute "
                "on T=200 fixture. 15.0 threshold = observed + "
                "~70%% headroom; catches gross regressions (sign "
                "flips, missing terms) while accepting the "
                "documented methodology offset. For tight log-"
                "likelihood parity, see ``log_likelihood_vs_kfas``."
            ),
        },
        "log_likelihood_vs_kfas": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "fixture": "phase1",
            "justification": (
                "Phase 1 audit 2a observed TSL vs KFAS log-"
                "likelihood = 3.64e-7 absolute on the exact "
                "fixture (T=100, Q=0.1, H=1.0, seed=42; "
                "TSL=-152.8192579684, KFAS=-152.8192583324). "
                "Asserting on the same fixture (loaded as "
                "``2a_kalman_phase1``) isolates package-drift and "
                "TSL-regression detection from fixture-scaling "
                "artifacts in floating-point accumulation. KFAS "
                "implements the same Koopman-Durbin convention as "
                "TSL/statsmodels, so log-likelihoods should match "
                "at FP-accumulation precision. 1e-6 threshold is "
                "one order of magnitude above the Phase 1 baseline; "
                "principled, not empirical curve-fit."
            ),
        },
        "kalman_gain_ss_vs_dlm": {
            "ladder": "absolute",
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "justification": (
                "Steady-state Kalman gain is the limit of the "
                "Riccati recursion; closed-form once converged. "
                "Diffuse-init transient is invisible at steady "
                "state. Session 2 measured 9.5e-12 abs diff — "
                "well within 1e-8."
            ),
        },
    },

    # Phase 2 Session 3a — 3d Johansen Bartlett/Reimers correction.
    # Multi-component ladder: raw trace stats vs urca + statsmodels
    # triangulation, Bartlett factor pure-arithmetic check,
    # corrected-stat internal consistency.
    "3d_johansen_bartlett": {
        "type": "absolute",
        "trace_stat_raw_vs_urca": {
            "ladder": "absolute",
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "justification": (
                "Phase 1 audit 3d (reports/3d_johansen_audit.md): "
                "closed-form Johansen test statistic from "
                "generalized eigenvalue problem on the same data. "
                "TSL uses statsmodels coint_johansen; R urca::"
                "ca.jo implements the same Johansen 1991 procedure. "
                "Phase 1 evidence: small cross-package divergence "
                "due to different reduced-rank-regression "
                "parametrizations. 1e-8 floor catches gross "
                "regressions while accepting modest cross-package "
                "drift."
            ),
        },
        "trace_stat_raw_vs_statsmodels": {
            "ladder": "absolute",
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "justification": (
                "TSL uses statsmodels coint_johansen internally; "
                "TSL vs statsmodels should agree at machine "
                "precision since they're the same implementation. "
                "1e-10 floor catches any wrapper-introduced "
                "numerical artifacts."
            ),
        },
        "urca_vs_statsmodels_xref": {
            "ladder": "absolute",
            "abs_tol": 50.0,
            "justification": (
                "Cross-reference check: urca and statsmodels both "
                "implement Johansen's procedure but differ in "
                "reduced-rank regression parametrization. Phase 1 "
                "audit 3d documented this as a real cross-package "
                "divergence (TSL=42.67 vs urca=42.95 on r=0; "
                "ratio 1.007 to 1.27 across rank hypotheses; 10-"
                "30%% divergence on small T per Phase 1 'vibes "
                "check'). 50.0 absolute tolerance accommodates the "
                "documented divergence on this fixture (T=100); "
                "catches gross regressions where urca and "
                "statsmodels diverge by orders of magnitude."
            ),
        },
        "bartlett_factor_arithmetic": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": (
                "Phase 1 audit 3d: Reimers correction factor is "
                "pure arithmetic (T - n*p - d) / T. TSL must "
                "produce exactly this value. Note: TSL's audit "
                "field rounds bartlett_factor to 6 decimals (per "
                "johansen_cointegration.py:514), so the floor is "
                "1e-6 — anything tighter would compare to TSL's "
                "rounded value and fail spuriously. The harness "
                "computes the formula independently and checks "
                "TSL's reported value against the formula."
            ),
        },
        "trace_stat_corrected_consistency": {
            "ladder": "absolute",
            "abs_tol": 1e-3,
            "justification": (
                "Phase 1 audit 3d: TSL applies the Reimers factor "
                "consistently (corrected_stat = raw_stat * "
                "bartlett_factor). TSL's audit field rounds "
                "trace_stat_corrected to 4 decimals (per "
                "johansen_cointegration.py:295), so the floor is "
                "1e-3 — comparison is to TSL's rounded value. The "
                "harness recomputes corrected_stat from full-"
                "precision raw_stat and bartlett_factor and "
                "checks TSL's rounded value matches at the "
                "rounding floor."
            ),
        },
    },

    # Phase 2 Session 3a — 3c EVT Ferro-Segers extremal-index parity.
    "3c_evt_ferro_segers": {
        "type": "absolute",
        "theta_garch_vs_extremes": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "rel_tol": 1e-6,
            "justification": (
                "Phase 1 audit 3c (reports/3c_ferro_segers_audit.md): "
                "Ferro-Segers 2003 intervals estimator is closed-"
                "form given inter-exceedance times. R extRemes::"
                "extremalindex(method='intervals') is the canonical "
                "implementation. Phase 1 measured 0.000e+00 abs "
                "diff (bitwise match) on GARCH fixture. Note: "
                "TSL's audit field rounds extremal_index_theta to "
                "6 decimals; harness floor is 1e-6 to match."
            ),
        },
        "theta_iid_vs_extremes": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "rel_tol": 1e-6,
            "justification": (
                "Same closed-form math on iid baseline. Theta "
                "should be near 1.0 (no clustering); TSL/extRemes "
                "should agree at FP precision. Phase 1 measured "
                "0.000e+00 abs diff. 1e-6 floor matches TSL's "
                "audit-field rounding precision."
            ),
        },
        "polynomial_branch_consistency_garch": {
            "ladder": "absolute",
            "abs_tol": 0,
            "justification": (
                "Phase 1 audit 3c flagged formula-branching edge "
                "case: TSL and extRemes must select the same "
                "Ferro-Segers polynomial branch (driven by "
                "max(T_i) <= 2 vs > 2). Branch disagreement is a "
                "structural bug, not a tolerance question — "
                "assert exact match. NOTE: current GARCH fixture "
                "lands on the (T_i-1)(T_i-2) bias-corrected branch; "
                "this assertion does NOT verify branch-decision "
                "rule equivalence on the T_i (raw) branch. Adding "
                "a fixture engineered for the T_i branch (very "
                "dense exceedances) is future work."
            ),
        },
        "polynomial_branch_consistency_iid": {
            "ladder": "absolute",
            "abs_tol": 0,
            "justification": (
                "Same branch-consistency assertion for the iid "
                "fixture. NOTE: current iid fixture also lands on "
                "the (T_i-1)(T_i-2) bias-corrected branch; the "
                "T_i (raw) branch is not exercised by either "
                "current fixture. See garch entry for future "
                "work note."
            ),
        },
    },

    # Phase 2 Session 3b — 3f Transformer attention capture parity.
    # First check using PyTorch native reference (no R subprocess).
    # Bitwise-parity assertion: TSL's _sa_block patch +
    # no-op forward-hook mechanism must produce attention matrices
    # bitwise-identical to a clean nn.MultiheadAttention call on a
    # cloned-weights model. Failure = TSL bug, not tolerance question.
    "3f_transformer_attention": {
        "type": "absolute",
        "attention_weights_per_layer_vs_native_mha": {
            "ladder": "absolute",
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "justification": (
                "Phase 1 audit 3f: TSL's _sa_block patch + no-op "
                "forward-hook mechanism disables PyTorch's "
                "sparsity fast path and threads need_weights=True "
                "through the same nn.MultiheadAttention.forward "
                "call as the native path. Given identical model "
                "weights and identical input, both paths must "
                "produce bitwise-identical attention matrices. "
                "FAILURE MODE: if this assertion fails, TSL's "
                "_sa_block patch mechanism is producing different "
                "outputs than PyTorch native MHA. This is a TSL "
                "production bug in the attention-capture path, "
                "NOT a parity tolerance question. Do not relax — "
                "investigate and fix the patch."
            ),
        },
        "per_layer_attention_consistency": {
            "ladder": "absolute",
            "abs_tol": 1e-12,
            "justification": (
                "Same assertion, applied per-layer for bug "
                "localization. If layer N's attention matrix "
                "differs while other layers match, the bug is in "
                "layer N's _sa_block patch specifically. "
                "Tolerance identical to aggregate metric."
            ),
        },
        "attention_matrix_shape_consistency": {
            "ladder": "absolute",
            "abs_tol": 0,
            "justification": (
                "Both paths must produce attention matrices of "
                "shape (1, n_lags, n_lags) per layer. Shape "
                "mismatch is a structural bug, not a tolerance "
                "question — assert exact shape match."
            ),
        },
    },

    # Phase 2 Session 4 — 2b MCMC SV Gaussian parity. First slow-
    # tier check; three-outcome PASS/CAVEAT/BLOCK with seed+1
    # re-roll. MC error O(1/sqrt(N_eff)) requires 5-10% rel-diff
    # bands rather than machine-precision absolute floors.
    "2b_mcmc_sv_gaussian": {
        "type": "three_outcome",
        "mu_posterior_mean_vs_stochvol": {
            "ladder": "three_outcome",
            "metric": "rel_diff",
            "thresholds": {"PASS": 0.05, "CAVEAT": 0.10},
            "justification": (
                "Phase 1 Stage B locked tolerance: MC error "
                "O(1/sqrt(N_eff)) ~5%% at N=10k draws with "
                "N_eff 500-2000. PASS-with-CAVEAT band 5-10%% "
                "accommodates MC noise; >10%% indicates "
                "methodology divergence requiring "
                "investigation."
            ),
        },
        "phi_posterior_mean_vs_stochvol": {
            "ladder": "three_outcome",
            "metric": "rel_diff",
            "thresholds": {"PASS": 0.10, "CAVEAT": 0.15},
            "justification": (
                "Phase 1 audit 2b observed 6.6%% phi divergence "
                "— within CAVEAT band on Phase 1 fixture. Phi "
                "is more sensitive to MCMC mixing than mu; "
                "widened thresholds accommodate this without "
                "losing regression detection."
            ),
        },
        "h_posterior_pearson_corr_vs_stochvol": {
            "ladder": "correlation",
            "thresholds": {"PASS": 0.95, "CAVEAT": 0.85},
            "justification": (
                "B7 Phase 4.5 protocol: Pearson correlation "
                "between TSL h_post_mean and stochvol $latent "
                "posterior mean. >0.95 PASS; 0.85-0.95 CAVEAT "
                "(re-roll); <0.85 BLOCK. Correlation metric "
                "robust to absolute level shifts from prior "
                "divergence on mu/sigma_eta."
            ),
        },
    },

    # Phase 7+ bond_yield_forecast COMMISSION, Arm 1 — BVAR-SV per-equation
    # SV-layer cross-package vs R stochvol. Same three-outcome disposition as
    # the 2b/2c sv-entries (mu/phi relative bands, h Pearson correlation; sigma
    # record-only). Matched mu prior (priormu=c(mu_OLS_i,1)) makes mu comparable.
    "p3_byf_sv_crosspkg": {
        "type": "three_outcome",
        # GATED metrics: the robust SV-DYNAMICS agreement.
        "h_corr": {"PASS": 0.95, "CAVEAT": 0.85},   # latent log-vol path corr
        "phi": {"PASS": 0.10, "CAVEAT": 0.20},      # persistence (weak-id-tolerant)
        # RECORD-ONLY (disclosed, NOT gated): mu + sigma — see justification.
        "mu": {"PASS": 0.05, "CAVEAT": 0.10},       # reported only
        "justification": (
            "Bond-yield BVAR-SV per-equation SV vs R stochvol::svsample on the "
            "engine's orthogonalized residuals. ★ This is a JOINT BVAR-SV "
            "validated against UNIVARIATE stochvol fit to the posterior-median "
            "orthogonalized residual — a different estimand than the 2b/2c "
            "standalone-univariate sv-entries, so the disposition differs and "
            "is HONESTLY looser. GATED: the latent log-vol PATH Pearson "
            "correlation (PASS 0.95 / CAVEAT 0.85 — the robust SV-dynamics "
            "metric) + phi persistence (PASS 0.10 / CAVEAT 0.20 — weak-id-"
            "tolerant: low-persistence-prior macro vol is weakly identified, "
            "and the strong h-correlation confirms the dynamics agree despite "
            "phi point noise). RECORD-ONLY (measured + disclosed, NOT gated): "
            "mu (unconditional log-vol mean) and sigma (vol-of-vol) — the "
            "engine's mu/sigma are joint-posterior estimands over all (B,A,h) "
            "draws while stochvol fits the FIXED median residual, so these "
            "level/scale params are not apples-to-apples (engine validation.py "
            "documents the same: 'expect mu disagreement to reflect prior/"
            "structural differences, not sampler bugs'). Measured: mu rel "
            "0.32-0.69, sigma rel 0.46-0.72 — disclosed, NOT widened to mask. "
            "Master plan §7.1 mcmc class; honest CAVEAT-tier cross-package."
        ),
    },

    # Phase 7+ bond_yield COMMISSION, Arm 2 — VAR-coefficient conjugate
    # Minnesota machinery, cross-LANGUAGE/cross-METHOD (Route B; R BVAR
    # infeasible). Two deterministic bit-exact arms.
    "p3_byf_coef_crosspkg": {
        "type": "tiered_outputs",
        # CONJUGATE POSTERIOR: engine normal-equations (numpy LAPACK) vs R
        # LAPACK augmented pseudo-observation OLS (QR). Two numerical routes
        # to the same closed-form posterior; bit-exact modulo the diffuse-
        # intercept conditioning (V_inv has a tiny intercept-precision entry,
        # large condition number) + CSV roundtrip.
        "posterior": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-3, "block_rel_tol": 1e-2,
        },
        # PRIOR vs documented Litterman/Sims-Zha formula (own λ1/l^λ3; cross
        # λ1·λ2·σ_i/(l^λ3·σ_j); intercept (λ4·σ)²) — both closed-form, bit-exact.
        "prior": {
            "abs_tol": 1e-9, "rel_tol": 1e-9,
            "block_abs_tol": 1e-6, "block_rel_tol": 1e-6,
        },
        "justification": (
            "Homoskedastic conjugate Minnesota posterior is closed-form. "
            "Route B (R BVAR infeasible — hierarchical MH cannot pin to the "
            "engine's fixed flat conjugate; R bvars unavailable): the conjugate "
            "posterior is validated CROSS-LANGUAGE/CROSS-METHOD — engine "
            "normal-equations (numpy LAPACK) vs R LAPACK augmented pseudo-"
            "observation OLS (QR) — bit-exact (abs 1e-6 cushions the diffuse-"
            "intercept conditioning + CSV roundtrip); the prior moments are "
            "validated against the documented Litterman/Sims-Zha formula "
            "(bit-exact, both closed-form). NOT a different-package validation; "
            "labelled cross-language/cross-method honestly. Master plan §7.1 "
            "closed_form class."
        ),
    },

    # Phase 7+ bond_yield COMMISSION, Arm 3 — emitted yield paths. NO
    # independent reference exists (R bvars unavailable; standalone repo
    # same-lineage/retired) -> verified defining invariant + honest disclosure.
    "p3_byf_paths": {
        "type": "tiered_outputs",
        # Load-bearing: strict-mode conditioning pins the conditioned macros
        # EXACTLY (macro_t = projection_t.copy()).
        "conditioning_strict": {"abs_tol": 1e-10},
        # In-harness negative control: soft mode must diverge well above the
        # strict pin (macros scatter with proj_unc std 0.5).
        "conditioning_soft_control": {"min_divergence": 1e-3},
        # PCA reconstruction identity yield_paths == pc_paths@loadings.T+mean.
        "pca_reconstruction": {"abs_tol": 1e-10},
        "justification": (
            "Emitted yield paths have NO independent cross-package/cross-source "
            "reference. Verified defining invariant: strict conditioning pins "
            "the conditioned macros < 1e-10 (machine precision; deterministic "
            "macro_t = projection_t.copy()); the soft-mode negative control "
            "(unpinned, proj_unc 0.5) must diverge > 1e-3 in-harness -> the "
            "invariant is verified-discriminating. PCA reconstruction is a "
            "deterministic identity (< 1e-10). The third-case pattern on a "
            "sub-surface with no reference; NOT cross-package. Master plan §7.1."
        ),
    },

    # Inert-control fix #5 — conformal_intervals coverage discrimination (a
    # clean same-quantity alias of confidence_level: the nominal interval
    # LEVEL, not the miscoverage alpha; both default 0.95). Directional +
    # saturation-tolerant: width 1.770/2.549/2.585 for coverage 0.90/0.95/0.99
    # -> strict lower step 0.78, plateau-prone top step 0.036, hard spread 0.816.
    "p3_conformal_coverage": {
        "type": "tiered_outputs",
        "default": {"abs_tol": 1e-9},               # resolved cl == passed; default == c95
        "discrimination": {"min_lower_step": 0.20,  # w(0.95)-w(0.90); measured 0.78
                           "min_spread": 0.20},     # w(0.99)-w(0.90); measured 0.816
        "justification": (
            "Split-conformal width is the deterministic empirical quantile of "
            "calibration residuals at ceil((n_cal+1)(1-alpha))/n_cal given the "
            "seeded base forecaster. coverage -> confidence_level is a clean "
            "same-quantity alias (the LEVEL; alpha = 1 - level stays internal). "
            "DIRECTIONAL: higher coverage -> wider; strict lower step (catches a "
            "complement-backwards wiring) + non-strict top step (tolerates only "
            "the finite-calibration quantile plateau at high levels) + a hard "
            "0.90<->0.99 spread (catches an inert engine). Default (0.95 == "
            "native) byte-identical; sentinels = p3_conformal + p3_conformal_cqr "
            "+ p3_conformal_enbpi. Master plan §7.1."
        ),
    },

    # Inert-control fix #4 — adf_test max_lags discrimination (type-mismatch:
    # the string "auto" branched as a sentinel for auto-select; an int = a fixed
    # maxlag cap). On a lag-4 DGP the cap BINDS the AIC selection: cap=1 -> lag
    # 1, ADF -12.504 vs auto's lag 3 -5.156 -> gap 7.35. "auto" reproduces the
    # no-param run byte-identical (sentinels = p3_adf + p3_adf_triage).
    "p3_adf_maxlags": {
        "type": "tiered_outputs",
        "default": {"abs_tol": 1e-9},            # "auto" == no-param run (sentinel)
        "discrimination": {"min_stat_gap": 1.0},  # |ADF(cap1) - ADF(auto)|; measured 7.35
        "justification": (
            "The ADF statistic is the deterministic statsmodels adfuller output "
            "given (maxlag, autolag, regression). max_lags is now engine-wired -> "
            "max_lag with the string 'auto' branched as a SENTINEL for auto-lag "
            "selection (reproduces the no-param run byte-identical -- sentinels "
            "p3_adf + p3_adf_triage); an int sets a fixed maxlag cap that, when it "
            "binds the AIC selection (lag-4 DGP), changes the selected lag + ADF "
            "statistic by a wide margin (cap1 -> lag1, |gap| 7.35). Master plan "
            "§7.1 closed_form."
        ),
    },

    # Inert-control fix #3 — caviar quantile + model_type discrimination
    # (engine-wired -> theta + specification via a value-map). quantile is
    # DIRECTIONAL (higher q -> less-extreme 1-step VaR, monotone; measured
    # -1.814/-1.347/-1.066 for q 0.01/0.05/0.10 -> gap 0.748). model_type is
    # PER-VALUE (each catalog value -> its engine spec SAV/AS/IG; VaR spread
    # ~0.094 across specs). The default (q=0.05, model_type=symmetric_abs)
    # reproduces theta 0.05 / spec SAV byte-identical (sentinel = 3a_caviar_sav).
    "p3_caviar_controls": {
        "type": "tiered_outputs",
        "default": {"abs_tol": 1e-9},            # resolved theta == passed value (sentinel)
        "discrimination": {"min_var_gap": 0.20,  # v(0.10)-v(0.01); measured 0.748
                           "min_spec_gap": 0.02},  # SAV/AS/IG VaR spread; measured 0.094
        "justification": (
            "CAViaR fit is a seeded stochastic-restart quantile-loss minimization; "
            "the 1-step VaR is the deterministic recursion on the fitted params. "
            "quantile -> theta is DIRECTIONAL (higher quantile -> less-extreme VaR, "
            "monotone) and model_type -> specification is a PER-VALUE value-map "
            "(symmetric_abs->SAV, asymmetric_slope->AS, igarch->IG, each validated). "
            "The default reproduces theta 0.05 / spec SAV byte-identical (sentinel = "
            "3a_caviar_sav). Master plan §7.1 closed_form (directional + categorical "
            "discrimination, robust to optimizer noise)."
        ),
    },

    # Inert-control fix #2 — bvar lambda_shrinkage discrimination (engine-wired
    # -> lambda1, the Minnesota overall tightness). Directional: tighter -> more
    # shrinkage of own-lag-1 toward the RW prior (1.0). Measured own-lag-1
    # 0.993/0.868/0.423 for lambda 0.02/0.1/0.8 -> spread 0.571.
    "p3_bvar_shrinkage": {
        "type": "tiered_outputs",
        "default": {"abs_tol": 1e-9},          # default lambda1 == cfg 0.1 (sentinel)
        "discrimination": {"min_spread": 0.10},  # tight-loose own-lag spread (measured 0.571)
        "justification": (
            "BVAR coefficient posterior mean is the closed-form conjugate "
            "Minnesota-NIW GLS solve (deterministic given the hyperparameters). "
            "lambda_shrinkage is now engine-wired -> lambda1; the default "
            "(lambda_shrinkage=0.1 == cfg) reproduces the prior posterior "
            "byte-identical (sentinel = 1c_bvar_irf_fevd). DIRECTIONAL "
            "discrimination: tighter lambda_shrinkage shrinks own-lag-1 TOWARD "
            "the RW prior mean 1.0 -> monotone tight>default>loose, spread >=0.10 "
            "(measured 0.571). The right thing, not just something. Master plan "
            "§7.1 closed_form."
        ),
    },

    # Inert-control fix #1 — forecast_combination models + combination_method
    # discrimination (engine-wired controls now LIVE). Measured: combination_method
    # moves the primary vector 0.47 (vs OLS), models-subset moves the combined
    # 0.027. The control must MOVE the headline forecast vector (not just a label).
    "p3_forecast_combination_controls": {
        "type": "tiered_outputs",
        "discrimination": {
            "match_tol": 1e-6,        # primary == the selected scheme's column (exact)
            "method_min_move": 1e-2,  # combination_method moves the primary vector (>=0.01; measured 0.47)
            "models_min_move": 1e-3,  # models-subset moves the combined forecast (>=0.001; measured 0.027)
        },
        "justification": (
            "Engine-wiring fix: models + combination_method are now LIVE. The "
            "default reproduces the prior inverse-MSE-primary all-3-models "
            "behavior byte-identical (sentinel = p3_forecast_combination). "
            "Discrimination: combination_method moves the PRIMARY FORECAST VECTOR "
            "(>=0.01; measured 0.47 vs OLS) — not just a label (the subtler-inert "
            "trap); models-subset (drop ETS) moves the combined (>=0.001; measured "
            "0.027). match_tol confirms the primary == the selected scheme's column. "
            "Master plan §7.1 closed_form."
        ),
    },

    # Satellite-ledger fix — VAR max_lag regression guard (catalog key fix
    # max_lags->max_lag). Guards the ENGINE honors max_lag (param affects VAR
    # order); NOT the catalog-fix validation (ribbon->engine = Matt-Excel).
    "p3_var_max_lag": {
        "type": "tiered_outputs",
        "discrimination": {"min_order_cap8": 2},
        "justification": (
            "VAR order selection is deterministic IC-argmin over OLS fits up to "
            "max_lag. On a VAR(1,3) DGP: cap=1 forces order 1; cap=8 lets IC "
            "select >=2 (measured 3). The load-bearing guard is the "
            "discrimination — the two caps give DIFFERENT orders; if the engine "
            "dropped max_lag (the catalog-bug shape) both would collapse to the "
            "same default order. Regression guard on the already-correct engine "
            "read, NOT the catalog-fix validation. Master plan §7.1 closed_form."
        ),
    },

    # Phase 7+ engine-improvement #3 — VECM half_life_periods guard (S65).
    # Valid-range half-life vs the documented formula -ln(2)/ln(1+alpha[0,0])
    # at the engine's own fitted alpha -> bit-exact (same closed form). The
    # over-correcting negative control is a None/nan boolean assertion (no band).
    "p3_vecm_half_life": {
        "type": "tiered_outputs",
        "formula": {"abs_tol": 1e-6, "rel_tol": 1e-4},
        "justification": (
            "VECM adjustment half-life -ln(2)/ln(1+alpha[0,0]) (defined on "
            "(-1,0)). S65 guard fix discrimination: valid-range half-life "
            "matches the documented formula at the fitted alpha, at the 2-dp "
            "emitted precision (B8 floor; abs 1e-6 after rounding both); the "
            "over-correcting range (alpha[0,0] in (-2,-1)) must return None (the "
            "undefined-flag) where the old loose guard silently leaked nan. "
            "Verified-discriminating negative control."
        ),
    },

    # Phase 7+ — var/vecm engine-invocation cross-package upgrades. Engine
    # output is 6-dp rounded (B8 floor); the reference is rounded to match.
    "p3_var_crosspkg": {
        "type": "tiered_outputs",
        # Engine-invoked VAR coefs/intercept/forecast vs R vars::VAR. Both
        # exact OLS -> agree at machine precision pre-rounding; 6-dp rounding
        # gives ~1e-6 residual. Wrapper-validated (modest tier).
        "primary": {"abs_tol": 5e-6, "rel_tol": 1e-4,
                    "block_abs_tol": 1e-3, "block_rel_tol": 1e-2},
        "justification": (
            "VAR(p) is closed-form OLS; engine (statsmodels wrapper) vs R "
            "vars::VAR. ENGINE-INVOKED to validate the wrapper plumbing "
            "(lag/trend/extraction); the estimator agreement is structural. "
            "6-dp engine rounding -> abs 5e-6. Cross-package OLS, engine-"
            "wrapper-validated (modest). Master plan §7.1 closed_form."
        ),
    },

    # Phase 7+ — vecm engine-invocation cross-package (genuine: independent
    # Johansen, rank + Phillips-normalized beta/alpha). Band set after measuring.
    "p3_vecm_crosspkg": {
        "type": "tiered_outputs",
        # Measured: beta 9.99e-16, alpha 2.78e-13 (independent Johansen,
        # machine-precision agreement). Band tightened to the measured
        # precision (honest; a loose band would understate the evidence + miss
        # regressions), with margin for cross-platform R variation.
        "primary": {"abs_tol": 1e-9, "rel_tol": 1e-6,
                    "block_abs_tol": 1e-7, "block_rel_tol": 1e-5},
        "justification": (
            "VECM Johansen is a generalized-eigenvalue / reduced-rank problem; "
            "statsmodels VECM (engine) vs R urca::ca.jo are INDEPENDENT "
            "implementations -> genuine cross-package (non-tautological). Rank "
            "exact-match; beta/alpha at first-element normalization + alpha "
            "sign-align. MEASURED machine-precision (beta 9.99e-16, alpha "
            "2.78e-13); band set to that precision with cross-platform margin. "
            "Master plan §7.1 single_impl_mle."
        ),
    },

    # Phase 7+ — fft_spectrum record-correction: engine FFT dominant frequency
    # vs the analytic truth of a known multi-tone (external authority), with a
    # white-noise negative control. Replaces the same-backend scipy-vs-numpy.
    "p3_fft_analytic": {
        "type": "tiered_outputs",
        # dominant_frequency == the dominant tone's exact DFT bin.
        "dominant_freq": {"abs_tol": 1e-6},
        # tone present in the peak table within ~1 frequency-resolution bin.
        "tone_match": {"tol": 3.0 / 512.0},
        # discrimination: the tone concentrates power (>=50%); white noise does
        # NOT (<=15%). Measured: tone 79.91% vs noise 1.99%.
        "discrimination": {"tone_min_pct": 50.0, "noise_max_pct": 15.0},
        "justification": (
            "FFT of a known multi-tone signal has an analytic spectrum: the "
            "dominant frequency is the larger-amplitude tone's bin exactly "
            "(abs 1e-6). Both known tones must appear in the peak table within "
            "~1 frequency-resolution bin. The white-noise negative control "
            "discriminates: a pure tone concentrates >=50% of power in its top "
            "peak (measured 79.91%), white noise <=15% (measured 1.99%). "
            "External-authority closed-form-of-known-process; engine-invoked. "
            "NOT same-backend FFT-vs-FFT. Master plan §7.1 closed_form."
        ),
    },

    # Phase 2 Session 4 — 2c Student-t SV parity. Same as 2b
    # plus nu (degrees of freedom) parity.
    "2c_mcmc_sv_student_t": {
        "type": "three_outcome",
        "mu_posterior_mean_vs_stochvol": {
            "ladder": "three_outcome",
            "metric": "rel_diff",
            "thresholds": {"PASS": 0.05, "CAVEAT": 0.10},
            "justification": (
                "Same MC-noise rationale as 2b. nu estimation "
                "in Student-t SV does not change mu-posterior "
                "noise floor; thresholds identical."
            ),
        },
        "phi_posterior_mean_vs_stochvol": {
            "ladder": "three_outcome",
            "metric": "rel_diff",
            "thresholds": {"PASS": 0.10, "CAVEAT": 0.15},
            "justification": (
                "Same as 2b. Phi-posterior mixing properties "
                "carry over from Gaussian to Student-t SV."
            ),
        },
        "h_posterior_pearson_corr_vs_stochvol": {
            "ladder": "correlation",
            "thresholds": {"PASS": 0.95, "CAVEAT": 0.85},
            "justification": (
                "Same B7 Phase 4.5 protocol as 2b. Student-t "
                "innovations don't change the latent-h "
                "comparison strategy."
            ),
        },
        "nu_posterior_mean_vs_stochvol": {
            "ladder": "three_outcome",
            "metric": "rel_diff",
            "thresholds": {"PASS": 0.10, "CAVEAT": 0.20},
            "justification": (
                "Phase 1 audit 2c classified nu divergence as "
                "methodology, NOT bug — driven by prior mismatch "
                "between TSL (TruncatedNormal(10, 10, [2.01, 200])) "
                "and stochvol (Exponential rate priornu=0.1, "
                "truncated at 2). These produce materially different "
                "posteriors on nu under identical data. Phase 1 "
                "baseline rel_diff was 13.24%; Session 4 first run "
                "measured 16.44% (within MCMC sampling variation of "
                "Phase 1 baseline). Threshold widened from the 5%/10% "
                "mu/phi convention to 10%/20% to accommodate this "
                "documented prior divergence while preserving "
                "regression detection: substantial drift beyond ~20% "
                "would indicate either a TSL nu sampling regression "
                "or a stochvol environment shift requiring "
                "investigation. ESS_min on nu typically 15-50 in "
                "this configuration (nu posteriors are inherently "
                "noisy at T=500); tighter tolerance is statistically "
                "meaningless given that ESS floor."
            ),
        },
    },

    # Phase 2 Session 5 — 3a CAViaR-SAV parity vs from-scratch
    # Engle-Manganelli 2004 reimplementation. Three-tier
    # comparison per Phase 1 audit B9 finding (Nelder-Mead non-
    # uniqueness on the non-smooth quantile loss): tier 1 strict
    # on recursion math given fixed beta, tier 2 lenient three-
    # outcome on optimum-quality (loss ratio), tier 3 record-only
    # diagnostic on converged beta.
    "3a_caviar_sav": {
        "type": "absolute",
        "q_path_given_fixed_beta_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-10,
            "justification": (
                "Phase 1 audit B9: Nelder-Mead local-optimum "
                "non-uniqueness on CAViaR objective. The recursion "
                "math given fixed beta is bitwise identical "
                "between TSL and reimpl. This metric isolates the "
                "recursion: pass TSL's converged beta to BOTH "
                "TSL's recursion path AND the reimpl's recursion; "
                "compare element-wise q-path. Machine precision "
                "expected; BLOCK on divergence (would indicate "
                "real bug in one of the two implementations of "
                "the same recursion). Phase 1 observed 0.0 max "
                "abs diff on this metric. NOTE: TSL does not "
                "expose the q-path directly in audit_fields; the "
                "harness reconstructs 'TSL q-path' inline using "
                "TSL's converged beta against the SAV recursion "
                "form, then compares to the reimpl recursion. This "
                "is therefore a recursion-correctness defensive "
                "check (both arms compute the same closed-form), "
                "and the supplementary "
                "``one_step_ahead_var_vs_reimpl`` metric provides "
                "the non-tautological TSL-output comparison."
            ),
        },
        "loss_ratio_tsl_to_reimpl": {
            "ladder": "three_outcome",
            "metric": "ratio",
            "thresholds": {"PASS": 1.05, "CAVEAT": 1.10},
            "justification": (
                "Phase 1 audit B9: TSL and reimpl converge to "
                "similar-quality but distinct local optima "
                "(Phase 1: TSL loss 0.040479 vs reimpl 0.041073, "
                "ratio 1.0147). Loss-ratio captures whether both "
                "implementations find similar-quality optima "
                "despite different beta values. Beta divergence "
                "is documented diagnostic, not asserted. Note: "
                "TSL rounds quantile_loss to 6 decimals (B8); "
                "ratio metric is robust to this floor since "
                "denominator scale is ~0.04 and rounding "
                "perturbation is ~2.5e-5 in ratio terms — well "
                "below the 5%% PASS band."
            ),
        },
    },

    # Phase 2 Session 5 — 3b HAR-CJ parity vs from-scratch
    # Andersen-Bollerslev-Diebold 2007 + Huang-Tauchen 2005
    # reimplementation. OLS is closed-form deterministic given
    # identical design matrix; both implementations should match
    # modulo Phase 1 audit B8 6-decimal rounding floor on TSL's
    # output table coefficients.
    "3b_har_cj": {
        "type": "absolute",
        "beta_intercept_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": (
                "Phase 1 audit B8: TSL rounds 'Estimate' column "
                "of the HAR-CJ Coefficients output table to 6 "
                "decimals. Cannot assert tighter than 1e-6 "
                "absolute. OLS is closed-form deterministic given "
                "identical design matrix; both implementations "
                "should match exactly modulo the rounding floor."
            ),
        },
        "beta_rv_daily_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "beta_rv_weekly_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "beta_rv_monthly_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "beta_j_daily_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "beta_j_weekly_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "beta_j_monthly_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": "Same B8 rounding floor as intercept.",
        },
        "r_squared_abs_diff": {
            "ladder": "absolute",
            "abs_tol": 1e-6,
            "justification": (
                "Same B8 rounding floor on R^2 audit field "
                "(``R2`` rounded to 6 decimals in audit_fields)."
            ),
        },
        "jump_count_match": {
            "ladder": "absolute",
            "abs_tol": 0,
            "justification": (
                "BNS jump-detection test deterministic given "
                "identical RV/BV/threshold. Counts must match "
                "exactly — divergence indicates a bug in one of "
                "the two BNS implementations, not a tolerance "
                "question."
            ),
        },
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 1 — R `forecast` family.
    # Tolerance class per master plan §7.1: "MLE-fit (deterministic
    # optimizer)" → abs_tol=1e-3, rel_tol=1e-2 on Primary outputs;
    # 5–10× looser on Secondary (master plan §7.2). Shared `primary` /
    # `secondary` sub-key shape across the three Batch 1 / Session 2
    # checks (p3_arima_manual, p3_sarima, p3_arimax_sarimax) — Session
    # 5 generator abstraction will factor this into a "MLE_FIT_BAND"
    # constant.
    # ------------------------------------------------------------------

    "p3_arima_manual": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Master plan §7.1 MLE-fit deterministic-optimizer band. "
            "Primary outputs (AR/MA coefs, log-likelihood, h-step "
            "forecast) compared at abs_tol=1e-3 / rel_tol=1e-2. "
            "Secondary (sigma2, AIC, BIC) at 10x looser per §7.2. "
            "statsmodels (L-BFGS-B-derived MLE) and R forecast::Arima "
            "(method='ML', BFGS) both optimize the same Gaussian "
            "innovation likelihood; the tolerance band accommodates "
            "the optimizer-convergence-criterion difference (each "
            "stops when its own gradient norm or function-value "
            "delta falls below an internal threshold). Session 2 "
            "manual-pattern lock: this ladder is the template for "
            "the rest of Batch 1 MLE-class wrappers."
        ),
    },

    "p3_sarima": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Same band as p3_arima_manual. SARIMA adds seasonal "
            "factors but uses the same Kalman-filter-on-state-space "
            "MLE backbone (statsmodels SARIMAX vs R forecast::Arima "
            "with seasonal arg). Master plan §7.1 MLE-fit class."
        ),
    },

    "p3_arimax_sarimax": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Same band as p3_arima_manual. ARIMAX/SARIMAX adds "
            "exogenous regressors but uses the same MLE backbone "
            "(statsmodels SARIMAX with exog vs R forecast::Arima "
            "with xreg). Master plan §7.1 MLE-fit class."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 7+ S73 — auto_arima (pmdarima vs R forecast::auto.arima).
    # NEW harness (Disposition B; net-new harness construction, not the
    # read+verify pattern of S68-S72). Two parity layers: (1) order-
    # selection-algorithm cross-implementation (Hyndman-Khandakar 2008
    # stepwise; pmdarima vs R auto.arima); (2) SARIMAX-fit-at-selected-
    # order (same backbone validated at S62/S70/S71/S72). When both arms
    # select the SAME order (path a), primary metrics (coefs + loglik +
    # forecast) compare at the §7.1 MLE-fit band identical to
    # p3_arima_manual. When orders DIFFER (path b), coef-by-coef is
    # meaningless (different models); forecast-only comparison applies
    # at a widened band absorbing model-selection-driven divergence.
    # Same numeric band as p3_arima_manual; the path determination is
    # made in the harness at runtime, not by separate ladders.
    # ------------------------------------------------------------------
    "p3_auto_arima": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Phase 7+ S73 auto_arima. Same §7.1 MLE-fit band as "
            "p3_arima_manual for the SARIMAX-fit-at-selected-order "
            "layer (pmdarima fits the selected order via statsmodels "
            "SARIMAX; R forecast::auto.arima fits via stats::arima — "
            "same Gaussian-innovation MLE). The order-selection-"
            "algorithm layer (Hyndman-Khandakar 2008 stepwise) is "
            "validated by selected-order AGREEMENT (path a) when "
            "pmdarima + R auto.arima converge to the same order; if "
            "orders DIFFER (path b), forecast-only parity at the same "
            "band characterizes model-selection-driven divergence. "
            "Cross-reference S62 conformal_intervals SARIMAX backbone "
            "for the fit layer; the order-selection-cross-implementation "
            "layer is novel to S73."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Session 3 — additional Batch 1 entries.
    # ETS / TBATS use the §7.1 MLE-fit band (deterministic optimizer);
    # Theta is closed-form post-deseasonalization; intermittent demand
    # is closed-form Croston/SBA/TSB exponential-smoothing recursion.
    # ------------------------------------------------------------------

    "p3_ets": {
        "type": "tiered_outputs",
        "primary": {
            # B1 migration (Q2): the engine now uses STATE-SPACE
            # ETSModel (likelihood MLE), same paradigm as R
            # forecast::ets — so this is now a state-space-vs-state-space
            # comparison. The well-identified parameters tightened
            # markedly (beta abs ~2.7e-5, gamma abs ~4.8e-5, forecast
            # rel ~0.089%), hence abs_tol tightened 5e-2 -> 2e-2. The
            # band is NOT tightened further because the LEVEL smoothing
            # parameter alpha is WEAKLY IDENTIFIED (flat likelihood
            # ridge — statsmodels reports an identical log-likelihood at
            # its own alpha=0.344 and at R's alpha=0.450; the level
            # smoothing trades off against the estimated initial level).
            # alpha lands at abs ~0.107 / rel ~0.24 and is RETAINED at
            # CAVEAT (block band) — honestly documented as weak
            # identification, NOT widened to PASS (S84 STAR
            # weakly-identified-gamma precedent: triage like cases
            # alike; tolerances report the measurement, not the
            # explanation).
            "abs_tol": 2e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 2e-1,
            "block_rel_tol": 5e-1,
        },
        "secondary": {
            "abs_tol": 5.0,
            "rel_tol": 5e-2,
            "block_abs_tol": 50.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Master plan §7.1 MLE-fit band. POST-B1-MIGRATION: both "
            "arms are now state-space ETS (engine ETSModel vs R "
            "forecast::ets) — the prior cross-API-paradigm divergence "
            "(classical SSE vs state-space likelihood) is gone; the "
            "well-identified params (beta/gamma/forecast) tightened to "
            "the 1e-5 / sub-0.1%-rel range (abs_tol 2e-2). The level "
            "smoothing alpha is WEAKLY IDENTIFIED (flat likelihood "
            "ridge; identical statsmodels llf at its alpha 0.344 and "
            "R's 0.450) -> retained at CAVEAT (block band rel 5e-1), "
            "documented as intrinsic weak identification, NOT widened "
            "to mask (S84 precedent). SECONDARY aic/bic: the engine is "
            "now likelihood-based, but statsmodels-ETS vs R-ets use "
            "different likelihood-NORMALIZATION constants -> a residual "
            "~505-abs gap remains (NARROWED from the classical ~1070 "
            "gap, ~53%). This is a Tier V Pattern D documented-"
            "divergence (likelihood-normalization, within-paradigm) — "
            "Secondary tier, NON-BLOCKING; argmin-preserving for model "
            "selection. The aic/bic absolute values are NOT cross-"
            "referenceable against R without accounting for the "
            "normalization constant."
        ),
    },

    "p3_theta": {
        "type": "tiered_outputs",
        "primary": {
            # R `forecast::thetaf` uses Assimakopoulos-Nikolopoulos
            # 2000 algorithm; statsmodels `ThetaModel` uses Hyndman-
            # Billah 2003 state-space reformulation. Forecasts
            # converge for theta=2 in the limit but small-sample
            # deviations are documented in the literature.
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 2e-1,
        },
        "secondary": {
            "abs_tol": 1e-1,
            "rel_tol": 1e-1,
            "block_abs_tol": 1.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Theta has a documented methodology divergence between "
            "R `forecast::thetaf` (Assimakopoulos-Nikolopoulos 2000 "
            "original) and statsmodels `ThetaModel` (Hyndman-Billah "
            "2003 state-space reformulation). Hyndman-Billah show "
            "the two are equivalent for theta=2 SES applied to "
            "differenced series, but small-sample deviations exist. "
            "Tolerance band widened to 1e-2 abs / 5e-2 rel on "
            "forecasts to accommodate. CAVEAT/DOCUMENTED-DIVERGENCE "
            "expected on some seeds. Master plan §7.1."
        ),
    },

    "p3_intermittent": {
        "type": "tiered_outputs",
        "primary": {
            # Croston's method is closed-form exponential smoothing
            # recursion; given identical alpha and identical
            # initialization, TSL and R should agree at machine
            # precision. The forecast::croston function uses simple
            # exponential smoothing with default alpha=0.1; TSL also
            # supports alpha=0.1 explicitly. Tight tolerance.
            "abs_tol": 1e-6,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "secondary": {
            "abs_tol": 1e-4,
            "rel_tol": 1e-3,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "Croston's method is closed-form exponential smoothing "
            "on demand sizes and inter-arrival intervals. Given "
            "identical alpha and identical initialization, TSL's "
            "_croston and R `forecast::croston` should agree at "
            "machine precision. Documented divergence: R uses the "
            "default initialization (first non-zero demand); TSL "
            "matches. Tight tolerance at 1e-6 abs / 1e-4 rel on "
            "forecast value."
        ),
    },

    "p3_classical_decompose": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Classical decomposition is closed-form arithmetic: "
            "centered moving average → trend → detrend → group "
            "seasonal averages → residual. statsmodels and R "
            "stats::decompose implement the same algorithm. "
            "Bit-exact parity expected (Session 3 Observation 1: "
            "closed-form recursion → machine-precision agreement)."
        ),
    },

    "p3_stl": {
        "type": "tiered_outputs",
        "primary": {
            # STL is iterative LOESS-based decomposition (Cleveland
            # et al. 1990). statsmodels STL and R stats::stl both
            # implement the canonical algorithm; differences in
            # default convergence criteria + LOESS internals
            # produce small (1e-3 to 1e-2) divergences in
            # individual components.
            "abs_tol": 5e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 2e-1,
        },
        "secondary": {
            "abs_tol": 5e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "STL is iterative LOESS decomposition. statsmodels' "
            "STL implementation and R's stats::stl differ in "
            "(a) inner/outer iteration counts, (b) LOESS "
            "smoothing-window defaults, and (c) trend extraction "
            "convention. Per-component values diverge by ~1e-2 "
            "absolute on synthetic fixtures even when default "
            "configuration is matched. Master plan §7.1 widened "
            "for iterative-algorithm convergence-criterion "
            "differences."
        ),
    },

    "p3_mstl": {
        "type": "tiered_outputs",
        "primary": {
            # MSTL has *two* sources of non-uniqueness: (i) STL's
            # iterative LOESS, (ii) the seasonal-period iteration
            # ordering. Both implementations satisfy the structural
            # identity y = trend + sum(seasonal_k) + resid but may
            # decompose into different non-unique components.
            # Per-component divergence on synthetic dual-seasonal
            # fixture observed at 1.0+ absolute. Tolerance widened
            # accordingly; CAVEAT verdict expected; on_caveat_reroll
            # override prevents BLOCK escalation.
            "abs_tol": 5e-1,
            "rel_tol": 5e-1,
            "block_abs_tol": 5.0,
            "block_rel_tol": 5.0,
        },
        "secondary": {
            "abs_tol": 5e-1,
            "rel_tol": 5e-1,
            "block_abs_tol": 5.0,
            "block_rel_tol": 5.0,
        },
        "justification": (
            "MSTL is iterative multi-period STL (Bandara, "
            "Hyndman, Bergmeir 2021). statsmodels MSTL and R "
            "forecast::mstl apply STL sequentially across periods "
            "with different default inner-iteration counts, LOESS "
            "bandwidths, and period-iteration ordering. The "
            "seasonal decomposition is non-unique within the "
            "constraint y = trend + sum(seasonal) + resid; each "
            "implementation picks a different feasible point. "
            "Per-component divergence ~1.0 absolute observed on "
            "dual-seasonal fixtures; tolerance bands widened to "
            "place this in CAVEAT not BLOCK. Structural identity "
            "(sum equals input) verified separately and is "
            "expected to PASS at bit-exactness."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 2 — R volatility (Session 6).
    # GARCH variants share the same MLE-fit-class band but with
    # variant-specific widening for EGARCH (log-variance amplifies
    # optimizer divergence). HAR-RV is closed-form OLS.
    # ------------------------------------------------------------------

    "p3_sgarch": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-2,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 5.0,
            "rel_tol": 5e-2,
            "block_abs_tol": 50.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Master plan §7.1 MLE-fit band, slightly widened from "
            "p3_arima_manual baseline because Python `arch` and R "
            "`rugarch` are independent implementations with "
            "different optimizer initialization (arch uses SLSQP "
            "with simulated annealing pre-pass; rugarch uses "
            "hybrid solver). On standard GARCH(1,1) fixtures, "
            "coefficient divergence ~1e-3 abs typical; widened to "
            "1e-2 to leave headroom."
        ),
    },

    "p3_gjr_garch": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-2,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 5.0,
            "rel_tol": 5e-2,
            "block_abs_tol": 50.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Same band as p3_sgarch. GJR adds gamma asymmetry "
            "term; identifiability of gamma depends on having "
            "enough negative shocks in the fixture (GARCH(1,1) "
            "DGP at T=1000 should suffice). MLE-fit band."
        ),
    },

    "p3_egarch": {
        "type": "tiered_outputs",
        "primary": {
            # EGARCH log-variance parameterization amplifies
            # optimizer divergence — widened band.
            "abs_tol": 5e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 5e-1,
        },
        "secondary": {
            "abs_tol": 10.0,
            "rel_tol": 1e-1,
            "block_abs_tol": 100.0,
            "block_rel_tol": 1.0,
        },
        "justification": (
            "EGARCH log-variance representation tends to amplify "
            "optimizer-convergence divergence vs sGARCH/GJR. "
            "Additionally arch and rugarch use SWAPPED naming "
            "conventions for alpha (magnitude) and gamma "
            "(leverage) — the helper `run_reference_garch` swaps "
            "names on the rugarch side so the comparison aligns "
            "by economic role, not raw name. Tolerance band "
            "widened to 5e-2 abs / 1e-1 rel on Primary; CAVEAT "
            "outcomes expected on some fixtures."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 3 — R multivariate (Session 7).
    # VAR is closed-form OLS; PCA is closed-form eigendecomposition;
    # VECM is MLE-class (Johansen reduced-rank regression);
    # DFM is EM-stochastic (state-space with EM iteration).
    # ------------------------------------------------------------------

    "p3_var": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "block_abs_tol": 1e-4,
            "block_rel_tol": 1e-4,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "justification": (
            "VAR(p) estimation is OLS-on-stacked-equations: a "
            "closed-form normal-equations solve for the stacked "
            "AR coefficient matrix. Both statsmodels VAR and R "
            "vars::VAR implement the same algorithm; achieved "
            "tolerance should match Pattern A (closed-form) at "
            "1e-12 abs typical. The 1e-8 floor leaves headroom "
            "for subprocess CSV roundtrip noise and for the "
            "Sigma residual covariance divisor convention "
            "differences (T - k_total vs T - k_total - 1)."
        ),
    },

    # ENG-EXT-MULTIVARIATE-001 M1 — the FIRST interval/band ladder.
    # First instantiation of the reserved bootstrap_distributional
    # verdict_class: the metric is band width-ratio + coverage, NOT point
    # max_abs_diff. Three arms: selfparity_endpoint (tight; engine
    # _mc_irf_bands vs from-scratch identical MC), point_anchor (band center
    # vs R point IRF), and the two load-bearing distributional cross-package
    # arms (width-ratio + containment vs R vars::irf). Pattern generalizes to
    # CONFORMAL-001 (the conformal_coverage sibling).
    "p3_var_irf_bands": {
        "type": "bootstrap_distributional",
        "selfparity_endpoint": {
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "point_anchor": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-6,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-3,
        },
        "crosspkg_width_ratio": {
            "pass_lo": 0.85,
            "pass_hi": 1.18,
            "block_lo": 0.70,
            "block_hi": 1.43,
        },
        "crosspkg_containment": {
            "pass_min": 0.95,
            "block_min": 0.90,
        },
        "justification": (
            "ENG-EXT-MULTIVARIATE-001 M1 — VAR IRF bootstrap confidence "
            "bands, the first interval-validation. ARM 1 (selfparity_"
            "endpoint): the engine _mc_irf_bands and a from-scratch "
            "reimplementation of the IDENTICAL Monte-Carlo formulation use "
            "the same distinct-per-replication-seed scheme + percentile "
            "indices → expected bit-exact; 1e-8 PASS / 1e-6 BLOCK floors "
            "leave headroom for incidental float-assoc noise. ARM 3 (point_"
            "anchor): band center = orthogonalized point IRF vs R vars::irf "
            "point IRF; 1e-6 absorbs the Sigma-divisor-convention difference "
            "(Pattern H DSCD, as in p3_var) while staying far tighter than "
            "the band geometry. ARM 2 (load-bearing, distributional): the "
            "engine band is parametric-Gaussian-MC; R vars::irf is residual-"
            "resampling — endpoints can never match, so width-ratio + "
            "containment are compared. width-ratio PASS [0.85,1.18] / BLOCK "
            "[0.70,1.43] and containment PASS>=0.95 / BLOCK>=0.90 are "
            "calibrated UNDER THE GAUSSIAN-INNOVATION DGP (where the two "
            "bootstrap methods converge); a non-Gaussian DGP would "
            "legitimately diverge and require widening. Do NOT widen to mask "
            "a real formulation difference — the cross-package arm gates "
            "(the A1c self-parity-validates-match-not-correctness lesson)."
        ),
    },

    # ENG-EXT-MULTIVARIATE-001 M3a — Blanchard–Quah SVAR identification
    # cross-package point-parity vs R vars::BQ. Closed-form matrix algebra
    # on the VAR OLS fit (B0 = C1^-1 chol(C1 Σ C1^T); structural IRF =
    # ma_rep @ B0) — the probe pre-verified bit-for-bit agreement. Machine
    # precision at the p3_var / 1c_bvar_irf_fevd closed_form band.
    "p3_var_bq": {
        "type": "tiered_outputs",
        "b0_vs_vars": {
            "abs_tol": 1e-8, "rel_tol": 1e-8,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-4,
        },
        "lrim_vs_vars": {
            "abs_tol": 1e-8, "rel_tol": 1e-8,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-4,
        },
        "struct_irf_vs_vars": {
            "abs_tol": 1e-8, "rel_tol": 1e-8,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-4,
        },
        "justification": (
            "ENG-EXT-MULTIVARIATE-001 M3a — Blanchard–Quah long-run-"
            "restriction SVAR. Net-new (statsmodels SVAR is A/B/AB short-run "
            "only); B0 = C(1)^-1 chol(C(1) Σ C(1)^T), structural IRF = "
            "ma_rep @ B0. Cross-package vs R vars::BQ ($B / $LRIM / structural "
            "irf) on p3_var's bivariate VAR(2) DGP (n=500, seed=42) — the same "
            "fit S64 validated, so the comparison isolates the BQ "
            "identification. The probe PRE-VERIFIED bit-for-bit agreement "
            "(engine B0 == R $B exactly; engine C1·B0 == R $LRIM exactly; sign "
            "convention matches — positive-diagonal long-run Cholesky). "
            "closed_form 1e-8 (block 1e-4), matching p3_var / 1c_bvar_irf_fevd "
            "— VAR is OLS (closed-form, not iterative MLE) and BQ is closed-"
            "form algebra on top. A per-shock-column sign alignment is applied "
            "defensively before comparison (structural shocks identified up to "
            "sign). Do NOT widen to mask a real divergence."
        ),
    },

    # ENG-EXT-MULTIVARIATE-001 M3c — proxy/IV-SVAR self-parity + the
    # LOAD-BEARING instrument-relevance functional check. Deterministic
    # closed-form covariance algebra → bit-exact self-parity; the relevance
    # check (corr of the identified shock with the instrument) is the
    # formulation-correctness substitute for the absent cross-package arm.
    "p3_var_proxy_svar": {
        "type": "tiered_outputs",
        "b1_selfparity": {
            "abs_tol": 1e-12, "rel_tol": 1e-12,
            "block_abs_tol": 1e-9, "block_rel_tol": 1e-9,
        },
        "struct_irf_selfparity": {
            "abs_tol": 1e-12, "rel_tol": 1e-12,
            "block_abs_tol": 1e-9, "block_rel_tol": 1e-9,
        },
        "instrument_relevance": {
            "min_corr": 0.2,
        },
        "justification": (
            "ENG-EXT-MULTIVARIATE-001 M3c — proxy / external-instrument SVAR. "
            "Net-new (statsmodels SVAR is A/B/AB short-run only); NO usable "
            "cross-package R package (svars is the wrong family — "
            "heteroskedasticity ID). Self-parity: engine _proxy_svar vs a "
            "from-scratch reimplementation of the IDENTICAL formulation "
            "(b1 ∝ Cov(u,z) normalized to unit impact on the reference "
            "variable; GLS-projected shock; structural IRF = ma_rep @ b1) → "
            "bit-exact (1e-12; covariance algebra is deterministic). The "
            "instrument_relevance check (min_corr 0.2) is LOAD-BEARING — the "
            "scheme-DEFINING property is that the identified shock correlates "
            "with the instrument (first-stage relevance; at n≈600 corr 0.2 ≈ "
            "F > 10). It is the formulation-correctness substitute for the "
            "absent cross-package arm (A1c lesson). Verified discriminating: "
            "relevant instrument corr ≈ 0.87 PASS, irrelevant control ≈ 0.09 "
            "BLOCK. Do NOT relax the threshold to mask a non-correlated shock."
        ),
    },

    # ENG-EXT-MULTIVARIATE-001 M3b — sign-restriction SVAR set-identification
    # (the third validation kind). Self-parity matched-rotation-sampling →
    # bit-exact set summary (median impact + median/lo16/hi84 IRF bands);
    # plus the LOAD-BEARING functional checks (sign-satisfaction == 1.0;
    # Cholesky-in-set admissibility; economic sign) as the
    # formulation-correctness substitute for the absent cross-package arm.
    "p3_var_sign_restriction": {
        "type": "tiered_outputs",
        "set_summary_selfparity": {
            "abs_tol": 1e-12, "rel_tol": 1e-12,
            "block_abs_tol": 1e-9, "block_rel_tol": 1e-9,
        },
        "sign_satisfaction": {
            "min_frac": 1.0,
        },
        "cholesky_in_set": {
            "required": True,
        },
        "economic_sign": {
            "required": True,
        },
        "justification": (
            "ENG-EXT-MULTIVARIATE-001 M3b — sign-restriction SVAR, the A-phase's "
            "THIRD validation kind (SET-identification). Net-new (statsmodels "
            "SVAR is A/B/AB short-run only); NO usable cross-package R package "
            "(svars wrong family; VARsignR CRAN-archived). The admissible set "
            "(Haar rotations satisfying the signs) is summarized by median-target "
            "+ 16/84 bands — the same percentile-band structure as M1's "
            "bootstrap_distributional (rotation sampling ≈ bootstrap resampling), "
            "so the verdict_class is reused. set_summary_selfparity 1e-12: engine "
            "_sign_restriction_svar vs a from-scratch reimplementation of the "
            "IDENTICAL rotation sampling (same seed/draws/QR-normalization/diag-"
            "normalization/retention) → bit-exact set summary (deterministic). "
            "The functional checks are LOAD-BEARING (the A1c formulation-"
            "correctness substitute): sign_satisfaction == 1.0 (every retained "
            "rotation satisfies the signs); cholesky_in_set (the diagonal-"
            "normalized Cholesky is admissible — the strongest invariant, a "
            "set-construction bug excluding it fails); economic_sign (median "
            "impact's restricted entries have the correct sign). Verified "
            "discriminating against deliberate bugs (retain-all → 0.58 caught; "
            "Cholesky-excluding pattern → admissible False caught). Do NOT relax "
            "these to mask a set-construction bug."
        ),
    },

    # ENG-EXT-CONFORMAL-001 C1 — CQR; the FIRST conformal_coverage ladder
    # (the interval family's coverage sibling). selfparity_bounds tight
    # (bit-exact); coverage_gap = the LOAD-BEARING empirical-coverage floor
    # (slack EARNED = 2·std of held-out coverage across 8 seeds = 0.07;
    # mean 0.905 ≈ nominal 0.90); crosspkg_* = distributional vs MAPIE
    # (matched calibration, but MAPIE's internal conformal-quantile shifts
    # bounds → width-ratio + coverage-agreement, not endpoints).
    "p3_conformal_cqr": {
        "type": "conformal_coverage",
        "selfparity_bounds": {
            "abs_tol": 1e-8, "rel_tol": 1e-8,
            "block_abs_tol": 1e-6, "block_rel_tol": 1e-6,
        },
        "coverage_gap": {"slack": 0.07, "caveat_mult": 3},
        "crosspkg_width_ratio": {
            "pass_lo": 0.85, "pass_hi": 1.18, "block_lo": 0.70, "block_hi": 1.43,
        },
        "crosspkg_coverage_agreement": {"pass_abs": 0.05, "block_abs": 0.12},
        "justification": (
            "ENG-EXT-CONFORMAL-001 C1 — Conformalized Quantile Regression "
            "(Romano-Patterson-Candès 2019); FIRST instantiation of the "
            "reserved conformal_coverage verdict_class. selfparity_bounds "
            "1e-8: engine _cqr_intervals vs a from-scratch reimplementation of "
            "the IDENTICAL Romano formulation (same seeded GBR base, same "
            "calibration split, same conformal-quantile index) → bit-exact "
            "bounds + Q. coverage_gap (LOAD-BEARING, the scheme-defining "
            "property): held-out empirical coverage ≥ (1−α) − slack; slack "
            "EARNED = 2·std of CQR held-out coverage measured across 8 seeds "
            "(mean 0.905 ≈ nominal 0.90, std 0.034 → slack 0.07; do NOT widen "
            "to mask under-coverage). caveat_mult 3 (CAVEAT band ≥ nominal − "
            "3·slack). crosspkg_* (distributional vs MAPIE "
            "ConformalizedQuantileRegressor, matched calibration): MAPIE's "
            "internal conformal-quantile / quantile-crossing handling shifts "
            "the bounds (~0.2), so the cross-package check is band GEOMETRY — "
            "width_ratio (pre-verified ≈ 0.99) + coverage_agreement (Δ ≈ 0.00) "
            "— NOT bit-exact endpoints (that is the self-parity arm). The "
            "mis-scaled (×0.3 width) discrimination guard confirms the "
            "coverage floor catches gross miscalibration. Pattern reusable for "
            "C2 (EnbPI). Reuses the conformal_nominal_coverage / "
            "interval_containment invariant functions in place."
        ),
    },

    # ENG-EXT-CONFORMAL-001 C2 — EnbPI; the SECOND conformal_coverage ladder
    # (inherits C1's shape). coverage_gap.slack 0.07 INHERITED (earned at C1,
    # finite-sample-variability-anchored). crosspkg_width_ratio MEASURED for
    # EnbPI (pre-verified ≈ 0.98 vs MAPIE EnbPI — the matched-distributional
    # posture transposes from C1). selfparity_bounds bit-exact for BOTH the
    # standard (gbr) and neural (MLP, the S85 fold-in) bases.
    "p3_conformal_enbpi": {
        "type": "conformal_coverage",
        "selfparity_bounds": {
            "abs_tol": 1e-8, "rel_tol": 1e-8,
            "block_abs_tol": 1e-6, "block_rel_tol": 1e-6,
        },
        "coverage_gap": {"slack": 0.07, "caveat_mult": 3},
        "crosspkg_width_ratio": {
            "pass_lo": 0.78, "pass_hi": 1.35, "block_lo": 0.65, "block_hi": 1.55,
        },
        "crosspkg_coverage_agreement": {"pass_abs": 0.06, "block_abs": 0.15},
        "justification": (
            "ENG-EXT-CONFORMAL-001 C2 — EnbPI (Xu-Xie 2021 ensemble batch "
            "prediction intervals); SECOND instantiation of conformal_coverage. "
            "selfparity_bounds 1e-8: engine _enbpi_intervals vs a from-scratch "
            "reimplementation of the IDENTICAL block-bootstrap-ensemble + OOB "
            "conformal-width formulation (same RandomState block bootstrap, "
            "same base, same OOB aggregation, same quantile index) → bit-exact "
            "bounds for BOTH the standard gradient-boosting base AND the neural "
            "MLP base (the S85 fold-in; MLPRegressor is deterministic given "
            "random_state — pre-verified 0.00). coverage_gap (LOAD-BEARING): "
            "slack 0.07 INHERITED from C1 (earned = 2·std of held-out coverage). "
            "crosspkg_* (distributional vs MAPIE TimeSeriesRegressor "
            "method='enbpi', matched base+block+ensemble+seed): MAPIE's "
            "independent block-bootstrap draws differ → width_ratio + "
            "coverage_agreement, NOT bit-exact endpoints. The width-ratio band "
            "[0.78,1.35] (block [0.65,1.55]) is EnbPI-SPECIFIC and EARNED by "
            "measurement: across-seed width-ratio measured 0.845-1.297 (mean "
            "1.01) — WIDER than C1 CQR's [0.85,1.18] because the ensemble-"
            "bootstrap mechanism is genuinely noisier than CQR's quantile-"
            "regression conformalization (it tightens to 0.87-1.17 at larger "
            "ensembles, but the harness uses a modest ensemble for runtime). "
            "The band still catches a formulation bug (wrong OOB aggregation / "
            "width → 2x or 0.5x, outside block); the LOAD-BEARING gate is "
            "coverage_gap + self-parity, with width-ratio a distributional "
            "sanity. The mis-scaled (×0.3) discrimination guard confirms the "
            "coverage floor catches gross miscalibration. Do NOT widen "
            "coverage_gap to mask under-coverage."
        ),
    },

    "p3_vecm": {
        # Phase 3.5 Session 3 (Item 1): tightened from canonical
        # mle_fit band (1e-3 abs / 1e-2 rel) to single_impl_mle
        # band (1e-5 abs / 1e-4 rel). Phase 3 Session 7 achieved
        # 9.99e-16 abs (beta) / 2.78e-13 abs (alpha) — 13 orders
        # of headroom inside the new band still. 1.5x margin per
        # master plan §4 risk 4 mitigation: 1e-5 abs is 1.5e+8
        # × the actual achieved 9.99e-16 abs.
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-5,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "secondary": {
            "abs_tol": 5.0,
            "rel_tol": 5e-2,
            "block_abs_tol": 50.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "VECM Johansen reduces to closed-form OLS on the "
            "cointegrating vectors. statsmodels VECM and R "
            "urca::ca.jo + vars::vec2var implement identical "
            "reduced-rank regression math; alpha-beta sign + "
            "normalization convention differs (statsmodels "
            "normalizes beta first element to 1; R's @V "
            "eigenvectors have arbitrary norm). The compare "
            "function applies a normalize-and-align step before "
            "comparison. Phase 3.5 Session 3 (Item 1) tightened "
            "to single_impl_mle band (1e-5 abs / 1e-4 rel) — "
            "achieved 9.99e-16 abs in Phase 3 Session 7 audit, "
            "13 orders of headroom; 1e-5 floor preserves "
            "subprocess CSV roundtrip noise margin."
        ),
    },

    # ENG-EXT-MULTIVARIATE-001 M2 — VECM IRF + FEVD cross-package
    # point-parity vs R urca::ca.jo + vars::vec2var -> vars::irf / fevd.
    # Sub-metric ladder (like 1c_bvar_irf_fevd): the orthogonalized IRF
    # carries a sigma-divisor sensitivity (mle-band); FEVD is ratio-
    # invariant to uniform sigma scaling (near-bit-exact); row-sum-to-one
    # is a structural invariant on both arms.
    "p3_vecm_irf_fevd": {
        "type": "tiered_outputs",
        "irf_vs_vars": {
            "abs_tol": 1e-5,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "fevd_vs_vars": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-6,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-3,
        },
        "fevd_sum_to_one": {
            "abs_tol": 1e-8,
        },
        "justification": (
            "ENG-EXT-MULTIVARIATE-001 M2 — VECM IRF (native wrap of "
            "statsmodels VECMResults.irf().orth_irfs) + FEVD (net-new "
            "cumulative-squared-orthogonalized-MA from orth_ma_rep; "
            "orth_ma_rep == orth_irfs exactly). Cross-package vs R "
            "urca::ca.jo -> vars::vec2var -> vars::irf(ortho=TRUE) / "
            "vars::fevd on p3_vecm's bivariate cointegrated rank=1 DGP "
            "(n=500, seed=42) — the same fit S65 validated at "
            "single_impl_mle, so the comparison isolates the IRF/FEVD "
            "computation. MEASURED (S-this): irf max_abs 5.63e-14 / max_rel "
            "1.34e-13; fevd max_abs 3.59e-14; row-sum dev 1.11e-16 — MACHINE "
            "PRECISION. The anticipated sigma-divisor IRF sensitivity "
            "(statsmodels sigma_u T-k_total vs R vec2var) did NOT materialize "
            "(the arms agree on the divisor here). irf_vs_vars set at the "
            "single_impl_mle band (1e-5 abs / 1e-4 rel; block 1e-3/1e-2) — 9+ "
            "orders of headroom over the measured 5.63e-14; matches p3_vecm's "
            "primary band (same Johansen fit). fevd_vs_vars 1e-6 (FEVD is "
            "ratio-invariant to uniform sigma scaling -> bit-exact). "
            "fevd_sum_to_one 1e-8: structural per-variable per-horizon "
            "normalization invariant on both arms. Do NOT widen to mask a "
            "real divergence should one ever appear (Pattern H DSCD discipline)."
        ),
    },

    "p3_dfm": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 5e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 5e-1,
        },
        "secondary": {
            "abs_tol": 50.0,
            "rel_tol": 1e-1,
            "block_abs_tol": 500.0,
            "block_rel_tol": 1.0,
        },
        "justification": (
            "DFM is fit via Kalman + EM. statsmodels "
            "DynamicFactor and R MARSS are independent "
            "implementations with different EM convergence "
            "criteria, parameter parameterizations, and "
            "initialization heuristics. Master plan §7.1 "
            "EM-stochastic class: 1e-2 abs / 5e-2 rel widened "
            "to 5e-2 abs / 1e-1 rel here because DFM EM is "
            "particularly sensitive to local optima on small T "
            "(200 obs)."
        ),
    },

    "p3_pca": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "secondary": {
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "block_abs_tol": 1e-4,
            "block_rel_tol": 1e-4,
        },
        "justification": (
            "PCA is closed-form eigendecomposition of the "
            "covariance matrix. NumPy `eigh` (TSL) and sklearn "
            "PCA (reference, internally `np.linalg.svd`) both "
            "produce numerically equivalent eigenvalue / "
            "eigenvector pairs (modulo sign convention, "
            "handled by sign-canonicalization in compare). "
            "Pattern A bit-exact target."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 4 — R Markov / nonlinear (Session 8).
    # HMM + Markov switching: em_stochastic class. TAR/SETAR + STAR:
    # mle_fit class. NAR/NARX: dl_seed_pinned (correlation-based
    # comparison; weight-level parity not feasible).
    # ------------------------------------------------------------------

    "p3_hmm": {
        "type": "tiered_outputs",
        "primary": {
            # Default band — used for any metric not in
            # `per_metric`. Wide because transition_matrix is
            # the most-divergent emission EM-stochastic metric.
            "abs_tol": 0.3,
            "rel_tol": 1.0,
            "block_abs_tol": 0.7,
            "block_rel_tol": 2.0,
        },
        "secondary": {
            "abs_tol": 5e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 5e-1,
        },
        "per_metric": {
            # Phase 3.5 Session 4 — em_stochastic per-metric
            # heterogeneity. Achieved tolerances in S2 fast-tier
            # were heterogeneous: transition_matrix 0.237 abs,
            # emission_means 1.48e-5, emission_covars 7.74e-5,
            # log_likelihood 5.46e-6. Keeping a single primary
            # band of 0.3 abs would swallow 4 orders of
            # achievable headroom on the three tight metrics.
            # Tightening only the metrics with demonstrated
            # headroom; transition_matrix retains the wide
            # Pattern H DSCD-EM band via the primary fallback.
            "transition_matrix": {
                # Pattern H DSCD-EM — kept wide because hmmlearn
                # and R depmixS4 routinely converge to different
                # transition matrices on the same likelihood
                # surface (state-label permutation +
                # initialization sensitivity).
                "abs_tol": 0.3,
                "rel_tol": 1.0,
                "block_abs_tol": 0.7,
                "block_rel_tol": 2.0,
            },
            "emission_means": {
                # Achieved 1.48e-5 abs in S2; 1e-3 preserves
                # 1.8 orders of headroom (67x safety).
                "abs_tol": 1e-3,
                "rel_tol": 1e-3,
                "block_abs_tol": 1e-2,
                "block_rel_tol": 1e-2,
            },
            "emission_covars": {
                # Achieved 7.74e-5 abs in S2; 1e-3 preserves
                # 1.1 orders of headroom (13x safety).
                "abs_tol": 1e-3,
                "rel_tol": 1e-3,
                "block_abs_tol": 1e-2,
                "block_rel_tol": 1e-2,
            },
            "log_likelihood": {
                # Achieved 5.46e-6 abs in S2; 1e-3 preserves
                # 2.3 orders of headroom (180x safety).
                "abs_tol": 1e-3,
                "rel_tol": 1e-3,
                "block_abs_tol": 1e-2,
                "block_rel_tol": 1e-2,
            },
        },
        "justification": (
            "HMM Baum-Welch EM. hmmlearn (Python) and R "
            "depmixS4 are independent EM implementations; "
            "both can converge to different local optima of "
            "the same likelihood surface. Phase 3.5 Session 4 "
            "split the canonical em_stochastic single-band "
            "(1e-2 abs / 5e-2 rel) into per-metric tiers: "
            "transition_matrix retains the wide Pattern H "
            "DSCD-EM band (0.3 abs / 1.0 rel) because EM "
            "label-permutation produces 0.2-0.3 abs divergence "
            "as a baseline; emission_means / emission_covars / "
            "log_likelihood tighten to 1e-3 abs (S2 measured "
            "1.5e-5 / 7.7e-5 / 5.5e-6 abs respectively, "
            "preserving 1.1-2.3 orders of headroom). The split "
            "exposes per-metric agreement that the single-band "
            "approach concealed."
        ),
    },

    "p3_markov_switching": {
        "type": "tiered_outputs",
        "primary": {
            # Default band — used for any metric not in
            # `per_metric`. Wide because the most-divergent
            # metrics (transition_matrix, log_likelihood)
            # routinely produce 0.3-2.0 abs divergence between
            # statsmodels and MSwM.
            "abs_tol": 2.0,
            "rel_tol": 1.0,
            "block_abs_tol": 5.0,
            "block_rel_tol": 5.0,
        },
        "per_metric": {
            # Phase 3.5 Session 4 — em_stochastic per-metric
            # heterogeneity. Achieved in S2 fast-tier:
            # regime_means 5.90e-5 abs, transition_matrix
            # 5.46e-2 abs, log_likelihood 0.348 abs. Only
            # regime_means has enough headroom to safely
            # tighten; the other two metrics stay at the wide
            # Pattern H DSCD band.
            "regime_means": {
                # Achieved 5.90e-5 abs in S2; 1e-2 preserves
                # 2.2 orders of headroom (170x safety). Most
                # informative metric for downstream
                # interpretation; tightening exposes that
                # statsmodels and MSwM agree on regime means
                # to ~5 orders, even when transition matrices
                # and log-likelihoods diverge.
                "abs_tol": 1e-2,
                "rel_tol": 1e-2,
                "block_abs_tol": 1e-1,
                "block_rel_tol": 1e-1,
            },
            "transition_matrix": {
                # Pattern H DSCD-EM — kept at primary band.
                # Achieved 5.46e-2 abs in S2; tightening below
                # 0.5 risks regression on the EM label-
                # permutation noise floor.
                "abs_tol": 2.0,
                "rel_tol": 1.0,
                "block_abs_tol": 5.0,
                "block_rel_tol": 5.0,
            },
            "log_likelihood": {
                # Pattern H DSCD-EM — kept at primary band.
                # Achieved 0.348 abs in S2; only 0.76 orders
                # of headroom to a 2.0 band, too risky to
                # tighten given MSwM's different log-lik sign
                # convention and statsmodels' filtering vs
                # smoothed-state ambiguity.
                "abs_tol": 2.0,
                "rel_tol": 1.0,
                "block_abs_tol": 5.0,
                "block_rel_tol": 5.0,
            },
        },
        "justification": (
            "Markov switching mean model. statsmodels "
            "MarkovRegression and R MSwM::msmFit are "
            "independent EM implementations of Hamilton 1989, "
            "but on synthetic fixtures they routinely converge "
            "to different local optima with substantially "
            "different mean estimates. MSwM uses a different "
            "log-likelihood sign convention. Phase 3.5 Session "
            "4 split the canonical em_stochastic single-band "
            "into per-metric tiers: regime_means tightens to "
            "1e-2 abs (S2 achieved 5.9e-5; 2.2 orders of "
            "headroom), exposing that the two backends agree "
            "on regime means to ~5 orders even when transition "
            "matrices and log-likelihoods diverge under "
            "Pattern H DSCD-EM. transition_matrix and "
            "log_likelihood retain the wide 2.0 abs / 1.0 rel "
            "Pattern H DSCD-EM band."
        ),
    },

    "p3_tar_setar": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "SETAR with grid-search threshold. TSL custom "
            "implementation and R tsDyn::setar use different "
            "threshold-search heuristics; threshold may differ "
            "by grid-resolution amount. MLE-fit class with "
            "moderate widening (5e-2 rel) for grid divergence."
        ),
    },

    "p3_star": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 5e-1,
            "rel_tol": 5e-1,
            "block_abs_tol": 2.0,
            "block_rel_tol": 1.0,
        },
        "justification": (
            "STAR Tier B/C per master plan §5 — TSL custom "
            "scipy.optimize fit and R tsDyn::star use different "
            "optimizer initialization for the smoothness "
            "parameter gamma (typically 1-50 range, can diverge "
            "by orders of magnitude across optimizers). Wide "
            "tolerance band acknowledges this; CAVEAT verdict "
            "expected on most fixtures."
        ),
    },

    "p3_nar_narx": {
        "type": "tiered_outputs",
        "primary": {
            # S85 self-parity rewrite (Disposition X): R tsDyn::nlar
            # FAILS to produce finite forecasts on this fixture
            # (genuine NO-REFERENCE), so the harness was rewritten to
            # self-parity — the reference independently reproduces the
            # engine's deterministic sklearn-MLP NAR pipeline (Fast
            # preset: ar_lags=3, hidden=(10,), random_state=42,
            # early_stopping). The MLP fit is BIT-IDENTICAL between
            # engine + reference (confirmed: the reference's full-
            # precision values round EXACTLY to the engine's emitted
            # values). The only residual is the ENGINE OUTPUT-ROUNDING
            # FLOOR (Phase 1 finding B8): run_tsl reads the engine's
            # 6-decimal-rounded forecast table (floor ~5e-7) and
            # 4-decimal-rounded r_squared audit (floor ~5e-5), while
            # the self-parity reference computes full precision. The
            # band is set just above this documented rounding floor —
            # bit-exact modulo B8 output rounding (S81 tar_setar
            # precedent: tsl-rounded vs ref-full-precision, diff IS
            # the rounding floor).
            "abs_tol": 1e-4,
            "rel_tol": 1e-3,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "NAR/NARX self-parity (S85 Disposition X). R "
            "tsDyn::nlar fails to converge / produce finite "
            "forecasts on the fixture (genuine NO-REFERENCE), so "
            "cross-package weight-level parity is impossible. The "
            "engine sklearn MLPRegressor is deterministic-bit-exact "
            "at fixed seed (confirmed cross-invocation); the "
            "self-parity reference reproduces the engine's NAR "
            "feature-construction + StandardScaler + MLP fit + "
            "iterative forecast recursion identically, validating "
            "the engine wrapper at machine precision (abs 1e-8 / "
            "rel 1e-6). Block precedent: Change Points "
            "S75/S76/S78/S79 self-parity for cross-package-"
            "unavailable situations; nar_narx is the strongest "
            "case (reference FAILS rather than diverges)."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 5 — R state space (Session 9).
    # 3 KFAS-based MLE Kalman wrappers + particle filter (SMC) +
    # kalman imputation. KFAS and statsmodels UC implement same
    # math; achievable mle_fit-class.
    # ------------------------------------------------------------------

    "p3_local_level": {
        "type": "tiered_outputs",
        "primary": {
            # Single-state Kalman MLE; both implementations
            # converge to similar variances modulo optimizer path.
            # Smoothed state achievable at near-bit-exact when
            # variances align.
            "abs_tol": 1e-2,
            "rel_tol": 1e-1,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Local level Kalman MLE. statsmodels UC and R KFAS "
            "implement the same Kalman recursion. Variance "
            "estimates can diverge by 5-10% due to BFGS "
            "convergence-criterion differences; smoothed states "
            "tighter (1e-3 abs typical given variance agreement)."
        ),
    },

    "p3_local_linear_trend": {
        "type": "tiered_outputs",
        "primary": {
            # LLT 3-variance identifiability is fundamentally
            # weak: statsmodels and KFAS routinely converge to
            # different local optima where one drives sigma_eta
            # to zero and the other drives sigma_zeta to zero.
            # Both are valid decompositions of same y. Pattern H
            # DSCD instance for LLT family. Wide band to map
            # to CAVEAT.
            "abs_tol": 2.0,
            "rel_tol": 2.0,
            "block_abs_tol": 10.0,
            "block_rel_tol": 10.0,
        },
        "justification": (
            "LLT 3-variance identifiability: statsmodels UC and "
            "R KFAS routinely converge to different local optima "
            "of the same Kalman likelihood (one drives sigma_eta "
            "to zero; other drives sigma_zeta to zero). Both are "
            "mathematically valid decompositions of identical y. "
            "Pattern H DSCD instance. Wide tolerance band; "
            "CAVEAT verdict expected on small-T fixtures; PASS "
            "when both implementations converge to same optimum."
        ),
    },

    "p3_structural_ts": {
        "type": "tiered_outputs",
        "primary": {
            # 4 variances + multi-state smoother. Hardest in
            # Batch 5; may CAVEAT depending on optimizer path.
            "abs_tol": 5e-1,
            "rel_tol": 1.0,
            "block_abs_tol": 2.0,
            "block_rel_tol": 5.0,
        },
        "justification": (
            "Structural TS = level + trend + seasonal Kalman "
            "MLE. 4 variances to fit; multiple local optima "
            "expected. Wide tolerance band; CAVEAT verdicts "
            "acceptable for level/trend/seasonal variance "
            "estimates."
        ),
    },

    "p3_particle_filter": {
        "type": "tiered_outputs",
        "primary": {
            "corr_pass": 0.85,
            "corr_caveat": 0.6,
            "abs_tol": 1.0,
            "rel_tol": 0.5,
            "block_abs_tol": 5.0,
            "block_rel_tol": 2.0,
        },
        "justification": (
            "Particle filter SMC. TSL numpy bootstrap PF and "
            "Python particles package use different resampling "
            "algorithms + RNG paths. Compare via filtered-mean "
            "Pearson correlation; corr >= 0.85 PASS; 0.60-0.85 "
            "CAVEAT. NO-REFERENCE Tier C class."
        ),
    },

    "p3_kalman_imputation": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 5e-2,
            "rel_tol": 2e-1,
            "block_abs_tol": 5e-1,
            "block_rel_tol": 1.0,
        },
        "justification": (
            "Kalman imputation via local-level smoother. "
            "Imputed values at NA positions = smoothed state; "
            "tightness depends on variance estimate agreement "
            "between statsmodels and KFAS optimizers."
        ),
    },

    "p3_har_rv": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "secondary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-6,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-3,
        },
        "justification": (
            "HAR-RV is closed-form OLS regression on identical "
            "regressors. NumPy lstsq (TSL) and R lm (reference) "
            "implement the same normal-equations solve; bit-"
            "exact parity expected (Session 3 Observation 1: "
            "closed-form recursion → machine precision). "
            "Achieved tolerance at 1e-12 to 1e-14 abs typical; "
            "the 1e-10 floor leaves headroom for subprocess CSV "
            "roundtrip noise."
        ),
    },

    "p3_tbats": {
        "type": "tiered_outputs",
        "primary": {
            # Python tbats 1.1.3 (Skorupa) and R forecast::tbats
            # are independent implementations of De Livera-Hyndman-
            # Snyder 2011 with different optimizer initialization.
            # Box-Cox lambda + smoothing parameters may differ by
            # 1e-3 to 1e-2 absolute depending on convergence path.
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 2e-1,
        },
        "secondary": {
            "abs_tol": 5.0,
            "rel_tol": 1e-1,
            "block_abs_tol": 50.0,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Phase 1 audit-script `audit_1b_tbats.py` (deprecated) "
            "documented Python tbats 1.1.3 and R forecast::tbats "
            "as independent implementations of De Livera-Hyndman-"
            "Snyder 2011 TBATS with different optimizer init. "
            "Smoothing params (alpha, beta, gamma) and Box-Cox "
            "lambda may differ by 1e-3 to 1e-2 absolute due to "
            "convergence-path divergence. Forecast values typically "
            "agree at 1e-2 abs / 5e-2 rel. Master plan §7.1 MLE-fit "
            "class. Harness promotion of pre-existing Phase 1 "
            "audit-script tolerance findings."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 6 — R change-points / stationarity (Session 10).
    # Three closed-form stationarity tests (ADF, KPSS, PP) target
    # Pattern A bit-exact at the test-statistic level given pinned
    # lags. Four change-point / anomaly wrappers use Pattern A
    # self-parity references (BOCPD, CUSUM/PH, PELT, STL+ESD); their
    # tolerance bands assert exact integer matches on detection counts
    # and indices. Intervention analysis is MLE-fit class via
    # statsmodels SARIMAX vs R stats::arima(xreg=...).
    # ------------------------------------------------------------------

    "p3_adf": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "ADF test statistic is closed-form OLS on the "
            "differenced series with optional lagged differences. "
            "Both statsmodels.adfuller and urca::ur.df implement "
            "the standard Dickey-Fuller 1979 procedure; given "
            "identical lag specification (lags=1, type='drift'), "
            "the tau statistic should agree at machine precision. "
            "1e-6 abs floor leaves headroom for subprocess CSV "
            "roundtrip noise. Master plan §7.1 closed-form class."
        ),
    },

    "p3_kpss": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "KPSS statistic is closed-form: ratio of partial-sum-"
            "of-residuals to a Newey-West-style long-run variance "
            "estimator. Both statsmodels.kpss and urca::ur.kpss "
            "compute the identical statistic given identical "
            "bandwidth (use.lag=5). 1e-6 abs floor for subprocess "
            "noise. Master plan §7.1 closed-form class."
        ),
    },

    "p3_kpss_trend": {
        "type": "tiered_outputs",
        # Scope-extension UNIT 2: kpss_test TREND spec (reg=ct), additive
        # over p3_kpss (reg=c). Same closed-form KPSS eta statistic with a
        # linear detrend -> urca::ur.kpss type="tau". Reuses the p3_kpss
        # bit-exact band for both arms (reg=ct at the engine's realized
        # auto bandwidth + at pinned LAG=5). B.i pure parameter-coverage:
        # no orchestration arm (the decision is a single threshold).
        "primary": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-3, "block_rel_tol": 1e-2,
        },
        "justification": (
            "KPSS trend-spec (reg=ct) eta statistic is the same closed-form "
            "ratio as the level spec, with a linear detrend; statsmodels.kpss "
            "and urca::ur.kpss type='tau' compute the identical statistic "
            "given identical bandwidth. Validated at the engine's realized "
            "auto bandwidth (library-selected, read back) and at pinned "
            "LAG=5; 1e-6 abs floor for subprocess CSV roundtrip noise — same "
            "closed_form band as p3_kpss. Master plan §7.1 closed-form class; "
            "Phase 7+ scope-extension B.i (component cross-package extension)."
        ),
    },

    "p3_pp": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "justification": (
            "Phillips-Perron Z(t) statistic is closed-form Newey-"
            "West correction to the DF t-stat. Pattern J candidate: "
            "arch.unitroot.PhillipsPerron and urca::ur.pp use "
            "potentially different Newey-West weight kernels and "
            "lag-truncation conventions. Pinning lags=5 on both "
            "sides aligns most of the divergence; remaining 1e-3 "
            "abs accommodates internal HAC kernel differences "
            "(Bartlett vs Quadratic-Spectral default). Master plan "
            "§7.1 with Pattern J widening."
        ),
    },

    "p3_adf_triage": {
        "type": "tiered_outputs",
        # COMPONENT arms: ADF/KPSS validated cross-package vs urca at the
        # engine's REALIZED triage lag (statsmodels AIC autolag / KPSS
        # nlags="auto"). Bit-exact bands reuse the p3_adf / p3_kpss
        # closed_form bands (1e-6 abs / 1e-4 rel; 1e-3 block) — the
        # statistic agrees at machine precision GIVEN the matched lag
        # (the library lag-selection rule is a trusted primitive, not
        # re-validated; disclosed in the §2.5 entry).
        "adf_component": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-3, "block_rel_tol": 1e-2,
        },
        "kpss_component": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-3, "block_rel_tol": 1e-2,
        },
        # PP arm: Pattern-J band (reuses p3_pp). Kernel/divisor convention
        # divergence + triage auto-bandwidth Schwert(2/9) + runtime
        # backend dispatch. PP bounds only the CONFLICTING tie-breaker
        # text, NOT the verdict.
        "pp_component": {
            "abs_tol": 1e-3, "rel_tol": 1e-2,
            "block_abs_tol": 1e-1, "block_rel_tol": 1e-1,
        },
        "justification": (
            "Scope-extension PILOT for the adf_test joint ADF/KPSS/PP "
            "triage verdict (ribbon default), additive over p3_adf. "
            "COMPONENT arms: ADF vs urca::ur.df and KPSS vs urca::ur.kpss "
            "at the engine's realized auto-selected lag — closed_form "
            "bit-exact bands (reuse p3_adf/p3_kpss); PP vs urca::ur.pp at "
            "Pattern-J widening (reuse p3_pp). ORCHESTRATION arms (the 2x2 "
            "rule test + integration cells) are boolean label-equality "
            "checks gated PASS/BLOCK in compare(), not numeric-tolerance "
            "comparisons, so they need no band here; their discrimination "
            "is the load-bearing negative-control mutant assertion. Master "
            "plan §7.1; Phase 7+ scope-extension §5.1 two-arm."
        ),
    },

    "p3_bocpd": {
        "type": "tiered_outputs",
        # n_cps / CP-index exact (integers).
        "primary": {
            "abs_tol": 0.0, "rel_tol": 0.0,
            "block_abs_tol": 1.0, "block_rel_tol": 0.5,
        },
        # Recursion SENTINEL: engine MAP run-length sequence (data-dependent,
        # integer) bit-exact vs the from-scratch reference -> confirms the
        # recursion is UNCHANGED + correct (the S79 fix touched only the
        # detection read-off, not the recursion).
        "map_rl": {
            "abs_tol": 0.5, "rel_tol": 0.0,
            "block_abs_tol": 0.5, "block_rel_tol": 0.0,
        },
        # cp_prob (6-dp emitted) — trivially the constant hazard, kept as a
        # secondary recursion check.
        "cp_prob": {
            "abs_tol": 1e-5, "rel_tol": 1e-3,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-2,
        },
        "justification": (
            "S79 engine-improvement #2 (MAP-run-length-reset detection fix). "
            "FUNCTIONAL DETECTION check, NOT self-parity-on-broken (the prior "
            "check was self-parity-COMPLICIT: the reference applied the same "
            "non-functional cp_prob>threshold criterion, so both returned "
            "n_cps=0 on a known change-point and the check PASSED with zero "
            "detections — the §5.1 founding case). Upgraded: (a) recursion "
            "SENTINEL — engine MAP run-length bit-exact vs the from-scratch "
            "reference (the recursion is unchanged); (b) criterion "
            "cross-validation — engine n_cps == reference n_cps, both via "
            "MAP-reset; (c) functional POSITIVE — fires within +/-15 of the "
            "true CP@150 (measured 153); (d) ★ functional NEGATIVE CONTROL — "
            "n_cps=0 on a no-change-point series (catches a fires-on-everything "
            "fix). The discrimination the self-parity check structurally lacked."
        ),
    },

    "p3_cusum_page_hinkley": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "Self-parity: TSL cusum_page_hinkley.py and reference "
            "(in p3_cusum_page_hinkley.py) implement identical "
            "deterministic recursive accumulators. Bit-exact match "
            "expected on n_cusum_up/down and n_ph_up/down counts. "
            "Pattern A target. R cpm/changepoint use different "
            "formulations (CPM tests; PELT-style cost functions); "
            "self-parity avoids Pattern J methodology zoo."
        ),
    },

    "p3_intervention_analysis": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-2,
            "block_rel_tol": 1e-1,
        },
        "secondary": {
            "abs_tol": 1e-2,
            "rel_tol": 5e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Intervention analysis = ARIMA + xreg dummy. TSL uses "
            "statsmodels SARIMAX with exog; R uses stats::arima "
            "with xreg. Both optimize the same Gaussian likelihood "
            "but with different optimizer convergence criteria "
            "(L-BFGS-B vs CSS-ML). Master plan §7.1 MLE-fit class: "
            "1e-3 abs / 1e-2 rel on Primary (ar1, omega, log-lik); "
            "1e-2 abs / 5e-2 rel on Secondary (sigma2, AIC) per "
            "§7.2 5-10× looser convention."
        ),
    },

    "p3_pelt": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "Same-library self-parity: TSL pelt_change_points.py "
            "and reference both invoke ruptures.Pelt with identical "
            "model='l2' / min_size=5 / jump=1 / pen=log(n)*sigma^2. "
            "Output is bitwise-identical given identical input. "
            "Pattern A bit-exact target on both n_change_points "
            "and the breakpoint position set. Failure indicates a "
            "TSL preprocessing or argument-passing bug, not a "
            "methodology question."
        ),
    },

    "p3_pelt_multivariate": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "ENG-EXT-CHANGEPOINT-001 A1a multivariate joint detection. "
            "Same-library self-parity (Pattern A.1): TSL "
            "pelt_change_points.py multivariate path and the reference "
            "both invoke ruptures.Pelt on the SAME (n,k) signal with "
            "model='l2' / min_size=5 / jump=1 / IDENTICAL numeric "
            "penalty (pen=log(n)*sum_j(var_j), the dimensionally-correct "
            "multivariate BIC). ruptures returns a single JOINT "
            "breakpoint set; output is bitwise-identical given identical "
            "input + arguments. Bit-exact target on n_change_points + "
            "the joint breakpoint position set. Failure indicates a TSL "
            "multivariate-stacking or penalty-convention bug, not a "
            "methodology question."
        ),
    },

    "p3_cusum_page_hinkley_multivariate": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "ENG-EXT-CHANGEPOINT-001 A1b multivariate joint CUSUM/"
            "Page-Hinkley. SELF-PARITY (no library for multivariate "
            "CUSUM): TSL's multivariate path (proper Crosier 1988 MCUSUM "
            "shrinking vector accumulator + joint Page-Hinkley, "
            "bootstrap-calibrated thresholds) vs a from-scratch "
            "reimplementation of the IDENTICAL formulation (same Σ via "
            "np.cov+pinv, same k_m allowance, same seeded permutation "
            "bootstrap null-max thresholds, same detection/reset, same "
            "NaN row-drop). Both deterministic given the seed -> "
            "bit-exact joint change-point set. Bit-exact target on "
            "n_change_points + the joint position set. Failure indicates "
            "a formulation/Σ/threshold/NaN convention divergence between "
            "the arms, not a methodology question."
        ),
    },

    "p3_bocpd_multivariate": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "ENG-EXT-CHANGEPOINT-001 A1c multivariate joint BOCPD. "
            "SELF-PARITY (no library for multivariate BOCPD): TSL's "
            "multivariate path (Adams-MacKay with a multivariate "
            "Normal-Inverse-Wishart conjugate -> multivariate-Student-t "
            "predictive, Cholesky-based, log-space; MAP-run-length-reset "
            "detection) vs a from-scratch reimplementation of the "
            "IDENTICAL formulation (same NIW hyperparams, rank-1 Ψ "
            "update, Cholesky logdet+solve, log-mv-t, recursion, "
            "MAP-reset detection). Both deterministic -> bit-exact joint "
            "change-point set on a NON-ZERO detection fixture (stronger "
            "than S79's bit-exact-on-empty). Failure indicates an "
            "NIW-hyperparameter / rank-1-update / Cholesky / log-mv-t / "
            "detection convention divergence between the arms, not a "
            "methodology question. (S79's univariate cp_prob criterion "
            "is non-functional [R[t+1,0]==hazard]; the multivariate path "
            "uses the correct MAP-reset signal — the S79 univariate-"
            "criterion bug is documented + banked separately.)"
        ),
    },

    "p3_stl_esd": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 2.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "Self-parity: both arms invoke statsmodels STL with "
            "identical config (period, seasonal_window, "
            "inner_iter=5, outer_iter=2, robust=True) producing "
            "bitwise-identical remainder. ESD test (Rosner 1983) "
            "is closed-form sequential test; reference implements "
            "identical recursion. Pattern A target on n_anomalies "
            "and anomaly-index set. Block band 2.0 absolute "
            "accommodates a 1-2 boundary index disagreement (last-"
            "rejection edge case in Rosner's sequential criterion) "
            "without escalating immediately to BLOCK; >2 mismatch "
            "= real bug. Pattern J avoidance: Twitter "
            "AnomalyDetection R archived; no CRAN successor."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 7 — Python spectral (Session 11).
    # First all-Python-reference batch; PyBridge primitives exercised
    # in-process (isolate=False default — no DL state to isolate).
    # FFT / periodogram / wavelets are closed-form numpy/scipy
    # operations; Pattern A bit-exact target. Lomb-Scargle is Pattern J
    # (scipy vs astropy normalization conventions). EMD/HHT is Tier C
    # NO-REFERENCE (different sifting libraries).
    # ------------------------------------------------------------------

    "p3_fft_spectrum": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "FFT is closed-form linear-algebra. scipy.fft and "
            "numpy.fft both wrap pocketfft (since numpy 1.17); "
            "given identical real-valued input, output is "
            "bit-identical at machine precision. 1e-10 floor "
            "leaves headroom for any future BLAS-implementation "
            "drift. Master plan section 7.1 closed-form class."
        ),
    },

    "p3_periodogram": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "scipy.signal.periodogram is deterministic; both "
            "arms invoke the same scipy primitive with identical "
            "(window, detrend, fs, scaling) arguments. Same-"
            "library self-test verifies wrapper preprocessing + "
            "parameter resolution round-trip the reference "
            "output without wrapper-introduced bugs. Pattern A "
            "bit-exact target."
        ),
    },

    "p3_lomb_scargle": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "Pattern J: scipy.signal.lombscargle and "
            "astropy.timeseries.LombScargle use DIFFERENT "
            "normalization conventions; absolute power values "
            "differ expectedly. Comparison aligned by peak-"
            "frequency LOCATION (normalization-invariant) "
            "against the same frequency grid. Bit-exact "
            "expected on the peak-bin index. Master plan "
            "section 7.1 with Pattern J alignment via metric "
            "selection."
        ),
    },

    "p3_wavelet_transform": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Same-library self-test: TSL and reference both "
            "invoke pywt.wavedec with identical wavelet (db4), "
            "level (4), and mode (symmetric). DWT is "
            "deterministic; bit-exact parity at machine "
            "precision. Pattern A target. Pattern F invariants "
            "(roundtrip + energy conservation) populated and "
            "verified inline."
        ),
    },

    "p3_wavelet_coherence": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Self-parity: both arms invoke pywt.cwt with "
            "identical wavelet (morl) + identical scipy "
            "smoothing kernel. Coherence is closed-form ratio "
            "of smoothed spectra; bit-exact expected. R "
            "biwavelet uses Liu-Liang-Weisberg 2007 estimator "
            "+ Monte Carlo significance - different "
            "methodology, not directly comparable. Self-parity "
            "catches TSL preprocessing / smoothing-application "
            "regressions."
        ),
    },

    "p3_emd_hht": {
        "type": "tiered_outputs",
        "primary": {
            "corr_pass": 0.85,
            "corr_caveat": 0.6,
            "abs_tol": 1.0,
            "rel_tol": 1.0,
            "block_abs_tol": 5.0,
            "block_rel_tol": 5.0,
        },
        "justification": (
            "Tier C NO-REFERENCE-class: TSL emd (AOE Quinn) / "
            "numpy fallback and PyEMD (Laszuk) are independent "
            "implementations of Huang 1998 sifting; per-IMF "
            "bitwise parity is mathematically intractable. "
            "Comparison via reconstruction identity (machine "
            "precision on both sides), IMF count agreement "
            "(within +/-1), and cumulative-energy-curve Pearson "
            "correlation (>= 0.85 PASS; 0.6-0.85 CAVEAT). "
            "Pattern K-style correlation-based check."
        ),
    },

    "p3_ssa": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "SSA is closed-form: SVD of Hankel trajectory "
            "matrix. Both TSL and reference call numpy.linalg."
            "svd on identical Hankel construction; eigenvalues "
            "are unique (sign-invariant) and singular vectors "
            "agree after sign-canonicalization. Pattern A "
            "bit-exact target at machine precision."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 8 — Python ML (Session 12).
    # All same-library self-tests against sklearn / xgboost / lightgbm.
    # Pattern A bit-exact target on all 7 wrappers (same library means
    # no optimizer divergence; deterministic given seed pinning).
    # robust_estimators uses R robustbase as cross-package reference;
    # closed-form arithmetic at machine precision modulo CSV roundtrip.
    # ------------------------------------------------------------------

    "p3_random_forest": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "sklearn.ensemble.RandomForestRegressor with "
            "identical hyperparameters and random_state. "
            "RF is deterministic given seed pinning; bit-exact "
            "predictions + feature importances expected."
        ),
    },

    "p3_gradient_boosting": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "sklearn.ensemble.GradientBoostingRegressor with "
            "identical hyperparameters and random_state. "
            "Deterministic; bit-exact expected."
        ),
    },

    "p3_xgboost": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "xgboost.XGBRegressor with identical hyperparameters, "
            "tree_method='hist' pinned for reproducibility, "
            "n_jobs=1 for thread determinism. 1e-10 floor "
            "leaves headroom for any internal float32 "
            "intermediate-state drift between identical runs."
        ),
    },

    "p3_lightgbm": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "lightgbm.LGBMRegressor with deterministic=True + "
            "force_col_wise=True + n_jobs=1 pinned. Bit-exact "
            "predictions expected. 1e-10 floor leaves headroom "
            "for float32 internal state drift."
        ),
    },

    "p3_svr": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "sklearn.svm.SVR with identical (kernel, C, epsilon, "
            "gamma). libsvm SMO optimizer is deterministic from "
            "fixed initialization (no random state); bit-exact "
            "predictions + n_support + intercept expected."
        ),
    },

    "p3_quantile_regression": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Same-library: TSL and reference both invoke "
            "sklearn.ensemble.GradientBoostingRegressor with "
            "loss='quantile' and pinned random_state per "
            "quantile level. Deterministic; bit-exact "
            "predictions expected per quantile."
        ),
    },

    "p3_robust_estimators": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Trimmed mean, winsorized mean, MAD, and Qn are "
            "closed-form arithmetic. scipy.stats and R "
            "stats::mad / robustbase::Qn implement identical "
            "formulae with identical consistency factors "
            "(1.4826 / 2.2219). Bit-exact at machine precision "
            "modulo subprocess CSV roundtrip noise. R Qn pinned "
            "with finite.corr=FALSE for asymptotic-factor-only "
            "match (matches scipy/numpy convention)."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 9 — Python DL (Session 13).
    # Most variance-prone batch; pre-budgeted >=30% Tier C per master
    # plan section 17.1 risk 2. PyTorch wrappers use seed-pinning +
    # cuDNN deterministic flag for in-process determinism. Same-library
    # self-parity for all DL wrappers (TSL uses direct torch.nn, not
    # neuralforecast which is unusable on Python 3.14).
    # ------------------------------------------------------------------

    "p3_lstm_gru": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-5,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "PyTorch nn.LSTM with all seeds pinned (torch + numpy "
            "+ random) and cuDNN deterministic=True is "
            "reproducible at machine precision modulo float32 "
            "accumulation drift. 1e-6 abs floor accommodates "
            "any internal float32 / float64 mixed-precision "
            "intermediate-state drift; same-library self-test."
        ),
    },

    "p3_tcn": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-5,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "PyTorch nn.Conv1d TCN with seed pinning + cuDNN "
            "deterministic. Same-library self-test; 1e-6 abs "
            "floor for float32 accumulation drift."
        ),
    },

    "p3_nbeats": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-5,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "Custom PyTorch NBEATS with seed pinning. Same-"
            "library self-test; neuralforecast (Nixtla) ruled "
            "out due to Python 3.14 incompatibility."
        ),
    },

    "p3_nhits": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-5,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "Custom PyTorch NHITS (NBEATS variant with multi-rate "
            "hierarchical sampling). Seed-pinned same-library "
            "self-test."
        ),
    },

    "p3_autoencoder": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-5,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "PyTorch encoder-decoder MLP with seed pinning + "
            "cuDNN deterministic. Same-library self-test on "
            "reconstruction errors."
        ),
    },

    "p3_esn": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "reservoirpy with set_seed pinned: reservoir-matrix "
            "initialization + ridge-regression solve are both "
            "deterministic. Pattern A.1 same-library bit-exact "
            "target at machine precision."
        ),
    },

    "p3_gp": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-8,
            "rel_tol": 1e-8,
            "block_abs_tol": 1e-4,
            "block_rel_tol": 1e-4,
        },
        "justification": (
            "sklearn.gaussian_process.GaussianProcessRegressor "
            "with random_state pinned: L-BFGS-B hyperparameter "
            "optimization is deterministic given fixed seed + "
            "fixed n_restarts_optimizer. Pattern A same-library "
            "bit-exact target. (TSL uses sklearn, NOT GPyTorch "
            "as named in master plan section 15.11.)"
        ),
    },

    "p3_prophet": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "justification": (
            "Prophet's Stan backend (cmdstanpy) is deterministic "
            "in MAP mode (uncertainty_samples=0) but L-BFGS-B "
            "convergence-criterion variation can produce ~1e-4 "
            "abs drift in fitted yhat / trend. Same-library "
            "self-test; 1e-3 abs / 1e-2 rel band accommodates "
            "Stan optimizer convergence differences across "
            "identical-input runs."
        ),
    },

    "p3_conformal": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Split-conformal prediction is closed-form: quantile "
            "of calibration absolute residuals. Both arms compute "
            "identical quantile on identical residuals; bit-exact "
            "qhat + lower/upper arrays expected. Pattern A self-"
            "parity. Pattern F invariant conformal_nominal_coverage "
            "verifies Vovk 2005 finite-sample coverage guarantee."
        ),
    },

    # ------------------------------------------------------------------
    # Phase 3 Batch 10 — misc + Tier C (Session 14, FINAL BATCH).
    # 11 wrappers spanning closed-form OLS / FFT / DTW / bootstrap /
    # disaggregation / LOESS / X-13. Mostly Pattern A bit-exact +
    # one Tier C (X-13 SKIP-graceful).
    # ------------------------------------------------------------------

    "p3_granger": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-6,
            "rel_tol": 1e-4,
            "block_abs_tol": 1e-3,
            "block_rel_tol": 1e-2,
        },
        "justification": (
            "Granger F-test is closed-form OLS-on-nested-models. "
            "statsmodels and R lmtest::grangertest implement "
            "identical procedure; sub-1e-6 abs expected modulo "
            "subprocess CSV roundtrip noise."
        ),
    },

    "p3_ccf": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Cross-correlation function is closed-form Pearson "
            "correlation across lags. Both implementations compute "
            "identical normalized cross-covariance values. Pattern "
            "A bit-exact target."
        ),
    },

    "p3_ccf_family": {
        "type": "tiered_outputs",
        # Scope-extension UNIT 3: validates the ENGINE custom-numpy CCF
        # (cross_correlation_lag / prewhitened / rolling) vs R stats::ccf —
        # additive over p3_ccf (which validates statsmodels, NOT the engine).
        # ccf_vector: engine emitted CCF table is 6-dp rounded, so bit-exact
        # is bounded by the emitted precision (~5e-7); abs 1e-6 / block 1e-4.
        "ccf_vector": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-2,
        },
        # reduction: rolling per-window CCF comes from the 4-dp heatmap; the
        # rolling@first-window vs static-on-same-slice consistency is bounded
        # by that precision; abs 2e-4 / block 1e-3.
        "reduction": {
            "abs_tol": 2e-4, "rel_tol": 1e-2,
            "block_abs_tol": 1e-3, "block_rel_tol": 1e-1,
        },
        "justification": (
            "Engine CCF is closed-form Pearson cross-correlation. The "
            "cross_correlation arm validates the engine's emitted CCF vector "
            "vs R stats::ccf at the emitted 6-dp precision (sign-flip lag "
            "alignment); 5e-7 measured. The reduction arm checks rolling's "
            "INDEPENDENT windowing CCF (4-dp heatmap) against the static "
            "engine CCF on the same slice. The whiteness, optimal-lag, and "
            "discrimination sub-arms are PASS/BLOCK gates (Ljung-Box min-p vs "
            "0.05; argmax equality), not numeric bands. Phase 7+ "
            "scope-extension B.i + defining-invariant (third case)."
        ),
    },

    "p3_gcc_phat": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "GCC-PHAT delay is integer-valued (argmax of cross-"
            "correlation peak). Self-parity reference; bit-exact "
            "delay match expected. Block band 1.0 absolute "
            "accommodates a potential boundary-tie-break ±1 sample "
            "without escalating to BLOCK."
        ),
    },

    "p3_dtw": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "DTW is closed-form dynamic programming. Numpy "
            "reference and dtaidistance C-implementation produce "
            "identical distances modulo float-precision drift; "
            "1e-10 abs floor for safety."
        ),
    },

    "p3_dtw_crosspkg": {
        "type": "tiered_outputs",
        # Scope-extension UNIT 5: ENGINE-invoked DTW distance vs the
        # independent dtaidistance library (the FIRST engine-in-the-loop
        # cross-package distance evidence; corrects the prior degenerate/
        # superseded "cross-package Layer 1" claim). The engine emits the
        # distance at 4-dp, so the match is bounded by that precision;
        # measured 3.87e-05. abs 1e-4 / block 1e-2 per the 4-dp granularity.
        "primary": {
            "abs_tol": 1e-4, "rel_tol": 1e-3,
            "block_abs_tol": 1e-2, "block_rel_tol": 1e-1,
        },
        "justification": (
            "Engine hand-rolled _dtw (squared-euclidean cost + min(diag,ins,"
            "del) + sqrt + Sakoe-Chiba window) == dtaidistance standard DTW "
            "given matched z-normalization + window; measured bit-exact at the "
            "engine's 4-dp emitted precision (3.87e-05). The z-norm negative "
            "control (raw series) diverges by 1.18 (discrimination, gated in "
            "compare). Phase 7+ scope-extension B.i; third case rejected "
            "(denton boundary — full cross-package reference covers the path)."
        ),
    },

    "p3_transfer_function": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Distributed-lag OLS is closed-form normal-equations "
            "solve. Self-parity reference; bit-exact betas + SSE."
        ),
    },

    "p3_block_bootstrap": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-10,
            "rel_tol": 1e-10,
            "block_abs_tol": 1e-6,
            "block_rel_tol": 1e-6,
        },
        "justification": (
            "Block bootstrap with pinned numpy.random.default_rng "
            "seed is fully deterministic. Self-parity reference; "
            "bit-exact moments expected."
        ),
    },

    "p3_forecast_combination": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Inverse-MSE weighted combination is closed-form "
            "weighted mean. Self-parity bit-exact target."
        ),
    },

    "p3_rolling_origin_cv": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "Rolling-origin CV with naive last-value forecaster "
            "is deterministic loop. Self-parity bit-exact target."
        ),
    },

    "p3_denton_chowlin": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1.0,
            "block_rel_tol": 1e-1,
        },
        "justification": (
            "Denton-Cholette / Chow-Lin disaggregation is closed-"
            "form quadratic optimization. TSL solves via numpy "
            "block-elimination of the KKT system; R tempdisagg::td "
            "uses GLS-equivalent reformulation. Numerical "
            "linear-algebra paths differ slightly; 1e-3 abs band "
            "accommodates conditioning-related drift."
        ),
    },

    "p3_denton_chowlin_methods": {
        "type": "tiered_outputs",
        # Scope-extension UNIT 4: ENGINE-invoked per-method validation
        # (Denton + Chow-Lin) vs tempdisagg, additive over p3_denton_chowlin
        # (which mirrors only Denton, never invokes the engine). Both arms
        # measured bit-exact at the engine's 6-dp emitted precision (Denton
        # 6.8e-07; Chow-Lin chow-lin-fixed at pinned rho + matched design
        # 5.0e-07 — the 1/(1-rho^2) AR(1) scaling cancels in the BLUE
        # distribution). abs 1e-6 / block 1e-4 per the 6-dp granularity.
        "denton": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-2,
        },
        "chowlin": {
            "abs_tol": 1e-6, "rel_tol": 1e-4,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-2,
        },
        # Chow-Lin rho-AUTO: post the continuous-optimizer engine fix
        # (banked-ledger item #1), the engine's auto-rho now reproduces
        # tempdisagg chow-lin-maxlog. Underlying rho match 1.3e-7; the ENGINE
        # EMITS rho rounded to 4-dp (engine line 363) so the rho-arm gap is
        # rounding-dominated (~1.1e-5, floor ~5e-5) -> rho_abs_tol 1e-4 (2x the
        # 4-dp floor; catches the prior 0.14 grid-regression by >1000x). The
        # SERIES arm carries the full-precision cross-package evidence (auto
        # series vs tempdisagg cl_maxlog_series, measured 5.1e-07 at the 6-dp
        # emitted precision).
        "chowlin_auto": {
            "abs_tol": 1e-5, "rel_tol": 1e-4,
            "block_abs_tol": 1e-4, "block_rel_tol": 1e-2,
            "rho_abs_tol": 1e-4,
        },
        "justification": (
            "Engine Denton (denton-cholette) and Chow-Lin (chow-lin-fixed at "
            "a pinned rho, [intercept+trend+indicator] design, conversion=sum) "
            "match tempdisagg::td bit-exact at the 6-dp emitted precision "
            "(measured 6.8e-07 / 5.0e-07). ★ Chow-Lin rho-AUTO is now a GATED "
            "cross-package arm (was a disclosure): post the continuous-optimizer "
            "engine fix, the engine's auto-rho reproduces tempdisagg "
            "chow-lin-maxlog (measured rho gap 1.3e-7) and the auto series "
            "matches cross-package (~1e-6); the prior grid landed 0.14 off (an "
            "objective mismatch, now fixed). Adding-up is structurally "
            "guaranteed (tautological, no arm). Phase 7+ pure-B.i + "
            "engine-improvement #1."
        ),
    },

    "p3_loess": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-12,
            "rel_tol": 1e-12,
            "block_abs_tol": 1e-8,
            "block_rel_tol": 1e-8,
        },
        "justification": (
            "statsmodels.nonparametric.lowess is deterministic "
            "given identical inputs + frac. Same-library self-"
            "test."
        ),
    },

    "p3_x13": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-3,
            "rel_tol": 1e-2,
            "block_abs_tol": 1e-1,
            "block_rel_tol": 1e-1,
        },
        "justification": (
            "X-13ARIMA-SEATS binary called by both arms. Tier C / "
            "SKIP-graceful: when R seasonal package or X-13 binary "
            "is unavailable, harness translates to SKIP outcome. "
            "When both available, output is deterministic; 1e-3 "
            "abs accommodates statsmodels.tsa.x13 vs R seasonal "
            "wrapper preprocessing differences."
        ),
    },

    # ------------------------------------------------------------------
    # Bond Yield Forecast (BYF integration Session 4)
    # ------------------------------------------------------------------

    "p3_bond_yield_forecast": {
        "type": "tiered_outputs",
        "primary": {
            # Pattern A.1 self-parity: bit-exact reproducibility (numpy
            # + numba random state is fully deterministic given pinned
            # seed). Tolerance band is machine-epsilon ceiling, not
            # mcmc-class default — the audit's reproducibility check
            # is much stricter than typical mcmc inter-implementation
            # comparison.
            "abs_tol": 1e-15,
            "rel_tol": 1e-15,
            "block_abs_tol": 1e-10,
            "block_rel_tol": 1e-10,
        },
        "secondary": {
            # Reserved for future Pattern A.3 paper-formula reimpl
            # comparison if/when budget allows. Currently unused.
            "abs_tol": 5e-3,
            "rel_tol": 5e-2,
            "block_abs_tol": 5e-2,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "Bond Yield Forecast (BVAR-SV per CCM-2019). Master plan "
            "§7.1 mcmc class default is 5e-3 abs / 5e-2 rel. The "
            "audit at p3_bond_yield_forecast.py uses Pattern A.1 "
            "self-parity (run TSL twice with same seed; assert byte-"
            "identical) instead of cross-implementation parity, "
            "because R bvars (Krueger; the plan §4.1 primary Pattern "
            "A.2 candidate) is not available for R 4.5.3 and a from-"
            "scratch Pattern A.3 reimpl is out of session-LOC budget. "
            "The strict abs_tol=1e-15 reflects what's achievable at "
            "the same-implementation reproducibility level — anything "
            "looser would mask seed-pinning or numba-cache bugs. "
            "Pattern F structural invariants (VAR companion eig < 1; "
            "SV |phi| < 1; PCA roundtrip residual; coef finiteness) "
            "are checked in compare() at property level (no tolerance "
            "band; PASS = property holds, BLOCK = violated). See "
            "tools/reference_parity/reports/p3_bond_yield_forecast_audit.md "
            "for full audit protocol + verdict."
        ),
    },
    # Phase 4 Session 4 (BYF v1.2.0 candidate #2 closure, 2026-05-01).
    # Pattern A.3 self-parity reimpl: Minnesota dummy-observation
    # construction is closed-form matrix arithmetic over the
    # hyperparameter set (lambda_1/3/4/sc/io, sigma, y_bar,
    # persistence). Same configuration must produce element-wise
    # identical (Y_d, X_d) arrays across implementations; bit-exact
    # tolerance applies. The reference is a from-scratch reimpl per
    # Doan-Litterman-Sims 1984 §3 + Sims-Zha 1998 extensions.
    "p3_byf_minnesota_dummies": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 1e-15,
            "rel_tol": 1e-15,
            "block_abs_tol": 1e-12,
            "block_rel_tol": 1e-12,
        },
        "justification": (
            "closed_form Pattern A.3 self-parity reimpl. Both "
            "implementations execute the same closed-form arithmetic "
            "on identical hyperparameter inputs, so bit-exact "
            "machine-precision agreement is the appropriate verdict "
            "band. Any divergence above 1e-15 surfaces a wrapper bug "
            "in the prior construction (Block A coefficients, "
            "Block B covariance, Block C intercept, Block D "
            "sum-of-coefficients, Block E initial-observation). "
            "See tools/reference_parity/harness/checks/"
            "p3_byf_minnesota_dummies.py for the full per-block "
            "formula trace."
        ),
    },
    # Phase 4 Session 6 (BYF v1.2.0 candidate #3 closure, 2026-05-02).
    # Pattern A.2 partial-component: TSL BVAR-SV per-equation log-
    # volatility posterior vs R stochvol::svsample on OLS-VAR
    # residuals. Per-parameter tolerance bands per BYF Phase 1 2b
    # audit precedent. Note: this ladder uses per-parameter rel
    # tolerances (mu_rel_tol / phi_rel_tol) rather than the standard
    # abs/rel pair; the comparison harness consumes them via
    # ladder["primary"]["mu_rel_tol"] etc.
    "p3_byf_stochvol_partial": {
        "type": "tiered_per_parameter",
        "primary": {
            "mu_rel_tol": 5e-2,
            "phi_rel_tol": 1e-1,
            # sigma is record-only per BYF Phase 1 2b precedent
            # (prior-divergence-driven; TSL Minnesota-prior-derived
            # omega prior vs stochvol IG-prior sigma)
        },
        "justification": (
            "mcmc Pattern A.2 partial-component cross-package. TSL "
            "BVAR-SV's per-equation log-volatility posterior (mu, "
            "phi, omega) vs R stochvol::svsample's per-series SV "
            "posterior on OLS-VAR residuals. The per-parameter "
            "tolerance band (5% mu / 10% phi / record-only sigma) "
            "is the canonical BYF Phase 1 2b audit precedent; "
            "absorbs methodology-equivalent divergences (residual-"
            "source asymmetry + sampler-framework gaps + prior-"
            "derivation gaps for sigma). Per master plan §11.9 + "
            "S6 trigger: any tolerance-band exceedance reclassifies "
            "as DOCUMENTED-DIVERGENCE (parallel to S5 disposition); "
            "the audit script's compare() handles this wiring."
        ),
    },
    # Phase 4 Session 5 (BYF v1.2.0 candidate #1 closure, 2026-05-02).
    # Pattern A.2 cross-package: TSL BVAR-SV with force_constant_h=True
    # vs R BVAR::bvar() (Kuschnig & Vashold 2021, JSS) at hyperprior-
    # pinned Minnesota config. Posterior-mean B comparison at MCMC band.
    "p3_byf_bvar_constant_vol": {
        "type": "tiered_outputs",
        "primary": {
            "abs_tol": 5e-3,
            "rel_tol": 5e-2,
            "block_abs_tol": 5e-2,
            "block_rel_tol": 5e-1,
        },
        "justification": (
            "mcmc Pattern A.2 cross-package. Two independent Bayesian "
            "VAR samplers (TSL CCM-2019 BVAR-SV with force_constant_h "
            "constant-vol toggle; R BVAR GLP-2015 hierarchical) on "
            "identical synthetic VAR(p) data with hyperparameters "
            "aligned via near-point-mass collapse of R BVAR's "
            "hyperpriors at TSL's fixed lambda values. The 5e-3 abs / "
            "5e-2 rel band absorbs methodology-equivalent divergences "
            "(sampler differences; hyperprior-vs-fixed framework "
            "differences even after point-mass collapse) while "
            "surfacing wrapper-level bugs above 5% relative. Per "
            "master plan §11.9: any divergence outside this band on "
            "Minnesota-prior coefficient posteriors must escalate to "
            "Chat for investigation."
        ),
    },
}


def get_ladder(technique_id: str) -> dict[str, Any]:
    """Look up the tolerance ladder for a technique id.

    Raises
    ------
    KeyError
        If no ladder is registered for the given id. Adding a
        new ParityCheck without a corresponding ladder entry is
        a contributor-guide violation — fail loudly.
    """
    if technique_id not in TOLERANCE_LADDERS:
        raise KeyError(
            f"No tolerance ladder registered for technique_id "
            f"'{technique_id}'. Add an entry to "
            f"reference_parity/harness/tolerances.py with a "
            f"justification citing the Phase 1 audit report."
        )
    return TOLERANCE_LADDERS[technique_id]


__all__ = ["TOLERANCE_LADDERS", "get_ladder"]
