## What It Does
This technique detects anomalies in a seasonal series in a way that respects the seasonality. It decomposes the series into trend, seasonal, and remainder components (STL), then runs the Generalized Extreme Studentized Deviate (Rosner) test on the *remainder* to flag points that are anomalous once trend and seasonality are removed. The result is genuine idiosyncratic shocks, not the routine seasonal highs and lows that a naive outlier test would flag.

## When to Use It
- You have a seasonal series and want anomalies that are not merely the expected seasonal peaks or troughs.
- You want a principled statistical test for outliers rather than a fixed threshold.
- You need to catch one-off shocks in the presence of trend and seasonality.
- Use it for seasonal data; for a non-seasonal series a plain outlier test on the series itself is sufficient.

## How to Read the Result
The output is the flagged anomaly indices and their severity. Because the test runs on the STL remainder, a flagged point is extreme *relative to its seasonal and trend context* — high for its position in the cycle, not merely high in absolute terms. On the airline-passengers series (monthly, period 12) with an injected spike of +200 at index 72, the technique flags two anomalies: the injected spike (the most extreme, roughly 59 deviations out) plus one genuine historical anomaly. The test is Bonferroni-adjusted to control false positives, but it assumes the remainder is independent — residual autocorrelation can inflate the number of flags.

## Related Techniques
- *(use after)* `intervention_analysis` to model a flagged anomaly as an event; `stl_decompose` to inspect the underlying components.
- *(alternatives)* a plain residual outlier test for non-seasonal data; `evt_pot_gpd` for tail-risk estimation rather than point-anomaly flagging.

## Technical Detail
The implementation is a statsmodels STL decomposition followed by the Rosner GESD test applied to the remainder. The seasonal period is inferred from the data frequency. The test iteratively removes the most extreme remainder point, up to a maximum share of the series, performing a studentized-deviate test at the chosen significance level at each step. The detection direction (both, upper, or lower) defaults to both.
*Reference run:* airline_passengers.csv (monthly, period 12) with an injected +200 spike at index 72, Balanced — two anomalies flagged (1.4% of points): the injected spike at index 72 (the most extreme, ~59 deviations out) plus one genuine historical anomaly at index 9.
