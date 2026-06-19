## What It Does
MSTL (Multiple Seasonal-Trend decomposition by Loess) extends STL to series with more than one seasonal cycle — for example daily data with both a weekly and an annual pattern. It extracts each seasonal component in turn using STL, leaving a trend and residual. It is the tool for high-frequency series where several seasonalities overlap.

## When to Use It
- Your series has multiple seasonal periods (e.g. hourly data with daily and weekly cycles, or daily data with weekly and yearly cycles).
- You want each seasonal component separated rather than blended into one.
- A single-seasonal method leaves visible structure in the residual.
- Use MSTL for multiple seasonalities; use `stl_decompose` for a single seasonal cycle; use `classical_decompose` for a simple fixed pattern.

## How to Read the Result
The output is a trend, a residual, and one seasonal component per period, each with a strength measure. On the airline series, with the periods inferred automatically, MSTL identifies a single period of 12 (it is a monthly series with one annual cycle) and returns a seasonal strength of 0.98 and a trend strength of 0.997. When you supply multiple periods, you get one seasonal series for each — read them separately to see how much each cycle contributes. Note the decomposition is additive; for a multiplicative relationship, log-transform the series first.

## Related Techniques
- *(use after)* analyze each extracted seasonal component, or feed the deseasonalized series onward.
- *(alternatives)* `stl_decompose` (single seasonal period); `classical_decompose` (fixed single pattern); `x13_seasonal_adjust` for monthly/quarterly official adjustment.

## Technical Detail
Estimation is statsmodels `MSTL`, which applies STL iteratively to extract each seasonal period. The periods default to automatic inference from the data frequency, or can be given as a list. The decomposition is additive (log-transform first for a multiplicative relationship), and a seasonal period that does not have at least two full cycles of data is dropped. Per-period Loess settings follow preset.
*Reference run:* airline_passengers.csv (144 monthly observations), periods auto, Balanced — inferred a single period of 12, seasonal strength 0.98, trend strength 0.997.
