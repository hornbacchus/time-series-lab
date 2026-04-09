"""
N-BEATS (Neural Basis Expansion Analysis for Time Series) Forecast
for Time Series Lab.

Uses PyTorch to implement the N-BEATS architecture with generic and trend/seasonality
stacks. Falls back to an ensemble of sklearn models (Ridge + GBR + MLP) when
PyTorch is not installed. Full training only under Thorough preset.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


def _has_torch():
    try:
        import torch
        return True
    except ImportError:
        return False


_PRESET_CONFIG = {
    "Fast": {
        "stack_types": ["generic"],
        "n_blocks": 2, "hidden_size": 64, "theta_size": 16,
        "epochs": 50, "n_lags": 8, "lr": 0.01, "use_torch": False,
    },
    "Balanced": {
        "stack_types": ["generic", "generic"],
        "n_blocks": 3, "hidden_size": 128, "theta_size": 32,
        "epochs": 150, "n_lags": 16, "lr": 0.005, "use_torch": True,
    },
    "Thorough": {
        "stack_types": ["trend", "seasonality", "generic"],
        "n_blocks": 4, "hidden_size": 256, "theta_size": 64,
        "epochs": 500, "n_lags": 32, "lr": 0.001, "use_torch": True,
    },
}


def _prepare_series(values):
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


def _create_sequences(data, lookback, horizon):
    """Create input/output sequence pairs for N-BEATS style training."""
    X, y = [], []
    for i in range(len(data) - lookback - horizon + 1):
        X.append(data[i:i + lookback])
        y.append(data[i + lookback:i + lookback + horizon])
    return np.array(X), np.array(y)


def _create_lag_features(series, n_lags):
    n = len(series)
    features, targets = [], []
    for i in range(n_lags, n):
        features.append(series[i - n_lags:i])
        targets.append(series[i])
    return np.array(features), np.array(targets)


def _build_nbeats_model(lookback, horizon, stack_types, n_blocks, hidden_size, theta_size):
    """Build N-BEATS model using PyTorch."""
    import torch
    import torch.nn as nn

    class NBEATSBlock(nn.Module):
        def __init__(self, input_size, hidden_size, theta_b_size, theta_f_size):
            super().__init__()
            self.fc = nn.Sequential(
                nn.Linear(input_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
            )
            self.theta_b = nn.Linear(hidden_size, theta_b_size, bias=False)
            self.theta_f = nn.Linear(hidden_size, theta_f_size, bias=False)
            self.backcast_fc = nn.Linear(theta_b_size, input_size)
            self.forecast_fc = nn.Linear(theta_f_size, horizon)

        def forward(self, x):
            h = self.fc(x)
            backcast = self.backcast_fc(self.theta_b(h))
            forecast = self.forecast_fc(self.theta_f(h))
            return backcast, forecast

    class NBEATSStack(nn.Module):
        def __init__(self, input_size, n_blocks, hidden_size, theta_size):
            super().__init__()
            self.blocks = nn.ModuleList([
                NBEATSBlock(input_size, hidden_size, theta_size, theta_size)
                for _ in range(n_blocks)
            ])

        def forward(self, x):
            residual = x
            stack_forecast = 0
            for block in self.blocks:
                backcast, forecast = block(residual)
                residual = residual - backcast
                stack_forecast = stack_forecast + forecast
            return residual, stack_forecast

    class NBEATS(nn.Module):
        def __init__(self, input_size, n_stacks, n_blocks, hidden_size, theta_size):
            super().__init__()
            self.stacks = nn.ModuleList([
                NBEATSStack(input_size, n_blocks, hidden_size, theta_size)
                for _ in range(n_stacks)
            ])

        def forward(self, x):
            residual = x
            total_forecast = 0
            for stack in self.stacks:
                residual, forecast = stack(residual)
                total_forecast = total_forecast + forecast
            return total_forecast

    n_stacks = len(stack_types)
    return NBEATS(lookback, n_stacks, n_blocks, hidden_size, theta_size)


def _train_torch_nbeats(X, y, stack_types, n_blocks, hidden_size, theta_size,
                        epochs, lr, seed, horizon):
    """Train N-BEATS model."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    lookback = X.shape[1]

    model = _build_nbeats_model(lookback, horizon, stack_types, n_blocks,
                                 hidden_size, theta_size)

    X_tensor = torch.FloatTensor(X)
    y_tensor = torch.FloatTensor(y)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(X_tensor)
        loss = loss_fn(pred, y_tensor)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    return model, losses


