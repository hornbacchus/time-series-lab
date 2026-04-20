# Canonical pattern for iterating `statsmodels` fit parameters

This note documents the engineering lesson from the Commit-1 alignment
fix that originally landed in `kalman_filter_model.py`. That wrapper has
since been retired (consolidated onto `structural_ts.py`), but the
pattern remains the correct template for every statsmodels-wrapping
technique and MUST be applied by every wrapper in `engine/techniques/`
that surfaces a Parameters / Estimates table in its output.

## Problem

`statsmodels` model-fit objects expose `params`, `bse`, `pvalues`,
`tvalues`, and related attributes whose concrete type alternates
between `numpy.ndarray` and `pandas.Series` depending on:

- the **input type** at fit time (ndarray input → ndarray output for
  most state-space classes; pandas Series input → pandas Series output),
- the **model class** itself (some always return Series, others always
  return ndarray regardless of input), and
- the **statsmodels minor version**.

Calling `.index` on one of these attributes crashes when the concrete
type is `ndarray`:

```
AttributeError: 'numpy.ndarray' object has no attribute 'index'
```

This failure was hit in production after a user passed a plain Python
`list` of floats into a Kalman-filter/UCM fit. The wrapper silently
succeeded through fit but raised during the "Build output tables"
phase when it tried to iterate `fit.params.index`.

## Anti-patterns (do NOT use)

```python
# WRONG — crashes when fit.params is an ndarray
for name in fit.params.index:
    value = fit.params[name]
    ...

# ALSO WRONG — works but is brittle under API drift
if hasattr(fit.params, "index"):
    names = fit.params.index.tolist()
else:
    names = [f"param_{i}" for i in range(len(fit.params))]
```

The `hasattr` form *works today* for some statsmodels versions, but
it will silently bypass the real name source (`fit.param_names`) and
emit placeholder names on the ndarray branch. A future statsmodels
version could also attach a non-list `.index` to the ndarray path
(e.g., through a lightweight wrapper class) and the `hasattr` gate
would admit broken input.

## Canonical pattern

Use `fit.param_names` (guaranteed `list[str]` across all statsmodels
versions and model classes) as the source of names, and coerce
`fit.params` / `fit.bse` through `np.asarray(...)` to iterate
positionally by index:

```python
import numpy as np

# Authoritative source of parameter names — plain list in every
# statsmodels version, for every model class that exposes it.
param_names = list(getattr(fit, "param_names", []) or [])

# Coerce to ndarray so positional indexing is consistent regardless
# of whether the fit returned a Series or an ndarray.
params_arr = np.asarray(fit.params)
try:
    bse_arr = np.asarray(fit.bse)
except Exception:
    bse_arr = None

# Iterate by position; guard against length mismatches.
rows = []
for i, pname in enumerate(param_names):
    if i >= len(params_arr):
        break
    pval = float(params_arr[i])
    se = None
    if bse_arr is not None and i < len(bse_arr):
        try:
            se_val = float(bse_arr[i])
            if not np.isnan(se_val) and not np.isinf(se_val):
                se = se_val
        except Exception:
            se = None
    rows.append([str(pname), round(pval, 6),
                 round(se, 6) if se is not None else None])
```

## When to apply

Every wrapper in `engine/techniques/` that emits a Parameters table
from a statsmodels fit. Concrete set (as of this note):

- `structural_ts.py` — UCM / Unobserved Components
- `sarima.py`, `arima.py`, `arimax_sarimax.py` — ARIMA family
- `var_model.py`, `vecm_model.py` — VAR / VECM
- `markov_switching.py` — regime-switching regression
- `garch_model.py` — ARCH/GARCH family (`arch` library, not statsmodels,
  but the same alternation applies; use `fit.params.index.tolist()` only
  after confirming the `arch` version always returns a pandas Series —
  otherwise adopt the same positional pattern)
- `local_level.py`, `local_linear_trend.py`, `structural_ts.py`,
  `particle_filter.py` — State Space batch (Prompt C)
- Any future wrapper whose fit exposes `params` / `bse` / `pvalues`

Prompt C's State Space batch MUST cite this note in its
pre-implementation checklist. The structural_ts.py wrapper currently
uses a `hasattr(params, 'index')` fallback; that works in practice but
should be migrated to this pattern when the State Space batch re-touches
that file for any other reason.

## Test coverage

The invariant test that originally surfaced the crash is in
`engine/tests/test_identification_conventions.py` under
`TestStructuralTSOutputAlignment` (formerly `TestKalmanOutputAlignment`).
Every new statsmodels-wrapping technique should have at least one test
that passes a pandas Series with a `DatetimeIndex` and verifies the
output Parameters table is populated (exercising the ndarray path is
harder to force deterministically without input-type coercion, so the
Series path is the standard gate).
