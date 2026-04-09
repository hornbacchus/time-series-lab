"""
LSTM/GRU Forecast for Time Series Lab.

Uses PyTorch LSTM or GRU networks when available, falling back to
sklearn MLPRegressor with lag features when PyTorch is not installed.
Full training only under Thorough preset; Fast/Balanced use a simpler model.
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
        "hidden_size": 32, "n_layers": 1, "epochs": 50,
        "n_lags": 8, "lr": 0.01, "use_torch": False,
    },
    "Balanced": {
        "hidden_size": 64, "n_layers": 2, "epochs": 100,
        "n_lags": 12, "lr": 0.005, "use_torch": True,
    },
    "Thorough": {
        "hidden_size": 128, "n_layers": 2, "epochs": 300,
        "n_lags": 24, "lr": 0.001, "use_torch": True,
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


def _create_sequences(data, seq_len):
    """Create sliding-window sequences for LSTM input."""
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i + seq_len])
        y.append(data[i + seq_len])
    return np.array(X), np.array(y)


def _create_lag_features(series, n_lags):
    """Create lag features for MLP fallback."""
    n = len(series)
    features = []
    targets = []
    for i in range(n_lags, n):
        features.append(series[i - n_lags:i])
        targets.append(series[i])
    return np.array(features), np.array(targets)


def _train_torch_model(X, y, model_type, hidden_size, n_layers, epochs, lr, seed):
    """Train LSTM or GRU model with PyTorch."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)

    class LSTMModel(nn.Module):
        def __init__(self, input_size, hidden_size, n_layers):
            super().__init__()
            self.lstm = nn.LSTM(input_size, hidden_size, n_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, 1)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.fc(out[:, -1, :]).squeeze(-1)

    class GRUModel(nn.Module):
        def __init__(self, input_size, hidden_size, n_layers):
            super().__init__()
            self.gru = nn.GRU(input_size, hidden_size, n_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, 1)

        def forward(self, x):
            out, _ = self.gru(x)
            return self.fc(out[:, -1, :]).squeeze(-1)

    # Reshape X: (n_samples, seq_len, 1)
    X_tensor = torch.FloatTensor(X).unsqueeze(-1)
    y_tensor = torch.FloatTensor(y)

    if model_type == "gru":
        model = GRUModel(1, hidden_size, n_layers)
    else:
        model = LSTMModel(1, hidden_size, n_layers)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        pred = model(X_tensor)
        loss = loss_fn(pred, y_tensor)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))

    model.eval()
    return model, losses


def _predict_torch(model, last_sequence, horizon):
    """Generate recursive multi-step forecast with PyTorch model."""
    import torch

    model.eval()
    forecasts = []
    seq = last_sequence.copy()

    with torch.no_grad():
        for _ in range(horizon):
            x = torch.FloatTensor(seq).unsqueeze(0).unsqueeze(-1)
            pred = float(model(x).item())
            forecasts.append(pred)
            seq = np.append(seq[1:], pred)

    return np.array(forecasts)


def _train_sklearn_mlp(X, y, hidden_sizes, epochs, lr, seed):
    """Train sklearn MLPRegressor as fallback."""
    from sklearn.neural_network import MLPRegressor

    model = MLPRegressor(
        hidden_layer_sizes=hidden_sizes,
        max_iter=epochs,
        learning_rate_init=lr,
        random_state=seed,
        early_stopping=True,
        validation_fraction=0.15,
        tol=1e-5,
    )
    model.fit(X, y)
    return model


