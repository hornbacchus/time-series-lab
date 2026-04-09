# Auto-ARIMA

## What It Does

Auto-ARIMA automates the selection of the best ARIMA or SARIMA model by systematically searching over combinations of (p, d, q) and (P, D, Q)_s orders. It uses unit root tests to determine differencing, then evaluates candidate models using information criteria, returning the model that balances fit and parsimony without requiring manual ACF/PACF interpretation.

## When to Use It

- You want ARIMA/SARIMA forecasting without manually identifying model orders
- You are processing many series in batch and cannot inspect each one individually
- You want a defensible, reproducible model selection procedure
- You are uncertain whether your series needs seasonal differencing or how many AR/MA terms are appropriate
- You need a quick but statistically principled forecast

## Key Assumptions

- The same assumptions as ARIMA/SARIMA apply: stationarity after differencing, white noise residuals
- The true model can be reasonably approximated by an ARIMA(p,d,q)(P,D,Q)_s within the search range
- The information criterion used (AIC, AICc, or BIC) provides a good balance of fit and complexity for your use case
- The search range is broad enough to include the best model

## Outputs

- **Selected model order**: the (p, d, q)(P, D, Q)_s specification chosen
- **Point forecasts and prediction intervals**
- **Estimated parameters** with standard errors
- **Information criterion value** for the selected model
- **Search trace** (optional): showing all models evaluated and their criteria values
- **Residual diagnostics** for the chosen model

## Technical Details

The dominant auto-ARIMA algorithm is the **Hyndman-Khandakar** stepwise procedure, used in the R `forecast` package and Python's `pmdarima`:

**Step 1 -- Determine differencing orders**:
- **d**: Apply the KPSS test iteratively. Start with d=0; if the test rejects stationarity, increment d. Repeat until the test does not reject or d reaches `max_d` (default 2).
- **D**: Apply the OCSB (Osborn-Chui-Smith-Birchenhall) test or the Canova-Hansen test to determine if seasonal differencing is needed. Usually D = 0 or 1.

**Step 2 -- Define the search space**:
- p ranges from 0 to `max_p` (default 5)
- q ranges from 0 to `max_q` (default 5)
- P ranges from 0 to `max_P` (default 2)
- Q ranges from 0 to `max_Q` (default 2)

**Step 3 -- Stepwise search**:

Rather than evaluating all combinations (which could be hundreds), the stepwise algorithm:

1. Fit four initial models: ARIMA(0,d,0), ARIMA(2,d,2), ARIMA(1,d,0), ARIMA(0,d,1), each with and without a constant (if d <= 1). Include seasonal terms if D was determined.
2. Select the model with the lowest AICc as the current best.
3. From the current best, generate candidate models by varying p and q by +/-1 and toggling the constant term. For seasonal models, also vary P and Q by +/-1.
4. Fit all candidates and update the current best if any candidate has a lower AICc.
5. Repeat step 3-4 until no improvement is found (convergence).

**Information criteria used**:
- **AICc** (default): `AICc = AIC + 2k(k+1)/(n-k-1)`, corrects for small samples.
- **AIC**: `-2 log(L) + 2k`
- **BIC**: `-2 log(L) + k log(n)`, penalizes complexity more heavily, tends to select simpler models.

**Grid search alternative**: Instead of stepwise, an exhaustive grid search evaluates all combinations within the specified ranges. This is slower but guaranteed to find the global optimum within the search space. The stepwise approach can get trapped in local optima but is typically 5-20x faster.

**Practical considerations**:
- If the algorithm fails to converge for a candidate model (common with near-unit-root parameters), that model is skipped.
- When `d + D >= 2`, the constant term is excluded to avoid explosive forecasts.
- A maximum model order constraint `p + q + P + Q <= max_order` (default 5) prevents overly complex models.
