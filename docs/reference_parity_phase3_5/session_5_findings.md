# Phase 3.5 Session 5 — Item 3: Manifest re-pin cadence

**Date:** 2026-04-29
**Scope:** Item 3 only. Single-session.
**Status:** COMPLETE.

First quarterly manifest re-pin cycle. Refreshes
`tools/reference_parity/harness/MANIFEST.toml` against the
current verifier-machine environment, applies dispositions
per drift case, runs selective re-validation on representative
wrappers per affected package family, advances
`last_review`/`next_review` to the next quarterly anchor, and
documents the recurring protocol for Session 5.5 + future
quarterly windows.

## Step 1 — Inventory: installed vs pinned

### Python packages (20 pinned, 1 real drift)

| Package | Pinned | Installed | Drift |
|---|---|---|---|
| hierarchicalforecast | 1.5.1 | 1.5.1 | — |
| pyextremes | 2.5.0 | 2.5.0 | — |
| tbats | 1.1.3 | 1.1.3 | — |
| arch | 8.0.0 | 8.0.0 | — |
| pmdarima | 2.1.1 | 2.1.1 | — |
| statsmodels | 0.14.6 | 0.14.6 | — |
| pymc | 5.28.4 | 5.28.4 | — |
| arviz | 0.23.4 | 0.23.4 | — |
| torch | 2.11.0+cpu | 2.11.0+cpu | — |
| ewstools | 2.1.2 | 2.1.2 | — |
| ruptures | 1.1.9 | 1.1.9 | — |
| astropy | 7.2.0 | 7.2.0 | — |
| **PyWavelets** | **1.8.0** | **1.9.0** | **YES (1 minor)** |
| EMD-signal | 1.9.0 | 1.9.0 | — |
| pyts | 0.13.0 | 0.13.0 | — |
| lightgbm | 4.6.0 | 4.6.0 | — |
| xgboost | 3.2.0 | 3.2.0 | — |
| reservoirpy | 0.4.1 | 0.4.1 | — |
| prophet | 1.3.0 | 1.3.0 | — |
| dtaidistance | 2.4.0 | 2.4.0 | — |

### R packages (20 pinned, 1 real drift + 2 cosmetic format)

| Package | Pinned | Installed | Drift |
|---|---|---|---|
| hts | 6.0.3 | 6.0.3 | — |
| stochvol | 3.2.9 | 3.2.9 | — |
| urca | 1.3.4 | 1.3.4 | — |
| extRemes | 2.2.1 | 2.2.1 | — |
| forecast | 9.0.2 | 9.0.2 | — |
| vars | 1.6.1 | 1.6.1 | — |
| tseries | 0.10.61 | 0.10.61 | — |
| fable | 0.5.0 | 0.5.0 | — |
| fabletools | 0.6.1 | 0.6.1 | — |
| evir | 1.7.4 | 1.7.4 | — |
| POT | 1.1.11 | 1.1.11 | — |
| rugarch | 1.5.5 | 1.5.5 | — |
| dlm | 1.1.6.1 | 1.1.6.1 | — |
| KFAS | 1.6.0 | 1.6.0 | — |
| quantreg | 6.1 | 6.1 | — |
| **robustbase** | **0.99-7** | **0.99.7** | format-only |
| lmtest | 0.9.40 | 0.9.40 | — |
| tempdisagg | 1.2.0 | 1.2.0 | — |
| **dtw** | **1.23-2** | **1.23.2** | format-only |
| **forecastHybrid** | **5.0.19** | **5.1.21** | **YES (1 minor)** |

### Drift summary

- **2 real drifts** (1 Python, 1 R): `PyWavelets` 1.8.0 →
  1.9.0, `forecastHybrid` 5.0.19 → 5.1.21.
- **2 cosmetic format-normalizations**: `robustbase`
  0.99-7 == 0.99.7, `dtw` 1.23-2 == 1.23.2 (CRAN's
  hyphen-suffix renders with a dot via R's
  `packageVersion()`; bit-identical CRAN releases).

## Step 2 — Per-drift-case dispositions

