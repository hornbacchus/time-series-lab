## What It Does
Robust estimators summarize a series' center and spread in a way that resists outliers, unlike the ordinary mean and standard deviation, which a few extreme values can distort badly. It computes location estimates (trimmed and winsorized means, the median) and scale estimates (MAD, Qn, the interquartile range) that stay stable even when the data contain spikes or fat tails. The gap between a robust estimate and its classical counterpart is itself a diagnostic — it tells you how much the outliers are moving the ordinary statistics.

## When to Use It
- Your series has outliers, spikes, or fat tails that distort the ordinary mean and standard deviation.
- You want a center and spread you can trust without first cleaning the data by hand.
- You want to quantify how much the outliers are influencing the classical statistics.
- Use robust estimators whenever the data are contaminated or heavy-tailed; the ordinary mean and standard deviation are fine only for clean, near-Gaussian data.

## How to Read the Result
Compare each robust estimate against its classical counterpart. On the SP500 daily returns, the mean is 0.048 but the median 0.075 and the 10%-trimmed mean 0.086 — the spread among the location estimates signals skew or outliers. The scale comparison is the sharper signal: the classical standard deviation is 1.14 while the robust MAD is 0.70 and Qn is 0.79, a standard-deviation-to-MAD ratio of 1.63 — well above the ratio of about 1.0 you would see in clean Gaussian data, flagging meaningful outlier influence. When the robust and classical numbers diverge like this, trust the robust ones. Each estimator has a breakdown point — the fraction of contamination it tolerates before failing — with the median and MAD tolerating up to about half the data.

## Related Techniques
- *(use after)* feed a robust scale into downstream risk or anomaly logic; `stl_esd_anomaly` to actually flag the outliers.
- *(alternatives)* the ordinary mean/standard deviation for clean data; `evt_pot_gpd` when the tail itself (not its influence on the center) is the question.

## Technical Detail
The estimators are computed directly (scipy/numpy): a trimmed mean (dropping a fraction from each tail), a winsorized mean and standard deviation (pulling the tails in to a fraction's quantile), the median, the median absolute deviation (MAD, scaled by 1.4826 to match the standard deviation under normality), the Rousseeuw-Croux Qn estimator (scaled by 2.2219), the interquartile range, and robust skewness and kurtosis. The trim and winsor fractions default internally (the Thorough preset grid-searches them). Note these are trimming/winsorizing and rank-based estimators, not Huber/Tukey M-estimators.
*Reference run:* sp500_returns.csv (2,512 daily log-return %), Balanced — mean 0.048, median 0.075, 10%-trimmed mean 0.086; classical standard deviation 1.14 versus robust MAD 0.70 and Qn 0.79 (a standard-deviation-to-MAD ratio of 1.63, flagging outlier influence).
