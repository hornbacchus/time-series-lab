"""
GARCH family models for Time Series Lab.

Fits GARCH, GJR-GARCH, or EGARCH models to the primary series using the
``arch`` package. These models capture time-varying volatility (heteroskedasticity)
and are commonly applied to financial returns data.
"""

import numpy as np
import warnings as _warnings
from arch import arch_model

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    format_significance_disclosure,
)

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None


def _prepare_series(values):
    """Strip edge NaN, interpolate interior."""
    first = 0
    while first < len(values) and np.isnan(values[first]):
        first += 1
    last = len(values) - 1
    while last >= 0 and np.isnan(values[last]):
        last -= 1
    if first > last:
        return np.array([]), 0
    trimmed = values[first:last + 1].copy()
    nan_count = int(np.isnan(trimmed).sum())
    if nan_count > 0:
        nans = np.where(np.isnan(trimmed))[0]
        valid = np.where(~np.isnan(trimmed))[0]
        if len(valid) >= 2:
            trimmed[nans] = np.interp(nans, valid, trimmed[valid])
        else:
            trimmed = trimmed[~np.isnan(trimmed)]
            nan_count = 0
    return trimmed, nan_count


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a GARCH-family model.

    Parameters (via ctx.params)
    ---------------------------
    vol : str, optional
        Volatility model: 'GARCH' (default), 'EGARCH', 'GJR-GARCH' (alias 'GJRGARCH').
    p : int, optional
        GARCH lag order. Default 1.
    q : int, optional
        ARCH lag order. Default 1.
    o : int, optional
        Asymmetry order (for GJR-GARCH / EGARCH). Default 1 if asymmetric model, else 0.
    mean : str, optional
        Mean model: 'Constant' (default), 'Zero', 'AR', 'ARX', 'HAR', 'LS'.
    dist : str, optional
        Error distribution: 'normal' (default), 't', 'skewt', 'ged'.
    horizon : int, optional
        Variance forecast horizon. Default 10.
    rescale : bool, optional
        Whether to rescale data (helps with convergence). Default True.
    """
    try:
        progress_callback("Validating inputs", 5)

        name, values = ctx.get_primary_series()
        warn_list = []

        clean, n_interp = _prepare_series(values)
        n = len(clean)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values linearly interpolated.")

        if n < 30:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. GARCH needs at least 30.",
                error_fixes=["Provide a longer time series, ideally 100+ observations."],
            )

        # Model specification.
        #
        # CAI Phase 2 Session 6 fix (F-G-DISPATCH): the catalog
        # exposes garch / gjr_garch / egarch as 3 separate technique
        # IDs but does NOT include `vol` in any variant's user-param
        # list. Without an explicit `vol` in ctx.params the wrapper
        # would default to "GARCH" — silently routing gjr_garch and
        # egarch invocations through vanilla GARCH math. Resolve
        # technique_id → variant-default for `vol` BEFORE reading the
        # user param so an explicit user `vol` still wins.
        _TID_VOL_MAP = {"gjr_garch": "GJR-GARCH", "egarch": "EGARCH"}
        if "vol" not in ctx.params and ctx.technique_id in _TID_VOL_MAP:
            vol_type = _TID_VOL_MAP[ctx.technique_id].upper().replace("-", "")
        else:
            vol_type = ctx.get_param("vol", "GARCH").upper().replace("-", "")
        if vol_type in ("GJRGARCH", "GJR"):
            vol_type = "GARCH"
            o_default = 1
            model_label = "GJR-GARCH"
        elif vol_type == "EGARCH":
            o_default = 1
            model_label = "EGARCH"
        else:
            vol_type = "GARCH"
            o_default = 0
            model_label = "GARCH"

        p_order = int(ctx.get_param("p", 1))
        q_order = int(ctx.get_param("q", 1))
        o_order = int(ctx.get_param("o", o_default))

        mean_model = ctx.get_param("mean", "Constant")
        dist = ctx.get_param("dist", "normal").lower()
        if dist not in ("normal", "t", "skewt", "ged"):
            warn_list.append(f"Unknown distribution '{dist}'. Using 'normal'.")
            dist = "normal"

        horizon = int(ctx.get_param("horizon", 10))
        rescale = ctx.get_param("rescale", True)

        progress_callback("Fitting GARCH model", 20)

        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            try:
                am = arch_model(
                    clean,
                    mean=mean_model,
                    vol=vol_type,
                    p=p_order,
                    q=q_order,
                    o=o_order,
                    dist=dist,
                    rescale=rescale,
                )
                fit = am.fit(disp="off", show_warning=False)
            except Exception as e1:
                # Fallback: simplest GARCH(1,1)
                warn_list.append(
                    f"{model_label}({p_order},{o_order},{q_order}) failed ({e1}). "
                    "Falling back to GARCH(1,1) with constant mean."
                )
                am = arch_model(clean, mean="Constant", vol="GARCH", p=1, q=1, dist="normal", rescale=True)
                fit = am.fit(disp="off", show_warning=False)
                model_label = "GARCH"
                p_order, q_order, o_order = 1, 1, 0

        if not fit.convergence_flag == 0:
            warn_list.append("Optimization did not fully converge. Results may be approximate.")

        progress_callback("Extracting results", 50)

        # Parameters
        params = fit.params
        param_rows = []
        for pname in params.index:
            pval = float(params[pname])
            try:
                se = float(fit.std_err[pname])
                tstat = float(fit.tvalues[pname])
                pvalue = float(fit.pvalues[pname])
                param_rows.append([
                    str(pname), round(pval, 6), round(se, 6),
                    round(tstat, 4), round(pvalue, 6),
                ])
            except Exception:
                param_rows.append([str(pname), round(pval, 6), None, None, None])

        param_table = make_table(
            "Parameter Estimates",
            ["Parameter", "Estimate", "Std Error", "t-Statistic", "P-Value"],
            param_rows,
        )

        # Conditional volatility
        cond_vol = fit.conditional_volatility
        cond_vol_arr = cond_vol.values if hasattr(cond_vol, 'values') else np.asarray(cond_vol)

        # Standardized residuals
        std_resid = fit.std_resid
        std_resid_arr = std_resid.values if hasattr(std_resid, 'values') else np.asarray(std_resid)

        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))

        # Build conditional volatility table (sample, not full)
        vol_rows = []
        # For large series, show every Nth row
        step = max(1, n // 200) if ctx.preset == "Fast" else max(1, n // 500)
        for i in range(0, n, step):
            vol_rows.append([
                time_col[i],
                clean[i],
                round(float(cond_vol_arr[i]), 6),
                round(float(std_resid_arr[i]), 4) if i < len(std_resid_arr) else None,
            ])
        vol_table = make_table(
            "Conditional Volatility",
            ["Time", name, "Cond. Volatility (sigma)", "Std. Residual"],
            vol_rows,
        )

        # Variance forecast.
        # arch's default `method='analytic'` only supports horizon=1
        # for EGARCH (Nelson's exponential parameterization has no
        # closed-form multi-step formula). Route EGARCH multi-step
        # forecasts to `method='simulation'`. Other engine-supported
        # variants (symmetric GARCH at o=0; GJR-GARCH at vol="GARCH"
        # + o>0 per _TID_VOL_MAP normalization) handle analytic
        # multi-step natively. Surfaced as S54 (egarch) wrapper-layer
        # check 3 failure with default analytic call returning
        # 1-row "Note" table instead of horizon-rows forecast.
        progress_callback("Forecasting volatility", 70)
        forecast_method = "simulation" if vol_type == "EGARCH" else "analytic"
        forecast_kwargs = {"horizon": horizon, "reindex": False,
                           "method": forecast_method}
        if forecast_method == "simulation":
            forecast_kwargs["simulations"] = 1000
        try:
            fc = fit.forecast(**forecast_kwargs)
            var_fc = fc.variance.values[-1] if hasattr(fc.variance, 'values') else np.asarray(fc.variance)[-1]
            vol_fc = np.sqrt(var_fc)
            fc_rows = []
            for i in range(horizon):
                fc_rows.append([
                    i + 1,
                    round(float(var_fc[i]), 6),
                    round(float(vol_fc[i]), 6),
                ])
            fc_table = make_table(
                "Volatility Forecast",
                ["Step", "Forecast Variance", "Forecast Volatility"],
                fc_rows,
            )
        except Exception as e:
            fc_table = make_table("Volatility Forecast", ["Note"], [[f"Forecast failed: {e}"]])
            warn_list.append(f"Volatility forecast failed: {e}")

        # Model diagnostics
        progress_callback("Diagnostics", 85)
        aic = float(fit.aic)
        bic = float(fit.bic)
        llf = float(fit.loglikelihood)

        diag_rows = [
            ["Model", f"{model_label}({p_order},{o_order},{q_order})" if o_order > 0 else f"{model_label}({p_order},{q_order})"],
            ["Mean Model", mean_model],
            ["Distribution", dist],
            ["AIC", round(aic, 2)],
            ["BIC", round(bic, 2)],
            ["Log-Likelihood", round(llf, 2)],
            ["Observations", n],
            ["Forecast Horizon", horizon],
        ]

        # Persistence calculation. Captured as locals so the
        # interpretation spec can read them without re-deriving from
        # the raw params index.
        #
        # CAI Phase 2 Session 6 fix (F-G-T2-EGARCH-PERSIST): the
        # formula alpha + beta + 0.5*gamma is GARCH-family-specific
        # (variance-level dynamics). EGARCH parameterizes
        # log-variance: log(sigma2_t) = omega + beta*log(sigma2_{t-1})
        # + alpha*g(z_{t-1}). Stationarity for EGARCH requires only
        # |beta| < 1; alpha is a magnitude-of-news coefficient, not a
        # variance lag. Pre-fix, the wrapper applied the GARCH formula
        # universally, which made EGARCH persistence appear > 1.0 on
        # 4 of 5 macro real-data series and triggered a misleading
        # IGARCH-style warning. Post-fix, EGARCH persistence reports
        # |beta| with a model-appropriate label.
        alpha_sum = None
        beta_sum = None
        persistence = None
        try:
            alpha_sum = sum(float(params[p]) for p in params.index if p.startswith("alpha"))
            beta_sum = sum(float(params[p]) for p in params.index if p.startswith("beta"))
            gamma_sum = sum(float(params[p]) for p in params.index if p.startswith("gamma"))
            if model_label == "EGARCH":
                # EGARCH: persistence is the log-variance AR coefficient
                # (sum of beta[i]); |beta| < 1 implies stationarity.
                persistence = beta_sum
                _persist_label = "Persistence (beta, EGARCH log-variance)"
            else:
                persistence = alpha_sum + beta_sum + 0.5 * gamma_sum
                _persist_label = "Persistence (alpha+beta+0.5*gamma)"
            diag_rows.append([_persist_label, round(persistence, 6)])
            if abs(persistence) >= 1.0:
                if model_label == "EGARCH":
                    warn_list.append(
                        f"EGARCH log-variance persistence |beta|="
                        f"{abs(persistence):.4f} >= 1. The fitted model "
                        "implies near-integrated log-variance dynamics; "
                        "shocks decay very slowly."
                    )
                else:
                    warn_list.append(
                        f"Volatility persistence ({persistence:.4f}) >= 1. "
                        "The model implies integrated (IGARCH) behaviour; shocks never fully decay."
                    )
            elif abs(persistence) > 0.95:
                warn_list.append(
                    f"High volatility persistence ({persistence:.4f}). "
                    "Shocks to volatility are very long-lived."
                )
        except Exception:
            pass

        # Ljung-Box on squared standardized residuals
        ljung_box_sq_p = None
        try:
            from statsmodels.stats.diagnostic import acorr_ljungbox
            sq_resid = std_resid_arr[~np.isnan(std_resid_arr)] ** 2
            if len(sq_resid) > 15:
                lb = acorr_ljungbox(sq_resid, lags=[10], return_df=True)
                for _, row in lb.iterrows():
                    diag_rows.append([
                        f"Ljung-Box Sq. Resid Lag {int(row.name)}",
                        f"Q={round(row['lb_stat'], 4)}, p={round(row['lb_pvalue'], 6)}"
                    ])
                    if ljung_box_sq_p is None:
                        ljung_box_sq_p = float(row["lb_pvalue"])
                    if row['lb_pvalue'] < 0.05:
                        warn_list.append(
                            "Remaining ARCH effects in squared residuals (Ljung-Box p < 0.05). "
                            "Consider higher order GARCH or a different specification."
                        )
        except Exception:
            pass

        diag_table = make_table("Model Diagnostics", ["Metric", "Value"], diag_rows)

        # Plain English
        plain = (
            f"{model_label} model fitted to '{name}' ({n} observations, {dist} distribution). "
            f"AIC={aic:.1f}, BIC={bic:.1f}."
        )
        try:
            avg_vol = float(np.mean(cond_vol_arr))
            plain += f" Average conditional volatility: {avg_vol:.4f}."
        except Exception:
            pass
        if o_order > 0:
            plain += (
                " The asymmetric specification captures leverage effects "
                "(negative shocks may have a different impact on volatility than positive ones)."
            )
        plain += f" {horizon}-step volatility forecast produced."

        charting = (
            "Two-panel chart: top panel shows the series with conditional volatility bands "
            "(+/- 2 sigma); bottom panel shows conditional volatility over time. "
            "Forecast continuation on the volatility panel."
        )

        progress_callback("Done", 100)

        interp = build_interpretation("garch_model", {
            "series_name": name,
            "n_obs": n,
            "dist": dist.capitalize() if isinstance(dist, str) else str(dist),
            "order_p": p_order,
            "order_q": q_order,
            "alpha": float(alpha_sum) if alpha_sum is not None else 0.0,
            "beta": float(beta_sum) if beta_sum is not None else 0.0,
            "persistence": float(persistence) if persistence is not None else 0.0,
            "ljung_box_sq_p": ljung_box_sq_p,
        })

        return make_response(
            ctx,
            tables=[param_table, diag_table, vol_table, fc_table],
            plain_english_summary=plain,
            warnings=warn_list,
            charting_suggestions=charting,
            interpretation=interp,
            audit_fields={
                "model": model_label,
                "p": p_order,
                "q": q_order,
                "o": o_order,
                "mean": mean_model,
                "dist": dist,
                "aic": round(aic, 2),
                "bic": round(bic, 2),
                "log_likelihood": round(llf, 2),
                "horizon": horizon,
                **format_significance_disclosure(
                    test_name=(
                        f"{model_label} MLE t-tests + Ljung-Box on squared "
                        "standardized residuals"
                    ),
                    critical_value_formula=(
                        "arch package MLE standard errors; two-sided t-tests; "
                        "Ljung-Box on standardized² via "
                        "statsmodels.stats.diagnostic.acorr_ljungbox"
                    ),
                    ac_corrected=True,
                ),
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"GARCH model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "GARCH works best on returns or stationary series. "
                "Try differencing or taking log-returns first.",
                "For convergence issues, try rescale=True or a simpler model (GARCH(1,1)).",
                "Check that the series has sufficient variance (not near-constant).",
            ],
        )
