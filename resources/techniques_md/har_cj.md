# HAR-CJ (Heterogeneous Autoregressive with Continuous + Jump decomposition)

## What It Does

HAR-CJ (Andersen, Bollerslev & Diebold 2007) is a **distinct model** from HAR-RV (Corsi 2009), not a mode of it. HAR-RV treats realized variance as a single cascade (daily / weekly / monthly averages). HAR-CJ first **decomposes each day's realized variance into a continuous component C_t and a jump component J_t**, then fits a 7-regressor HAR-family regression with separate cascades for C and J. The central empirical finding of ABD 2007 — that jumps have near-zero persistence while continuous volatility is highly persistent — is directly exposed in the wrapper's audit fields and Tier 1 rendering.

## When to Use It

- Risk-management applications where jump-adjusted volatility matters more than total realized volatility
- Research on whether realized volatility dynamics are driven by persistent continuous processes or transient jumps
- Model comparison against HAR-RV to quantify the benefit of jump decomposition
- Series where upstream intraday preprocessing has produced paired RV and BV (bipower variation) estimates
- Stress testing where the "typical day" versus "jump day" distinction changes the forecast

## Key Assumptions

- Realized variance can be meaningfully decomposed into continuous and jump contributions
- Bipower variation (BV) is a robust-to-jumps estimator of integrated variance (classical result; Barndorff-Nielsen & Shephard 2004)
- The BNS ratio test correctly identifies jump days at the user-chosen significance level α
- Intraday sampling frequency M is reported correctly (the z-statistic denominator scales with √M)
- After decomposition, C_t and J_t follow a linear HAR-style cascade with daily / weekly / monthly horizons
- Residuals satisfy standard OLS assumptions (iid normal is a simplification; HAR residuals often show mild autocorrelation)

## Outputs

- **HAR-CJ Coefficients**: β₀ plus 6 regressors — 3 continuous (β_cd, β_cw, β_cm) and 3 jump (β_jd, β_jw, β_jm) with standard errors, t-stats, p-values, and bootstrap CIs (Balanced / Thorough presets)
- **Jump Detection Summary**: α, z-threshold, jumps count / fraction, mean jump contribution as % of RV, max observed z-statistic, TQ approximation flag
- **Model Fit**: R² / adjusted R² / AIC / BIC / residual SE; model label (HAR-CJ or log-HAR-CJ); lag configuration
- **Residual Diagnostics** (Balanced / Thorough): Ljung-Box Q(10), Jarque-Bera, Durbin-Watson
- **Fitted Values** time series for visualization

## Input Contract

HAR-CJ requires **two or three aligned input series** and one required parameter:

- `series[0]` = realized variance (RV) — required
- `series[1]` = bipower variation (BV) — required
- `series[2]` = realized tripower quarticity (TQ) — optional; if absent, falls back to TQ ≈ BV² with a Tier 3 D2 honest-disclosure trigger
- `ctx.params["M"]` = intraday sampling frequency (number of intraday return intervals used upstream when computing RV and BV) — **required, no default**

The wrapper fails cleanly with an informative error if RV or BV is missing, or if M is not supplied.

## Technical Details

### Jump detection (Barndorff-Nielsen–Shephard ratio test)

```
Z_t = (RV_t − BV_t) / √(θ · max(TQ_t, BV_t²) / M)
```

where θ = (π/2)² + π − 5 ≈ 0.609 is the asymptotic variance constant from Huang & Tauchen (2005). Days with Z_t > Φ⁻¹(1 − α) are classified as jump days (α default 0.01 ⇒ threshold ≈ 2.326).

A numerical safeguard (D6): when RV < BV (rare microstructure artifact), the wrapper forces `is_jump = False` regardless of z-statistic sign. Jump magnitudes are capped at `max(RV − BV, 0)` so J_t ≥ 0 by construction.

### Decomposition

