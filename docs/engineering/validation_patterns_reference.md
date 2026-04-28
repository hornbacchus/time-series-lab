# Validation Patterns Reference

**Status:** Reference document. Diagnostic tests + fix
patterns + empirical examples for the 5 failure modes
characterized during CAI Phase 2.

**Audience:** Wrapper-PR reviewers, future audit
practitioners, debugging engineers.

**Companion documents:**
- [Wrapper Development Standard](wrapper_development_standard.md) — directive ("must")
- [CAI Empirical Findings](cai_empirical_findings.md) — descriptive ("what we learned")

This document is **reference**: how to test for each
failure mode, how to fix it, and where it surfaced
empirically across 83 wrappers.

---

## 1. Validation-Presence Pattern

### 1.1 Empirical statement

**100% predictive across 77 extension wrappers.**

The validation-presence pattern says: a wrapper produces
zero CAI findings if and only if BOTH of these hold:

1. The wrapper has explicit input validation (allowlist
   gates for strings, range gates for numerics, consistency
   checks for multi-parameter surfaces) at the wrapper
   layer, OR
2. The wrapper exposes only a low-string-surface parameter
   set (numeric/bool only, with no if/elif/else chains
   dispatching on user strings).

The pattern's contrapositive: wrappers WITHOUT validation
AND with string-handling chains produced findings — and
the prediction was empirically correct in every observed
case across the CAI cycle.

### 1.2 Refined definition (post-Session 18)

The original validation-presence formulation pre-Session
17 was simpler: "wrappers with validation are clean;
wrappers without are buggy." Sessions 17-18 refined it to
include a third condition:

3. The wrapper does NOT short-circuit upstream validation
   via try/except suppression that swallows ValueError
   without surfacing actionable errors.

The refined predictor:
- WITH validation OR low math: 36 wrappers → 0 findings
- WITHOUT validation: 41 wrappers → 80 severe/op findings
  (all fixed inline)

### 1.3 Cross-reference to evidence

The pattern was verified across all extension sessions:

| Session | Verification |
|---|---|
| S6 | GARCH variant dispatch + EGARCH persistence formula — pre-existing tier validation guarded the math |
| S7 | har_rv: clean (numeric-only params) — "WITH low math" branch |
| S8 | caviar: clean (numeric + tier validation) — "WITH validation" branch |
| S9 | var/vecm: var clean, vecm 1 finding — silent string acceptance for `det_order` |
| S13 | Frequency-domain: 7 wrappers, 3 findings (fft, periodogram, lomb_scargle had string fall-throughs) |
| S14-S15 | Causality + Change-points: silent string-acceptance dominant pattern |
| S17 | **Stationarity tests:** 5 findings revealed try/except suppression as new failure mode |
| S18 | **State Space:** structural_ts has try/except fallback but pattern is SAFE-FALLBACK; framework refined |
| S19 | Missing data: 3 numeric-range coercions identified extension to "string acceptance" |
| S21 | **Eval/Uncertainty: 0 severe.** First clean batch since S8 — confirmed pattern's "low-string-surface" branch |
| S23 | **Tree forecasters: 0 severe.** Numeric-only wrappers ship clean |
| S25 | **N-HiTS / N-BEATS sibling propagation:** identical try/except-pass defect in two architectural siblings |

---

## 2. The Five Failure Modes

### 2.1 Mode 1: String acceptance via if/elif/else default

**Architectural cause:** Custom wrapper code dispatches on
a string parameter via `if x == "a": ... elif x == "b":
... else: do_default()`. The trailing `else` silently
captures all unrecognized strings and runs the default
branch.

#### Diagnostic test (Sweep 0 probe)

```python
# Pass clearly invalid string; verify rejection
res = wrapper.run(_ctx(y, params={"method": "zzz_invalid"}),
                  _null)
if res.get("status") == "success":
    # SEVERE: silent fall-through
    ...
elif res.get("status") == "failure":
    em = res.get("error_message") or ""
    if "Unknown method" in em:
        # CLEAN: explicit allowlist gate
        pass
    else:
        # OPERATIONAL: rejected but not with clean error
        ...
```

