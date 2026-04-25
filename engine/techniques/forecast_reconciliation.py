"""
Hierarchical Forecast Reconciliation for Time Series Lab.

Implements bottom-up, top-down, and the full MinT (Minimum Trace)
family — OLS, WLS-variance, MinT-shrinkage (Schäfer-Strimmer 2005),
MinT-sample — per Wickramasuriya-Athanasopoulos-Hyndman 2019.

The user provides series in a hierarchy: the first series is the
top-level aggregate, and the remaining series are the bottom-level
components that should sum to the top level.

Follow-up 3e: full MinT family. Two operating modes:

**Auto 2-level mode** (default, backward compat): S is constructed
internally as a 2-level summing matrix from ``ctx.get_all_series()``.
Base forecasts and residuals are computed internally from the
chosen ``base_forecaster`` ∈ {naive, drift, ets}.

**Explicit n-level mode** (opt-in): user provides
``ctx.params["S_matrix"]`` (list-of-lists, shape n_total × n_bottom).
Optionally also provides ``ctx.params["y_hat_matrix"]`` and
``ctx.params["residuals_matrix"]`` for general n-level
reconciliation outside the 2-level assumption. Follows the
hts/fable/statsforecast API convention.

MinT variants:

- ``ols``: W = I. No residual-based weighting.
- ``wls_variance`` (alias ``wls``): W = diag(Var(residuals)).
- ``mint_shrinkage``: W = Schäfer-Strimmer 2005 shrunk sample
  covariance (shrinks correlations toward 0; preserves variances).
- ``mint_sample``: W = full sample covariance. Requires T > n_total.

Graceful fallback cascade (D22): mint_sample → mint_shrinkage →
wls_variance → ols; mint_shrinkage → mint_sample → wls_variance →
ols. OLS (W=I) never falls back.

Nonnegative reconciliation: opt-in via ``ctx.params["nonnegative"]``.
Uses ``scipy.optimize.nnls`` to solve the whitened bottom-level
NNLS problem, then maps to all levels via S. Ensures bottom ≥ 0
(and hence all aggregates ≥ 0 since S is binary).
"""

import numpy as np
from scipy import linalg

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# Follow-up 3e: MinT family method names. `wls` is a backward-
# compatible alias for `wls_variance` (the catalog already declares
# `wls` as an option).
_MINT_METHODS = ("ols", "wls_variance", "wls", "mint_shrinkage", "mint_sample")


# Fallback cascade order per D22.
_FALLBACK_CHAIN = {
    "mint_sample": ("mint_shrinkage", "wls_variance", "ols"),
    "mint_shrinkage": ("mint_sample", "wls_variance", "ols"),
    "wls_variance": ("ols",),
    "wls": ("ols",),
    "ols": (),
}


