# Calibration Audit: State Space family batch (Session 18)

**Audit date:** 2026-04-26
**Wrappers audited (4):**
  - `engine/techniques/local_level.py`
  - `engine/techniques/local_linear_trend.py`
  - `engine/techniques/structural_ts.py`
  - `engine/techniques/particle_filter.py`

## Summary

**Findings: 1 severe (FIXED INLINE) / 0 operational / 0
cosmetic.** Cumulative engine LOC: ~28 (within CAL-R6
budget).

The single severe finding is the textbook silent-acceptance
pattern from Sessions 9-17:
- F-SS-PF-MODEL — particle_filter silently coerced invalid
  `model` to "local_level" via `if/elif/else` chain in
  `_get_model_functions`

Fixed via explicit allowlist gate parallel to Sessions 13-17's
fixes.

**NEW — try/except suppression check (Session 17 lesson):**
This session incorporated Session 17's NEW bug-class check
into Sweep 0. Per-wrapper try/except suppression assessment:

| Wrapper | try/except blocks | Suppression risk? |
|---|---|---|
| local_level | outer `except ValueError`, `except Exception` → propagate via make_error_response | NO |
| local_linear_trend | same outer pattern | NO |
| structural_ts | inner try/except FALLBACK at line 159-171 catches UnobservedComponents failures and retries with simpler spec; outer try/except propagates on full failure | **POTENTIAL** but verified safe — invalid `level` triggers same ValueError on both attempts → outer except converts to actionable error |
| particle_filter | outer try/except propagates correctly; inner if/elif/else for `model` is the silent-coercion path (not try/except) | NO try/except suppression but YES if/elif/else fall-through |

**structural_ts deserves explicit note:** The wrapper has an
inner try/except fallback designed for convergence failures
(e.g., cycle component fails to converge → retry without
cycle). When the user passes invalid `level="zzz"`, the first
UnobservedComponents call raises `ValueError("Invalid
level/trend specification: 'zzz_invalid'")`. The fallback
retries with the SAME invalid `level_type`, also raises, and
the outer `except` propagates the error. So invalid `level`
correctly triggers status=failure with an actionable error
message — verified during audit.

This is the FIRST clean try/except-fallback we've seen in CAI:
it doesn't suppress upstream validation, only suppresses
intermediate convergence failures. Pattern worth preserving:
fallback should retry only DIFFERENT specifications, never
the same one — and on final failure, propagate the original
error.

## Sweep 0 — Per-wrapper input-validation matrix

| Wrapper | Status | Notes |
|---|---|---|
| local_level | ✅ | numeric/bool params only; no string-acceptance surface |
| local_linear_trend | ✅ | numeric/bool params; `damped` no-op already disclosed via D7 |
| structural_ts | ✅ | UnobservedComponents validates `level`; wrapper's inner fallback retries with same level → outer propagates clean error |
| **particle_filter** | ❌→✅ | invalid `model` silently coerced to "local_level" → allowlist added |

## Real-data baselines (GSPC log returns + DGS10 levels, T=300)

All 4 wrappers SUCCESS on both series:

### GSPC log returns

| Wrapper | RMSE | Runtime |
|---|---|---|
| local_level | 1.17 | 0.02s |
| local_linear_trend | 1.20 | 0.10s |
| structural_ts | 1.59 | 0.22s |
| particle_filter | 0.60 | 0.02s |

### DGS10 yield levels

| Wrapper | RMSE | Runtime |
|---|---|---|
| local_level | 0.26 | 0.03s |
| local_linear_trend | 0.26 | 0.09s |
| structural_ts | 0.44 | 0.40s |
| particle_filter | 0.02 | 0.04s |

Notes:
- particle_filter shows the lowest RMSE on both series. This
  reflects the bootstrap PF tracking the latest observation
  closely (auto-tuned `sigma_state`/`sigma_obs` from the
  data); not necessarily a more accurate model than ML
  Kalman, but a consequence of how RMSE is computed
  (filtered-state-vs-observation residuals).
- structural_ts has the highest RMSE because it's fitting a
  fuller decomposition (level + trend + cycle + AR) and the
  fitted-vs-actual residual is more conservatively defined.
- local_level and local_linear_trend show similar RMSEs;
  llt's stochastic slope adds little explanatory power on
  these series.

Cross-reference Session 1 (Kalman audit): all state space
wrappers share Kalman-filter infrastructure with kalman_filter
/ kalman_smoother. Session 1 already verified the underlying
filter math; this session's findings are layer-specific
(model-dispatch and parameter-validation issues at the
wrapper layer).

## Cross-wrapper recommendations

| Use case | Recommended | Why |
|---|---|---|
| Slowly-evolving level (random walk + noise) | `local_level` | Simplest UCM; minimal parameters; classical |
| Trending series with stochastic slope | `local_linear_trend` | Adds slope state; useful for series with changing growth rates |
| Multi-component decomposition (level + trend + seasonal + cycle + AR) | `structural_ts` | Most flexible; encompasses local level / linear trend as special cases |
| Nonlinear / non-Gaussian state-space | `particle_filter` | SMC handles models where Kalman assumptions break |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-SS-PF-MODEL | Severe | particle_filter silently coerced invalid `model` to "local_level" | **Fixed inline** |

## Validation-presence pattern update (refined per Session 17)

Cumulative across 47 wrappers in 13 extension sessions:
- **WITH validation OR low math**: 27 wrappers → 0 findings
- **WITHOUT validation**: 20 wrappers → 22 severe findings (all fixed inline)

Pattern's predictive power exceptionally strong. Session 18
hit the prediction precisely:
- local_level, local_linear_trend: numeric/bool params only —
  ship clean.
- structural_ts: UnobservedComponents validates upstream AND
  the wrapper's inner try/except fallback doesn't swallow the
  validation error (because retrying with same invalid input
  fails the same way) — ship clean.
- particle_filter: custom string-handling chain with if/elif/
  else fall-through to default — surfaced exactly the
  expected silent-coercion bug.

Session 17 try/except suppression check was operationally
useful: structural_ts triggered the check criterion (inner
try/except catching `Exception`) but verification showed the
suppression was BENIGN. Pattern refinement: not all
try/except suppression is harmful — the harmful case is when
the except clause RETURNS SUCCESS without surfacing an
actionable error. Wrappers whose except clauses re-raise,
fall through to outer error handlers, or set `status=failure`
are safe.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 4 wrapper APIs verified. |
| **CAL-R3** | 4 rows AUDITED. Cycle 49 → 53. |
| **CAL-R4** | 4 NEW canonical scripts (6 each = 24 canonicals). |
| **CAL-R5** | 8 cells of real-data baselines on (GSPC, DGS10) × 4 wrappers. |
| **CAL-R6** | 1 inline fix (~28 LOC in 1 file). Within ≤100 LOC budget. |

## Recommended follow-ups

None. State Space extension batch CLOSED.