#### Fix pattern

```python
_METHOD_OPTS = ("a", "b", "c")
method = ctx.get_param("method", "a")
if method not in _METHOD_OPTS:
    return make_error_response(
        ctx,
        f"Unknown method '{method}'. Must be one of: "
        f"{', '.join(_METHOD_OPTS)}.",
        error_fixes=[
            "Use 'a' (description), 'b' (description), or "
            "'c' (description).",
        ],
    )
# downstream if/elif chain is now safe
if method == "a":
    ...
elif method == "b":
    ...
else:  # method == "c" — guaranteed by gate
    ...
```

#### Empirical examples

| F-ID | Wrapper | Parameter | Session |
|---|---|---|---|
| F-CL-GCC-WEIGHTING | gcc_phat_delay | weighting | 14 |
| F-CL-DTW-STEP | dtw_alignment_lag | step_pattern | 14 |
| F-CP-INT-TYPE | intervention_analysis | type | 15 |
| F-CP-PELT-PENALTY | pelt_change_points | penalty | 15 |
| F-CP-STL-DIRECTION | stl_esd_anomaly | direction | 15 |
| F-CD-CLASSIC-MODEL | classical_decompose | model | 16 |
| F-CD-X13-TRANSFORM | x13_seasonal_adjust | transform | 16 |
| F-SS-PF-MODEL | particle_filter | model | 18 |
| F-MV-DFM-TRANSFORM | dynamic_factor_model | transform | 22 |
| F-MV-FR-BASEFC | forecast_reconciliation | base_forecaster | 22 |
| F-MV-FR-TDWEIGHTS | forecast_reconciliation | top_down_weights | 22 |
| F-MV-PCA-ROTATION | pca_analysis | rotation | 22 |
| F-NN-LG-MODELTYPE | lstm_gru_forecast | model_type | 24 |
| F-ML-GP-KERNEL | gaussian_process_forecast | kernel | 26 |
| F-ML-SVR-KERNEL | svr_forecast | kernel | 26 |
| F-ETS-TREND | ets_hw | trend | 27 |
| F-ETS-SEASONAL | ets_hw | seasonal | 27 |
| F-CSD-COMPOSITE | critical_slowing_down | composite_method | 28 |

(Truncated; this mode produced ~20 findings across the
cycle, the dominant CAI bug class.)

#### Common variants

- **Lowercase normalization + slicing:** `method[:3].lower()`
  collapses "additive" / "ADDITIVE" / "additive_v2" all to
  `"add"`. Forbidden because it loses the user's original
  string and silently reaches the same default branch.
  Fix: allowlist BEFORE normalization, or normalize then
  allowlist.

- **Boolean-as-string handling:** `"true"` / `"false"` /
  `"none"` / `"null"` are commonly accepted as bool
  equivalents. This is fine when explicit, but the
  allowlist must enumerate all accepted spellings:
  `("none", "null", "false")` for "disabled".

- **Helper-layer dispatch:** Sometimes the if/elif/else
  is in a `_helper.py` module rather than in the wrapper.
  Audit the helper too. CSD's `_composite_ews_score`
  helper had the bug at the helper layer; the wrapper
  layer fix added the allowlist gate before reaching the
  helper.

---

### 2.2 Mode 2: HARMFUL try/except suppression

**Architectural cause:** Wrapper has its own try/except
that catches exceptions raised by the upstream library
(statsmodels, etc.) and stores the error in a per-series
or per-result dict, then continues with degraded output
and reports `status="success"` at the end.

#### Diagnostic test (Sweep 0 probe)

```python
# Pass invalid input; verify failure status, NOT success
res = wrapper.run(_ctx(y, params={"regression": "zzz"}),
                  _null)
if res.get("status") == "success":
    # Check audit_fields — does it report user's invalid value?
    af = res.get("audit_fields") or {}
    if af.get("regression") == "zzz":
        # SEVERE: try/except is HARMFUL
        ...
```

#### Identifying suppression

Inspect every try/except in the wrapper. For each:

1. Does the except clause RETURN make_error_response
   directly? → SAFE-PROPAGATE. Done.
