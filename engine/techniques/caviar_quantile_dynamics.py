"""
CAViaR (Conditional Autoregressive Value-at-Risk) quantile dynamics
for Time Series Lab.

Implements the Engle & Manganelli (2004) CAViaR model for dynamic quantile estimation.
The quantile q_t evolves as an autoregressive process, estimated by minimizing
the asymmetric (quantile) loss function.

Supported specifications:
- Symmetric Absolute Value (SAV):
    q_t = beta_0 + beta_1 * q_{t-1} + beta_2 * |y_{t-1}|
- Asymmetric Slope (AS):
    q_t = beta_0 + beta_1 * q_{t-1} + beta_2 * max(y_{t-1}, 0) + beta_3 * min(y_{t-1}, 0)
- Indirect GARCH (IG):
    q_t = (beta_0 + beta_1 * q_{t-1}^2 + beta_2 * y_{t-1}^2)^(1/2)

Follow-up 3a — Multi-horizon VaR capability. Prior to 3a the wrapper
emitted only the in-sample quantile path and backtests; users had no
explicit forecast output. 3a adds (a) explicit 1-step-ahead VaR
q_{T+1|T} via the recursion applied to the last observation, and
(b) multi-horizon VaR at user-specified horizons via Monte Carlo
bootstrap simulation. Simulation resamples raw residuals
r_t = y_t - q_t (preserves empirical CDF; Christoffersen 2012),
propagates the CAViaR recursion forward, and extracts the θ-quantile
of simulated y values at each horizon.
"""

import ast

import numpy as np
from scipy.optimize import minimize

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

_PRESET_CONFIG = {
    "Fast":     {"n_restarts": 3,  "maxiter": 500,  "n_simulation_paths": 500},
    "Balanced": {"n_restarts": 10, "maxiter": 2000, "n_simulation_paths": 2000},
    "Thorough": {"n_restarts": 30, "maxiter": 5000, "n_simulation_paths": 10000},
}

# Default forecast horizons for daily VaR practitioner use:
# 1-day / 1-week / 2-week / 1-month.
_DEFAULT_HORIZONS = [1, 5, 10, 22]