| Package | Drift | Disposition | Rationale |
|---|---|---|---|
| PyWavelets 1.8.0 → 1.9.0 | minor | **Re-pin to 1.9.0** | Routine update. PyWavelets is consumed by `p3_wavelet_transform` + `p3_wavelet_coherence`. Re-validation under 1.9.0 produced bit-exact PASS (0.0 max_abs_diff). No methodology divergence. |
| forecastHybrid 5.0.19 → 5.1.21 | minor | **Re-pin to 5.1.21** | Documentation-only pin. No wrapper currently consumes forecastHybrid (S14 commentary: "documented but not consumed this batch — `forecast_combination` uses self-parity reference"). Re-pin is metadata-only. No re-validation needed. |
| robustbase 0.99-7 / dtw 1.23-2 | format | **Normalize pin format** | Update pins to dot-format to match `packageVersion()` output and clean `--check-environment` reporting. Bit-identical CRAN releases; no behavior change. |

**Zero "Hold pin" or "Investigate" dispositions.** All drifts
are routine patch/minor updates with no observed methodology
impact.

## Step 3 — Selective re-validation

Per Session 5 prompt step 3: representative wrappers per
package family, NOT full 76/76 sweep.

| # | Wrapper | Package family | Drift impact | Verdict | Wall (s) |
|---|---|---|---|---|---:|
| 1 | `p3_wavelet_transform` | PyWavelets (REAL drift) | direct | **PASS** (0.0 max_abs_diff) | 0.03 |
| 2 | `p3_wavelet_coherence` | PyWavelets (REAL drift) | direct | **PASS** (0.0 max_abs_diff) | 0.11 |
| 3 | `p3_sgarch` | rugarch | sentinel | **PASS** | 15.59 |
| 4 | `p3_arima_manual` | forecast | sentinel | **PASS** | 6.04 |
| 5 | `p3_local_level` | KFAS | sentinel | **PASS** | 0.71 |
| 6 | `p3_arimax_sarimax` | statsmodels | sentinel | **PASS** | 2.45 |
| 7 | `p3_fft_spectrum` | scipy | sentinel | **PASS** | 0.00 |
| 8 | `p3_random_forest` | sklearn | sentinel | **PASS** | 0.98 |
| 9 | `p3_lstm_gru` | torch | sentinel | **PASS** | 5.30 |

**9/9 PASS.** §8.1 risk 4 (re-validation surfaces regression)
**NOT triggered**. PyWavelets 1.9.0 reproduces orthogonal-
wavelet (Daubechies db4 / Morlet) outputs bit-exactly; minor
version bump did not perturb wavelet math.

## Step 4 — MANIFEST.toml updates

### Functional pin changes

```toml
# Python
PyWavelets = "1.8.0"  ->  "1.9.0"

# R
robustbase = "0.99-7"  ->  "0.99.7"  # format normalization
dtw = "1.23-2"  ->  "1.23.2"          # format normalization
forecastHybrid = "5.0.19"  ->  "5.1.21"
```

### Cadence advancement

```toml
[refresh]
last_review = "2026-04-25"  ->  "2026-04-29"
next_review = "2026-07-25"  ->  "2026-07-29"
```

### Refresh notes

`[refresh].notes` rewritten to:
- Document the 2 real + 2 cosmetic drifts with disposition
  rationale.
- Cite the 9-wrapper sentinel re-validation outcome (9/9
  PASS).
- Anchor the next quarterly review window (2026-07-29 = exactly
  3 months from the S5 close date).
- Confirm §8.1 risk 4 not triggered.

### Environment-check verification post-update

```
manifest: tools/reference_parity/harness/MANIFEST.toml
  last_review=2026-04-29 next_review=2026-07-29 stale=False
R: pinned=4.5.3 actual=4.5.3
  R packages: all match
  Python packages: all match
```

Clean — no divergences flagged.

## Step 5 — Recurring quarterly protocol (banked)

Reads as the protocol for the next window (2026-07-29) and
beyond. Banked here as a session-output artifact; the cadence
itself is enforced by the `[refresh].next_review` field which
the harness's `--check-environment` flags as `stale=True` when
the date passes.

### What triggers a re-pin investigation

1. **Quarterly anchor reached.** `next_review` date passes;
   `--check-environment` reports `stale=True`. Open a session
   to run the re-pin protocol.
2. **CI parity-fast / parity-slow regression on a wrapper that
   was passing.** Even within a quarter, an upstream release
   introducing methodology divergence may surface as a sudden
   PASS → CAVEAT/BLOCK transition. Run a focused re-pin
   investigation on the affected package family.
3. **Manual contributor notice.** A contributor reports a
   methodology change in an upstream package they consume
   (e.g., a `forecast::ets` optimizer default change, an
   `rugarch` numerical fix). Run a focused re-pin
   investigation.

