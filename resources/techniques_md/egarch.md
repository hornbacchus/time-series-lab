## What It Does
EGARCH (Exponential GARCH, Nelson 1991) models the log of conditional variance as an autoregressive process. Because it works in logs, variance is always positive with no constraints on the parameters, and the leverage effect enters multiplicatively. It typically fits return data better than GARCH or GJR, at the cost of a slightly less transparent persistence measure and simulation-based multi-step forecasts.

## When to Use It
- You want the best-fitting single-regime volatility model and are comparing on AIC (EGARCH often wins).
- Positivity constraints or parameter boundary issues are biting a standard GARCH fit.
- You want leverage modeled in log-variance.
- For a one-step-ahead forecast EGARCH is analytic; if you need long multi-step forecasts and care about speed, note the simulation step below.

## How to Read the Result
The leverage sign is reversed from GJR: in EGARCH a negative γ means negative shocks raise volatility more (same economics as GJR's positive γ, opposite sign). On the SP500 reference, γ=−0.173 and significant — leverage confirmed. Persistence is read off β alone (the log-variance AR coefficient), not α+β: here β=0.972, so volatility is highly persistent. The AIC of 6170.4 is the lowest of the three GARCH-family models on this data, completing a clean story — adding asymmetry (GARCH→GJR→EGARCH) lowers AIC at each step. Don't compare EGARCH's β to a GARCH α+β directly; the persistence definitions differ by construction.

## Related Techniques
- *(use after)* `evt_pot_gpd` and `caviar_quantile_dynamics` for tails and VaR.
- *(alternatives)* `garch`, `gjr_garch` (the family; compare on AIC); `stochastic_volatility` as the latent-vol alternative to the whole GARCH class.

## Technical Detail
`arch_model(returns, mean='Constant', vol='EGARCH', p=1, q=1, o=1, dist='t', rescale=True).fit(disp='off')`. Variance is modeled as `log(sigma2_t)` following an AR process, so persistence is the AR coefficient β. Multi-step forecasts use simulation (1,000 paths) because the Nelson exponential form has no closed-form multi-step recursion (arch's analytic EGARCH supports horizon=1 only); GARCH/GJR use analytic recursion. The Model-Diagnostics persistence row is labeled |β| for EGARCH.
*Reference run:* sp500_returns.csv, Balanced, seed 42 — EGARCH(1,1,1)-t: `α=0.187, γ=−0.173 (sig), β=0.972 (=persistence), ν=5.35`, AIC 6170.4 (best of GARCH/GJR/EGARCH on this data).
