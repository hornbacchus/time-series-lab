# Forecast Combination

## What It Does

Forecast combination (ensemble forecasting) merges predictions from **multiple forecasting models** into a single, improved forecast. Different models capture different aspects of the data, and their errors tend to be partially uncorrelated. By combining them, the combined forecast typically outperforms most or all individual models -- a phenomenon so reliable it has been called the "forecast combination puzzle."

## When to Use It

- You have forecasts from multiple models and want to choose or combine them
- No single model consistently outperforms others across all horizons and time periods
- You want to reduce the risk of relying on a single, potentially misspecified model
- Forecasting competitions and applications consistently show combination improves accuracy
- You need a robust forecast that is less sensitive to model selection

## Key Assumptions

- Multiple forecast models are available for the same target and horizon
- The individual forecasts have some diversity (not perfectly correlated errors)
- The combination weights, if estimated, have been calibrated on appropriate historical data
- The relative performance of models is sufficiently stable for estimated weights to be useful out-of-sample
- The models are producing forecasts for the same quantity at the same time

## Outputs

- **Combined forecast**: the weighted average (or other combination) of individual forecasts
- **Combination weights**: the relative contribution of each model
- **Improvement metrics**: how much the combination outperforms individual models
- **Diversity analysis**: correlation between individual model errors
- **Combined prediction intervals**: reflecting the uncertainty of the ensemble

## Technical Details

**Simple combination methods**:

1. **Simple (equal-weight) average**: `F_c = (1/M) sum_{m=1}^{M} F_m`

   Remarkably effective in practice. Often outperforms complex weighting schemes because estimated weights add estimation error. Recommended as the default.

2. **Median combination**: `F_c = median(F_1, ..., F_M)`. More robust to outlier forecasts than the mean.

3. **Trimmed mean**: Remove the highest and lowest k forecasts, average the rest. Balances robustness and efficiency.

**Estimated weight methods**:

4. **Inverse MSE weighting**: `w_m = (1/MSE_m) / sum_j (1/MSE_j)`, where `MSE_m` is model m's historical mean squared error. Gives more weight to better-performing models.

5. **OLS (Granger-Ramanathan) regression**:
   `Y_t = beta_0 + beta_1 F_{1,t} + ... + beta_M F_{M,t} + e_t`

   Variants: (a) unconstrained, (b) intercept = 0, (c) weights sum to 1 and intercept = 0.
   Risk: overfitting when M is large or the calibration window is short.

6. **Constrained Least Squares**: Minimize `sum(Y_t - sum w_m F_{m,t})^2` subject to `w_m >= 0` and `sum w_m = 1`. Non-negative weights with no intercept, reducing overfitting.

7. **Bayesian Model Averaging (BMA)**:
   `F_c = sum_m P(M_m | Y) F_m`

   Weights are posterior model probabilities. `P(M_m | Y) propto P(Y | M_m) P(M_m)`, where `P(Y | M_m)` is the marginal likelihood. Models that fit the data better in a Bayesian sense get higher weight.

**Time-varying weights**:

8. **Exponentially weighted combination**: `w_{m,t} propto exp(-lambda * sum_{s=t-W}^{t-1} L(e_{m,s}))`, where `L` is a loss function and lambda controls the speed of adaptation. Recent performance is emphasized.

9. **Online learning (expert aggregation)**: Algorithms like the exponentially weighted average forecaster or the fixed-share algorithm update weights after each observation, with theoretical regret bounds.

**Why simple averaging works**: The MSE of the combined forecast is:

`MSE_c = sum_m sum_j w_m w_j Cov(e_m, e_j)`

With equal weights: `MSE_c = (1/M^2) sum_m sum_j sigma_m sigma_j rho_{mj}`. As M grows, the contribution of individual variances shrinks as 1/M while the average covariance remains. With diverse (low-correlated) models, the combination variance decreases substantially.

**Combining prediction intervals**: Methods include:
- Average the interval endpoints from each model.
- Use the widest interval (conservative).
- Combine quantile forecasts and apply Vincentization (averaging quantile functions).
- Simulation-based: draw from each model's predictive distribution with weights proportional to the combination weights.

**Model diversity**: The effectiveness of combination depends on error diversity. Adding a model that is highly correlated with existing models provides little benefit. The optimal ensemble has models with uncorrelated errors, even if individually they are not the best.

## Interpretation

**Plain-Language Finding (Tier 1)** - ensemble size, dominant model weight, inverse-MSE weighting, ensemble holdout MSE vs best single constituent MSE with delta percentage (Decision A option b).

**Technical Interpretation (Tier 2)** - holdout split, per-model MSE values in prose (S3 convention), equal-weight baseline comparison.

**Caveats (Tier 3, conditional)**:
- Near-single ensemble (dominant weight > 0.9) - use dominant alone.
- Ensemble hurts (ensemble MSE > best constituent) - use best alone.
- Weights ~= equal - simple averaging suffices.
