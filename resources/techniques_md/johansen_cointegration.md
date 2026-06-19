## What It Does
The Johansen procedure tests whether a set of non-stationary series share one or more long-run equilibrium (cointegrating) relationships, and how many. It runs two complementary rank tests — the trace test and the maximum-eigenvalue test — and returns the eigenvalues and the estimated cointegrating vectors. It is the standard precursor to fitting a VECM: it tells you the cointegrating rank to use.

## When to Use It
- You have several non-stationary level series and want to know whether they're cointegrated before modeling them.
- You need the cointegrating rank to parameterize a `vecm`.
- You're testing an arbitrage or equilibrium hypothesis across maturities or markets.
- Run it whenever you're deciding between a VECM (cointegrated levels) and a differenced VAR (not cointegrated).

## How to Read the Result
Each test compares a statistic against critical values at the chosen significance level; the cointegrating rank is the largest r for which the statistic still exceeds its critical value. On the Treasury reference both tests agree on rank 2 — at the decision point the trace statistic is 34.53 against a 29.80 critical value (95%) — so the curve has two long-run relationships and a rank-2 VECM is recommended. The eigenvalues (0.0059, 0.0041, 0.0011, 0.0004 here) rank the strength of each potential relationship. When the two tests disagree, the trace test is generally the more robust call.

## Related Techniques
- *(use after)* `vecm` with the rank this test recommends — the natural next step.
- *(alternatives)* `var` on differences if the test finds no cointegration (rank 0); the ADF and KPSS stationarity tests to first confirm the individual series are non-stationary.

## Technical Detail
Estimation is statsmodels `coint_johansen(data, det_order=…, k_ar_diff=…)`, with the deterministic order and lag length selectable (blank lags auto-select by information criterion). Critical values are MacKinnon (1996) asymptotics. An optional Reimers (1992) Bartlett small-sample correction (for samples under roughly 100) rescales the statistics; when enabled, both the uncorrected and corrected statistics are reported side by side. The rank decision uses the (corrected, if enabled) statistic against the critical value at the chosen level.
*Reference run:* treasury_yields.csv (2Y/5Y/10Y/30Y, 6,146 obs), deterministic order 0, lags auto-selected, Balanced — rank 2 (trace and max-eigenvalue agree), trace statistic at the decision point 34.53 vs 29.80 critical value (95%), eigenvalues 0.0059 / 0.0041 / 0.0011 / 0.0004 → recommends a rank-2 VECM.
