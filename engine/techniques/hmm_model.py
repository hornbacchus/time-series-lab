"""
Hidden Markov Model (HMM) for Time Series Lab.

Fits a Gaussian Hidden Markov Model using hmmlearn's GaussianHMM.
Decodes the most likely sequence of hidden states and provides
state-dependent distributional parameters.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
    label_regimes_by_dominant_key,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"n_components": 2, "n_iter": 50, "covariance_type": "diag"},
    "Balanced": {"n_components": 2, "n_iter": 100, "covariance_type": "full"},
    "Thorough": {"n_components": 3, "n_iter": 200, "covariance_type": "full"},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Fit a Gaussian HMM.

    Parameters (via ctx.params)
    ---------------------------
    n_components : int, optional
        Number of hidden states. Preset-dependent.
    covariance_type : str, optional
        'diag', 'full', 'spherical', 'tied'. Preset-dependent.
    n_iter : int, optional
        Max EM iterations. Preset-dependent.
    horizon : int
        Forecast / simulation horizon. Default 10.

    Series layout
    -------------
    All series are treated as observation dimensions.
    Single series -> univariate HMM. Multiple -> multivariate.
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        # Import hmmlearn (optional dependency)
        try:
            from hmmlearn.hmm import GaussianHMM
        except ImportError:
            return make_error_response(
                ctx,
                "The 'hmmlearn' package is required but not installed.",
                error_fixes=[
                    "Install hmmlearn: pip install hmmlearn",
                    "Or use the Markov-switching model (markov_switching) which uses statsmodels.",
                ],
            )

        all_series = ctx.get_all_series()
        names = [s[0] for s in all_series]
        arrays = [s[1] for s in all_series]
        n_features = len(names)

        # Align and build observation matrix
        min_len = min(len(a) for a in arrays)
        X = np.column_stack([a[:min_len] for a in arrays])
        T = X.shape[0]

        # Handle NaN
        nan_count = int(np.isnan(X).sum())
        if nan_count > 0:
            warnings.append(f"{nan_count} NaN values interpolated.")
            for col in range(n_features):
                nans = np.where(np.isnan(X[:, col]))[0]
                valid = np.where(~np.isnan(X[:, col]))[0]
                if len(valid) < 3:
                    return make_error_response(
                        ctx,
                        f"Series '{names[col]}' has too few valid observations.",
                    )
                X[nans, col] = np.interp(nans, valid, X[valid, col])

        if T < 15:
            return make_error_response(
                ctx,
                f"Only {T} observations. HMM needs at least 15.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_components = int(ctx.get_param("n_components", cfg["n_components"]))
        covariance_type = ctx.get_param("covariance_type", cfg["covariance_type"])
        n_iter = int(ctx.get_param("n_iter", cfg["n_iter"]))
        horizon = max(1, int(ctx.get_param("horizon", 10)))

        n_components = max(2, min(n_components, min(T // 5, 10)))

        progress_callback(f"Fitting Gaussian HMM ({n_components} states)", 20)

        # Fit HMM with multiple restarts for robustness
        best_model = None
        best_score = -np.inf
        n_restarts = {"Fast": 3, "Balanced": 5, "Thorough": 10}.get(ctx.preset, 5)

        for restart in range(n_restarts):
            try:
                model = GaussianHMM(
                    n_components=n_components,
                    covariance_type=covariance_type,
                    n_iter=n_iter,
                    random_state=ctx.seed + restart,
                    tol=1e-4,
                )
                model.fit(X)
                score = model.score(X)

                if score > best_score:
                    best_score = score
                    best_model = model
            except Exception:
                continue

            pct = 20 + int(40 * (restart + 1) / n_restarts)
            progress_callback(f"Restart {restart + 1}/{n_restarts}, best score={best_score:.2f}", pct)

        if best_model is None:
            return make_error_response(
                ctx,
                "HMM fitting failed across all restarts.",
                error_fixes=[
                    "Try fewer hidden states (n_components=2).",
                    "Use covariance_type='diag' for numerical stability.",
                    "Check for constant or near-constant series.",
                ],
            )

        if not best_model.monitor_.converged:
            warnings.append("HMM did not converge within max iterations. Results may be approximate.")

        progress_callback("Decoding hidden states", 65)

        # Viterbi decoding
        log_prob, states = best_model.decode(X, algorithm="viterbi")

        # State probabilities
        state_probs = best_model.predict_proba(X)

        # Sort states deterministically so "State 0" is the lowest-axis
        # regime across runs. Without this, hmmlearn's internal ordering
        # (driven by EM starting point and the restart that won best
        # score) can flip between otherwise-identical analyses, giving
        # the user charts where the regime labels swap randomly.
        #
        # Axis selection (mean vs std) is decided by
        # label_regimes_by_dominant_key: mean-sort by default, std-sort
        # when the variance ratio dominates the mean separation
        # (variance_ratio >= 3.0 AND variance_ratio /
        # max(mean_sep_in_min_sigma, 0.5) > 2.0). This prevents the
        # misleading mean-labeling on runs where two regimes have
        # nearly-identical means but very different volatilities.
        #
        # We keep sorted COPIES for reporting rather than mutating the
        # fitted hmmlearn model — ``best_model.covars_`` is a property
        # with strict shape validation that can reject an assignment
        # even when the values are correct. The downstream forecast
        # path below uses ``best_model.sample()`` which draws from the
        # unsorted internal state indices; that's fine because the
        # sampled values themselves are invariant to relabeling.
        # Extract per-state std from covars_ for the dominant-key
        # sort helper. hmmlearn normalizes all covariance_types
        # ("diag"/"full"/"spherical"/"tied") to the same 3-D shape
        # (n_components, n_features, n_features) on .covars_; the
        # [i, 0, 0] element is always the regime-i variance along
        # the first feature, which is the only feature for the
        # univariate series this wrapper supports. Handle 1-D /
        # 2-D / 3-D defensively in case a future hmmlearn version
        # changes the layout.
        _covars_arr = np.asarray(best_model.covars_)
        if _covars_arr.ndim == 3:
            # Standard hmmlearn layout: (n_components, n_features, n_features)
            state_vars = _covars_arr[:, 0, 0]
        elif _covars_arr.ndim == 2:
            # (n_components, n_features) per-state diag variances.
            state_vars = _covars_arr[:, 0]
        elif _covars_arr.ndim == 1:
            # Rare: (n_components,) scalar per-state variances.
            state_vars = _covars_arr
        else:
            # Unknown layout → uniform stds trigger mean-sort fallback.
            state_vars = np.ones(best_model.n_components)
        # Guard against negative variances from numerical noise.
        state_stds = np.sqrt(np.maximum(np.asarray(state_vars, dtype=float), 0.0))

        # Pass the 2-D means array as-is; the helper uses column 0 as
        # the sort key while preserving full 2-D shape in the reordered
        # output so downstream per-feature rendering still works.
        sort_result = label_regimes_by_dominant_key(
            means=best_model.means_,
            stds=state_stds,
            covars=best_model.covars_,
            transmat=best_model.transmat_,
            labels=states,
            probs=state_probs,
        )
        order = sort_result["order"]
        sorted_means = sort_result["means"]
        sorted_covars = sort_result["covars"]
        sorted_transmat = sort_result["transmat"]
        sorted_startprob = best_model.startprob_[order]
        states = sort_result["labels"]
        state_probs = sort_result["probs"]
        hmm_sort_axis = sort_result["axis_name"]

        progress_callback("Generating forecasts via simulation", 75)

        # Forecast: simulate from the model starting from the last state
        simulated, sim_states = best_model.sample(n_samples=horizon)
        # Average multiple simulations for robust forecast
        n_sims = 100
        sim_paths = np.zeros((n_sims, horizon, n_features))
        for s in range(n_sims):
            sim_data, _ = best_model.sample(n_samples=horizon)
            sim_paths[s] = sim_data

        fc_mean = np.mean(sim_paths, axis=0)
        fc_q05 = np.percentile(sim_paths, 5, axis=0)
        fc_q95 = np.percentile(sim_paths, 95, axis=0)

        progress_callback("Building output tables", 85)

        tables = []

        # ---- State means and covariances ----
        # Use the sorted copies built above so State 0 is the low-mean
        # regime. best_model itself still carries the unsorted
        # parameters because hmmlearn's covars_ property rejects in-
        # place reassignment; the forecast-simulation path drew from
        # the unsorted model, but the sampled values are invariant to
        # relabeling so the end-user output is still consistent.
        means = sorted_means        # (n_components, n_features)
        covars = sorted_covars      # shape depends on covariance_type

        def _diag_var_per_state(covars_arr, s, f):
            """Extract the per-feature variance for state s, feature f.

            hmmlearn's covars_ shape depends on covariance_type AND the
            library's internal storage convention — even "diag" is
            commonly stored as (n_components, n_features, n_features)
            with zeros off-diagonal. Pull the diagonal robustly instead
            of indexing with assumed shape.
            """
            arr_s = np.asarray(covars_arr[s])
            if arr_s.ndim == 0:
                return float(arr_s)           # scalar (spherical-style)
            if arr_s.ndim == 1:
                return float(arr_s[f])         # diag vector
            return float(arr_s[f, f])          # full-matrix (or diag stored as full)

        mean_rows = []
        for s in range(n_components):
            row = [f"State {s}"]
            for f in range(n_features):
                row.append(round(float(means[s, f]), 4))
            if covariance_type == "spherical":
                var_s = float(np.asarray(covars[s]).flatten()[0])
                for f in range(n_features):
                    row.append(round(float(np.sqrt(var_s)), 4))
            elif covariance_type == "tied":
                # Single shared covariance matrix for all states.
                tied = np.asarray(covars)
                if tied.ndim == 2:
                    for f in range(n_features):
                        row.append(round(float(np.sqrt(tied[f, f])), 4))
                else:
                    for f in range(n_features):
                        row.append(round(float(np.sqrt(tied.flatten()[f])), 4))
            else:  # "full" or "diag" (both stored as (K, d, d) by hmmlearn)
                for f in range(n_features):
                    row.append(round(float(np.sqrt(_diag_var_per_state(covars, s, f))), 4))
            mean_rows.append(row)
        mean_cols = [f"Mean({names[f]})" for f in range(n_features)]
        std_cols = [f"Std({names[f]})" for f in range(n_features)]
        tables.append(make_table(
            "State Parameters",
            ["State"] + mean_cols + std_cols,
            mean_rows,
        ))

        # ---- Transition matrix ----
        transmat = sorted_transmat
        trans_rows = []
        for i in range(n_components):
            row = [f"From State {i}"]
            for j in range(n_components):
                row.append(round(float(transmat[i, j]), 4))
            trans_rows.append(row)
        tables.append(make_table(
            "Transition Matrix",
            [""] + [f"To State {j}" for j in range(n_components)],
            trans_rows,
        ))

        # ---- State sequence table ----
        time_col = ctx.time if ctx.time and len(ctx.time) >= T else list(range(1, T + 1))
        seq_rows = []
        for t in range(T):
            row = [time_col[t]]
            for f in range(n_features):
                row.append(round(float(X[t, f]), 4))
            row.append(int(states[t]))
            for s in range(n_components):
                row.append(round(float(state_probs[t, s]), 4))
            seq_rows.append(row)
        obs_cols = [names[f] for f in range(n_features)]
        prob_cols = [f"P(State {s})" for s in range(n_components)]
        tables.append(make_table(
            "State Sequence",
            ["Time"] + obs_cols + ["Decoded State"] + prob_cols,
            seq_rows,
        ))

        # ---- Forecast table (per feature) ----
        for f in range(n_features):
            fc_rows = []
            for h in range(horizon):
                fc_rows.append([
                    T + h + 1,
                    round(float(fc_mean[h, f]), 4),
                    round(float(fc_q05[h, f]), 4),
                    round(float(fc_q95[h, f]), 4),
                ])
            tables.append(make_table(
                f"Forecast: {names[f]}",
                ["Step", "Mean", "Lower 90%", "Upper 90%"],
                fc_rows,
            ))

        # ---- State summary ----
        state_summary_rows = []
        for s in range(n_components):
            mask_s = states == s
            count_s = int(mask_s.sum())
            pct_s = count_s / T * 100
            # Expected duration
            dur = 1 / (1 - transmat[s, s]) if transmat[s, s] < 1 else float('inf')
            state_summary_rows.append([
                f"State {s}",
                count_s,
                round(pct_s, 1),
                round(dur, 2),
            ])
        tables.append(make_table(
            "State Summary",
            ["State", "Periods", "% of Time", "Expected Duration"],
            state_summary_rows,
        ))

        # ---- Model summary ----
        summary_rows = [
            ["Model", f"Gaussian HMM ({n_components} states)"],
            ["Features", ", ".join(names)],
            ["Covariance Type", covariance_type],
            ["Observations", T],
            ["Log-Likelihood", round(float(best_score), 2)],
            ["AIC (approx)", round(-2 * best_score + 2 * _count_params(n_components, n_features, covariance_type), 2)],
            ["BIC (approx)", round(-2 * best_score + _count_params(n_components, n_features, covariance_type) * np.log(T), 2)],
            ["Converged", best_model.monitor_.converged],
            ["Current State", int(states[-1])],
            ["Restarts", n_restarts],
            ["Forecast Horizon", horizon],
        ]
        tables.append(make_table("Model Summary", ["Metric", "Value"], summary_rows))

        # ---- Plain English ----
        current_state = int(states[-1])
        aic = -2 * best_score + 2 * _count_params(n_components, n_features, covariance_type)
        plain = (
            f"Gaussian HMM with {n_components} hidden states fitted to "
            f"{n_features} feature(s) ({', '.join(names)}), {T} observations. "
            f"The series is currently in State {current_state}. "
        )
        for s in range(n_components):
            mask_s = states == s
            if mask_s.any():
                mean_str = ", ".join([f"{names[f]}={means[s, f]:.3f}" for f in range(n_features)])
                plain += f"State {s} ({mask_s.sum()} periods): mean [{mean_str}]. "
        plain += f"Log-likelihood = {best_score:.2f}, AIC = {aic:.1f}."

        charting = (
            "Multi-panel chart: (1) Time series colored by decoded state, "
            "with state transitions marked. (2) State probabilities over time "
            "(one line per state). (3) State-conditional distributions as violin or density plots."
        )

        progress_callback("Done", 100)

        audit = {
            "n_components": n_components,
            "covariance_type": covariance_type,
            "features": names,
            "n_features": n_features,
            "log_likelihood": round(float(best_score), 2),
            "aic": round(float(aic), 2),
            "current_state": current_state,
            "converged": best_model.monitor_.converged,
            "n_restarts": n_restarts,
            "horizon": horizon,
        }

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain,
            warnings=warnings,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"HMM model failed: {e}",
            error_fixes=[
                "Install hmmlearn if not available: pip install hmmlearn",
                "Try fewer hidden states (n_components=2).",
                "Use covariance_type='diag' for stability.",
                "Check for constant or extreme-valued series.",
            ],
        )


def _count_params(n_components, n_features, cov_type):
    """Count the number of free parameters in the HMM."""
    # Transition matrix: n_components * (n_components - 1)
    n_trans = n_components * (n_components - 1)
    # Start probabilities: n_components - 1
    n_start = n_components - 1
    # Means: n_components * n_features
    n_means = n_components * n_features
    # Covariances
    if cov_type == "full":
        n_cov = n_components * n_features * (n_features + 1) // 2
    elif cov_type == "diag":
        n_cov = n_components * n_features
    elif cov_type == "spherical":
        n_cov = n_components
    else:  # tied
        n_cov = n_features * (n_features + 1) // 2
    return n_trans + n_start + n_means + n_cov
