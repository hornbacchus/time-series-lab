"""
N-HiTS (Neural Hierarchical Interpolation for Time Series) Forecast
for Time Series Lab.

Uses PyTorch to implement the N-HiTS architecture with multi-rate signal
sampling and hierarchical interpolation. Falls back to an sklearn ensemble
(Ridge + GBR + MLP) when PyTorch is not installed.

N-HiTS improves on N-BEATS by adding hierarchical interpolation for
more efficient long-horizon forecasting.
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
        "n_stacks": 2, "n_blocks": 2, "hidden_size": 64,
        "pooling_sizes": [2, 1],
        "epochs": 50, "n_lags": 8, "lr": 0.01, "use_torch": False,
    },
    "Balanced": {
        "n_stacks": 3, "n_blocks": 3, "hidden_size": 128,
        "pooling_sizes": [4, 2, 1],
        "epochs": 50, "n_lags": 16, "lr": 0.005, "use_torch": True,
    },
    "Thorough": {
        "n_stacks": 3, "n_blocks": 4, "hidden_size": 256,
        "pooling_sizes": [8, 4, 1],
        "epochs": 150, "n_lags": 32, "lr": 0.001, "use_torch": True,
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


def _create_sequences(data, lookback, horizon):
    """Create input/output sequence pairs for N-HiTS style training."""
    X, y = [], []
    for i in range(len(data) - lookback - horizon + 1):
        X.append(data[i:i + lookback])
        y.append(data[i + lookback:i + lookback + horizon])
    return np.array(X), np.array(y)


def _create_lag_features(series, n_lags):
    """Create lag features for sklearn fallback."""
    n = len(series)
    features, targets = [], []
    for i in range(n_lags, n):
        features.append(series[i - n_lags:i])
        targets.append(series[i])
    return np.array(features), np.array(targets)


def _build_nhits_model(lookback, horizon, n_stacks, n_blocks, hidden_size, pooling_sizes):
    """Build N-HiTS model using PyTorch."""
    import torch
    import torch.nn as nn

    class NHiTSBlock(nn.Module):
        def __init__(self, input_size, hidden_size, horizon, pool_size):
            super().__init__()
            self.pool_size = pool_size
            pooled_input = max(1, input_size // pool_size)
            # Number of interpolation coefficients (smaller than horizon)
            self.n_coeff = max(1, horizon // pool_size)

            self.fc = nn.Sequential(
                nn.Linear(pooled_input, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
                nn.Linear(hidden_size, hidden_size),
                nn.ReLU(),
            )
            self.backcast_fc = nn.Linear(hidden_size, pooled_input)
            self.forecast_fc = nn.Linear(hidden_size, self.n_coeff)
            self.horizon = horizon

        def forward(self, x):
            # MaxPool1d for multi-rate sampling
            if self.pool_size > 1 and x.shape[-1] > self.pool_size:
                # Reshape for pooling: (batch, 1, seq_len)
                x_pool = x.unsqueeze(1)
                x_pool = nn.functional.max_pool1d(
                    x_pool, kernel_size=self.pool_size,
                    stride=self.pool_size, ceil_mode=True
                )
                x_pool = x_pool.squeeze(1)
            else:
                x_pool = x

            h = self.fc(x_pool)
            backcast = self.backcast_fc(h)
            forecast_coeff = self.forecast_fc(h)

            # Hierarchical interpolation: upsample coefficients to horizon length
            if forecast_coeff.shape[-1] < self.horizon:
                forecast = nn.functional.interpolate(
                    forecast_coeff.unsqueeze(1),
                    size=self.horizon,
                    mode="linear",
                    align_corners=False,
                ).squeeze(1)
            else:
                forecast = forecast_coeff[:, :self.horizon]

            return backcast, forecast

    class NHiTSStack(nn.Module):
        def __init__(self, input_size, n_blocks, hidden_size, horizon, pool_size):
            super().__init__()
            pooled_input = max(1, input_size // pool_size)
            self.blocks = nn.ModuleList([
                NHiTSBlock(input_size, hidden_size, horizon, pool_size)
                for _ in range(n_blocks)
            ])
            self.pool_size = pool_size

        def forward(self, x):
            residual = x
            stack_forecast = 0
            for block in self.blocks:
                backcast, forecast = block(residual)
                # Upsample backcast back to original size if needed
                if backcast.shape[-1] < residual.shape[-1]:
                    backcast = nn.functional.interpolate(
                        backcast.unsqueeze(1),
                        size=residual.shape[-1],
                        mode="linear",
                        align_corners=False,
                    ).squeeze(1)
                elif backcast.shape[-1] > residual.shape[-1]:
                    backcast = backcast[:, :residual.shape[-1]]
                residual = residual - backcast
                stack_forecast = stack_forecast + forecast
            return residual, stack_forecast

    class NHiTS(nn.Module):
        def __init__(self, input_size, n_stacks, n_blocks, hidden_size, horizon, pooling_sizes):
            super().__init__()
            self.stacks = nn.ModuleList([
                NHiTSStack(input_size, n_blocks, hidden_size, horizon,
                           pooling_sizes[i] if i < len(pooling_sizes) else 1)
                for i in range(n_stacks)
            ])

        def forward(self, x):
            residual = x
            total_forecast = 0
            for stack in self.stacks:
                residual, forecast = stack(residual)
                total_forecast = total_forecast + forecast
            return total_forecast

    return NHiTS(lookback, n_stacks, n_blocks, hidden_size, horizon, pooling_sizes)


def _train_torch_nhits(X, y, n_stacks, n_blocks, hidden_size, pooling_sizes,
                        epochs, lr, seed, horizon):
    """Train N-HiTS model."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)
    lookback = X.shape[1]

    model = _build_nhits_model(lookback, horizon, n_stacks, n_blocks,
                                hidden_size, pooling_sizes)

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