```
J_t = max(RV_t − BV_t, 0)    if is_jump_t     else 0
C_t = RV_t − J_t             (equals BV_t on jump days, RV_t otherwise)
```

### HAR-CJ regression

```
y_t = β_0
    + β_cd · C_{t-1} + β_cw · avg_wk(C) + β_cm · avg_mo(C)
    + β_jd · J_{t-1} + β_jw · avg_wk(J) + β_jm · avg_mo(J)
    + ε_t
```

where `y_t` inherits HAR-RV's forward-averaging semantics (forward average over h_ahead days when h_ahead > 1). OLS estimation with optional preset-gated bootstrap CIs.

### Parameter expectations (ABD 2007)

On typical equity index data:

- **Continuous persistence** (Σβ_c = β_cd + β_cw + β_cm) typically 0.7–0.9 — volatility is highly persistent.
- **Jump persistence** (Σβ_j = β_jd + β_jw + β_jm) typically near zero — jumps are mostly transient, with little predictive content for future RV.
- β_cd dominates β_jd in magnitude and significance.

The Tier 1 rendering makes this contrast explicit in every run.

### TQ approximation (when not supplied)

Full realized tripower quarticity is:

```
TQ_t = M · μ_{4/3}⁻³ · Σ |r_i|^{4/3} · |r_{i-1}|^{4/3} · |r_{i-2}|^{4/3}
```

where `μ_{4/3} = 2^{2/3} · Γ(7/6) / √π ≈ 0.809`. If the user does not supply TQ as `series[2]`, the wrapper substitutes BV² — a jump-robust lower bound on the true integrated quarticity. This is conservative (makes jump detection slightly less sensitive) and is disclosed via the Tier 3 D2 trigger.

## Interpretation

Every HAR-CJ run emits a two-tier plain-language Interpretation block with a distinct "decomposition-regression-with-contrast" Tier 1 shape.

**Plain-Language Finding (Tier 1)** — names HAR-CJ with the Andersen-Bollerslev-Diebold 2007 citation, states the jump fraction (N of M days classified as jumps at the specified α), reports the mean jump contribution as % of RV, and — most importantly — contrasts the continuous persistence sum (Σβ_c) against the jump persistence sum (Σβ_j) with an explicit "consistent with / in contrast to" alignment against the ABD 2007 expected finding. Includes forecaster-family baseline comparison and R² fit metric.

**Technical Interpretation (Tier 2)** — full 7-regressor regression equation with coefficient values and persistence-sum breakdown; AIC / BIC on T effective observations; residual diagnostics (Ljung-Box, Jarque-Bera); full jump-detection methodology (BNS z-statistic formula, θ constant, M, threshold, max observed z); conditional TQ-approximation disclosure; input contract reminder; scale note (RV-scale, not return-scale) and annualization (×√252); OLS-SE caveat (not HAC-corrected); log-HAR-CJ note (J has zeros ⇒ log-space spikes); refit suggestions pointing to HAR-RV for pure cascade or to upstream M / BV verification if jump fraction looks implausible.

**Caveats (Tier 3, conditional)**:
- **D1 `jump_fraction_unusual`**: fires when jump fraction < 0.5% (half the nominal α = 0.01 rate — suggests M or α mis-set) OR > 20% (microstructure noise or unusual regime).
- **D2 `tq_approximated_disclosure`**: fires when TQ was derived from BV² rather than supplied; warns about borderline-classification precision.
- **D3 `jump_persistence_negative`**: fires when any β_j* is significantly negative (p < 0.05 AND coefficient < 0); ABD 2007 predicted near-zero positive — negative is an anomaly.
- **D4 `jump_explains_excess_variation`**: fires when mean jump contribution > 50% of RV; unusual and suggests BV mis-estimation or extreme regime.
- **Inherited RMSE-exceeds-baseline**: fires when HAR-CJ fit RMSE ≥ rolling-22-period mean RV RMSE.
- **Inherited low-R²**: fires when R² < 0.30.