# Value-map: the `model_type` dialog control's vocabulary -> the engine's
# `specification` codes (Engle-Manganelli 2004). The catalog dialog offers
# user-friendly names; the engine branches on SAV/AS/IG. Case-insensitive;
# also accepts the native codes so a THOROUGH `model_type:"SAV"` works. NOTE:
# the catalog's third spec is `igarch` (-> IG, Indirect GARCH), matching what
# the engine implements; the Engle-Manganelli "Adaptive" spec is NOT yet in
# the engine (a banked engine-improvement) and is deliberately absent here —
# routing it to another spec would silently mislead the user.
_MODEL_TYPE_MAP = {
    "symmetric_abs": "SAV", "sav": "SAV", "symmetric_absolute_value": "SAV",
    "asymmetric_slope": "AS", "as": "AS",
    "igarch": "IG", "ig": "IG", "indirect_garch": "IG",
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Estimate CAViaR model for dynamic quantile / VaR.

    Parameters (via ctx.params)
    ---------------------------
    theta : float, optional
        Quantile level (default 0.05 for 5% VaR). Sourced from the `quantile`
        dialog control when a native `theta` is not passed (THOROUGH power-path).
    specification : str, optional
        'SAV' (default), 'AS', or 'IG'. Sourced from the `model_type` dialog
        control via `_MODEL_TYPE_MAP` (symmetric_abs->SAV, asymmetric_slope->AS,
        igarch->IG) when a native `specification` is not passed.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warnings = []

        # Drop NaN
        clean = values[~np.isnan(values)]
        n_dropped = len(values) - len(clean)
        if n_dropped > 0:
            warnings.append(f"{n_dropped} missing values removed.")

        n = len(clean)
        if n < 100:
            return make_error_response(
                ctx,
                f"Only {n} valid observations. CAViaR needs at least 100 for reliable estimation.",
                error_fixes=["Provide a longer return series."],
            )

        # theta = the VaR quantile level, sourced from the `quantile` dialog
        # control; precedence theta (THOROUGH power-path) > quantile (dialog) >
        # default 0.05. The (0,1) gate validates the resolved value.
        theta = float(ctx.get_param("theta", ctx.get_param("quantile", 0.05)))
        if theta <= 0 or theta >= 1:
            return make_error_response(
                ctx,
                f"Quantile level theta must be in (0, 1), got {theta}.",
                error_fixes=["Set theta between 0 and 1 (e.g., 0.05 for 5% VaR)."],
            )

        # specification sourced from the `model_type` dialog control via the
        # value-map; precedence specification (THOROUGH, native SAV/AS/IG) >
        # model_type (dialog, mapped) > default SAV.
        _mt = ctx.get_param("model_type", None)
        _mapped = (
            _MODEL_TYPE_MAP.get(str(_mt).strip().lower(), _mt)
            if _mt is not None else "SAV"
        )
        spec = str(ctx.get_param("specification", _mapped)).upper()
        if spec not in ("SAV", "AS", "IG"):
            return make_error_response(
                ctx,
                f"Unknown specification '{spec}'. Use 'SAV', 'AS', or 'IG' "
                f"(model_type: symmetric_abs, asymmetric_slope, igarch).",
                error_fixes=[
                    "Choose one of: SAV, AS, IG.",
                    "Or set model_type to symmetric_abs, asymmetric_slope, or igarch.",
                ],
            )

        y = clean.copy()

        # Initial quantile estimate (empirical)
        q0 = float(np.quantile(y, theta))

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])

        progress_callback(f"Estimating CAViaR ({spec}) model", 20)

        best_loss = np.inf
        best_params = None

        for restart in range(cfg["n_restarts"]):
            pct = 20 + int(55 * restart / cfg["n_restarts"])
            progress_callback(f"Optimization restart {restart + 1}/{cfg['n_restarts']}", pct)

            params0 = _get_initial_params(spec, y, theta, q0)

            try:
                res = minimize(
                    _quantile_loss,
                    params0,
                    args=(y, theta, spec, q0),
                    method="Nelder-Mead",
                    options={"maxiter": cfg["maxiter"], "xatol": 1e-8, "fatol": 1e-10},
                )
                if res.fun < best_loss and np.isfinite(res.fun):
                    best_loss = res.fun
                    best_params = res.x
            except Exception:
                continue

        if best_params is None:
            return make_error_response(
                ctx,
                "CAViaR optimization failed to converge on all restarts.",
                error_fixes=[
                    "Try the 'Thorough' preset for more restarts.",
                    "Check for extreme outliers in the series.",
                    "Try a different specification (SAV, AS, IG).",
                ],
            )

        progress_callback("Computing dynamic quantiles", 80)

        # Generate the quantile path
        q_path = _compute_quantile_path(best_params, y, spec, q0)

        # Exceedance analysis
        violations = y < q_path  # VaR violations (left tail)
        n_violations = int(violations.sum())
        expected_violations = n * theta
        violation_ratio = n_violations / (n * theta) if n * theta > 0 else np.inf

        # Kupiec unconditional coverage test
        kupiec_stat, kupiec_pval = _kupiec_test(n, n_violations, theta)

        # Christoffersen independence test
        cc_stat, cc_pval = _christoffersen_test(violations, theta)

        # Dynamic Quantile (DQ) test - Engle & Manganelli
        dq_stat, dq_pval = _dq_test(y, q_path, violations, theta)

        # ── Follow-up 3a — Multi-horizon VaR forecasts ───────────────
        progress_callback("Multi-horizon MC simulation", 88)

        horizons = _parse_horizons(ctx.get_param("horizons", None))
        if not horizons:
            horizons = list(_DEFAULT_HORIZONS)
        H_max = max(horizons)
        n_sim_paths = int(ctx.get_param(
            "n_simulation_paths", cfg["n_simulation_paths"],
        ))
        n_sim_paths = max(100, n_sim_paths)  # lower-bound sanity

        # Explicit 1-step-ahead VaR q_{T+1|T} per Phase 1 Q7
        one_step_ahead_var = float(_caviar_recurse_one_step(
            spec, best_params, q_path[-1], y[-1],
        ))

        # Raw in-sample residuals for bootstrap (Phase 1 Q2)
        r_in_sample = np.asarray(y - q_path, dtype=np.float64)
        lb_pval = _ljung_box_on_residuals(r_in_sample)

        # Stationarity check (per-spec; effective persistence)
        beta_1_param, effective_persistence, is_stationary = _extract_stationarity_param(
            spec, best_params,
        )

        # Run MC simulation with graceful degradation (D12). Common
        # failure mode: non-stationary recursion causes inf/nan q
        # values. We still return audit fields in that case; Tier 3
        # D3 trigger flags the non-stationarity for the user.
        mh = {}
        multi_step_computed = False
        try:
            mc_rng = np.random.default_rng(ctx.seed)
            sim_out = _simulate_multi_horizon_paths(
                spec=spec, params=best_params,
                q_T=float(q_path[-1]), y_T=float(y[-1]),
                r_in_sample=r_in_sample,
                H_max=H_max, n_paths=n_sim_paths, rng=mc_rng,
            )
            mh = _multi_horizon_quantiles_and_noise(
                y_sim=sim_out["y_sim"], horizons=horizons,
                theta=theta, B_subsamples=50, rng=mc_rng,
            )
            # If every horizon returned NaN, mark as not computed
            if mh and any(
                np.isfinite(v["VaR"]) for v in mh.values()
            ):
                multi_step_computed = True
            else:
                multi_step_computed = False
                warnings.append(
                    "Multi-horizon simulation produced non-finite "
                    "values (likely non-stationary CAViaR recursion). "
                    "See Tier 3 for stationarity diagnostic."
                )
        except Exception as mc_err:
            warnings.append(
                f"Multi-horizon MC simulation failed: "
                f"{type(mc_err).__name__}: {mc_err}. Single-horizon "
                f"VaR is still reported."
            )
            mh = {}
            multi_step_computed = False

        progress_callback("Building output", 90)

        # Parameter names
        if spec == "SAV":
            pnames = ["beta_0", "beta_1", "beta_2"]
        elif spec == "AS":
            pnames = ["beta_0", "beta_1", "beta_2 (positive)", "beta_3 (negative)"]
        else:  # IG
            pnames = ["beta_0", "beta_1", "beta_2"]

        # Parameters table
        param_rows = []
        for i, pn in enumerate(pnames):
            param_rows.append([pn, round(float(best_params[i]), 6)])
        param_rows.append(["Quantile loss", round(float(best_loss), 6)])
        param_rows.append(["theta (quantile level)", theta])
        param_rows.append(["Specification", spec])
        param_table = make_table("CAViaR Parameters", ["Parameter", "Value"], param_rows)

        # Backtesting table
        bt_rows = [
            ["N observations", n],
            ["N violations", n_violations],
            ["Expected violations", round(expected_violations, 1)],
            ["Violation ratio", round(violation_ratio, 4)],
            ["Kupiec LR stat", round(float(kupiec_stat), 4)],
            ["Kupiec p-value", round(float(kupiec_pval), 6)],
            ["Christoffersen stat", round(float(cc_stat), 4)],
            ["Christoffersen p-value", round(float(cc_pval), 6)],
            ["DQ stat", round(float(dq_stat), 4)],
            ["DQ p-value", round(float(dq_pval), 6)],
        ]
        bt_table = make_table("VaR Backtesting", ["Metric", "Value"], bt_rows)

        # Time series table
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        max_display = 500
        step = max(1, n // max_display)
        ts_rows = []
        for i in range(0, n, step):
            ts_rows.append([
                time_col[i],
                round(float(y[i]), 6),
                round(float(q_path[i]), 6),
                "Yes" if violations[i] else "No",
            ])

        ts_table = make_table(
            "Dynamic Quantile Path",
            ["Time", "Return", f"q_{theta:.2f}", "Violation"],
            ts_rows,
        )

        # Multi-Horizon VaR Forecasts table (Follow-up 3a)
        mh_rows = []
        for h in horizons:
            row = mh.get(int(h))
            if row is None:
                mh_rows.append([int(h), None, None, None, None])
                continue
            mh_rows.append([
                int(h),
                round(row["VaR"], 6) if np.isfinite(row["VaR"]) else None,
                round(row["mc_std"], 6) if np.isfinite(row["mc_std"]) else None,
                round(row["hdi_lower"], 6) if np.isfinite(row["hdi_lower"]) else None,
                round(row["hdi_upper"], 6) if np.isfinite(row["hdi_upper"]) else None,
            ])
        mh_table = make_table(
            "Multi-Horizon VaR Forecasts",
            ["Horizon (periods)", "VaR", "MC Std Error",
             "5% Lower", "95% Upper"],
            mh_rows,
        )

        # Plain English summary
        if violation_ratio < 0.8:
            coverage_desc = "too conservative (fewer violations than expected)"
        elif violation_ratio > 1.2:
            coverage_desc = "too aggressive (more violations than expected)"
        else:
            coverage_desc = "well-calibrated"

        test_pass = kupiec_pval > 0.05 and cc_pval > 0.05
        backtest_desc = "passes" if test_pass else "fails"

        plain_english = (
            f"CAViaR {spec} model estimated on '{name}' ({n} observations) "
            f"for the {theta*100:.1f}% quantile (VaR). "
            f"The model is {coverage_desc} with {n_violations} violations "
            f"(expected {expected_violations:.0f}, ratio {violation_ratio:.2f}). "
            f"The model {backtest_desc} backtesting at 5% significance "
            f"(Kupiec p={kupiec_pval:.4f}, Christoffersen p={cc_pval:.4f})."
        )

        if kupiec_pval <= 0.05:
            warnings.append("Kupiec test rejects correct unconditional coverage.")
        if cc_pval <= 0.05:
            warnings.append("Christoffersen test rejects violation independence.")
        if dq_pval <= 0.05:
            warnings.append("Dynamic Quantile test rejects model adequacy.")

        charting = (
            "Time series chart with the return series as a line and the dynamic quantile "
            f"(q_{theta:.2f}) as a dashed line below it. "
            "Highlight violation points (where return < quantile) with red markers. "
            "Optionally show a histogram of violations over rolling windows."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C6) ──────────────────────────
        # Parameter-name mapping so the spec can cite β-labels without
        # re-deriving the spec-to-name mapping.
        _parameter_names = list(pnames)

        # Multi-horizon audit fields (Follow-up 3a)
        multi_step_quantiles_audit = {}
        multi_step_mc_noise_audit = {}
        if multi_step_computed:
            for h in horizons:
                row = mh.get(int(h))
                if row is not None and np.isfinite(row["VaR"]):
                    multi_step_quantiles_audit[int(h)] = round(
                        float(row["VaR"]), 6,
                    )
                    multi_step_mc_noise_audit[int(h)] = round(
                        float(row["mc_std"]), 6,
                    )

        audit = {
            "specification": spec,
            "theta": theta,
            "quantile_theta": theta,  # alias to avoid T14 collision risk
            "parameter_names": _parameter_names,
            "parameters": [round(float(p), 6) for p in best_params],
            "quantile_loss": round(float(best_loss), 6),
            "n_violations": n_violations,
            "expected_violations": round(expected_violations, 2),
            "violation_ratio": round(violation_ratio, 4),
            "kupiec_stat": round(float(kupiec_stat), 4),
            "kupiec_pval": round(float(kupiec_pval), 6),
            "christoffersen_stat": round(float(cc_stat), 4),
            "christoffersen_pval": round(float(cc_pval), 6),
            "dq_stat": round(float(dq_stat), 4),
            "dq_pval": round(float(dq_pval), 6),
            "n_obs": n,
            "n_restarts": cfg["n_restarts"],
            "distribution_free": True,
            "series_name": name,
            # Follow-up 3a — multi-horizon audit fields
            "multi_step_computed": bool(multi_step_computed),
            "horizons_forecasted": list(horizons) if multi_step_computed else [],
            "multi_step_quantiles": multi_step_quantiles_audit,
            "multi_step_mc_paths": int(n_sim_paths) if multi_step_computed else None,
            "multi_step_mc_noise_std": multi_step_mc_noise_audit,
            "multi_step_residual_autocorr_lbq": (
                round(float(lb_pval), 6) if lb_pval is not None else None
            ),
            "caviar_stationarity_param": round(float(beta_1_param), 6),
            "caviar_effective_persistence": round(float(effective_persistence), 6),
            "caviar_stationarity_ok": bool(is_stationary),
            "one_step_ahead_var": round(float(one_step_ahead_var), 6),
            **format_significance_disclosure(
                test_name=(
                    "Kupiec unconditional coverage + Christoffersen "
                    "conditional coverage + Engle-Manganelli Dynamic "
                    "Quantile backtests"
                ),
                critical_value_formula=(
                    "chi-squared p-values from likelihood-ratio (Kupiec, "
                    "Christoffersen) and dynamic-quantile (DQ) tests"
                ),
                ac_corrected=True,
            ),
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("caviar_quantile_dynamics", dict(audit))

        return make_response(
            ctx,
            tables=[param_table, bt_table, mh_table, ts_table],
            plain_english_summary=plain_english,
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
            f"CAViaR estimation failed: {e}",
            error_fixes=[
                "Ensure the series represents returns.",
                "Try a different specification (SAV, AS, IG).",
                "Try the 'Thorough' preset for more optimization restarts.",
            ],
        )


def _get_initial_params(spec, y, theta, q0):
    """Generate random starting parameters for a given specification."""
    if spec == "SAV":
        beta0 = q0 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = -0.1 * np.std(y) * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2])
    elif spec == "AS":
        beta0 = q0 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = -0.05 * np.std(y) * (0.5 + np.random.rand())
        beta3 = 0.1 * np.std(y) * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2, beta3])
    else:  # IG
        # Note: the previous implementation assigned ``sigma = np.std(y)``
        # here but never used it in the IG initialization (the beta2
        # draw is scale-free). Removed as orphan per Prompt C6 D17.
        beta0 = q0 ** 2 * (1 - 0.9) * (0.5 + np.random.rand())
        beta1 = 0.85 + 0.1 * np.random.rand()
        beta2 = 0.1 * (0.5 + np.random.rand())
        return np.array([beta0, beta1, beta2])


