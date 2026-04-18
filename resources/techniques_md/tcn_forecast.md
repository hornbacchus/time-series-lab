# TCN (Temporal Convolutional Network) Forecast

## What It Does

A Temporal Convolutional Network (TCN) applies **causal dilated convolutions** to a time series, building a deep network that can capture long-range temporal dependencies without the sequential processing bottleneck of recurrent networks. By stacking convolutional layers with exponentially increasing dilation factors, a TCN can look back over very long histories while maintaining a manageable number of parameters and enabling fully parallel computation.

## When to Use It

- You need to model long-range temporal dependencies efficiently
- Training speed matters (TCNs are significantly faster to train than LSTMs due to parallelism)
- The receptive field needs to cover a long history (hundreds of time steps)
- You want a deep learning approach with stable gradients (no vanishing gradient problem)
- The series has patterns at multiple time scales that dilated convolutions can capture naturally

## Key Assumptions

- Enough training data exists for deep learning (typically hundreds of observations minimum)
- The temporal patterns can be captured by hierarchical feature extraction through convolutional layers
- Causal convolutions are appropriate (no future information leaks into predictions)
- The network architecture (number of layers, kernel size, dilation factors) is suitable for the data
- The series has been preprocessed (normalized, possibly differenced)

## Outputs

- **Point forecasts** for the specified horizon
- **Training and validation loss curves**
- **Receptive field size**: the number of historical time steps the network can use
- **Prediction intervals**: via quantile outputs, MC dropout, or ensembling
- **Feature maps**: intermediate layer activations showing learned temporal patterns

## Technical Details

**Causal convolution**: A standard 1D convolution that is masked to prevent the output at time t from depending on inputs at times t+1, t+2, etc. For a filter of size k applied to input x:

`y_t = sum_{i=0}^{k-1} w_i * x_{t-i}`

Only past and current values are used -- no future information leaks.

**Dilated convolution**: Introduces gaps between filter elements. With dilation factor d and kernel size k:

`y_t = sum_{i=0}^{k-1} w_i * x_{t - d*i}`

Dilation d=1 is standard convolution. Dilation d=2 skips every other element. Dilation d=4 skips every 3 elements. This allows the filter to cover a much larger receptive field without increasing the number of parameters.

**TCN architecture**: Stack multiple residual blocks, each containing:
1. Dilated causal convolution (dilation doubles at each layer: 1, 2, 4, 8, 16, ...)
2. Weight normalization or batch normalization
3. ReLU activation
4. Dropout for regularization
5. A second dilated causal convolution
6. Residual connection (skip connection adding the input to the output)

**Receptive field**: For a TCN with L layers, kernel size k, and dilation factors `d_l = 2^l`:

`receptive_field = 1 + (k-1) * sum_{l=0}^{L-1} d_l = 1 + (k-1) * (2^L - 1)`

Example: k=3, L=8 gives a receptive field of 1 + 2*255 = 511 time steps. This means the network can use up to 511 past observations to make each prediction.

**Residual blocks**: The skip connections `y = F(x) + x` enable training of deep networks by providing gradient shortcuts. If the input and output have different channel dimensions, a 1x1 convolution adjusts the input dimension before adding.

**Advantages over LSTM/GRU**:
- **Parallelism**: All time steps can be processed simultaneously (no sequential dependency), making training much faster on GPUs.
- **Stable gradients**: The combination of residual connections and convolutional architecture avoids vanishing/exploding gradients.
- **Flexible receptive field**: Easily controlled by adjusting depth and kernel size.
- **Memory efficiency**: No hidden state to maintain during inference; all computation is through convolutions.

**Training for time series**:
- Input: sliding windows of shape (batch_size, num_channels, sequence_length)
- Output: either the last time step (one-step) or a vector of future values (direct multi-step)
- Loss: MSE, MAE, or quantile loss
- Optimizer: Adam with learning rate scheduling
- Regularization: dropout between layers (spatial dropout preserving channel structure)

**WaveNet connection**: TCN is closely related to WaveNet (DeepMind), which uses dilated causal convolutions with gated activations for audio generation. The TCN simplifies the architecture (ReLU instead of gated activations) and adds residual connections, adapting the approach for general time series forecasting.

**Comparison with recurrent models**: In benchmark studies, TCNs often match or exceed LSTM/GRU accuracy while training several times faster. TCNs are particularly advantageous when the receptive field needs to be very large (hundreds of time steps) and when GPU parallelism can be exploited.

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
