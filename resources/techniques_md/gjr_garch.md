## What It Does
GJR-GARCH (Glosten-Jagannathan-Runkle) extends GARCH with a leverage term that lets negative shocks raise volatility more than positive shocks of the same size — the asymmetry observed in most equity and credit return series, where bad news drives bigger volatility spikes than good news. It adds one parameter (γ) that switches on only for negative shocks.

## When to Use It
- Your return series shows the leverage effect: down-moves are followed by more volatility than up-moves (typical for equities, credit, risk assets).
- You want to test whether asymmetry is statistically present — a significant γ is the evidence.
- You need a volatility or VaR model that doesn't understate risk after selloffs.
- Prefer it over plain GARCH whenever leverage is plausible; prefer EGARCH if you want guaranteed-positive variance without parameter constraints or a multiplicative (log-variance) structure.

## How to Read the Result
The new term is γ (the leverage coefficient). On the SP500 reference, γ=0.255 and is significant — negative shocks add materially to next-day variance — while the symmetric ARCH term α=0.0096 is not significant, meaning the volatility response is almost entirely asymmetric. Persistence here is α + β + 0.5·γ ≈ 0.982. The AIC of 6188.7 beats plain GARCH (6259.1) on the same data, confirming the asymmetry earns its parameter. A positive, significant γ is the leverage signature; if γ is near zero or insignificant, plain GARCH is adequate.

## Related Techniques
- *(use after)* `evt_pot_gpd` and `caviar_quantile_dynamics` for tail and VaR estimation; backtest VaR built from the fitted vol.
- *(alternatives)* `garch` (no leverage); `egarch` (leverage in log-variance, no positivity constraints, often the best fit); `stochastic_volatility` for the latent-vol route.

## Technical Detail
`arch_model(returns, mean='Constant', vol='GARCH', p=1, o=1, q=1, dist='t', rescale=True).fit(disp='off')` (GJR is `vol='GARCH'` with `o=1`). The leverage term multiplies an indicator for negative shocks; `γ>0` means negative shocks raise volatility more. Persistence is reported as α + β + 0.5·γ. Multi-step forecasts are analytic.
*Reference run:* sp500_returns.csv, Balanced, seed 42 — GJR-GARCH(1,1,1)-t: `α=0.0096 (ns), γ=0.255 (sig), β=0.845, ν=5.23`, persistence 0.982, AIC 6188.7 (beats plain GARCH 6259.1).
