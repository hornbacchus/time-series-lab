# Autoencoder Anomaly Detection

## What It Does

Autoencoder Anomaly Detection uses a neural network autoencoder to learn a compressed representation of normal time series patterns and then identifies anomalies based on reconstruction error. The autoencoder is trained to compress sliding windows of the series through a bottleneck layer and reconstruct them. Normal patterns are reconstructed accurately (low error), while anomalous patterns produce high reconstruction error because the model has not learned to represent them.

## When to Use It

- You want to detect anomalies without labeled examples (unsupervised)
- The series contains complex, multivariate patterns where simple threshold methods fail
- You need a flexible anomaly detector that learns "normal" from the data itself
- Point anomalies, contextual anomalies, or collective anomalies may be present
- You want anomaly scores (reconstruction error) rather than just binary labels
- The normal patterns in the series are relatively stable and well-represented in the training data

## Key Assumptions

- The training data is predominantly normal (anomalies are rare)
- Normal patterns can be efficiently encoded in a low-dimensional representation
- The bottleneck dimension is small enough to prevent the autoencoder from learning the identity function
- Anomalous patterns differ structurally from normal patterns (not just in magnitude)
- The sliding window size captures the relevant temporal context for detecting anomalies

## Outputs

- **Anomaly flags**: binary indicators for each time point exceeding the threshold
- **Reconstruction error**: per-point error scores (higher = more anomalous)
- **Anomaly threshold**: the computed threshold (mean + k*sigma of reconstruction error)
- **Model summary**: architecture, encoding dimension, training loss, number of anomalies detected

## Technical Details

**Architecture**: The autoencoder consists of an encoder and decoder, both using fully connected layers with ReLU activations. The encoder maps the input window `x in R^W` to a latent representation `z in R^d` where `d << W`. The decoder maps `z` back to `x_hat in R^W`. The bottleneck forces the network to learn a compressed representation of the input.

**Encoder**: `z = f_enc(x) = ReLU(W_2 * ReLU(W_1 * x + b_1) + b_2)` with progressive dimension reduction (e.g., W -> W/2 -> d).

**Decoder**: `x_hat = f_dec(z) = sigmoid(W_4 * ReLU(W_3 * z + b_3) + b_4)` with progressive dimension expansion (d -> W/2 -> W).

**Training loss**: MSE reconstruction loss: `L = (1/N) * sum_i ||x_i - x_hat_i||^2`. Only normal data (or all data, assuming anomalies are rare) is used for training.

**Sliding window**: The series is segmented into overlapping windows of size `W` with stride 1. Each window is treated as an independent input sample. The reconstruction error for each time point is averaged across all windows containing that point.

**Anomaly threshold**: Computed as `threshold = mean(errors) + k * std(errors)` where `k` is the `threshold_sigma` parameter (default 3.0). Points with reconstruction error above this threshold are flagged as anomalies.

**PCA fallback**: When PyTorch is not available, the implementation uses PCA-based reconstruction. PCA projects windows onto the top `d` principal components and reconstructs from this subspace. The reconstruction error serves the same anomaly detection purpose, though with a linear model instead of nonlinear.

**Comparison**: Autoencoders can capture complex nonlinear patterns that statistical methods (Z-score, IQR) miss. They are especially effective for multivariate time series where anomalies manifest as unusual combinations of variables. For univariate series with simple patterns, the STL-ESD method may be simpler and equally effective.


## Interpretation

Every Autoencoder Anomaly run emits a two-tier Interpretation block. Inherits the **C1 `stl_esd_anomaly` Tier 1 shape** (count + rate + threshold + most-extreme) with modifications.

**Tier 1** - cites detected anomaly count and rate, most-extreme anomaly index and reconstruction error, window size and latent dimension. PyTorch preferred; sklearn PCA reconstruction fallback.

**Tier 2** - discloses autoencoder reconstruction structure (window -> latent -> reconstruction; anomaly score = squared reconstruction error). **D10 threshold disclosure**: threshold is percentile-of-training-error controlled by the `contamination` parameter - NOT a hypothesis-test alpha (unlike stl_esd_anomaly). **Key divergence from stl_esd_anomaly**: reconstruction error is unsigned - no upward/downward direction split. Per-feature error attribution not exposed (backlog).

**Caveats (Tier 3, conditional)**:
- Backend fallback (PyTorch -> PCA linear reconstruction).
- **D18 always-fires**: detected anomaly rate equals contamination parameter by construction - the count does not provide evidence about true anomaly fraction.
