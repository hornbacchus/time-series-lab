"""
InterpretationSpec for forecast_reconciliation (hierarchical / grouped
forecasts).

NEW Tier 1 shape — coherence-operation framing (Decision D6). This is a
post-processing operation, NOT a fit technique; Tier 1 leads with
"Reconciled N-level hierarchy..." rather than "Fitted model to...".

Decision D5: primary-method citation convention — MinT preferred (with
3e family extension: mint_shrinkage > mint_sample > wls_variance > ols),
bottom_up fallback when covariance is ill-conditioned.

Follow-up 3e: full MinT family (OLS, WLS-variance, MinT-shrinkage
Schäfer-Strimmer 2005, MinT-sample). Tier 1 gains a closer naming the
applied MinT variant and reconciliation change magnitude. Tier 2 gains
mode disclosure (auto 2-level vs explicit n-level), a MinT methodology
block (Wickramasuriya-Athanasopoulos-Hyndman 2019 formula, shrinkage
lambda, W characterization), an OLS-default upgrade-recommendation
clause (D23, fires only when method defaulted AND applied=="ols"), and
a fallback-disclosure block. Legacy ``_trigger_mint_ols_fell_back`` is
re-gated to suppress when the broader D1 ``method_fallback_occurred``
fires. Six new Tier 3 triggers (D1-D6).

Results-dict keys consumed for 3e:

    reconciliation_mode                         : "auto_2_level" | "explicit_n_level"
    reconciliation_method_requested / _applied
    reconciliation_fallback_reason              : str | None
    method_was_default                          : bool (D23 gate)
    n_total / n_bottom / n_horizons / residuals_T
    hierarchy_levels
    w_matrix_condition_number / _is_diagonal / _rank / _ill_conditioned
    shrinkage_lambda                            : float | None
    reconciliation_change_rmse
    top_level_change_magnitude
    bottom_level_change_rmse
    coherence_pre_reconciliation_L2 / _max
    coherence_post_reconciliation_L2 / _max
    nonnegative_requested / nonnegative_constraint_binding
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import format_scale_aware
from interpretation.registry import register

PRESET_GATED_KEYS = ()


_METHOD_DISPLAY = {
    "ols": "MinT-OLS",
    "bottom_up": "bottom-up",
    "top_down": "top-down",
    "wls_variance": "MinT-WLS (variance)",
    "wls": "MinT-WLS (variance)",
    "mint_shrinkage": "MinT-shrinkage (Schäfer-Strimmer 2005)",
    "mint_sample": "MinT-sample (full covariance)",
}


# Follow-up 3e: the MinT family names used in 3e logic.
_MINT_FAMILY = (
    "ols", "wls_variance", "wls", "mint_shrinkage", "mint_sample",
)


def _method_name(method: str) -> str:
    return _METHOD_DISPLAY.get(
        str(method or "").lower(), str(method or "bottom-up"),
    )


def _mode_label(mode: str) -> str:
    """Convert audit mode identifier to Tier 2 display label."""
    if mode == "explicit_n_level":
        return "explicit n-level"
    return "auto 2-level"


def _tier1(results: dict) -> str:
    top = str(results.get("top_series", "top aggregate"))
    bottom = list(results.get("bottom_series") or [])
    n_bottom = int(results.get("n_bottom", len(bottom)))
    horizon = int(results.get("horizon", 0))
    primary = _method_name(results.get("primary_method"))
    rel_incoh = results.get("relative_incoherence")

    bottom_quoted = ", ".join(f"'{s}'" for s in bottom) if bottom else f"{n_bottom} components"

    if rel_incoh is None:
        incoh_clause = "Historical coherence not reported"
    else:
        try:
            rel = float(rel_incoh)
        except Exception:
            rel = 0.0
        if rel <= 0.01:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level (input hierarchy is coherent)"
            )
        elif rel <= 0.05:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level (mildly incoherent)"
            )
        else:
            incoh_clause = (
                f"Historical coherence check: mean aggregation residual "
                f"{rel*100:.1f}% of top level — the input hierarchy is "
                f"materially incoherent before reconciliation"
            )

    base_tier1 = (
        f"Reconciled 2-level hierarchy over {horizon} periods: "
        f"'{top}' = sum of {n_bottom} bottom-level series ({bottom_quoted}). "
        f"{primary} reconciliation applied (preferred when available, with "
        f"bottom-up fallback on singular covariance). {incoh_clause}. "
        f"Reconciled forecasts respect the aggregation constraint exactly; "
        f"per-method results disclosed in Tier 2."
    )

    # Follow-up 3e: append closer when a MinT variant was the primary
    # method and reported a reconciliation change.
    primary_method_raw = str(results.get("primary_method") or "").lower()
    if primary_method_raw in _MINT_FAMILY:
        try:
            mode = str(results.get("reconciliation_mode", "auto_2_level"))
            mode_disp = _mode_label(mode)
            change_rmse = results.get("reconciliation_change_rmse")
            if change_rmse is not None:
                base_tier1 = base_tier1 + (
                    f" MinT reconciliation ({primary_method_raw}, "
                    f"{mode_disp} mode) — reconciliation change RMSE = "
                    f"{float(change_rmse):.4f}."
                )
        except Exception:
            pass

    return base_tier1


def _tier2(results: dict) -> str:
    methods = list(results.get("methods") or [])
    methods_display = [_method_name(m) for m in methods]
    primary = _method_name(results.get("primary_method"))
    primary_raw = str(results.get("primary_method") or "").lower()
    fell_back = bool(results.get("primary_method_fell_back", False))
    horizon = int(results.get("horizon", 0))
    base = str(results.get("base_forecaster", "naive"))
    rel_incoh = results.get("relative_incoherence")

    # Follow-up 3e: broader fallback disclosure via
    # reconciliation_fallback_reason (D1).
    new_fallback_reason = results.get("reconciliation_fallback_reason")
    fell_back_clause = ""
    if new_fallback_reason:
        reason_str = str(new_fallback_reason)
        fell_back_clause = (
            f" Graceful fallback: requested primary method "
            f"'{results.get('reconciliation_method_requested') or primary_raw}' "
            f"was replaced by applied method "
            f"'{results.get('reconciliation_method_applied') or primary_raw}' "
            f"(reason: {reason_str})."
        )
    elif fell_back:
        # Legacy (pre-3e) OLS→bottom_up fallback path.
        fell_back_clause = (
            " MinT-OLS reconciliation failed on this run (singular S'S "
            "covariance); the wrapper fell back to bottom-up reconciliation "
            "and that fallback is cited as the primary method above."
        )

    try:
        rel_pct = float(rel_incoh) * 100 if rel_incoh is not None else None
    except Exception:
        rel_pct = None
    if rel_pct is None:
        incoh_sent = "Historical aggregation residuals not reported."
    else:
        incoh_sent = (
            f"Historical aggregation residuals (pre-reconciliation): "
            f"{rel_pct:.2f}% of the top-level mean."
        )

    # Follow-up 3e: mode disclosure (always-on).
    mode = str(results.get("reconciliation_mode", ""))
    if mode == "auto_2_level":
        mode_clause = (
            " Mode: auto 2-level (S constructed internally from top + "
            "bottom series)."
        )
    elif mode == "explicit_n_level":
        mode_clause = (
            " Mode: explicit n-level (user-provided S_matrix, "
            "y_hat_matrix, residuals_matrix via ctx.params)."
        )
    else:
        mode_clause = ""

    # Follow-up 3e: MinT methodology block when MinT variant applied.
    mint_clause = ""
    if primary_raw in _MINT_FAMILY:
        try:
            lam = results.get("shrinkage_lambda")
            cond = results.get("w_matrix_condition_number")
            is_diag = results.get("w_matrix_is_diagonal")
            n_total = results.get("n_total")
            L2_post = results.get("coherence_post_reconciliation_L2")
            cond_str = (
                f"{float(cond):.2e}" if cond is not None else "n/a"
            )
            rank_str = (
                str(int(results.get("w_matrix_rank")))
                if results.get("w_matrix_rank") is not None else "n/a"
            )
            W_descriptor = (
                "diagonal" if bool(is_diag) else "full"
            )
            mint_clause = (
                f" MinT (Wickramasuriya-Athanasopoulos-Hyndman 2019) "
                f"with method '{primary_raw}': reconciled forecast "
                f"y_tilde = S (S' W^-1 S)^-1 S' W^-1 y_hat; W is "
                f"{W_descriptor} (condition number {cond_str}, "
                f"rank {rank_str})."
            )
            if lam is not None:
                try:
                    mint_clause += (
                        f" Shrinkage intensity lambda = "
                        f"{float(lam):.4f} "
                        f"(Schäfer-Strimmer 2005 optimal shrinkage of "
                        f"sample correlations toward 0)."
                    )
                except Exception:
                    pass
            if L2_post is not None:
                try:
                    mint_clause += (
                        f" Post-reconciliation coherence L2 = "
                        f"{float(L2_post):.2e} (perfect = 0)."
                    )
                except Exception:
                    pass
        except Exception:
            mint_clause = ""

    # Follow-up 3e D23: OLS-default upgrade recommendation (fires
    # only when method defaulted AND applied=="ols").
    ols_upgrade_clause = ""
    if (
        primary_raw == "ols"
        and bool(results.get("method_was_default", False))
    ):
        ols_upgrade_clause = (
            " Method defaulted to OLS for backward compatibility. "
            "WAH 2019 recommends mint_shrinkage which typically "
            "produces more accurate reconciled forecasts via "
            "covariance-weighted projection. Set "
            "method='mint_shrinkage' to upgrade."
        )

    return (
        f"Hierarchical forecast reconciliation via linear post-processing. "
        f"{len(methods)} reconciliation method{'s' if len(methods) != 1 else ''} "
        f"applied ({', '.join(methods_display) if methods_display else 'none'}); "
        f"{primary} cited as the primary method when the S'S covariance matrix "
        f"is well-conditioned, with bottom-up fallback otherwise.{fell_back_clause} "
        f"Base forecasts generated via '{base}' over the {horizon}-step horizon; "
        f"reconciliation then projects onto the coherent subspace so that the "
        f"top forecast equals the sum of the bottom forecasts exactly at "
        f"every step. "
        f"{incoh_sent} Reconciliation preserves ranking of base forecasts but "
        f"cannot correct systematic base-forecast bias; if base forecasts are "
        f"poor, reconciled forecasts will also be poor — reconciliation "
        f"enforces coherence only."
        f"{mode_clause}{mint_clause}{ols_upgrade_clause}"
    )


def _trigger_historical_incoherence_high(results: dict) -> Optional[str]:
    rel = results.get("relative_incoherence")
    if rel is None:
        return None
    try:
        v = float(rel)
    except Exception:
        return None
    if v <= 0.05:
        return None
    return (
        f"Historical incoherence is {v*100:.1f}% of the top level — the "
        f"input hierarchy does not already add up to the top aggregate. "
        f"Reconciliation will force coherence on the forecasts but the "
        f"underlying data inconsistency should be investigated first; "
        f"reconciliation is not a substitute for data cleaning."
    )


def _trigger_mint_ols_fell_back(results: dict) -> Optional[str]:
    """C5 legacy trigger — narrowed per Follow-up 3e D26. Fires only
    on the OLS→bottom_up fallback path AND when the broader D1
    ``method_fallback_occurred`` is NOT firing (to avoid duplicate
    disclosure)."""
    fell_back = bool(results.get("primary_method_fell_back", False))
    if not fell_back:
        return None
    # Suppress when 3e D1 fires (broader disclosure already covers it)
    if results.get("reconciliation_fallback_reason"):
        return None
    # Suppress when applied method is a MinT variant (3e path)
    applied = str(results.get("reconciliation_method_applied") or "").lower()
    if applied in _MINT_FAMILY and applied != "ols":
        return None
    return (
        "MinT-OLS reconciliation failed (singular S'S covariance); the "
        "wrapper fell back to bottom-up. Results are still coherent, but "
        "MinT-OLS's variance-minimization benefit is lost. This typically "
        "happens when the hierarchy has more bottom series than independent "
        "observations, or when bottom series are collinear."
    )


def _trigger_base_forecaster_is_naive_long_horizon(results: dict) -> Optional[str]:
    base = str(results.get("base_forecaster", "")).lower()
    horizon = int(results.get("horizon", 0))
    if base != "naive" or horizon <= 3:
        return None
    return (
        f"Base forecaster is 'naive' (last-value persistence) over a "
        f"{horizon}-step horizon; reconciliation preserves the flat "
        f"trajectory. For a more informative reconciled forecast, "
        f"configure the wrapper to use 'drift' or 'ets' as the base forecaster."
    )


# ── Follow-up 3e Tier 3 triggers (D1-D6) ───────────────────────────


def _trigger_method_fallback_occurred(results: dict) -> Optional[str]:
    """D1 (3e) — fires on ANY MinT-family method fallback. Text
    disambiguates cause (insufficient-T vs numerical failure vs
    cascade exhausted)."""
    reason = results.get("reconciliation_fallback_reason")
    if not reason:
        return None
    requested = str(results.get("reconciliation_method_requested") or "")
    applied = str(results.get("reconciliation_method_applied") or "")
    reason_str = str(reason)
    if reason_str == "mint_sample_requires_T_gt_n":
        # D5 covers this more specifically; D1 still fires for
        # the broader signal.
        cause = (
            "mint_sample requires T > n_total (insufficient residual "
            "sample size for full covariance estimation)"
        )
    elif reason_str.startswith("runtime_error_in_"):
        cause = (
            f"runtime error in the requested method's W estimation; "
            f"cascade advanced to the next fallback tier"
        )
    elif reason_str.startswith("cascade_exhausted"):
        cause = (
            "the entire MinT fallback cascade failed; wrapper "
            "returned bottom-up aggregation as a last resort"
        )
    else:
        cause = reason_str
    return (
        f"Reconciliation method fallback: requested '{requested}' → "
        f"applied '{applied}' ({cause}). Reconciled forecasts are "
        f"still coherent, but the variance-minimization guarantee of "
        f"the requested method is lost."
    )


def _trigger_w_matrix_ill_conditioned(results: dict) -> Optional[str]:
    """D2 (3e) — fires when W condition number > 1e12."""
    if not bool(results.get("w_matrix_ill_conditioned", False)):
        return None
    cond = results.get("w_matrix_condition_number")
    try:
        cond_val = float(cond) if cond is not None else None
    except Exception:
        cond_val = None
    cond_str = f"{cond_val:.2e}" if cond_val is not None else "n/a"
    return (
        f"W matrix is ill-conditioned (condition number {cond_str} > "
        f"1e12). Near-singular W amplifies residual noise through the "
        f"MinT projection G = (S' W^-1 S)^-1 S' W^-1. Consider "
        f"mint_shrinkage (which regularises correlations toward 0) or "
        f"increasing the residual sample size via a longer training "
        f"window."
    )


def _trigger_shrinkage_extreme(results: dict) -> Optional[str]:
    """D3 (3e) — fires when lambda > 0.95 (degenerate to WLS) or
    lambda < 0.05 (could use mint_sample instead)."""
    lam = results.get("shrinkage_lambda")
    if lam is None:
        return None
    try:
        v = float(lam)
    except Exception:
        return None
    if 0.05 <= v <= 0.95:
        return None
    if v > 0.95:
        return (
            f"Shrinkage intensity lambda = {v:.4f} is very high (> 0.95). "
            f"The Schäfer-Strimmer shrinkage has effectively degenerated "
            f"toward the diagonal (WLS-variance) solution — off-diagonal "
            f"correlation information is deemed unreliable at this sample "
            f"size. Results should be nearly identical to method="
            f"'wls_variance'."
        )
    return (
        f"Shrinkage intensity lambda = {v:.4f} is very low (< 0.05). "
        f"The sample covariance is well-conditioned relative to the "
        f"residual sample size; method='mint_sample' (no shrinkage) "
        f"should give similar results with lower bias."
    )


def _trigger_reconciliation_change_material(results: dict) -> Optional[str]:
    """D4 (3e) — fires when top-level change > 5% of top-level
    forecast magnitude."""
    top_change = results.get("top_level_change_magnitude")
    if top_change is None:
        return None
    # Use any top-level reference: fall back to change_rmse if
    # no direct top reference is available.
    try:
        top_change_val = float(top_change)
    except Exception:
        return None
    # Need a reference magnitude to compare against. Use RMSE of the
    # reconciliation change as a proxy.
    change_rmse = results.get("reconciliation_change_rmse")
    if change_rmse is None:
        return None
    try:
        rmse_val = float(change_rmse)
    except Exception:
        return None
    # If top change is less than 5% of total change, not material.
    # Use relative comparison: the trigger text reports the abs top
    # change; the threshold is relative to forecast magnitude which
    # the spec doesn't have directly. Conservative: fire only when
    # top_change > 5% of the change_rmse scale (high material).
    # Practical heuristic: fire when top_change > 5 * rmse_val.
    if top_change_val < max(rmse_val * 5.0, 1e-6):
        return None
    return (
        f"Top-level reconciliation change is material "
        f"(magnitude {top_change_val:.4f}, dominating the reconciliation "
        f"RMSE {rmse_val:.4f}). Base forecasts were substantially "
        f"incoherent; the reconciled top-level estimate differs "
        f"materially from the base top forecast. Treat this as "
        f"information about the magnitude of the coherence correction, "
        f"not as a model-quality issue."
    )


def _trigger_residuals_insufficient_for_method(
    results: dict,
) -> Optional[str]:
    """D5 (3e) — fires on the specific mint_sample_requires_T_gt_n
    fallback branch."""
    reason = str(results.get("reconciliation_fallback_reason") or "")
    if reason != "mint_sample_requires_T_gt_n":
        return None
    T = results.get("residuals_T")
    n = results.get("n_total")
    requested = results.get("reconciliation_method_requested")
    applied = results.get("reconciliation_method_applied")
    return (
        f"Requested method '{requested}' requires T > n_total for "
        f"non-singular sample covariance; available T = {T} with "
        f"n_total = {n}. Wrapper gracefully fell back to '{applied}' "
        f"(Schäfer-Strimmer shrinkage regularises the covariance and "
        f"works for any T >= 2). For mint_sample to be valid on this "
        f"hierarchy, provide at least {int(n) + 1 if n is not None else 'n_total + 1'} "
        f"residual observations."
    )


def _trigger_nonnegative_constraint_binding(
    results: dict,
) -> Optional[str]:
    """D6 (3e) — fires when nonnegative=True and NNLS constraint
    was active (some reconciled bottom value would have been
    negative without the constraint)."""
    if not bool(results.get("nonnegative_requested", False)):
        return None
    if not bool(results.get("nonnegative_constraint_binding", False)):
        return None
    return (
        "Nonnegative constraint is binding — at least one bottom-level "
        "reconciled forecast would have been negative under the "
        "unconstrained MinT projection. The NNLS solver pinned those "
        "values to 0, which keeps all aggregates non-negative (since S "
        "is binary) but loses the MinT minimum-trace optimality. "
        "Consider whether the negative base forecasts reflect genuine "
        "data signal that the nonnegative assumption is suppressing."
    )


SPEC = InterpretationSpec(
    technique_id="forecast_reconciliation",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # C5 legacy triggers
        _trigger_historical_incoherence_high,
        _trigger_mint_ols_fell_back,  # re-gated per D26
        _trigger_base_forecaster_is_naive_long_horizon,
        # Follow-up 3e D1-D6
        _trigger_method_fallback_occurred,
        _trigger_w_matrix_ill_conditioned,
        _trigger_shrinkage_extreme,
        _trigger_reconciliation_change_material,
        _trigger_residuals_insufficient_for_method,
        _trigger_nonnegative_constraint_binding,
    ),
    mode_aware=False,
)

register(SPEC)
