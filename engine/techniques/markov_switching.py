"""
Markov-Switching Regression Model for Time Series Lab.

Fits a Markov-switching model using statsmodels MarkovRegression.
Allows regime-dependent mean, variance, and autoregressive parameters.
"""

import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.regime_switching.markov_regression import MarkovRegression
from statsmodels.tsa.regime_switching.markov_autoregression import MarkovAutoregression

try:
    from interpretation import build_interpretation  # type: ignore
except Exception:
    def build_interpretation(technique_id, results):  # type: ignore
        return None

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    label_regimes_by_dominant_key,
    build_forecast_time_axis,
    stationary_distribution,
)


# ---------------------------------------------------------------------------
# Forecast-construction helpers
# ---------------------------------------------------------------------------
# statsmodels' MarkovRegression and MarkovAutoregression expose a
# ``.predict()`` / ``.forecast()`` signature but both raise
# NotImplementedError on any multi-step call. Per §4.3 the library is
# inviting the caller to do this construction from fitted quantities —
# the transition matrix and the final filtered regime probabilities are
# all we need for the probability-path recursion, and ``fit.params``
# plus ``fit.model.param_names`` supply the per-regime constants and AR
# coefficients for the conditional-mean recursion.

# _stationary_distribution promoted to engine/techniques/base.py as
# `stationary_distribution` during Prompt C1 (second consumer: HMM spec).
_stationary_distribution = stationary_distribution


def _extract_ar_params(param_names, params_native, k_regimes, order):
    """Pull per-regime constants and AR coefficients from the fit's
    parameter vector in native (statsmodels) regime order.

    Returns
    -------
    consts_native : ndarray (k_regimes,)
        const[j] for native regime index j. Entries default to 0.0
        when a name is missing (e.g., non-switching trend across
        regimes produces a single "const" without a regime index).
    ar_coefs_native : ndarray (k_regimes, order)
        ar.L{lag}[j] for native regime j and lag index ``lag - 1``.
        Non-switching AR produces a single "ar.L{lag}" name without
        regime index; that value is broadcast across all regimes.
    """
    consts_native = np.zeros(k_regimes)
    ar_coefs_native = np.zeros((k_regimes, max(order, 1)))
    for idx, pname in enumerate(param_names):
        try:
            val = float(params_native[idx])
        except (TypeError, ValueError, IndexError):
            continue
        if pname.startswith("const["):
            try:
                j = int(pname[len("const["):-1])
                if 0 <= j < k_regimes:
                    consts_native[j] = val
            except ValueError:
                continue
        elif pname == "const":
            # Non-switching constant: broadcast to all regimes.
            consts_native[:] = val
        elif pname.startswith("ar.L"):
            rest = pname[len("ar.L"):]
            if "[" in rest:
                lag_str, regime_str = rest.split("[", 1)
                try:
                    lag = int(lag_str) - 1
                    j = int(regime_str.rstrip("]"))
                    if 0 <= j < k_regimes and 0 <= lag < order:
                        ar_coefs_native[j, lag] = val
                except ValueError:
                    continue
            else:
                # Non-switching AR: broadcast.
                try:
                    lag = int(rest) - 1
                    if 0 <= lag < order:
                        ar_coefs_native[:, lag] = val
                except ValueError:
                    continue
    return consts_native, ar_coefs_native


def _fit_benchmark(filled, order):
    """Fit a single-regime reference model with matching AR order.

    Used to convert the Markov Switching RMSE from an absolute number
    into a lift metric: how much does the regime-switching
    specification reduce in-sample error over the simplest same-order
    alternative?

    - ``order == 0``  → constant-mean benchmark
      (RMSE reduces to the sample standard deviation of ``filled``).
      Name: ``"constant mean"``.
    - ``order >= 1``  → statsmodels ARIMA(order, 0, 0) benchmark.
      Name: ``"AR({order})"``.

    Benchmark RMSE is computed against the same ``filled`` series the
    Markov fit used, so the denominator is consistent. The first
    ``order`` residuals of the ARIMA fit are dropped to match the
    AR-initialization window dropped from the Markov residual vector.

    Returns
    -------
    (benchmark_rmse, benchmark_name) : tuple
        Both ``None`` when the benchmark fit raises an exception; the
        caller emits a warning and omits the benchmark rows. The main
        Markov fit is unaffected.
    """
    try:
        y = np.asarray(filled, dtype=float)
        if order == 0:
            mu = float(np.mean(y))
            rmse = float(np.sqrt(np.mean((y - mu) ** 2)))
            return rmse, "constant mean"
        # order >= 1
        arima_fit = ARIMA(y, order=(order, 0, 0)).fit()
        resid = np.asarray(arima_fit.resid, dtype=float)
        # Match the Markov wrapper's AR-init drop: skip the first
        # `order` residuals where the AR term has no history.
        if len(resid) > order:
            resid = resid[order:]
        valid = resid[np.isfinite(resid)]
        if len(valid) == 0:
            return None, None
        rmse = float(np.sqrt(np.mean(valid ** 2)))
        return rmse, f"AR({order})"
    except Exception:
        return None, None


