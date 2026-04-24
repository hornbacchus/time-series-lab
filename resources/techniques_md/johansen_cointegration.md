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

## Finite-Sample Correction (Reimers 1992, opt-in)

The wrapper's default path uses statsmodels's asymptotic MacKinnon (1996) critical-value tables (via `statsmodels.tsa.coint_tables`). Asymptotic critical values are known to over-reject the no-cointegration null on small samples — at T < 100 the nominal 5% rejection rate can run to 10–20% in truth, systematically overstating cointegration evidence.

Set `finite_sample_correction=True` to apply the **Reimers (1992) modified likelihood-ratio correction** — a Bartlett-type factor widely used in practice (R `urca::ca.jo(..., small_sample=TRUE)`, Stata `vecrank`):

```
B(T, n, p, d) = (T - n*p - d) / T
Q_corrected = B * Q_asymptotic
```

where `T` is the effective sample size, `n` is the VAR dimension, `p` is the VECM lag order (`k_ar_diff`), and `d ∈ {0, 1, 2}` is the number of deterministic regressors implied by `det_order ∈ {-1, 0, 1}`. The same factor applies to both trace and maximum-eigenvalue statistics. Corrected statistics are compared against the same statsmodels critical values; the Bartlett-on-statistic approach is arithmetically equivalent to applying MHM 1999 response-surface CVs to uncorrected statistics at the decision level.

When the correction is applied, the wrapper emits a dedicated **Finite-Sample Correction (Reimers 1992)** output table showing per-rank uncorrected statistic, Bartlett factor, corrected statistic, critical value, and decision side-by-side for both tests. Audit fields expose `bartlett_factor`, `correction_pct_reduction`, `trace_rank_corrected`, `max_eig_rank_corrected`, and `correction_impact_material` (True when the correction flips rank inference). Four Tier 3 triggers cover rank-flipping corrections (D1), material reductions without flip (D2, >5%), very small samples T < 50 (D3, residual distortion possible), and runtime-error graceful fallback (D4).

Johansen (2002) provides refined higher-order terms for this correction that are not implemented here. The Reimers form captures the leading-order correction and matches the industry-standard R and Stata implementations. Reinsel-Ahn (1988) and Cheung-Lai (1993) are alternative finite-sample corrections not implemented in this wrapper.

Default `False` preserves backward compatibility — existing users get the uncorrected asymptotic inference unchanged. The legacy small-sample honest-disclosure trigger (C5 D8) is re-gated to fire only on the opt-out path with updated text pointing at `finite_sample_correction=True` as the actionable option.

## Interpretation

Every Johansen cointegration run emits a two-tier plain-language Interpretation block with a rank-centric Tier 1 shape.

**Plain-Language Finding (Tier 1)** - leads with the trace-test rank decision ("trace test selects rank r"), the trace statistic at the decision boundary vs the critical value at the chosen significance level, whether the max-eigenvalue test agrees, and a rank-implication actionable clause: rank 0 → differenced-VAR; 1 <= r < k-1 → VECM with r long-run equilibrium relationships; r >= k-1 → levels-VAR may be appropriate.

**Technical Interpretation (Tier 2)** - discloses the VAR lag order, deterministic-component specification (det_order), trace and max-eigenvalue agreement, eigenvalues, and the first cointegrating vector (when r >= 1) aligned with the variable names. Honestly discloses the MacKinnon-Haug-Michelis asymptotic critical values limitation: "on samples below ~100 observations these tend to over-reject the no-cointegration null," with a positive acknowledgment when the sample is comfortably large.

**Caveats (Tier 3, conditional)**:
- Trace and max-eigenvalue tests select different ranks - borderline case; trace-test decision is cited for robustness.
- Sample size n < 100 with `finite_sample_correction=False` - MacKinnon asymptotic CVs over-reject; trigger text points at `finite_sample_correction=True` as the actionable opt-in. Suppressed when the user has opted in.
- Rank >= k-1 - series may all be stationary; verify with per-series ADF / KPSS / PP triage before committing to a VECM.

**Follow-up 3d triggers (fire only when `finite_sample_correction=True`)**:
- Correction flips rank inference - the corrected rank differs from the uncorrected rank for either test. The asymptotic test over-rejects; the corrected rank is the reliable estimate for downstream VECM / VAR specification decisions.
- Correction material (>5%) but no rank flip - the Bartlett factor reduces statistics materially, but rank inference is stable under correction. Small-sample size distortion would have been notable; the corrected rank is the reliable estimate.
- Sample T < 50 - very small sample; Bartlett is asymptotic in T and residual size distortion is plausible. Consider bootstrap-based rank inference (Cavaliere-Rahbek-Taylor 2012) for more reliable estimates.
- Runtime error during correction - graceful fallback to uncorrected asymptotic inference with disclosure of the exception cause.

