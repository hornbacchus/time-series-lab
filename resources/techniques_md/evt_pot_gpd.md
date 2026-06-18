## What It Does
Extreme Value Theory via Peaks-Over-Threshold fits a Generalized Pareto Distribution to the observations that exceed a high threshold, then reads off VaR and Expected Shortfall at extreme quantiles (99%, 99.9%). It models the tail directly rather than extrapolating from a fitted full distribution — the right tool when the question is specifically about rare, large moves. The shape parameter ξ characterizes how heavy the tail is.

## When to Use It
- You need VaR/ES at extreme quantiles (99%, 99.9%) where the body of the distribution is uninformative.
- You want to characterize tail heaviness directly (the ξ shape parameter).
- You're stress-testing or sizing for rare events rather than typical-day risk.
- Use it alongside GARCH or CAViaR: those model the conditional center and near-tail; EVT models the far tail.

## How to Read the Result
Read the tail direction first — this is the critical point. The default fits the upper (gains) tail, so on a returns series EVT analyzes gains, not losses. For market risk you almost always want the loss tail: feed a negated (loss-positive) series, or read the lower-tail output. On the SP500 reference the difference is material — the default upper tail gives ξ=0.441 and VaR99=2.78%, while the loss tail gives ξ=0.263 and VaR99=−3.37%. The shape ξ is the headline: ξ>0 is a heavy (Fréchet) tail, and the larger it is the fatter the tail. Expected Shortfall is infinite when ξ≥1. The KS goodness-of-fit p-value indicates whether the GPD fits the exceedances (high p = good). Bootstrap confidence intervals for ξ are biased near ξ=0.5 and ξ=1, so treat them as informational when |ξ|>0.4.

## Related Techniques
- *(use after)* combine the EVT tail with a `garch` or `egarch` conditional-vol estimate for conditional-EVT risk; report alongside `caviar_quantile_dynamics` VaR.
- *(alternatives)* `caviar_quantile_dynamics` for a distribution-free near-tail VaR; the GARCH family for the conditional center.

## Technical Detail
Backend is `scipy.stats.genpareto`: exceedances above the threshold are fit with `genpareto.fit(exceedances, floc=0)`, then VaR/ES are computed at the requested levels. The threshold is set by the threshold quantile (default 0.975). Minimum 50 observations and at least 10 exceedances (30+ for reliability). Only KS goodness-of-fit is reported — the Anderson-Darling test was dropped (scipy cannot run it for this distribution); older notes referencing AD are stale. Optional Ferro-Segers declustering (default off) handles volatility-clustered exceedances via the extremal index. By default this analyzes the upper/right tail of the series as given; for loss analysis, feed a negated series.
*Reference run:* sp500_returns.csv, threshold quantile 0.975, Balanced — default upper tail (gains): threshold 1.995% (97.5pct), 63 exceedances, `ξ=0.441` (heavy/Fréchet), VaR99=2.78%, ES99=4.63%, KS p=0.852. Loss tail (via negation): threshold −2.40%, 63 exceedances, `ξ=0.263`, VaR99=−3.37%, ES99=−5.00%, KS p=0.869. The upper figures are the literal dialog default; the lower figures are the risk-relevant ones.
