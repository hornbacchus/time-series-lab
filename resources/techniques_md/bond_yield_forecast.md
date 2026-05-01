# Bond Yield Forecast

**Category:** Multivariate Systems
**Algorithm:** Large Bayesian Vector Autoregression with Stochastic
Volatility (BVAR-SV), Carriero-Clark-Marcellino (2019) sampler,
conditioned on economist macro projections via Banbura-Giannone-
Lenza (2015) Kalman-filter conditioning.

## What it does

Bond Yield Forecast generates probabilistic forecasts of the U.S.
Treasury yield curve over a 1-20 quarter horizon by:

1. Decomposing the yield curve into 3 principal components (level,
   slope, curvature) via PCA over a configurable historical window.
2. Estimating a 6-variable BVAR-SV (3 macro + 3 yield-curve PCs)
   with Minnesota prior + stochastic volatility on innovations.
3. Conditioning the forecast on user-supplied macro projection paths
   (e.g., consensus economist projections for GDP, CPI, fed funds).
4. Mapping the PC-space conditional forecast back to yield space
   across 10 standard maturities (3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y,
   20Y, 30Y).
5. Producing 5/25/50/75/95 percentile bands per maturity-horizon
   cell.

## Input

Bond Yield Forecast deviates from typical TSL wrappers: instead of
consuming Excel-cell-selection data via `ctx.series`, it reads a
**3-sheet bundled .xlsx workbook** referenced by the
`input_workbook` parameter. The workbook must contain:

| Sheet | Content |
|---|---|
| `BondYield_Macro` | Quarterly macro history (Real GDP growth, CPI inflation, Fed funds rate). Aim for ≥60 quarters (15 years). |
| `BondYield_Yields` | Quarterly Treasury yields at 10 standard maturities. Same time axis as macro. |
| `BondYield_Projections` | Forward-looking macro projections per scenario (`baseline`, `upside`, `downside`, etc.). 1-20 quarter horizon. |
| `README` | Optional. Plain-text instructions; ignored by the engine. |

Use the **Bond Yield Forecast → Open Input Template** Ribbon menu
item (Session 3 scope) to create a starter workbook with example
data already populated.

## Output

The wrapper produces 4 output tables on a Results sheet:

1. **Yield Forecast (5/25/50/75/95 percentiles)** — one row per
   (horizon, maturity) cell with median forecast and 4 credible
   bands.
2. **Macro Conditioning Paths (5/50/95 percentiles)** — the
   conditional macro paths the BVAR was conditioned on (post-
   uncertainty inflation).
3. **Convergence Diagnostics** — per-equation effective sample
   size (ESS) and Geweke z-scores, surfacing
   `ConvergenceWarning` if pass rates drop below the Session 0
   thresholds (90% overall, 80% per parameter group).
4. **Run Metadata** — algorithm version, sample period, chain
   length, runtime, etc.

The Audit sheet captures the full RunRequest configuration plus
captured `BVARWarning` instances, categorized by subclass
(`ConvergenceWarning`, `ProjectionAtBoundWarning`,
`ValidationDomainWarning`).

## Parameters

| Parameter | Default | Range | Notes |
|---|---|---|---|
| `input_workbook` | (required) | — | Path to the 3-sheet xlsx |
| `scenario` | `baseline` | (any column in BondYield_Projections) | Which projection scenario to run |
| `horizon` | 8 | 1-20 quarters | Forecast horizon |
| `n_draws` | 10000 | 1000-50000 | MCMC total draws (incl. burn-in) |
| `n_burn` | 3000 | 100-20000 | MCMC burn-in to discard |
| `n_paths_per_draw` | 50 | 10-500 | Forecast paths per posterior draw |
| `n_draws_subsample` | 1000 | 100-**5000** | Subsample for forecasting (capped per friction-points §3 OOM evidence) |
| `projection_uncertainty` | 0.25 | ≥0.01 | Soft-mode projection std |
| `lambda_1` | 0.2 | 0.001-2.0 | Minnesota overall tightness |
| `lambda_2` | 0.5 | ≥0.001 | Minnesota cross-equation |
| `lambda_3` | 1.0 | ≥0.001 | Minnesota lag decay |
| `seed` | 42 | ≥0 | Random seed |

All bounds are enforced both in the catalog (UI controls) and in the
wrapper's pre-flight validation layer (defense-in-depth). Bounds
match the Session 0 ValueError thresholds in BVAR's source
(`techniques.bond_yield_forecast.priors.MinnesotaPrior`,
`.estimation.BVARSV`, `.conditioning.ConditionalForecaster`).

## Performance characteristics

On the canonical fixture (143 quarters × 6 variables,
`n_draws=10000`, `n_burn=3000`):

| Phase | Wall-clock |
|---|---:|
| Pre-flight validation | <0.1s |
| Workbook read + PCA panel build | ~1s |
| BVAR-SV estimation | ~18s (numba-JIT-warmed; ~25s cold-start) |
| Conditional forecast (n_paths_per_draw=50) | ~3s |
| Yield-space mapping + table assembly | <1s |
| **Total** | **~22s** |

### First-call vs subsequent-call latency (numba JIT)

Bond Yield Forecast uses **numba `@jit(cache=True)`** on two
inner loops for performance:

1. **FFBS state sampling** (`_ffbs.ffbs_one_equation`) — runs
   once per equation per Gibbs draw inside BVAR-SV estimation.
2. **Conditional-forecast inner loop**
   (`_conditional_inner.conditional_forecast_inner_loop`) —
   runs once per kept draw inside the conditioning step.

