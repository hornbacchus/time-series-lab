# Calibration Audit: ets_hw solo (Session 27 — FINAL)

**Audit date:** 2026-04-27
**Wrapper audited (1):** `engine/techniques/ets_hw.py`
**Cycle status:** CAI Phase 2 extension cycle CLOSED.

## Summary

**Findings: 4 severe / 2 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~80 in 1 file (within
100 LOC budget for solo audit).

| ID | Severity | Parameter | Bug Class |
|---|---|---|---|
| F-ETS-TREND | severe | `trend` | string fall-through (S18) |
| F-ETS-SEASONAL | severe | `seasonal` | string fall-through (S18) |
| F-ETS-MUL-NEG-TREND | severe | `trend` + data sign | multi-parameter consistency loud-and-coerced (S16/S20) |
| F-ETS-MUL-NEG-SEAS | severe | `seasonal` + data sign | same |
| F-ETS-DAMPED-NOTREND | operational | `damped_trend` + `trend` | multi-parameter consistency silent disable |
| F-ETS-HORIZON | operational | `horizon` | numeric range (S19) |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Mode | Status |
|---|---|
| (1) String acceptance | ❌→✅ × 2 (trend, seasonal) |
| (2) try/except suppression | SAFE-FALLBACK (inner fit fallback retries with hardcoded simple spec; doesn't suppress upstream validation errors because pre-coercion already cleaned strings) |
| (3) Numeric range | ❌→✅ (horizon) |
| (4) Fall-through default | ❌→✅ × 2 (same fix as String) |
| (5) Multi-parameter consistency | ❌→✅ × 3 (mul+neg trend, mul+neg seasonal, damped+no-trend) |

### try/except taxonomy (Session 18 framework)

`ets_hw.run` has an inner try/except at line 174-202 that catches
`Exception` from statsmodels' `ExponentialSmoothing.fit()` and
retries with a hardcoded simpler specification (`trend='add'`,
`seasonal=None`, `damped_trend=False`).

Pre-fix this fallback could potentially have masked invalid
input by retrying with valid spec. Post-fix, the wrapper's
allowlist gates reject invalid input BEFORE reaching the
fitter, so the fallback only fires for legitimate convergence
failures.

**Classification: SAFE-FALLBACK** (Session 18 structural_ts
pattern; retries with different specification, surfaces
clean error if both attempts fail via outer `except
Exception` at the run() level).

## Real-data baselines (5 macro series, T=300)

| Series | Trend | Seasonal | AIC | Runtime |
|---|---|---|---|---|
| GSPC_logret | add | add | 102.36 | 0.34s |
| DGS10_level | add | add | -1710.80 | 0.29s |
| DGS2_level | add | add | -1688.28 | 0.28s |
| DEXUSEU_logret | add | add | -459.08 | 0.31s |
| GOLD_logret | add | add | 37.66 | 0.34s |

All 5 SUCCESS. ets_hw auto-selects additive trend + seasonal
across all macro series. AIC ranking: yields (very negative;
strong fit) > FX returns > GSPC/GOLD returns.

## Cross-references

- **Session 10 ARIMA family:** auto_arima found returns →
  white noise, yields → random walk. ets_hw on returns
  produces fitted ETS but with weak trend signal (AIC
  positive, indicating noise-dominated). Consistent: ETS
  with auto-selection isn't dramatically better than SES on
  log returns.
- **Session 16 STL/MSTL decomposition:** ets_hw with
  seasonal='add' performs implicit decomposition. STL
  decomposition (Session 16) is more flexible (LOESS-based
  smoother, handles changing seasonal) but ETS provides
  forecasts directly. Both audited clean post-fix.

## Methodology comparison

| Use case | Recommended |
|---|---|
| Short forecast horizons, simple smoothing | `ets_hw` (Holt-Winters) |
| Stationary series with autocorrelation | `arima` family (Session 10) |
| Decomposition without forecasting | `stl_decompose` / `mstl_decompose` (Session 16) |
| Production seasonal adjustment | `x13_seasonal_adjust` (Session 16) |

## Validation-presence pattern — final tally

Cumulative across 76 extension wrappers in 22 extension sessions:
- **WITH validation OR low math**: 36 wrappers → 0 findings
- **WITHOUT validation**: 40 wrappers → 76 severe/op findings (all fixed inline)

Pattern remains 100% predictive across the full extension cycle.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | ets_hw API verified. |
| **CAL-R3** | 1 row AUDITED. Cycle 81 → 82. |
| **CAL-R4** | 1 NEW canonical script (9 canonicals — full-depth solo audit). |
| **CAL-R5** | 5 macro series baselines (GSPC, DGS10, DGS2, DEXUSEU, GOLD). |
| **CAL-R6** | 6 inline fixes (~80 LOC in 1 file). Within 100 LOC solo budget. |

## Recommended follow-ups

None blocking. ets_hw audit CLOSES the CAI extension cycle.

# CYCLE CLOSURE SUMMARY — CAI Phase 2

**Final state (post-Session 27):**

| Metric | Value |
|---|---|
| Sessions completed | 27 (5 core + 22 extension) |
| Wrappers AUDITED | **82 / 83** (98.8%) |
| Wrappers DEFERRED | 1 (`critical_slowing_down` — too new at audit start) |
| Cumulative findings — severe | 38 (all fixed inline) |
| Cumulative findings — operational | 40 (all fixed inline) |
| Cumulative findings — cosmetic | 6 |
| Cumulative engine LOC delta | ~1500-1700 across all wrappers |
| Validation-presence pattern accuracy | 100% across 76 extension wrappers |
| Canonical scripts | 84 (1 per audited wrapper + 4 verification-initiative + B6/B7) |
| Full regression suite | 84/84 PASS |
| Local + CI fast-tier reference parity | PASS overall |

**5 failure modes characterized:**
1. String acceptance via if/elif/else default
2. HARMFUL try/except suppression
3. Numeric range silent coercion
4. String-handling chain fall-through
5. Multi-parameter consistency violation

**Safe vs harmful try/except taxonomy** (S18 framework):
- SAFE-PROPAGATE: outer `except → make_error_response`
- SAFE-FALLBACK: retries with different spec, surfaces error
  if all attempts fail (structural_ts, ets_hw, neural
  wrappers' sklearn fallback)
- SAFE-RERAISE: catches, transforms, re-raises
- HARMFUL: catches and returns success without surfacing
  actionable error (Session 17 ADF/KPSS/PP pattern — not
  observed elsewhere post-fix)

**Recommended next phase:**

(C) Documentation consolidation — synthesize CAI cycle
findings into:
1. A unified bug taxonomy for engineering reference
2. A wrapper-development checklist (e.g., "before
   merging, validate all string params have allowlists,
   all numeric params have range gates, all multi-param
   surfaces have consistency checks")
3. Cross-reference index: which session found which
   wrapper's bug, by failure mode
4. Lessons-learned for future plugins / wrappers

This consolidation would make CAI's institutional
knowledge reusable for future TSL development without
requiring engineers to re-derive the patterns from per-
session findings docs.
