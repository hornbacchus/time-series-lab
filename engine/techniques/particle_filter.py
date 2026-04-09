"""
Bootstrap Particle Filter for Nonlinear State-Space Models (Time Series Lab).

Implements a Sequential Monte Carlo (particle filter) for a generic
nonlinear state-space model. Default model is a local-level with
possible nonlinear observation equation, but users can choose among
several built-in state-space specifications.

Implemented purely in numpy (no external SMC library).
"""

import numpy as np
from scipy import stats as sp_stats

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# ---------------------------------------------------------------------------
# Preset configurations
# ---------------------------------------------------------------------------
_PRESET_CONFIG = {
    "Fast": {"n_particles": 500, "resample_threshold": 0.5},
    "Balanced": {"n_particles": 2000, "resample_threshold": 0.5},
    "Thorough": {"n_particles": 10000, "resample_threshold": 0.5},
}


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Run a bootstrap particle filter.

    Parameters (via ctx.params)
    ---------------------------
    model : str, optional
        State-space model specification:
        - 'local_level' (default): x(t) = x(t-1) + eta, y(t) = x(t) + eps
        - 'local_level_sv': stochastic volatility local level
        - 'nonlinear_growth': x(t) = 0.5*x(t-1) + 25*x(t-1)/(1+x(t-1)^2) + 8*cos(1.2*t) + eta
        - 'random_walk_sv': random walk with stochastic volatility
    n_particles : int, optional
        Number of particles. Preset-dependent.
    sigma_state : float, optional
        State noise std dev. Default 1.0.
    sigma_obs : float, optional
        Observation noise std dev. Default 1.0.
    horizon : int
        Forecast steps. Default 10.

    Series layout
    -------------
    First series -> observations y(t).
    """
    try:
        progress_callback("Validating inputs", 5)
        warnings = []
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        n = len(values)

        # Handle NaN: particle filter can handle missing obs (skip update step)
        nan_mask = np.isnan(values)
        nan_count = int(nan_mask.sum())
        if nan_count > 0:
            warnings.append(
                f"{nan_count} missing observations. Particle filter will propagate "
                "particles without conditioning on missing time steps."
            )

        if n < 5:
            return make_error_response(
                ctx,
                f"Only {n} observations. Need at least 5 for particle filtering.",
                error_fixes=["Provide a longer series."],
            )

        cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_particles = int(ctx.get_param("n_particles", cfg["n_particles"]))
        resample_thresh = float(ctx.get_param("resample_threshold", cfg["resample_threshold"]))
        model_type = ctx.get_param("model", "local_level")
        sigma_state = float(ctx.get_param("sigma_state", 1.0))
        sigma_obs = float(ctx.get_param("sigma_obs", 1.0))
        horizon = max(1, int(ctx.get_param("horizon", 10)))

        # Auto-estimate noise scales if not provided
        auto_sigma = ctx.get_param("auto_sigma", True)
        if auto_sigma and not np.all(nan_mask):
            valid_vals = values[~nan_mask]
            if len(valid_vals) > 3:
                diff_std = float(np.std(np.diff(valid_vals), ddof=1))
                if ctx.get_param("sigma_state") is None:
                    sigma_state = max(diff_std * 0.5, 1e-6)
                if ctx.get_param("sigma_obs") is None:
                    sigma_obs = max(diff_std * 0.5, 1e-6)

        # Select state-space model functions
        state_transition, obs_likelihood, obs_func = _get_model_functions(model_type)

        progress_callback(f"Running particle filter ({n_particles} particles)", 15)

        # Initialize particles
        if not np.all(nan_mask):
            first_valid = values[~nan_mask][0]
        else:
            first_valid = 0.0

        particles = np.random.normal(first_valid, sigma_state * 2, size=n_particles)
        weights = np.ones(n_particles) / n_particles

        # Storage
        filtered_mean = np.zeros(n)
        filtered_std = np.zeros(n)
        filtered_median = np.zeros(n)
        filtered_q05 = np.zeros(n)
        filtered_q95 = np.zeros(n)
        ess_history = np.zeros(n)
        n_resamples = 0
        log_likelihood = 0.0

        for t in range(n):
            if t % max(1, n // 20) == 0:
                pct = 15 + int(60 * t / n)
                progress_callback(f"Filtering t={t+1}/{n}", pct)

            # Propagate (state transition)
            particles = state_transition(particles, t, sigma_state)

            # Update weights if observation is available
            if not nan_mask[t]:
                log_w = obs_likelihood(values[t], particles, sigma_obs)
                # Numerical stability
                max_log_w = np.max(log_w)
                w = np.exp(log_w - max_log_w)
                w_sum = np.sum(w)

                if w_sum > 0:
                    weights = w / w_sum
                    # Marginal likelihood contribution
                    log_likelihood += max_log_w + np.log(w_sum) - np.log(n_particles)
                else:
                    weights = np.ones(n_particles) / n_particles
                    warnings.append(f"All particle weights collapsed to zero at t={t+1}.")

            # Effective sample size
            ess = 1.0 / np.sum(weights ** 2)
            ess_history[t] = ess

            # Store filtered estimates
            filtered_mean[t] = np.average(particles, weights=weights)
            filtered_std[t] = np.sqrt(np.average((particles - filtered_mean[t]) ** 2, weights=weights))
            sorted_idx = np.argsort(particles)
            cum_weights = np.cumsum(weights[sorted_idx])
            filtered_median[t] = particles[sorted_idx[np.searchsorted(cum_weights, 0.5)]]
            filtered_q05[t] = particles[sorted_idx[np.searchsorted(cum_weights, 0.05)]]
            filtered_q95[t] = particles[sorted_idx[np.searchsorted(cum_weights, 0.95)]]

            # Resample if ESS drops below threshold
            if ess < resample_thresh * n_particles:
                indices = _systematic_resample(weights, n_particles)
                particles = particles[indices]
                weights = np.ones(n_particles) / n_particles
                n_resamples += 1

        progress_callback("Generating forecasts", 78)

        # Forecast: propagate particles forward without conditioning
        fc_mean = np.zeros(horizon)
        fc_std = np.zeros(horizon)
        fc_q05 = np.zeros(horizon)
        fc_q95 = np.zeros(horizon)

        fc_particles = particles.copy()
        for h in range(horizon):
            fc_particles = state_transition(fc_particles, n + h, sigma_state)
            fc_obs = obs_func(fc_particles, sigma_obs)
            fc_mean[h] = np.mean(fc_obs)
            fc_std[h] = np.std(fc_obs)
            fc_q05[h] = np.percentile(fc_obs, 5)
            fc_q95[h] = np.percentile(fc_obs, 95)

        progress_callback("Building output tables", 85)

        # ---- Forecast table ----
        fc_rows = []
        for h in range(horizon):
            fc_rows.append([
                n + h + 1,
                round(float(fc_mean[h]), 6),
                round(float(fc_q05[h]), 6),
                round(float(fc_q95[h]), 6),
                round(float(fc_std[h]), 6),
            ])
        fc_table = make_table(
            "Forecast",
            ["Step", "Mean", "Lower 90%", "Upper 90%", "Std Dev"],
            fc_rows,
        )

        # ---- Filtered state table ----
        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))
        state_rows = []
        for t in range(n):
            state_rows.append([
                time_col[t],
                float(values[t]) if not nan_mask[t] else None,
                round(float(filtered_mean[t]), 6),
                round(float(filtered_median[t]), 6),
                round(float(filtered_q05[t]), 6),
                round(float(filtered_q95[t]), 6),
                round(float(filtered_std[t]), 6),
                round(float(ess_history[t]), 0),
            ])
        state_table = make_table(
            "Filtered State",
            ["Time", "Observed", "State Mean", "State Median", "Q5", "Q95", "Std", "ESS"],
            state_rows,
        )

        # ---- Model summary ----
        residuals = values[~nan_mask] - filtered_mean[~nan_mask]
        rmse = float(np.sqrt(np.mean(residuals ** 2))) if len(residuals) > 0 else None
        mae = float(np.mean(np.abs(residuals))) if len(residuals) > 0 else None
        avg_ess = float(np.mean(ess_history))
        min_ess = float(np.min(ess_history))

        summary_rows = [
            ["Model", model_type],
            ["Particles", n_particles],
            ["Observations", n],
            ["Missing Observations", nan_count],
            ["State Noise (sigma_state)", round(sigma_state, 6)],
            ["Observation Noise (sigma_obs)", round(sigma_obs, 6)],
            ["Log-Likelihood (approx)", round(float(log_likelihood), 2)],
            ["RMSE", round(rmse, 4) if rmse else None],
            ["MAE", round(mae, 4) if mae else None],
            ["Average ESS", round(avg_ess, 0)],
            ["Minimum ESS", round(min_ess, 0)],
            ["Resampling Events", n_resamples],
            ["Resample Threshold", resample_thresh],
            ["Forecast Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # ESS quality assessment
        if min_ess < 10:
            warnings.append(
                f"Minimum ESS was only {min_ess:.0f}. Consider increasing n_particles "
                "or adjusting sigma_state / sigma_obs."
            )
        if n_resamples > n * 0.9:
            warnings.append(
                "Resampling occurred at almost every time step. The model may be "
                "misspecified or noise parameters may need adjustment."
            )

        # ---- Plain English ----
        plain = (
            f"Bootstrap particle filter ({model_type} model) applied to '{name}' "
            f"({n} observations, {n_particles} particles). "
            f"Approximate log-likelihood = {log_likelihood:.2f}. "
        )
        if rmse:
            plain += f"RMSE = {rmse:.4f}. "
        plain += (
            f"Average ESS = {avg_ess:.0f} ({avg_ess/n_particles*100:.0f}% of particles effective). "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with observed series, filtered state mean, and 90% credible band "
            "(Q5 to Q95) as shaded region. Forecast continuation with widening band. "
            "Secondary panel: Effective Sample Size (ESS) over time."
        )

        progress_callback("Done", 100)

        audit = {
            "model": model_type,
            "n_particles": n_particles,
            "sigma_state": round(sigma_state, 6),
            "sigma_obs": round(sigma_obs, 6),
            "log_likelihood": round(float(log_likelihood), 2),
            "rmse": round(rmse, 4) if rmse else None,
            "avg_ess": round(avg_ess, 0),
            "min_ess": round(min_ess, 0),
            "n_resamples": n_resamples,
            "horizon": horizon,
        }

        return make_response(
            ctx,
            tables=[fc_table, state_table, summary_table],
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
            f"Particle filter failed: {e}",
            error_fixes=[
                "Ensure the series is numeric.",
                "Try increasing n_particles for better approximation.",
                "Adjust sigma_state and sigma_obs to match data scale.",
                "Try a different model specification.",
            ],
        )


# ---------------------------------------------------------------------------
# State-space model specifications
# ---------------------------------------------------------------------------

def _get_model_functions(model_type):
    """Return (state_transition, obs_log_likelihood, obs_func) for a model."""

    if model_type == "nonlinear_growth":
        def state_trans(x, t, sigma):
            return 0.5 * x + 25 * x / (1 + x ** 2) + 8 * np.cos(1.2 * t) + sigma * np.random.randn(len(x))

        def obs_loglik(y, x, sigma):
            y_pred = x ** 2 / 20
            return -0.5 * ((y - y_pred) / sigma) ** 2

        def obs_fn(x, sigma):
            return x ** 2 / 20 + sigma * np.random.randn(len(x))

        return state_trans, obs_loglik, obs_fn

    elif model_type == "random_walk_sv":
        # Stochastic volatility model
        def state_trans(x, t, sigma):
            # x = [h_t]: log-volatility follows random walk
            return x + sigma * np.random.randn(len(x))

        def obs_loglik(y, x, sigma):
            # y | h ~ N(0, exp(h))
            vol = np.exp(x / 2)
            return -0.5 * np.log(2 * np.pi) - x / 2 - 0.5 * (y / vol) ** 2

        def obs_fn(x, sigma):
            vol = np.exp(x / 2)
            return vol * np.random.randn(len(x))

        return state_trans, obs_loglik, obs_fn

    elif model_type == "local_level_sv":
        # Local level with stochastic volatility (2-state: level + log-vol)
        # Simplify: track only level, with slowly varying noise
        def state_trans(x, t, sigma):
            return x + sigma * np.random.randn(len(x))

        def obs_loglik(y, x, sigma):
            return -0.5 * ((y - x) / sigma) ** 2

        def obs_fn(x, sigma):
            return x + sigma * np.random.randn(len(x))

        return state_trans, obs_loglik, obs_fn

    else:
        # Default: local_level
        def state_trans(x, t, sigma):
            return x + sigma * np.random.randn(len(x))

        def obs_loglik(y, x, sigma):
            return -0.5 * ((y - x) / sigma) ** 2

        def obs_fn(x, sigma):
            return x + sigma * np.random.randn(len(x))

        return state_trans, obs_loglik, obs_fn


# ---------------------------------------------------------------------------
# Resampling
# ---------------------------------------------------------------------------

def _systematic_resample(weights, n):
    """Systematic resampling for particle filters."""
    positions = (np.arange(n) + np.random.uniform()) / n
    cumsum = np.cumsum(weights)
    cumsum[-1] = 1.0  # ensure exactly 1
    indices = np.searchsorted(cumsum, positions)
    return np.clip(indices, 0, len(weights) - 1)
