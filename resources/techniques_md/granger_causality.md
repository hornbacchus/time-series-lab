# Granger Causality Test

## What It Does

The Granger causality test determines whether one time series is useful in **predicting** another. If past values of series X significantly improve the forecast of series Y (beyond what Y's own past provides), then X is said to "Granger-cause" Y. This is a test of predictive causality, not true causality -- it measures whether X contains information about Y's future that is not already in Y's own history.

## When to Use It

- You want to test whether one variable has predictive power for another
- You are investigating lead-lag relationships between economic or financial variables
- You need to justify including one variable as a predictor in a forecasting model for another
- You want evidence (or lack thereof) for directional information flow between series
- You are building a VAR model and want to understand which variables drive which

## Key Assumptions

- Both series are stationary (or have been differenced to achieve stationarity)
- The relationship between the series is linear
- The chosen number of lags is sufficient to capture the predictive relationship
- No important confounding variables are omitted from the model
- The residuals are white noise (no remaining autocorrelation)

## Outputs

- **F-statistic** (or chi-squared statistic): the test statistic for joint significance of the lags of X in the Y equation
- **p-value**: the probability of observing the test statistic under the null of no Granger causality
- **Direction of causality**: X -> Y, Y -> X, bidirectional, or neither
- **Selected lag order**: the number of lags used in the test
- **Coefficient estimates**: the estimated effect of each lag of X on Y

## Technical Details

**Bivariate Granger causality test**: Test whether X Granger-causes Y by comparing two models:

Unrestricted: `Y_t = c + sum_{i=1}^{p} alpha_i Y_{t-i} + sum_{j=1}^{p} beta_j X_{t-j} + u_t`

Restricted: `Y_t = c + sum_{i=1}^{p} alpha_i Y_{t-i} + u_t`

**Null hypothesis**: H0: `beta_1 = beta_2 = ... = beta_p = 0` (X does not Granger-cause Y)

**Test statistic**: F-test comparing the restricted and unrestricted models:

`F = ((RSS_R - RSS_U) / p) / (RSS_U / (T - 2p - 1))`

Under H0, `F ~ F(p, T - 2p - 1)`.

Alternatively, the Wald chi-squared test: `W = T * (RSS_R - RSS_U) / RSS_U ~ chi^2(p)` under H0.

**Lag selection**: Critical for the validity of the test. Too few lags may miss the predictive relationship; too many reduce power. Choose p using:
- AIC or BIC on the unrestricted VAR(p) model for both variables
- Ensure residuals from the selected lag order are white noise (Ljung-Box test)

**Conditional Granger causality**: In a multivariate system with additional variables Z:

`Y_t = c + sum alpha_i Y_{t-i} + sum beta_j X_{t-j} + sum gamma_k Z_{t-k} + u_t`

Test `beta_1 = ... = beta_p = 0`. This tests whether X predicts Y beyond what both Y and Z provide, addressing potential confounding by Z.

**Toda-Yamamoto approach**: When the stationarity status is uncertain, fit a VAR(p + d_max) in levels (where d_max is the maximum order of integration) but test only the first p lags. This avoids pre-testing for unit roots and cointegration while maintaining the chi-squared distribution of the test statistic.

**Interpretation pitfalls**:
- Granger causality is about prediction, not causation. X may Granger-cause Y because both respond to a common unobserved factor, with X responding faster.
- Failure to reject may occur due to insufficient lag length, nonlinear relationships, or low power.
- Bidirectional Granger causality (feedback) is common in economics and does not indicate simultaneous causation.
- The test is sensitive to the information set: adding or removing variables can change the results.

**Nonlinear Granger causality**: Extensions using nonparametric methods (Diks-Panchenko test) or transfer entropy measure whether X provides nonlinear predictive information about Y beyond the linear relationship captured by the standard test.
