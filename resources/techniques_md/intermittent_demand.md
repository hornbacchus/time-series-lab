# Intermittent Demand Forecasting

## What It Does

Intermittent demand forecasting handles time series where many observations are zero, with non-zero values occurring irregularly. Standard forecasting methods perform poorly on such data because they assume continuous demand. Specialized methods like Croston's method and its variants separately model the demand size and the interval between demand events, then combine them for a forecast.

## When to Use It

- Your data has frequent zero values interspersed with sporadic non-zero demands
- You are forecasting spare parts, slow-moving inventory, or specialty products
- Standard methods (ARIMA, ETS) produce poor forecasts because they smooth over the zeros
- You need to set safety stock levels or reorder points for items with irregular demand
- The demand pattern shows a mix of long quiet periods and occasional bursts

## Key Assumptions

- Demand occurrences and demand sizes are independent processes
- The demand process is stationary (the probability of demand and the mean size do not change over time)
- Non-zero demand sizes are positive
- The process is not trending or seasonal (extensions exist for those cases)
- The demand intervals and sizes can each be described by simple time series models

## Outputs

- **Flat demand rate forecast**: the expected demand per period (demand size / inter-demand interval)
- **Estimated mean demand size**: average of non-zero demands, updated via exponential smoothing
- **Estimated mean inter-demand interval**: average time between demands, updated via exponential smoothing
- **Classification**: whether the item is smooth, intermittent, erratic, or lumpy (based on the CV of demand size and the average inter-demand interval)

## Technical Details

**Croston's method (1972)**:

The original method maintains two separate exponential smoothing estimates updated only when a non-zero demand occurs:

When demand `Y_t > 0` at time `t`:
- Update demand size estimate: `Z_t = alpha * Y_t + (1-alpha) * Z_{t-1}`
- Update inter-demand interval: `P_t = alpha * q_t + (1-alpha) * P_{t-1}`, where `q_t` is the number of periods since the last non-zero demand.

When demand `Y_t = 0`: estimates remain unchanged.

The forecast demand rate is: `F_t = Z_t / P_t`.

**Syntetos-Boylan Approximation (SBA)**:

Croston's method has a known positive bias. The SBA corrects this by adjusting the forecast:

`F_t = (1 - alpha/2) * Z_t / P_t`

This correction accounts for the timing bias in Croston's interval estimation and is the recommended default for most intermittent demand applications.

**Teunter-Syntetos-Babai (TSB) method**:

Instead of smoothing the inter-demand interval, TSB directly smooths the demand probability:

When `Y_t > 0`: `D_t = beta * 1 + (1-beta) * D_{t-1}` and `Z_t = alpha * Y_t + (1-alpha) * Z_{t-1}`
When `Y_t = 0`: `D_t = beta * 0 + (1-beta) * D_{t-1}` and `Z_t` unchanged.

Forecast: `F_t = D_t * Z_t`. TSB naturally produces forecasts that decline toward zero for items with obsolescence risk, since D_t decays when demand stops.

**Demand classification (Syntetos-Boylan framework)**:

Items are classified based on two dimensions:
- Average inter-demand interval (ADI): threshold at 1.32 periods
- Coefficient of variation of demand size (CV^2): threshold at 0.49

| | CV^2 < 0.49 | CV^2 >= 0.49 |
|---|---|---|
| ADI < 1.32 | Smooth | Erratic |
| ADI >= 1.32 | Intermittent | Lumpy |

Smooth items can use standard ETS/ARIMA. Erratic items have variable sizes. Intermittent items have sporadic timing. Lumpy items have both problems and are the most challenging.

**Prediction intervals**: Standard Gaussian intervals do not apply. Bootstrap or empirical methods are used, or parametric approaches assuming negative binomial or Poisson-distributed demand occurrences combined with a size distribution (gamma or log-normal).

## Interpretation

Intermittent-demand runs (Croston / SBA / TSB) emit a two-tier Interpretation block with a distinct Tier 1 shape — NOT the shared forecaster template used by the other six C2 techniques.

**Plain-Language Finding (Tier 1)** - Syntetos-Boylan pattern classification (smooth / intermittent / erratic / lumpy) rendered via plain-language ADI and CV² descriptors (sporadic vs frequent demand periods; high / moderate / low demand-size variability). Flat forecast per period; mean-demand baseline (generic last-value naive is misleading for zero-dominant series); always-on caveat that intermittent forecasts ship without calibrated prediction intervals.

**Technical Interpretation (Tier 2, method-branched)** - method-specific citation-form disclosure: Croston discloses the (z, p) updating rule and upward-bias property; SBA discloses the (1 - alpha/2) bias correction; TSB discloses the (z, d) parameterization and decay-to-zero probability for obsolescence handling. Every method's Tier 2 states which method was selected via the method parameter and names the alternatives.

**Caveats (Tier 3, conditional)**:
- Pattern is smooth but an intermittent method was chosen.
- Last 10 periods all zero but method is not TSB - consider TSB.
- Mean-demand baseline matches or beats the fitted model.
- Prediction intervals are not calibrated (always fires).
