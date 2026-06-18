## What It Does

Tests whether a series has a **unit root** (whether it wanders rather than reverting to a level) — the same question as the ADF test, reached a different way. Where ADF adds lag terms to soak up short-run autocorrelation, Phillips–Perron applies a statistical correction instead, which makes it more robust when the series has changing volatility or mild structure that lag-based tests handle poorly.

It reads the same direction as ADF: **unit root not rejected** means the series wanders (difference it before modeling); **rejected** means evidence of stationarity. It's the third leg of the ribbon triage, providing a robustness check that complements ADF and KPSS.

## When to Use It

- **As a robustness check on ADF** — when you want a unit-root test that handles changing volatility or autocorrelation differently. The ribbon triage includes it automatically.
- **On financial and high-frequency series** — where volatility clusters and shifts, Phillips–Perron's correction is often better-behaved than ADF's lag approach.
- **When ADF's lag choice feels fragile** — PP sidesteps lag selection with its correction.

## How to Read the Result

Same orientation as ADF: **not rejected = wanders** (difference it), **rejected = stationary**. The statistic is negative, compared against the same critical-value magnitudes as ADF (**−3.43 / −2.86 / −2.57** at 1% / 5% / 10%, constant test) — more negative than the threshold rejects the unit root. A **Method** note reports which computational path produced the result. Two real examples:

- **A stationary series** (S&P 500 log returns): PP **−57.96**, p **0.000** → reject the unit root → stationary. (Matches ADF's −15.9.)
- **A wandering series** (nonfarm payrolls, in levels): PP **−0.20**, p **0.94** → fail to reject → wanders, difference it. (Matches ADF's −0.16.)

Read it together with the other two tests — agreement across all three (as in both examples here) is the strongest signal.

## Related Techniques

- **ADF Test** *(alternative / use alongside)* — the companion unit-root test; PP is the robustness cross-check, and the triage runs both.
- **KPSS Test** *(use alongside)* — the opposite-null test; the three together give the fused verdict.
- **GARCH** *(use after)* — if PP flags changing volatility as the reason a series looks borderline, a volatility model may be the better tool.

## Technical Detail

*Enough to reproduce the result in Python.*

The working backend is the **`arch` library**: `PhillipsPerron(series, trend=trend, lags=...)`, reading `.stat`, `.pvalue`, and `.critical_values` (with a "Method" label of `arch.PhillipsPerron`). The implementation tries a statsmodels path first, but that function does not exist in statsmodels and always falls through — so in practice `arch` is what runs. A hand-rolled Z(t) computation exists as a final fallback.

One documentation caveat: the technique's older notes mention a `Z_alpha` statistic and a Schwert bandwidth — neither is what the code actually produces. The `arch` backend emits a single Z(t)-style statistic, and the manual fallback's bandwidth is `floor(4·(n/100)^(2/9))`, not the Schwert form. Trust the behavior described here over any older text.

*(For the fallback, if `arch` is unavailable: OLS of the series on its lag plus deterministic terms; a Newey–West long-run variance with a Bartlett kernel; the standard Phillips–Perron correction `pp_stat = t_rho − correction`; MacKinnon p-values. The `arch` path is preferred and is what runs by default.)*

*Reference run:* on S&P 500 log returns (n≈2,500), PP = −57.96 (lag 27), p = 0.000, Method = arch.PhillipsPerron → reject; on nonfarm payrolls in levels (n≈1,000), PP = −0.20 (lag 22), p = 0.94 → fail to reject.
