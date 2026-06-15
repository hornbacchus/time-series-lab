"""
Transformer Forecast for Time Series Lab.

Uses PyTorch to implement a Transformer encoder for time series forecasting.
Falls back to sklearn MLPRegressor with lag features when PyTorch is not installed.
Full training only under Thorough preset.

Follow-up 3f: opt-in ``attention_exposure=True`` captures per-layer
attention weights during the t+1 forecast forward pass and exposes
two views (last-layer and cross-layer mean) with top-K ranked
forecast-position attention plus summary statistics (normalized
Shannon entropy, effective context length, dominant lag).

Capture mechanism — per-layer ``_sa_block`` patch. PyTorch's
``nn.TransformerEncoderLayer._sa_block`` hardcodes
``need_weights=False`` internally, so a forward hook on
``self_attn`` sees ``(output, None)``. The standard fix is to
patch ``layer._sa_block`` at capture time with a version that
forces ``need_weights=True, average_attn_weights=True``, stashes
the returned weights tensor, and is torn down via try/finally
(D15). Patching also disables PyTorch's fused fast-path,
guaranteeing the slow path is taken and hooks fire.

PyTorch-only. Graceful fallback on the sklearn MLP path:
``attention_exposure_applied=False`` with
``fallback_reason="sklearn_fallback_no_attention"``.
"""

import numpy as np

from techniques.base import (
    RunContext,
    make_table,
    make_response,
    make_error_response,
)


# Follow-up 3f: seasonal lags recognized by D3
# ``dominant_lag_matches_seasonal``. Static set; wrapper does not
# read ``ctx.frequency``. Informational only — D3 is not a warning.
_SEASONAL_LAGS = (4, 7, 12, 24, 52, 365)


def _has_torch():
    try:
        import torch
        return True
    except ImportError:
        return False


def _patch_sa_blocks_for_capture(encoder, captured):
    """Patch each TransformerEncoderLayer's ``_sa_block`` to force
    ``need_weights=True, average_attn_weights=True`` and stash the
    returned (head-averaged) attention weights into ``captured``.

    Follow-up 3f helper. D15: must be called inside a try/finally
    with guaranteed teardown via ``_restore_sa_blocks``.

    Important implementation note: PyTorch's
    ``nn.TransformerEncoderLayer.forward`` has a *sparsity fast
    path* that dispatches to a fused CUDA/CPU kernel
    (``torch._transformer_encoder_layer_fwd``) bypassing
    ``_sa_block`` entirely when the model is in eval mode with no
    masks and no hooks. Patching ``_sa_block`` alone is therefore
    insufficient — we ALSO register a no-op forward hook on each
    layer to disable the fast path.

    Parameters
    ----------
    encoder : torch.nn.TransformerEncoder
        Holds the list of ``TransformerEncoderLayer`` instances as
        ``encoder.layers``.
    captured : list
        Mutable list that will be appended with ``(layer_idx,
        weights_tensor)`` tuples per forward pass per layer.

    Returns
    -------
    list of (layer, original_sa_block, hook_handle)
        For teardown via ``_restore_sa_blocks``.
    """
    originals = []

    def _noop_hook(_module, _inputs, output):
        # No-op hook: its mere presence disables the
        # sparsity fast path in TransformerEncoderLayer.forward.
        return None

    for layer_idx, layer in enumerate(encoder.layers):
        orig_sa = layer._sa_block

        def _make_patched(_layer, _idx):
            def _patched_sa(
                x,
                attn_mask,
                key_padding_mask,
                is_causal=False,
            ):
                out, weights = _layer.self_attn(
                    x, x, x,
                    attn_mask=attn_mask,
                    key_padding_mask=key_padding_mask,
                    need_weights=True,
                    average_attn_weights=True,
                    is_causal=is_causal,
                )
                captured.append(
                    (_idx, weights.detach().clone())
                )
                return _layer.dropout1(out)
            return _patched_sa

        layer._sa_block = _make_patched(layer, layer_idx)
        hook_handle = layer.register_forward_hook(_noop_hook)
        originals.append((layer, orig_sa, hook_handle))
    return originals


