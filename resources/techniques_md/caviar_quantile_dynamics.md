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
- **One-step-ahead VaR forecast** q_{T+1|T} as a first-class audit field (Follow-up 3a)
- **Multi-Horizon VaR Forecasts table** at user-specified horizons (default 1 / 5 / 10 / 22 periods) with MC standard errors and 90% bands (Follow-up 3a)

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

### Multi-horizon VaR forecasts (Follow-up 3a)

Prior to Follow-up 3a, the wrapper emitted only the in-sample quantile path and backtests — no explicit forecasts. 3a adds two capabilities:

1. **1-step-ahead VaR q_{T+1|T}** as a first-class audit field, computed by applying the CAViaR recursion one step past the last observation.

2. **Multi-horizon VaR forecasts** at user-specified horizons via **Monte Carlo bootstrap simulation**. Default horizons `[1, 5, 10, 22]` correspond to 1-day / 1-week / 2-week / 1-month at daily frequency; override via the `horizons` parameter.

**Algorithm.** At each simulation path, the wrapper:

1. Starts at the last observed state (q_T, y_T).
2. For h = 1..H_max, computes q_{T+h} via the CAViaR recursion, then simulates y_{T+h} = q_{T+h} + r where r is bootstrap-resampled from the in-sample raw residuals r_t = y_t − q_t (preserves the empirical CDF; Christoffersen 2012).
3. Records y_{T+h}.

The θ-quantile of simulated y values at each horizon is the multi-horizon VaR. The 5th / 95th percentiles provide the 90% band (shown as "5% Lower" / "95% Upper" in the Multi-Horizon VaR Forecasts table).

**Preset-gated simulation path count:**
- Fast: 500 paths (fast but noisier tail estimates)
- Balanced: 2000 paths (balance cost/precision)
- Thorough: 10000 paths (precise tail estimates)

MC standard error at each horizon is computed via sub-sample bootstrap of the quantile estimator (B = 50 sub-samples of size √N). MC SE scales as 1/√N across presets, so Thorough's SE is ~1/√5 ≈ 0.45× Balanced's.

**Three methodological caveats (disclosed in Tier 2 and via Tier 3 triggers):**

- **(a) MC noise at deep tails (D1 trigger).** For θ = 0.01 with N = 500 paths, the 1%-quantile is estimated from 5 extremes; MC standard error is substantial. D1 fires when MC SE at the longest horizon exceeds 10% of the quantile estimate. Rerun on Thorough preset to reduce noise.

- **(b) Bootstrap independence assumption (D2 trigger).** Resampling r_t iid assumes they're exchangeable. If Ljung-Box on r_t rejects at 5%, the simulation is miscalibrated. D2 fires on LB p < 0.05. Consider fitting a richer CAViaR variant (SAV → AS → IG) or block bootstrap (backlog).

- **(c) Multi-horizon stationarity (D3 trigger).** Simple |β₁| < 1 is **not sufficient** for bootstrap stability. When the left-tail VaR is far from zero, `|y| ≈ |q|` feeds back into the recursion, giving an effective persistence:
  - SAV: β₁ + |β₂|
  - AS:  β₁ + max(|β₂|, |β₃|)
  - IG:  β₁ + β₂ (variance stationarity)

  D3 fires when this effective persistence ≥ 1. The bound is a conservative worst-case; AS in particular can stay empirically bounded under sign-asymmetric residual dynamics even when D3 fires — inspect the MC Std Error column to diagnose.

## Interpretation

Every CAViaR run emits a two-tier plain-language Interpretation block with a distinct quantile-forecast-with-backtest Tier 1 shape.

**Plain-Language Finding (Tier 1)** - names the CAViaR specification variant (SAV / AS / IG with full names Symmetric Absolute Value / Asymmetric Slope / Indirect GARCH), the VaR confidence level (integer-when-whole per Convention A), the quantile level θ, realized vs expected violation counts with the exceedance ratio, a coverage descriptor (too conservative / too aggressive / well-calibrated), and two of the three backtest p-values: Kupiec unconditional coverage first, then Engle-Manganelli Dynamic Quantile (Convention D backtest ordering per D8). The Christoffersen conditional coverage test is flagged separately in Tier 3.

**Technical Interpretation (Tier 2)** - explicitly states the distribution-free framing (Convention C): the quantile loss (check / pinball function) makes no distributional assumption about returns. Discloses the Nelder-Mead optimization with random restarts, the specification-specific quantile-dynamics equation, parameter values with coefficient labels, minimized quantile loss, and all three backtests with verdicts (Kupiec, Christoffersen conditional coverage via first-order Markov chain, and Engle-Manganelli Dynamic Quantile joint test). Suggests refitting with Asymmetric Slope if leverage effects are of interest.

**Caveats (Tier 3, conditional)**:
- Kupiec rejects - realized exceedance rate differs materially from nominal; quantile level miscalibrated.
- Christoffersen conditional-coverage rejects - violations are clustered; dynamic response too slow. Consider AS variant for leverage-effect responses.
- DQ joint test rejects - neither well-calibrated nor adequate; consider AS, IG, or more optimization restarts (Thorough preset).
- **D1 multi-horizon MC noise** (Follow-up 3a) - MC SE at the longest horizon exceeds 10% of the quantile estimate; rerun Thorough preset for more paths.
- **D2 residual autocorrelation** (Follow-up 3a) - in-sample residuals have Ljung-Box p < 0.05; bootstrap iid assumption violated. Try a richer CAViaR variant.
- **D3 stationarity violation** (Follow-up 3a) - effective persistence ≥ 1 (per-spec formula). Multi-horizon values may be unreliable. Conservative worst-case bound; AS can stay empirically bounded even when D3 fires — inspect MC Std Error to diagnose.

