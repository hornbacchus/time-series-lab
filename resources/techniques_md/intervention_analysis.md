# Intervention Analysis

## What It Does

Intervention analysis models the **effect of a known external event** on a time series. When you know that a specific event occurred at a particular time (a policy change, natural disaster, marketing campaign, or system failure), intervention analysis quantifies the magnitude, shape, and duration of its impact. It extends ARIMA modeling by including intervention variables that represent different types of effects: sudden and permanent, sudden and temporary, or gradual and permanent.

## When to Use It

- A known event occurred at a specific time and you want to measure its impact
- Policy evaluation requires estimating the effect of a regulation, tax change, or program launch
- You need to model the response pattern of a series to a shock (immediate vs. gradual, permanent vs. decaying)
- Marketing mix modeling requires measuring campaign lift above baseline
- You want to produce forecasts that account for known future interventions

## Key Assumptions

- The time of the intervention is known exactly
- The type of intervention response (pulse, step, ramp) is correctly specified or can be identified
- The underlying ARIMA process (without the intervention) is correctly modeled
- There is only one intervention at a time (or multiple interventions can be separated)
- The effect is deterministic given the intervention type (not random)

## Outputs

- **Intervention effect estimates**: the magnitude and timing of the impact
- **Response pattern**: how the effect unfolds and decays over time
- **Counterfactual series**: what the series would have looked like without the intervention
- **Statistical significance**: whether the intervention effect is significantly different from zero
- **Adjusted series**: the original series with the intervention effect removed

## Technical Details

**Model formulation**: The intervention model combines a transfer function for the intervention variable with an ARIMA noise model:

`Y_t = sum_j v_j(B) X_{j,t}^{(T_j)} + N_t`

where `X_{j,t}^{(T_j)}` is the intervention variable for event j at time T_j, `v_j(B)` is the transfer function describing the response shape, and `N_t ~ ARIMA(p,d,q)` is the background process.

**Intervention variable types**:

1. **Pulse variable**: `P_t^{(T)} = 1` if t = T, 0 otherwise. Represents a one-time shock.

2. **Step variable**: `S_t^{(T)} = 1` if t >= T, 0 otherwise. Represents a permanent level shift. Note: `S_t^{(T)} = P_t^{(T)} / (1 - B)`.

3. **Ramp variable**: `R_t^{(T)} = t - T + 1` if t >= T, 0 otherwise. Represents a gradual, linearly increasing effect.

**Response patterns** (combining intervention variables with transfer functions):

1. **Abrupt, permanent (step change)**: `omega * S_t^{(T)}`
   Effect: jumps by omega at time T and stays there.

2. **Abrupt, temporary (pulse decay)**: `omega / (1 - delta B) * P_t^{(T)}`
   Effect: jumps by omega at T, then decays geometrically with rate delta (0 < delta < 1). Returns to baseline eventually.

3. **Gradual, permanent**: `omega / (1 - delta B) * S_t^{(T)}`
   Effect: starts at time T and gradually approaches omega / (1 - delta) as t -> infinity. Useful for effects that build up over time.

4. **Temporary pulse (additive outlier)**: `omega * P_t^{(T)}`
   Effect: omega at time T only, zero before and after.

**Identification of response type**:
1. Fit a preliminary ARIMA model without intervention variables.
2. Examine residuals around the intervention time for clues about the response pattern.
3. Fit candidate intervention models (pulse, step, pulse-decay) and compare using AIC/BIC.
4. Check residual diagnostics for the selected model.

**Estimation**: Joint MLE of intervention parameters (omega, delta) and ARIMA parameters (phi, theta). The intervention variables enter the model as known regressors, making estimation straightforward once the type is specified.

**Multiple interventions**: Multiple events at different times can be included simultaneously: `Y_t = v_1(B) X_{1,t}^{(T_1)} + v_2(B) X_{2,t}^{(T_2)} + ... + N_t`. Each intervention has its own response function.

**Automatic outlier detection**: A related technique fits the ARIMA model and then systematically tests for the presence of additive outliers (AO), level shifts (LS), temporary changes (TC), and innovational outliers (IO) at each time point, using t-statistics to identify significant interventions. This is built into X-13-ARIMA-SEATS and other packages.

**Counterfactual analysis**: The estimated counterfactual (no-intervention) series is `Y_t - v(B) X_t^{(T)}`, giving the series that would have been observed without the event. The cumulative intervention effect over time sums the differences.

## Interpretation

**Plain-Language Finding (Tier 1)** - event-centered (distinct from detection-based change-point specs). Leads with the top intervention's date, label, effect coefficient, p-value, CI, significance verdict, count of significant effects, and scale reference.

**Technical Interpretation (Tier 2)** - ARIMA order with intervention dummies, Ljung-Box residual diagnostic, AIC improvement over no-intervention baseline.

**Caveats (Tier 3, conditional)**:
- Some interventions not significant at 5%.
- AIC improvement < 2 over no-intervention - interventions add little.
- Residual Ljung-Box rejects - ARMA structure inadequate.