def _restore_sa_blocks(originals):
    """Restore original ``_sa_block`` methods + remove fast-path-
    disabling forward hooks (D15 teardown)."""
    for entry in originals:
        # Tuple is (layer, orig_sa, hook_handle). Tolerate 2-tuple
        # form defensively for forward compatibility.
        try:
            if len(entry) == 3:
                layer, orig_sa, hook_handle = entry
            else:
                layer, orig_sa = entry[0], entry[1]
                hook_handle = None
            try:
                layer._sa_block = orig_sa
            except Exception:
                pass
            if hook_handle is not None:
                try:
                    hook_handle.remove()
                except Exception:
                    pass
        except Exception:
            # Defensive: if teardown of one layer fails, continue
            # restoring the others rather than short-circuit.
            pass


def _compute_attention_summaries(forecast_row, context_length):
    """Compute (H_norm, effective_context_length, dominant_lag).

    Parameters
    ----------
    forecast_row : array-like
        Length-``context_length`` attention vector (weights over
        past positions when predicting t+1).
    context_length : int
        Sequence length L. Last row's position index is L-1;
        position i has lag ``(L-1) - i`` from the forecast position.

    Returns
    -------
    (entropy_norm, eff_context_length, dominant_lag)
        All floats except dominant_lag which is int. Any component
        may be None on degenerate input.
    """
    try:
        a = np.asarray(forecast_row, dtype=np.float64)
    except Exception:
        return None, None, None
    if a.size == 0:
        return None, None, None
    total = float(a.sum())
    if total <= 0:
        return None, None, None
    a = a / total
    eps = 1e-12
    a_safe = np.clip(a, eps, 1.0)
    H = -float(np.sum(a_safe * np.log(a_safe)))
    denom = float(np.log(max(int(context_length), 2)))
    H_norm = (H / denom) if denom > 0 else None
    positions = np.arange(int(context_length))
    lags = (int(context_length) - 1) - positions
    eff_cl = float(np.sum(lags * a))
    dom_lag = int(lags[int(np.argmax(a))])
    return (
        float(H_norm) if H_norm is not None else None,
        eff_cl,
        dom_lag,
    )