# Follow-up B1 — custom exception for rank-deficient W matrix.
class RankDeficientWMatrixError(np.linalg.LinAlgError):
    """W matrix has rank < n_total; mint_sample produces
    numerically-unstable solve. Raised by ``_mint_reconcile`` to
    trigger the D22 cascade with the distinct
    ``w_matrix_rank_deficient`` fallback_reason. Inherits from
    ``np.linalg.LinAlgError`` so the cascade's existing
    ``except Exception`` branch continues to catch it; a more
    specific ``except RankDeficientWMatrixError`` branch in
    ``_reconcile_with_fallback`` populates the distinct reason
    string before falling through to the generic handler."""


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"methods": ["bottom_up"], "horizon": 10},
    "Balanced": {"methods": ["bottom_up", "top_down", "ols"], "horizon": 10},
    "Thorough": {"methods": ["bottom_up", "top_down", "ols"], "horizon": 10},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Reconcile hierarchical forecasts.

    Parameters (via ctx.params)
    ---------------------------
    method : str or list[str], optional
        'bottom_up', 'top_down', 'ols'. Preset-dependent.
    horizon : int
        Forecast horizon. Default 10.
    base_forecaster : str, optional
        How to produce base forecasts: 'naive' (random walk), 'drift', 'ets'.
        Default 'naive'.
    top_down_weights : str, optional
        For top-down: 'proportions_avg' (default) or 'proportions_last'.

    Series layout
    -------------
    First series  -> top-level aggregate.
    Remaining series -> bottom-level components (should sum to top).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        ctx.validate_min_series(2)
        all_series = ctx.get_all_series()
        top_name, top_vals = all_series[0]
        bottom_names = [s[0] for s in all_series[1:]]
        bottom_arrays = [s[1] for s in all_series[1:]]
        n_bottom = len(bottom_names)
        n_total = n_bottom + 1  # top + bottom levels

        # Align lengths
        min_len = min(len(top_vals), *(len(a) for a in bottom_arrays))
        top_vals = top_vals[:min_len]
        bottom_arrays = [a[:min_len] for a in bottom_arrays]
        T = min_len

        # Handle NaN via interpolation
        def _fill_nan(arr, label):
            nans = np.where(np.isnan(arr))[0]
            valid = np.where(~np.isnan(arr))[0]
            if len(nans) > 0:
                if len(valid) < 3:
                    raise ValueError(f"Series '{label}' has too few non-missing values.")
                arr = arr.copy()
                arr[nans] = np.interp(nans, valid, arr[valid])
            return arr

        top_vals = _fill_nan(top_vals, top_name)
        for i in range(n_bottom):
            bottom_arrays[i] = _fill_nan(bottom_arrays[i], bottom_names[i])

        if T < 10:
            return make_error_response(
                ctx,
                f"Only {T} observations. Need at least 10 for reconciliation.",
                error_fixes=["Provide longer series."],
            )

        # Check coherence: does sum of bottom ≈ top?
        bottom_sum = np.sum(np.column_stack(bottom_arrays), axis=1)
        max_diff = float(np.max(np.abs(top_vals - bottom_sum)))
        mean_top = float(np.mean(np.abs(top_vals)))
        relative_incoherence = max_diff / mean_top if mean_top > 0 else max_diff
        if relative_incoherence > 0.05:
            warnings.append(
                f"Historical bottom-level series do not exactly sum to the top level "
                f"(max absolute difference = {max_diff:.4f}, relative = {relative_incoherence:.2%}). "
                "Reconciliation will enforce coherence in the forecasts."
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        horizon = max(1, int(ctx.get_param("horizon", cfg["horizon"])))
        methods_param = ctx.get_param("method")
        # Follow-up 3e D23: track whether method was defaulted so
        # the spec can emit a Tier 2 OLS-upgrade recommendation
        # without nagging users who explicitly chose ols.
        method_was_default = methods_param is None
        if methods_param is not None:
            if isinstance(methods_param, str):
                methods = [methods_param.lower()]
            else:
                methods = [m.lower() for m in methods_param]
        else:
            methods = cfg["methods"]
        base_fc_type = ctx.get_param("base_forecaster", "naive")
        td_weights = ctx.get_param("top_down_weights", "proportions_avg")

        # Follow-up 3e: optional MinT family params.
        nonnegative = bool(ctx.get_param("nonnegative", False))
        # Mode detection: presence of S_matrix activates explicit
        # n-level mode. y_hat_matrix and residuals_matrix are
        # optional even in explicit mode (wrapper falls back to
        # internal base-forecaster computation for missing ones).
        s_matrix_param = ctx.get_param("S_matrix")
        y_hat_matrix_param = ctx.get_param("y_hat_matrix")
        residuals_matrix_param = ctx.get_param("residuals_matrix")
        explicit_mode = s_matrix_param is not None
        reconciliation_mode = (
            "explicit_n_level" if explicit_mode else "auto_2_level"
        )

        progress_callback("Generating base forecasts", 20)

        # Generate base forecasts for all series
        all_vals = [top_vals] + bottom_arrays
        all_names = [top_name] + bottom_names
        base_fc = np.zeros((horizon, n_total))
        base_residuals = np.zeros((T, n_total))

        for i, (sname, svals) in enumerate(zip(all_names, all_vals)):
            fc, resid = _base_forecast(svals, horizon, base_fc_type)
            base_fc[:, i] = fc
            base_residuals[-len(resid):, i] = resid

        progress_callback("Reconciling forecasts", 45)

        # S matrix: maps bottom-level to all levels.
        # Follow-up 3e: in explicit mode, use user-provided S.
        # In auto 2-level mode (default), construct as before:
        # S = [[1, 1, ..., 1], I_n_bottom].
        if explicit_mode:
            try:
                S = np.asarray(s_matrix_param, dtype=np.float64)
                if S.ndim != 2:
                    raise ValueError(
                        f"S_matrix must be 2D; got ndim={S.ndim}"
                    )
                # Shape consistency: rows must equal n_total from
                # the aligned series (but in explicit n-level mode
                # n_total from S may differ from n_total deduced
                # from series). We trust S and override base_fc /
                # base_residuals shapes below.
            except Exception as e:
                return make_error_response(
                    ctx,
                    f"Invalid S_matrix parameter: {e}",
                    error_fixes=[
                        "S_matrix must be a 2D nested list / ndarray "
                        "with shape (n_total, n_bottom).",
                    ],
                )
        else:
            S = np.vstack([np.ones((1, n_bottom)), np.eye(n_bottom)])  # (n_total, n_bottom)

        # Follow-up 3e: overrides for y_hat and residuals when
        # user provides them explicitly (explicit n-level mode).
        if explicit_mode and y_hat_matrix_param is not None:
            try:
                _user_y_hat = np.asarray(y_hat_matrix_param, dtype=np.float64)
                if _user_y_hat.ndim == 1:
                    # Single-horizon; expand to (n_total, 1)
                    _user_y_hat = _user_y_hat.reshape(-1, 1)
                # Convention: user passes (n_total, h); base_fc stores
                # (horizon, n_total). Transpose if needed based on
                # S.shape[0].
                if _user_y_hat.shape[0] != S.shape[0]:
                    if _user_y_hat.shape[1] == S.shape[0]:
                        _user_y_hat = _user_y_hat.T
                    else:
                        return make_error_response(
                            ctx,
                            f"y_hat_matrix shape {_user_y_hat.shape} "
                            f"does not align with S_matrix rows "
                            f"({S.shape[0]}).",
                        )
                # base_fc convention: (horizon, n_total)
                base_fc_override = _user_y_hat.T  # (h, n_total)
                horizon_from_y = base_fc_override.shape[0]
            except Exception as e:
                return make_error_response(
                    ctx,
                    f"Invalid y_hat_matrix parameter: {e}",
                )
        else:
            base_fc_override = None
            horizon_from_y = None

        if explicit_mode and residuals_matrix_param is not None:
            try:
                _user_residuals = np.asarray(
                    residuals_matrix_param, dtype=np.float64,
                )
                if _user_residuals.ndim != 2:
                    raise ValueError(
                        f"residuals_matrix must be 2D; got "
                        f"ndim={_user_residuals.ndim}"
                    )
                if _user_residuals.shape[0] != S.shape[0]:
                    if _user_residuals.shape[1] == S.shape[0]:
                        _user_residuals = _user_residuals.T
                    else:
                        return make_error_response(
                            ctx,
                            f"residuals_matrix shape "
                            f"{_user_residuals.shape} does not align "
                            f"with S_matrix rows ({S.shape[0]}).",
                        )
                # Expected shape (n_total, T_train)
                base_residuals_override = _user_residuals
            except Exception as e:
                return make_error_response(
                    ctx,
                    f"Invalid residuals_matrix parameter: {e}",
                )
        else:
            base_residuals_override = None

        # Apply overrides (if any). Note: n_total, bottom/top series
        # names remain as inferred from ctx.get_all_series(). In
        # explicit n-level mode we derive display names from the
        # summing-matrix structure.
        if base_fc_override is not None:
            base_fc = base_fc_override
            horizon = horizon_from_y
        if base_residuals_override is not None:
            # base_residuals stored as (T, n_total) in existing code;
            # override is (n_total, T_train). Transpose to match.
            base_residuals = base_residuals_override.T
        # Update n_total derived from S for explicit mode
        if explicit_mode:
            n_total = int(S.shape[0])
            n_bottom = int(S.shape[1])
            # Generate synthetic names if needed
            if len(all_series) != n_total:
                # User did not supply aligned series count;
                # synthesise names for display.
                synth_names = [f"series_{i}" for i in range(n_total)]
                all_names = synth_names
                top_name = synth_names[0]
                bottom_names = synth_names[-n_bottom:]

        results = {}
        # Follow-up 3e: capture MinT-specific audit sub-fields per
        # method as cascade runs.
        mint_audit_per_method = {}

        for method in methods:
            if method == "bottom_up":
                # G = [0, I] -> reconciled = S @ bottom_base_fc
                fc_bottom = base_fc[:, 1:]  # (horizon, n_bottom)
                fc_reconciled = fc_bottom @ S.T  # This is wrong; we need S @ fc_bottom.T
                fc_reconciled = (S @ fc_bottom.T).T  # (horizon, n_total)
                results["bottom_up"] = fc_reconciled

            elif method == "top_down":
                # Compute proportions
                if td_weights == "proportions_last":
                    props = np.zeros(n_bottom)
                    for j in range(n_bottom):
                        props[j] = bottom_arrays[j][-1] / top_vals[-1] if top_vals[-1] != 0 else 1.0 / n_bottom
                else:
                    # proportions_avg
                    props = np.zeros(n_bottom)
                    for j in range(n_bottom):
                        props[j] = np.mean(bottom_arrays[j]) / np.mean(top_vals) if np.mean(top_vals) != 0 else 1.0 / n_bottom

                # Normalise
                prop_sum = props.sum()
                if prop_sum > 0:
                    props = props / prop_sum

                fc_top = base_fc[:, 0]  # (horizon,)
                fc_reconciled = np.zeros((horizon, n_total))
                fc_reconciled[:, 0] = fc_top
                for j in range(n_bottom):
                    fc_reconciled[:, 1 + j] = fc_top * props[j]

                results["top_down"] = fc_reconciled

            elif method in _MINT_METHODS:
                # Follow-up 3e: MinT family dispatch via cascade.
                # base_fc stored (horizon, n_total); convert to
                # (n_total, horizon) for matrix math.
                y_hat_matrix = base_fc.T  # (n_total, horizon)
                # base_residuals stored (T, n_total); transpose to
                # (n_total, T). Drop leading zero-padding rows if
                # any (the existing wrapper zero-pads residuals from
                # the front of base_residuals when resid is shorter
                # than T — this pad reflects positions we don't
                # have true residuals for).
                R_full = base_residuals.T  # (n_total, T)
                # Determine effective T_effective: drop leading
                # all-zero columns (which are the pad positions).
                col_is_zero = np.all(R_full == 0, axis=0)
                if col_is_zero.any():
                    first_nonzero = int(
                        np.argmax(~col_is_zero) if (~col_is_zero).any()
                        else R_full.shape[1]
                    )
                    R_effective = R_full[:, first_nonzero:]
                else:
                    R_effective = R_full
                try:
                    (
                        y_tilde, W, applied, fallback_reason,
                        extras, constraint_binding,
                    ) = _reconcile_with_fallback(
                        y_hat_matrix, S, R_effective, method,
                        nonnegative,
                    )
                    fc_reconciled = y_tilde.T  # back to (horizon, n_total)
                except Exception as e:
                    warnings.append(
                        f"Reconciliation method '{method}' failed and "
                        f"entire fallback cascade exhausted: {e}. "
                        f"Falling back to bottom-up sum."
                    )
                    fc_bottom = base_fc[:, 1:] if not explicit_mode else base_fc
                    fc_reconciled = (S @ fc_bottom.T).T
                    applied = method
                    fallback_reason = f"cascade_exhausted: {e}"
                    extras = {"is_diagonal": True, "shrinkage_lambda": None}
                    W = np.eye(n_total)
                    constraint_binding = False

                # Store results under REQUESTED method name (so
                # table / audit keys match user input), but track
                # applied in per-method audit.
                results[method] = fc_reconciled
                mint_audit_per_method[method] = {
                    "applied": applied,
                    "fallback_reason": fallback_reason,
                    "W": W,
                    "extras": extras,
                    "constraint_binding": constraint_binding,
                    "y_tilde": y_tilde if 'y_tilde' in locals() else None,
                }

            else:
                warnings.append(f"Unknown method '{method}' skipped.")

        if not results:
            return make_error_response(ctx, "No valid reconciliation method was specified.")

        progress_callback("Building output tables", 70)

        tables = []

        # ---- Reconciled forecasts per method ----
        for method_name, fc_rec in results.items():
            fc_rows = []
            for h in range(horizon):
                row = [h + 1]
                for i in range(n_total):
                    row.append(round(float(fc_rec[h, i]), 4))
                fc_rows.append(row)
            tables.append(make_table(
                f"Reconciled Forecast ({method_name})",
                ["Step"] + all_names,
                fc_rows,
            ))

        # ---- Base vs reconciled comparison ----
        for method_name, fc_rec in results.items():
            comp_rows = []
            for i in range(n_total):
                base_mean = float(np.mean(base_fc[:, i]))
                rec_mean = float(np.mean(fc_rec[:, i]))
                diff = rec_mean - base_mean
                comp_rows.append([
                    all_names[i],
                    round(base_mean, 4),
                    round(rec_mean, 4),
                    round(diff, 4),
                ])
            tables.append(make_table(
                f"Base vs Reconciled Mean ({method_name})",
                ["Series", "Base Mean FC", "Reconciled Mean FC", "Adjustment"],
                comp_rows,
            ))

        # ---- Coherence check on reconciled ----
        for method_name, fc_rec in results.items():
            coh_rows = []
            for h in range(horizon):
                top_fc = fc_rec[h, 0]
                bot_sum = np.sum(fc_rec[h, 1:])
                coh_rows.append([h + 1, round(float(top_fc), 4), round(float(bot_sum), 4),
                                 round(float(top_fc - bot_sum), 6)])
            tables.append(make_table(
                f"Coherence Check ({method_name})",
                ["Step", "Top Forecast", "Bottom Sum", "Difference"],
                coh_rows,
            ))

        # ---- Historical coherence ----
        hist_rows = [
            ["Mean Top Level", round(float(np.mean(top_vals)), 4)],
            ["Mean Bottom Sum", round(float(np.mean(bottom_sum)), 4)],
            ["Max Abs Difference", round(max_diff, 4)],
            ["Relative Incoherence", f"{relative_incoherence:.4%}"],
        ]
        if "top_down" in results:
            prop_rows = []
            props = np.zeros(n_bottom)
            for j in range(n_bottom):
                props[j] = np.mean(bottom_arrays[j]) / np.mean(top_vals) if np.mean(top_vals) != 0 else 1.0 / n_bottom
            prop_sum = props.sum()
            if prop_sum > 0:
                props = props / prop_sum
            for j in range(n_bottom):
                hist_rows.append([f"Proportion ({bottom_names[j]})", round(float(props[j]), 4)])
        tables.append(make_table("Historical Coherence", ["Metric", "Value"], hist_rows))

        # ---- Summary ----
        summary_rows = [
            ["Top-Level Series", top_name],
            ["Bottom-Level Series", ", ".join(bottom_names)],
            ["Number of Bottom Series", n_bottom],
            ["Observations", T],
            ["Forecast Horizon", horizon],
            ["Base Forecaster", base_fc_type],
            ["Methods Applied", ", ".join(results.keys())],
            ["Reconciliation Mode", reconciliation_mode],
        ]
        tables.append(make_table("Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        method_list = ", ".join(results.keys())
        plain = (
            f"Hierarchical forecast reconciliation for {n_total} series "
            f"({top_name} = sum of {', '.join(bottom_names)}). "
            f"Methods applied: {method_list}. "
            f"Base forecasts generated using '{base_fc_type}' method, "
            f"then reconciled to enforce coherence over {horizon} steps. "
        )
        if relative_incoherence > 0.05:
            plain += f"Note: historical data was {relative_incoherence:.1%} incoherent."

        charting = (
            "Stacked area chart of bottom-level reconciled forecasts summing to top-level. "
            "Line overlay showing original base forecasts vs reconciled. "
            "Bar chart comparing base vs reconciled mean forecasts per series."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C5) ──────────────────────────
        # Primary-method citation convention (Decision D5):
        # MinT-OLS preferred when available; fall back to bottom_up
        # when OLS fails (detected via cascade-exhausted warning).
        _methods_ran = list(results.keys())
        # Prefer the newer MinT variants, then ols, then others.
        if "mint_shrinkage" in _methods_ran:
            primary_method = "mint_shrinkage"
        elif "mint_sample" in _methods_ran:
            primary_method = "mint_sample"
        elif "wls_variance" in _methods_ran:
            primary_method = "wls_variance"
        elif "wls" in _methods_ran:
            primary_method = "wls"
        elif "ols" in _methods_ran:
            primary_method = "ols"
        elif "bottom_up" in _methods_ran:
            primary_method = "bottom_up"
        elif "top_down" in _methods_ran:
            primary_method = "top_down"
        else:
            primary_method = _methods_ran[0] if _methods_ran else None

        # Follow-up 3e: pull primary-method MinT sub-audit (if any).
        _primary_mint = (
            mint_audit_per_method.get(primary_method)
            if primary_method in mint_audit_per_method else None
        )
        _primary_applied = (
            _primary_mint["applied"] if _primary_mint else primary_method
        )
        _primary_fallback_reason = (
            _primary_mint["fallback_reason"] if _primary_mint else None
        )
        _primary_W = _primary_mint["W"] if _primary_mint else None
        _primary_extras = (
            _primary_mint["extras"] if _primary_mint else {}
        )
        _primary_constraint_binding = bool(
            _primary_mint["constraint_binding"] if _primary_mint else False
        )

        # W matrix characterization (only for MinT primary)
        if _primary_W is not None:
            _w_cond, _w_rank, _w_is_diag = _w_matrix_characterize(_primary_W)
        else:
            _w_cond, _w_rank, _w_is_diag = None, None, None

        # Coherence pre/post (only for MinT primary — other methods
        # like bottom_up / top_down are coherent by construction).
        _coh_pre_L2, _coh_pre_max = None, None
        _coh_post_L2, _coh_post_max = None, None
        _recon_change_rmse = None
        _top_level_change = None
        _bottom_level_change_rmse = None
        if primary_method in _MINT_METHODS and primary_method in results:
            try:
                _y_hat_primary = base_fc.T  # (n_total, horizon)
                _y_tilde_primary = results[primary_method].T
                _coh_pre_L2, _coh_pre_max = _coherence_metrics(
                    _y_hat_primary, S,
                )
                _coh_post_L2, _coh_post_max = _coherence_metrics(
                    _y_tilde_primary, S,
                )
                _recon_change_rmse = float(np.sqrt(np.mean(
                    (_y_tilde_primary - _y_hat_primary) ** 2
                )))
                _top_level_change = float(np.max(np.abs(
                    _y_tilde_primary[0] - _y_hat_primary[0]
                )))
                if n_bottom > 0:
                    _bot_idx = slice(-n_bottom, None)
                    _bottom_level_change_rmse = float(np.sqrt(np.mean(
                        (_y_tilde_primary[_bot_idx]
                         - _y_hat_primary[_bot_idx]) ** 2
                    )))
            except Exception:
                pass

        # D1 "primary method fell back" (new broader definition):
        # fires whenever the primary method's fallback_reason is
        # populated. Back-compat: legacy trigger re-gated to
        # suppress when this is True.
        _primary_fell_back = bool(_primary_fallback_reason)

        audit = {
            "top_series": top_name,
            "bottom_series": bottom_names,
            "n_bottom": n_bottom,
            "methods": _methods_ran,
            "primary_method": primary_method,
            "primary_method_fell_back": _primary_fell_back,
            "base_forecaster": base_fc_type,
            "horizon": horizon,
            "n_observations": T,
            "relative_incoherence": round(relative_incoherence, 4),
            # Follow-up 3e — MinT family audit additions
            "reconciliation_mode": reconciliation_mode,
            "reconciliation_method_requested": primary_method,
            "reconciliation_method_applied": _primary_applied,
            "reconciliation_fallback_reason": _primary_fallback_reason,
            "method_was_default": bool(method_was_default),
            "n_total": int(n_total),
            "n_horizons": int(horizon),
            "residuals_T": int(T),
            "hierarchy_levels": int(_infer_hierarchy_levels(S)),
            "w_matrix_condition_number": (
                round(_w_cond, 4) if _w_cond is not None else None
            ),
            "w_matrix_is_diagonal": _w_is_diag,
            "w_matrix_rank": _w_rank,
            "w_matrix_ill_conditioned": (
                bool(_w_cond is not None and _w_cond > 1e12)
                if _w_cond is not None else False
            ),
            "shrinkage_lambda": _primary_extras.get("shrinkage_lambda"),
            "reconciliation_change_rmse": (
                round(_recon_change_rmse, 6)
                if _recon_change_rmse is not None else None
            ),
            "top_level_change_magnitude": (
                round(_top_level_change, 6)
                if _top_level_change is not None else None
            ),
            "bottom_level_change_rmse": (
                round(_bottom_level_change_rmse, 6)
                if _bottom_level_change_rmse is not None else None
            ),
            "coherence_pre_reconciliation_L2": (
                round(_coh_pre_L2, 6)
                if _coh_pre_L2 is not None else None
            ),
            "coherence_pre_reconciliation_max": (
                round(_coh_pre_max, 6)
                if _coh_pre_max is not None else None
            ),
            "coherence_post_reconciliation_L2": (
                round(_coh_post_L2, 6)
                if _coh_post_L2 is not None else None
            ),
            "coherence_post_reconciliation_max": (
                round(_coh_post_max, 6)
                if _coh_post_max is not None else None
            ),
            "nonnegative_requested": bool(nonnegative),
            "nonnegative_constraint_binding": _primary_constraint_binding,
        }

        # Follow-up 3e: MinT-family output tables (appended AFTER
        # audit dict is built so we can read primary_method and
        # derived audit fields). Only when a MinT variant was the
        # primary method.
        if primary_method in _MINT_METHODS and primary_method in results:
            mint_summary_rows = [
                ["Method Requested", primary_method],
                ["Method Applied", _primary_applied],
                ["Mode", reconciliation_mode],
                ["n_total", int(n_total)],
                ["n_bottom", int(n_bottom)],
                ["n_horizons", int(horizon)],
                ["Residuals T", int(T)],
                ["Hierarchy Levels", int(audit["hierarchy_levels"])],
                [
                    "Shrinkage Lambda",
                    (round(float(audit["shrinkage_lambda"]), 6)
                     if audit["shrinkage_lambda"] is not None else "N/A"),
                ],
                [
                    "Coherence Pre-Reconciliation (L2)",
                    (f"{audit['coherence_pre_reconciliation_L2']:.2e}"
                     if audit["coherence_pre_reconciliation_L2"] is not None
                     else "N/A"),
                ],
                [
                    "Coherence Post-Reconciliation (L2)",
                    (f"{audit['coherence_post_reconciliation_L2']:.2e}"
                     if audit["coherence_post_reconciliation_L2"] is not None
                     else "N/A"),
                ],
                [
                    "Coherence Post-Reconciliation (max)",
                    (f"{audit['coherence_post_reconciliation_max']:.2e}"
                     if audit["coherence_post_reconciliation_max"] is not None
                     else "N/A"),
                ],
                [
                    "Fallback Reason",
                    (str(_primary_fallback_reason)
                     if _primary_fallback_reason else "None"),
                ],
            ]
            tables.append(make_table(
                "MinT Reconciliation Summary",
                ["Metric", "Value"],
                mint_summary_rows,
            ))

            w_char_rows = [
                ["Condition Number", (
                    f"{audit['w_matrix_condition_number']:.4e}"
                    if audit["w_matrix_condition_number"] is not None
                    else "N/A"
                )],
                ["Rank", (
                    int(audit["w_matrix_rank"])
                    if audit["w_matrix_rank"] is not None else "N/A"
                )],
                [
                    "Is Diagonal",
                    (bool(audit["w_matrix_is_diagonal"])
                     if audit["w_matrix_is_diagonal"] is not None else "N/A"),
                ],
                [
                    "Ill-Conditioned (cond > 1e12)",
                    bool(audit["w_matrix_ill_conditioned"]),
                ],
                [
                    "Shrinkage Lambda",
                    (round(float(audit["shrinkage_lambda"]), 6)
                     if audit["shrinkage_lambda"] is not None else "N/A"),
                ],
            ]
            tables.append(make_table(
                "W Matrix Characterization",
                ["Metric", "Value"],
                w_char_rows,
            ))

            impact_rows = [
                [
                    "Reconciliation Change RMSE",
                    (round(float(audit["reconciliation_change_rmse"]), 6)
                     if audit["reconciliation_change_rmse"] is not None
                     else "N/A"),
                ],
                [
                    "Top-Level Change (max magnitude)",
                    (round(float(audit["top_level_change_magnitude"]), 6)
                     if audit["top_level_change_magnitude"] is not None
                     else "N/A"),
                ],
                [
                    "Bottom-Level Change RMSE",
                    (round(float(audit["bottom_level_change_rmse"]), 6)
                     if audit["bottom_level_change_rmse"] is not None
                     else "N/A"),
                ],
                [
                    "Nonnegative Requested",
                    bool(audit["nonnegative_requested"]),
                ],
                [
                    "Nonnegative Constraint Binding",
                    bool(audit["nonnegative_constraint_binding"]),
                ],
            ]
            tables.append(make_table(
                "Reconciliation Impact",
                ["Metric", "Value"],
                impact_rows,
            ))

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        _interp_dict = dict(audit)
        interp = build_interpretation("forecast_reconciliation", _interp_dict)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Forecast reconciliation failed: {e}",
            error_fixes=[
                "Ensure first series is the aggregate and remaining are components.",
                "All series must be numeric and the same length.",
                "Check that bottom-level series approximately sum to the top level.",
            ],
        )


# ---------------------------------------------------------------------------
# Base forecasters
# ---------------------------------------------------------------------------

def _base_forecast(y, horizon, method="naive"):
    """
    Generate base forecasts and in-sample residuals.

    Returns (forecast_array, residual_array).
    """
    n = len(y)

    if method == "drift":
        # Random walk with drift
        drift = (y[-1] - y[0]) / (n - 1) if n > 1 else 0.0
        fc = y[-1] + drift * np.arange(1, horizon + 1)
        fitted = np.full(n, np.nan)
        fitted[1:] = y[:-1] + drift
        resid = y - fitted
        resid = resid[~np.isnan(resid)]
    elif method == "ets":
        # Simple exponential smoothing
        alpha = 0.3
        level = y[0]
        fitted = np.zeros(n)
        for t in range(n):
            fitted[t] = level
            level = alpha * y[t] + (1 - alpha) * level
        fc = np.full(horizon, level)
        resid = y - fitted
    else:
        # naive (random walk)
        fc = np.full(horizon, y[-1])
        fitted = np.full(n, np.nan)
        fitted[1:] = y[:-1]
        resid = y[1:] - y[:-1]

    return fc, resid


# ---------------------------------------------------------------------------
# Follow-up 3e — MinT family helpers
# ---------------------------------------------------------------------------


def _schafer_strimmer_shrinkage(residuals):
    """Schäfer-Strimmer (2005) optimal shrinkage of the sample
    correlation toward identity, preserving diagonal variances.

    Parameters
    ----------
    residuals : ndarray, shape (n_total, T)
        Rows are series; columns are time points.

    Returns
    -------
    W_shrunk : ndarray, shape (n_total, n_total)
        Shrunk covariance = D + (1 - lambda) * (S_sample - D)
        where D is diag(S_sample) and lambda ∈ [0, 1]. Equivalent
        form: correlations shrunk toward 0 by factor (1 - lambda).
    lambda_hat : float
        Optimal shrinkage intensity in [0, 1].
    """
    R = np.asarray(residuals, dtype=np.float64)
    n, T = R.shape
    if T < 2:
        # Degenerate: can't estimate variance; return identity.
        return np.eye(n), 1.0

    # Centered residuals
    R_c = R - R.mean(axis=1, keepdims=True)
    # Sample covariance (unbiased)
    S_sample = (R_c @ R_c.T) / max(T - 1, 1)
    # Variances and diagonal matrix
    var_diag = np.diag(S_sample).copy()
    var_diag_safe = np.where(var_diag > 0, var_diag, 1.0)
    d = np.sqrt(var_diag_safe)
    # Sample correlation
    corr = S_sample / np.outer(d, d)
    np.fill_diagonal(corr, 1.0)

    # Standardized residuals (per row)
    R_std = R_c / d[:, None]

    # Compute Var(r_ij) for i != j per Schäfer-Strimmer eq 2.4
    # Var(r_ij) = (T / (T-1)^3) * sum_t (w_ij,t - w_ij_bar)^2
    # where w_ij,t = x_it * x_jt (standardized).
    # Build w_ij tensor only off-diagonal contributions.
    # Efficient: compute elementwise product of R_std with its rows,
    # accumulate variance across time.
    sum_var_r = 0.0
    sum_r_sq = 0.0
    # Loop over off-diagonal pairs. For small n this is fine;
    # matrices larger than ~50 we still have quadratic cost but
    # it's manageable for typical reconciliation problem sizes.
    if n <= 1:
        return S_sample, 0.0
    scale_var = T / max((T - 1) ** 3, 1)
    for i in range(n):
        for j in range(i + 1, n):
            w_ij = R_std[i] * R_std[j]
            w_ij_mean = w_ij.mean()
            var_r_ij = scale_var * float(np.sum((w_ij - w_ij_mean) ** 2))
            sum_var_r += 2.0 * var_r_ij  # (i,j) + (j,i) both count
            sum_r_sq += 2.0 * (corr[i, j] ** 2)

    if sum_r_sq <= 1e-12:
        lambda_hat = 1.0
    else:
        lambda_hat = float(sum_var_r / sum_r_sq)
    # Clamp to [0, 1]
    lambda_hat = max(0.0, min(1.0, lambda_hat))

    # Shrunk covariance: shrink off-diagonal correlations toward 0,
    # preserve diagonal variances. Equivalent to:
    #   corr_shrunk = (1 - lambda) * corr + lambda * I_n
    # W_shrunk = diag(d) * corr_shrunk * diag(d)
    corr_shrunk = (1.0 - lambda_hat) * corr
    np.fill_diagonal(corr_shrunk, 1.0)
    W_shrunk = corr_shrunk * np.outer(d, d)
    return W_shrunk, lambda_hat


def _estimate_W_matrix(residuals, method):
    """Estimate the MinT covariance weight matrix W.

    Parameters
    ----------
    residuals : ndarray, shape (n_total, T)
    method : str in {'ols', 'wls_variance', 'wls', 'mint_shrinkage', 'mint_sample'}

    Returns
    -------
    W : ndarray, shape (n_total, n_total)
    extras : dict
        Keys: 'is_diagonal' (bool), 'shrinkage_lambda' (float or None).
    """
    n, T = residuals.shape
    if method == "ols":
        return np.eye(n), {"is_diagonal": True, "shrinkage_lambda": None}
    if method in ("wls_variance", "wls"):
        variances = residuals.var(axis=1, ddof=1) if T > 1 else np.ones(n)
        variances = np.maximum(variances, 1e-12)
        return np.diag(variances), {"is_diagonal": True, "shrinkage_lambda": None}
    if method == "mint_sample":
        if T <= n:
            raise ValueError(
                f"mint_sample requires T > n_total "
                f"(T={T}, n_total={n})"
            )
        R_c = residuals - residuals.mean(axis=1, keepdims=True)
        W = (R_c @ R_c.T) / (T - 1)
        return W, {"is_diagonal": False, "shrinkage_lambda": None}
    if method == "mint_shrinkage":
        W, lam = _schafer_strimmer_shrinkage(residuals)
        return W, {"is_diagonal": False, "shrinkage_lambda": float(lam)}
    raise ValueError(f"Unknown MinT method: {method}")


def _mint_reconcile(y_hat, S, W):
    """Reconcile via y_tilde = S · G · y_hat,
    G = (S' W^{-1} S)^{-1} S' W^{-1}.

    y_hat shape (n_total,) or (n_total, h).

    Raises
    ------
    RankDeficientWMatrixError
        If W is rank-deficient (rank < n_total), which makes
        ``np.linalg.solve`` numerically unstable. Caller's cascade
        (``_reconcile_with_fallback``) catches this and advances
        to the next method (typically mint_shrinkage, which adds
        Schaefer-Strimmer regularization and is rank-deficient-
        safe). Defensive: any internal exception in the rank
        check itself is treated as rank-deficient (conservative
        — fall back to a more stable method rather than risk a
        numerically-unstable solve).
    """
    # Follow-up B1 — pre-solve rank check. On perfectly coherent
    # hierarchies (top residual = exact sum of bottom residuals)
    # the sample covariance W_sam has rank n_bottom < n_total,
    # making np.linalg.solve produce numerically-unstable output
    # rather than NaN. Detect early and raise so the cascade
    # falls back to a regularised method.
    n_total = W.shape[0]
    try:
        rank = int(np.linalg.matrix_rank(W))
    except Exception:
        # Conservative: treat any rank-check exception as
        # rank-deficient and fall back.
        raise RankDeficientWMatrixError(
            "W matrix rank check raised; treating as "
            "rank-deficient (fallback to next cascade method)."
        )
    if rank < n_total:
        raise RankDeficientWMatrixError(
            f"W matrix rank {rank} < n_total {n_total} "
            f"(rank-deficient; np.linalg.solve would produce "
            f"numerically unstable output)."
        )

    W_inv = np.linalg.inv(W)
    # Use solve for numerical stability
    StWinv = S.T @ W_inv          # (n_bottom, n_total)
    A = StWinv @ S                # (n_bottom, n_bottom)
    G = np.linalg.solve(A, StWinv)  # (n_bottom, n_total)
    return S @ (G @ y_hat)


def _mint_reconcile_nonneg(y_hat, S, W):
    """Nonnegative reconciliation via NNLS.

    Solve per horizon:
        min_b || W^{-1/2} (S b - y_hat) ||_2    s.t.  b >= 0
    Then return y_tilde = S b. Since S is binary (summing matrix),
    b >= 0 implies all aggregates are >= 0 too.

    Returns (y_tilde, constraint_binding) where constraint_binding
    is True if any NNLS bottom value was pinned to 0.
    """
    from scipy.optimize import nnls
    # Whitening: W^{-1/2}. Use eigen-decomposition (W is symmetric
    # PSD). Regularise tiny eigenvalues to avoid blow-up.
    eigvals, eigvecs = np.linalg.eigh(W)
    eigvals_safe = np.maximum(eigvals, 1e-12)
    W_inv_sqrt = eigvecs @ np.diag(1.0 / np.sqrt(eigvals_safe)) @ eigvecs.T
    A = W_inv_sqrt @ S                 # (n_total, n_bottom)
    if y_hat.ndim == 1:
        rhs = W_inv_sqrt @ y_hat
        b, _ = nnls(A, rhs)
        constraint_binding = bool(np.any(b < 1e-10))
        y_tilde = S @ b
    else:
        n_bottom = S.shape[1]
        h = y_hat.shape[1]
        b_mat = np.zeros((n_bottom, h))
        binding = False
        for j in range(h):
            rhs = W_inv_sqrt @ y_hat[:, j]
            b_j, _ = nnls(A, rhs)
            b_mat[:, j] = b_j
            if np.any(b_j < 1e-10):
                binding = True
        constraint_binding = bool(binding)
        y_tilde = S @ b_mat
    return y_tilde, constraint_binding


def _w_matrix_characterize(W):
    """Return (condition_number, rank, is_diagonal)."""
    W = np.asarray(W, dtype=np.float64)
    try:
        cond = float(np.linalg.cond(W))
    except Exception:
        cond = float("inf")
    try:
        rank = int(np.linalg.matrix_rank(W))
    except Exception:
        rank = W.shape[0]
    eps = 1e-10
    off_diag = W - np.diag(np.diag(W))
    is_diagonal = bool(np.max(np.abs(off_diag)) < eps)
    return cond, rank, is_diagonal


def _coherence_metrics(y_vec, S):
    """Return (L2_rmse, max_violation) for the aggregation residual
    y - S S^+ y. Zero iff y lies in the column space of S
    (perfectly coherent).

    y_vec shape (n_total,) or (n_total, h).
    """
    y_arr = np.asarray(y_vec, dtype=np.float64)
    S_pinv = np.linalg.pinv(S)
    if y_arr.ndim == 1:
        b_hat = S_pinv @ y_arr
        residual = y_arr - S @ b_hat
    else:
        b_hat = S_pinv @ y_arr
        residual = y_arr - S @ b_hat
    L2 = float(np.sqrt(np.mean(residual ** 2)))
    max_abs = float(np.max(np.abs(residual)))
    return L2, max_abs


def _infer_hierarchy_levels(S):
    """Count distinct aggregation levels in a binary summing matrix.

    The number of levels equals the number of distinct "column-sum
    counts" across rows, plus 1 (bottom level). For the simple
    2-level matrix [[1..1], I_n_bottom], rows sum to {n_bottom, 1}
    → 2 levels. For a 3-level matrix with top=1, middle=3, bottom=9,
    rows sum to {9, 3, 3, 3, 1,1,...,1} → 3 levels.
    """
    S_arr = np.asarray(S)
    row_sums = S_arr.sum(axis=1)
    distinct = set(int(s) for s in row_sums.tolist())
    return len(distinct)


def _reconcile_with_fallback(
    y_hat, S, residuals, method, nonnegative,
):
    """Execute MinT reconciliation with the 3e fallback cascade.

    Parameters
    ----------
    y_hat : ndarray, shape (n_total,) or (n_total, h)
    S : ndarray, shape (n_total, n_bottom)
    residuals : ndarray, shape (n_total, T)
    method : str, requested method
    nonnegative : bool

    Returns
    -------
    y_tilde : ndarray, reconciled forecast
    W : ndarray, the W matrix actually used
    applied : str, method actually applied (may differ on fallback)
    fallback_reason : str or None
    extras : dict from _estimate_W_matrix
    constraint_binding : bool (only meaningful if nonnegative=True)
    """
    n, T = residuals.shape
    requested = method
    applied = method
    fallback_reason = None

    # Pre-flight: mint_sample requires T > n
    if method == "mint_sample" and T <= n:
        fallback_reason = "mint_sample_requires_T_gt_n"
        applied = "mint_shrinkage"

    # Attempt cascade
    chain = [applied] + list(_FALLBACK_CHAIN.get(applied, ()))
    y_tilde = None
    W = None
    extras = {}
    constraint_binding = False
    last_err = None
    for idx, try_method in enumerate(chain):
        try:
            W_try, extras_try = _estimate_W_matrix(residuals, try_method)
            if nonnegative:
                y_tilde_try, binding = _mint_reconcile_nonneg(
                    y_hat, S, W_try,
                )
            else:
                y_tilde_try = _mint_reconcile(y_hat, S, W_try)
                binding = False
            # Success
            applied = try_method
            W = W_try
            extras = extras_try
            y_tilde = y_tilde_try
            constraint_binding = binding
            if idx > 0 and fallback_reason is None:
                # Fell back due to exception on primary
                fallback_reason = (
                    f"runtime_error_in_{requested}: "
                    f"{type(last_err).__name__ if last_err else 'Exception'}: "
                    f"{last_err}"
                )
            break
        except RankDeficientWMatrixError as e:
            # Follow-up B1 — distinct reason string for the
            # rank-deficient case (vs the generic
            # ``runtime_error_in_<method>: ...`` pattern). The
            # success branch above guards on
            # ``fallback_reason is None``, so this assignment
            # is preserved through the next-method retry. The
            # ``idx == 0`` gate ensures we attribute rank-
            # deficiency to the originally-requested method,
            # not to a downstream cascade attempt.
            last_err = e
            if fallback_reason is None and idx == 0:
                fallback_reason = "w_matrix_rank_deficient"
            continue
        except Exception as e:
            last_err = e
            continue

    if y_tilde is None:
        raise RuntimeError(
            f"All reconciliation methods in cascade failed; "
            f"last error: {last_err}"
        )

    return y_tilde, W, applied, fallback_reason, extras, constraint_binding
