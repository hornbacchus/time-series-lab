# Dynamic Factor Model

## What It Does

A Dynamic Factor Model (DFM) reduces a large panel of time series to a small number of unobserved **common factors** that drive co-movement across all the series. Each observed variable is expressed as a linear combination of these factors plus an idiosyncratic component. The factors themselves evolve over time as a VAR process, capturing the shared dynamics in a compact representation.

## When to Use It

- You have a large number of related time series and want to extract the common driving forces
- Dimensionality reduction is needed before forecasting (too many predictors for direct regression)
- You want to build a coincident or leading economic indicator from many series
- Nowcasting with mixed-frequency data (monthly GDP from daily/weekly indicators)
- You want to fill in missing values across a panel of series by leveraging cross-sectional correlations

## Key Assumptions

- A small number of factors explain most of the co-movement in the data
- The relationship between observed variables and factors is linear
- Idiosyncratic components are weakly correlated across series (or uncorrelated in the strict factor model)
- The factors follow a stationary VAR process
- The number of series is large relative to the number of factors

## Outputs

- **Estimated common factors**: the unobserved drivers of co-movement
- **Factor loadings**: how strongly each observed variable relates to each factor
- **Variance decomposition**: what fraction of each variable's variance is explained by common factors vs. idiosyncratic noise
- **Forecasts** based on the factor dynamics
- **Nowcasts** for variables with missing or delayed data releases

## Technical Details

**Model specification**: For `n` observed variables `Y_t = (Y_{1,t}, ..., Y_{n,t})'` and `r` latent factors `F_t = (F_{1,t}, ..., F_{r,t})'`:

Observation equation: `Y_t = Lambda * F_t + e_t`

where `Lambda` is the n-by-r factor loading matrix and `e_t ~ N(0, R)` are idiosyncratic errors.

State equation (factor dynamics): `F_t = A_1 F_{t-1} + ... + A_p F_{t-p} + u_t`

where `u_t ~ N(0, Q)` are factor innovations.

**Estimation approaches**:

1. **Principal Components (static approach)**: Estimate factors as the first r principal components of the standardized data matrix. The loadings are the corresponding eigenvectors scaled by eigenvalues. This is fast and works well for large n. The Bai-Ng information criteria help select r:
   - `IC(r) = log(V(r)) + r * g(n, T)` where `V(r)` is the residual variance and `g(n,T)` is a penalty function.

2. **Maximum Likelihood via EM algorithm**:
   - E-step: Given current parameter estimates, run the Kalman smoother to compute `E[F_t | Y_1, ..., Y_T]` and their covariances.
   - M-step: Update `Lambda`, `R`, `A_i`, and `Q` using the smoothed factor estimates.
   - Iterate until convergence. This approach naturally handles missing data (the Kalman filter simply skips missing observations).

3. **Two-step approach**: Extract factors via principal components, then estimate the factor VAR on the extracted factors. Simpler but less efficient than joint estimation.

**Selecting the number of factors**: Methods include the Bai-Ng information criteria, the ratio of adjacent eigenvalues, or scree plot inspection. The optimal r balances explaining enough of the data variance against parsimony.

**Mixed-frequency and ragged edges**: For nowcasting, DFMs handle data arriving at different frequencies (e.g., monthly and quarterly) and at different publication lags (ragged edges). The state space formulation naturally accommodates this by treating unobserved values as missing data in the Kalman filter.

**Identification**: Factors are identified only up to rotation. Common normalizations include requiring `Lambda' Lambda / n = I_r` (principal components normalization) or imposing a lower-triangular structure on the first r rows of `Lambda`.