2. Does it RETRY with different parameters and surface
   the original error if all retries fail? → SAFE-FALLBACK.
   Done.
3. Does it CATCH-AND-CONTINUE without re-raising or
   converting to make_error_response? → POTENTIAL HARMFUL.
   Inspect downstream code — does the wrapper return
   `status="success"` at the end despite the inner failure?
   If yes, HARMFUL.

#### Fix pattern

The fix is usually to ADD an allowlist gate BEFORE the
try block, so invalid input never reaches the upstream
library. The library's ValueError stops being relevant
because the allowlist already rejected the input.

```python
# Pre-fix (HARMFUL):
def _run_test(values, regression):
    try:
        result = statsmodels_test(values, regression=regression)
        return {"status": "success", "regression": regression, ...}
    except Exception as e:
        return {"status": "success",  # ← HARMFUL!
                "regression": regression, "error": str(e)}

# Post-fix:
def run(ctx, ...):
    regression = ctx.get_param("regression", "c")
    if regression not in _REGRESSION_OPTS:
        return make_error_response(...)
    # Now invalid input never reaches _run_test
    return _run_test(values, regression)
```

#### Empirical examples

The HARMFUL pattern was observed in CAI Phase 2 ONLY in
Session 17 (stationarity tests):

| F-ID | Wrapper | Parameter | Session |
|---|---|---|---|
| F-ST-ADF-REGRESSION | adf_test | regression | 17 |
| F-ST-ADF-AUTOLAG | adf_test | autolag | 17 |
| F-ST-KPSS-REGRESSION | kpss_test | regression | 17 |
| F-ST-KPSS-NLAGS | kpss_test | nlags | 17 |
| F-ST-PP-REGRESSION | pp_test | regression | 17 |

In each case, the wrapper called statsmodels (which
raised ValueError on invalid input), caught the
ValueError in `_run_*_single`, stored it in a per-series
error dict, and returned `status="success"` at the
top-level `run()`. The audit_fields recorded the user's
invalid string.

Post-fix, all 5 use SAFE-PROPAGATE via wrapper-layer
allowlist gates. No HARMFUL try/except remains in the
codebase as of Session 28.

---

### 2.3 Mode 3: Numeric range silent coercion

**Architectural cause:** Wrapper has a check like `if x <
1: x = 1` that silently changes the user's value without
returning an error. User passes `horizon=-1`, gets
`horizon=1` silently.

#### Diagnostic test (Sweep 0 probe)

```python
# Pass out-of-range numeric; verify failure status
res = wrapper.run(_ctx(y, params={"horizon": -1}), _null)
if res.get("status") == "success":
    af = res.get("audit_fields") or {}
    if af.get("horizon") == 1:
        # OPERATIONAL: silent coercion to 1
        ...
```

#### Fix pattern

```python
horizon = int(ctx.get_param("horizon", 10))
if horizon < 1:
    return make_error_response(
        ctx,
        f"horizon must be >= 1. Got {horizon}.",
        error_fixes=["Use a positive integer."],
    )
```

#### Empirical examples

The most prolific finding class in absolute count (~25
findings):

