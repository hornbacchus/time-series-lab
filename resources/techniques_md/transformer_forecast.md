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
