## What It Does
A transfer-function model (distributed-lag / dynamic regression) relates an output series to the current and lagged values of an input series, plus the output's own past. It estimates how a change in the input propagates to the output over time — the distributed-lag weights — and the cumulative long-run effect. It is the interpretable tool for an input-output relationship where the input leads the output with some lag structure.

## When to Use It
- You have an input series and an output series and want to quantify how the input drives the output over time.
- You want the distributed-lag weights (the effect at each lag) and the long-run multiplier (the cumulative effect).
- The input can be treated as driving the output without strong feedback the other way.
- Use it for an interpretable lead-lag/driver analysis; use `arimax_sarimax` when you want ARIMA error dynamics around the driver effect; find the lag structure first with `cross_correlation_lag`.

## How to Read the Result
The first series is the output, the second the input. The output is the lag weights, the long-run multiplier, and fit statistics. On a synthetic distributed-lag relationship the model recovers the structure with R² 0.947: the peak effect is at lag 0 (weight 0.47) and the long-run multiplier — the total effect of a sustained one-unit change in the input — is 0.56. Read the lag profile for the timing of the response and the long-run multiplier for its eventual size. One assumption to keep in mind: the model treats the input as weakly exogenous (it does not model feedback from the output back to the input), so it is appropriate when the causal direction runs predominantly one way.

## Related Techniques
- *(use before)* `cross_correlation_lag` or `prewhitened_ccf_lag` to identify the lead-lag structure before specifying the lags.
- *(alternatives)* `arimax_sarimax` (exogenous regressors with ARIMA errors); the VAR family when input and output are mutually endogenous.

## Technical Detail
Estimation is ordinary least squares (numpy) of the output on the contemporaneous and lagged input and on lagged output terms: `Y_t = c + Σ w_k·X_{t-k} + Σ p_j·Y_{t-j} + e_t`. The first series is the output, the second the input. The maximum input lag is set by the dialog; the autoregressive order on the output, whether the contemporaneous input term is included, and an optional Almon polynomial lag restriction are governed by preset. Outputs include the distributed-lag weights, the long-run multiplier, R², and a residual diagnostic.
*Reference run:* a synthetic distributed-lag series with input weights (0.5, 0.3, 0.1) on an AR(0.6) input plus AR(1) noise (n=200), maximum lag 12, Balanced — peak weight at lag 0 (0.47), long-run multiplier 0.56, R² 0.947, RMSE 0.20, Ljung-Box(10) p = 0.87.
