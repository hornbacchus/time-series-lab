# Denton / Chow-Lin Temporal Disaggregation

## What It Does

Temporal disaggregation converts **low-frequency data into high-frequency estimates** -- for example, converting quarterly GDP into monthly estimates, or annual data into quarterly estimates. It uses related high-frequency indicator series as guides, ensuring that the disaggregated series is consistent with the observed low-frequency totals (or averages) while following the pattern of the indicator. This is essential for mixed-frequency analysis where different variables are available at different time intervals.

## When to Use It

- You need monthly estimates of a variable only available quarterly (e.g., GDP, investment)
- You want to align series measured at different frequencies for joint analysis
- High-frequency indicator series are available that track the target variable's movements
- You need to temporally distribute annual benchmarks using monthly or quarterly patterns
- Mixed-frequency modeling or nowcasting requires all variables at the same frequency

## Key Assumptions

- A high-frequency indicator series is available that is correlated with the target variable
- The relationship between the indicator and the target is linear and stable
- The low-frequency values represent exact sums (or averages) of the high-frequency values (temporal aggregation constraint)
- The residuals from the regression relationship follow a specified autocorrelation structure
- The indicator series is available for the entire period of interest

## Outputs

- **Disaggregated high-frequency series**: the target variable estimated at the higher frequency
- **Consistency check**: the high-frequency estimates aggregate back exactly to the observed low-frequency values
- **Regression coefficients**: the relationship between the target and the indicator
- **Residual analysis**: diagnostics for the assumed error structure
- **Smoothness of the disaggregated series**: how well it follows the indicator pattern

## Technical Details

**The temporal aggregation constraint**: If `y_t` (t = 1, ..., n) is the unobserved high-frequency series and `Y_s` (s = 1, ..., N) is the observed low-frequency series, the constraint is:

`Y_s = sum_{t in period s} y_t` (for flow variables like GDP)
`Y_s = y_{last(s)}` (for stock variables like end-of-period levels)
`Y_s = (1/m) sum_{t in period s} y_t` (for averages)

where m is the number of high-frequency periods per low-frequency period (e.g., 3 for quarterly to monthly).

In matrix form: `Y = C y`, where C is the N-by-n aggregation matrix.

**Chow-Lin method** (regression-based):

Model: `y = X beta + u`, where X is the n-by-k matrix of high-frequency indicator values and `u` is a residual with covariance `V`.

The Chow-Lin estimate minimizes the GLS criterion subject to the temporal constraint:

`y_hat = X beta_hat + V C' (C V C')^{-1} (Y - C X beta_hat)`

where `beta_hat = (X' V^{-1} X)^{-1} X' V^{-1} y` is the GLS estimate (which itself depends on the unknown y, requiring iteration).

**Residual specifications**:
- **AR(1)**: `u_t = rho u_{t-1} + e_t`. The most common choice. The autocorrelation parameter rho is estimated by MLE or by iterating the GLS procedure.
- **Random walk**: `u_t = u_{t-1} + e_t`. Produces smoother disaggregated series. Equivalent to the Fernandez method.

**Denton method** (smoothness-based):

The Denton method does not use regression. Instead, it finds the high-frequency series that:
1. Satisfies the temporal aggregation constraint: `C y = Y`
2. Minimizes a smoothness criterion: `min_y (y - z)' D' D (y - z)`

where z is the preliminary high-frequency indicator (or zero if unavailable) and D is a differencing matrix:
- **Denton original**: `D = I` (minimize deviations from the indicator)
- **Denton first difference**: `D` is the first-difference operator (minimize changes in the adjustment factor)
- **Denton proportional**: minimize `sum ((y_t/z_t) - (y_{t-1}/z_{t-1}))^2` (proportional Denton, the most common variant). This keeps the ratio between the target and indicator as smooth as possible.

**Solution**: The constrained optimization has a closed-form solution:

`y_hat = z + D_inv C' (C D_inv C')^{-1} (Y - C z)` (simplified)

where `D_inv` involves the inverse of `D' D` appropriately handled.

**Without an indicator**: If no indicator is available, both methods can still disaggregate using only the smoothness constraint, distributing the low-frequency total smoothly across the high-frequency periods. This is common for historical data where indicators are unavailable.

**Estimation of rho (Chow-Lin)**: Since the low-frequency residuals `U_s = Y_s - C X beta` are observed, rho can be estimated from the aggregated autocovariance structure using MLE:

`log L(rho) = -N/2 log|C V(rho) C'| - 1/2 U' (C V(rho) C')^{-1} U`

Maximize over rho in (-1, 1).

**Practical guidance**: Chow-Lin is preferred when a good indicator is available (it uses the regression relationship). Denton proportional is preferred when you want to preserve the movement pattern of the indicator without imposing a statistical relationship.
