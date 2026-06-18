## What It Does

Checks whether a time series is **stationary** — whether its statistical behavior (its average level and its swings) stays put over time, or whether it drifts and wanders. This matters because most forecasting and regression tools assume stationarity; feeding them a wandering series produces results that look meaningful but aren't.

On the ribbon, this runs a **three-test triage**, not a single test. It applies the Augmented Dickey-Fuller (ADF), KPSS, and Phillips-Perron tests together — three different angles on the same question — and fuses them into one plain verdict: **STATIONARY**, **UNIT ROOT** (it wanders), **CONFLICTING** (the tests disagree), or **INCONCLUSIVE**, with a recommendation on what to do next. Using three tests guards against the weakness of any one: ADF and KPSS rest on opposite assumptions, so when they agree you can trust the answer, and when they disagree the triage tells you so rather than giving false confidence.

## When to Use It

- **Before fitting an ARIMA model** — to decide how many times to difference the series (the *d* term). A unit-root verdict means difference it first.
- **Before a regression between two series** — running ordinary regression on two wandering series produces *spurious* relationships (high R², no real link). Test both for stationarity first.
- **Before testing for cointegration** — the triage confirms the inputs are the kind of series cointegration analysis expects.
- **As a first look at any new series** — a quick read on whether it's mean-reverting (returns to a level) or trending/wandering.

## How to Read the Result

The triage reports each test's finding plus a fused verdict, in deliberately careful language: a series has its **unit root rejected** (evidence of stationarity) or **not rejected** (consistent with wandering) — never flatly "stationary," because these are statistical tests.

**What the numbers look like.** The ADF statistic is a negative number; the more negative, the stronger the evidence against a unit root. The test compares it against critical values that print at roughly **−3.43 / −2.86 / −2.57** (the 1% / 5% / 10% thresholds for a constant-only test) — the statistic must be *more negative* than these to reject.

Two real examples make the contrast concrete:

- **A stationary series** (S&P 500 daily log returns): ADF statistic **−15.9**, p-value **0.000** — far past every threshold. KPSS agrees (statistic 0.03, fails to reject). Verdict: **STATIONARY**.
- **A wandering series** (nonfarm payrolls, in levels): ADF statistic **−0.16**, p-value **0.94** — nowhere near the thresholds. KPSS agrees in reverse (statistic 5.36, rejects stationarity). Verdict: **UNIT ROOT (I(1))** — difference it before modeling.

So: a strongly negative ADF statistic (say −3 or beyond) with a small p-value points to stationarity; a statistic near 0 to −2 with a large p-value points to wandering. When the three tests conflict, treat the series as borderline and lean on the recommendation.

## Related Techniques

- **ARIMA / Auto-ARIMA** *(use after)* — the stationarity verdict sets the differencing order (*d*); this test is the standard precursor.
- **Cointegration (Johansen)** *(use after)* — when two series each wander, test whether they wander *together*; stationarity screening comes first.
- **KPSS Test** and **Phillips-Perron Test** *(alternatives)* — the other two legs of this triage; run either alone if you want a single test rather than the fused verdict.

## Technical Detail

*Enough to reproduce the result in Python.*

The core test is statsmodels' `adfuller(series, maxlag=maxlag, regression='c', autolag='AIC')`. When the lag cap is left blank, `maxlag` is set to the Schwert upper bound, computed as `floor(12 · (n/100)^0.25)` (floored to 1 for fewer than 12 observations); AIC then selects the actual lag within `[0, maxlag]`. Critical values are MacKinnon's, taken directly from statsmodels.

Before testing, the series is cleaned: leading and trailing missing values are trimmed, then interior gaps are filled by **linear interpolation** (`np.interp`) — worth knowing, since interpolating across gaps can bias a unit-root test, so pre-clean where you can. Minimum 12 observations.

On the ribbon path the technique runs all three tests and fuses them via this exact rule (ADF's null is a unit root; KPSS's null is stationarity):

- ADF rejects **and** KPSS does not → **STATIONARY**
- ADF does not reject **and** KPSS rejects → **UNIT ROOT (I(1))**
- both reject → **CONFLICTING** (suggests a structural break or near-unit-root)
- neither rejects → **INCONCLUSIVE**

where "rejects" means p-value < 0.05. The KPSS and Phillips-Perron legs inherit the deterministic specification from the ADF `regression` setting. The ADF-only result (no triage) is available through the `TSL_ADF` worksheet function.

*Reference run:* on S&P 500 log returns (n≈2,500), the engine returns ADF = −15.86 (AIC lag 8), KPSS = 0.028, PP = −57.96 → STATIONARY; on nonfarm payrolls in levels (n≈1,000), ADF = −0.16, KPSS = 5.36, PP = −0.20 → UNIT ROOT (I(1)).
