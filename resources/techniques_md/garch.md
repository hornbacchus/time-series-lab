## What It Does
GARCH models how a return series' volatility clusters and changes over time. It captures the stylized fact that big moves cluster — a turbulent day is more likely to be followed by another turbulent day — by letting today's conditional variance depend on yesterday's squared shock and yesterday's variance. The output is a fitted volatility path, a multi-day variance forecast, and persistence and fat-tail diagnostics. The shipped default uses Student-t innovations, so it accommodates the fat tails real return series exhibit rather than assuming normal shocks.

## When to Use It
- You need a conditional-volatility estimate or short-horizon variance forecast for a single return series (rates, FX, equity, spreads).
- You want to quantify volatility persistence — how long a shock keeps volatility elevated.
- You're building VaR or risk inputs and want a model-based vol rather than a rolling-window standard deviation.
- Use plain GARCH when you don't need to model leverage; if negative shocks raise vol more than positive ones, step up to GJR or EGARCH.

## How to Read the Result
The key numbers are the ARCH coefficient (α — reaction to the latest shock), the GARCH coefficient (β — persistence of past variance), and their sum (α+β = total persistence; close to 1 means shocks are long-lived). On the SP500 reference, α=0.168 and β=0.831 give persistence 0.9992 — volatility shocks decay very slowly, typical for daily equity returns. The estimated degrees-of-freedom (ν≈5) confirms genuinely fat tails; a ν this low means a normal-innovation model would understate tail risk. AIC and BIC let you compare against GJR/EGARCH on the same data — lower is better. The fitted conditional vol (avg ≈0.995%/day here) and the multi-day forecast (1.12→1.20% over 10 days) are the directly usable outputs.

## Related Techniques
- *(use after)* `evt_pot_gpd` for the extreme tail beyond what GARCH's parametric innovations capture; `caviar_quantile_dynamics` for a distribution-free VaR that sidesteps the innovation assumption.
- *(alternatives)* `gjr_garch` and `egarch` add leverage and usually fit return data better; `stochastic_volatility` treats volatility as a latent random process; `har_rv` if you have realized-variance inputs.

## Technical Detail
Backend is the `arch` library: `arch_model(returns, mean='Constant', vol='GARCH', p=1, q=1, o=0, dist='t', rescale=True).fit(disp='off')`. The series is the return series directly (the dialog assumes a constant mean, appropriate for returns). On a fit failure the engine falls back to GARCH(1,1) with normal innovations and warns. Persistence is reported as α+β. Multi-step variance forecasts use the analytic GARCH recursion. The mean model and rescale flag are fixed internally and not exposed.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), preset Balanced, seed 42 — GARCH(1,1)-t: `ω=0.0201, α=0.168, β=0.831, ν=5.03`, persistence `α+β=0.9992`, AIC 6259.1 / BIC 6288.2, average conditional vol 0.995%/day, 10-day vol forecast 1.12→1.20%.
