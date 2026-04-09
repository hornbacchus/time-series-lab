# Vector Autoregression (VAR)

## What It Does

VAR (Vector Autoregression) models multiple time series simultaneously, where each variable is expressed as a linear function of its own past values and the past values of all other variables in the system. It captures the dynamic interdependencies among a set of time series without requiring prior assumptions about which variables are exogenous and which are endogenous.

## When to Use It

- You have multiple related time series that influence each other (e.g., GDP, inflation, interest rates)
- You want to understand dynamic interactions between variables without imposing structural restrictions
- You need multi-step forecasts for a system of variables
- You want to perform impulse response analysis or forecast error variance decomposition
- Granger causality testing is needed to assess whether one variable helps predict another

## Key Assumptions

- All variables in the system are stationary (or the VAR is estimated in differences)
- The number of lags is sufficient to capture the dynamics but not so large as to overfit
- Residuals are white noise (no remaining autocorrelation) and may be contemporaneously correlated
- The system is stable (all eigenvalues of the companion matrix lie inside the unit circle)
- No important variables are omitted from the system

## Outputs

- **Coefficient matrices** showing how each variable depends on lagged values of all variables
- **Multi-step forecasts** for all variables simultaneously
- **Impulse response functions (IRFs)**: how each variable responds over time to a shock in another
- **Forecast error variance decomposition (FEVD)**: the proportion of forecast uncertainty for each variable attributable to shocks from each other variable
- **Granger causality tests**: whether lagged values of one variable significantly predict another

## Technical Details

**Model specification**: A VAR(p) model for a k-dimensional vector `Y_t = (Y_{1,t}, ..., Y_{k,t})'` is:

`Y_t = c + A_1 Y_{t-1} + A_2 Y_{t-2} + ... + A_p Y_{t-p} + u_t`

where `c` is a k-by-1 vector of constants, `A_i` are k-by-k coefficient matrices, and `u_t ~ N(0, Sigma_u)` is the vector of innovations with covariance matrix `Sigma_u`.

**Estimation**: Each equation can be estimated separately by OLS, which is efficient because all equations have the same regressors. The OLS estimator for each equation is consistent and asymptotically normal. The residual covariance matrix is estimated as `Sigma_hat = (1/T) * sum u_hat_t * u_hat_t'`.

**Lag order selection**: Select p using information criteria applied to the system:
- AIC(p) = log|Sigma_hat(p)| + 2*p*k^2/T
- BIC(p) = log|Sigma_hat(p)| + p*k^2*log(T)/T

AIC tends to overfit; BIC tends to select more parsimonious models.

**Stability condition**: The VAR(p) is stable if all eigenvalues of the k*p by k*p companion matrix have modulus less than 1. The companion form stacks the system into a VAR(1):

`Z_t = C + A * Z_{t-1} + U_t`

where `Z_t = (Y_t', Y_{t-1}', ..., Y_{t-p+1}')'` and `A` is the companion matrix.

**Impulse response functions**: The VAR can be written as an infinite vector MA: `Y_t = mu + sum_{i=0}^{inf} Phi_i u_{t-i}`, where `Phi_i` are the MA coefficient matrices. Element `(j,k)` of `Phi_i` gives the response of variable j at horizon i to a unit shock in variable k. Since innovations may be contemporaneously correlated, structural identification (e.g., Cholesky decomposition of `Sigma_u`) is used to orthogonalize shocks.

**Granger causality**: Variable X Granger-causes variable Y if lagged values of X significantly improve the prediction of Y, conditional on Y's own lags. Tested via an F-test (or Wald test) comparing the unrestricted VAR with a restricted version excluding the lags of X in the Y equation.

**Forecast error variance decomposition**: Decomposes the h-step forecast error variance of each variable into contributions from orthogonalized shocks: `FEVD_j,k(h) = sum_{i=0}^{h-1} (e_j' Phi_i P e_k)^2 / sum_{i=0}^{h-1} e_j' Phi_i Sigma_u Phi_i' e_j`, where `P` is the Cholesky factor of `Sigma_u`.