def _compute_quantile_path(params, y, spec, q0):
    """Compute the dynamic quantile path given parameters."""
    n = len(y)
    q = np.zeros(n)
    q[0] = q0

    if spec == "SAV":
        b0, b1, b2 = params
        for t in range(1, n):
            q[t] = b0 + b1 * q[t - 1] + b2 * abs(y[t - 1])
    elif spec == "AS":
        b0, b1, b2, b3 = params
        for t in range(1, n):
            q[t] = b0 + b1 * q[t - 1] + b2 * max(y[t - 1], 0) + b3 * min(y[t - 1], 0)
    else:  # IG
        b0, b1, b2 = params
        for t in range(1, n):
            inside = b0 + b1 * q[t - 1] ** 2 + b2 * y[t - 1] ** 2
            q[t] = -np.sqrt(max(abs(inside), 1e-20))  # negative for left tail quantile

    return q


# ---------------------------------------------------------------------
# Follow-up 3a — Multi-horizon VaR forecasting helpers
# ---------------------------------------------------------------------


def _caviar_recurse_one_step(spec, params, q_prev, y_prev):
    """One step of the CAViaR recursion: (q_prev, y_prev) → q_next.

    Same logic as _compute_quantile_path but factored for forward
    simulation (computes one step given an arbitrary previous state,
    rather than iterating over the observed y array).
    """
    if spec == "SAV":
        b0, b1, b2 = params
        return b0 + b1 * q_prev + b2 * abs(y_prev)
    elif spec == "AS":
        b0, b1, b2, b3 = params
        return (
            b0 + b1 * q_prev
            + b2 * max(y_prev, 0.0) + b3 * min(y_prev, 0.0)
        )
    else:  # IG
        b0, b1, b2 = params
        inside = b0 + b1 * q_prev ** 2 + b2 * y_prev ** 2
        return -np.sqrt(max(abs(inside), 1e-20))


