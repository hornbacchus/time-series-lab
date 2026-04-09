# CUSUM / Page-Hinkley Test

## What It Does

CUSUM (Cumulative Sum) and the Page-Hinkley test are sequential monitoring procedures that detect **shifts in the mean** (or other parameters) of a process. They accumulate evidence of deviation from a target value over time, triggering an alarm when the cumulative sum exceeds a threshold. These are foundational methods in statistical process control, designed for continuous monitoring of production quality, system performance, or any process where small persistent shifts need to be detected quickly.

## When to Use It

- You are monitoring a process in real time and need to detect when the mean shifts
- Small but persistent changes need to be caught quickly (unlike Shewhart charts which detect large shifts)
- Quality control applications in manufacturing, healthcare, or service delivery
- You need a method with well-understood average run length (ARL) properties
- You want a cumulative approach that accumulates evidence over multiple observations

## Key Assumptions

- Observations are independent and identically distributed within each segment
- The in-control (target) distribution is known, typically Gaussian with known mean and variance
- The shift to be detected has a known direction (upward or downward) or both are monitored
- The process parameters do not drift slowly (CUSUM is designed for step changes)
- The threshold and reference value are chosen to balance detection speed and false alarm rate

## Outputs

- **CUSUM statistic over time**: the running cumulative sum showing evidence accumulation
- **Alarm time**: when the statistic exceeds the threshold, indicating a detected change
- **Estimated change point**: working backward from the alarm to find when the shift began
- **Average Run Length (ARL)**: expected time to detection for a given shift size
- **CUSUM chart**: visual display of the cumulative sum with decision boundaries

## Technical Details

**One-sided CUSUM** (for detecting an upward shift):

`C_t^+ = max(0, C_{t-1}^+ + (y_t - mu_0) - k)`

where `mu_0` is the target (in-control) mean, `k` is the reference value (allowance), and `C_0^+ = 0`. An alarm is raised when `C_t^+ > h`, where h is the decision threshold.

**Two-sided CUSUM** (for detecting shifts in either direction):

`C_t^+ = max(0, C_{t-1}^+ + (y_t - mu_0) - k)` (upper CUSUM)
`C_t^- = max(0, C_{t-1}^- - (y_t - mu_0) - k)` (lower CUSUM)

Alarm when either `C_t^+ > h` or `C_t^- > h`.

**Parameter selection**:
- **Reference value k**: Set to `delta/2` where `delta` is the shift size (in standard deviations) you want to detect most efficiently. For detecting a 1-sigma shift, k = 0.5.
- **Threshold h**: Determines the false alarm rate. Larger h means fewer false alarms but slower detection. Chosen to achieve a desired in-control ARL (e.g., ARL_0 = 500).

**Average Run Length (ARL)**: The expected number of observations before an alarm:
- **In-control ARL (ARL_0)**: Average time to a false alarm when no shift has occurred. Should be large (e.g., 370 or 500).
- **Out-of-control ARL (ARL_1)**: Average time to detect a shift of size delta. Should be small.

Siegmund's approximation for ARL of one-sided CUSUM:
`ARL_0 approx exp(2*Delta*h + 1.166) / (2*Delta^2)` where `Delta = delta / sigma - k / sigma`.

**Page-Hinkley test**: A variant that uses a different stopping rule:

`m_t = sum_{i=1}^{t} (y_i - mu_0 - delta/2)`
`M_t = max_{1<=j<=t} m_j`
`PH_t = M_t - m_t`

Alarm when `PH_t > lambda` (threshold). This is equivalent to the CUSUM but accumulates from the maximum rather than resetting at zero.

**Change point estimation**: When the CUSUM triggers at time T, the change point is estimated as the last time the CUSUM was at or near zero: `tau_hat = max{t < T : C_t = 0}`.

**Standardization**: For non-unit-variance data, standardize by dividing by sigma: use `(y_t - mu_0)/sigma` instead of `y_t - mu_0`, and express k and h in standard deviation units.

**Extensions**:
- **Weighted CUSUM**: Different weights for different observations.
- **CUSUM for variance**: Monitor `(y_t - mu_0)^2` instead of `y_t - mu_0`.
- **Multivariate CUSUM**: Use the Mahalanobis distance or directional CUSUMs.
- **Self-starting CUSUM**: Estimate mu_0 and sigma from the data during an initial learning period.
