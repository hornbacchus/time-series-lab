## What It Does
This technique performs official-statistics-grade seasonal adjustment using the U.S. Census Bureau's X-13 program. It runs the X-11 seasonal-adjustment algorithm (with an automatic regARIMA model used to pre-adjust the series for outliers and calendar effects), returning the seasonally-adjusted series along with its trend, seasonal, and irregular components. It is the method national statistical agencies use to publish seasonally-adjusted economic data.

## When to Use It
- You want seasonal adjustment to the standard used by official statistical agencies (the Census X-11 method).
- You're working with monthly or quarterly economic data and want a defensible, widely-accepted adjustment.
- You want automatic outlier and calendar pre-adjustment built into the procedure.
- Use X-13 for official-grade monthly/quarterly adjustment; use `stl_decompose` or `classical_decompose` for a lighter, dependency-free decomposition.

## How to Read the Result
The output is four series — the seasonally-adjusted series (Census table D11), the trend (D12), the seasonal factors (D10), and the irregular component (D13) — plus a seasonal-strength measure. On the airline series the adjustment returns a seasonal strength of 0.98. Two behaviors to know: by default the model fits only the most recent 120 observations (a rolling concurrent window, in the style of agency practice), so on a longer series the oldest data are dropped with a warning — set the fit window to 0 to use all available data. And note this runs the X-11 decomposition specifically; despite the program's "ARIMA-SEATS" name, the SEATS decomposition is not used here.

## Related Techniques
- *(use after)* analyze the seasonally-adjusted series or the irregular component for residual signal.
- *(alternatives)* `stl_decompose` (Loess-based, no external dependency); `classical_decompose` (simplest); `mstl_decompose` (multiple seasonal periods).

## Technical Detail
The engine calls the Census X-13 binary, writing an X-11 specification with an automatic regARIMA pre-adjustment model (`automdl`) for outliers and calendar effects. It returns the Census D-tables — D11 (seasonally adjusted), D12 (trend), D10 (seasonal), D13 (irregular) — and a computed seasonal strength; the higher-level X-13 diagnostics (M and Q statistics, sliding spans, revision histories) are not extracted. The seasonal period and series start are inferred from the data; the transform and outlier settings follow preset. **Dependency note:** this technique requires the Census X-13 binary to be present on the machine (it is located via an environment variable, a bundled `resources/x13/` folder, or the system path). The binary is not distributed with the repository — a fresh clone will not run X-13 until the binary is installed.
*Reference run:* airline_passengers.csv (144 monthly observations), default settings, Balanced — ran X-11 via the local Census binary, period 12, transform auto, outliers on, seasonal strength 0.98; the default 120-observation fit window dropped the 24 oldest observations; returned the seasonally-adjusted, trend, seasonal, and irregular series.