def _extract_stationarity_param(spec, params):
    """Return (beta_1, effective_persistence, is_stationary).

    Simple |β₁| < 1 is NOT sufficient for CAViaR multi-horizon
    stability because the recursion depends on |y| or y² which
    feeds back through q (simulated y = q + r, |y| ≈ |q| when
    q is far from zero). For a left-tail VaR (q < 0), the
    effective persistence under bootstrap simulation is:

      SAV:  β₁ + |β₂|       (|y| pushes q more negative when β₂ < 0)
      AS:   β₁ + max(|β₂|, |β₃|)   (worst-case asymmetric response)
      IG:   β₁ + β₂        (GARCH variance stationarity; q² recursion)

    The effective persistence must be < 1 for multi-horizon forecasts
    to stay bounded. We report the effective persistence as the
    primary stability quantity; β₁ alone is retained for parameter
    disclosure.
    """
    beta_1 = float(params[1])
    if spec == "SAV":
        beta_2 = float(params[2])
        effective = beta_1 + abs(beta_2)
        is_stationary = effective < 1.0
    elif spec == "AS":
        beta_2 = float(params[2])
        beta_3 = float(params[3])
        effective = beta_1 + max(abs(beta_2), abs(beta_3))
        is_stationary = effective < 1.0
    else:  # IG — variance-process recursion, β₁ + β₂ < 1 for stability
        beta_2 = float(params[2])
        effective = beta_1 + beta_2
        is_stationary = (beta_1 >= 0.0) and (effective < 1.0)
    return beta_1, float(effective), bool(is_stationary)


