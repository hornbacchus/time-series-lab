# Critical Slowing Down (Early Warning)

## Overview

Critical Slowing Down (CSD) is a class of statistical signatures
that complex dynamical systems exhibit as they approach a critical
transition — a regime shift, phase transition, or bifurcation
between qualitatively different stable states. The theory comes
from dynamical systems mathematics: as the dominant eigenvalue
of a system's local linearization approaches zero, the system's
recovery from small perturbations slows, manifesting as rising
lag-1 autocorrelation, rising variance, and shifting higher-moment
shape. Scheffer's 2009 *Critical Transitions in Nature and Society*
collected a wide body of ecological, climatological, and financial
applications; Dakos et al. 2012 codified the now-standard CSD
detection pipeline.

This wrapper implements the canonical Dakos pipeline on a single
univariate input series. It produces a composite Early Warning
Signal (EWS) score, classifies the result as **normal**,
**elevated**, or **critical**, and exposes per-indicator Kendall
tau trend statistics with surrogate-derived empirical p-values.

The wrapper is intentionally **descriptive**, not predictive. CSD
signatures observed in a series are evidence that the underlying
process exhibits the statistical pattern of approaching a
transition; whether that transition will materialize, on what
timeline, and in what direction are separate questions the
indicators do not answer.

## The Four-Stage Pipeline

**Stage A — Detrending.** CSD signals appear in residuals from a
slowly-varying mean. The wrapper supports three detrending
methods: Gaussian-kernel smoothing (literature default), first
differences, and linear OLS detrending.

**Stage B — Rolling indicators.** On the detrended residuals,
the wrapper computes six rolling indicators over a configurable
window: lag-1 autocorrelation, variance, skewness, kurtosis,
return rate, and spectral density ratio.

**Stage C — Kendall tau trend statistic.** For each rolling
indicator series, the wrapper computes Kendall's tau-b correlation
between time index and indicator value over a trailing
Kendall-lookback window. Rising tau on AR(1) and variance is the
canonical CSD-firing pattern.

**Stage D — Composite EWS scoring.** Per-indicator taus are
combined into a single z-score-equivalent composite EWS score.
Two combination methods are supported: equal-weight averaging
of z-scored taus (default), and Fisher-combined empirical p-values.

## Indicator Definitions

| Indicator | Formula | Interpretation |
|---|---|---|
| `ar1` | corrcoef(x[:-1], x[1:]) | Lag-1 autocorrelation; rising AR(1) reflects slower recovery from perturbations. |
| `variance` | sample variance with ddof=1 | Rising variance reflects accumulating shock impacts as recovery slows. |
| `skewness` | Fisher-Pearson (bias=False) | Asymmetric perturbation responses; rises near transitions in many systems. |
| `kurtosis` | Fisher excess kurtosis (bias=False) | Rising kurtosis indicates heavier tails / more extreme excursions. |
| `return_rate` | 1 - AR(1) | Convenience: lower return rate = slower recovery = stronger CSD. |
| `density_ratio` | low-frequency power / total power | Spectral red-shift; CSD theory predicts this ratio rises as transition approaches. |

All six are computed over a rolling window with right-aligned
output convention.

## Detrending Methods

Choice of detrending materially affects results. The wrapper
exposes three options:

**Gaussian kernel** (default). Smooths the input series with a
Gaussian filter (scipy.ndimage.gaussian_filter1d, mode='reflect')
and returns the residual. Bandwidth defaults to T/10 samples per
Dakos convention. This is the most flexible method; suitable for
slowly-varying trends without specific functional form. Smaller
bandwidth captures finer trend structure (less residual variance,
weaker CSD signal); larger bandwidth produces residuals closer to
the raw series (stronger trend pattern in residuals, possibly
spurious CSD).

**First differences**. Returns y[t] - y[t-1]. Simplest and least
sensitive method. Best when the underlying trend is approximately
linear and the residual structure is the focus of analysis.
Output length is T-1.

**Linear OLS**. Subtracts the OLS regression of y on time. Best
when a strict linear trend is known; otherwise the method
under-detrends curvature and the residuals retain trend energy.

## Surrogate-Based P-Values

When `compute_pvalues=True` (default), the wrapper generates
AR(1)-bootstrap surrogates that preserve the variance and lag-1
persistence of the input residuals. For each surrogate, the
wrapper recomputes the rolling indicator and its Kendall tau,
forming an empirical null distribution. The p-value for the
observed indicator is the fraction of surrogate taus equal to or
greater than the observed tau.

Surrogate count is preset-driven: Fast=200, Balanced=1000,
Thorough=5000. Higher counts yield tighter p-value precision at
proportional runtime cost. The runtime dominates the wrapper's
total time budget, so for exploratory analysis on long series,
consider running with `compute_pvalues=False` first to use the
fast asymptotic Kendall tau p-value, then switching to surrogate-
based p-values for the final assessment.

## Composite EWS Score Interpretation

The composite score classifies the result into one of three
states:

