"""
Transformer Forecast for Time Series Lab.

Uses PyTorch to implement a Transformer encoder for time series forecasting.
Falls back to sklearn MLPRegressor with lag features when PyTorch is not installed.
Full training only under Thorough preset.
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
        "d_model": 32, "n_heads": 2, "n_encoder_layers": 1,
        "dim_feedforward": 64, "epochs": 50, "n_lags": 8,
        "lr": 0.01, "dropout": 0.1, "use_torch": False,
    },
    "Balanced": {
        "d_model": 64, "n_heads": 4, "n_encoder_layers": 2,
        "dim_feedforward": 128, "epochs": 150, "n_lags": 16,
        "lr": 0.005, "dropout": 0.1, "use_torch": True,
    },
    "Thorough": {
        "d_model": 128, "n_heads": 8, "n_encoder_layers": 4,
        "dim_feedforward": 256, "epochs": 500, "n_lags": 32,
        "lr": 0.001, "dropout": 0.1, "use_torch": True,
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


def _create_sequences(data, seq_len):
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i + seq_len])
        y.append(data[i + seq_len])
    return np.array(X), np.array(y)


def _create_lag_features(series, n_lags):
    n = len(series)
    features, targets = [], []
    for i in range(n_lags, n):
        features.append(series[i - n_lags:i])
        targets.append(series[i])
    return np.array(features), np.array(targets)


def _build_transformer_model(d_model, n_heads, n_encoder_layers, dim_feedforward,
                              seq_len, dropout):
    """Build a Transformer encoder model for time series."""
    import torch
    import torch.nn as nn
    import math

    class PositionalEncoding(nn.Module):
        def __init__(self, d_model, max_len=512, dropout=0.1):
            super().__init__()
            self.dropout = nn.Dropout(p=dropout)
            pe = torch.zeros(max_len, d_model)
            position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
            div_term = torch.exp(
                torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
            )
            pe[:, 0::2] = torch.sin(position * div_term)
            if d_model > 1:
                pe[:, 1::2] = torch.cos(position * div_term[:d_model // 2])
            pe = pe.unsqueeze(0)
            self.register_buffer("pe", pe)

        def forward(self, x):
            x = x + self.pe[:, :x.size(1), :]
            return self.dropout(x)

    class TimeSeriesTransformer(nn.Module):
        def __init__(self, d_model, n_heads, n_encoder_layers, dim_feedforward,
                     seq_len, dropout):
            super().__init__()
            self.input_proj = nn.Linear(1, d_model)
            self.pos_encoder = PositionalEncoding(d_model, max_len=seq_len + 10,
                                                   dropout=dropout)
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=d_model,
                nhead=n_heads,
                dim_feedforward=dim_feedforward,
                dropout=dropout,
                batch_first=True,
            )
            self.encoder = nn.TransformerEncoder(encoder_layer, num_layers=n_encoder_layers)
            self.output_fc = nn.Sequential(
                nn.Linear(d_model * seq_len, dim_feedforward),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(dim_feedforward, 1),
            )
            self.seq_len = seq_len
            self.d_model = d_model

        def forward(self, x):
            # x: (batch, seq_len, 1)
            x = self.input_proj(x)      # (batch, seq_len, d_model)
            x = self.pos_encoder(x)
            x = self.encoder(x)          # (batch, seq_len, d_model)
            x = x.reshape(x.size(0), -1) # flatten
            return self.output_fc(x).squeeze(-1)

    return TimeSeriesTransformer(d_model, n_heads, n_encoder_layers,
                                  dim_feedforward, seq_len, dropout)


def _train_torch_transformer(X, y, d_model, n_heads, n_encoder_layers,
                              dim_feedforward, epochs, lr, dropout, seed):
    """Train Transformer model."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    seq_len = X.shape[1]

    model = _build_transformer_model(d_model, n_heads, n_encoder_layers,
                                      dim_feedforward, seq_len, dropout)

    # X: (n_samples, seq_len) -> (n_samples, seq_len, 1)
    X_tensor = torch.FloatTensor(X).unsqueeze(-1)
    y_tensor = torch.FloatTensor(y)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.StepLR(optimizer, step_size=max(50, epochs // 5),
                                                  gamma=0.5)
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
        scheduler.step()
        losses.append(float(loss.item()))

    model.eval()
    return model, losses


def _predict_torch_transformer(model, last_sequence, horizon):
    """Recursive multi-step forecast with Transformer."""
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


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Transformer forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    d_model : int, optional
        Model dimension. Default from preset.
    n_heads : int, optional
        Number of attention heads. Default from preset.
    n_encoder_layers : int, optional
        Number of Transformer encoder layers. Default from preset.
    epochs : int, optional
        Training epochs. Default from preset.
    n_lags : int, optional
        Sequence length. Default from preset.
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
                "Transformer needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        d_model = int(ctx.get_param("d_model", preset_cfg["d_model"]))
        n_heads = int(ctx.get_param("n_heads", preset_cfg["n_heads"]))
        n_encoder_layers = int(ctx.get_param("n_encoder_layers", preset_cfg["n_encoder_layers"]))
        dim_feedforward = int(ctx.get_param("dim_feedforward", preset_cfg["dim_feedforward"]))
        epochs = int(ctx.get_param("epochs", preset_cfg["epochs"]))
        n_lags = int(ctx.get_param("n_lags", preset_cfg["n_lags"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["lr"]))
        dropout = float(ctx.get_param("dropout", preset_cfg["dropout"]))

        # Ensure d_model is divisible by n_heads
        if d_model % n_heads != 0:
            d_model = n_heads * (d_model // n_heads)
            if d_model == 0:
                d_model = n_heads
            warn_list.append(f"d_model adjusted to {d_model} (must be divisible by n_heads={n_heads}).")

        n_lags = min(n_lags, n // 3)

        # Normalize
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
                "Install PyTorch for full Transformer support."
            )

        if use_torch:
            progress_callback("Creating sequences", 15)
            X, y_arr = _create_sequences(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for sequence creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            progress_callback(f"Training Transformer ({epochs} epochs)", 20)
            model, losses = _train_torch_transformer(
                X, y_arr, d_model, n_heads, n_encoder_layers,
                dim_feedforward, epochs, lr, dropout, ctx.seed,
            )
            final_loss = losses[-1] if losses else float("inf")

            progress_callback("Generating forecasts", 80)
            last_seq = normalized[-n_lags:]
            fc_norm = _predict_torch_transformer(model, last_seq, horizon)

            # In-sample
            import torch
            model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X).unsqueeze(-1)
                y_pred_norm = model(X_tensor).numpy()

            n_params = sum(p.numel() for p in model.parameters())
            model_desc = (
                f"Transformer (PyTorch, d={d_model}, heads={n_heads}, "
                f"layers={n_encoder_layers}, params={n_params})"
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

            # Use MLP as Transformer surrogate
            hidden_sizes = (dim_feedforward, dim_feedforward)
            progress_callback(f"Training MLP ({epochs} epochs)", 20)
            from sklearn.neural_network import MLPRegressor
            model = MLPRegressor(
                hidden_layer_sizes=hidden_sizes,
                max_iter=epochs,
                learning_rate_init=lr,
                random_state=ctx.seed,
                early_stopping=True,
                validation_fraction=0.15,
                tol=1e-5,
            )
            model.fit(X, y_arr)
            final_loss = float(np.mean((y_arr - model.predict(X)) ** 2))
            losses = []

            progress_callback("Generating forecasts", 80)
            current = normalized[-n_lags:]
            fc_list = []
            for _ in range(horizon):
                pred = float(model.predict(current.reshape(1, -1))[0])
                fc_list.append(pred)
                current = np.append(current[1:], pred)
            fc_norm = np.array(fc_list)

            y_pred_norm = model.predict(X)
            n_params = sum(c.size for c in model.coefs_) + sum(b.size for b in model.intercepts_)
            model_desc = f"MLPRegressor (sklearn, layers={hidden_sizes}, params={n_params})"

        # Denormalize
        fc_values = fc_norm * y_std + y_mean
        y_actual = y_arr * y_std + y_mean
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
            ["d_model", d_model],
            ["Attention Heads", n_heads],
            ["Encoder Layers", n_encoder_layers],
            ["Feedforward Dim", dim_feedforward],
            ["Dropout", dropout],
            ["Sequence Length", n_lags],
            ["Epochs", epochs],
            ["Learning Rate", lr],
            ["Parameters", n_params if use_torch or backend == "sklearn_mlp" else "N/A"],
            ["Final Training Loss", round(final_loss, 6)],
            ["RMSE", round(rmse, 4)],
            ["MAE", round(mae, 4)],
            ["R-squared", round(r2, 4)],
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
                "Negative R-squared. The model is worse than predicting the mean. "
                "Try more epochs, lower learning rate, or more data."
            )
        if use_torch and len(X) < 50:
            warn_list.append(
                f"Only {len(X)} training samples. Transformers typically need more data. "
                "Consider a simpler model for short series."
            )

        plain_english = (
            f"Transformer forecast for '{name}' ({n} observations) using {backend}. "
            f"Architecture: d_model={d_model}, heads={n_heads}, "
            f"layers={n_encoder_layers}, sequence length={n_lags}. "
            f"RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and Transformer forecast continuation. "
            "If PyTorch used, show training loss curve and attention weight heatmap if feasible. "
            "Overlay fitted values."
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
                "d_model": d_model,
                "n_heads": n_heads,
                "n_encoder_layers": n_encoder_layers,
                "dim_feedforward": dim_feedforward,
                "n_lags": n_lags,
                "epochs": epochs,
                "n_params": n_params if use_torch or backend == "sklearn_mlp" else None,
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
            f"Transformer forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs, smaller d_model, or fewer layers.",
                "Install PyTorch for full Transformer support.",
                "Ensure d_model is divisible by n_heads.",
            ],
        )
