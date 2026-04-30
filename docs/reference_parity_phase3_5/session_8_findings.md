# Phase 3.5 Session 8 — Item 9 second session: rates + commodity expansion

**Date:** 2026-04-30
**Scope:** Item 9 — second of 3 sessions (Sessions 7-9 budget).
**Status:** COMPLETE (single-session close).

Adds 4 rates series (DGS5, DGS30, FEDFUNDS, T10Y2Y) and 3
commodity series (WTI, NG, HG) to the canonical macro fixture.
Re-validates GARCH-family on commodities, CSD on rates +
commodities, PELT on rates + commodities. Surfaces a wrapper-
side memory-management finding (CSD default-surrogate-count
blow-up on long series) as a Phase 4 candidate.

## Step 1 — Data source reliability audit

Per Session 8 prompt's audit-first discipline, every series
was verified via the public source before commit.

### FRED rates verification

| Series | Total rows | Non-null | First | Last | Frequency |
|---|---:|---:|---:|---:|---|
| `DGS5` | 2610 | 2501 | 1.36 | 3.88 | **daily** |
| `DGS30` | 2610 | 2501 | 2.61 | 4.74 | **daily** |
| `FEDFUNDS` | 120 | 120 | 0.12 | 4.33 | **monthly** |

DGS5 and DGS30 align with existing DGS10/DGS2 (2501 obs
daily). **FEDFUNDS is published monthly** — its 120 obs are
the full 10-year history at native publication frequency, not
"insufficient." Including FEDFUNDS adds a heterogeneous-
frequency series; consumers should treat it as monthly via the
`_fedfunds_freq_note` metadata key.

### Yahoo Finance commodity verification

| Ticker | Label | n | First | Last | Gaps (>5d) |
|---|---|---:|---:|---:|---:|
| `CL=F` | WTI crude oil | 2514 | 56.99 | 62.79 | 0 |
| `NG=F` | Henry Hub natural gas | 2515 | 2.49 | 2.93 | 0 |
| `HG=F` | Copper front-month | 2514 | 2.77 | 4.85 | 0 |

All 3 commodities passed the gap-detection check (no 5-day-or-
greater gaps within the 10-year window). Volume and timestamp
density consistent with Phase 3 GSPC / GOLD pattern.

**§8.1 risk 2 (acquisition unreliability) NOT triggered.**
All 6 explicit fetches succeeded on first attempt; the 7th
series (T10Y2Y) is a cross-construction from existing DGS10 −
DGS2 (no fetch needed).

## Step 2 — Rates expansion

Added 4 rates series:

| Key | Source | Construction |
|---|---|---|
| `DGS5` | FRED `DGS5` | 5-year Treasury Constant Maturity Rate |
| `DGS30` | FRED `DGS30` | 30-year Treasury Constant Maturity Rate |
| `FEDFUNDS` | FRED `FEDFUNDS` | Effective Fed Funds Rate (monthly) |
| `T10Y2Y` | derived | DGS10 − DGS2 (cross-construction; no fetch) |

T10Y2Y is the canonical 10y-2y yield curve spread. Cross-
construction from existing DGS10 (2501 obs) − DGS2 (2501 obs)
produces 2501-obs spread without re-fetching. Documented in
`_t10y2y_construct` metadata key. Pattern J.E candidate
(banked for Session 11) — first cross-construction in the
fixture; conventions for derived series banking.

## Step 3 — Commodity expansion

Added 3 commodity series:

| Key | Source | Description |
|---|---|---|
| `WTI` | Yahoo `CL=F` | WTI crude oil front-month future |
| `NG` | Yahoo `NG=F` | Henry Hub natural gas front-month future |
| `HG` | Yahoo `HG=F` | Copper front-month future |

All 3 stored at native daily-close frequency. Energy + base-
metals coverage gives Path Q investigation breadth across:
- Equity-correlated commodities (HG copper, AUDUSD-correlated)
- Geopolitical-shock commodities (WTI, NG)
- Volatility-clustering canonical (NG — gas exhibits the
  most extreme vol clusters of major commodities)