def _simulate_multi_horizon_paths(
    *, spec, params, q_T, y_T, r_in_sample, H_max, n_paths, rng,
):
    """Monte Carlo forward simulation for multi-horizon VaR.

    For each of n_paths simulated paths:
        1. Start at (q_prev, y_prev) = (q_T, y_T).
        2. At each horizon h in 1..H_max:
           a. q_next = CAViaR recursion from (q_prev, y_prev).
           b. r_sample = bootstrap from raw residuals r_in_sample.
           c. y_next = q_next + r_sample.
           d. advance (q_prev, y_prev) = (q_next, y_next).

    Returns dict with "y_sim" array of shape (n_paths, H_max).
    On numerical blow-up (non-stationary recursion), returns inf/nan
    gracefully; caller handles via graceful-degradation cascade (D12).
    """
    n_r = len(r_in_sample)
    if n_r == 0:
        raise ValueError("Empty residual array for bootstrap")
    y_sim = np.empty((n_paths, H_max), dtype=np.float64)

    # Precompute bootstrap indices for vectorized residual lookup
    idx_all = rng.integers(0, n_r, size=(n_paths, H_max))

    for n in range(n_paths):
        q_prev = float(q_T)
        y_prev = float(y_T)
        for h in range(H_max):
            q_next = _caviar_recurse_one_step(spec, params, q_prev, y_prev)
            r_sample = float(r_in_sample[idx_all[n, h]])
            y_next = q_next + r_sample
            y_sim[n, h] = y_next
            q_prev = q_next
            y_prev = y_next

    return {"y_sim": y_sim}