def _build_forecast(
    *,
    order,
    horizon,
    transition_matrix,
    pi_T,
    sort_order,
    regime_means_sorted,
    regime_stds_sorted,
    last_observations,
    param_names,
    params_native,
):
    """Construct h-step regime-probability, conditional-mean, and
    conditional-variance forecasts for a Markov-switching fit.

    All sorted-aligned inputs must be permuted according to the wrapper's
    post-fit labeling decision (``sort_axis`` mean-dominant or
    std-dominant); ``sort_order`` supplies the native → sorted
    permutation for mapping native-order fit.params entries to the
    sorted column layout used by ``pi_T`` and ``transition_matrix``.

    Method selection:
      order == 0 → "transition_matrix_closed_form": the mean forecast
        reduces to ``pi_h @ regime_means_sorted`` with no AR
        recursion.
      order >= 1 → "iterated_regime_weighted" (Hamilton 1994 /
        Kim-Nelson 1999): at each horizon, compute per-regime one-step
        conditional means given the AR history, weight by pi_h, append
        the weighted mean to the history as if realized, and iterate.
        Biased at long horizons when the implied regime path is
        uncertain; disclosed in Tier 2 output.

    Variance construction uses the law of total variance across
    regimes (within + between). Three sources of variance are NOT
    compounded: AR-innovation variance across forecast horizons;
    parameter estimation uncertainty; and non-Gaussian within-regime
    emissions. All three are disclosed in the audit field and Tier 2.

    Returns
    -------
    dict with keys
        regime_probs_forecast : (horizon, k) ndarray  (sorted columns)
        mean_forecast         : (horizon,) ndarray
        variance_forecast     : (horizon,) ndarray
        lower_95 / upper_95   : (horizon,) ndarray
        stationary_distribution : (k,) ndarray       (sorted order)
        method                : str
    """
    P = np.asarray(transition_matrix, dtype=float)
    k = P.shape[0]
    pi_T_arr = np.asarray(pi_T, dtype=float).reshape(-1)
    if pi_T_arr.shape[0] != k:
        raise ValueError(
            f"pi_T length {pi_T_arr.shape[0]} does not match "
            f"transition matrix dim {k}"
        )

    # --- P.2 regime probability recursion ---
    regime_probs_forecast = np.empty((horizon, k))
    P_power = np.eye(k)
    for h in range(horizon):
        P_power = P_power @ P
        regime_probs_forecast[h] = pi_T_arr @ P_power

    stationary = _stationary_distribution(P)

    # --- P.3 conditional mean construction ---
    method = ("transition_matrix_closed_form" if order == 0
              else "iterated_regime_weighted")

    regime_means_sorted_arr = np.asarray(regime_means_sorted, dtype=float)
    regime_stds_sorted_arr = np.asarray(regime_stds_sorted, dtype=float)

    # Per-horizon per-regime conditional mean matrix — (horizon, k).
    # Needed for both the mean forecast and the between-regime
    # variance contribution.
    per_regime_h = np.empty((horizon, k))

    if order == 0:
        # Closed form: every horizon's per-regime mean is just the
        # regime's unconditional mean.
        per_regime_h[:] = regime_means_sorted_arr
        mean_forecast = regime_probs_forecast @ regime_means_sorted_arr
    else:
        # Extract native-order per-regime constants and AR coefficients.
        consts_native, ar_coefs_native = _extract_ar_params(
            param_names, params_native, k, order
        )
        # Permute to sorted regime order so columns align with pi_h.
        sort_order_arr = np.asarray(sort_order, dtype=int)
        consts_sorted = consts_native[sort_order_arr]
        ar_coefs_sorted = ar_coefs_native[sort_order_arr]

        # Build y_history starting from the last ``order`` observed
        # values. Appending forecasts as if realized is the iterated
        # convention (Note 1); bias is disclosed in Tier 2.
        y_history = list(np.asarray(last_observations, dtype=float))
        # Guard: if last_observations is shorter than order, pad with
        # the overall mean (rare — happens only when n <= order at fit
        # time, which the wrapper's min-obs check prevents).
        while len(y_history) < order:
            y_history.insert(
                0, float(np.mean(regime_means_sorted_arr))
            )

        mean_forecast = np.empty(horizon)
        for h in range(horizon):
            # For each sorted regime j compute the one-step conditional
            # mean given current y_history:
            #   ŷ_h(j) = const[j] + Σ_lag ar[j, lag] * (y_{-(lag+1)} - const[j])
            for j in range(k):
                ar_contrib = 0.0
                for lag in range(order):
                    ar_contrib += ar_coefs_sorted[j, lag] * (
                        y_history[-lag - 1] - consts_sorted[j]
                    )
                per_regime_h[h, j] = consts_sorted[j] + ar_contrib
            mean_forecast[h] = float(
                regime_probs_forecast[h] @ per_regime_h[h]
            )
            # Iterated convention: treat ŷ_h as realized for next step.
            y_history.append(mean_forecast[h])

    # --- P.4 conditional variance via law of total variance ---
    variance_forecast = np.empty(horizon)
    sigma2_sorted = regime_stds_sorted_arr ** 2
    for h in range(horizon):
        within = float(regime_probs_forecast[h] @ sigma2_sorted)
        between = float(
            regime_probs_forecast[h]
            @ (per_regime_h[h] - mean_forecast[h]) ** 2
        )
        variance_forecast[h] = within + between

    z = 1.96
    sd = np.sqrt(np.maximum(variance_forecast, 0.0))
    lower_95 = mean_forecast - z * sd
    upper_95 = mean_forecast + z * sd

    return {
        "regime_probs_forecast": regime_probs_forecast,
        "mean_forecast": mean_forecast,
        "variance_forecast": variance_forecast,
        "lower_95": lower_95,
        "upper_95": upper_95,
        "stationary_distribution": stationary,
        "method": method,
    }


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"k_regimes": 2, "order": 0, "switching_variance": False, "maxiter": 200},
    "Balanced": {"k_regimes": 2, "order": 1, "switching_variance": True, "maxiter": 500},
    "Thorough": {"k_regimes": 3, "order": 2, "switching_variance": True, "maxiter": 1000},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a Markov-switching regression model.

    Parameters (via ctx.params)
    ---------------------------
    k_regimes : int, optional
        Number of regimes. Default 2 (Fast/Balanced) or 3 (Thorough).
    order : int, optional
        Autoregressive order for each regime. Preset-dependent.
    switching_variance : bool, optional
        Allow variance to differ across regimes. Preset-dependent.
    switching_trend : bool, optional
        Allow intercept to differ across regimes. Default True.
    horizon : int
        Forecast horizon. Default 10.

    Series layout
    -------------
    First series -> observed time series.
    Additional series -> exogenous regressors (optional).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Exogenous
        all_series = ctx.get_all_series()
        exog_arrays = []
        exog_names = []
        for sname, svals in all_series[1:]:
            if len(svals) >= n:
                exog_arrays.append(svals[:n])
                exog_names.append(sname)

        if exog_arrays:
            exog = np.column_stack(exog_arrays)
        else:
            exog = None

        # Handle NaN
        nan_count = int(np.isnan(values).sum())
        if nan_count > 0 and nan_count < n - 10:
            warnings.append(f"{nan_count} missing values linearly interpolated.")
            filled = values.copy()
            nans = np.where(np.isnan(filled))[0]
            valid = np.where(~np.isnan(filled))[0]
            filled[nans] = np.interp(nans, valid, filled[valid])
            if exog is not None:
                for col in range(exog.shape[1]):
                    nans_e = np.where(np.isnan(exog[:, col]))[0]
                    valid_e = np.where(~np.isnan(exog[:, col]))[0]
                    if len(nans_e) > 0 and len(valid_e) > 2:
                        exog[nans_e, col] = np.interp(nans_e, valid_e, exog[valid_e, col])
        elif nan_count >= n - 10:
            return make_error_response(ctx, "Too few non-missing values to fit Markov-switching model.")
        else:
            filled = values

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        k_regimes = int(ctx.get_param("k_regimes", cfg["k_regimes"]))
        order = int(ctx.get_param("order", cfg["order"]))
        switching_var = ctx.get_param("switching_variance", cfg["switching_variance"])
        switching_trend = ctx.get_param("switching_trend", True)
        horizon = max(1, int(ctx.get_param("horizon", 10)))
        maxiter = cfg["maxiter"]

        if k_regimes < 2:
            k_regimes = 2
            warnings.append("k_regimes must be >= 2. Set to 2.")
        if k_regimes > 4:
            k_regimes = 4
            warnings.append("k_regimes capped at 4 to avoid over-parameterization.")

        min_obs = k_regimes * (order + 3) * 3
        if n < min_obs:
            return make_error_response(
                ctx,
                f"Only {n} observations for {k_regimes} regimes with AR({order}). "
                f"Need at least {min_obs}.",
                error_fixes=["Reduce k_regimes or order, or provide more data."],
            )

        progress_callback(f"Fitting Markov-switching model ({k_regimes} regimes)", 20)

        try:
            # Class selection by `order` semantics:
            #   order == 0 → MarkovRegression (plain MS, no AR)
            #   order >= 1 → MarkovAutoregression (genuine MS-AR, per
            #               Hamilton 1989). `switching_ar=True` lets the
            #               AR coefficients differ by regime, which is
            #               what the user-facing "AR Order" claim and the
            #               preset defaults have always implied.
            # Pre-change behavior: MarkovRegression silently accepted
            # `order` but interpreted it as regime-likelihood dependence,
            # NOT as AR lag polynomial — so order >= 1 never actually
            # fitted any AR terms. This conditional fixes that.
            if order >= 1:
                model = MarkovAutoregression(
                    filled,
                    k_regimes=k_regimes,
                    order=order,
                    trend="c",
                    switching_ar=True,
                    switching_trend=switching_trend,
                    switching_variance=switching_var,
                    exog=exog,
                )
            else:
                model = MarkovRegression(
                    filled,
                    k_regimes=k_regimes,
                    order=0,
                    trend="c",
                    switching_trend=switching_trend,
                    switching_variance=switching_var,
                    exog=exog,
                )
            fit = model.fit(maxiter=maxiter, search_reps=25)
        except Exception as e1:
            # Fallback: simpler model
            warnings.append(f"Full model failed ({e1}). Trying simpler specification.")
            try:
                model = MarkovRegression(
                    filled,
                    k_regimes=2,
                    order=0,
                    trend="c",
                    switching_trend=True,
                    switching_variance=False,
                )
                fit = model.fit(maxiter=maxiter, search_reps=25)
                k_regimes = 2
                order = 0
                switching_var = False
            except Exception as e2:
                return make_error_response(
                    ctx,
                    f"Markov-switching model failed: {e2}",
                    error_fixes=[
                        "Ensure data is numeric and not constant.",
                        "Try k_regimes=2 with order=0.",
                    ],
                )

        progress_callback("Extracting regime probabilities", 55)

        # Smoothed regime probabilities
        smoothed_probs = fit.smoothed_marginal_probabilities
        if hasattr(smoothed_probs, 'values'):
            smoothed_probs = smoothed_probs.values
        smoothed_probs = np.asarray(smoothed_probs)
        if smoothed_probs.ndim == 1:
            smoothed_probs = smoothed_probs.reshape(-1, 1)

        # Most likely regime at each time
        n_probs = smoothed_probs.shape[0]
        most_likely_regime = np.argmax(smoothed_probs, axis=1)

        # Fitted values
        fitted = fit.fittedvalues
        if hasattr(fitted, 'values'):
            fitted = fitted.values
        fitted = np.asarray(fitted, dtype=np.float64)
        if len(fitted) < n:
            fitted = np.concatenate([np.full(n - len(fitted), np.nan), fitted])
        residuals = filled - fitted

        progress_callback("Extracting regime parameters", 65)

        # Regime-specific parameters — route through `fit.model.param_names`
        # per the canonical statsmodels-wrapping pattern documented in
        # engine/techniques/NOTES_statsmodels_params.md. `fit.params` is
        # an ndarray for MarkovRegression/MarkovAutoregression (not a
        # pandas Series), so `.index` would fall through to the
        # placeholder "p0..pN" labels and hide meaningful names like
        # "p[0->0]", "const[0]", "ar.L1[0]". Name source is the
        # underlying model (guaranteed list[str] on both classes).
        params = np.asarray(fit.params)
        param_names_list = list(
            getattr(fit, "param_names", None)
            or getattr(getattr(fit, "model", None), "param_names", None)
            or [f"p{i}" for i in range(len(params))]
        )

        # Transition matrix
        transition_matrix = np.zeros((k_regimes, k_regimes))
        for i, pn in enumerate(param_names_list):
            if 'p[' in pn.lower() or 'regime_transition' in pn.lower():
                try:
                    val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
                    # Parse indices from parameter name
                    # e.g., "p[0->0]" or similar patterns
                    pass
                except Exception:
                    pass

        # Try to extract transition matrix from model. statsmodels
        # returns `regime_transition` in COLUMN-stochastic convention:
        # regime_transition[i, j, t] = P(S_{t+1} = i | S_t = j), so
        # columns sum to 1 and rows don't. Transpose to the row-
        # stochastic convention used everywhere else in this wrapper
        # (display: "From Regime i" rows, forecast recursion:
        # pi_T @ P, fallback transition-count path: [prev, curr]).
        # This was a latent display bug before the forecast landing:
        # "From Regime 0" row actually showed P(→ 0 | ← j) values.
        try:
            tp = fit.regime_transition
            if hasattr(tp, 'values'):
                tp = tp.values
            transition_matrix = np.asarray(tp)
            if transition_matrix.ndim == 3:
                transition_matrix = transition_matrix[:, :, 0]
            transition_matrix = transition_matrix.T
        except Exception:
            # Build from smoothed probabilities
            for t in range(1, n_probs):
                r_prev = most_likely_regime[t - 1]
                r_curr = most_likely_regime[t]
                if r_prev < k_regimes and r_curr < k_regimes:
                    transition_matrix[r_prev, r_curr] += 1
            row_sums = transition_matrix.sum(axis=1, keepdims=True)
            row_sums[row_sums == 0] = 1
            transition_matrix = transition_matrix / row_sums

        # Sort regimes deterministically by empirical mean so "Regime 0" is
        # always the lowest-mean regime across runs. statsmodels'
        # MarkovRegression assigns regime indices based on EM starting
        # point — without this step, otherwise-identical runs can produce
        # charts where the "high" and "low" labels swap between sessions.
        # fit.params does not get remapped (the parameter names like
        # "const[0]" are opaque strings); the Parameters table shows them
        # as-returned and is documented as such.
        regime_means_empirical = np.zeros(k_regimes)
        regime_stds_empirical = np.zeros(k_regimes)
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            count_r = int(mask_r.sum())
            if count_r > 0:
                regime_means_empirical[r] = np.mean(filled[:n_probs][mask_r])
                # ddof=1 matches the Regime Summary table below; regimes
                # with count=1 get 0.0 std, treated as degenerate by the
                # dominant-key helper (→ mean-axis fallback).
                regime_stds_empirical[r] = (
                    float(np.std(filled[:n_probs][mask_r], ddof=1))
                    if count_r > 1 else 0.0
                )
            else:
                regime_means_empirical[r] = np.nan
                regime_stds_empirical[r] = np.nan
        # Preserve NaN regimes at the end of the sort order
        finite_mask = ~np.isnan(regime_means_empirical)
        sort_axis = "mean"
        sort_order = np.arange(k_regimes, dtype=int)
        if finite_mask.sum() >= 2:
            sort_result = label_regimes_by_dominant_key(
                regime_means_empirical,
                regime_stds_empirical,
                transmat=transition_matrix,
                labels=most_likely_regime,
                probs=smoothed_probs,
            )
            most_likely_regime = sort_result["labels"]
            smoothed_probs = sort_result["probs"]
            transition_matrix = sort_result["transmat"]
            sort_axis = sort_result["axis_name"]
            sort_order = np.asarray(sort_result["order"], dtype=int)
            if sort_axis == "std":
                vr = sort_result["variance_ratio"]
                msr = sort_result["mean_sep_in_min_sigma"]
                warnings.append(
                    f"Regimes have been sorted by empirical standard "
                    f"deviation (variance ratio {vr:.1f}× dominates mean "
                    f"separation {msr:.2f}σ). \"Regime 0\" is the "
                    f"lowest-σ state. To override, re-run with "
                    f"switching_variance=False. Model parameters in the "
                    f"Parameters table retain the statsmodels-native "
                    f"regime indices (which may differ from the sorted "
                    f"labels)."
                )
            else:
                warnings.append(
                    "Regimes have been sorted by empirical mean so that "
                    "\"Regime 0\" is the lowest-mean state. Model parameters "
                    "in the Parameters table retain the statsmodels-native "
                    "regime indices (which may differ from the sorted labels)."
                )

        progress_callback("Building output tables", 75)

        tables = []

        # ---- Regime probabilities table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= n_probs else list(range(1, n_probs + 1))
        prob_rows = []
        for t in range(n_probs):
            row = [time_col[t] if t < len(time_col) else t + 1]
            row.append(float(filled[t]) if t < n else None)
            for r in range(min(k_regimes, smoothed_probs.shape[1])):
                row.append(round(float(smoothed_probs[t, r]), 4))
            row.append(int(most_likely_regime[t]))
            prob_rows.append(row)
        regime_cols = [f"P(Regime {r})" for r in range(min(k_regimes, smoothed_probs.shape[1]))]
        tables.append(make_table(
            "Regime Probabilities",
            ["Time", name] + regime_cols + ["Most Likely Regime"],
            prob_rows,
        ))

        # ---- Transition matrix ----
        trans_rows = []
        for i in range(k_regimes):
            row = [f"From Regime {i}"]
            for j in range(k_regimes):
                row.append(round(float(transition_matrix[i, j]), 4) if i < transition_matrix.shape[0] and j < transition_matrix.shape[1] else None)
            trans_rows.append(row)
        tables.append(make_table(
            "Transition Matrix",
            [""] + [f"To Regime {j}" for j in range(k_regimes)],
            trans_rows,
        ))

        # ---- All parameters ----
        param_rows = []
        for i, pn in enumerate(param_names_list):
            val = float(params.iloc[i] if hasattr(params, 'iloc') else params[i])
            param_rows.append([pn, round(val, 6)])
        # TODO: rename to "Estimated Parameters" to match the cross-wrapper
        # naming convention — see engine/techniques/README.md
        tables.append(make_table("Model Parameters", ["Parameter", "Value"], param_rows))

        # ---- Regime summary ----
        regime_summary_rows = []
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            count_r = int(mask_r.sum())
            pct_r = count_r / n_probs * 100 if n_probs > 0 else 0.0
            mean_r = float(np.mean(filled[:n_probs][mask_r])) if count_r > 0 else None
            std_r = float(np.std(filled[:n_probs][mask_r], ddof=1)) if count_r > 1 else None
            regime_summary_rows.append([
                f"Regime {r}",
                count_r,
                round(pct_r, 1),
                round(mean_r, 4) if mean_r is not None else None,
                round(std_r, 4) if std_r is not None else None,
            ])
        tables.append(make_table(
            "Regime Summary",
            ["Regime", "Periods", "% of Time", "Mean", "Std Dev"],
            regime_summary_rows,
        ))

        # ---- Forecast ----
        # Manual regime-weighted construction. statsmodels'
        # MarkovRegression and MarkovAutoregression both raise
        # NotImplementedError on their .predict/.forecast entry points
        # (stubs with signatures but no bodies) — the library invites
        # the caller to do this construction from fitted quantities per
        # §4.3. See _build_forecast for the mean/variance math and the
        # iterated-regime-weighted convention under order >= 1.
        progress_callback("Generating forecasts", 85)
        forecast_method = None
        stationary_distribution = None
        final_horizon_probs = None
        try:
            # Permute empirical regime stats to sorted column order so
            # they align with pi_T / transition_matrix columns.
            regime_means_sorted = regime_means_empirical[sort_order]
            regime_stds_sorted = regime_stds_empirical[sort_order]
            # Replace any NaN (rare: regimes with zero decoded periods)
            # with 0.0 to keep the forecast math finite; their
            # contribution is gated by pi_h[h, j] which will be near
            # zero in practice.
            regime_means_sorted = np.where(
                np.isfinite(regime_means_sorted), regime_means_sorted, 0.0
            )
            regime_stds_sorted = np.where(
                np.isfinite(regime_stds_sorted) & (regime_stds_sorted > 0),
                regime_stds_sorted, 0.0,
            )

            # π_T: the final smoothed regime-probability vector
            # (sorted columns via the earlier sort_result).
            pi_T = smoothed_probs[-1, :] if n_probs > 0 else np.ones(k_regimes) / k_regimes

            # Last `order` observations from the filled series feed the
            # AR recursion (order=0: list is empty and unused).
            last_observations = (
                filled[-order:].tolist() if order > 0 else []
            )

            param_names_list_nat = list(
                getattr(fit, "param_names", None)
                or getattr(getattr(fit, "model", None), "param_names", None)
                or [f"p{i}" for i in range(len(params))]
            )
            params_native_arr = np.asarray(params, dtype=float)

            fc = _build_forecast(
                order=order,
                horizon=horizon,
                transition_matrix=transition_matrix,
                pi_T=pi_T,
                sort_order=sort_order,
                regime_means_sorted=regime_means_sorted,
                regime_stds_sorted=regime_stds_sorted,
                last_observations=last_observations,
                param_names=param_names_list_nat,
                params_native=params_native_arr,
            )
            forecast_method = fc["method"]
            stationary_distribution = fc["stationary_distribution"]
            final_horizon_probs = fc["regime_probs_forecast"][-1]

            fc_time_axis = build_forecast_time_axis(
                ctx.time[-1] if ctx.time else None,
                ctx.frequency or "",
                horizon,
            )

            fc_rows = []
            for h in range(horizon):
                row = [
                    fc_time_axis[h],
                    round(float(fc["mean_forecast"][h]), 6),
                    round(float(fc["lower_95"][h]), 6),
                    round(float(fc["upper_95"][h]), 6),
                ]
                for r in range(k_regimes):
                    row.append(round(float(fc["regime_probs_forecast"][h, r]), 4))
                fc_rows.append(row)
            prob_cols = [f"P(Regime {r})" for r in range(k_regimes)]
            tables.append(make_table(
                "Forecast",
                ["Time", "Mean Forecast", "Lower 95%", "Upper 95%"] + prob_cols,
                fc_rows,
            ))
        except Exception as fc_e:
            warnings.append(
                f"Forecast construction failed: {fc_e}. "
                "The fit completed successfully; re-run or inspect the "
                "transition matrix and regime probability tables for "
                "manual-forecast construction."
            )

        # ---- Model summary ----
        valid_resid = residuals[~np.isnan(residuals)]
        rmse = float(np.sqrt(np.mean(valid_resid ** 2))) if len(valid_resid) > 0 else None

        # Single-regime benchmark — converts the absolute RMSE above
        # into a lift metric so the user can see whether the Markov
        # specification is earning its complexity. In-sample match of
        # AR order so the comparison is structurally apples-to-apples.
        benchmark_rmse, benchmark_name = _fit_benchmark(filled, order)
        rmse_lift_vs_benchmark = None
        if benchmark_rmse is not None and rmse is not None and benchmark_rmse > 0:
            rmse_lift_vs_benchmark = float(
                (benchmark_rmse - rmse) / benchmark_rmse
            )
        elif benchmark_rmse is None:
            warnings.append(
                "Benchmark fit failed. RMSE Lift vs Benchmark row omitted "
                "from Model Summary."
            )

        # Expected regime duration
        durations = []
        for r in range(k_regimes):
            if r < transition_matrix.shape[0] and r < transition_matrix.shape[1]:
                p_stay = transition_matrix[r, r]
                dur = 1 / (1 - p_stay) if p_stay < 1 else float('inf')
                durations.append(round(dur, 2))
            else:
                durations.append(None)

        summary_rows = [
            ["Model", f"Markov-Switching (k={k_regimes}, AR={order})"],
            ["Regimes", k_regimes],
            ["AR Order", order],
            ["Switching Variance", switching_var],
            ["Observations", n],
            ["Log-Likelihood", round(float(fit.llf), 2)],
            ["AIC", round(float(fit.aic), 2)],
            ["BIC", round(float(fit.bic), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
        ]
        # Benchmark comparison — appended only when the benchmark fit
        # succeeded. Negative lift values permitted: a negative lift
        # is useful signal that the specification is overfitting noise
        # on a series without real regime structure.
        if benchmark_rmse is not None:
            summary_rows.append([
                "Benchmark RMSE",
                f"{benchmark_rmse:.4f} ({benchmark_name})",
            ])
        if rmse_lift_vs_benchmark is not None:
            summary_rows.append([
                "RMSE Lift vs Benchmark",
                f"{rmse_lift_vs_benchmark:+.1%}",
            ])
        summary_rows.append(["Forecast Horizon", horizon])
        for r in range(k_regimes):
            summary_rows.append([f"Expected Duration Regime {r}", durations[r] if r < len(durations) else None])

        if exog_names:
            summary_rows.append(["Exogenous Variables", ", ".join(exog_names)])
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        current_regime = int(most_likely_regime[-1]) if n_probs > 0 else 0
        plain = (
            f"Markov-switching model with {k_regimes} regimes fitted to '{name}' ({n} observations). "
            f"The series is currently in Regime {current_regime}. "
        )
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            if mask_r.any():
                mean_r = float(np.mean(filled[:n_probs][mask_r]))
                plain += f"Regime {r}: mean={mean_r:.4f} ({mask_r.sum()} periods). "
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += f"AIC = {fit.aic:.1f}."

        charting = (
            "Two-panel chart: (1) Original series colored by most likely regime, with "
            "regime probability bands. (2) Smoothed regime probabilities over time, "
            "one line per regime. Regime transitions shown as vertical dashed lines."
        )

        progress_callback("Done", 100)

        audit = {
            "k_regimes": k_regimes,
            "order": order,
            "switching_variance": switching_var,
            "current_regime": current_regime,
            "aic": round(float(fit.aic), 2),
            "bic": round(float(fit.bic), 2),
            "log_likelihood": round(float(fit.llf), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "expected_durations": durations,
            "horizon": horizon,
            "forecast_method": forecast_method,
            "forecast_horizon": horizon if forecast_method else None,
            "forecast_interval_assumes": (
                "Gaussian within-regime emissions; plug-in forecast "
                "ignoring parameter estimation uncertainty; AR-innovation "
                "variance not compounded across horizons"
            ) if forecast_method else None,
            "benchmark_rmse": (
                round(benchmark_rmse, 4) if benchmark_rmse is not None else None
            ),
            "benchmark_name": benchmark_name,
            "rmse_lift_vs_benchmark": (
                round(rmse_lift_vs_benchmark, 4)
                if rmse_lift_vs_benchmark is not None else None
            ),
        }

        # Build per-regime empirical means and stds for the interpretation
        # spec (same computation as the Regime Summary table, distilled
        # into flat lists). Regime order matches the sorted post-mean-sort
        # convention applied to ``most_likely_regime``.
        _regime_means_list = []
        _regime_stds_list = []
        for r in range(k_regimes):
            mask_r = most_likely_regime == r
            count_r = int(mask_r.sum())
            mean_r = (float(np.mean(filled[:n_probs][mask_r])) if count_r > 0 else 0.0)
            std_r = (float(np.std(filled[:n_probs][mask_r], ddof=1)) if count_r > 1 else 0.0)
            _regime_means_list.append(mean_r)
            _regime_stds_list.append(std_r)

        _final_probs = (smoothed_probs[-1, :].tolist()
                        if n_probs > 0 else [0.0] * k_regimes)
        _current_prob = float(smoothed_probs[-1, current_regime]) if n_probs > 0 else 0.0

        interp = build_interpretation("markov_switching", {
            "k_regimes": k_regimes,
            "regime_means": _regime_means_list,
            "regime_stds": _regime_stds_list,
            "current_regime": current_regime,
            "current_prob": _current_prob,
            "expected_durations": durations,
            "final_period_probs": _final_probs,
            "sort_axis": sort_axis,
            "forecast_method": forecast_method,
            "forecast_horizon": horizon if forecast_method else None,
            "forecast_h_probs": (
                final_horizon_probs.tolist()
                if final_horizon_probs is not None else None
            ),
            "forecast_stationary": (
                stationary_distribution.tolist()
                if stationary_distribution is not None else None
            ),
            "markov_rmse": rmse,
            "benchmark_rmse": benchmark_rmse,
            "benchmark_name": benchmark_name,
            "rmse_lift_vs_benchmark": rmse_lift_vs_benchmark,
        })

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
            f"Markov-switching model failed: {e}",
            error_fixes=[
                "Ensure the series is numeric with enough observations.",
                "Try k_regimes=2 with order=0 as a simpler model.",
                "Check for constant series or extreme outliers.",
                "Markov-switching models can be sensitive to initial values; try again with different seed.",
            ],
        )