| F-ID | Wrapper | Param | Session |
|---|---|---|---|
| F-EU-BB-BLOCKLEN | block_bootstrap | block_length | 21 |
| F-EU-BB-CONFLEVEL | block_bootstrap | confidence_level | 21 |
| F-EU-CI-CALFRAC | conformal_intervals | cal_fraction | 21 |
| F-EU-FC-HOLDOUT | forecast_combination | holdout_fraction | 21 |
| F-EU-RE-TRIM | robust_estimators | trim_fraction | 21 |
| F-MV-BVAR-LAMBDA | bvar | lambda1/2/3 | 22 |
| F-TR-{GBM,LGBM,RF,XGB}-NLAGS | tree forecasters | n_lags | 23 |
| F-TR-{GBM,LGBM,RF,XGB}-HORIZON | tree forecasters | horizon | 23 |
| F-NN-{LG,TCN,TF,NB}-HORIZON | neural sequence | horizon | 24 |
| F-SN-NHITS-HORIZON | nhits_forecast | horizon | 25 |
| F-SN-AE-CONTAMINATION | autoencoder_anomaly | contamination | 25 |
| F-SN-ESN-HORIZON | echo_state_network | horizon | 25 |
| F-SN-ESN-SPECTRAL | echo_state_network | spectral_radius | 25 |
| F-SN-ESN-LEAK | echo_state_network | leak_rate | 25 |
| F-ML-{GP,P,QR,SVR}-HORIZON | statistical ML | horizon | 26 |
| F-ML-GP-CONFLEVEL | gaussian_process_forecast | confidence_level | 26 |
| F-ML-QR-NLAGS | quantile_regression_model | n_lags | 26 |
| F-ETS-HORIZON | ets_hw | horizon | 27 |
| F-CSD-ROLLINGWIN | critical_slowing_down | rolling_window | 28 |
| F-CSD-ROLLINGWIN-NEG | critical_slowing_down | rolling_window | 28 |
| F-CSD-KENDALL | critical_slowing_down | kendall_lookback | 28 |

#### Common range patterns

| Parameter type | Required range | Severity if violated |
|---|---|---|
| horizon (forecast steps) | `>= 1` | operational |
| n_lags / max_lag | `>= 1` | operational |
| n_estimators / n_particles | `>= 10` (typical), at minimum `>= 1` | operational |
| confidence_level / alpha | `0 < x < 1` (open) | operational |
| cal_fraction / holdout_fraction | `0 < x < 1` | operational |
| trim_fraction / winsor_fraction | `0 < x < 0.5` | operational |
| Bayesian shrinkage / regularization | `> 0` | operational (mathematically undefined for ≤ 0) |
| spectral_radius (ESN) | `> 0` | operational |
| leak_rate (ESN) | `0 <= x <= 1` | operational |
| ridge_alpha / l2_penalty | `> 0` | operational |

---

### 2.4 Mode 4: String-handling chain fall-through

**Architectural cause:** Same as Mode 1 in mechanism, but
the if/elif/else is buried inside a HELPER function called
from the wrapper, not in the wrapper itself. The wrapper
calls `helper(method=user_value)` and the helper
internally has the if/elif/else with silent fall-through.

#### Diagnostic test

Same as Mode 1: pass invalid string, verify rejection.

#### Fix pattern

Add the allowlist gate at the WRAPPER layer (before
calling the helper), even if the bug is in the helper.
This is preferable because:

1. The wrapper layer has access to `make_error_response`
   and produces actionable errors.
2. Fixing at the wrapper layer doesn't risk breaking
   other consumers of the helper.
3. Multiple wrappers can share the same helper and each
   gate independently.

```python
# Pre-fix:
def run(ctx, ...):
    method = ctx.get_param("composite_method", "default")
    score = _composite_helper(taus, method=method)  # silent fall-through inside helper
    return ...

# Post-fix:
def run(ctx, ...):
    method = ctx.get_param("composite_method", "default")
    if method not in _METHOD_OPTS:
        return make_error_response(...)
    score = _composite_helper(taus, method=method)
    return ...
```

#### Empirical examples

| F-ID | Wrapper | Helper | Session |
|---|---|---|---|
| F-CSD-COMPOSITE | critical_slowing_down | _csd_helpers._composite_ews_score | 28 |
| F-MV-FR-BASEFC | forecast_reconciliation | _base_forecast | 22 |

These cases show that helpers can also silently coerce
even when the wrapper looks clean. The wrapper-layer gate
is the right fix because it's user-facing and provides
the actionable error message.

---

### 2.5 Mode 5: Multi-parameter consistency violation

**Architectural cause:** Two parameters interact (e.g.,
`damped_trend` requires `trend != None`, `seasonal='mul'`
requires positive observations). The wrapper silently
modifies one parameter when the combination is
inconsistent, often with a warning. This is the
loud-and-coerced antipattern.

#### Diagnostic test

