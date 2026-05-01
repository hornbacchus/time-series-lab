# Wrapper Development Standard

**Status:** Binding for new TSL technique wrappers and any
significant modification to existing wrappers.

**Audience:** TSL engineers (humans + Claude Code) writing
or reviewing wrapper code.

**Origin:** Distilled from CAI Phase 2 (28 sessions,
83/83 wrappers, 88 findings fixed across 5 failure modes).
Companion documents:
- [Validation Patterns Reference](validation_patterns_reference.md) — diagnostic + fix patterns
- [CAI Empirical Findings](cai_empirical_findings.md) — what we learned

This document is **directive** ("must"). The companions are
descriptive ("what we found") and reference ("how to test
and fix").

---

## 1. Purpose and Scope

### 1.1 What this standard applies to

Every Python module under `engine/techniques/` that exposes
a `run(ctx: RunContext, progress_callback) -> dict`
entry point.

Applies to:
- New wrapper modules (e.g., next time we add a forecasting
  technique).
- Significant modifications to existing wrappers (parameter
  surface changes, helper-function refactors that touch
  user-input handling).
- Any wrapper-layer try/except block edits.

Does NOT apply to:
- Pure helper modules that don't touch user input (e.g.,
  `_csd_helpers.py`'s pure-math functions).
- The interpretation layer (`engine/interpretation/specs/`).
- Engine harness code (`engine/engine_worker.py`,
  `engine/techniques/base.py`).

### 1.2 Standard tier

Items below are split into two tiers:

- **Binding (B):** Required. PRs that fail B-tier checks
  do not merge. CI canonicals must catch B-tier violations.
- **Aspirational (A):** Recommended. Encourage in code
  review, but PRs may merge with A-tier exceptions if
  documented.

The pre-merge checklist (§5) is binding in full.

---

## 2. Validation Requirements

### 2.1 String parameter allowlist requirement (B)

Every user-facing string parameter MUST have an explicit
allowlist gate that produces `make_error_response` on
unknown values.

**Forbidden pattern** (Sessions 18 / 22 / 24 / 25 / 26 / 27 / 28):

```python
# FORBIDDEN — silent fall-through
method = ctx.get_param("method", "default_method")
if method == "option_a":
    do_a()
elif method == "option_b":
    do_b()
else:  # silently picks default!
    do_default()
```

This pattern silently coerces invalid `method` values to
the default branch. It surfaced in 14 of the 28 audit
sessions and produced the dominant CAI bug class. See
[Validation Patterns Reference §2.1](validation_patterns_reference.md#21-mode-1-string-acceptance-via-iflses)
for full diagnosis.

**Required pattern:**

```python
# REQUIRED — explicit allowlist gate
_METHOD_OPTS = ("option_a", "option_b", "default_method")
method = ctx.get_param("method", "default_method")
if method not in _METHOD_OPTS:
    return make_error_response(
        ctx,
        f"Unknown method '{method}'. Must be one of: "
        f"{', '.join(_METHOD_OPTS)}.",
        error_fixes=[
            "Use 'option_a' (description), 'option_b' "
            "(description), or 'default_method' (default).",
        ],
    )
if method == "option_a":
    do_a()
elif method == "option_b":
    do_b()
else:  # method == "default_method" — guaranteed by gate
    do_default()
```

**Edge cases:**

- **List-of-strings parameters** (e.g., `stack_types`,
  `pooling_sizes`, `quantiles`): allowlist must validate
  each entry. See N-BEATS / N-HiTS pattern (Sessions 24/25).
- **Mixed-type parameters** (e.g., `penalty` accepts both
  string and numeric in `pelt_change_points`): allowlist
  the string branch; range-gate the numeric branch.
- **Optional string parameters** that allow `None`: include
  `None` in the allowlist tuple, e.g.,
  `_OPTS = (None, "varimax")`.

### 2.2 Numeric parameter range gate requirement (B)

Every user-facing numeric parameter MUST have an explicit
range gate that returns `make_error_response` on
out-of-range values.

**Forbidden pattern** (Session 19/21/23/24/25/26/27/28):

```python
# FORBIDDEN — silent coercion
horizon = int(ctx.get_param("horizon", 10))
if horizon < 1:
    horizon = 1  # silent change of user's intent
```

**Required pattern:**

```python
# REQUIRED — explicit range gate
horizon = int(ctx.get_param("horizon", 10))
if horizon < 1:
    return make_error_response(
        ctx,
        f"horizon must be >= 1. Got {horizon}.",
        error_fixes=["Use a positive integer (typical 1-24)."],
    )
```

**Common range patterns:**

| Parameter type | Required range |
|---|---|
| Forecast horizon | `>= 1` |
| Window/lag count | `>= 1` |
| n_estimators / n_particles / draws | `>= 1` (>= 10 for MCMC) |
| Confidence level / alpha | `0 < x < 1` (open interval) |
| Calibration / holdout fraction | `0 < x < 1` |
| Trim / winsor fraction | `0 < x < 0.5` |
| Smoothing / shrinkage parameter | `> 0` (strictly positive) |
| Spectral radius (ESN) | `> 0` (typical < 1.5) |
| Leak rate (ESN) | `0 <= x <= 1` |
| ARIMA / VAR lag | `>= 1` |

### 2.3 Multi-parameter consistency check requirement (B)

When two or more parameters interact, the wrapper MUST
detect inconsistent combinations and reject explicitly,
NOT silently coerce.

**Forbidden patterns:**

- `damped_trend=True` + `trend=None` silently disabled
  (Session 27).
- `seasonal='mul'` + non-positive observations silently
  switched to `'add'` (Session 27).
- `d_model` not divisible by `n_heads` silently rounded
  (Session 24).
- `growth='logistic'` + missing cap column silently
  failed downstream (anticipated S26 — wrapper hides
  surface).
- `cal_fraction` consuming most of a series with `n_train
  < n_lags` silently produced degenerate splits (S21).

**Required pattern:**

```python
# REQUIRED — reject inconsistent combination explicitly
if damped_trend and trend is None:
    return make_error_response(
        ctx,
        "damped_trend=True requires trend to be set "
        "('add' or 'mul'). Got trend=None.",
        error_fixes=[
            "Set trend='add'/'mul' to use damped trend, "
            "or set damped_trend=False.",
        ],
    )
```

### 2.4 try/except taxonomy: required vs forbidden (B)

Every try/except in wrapper code (the file under
`engine/techniques/`, not helper modules) must be
classifiable into one of four taxonomy classes per
[Validation Patterns Reference §3](validation_patterns_reference.md#3-tryexcept-taxonomy).

**Required (any of):**

- **SAFE-PROPAGATE:** outer `except → make_error_response`.
  Library exceptions surface to the user as actionable
  errors.
- **SAFE-FALLBACK:** retries with a different specification
  on failure, surfaces error if all retries fail. Example:
  `structural_ts.py` falls back to simpler model on
  convergence failure.
- **SAFE-RERAISE:** catches a specific exception, transforms
  it (e.g., add context), re-raises.

**Forbidden (HARMFUL):**

- An `except` clause that returns `status="success"` (or
  equivalently, populates audit_fields and proceeds without
  ever surfacing an actionable error). This was the Session
  17 ADF/KPSS/PP failure mode where statsmodels rejected
  the user's invalid `regression` value but the wrapper
  swallowed the ValueError and reported success with the
  user's invalid string in audit_fields.

If a try/except can't be classified into the three SAFE
categories, it is HARMFUL and the wrapper does not pass
review.

### 2.5 Allowed exceptions to "no library validation alone"

Wrappers MAY rely on upstream library validation if AND
only if all three of these hold:

1. The library is mature and well-tested (statsmodels,
   sklearn, scipy, ruptures, pmdarima qualify; obscure
   one-off packages do not).
2. The wrapper does not have its own try/except suppressing
   the upstream exception. (Session 17 ADF/KPSS/PP all
   wrapped statsmodels but caught ValueError internally —
   that's the failure pattern.)
3. The wrapper does not pre-process the user's string
   (e.g., applying `.lower()` or `[:3]` slicing) in a way
   that could silently change which library branch is
   reached.

When in doubt, add the allowlist gate at the wrapper layer.
The gate is cheap, the bug is expensive.

---

## 3. Audit Field Discipline

### 3.1 audit_fields must reflect actual computation (B)

Every key in `audit_fields` must report what the wrapper
ACTUALLY computed, not what the user requested. If those
diverge, the audit field reports the actual.

**Forbidden:**

```python
# FORBIDDEN — audit_fields lies about what ran
audit_fields = {
    "kernel": ctx.get_param("kernel"),  # user's input
    # ... but the wrapper silently coerced to RBF
}
```

**Required:**

```python
# REQUIRED — audit_fields tracks the actual computation
kernel = ctx.get_param("kernel", "rbf")
if kernel not in _KERNELS:
    return make_error_response(...)
# kernel is now guaranteed to be a valid value;
# audit_fields["kernel"] = kernel reflects what ran
```

This rule was violated in Sessions 9 (VECM), 16 (X-13),
27 (ETS), and 28 (CSD composite_method). In each case,
fixing the silent-coercion path also fixed the audit_field
discrepancy because rejection makes coercion impossible.

### 3.2 Required audit fields

Every wrapper's `audit_fields` dict must include at minimum:

| Key | Type | Purpose |
|---|---|---|
| (technique-specific param keys) | matches spec | Reflect actual computation per §3.1 |
| `n_obs` | int | Number of observations actually used |
| (key fitted parameters) | varies | E.g., `aic`, `bic`, `log_likelihood`, `rmse` |

Additional keys should match what the interpretation
spec at `engine/interpretation/specs/<technique>.py`
expects.

### 3.3 Significance disclosure for tests producing p-values

Hypothesis-test wrappers (ADF, KPSS, PP, Granger, etc.)
must include a `format_significance_disclosure()` block
in audit_fields per the established pattern:

```python
**format_significance_disclosure(
    test_name="...",
    critical_value_formula="...",
    ac_corrected=True,
),
```

---

## 4. Pre-merge Checklist

Every PR creating or modifying a wrapper must pass this
checklist. Reviewer signs off explicitly.

### 4.1 Validation gates (binding)

- [ ] **B-1**: All user-facing string parameters have explicit
  allowlist gates returning `make_error_response` on miss.
- [ ] **B-2**: All user-facing numeric parameters have explicit
  range gates returning `make_error_response` on out-of-range.
- [ ] **B-3**: All multi-parameter consistency surfaces have
  explicit checks rejecting inconsistent combinations.
- [ ] **B-4**: No try/except clause in the wrapper file
  returns `status="success"` after catching an Exception
  that indicates user input is invalid.
- [ ] **B-5**: Sweep 0-style probe test exists (a calibration
  audit script under `tools/calibration_audit/audit_*.py`
  OR an inline test verifying that invalid params produce
  `status="failure"` with actionable error_message).

### 4.2 Audit fields (binding)

- [ ] **B-6**: `audit_fields` reflects what the wrapper
  actually computed, not what the user requested. Verified
  by running the wrapper with a valid input and inspecting
  the audit_fields keys against the actual code path.
- [ ] **B-7**: Hypothesis-test wrappers include
  `format_significance_disclosure()`.
- [ ] **B-8**: Audit field keys match the interpretation
  spec's expectations under
  `engine/interpretation/specs/<technique>.py`.

### 4.3 Canonical test suite (binding)

- [ ] **B-9**: A `tools/validate_<technique>_canonicals.py`
  script exists with at least 6 cases (pattern: 4-5 base
  + 1-2 fix-verification + 1 short-series boundary).
- [ ] **B-10**: All canonicals pass (`Overall: ALL PASS`).
- [ ] **B-11**: New canonical script is added to the regression
  sweep so it runs in future sessions' regressions.

### 4.4 Documentation (binding)

- [ ] **B-12**: `error_fixes` argument to every
  `make_error_response` includes a concrete user-actionable
  fix (not a vague "check your input").
- [ ] **B-13**: Docstring on `run()` documents every user-
  facing parameter with valid range / allowed values.

### 4.5 Aspirational (recommended, not blocking)

- [ ] **A-1**: Wrapper file under 600 LOC (statistical models
  with multiple variants may exceed; tree-of-models wrappers
  shouldn't).
- [ ] **A-2**: Helper functions extracted to `_<technique>_
  helpers.py` if total wrapper LOC > 500.
- [ ] **A-3**: Backend-fallback pattern (sklearn fallback
  when torch unavailable, etc.) when relevant.

### 4.6 Dependency-addition checklist (binding)

Phase 4 Session 1 (2026-05-01). Cross-references P-1 §8.5
install-matrix gate
([parity_standard.md §8.5](parity_standard.md#85-required-install-matrix-updates-b)).

If the wrapper depends on a non-stdlib Python package or any
R package or any system binary that is **not already** in
TSL's existing install matrix (i.e., not already imported by
some other shipped wrapper), the PR author MUST verify the
new dependency is added across all four CI-relevant surfaces:

- [ ] **B-14**: New runtime dependency added to all four
  install surfaces:
  - `engine/requirements.txt` (engine-side runtime install)
  - `tools/reference_parity/harness/MANIFEST.toml`
    (parity-harness pinned version)
  - `.github/workflows/parity-fast.yml` (fast-tier CI;
    Windows job)
  - `.github/workflows/parity-slow.yml` **both** the
    Windows job AND the Linux job (per Phase 3.5 Session 1
    Item 4 protocol: all check classes import at runner-
    discovery time regardless of tier).

**Failure mode codified by this checklist item:** historical
precedent shows that single-surface omissions produce
asymmetric CI failures invisible to local-only testing
(local installs resolve the dependency from site-packages
regardless of which TSL surface declares it). The four-
surface check is the minimum sufficient gate.

**Two recurring instances of this failure class** prior to
codification:

1. Phase 3.5 Session 6 — Linux `parity-slow.yml`
   missing `x13binary`.
2. Bond Yield Forecast Session 4 → Session 5 — fast-tier
   `parity-fast.yml` missing `openpyxl`.

Both closed by retrospective install-matrix amendment.

The parity-dimension checklist item lives in
[P-1 §8.5](parity_standard.md#85-required-install-matrix-updates-b);
this C-1 item is the engine-side companion. Both must hold
for any wrapper PR introducing a new dependency.

---

## 5. Canonical Test Suite Requirement

### 5.1 Minimum structure

Every wrapper requires a canonical test suite with:

- **5 base cases (canonical_1 through canonical_5):**
  baseline, parameter variants, alternative valid configs,
  short series boundary, and one wrapper-specific feature
  test.
- **At least 1 fix-verification case (typically canonical_5):**
  passes invalid input, asserts `status="failure"` and
  asserts the error_message contains an expected
  identifier (e.g., "Unknown method").
- **Optional 4 adversarial cases (canonical_6 through
  canonical_9):** for solo audits per Sessions 7/8/20/27/28
  precedent (constant series, white noise, edge cases).

### 5.2 Required structure (template)

```python
"""Phase 5 canonical validation for <technique>.

Created during PR #XYZ. N canonicals.
"""

import os, sys
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception: pass

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_R, "engine"))

import numpy as np
from techniques.base import RunContext
from techniques import <technique> as mod

def _null(*a, **k): pass

def _ctx(values, *, params=None, preset="Fast", frequency="D"):
    return RunContext({
        "run_id": "test_<short>",
        "technique_id": "<technique>",
        "preset": preset, "seed": 42, "frequency": frequency,
        "time": list(range(len(values))),
        "series": [{"name": "y", "values": list(values)}],
        "params": dict(params or {}),
    })

def canonical_1():
    print("\n=== c1: baseline ===")
    # ... synthesize fixture ...
    res = mod.run(_ctx(y), _null)
    return res.get("status") == "success"

# ... canonical_2 through canonical_N ...

def canonical_5():
    """Fix verification — invalid params rejected."""
    print("\n=== c5: invalid params rejected ===")
    res = mod.run(_ctx(y, params={"method": "zzz"}), _null)
    if res.get("status") != "failure": return False
    if "Unknown method" not in (res.get("error_message") or ""):
        return False
    return True

def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
        try: ok = fn()
        except Exception as e:
            print(f"  RAISED: {e}"); ok = False
        results.append((fn.__name__, ok))
        print(f"  {'PASS' if ok else 'FAIL'}: {fn.__name__}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)

if __name__ == "__main__": main()
```

### 5.3 Adding to the regression sweep

After creating the canonical script:

1. Run it locally:
   `python tools/validate_<technique>_canonicals.py`
2. Confirm all cases pass.
3. Add it to any project-wide regression manifests (it's
   automatically picked up by `tools/validate_*.py` glob in
   the standard regression sweep).
4. The CI pipeline runs `tools/validate_*.py` glob; new
   canonical files are picked up automatically.

### 5.4 Smoke test on macro fixture

For wrappers operating on time-series data, include a
canonical that hits real macro data from
`tools/calibration_audit/fixtures/macro_canonical_series.npz`
(GSPC, DGS10, DGS2, DEXUSEU, GOLD). This catches issues
that synthetic fixtures miss (e.g., autocorrelation
patterns, missing values, fat tails).

---

## 6. References

- [Validation Patterns Reference](validation_patterns_reference.md):
  diagnostic and fix patterns by failure mode
- [CAI Empirical Findings](cai_empirical_findings.md):
  what we found across 83 wrapper audits
- `docs/calibration_audit_status.md`: per-wrapper audit
  status (master tracker)
- `docs/calibration_audit/<wrapper>_findings_<date>.md`:
  per-session findings (28 sessions in CAI Phase 2)

---

## 7. Standard amendment process

Amendments to this standard are made via PR. The standard
is binding as of the date of merge. Existing wrappers
that violate the standard are NOT automatically grandfathered
in — they remain in their current state until the next
audit cycle catches them, OR until a PR modifies them and
the new code must conform.

**Last revised:** 2026-04-28 (Session 29, post-CAI Phase 2
cycle closure).
