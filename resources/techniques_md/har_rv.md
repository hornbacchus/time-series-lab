# HAR-RV Model

## What It Does

The HAR-RV (Heterogeneous Autoregressive model of Realized Volatility) forecasts volatility using **realized volatility** measures computed from high-frequency intraday data. It captures the empirical finding that volatility depends on activity at multiple time horizons -- daily, weekly, and monthly -- reflecting the behavior of different types of market participants. Despite its simplicity (a linear regression), it is remarkably effective at modeling the long-memory-like behavior of realized volatility.

## When to Use It

- You have access to high-frequency (intraday) price data to compute realized volatility
- You need to forecast volatility at daily, weekly, or monthly horizons
- You want a simple, interpretable model that captures the long-memory persistence of volatility
- GARCH-based models on daily returns do not fully exploit available intraday information
- You are computing risk measures, hedging ratios, or option-implied vs. realized volatility comparisons

## Key Assumptions

- Reliable high-frequency data is available to compute realized volatility
- Microstructure noise is adequately handled (through sampling frequency choice or noise-robust estimators)
- The additive multi-horizon structure captures the relevant volatility dynamics
- The realized volatility measure is a consistent estimator of integrated volatility
- The relationship between past realized volatilities at different horizons and future volatility is stable

## Outputs

- **Realized volatility forecasts** at the target horizon
- **Regression coefficients** for daily, weekly, and monthly RV components
- **Component contributions**: relative importance of short-, medium-, and long-term volatility
- **R-squared and forecast accuracy metrics** (MSE, QLIKE)
- **Fitted vs. actual realized volatility** time series

## Technical Details

**Realized volatility**: Computed from intraday returns sampled at frequency delta (typically 5-minute intervals):

`RV_t = sum_{j=1}^{M} r_{t,j}^2`

where `r_{t,j}` is the j-th intraday return on day t and M is the number of intraday intervals. Under ideal conditions, `RV_t -> int_0^1 sigma_s^2 ds` (integrated variance) as the sampling frequency increases.

**HAR-RV model** (Corsi, 2009):

`RV_t = c + beta_D RV_{t-1}^{(D)} + beta_W RV_{t-1}^{(W)} + beta_M RV_{t-1}^{(M)} + e_t`

where:
- `RV_{t-1}^{(D)} = RV_{t-1}` (previous day's RV)
- `RV_{t-1}^{(W)} = (1/5) sum_{i=1}^{5} RV_{t-i}` (average RV over the past week)
- `RV_{t-1}^{(M)} = (1/22) sum_{i=1}^{22} RV_{t-i}` (average RV over the past month)

**Why it works**: Different market participants operate at different frequencies. Day traders respond to daily volatility, portfolio managers to weekly, and institutional investors to monthly. The HAR specification aggregates these heterogeneous behaviors. Although it is a simple linear regression with only 3 regressors, it produces a flexible lag structure that mimics long memory: a shock to daily RV affects the weekly average, which in turn affects the monthly average, creating persistence that decays slowly.

**Estimation**: OLS on the realized volatility series. For h-day-ahead forecasts, the dependent variable is the average RV over the next h days:

`RV_t^{(h)} = (1/h) sum_{j=1}^{h} RV_{t+j} = c + beta_D RV_t^{(D)} + beta_W RV_t^{(W)} + beta_M RV_t^{(M)} + e_t`

Newey-West standard errors account for serial correlation in the residuals (especially for multi-day horizons).

**Extensions**:
- **HAR-RV-J**: Add a jump component `J_t = max(RV_t - BV_t, 0)` as a regressor, where `BV_t` is bipower variation. Jumps increase short-term volatility forecasts.
- **HAR-RV-CJ**: Separate continuous and jump components.
- **LHAR-RV**: Use leverage (negative returns) as additional regressors to capture asymmetric effects.
- **Log-HAR**: Model `log(RV_t)` to reduce heteroskedasticity and ensure positive forecasts.

**Microstructure noise**: At very high frequencies, bid-ask bounce and other microstructure effects inflate RV. Solutions include sampling at 5-minute intervals, using kernel-based estimators (Barndorff-Nielsen et al.), or pre-averaging.

## Interpretation

Every HAR-RV run emits a two-tier plain-language Interpretation block. Tier 1 inherits the Prompt C2 forecaster template (RMSE + baseline comparison + horizon-trend) with a volatility-vs-return unit distinction.

**Plain-Language Finding (Tier 1)** - names the model type, the Corsi-2009 default lag structure (1 / 5 / 22 for daily / weekly / monthly), the rolling-22-period mean RV baseline comparison, the horizon-trend clause, the fit R² with adjusted R², and the dominant component (daily, weekly, or monthly) by coefficient magnitude. The noun phrase "realized volatility" anchors the reader on volatility scale to prevent unit-confusion with return-forecasting techniques.

**Technical Interpretation (Tier 2)** - discloses the OLS coefficients (β₀, β_d, β_w, β_m) with signed values, the persistence sum β_d + β_w + β_m, AIC / BIC, residual Ljung-Box and Jarque-Bera p-values, and three structured notes:
1. **Scale note:** fit RMSE is on realized-variance scale (not return scale) — direct RMSE comparison with return-forecasting techniques such as ARIMA is not meaningful.
2. **Annualization (Convention B):** daily volatility × √252 ≈ 15.87 converts to annual-scale volatility; daily variance × 252 converts to annual-scale variance. No wrapper change is applied; the caller annualizes post-hoc.
3. **Standard errors:** OLS under normal-residuals assumption (not HAC/Newey-West corrected); HAR residuals often exhibit heteroscedasticity and autocorrelation on RV, so coefficient-level significance should be treated as indicative.

**Caveats (Tier 3, conditional)**:
- Residual Ljung-Box rejects white-noise - HAR structure is inadequate; consider log-HAR form (use_log=True), adding lags beyond 22, or a HAR-CJ variant for jumps.
- Residual Jarque-Bera rejects normality (and use_log=False) - raw-scale HAR is sensitive to right-skewness; consider log-HAR (use_log=True).
- Fit RMSE ≥ rolling-mean baseline - HAR does not beat a simple trailing-average volatility forecast on this series.
- R² < 0.30 - lag structure may not capture the full volatility dynamics; consider (a) log-HAR, (b) longer lags for long-memory volatility, or (c) jumps-aware variants like HAR-CJ.