```python
# Pass a known-inconsistent combination
res = wrapper.run(_ctx(y, params={
    "trend": None,
    "damped_trend": True,
}), _null)
if res.get("status") == "success":
    # Look at warnings
    warns = res.get("warnings") or []
    if any("damped" in str(w).lower() for w in warns):
        # Wrapper silently disabled — even with warning, this is
        # SEVERE per the loud-and-coerced rule
        ...
```

#### Fix pattern

```python
if damped_trend and trend is None:
    return make_error_response(
        ctx,
        "damped_trend=True requires trend to be set "
        "('add' or 'mul'). Got trend=None.",
        error_fixes=[
            "Set trend='add'/'mul' to use damped trend, or "
            "set damped_trend=False.",
        ],
    )
```

#### Empirical examples

| F-ID | Wrapper | Inconsistency | Session |
|---|---|---|---|
| F-NN-TF-DMODEL | transformer_forecast | d_model not divisible by n_heads | 24 |
| F-ETS-MUL-NEG-TREND | ets_hw | trend='mul' + non-positive data | 27 |
| F-ETS-MUL-NEG-SEAS | ets_hw | seasonal='mul' + non-positive data | 27 |
| F-ETS-DAMPED-NOTREND | ets_hw | damped_trend=True + trend=None | 27 |

---

## 3. try/except Taxonomy

Every try/except in wrapper code falls into one of four
classes:

### 3.1 SAFE-PROPAGATE

The except clause produces an actionable error response
that surfaces to the user.

```python
try:
    fit = model.fit(...)
except Exception as e:
    return make_error_response(
        ctx,
        f"Fitting failed: {e}",
        error_fixes=["Try a simpler specification."],
    )
```

This is the most common pattern. SAFE.

### 3.2 SAFE-FALLBACK

The except clause retries with a DIFFERENT specification.
If all retries fail, the final error propagates as an
actionable message (typically via the outer SAFE-PROPAGATE
clause).

```python
try:
    fit = model.fit(complex_spec)
except Exception:
    # Retry with simpler spec
    fit = model.fit(simple_spec)
```

Used by: `structural_ts`, `ets_hw`, neural wrappers'
sklearn fallback when torch unavailable, prophet's
seasonal-naive fallback when prophet unavailable.

The pattern is SAFE only if (a) the retry is with a
genuinely DIFFERENT specification (not the same
parameters), and (b) the wrapper's outer try/except
surfaces error if the retry also fails.

`structural_ts` is the canonical example: when user
passes invalid `level="zzz"`, both the original and
fallback attempts fail with the same upstream
ValueError, which propagates through the outer except
to make_error_response. The user sees "Invalid level
specification" not "Fallback also failed".

### 3.3 SAFE-RERAISE

The except clause catches a specific exception, performs
some action (e.g., logging, adding context), and
re-raises.

```python
try:
    do_thing()
except SomeException as e:
    log.warning(f"do_thing failed: {e}")
    raise  # propagate
```

Less common in TSL but valid.

### 3.4 HARMFUL

The except clause catches an exception and returns
`status="success"` (or equivalent) without surfacing the
exception. This is the Session 17 ADF/KPSS/PP failure
mode.

```python
# HARMFUL:
def _run_single(...):
    try:
        result = library.test(...)
    except Exception as e:
        return {"error": str(e), "stat": None, "pvalue": None}

def run(ctx, ...):
    out = _run_single(...)
    if out.get("error"):
        # Wrapper records error in audit_fields but returns success!
        return make_response(ctx, status="success",
                              audit_fields={"error": out["error"], ...},
                              ...)
```

The HARMFUL pattern produces wrappers that report
"computation succeeded" while the actual computation
failed. audit_fields is misleading; users can't tell
their input was invalid.

**Forbidden by [Wrapper Development Standard](wrapper_development_standard.md) §2.4.**

If a wrapper has multiple series and one fails, the
correct behavior is to surface that one failure
explicitly (in warnings + a per-series error indicator)
while the wrapper-level status remains success ONLY if
at least one series produced valid output. If all
series failed, status must be "failure".

---

## 4. Audit Methodology

### 4.1 Three-technique audit structure

CAI Phase 2 used a 3-technique audit per wrapper:

