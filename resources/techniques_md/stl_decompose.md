## What It Does
STL (Seasonal-Trend decomposition by Loess) splits a series into trend, seasonal, and residual components using locally-weighted regression (Loess). Unlike classical decomposition, the seasonal component can evolve over time rather than being held fixed, and the procedure is robust to outliers. It is the modern default for decomposing a single-seasonal series.

## When to Use It
- The seasonal pattern changes shape or amplitude over time (evolving seasonality).
- The series has outliers you do not want distorting the trend and seasonal estimates.
- You want a flexible, well-behaved decomposition as a basis for seasonal adjustment or anomaly detection.
- Use STL for a single evolving seasonal cycle; use `classical_decompose` for a simple fixed pattern; use `mstl_decompose` when there is more than one seasonal period.

## How to Read the Result
The output is the three component series plus seasonal and trend strength measures. On the airline series, STL returns a seasonal strength of 0.98 and a trend strength of 0.997 — slightly higher than classical decomposition because the Loess fit adapts to the evolving seasonal amplitude. The robustness setting matters: with it on, outliers are down-weighted so they do not distort the trend and seasonal components (note that the Fast preset disables robustness for speed). The seasonal component is allowed to change gradually across cycles, which is the main advantage over the fixed classical pattern.

## Related Techniques
- *(use after)* `stl_esd_anomaly` to flag anomalies in the STL residual; `x13_seasonal_adjust` for official seasonal adjustment.
- *(alternatives)* `classical_decompose` (fixed seasonal pattern); `mstl_decompose` (multiple seasonal periods); `x13_seasonal_adjust` (Census-grade adjustment).

## Technical Detail
Estimation is statsmodels `STL` (Loess-based). The seasonal smoothing window governs how quickly the seasonal shape may evolve; the engine sets it from the period when not specified (the seasonal parameter), and the Loess degrees and iteration counts are governed by preset. Robustness, when on, runs additional iterations that down-weight outliers (the Fast preset turns this off). The seasonal period is inferred from the data frequency when left blank.
*Reference run:* airline_passengers.csv (144 monthly observations), robust on, Balanced — period 12, seasonal strength 0.98, trend strength 0.997.
