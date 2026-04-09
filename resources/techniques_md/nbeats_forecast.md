# N-BEATS Forecast

## What It Does

N-BEATS (Neural Basis Expansion Analysis for Time Series) is a deep learning architecture designed **specifically for time series forecasting**. It uses a deep stack of fully connected blocks that produce both a "backcast" (fit to the past) and a "forecast" (prediction of the future). Each block's backcast is subtracted from the input before passing to the next, creating a residual learning scheme. The interpretable variant decomposes the forecast into trend and seasonal components using structured basis functions.

## When to Use It

- You want a state-of-the-art deep learning forecast for univariate time series
- You need a pure time series architecture (not borrowed from NLP or computer vision)
- The interpretable variant is desired, producing explicit trend and seasonal decompositions
- You have enough data for deep learning but want an architecture that works without exogenous features
- You want to ensemble multiple models for robust forecasts (as used in the M4 competition win)

## Key Assumptions

- The series is univariate (multivariate extensions exist but the core architecture is univariate)
- The lookback window is long enough to capture the relevant dynamics (typically 2-7 times the forecast horizon)
- Enough training data is available for the fully connected layers to learn meaningful patterns
- The basis functions (polynomial for trend, Fourier for seasonality) are appropriate for the interpretable variant
- The series can be meaningfully predicted from its own past (no critical exogenous dependencies)

## Outputs

- **Point forecasts** for the specified horizon
- **Component decomposition** (interpretable variant): separate trend and seasonal forecast components
- **Backcast fit**: how well each block fits the historical input
- **Training and validation loss curves**
- **Ensemble forecasts**: when multiple models are combined

## Technical Details

**Architecture overview**: N-BEATS consists of multiple stacks, each containing several blocks. Information flows through the stacks sequentially, with residual connections ensuring that each stack focuses on explaining what the previous stacks could not.

**Block structure**: Each block takes input `x` (the lookback window or its residual) and produces:
1. Pass x through a stack of fully connected layers with ReLU activations (typically 4 layers of 256-512 units).
2. From the final hidden layer, produce two linear projections:
   - `theta_b` (backcast parameters): coefficients for the basis expansion of the past
   - `theta_f` (forecast parameters): coefficients for the basis expansion of the future
3. **Backcast**: `x_hat = V_b * theta_b` (basis expansion for the lookback window)
4. **Forecast**: `y_hat = V_f * theta_f` (basis expansion for the forecast horizon)

The residual passed to the next block is `x - x_hat`.

**Basis functions for the interpretable variant**:

- **Trend stack**: `V` contains polynomial basis vectors: `[1, t, t^2, ..., t^p]` for each time point. Degree p is typically 2-3. This constrains the trend output to be a smooth polynomial.

- **Seasonal stack**: `V` contains Fourier basis vectors: `[cos(2*pi*k*t/period), sin(2*pi*k*t/period)]` for harmonics k = 1, ..., K. This constrains the seasonal output to be a periodic function.

**Generic variant**: `V_b` and `V_f` are fully learnable linear layers (no structural constraints). This gives maximum flexibility but sacrifices interpretability.

**Stack-level aggregation**: The total forecast is the sum of forecasts from all blocks across all stacks: `y_total = sum_s sum_b y_hat_{s,b}`. The residual subtraction ensures that each block focuses on different aspects of the signal.

**Training**:
- Loss: MSE, MAE, or MAPE (symmetric MAPE was used in the M4 competition)
- Optimizer: Adam with learning rate 0.001, reduced on plateau
- Lookback: 2x to 7x the forecast horizon (longer lookback captures more context)
- Batch size: 1024 (using random windows from the training set)
- Ensemble: Train 3-18 models with different random initializations and average their forecasts. The ensemble significantly improves robustness.

**Doubly residual architecture**: The residual learning operates at two levels: (1) within each stack, the backcast of each block removes the explained variation, and (2) across stacks, the input to each stack is the residual from all previous stacks. This hierarchical residual learning enables very deep networks (30+ blocks) to train effectively.

**N-BEATSx extension**: Adds exogenous variables by concatenating them with the lookback input at each block. The block structure remains the same, but the input dimension increases.

**Comparison**: N-BEATS won the M4 competition (2018) in the pure ML category and was competitive with statistical ensembles. Its key innovation is showing that a simple fully-connected architecture with residual learning and structured basis functions can outperform recurrent and convolutional approaches for time series forecasting.
