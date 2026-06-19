## What It Does
Principal Component Analysis reduces a set of correlated series to a smaller number of orthogonal components ranked by how much variance each explains. For a yield curve it recovers the classic level / slope / curvature decomposition: a handful of components capture nearly all the co-movement across maturities. The output is the components, their loadings (how each input series maps onto each component), and the share of total variance each explains.

## When to Use It
- You have several correlated series (a yield curve, a set of spreads, a factor panel) and want the few underlying drivers.
- You want the level/slope/curvature structure of a curve, or to compress many series before feeding a smaller system into a VAR or regression.
- You're checking how many independent dimensions actually move the data.
- Use PCA for a static variance decomposition; use `dynamic_factor_model` when you want latent factors with their own time-series dynamics.

## How to Read the Result
Read the variance-explained shares first. On the 2Y/5Y/10Y/30Y Treasury reference, PC1 explains 88.3% with all-positive loadings (0.89–0.98) — the level factor, a parallel shift of the curve. PC2 explains 11.3% with loadings running from 2Y −0.45 to 30Y +0.44 — the slope factor, steepening versus flattening. Cumulatively the first two components capture 99.6%, so the curve is effectively two-dimensional. The Kaiser rule (keep components with eigenvalue greater than 1) recommends 1 component here. Loadings give each component its economic interpretation; the variance shares tell you how many to keep.

## Related Techniques
- *(use after)* `var`, `bvar`, or `vecm` on the retained components to model their joint dynamics; `dynamic_factor_model` for a dynamic version of the same dimensionality reduction.
- *(alternatives)* `dynamic_factor_model` (latent factors with AR dynamics); `vecm` / `johansen_cointegration` when the question is long-run equilibrium rather than variance structure.

## Technical Detail
Eigendecomposition (`numpy.linalg.eigh`) of the covariance matrix of the standardized series. Standardization (center and scale) is on by default and is appropriate — the Kaiser eigenvalue-greater-than-1 criterion is only meaningful on standardized data, and unscaled PCA would let the highest-variance series dominate. An optional varimax rotation aids interpretability. The number of components defaults blank to all available (`min(observations, series)`). Only PC1's sign is anchored (its largest-magnitude loading is forced positive); PC2 and beyond keep their raw orientation, so a loading's sign is meaningful only relative to the others within a component.
*Reference run:* treasury_yields.csv (2Y/5Y/10Y/30Y, 6,146 daily obs), standardized, preset Balanced — PC1 88.3% (level; loadings 0.89–0.98), PC2 11.3% (slope; 2Y −0.45 → 30Y +0.44), cumulative 99.6%, Kaiser rule selects 1 component.
