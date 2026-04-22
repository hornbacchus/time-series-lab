"""
Temporal Convolutional Network (TCN) Forecast for Time Series Lab.

Uses PyTorch to implement a TCN with causal dilated convolutions when available.
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
        "n_channels": [16, 16], "kernel_size": 3, "epochs": 50,
        "n_lags": 8, "lr": 0.01, "use_torch": False,
    },
    "Balanced": {
        "n_channels": [32, 32], "kernel_size": 3, "epochs": 100,
        "n_lags": 16, "lr": 0.005, "use_torch": True,
    },
    "Thorough": {
        "n_channels": [64, 64, 64], "kernel_size": 5, "epochs": 300,
        "n_lags": 32, "lr": 0.001, "use_torch": True,
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
    """Create sliding-window sequences."""
    X, y = [], []
    for i in range(len(data) - seq_len):
        X.append(data[i:i + seq_len])
        y.append(data[i + seq_len])
    return np.array(X), np.array(y)


def _create_lag_features(series, n_lags):
    """Create lag features for MLP fallback."""
    n = len(series)
    features, targets = [], []
    for i in range(n_lags, n):
        features.append(series[i - n_lags:i])
        targets.append(series[i])
    return np.array(features), np.array(targets)


def _build_tcn_model(input_size, n_channels, kernel_size, seq_len):
    """Build a TCN model using PyTorch."""
    import torch
    import torch.nn as nn

    class CausalConv1d(nn.Module):
        def __init__(self, in_ch, out_ch, kernel_size, dilation):
            super().__init__()
            self.padding = (kernel_size - 1) * dilation
            self.conv = nn.Conv1d(in_ch, out_ch, kernel_size,
                                  padding=self.padding, dilation=dilation)
            self.relu = nn.ReLU()
            self.dropout = nn.Dropout(0.1)

        def forward(self, x):
            out = self.conv(x)
            if self.padding > 0:
                out = out[:, :, :-self.padding]
            return self.dropout(self.relu(out))

    class ResidualBlock(nn.Module):
        def __init__(self, in_ch, out_ch, kernel_size, dilation):
            super().__init__()
            self.conv1 = CausalConv1d(in_ch, out_ch, kernel_size, dilation)
            self.conv2 = CausalConv1d(out_ch, out_ch, kernel_size, dilation)
            self.downsample = nn.Conv1d(in_ch, out_ch, 1) if in_ch != out_ch else None
            self.relu = nn.ReLU()

        def forward(self, x):
            residual = x if self.downsample is None else self.downsample(x)
            out = self.conv1(x)
            out = self.conv2(out)
            return self.relu(out + residual)

    class TCN(nn.Module):
        def __init__(self, input_size, n_channels, kernel_size):
            super().__init__()
            layers = []
            num_levels = len(n_channels)
            for i in range(num_levels):
                dilation = 2 ** i
                in_ch = input_size if i == 0 else n_channels[i - 1]
                out_ch = n_channels[i]
                layers.append(ResidualBlock(in_ch, out_ch, kernel_size, dilation))
            self.network = nn.Sequential(*layers)
            self.fc = nn.Linear(n_channels[-1], 1)

        def forward(self, x):
            # x: (batch, channels, seq_len)
            out = self.network(x)
            # Take the last time step
            return self.fc(out[:, :, -1]).squeeze(-1)

    return TCN(input_size, n_channels, kernel_size)


def _train_torch_tcn(X, y, n_channels, kernel_size, epochs, lr, seed):
    """Train TCN model with PyTorch."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)

    # X shape: (n_samples, seq_len) -> (n_samples, 1, seq_len)
    X_tensor = torch.FloatTensor(X).unsqueeze(1)
    y_tensor = torch.FloatTensor(y)

    model = _build_tcn_model(1, n_channels, kernel_size, X.shape[1])
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


