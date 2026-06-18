## What It Does
The HAR (Heterogeneous AutoRegressive) model, Corsi 2009, forecasts realized volatility by regressing future realized variance on its own daily, weekly, and monthly averages. The three horizons proxy the different trading frequencies — short-term traders, weekly rebalancers, monthly allocators — that drive volatility, and the simple OLS structure makes it a robust, widely-used realized-vol forecaster. The input is a realized-variance series, computed upstream from intraday data.

## When to Use It
- You have a realized-variance series (e.g. from intraday returns) and want to forecast future realized vol.
- You want a transparent, hard-to-overfit alternative to GARCH for volatility forecasting.
- You're working at a daily frequency with access to high-frequency-based RV.
- Use HAR-RV when you have a single RV series; step up to HAR-CJ if you also have bipower variation and want to separate continuous volatility from jumps.

## How to Read the Result
The three slope coefficients (daily β_d, weekly β_w, monthly β_m) show which horizon drives the forecast. On the SP500 reference (RV proxy), β_w=0.464 is the largest — the weekly component dominates, the canonical Corsi pattern — with β_d=0.191 and β_m=0.091, all significant. The R² of 0.279 is in the normal range for daily RV forecasting. The persistence (sum of slopes ≈0.746) measures how much past RV carries forward. One caveat on the p-values: the default OLS standard errors assume iid homoskedastic residuals and are not autocorrelation-aware; for persistent RV, consider HAC/Newey-West errors or a block bootstrap before leaning on significance.

## Related Techniques
- *(use after)* `har_cj` to decompose into continuous and jump components if bipower variation is available.
- *(alternatives)* `garch` / `egarch` / `stochastic_volatility` when you have returns rather than realized variance; `har_cj` for the jump-aware extension.

## Technical Detail
Backend is numpy OLS (`np.linalg.lstsq`) of future RV on the daily, weekly, and monthly RV averages. Input is a single non-negative realized-variance series (RV is computed upstream — e.g. the sum of intraday squared returns). The daily, weekly, and monthly lags default blank to the Corsi canonical 1/5/22 (fixed constants, not data-dependent). Minimum observations = `monthly_lag` + `h_ahead` + 10 (33 by default). Bootstrap CIs are preset-dependent (Fast 0 / Balanced 500 / Thorough 2,000).
*Reference run:* a daily squared-log-return RV proxy from the SP500 sample (no intraday RV in the sample data), n=2,490, Corsi 1/5/22, h=1, Balanced — `R²=0.279` (adj 0.277), `β_d=0.191, β_w=0.464 (largest), β_m=0.091`, intercept 0.333, all significant at 5%, persistence sum 0.746. The reference RV is a proxy; true HAR-RV uses intraday-based realized variance, but the weekly-dominates pattern is the canonical Corsi result and survives the proxy.