## Step 4 — SHA256 re-pin

Pre-existing 9 series byte-equal verified before write
(np.array_equal on each: DGS10, DGS2, DEXUSEU, GSPC, GOLD,
GBPUSD, USDJPY, AUDUSD, EURJPY).

**SHA256 update:** `f80fc1ce...` → `7dfc7d657fc5a7cb295110a0017ad1b3fa0ede2bcddd842fe4ecd2f5a4cfbb4d`.

**Post-Session 8 fixture state** — 16 series total:

| Category | Series | Count |
|---|---|---:|
| Rates (Phase 3) | DGS10, DGS2 | 2 |
| Rates (Session 8) | DGS5, DGS30, FEDFUNDS, T10Y2Y | 4 |
| FX (Phase 3) | DEXUSEU | 1 |
| FX (Session 7) | GBPUSD, USDJPY, AUDUSD, EURJPY | 4 |
| Equity (Phase 3) | GSPC | 1 |
| Commodities (Phase 3) | GOLD | 1 |
| Commodities (Session 8) | WTI, NG, HG | 3 |
| **Total** | | **16** |

Provenance metadata keys:
- `_start`, `_end`: 2015-04-25, 2025-04-25 (10y window)
- `_source_doc`: Phase 3 originated
- `_gold_fallback`: GOLD fallback documentation (Phase 3)
- `_fx_added`, `_fx_session`: Session 7 provenance
- `_rates_added`, `_commodities_added`, `_s8_session`: Session 8 provenance
- `_fedfunds_freq_note`: FEDFUNDS monthly-frequency disclosure
- `_t10y2y_construct`: T10Y2Y cross-construction disclosure
- `_commodities_source`: yfinance source for commodities

## Step 5 — Selective re-validation

### Parity-harness fast-tier (sanity)

```
Total: 76 / 76
PASS: 71, CAVEAT: 5 (p3_emd_hht, p3_mstl, p3_nar_narx,
                     p3_star, p3_stl — unchanged)
BLOCK: 0
```

Identical to S6/S7 baseline. Parity harness uses synthetic DGP
fixtures, not `macro_canonical_series.npz`; FX + rates +
commodity additions have zero impact on parity CI.

### GARCH variants × 3 commodities (9 runs)

| Commodity | sGARCH log-lik | GJR-GARCH log-lik | EGARCH log-lik |
|---|---:|---:|---:|
| WTI | −5651.92 | −5636.17 | −5648.19 |
| NG | −6692.76 | −6692.65 | −6692.97 |
| HG | −4374.72 | −4374.22 | −4377.08 |

**All 9 runs status=success.** GJR-GARCH log-likelihood ≥
sGARCH on every commodity (consistent with leverage-asymmetric
fitting better on commodity returns; WTI has the largest gap
−5651.92 → −5636.17, ~16 likelihood-units, suggesting genuine
asymmetric volatility in oil — consistent with the empirical
"cuts deeper than spikes" oil-price stylized fact).

Pattern A.1 stability further validated across commodity
asset class — same wrapper produces well-formed outputs across
crude, gas, copper without numerical issues or silent
divergence.

### CSD on long rates / commodities — Phase 4 candidate

**Wrapper-side memory blow-up on default n_surrogates:**

CSD wrapper invoked on T10Y2Y with default params triggered:
```
numpy._core._exceptions._ArrayMemoryError: Unable to allocate
11.7 GiB for an array with shape (1000, 1252, 626) and data
type complex128
```

Trace into `_csd_helpers.py:_vectorized_rolling_indicators`
calling `scipy.signal.periodogram` on a vectorized
(n_surrogates × n_windows × n_freqs) array. Default
n_surrogates ≈ 1000 + n_windows ≈ 1252 (for window=250 on
2501-obs series) + n_freqs ≈ 626 → 11.7 GB complex128 alloc.