def _predict_torch_tcn(model, last_sequence, horizon):
    """Recursive multi-step forecast with TCN."""
    import torch

    model.eval()
    forecasts = []
    seq = last_sequence.copy()

    with torch.no_grad():
        for _ in range(horizon):
            x = torch.FloatTensor(seq).unsqueeze(0).unsqueeze(0)
            pred = float(model(x).item())
            forecasts.append(pred)
            seq = np.append(seq[1:], pred)

    return np.array(forecasts)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Temporal Convolutional Network forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 10.
    n_channels : list[int], optional
        Channel sizes per TCN layer. Default from preset.
    kernel_size : int, optional
        Convolution kernel size. Default from preset.
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
                "TCN needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 10))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_channels = ctx.get_param("n_channels", preset_cfg["n_channels"])
        if isinstance(n_channels, str):
            n_channels = preset_cfg["n_channels"]
        kernel_size = int(ctx.get_param("kernel_size", preset_cfg["kernel_size"]))
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
        backend = "pytorch" if use_torch else "sklearn_mlp"

        if not use_torch and preset_cfg["use_torch"]:
            warn_list.append(
                "PyTorch not available. Falling back to sklearn MLPRegressor. "
                "Install PyTorch for full TCN support."
            )

        if use_torch:
            progress_callback("Creating sequences", 15)
            X, y = _create_sequences(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for sequence creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            progress_callback(f"Training TCN ({epochs} epochs)", 20)
            model, losses = _train_torch_tcn(
                X, y, n_channels, kernel_size, epochs, lr, ctx.seed,
            )
            final_loss = losses[-1] if losses else float("inf")
            # Parameter count (Follow-up 1a D16 parity with Transformer).
            try:
                n_params = int(sum(p.numel() for p in model.parameters()))
            except Exception:
                n_params = None

            progress_callback("Generating forecasts", 80)
            last_seq = normalized[-n_lags:]
            fc_norm = _predict_torch_tcn(model, last_seq, horizon)

            # In-sample
            import torch
            model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X).unsqueeze(1)
                y_pred_norm = model(X_tensor).numpy()

            receptive_field = sum([(kernel_size - 1) * 2**i for i in range(len(n_channels))]) + 1
            model_desc = f"TCN (PyTorch, channels={n_channels}, k={kernel_size}, RF={receptive_field})"
        else:
            progress_callback("Creating lag features", 15)
            X, y = _create_lag_features(normalized, n_lags)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for feature creation.",
                    error_fixes=["Reduce n_lags or provide more data."],
                )

            hidden_sizes = tuple(n_channels)
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
            model.fit(X, y)
            final_loss = float(np.mean((y - model.predict(X)) ** 2))
            losses = list(getattr(model, "loss_curve_", []))
            # Parameter count (Follow-up 1a D16 parity with Transformer).
            try:
                n_params = int(
                    sum(c.size for c in model.coefs_)
                    + sum(b.size for b in model.intercepts_)
                )
            except Exception:
                n_params = None

            progress_callback("Generating forecasts", 80)
            current = normalized[-n_lags:]
            fc_list = []
            for _ in range(horizon):
                pred = float(model.predict(current.reshape(1, -1))[0])
                fc_list.append(pred)
                current = np.append(current[1:], pred)
            fc_norm = np.array(fc_list)

            y_pred_norm = model.predict(X)
            receptive_field = n_lags
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

        # Summary
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["Channels", str(n_channels)],
            ["Kernel Size", kernel_size],
            ["Receptive Field", receptive_field],
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

        tables = [fc_table, summary_table]

        # Training loss trajectory (if torch)
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
            f"TCN forecast for '{name}' ({n} observations) using {backend}. "
            f"Architecture: channels={n_channels}, kernel={kernel_size}, "
            f"receptive field={receptive_field}. "
            f"RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and TCN forecast continuation. "
            "If PyTorch was used, include training loss curve. "
            "Overlay fitted values on original series."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(fc_values[-1]) if len(fc_values) else _last_observed_value
        _n_train = int(len(X))
        _initial_loss = float(losses[0]) if losses else None
        _loss_curve_summary = None
        if losses and len(losses) >= 3:
            mid_start = len(losses) // 3
            mid_end = 2 * len(losses) // 3
            mid_slice = losses[mid_start:mid_end] if mid_end > mid_start else losses
            _loss_curve_summary = {
                "initial": float(losses[0]),
                "final": float(losses[-1]),
                "median_middle_30pct": float(np.median(mid_slice)),
                "n_epochs": len(losses),
            }

        audit = {
            "backend": backend,
            "n_channels": n_channels,
            "kernel_size": kernel_size,
            "receptive_field": receptive_field,
            "n_lags": n_lags,
            "epochs": epochs,
            "n_params": n_params,
            "final_loss": round(final_loss, 6),
            "initial_loss": round(_initial_loss, 6) if _initial_loss is not None else None,
            "loss_curve_summary": _loss_curve_summary,
            "rmse": round(rmse, 4),
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
        interp = build_interpretation("tcn_forecast", dict(audit))

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
            f"TCN forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs or a smaller architecture.",
                "Install PyTorch for full TCN support.",
            ],
        )
