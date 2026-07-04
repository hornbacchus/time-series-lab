"""
Johansen Cointegration Test for Time Series Lab.

Tests for the number of cointegrating relations among 2+ I(1) time series
using the Johansen trace and maximum eigenvalue statistics.

Follow-up 3d: opt-in `finite_sample_correction=True` applies the
Reimers (1992) modified likelihood-ratio correction — a Bartlett-type
finite-sample adjustment widely used in VECM practice (R urca
``ca.jo(..., small_sample=TRUE)``, Stata vecrank). The correction
factor is

    B(T, n, p, d) = (T − n*p − d(det_order)) / T

where T is sample size, n is VAR dimension, p is VECM lag order
(k_ar_diff), and d ∈ {0, 1, 2} is the number of deterministic
regressors implied by det_order ∈ {−1, 0, 1}. Corrected statistics
are Q_corrected = B * Q_asymptotic. Comparison against statsmodels's
existing MacKinnon asymptotic critical values is arithmetically
equivalent to comparing uncorrected statistics against MHM 1999
response-surface CVs at the decision level.

References
----------
Johansen 1988 / 1991 (trace + maximum eigenvalue tests); Reimers 1992
(small-sample correction); MacKinnon-Haug-Michelis 1999 (response-
surface CVs); Johansen 2002 (refined higher-order corrections, not
implemented here). Reference parity check: R `urca::ca.jo` with
`small_sample=TRUE` (Phase 1 audit 3d).

Audit fields (S8 P4-1.2 alias additions)
----------------------------------------
- ``trace_rank`` (legacy name; retained for backward compat).
- ``determined_rank_trace``: alias of trace_rank per master plan
  §15 S8 naming convention.
- ``cointegrating_rank``: alias of trace_rank; matches the registry
  checker contract (P-2 §D.1 ``vecm_cointegration_rank``). All three
  hold the same integer value; the multi-name surface bridges naming
  conventions across consumer code.
"""

import logging
import numpy as np
import warnings as _warnings
import pandas as pd
from statsmodels.tsa.vector_ar.vecm import coint_johansen, select_order

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)


# Deterministic-regressor count per statsmodels det_order convention.
# det_order = -1: no deterministic → d = 0
# det_order =  0: unrestricted constant → d = 1
# det_order =  1: unrestricted linear trend → d = 2
_DET_ORDER_D = {-1: 0, 0: 1, 1: 2}