| Technique | Purpose | Output |
|---|---|---|
| Sweep 0 | Input validation matrix | List of findings (severe / op / cosmetic) |
| Technique 1 | Compressed parameter sweep | Validates parameters exercise expected behavior |
| Technique 2 | Real-data stress test | Macro fixtures verify wrapper handles realistic input |
| Technique 3 | Adversarial canonicals | Edge cases (white noise, constant, short, etc.) |

### 4.2 When to use which technique

- **For new wrapper PRs:** Sweep 0 only is sufficient.
  The pre-merge canonical suite covers Techniques 2-3.
- **For wrapper refactors:** Sweep 0 + Technique 3
  (re-run canonicals on changed code).
- **For audit cycles like CAI:** Full 3-technique stack
  per wrapper.

### 4.3 CAL-R6 LOC budget protocol

Per CAI methodology:
- **Solo audits** (1 wrapper per session): 100-LOC budget
  for inline fixes.
- **Multi-wrapper batches** (4+ wrappers): 150-LOC
  budget per session.
- **Same-bug-class bundling:** acceptable up to 5
  findings if all are the same architectural pattern
  and fits within budget.
- **Stop and defer:** if cumulative LOC exceeds budget
  or findings exceed 6 severe, defer 4th+ to follow-up
  commits.

### 4.4 Sweep 0 probe template

```python
def sweep_0_validation():
    findings = []

    # 1. Baseline
    res, dt, _ = _safe_run(_ctx(y_valid))
    print(f"  baseline: {res.get('status')}")

    # 2. Each string param: valid + invalid
    for opt in valid_string_options:
        res, _, _ = _safe_run(_ctx(y, params={"strparam": opt}))
        # Should succeed for valid options

    res, _, _ = _safe_run(_ctx(y, params={"strparam": "zzz"}))
    if res and res.get("status") == "success":
        findings.append({
            "id": "F-...",
            "severity": "severe",
            "description": "...",
        })

    # 3. Each numeric param: out-of-range
    res, _, _ = _safe_run(_ctx(y, params={"numparam": -1}))
    if res and res.get("status") == "success":
        findings.append({
            "id": "F-...",
            "severity": "operational",
            ...
        })

    # 4. Multi-parameter consistency violations
    res, _, _ = _safe_run(_ctx(y, params={
        "param1": "a",
        "param2": True,  # known inconsistent with param1='a'
    }))
    if res and res.get("status") == "success":
        findings.append({
            "id": "F-...",
            "severity": "severe",
            ...
        })

    return findings
```

---

## Appendix A: Per-finding cross-reference index

Below is the master cross-reference of all 88 CAI Phase
2 findings, indexed by F-ID, sorted by session.

