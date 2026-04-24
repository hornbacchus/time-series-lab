# Transformer Forecast

## What It Does

The Transformer architecture uses **self-attention mechanisms** to capture dependencies between all positions in a time series simultaneously, without the sequential processing limitation of recurrent networks. Each time step can directly attend to any other time step, allowing the model to learn which parts of the history are most relevant for forecasting. Adapted from NLP, Transformers have become a leading architecture for time series with innovations like sparse attention, decomposition-aware design, and patching.

## When to Use It

- You have long sequences where distant past values may influence future values
- You want the model to learn which historical time steps are most relevant (through attention weights)
- Multivariate inputs are available and interactions between variables matter
- You have substantial training data (thousands of observations or many related series)
- You want to leverage the latest deep learning research in time series forecasting

## Key Assumptions

- Sufficient training data is available for the attention mechanism to learn meaningful patterns
- The relevant historical information can be identified through attention (not all past information contributes equally)
- Positional encoding adequately communicates temporal ordering to the model
- The sequence length is manageable for the attention computation (or efficient attention variants are used)
- The model architecture and training procedure are properly tuned for time series (not naively applied from NLP)

## Outputs

- **Point forecasts** for the specified horizon
- **Attention weight matrices**: showing which past time steps the model focuses on for each prediction
- **Training and validation loss curves**
- **Prediction intervals**: via quantile heads, MC dropout, or ensembling
- **Multi-step forecasts**: generated in a single forward pass (non-autoregressive) or step by step (autoregressive)

## Technical Details

**Self-attention mechanism**: For a sequence of input vectors `X = (x_1, ..., x_T)`, self-attention computes:

`Attention(Q, K, V) = softmax(Q K' / sqrt(d_k)) V`

where `Q = X W_Q` (queries), `K = X W_K` (keys), `V = X W_V` (values), and `d_k` is the key dimension. The softmax over `Q K' / sqrt(d_k)` produces attention weights: how much each position attends to every other position.

**Multi-head attention**: Run h parallel attention operations with different learned projections, then concatenate:

`MultiHead(X) = Concat(head_1, ..., head_h) W_O`

where `head_i = Attention(X W_Q^i, X W_K^i, X W_V^i)`. Multiple heads allow the model to attend to different patterns simultaneously.

**Transformer encoder block**: Each block consists of:
1. Multi-head self-attention with residual connection and layer normalization
2. Position-wise feedforward network (two linear layers with ReLU) with residual connection and layer normalization

**Positional encoding**: Since self-attention is permutation-invariant, positional information must be added. Standard sinusoidal encoding:

`PE(pos, 2i) = sin(pos / 10000^{2i/d_model})`
`PE(pos, 2i+1) = cos(pos / 10000^{2i/d_model})`

Added to the input embeddings so the model knows the temporal position of each time step.

**Causal masking**: For autoregressive forecasting, a causal mask prevents position t from attending to positions t+1, t+2, etc. This is implemented by setting future positions to -infinity before the softmax.

**Time series-specific innovations**:

- **Informer** (2021): Uses ProbSparse attention that selects the top-K most important queries, reducing complexity from O(T^2) to O(T log T). Includes a distilling operation that progressively halves the sequence length.

- **Autoformer** (2021): Replaces standard attention with auto-correlation-based attention that operates in the frequency domain. Includes a decomposition architecture that separates trend and seasonal components within the network.

- **PatchTST** (2023): Divides the time series into patches (subsequences) and treats each patch as a token. This reduces the effective sequence length, improves computational efficiency, and captures local patterns within patches while using attention across patches for global patterns.

- **iTransformer** (2024): Inverts the standard approach by treating each variable (not each time step) as a token. Self-attention operates across variables at each time point, naturally capturing multivariate correlations.

**Training considerations**:
- Input normalization (reversible instance normalization) prevents distribution shift from degrading performance.
- Direct multi-step output (predicting all h future values at once) is preferred over autoregressive decoding.
- Learning rate warmup followed by cosine decay is common.
- For univariate series, channel-independent processing (treating each variable separately) often outperforms multivariate attention.

**Computational complexity**: Standard self-attention is O(T^2 * d) in time and O(T^2) in memory. For long sequences, efficient attention variants (Informer, Performer, FlashAttention) reduce this to O(T log T) or O(T).

## Prediction Intervals — important caveat

Machine-learning forecasters do **not** come with native prediction-
interval machinery the way classical models (ARIMA, ETS, state-space)
do. When this technique returns a prediction interval, it is derived
empirically from in-sample residuals using a normal or t approximation —
NOT from a probabilistic forecast distribution.

Consequences:

- The interval width does **not** reflect model uncertainty
  (epistemic uncertainty about the learned parameters) — only
  aleatoric noise captured by the residual distribution.
- Coverage is not guaranteed. On out-of-sample data with regime
  shifts or distribution drift, empirical intervals typically
  under-cover.
- The interval is **symmetric** around the point forecast, which
  mis-represents asymmetric error distributions that ML models
  often produce.

