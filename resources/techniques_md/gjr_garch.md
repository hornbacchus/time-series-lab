# GJR-GARCH Model

## What It Does

The GJR-GARCH (Glosten-Jagannathan-Runkle GARCH) model extends standard GARCH by capturing the **leverage effect** -- the empirical observation that negative returns (bad news) tend to increase volatility more than positive returns (good news) of the same magnitude. It adds an asymmetry term that gives extra weight to negative shocks, making it the most widely used asymmetric volatility model.

## When to Use It

- Financial return data shows that negative shocks increase volatility more than positive shocks
- You want to model the leverage effect in equity markets
- Standard GARCH residuals show asymmetry (negative standardized residuals are larger in magnitude during high-volatility periods)
- You are computing risk measures (VaR, ES) that need to account for downside volatility amplification
- You need a simple extension of GARCH that captures asymmetric volatility response

## Key Assumptions

- The same general assumptions as GARCH (correctly specified mean model, stationarity)
- The asymmetric response to shocks is captured by a single leverage parameter
- The leverage effect is constant over time
- The asymmetry is driven by the sign of the shock, not its magnitude alone
- The innovation distribution accounts for remaining non-normality

## Outputs

- **Conditional variance series** with asymmetric volatility responses
- **GARCH parameters**: omega, alpha (symmetric ARCH), gamma (leverage/asymmetry), beta (persistence)
- **Leverage effect magnitude**: how much extra volatility a negative shock produces
- **News impact curve**: showing the asymmetric response of volatility to positive vs. negative shocks
- **Standardized residuals** and volatility forecasts

## Technical Details

**GJR-GARCH(1,1) model**:

Mean equation: `Y_t = mu + e_t`, where `e_t = sigma_t * z_t`

Variance equation:
`sigma_t^2 = omega + alpha e_{t-1}^2 + gamma e_{t-1}^2 I(e_{t-1} < 0) + beta sigma_{t-1}^2`

where `I(e_{t-1} < 0)` is an indicator function equal to 1 when the previous shock is negative and 0 otherwise.

**Interpretation**:
- After a positive shock: `sigma_t^2 = omega + alpha e_{t-1}^2 + beta sigma_{t-1}^2`
- After a negative shock: `sigma_t^2 = omega + (alpha + gamma) e_{t-1}^2 + beta sigma_{t-1}^2`

So `gamma > 0` means negative shocks have a larger impact on volatility (leverage effect). The total impact of a negative shock is `alpha + gamma`, while a positive shock contributes only `alpha`.

**Constraints**:
- `omega > 0`
- `alpha >= 0`
- `alpha + gamma >= 0` (so that negative shocks do not reduce variance)
- `beta >= 0`
- `alpha + gamma/2 + beta < 1` (stationarity condition, assuming symmetric innovation distribution)

**Unconditional variance**: `E[sigma^2] = omega / (1 - alpha - gamma/2 - beta)`, where the `gamma/2` term arises because `E[I(e_t < 0)] = 0.5` for symmetric distributions.

**Persistence**: `alpha + gamma/2 + beta` determines how quickly volatility shocks decay.

**News Impact Curve (NIC)**: Plots `sigma_t^2` as a function of `e_{t-1}` holding `sigma_{t-1}^2` at its unconditional value:
- For `e_{t-1} >= 0`: NIC = `omega + alpha e_{t-1}^2 + beta sigma^2` (flatter slope)
- For `e_{t-1} < 0`: NIC = `omega + (alpha + gamma) e_{t-1}^2 + beta sigma^2` (steeper slope)

This produces a V-shaped curve that is steeper on the left (negative shocks) when gamma > 0.

**Estimation**: MLE as in standard GARCH, with the log-likelihood augmented for the chosen innovation distribution. The indicator function `I(e_{t-1} < 0)` makes the likelihood non-smooth, but standard numerical optimizers handle this well.

**Relationship to other asymmetric models**:
- **TGARCH (Threshold GARCH)**: Models the conditional standard deviation (not variance) with an asymmetry term. Different parameterization but similar idea.
- **EGARCH**: Uses log-variance, which avoids positivity constraints but has different asymmetry mechanics.
- When `gamma = 0`, GJR-GARCH reduces to standard GARCH.

**Testing for leverage effect**: Test `H0: gamma = 0` using a t-test or likelihood ratio test. The Engle-Ng sign bias test provides a pre-estimation diagnostic by regressing squared residuals from a GARCH fit on an indicator for negative residuals.
