# CAViaR / Quantile Dynamics

## What It Does

CAViaR (Conditional Autoregressive Value at Risk) directly models the **dynamics of a specific quantile** of the return distribution over time, without first specifying the entire conditional distribution. Instead of estimating volatility and then deriving VaR from a distributional assumption, CAViaR models the quantile itself as an autoregressive process, allowing VaR to adapt to changing market conditions while remaining agnostic about the full distribution shape.

## When to Use It

- You want Value-at-Risk estimates that adapt to changing market conditions without specifying a full distributional model
- Standard GARCH + distributional assumption VaR models are mis-specified or too restrictive
- You are interested in the dynamics of specific quantiles (e.g., 1% or 5% loss quantile)
- You want a semiparametric approach that avoids tail distribution assumptions
- Risk management requires robust, direct quantile estimation

## Key Assumptions

- The conditional quantile follows an autoregressive process
- The chosen CAViaR specification captures the essential dynamics of the quantile
- The quantile regression framework is valid (no crossing of quantile estimates at different levels, in practice)
- Enough data is available for reliable quantile regression estimation (hundreds of observations minimum)
- The quantile dynamics are stable enough to be extrapolated forward

## Outputs

- **Time-varying VaR series**: the estimated quantile at each time point
- **CAViaR parameters**: coefficients governing the autoregressive quantile dynamics
- **VaR exceedance analysis**: comparing observed violations with the target quantile level
- **Backtesting results**: Kupiec, Christoffersen, and DQ tests on VaR violations
- **One-step-ahead VaR forecasts**

## Technical Details

**Quantile regression foundation**: For quantile level tau (e.g., 0.05 for 5% VaR), the conditional quantile `q_t(tau)` satisfies `P(Y_t <= q_t(tau) | I_{t-1}) = tau`.

**CAViaR specifications** (Engle and Manganelli, 2004):

1. **Symmetric Absolute Value (SAV)**:
`q_t(tau) = beta_0 + beta_1 q_{t-1}(tau) + beta_2 |Y_{t-1}|`

2. **Asymmetric Slope (AS)**:
`q_t(tau) = beta_0 + beta_1 q_{t-1}(tau) + beta_2 max(Y_{t-1}, 0) + beta_3 min(Y_{t-1}, 0)`

This allows positive and negative returns to have different effects on the quantile.

3. **Indirect GARCH(1,1)**:
`q_t(tau) = -sqrt(beta_0 + beta_1 q_{t-1}(tau)^2 + beta_2 Y_{t-1}^2)`

Motivated by the GARCH(1,1) variance equation, applied to the quantile.

4. **Adaptive**:
`q_t(tau) = q_{t-1}(tau) + beta_1 {[1 + exp(G(Y_{t-1} - q_{t-1}(tau)))]^{-1} - tau}`

where G is a smooth function. The quantile adapts based on whether the previous observation exceeded the current quantile.

**Estimation**: Parameters are estimated by minimizing the quantile regression loss (check function):

`min_beta sum_{t=1}^{T} rho_tau(Y_t - q_t(tau; beta))`

where `rho_tau(u) = u * (tau - I(u < 0)) = tau * max(u, 0) + (1-tau) * max(-u, 0)`.

This is a non-differentiable, nonlinear optimization problem. The standard approach uses:
- Grid search over starting values for beta_1 (the persistence parameter)
- Numerical optimization (simplex or differential evolution) to minimize the quantile loss
- Multiple random restarts to avoid local optima

**Dynamic Quantile (DQ) test**: The key backtesting diagnostic. Define `Hit_t = I(Y_t < q_t(tau)) - tau`. The DQ test regresses `Hit_t` on lagged hits and lagged VaR, testing whether all coefficients are zero. Significant coefficients indicate the VaR model fails to adapt properly.

**Prediction intervals**: The quantile regression framework does not directly produce confidence intervals for the VaR estimate. Bootstrap methods or asymptotic standard errors from the quantile regression theory are used.

**Comparison with GARCH-based VaR**: CAViaR directly models the object of interest (the quantile) rather than going through a volatility model plus distributional assumption. This avoids the risk of distributional misspecification. However, it provides VaR for only one quantile level at a time and does not produce a full conditional distribution.

**Expected Shortfall extension**: ES cannot be directly estimated by quantile regression. Two-step approaches first estimate VaR via CAViaR, then estimate ES conditional on VaR exceedance. Joint quantile-ES regression methods (Patton, Ziegel, Chen, 2019) estimate both simultaneously.

## Interpretation

Every CAViaR run emits a two-tier plain-language Interpretation block with a distinct quantile-forecast-with-backtest Tier 1 shape.

**Plain-Language Finding (Tier 1)** - names the CAViaR specification variant (SAV / AS / IG with full names Symmetric Absolute Value / Asymmetric Slope / Indirect GARCH), the VaR confidence level (integer-when-whole per Convention A), the quantile level θ, realized vs expected violation counts with the exceedance ratio, a coverage descriptor (too conservative / too aggressive / well-calibrated), and two of the three backtest p-values: Kupiec unconditional coverage first, then Engle-Manganelli Dynamic Quantile (Convention D backtest ordering per D8). The Christoffersen conditional coverage test is flagged separately in Tier 3.

**Technical Interpretation (Tier 2)** - explicitly states the distribution-free framing (Convention C): the quantile loss (check / pinball function) makes no distributional assumption about returns. Discloses the Nelder-Mead optimization with random restarts, the specification-specific quantile-dynamics equation, parameter values with coefficient labels, minimized quantile loss, and all three backtests with verdicts (Kupiec, Christoffersen conditional coverage via first-order Markov chain, and Engle-Manganelli Dynamic Quantile joint test). Suggests refitting with Asymmetric Slope if leverage effects are of interest.

**Caveats (Tier 3, conditional)**:
- Kupiec rejects - realized exceedance rate differs materially from nominal; quantile level miscalibrated.
- Christoffersen conditional-coverage rejects - violations are clustered; dynamic response too slow. Consider AS variant for leverage-effect responses.
- DQ joint test rejects - neither well-calibrated nor adequate; consider AS, IG, or more optimization restarts (Thorough preset).