def _multi_horizon_quantiles_and_noise(
    *, y_sim, horizons, theta, B_subsamples=50, rng,
):
    """Compute θ-quantile + MC noise at each requested horizon.

    Uses sub-sample bootstrap for MC noise estimation (Phase 2 D11):
    subsample size = max(sqrt(n_paths), 100), B=50 subsamples, report
    std of the quantile estimator across subsamples.

    The 90% band is the 5th/95th percentile of simulated y at each
    horizon (Phase 2 Q6).

    Returns dict {h: {"VaR": float, "mc_std": float,
                       "hdi_lower": float, "hdi_upper": float}}.
    """
    n_paths, H_max = y_sim.shape
    subsample_size = max(int(np.sqrt(n_paths)), 100)
    subsample_size = min(subsample_size, n_paths)  # guard if N < 100

    out = {}
    for h in horizons:
        if h < 1 or h > H_max:
            continue
        yh = y_sim[:, h - 1]

        # Guard against non-finite values from a blown-up recursion
        finite_mask = np.isfinite(yh)
        if not finite_mask.any():
            out[int(h)] = {
                "VaR": float("nan"),
                "mc_std": float("nan"),
                "hdi_lower": float("nan"),
                "hdi_upper": float("nan"),
            }
            continue
        yh_finite = yh[finite_mask]

        # Point estimate: θ-quantile of simulated y
        VaR_h = float(np.quantile(yh_finite, theta))

        # 90% band from simulated y
        hdi_lo = float(np.quantile(yh_finite, 0.05))
        hdi_hi = float(np.quantile(yh_finite, 0.95))

        # MC noise via sub-sample bootstrap
        boot_q = np.empty(B_subsamples, dtype=np.float64)
        n_finite = len(yh_finite)
        ss = min(subsample_size, n_finite)
        for b in range(B_subsamples):
            idx = rng.integers(0, n_finite, size=ss)
            boot_q[b] = np.quantile(yh_finite[idx], theta)
        mc_std = float(np.std(boot_q, ddof=1)) if B_subsamples > 1 else 0.0

        out[int(h)] = {
            "VaR": VaR_h,
            "mc_std": mc_std,
            "hdi_lower": hdi_lo,
            "hdi_upper": hdi_hi,
        }
    return out