**Workaround verified:** `n_surrogates=100` reduces the alloc
to ~1.2 GB and PASSes:
```
T10Y2Y n_surrogates=100: status=success
DGS5   n_surrogates=100: status=success
WTI    n_surrogates=100: status=success
```

**Phase 4 wrapper-engineering candidate** — banked for Phase 4
investigation (NOT Session 8.5 — out of fixture-expansion
scope):
- Vectorized periodogram alloc grows O(n_surrogates × n_windows
  × n_freqs); for series longer than ~1500 obs at default
  n_surrogates, alloc exceeds typical RAM ceilings.
- Possible fixes: chunk the surrogate dimension, reduce default
  n_surrogates from 1000 → 200, or detect series length and
  auto-cap n_surrogates.
- Documents Pattern J candidate (Session 11 banked):
  **Pattern J.F — wrapper memory scaling on long real-data
  series** (CSD vectorized periodogram alloc).

### PELT change-point on rates + commodities

Selective sample:

| Series | Wrapper | Status |
|---|---|---|
| DGS5 (level) | pelt_change_points | success |
| WTI returns | pelt_change_points | success |

**Both succeed.** PELT change-point detection is well-behaved
on both rates levels and commodity returns at default
parameters. No memory-scaling issues observed (unlike CSD —
PELT operates on the time series directly, not via vectorized
surrogates).

## Cross-pair stability summary (Pattern A.1)

Sessions 7 + 8 cumulative: 21 GARCH-family runs across 7 real-
data series (4 FX + 3 commodities) × 3 variants. All 21
status=success with sensible log-lik / AIC / BIC ranges.
GJR-GARCH ≥ sGARCH on every series (theoretically expected
for leverage-asymmetric superset).

Pattern A.1 stability claim **confirmed empirically across FX
+ commodities** (Session 7 + 8). Banked for Session 9 cross-
pair empirical synthesis closeout.

## Documentation banked for Session 11

| Item | Origin |
|---|---|
| Pattern A.1 stability claim — empirical confirmation across FX, commodity, rates | Sessions 7-9 cumulative |
| Pattern J.E — cross-construction conventions in fixture | Session 8 (T10Y2Y first instance) |
| Pattern J.F — CSD wrapper memory scaling on long series | Session 8 (default n_surrogates blow-up) |
| FEDFUNDS heterogeneous-frequency disclosure | Session 8 (monthly amid daily fixture) |

## Phase 4 candidates banked

| Item | Origin |
|---|---|
| CSD wrapper engineering — chunked surrogate dimension OR reduced default n_surrogates OR auto-capped per series length | Session 8 wrapper-side memory blow-up on T10Y2Y default-params |
| statsmodels ↔ x13ashtml integration | Session 6 |

## Commit footprint

| File | Change |
|---|---|
| `tools/calibration_audit/fixtures/macro_canonical_series.npz` | +7 series keys (DGS5, DGS30, FEDFUNDS, T10Y2Y, WTI, NG, HG) + 5 metadata keys; existing 9 series byte-equal preserved |
| `tools/calibration_audit/fixtures/macro_canonical_series.sha256` | re-pin: `f80fc1ce...` → `7dfc7d65...` |
| `docs/reference_parity_phase3_5/session_8_findings.md` | new (~250 LOC) |
| `docs/reference_parity_status.md` | -1 / +20 LOC |
| **Total** | **0 LOC functional code; 7 data series added; ~270 LOC docs** within CAL-R6 100-LOC engine-side budget (zero engine changes) |

## Schedule status

8 of 17 sessions through Phase 3.5. On-pace numerically.

## Next session

Phase 3.5 Session 9 — Item 9 third session: cross-pair
empirical synthesis closeout + structural_invariants on 12
inherited consolidation candidate (per Session 2 banking).
Per locked schedule.