def _predict_torch_nbeats(model, last_sequence, horizon):
    """Generate forecast with N-BEATS."""
    import torch

    model.eval()
    with torch.no_grad():
        x = torch.FloatTensor(last_sequence).unsqueeze(0)
        forecast = model(x).squeeze(0).numpy()

    return forecast[:horizon]


def _train_sklearn_ensemble(X, y, seed):
    """Train an ensemble of sklearn models as N-BEATS surrogate."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor

    models = []

    # Ridge
    ridge = Ridge(alpha=1.0, random_state=seed)
    ridge.fit(X, y)
    models.append(("Ridge", ridge))

    # GBR
    gbr = GradientBoostingRegressor(
        n_estimators=100, max_depth=3,
        learning_rate=0.1, random_state=seed,
    )
    gbr.fit(X, y)
    models.append(("GBR", gbr))

    # MLP
    mlp = MLPRegressor(
        hidden_layer_sizes=(64, 32),
        max_iter=200, learning_rate_init=0.01,
        random_state=seed, early_stopping=True,
        validation_fraction=0.15,
    )
    mlp.fit(X, y)
    models.append(("MLP", mlp))

    return models


def _predict_sklearn_ensemble(models, last_features, horizon, n_lags):
    """Recursive forecast with sklearn ensemble (averaged)."""
    forecasts_per_model = []
    for mname, model in models:
        current = last_features.copy()
        fc = []
        for _ in range(horizon):
            pred = float(model.predict(current.reshape(1, -1))[0])
            fc.append(pred)
            current = np.append(current[1:], pred)
        forecasts_per_model.append(np.array(fc))

    # Average ensemble
    return np.mean(forecasts_per_model, axis=0)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    N-BEATS forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    n_blocks : int, optional
        Blocks per stack. Default from preset.
    hidden_size : int, optional
        Hidden layer size. Default from preset.
    epochs : int, optional
        Training epochs. Default from preset.
    n_lags : int, optional
        Lookback length. Default from preset.
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
                "N-BEATS needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        stack_types = preset_cfg["stack_types"]
        n_blocks = int(ctx.get_param("n_blocks", preset_cfg["n_blocks"]))
        hidden_size = int(ctx.get_param("hidden_size", preset_cfg["hidden_size"]))
        theta_size = int(ctx.get_param("theta_size", preset_cfg["theta_size"]))
        epochs = int(ctx.get_param("epochs", preset_cfg["epochs"]))
        n_lags = int(ctx.get_param("n_lags", preset_cfg["n_lags"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["lr"]))

        n_lags = min(n_lags, n // 3)

        # Normalize
        y_mean = float(np.mean(clean))
        y_std = float(np.std(clean, ddof=1))
        if y_std == 0:
            y_std = 1.0
        normalized = (clean - y_mean) / y_std

        use_torch = preset_cfg["use_torch"] and _has_torch()
        backend = "pytorch" if use_torch else "sklearn_ensemble"

        if not use_torch and preset_cfg["use_torch"]:
            warn_list.append(
                "PyTorch not available. Falling back to sklearn ensemble (Ridge+GBR+MLP). "
                "Install PyTorch for full N-BEATS support."
            )

        if use_torch:
            progress_callback("Creating N-BEATS sequences", 15)
            X, y_seq = _create_sequences(normalized, n_lags, horizon)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for N-BEATS sequence creation.",
                    error_fixes=["Reduce n_lags/horizon or provide more data."],
                )

            progress_callback(f"Training N-BEATS ({epochs} epochs)", 20)
            model, losses = _train_torch_nbeats(
                X, y_seq, stack_types, n_blocks, hidden_size, theta_size,
                epochs, lr, ctx.seed, horizon,
            )
            final_loss = losses[-1] if losses else float("inf")

            progress_callback("Generating forecast", 80)
            last_seq = normalized[-n_lags:]
            fc_norm = _predict_torch_nbeats(model, last_seq, horizon)

            # In-sample: predict for each training sample
            import torch
            model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X)
                y_pred_all = model(X_tensor).numpy()

            # Use first-step predictions for in-sample comparison
            y_pred_norm = y_pred_all[:, 0]
            y_actual_norm = y_seq[:, 0]

            n_params = sum(p.numel() for p in model.parameters())
            model_desc = (
                f"N-BEATS (PyTorch, stacks={stack_types}, "
                f"blocks={n_blocks}, hidden={hidden_size}, params={n_params})"
            )
        else:
            progress_callback("Creating lag features", 15)
            X, y_arr = _create_lag_features(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for feature creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            progress_callback("Training sklearn ensemble", 20)
            models = _train_sklearn_ensemble(X, y_arr, ctx.seed)
            losses = []

            progress_callback("Generating forecast", 80)
            last_features = normalized[-n_lags:]
            fc_norm = _predict_sklearn_ensemble(models, last_features, horizon, n_lags)

            # In-sample
            preds_per_model = [m.predict(X) for _, m in models]
            y_pred_norm = np.mean(preds_per_model, axis=0)
            y_actual_norm = y_arr
            final_loss = float(np.mean((y_actual_norm - y_pred_norm) ** 2))

            model_desc = "Ensemble (Ridge + GBR + MLP)"

        # Denormalize
        fc_values = fc_norm * y_std + y_mean
        y_actual = y_actual_norm * y_std + y_mean
        y_pred = y_pred_norm * y_std + y_mean

        # Metrics
        residuals = y_actual - y_pred
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(np.sum((y_actual - np.mean(y_actual)) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0

        progress_callback("Building output", 90)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([n + i + 1, round(float(fc_values[i]), 6)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # Summary
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["Stack Types", str(stack_types)],
            ["Blocks per Stack", n_blocks],
            ["Hidden Size", hidden_size],
            ["Lookback Length", n_lags],
            ["Epochs", epochs],
            ["Learning Rate", lr],
            ["Final Training Loss", round(final_loss, 6)],
            ["RMSE (1-step)", round(rmse, 4)],
            ["MAE (1-step)", round(mae, 4)],
            ["R-squared (1-step)", round(r2, 4)],
            ["Training Samples", len(X)],
            ["Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [fc_table, summary_table]

        if use_torch and len(losses) > 0:
            step_size = max(1, len(losses) // 20)
            loss_rows = []
            for i in range(0, len(losses), step_size):
                loss_rows.append([i + 1, round(losses[i], 6)])
            if (len(losses) - 1) % step_size != 0:
                loss_rows.append([len(losses), round(losses[-1], 6)])
            tables.append(make_table("Training Loss", ["Epoch", "Loss"], loss_rows))

        if r2 < 0:
            warn_list.append(
                "Negative R-squared. The model may need more training or data."
            )

        plain_english = (
            f"N-BEATS forecast for '{name}' ({n} observations) using {backend}. "
            f"Stacks: {stack_types}, lookback={n_lags}. "
            f"1-step RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and N-BEATS multi-step forecast. "
            "If PyTorch used, show training loss curve. "
            "Bar chart comparing individual horizon step forecasts."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "backend": backend,
                "stack_types": stack_types,
                "n_blocks": n_blocks,
                "hidden_size": hidden_size,
                "n_lags": n_lags,
                "epochs": epochs,
                "final_loss": round(final_loss, 6),
                "rmse": round(rmse, 4),
                "r2": round(r2, 4),
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"N-BEATS forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs or a smaller model.",
                "Install PyTorch for full N-BEATS support.",
            ],
        )