def _build_attention_top_k(forecast_row, K_effective):
    """Build a top-K ranked list of dicts sorted by attention weight.

    Each entry: ``{"rank": int, "position": int, "lag": int, "weight": float}``.
    ``lag`` is the distance back from the forecast position.
    """
    a = np.asarray(forecast_row, dtype=np.float64)
    L = len(a)
    K = int(max(1, min(int(K_effective), L)))
    idx_desc = np.argsort(-a)[:K]
    out = []
    for rank, pos in enumerate(idx_desc, start=1):
        lag = int((L - 1) - int(pos))
        out.append({
            "rank": int(rank),
            "position": int(pos),
            "lag": lag,
            "weight": round(float(a[int(pos)]), 6),
        })
    return out


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
        # CAI Phase 2 Session 24 fix (F-NN-TF-HORIZON): explicit
        # range gate.
        if horizon < 1:
            return make_error_response(
                ctx,
                f"horizon must be >= 1. Got {horizon}.",
                error_fixes=["Use a positive integer for forecast horizon."],
            )

        preset_cfg = _PRESET_CONFIG.get(ctx.preset, _PRESET_CONFIG["Balanced"])
        # Fix B Tier 1b: blank/absent -> preset cfg (byte-identical); literal
        # get_param keeps the key visible to catalog_key_alignment.
        _dm = ctx.get_param("d_model", preset_cfg["d_model"])
        d_model = preset_cfg["d_model"] if (_dm is None or str(_dm).strip() == "") else int(_dm)
        _nh = ctx.get_param("n_heads", preset_cfg["n_heads"])
        n_heads = preset_cfg["n_heads"] if (_nh is None or str(_nh).strip() == "") else int(_nh)
        _nel = ctx.get_param("n_encoder_layers", preset_cfg["n_encoder_layers"])
        n_encoder_layers = preset_cfg["n_encoder_layers"] if (_nel is None or str(_nel).strip() == "") else int(_nel)
        _dff = ctx.get_param("dim_feedforward", preset_cfg["dim_feedforward"])
        dim_feedforward = preset_cfg["dim_feedforward"] if (_dff is None or str(_dff).strip() == "") else int(_dff)
        _ep = ctx.get_param("epochs", preset_cfg["epochs"])
        epochs = preset_cfg["epochs"] if (_ep is None or str(_ep).strip() == "") else int(_ep)
        _nlg = ctx.get_param("n_lags", preset_cfg["n_lags"])
        n_lags = preset_cfg["n_lags"] if (_nlg is None or str(_nlg).strip() == "") else int(_nlg)
        _lrp = ctx.get_param("learning_rate", preset_cfg["lr"])
        lr = preset_cfg["lr"] if (_lrp is None or str(_lrp).strip() == "") else float(_lrp)
        _dp = ctx.get_param("dropout", preset_cfg["dropout"])
        dropout = preset_cfg["dropout"] if (_dp is None or str(_dp).strip() == "") else float(_dp)

        from techniques._validation import ParamError, require
        try:
            require(n_lags >= 1, f"n_lags ({n_lags}) must be >= 1.",
                    fixes=["Use n_lags >= 1, or leave blank for the preset default."])
            require(1 <= epochs <= 1000, f"epochs ({epochs}) must be between 1 and 1000.",
                    fixes=["Use 1..1000 epochs, or leave blank."])
            require(lr > 0, f"learning_rate ({lr}) must be > 0.",
                    fixes=["Use a positive learning rate, or leave blank."])
            require(0 <= dropout < 1, f"dropout ({dropout}) must be in [0, 1).",
                    fixes=["Use a dropout fraction between 0 and 1 (e.g. 0.1)."])
        except ParamError as e:
            return make_error_response(ctx, str(e), error_fixes=e.fixes)

        # CAI Phase 2 Session 24 fix (F-NN-TF-DMODEL): explicit
        # multi-parameter consistency gate. Pre-fix, d_model not
        # divisible by n_heads was silently adjusted (loud-and-
        # coerced with warning). Now reject so the user can fix
        # the spec rather than train a different model than asked.
        if d_model % n_heads != 0:
            return make_error_response(
                ctx,
                f"d_model ({d_model}) must be divisible by n_heads "
                f"({n_heads}). PyTorch nn.MultiheadAttention requires "
                "this for tensor reshaping.",
                error_fixes=[
                    f"Choose d_model as a multiple of n_heads "
                    f"(e.g., d_model={n_heads * (d_model // n_heads + 1)} "
                    f"or n_heads={max(1, d_model // (d_model // n_heads or 1))}).",
                ],
            )

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

            # ── Follow-up 3f — attention weight exposure (opt-in) ──
            # Only attempted on the PyTorch path. sklearn fallback
            # handled separately in the else branch below (Q9).
            _attn_request_pt = bool(
                ctx.get_param("attention_exposure", False)
            )
            if _attn_request_pt:
                progress_callback(
                    "Capturing attention weights (t+1)", 85
                )
                _captured_pt = []
                _originals_pt = []
                try:
                    _originals_pt = _patch_sa_blocks_for_capture(
                        model.encoder, _captured_pt,
                    )
                    # Q3/D16: single t+1 forward pass over the last
                    # n_lags context. Do not re-run the recursive
                    # horizon loop — we captured weights that drive
                    # the first forecast step, which is the
                    # practitioner-relevant question.
                    with torch.no_grad():
                        _x0 = torch.FloatTensor(
                            normalized[-n_lags:]
                        ).unsqueeze(0).unsqueeze(-1)
                        _ = model(_x0)
                    if len(_captured_pt) != n_encoder_layers:
                        raise ValueError(
                            f"Captured {len(_captured_pt)} attention "
                            f"tensors from encoder but expected "
                            f"{n_encoder_layers} (one per layer); "
                            f"single-pass capture invariant violated"
                        )
                    _attn_capture_ok = True
                    _attn_capture_err = None
                except Exception as _attn_err:
                    _attn_capture_ok = False
                    _attn_capture_err = _attn_err
                finally:
                    # D15: guaranteed teardown — restore original
                    # _sa_block for every layer, even on exception.
                    _restore_sa_blocks(_originals_pt)
            else:
                _attn_capture_ok = False
                _attn_capture_err = None
                _captured_pt = None
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
            losses = list(getattr(model, "loss_curve_", []))

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

            # Follow-up 3f — Q9 sklearn fallback branch. Attention
            # capture is structurally impossible on the MLP path.
            _attn_request_pt = bool(
                ctx.get_param("attention_exposure", False)
            )
            _attn_capture_ok = False
            _attn_capture_err = None
            _captured_pt = None

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

        # ── Follow-up 3f — attention post-processing ──────────────
        # Consolidates the PyTorch capture result (_captured_pt,
        # _attn_capture_ok, _attn_capture_err) and the sklearn
        # fallback into a unified set of audit fields plus an
        # optional "Attention Weights" output table.
        attn_request = bool(_attn_request_pt)
        attn_applied = False
        attn_fallback_reason = None
        attn_top_k_req = int(ctx.get_param("attention_top_k", 10))
        attn_audit = {}
        attn_table = None

        if attn_request:
            if backend == "sklearn_mlp":
                attn_fallback_reason = "sklearn_fallback_no_attention"
                warn_list.append(
                    "Attention exposure requested but backend is "
                    "sklearn MLPRegressor; attention weights are "
                    "undefined for the fallback architecture. "
                    "Install PyTorch to enable."
                )
            elif not _attn_capture_ok:
                err = _attn_capture_err
                attn_fallback_reason = (
                    f"runtime_error: "
                    f"{type(err).__name__ if err is not None else 'Exception'}: "
                    f"{err}"
                )
                warn_list.append(
                    f"Attention exposure raised "
                    f"{type(err).__name__ if err is not None else 'Exception'}: "
                    f"{err}. Baseline forecast preserved."
                )
            else:
                # Successful capture — process into two views.
                try:
                    # Stack captured tensors by layer index.
                    _layer_mats = [
                        w.squeeze(0).cpu().numpy()
                        for _, w in sorted(
                            _captured_pt, key=lambda t: t[0]
                        )
                    ]
                    _last_mat = _layer_mats[-1]
                    _cross_mat = np.mean(
                        np.stack(_layer_mats, axis=0), axis=0,
                    )
                    _last_row = _last_mat[-1]
                    _cross_row = _cross_mat[-1]

                    # Q5: silent clip to min(K, n_lags).
                    K_eff = int(max(1, min(attn_top_k_req, n_lags)))

                    _ll_topk = _build_attention_top_k(_last_row, K_eff)
                    _cl_topk = _build_attention_top_k(_cross_row, K_eff)
                    _ll_H, _ll_ecl, _ll_dom = (
                        _compute_attention_summaries(_last_row, n_lags)
                    )
                    _cl_H, _cl_ecl, _cl_dom = (
                        _compute_attention_summaries(_cross_row, n_lags)
                    )

                    attn_audit = {
                        "attention_n_layers": int(n_encoder_layers),
                        "attention_n_heads": int(n_heads),
                        "attention_context_length": int(n_lags),
                        "attention_top_k": int(attn_top_k_req),
                        "attention_top_k_effective": int(K_eff),
                        "attention_last_layer_top_k": _ll_topk,
                        "attention_cross_layer_top_k": _cl_topk,
                        "attention_last_layer_entropy_normalized": (
                            round(_ll_H, 6) if _ll_H is not None else None
                        ),
                        "attention_last_layer_effective_context_length": (
                            round(_ll_ecl, 6)
                            if _ll_ecl is not None else None
                        ),
                        "attention_last_layer_dominant_lag": _ll_dom,
                        "attention_cross_layer_entropy_normalized": (
                            round(_cl_H, 6) if _cl_H is not None else None
                        ),
                        "attention_cross_layer_effective_context_length": (
                            round(_cl_ecl, 6)
                            if _cl_ecl is not None else None
                        ),
                        "attention_cross_layer_dominant_lag": _cl_dom,
                    }

                    # Build "Attention Weights" output table
                    # (fulfills C7 catalog placeholder).
                    _rows = []
                    for r in range(K_eff):
                        _ll = _ll_topk[r]
                        _cl = _cl_topk[r]
                        _rows.append([
                            r + 1,
                            _ll["position"], _ll["lag"], _ll["weight"],
                            _cl["position"], _cl["lag"], _cl["weight"],
                        ])
                    attn_table = make_table(
                        "Attention Weights",
                        [
                            "Rank",
                            "Last-Layer Position", "Last-Layer Lag",
                            "Last-Layer Weight",
                            "Cross-Layer Position", "Cross-Layer Lag",
                            "Cross-Layer Weight",
                        ],
                        _rows,
                    )
                    attn_applied = True
                except Exception as _post_err:
                    attn_fallback_reason = (
                        f"runtime_error: "
                        f"{type(_post_err).__name__}: {_post_err}"
                    )
                    warn_list.append(
                        f"Attention post-processing raised "
                        f"{type(_post_err).__name__}: {_post_err}. "
                        f"Baseline forecast preserved."
                    )

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
        # Follow-up 3f: insert Attention Weights table before
        # Training Loss so it reads naturally after Model Summary.
        if attn_table is not None:
            tables.append(attn_table)

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
            "d_model": d_model,
            "n_heads": n_heads,
            "n_encoder_layers": n_encoder_layers,
            "dim_feedforward": dim_feedforward,
            "n_lags": n_lags,
            "epochs": epochs,
            "n_params": n_params if use_torch or backend == "sklearn_mlp" else None,
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
            # Follow-up 3f — attention exposure audit fields
            "attention_exposure_requested": bool(attn_request),
            "attention_exposure_applied": bool(attn_applied),
            "attention_exposure_fallback_reason": attn_fallback_reason,
        }
        # Populate per-view attention audit fields (all None if not
        # applied; present as None-safe defaults regardless).
        for _k in (
            "attention_n_layers",
            "attention_n_heads",
            "attention_context_length",
            "attention_top_k",
            "attention_top_k_effective",
            "attention_last_layer_top_k",
            "attention_cross_layer_top_k",
            "attention_last_layer_entropy_normalized",
            "attention_last_layer_effective_context_length",
            "attention_last_layer_dominant_lag",
            "attention_cross_layer_entropy_normalized",
            "attention_cross_layer_effective_context_length",
            "attention_cross_layer_dominant_lag",
        ):
            audit[_k] = attn_audit.get(_k)

        try:
            from interpretation import build_interpretation  # type: ignore
        except Exception:
            def build_interpretation(technique_id, results):  # type: ignore
                return None
        interp = build_interpretation("transformer_forecast", dict(audit))

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
            f"Transformer forecast failed: {e}",
            error_fixes=[
                "Ensure your data is numeric with sufficient observations (>=20).",
                "Try fewer epochs, smaller d_model, or fewer layers.",
                "Install PyTorch for full Transformer support.",
                "Ensure d_model is divisible by n_heads.",
            ],
        )