def _ljung_box_on_residuals(r, n_lags=10):
    """Ljung-Box test on raw residuals. Returns p-value or None.

    Used by D2 Tier 3 trigger to warn when bootstrap iid-resampling
    assumption is violated (residual autocorrelation present).
    """
    try:
        from statsmodels.stats.diagnostic import acorr_ljungbox
        if len(r) < n_lags + 2:
            return None
        result = acorr_ljungbox(r, lags=[n_lags], return_df=True)
        return float(result["lb_pvalue"].values[0])
    except Exception:
        return None


def _parse_horizons(raw):
    """Parse horizons param from either list or string.

    Catalog JSON stores horizons as a default string; user-param
    inputs may arrive as list (direct) or string (serialized).
    Defensive parse per Phase 2 D9.
    """
    if raw is None:
        return list(_DEFAULT_HORIZONS)
    if isinstance(raw, (list, tuple)):
        parsed = raw
    elif isinstance(raw, str):
        try:
            parsed = ast.literal_eval(raw)
        except Exception:
            return list(_DEFAULT_HORIZONS)
        if not isinstance(parsed, (list, tuple)):
            return list(_DEFAULT_HORIZONS)
    else:
        return list(_DEFAULT_HORIZONS)
    try:
        return sorted(set(int(h) for h in parsed if int(h) >= 1))
    except Exception:
        return list(_DEFAULT_HORIZONS)


