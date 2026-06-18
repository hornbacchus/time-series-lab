## What It Does
HAR-CJ (Andersen-Bollerslev-Diebold 2007) extends the HAR model by splitting realized variance into a continuous component and a jump component, then forecasting each through its own daily/weekly/monthly cascade. A Barndorff-Nielsen-Shephard test identifies which days contain statistically significant jumps. Separating smooth volatility from discrete jumps usually improves volatility forecasts and isolates jump risk explicitly.

## When to Use It
- You have realized variance and bipower variation and want to separate continuous volatility from jumps.
- You want to quantify jump frequency and jump persistence distinctly from continuous-vol persistence.
- You're building a jump-aware volatility forecast.
- Use it when bipower variation is available; if you only have a single RV series, use HAR-RV instead.

## How to Read the Result
First the jump test: on the reference fixture, 54 of 1,500 days (3.6%) are flagged as significant jumps (BNS z-threshold 2.326, max z 15.8) — a typical jump rate for daily equity data. Then two sets of persistence: continuous persistence 0.825 (smooth volatility carries forward strongly) versus jump persistence 0.197 (jumps are far less persistent — they don't cluster the way continuous vol does). The continuous-cascade slopes (β_cd=0.472, β_cw=0.267, β_cm=0.085) and a significant jump-weekly term (β_jw=0.289) show where forecasting power sits. R²=0.334. The economic story — continuous vol persistent, jumps transient — is the standard ABD finding and the reason for the decomposition.

## Related Techniques
- *(use after)* report jump days alongside event analysis; compare the jump-aware forecast to plain HAR-RV.
- *(alternatives)* `har_rv` when only RV is available; the GARCH family or `stochastic_volatility` when working from returns rather than realized measures.

## Technical Detail
Backend is numpy OLS plus the BNS jump test. Inputs are 2–3 series: position 1 realized variance (RV), position 2 bipower variation (BV), position 3 optional tripower quarticity (TQ); when TQ is absent it is approximated as BV-squared (flagged in the audit). The intraday sampling count `M` is required and has no default — it must be supplied (e.g. 78–79 for 5-minute returns in a 6.5-hour US equity session). The jump significance level `jump_alpha` defaults to 0.01; the daily/weekly/monthly lags are 1/5/22. A safeguard forces a no-jump day when RV is below BV (a microstructure artifact). The `use_log` option is discouraged here — the jump series contains many zeros, so logging injects large negative spikes; keep it off unless RV is heavily right-skewed.
*Reference run:* the parity fixture `3b_har_cj.npz` (rv/bv/tq, n=1,478 effective, M=78), `jump_alpha=0.01`, h=1, Balanced — 54/1,500 days (3.6%) flagged as jumps (BNS z-threshold 2.326, max z 15.8), continuous persistence 0.825, jump persistence 0.197, `β_cd=0.472, β_cw=0.267, β_cm=0.085`, `β_jw=0.289 (sig)`, R²=0.334. The fixture is used because no intraday RV/BV exists in the sample data; its synthetic series are in tiny variance units, so the raw AIC is a units artifact and is omitted.
