# Prophet Forecast

## What It Does

Prophet is an additive regression model developed by Facebook (Meta) for time series forecasting. It decomposes the series into trend, seasonality (yearly, weekly, daily), and holiday/event effects, fitting each component using interpretable sub-models. The trend uses a piecewise linear or logistic growth curve with automatic changepoint detection, while seasonality is modeled with Fourier series. Prophet is designed to be robust to missing data, outliers, and trend shifts.

## When to Use It

- You need an easy-to-use forecasting model that handles seasonality automatically
- Your data has strong seasonal patterns (yearly, weekly) and possible holiday effects
- The series contains trend changes or shifts that need automatic detection
- You have missing observations or irregular time spacing
- You want interpretable component decompositions (trend, seasonality, holidays)
- Business forecasting tasks where domain knowledge can be incorporated via prior scales

## Key Assumptions

- The series is univariate with a datetime index
- The trend is piecewise linear (or logistic with a cap) with a finite number of changepoints
- Seasonal patterns are well-approximated by Fourier series
- Holiday/event effects are additive and independent
- Future seasonality will resemble past seasonality (stationarity of seasonal pattern)
- The residuals after removing trend and seasonality are approximately white noise

## Outputs

- **Point forecasts** for the specified horizon with uncertainty intervals
- **Trend component**: the long-term trajectory with detected changepoints
- **Seasonal components**: yearly and weekly patterns as separate curves
- **Changepoint locations**: where the trend slope changed significantly
- **Model parameters**: growth rate, seasonality coefficients, changepoint magnitudes

## Technical Details

**Additive model**: The forecast is `y(t) = g(t) + s(t) + h(t) + e(t)` where `g(t)` is the trend, `s(t)` is seasonality, `h(t)` is holiday effects, and `e(t)` is the error term.

**Trend model**: For linear trend, `g(t) = (k + a(t)^T * delta) * t + (m + a(t)^T * gamma)` where `k` is the base growth rate, `delta` is a vector of rate changes at changepoints, `a(t)` is an indicator vector for which changepoints are active, and `gamma` ensures continuity.

**Seasonality**: Modeled as a Fourier series: `s(t) = sum_{n=1}^{N} (a_n * cos(2*pi*n*t/P) + b_n * sin(2*pi*n*t/P))` where `P` is the period (365.25 for yearly, 7 for weekly) and `N` controls the number of Fourier terms (higher N = more flexible seasonality).

**Changepoint detection**: Prophet places potential changepoints uniformly across the first 80% of the training data. A sparse prior (Laplace) on `delta` encourages most changepoints to have zero magnitude, effectively selecting only the significant trend changes. The `changepoint_prior_scale` parameter controls this sparsity.

**Uncertainty intervals**: Generated via simulation. The future trend uncertainty accounts for the historical rate of changepoints, assuming similar changepoint frequency will continue. Seasonal uncertainty comes from the posterior distribution of Fourier coefficients.

**Fitting**: Prophet uses Stan (a probabilistic programming framework) for MAP estimation by default, or full Bayesian inference via MCMC for uncertainty quantification. The fallback implementation uses seasonal naive forecasting when Prophet is not installed.

**Comparison**: Prophet excels at business time series with strong seasonality and is widely used in industry. It trades statistical optimality for ease of use and robustness. For purely stationary series or short series, classical methods like ARIMA or ETS may perform better.

## Interpretation

Prophet runs emit a two-tier Interpretation block with forecast-centric Tier 1 framing.

**Plain-Language Finding (Tier 1)** - fit RMSE vs seasonal-naive baseline with percentage delta, yearly / weekly seasonality flags, number of candidate changepoints (most-recent candidate date rendered via frequency-aware ``format_break_date``). Honest disclosure: candidate changepoints are sparsity-controlled priors, not threshold-detected regime shifts.

**Technical Interpretation (Tier 2)** - piecewise-linear trend with changepoint_prior_scale, yearly seasonality Fourier order, weekly flag, holiday component, L1-shrinkage prior for changepoints, 95% prediction intervals (forced at wrapper to match TSL's convention; Prophet library default is 80%), backend (Stan MAP via cmdstanpy). Includes an actionable closing sentence interpreting candidate changepoints as a flexibility budget the trend uses if the data supports it.

**Caveats (Tier 3, conditional)**:
- Fit RMSE >= naive baseline.
- Candidate changepoint density > 20% of observations.
- Forecast extrapolation > 2x historical max (consider logistic growth).