**First-call cost (cold cache):** ~2-5 seconds. The first
invocation after a fresh Python process must JIT-compile both
functions. Numba writes the compiled artifacts to an on-disk
cache (`__pycache__/` adjacent to the .py source) keyed by
(numba version, Python version, platform, source-file mtime).

**Subsequent-call cost (warm cache):** <0.001s for the JIT
lookup itself; the actual loops run at compiled C-extension
speed. Wall-clock per BVAR-SV run is dominated by the algorithm
not the JIT lookup.

**TSL integration smooths this for users:** the
`engine_worker` startup (BYF Session 5, commit `38a5144`)
invokes a JIT warmer
(`engine/techniques/bond_yield_forecast/_jit_warmer.py`)
exactly once at process startup, before the named-pipe server
accepts connections. The first user-facing click after Excel
loads the add-in therefore sees the warm path — no surprise
2-5s latency hiding inside the first BYF run.

**When you might see cold-call latency anyway:**
- First run after a fresh deployment (cache binds to source
  mtime; new install = new mtime = first run pays compile).
- After a numba upgrade (cache binds to numba version).
- After a Python upgrade (cache binds to Python version).
- If running BYF outside the engine_worker process (e.g.,
  ad-hoc Python scripts, CI parity-audit invocations); these
  paths bypass the engine_worker startup hook and pay the
  cold JIT cost on first call.

The integration plan §5.3 banked the lazy-warming alternative
(move the warmer call to the BYF dispatch instead of the
engine_worker startup) for hardware where cold-warm exceeds
~10s. Current dev-hardware measurement: ~2.05s cold / <0.001s
warm — well within the budget; eager warming preserved.

`n_draws_subsample=1000` and `n_paths_per_draw=50` (defaults)
keep the conditional-forecast peak memory under ~150 MB. Setting
`n_draws_subsample=5000` (catalog max) at `n_paths_per_draw=500`
on `horizon=20` peaks around ~1.5 GB; the catalog cap of 5000 was
chosen per friction-points §3 OOM evidence to stay within typical
desk-laptop RAM.

## Methodology references

- **Carriero, A., Clark, T.E., Marcellino, M. (2019).** "Large
  Bayesian Vector Autoregressions with Stochastic Volatility and
  Non-Conjugate Priors." *Journal of Econometrics* 212(1):137-154.
  Implementation backbone for the BVAR-SV sampler.
- **Banbura, M., Giannone, D., Lenza, M. (2015).** "Conditional
  Forecasts and Scenario Analysis with Vector Autoregressions for
  Large Cross-Sections." *International Journal of Forecasting*
  31(3):739-756. Conditional-forecast machinery in
  `conditioning.py`.
- **Kim, S., Shephard, N., Chib, S. (1998).** "Stochastic
  Volatility: Likelihood Inference and Comparison with ARCH
  Models." *Review of Economic Studies* 65(3):361-393. Mixture-of-
  normals approximation for SV (KSC) in `_ksc_mixture.py`.
- **Carter, C.K., Kohn, R. (1994).** "On Gibbs Sampling for State
  Space Models." *Biometrika* 81(3):541-553. FFBS state-sampling
  in `_ffbs.py`.
- **Litterman, R. (1986).** "Forecasting with Bayesian Vector
  Autoregressions: Five Years of Experience." *Journal of Business
  & Economic Statistics* 4(1):25-38. Minnesota prior structure in
  `priors.py`.

## Coexistence with TSL's existing BVAR wrapper

TSL's `engine/techniques/bvar.py` is a small Phase 1/2 BVAR wrapper
implementing IRF/FEVD on top of statsmodels VAR with a
Normal-Inverse-Wishart conjugate posterior. It registers under
`technique_id="1c_bvar_irf_fevd"` and is unrelated to this
wrapper. Bond Yield Forecast registers under
`technique_id="bond_yield_forecast"` (aliases: `byf`,
`yield_forecast`). The two methods serve different use cases:

| Aspect | `1c_bvar_irf_fevd` (existing) | `bond_yield_forecast` (this) |
|---|---|---|
| Use case | Generic n-variable BVAR with IRF + FEVD | Treasury yield curve forecast conditioned on macro projections |
| Sampler | Closed-form NIW conjugate | Full Gibbs (CCM-2019) with stochastic volatility |
| Input | Excel cell selection (ctx.series) | 3-sheet xlsx workbook |
| Output | IRF / FEVD tables | Yield forecast percentile bands |
| Scope | ~250 LOC (engine/techniques/bvar.py) | ~7100 LOC subpackage (engine/techniques/bond_yield_forecast/) |

## Migration provenance

Migrated from the standalone `bvar-yield-forecaster` repo at the
`v1.0.0-session-0-complete` tag in Bond Yield Forecast Integration
Session 1 (commit `95f5f01`). Subpackage at
`engine/techniques/bond_yield_forecast/` contains 17 source modules
+ 14 test files. Smoke verified byte-identical to the pre-
migration baseline across all 6 numerical array sets
(`coefficients`, `A_lower_triangular`, `log_volatilities`, `mu`,
`omega`, `phi`, `target_paths`, `macro_paths`, `yield_paths`,
`projections_*`).

The standalone `bvar-yield-forecaster` repo retires at integration
Session 6 closeout. Subsequent improvements to Bond Yield Forecast
flow through TSL's normal modification discipline (per Phase 3 /
Phase 3.5 wrapper-modification standard).
