# X-13 Seasonal Adjustment

## What It Does

X-13-ARIMA-SEATS is the U.S. Census Bureau's official seasonal adjustment program. It combines ARIMA-based time series modeling with either the X-11 filter-based approach or the SEATS (Signal Extraction in ARIMA Time Series) model-based approach to produce high-quality seasonally adjusted data. It is the standard used by most national statistical agencies worldwide.

## When to Use It

- You are working with official economic statistics (GDP, employment, CPI, retail sales)
- You need publication-quality seasonal adjustment that follows established standards
- You want to account for trading-day effects, holiday effects, and outliers during adjustment
- Your decomposition needs to handle moving holidays like Easter or Chinese New Year
- You require diagnostics to assess the quality and stability of the seasonal adjustment

## Key Assumptions

- The series is monthly or quarterly (the standard frequencies for X-13)
- There is a meaningful seasonal pattern to extract
- The series is long enough for reliable estimation (at least 3 years, preferably 5+)
- Calendar effects and outliers can be modeled through regression variables (regARIMA)

## Outputs

- **Seasonally adjusted series**: the original data with seasonal effects removed
- **Trend-cycle estimate**: the smoothed underlying movement
- **Seasonal factors**: multiplicative or additive adjustments for each period
- **Irregular component**: residual noise after seasonal and trend removal
- **Diagnostics**: M and Q statistics, sliding spans, revision history, spectral plots

## Technical Details

X-13 operates in two main stages: the **regARIMA** modeling stage and the **seasonal adjustment** stage.

**Stage 1 -- regARIMA modeling**:

A regression model with ARIMA errors is fit to the series: `Y_t = sum(beta_i * X_i,t) + Z_t`, where `Z_t ~ ARIMA(p,d,q)(P,D,Q)_s`. The regression variables `X_i` can include:

- **Trading-day regressors**: account for the varying number of each day-of-week in a month.
- **Holiday regressors**: model effects of moving holidays (Easter, Labor Day, Thanksgiving).
- **Outlier regressors**: additive outliers (AO), level shifts (LS), temporary changes (TC), detected automatically or specified by the user.

The ARIMA model is either specified by the user or selected automatically using the Hyndman-Khandakar algorithm or the X-13 built-in selection procedure, which tests a predefined set of models.

The regARIMA model serves two purposes: (a) extending the series with forecasts and backcasts so the X-11 filters do not lose observations at the endpoints, and (b) pre-adjusting the series for calendar and outlier effects.

**Stage 2a -- X-11 filter approach**:

1. Apply a centered moving average (2x12 for monthly data) to estimate an initial trend.
2. Compute seasonal-irregular ratios: `SI_t = Y_t / T_t` (multiplicative) or `Y_t - T_t` (additive).
3. Smooth the SI ratios with a seasonal moving average (e.g., 3x3 or 3x5) applied to each month separately.
4. Normalize seasonal factors to average 1.0 (multiplicative) or 0.0 (additive).
5. Compute a refined seasonally adjusted series and re-estimate the trend with a Henderson filter.
6. Repeat for a total of three iterations, refining estimates each time.

**Stage 2b -- SEATS approach** (alternative to X-11):

Decompose the ARIMA model for `Z_t` into signal components (trend, seasonal, irregular) using the canonical decomposition of Burman. Each component is an ARIMA process, and Wiener-Kolmogorov filters extract the minimum mean square error estimate of each component.

**Key diagnostics**:
- **M-statistics (M1-M11)**: assess quality aspects like relative contribution of the irregular, seasonal moving average adequacy, and randomness of residuals. The overall **Q-statistic** summarizes them; Q < 1 indicates acceptable quality.
- **Sliding spans**: re-run the adjustment on overlapping subspans to check stability. Seasonal factors should not change substantially across spans.
- **Spectral plots**: check for residual seasonality in the adjusted series at seasonal frequencies.

## Interpretation

**Plain-Language Finding (Tier 1)** - observations, frequency, transform choice, outlier-detection status, seasonal strength band. Closes by pointing at the seasonally-adjusted series for month-over-month analysis.

**Technical Interpretation (Tier 2)** - **always discloses which backend** (Census Bureau binary or statsmodels fallback) was actually used. Reports outlier count, seasonal strength formula, and notes the separate irregular component.

**Caveats (Tier 3, conditional)**:
- Fallback in use - Census binary unavailable, results are approximate.
- Negligible seasonality (< 0.3) - series may not require SA.
