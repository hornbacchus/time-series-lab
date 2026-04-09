"""
Autoencoder-based Anomaly Detection for Time Series Lab.

Uses a PyTorch autoencoder when available to learn normal patterns in sliding
windows and detect anomalies via reconstruction error. Falls back to sklearn
PCA reconstruction error when PyTorch is not installed.

This is a DETECTION technique, not a forecasting technique.
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
        "hidden_dim": 8, "window_size": 5, "epochs": 20,
        "lr": 0.01, "use_torch": False,
        "n_pca_components": 3,
    },
    "Balanced": {
        "hidden_dim": 16, "window_size": 10, "epochs": 30,
        "lr": 0.005, "use_torch": True,
        "n_pca_components": 5,
    },
    "Thorough": {
        "hidden_dim": 32, "window_size": 20, "epochs": 80,
        "lr": 0.001, "use_torch": True,
        "n_pca_components": 8,
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


def _create_windows(data, window_size):
    """Create sliding windows from the series."""
    windows = []
    for i in range(len(data) - window_size + 1):
        windows.append(data[i:i + window_size])
    return np.array(windows)


def _train_torch_autoencoder(X, hidden_dim, epochs, lr, seed):
    """Train a PyTorch autoencoder and return reconstruction errors."""
    import torch
    import torch.nn as nn

    torch.manual_seed(seed)

    input_dim = X.shape[1]

    class Autoencoder(nn.Module):
        def __init__(self, input_dim, hidden_dim):
            super().__init__()
            mid_dim = max(hidden_dim + 4, (input_dim + hidden_dim) // 2)
            self.encoder = nn.Sequential(
                nn.Linear(input_dim, mid_dim),
                nn.ReLU(),
                nn.Linear(mid_dim, hidden_dim),
                nn.ReLU(),
            )
            self.decoder = nn.Sequential(
                nn.Linear(hidden_dim, mid_dim),
                nn.ReLU(),
                nn.Linear(mid_dim, input_dim),
            )

        def forward(self, x):
            encoded = self.encoder(x)
            decoded = self.decoder(encoded)
            return decoded

    X_tensor = torch.FloatTensor(X)

    model = Autoencoder(input_dim, hidden_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss_fn = nn.MSELoss()

    model.train()
    losses = []
    for epoch in range(epochs):
        optimizer.zero_grad()
        reconstructed = model(X_tensor)
        loss = loss_fn(reconstructed, X_tensor)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.item()))

    # Compute per-window reconstruction errors
    model.eval()
    with torch.no_grad():
        reconstructed = model(X_tensor).numpy()

    recon_errors = np.mean((X - reconstructed) ** 2, axis=1)

    return model, recon_errors, losses


def _train_pca_anomaly(X, n_components):
    """Use PCA reconstruction error as anomaly detector."""
    from sklearn.decomposition import PCA
    from sklearn.preprocessing import StandardScaler

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    n_components = min(n_components, X.shape[1], X.shape[0])
    pca = PCA(n_components=n_components)
    X_transformed = pca.fit_transform(X_scaled)
    X_reconstructed = pca.inverse_transform(X_transformed)
    X_reconstructed = scaler.inverse_transform(X_reconstructed)

    recon_errors = np.mean((X - X_reconstructed) ** 2, axis=1)
    explained_variance = float(np.sum(pca.explained_variance_ratio_))

    return pca, recon_errors, explained_variance


def run(ctx: RunContext, progress_callback) -> dict:
    """
    Autoencoder-based anomaly detection.

    Parameters (via ctx.params)
    ---------------------------
    contamination : float
        Expected proportion of anomalies (default 0.05).
    hidden_dim : int
        Autoencoder bottleneck dimension (default 16).
    window_size : int
        Sliding window size (default 10).
    epochs : int
        Training epochs for autoencoder (default 30).
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
                "Autoencoder anomaly detection needs at least 20.",
                error_fixes=["Provide a longer time series."],
            )

        contamination = float(ctx.get_param("contamination", 0.05))
        if contamination <= 0 or contamination >= 1:
            contamination = 0.05
            warn_list.append("Contamination must be in (0, 1). Defaulting to 0.05.")

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        hidden_dim = int(ctx.get_param("hidden_dim", preset_cfg["hidden_dim"]))
        window_size = int(ctx.get_param("window_size", preset_cfg["window_size"]))
        epochs = int(ctx.get_param("epochs", preset_cfg["epochs"]))
        lr = preset_cfg["lr"]

        # Ensure window size is reasonable
        window_size = max(2, min(window_size, n // 3))

        # Normalize data
        y_mean = float(np.mean(clean))
        y_std = float(np.std(clean, ddof=1))
        if y_std == 0:
            y_std = 1.0
        normalized = (clean - y_mean) / y_std

        progress_callback("Creating sliding windows", 15)

        windows = _create_windows(normalized, window_size)
        if len(windows) < 10:
            return make_error_response(
                ctx,
                "Not enough windows for anomaly detection. "
                "Try a smaller window_size or provide more data.",
                error_fixes=["Reduce window_size.", "Provide more data."],
            )

        use_torch = preset_cfg["use_torch"] and _has_torch()
        backend = "pytorch_autoencoder" if use_torch else "pca_reconstruction"

        if not use_torch and preset_cfg["use_torch"]:
            warn_list.append(
                "PyTorch not available. Falling back to PCA reconstruction error. "
                "Install PyTorch for full autoencoder support."
            )

        if use_torch:
            progress_callback(f"Training autoencoder ({epochs} epochs)", 25)
            model, recon_errors, losses = _train_torch_autoencoder(
                windows, hidden_dim, epochs, lr, ctx.seed,
            )
            final_loss = losses[-1] if losses else float("inf")
            model_desc = f"Autoencoder (PyTorch, hidden_dim={hidden_dim})"
            extra_info = {"final_loss": round(final_loss, 6)}
        else:
            progress_callback("Computing PCA reconstruction errors", 25)
            n_pca = preset_cfg["n_pca_components"]
            pca_model, recon_errors, explained_var = _train_pca_anomaly(
                windows, n_pca,
            )
            losses = []
            model_desc = f"PCA reconstruction (n_components={min(n_pca, window_size)})"
            extra_info = {"explained_variance": round(explained_var, 4)}

        progress_callback("Detecting anomalies", 60)

        # Map window-level errors back to point-level errors
        # Each point participates in multiple windows; take the max error
        point_errors = np.zeros(n)
        point_counts = np.zeros(n)
        for i, err in enumerate(recon_errors):
            for j in range(window_size):
                idx = i + j
                if idx < n:
                    point_errors[idx] = max(point_errors[idx], err)
                    point_counts[idx] += 1

        # Determine threshold based on contamination
        threshold = float(np.percentile(point_errors, 100 * (1 - contamination)))
        is_anomaly = point_errors > threshold
        anomaly_indices = np.where(is_anomaly)[0]
        n_anomalies = len(anomaly_indices)

        progress_callback("Building output", 85)

        time_col = ctx.time if ctx.time and len(ctx.time) == n else list(range(1, n + 1))

        # Anomalies table
        anomaly_rows = []
        for idx in anomaly_indices:
            anomaly_rows.append([
                int(idx + 1),
                round(float(clean[idx]), 6),
                round(float(point_errors[idx]), 6),
                "Yes",
            ])
        anomaly_table = make_table(
            "Anomalies",
            ["Index", "Value", "ReconstructionError", "IsAnomaly"],
            anomaly_rows,
        )

        # Full series table (sampled for large series)
        max_display = min(n, 300)
        step = max(1, n // max_display)
        series_rows = []
        for i in range(0, n, step):
            series_rows.append([
                int(i + 1),
                round(float(clean[i]), 6),
                round(float(point_errors[i]), 6),
                "Yes" if is_anomaly[i] else "No",
            ])
        series_table = make_table(
            "Reconstruction Errors",
            ["Index", "Value", "ReconstructionError", "IsAnomaly"],
            series_rows,
        )

        # Model summary
        summary_rows = [
            ["Model", model_desc],
            ["Backend", backend],
            ["Observations", n],
            ["Window Size", window_size],
            ["Hidden Dimension", hidden_dim],
            ["Contamination", contamination],
            ["Threshold", round(threshold, 6)],
            ["Anomalies Detected", n_anomalies],
            ["Anomaly Rate", f"{100 * n_anomalies / n:.2f}%"],
            ["Mean Reconstruction Error", round(float(np.mean(point_errors)), 6)],
            ["Max Reconstruction Error", round(float(np.max(point_errors)), 6)],
        ]

        if use_torch:
            summary_rows.append(["Epochs", epochs])
            summary_rows.append(["Final Training Loss", round(extra_info["final_loss"], 6)])
        else:
            summary_rows.append(["PCA Explained Variance", round(extra_info["explained_variance"], 4)])

        summary_table = make_table("Model Summary", ["Metric", "Value"], summary_rows)

        tables = [anomaly_table, summary_table, series_table]

        # Training loss trajectory (if torch)
        if use_torch and len(losses) > 0:
            step_size = max(1, len(losses) // 20)
            loss_rows = []
            for i in range(0, len(losses), step_size):
                loss_rows.append([i + 1, round(losses[i], 6)])
            if (len(losses) - 1) % step_size != 0:
                loss_rows.append([len(losses), round(losses[-1], 6)])
            tables.append(make_table("Training Loss", ["Epoch", "Loss"], loss_rows))

        if n_anomalies == 0:
            warn_list.append(
                "No anomalies detected. Consider increasing contamination or adjusting window_size."
            )

        if n_anomalies > 0:
            most_extreme_idx = anomaly_indices[np.argmax(point_errors[anomaly_indices])]
            plain_english = (
                f"Autoencoder anomaly detection on '{name}' ({n} observations) using {backend}. "
                f"Window size={window_size}, hidden_dim={hidden_dim}. "
                f"Detected {n_anomalies} anomalies ({100 * n_anomalies / n:.1f}% of data). "
                f"Most extreme anomaly at index {most_extreme_idx + 1} "
                f"(value={clean[most_extreme_idx]:.4f}, error={point_errors[most_extreme_idx]:.4f})."
            )
        else:
            plain_english = (
                f"Autoencoder anomaly detection on '{name}' ({n} observations) using {backend}. "
                f"Window size={window_size}, hidden_dim={hidden_dim}. "
                f"No anomalies detected at contamination={contamination}."
            )

        charting = (
            "Two-panel chart: (1) Original series with anomaly points highlighted in red, "
            "(2) Reconstruction error over time with threshold line. "
            "If PyTorch used, add a training loss curve panel."
        )

        progress_callback("Done", 100)

        audit = {
            "backend": backend,
            "window_size": window_size,
            "hidden_dim": hidden_dim,
            "contamination": contamination,
            "threshold": round(threshold, 6),
            "n_anomalies": n_anomalies,
            "anomaly_rate": round(n_anomalies / n, 6),
            "mean_recon_error": round(float(np.mean(point_errors)), 6),
            "max_recon_error": round(float(np.max(point_errors)), 6),
            "anomaly_indices": [int(i) for i in anomaly_indices],
        }
        audit.update(extra_info)

        return make_response(
            ctx,
            tables=tables,
            plain_english_summary=plain_english,
            warnings=warn_list,
            charting_suggestions=charting,
            audit_fields=audit,
        )

    except ValueError as e:
        return make_error_response(ctx, str(e))
    except Exception as e:
        return make_error_response(
            ctx,
            f"Autoencoder anomaly detection failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try a smaller window_size.",
                "Install PyTorch for full autoencoder support, or use PCA fallback.",
                "Adjust contamination parameter.",
            ],
        )