def _predict_sklearn(model, last_features, horizon, n_lags):
    """Generate recursive multi-step forecast with sklearn MLP."""
    forecasts = []
    current = last_features.copy()

    for _ in range(horizon):
        pred = float(model.predict(current.reshape(1, -1))[0])
        forecasts.append(pred)
        current = np.append(current[1:], pred)

    return np.array(forecasts)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    LSTM/GRU forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    model_type : str
        "lstm" (default) or "gru".
    hidden_size : int, optional
        Hidden layer size. Default from preset.
    n_layers : int, optional
        Number of recurrent layers. Default from preset.
    epochs : int, optional
        Training epochs. Default from preset.
    n_lags : int, optional
        Sequence/lag length. Default from preset.
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
                "LSTM/GRU needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        model_type = ctx.get_param("model_type", "lstm").lower()
        if model_type not in ("lstm", "gru"):
            model_type = "lstm"

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        hidden_size = int(ctx.get_param("hidden_size", preset_cfg["hidden_size"]))
        n_layers = int(ctx.get_param("n_layers", preset_cfg["n_layers"]))
        epochs = int(ctx.get_param("epochs", preset_cfg["epochs"]))
        n_lags = int(ctx.get_param("n_lags", preset_cfg["n_lags"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["lr"]))

        n_lags = min(n_lags, n // 3)

        # Normalize data
        y_mean = float(np.mean(clean))
        y_std = float(np.std(clean, ddof=1))
        if y_std == 0:
            y_std = 1.0
        normalized = (clean - y_mean) / y_std

        use_torch = preset_cfg["use_torch"] and _has_torch()
        backend = "pytorch" if use_torch else "sklearn_mlp"

        if not use_torch and preset_cfg["use_torch"]:
            warn_list.append(
                "PyTorch not available. Falling back to sklearn MLPRegressor. "
                "Install PyTorch for full LSTM/GRU support."
            )

        if use_torch:
            progress_callback(f"Creating {model_type.upper()} sequences", 15)
            X, y = _create_sequences(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for sequence creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            progress_callback(f"Training {model_type.upper()} ({epochs} epochs)", 20)
            model, losses = _train_torch_model(
                X, y, model_type, hidden_size, n_layers, epochs, lr, ctx.seed,
            )
            final_loss = losses[-1] if losses else float("inf")

            progress_callback("Generating forecasts", 80)
            last_seq = normalized[-n_lags:]
            fc_norm = _predict_torch(model, last_seq, horizon)

            # In-sample predictions
            import torch
            model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X).unsqueeze(-1)
                y_pred_norm = model(X_tensor).numpy()

            model_desc = f"{model_type.upper()} (PyTorch, {n_layers}x{hidden_size})"
        else:
            progress_callback("Creating lag features", 15)
            X, y = _create_lag_features(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for feature creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            hidden_sizes = tuple([hidden_size] * n_layers)
            progress_callback(f"Training MLP ({epochs} epochs)", 20)
            model = _train_sklearn_mlp(X, y, hidden_sizes, epochs, lr, ctx.seed)
            final_loss = float(np.mean((y - model.predict(X)) ** 2))

            progress_callback("Generating forecasts", 80)
            last_features = normalized[-n_lags:]
            fc_norm = _predict_sklearn(model, last_features, horizon, n_lags)

            # In-sample predictions
            y_pred_norm = model.predict(X)

            model_desc = f"MLPRegressor (sklearn, layers={hidden_sizes})"

        # Denormalize
        fc_values = fc_norm * y_std + y_mean
        y_actual = y * y_std + y_mean
        y_pred = y_pred_norm * y_std + y_mean

        # Metrics
        residuals = y_actual - y_pred
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        r2 = float(1.0 - np.sum(residuals ** 2) / np.sum((y_actual - np.mean(y_actual)) ** 2))

        progress_callback("Building output", 90)

        # Forecast table
        fc_rows = []
        for i in range(horizon):
            fc_rows.append([n + i + 1, round(float(fc_values[i]), 6)])
        fc_table = make_table("Forecast", ["Step", "Forecast"], fc_rows)

        # Summary table
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["Model Type", model_type.upper()],
            ["Hidden Size", hidden_size],
            ["Layers", n_layers],
            ["Sequence Length", n_lags],
            ["Epochs", epochs],
            ["Learning Rate", lr],
            ["Final Training Loss", round(final_loss, 6)],
            ["RMSE", round(rmse, 4)],
            ["MAE", round(mae, 4)],
            ["R-squared", round(r2, 4)],
            ["Training Samples", len(X)],
            ["Horizon", horizon],
        ]
        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        # Training loss trajectory (if torch)
        if use_torch and len(losses) > 0:
            step_size = max(1, len(losses) // 20)
            loss_rows = []
            for i in range(0, len(losses), step_size):
                loss_rows.append([i + 1, round(losses[i], 6)])
            if (len(losses) - 1) % step_size != 0:
                loss_rows.append([len(losses), round(losses[-1], 6)])
            loss_table = make_table("Training Loss", ["Epoch", "Loss"], loss_rows)
            tables = [fc_table, summary_table, loss_table]
        else:
            tables = [fc_table, summary_table]

        if r2 < 0:
            warn_list.append(
                "Negative R-squared indicates the model is worse than predicting the mean. "
                "Try more epochs, different hyperparameters, or a longer series."
            )
        if rmse > y_std:
            warn_list.append(
                "RMSE exceeds the series standard deviation, suggesting poor model fit."
            )

        plain_english = (
            f"{model_type.upper()} forecast for '{name}' ({n} observations) using {backend}. "
            f"Architecture: {n_layers} layer(s) x {hidden_size} units, "
            f"sequence length {n_lags}, trained for {epochs} epochs. "
            f"RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and forecast continuation. "
            "If PyTorch was used, include a training loss curve in a secondary panel. "
            "Overlay fitted values on the original series."
        )

        progress_callback("Done", 100)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields={
                "model_type": model_type,
                "backend": backend,
                "hidden_size": hidden_size,
                "n_layers": n_layers,
                "n_lags": n_lags,
                "epochs": epochs,
                "learning_rate": lr,
                "final_loss": round(final_loss, 6),
                "rmse": round(rmse, 4),
                "mae": round(mae, 4),
                "r2": round(r2, 4),
                "horizon": horizon,
            },
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"LSTM/GRU forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs or a smaller model.",
                "Install PyTorch for full LSTM/GRU support, or use sklearn fallback.",
            ],
        )
