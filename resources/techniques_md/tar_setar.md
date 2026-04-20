# TAR / SETAR Models

## What It Does

Threshold Autoregressive (TAR) and Self-Exciting Threshold Autoregressive (SETAR) models capture **regime-dependent dynamics** based on observable threshold variables. When a variable crosses a threshold, the model switches between different autoregressive specifications. In SETAR, the threshold variable is the series' own lagged value, making the regime switches endogenous. This allows asymmetric behavior -- for example, different dynamics during expansions vs. recessions.

## When to Use It

- Your series exhibits asymmetric behavior (e.g., sharp declines but gradual recoveries)
- You believe the dynamics change depending on whether the series is above or below a critical level
- Economic theory suggests threshold effects (e.g., unemployment dynamics differ above/below a natural rate)
- You want a nonlinear model that remains interpretable (piecewise linear)
- You need to test for threshold nonlinearity in your data

## Key Assumptions

- The regime is determined by an observable threshold variable (a lagged value of the series in SETAR)
- Within each regime, the dynamics are linear (autoregressive)
- The threshold value and delay parameter are fixed over time
- The number of regimes (usually 2 or 3) is correctly specified
- The series is stationary within each regime (though globally it may appear non-stationary)

## Outputs

- **Threshold value(s)**: the estimated boundary between regimes
- **Regime-specific AR coefficients**: separate dynamics for each regime
- **Delay parameter**: which lag of the threshold variable triggers the switch
- **Regime classification**: which regime each observation belongs to
- **Threshold test results**: whether the threshold effect is statistically significant

## Technical Details

**SETAR(k, p_1, ..., p_k) model** with k regimes:

For a 2-regime SETAR:
```
Y_t = c_1 + phi_{1,1} Y_{t-1} + ... + phi_{1,p1} Y_{t-p1} + e_{1,t}   if Y_{t-d} <= r
Y_t = c_2 + phi_{2,1} Y_{t-1} + ... + phi_{2,p2} Y_{t-p2} + e_{2,t}   if Y_{t-d} > r
```

where `r` is the threshold, `d` is the delay parameter (d >= 1), `p_1, p_2` are the AR orders in each regime, and `e_{i,t} ~ N(0, sigma_i^2)`.

**TAR model**: The general TAR form uses an external threshold variable `Z_t` instead of the series itself: the regime is determined by `Z_{t-d} <= r` vs. `Z_{t-d} > r`.

**Estimation**:

1. **Conditional on r and d**: For given threshold and delay, the model splits into two separate AR regressions. OLS is applied to each subsample, and the residual sum of squares (RSS) is computed.

2. **Grid search over r and d**: The threshold `r` is searched over a grid of observed values of `Y_{t-d}` (excluding the extreme 10-15% to ensure enough observations in each regime). The delay d is searched over `{1, 2, ..., d_max}`. The combination minimizing the total RSS is selected.

3. **Concentrated least squares**: `(r_hat, d_hat) = argmin_{r,d} RSS(r, d)`, where `RSS(r, d) = RSS_1(r, d) + RSS_2(r, d)`.

**Testing for threshold effects**: Standard tests do not apply because the threshold parameter is unidentified under the null hypothesis of no threshold (the Davies problem). Solutions include:

- **Sup-LR test** (Hansen 1996): Compute the likelihood ratio statistic for each candidate threshold and take the supremum. P-values are obtained by bootstrap:
  1. Fit the linear AR (null) model and save residuals.
  2. Resample residuals to generate B bootstrap series.
  3. For each bootstrap series, compute the sup-LR statistic.
  4. The p-value is the proportion of bootstrap statistics exceeding the observed statistic.

- **Tsay's test**: A simpler arranged autoregression test that orders observations by the threshold variable and detects parameter instability.

**Threshold cointegration**: TAR models can be applied to error correction terms to allow asymmetric adjustment toward equilibrium. The Enders-Siklos threshold cointegration test extends the Engle-Granger framework.

**Ergodicity and stationarity**: A 2-regime SETAR is globally stationary if the autoregressive processes in both regimes are contractive. Sufficient conditions involve the spectral radii of the companion matrices in each regime being less than 1.

## Interpretation

**Plain-Language Finding (Tier 1)** - SETAR with threshold(s) on y(t-d), delay, linearity-test F-stat and p-value verdict, regime-1 share, actionable closer on regime-conditional inference.

**Technical Interpretation (Tier 2)** - threshold grid-search estimation, per-regime sigma and observation counts, linearity-test construction. Contrasts with STAR (discrete vs smooth transition) and Markov Switching (observable vs latent triggering variable).

**Caveats (Tier 3, conditional)**:
- Weak linearity test (p > 0.10) - linear AR may suffice.
- Imbalanced regimes (any < 15%) - coefficient estimates unstable.
- Underpopulated inner regime in 3-regime SETAR - consider 2-regime.