| F-ID | Wrapper | Mode | Severity | Session |
|---|---|---|---|---|
| F-K-FILTER-OUTPUT | kalman_filter | (legacy session 1) | op | 1 |
| F-K-SMOOTHER-OUTPUT | kalman_smoother | (legacy session 1) | op | 1 |
| F-HARCJ-* | har_cj | various | various | 2 |
| F-EVT-* | evt_pot_gpd | cosmetic | cosm | 3 |
| F-J-* | johansen_cointegration | cosmetic | cosm | 4 |
| F-SV-* | stochastic_volatility | cosmetic | cosm | 5 |
| F-G-DISPATCH | garch_model | dispatch routing | severe | 6 |
| F-G-PERSIST-FORMULA | garch_model | EGARCH formula | severe | 6 |
| F-VECM-* | vecm_model | string acceptance | severe | 9 |
| F-PMD-START | auto_arima | start_P | severe | 10 |
| F-MS-NREGIMES | markov_switching | n_regimes | severe | 12 |
| F-FFT-WINDOW | fft_spectrum | window | severe | 13 |
| F-PSD-METHOD | periodogram_spectral_density | method | severe | 13 |
| F-LS-NORMALIZATION | lomb_scargle | normalization | severe | 13 |
| F-CL-GCC-WEIGHTING | gcc_phat_delay | weighting | severe | 14 |
| F-CL-DTW-STEP | dtw_alignment_lag | step_pattern | severe | 14 |
| F-CP-INT-TYPE | intervention_analysis | type | severe | 15 |
| F-CP-PELT-PENALTY | pelt_change_points | penalty | severe | 15 |
| F-CP-STL-DIRECTION | stl_esd_anomaly | direction | severe | 15 |
| F-CD-CLASSIC-MODEL | classical_decompose | model | severe | 16 |
| F-CD-X13-TRANSFORM | x13_seasonal_adjust | transform | severe | 16 |
| F-ST-ADF-REGRESSION | adf_test | regression (HARMFUL) | severe | 17 |
| F-ST-ADF-AUTOLAG | adf_test | autolag (HARMFUL) | severe | 17 |
| F-ST-KPSS-REGRESSION | kpss_test | regression (HARMFUL) | severe | 17 |
| F-ST-KPSS-NLAGS | kpss_test | nlags (HARMFUL) | severe | 17 |
| F-ST-PP-REGRESSION | pp_test | regression (HARMFUL) | severe | 17 |
| F-SS-PF-MODEL | particle_filter | model | severe | 18 |
| F-MD-* | missing_data batch | various | various | 19 |
| F-TF-* | transfer_function | various | various | 20 |
| F-EU-{BB,CI,FC,RE}-* | eval/uncertainty | numeric range | op | 21 |
| F-MV-DFM-TRANSFORM | dynamic_factor_model | transform | severe | 22 |
| F-MV-FR-BASEFC | forecast_reconciliation | base_forecaster | severe | 22 |
| F-MV-FR-TDWEIGHTS | forecast_reconciliation | top_down_weights | severe | 22 |
| F-MV-PCA-ROTATION | pca_analysis | rotation | severe | 22 |
| F-MV-BVAR-LAMBDA | bvar | shrinkage | op | 22 |
| F-TR-{GBM,LGBM,RF,XGB}-{NLAGS,HORIZON,NEST} | tree forecasters | numeric range | op | 23 |
| F-NN-LG-MODELTYPE | lstm_gru_forecast | model_type | severe | 24 |
| F-NN-NB-STACKTYPES | nbeats_forecast | stack_types | severe | 24 |
| F-NN-TF-DMODEL | transformer_forecast | d_model/n_heads | op | 24 |
| F-NN-{LG,TCN,TF,NB}-HORIZON | neural sequence | horizon | op | 24 |
| F-SN-NHITS-POOLING | nhits_forecast | pooling_sizes | severe | 25 |
| F-SN-NHITS-POOLING-NEG | nhits_forecast | pooling_sizes | severe | 25 |
| F-SN-{NHITS,AE,ESN}-* | specialized neural | various | various | 25 |
| F-ML-GP-KERNEL | gaussian_process_forecast | kernel | severe | 26 |
| F-ML-SVR-KERNEL | svr_forecast | kernel | severe | 26 |
| F-ML-{GP,P,QR,SVR}-* | statistical ML | various | various | 26 |
| F-ETS-TREND | ets_hw | trend | severe | 27 |
| F-ETS-SEASONAL | ets_hw | seasonal | severe | 27 |
| F-ETS-MUL-NEG-TREND | ets_hw | mul + neg | severe | 27 |
| F-ETS-MUL-NEG-SEAS | ets_hw | mul + neg | severe | 27 |
| F-ETS-DAMPED-NOTREND | ets_hw | damped + no-trend | op | 27 |
| F-ETS-HORIZON | ets_hw | horizon | op | 27 |
| F-CSD-COMPOSITE | critical_slowing_down | composite_method | severe | 28 |
| F-CSD-ROLLINGWIN-NEG | critical_slowing_down | rolling_window | severe | 28 |
| F-CSD-ROLLINGWIN | critical_slowing_down | rolling_window | op | 28 |
| F-CSD-KENDALL | critical_slowing_down | kendall_lookback | op | 28 |

For full per-finding diagnostic detail, see the
appropriate session findings doc under
`docs/calibration_audit/`.

---

**Last revised:** 2026-04-28 (Session 29).
