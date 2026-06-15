"""
Echo State Network (ESN) / Reservoir Computing Forecast for Time Series Lab.

Uses the reservoirpy library when available for Echo State Networks.
Falls back to a manual numpy implementation of reservoir computing
with a random sparse reservoir matrix and ridge regression readout.

ESNs are efficient recurrent architectures that only train the readout layer,
making them fast to train while still capturing temporal dependencies.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _has_reservoirpy():
    try:
        import reservoirpy
        return True
    except ImportError:
        return False


_PRESET_CONFIG = {
    "Fast": {
        "reservoir_size": 100, "spectral_radius": 0.9,
        "leak_rate": 0.3, "input_scaling": 1.0,
        "ridge_alpha": 1e-4, "n_lags": 1,
        "warmup": 10, "sparsity": 0.1,
    },
    "Balanced": {
        "reservoir_size": 200, "spectral_radius": 0.9,
        "leak_rate": 0.3, "input_scaling": 1.0,
        "ridge_alpha": 1e-6, "n_lags": 1,
        "warmup": 20, "sparsity": 0.1,
    },
    "Thorough": {
        "reservoir_size": 500, "spectral_radius": 0.95,
        "leak_rate": 0.2, "input_scaling": 0.5,
        "ridge_alpha": 1e-8, "n_lags": 1,
        "warmup": 50, "sparsity": 0.05,
    },
}


def _prepare_series(values):
    """Strip edge NaN, interpolate interior NaN."""
    first_valid = 0
    while first_valid < len(values) and np.isnan(values[first_valid]):
        first_valid += 1
    last_valid = len(values) - 1
    while last_valid >= 0 and np.isnan(values[last_valid]):
        last_valid -= 1
    if first_valid > last_valid:
        return np.array([]), 0
    trimmed = values[first_valid:last_valid + 1].copy()
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


class _NumpyESN:
    """
    Minimal Echo State Network implemented in pure numpy.

    Architecture:
    - Random sparse reservoir with specified spectral radius
    - Leaky-integrator neurons with tanh activation
    - Ridge regression readout (only trained layer)
    """

    def __init__(self, input_dim, reservoir_size, spectral_radius,
                 leak_rate, input_scaling, ridge_alpha, sparsity, seed):
        rng = np.random.RandomState(seed)

        self.reservoir_size = reservoir_size
        self.leak_rate = leak_rate
        self.input_scaling = input_scaling
        self.ridge_alpha = ridge_alpha

        # Input weights: input_dim -> reservoir_size
        self.W_in = rng.randn(reservoir_size, input_dim) * input_scaling

        # Reservoir weights: sparse random matrix
        W = rng.randn(reservoir_size, reservoir_size)
        # Apply sparsity mask
        mask = rng.rand(reservoir_size, reservoir_size) < sparsity
        W = W * mask

        # Scale to desired spectral radius
        eigenvalues = np.abs(np.linalg.eigvals(W))
        max_eigenvalue = np.max(eigenvalues) if len(eigenvalues) > 0 else 1.0
        if max_eigenvalue > 0:
            W = W * (spectral_radius / max_eigenvalue)
        self.W = W

        # Readout weights (to be trained)
        self.W_out = None

        # Bias
        self.bias = rng.randn(reservoir_size) * 0.1

    def _run_reservoir(self, inputs):
        """
        Run inputs through the reservoir and collect states.

        Parameters
        ----------
        inputs : ndarray, shape (n_steps, input_dim)

        Returns
        -------
        states : ndarray, shape (n_steps, reservoir_size)
        """
        n_steps = inputs.shape[0]
        states = np.zeros((n_steps, self.reservoir_size))
        state = np.zeros(self.reservoir_size)

        for t in range(n_steps):
            pre_activation = (
                self.W_in @ inputs[t]
                + self.W @ state
                + self.bias
            )
            state = (
                (1 - self.leak_rate) * state
                + self.leak_rate * np.tanh(pre_activation)
            )
            states[t] = state

        return states

    def fit(self, inputs, targets, warmup=0):
        """
        Train the readout layer using ridge regression.

        Parameters
        ----------
        inputs : ndarray, shape (n_steps, input_dim)
        targets : ndarray, shape (n_steps,)
        warmup : int
            Number of initial steps to discard (reservoir warmup).
        """
        states = self._run_reservoir(inputs)

        # Discard warmup states
        S = states[warmup:]
        T = targets[warmup:]

        # Ridge regression: W_out = T @ S^T @ (S @ S^T + alpha * I)^-1
        # Or equivalently: solve (S^T @ S + alpha * I) @ W_out^T = S^T @ T
        reg = self.ridge_alpha * np.eye(self.reservoir_size)
        self.W_out = np.linalg.solve(
            S.T @ S + reg,
            S.T @ T,
        )

        # Return in-sample predictions
        predictions = S @ self.W_out
        return predictions, states

    def predict_step(self, state, input_val):
        """
        Predict one step and return updated state.
        """
        pre_activation = (
            self.W_in @ input_val
            + self.W @ state
            + self.bias
        )
        new_state = (
            (1 - self.leak_rate) * state
            + self.leak_rate * np.tanh(pre_activation)
        )
        prediction = new_state @ self.W_out
        return float(prediction), new_state

    def forecast(self, last_states, last_input, horizon):
        """
        Generate multi-step recursive forecast.

        Parameters
        ----------
        last_states : ndarray, shape (reservoir_size,)
            Last reservoir state.
        last_input : ndarray, shape (input_dim,)
            Last input value.
        horizon : int

        Returns
        -------
        forecasts : ndarray, shape (horizon,)
        """
        forecasts = []
        state = last_states.copy()
        inp = last_input.copy()

        for _ in range(horizon):
            pred, state = self.predict_step(state, inp)
            forecasts.append(pred)
            inp = np.array([pred])

        return np.array(forecasts)


def _run_reservoirpy_esn(normalized, horizon, reservoir_size, spectral_radius,
                          leak_rate, input_scaling, ridge_alpha, warmup, seed):
    """Train ESN using reservoirpy library."""
    import reservoirpy as rpy
    from reservoirpy.nodes import Reservoir, Ridge

    rpy.verbosity(0)
    rpy.set_seed(seed)

    reservoir = Reservoir(
        reservoir_size,
        sr=spectral_radius,
        lr=leak_rate,
        input_scaling=input_scaling,
        seed=seed,
    )
    readout = Ridge(ridge=ridge_alpha)

    esn = reservoir >> readout

    # Prepare data: input at t -> target at t+1
    X_train = normalized[:-1].reshape(-1, 1)
    y_train = normalized[1:].reshape(-1, 1)

    # Warmup
    if warmup > 0 and warmup < len(X_train):
        X_warmup = X_train[:warmup]
        X_fit = X_train[warmup:]
        y_fit = y_train[warmup:]
        # Run warmup
        esn.run(X_warmup)
        esn = esn.fit(X_fit, y_fit, warmup=0)
    else:
        esn = esn.fit(X_train, y_train, warmup=warmup)

    # In-sample predictions
    y_pred = esn.run(X_train)
    if isinstance(y_pred, list):
        y_pred = np.array(y_pred)
    y_pred = y_pred.flatten()

    # Forecast
    last_input = normalized[-1:].reshape(1, 1)
    forecasts = []
    current_input = last_input
    for _ in range(horizon):
        pred = esn.run(current_input)
        if isinstance(pred, list):
            pred = np.array(pred)
        val = float(pred.flatten()[0])
        forecasts.append(val)
        current_input = np.array([[val]])

    return y_pred, np.array(forecasts), "reservoirpy"


def _run_numpy_esn(normalized, horizon, reservoir_size, spectral_radius,
                    leak_rate, input_scaling, ridge_alpha, sparsity, warmup, seed):
    """Train ESN using pure numpy implementation."""
    esn = _NumpyESN(
        input_dim=1,
        reservoir_size=reservoir_size,
        spectral_radius=spectral_radius,
        leak_rate=leak_rate,
        input_scaling=input_scaling,
        ridge_alpha=ridge_alpha,
        sparsity=sparsity,
        seed=seed,
    )

    # Prepare data: input at t -> target at t+1
    inputs = normalized[:-1].reshape(-1, 1)
    targets = normalized[1:]

    # Train
    y_pred, states = esn.fit(inputs, targets, warmup=warmup)

    # Last state for forecasting
    all_states = esn._run_reservoir(inputs)
    last_state = all_states[-1]
    last_input = np.array([normalized[-1]])

    # Forecast
    fc_norm = esn.forecast(last_state, last_input, horizon)

    # Pad y_pred with warmup NaNs for alignment
    y_pred_full = np.concatenate([np.full(warmup, np.nan), y_pred])

    return y_pred_full, fc_norm, "numpy"


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Echo State Network / Reservoir Computing forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    reservoir_size : int
        Number of reservoir neurons. Default 200.
    spectral_radius : float
        Spectral radius of reservoir weight matrix. Default 0.9.
    leak_rate : float
        Leaky integrator rate. Default 0.3.
    """
    try:
        progress_callback("Validating inputs", 5)
        np.random.seed(ctx.seed)

        name, values = ctx.get_primary_series()
        warn_list = []
        clean, n_interp = _prepare_series(values)
        if n_interp > 0:
            warn_list.append(f"{n_interp} interior missing values were linearly interpolated.")
        n = len(clean)

        if n < 20:
            return make_error_response(
                ctx,
                f"Series '{name}' has only {n} valid observations. "
                "Echo State Network needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        # CAI Phase 2 Session 25 fix (F-SN-ESN-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=["Use a positive integer for forecast horizon."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        # Fix B Tier 1b-bis: blank/absent -> preset cfg (byte-identical); literal
        # get_param keeps keys visible to catalog_key_alignment.
        _rs = ctx.get_param("reservoir_size", preset_cfg["reservoir_size"])
        reservoir_size = preset_cfg["reservoir_size"] if (_rs is None or str(_rs).strip() == "") else int(_rs)
        _sr = ctx.get_param("spectral_radius", preset_cfg["spectral_radius"])
        spectral_radius = preset_cfg["spectral_radius"] if (_sr is None or str(_sr).strip() == "") else float(_sr)
        # CAI Phase 2 Session 25 fix (F-SN-ESN-SPECTRAL): explicit
        # range gate. Negative spectral_radius makes no sense for
        # eigenvalue-magnitude scaling.
        if spectral_radius <= 0:
            return make_error_response(
                ctx,
                f"spectral_radius must be > 0. Got {spectral_radius}.",
                error_fixes=[
                    "Use a positive value; typical 0.5-1.0 for "
                    "stable echo state property.",
                ],
            )
        _lk = ctx.get_param("leak_rate", preset_cfg["leak_rate"])
        leak_rate = preset_cfg["leak_rate"] if (_lk is None or str(_lk).strip() == "") else float(_lk)
        # CAI Phase 2 Session 25 fix (F-SN-ESN-LEAK): explicit
        # range gate. Leaky-integrator parameter only meaningful
        # in [0, 1].
        if not (0.0 <= leak_rate <= 1.0):
            return make_error_response(
                ctx,
                f"leak_rate must be in [0, 1]. Got {leak_rate}.",
                error_fixes=[
                    "Use a value in [0, 1]; typical 0.1-0.5. "
                    "1.0 means no leak (standard ESN).",
                ],
            )
        _is = ctx.get_param("input_scaling", preset_cfg["input_scaling"])
        input_scaling = preset_cfg["input_scaling"] if (_is is None or str(_is).strip() == "") else float(_is)
        _ra = ctx.get_param("ridge_alpha", preset_cfg["ridge_alpha"])
        ridge_alpha = preset_cfg["ridge_alpha"] if (_ra is None or str(_ra).strip() == "") else float(_ra)
        _wu = ctx.get_param("warmup", preset_cfg["warmup"])
        warmup = preset_cfg["warmup"] if (_wu is None or str(_wu).strip() == "") else int(_wu)
        sparsity = preset_cfg["sparsity"]

        from techniques._validation import ParamError, require
        try:
            require(reservoir_size >= 1, f"reservoir_size ({reservoir_size}) must be >= 1.",
                    fixes=["Use reservoir_size >= 1, or leave blank for the preset default."])
            require(ridge_alpha > 0, f"ridge_alpha ({ridge_alpha}) must be > 0.",
                    fixes=["Use a positive ridge regularization (e.g. 1e-6), or leave blank."])
            require(input_scaling > 0, f"input_scaling ({input_scaling}) must be > 0.",
                    fixes=["Use a positive input scaling, or leave blank."])
            require(warmup >= 0, f"warmup ({warmup}) must be >= 0.",
                    fixes=["Use warmup >= 0, or leave blank."])
        except ParamError as e:
            return make_error_response(ctx, str(e), error_fixes=e.fixes)

        # Ensure warmup is reasonable
        warmup = min(warmup, n // 4)

        # Normalize data
        y_mean = float(np.mean(clean))
        y_std = float(np.std(clean, ddof=1))
        if y_std == 0:
            y_std = 1.0
        normalized = (clean - y_mean) / y_std

        use_reservoirpy = _has_reservoirpy()
        backend = "reservoirpy" if use_reservoirpy else "numpy"

        if not use_reservoirpy:
            warn_list.append(
                "reservoirpy not available. Using built-in numpy ESN implementation. "
                "Install reservoirpy (pip install reservoirpy) for the full library."
            )

        if use_reservoirpy:
            progress_callback("Training ESN with reservoirpy", 20)
            try:
                y_pred_norm, fc_norm, backend = _run_reservoirpy_esn(
                    normalized, horizon, reservoir_size, spectral_radius,
                    leak_rate, input_scaling, ridge_alpha, warmup, ctx.seed,
                )
            except Exception as rpy_err:
                warn_list.append(
                    f"reservoirpy failed ({rpy_err}). Falling back to numpy ESN."
                )
                use_reservoirpy = False
                backend = "numpy"

        if not use_reservoirpy:
            progress_callback("Training ESN with numpy", 20)
            y_pred_norm, fc_norm, backend = _run_numpy_esn(
                normalized, horizon, reservoir_size, spectral_radius,
                leak_rate, input_scaling, ridge_alpha, sparsity, warmup, ctx.seed,
            )

        progress_callback("Computing metrics", 70)

        # Denormalize forecasts
        fc_values = fc_norm * y_std + y_mean

        # Denormalize in-sample predictions
        # Align: predictions are for indices [1, 2, ..., n-1] (predicting next from current)
        targets_norm = normalized[1:]
        targets = clean[1:]

        # Handle predictions alignment
        valid_mask = ~np.isnan(y_pred_norm)
        if np.sum(valid_mask) > 0:
            y_pred_valid = y_pred_norm[valid_mask]
            targets_valid_norm = targets_norm[valid_mask]
            targets_valid = targets[valid_mask]
            y_pred_denorm = y_pred_valid * y_std + y_mean

            residuals = targets_valid - y_pred_denorm
            rmse = float(np.sqrt(np.mean(residuals ** 2)))
            mae = float(np.mean(np.abs(residuals)))
            ss_res = float(np.sum(residuals ** 2))
            ss_tot = float(np.sum((targets_valid - np.mean(targets_valid)) ** 2))
            r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
            n_train = len(targets_valid)
        else:
            rmse = float("inf")
            mae = float("inf")
            r2 = 0.0
            n_train = 0

        progress_callback("Building output", 90)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([n + i + 1, round(float(fc_values[i]), 6)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # Model summary
        summary_rows = [
            ["Algorithm", "Echo State Network (Reservoir Computing)"],
            ["Backend", backend],
            ["Reservoir Size", reservoir_size],
            ["Spectral Radius", spectral_radius],
            ["Leak Rate", leak_rate],
            ["Input Scaling", input_scaling],
            ["Ridge Alpha", ridge_alpha],
            ["Sparsity", sparsity],
            ["Warmup Steps", warmup],
            ["Observations", n],
            ["Training Samples", n_train],
            ["RMSE", round(rmse, 4)],
            ["MAE", round(mae, 4)],
            ["R-squared", round(r2, 4)],
            ["Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [fc_table, summary_table]

        if r2 < 0:
            warn_list.append(
                "Negative R-squared indicates the model is worse than predicting the mean. "
                "Try adjusting spectral_radius, leak_rate, or reservoir_size."
            )
        if rmse > y_std:
            warn_list.append(
                "RMSE exceeds the series standard deviation, suggesting poor model fit."
            )
        if horizon > n // 2:
            warn_list.append(
                f"Forecast horizon ({horizon}) is large relative to series length ({n}). "
                "Recursive forecasts degrade significantly with longer horizons."
            )

        plain_english = (
            f"Echo State Network forecast for '{name}' ({n} observations) using {backend}. "
            f"Reservoir: {reservoir_size} neurons, spectral radius={spectral_radius}, "
            f"leak rate={leak_rate}. "
            f"RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and ESN forecast continuation. "
            "Overlay fitted values on the original series. "
            "Consider a heatmap of reservoir state activations for interpretability."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(fc_values[-1]) if len(fc_values) else _last_observed_value
        _n_train = int(n - warmup)

        audit = {
            "backend": backend,
            "reservoir_size": reservoir_size,
            "spectral_radius": spectral_radius,
            "leak_rate": leak_rate,
            "input_scaling": input_scaling,
            "ridge_alpha": ridge_alpha,
            "sparsity": sparsity,
            "warmup": warmup,
            "rmse": round(rmse, 4),
            "mae": round(mae, 4),
            "r2": round(r2, 4),
            "horizon": horizon,
            "series_mean": round(_series_mean, 6),
            "series_std": round(_series_std, 6),
            "last_observed_value": round(_last_observed_value, 6),
            "forecast_end_value": round(_forecast_end_value, 6),
            "n_train": _n_train,
            "n_obs": n,
            "series_name": name,
        }

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("echo_state_network", dict(audit))

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
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
            f"Echo State Network forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try a different reservoir_size or spectral_radius.",
                "Adjust leak_rate (0 < leak_rate <= 1).",
                "Install reservoirpy (pip install reservoirpy) for library support.",
            ],
        )
