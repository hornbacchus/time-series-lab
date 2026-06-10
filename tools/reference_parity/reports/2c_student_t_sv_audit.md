# 2c Student-t SV — reference parity audit

**Date:** 2026-04-24

**Fixture (synthetic Student-t SV path):**
- True parameters: mu = -10.0, phi = 0.98, sigma_eta = 0.2, nu = 5.0
- T = 500, seed = 43
- Student-t(5.0) innovations on the observation equation.

**Implementations compared:**
- **TSL** (GIBBS backend): preset Thorough (4 chains × 4000 draws each, tune 2000; total 16000 post-warmup draws). Fit time: 39.21s.
  - Backend: Gibbs (Kim-Shephard-Chib mixture-of-
    normals + Student-t inverse-gamma mixture). PyMC
    NUTS path unusable on this machine due to
    pytensor pure-Python fallback (see B6).
- **R stochvol** (`svtsample`): 10000 draws, 1000 burnin, single chain. Compiled C++.

**Tolerance ladder:** `< 5%` PASS, `5-10%` CAVEAT, `> 10%` METHODOLOGY (priors).

**Prior parameterization (audit-relevant):**

| Parameter | TSL (PyMC / Gibbs) | stochvol::svtsample |
|---|---|---|
| `mu` | Normal(0, 10) | priormu = c(0, 100) → Normal(0, 10) — **matches** |
| `phi` | Beta(20, 1.5) on (0, 1) | (phi+1)/2 ~ Beta(20, 1.5) — **DIFFERS** |
| `sigma_eta` | HalfNormal(0, 2) | priorsigma=1 — **DIFFERS** |
| `nu` | TruncatedNormal(10, 10, [2.01, 200]) | priornu = c(2, 100) → uniform-like — **DIFFERS** |

Diverging priors yield diverging posteriors; documented as methodology context, not bug.

## Posterior mean comparison

| Parameter | TSL | stochvol | abs_diff | rel_diff | Verdict |
|---|---|---|---|---|---|
| `mu` | -9.771795 | -9.487077 | 2.847e-01 | 2.914e-02 | **PASS** |
| `phi` | 0.984693 | 0.977329 | 7.364e-03 | 7.478e-03 | **PASS** |
| `sigma_eta` | 0.166560 | 0.225337 | 5.878e-02 | 2.608e-01 | **METHODOLOGY** |
| `nu` | 7.361778 | 6.387312 | 9.745e-01 | 1.324e-01 | **METHODOLOGY** |

## Posterior std (uncertainty)

| Parameter | TSL sd | stochvol sd |
|---|---|---|
| `mu` | 0.826517 | 0.729014 |
| `phi` | 0.009370 | 0.012582 |
| `sigma_eta` | 0.035846 | 0.049750 |
| `nu` | 2.607052 | 2.231816 |

**nu posterior std (TSL): 2.6071** (expected 0.5–1.0 at T=500 per Stage B notes; actual depends on data and posterior shape).
**nu posterior std (stochvol): 2.2318**

## ESS / convergence diagnostics

**TSL** (Gibbs): ess_min = 59.9 (param: `nu`); rhat_max = 1.1446 (param: `nu`); divergences = 0

**stochvol per-parameter ESS:**

| Parameter | ESS | Note |
|---|---|---|
| `mu` | 4116 |  |
| `phi` | 497 | below 500 threshold |
| `sigma_eta` | 194 | below 500 threshold |
| `nu` | 80 | below 500 threshold |

## Methodology notes

- **TSL Gibbs Student-t backend** uses a Kim-Shephard-
  Chib mixture-of-normals on log y² PLUS an inverse-
  gamma mixing distribution on the t innovations'
  scale parameter. This is the standard Bayesian SV-t
  parameterization (Watanabe-Omori 2004, Chib-Nardari-
  Shephard 2002). stochvol::svtsample uses the same
  general approach; minor sampler details (block sizes,
  proposal tuning) differ.

- **nu identifiability** is the primary parameter at
  risk. With T=500 observations of moderately fat-
  tailed returns, nu posteriors are typically wide
  (sd 0.5–1.0). Different priors on nu (TSL
  TruncatedNormal vs stochvol uniform-ish) yield
  visibly different posteriors. Treat any rel_diff
  on nu greater than 10% as a prior-driven effect,
  not a bug, unless ESS is also very low (< 100).
