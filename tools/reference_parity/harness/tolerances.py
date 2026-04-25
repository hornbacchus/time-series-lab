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