def _bartlett_factor(T: int, n: int, p: int, det_order: int) -> float | None:
    """Reimers (1992) modified likelihood-ratio Bartlett-type factor.

    Follow-up 3d finite-sample correction. The same factor applies to
    both trace and maximum-eigenvalue statistics.

    Parameters
    ----------
    T : int
        Sample size (observations) after data cleaning.
    n : int
        VAR dimension (number of series).
    p : int
        VECM lag order (k_ar_diff).
    det_order : int
        statsmodels deterministic order ∈ {-1, 0, 1}.

    Returns
    -------
    float or None
        B ∈ (0, 1] with Q_corrected = B * Q_asymptotic. Returns None on
        degenerate inputs (non-positive T, uncovered det_order, or
        degrees-of-freedom exhaustion).
    """
    try:
        T_i = int(T)
        n_i = int(n)
        p_i = int(p)
        d = _DET_ORDER_D.get(int(det_order))
    except Exception:
        return None
    if d is None:
        return None
    if T_i <= 0 or n_i <= 0 or p_i < 0:
        return None
    # Degrees-of-freedom consumed by the VECM fit.
    dof_consumed = n_i * p_i + d
    numerator = T_i - dof_consumed
    if numerator <= 0:
        # Degrees-of-freedom exhausted — correction is degenerate.
        return None
    B = numerator / float(T_i)
    # Guard: clamp to (0, 1]. The Reimers formula naturally produces
    # values in this range for reasonable T, n, p.
    return max(1e-6, min(B, 1.0))


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run the Johansen cointegration test on 2+ series.

    Parameters (via ctx.params)
    ---------------------------
    lag : int, optional
        Number of lagged differences (k_ar_diff). If omitted, auto-selected.
        Also sourced from the `k_ar_diff` dialog control: the string "auto"
        (its default) -> IC-selection (== omitting it); an int -> a pinned lag.
    max_lag : int, optional
        Maximum lag for automatic selection. Default depends on preset.
    det_order : int, optional
        Deterministic term: -1 (no deterministic), 0 (constant in coint eq),
        1 (linear trend in coint eq). Default 0.
    significance_level : float, optional
        Threshold for rank determination. Default 0.05.
    """
    try:
        progress_callback("Validating inputs", 5)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        k = len(names)
        warn_list = []

        # Build aligned data matrix
        arrays = [vals for _, vals in all_series]
        lengths = [len(a) for a in arrays]
        if len(set(lengths)) > 1:
            min_len = min(lengths)
            arrays = [a[:min_len] for a in arrays]
            warn_list.append(f"Series truncated to shortest length ({min_len}).")

        stacked = np.column_stack(arrays)

        # Interpolate NaN
        for col in range(k):
            nan_idx = np.where(np.isnan(stacked[:, col]))[0]
            valid_idx = np.where(~np.isnan(stacked[:, col]))[0]
            if len(nan_idx) > 0 and len(valid_idx) >= 2:
                stacked[nan_idx, col] = np.interp(nan_idx, valid_idx, stacked[valid_idx, col])
                warn_list.append(f"'{names[col]}': {len(nan_idx)} NaN values interpolated.")

        mask = np.all(~np.isnan(stacked), axis=1)
        stacked = stacked[mask]
        n = stacked.shape[0]

        if n < 3 * k + 10:
            return make_error_response(
                ctx,
                f"Too few observations ({n}) for Johansen test with {k} variables.",
                error_fixes=["Provide longer series."],
            )

        det_order = int(ctx.get_param("det_order", 0))
        significance = ctx.get_param("significance_level", 0.05)

        # Lag selection
        progress_callback("Selecting lag order", 15)

        preset_max = {"Fast": 4, "Balanced": 8, "Thorough": 12}
        max_lag = int(ctx.get_param("max_lag", preset_max.get(ctx.preset, 8)))
        max_lag = min(max_lag, n // (2 * k) - 1, n // 4)
        max_lag = max(max_lag, 1)

        # lag (the VECM diff-lag order, == statsmodels k_ar_diff) sourced from
        # the `k_ar_diff` dialog control; precedence lag (THOROUGH) > k_ar_diff
        # (dialog) > None. The dialog default is the STRING "auto" -- a SENTINEL
        # for IC-selection (the delivered behavior); branch it here, never
        # int-cast it. An int (or int-string) pins the lag.
        fixed_lag = ctx.get_param("lag", ctx.get_param("k_ar_diff"))
        if isinstance(fixed_lag, str):
            _fl = fixed_lag.strip().lower()
            if _fl in ("", "auto", "none"):
                fixed_lag = None
            else:
                try:
                    fixed_lag = int(_fl)
                except ValueError:
                    return make_error_response(
                        ctx,
                        f"k_ar_diff must be 'auto' or an integer, got "
                        f"'{fixed_lag}'.",
                        error_fixes=[
                            "Use 'auto' (IC-selected lag order) or a positive "
                            "integer number of lagged differences.",
                        ],
                    )
        if fixed_lag is not None:
            p = int(fixed_lag)
        else:
            df = pd.DataFrame(stacked, columns=names)
            with _warnings.catch_warnings():
                _warnings.simplefilter("ignore")
                try:
                    det_map = {-1: "n", 0: "ci", 1: "li"}
                    order_result = select_order(df, maxlags=max_lag, deterministic=det_map.get(det_order, "ci"))
                    p = order_result.aic
                    if p == 0:
                        p = 1
                except Exception:
                    p = min(2, max_lag)
                    warn_list.append(f"Automatic lag selection failed. Using p={p}.")

        progress_callback("Running Johansen test", 30)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            result = coint_johansen(stacked, det_order=det_order, k_ar_diff=p)

        progress_callback("Building output", 65)

        # Trace test results
        trace_stats = result.lr1       # trace statistics
        trace_cvs = result.cvt         # critical values: columns = 90%, 95%, 99%
        trace_rows = []
        determined_rank_trace = 0

        cv_labels = ["90%", "95%", "99%"]
        # Determine significance column index based on significance_level
        if significance <= 0.01:
            sig_col = 2  # 99%
        elif significance <= 0.05:
            sig_col = 1  # 95%
        else:
            sig_col = 0  # 90%

        for i in range(k):
            h0 = f"r <= {i}"
            stat = float(trace_stats[i])
            cv90 = float(trace_cvs[i, 0])
            cv95 = float(trace_cvs[i, 1])
            cv99 = float(trace_cvs[i, 2])
            reject = stat > trace_cvs[i, sig_col]
            if reject and i >= determined_rank_trace:
                determined_rank_trace = i + 1
            trace_rows.append([
                h0, round(stat, 4), round(cv90, 4), round(cv95, 4), round(cv99, 4),
                "Reject" if reject else "Fail to Reject"
            ])

        trace_table = make_table(
            "Trace Test",
            ["H0", "Trace Stat", "CV 90%", "CV 95%", "CV 99%", "Decision"],
            trace_rows,
        )

        # Max Eigenvalue test results
        max_eig_stats = result.lr2
        max_eig_cvs = result.cvm
        eig_rows = []
        determined_rank_eig = 0

        for i in range(k):
            h0 = f"r <= {i}"
            stat = float(max_eig_stats[i])
            cv90 = float(max_eig_cvs[i, 0])
            cv95 = float(max_eig_cvs[i, 1])
            cv99 = float(max_eig_cvs[i, 2])
            reject = stat > max_eig_cvs[i, sig_col]
            if reject and i >= determined_rank_eig:
                determined_rank_eig = i + 1
            eig_rows.append([
                h0, round(stat, 4), round(cv90, 4), round(cv95, 4), round(cv99, 4),
                "Reject" if reject else "Fail to Reject"
            ])

        eig_table = make_table(
            "Maximum Eigenvalue Test",
            ["H0", "Max Eig Stat", "CV 90%", "CV 95%", "CV 99%", "Decision"],
            eig_rows,
        )

        # ── Follow-up 3d — Reimers Bartlett-type finite-sample correction ──
        correction_requested = bool(
            ctx.get_param("finite_sample_correction", False)
        )
        correction_applied = False
        correction_fallback_reason = None
        bartlett_factor = None
        trace_stat_corrected = None
        trace_rank_corrected = None
        max_eig_stat_corrected = None
        max_eig_rank_corrected = None
        correction_impact_material = False
        correction_pct_reduction = None
        correction_table = None

        if correction_requested:
            progress_callback(
                "Applying Reimers finite-sample correction", 70
            )
            try:
                B = _bartlett_factor(
                    T=n, n=k, p=p, det_order=det_order,
                )
                if B is None:
                    raise ValueError(
                        f"Bartlett factor is degenerate for "
                        f"T={n}, n={k}, p={p}, det_order={det_order} "
                        f"(degrees of freedom exhausted or uncovered "
                        f"det_order)"
                    )

                # Apply factor to both test statistics.
                tr_stats_c = [float(trace_stats[i]) * B for i in range(k)]
                me_stats_c = [
                    float(max_eig_stats[i]) * B for i in range(k)
                ]

                # Re-determine rank under corrected statistics vs
                # existing statsmodels CVs (Bartlett-on-statistic
                # approach; arithmetically equivalent to MHM 1999
                # response-surface CVs at the decision level).
                tr_rank_c = 0
                for i in range(k):
                    if tr_stats_c[i] > float(trace_cvs[i, sig_col]):
                        tr_rank_c = i + 1
                me_rank_c = 0
                for i in range(k):
                    if me_stats_c[i] > float(max_eig_cvs[i, sig_col]):
                        me_rank_c = i + 1

                bartlett_factor = float(B)
                trace_stat_corrected = [round(v, 4) for v in tr_stats_c]
                trace_rank_corrected = int(tr_rank_c)
                max_eig_stat_corrected = [round(v, 4) for v in me_stats_c]
                max_eig_rank_corrected = int(me_rank_c)
                correction_impact_material = bool(
                    tr_rank_c != determined_rank_trace
                    or me_rank_c != determined_rank_eig
                )
                correction_pct_reduction = float(1.0 - B)
                correction_applied = True

                # Build correction output table (per-H0 side-by-side
                # uncorrected / factor / corrected / decisions).
                corr_rows = []
                for i in range(k):
                    tr_u = float(trace_stats[i])
                    tr_c = tr_stats_c[i]
                    me_u = float(max_eig_stats[i])
                    me_c = me_stats_c[i]
                    cv_tr = float(trace_cvs[i, sig_col])
                    cv_me = float(max_eig_cvs[i, sig_col])
                    corr_rows.append([
                        f"r <= {i}",
                        round(tr_u, 4),
                        round(B, 4),
                        round(tr_c, 4),
                        round(cv_tr, 4),
                        "Reject" if tr_c > cv_tr else "Fail to Reject",
                        round(me_u, 4),
                        round(me_c, 4),
                        round(cv_me, 4),
                        "Reject" if me_c > cv_me else "Fail to Reject",
                    ])
                cv_name_for_cols = cv_labels[sig_col]
                correction_table = make_table(
                    "Finite-Sample Correction (Reimers 1992)",
                    [
                        "H0",
                        "Trace Stat (uncorrected)",
                        "Bartlett Factor",
                        "Trace Stat (corrected)",
                        f"Trace CV {cv_name_for_cols}",
                        "Trace Decision (corrected)",
                        "Max-Eig Stat (uncorrected)",
                        "Max-Eig Stat (corrected)",
                        f"Max-Eig CV {cv_name_for_cols}",
                        "Max-Eig Decision (corrected)",
                    ],
                    corr_rows,
                )
            except Exception as corr_err:
                correction_fallback_reason = (
                    f"runtime_error: {type(corr_err).__name__}: "
                    f"{corr_err}"
                )
                warn_list.append(
                    f"Finite-sample correction raised "
                    f"{type(corr_err).__name__}: {corr_err}. "
                    f"Reverted to uncorrected asymptotic inference."
                )

        # Eigenvalues
        eigenvalues = result.eig
        eig_val_rows = []
        for i, ev in enumerate(eigenvalues):
            eig_val_rows.append([i + 1, round(float(ev), 6)])
        eig_val_table = make_table("Eigenvalues", ["#", "Eigenvalue"], eig_val_rows)

        # Cointegrating vectors (eigenvectors)
        evecs = result.evec  # shape (k, k)
        evec_rows = []
        for j in range(k):
            row = [f"Vector {j + 1}"]
            for i in range(k):
                row.append(round(float(evecs[i, j]), 6))
            evec_rows.append(row)
        evec_table = make_table(
            "Cointegrating Vectors (Eigenvectors)",
            ["Vector"] + names,
            evec_rows,
        )

        # Summary
        summary_rows = [
            ["Variables", k],
            ["Variable Names", ", ".join(names)],
            ["Lag Order (k_ar_diff)", p],
            ["Deterministic Order", det_order],
            ["Observations", n],
            ["Trace Test Rank", determined_rank_trace],
            ["Max Eigenvalue Test Rank", determined_rank_eig],
            ["Significance Level Used", significance],
        ]
        summary_table = make_table("Summary", ["Field", "Value"], summary_rows)

        # Plain English — F2 (d)-form: include the trace-statistic magnitude
        # and the critical value it is being compared against, so a reader
        # can judge the strength of the rejection rather than seeing only
        # the discrete rank decision.
        cv_name = cv_labels[sig_col]
        # Trace stat at the H0: r <= determined_rank_trace - 1 boundary is
        # the one that drove the decision (first index that rejected).
        boundary_idx = max(0, determined_rank_trace - 1)
        trace_stat_at_decision = float(trace_stats[boundary_idx])
        trace_cv_at_decision = float(trace_cvs[boundary_idx, sig_col])

        if determined_rank_trace == determined_rank_eig:
            rank_msg = (
                f"Both trace and max-eigenvalue tests indicate "
                f"{determined_rank_trace} cointegrating relation(s) among the "
                f"{k} series."
            )
        else:
            rank_msg = (
                f"Trace test indicates {determined_rank_trace} cointegrating "
                f"relation(s), while max-eigenvalue indicates "
                f"{determined_rank_eig}. The results are not unanimous; prefer "
                f"the trace test for robustness."
            )

        plain = (
            f"Johansen cointegration test on {k} series "
            f"({', '.join(names)}), lag order {p}. {rank_msg} "
            f"Trace statistic at the decision boundary = "
            f"{trace_stat_at_decision:.2f} vs CV({cv_name}) = "
            f"{trace_cv_at_decision:.2f}."
        )

        if determined_rank_trace == 0 and determined_rank_eig == 0:
            plain += (
                " No cointegration detected. The series do not share a long-run equilibrium. "
                "A VAR model in first differences may be more appropriate."
            )
        elif determined_rank_trace >= k - 1:
            plain += (
                " High cointegration rank suggests the series may all be stationary. "
                "Consider a VAR in levels rather than a VECM."
            )
        else:
            plain += (
                " Cointegration implies a long-run equilibrium relationship. "
                "A VECM (Vector Error Correction Model) is recommended for modelling."
            )

        charting = (
            "Table display with color coding for reject/fail-to-reject. "
            "Bar chart comparing test statistics to critical values at each rank."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C5) ──────────────────────────
        # Rank-implication label (Decision D7): encodes the downstream
        # model suggestion consistent with the plain_english above.
        if determined_rank_trace == 0:
            rank_implication_label = "differenced-VAR"
        elif determined_rank_trace >= k:
            rank_implication_label = "levels-VAR"
        elif determined_rank_trace >= k - 1:
            rank_implication_label = "levels-VAR"
        else:
            rank_implication_label = "VECM"

        # First cointegrating vector (if any) for Tier 2 display.
        first_cointegrating_vector = None
        try:
            # evec_rows[i] is an eigenvector row; the first vector is
            # the one corresponding to the largest eigenvalue.
            if determined_rank_trace >= 1 and hasattr(result, "evec"):
                evec_arr = np.asarray(result.evec)
                if evec_arr.ndim == 2 and evec_arr.shape[1] >= 1:
                    first_cointegrating_vector = [
                        round(float(v), 4) for v in evec_arr[:, 0]
                    ]
        except Exception as exc:
            # Fail-soft is the intended posture for this display-layer field,
            # but the swallow must stay visible in diagnostics (AUD-D1: an
            # undefined-name NameError hid here silently for 2.5 months).
            logging.getLogger(__name__).debug(
                "first_cointegrating_vector extraction failed: %s", exc)
            first_cointegrating_vector = None

        # Follow-up 3d: identification-field label correction.
        # statsmodels actually uses MacKinnon (1996) asymptotic tables
        # from the FORTRAN program johdist.f, not the MHM 1999 response-
        # surface formulas (confirmed by audit of
        # statsmodels.tsa.coint_tables). When finite_sample_correction
        # is applied, note the Reimers / Johansen 2002 addition.
        if correction_applied:
            _cv_formula = (
                "MacKinnon (1996) asymptotic tables via "
                "statsmodels.tsa.vector_ar.vecm.coint_johansen; "
                "Reimers (1992) Bartlett-type finite-sample correction "
                "applied to test statistics (see also Johansen 2002 for "
                "higher-order refinements)"
            )
        else:
            _cv_formula = (
                "MacKinnon (1996) asymptotic tables via "
                "statsmodels.tsa.vector_ar.vecm.coint_johansen"
            )

        audit = {
            "n_variables": k,
            "variable_names": names,
            "lag_order": p,
            "det_order": det_order,
            "trace_rank": determined_rank_trace,
            "max_eig_rank": determined_rank_eig,
            # Phase 4 Session 8 (P4-1.2, 2026-05-02) — VECM rank
            # invariance precondition. Surfaces the trace-test-based
            # cointegrating rank under both the master-plan-mandated
            # name ``determined_rank_trace`` (per §15 S8) and the
            # registry-checker-expected name ``cointegrating_rank``
            # (per tools/reference_parity/harness/structural_invariants.py
            # `vecm_cointegration_rank` checker, populated at Phase 3
            # Session 7). Both fields hold the same value
            # (= ``trace_rank`` above; redundant by design for
            # backward compatibility + structural-invariants registry
            # contract).
            "determined_rank_trace": determined_rank_trace,
            "cointegrating_rank": determined_rank_trace,
            "trace_stat_at_decision": round(trace_stat_at_decision, 4),
            "trace_cv_at_decision": round(trace_cv_at_decision, 4),
            "significance_level": significance,
            "eigenvalues": [round(float(ev), 6) for ev in eigenvalues],
            "rank_implication_label": rank_implication_label,
            "first_cointegrating_vector": first_cointegrating_vector,
            "n_observations": n,
            "tests_agree": bool(determined_rank_trace == determined_rank_eig),
            # Follow-up 3d — finite-sample correction audit fields
            "finite_sample_correction_requested": correction_requested,
            "finite_sample_correction_applied": correction_applied,
            "finite_sample_correction_fallback_reason": correction_fallback_reason,
            "correction_method": (
                "reimers_1992" if correction_applied else None
            ),
            "bartlett_factor": (
                round(bartlett_factor, 6)
                if bartlett_factor is not None else None
            ),
            "trace_stat_corrected": trace_stat_corrected,
            "trace_rank_corrected": trace_rank_corrected,
            "max_eig_stat_corrected": max_eig_stat_corrected,
            "max_eig_rank_corrected": max_eig_rank_corrected,
            "correction_impact_material": bool(correction_impact_material),
            "correction_pct_reduction": (
                round(correction_pct_reduction, 6)
                if correction_pct_reduction is not None else None
            ),
            **format_significance_disclosure(
                test_name="Johansen trace and max-eigenvalue tests",
                critical_value_formula=_cv_formula,
                ac_corrected=True,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        interp = build_interpretation("johansen_cointegration", _interp_dict)

        tables_out = [summary_table, trace_table, eig_table]
        if correction_table is not None:
            tables_out.append(correction_table)
        tables_out.extend([eig_val_table, evec_table])

        return make_response(
            ctx,
            tables=tables_out,
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Johansen test failed: {e}",
            error_fixes=[
                "Ensure all series are numeric and the same length.",
                "Provide at least 2 series.",
                "Series should be I(1) for meaningful cointegration testing.",
                "Try a different lag order or det_order.",
            ],
        )
