## What It Does
CAViaR (Conditional Autoregressive Value-at-Risk, Engle-Manganelli 2004) models the Value-at-Risk quantile path directly, without assuming any return distribution. Instead of fitting a full conditional density and reading off a quantile, it specifies an autoregressive process for the quantile itself and estimates it by minimizing the asymmetric tick (quantile) loss. The result is a dynamic 1-day VaR plus multi-horizon VaR via bootstrap simulation and a full backtest suite.

## When to Use It
- You want a VaR estimate that makes no Gaussian or Student-t assumption — the quantile is modeled directly.
- You care specifically about the tail (1% or 5% VaR) rather than the whole conditional distribution.
- You need formal VaR backtests (Kupiec, Christoffersen, Engle-Manganelli DQ) on the fitted series.
- Choose it over GARCH-based VaR when the innovation distribution is the weak link; choose GARCH or EVT when you need the full density or the far tail beyond the modeled quantile.

## How to Read the Result
The headline is the 1-day VaR and the backtest p-values. On the SP500 reference (5% VaR, symmetric-absolute spec), the 1-day VaR is −1.97%, with 125 violations against 125.6 expected (ratio 0.995) and Kupiec p=0.956 / Christoffersen p=0.925 / DQ p=0.992 — very well calibrated at the 1-day horizon. Critical caveat on multi-horizon VaR: the multi-step recursion can be non-stationary, and on this very data it is — effective persistence is 1.20, the stationarity flag trips to false, and the 22-day VaR explodes to −41.2% versus the sane −1.97% 1-day figure. The engine flags this in the audit and widens the simulation error. Trust the 1-day VaR; treat long-horizon VaR as unreliable whenever the stationarity flag is false — and here it is.

## Related Techniques
- *(use after)* feed the VaR series into a risk report; compare against `evt_pot_gpd` VaR for the extreme tail.
- *(alternatives)* `garch` / `gjr_garch` / `egarch` for parametric VaR (full density); `evt_pot_gpd` for the far tail; `stochastic_volatility` for the latent-vol route.

## Technical Detail
Backend is a scipy minimization of the asymmetric tick loss over the chosen quantile. The specification is selected by the model type: `symmetric_abs` (SAV, default), `asymmetric_slope` (AS), or `igarch` (IG). Multi-horizon VaR (horizons default `[1, 5, 10, 22]`) is produced by Monte-Carlo bootstrap of the fitted residuals; the path count defaults blank to the preset (Fast 500 / Balanced 2,000 / Thorough 10,000, lower-bounded 100). The Engle-Manganelli Adaptive specification is not implemented (only SAV/AS/IG). A graceful-degradation guard widens MC error and flags non-stationarity when effective persistence reaches or exceeds 1.
*Reference run:* sp500_returns.csv, SAV, 5% VaR, Balanced — `β0=−0.089, β1=0.756, β2=−0.444`, quantile loss 0.120, 125/2,512 violations (expected 125.6, ratio 0.995), Kupiec p=0.956 / Christoffersen p=0.925 / DQ p=0.992, 1-day VaR = −1.97%. Multi-horizon is non-stationary on this data (effective persistence 1.20; 22-day VaR −41.2% blow-up) — the 1-day VaR is the headline, the blow-up the honest caveat.
