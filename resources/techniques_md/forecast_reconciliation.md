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

## MinT Family (Follow-up 3e)

Follow-up 3e ships the **full MinT (Minimum Trace) family** from Wickramasuriya, Athanasopoulos, Hyndman (2019), fulfilling the catalog's pre-existing `wls` option declaration and completing the methods roster sketched in the Technical Details section.

### The four variants

All four share the MinT projection formula:

```
y_tilde = S · G · y_hat
G = (S' · W^{-1} · S)^{-1} · S' · W^{-1}
```

Differences lie in the choice of `W` (the residual-covariance weight matrix):

- **`ols`** — `W = I`. No residual-based weighting. Minimizes squared distance between base and reconciled forecasts equally across series. Equivalent to orthogonal projection onto the coherent subspace.
- **`wls_variance`** (alias `wls`) — `W = diag(Var(residuals_i))`. Diagonal weighting by per-series in-sample residual variance. Ignores cross-series correlation.
- **`mint_shrinkage`** (WAH 2019 recommended) — `W = diag(sample covariance) + (1 − lambda) · (off-diagonal of sample covariance)`, where lambda is the Schäfer-Strimmer (2005) optimal shrinkage intensity clamped to `[0, 1]`. Shrinks correlations toward 0 while preserving per-series variances. Optimal in expected squared-error sense.
- **`mint_sample`** — `W = (1/T) · R · R'` (full sample covariance). Requires `T > n_total` for invertibility. Noisy for large `n` relative to training-residual sample size.

### Two operating modes

**Auto 2-level mode** (default, backward-compatible): `S` is constructed internally as a 2-level summing matrix from `ctx.get_all_series()`. Base forecasts and in-sample residuals are computed internally from the chosen `base_forecaster` ∈ `{naive, drift, ets}`. No user-facing API change vs. pre-3e wrapper.

**Explicit n-level mode** (opt-in via `ctx.params["S_matrix"]`): user provides a custom summing matrix for general n-level hierarchies or grouped (non-tree) structures. Optionally also supplies `y_hat_matrix` and `residuals_matrix` to use external base forecasts produced upstream from the user's preferred forecasting method. Matches the `hts::MinT` / `fable::reconcile` / `statsforecast.MinT` API convention.

Tier 2 always names the mode exercised ("Mode: auto 2-level" or "Mode: explicit n-level") so users know what their invocation triggered.

### Schäfer-Strimmer 2005 shrinkage

Per WAH 2019 eq. 8 (citing Schäfer-Strimmer 2005), the optimal shrinkage intensity is:

```
lambda_hat = sum_{i != j} Var(r_ij) / sum_{i != j} r_ij^2
```

where `r_ij` are sample correlations and `Var(r_ij)` is the estimated variance of the sample correlation across time. Clamped to `[0, 1]`. The shrunk covariance preserves diagonal variances and shrinks off-diagonal correlations by factor `(1 − lambda)` toward zero. In practice, typical values fall in `[0.05, 0.95]`; extreme values trigger Tier 3 D3.

### Fallback cascade

If the requested method fails (numerically or due to `T ≤ n_total` for `mint_sample`), the wrapper gracefully advances through the cascade:

- `mint_sample` → `mint_shrinkage` → `wls_variance` → `ols`
- `mint_shrinkage` → `mint_sample` → `wls_variance` → `ols`
- `wls_variance` / `wls` → `ols`
- `ols` — never falls back (W=I is always invertible for S' S non-singular)

The audit field `reconciliation_fallback_reason` records which step in the cascade succeeded (and the reason the primary step failed). Tier 3 D1 `method_fallback_occurred` fires on any fallback with diagnostic disambiguation.

### Nonnegative reconciliation

Opt-in via `ctx.params["nonnegative"] = True`. The wrapper solves the whitened bottom-level NNLS problem via `scipy.optimize.nnls`:

```
min_b || W^{-1/2} (S b - y_hat) ||_2    subject to  b >= 0
```

then returns `y_tilde = S b`. Since `S` is binary, `b >= 0` implies all aggregate levels are non-negative too. Forfeits the MinT minimum-trace optimality when the constraint binds. Tier 3 D6 fires when at least one bottom value was pinned to zero.

### Backward compatibility

- Default `method` remains `"ols"` (not changed to `"mint_shrinkage"`). Existing users without explicit method specification get identical behavior.
- When OLS is defaulted (not explicit), Tier 2 emits a D23 upgrade recommendation suggesting `method='mint_shrinkage'` per WAH 2019. Users who explicitly chose `method='ols'` do NOT receive this nag.
- The `wls` catalog option is preserved as an alias for `wls_variance`. Both register.
- Existing methods (`bottom_up`, `top_down`, pre-existing `ols`) are strictly additive — new MinT variants (`wls_variance`, `mint_shrinkage`, `mint_sample`) augment without replacing.

## Interpretation

Every Forecast Reconciliation run emits a two-tier plain-language Interpretation block, framed as a post-processing operation rather than a fit technique.

**Plain-Language Finding (Tier 1)** - names the hierarchy shape (top aggregate = sum of N bottom components), the primary reconciliation method (MinT-OLS preferred when the covariance is well-conditioned, bottom-up fallback otherwise), the forecast horizon, and the historical coherence status. The voice leads with "Reconciled N-level hierarchy..." to signal that this is a coherence operation, not a fit.

**Technical Interpretation (Tier 2)** - discloses which reconciliation methods ran, the primary-method convention and any fallback, the base forecaster, and the historical aggregation residual. Explicitly notes that reconciliation projects base forecasts onto the coherent subspace (so the top forecast equals the sum of the bottom forecasts exactly at every step) but cannot correct systematic base-forecast bias — "reconciliation enforces coherence only."

**Caveats (Tier 3, conditional)**:
- Historical incoherence > 5% of top level - input hierarchy is materially inconsistent; investigate data quality before trusting reconciliation.
- MinT-OLS fell back to bottom-up - singular covariance detected; MinT's variance-minimization benefit is lost. (Re-gated per Follow-up 3e D26 — suppressed when the broader D1 fires.)
- Base forecaster is 'naive' with horizon > 3 - reconciliation preserves a flat trajectory; consider 'drift' or 'ets' for more informative forecasts.

**Follow-up 3e triggers (fire only when a MinT family variant is the primary method)**:
- **D1 method_fallback_occurred** - any fallback in the MinT cascade. Text disambiguates cause (insufficient T, numerical failure, cascade exhausted).
- **D2 w_matrix_ill_conditioned** - condition number > 1e12. Consider mint_shrinkage to regularize, or a longer training window.
- **D3 shrinkage_extreme** - Schäfer-Strimmer lambda > 0.95 (degenerate to wls_variance) or < 0.05 (could use mint_sample).
- **D4 reconciliation_change_material** - top-level reconciled forecast differs materially from base top forecast; reflects the magnitude of the coherence correction.
- **D5 residuals_insufficient_for_method** - requested mint_sample but T <= n_total; gracefully fell back to mint_shrinkage.
- **D6 nonnegative_constraint_binding** - NNLS pinned at least one bottom value to zero; MinT optimality forfeited but aggregates remain non-negative.
