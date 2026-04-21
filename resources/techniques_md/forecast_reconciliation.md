# Forecast Reconciliation

## What It Does

Forecast reconciliation ensures that forecasts across a hierarchical or grouped structure are **coherent** -- they add up correctly. For example, forecasts for individual product lines should sum to the total company forecast, and regional forecasts should aggregate to the national total. Reconciliation adjusts independently generated base forecasts to satisfy these aggregation constraints while minimizing the overall forecast error.

## When to Use It

- You have a hierarchy of time series (e.g., country > region > store, or total > category > SKU)
- Forecasts are generated independently at different levels and do not naturally sum correctly
- You want to leverage information across all levels of the hierarchy to improve accuracy
- Organizational requirements demand that detailed forecasts are consistent with aggregate plans
- You are combining top-down planning with bottom-up operational forecasts

## Key Assumptions

- The hierarchical or grouping structure is known and fixed
- Base forecasts are available for all series at all levels (or at least selected levels)
- The reconciliation method (e.g., MinT) requires an estimate of the base forecast error covariance
- The linear reconciliation framework is appropriate (non-linear relationships are not modeled)
- The aggregation constraints are exact (e.g., sum, not approximate relationships)

## Outputs

- **Reconciled forecasts**: adjusted forecasts that satisfy all aggregation constraints
- **Improved accuracy**: reconciled forecasts typically outperform base forecasts at most levels
- **Coherent prediction intervals** (when available) that respect the hierarchical structure
- **Reconciliation weights**: showing how information flows between levels

## Technical Details

**Notation**: Let `b_t` be the vector of all bottom-level series (the most disaggregated). The full vector of all series (bottom and upper levels) is `y_t = S * b_t`, where `S` is the **summing matrix** that maps bottom-level to all levels. For example, if the total equals the sum of three regions, `S` has a row of ones at the top and an identity block for the bottom.

**Base forecasts**: Let `y_hat` be the vector of independently generated base forecasts for all series (these generally do not satisfy `y_hat = S * b_hat`).

**Reconciliation framework**: Find reconciled forecasts `y_tilde = S * P * y_hat`, where `P` is a matrix that maps the base forecasts back to coherent bottom-level forecasts. The reconciled forecasts automatically satisfy the aggregation constraints because they are constructed via the summing matrix `S`.

**Key methods for choosing P**:

1. **Bottom-Up (BU)**: `P = [0 | I]`, simply using the bottom-level base forecasts. Ignores upper-level information.

2. **Top-Down (TD)**: Allocate the top-level forecast down using historical proportions. `P = [p | 0]` where `p` contains the disaggregation proportions.

3. **OLS reconciliation**: `P = (S'S)^{-1} S'`. Minimizes the squared distance between base and reconciled forecasts, assuming equal variance for all base forecast errors.

4. **WLS (Weighted Least Squares)**: `P = (S'W^{-1}S)^{-1} S'W^{-1}`, where `W` is a diagonal matrix of base forecast error variances. Common choices:
   - **Structural scaling**: `W_ii` proportional to the number of bottom-level series that aggregate into series i.
   - **Variance scaling**: `W_ii = Var(e_i)` estimated from in-sample residuals.

5. **MinT (Minimum Trace)**: `P = (S'W_h^{-1}S)^{-1} S'W_h^{-1}`, where `W_h` is the full covariance matrix of the h-step-ahead base forecast errors. This minimizes the total variance of the reconciled forecast errors and is the optimal linear reconciliation method.

   Estimators for `W_h`:
   - **Sample covariance**: full covariance estimated from base forecast residuals.
   - **Shrinkage estimator**: shrinks the sample covariance toward a structured target to improve conditioning.

**Probabilistic reconciliation**: To reconcile not just point forecasts but full predictive distributions, methods include:
- Bootstrap reconciliation: resample base forecast errors, reconcile each sample, build empirical distributions.
- Gaussian reconciliation: if base forecasts are Gaussian, the reconciled forecasts are also Gaussian with analytically computable mean and covariance.

**Cross-temporal reconciliation**: Extends the framework to simultaneously reconcile across the hierarchy and across temporal aggregation levels (e.g., monthly forecasts must sum to quarterly, which must sum to annual).

## Interpretation

Every Forecast Reconciliation run emits a two-tier plain-language Interpretation block, framed as a post-processing operation rather than a fit technique.

**Plain-Language Finding (Tier 1)** - names the hierarchy shape (top aggregate = sum of N bottom components), the primary reconciliation method (MinT-OLS preferred when the covariance is well-conditioned, bottom-up fallback otherwise), the forecast horizon, and the historical coherence status. The voice leads with "Reconciled N-level hierarchy..." to signal that this is a coherence operation, not a fit.

**Technical Interpretation (Tier 2)** - discloses which reconciliation methods ran, the primary-method convention and any fallback, the base forecaster, and the historical aggregation residual. Explicitly notes that reconciliation projects base forecasts onto the coherent subspace (so the top forecast equals the sum of the bottom forecasts exactly at every step) but cannot correct systematic base-forecast bias — "reconciliation enforces coherence only."

**Caveats (Tier 3, conditional)**:
- Historical incoherence > 5% of top level - input hierarchy is materially inconsistent; investigate data quality before trusting reconciliation.
- MinT-OLS fell back to bottom-up - singular covariance detected; MinT's variance-minimization benefit is lost.
- Base forecaster is 'naive' with horizon > 3 - reconciliation preserves a flat trajectory; consider 'drift' or 'ets' for more informative forecasts.