def _quantile_loss(params, y, theta, spec, q0):
    """Compute the quantile regression loss (tick loss / check function)."""
    q = _compute_quantile_path(params, y, spec, q0)
    residuals = y - q
    loss = np.where(residuals >= 0, theta * residuals, (theta - 1) * residuals)
    return np.mean(loss)


def _kupiec_test(n, v, theta):
    """Kupiec (1995) unconditional coverage LR test."""
    if v == 0 or v == n:
        return 0.0, 1.0

    pi_hat = v / n
    lr = 2 * (v * np.log(pi_hat / theta) + (n - v) * np.log((1 - pi_hat) / (1 - theta)))
    from scipy.stats import chi2
    pval = 1 - chi2.cdf(lr, 1)
    return float(lr), float(pval)


def _christoffersen_test(violations, theta):
    """Christoffersen (1998) conditional-coverage test for violation
    clustering via first-order Markov chain. Prompt C6 D17 label fix:
    this is a conditional-coverage test (hit indicators form a Markov
    chain), not a pure "independence" test — the name was previously
    mislabeled. The Engle-Manganelli Dynamic Quantile test is a
    separate, stronger joint-coverage test that complements this one."""
    from scipy.stats import chi2
    v = violations.astype(int)
    n = len(v)

    # Transition counts
    n00, n01, n10, n11 = 0, 0, 0, 0
    for t in range(1, n):
        if v[t - 1] == 0 and v[t] == 0:
            n00 += 1
        elif v[t - 1] == 0 and v[t] == 1:
            n01 += 1
        elif v[t - 1] == 1 and v[t] == 0:
            n10 += 1
        else:
            n11 += 1

    # Transition probabilities
    pi01 = n01 / (n00 + n01) if (n00 + n01) > 0 else 0.0
    pi11 = n11 / (n10 + n11) if (n10 + n11) > 0 else 0.0
    pi = (n01 + n11) / (n - 1) if n > 1 else 0.0

    if pi01 <= 0 or pi11 <= 0 or pi <= 0 or pi01 >= 1 or pi11 >= 1 or pi >= 1:
        return 0.0, 1.0

    # LR independence
    lr_ind = 2 * (
        n00 * np.log(1 - pi01) + n01 * np.log(pi01) +
        n10 * np.log(1 - pi11) + n11 * np.log(pi11) -
        (n00 + n10) * np.log(1 - pi) - (n01 + n11) * np.log(pi)
    )

    if not np.isfinite(lr_ind) or lr_ind < 0:
        return 0.0, 1.0

    pval = 1 - chi2.cdf(lr_ind, 1)
    return float(lr_ind), float(pval)


def _dq_test(y, q, violations, theta, n_lags=4):
    """
    Engle & Manganelli Dynamic Quantile test.
    Regress hit indicator on lagged hits and current quantile.
    """
    from scipy.stats import chi2

    hit = violations.astype(float) - theta
    n = len(hit)

    if n <= n_lags + 2:
        return 0.0, 1.0

    # Build regressor matrix
    start = n_lags
    T = n - start
    Z = np.zeros((T, n_lags + 2))  # lags of hit + constant + quantile
    Z[:, 0] = 1.0  # constant
    for lag in range(1, n_lags + 1):
        Z[:, lag] = hit[start - lag:n - lag]
    Z[:, n_lags + 1] = q[start:n]

    hit_dep = hit[start:n]

    try:
        ZtZ_inv = np.linalg.inv(Z.T @ Z)
        DQ = hit_dep @ Z @ ZtZ_inv @ Z.T @ hit_dep / (theta * (1 - theta))
        k = Z.shape[1]
        pval = 1 - chi2.cdf(DQ, k)
        return float(DQ), float(pval)
    except np.linalg.LinAlgError:
        return 0.0, 1.0
