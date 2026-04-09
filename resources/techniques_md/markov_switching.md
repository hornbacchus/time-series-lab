# Markov Switching Model

## What It Does

A Markov switching model allows the parameters of a time series model to change depending on an unobserved **regime** or state. The transitions between regimes follow a Markov chain, meaning the probability of being in a given regime depends only on the previous regime. This captures structural changes in the data such as business cycle expansions and recessions, bull and bear markets, or shifts between high and low volatility periods.

## When to Use It

- Your data appears to switch between distinct behavioral patterns (e.g., growth vs. contraction)
- You want to model business cycles with different mean growth rates across regimes
- Financial returns exhibit periods of high and low volatility
- The data shows occasional abrupt shifts in level, trend, or variance
- You want to estimate the probability of being in each regime at each point in time

## Key Assumptions

- The number of regimes is known and fixed (usually 2 or 3)
- Regime transitions follow a first-order Markov chain (history beyond the previous state does not matter)
- Within each regime, the model parameters are constant
- The model specification (e.g., AR, regression) is the same across regimes (only parameter values change)
- The regimes represent genuinely distinct states, not gradual transitions

## Outputs

- **Regime-specific parameters**: separate intercepts, coefficients, and/or variances for each regime
- **Smoothed regime probabilities**: the probability of being in each regime at each time point, using all data
- **Filtered regime probabilities**: real-time regime probabilities using data up to each time point
- **Transition probability matrix**: the probability of switching from one regime to another
- **Expected regime durations**: the average time spent in each regime before switching

## Technical Details

**Model specification**: For a Markov switching autoregression with k regimes and an AR(p) process:

`Y_t = c(S_t) + phi_1(S_t) Y_{t-1} + ... + phi_p(S_t) Y_{t-p} + sigma(S_t) e_t`

where `S_t in {1, 2, ..., k}` is the unobserved regime at time t and `e_t ~ N(0, 1)`.

**Transition probabilities**: `P(S_t = j | S_{t-1} = i) = p_{ij}`, collected in the k-by-k transition matrix P where rows sum to 1.

**Expected duration**: The expected duration of regime i is `1 / (1 - p_{ii})`.

**Hamilton filter** (forward recursion for filtered probabilities):

1. **Prediction**: `P(S_t = j | Y_{t-1}, ..., Y_1) = sum_i P(S_t = j | S_{t-1} = i) * P(S_{t-1} = i | Y_{t-1}, ..., Y_1)`

2. **Likelihood for each regime**: `f(Y_t | S_t = j, Y_{t-1}, ...) = N(Y_t; mu_j, sigma_j^2)`, where `mu_j` is the conditional mean under regime j.

3. **Update**: `P(S_t = j | Y_t, ..., Y_1) = f(Y_t | S_t = j) * P(S_t = j | Y_{t-1}) / f(Y_t | Y_{t-1})`, where the denominator is the mixture likelihood `f(Y_t | Y_{t-1}) = sum_j f(Y_t | S_t = j) * P(S_t = j | Y_{t-1})`.

**Kim smoother** (backward recursion for smoothed probabilities):

`P(S_t = i | Y_T, ..., Y_1) = P(S_t = i | Y_t, ..., Y_1) * sum_j [p_{ij} * P(S_{t+1} = j | Y_T) / P(S_{t+1} = j | Y_t)]`

**Estimation**: Parameters (regime-specific coefficients and transition probabilities) are estimated via MLE using the EM algorithm:

- **E-step**: Run the Hamilton filter and Kim smoother to compute smoothed regime probabilities and joint probabilities `P(S_t = j, S_{t-1} = i | Y_T)`.
- **M-step**: Update transition probabilities: `p_hat_{ij} = sum_t P(S_t = j, S_{t-1} = i | Y_T) / sum_t P(S_{t-1} = i | Y_T)`. Update regime-specific parameters using weighted regressions with smoothed probabilities as weights.

**Log-likelihood**: `log L = sum_t log f(Y_t | Y_{t-1})`, summing the log of the mixture likelihood at each step. The number of regimes is selected by BIC or likelihood ratio tests (with non-standard distributions due to unidentified parameters under the null).
