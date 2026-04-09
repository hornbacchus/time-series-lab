# Johansen Cointegration Test

## What It Does

The Johansen cointegration test determines whether a set of non-stationary time series share **long-run equilibrium relationships**. While individual series may each wander randomly (unit roots), cointegration means some linear combinations of them are stationary -- they move together over time. The test identifies how many such independent equilibrium relationships exist (the cointegrating rank) and estimates the cointegrating vectors.

## When to Use It

- You have two or more I(1) (non-stationary, first-difference-stationary) time series
- Economic theory suggests the variables should maintain a long-run relationship
- You need to determine whether to model the system as a VAR in differences or a VECM
- You want to estimate multiple cointegrating relationships simultaneously (unlike the Engle-Granger two-step method, which handles only one)
- You are building a VECM and need to specify the cointegrating rank

## Key Assumptions

- All variables are integrated of the same order, typically I(1)
- The VAR model underlying the test is correctly specified (appropriate lag length)
- There are no structural breaks in the cointegrating relationships
- The sample size is large enough for the asymptotic critical values to be reliable (at least 50 observations per variable)
- The deterministic specification (intercept/trend in the cointegrating equation) is correctly chosen

## Outputs

- **Cointegrating rank**: the number of independent long-run equilibrium relationships (0 to k-1 for k variables)
- **Trace test statistics and critical values** for each possible rank
- **Maximum eigenvalue test statistics and critical values** for sequential testing
- **Estimated cointegrating vectors** (beta matrix)
- **Adjustment coefficients** (alpha matrix) showing the speed of adjustment
- **Eigenvalues** of the characteristic equation

## Technical Details

The Johansen procedure is based on the VECM representation of a VAR(p) system (see the VECM technique for the derivation). The central object is the long-run matrix `Pi = alpha * beta'`, where the rank of `Pi` equals the number of cointegrating relationships `r`.

**Estimation procedure**:

1. Specify the VAR lag order `p` (using AIC/BIC on the VAR in levels).
2. Compute the concentrated VECM by regressing out the short-run dynamics (see VECM technical details for the residual construction `R_0t` and `R_1t`).
3. Solve `|lambda S_{11} - S_{10} S_{00}^{-1} S_{01}| = 0` for eigenvalues `lambda_1 >= lambda_2 >= ... >= lambda_k >= 0`.

**Trace test**: Tests `H0: rank(Pi) <= r` vs. `H1: rank(Pi) > r`:

`trace(r) = -T * sum_{i=r+1}^{k} log(1 - lambda_hat_i)`

Start with r=0. If rejected, test r=1, and so on until failure to reject. The first non-rejected r is the estimated cointegrating rank.

**Maximum eigenvalue test**: Tests `H0: rank(Pi) = r` vs. `H1: rank(Pi) = r+1`:

`lambda_max(r, r+1) = -T * log(1 - lambda_hat_{r+1})`

This focuses on whether adding one more cointegrating vector is significant.

**Five deterministic specifications (Cases 1-5)**:
1. No intercept or trend in the VAR or cointegrating equation
2. Intercept restricted to the cointegrating equation only
3. Unrestricted intercept in the VAR, no trend (most common)
4. Intercept unrestricted, trend restricted to the cointegrating equation
5. Unrestricted intercept and trend in the VAR

The choice affects the critical values and the interpretation of the cointegrating vectors. Case 3 (unrestricted constant) is the default for most economic applications.

**Critical values**: The distributions are non-standard and depend on `k - r` (the number of common stochastic trends), the deterministic specification, and the sample size. Tabulated values from Osterwald-Lenum or computed by response surface regressions are used. Finite-sample corrections (Reimers or Bartlett corrections) can improve small-sample performance.

**Normalization**: The cointegrating vectors `beta` are identified only up to a non-singular transformation. Normalization (e.g., setting the coefficient of one variable to 1 in each vector) is needed for interpretation. The loading matrix `alpha` adjusts accordingly.