### Expected output of a re-pin session

A drift report consisting of:

1. **Inventory table.** Pinned vs installed for all R + Python
   packages in the manifest.
2. **Drift summary.** Real-drift cases (semver minor or major
   bumps) separated from cosmetic format-only differences.
3. **Per-drift disposition.** One of:
   - **Re-pin to current.** Default for routine updates with
     no observed methodology impact (sentinel re-validation
     PASS).
   - **Hold pin.** When the upstream change introduces
     methodology divergence the session does not want to
     adopt yet (e.g., a default-prior change in `stochvol`
     that would require a new tolerance ladder discussion).
     Document rationale.
   - **Investigate.** When the upstream change produces
     unexpected divergence in re-validation. Escalate per
     escalation protocol below.
4. **Selective re-validation outcome.** Sentinel wrapper(s)
   for each affected package family, with PASS/CAVEAT/BLOCK
   verdicts.
5. **Cadence advancement.** `last_review` → today's date;
   `next_review` → today + 3 months (or alternative cadence
   anchor if locked).

### Sentinel-wrapper coverage convention

The Session 5 sentinel set (`p3_sgarch`, `p3_arima_manual`,
`p3_local_level`, `p3_arimax_sarimax`, `p3_fft_spectrum`,
`p3_random_forest`, `p3_lstm_gru`, plus the drift-direct
wrappers for the affected package family) covers all major
package families where at least one wrapper consumes the
package. Future sessions should add any new package family
covered by a new wrapper batch (e.g., when Phase 4+ adds
covid-related references like `covidcast-py`, add a sentinel
wrapper from that family).

### Escalation protocol — Phase 3.5 v1.1.0 finding

If selective re-validation surfaces a regression (PASS →
CAVEAT/BLOCK on any sentinel wrapper):

1. **Surface immediately** in the session findings doc + the
   Chat check-in (no wait until session end).
2. **Classify regression cause:**
   - Tolerance band needs widening (Pattern H DSCD
     manifestation — methodology divergence within the
     verdict_class). → Bank as a Phase 3.5 v1.1.0 follow-up;
     do not block the re-pin commit.
   - True numerical bug in upstream package. → Hold the pin;
     report upstream; document in P-2 quirk catalog.
   - True bug in TSL wrapper that the new version exposes. →
     Hold the pin; open a wrapper-fix session (Session 5.5
     continuation).
3. **Re-pin commit may proceed iff** all regressions are
   classified as "Pattern H DSCD widening" (i.e., they don't
   indicate a TSL-side bug). Otherwise hold the pin and run
   Session 5.5.

### CAL-R6 budget for re-pin sessions

100 LOC engine-side budget. Manifest changes + tolerance
ladder widenings (if any) typically fall well within this.
The Session 5 commit footprint was 4 pin changes + 2 cadence
date updates + ~25 LOC of refresh-notes prose — well within
budget.

## Commit footprint

| File | Change |
|---|---|
| `tools/reference_parity/harness/MANIFEST.toml` | -3 / +28 LOC (2 functional pin changes + 2 format normalizations + cadence dates + refresh-notes rewrite) |
| `docs/reference_parity_phase3_5/session_5_findings.md` | new (~200 LOC) |
| `docs/reference_parity_status.md` | -1 / +9 LOC |
| **Total** | **~5 LOC functional + ~230 LOC docs**, well within CAL-R6 100-LOC engine-side budget |

## Banked items remaining (after Session 5)

| Item | Status | Session |
|---|---|---|
| 6 | X-13 binary on Linux CI | Session 6 (next) |
| 9 | Macro fixture expansion | Pending |
| (S2 banked) | structural_invariants on 12 inherited | Phase 3.5 S9 candidate |
| (doc) | Phase 3.5 documentation phase incl. P-1 §5.1 + P-2 §A.10 single_impl_mle prod-lock + P-1 §5.2.1 per_metric schema + P-3 §3 Pattern H per-metric finding | Session 11 |
| (close) | Phase 3.5 closeout | Session 12 |

Master plan §17.1 worst-case projection: 17 sessions for
Phase 3.5. Through Session 5: on-pace; zero scope deviation
across S1-S5 (all closed at single-session targets).

## Next session

Phase 3.5 Session 6 — Item 6: X-13 binary on Linux CI.
Per locked schedule. Per-session findings doc + status doc
update + commit/push at session end. No Chat re-engagement
unless escalation triggers.