def _predict_torch_nhits(model, last_sequence, horizon):
    """Generate forecast with N-HiTS."""
    import torch

    model.eval()
    with torch.no_grad():
        x = torch.FloatTensor(last_sequence).unsqueeze(0)
        forecast = model(x).squeeze(0).numpy()

    return forecast[:horizon]


def _train_sklearn_ensemble(X, y, seed):
    """Train an ensemble of sklearn models as N-HiTS surrogate."""
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.linear_model import Ridge
    from sklearn.neural_network import MLPRegressor

    models = []

    ridge = Ridge(alpha=1.0, random_state=seed)
    ridge.fit(X, y)
    models.append(("Ridge", ridge))

    gbr = GradientBoostingRegressor(
        n_estimators=100, max_depth=3,
        learning_rate=0.1, random_state=seed,
    )
    gbr.fit(X, y)
    models.append(("GBR", gbr))

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

    return np.mean(forecasts_per_model, axis=0)


def run(ctx: RunContext, progress_callback) -> dict:
    """
    N-HiTS forecast.

    Parameters (via ctx.params)
    ---------------------------
    horizon : int
        Forecast horizon. Default 12.
    n_stacks : int, optional
        Number of hierarchical stacks. Default 3.
    epochs : int, optional
        Training epochs. Default 50.
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
                "N-HiTS needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        horizon = int(ctx.get_param("horizon", 12))
        if horizon < 1:
            horizon = 1

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        n_stacks = int(ctx.get_param("n_stacks", preset_cfg["n_stacks"]))
        n_blocks = int(ctx.get_param("n_blocks", preset_cfg["n_blocks"]))
        # Honor user-supplied pooling_sizes override (Follow-up 1a
        # fix — was silently ignored, always using preset default).
        _pooling_user = ctx.get_param("pooling_sizes", None)
        if _pooling_user is not None:
            try:
                _candidate = list(_pooling_user)
                if all(isinstance(p, (int, float)) and p >= 1 for p in _candidate) and _candidate:
                    preset_cfg = dict(preset_cfg)
                    preset_cfg["pooling_sizes"] = [int(p) for p in _candidate]
            except (TypeError, ValueError):
                pass
        hidden_size = int(ctx.get_param("hidden_size", preset_cfg["hidden_size"]))
        epochs = int(ctx.get_param("epochs", preset_cfg["epochs"]))
        n_lags = int(ctx.get_param("n_lags", preset_cfg["n_lags"]))
        lr = float(ctx.get_param("learning_rate", preset_cfg["lr"]))
        pooling_sizes = preset_cfg["pooling_sizes"]

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
                "Install PyTorch for full N-HiTS support."
            )

        if use_torch:
            progress_callback("Creating N-HiTS sequences", 15)
            X, y_seq = _create_sequences(normalized, n_lags, horizon)
            if len(X) < 5:
                return make_error_response(
                    ctx,
                    "Not enough data for N-HiTS sequence creation.",
                    error_fixes=["Reduce n_lags/horizon or provide more data."],
                )

            progress_callback(f"Training N-HiTS ({epochs} epochs)", 20)
            model, losses = _train_torch_nhits(
                X, y_seq, n_stacks, n_blocks, hidden_size, pooling_sizes,
                epochs, lr, ctx.seed, horizon,
            )
            final_loss = losses[-1] if losses else float("inf")

            progress_callback("Generating forecast", 80)
            last_seq = normalized[-n_lags:]
            fc_norm = _predict_torch_nhits(model, last_seq, horizon)

            # In-sample predictions
            import torch
            model.eval()
            with torch.no_grad():
                X_tensor = torch.FloatTensor(X)
                y_pred_all = model(X_tensor).numpy()

            # Use first-step predictions for in-sample comparison
            y_pred_norm = y_pred_all[:, 0]
            y_actual_norm = y_seq[:, 0]

            n_params = int(sum(p.numel() for p in model.parameters()))
            model_desc = (
                f"N-HiTS (PyTorch, stacks={n_stacks}, "
                f"blocks={n_blocks}, hidden={hidden_size}, "
                f"pooling={pooling_sizes}, params={n_params})"
            )
        else:
            # Follow-up B10 — n_params is meaningful only on the
            # PyTorch path (a single torch.nn.Module with a defined
            # parameter count). The sklearn fallback uses an
            # ensemble of {Ridge, GradientBoostingRegressor,
            # MLPRegressor}; counting parameters across a
            # heterogeneous ensemble is ambiguous, so audit-field
            # n_params stays None on this branch (matches the
            # 1a-fix convention for LSTM/GRU/TCN sklearn
            # fallbacks).
            n_params = None
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

        # Training log
        tables = [fc_table]

        if use_torch and len(losses) > 0:
            step_size = max(1, len(losses) // 20)
            loss_rows = []
            for i in range(0, len(losses), step_size):
                loss_rows.append([i + 1, round(losses[i], 6)])
            if (len(losses) - 1) % step_size != 0:
                loss_rows.append([len(losses), round(losses[-1], 6)])
            tables.append(make_table("Training Log", ["Epoch", "Loss"], loss_rows))

        # Summary
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["N Stacks", n_stacks],
            ["Blocks per Stack", n_blocks],
            ["Hidden Size", hidden_size],
            ["Pooling Sizes", str(pooling_sizes)],
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
        tables.append(summary_table)

        if r2 < 0:
            warn_list.append(
                "Negative R-squared. The model may need more training or data."
            )

        plain_english = (
            f"N-HiTS forecast for '{name}' ({n} observations) using {backend}. "
            f"{n_stacks} stacks, pooling={pooling_sizes}, lookback={n_lags}. "
            f"1-step RMSE={rmse:.4f}, R-squared={r2:.4f}. "
            f"{horizon}-step forecast produced."
        )

        charting = (
            "Line chart with original series and N-HiTS multi-step forecast. "
            "If PyTorch used, show training loss curve. "
            "Bar chart comparing individual horizon step forecasts."
        )

        progress_callback("Done", 100)

        # ── Interpretation layer (Prompt C7) ──────────────────────────
        _series_mean = float(np.mean(clean))
        _series_std = float(np.std(clean, ddof=1)) if len(clean) > 1 else 0.0
        _last_observed_value = float(clean[-1])
        _forecast_end_value = float(fc_values[-1]) if len(fc_values) else _last_observed_value
        _n_train = int(len(X)) if "X" in dir() else n - n_lags
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
            "n_stacks": n_stacks,
            "n_blocks": n_blocks,
            "hidden_size": hidden_size,
            "pooling_sizes": pooling_sizes,
            "n_lags": n_lags,
            "epochs": epochs,
            # Follow-up B10 — surface the trained model's parameter
            # count on the PyTorch path (already computed during
            # training; previously embedded in model_desc only).
            # None on the sklearn ensemble fallback path.
            "n_params": n_params,
            "final_loss": round(final_loss, 6),
            "initial_loss": round(_initial_loss, 6) if _initial_loss is not None else None,
            "loss_curve_summary": _loss_curve_summary,
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
        interp = build_interpretation("nhits_forecast", dict(audit))

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
            f"N-HiTS forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs or a smaller model.",
                "Install PyTorch for full N-HiTS support.",
            ],
        )
