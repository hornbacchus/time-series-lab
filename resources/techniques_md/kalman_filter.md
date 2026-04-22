# Kalman Filter (Direct Access)

## What It Does

The Kalman filter computes online, one-step-ahead state estimates for a linear Gaussian state-space model. At each period t, the filter combines the model's transition dynamics with the newly observed data point to update the state distribution — conditioning only on past and current observations (y_{1:t}). This is the natural tool for real-time inference, streaming applications, and any setting where future observations are not yet available.

This wrapper offers four named templates (local_level, local_linear_trend, seasonal, ar1) plus a custom path that accepts a user-supplied (Z, T, R, H, Q) specification. Together these cover most practical linear Gaussian setups without requiring MLE on user matrices.

Use `kalman_smoother` instead when you need retrospective estimates conditioned on the full sample y_{1:T}.

## When to Use It

- Real-time or streaming inference — the filtered state is the best estimate at time t using only past and current observations.
- Early-period state trajectory matters — the filter is the valid representation before smoothing folds in later observations.
- Diagnostic purposes — filtered innovations (one-step-ahead residuals) are the right input to model-checking tests.
- Custom matrices are already estimated elsewhere (another tool, theoretical derivation) and you want to run inference at those fixed matrices.
- You want a different set of filtered-state outputs than structural_ts provides.

## Key Assumptions

- The state dynamics and observation equation are linear and Gaussian.
- Variance components (or the user-supplied H, Q matrices) are stable over the sample.
- Diffuse initialization is acceptable for early-period states (or you supply known initial state and covariance).
- For the template path: MLE-estimated variances are identifiable from the data.
- For the custom path: the user's Z, T, R, H, Q matrices faithfully represent the data-generating process.

## Outputs

- **Forecast** — horizon-step forecast with configurable CI coverage.
- **Filtered State** — period-by-period filtered state mean and SE for each state dimension.
- **Model Summary** — wrapper kind, template, dimensions, likelihood, AIC, BIC, variance components, RMSE.
- **Residual Diagnostics** — Jarque-Bera, Ljung-Box lag-10, Durbin-Watson, RMSE, MAE.

## Technical Details

**State-space equations (general form):**

- Observation equation: `y_t = Z_t s_t + ε_t`, `ε_t ~ N(0, H_t)`
- State equation: `s_t = T_t s_{t-1} + R_t η_t`, `η_t ~ N(0, Q_t)`

This wrapper currently assumes time-invariant Z, T, R, H, Q.

**Template path.** One of `{local_level, local_linear_trend, seasonal, ar1}` routed through `statsmodels.tsa.statespace.structural.UnobservedComponents`. Variance components are estimated by MLE; filtered states are extracted via the `.filtered_state` attribute on the results object.

**Custom path.** The user supplies concrete Z, T, R, H, Q arrays (plus initial_state and initial_covariance under known initialization). The wrapper wires these into a thin `_TSLStateSpaceModel(MLEModel)` subclass with zero free parameters — the filter evaluates at the fixed matrices and extracts states directly. This mode is intended for users who have already determined their state-space matrices through prior estimation (in another tool or via theoretical reasoning) and want TSL to perform the state inference. For matrix estimation, use the template path.

**Initialization.**

- `diffuse` (default) — statsmodels default; large prior variance on the initial state. Early-period filtered states depend on the init until the Kalman gain has propagated several observations.
- `known` — user-supplied `initial_state` and `initial_covariance`. Required on the custom path.
- `approximate_diffuse` — alias for diffuse.

**Shape validation (custom path).** The wrapper validates all matrices at entry:
- Z: (obs_dim, state_dim)
- T: (state_dim, state_dim)
- R: (state_dim, state_shock_dim)
- H: (obs_dim, obs_dim)
- Q: (state_shock_dim, state_shock_dim)
- initial_state: (state_dim,)
- initial_covariance: (state_dim, state_dim)

Informative `ValueError` on mismatch.

## Interpretation

kalman_filter runs emit a two-tier Interpretation block.

**Plain-Language Finding (Tier 1)** — names the wrapper kind (Kalman filter), series, state dimension, state labels, template name (or "custom linear-Gaussian model with user-supplied matrices"), observation count, initialization choice, the final filtered state value and SE at period T, and the horizon forecast trend clause with baseline comparison.

**Technical Interpretation (Tier 2)** — opens with the filter vs smoother disclosure (online y_{1:t} vs retrospective y_{1:T}), then renders either the state equations (template path) or the custom-matrix disclosure with shape summary and "no free parameters" framing. Discloses initialization choice, MLE variance components (template path), log-likelihood / AIC / BIC, and residual diagnostics. Closes with forecast-mechanism sentence.

**Caveats (Tier 3, conditional):**
- **Convergence warning** (template path) — MLE optimizer did not fully converge.
- **Residual non-normality** (Jarque-Bera p < 0.05) — Gaussian assumption may not hold.
- **Residual autocorrelation** (Ljung-Box lag-10 p < 0.05) — model leaves structure in residuals.
- **RMSE exceeds baseline** — state-space model does not beat naive on this series.
- **Custom path no-MLE disclosure** — reported log-likelihood reflects user's matrix choices; AIC/BIC degenerate (k=0 free params) and reported for parity only.
- **Low signal-to-noise ratio** (q < 0.05 on local_level / local_linear_trend) — level estimate heavily smoothed toward prior.
- **Early-period initialization sensitivity** (diffuse init + n < 50 + state_dim ≤ 3) — first few filtered states dominated by initial-covariance prior; use kalman_smoother for retrospective analysis on short series.
