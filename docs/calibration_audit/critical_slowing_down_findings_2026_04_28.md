# Calibration Audit: critical_slowing_down (Session 28 — TRUE CYCLE CLOSURE)

**Audit date:** 2026-04-28
**Wrapper audited (1):** `engine/techniques/critical_slowing_down.py`
**Cycle status:** CAI Phase 2 COMPLETE — **83/83 wrappers (100%)**.

## Phase A — Deferral rationale

**Original deferral (per `docs/calibration_audit_status.md`
line 276-278):** "critical_slowing_down deferred because it
shipped on 2026-04-25 (commit `94742fe`); too new for the
calibration audit cycle. Will be candidate for next CAI
cycle."

**Resolution (2026-04-28):** wrapper has been in production
for 3 days, has not changed since shipping, and existing
canonical script `validate_critical_slowing_down_canonicals.py`
(5/5 PASS in regression sweeps across Sessions 14-27)
demonstrates the wrapper is stable. Deferral lifts.

## Summary

**Findings: 2 severe / 2 operational (ALL FIXED INLINE) /
0 cosmetic.** Cumulative engine LOC: ~70 in 1 file (within
100 LOC solo budget).

| ID | Severity | Parameter | Bug Class |
|---|---|---|---|
| F-CSD-COMPOSITE | severe | `composite_method` | string fall-through (S18) |
| F-CSD-ROLLINGWIN-NEG | severe | `rolling_window` | numeric range (negative) |
| F-CSD-ROLLINGWIN | operational | `rolling_window` | numeric range (zero falls back to default) |
| F-CSD-KENDALL | operational | `kendall_lookback` | numeric range |

## Sweep 0 — Per-wrapper validation matrix (5 failure modes)

| Mode | Status |
|---|---|
| (1) String acceptance | ❌→✅ (composite_method) — note: `detrending_method` already had explicit allowlist pre-Session 28 (line 247) |
| (2) try/except suppression | SAFE-PROPAGATE (outer except → make_error_response); inner helpers raise on legitimate errors |
| (3) Numeric range | ❌→✅ × 2 (rolling_window, kendall_lookback) |
| (4) Fall-through default | ❌→✅ (composite_method via _composite_ews_score helper) |
| (5) Multi-parameter consistency | OK (existing insufficient-data guard at line 283 handles `T < rolling_window + kendall_lookback` correctly) |

## Pre-existing validation discipline (commendable)

The CSD wrapper had THE BEST pre-audit input validation of
any wrapper in the CAI cycle:
- `detrending_method` allowlist already implemented (line 247)
- Insufficient-data guard with structured response
- ADF stationarity check with D-CSD-5 trigger
- 5 well-organized canonical test cases (D-CSD-1 through
  D-CSD-5)

The Session 28 fixes close gaps in `composite_method`
(silent fall-through inherited from the helper) and numeric
range gates that the original developer didn't add. The
wrapper's overall quality is HIGH.

## try/except taxonomy (Session 18 framework)

`critical_slowing_down.run` has minimal try/except — the
wrapper relies on csd helpers (`_csd_helpers.py`) which raise
on legitimate errors. Outer wrapper-level try/except converts
exceptions to `make_error_response`. **Classification:
SAFE-PROPAGATE.**

No HARMFUL try/except suppression.

## Real-data baselines (5 macro series, T=2000)

| Series | EWS Score | State | Runtime |
|---|---|---|---|
| GSPC_logret | 0.62 | normal | 28.9s |
| DGS10_level | -5.09 | normal | 25.7s |
| DGS2_level | -6.96 | normal | 21.7s |
| DEXUSEU_logret | 6.57 | **critical** | 21.8s |
| GOLD_logret | -2.35 | normal | 21.4s |

**Synthetic bifurcation control:** EWS=3.43, state=critical
(2-second runtime on T=800).

**Cross-validation interpretation:**
- GSPC, GOLD, DGS10, DGS2: normal — consistent with macro
  series being in stable regimes over the audit window. No
  spurious warnings, confirming the wrapper's specificity.
