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
            # ETS state-space representation in R `forecast::ets`
            # vs Holt-Winters smoothing recursion in statsmodels
            # `ExponentialSmoothing`. Mathematically equivalent for
            # deterministic-state case but optimizers (R's BFGS on
            # likelihood vs statsmodels' L-BFGS-B on SSE) converge
            # to numerically nearby smoothing parameters with
            # tolerance-class divergence in the 1e-2 range.
            "abs_tol": 5e-2,
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
            "Master plan §7.1 MLE-fit band, widened from the strict "
            "1e-3 / 1e-2 baseline because R `forecast::ets` and "
            "statsmodels `ExponentialSmoothing` parameterize the "
            "state-space form differently (state-space innovation "
            "vs SSE-minimizing classical recursion). Hyndman-Khandakar "
            "2008 §6.4 documents the equivalence is mathematical, "
            "not implementational. Smoothing-parameter tolerance "
            "5e-2 absolute / 1e-1 relative; AIC tolerance 5.0 abs "
            "(state-space likelihood vs SSE-based AIC differ by an "
            "additive constant of -n*log(2*pi)/2 in the standard "
            "form). DOCUMENTED-DIVERGENCE candidate if observed "
            "divergence exceeds these widened thresholds; CAVEAT if "
            "in the block band; PASS otherwise."
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

    "p3_bocpd": {
        "type": "tiered_outputs",
        "primary": {
            # Self-parity: TSL and reference both implement
            # Adams-MacKay 2007 verbatim with NIG conjugate prior.
            # n_cps and CP-index set must match exactly. Setting
            # abs_tol=0 forces strict equality on integer counts.
            "abs_tol": 0.0,
            "rel_tol": 0.0,
            "block_abs_tol": 1.0,
            "block_rel_tol": 0.5,
        },
        "justification": (
            "Self-parity: TSL bocpd.py and from-scratch reference "
            "(in p3_bocpd.py) implement identical Adams-MacKay 2007 "
            "recursion with NIG conjugate prior. Bit-exact match "
            "expected on both n_change_points and the change-point "
            "index set. Pattern A target. PyPI bocd uses non-"
            "conjugate Gaussian prior and would not produce a "
            "matching reference; self-parity is the only path to "
            "PASS. Block band at abs_tol=1 (±1 CP off) → BLOCK."
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
