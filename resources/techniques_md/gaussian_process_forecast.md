# Gaussian Process Forecast

## What It Does

A Gaussian Process (GP) is a **Bayesian nonparametric model** that defines a probability distribution over functions. For time series forecasting, it uses past values as inputs and produces not just point forecasts but also **calibrated uncertainty estimates** at each forecast horizon. The GP naturally provides wider prediction intervals where data is sparse or the pattern is uncertain, and narrower intervals where the model is confident.

## When to Use It

- You need principled, well-calibrated prediction intervals (not just point forecasts)
- The relationship between past and future values may be nonlinear and unknown
- Your series is relatively short (under 1000 observations; GPs scale cubically with data size)
- You want to encode prior beliefs about smoothness, periodicity, or other properties via the kernel
- You need a model that quantifies both epistemic uncertainty (model uncertainty) and aleatoric uncertainty (noise)

## Key Assumptions

- The time series can be modeled as a noisy realization of a smooth underlying function
- The kernel (covariance function) captures the relevant structure (smoothness, periodicity, trends)
- The noise is independent and identically distributed (typically Gaussian)
- The data is not too large for exact GP inference (or sparse approximations are used)
- The input features (lags, time index) are informative for predicting the target

## Outputs

- **Point forecasts**: the posterior mean at each forecast horizon
- **Prediction intervals**: the posterior standard deviation gives calibrated uncertainty bands
- **Optimized kernel hyperparameters**: length scales, signal variance, noise variance, periodicity
- **Marginal likelihood**: for model comparison and kernel selection
- **Posterior function samples**: possible future trajectories drawn from the posterior

## Technical Details

**GP definition**: A Gaussian Process is a collection of random variables, any finite subset of which has a joint Gaussian distribution. A GP is fully specified by:
- Mean function: `m(x) = E[f(x)]` (often set to zero after centering the data)
- Covariance (kernel) function: `k(x, x') = Cov(f(x), f(x'))`

**Model**: `y_i = f(x_i) + epsilon_i`, where `f ~ GP(m, k)` and `epsilon_i ~ N(0, sigma_n^2)`.

**Posterior prediction**: Given training data `X, y` and test inputs `X*`:

Posterior mean: `f* = K(X*, X) [K(X, X) + sigma_n^2 I]^{-1} y`
Posterior variance: `Var(f*) = K(X*, X*) - K(X*, X) [K(X, X) + sigma_n^2 I]^{-1} K(X, X*)`

where `K(A, B)` is the kernel matrix with entries `k(a_i, b_j)`.

**Common kernels for time series**:

- **RBF (Squared Exponential)**: `k(x, x') = sigma_f^2 exp(-||x-x'||^2 / (2l^2))`. Assumes smooth, infinitely differentiable functions. Length scale l controls how quickly correlation decays with distance.

- **Matern**: `k(x, x') = sigma_f^2 * (2^{1-nu} / Gamma(nu)) * (sqrt(2nu) r/l)^nu K_nu(sqrt(2nu) r/l)`, where r = ||x-x'||. The parameter nu controls smoothness: nu=1/2 gives the exponential kernel (rough), nu=3/2 is once differentiable, nu=inf recovers the RBF.

- **Periodic kernel**: `k(x, x') = sigma_f^2 exp(-2 sin^2(pi|x-x'|/p) / l^2)`, where p is the period. Captures repeating patterns.

- **Composite kernels**: Sum or multiply kernels to capture different structures. For example: `k = k_RBF + k_periodic + k_noise` models a smooth trend plus periodic component plus noise.

**Hyperparameter optimization**: Maximize the log marginal likelihood:

`log p(y | X, theta) = -1/2 y' K_y^{-1} y - 1/2 log|K_y| - n/2 log(2pi)`

where `K_y = K(X, X) + sigma_n^2 I` and theta collects all kernel hyperparameters. Optimization uses gradient-based methods (L-BFGS) with multiple random restarts to avoid local optima.

**Computational cost**: Exact GP inference requires O(n^3) for the matrix inversion and O(n^2) storage. For large datasets, sparse GP approximations (inducing points) reduce cost to O(n * m^2) where m << n is the number of inducing points.

**Time series application**: Inputs X can be the time index directly (for smooth interpolation/extrapolation) or lag features (for AR-type prediction). When using the time index, kernel composition directly encodes trend, periodicity, and noise. When using lags, the GP acts as a nonlinear autoregression with Bayesian uncertainty.

**Advantages over other nonlinear methods**: GPs provide full posterior distributions with well-calibrated uncertainty, automatic complexity control via the marginal likelihood, and interpretable kernel structure. The main limitation is scalability -- for series longer than about 1000 points, sparse approximations or alternative methods are needed.
