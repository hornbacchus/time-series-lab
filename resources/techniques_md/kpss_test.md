## What It Does

Tests whether a series is **stationary** — but from the opposite direction to the ADF test, which is exactly what makes it a valuable cross-check. KPSS starts by *assuming* the series is stationary and looks for evidence against that assumption. So its verdict reads in reverse: **"fail to reject"** means the series **appears stationary**, while **"reject"** means there's evidence it wanders or trends.

Pairing KPSS with ADF is standard practice precisely because their assumptions are flipped. When both point the same way, the conclusion is solid. When they disagree — ADF says "wanders," KPSS says "stationary" — the series is likely borderline, often *trend-stationary* (stationary once you account for a trend), and worth a closer look.

## When to Use It

- **Alongside ADF**, as the confirming half of a stationarity check — this is its primary role, and the ribbon triage runs it for you automatically.
- **To distinguish trend-stationary from difference-stationary** — test around a trend (`ct`) and compare against the level test (`c`).
- **When an ADF result feels borderline** — KPSS's opposite framing often breaks the tie.

## How to Read the Result

Remember the inversion: **fail to reject = stationary**, **reject = not stationary** — the reverse of ADF. The test compares a statistic against critical values; a statistic **above** the critical value rejects stationarity. If you remember one thing: with KPSS, "rejection" is the *bad* news for stationarity.

**What the numbers look like.** The KPSS statistic is a small positive number, compared against critical values that print at roughly **0.74 / 0.46 / 0.35** (1% / 5% / 10%, level test). Below the threshold → stationary; above → not. Two real examples:

- **A stationary series** (S&P 500 log returns): KPSS **0.028**, well below every threshold → *fail to reject* → appears stationary. (ADF agrees: −15.9.)
- **A wandering series** (nonfarm payrolls, in levels): KPSS **5.36**, far above the 1% threshold → *reject* → non-stationary, difference it. (ADF agrees: −0.16.)

So a statistic near zero means stationary; a statistic above ~0.5–0.7 means it wanders. The contrast here is stark — 0.028 vs 5.36 — because both series are unambiguous; borderline series land nearer the thresholds.

## Related Techniques

- **ADF Test** *(use alongside)* — the standard companion; their opposite nulls make the pair more reliable than either alone, which is why the triage runs both.
- **Phillips-Perron Test** *(alternative)* — another unit-root test (same direction as ADF) for cross-checking.
- **ARIMA / Auto-ARIMA** *(use after)* — once stationarity is settled, KPSS's level-vs-trend finding informs whether to difference or detrend.

## Technical Detail

*Enough to reproduce the result in Python.*

The test is statsmodels' `kpss(series, regression='c', nlags='auto')`, run inside a warnings-capture block. With `nlags='auto'` the bandwidth follows the data-driven **Hobijn–Franses–Ooms (1998)** rule; `'legacy'` uses the Schwert rule `floor(12·(n/100)^0.25)`; an integer fixes it. The long-run variance uses a Newey–West (Bartlett-kernel) estimator, and critical values are the KPSS (1992) asymptotics from statsmodels.

The inverted null is enforced explicitly in code: the rejection flag is computed as **statistic > critical value** (rather than the < comparison the other tests use), so rejection corresponds to evidence *against* stationarity. The decision still reports p-value < 0.05 as the formal threshold. Level (`c`) tests stationarity around a constant; trend (`ct`) tests stationarity around a linear trend — statsmodels accepts only these two (no "none" option).

*Reference run:* on S&P 500 log returns (n≈2,500), KPSS = 0.028 (auto lag 2), p = 0.10 → fail to reject; on nonfarm payrolls in levels (n≈1,000), KPSS = 5.36 (auto lag 19), p = 0.01 → reject.