| State | Composite Score | Meaning |
|---|---|---|
| `normal` | < 1.0σ | No statistical signature of approaching transition. |
| `elevated` | 1.0σ ≤ score < 1.5σ | Some indicators trending consistently with CSD; not all confirming. |
| `critical` | ≥ 1.5σ | Multiple indicators agreeing strongly; statistical signature of approaching transition is present. |

Two combination methods:

**equal_weight_zscore** (default). For each indicator, compute the
z-score of its observed Kendall tau against the asymptotic null
distribution (mean 0, variance 2(2T+5)/(9T(T-1))). Average the
z-scores across indicators. Result is a composite z-score.

**fisher_combined**. Combine the per-indicator empirical p-values
via Fisher's method:
    chi-squared = -2 × Σ log(p_i),  df = 2k
where k is the number of indicators. Convert the resulting
combined p-value to a z-score equivalent. Requires
`compute_pvalues=True`.

## Tier 3 Triggers

The wrapper produces five Tier 3 diagnostic triggers:

- **D-CSD-1 composite_elevated** — Composite EWS score is in the
  elevated or critical band. Provides the headline CSD finding
  with severity classification.
- **D-CSD-2 consistent_tau_pattern** — Both AR(1) and variance
  show statistically significant rising Kendall tau trends. This
  is the strictest CSD pattern in the Dakos 2012 framework; both
  primary indicators agreeing increases confidence that the
  underlying system is approaching a transition rather than
  experiencing transient volatility.
- **D-CSD-3 post_transition** — Tail residuals show elevated
  skewness or kurtosis, suggesting the series may have already
  undergone a regime shift rather than approaching one. CSD
  indicators are most reliable as early warnings in pre-transition
  regimes.
- **D-CSD-4 insufficient_data** — Series too short for stable
  estimation given the rolling window and Kendall lookback
  parameters. CSD literature recommends T ≥ 500 with T > 1000
  preferred for surrogate-based testing.
- **D-CSD-5 non_stationary_residuals** — Detrending residuals
  failed the ADF stationarity test. Non-stationary residuals
  produce spurious trends in rolling indicators that can mimic
  CSD without an actual underlying transition.

## Methodological Caveats

These caveats are first-class output of this wrapper, not
footnotes. All apply regardless of how clean the EWS signal looks.

**Predictive value out-of-sample is contested.** The
dynamical-systems theory underlying CSD predicts these signatures
near critical transitions in known mechanistic systems
(experimentally manipulated lakes, simulated climate models). Its
predictive value on real financial market data is mixed in the
empirical literature. Diks, Hommes & Wang 2018 examined CSD
indicators on historical financial crises and found mixed
results — some crises were preceded by clear CSD patterns,
others not. Treat positive CSD findings as one input among
several regime-detection signals, not as standalone trading
signals.

**Detrending bandwidth sensitivity.** Different bandwidths can
produce different EWS conclusions on the same series.
Sensitivity analysis is recommended: vary the bandwidth across
its plausible range and confirm the EWS conclusion is robust
before relying on the result.

**Volatility-clustering confound.** Rising variance is a CSD
indicator, but it can also signal pure volatility clustering
(GARCH-style heteroskedasticity) without any underlying phase
transition. The skewness/kurtosis indicators help disambiguate,
but the confound is fundamental to univariate CSD detection.

**Kendall tau on cyclical or trending series.** Kendall tau
measures monotonic correlation. Series with cycles or strong
unmodelled trends produce taus that reflect those features rather
than CSD. The detrending step is intended to remove this; the
ADF stationarity check on detrending residuals (D-CSD-5)
catches the most blatant failures.

## References

- Scheffer, M. (2009). *Critical Transitions in Nature and
  Society.* Princeton Univ. Press.
- Dakos, V., Carpenter, S.R., Brock, W.A., et al. (2012).
  Methods for detecting early warnings of critical transitions
  in time series illustrated using simulated ecological data.
  *PLoS ONE* 7(7): e41010.
- Diks, C., Hommes, C., Wang, J. (2018). Critical slowing down
  as an early warning signal for financial crises? *Empirical
  Economics.*
- Bury, T.M., Sujith, R.I., Pavithran, I., Scheffer, M.,
  Lenton, T.M., Anand, M., Bauch, C.T. (2023). ewstools: A
  Python package for early warning signals of bifurcations in
  time series data. *Journal of Open Source Software.*

## Application Examples

**Synthetic logistic-map example.** A canonical CSD test case is
the discrete logistic map x[t+1] = r·x[t]·(1-x[t]) with the
control parameter r slowly varying from 2.5 (single stable
fixed point) toward 3.6 (chaos via period-doubling cascade
through r=3.0 saddle-node bifurcation). On T=2000 observations
with observation noise sigma=0.05, the wrapper detects rising
AR(1) and variance trends consistent with approaching the
saddle-node bifurcation. This is the test case used in this
wrapper's parity check against the ewstools reference
implementation.

**Financial application disclaimer.** Applying CSD detection to
financial returns requires care. Returns are typically already
mean-zero and approximately stationary, so the detrending
literature defaults need adjustment. Volatility clustering is a
strong confound for the variance indicator. The
methodological-caveats block above applies in full to all
financial uses. The wrapper does not produce trading signals.
