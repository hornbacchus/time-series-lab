# TBATS / BATS

## What It Does

TBATS (Trigonometric seasonality, Box-Cox, ARMA errors, Trend, Seasonal)
and BATS (the non-trigonometric sibling) are forecasting models built
specifically for series with **multiple, possibly non-integer, seasonal
cycles**. Examples include daily retail data with both a 7-day weekly
pattern and a 365.25-day annual pattern, or hourly electricity load
with hourly, daily, and weekly cycles stacking simultaneously.

TBATS uses a trigonometric (Fourier) representation of each seasonal
state, which lets it fit non-integer periods (like 365.25 days) exactly
and compactly. BATS uses classical seasonal-dummy states and therefore
requires integer periods.

## When to Use It

- You have daily, hourly, or sub-hourly data with more than one clear
  seasonal cycle (daily + weekly; weekly + annual; intraday + daily +
  weekly).
- The primary seasonal period is non-integer (like 365.25) and you
  want it represented exactly.
- You suspect multiplicative variance (Box-Cox transformation will
  be auto-selected).
- You want a forecaster that handles complex seasonality without
  manual Fourier-regressor engineering.

## Key Assumptions

- The seasonal periods are approximately stable across the sample.
- Observations are regularly spaced.
- For Box-Cox to apply, the series must be strictly positive.
- Series length `n` is at least `2 * max(seasonal_periods)` for the
  model to estimate each seasonal state (the wrapper filters periods
  that violate this).

## Outputs

- **Point forecast** for the specified horizon plus 95% prediction
  intervals.
- **Fitted values** on the training sample.
- **Model summary** including AIC, smoothing parameters (alpha, beta,
  gamma-per-period), chosen options (Box-Cox, ARMA errors, damped
  trend), and the harmonics per seasonal period (TBATS only).
- **Naive baseline** comparison: seasonal-naive when a seasonal period
  is fitted, last-value-naive otherwise.

## Caveats

- Fit times grow with the number of seasonal periods and the Balanced
  / Thorough presets' AIC search; for large series with 3+ seasonal
  periods the Thorough preset can take several minutes.
- BATS forces non-integer periods to integer by rounding; use TBATS
  (the default `use_trigonometric=True`) when any period is non-
  integer.
- Prediction intervals assume normally-distributed innovations after
  Box-Cox transformation; heavy-tailed residuals can under-cover.

## Interpretation

Every TBATS / BATS run emits a two-tier plain-language Interpretation
block. Inherits the Prompt C2 forecaster Tier 1 template via
`_forecast_common` helpers with a seasonality-rendering closer.

**Plain-Language Finding (Tier 1)** — names the model variant (TBATS
or BATS), observations, horizon, fit RMSE vs naive baseline with the
improvement percentage, the horizon-trend clause (forecast end vs
latest observation), and a seasonality description citing each fitted
period (with named aliases like "weekly=7", "annual=365.25" where
recognized). If any user- or auto-inferred periods were filtered
because the sample was too short, Tier 1 discloses the filter.

**Technical Interpretation (Tier 2)** — opens with TBATS vs BATS
framing, discloses whether seasonal periods were user-specified or
auto-inferred from the series frequency, cites the AIC-selected
options (Box-Cox with a λ interpretation band, ARMA errors, damped
trend), reports smoothing parameters and AIC, lists the harmonics-per-
period (TBATS only), and — for BATS runs — explicitly discloses any
non-integer periods that were rounded to integers with a pointer to
`use_trigonometric=True` for native handling.

**Caveats (Tier 3, conditional)**:
- `short_series_for_seasonality` — series length less than 2× the
  longest fitted period.
- `box_cox_severe` — Box-Cox λ outside [-0.5, 1.5] indicates extreme
  heteroscedasticity.
- `non_integer_seasonality` — fires on TBATS runs with any non-
  integer period, highlighting the TBATS-specific capability.
- `rmse_exceeds_naive` — fit RMSE at or above the naive baseline;
  model does not beat naive.
- `user_specified_periods_filtered` — fires when the user explicitly
  passed `seasonal_periods=[…]` but the wrapper dropped one or more
  because the sample was too short. Auto-inferred filtering does not
  fire this caveat (Tier 2 disclosure is sufficient); user-specified
  filtering does, because user intent was explicit.
