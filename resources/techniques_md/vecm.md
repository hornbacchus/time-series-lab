# Vector Error Correction Model (VECM)

## What It Does

VECM (Vector Error Correction Model) extends the VAR framework for systems of non-stationary time series that share long-run equilibrium relationships (cointegration). While a VAR in differences would lose information about these long-run relationships, the VECM preserves them by including error correction terms that pull the variables back toward their equilibrium when they deviate.

## When to Use It

- Multiple time series are individually non-stationary (I(1)) but move together in the long run
- Economic theory suggests a long-run equilibrium between variables (e.g., prices and wages, exchange rates and price levels)
- The Johansen test has identified one or more cointegrating relationships
- You want both short-term dynamics and long-run equilibrium behavior in a single model
- Forecasting non-stationary systems where differencing would discard useful long-run information

## Key Assumptions

- All variables are integrated of the same order, typically I(1)
- There exists at least one cointegrating relationship (otherwise, use a VAR in differences)
- The number of cointegrating vectors is correctly specified
- The error correction mechanism is linear and symmetric
- No structural breaks in the cointegrating relationship

## Outputs

- **Cointegrating vectors**: the long-run equilibrium relationships between variables
- **Adjustment (loading) coefficients**: how quickly each variable adjusts back to equilibrium
- **Short-run dynamics**: coefficients on lagged differences showing transient effects
- **Forecasts** that respect the long-run equilibrium
- **Impulse response functions** and variance decompositions

## Technical Details

**From VAR to VECM**: Starting from a VAR(p) in levels `Y_t = A_1 Y_{t-1} + ... + A_p Y_{t-p} + u_t`, the VECM representation is:

`Delta Y_t = Pi * Y_{t-1} + Gamma_1 * Delta Y_{t-1} + ... + Gamma_{p-1} * Delta Y_{t-p+1} + u_t`

where:
- `Pi = A_1 + A_2 + ... + A_p - I_k` is the long-run impact matrix
- `Gamma_i = -(A_{i+1} + A_{i+2} + ... + A_p)` capture short-run dynamics

**Cointegration and rank of Pi**: The key insight is the rank of the matrix `Pi`:
- If rank(Pi) = 0: no cointegration, use VAR in differences.
- If rank(Pi) = k (full rank): variables are stationary, use VAR in levels.
- If rank(Pi) = r where 0 < r < k: there are r cointegrating relationships.

When rank(Pi) = r, we can decompose: `Pi = alpha * beta'`, where:
- `beta` is a k-by-r matrix whose columns are the cointegrating vectors (long-run equilibrium relationships)
- `alpha` is a k-by-r matrix of adjustment (loading) coefficients

The term `beta' Y_{t-1}` measures the deviation from the r equilibria, and `alpha` determines how each variable responds to those deviations.

**Estimation (Johansen's method)**:

1. Regress `Delta Y_t` on `Delta Y_{t-1}, ..., Delta Y_{t-p+1}` and collect residuals `R_0t`.
2. Regress `Y_{t-1}` on `Delta Y_{t-1}, ..., Delta Y_{t-p+1}` and collect residuals `R_1t`.
3. Form the sample covariance matrices `S_{ij} = (1/T) sum R_{it} R_{jt}'`.
4. Solve the generalized eigenvalue problem `|lambda S_{11} - S_{10} S_{00}^{-1} S_{01}| = 0` to get ordered eigenvalues `lambda_1 >= ... >= lambda_k`.
5. The eigenvectors associated with the r largest eigenvalues form `beta_hat`.
6. `alpha_hat = S_{01} beta_hat`.

**Testing the cointegrating rank**: The trace test statistic is `trace(r) = -T * sum_{i=r+1}^{k} log(1 - lambda_i)`, tested against critical values. The maximum eigenvalue test uses `lambda_max(r) = -T * log(1 - lambda_{r+1})`.

**Forecasting**: VECM forecasts are generated recursively, and the error correction term keeps forecasts from diverging from the long-run equilibrium. This makes VECM forecasts especially valuable at longer horizons where the equilibrium relationship dominates.
