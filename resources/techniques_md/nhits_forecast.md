# N-HiTS Forecast

## What It Does

N-HiTS (Neural Hierarchical Interpolation for Time Series) is a deep learning architecture for time series forecasting that extends N-BEATS with hierarchical interpolation and multi-rate signal sampling. Each stack in N-HiTS operates at a different temporal resolution, allowing the model to efficiently capture patterns at multiple scales. The hierarchical interpolation reduces the number of parameters and improves long-horizon forecasting performance compared to N-BEATS.

## When to Use It

- You want a deep learning model optimized for long-horizon forecasting
- The series contains patterns at multiple temporal scales (short-term fluctuations + long-term trends)
- You need better computational efficiency than N-BEATS for long horizons
- You want a pure time series architecture that works without exogenous features
- The series has enough historical data to train a neural network (typically 100+ observations)

## Key Assumptions

- The series is univariate with sufficient history for the lookback window
- Patterns at different temporal scales are present and can be captured hierarchically
- The lookback window is long enough to capture relevant dynamics
- Enough training data is available for the neural network to generalize
- Future patterns will resemble historical patterns at the relevant scales

## Outputs

- **Point forecasts** for the specified horizon
- **Training log**: loss progression over epochs
- **Model summary**: architecture details, number of parameters, training/validation loss

## Technical Details

**Key innovation over N-BEATS**: N-HiTS introduces two mechanisms: (1) multi-rate signal sampling via MaxPool layers that downsample the input at different rates for each stack, and (2) hierarchical interpolation that produces forecasts at a coarser resolution and then interpolates to the full forecast horizon.

**Multi-rate sampling**: Each stack `s` applies MaxPool with kernel size `k_s` to the input lookback window. Stack 1 might use `k_1=1` (full resolution), Stack 2 uses `k_2=2` (half resolution), Stack 3 uses `k_3=4` (quarter resolution). This creates a hierarchy where different stacks see the signal at different temporal granularities.

**Hierarchical interpolation**: Instead of directly outputting `H` forecast values (like N-BEATS), each block outputs `H/r_s` values where `r_s` is the interpolation ratio for stack `s`. These are then upsampled via interpolation to the full `H` length. This dramatically reduces the number of output parameters.

**Block structure**: Similar to N-BEATS, each block:
1. Takes the downsampled input through fully connected layers with ReLU
2. Produces backcast coefficients and forecast coefficients
3. The backcast is subtracted from the input (residual learning)
4. The forecast is interpolated to the full horizon

**Stack aggregation**: The total forecast is the sum of interpolated forecasts from all stacks: `y_total = sum_s Interp(f_s, r_s)`.

**Parameter efficiency**: For a horizon of H=720 (long horizon), N-BEATS needs each block to output 720 values, while N-HiTS with interpolation ratios [1, 4, 16] outputs [720, 180, 45] values across stacks. This 3-10x reduction in output parameters prevents overfitting and speeds up training.

**Fallback implementation**: When PyTorch is not installed, the module falls back to a sklearn-based ensemble that combines GradientBoosting regressors at multiple lag resolutions (full, half, quarter) to approximate the hierarchical concept.

**Comparison**: N-HiTS achieves comparable or better accuracy than N-BEATS while using significantly fewer parameters, especially for long forecast horizons. It was introduced as a direct improvement over N-BEATS, showing particular strength on the long-horizon benchmarks (ETTh, Weather, Traffic).

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