- **DEXUSEU_logret flags critical (EWS=6.57)** — this is a
  notable finding worth documenting. Possible interpretations:
  (a) genuine signal of a regime shift in EUR/USD volatility;
  (b) wrapper sensitivity to autocorrelated FX returns at
  this window length; (c) underlying market dynamics during
  the fixture window. Recommendation: investigate the
  fixture date range manually before treating as a
  production-grade signal.
- Negative EWS on DGS10/DGS2 suggests yield series have
  DECREASING autocorrelation toward the window end —
  opposite of CSD's positive-EWS direction.

CSD is correctly identifying the synthetic bifurcation
control (EWS=3.43, "critical") and producing nuanced
real-data results.

## Cross-references to other anomaly/regime detection

| Wrapper | Session | Approach | Use case |
|---|---|---|---|
| critical_slowing_down | S28 (this) | EWS via rolling AR1/variance/Kendall-tau | Early warning of bifurcation/regime change |
| stl_esd_anomaly | S15 | STL decomposition + Generalized ESD | Outlier detection on de-seasonalized series |
| autoencoder_anomaly | S25 | Reconstruction error from learned encoder | Unsupervised anomaly on multivariate windows |
| bocpd | S15 | Bayesian online change point detection | Probabilistic change-point posterior |
| pelt_change_points | S15 | PELT segmentation | Offline known-K change points |

CSD is unique in the family: it doesn't detect anomalies in
realized data, it forecasts probability of upcoming regime
shifts based on slowing dynamics. Complementary to all four
above.

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-CSD-COMPOSITE | Severe | invalid composite_method silently fell through to equal_weight_zscore via helper if/else | **Fixed inline** |
| F-CSD-ROLLINGWIN-NEG | Severe | negative rolling_window silently accepted | **Fixed inline** |
| F-CSD-ROLLINGWIN | Op | rolling_window=0 silently fell back to default (truthy check) | **Fixed inline** (same fix) |
| F-CSD-KENDALL | Op | negative kendall_lookback silently accepted | **Fixed inline** |

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | CSD wrapper API verified. |
| **CAL-R3** | 1 row DEFERRED → AUDITED. Cycle 82 → 83 (TRULY CLOSED). |
| **CAL-R4** | 1 NEW canonical script (6 cases for S28 fixes) + existing 5-case canonical preserved. |
| **CAL-R5** | 5 macro series + synthetic bifurcation control. |
| **CAL-R6** | 4 inline fixes (~70 LOC in 1 file). Within 100 LOC solo budget. |

# 🎯 CAI PHASE 2 — TRUE CYCLE CLOSURE

After **28 sessions** spanning 2026-04-25 → 2026-04-28:

| Metric | Value |
|---|---|
| Sessions | **28** (5 core + 23 extension) |
| Wrappers AUDITED | **83 / 83** (100%) |
| Wrappers DEFERRED | **0** |
| Severe findings | **40 (all fixed inline)** |
| Operational findings | **42 (all fixed inline)** |
| Cosmetic findings | 6 |
| Cumulative engine LOC delta | ~1600-1800 |
| Validation-presence pattern | **100% predictive across 77 extension wrappers** |
| Canonical scripts | 86 |

**5 failure modes characterized:**
1. String acceptance via if/elif/else default
2. HARMFUL try/except suppression
3. Numeric range silent coercion
4. String-handling chain fall-through
5. Multi-parameter consistency violation

**try/except taxonomy:**
- SAFE-PROPAGATE: most wrappers
- SAFE-FALLBACK: structural_ts, ets_hw, neural wrappers
- SAFE-RERAISE: catches, transforms, re-raises
- HARMFUL: Session 17 ADF/KPSS/PP only — not observed
  elsewhere post-fix

**CAI Phase 2 extension cycle TRULY CLOSED.** Zero unaudited
wrappers remaining.

## Recommended next phase

(C) Documentation consolidation — synthesize CAI cycle
findings into:
1. Unified bug taxonomy (5 failure modes × wrapper inventory)
2. Wrapper-development checklist for future engineering
3. Cross-reference index: which session found which bug
4. Lessons-learned doc

This consolidation makes CAI's institutional knowledge
reusable without engineers needing to re-derive patterns
from 28 per-session findings docs.
