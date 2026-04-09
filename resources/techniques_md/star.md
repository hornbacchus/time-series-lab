# STAR Models (Smooth Transition AR)

## What It Does

Smooth Transition Autoregressive (STAR) models generalize the abrupt regime switches of SETAR models by allowing **gradual transitions** between regimes. Instead of jumping between two sets of parameters at a sharp threshold, the model smoothly blends them using a logistic or exponential transition function. This is more realistic for many economic and financial processes where regime changes occur progressively.

## When to Use It

- Your data transitions gradually between different dynamic behaviors rather than switching abruptly
- Business cycle dynamics shift smoothly between expansion and contraction modes
- You want a nonlinear model that nests the linear AR as a special case (for testing)
- SETAR seems too restrictive with its sharp threshold, but you still want interpretable regime-dependent dynamics
- You need to model asymmetric adjustment where the speed of transition varies

## Key Assumptions

- Two regimes with a smooth transition between them (extensions to multiple regimes exist)
- The transition variable is observable (typically a lagged value of the series)
- The transition function is monotonic (LSTAR) or symmetric (ESTAR) and correctly specified
- The model is stationary and ergodic
- Enough data to estimate the transition function parameters (typically 100+ observations)

## Outputs

- **Regime-specific AR coefficients**: parameters for the two extreme regimes
- **Transition function parameters**: the threshold location (c) and smoothness (gamma)
- **Transition function values**: showing how smoothly the model moves between regimes over time
- **Linearity test results**: whether the nonlinear STAR model significantly improves over a linear AR
- **Fitted values and forecasts** with the nonlinear dynamics

## Technical Details

**General STAR model**:

`Y_t = (c_1 + phi_{1,1} Y_{t-1} + ... + phi_{1,p} Y_{t-p})(1 - G(s_t; gamma, c)) + (c_2 + phi_{2,1} Y_{t-1} + ... + phi_{2,p} Y_{t-p}) G(s_t; gamma, c) + e_t`

Or more compactly: `Y_t = x_t' Phi_1 (1 - G_t) + x_t' Phi_2 G_t + e_t`, where `x_t = (1, Y_{t-1}, ..., Y_{t-p})'` and `G_t = G(s_t; gamma, c)` is the transition function with transition variable `s_t` (typically `Y_{t-d}`).

**LSTAR (Logistic STAR)**:
`G(s_t; gamma, c) = 1 / (1 + exp(-gamma (s_t - c)))`, gamma > 0

- When gamma -> 0: G -> 0.5, the model becomes linear (average of both regimes).
- When gamma -> infinity: G approaches a step function (SETAR).
- The transition is asymmetric: different behavior above and below c.

**ESTAR (Exponential STAR)**:
`G(s_t; gamma, c) = 1 - exp(-gamma (s_t - c)^2)`, gamma > 0

- G = 0 when s_t = c (the inner regime).
- G -> 1 as s_t moves away from c in either direction (the outer regime).
- Symmetric around c: useful for modeling mean-reverting deviations.

**Linearity testing** (Luukkonen-Saikkonen-Terasvirta test):

Since gamma = 0 makes the model linear but also makes c unidentified (nuisance parameter problem), a Taylor expansion of G around gamma = 0 is used. The auxiliary regression:

`Y_t = beta_0 x_t + beta_1 x_t s_t + beta_2 x_t s_t^2 + beta_3 x_t s_t^3 + u_t`

Test H0: beta_1 = beta_2 = beta_3 = 0 using an F-test or LM test. Rejection indicates nonlinearity. Sequential testing of the beta terms helps choose between LSTAR and ESTAR.

**Estimation**: Nonlinear least squares (NLS) or MLE. The procedure is:

1. Select the transition variable and delay via linearity tests for each candidate.
2. Obtain starting values: grid search over c (within the range of s_t) and gamma.
3. Estimate all parameters jointly by NLS, minimizing `sum e_t^2`.

**Identification issue**: gamma and c can be poorly identified when gamma is very large (near SETAR) or very small (near linear). Rescaling gamma by the standard deviation of s_t helps: `gamma* = gamma / std(s_t)`.

**Forecasting**: Multi-step forecasts require simulating forward, since `E[G(Y_{t+h-d})]` does not equal `G(E[Y_{t+h-d}])`. Monte Carlo simulation or skeleton (deterministic) forecasts are used.
