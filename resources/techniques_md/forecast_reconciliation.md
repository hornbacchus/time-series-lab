## What It Does
Forecast reconciliation makes a set of hierarchical or grouped forecasts coherent — so that the forecasts of the parts add up to the forecast of the whole (regional sales summing to national; individual tenors consistent with an aggregate). The MinT (minimum-trace) family does this optimally, adjusting the base forecasts to minimize the reconciled forecast-error variance rather than naively summing or splitting. Outputs are the reconciled forecasts at every level of the hierarchy.

## When to Use It
- You forecast a hierarchy or grouping separately and need the levels to be mutually consistent.
- You want the statistically optimal reconciliation, not just bottom-up summation or top-down splitting.
- You have base forecasts plus a structure describing how the series aggregate.
- Use MinT methods when you have residuals to estimate the error covariance; fall back to bottom-up/top-down when you don't.

## How to Read the Result
The method determines how the base forecasts are combined. The MinT variants estimate the forecast-error covariance and weight accordingly: `mint_shrinkage` (the robust default) shrinks the sample covariance toward a diagonal target. On the reference hierarchy the shrinkage intensity is 0.0588 with a well-conditioned weight matrix (condition number 51.5). When the hierarchy is already perfectly coherent the reconciliation adjustment is near zero, which is the correct behavior — there is nothing to reconcile. If the error-covariance estimate is rank-deficient (common on clean, perfectly-coherent hierarchies), the method automatically falls back down the cascade to a simpler estimator.

## Related Techniques
- *(use after)* any base forecaster whose outputs form a hierarchy — the classical and ML forecasting techniques can supply the base forecasts.
- *(alternatives)* simple bottom-up or top-down reconciliation (also available as methods here) when you lack the residuals for a MinT estimate.

## Technical Detail
The reconciliation maps base forecasts through `G = (S'W⁻¹S)⁻¹S'W⁻¹` for the chosen weight matrix W (numpy/scipy). Methods are the MinT family — ols, wls_variance, mint_shrinkage (Schäfer-Strimmer shrinkage), mint_sample (needs more observations than series) — plus classical bottom_up and top_down. A fallback cascade (mint_sample → mint_shrinkage → wls_variance → ols) handles a rank-deficient W. Two input modes are supported: an automatic two-level construction (the first series is the top of the hierarchy) or an explicit n-level structure when a structure matrix is supplied. A non-negativity option uses NNLS but forfeits MinT optimality where the constraint binds.
*Reference run:* the parity fixture 3e_mint.npz (5 nodes, 4 bottom-level, 200 observations, 3-step horizon), mint_shrinkage, explicit n-level mode, Balanced — shrinkage intensity 0.0588, weight-matrix condition number 51.5, rank 5. The fixture is purpose-built and already coherent, so the reconciliation adjustment is near zero (correct); no natural hierarchical set exists in the sample data.
