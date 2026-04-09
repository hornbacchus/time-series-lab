# BOCPD (Bayesian Online Change Point Detection)

## What It Does

BOCPD (Bayesian Online Change Point Detection) detects change points in real time as data arrives, computing the **posterior probability of a change point** at each time step. It maintains a probability distribution over the "run length" -- the number of time steps since the last change point -- and updates this distribution with each new observation. This provides a principled, probabilistic approach to online change detection.

## When to Use It

- You need to detect change points in real time (streaming data, monitoring)
- You want probabilistic change point detection with posterior probabilities
- The data arrives sequentially and decisions must be made without future information
- You are monitoring a process for quality control, anomaly detection, or system health
- You prefer a Bayesian framework that naturally handles uncertainty about change locations

## Key Assumptions

- Data within each segment follows a known parametric model (Gaussian, Poisson, etc.)
- Change points occur independently with a known or estimated hazard rate (geometric prior by default)
- The parameters reset to their prior values after each change point
- The prior distributions for segment parameters are conjugate to the likelihood (for computational efficiency)
- Observations are independent within each segment, conditional on the segment parameters

## Outputs

- **Run length posterior**: at each time, the probability distribution over how long the current segment has been running
- **Change point probability**: the probability that a change occurred at each time step
- **Estimated segment parameters**: posterior mean of parameters for the current segment
- **MAP run length**: the most probable run length at each time, indicating the last change point
- **Real-time alerts**: flagging time points where change probability exceeds a threshold

## Technical Details

**Setup**: At each time t, the run length `r_t` indicates how many observations have occurred since the last change point. If `r_t = 0`, a change point just occurred at time t.

**Recursive update** (Adams and MacKay, 2007):

For each new observation `y_t`, update the run length distribution:

1. **Growth probability** (no change, extend current run):
`P(r_t = r_{t-1} + 1, y_{1:t}) = P(r_{t-1}, y_{1:t-1}) * pi_t(y_t | r_{t-1}) * (1 - H(r_{t-1}))`

where `pi_t(y_t | r_{t-1})` is the predictive probability of `y_t` given the current run data, and `H(r)` is the hazard function (probability of a change point given run length r).

2. **Change point probability** (new segment starts):
`P(r_t = 0, y_{1:t}) = sum_{r_{t-1}} P(r_{t-1}, y_{1:t-1}) * pi_t(y_t | r_{t-1}) * H(r_{t-1})`

3. **Normalize**: `P(r_t | y_{1:t}) = P(r_t, y_{1:t}) / P(y_{1:t})`

**Predictive probability**: With conjugate priors, `pi_t(y_t | r_{t-1})` is the posterior predictive distribution given the data in the current run. For a Gaussian model with unknown mean and known variance:

- Prior: `mu ~ N(mu_0, sigma_0^2)`
- After observing `y_{t-r}, ..., y_{t-1}`, the posterior is Gaussian with updated mean and precision.
- The predictive distribution for `y_t` is Student-t (for unknown variance) or Gaussian (for known variance).

**Hazard function**: The simplest choice is a constant hazard `H(r) = 1/lambda`, corresponding to a geometric prior on segment length with expected length lambda. This means change points are equally likely at any time.

**Efficient computation**: Maintain sufficient statistics (sum, sum of squares, count) for each active run length. When a new observation arrives, update all active runs. Prune runs with negligible probability to keep computation bounded.

**Computational cost**: O(T) per time step in the worst case (maintaining T possible run lengths), but pruning keeps the effective cost much lower. With pruning threshold epsilon, runs with `P(r_t) < epsilon` are discarded.

**Extensions**:
- **Unknown hazard rate**: Place a prior on lambda and update it online.
- **Multivariate observations**: Use multivariate conjugate priors (Normal-Wishart).
- **Non-conjugate models**: Use approximate inference (particle filters, variational methods).
- **Gradual changes**: Use models that can capture both abrupt and gradual transitions.

**Comparison with offline methods**: BOCPD processes data sequentially and does not need the full series. PELT requires the full series but can be more accurate because it optimizes a global objective. BOCPD provides probabilities at each step; PELT provides a single best segmentation.
