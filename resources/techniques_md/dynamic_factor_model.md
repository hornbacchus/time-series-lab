## What It Does
A Dynamic Factor Model extracts a small number of latent common factors that drive a panel of many series, where the factors themselves follow their own autoregressive dynamics. It is the time-series counterpart to PCA: instead of a static variance decomposition, the common factor has persistence and can be forecast. For a yield panel, one factor typically captures the dominant common movement. Outputs are the estimated factors, their loadings on each series, and forecasts.

## When to Use It
- You have many correlated series driven by a few unobserved common forces, and you want those forces as a time series with dynamics.
- You want to forecast a common factor, or use it as a conditioning variable.
- You prefer a model-based latent factor over PCA's static components.
- Use it when the factor dynamics matter; use `pca_analysis` for a quick static decomposition without a dynamic model.

## How to Read the Result
The headline is how much variance the common factor explains and which series load most heavily on it. On the Treasury reference, one factor explains 77.1% of the transformed panel variance, with the 10Y loading anchored at 1.00 and the others at 0.63–0.93 — a common curve factor. Note the transform: with the default auto setting the engine ADF-tests each series and differences the non-stationary ones, so on yield levels it works in log-differences. That means the factor captures the common cyclical (change) variation, not the secular level — read it as a factor over yield changes, not yield levels. The loadings are sign-anchored so the largest-magnitude one is positive, giving a "level" orientation.

## Related Techniques
- *(use after)* feed the extracted factor into a `var` or regression as a conditioning series.
- *(alternatives)* `pca_analysis` (static factors, much faster); `var` / `bvar` when you'd rather model all series jointly than compress to factors.

## Technical Detail
Estimation is EM/Kalman maximum likelihood (statsmodels `DynamicFactor`), with the factor count and the AR orders of the factors and idiosyncratic errors set by preset (`DynamicFactor(Y, k_factors=…, factor_order=…, error_order=…).fit()`). A convergence-failure fallback cascade reduces the factor count or AR order rather than failing outright. The transform defaults to auto, which ADF-tests each series and applies log-differencing or differencing where needed (Stock-Watson canonical preprocessing); on already-stationary inputs it can be set to none. Factors are rescaled to unit variance and sign-anchored. This is the slowest technique in the block — roughly 44 seconds on 6,146 observations.
*Reference run:* treasury_yields.csv (2Y/5Y/10Y/30Y, 6,146 obs), 1 factor, factor order 2, transform auto, Balanced — auto-selected log-differencing (all four yields ADF non-stationary), 1 factor explains 77.1% (loadings: 10Y 1.00 anchor, 5Y 0.91, 30Y 0.93, 2Y 0.63).