For calibrated intervals on an ML forecast, wrap this technique with
**Conformal Prediction Intervals** — it takes a point-forecast model
and produces distribution-free intervals via a held-out calibration
set. See also **Quantile Regression Forecast** for directly
modeling conditional quantiles.

## Attention Weights Exposure (Follow-up 3f, opt-in)

Self-attention is the defining interpretability axis of Transformer models: each prediction is a weighted average over past time steps, and the weights themselves answer the practitioner question "which past positions drove this forecast?" Prior to Follow-up 3f the wrapper's Tier 2 explicitly acknowledged attention-weight extraction as *"backlog for future enhancement"* and the C7 catalog declared `attention_weights` in `output_tables` as an aspirational placeholder — 3f fulfills both commitments.

Set `attention_exposure=True` (default `False`, backward compat) to capture per-layer attention matrices during the t+1 forecast forward pass and expose two complementary views:

- **Last-layer view** — per-head attention from the final encoder layer, head-averaged to produce a single `(n_lags × n_lags)` matrix. The final layer is most directly responsible for the prediction.
- **Cross-layer mean view** — averaged across all encoder layers and heads for the aggregate attention pattern.

For each view the wrapper extracts the **forecast-position row** (the last row of the matrix — what past positions the model attends to when predicting t+1) and reports:

- **Top-K ranked list** (default K=10, user-configurable via `attention_top_k`, silently clipped to `n_lags` if larger). Each entry records rank, position index, lag from forecast position, and attention weight.
- **Normalized Shannon entropy** `H / log(n_lags) ∈ [0, 1]`. Low (< 0.3) ⇒ concentrated attention on few lags; high (> 0.8) ⇒ diffuse, near-uniform attention.
- **Effective context length** `Σ lag_i · w_i`. Small ⇒ model focuses on recent past; large ⇒ model uses deep history.
- **Dominant lag** — argmax of the attention row.

The output is surfaced in the "Attention Weights" table and in Tier 2 methodology prose.

### Capture mechanism

PyTorch's `nn.TransformerEncoderLayer._sa_block` hardcodes `need_weights=False`, so a naïve forward hook on `self_attn` would see `(output, None)`. Additionally, `TransformerEncoderLayer.forward` has a "sparsity fast path" that dispatches to a fused kernel, bypassing `_sa_block` entirely when no hooks are registered. Follow-up 3f uses the standard PyTorch interpretability pattern:

1. Register a no-op `forward_hook` on each encoder layer to disable the fast path.
2. Patch `layer._sa_block` with a version that forces `need_weights=True, average_attn_weights=True` and stashes the returned (head-averaged) weights tensor.
3. Wrap the capture forward pass in `try / except / finally` with **guaranteed teardown** — every patched `_sa_block` is restored and every hook is removed regardless of downstream outcome.

### Graceful degradation

- **sklearn fallback.** If PyTorch is unavailable and the wrapper falls back to `MLPRegressor`, attention weights are not defined for the MLP architecture. `attention_exposure_applied=False`, `fallback_reason="sklearn_fallback_no_attention"`, Tier 3 D5 fires with the sklearn-fallback branch message.
- **Runtime error.** If the capture cascade raises for any reason, `try/finally` restores all patched `_sa_block` methods and removes all hooks, `fallback_reason="runtime_error: ..."`, D5 fires with the runtime-error branch. Baseline forecast is always preserved.

### Tier 3 triggers (fire only when `attention_exposure=True` and capture succeeded, except D5)

- **D1 attention_highly_concentrated** — last-layer normalized entropy < 0.3. Very few past positions drive the prediction; may indicate lag-1 dominance (AR structure), spurious reliance, or insufficient capacity.
- **D2 attention_highly_diffuse** — last-layer normalized entropy > 0.8. Near-uniform attention; may indicate undertrained model or a series with no strong lag structure.
- **D3 dominant_lag_matches_seasonal** — informational heuristic. Fires when dominant lag ∈ {4, 7, 12, 24, 52, 365} (quarterly, weekly, monthly, daily-hourly, annual-weekly, annual-daily). The model may have learned seasonal structure at this lag.
- **D4 last_layer_cross_layer_disagreement** — strict exact-position top-1 mismatch between the two views. Research-relevant signal that the final layer uses different information than earlier layers on average.
- **D5 attention_exposure_runtime_error** — fires on graceful fallback (both sklearn-fallback and runtime-error branches).

## Interpretation

Every Transformer run emits a two-tier Interpretation block with neural-sequence-cohort shared helpers.

**Tier 1** - names d_model, attention heads, encoder layers, feed-forward dim, total parameter count.

**Tier 2** - explains self-attention structure (query/key/value projections). When `attention_exposure=True`, adds a methodology block describing the `_sa_block` patch, two-view reporting, and summary statistics; when NOT opted in, includes a pointer to the opt-in parameter.

**Caveats (Tier 3, conditional)**: shared neural-sequence triggers (backend fallback, insufficient training, non-convergence, over-parameterization) plus 5 new Follow-up 3f triggers (D1-D5) covering attention concentration, diffusion, seasonal-match, layer disagreement, and graceful-fallback cases.
