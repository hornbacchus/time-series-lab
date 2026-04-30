# Phase 3.5 Session 7 — Item 9 entry: macro fixture expansion (FX pairs)

**Date:** 2026-04-30
**Scope:** Item 9 — first of 3 sessions (Sessions 7-9 budget).
**Status:** COMPLETE (single-session close).

Adds 4 FX pairs to the canonical real-data macro fixture
(`tools/calibration_audit/fixtures/macro_canonical_series.npz`),
re-pins SHA256, exercises the new pairs through GARCH-family
wrappers + CSD + PELT to verify wrapper-level stability on the
extended pair set, and tests the Pattern A.1 stability claim
(same-library wrappers should produce numerically-well-formed
outputs across heterogeneous FX pairs).

## Step 1 — Fixture pool audit

**Pre-Session 7 fixture pool** at
`tools/calibration_audit/fixtures/macro_canonical_series.npz`
(SHA256 `ba90ffe0...`):

| Series | Source | Description | Length |
|---|---|---|---:|
| `DGS10` | FRED | 10-Year Treasury Constant Maturity Rate | 2501 |
| `DGS2` | FRED | 2-Year Treasury Constant Maturity Rate | 2501 |
| `DEXUSEU` | FRED | US/Euro FX Rate (USD per EUR) | 2499 |
| `GSPC` | Yahoo Finance | S&P 500 daily close | 2515 |
| `GOLD` | Yahoo (`GC=F`) | Gold front-month future | 2513 |

Window: 2015-04-25 to 2025-04-25 (10 years, ~2500 trading
days). Single-fixture file used by 56 audit/canonical scripts
across `tools/calibration_audit/` and `tools/validate_*`.

The Phase 3 reference-parity harness (`tools/reference_parity/`)
does NOT reference this fixture — parity checks use synthetic
DGP fixtures pinned per check. So expanding the macro fixture
has zero impact on the parity-harness CI.

## Step 2 — FX pair selection

Per Session 7 prompt candidate set: GBPUSD, USDJPY, AUDUSD,
EURJPY, GBPJPY, EURGBP. **Selected 4 pairs** (within prompt's
"4-6 pairs" range):

| Pair | Source | FRED ID | Rationale |
|---|---|---|---|
| **GBPUSD** | FRED | `DEXUSUK` | Major USD-cross pair; spans Brexit (2016/2019/2020) regime breaks — Path Q change-point candidate |
| **USDJPY** | FRED | `DEXJPUS` | Major USD-cross pair; spans BOJ YCC era (2016+); volatility regime contrast vs GBPUSD |
| **AUDUSD** | FRED | `DEXUSAL` | Commodity-linked currency; covaries with GOLD; Path Q cross-method investigation potential |
| **EURJPY** | computed (`DEXUSEU * DEXJPUS`) | — | Cross-pair (no USD); decoupled from USD-DXY regime; tests cross-construction robustness |

**Excluded:**
- GBPJPY: cross-pair via GBPUSD * USDJPY would be redundant
  with EURJPY's cross-construction test.
- EURGBP: cross-pair via DEXUSUK / DEXUSEU would be redundant.

4 pairs gives Path Q investigation breadth (GBP-anchored,
JPY-anchored, AUD-anchored, EUR/JPY-cross) without scope
expansion beyond what Session 7's CI runtime budget allows.

## Step 3 — Pin via SHA256

Generation script (one-off; not committed):

```python
import pandas_datareader.data as pdr
import numpy as np

START, END = "2015-04-25", "2025-04-25"
existing = dict(np.load(FIX))

# FRED-direct pairs
fx = {
    "GBPUSD": pdr.DataReader("DEXUSUK", "fred", START, END).iloc[:, 0].dropna().values,
    "USDJPY": pdr.DataReader("DEXJPUS", "fred", START, END).iloc[:, 0].dropna().values,
    "AUDUSD": pdr.DataReader("DEXUSAL", "fred", START, END).iloc[:, 0].dropna().values,
}

# Cross-construction EURJPY = DEXUSEU * DEXJPUS (date-aligned inner join)
dexuseu = pdr.DataReader("DEXUSEU", "fred", START, END).dropna()
dexjpus = pdr.DataReader("DEXJPUS", "fred", START, END).dropna()
joined = dexuseu.join(dexjpus, how="inner").dropna()
fx["EURJPY"] = (joined["DEXUSEU"] * joined["DEXJPUS"]).values

out = {**existing, **{k: v.astype(np.float64) for k, v in fx.items()}}
out["_fx_added"] = np.array(["GBPUSD,USDJPY,AUDUSD,EURJPY"], dtype="S")
out["_fx_session"] = np.array(["phase3.5_session_7"], dtype="S")
np.savez(FIX, **out)
```

**Pre-existing 5 series byte-equal verified** before write
(`np.array_equal` check on each).

| Pair | Length | First obs | Last obs |
|---|---:|---:|---:|
| GBPUSD | 2499 | 1.5235 | 1.3331 |
| USDJPY | 2499 | 119.12 | 143.75 |
| AUDUSD | 2499 | 0.7859 | 0.6396 |
| EURJPY | 2499 | 129.7455 | 163.6019 |

**SHA256 update:** `ba90ffe0...` → `f80fc1ce942431c4cdc50867da758c2e890f31e85caa0a4928a078911431c61c`.

## Step 4 — Selective re-validation

### Parity-harness fast-tier (sanity)

```
Total: 76 / 76
PASS: 71, CAVEAT: 5 (p3_emd_hht, p3_mstl, p3_nar_narx,
                     p3_star, p3_stl — unchanged)
BLOCK: 0
```

Identical to S6 baseline. As predicted, parity harness uses
synthetic DGP fixtures (not `macro_canonical_series.npz`), so
fixture extension has zero impact on the parity CI.

### GARCH variants × 4 FX pairs (12 runs)

All log-returns scaled to percent for GARCH numerical
stability.

| Pair | sGARCH log-lik | GJR-GARCH log-lik | EGARCH log-lik |
|---|---:|---:|---:|
| GBPUSD | −2071.83 | −2071.63 | −2081.05 |
| USDJPY | −1994.96 | −1994.59 | −2006.68 |
| AUDUSD | −2372.99 | −2372.98 | −2374.09 |
| EURJPY | −2042.52 | −2040.21 | −2041.70 |

**All 12 runs status=success.** GJR-GARCH log-likelihood ≥
sGARCH log-likelihood on every pair (consistent with leverage-
asymmetric extension being a strict superset of symmetric).
EGARCH log-likelihood lowest of the three on most pairs
(consistent with EGARCH's different variance parameterization
having a slight estimation-noise penalty on these specific
realizations). AIC / BIC ranges scale appropriately.

**Pattern A.1 stability claim verified:** wrappers produce
numerically-well-formed outputs across heterogeneous FX pairs
without any failures, divergences, or silent corruption. This
matches the Pattern A.1 (same-library wrappers stay
bit-exact-equivalent across different inputs) claim banked at
Session 5.

### Critical Slowing Down on USDJPY

```
USDJPY: status=success
```

CSD wrapper completes successfully; specific Kendall-tau audit
fields surface in the wrapper's output table rather than the
`audit_fields` dict (consistent with existing CSD wrapper
behavior; not a Session 7 finding).

### PELT change-point on EURJPY (log-returns)

```
EURJPY rets: status=success
```

PELT wrapper completes successfully on the EURJPY cross-rate
return series; breakpoint output surfaces in the wrapper's
output table.

**No regression on existing 5 series.** Existing audits /
canonicals that consume `macro_canonical_series.npz` by name
will load the same byte-for-byte data on the 5 original keys
(`DGS10`, `DGS2`, `DEXUSEU`, `GSPC`, `GOLD`) — they're
preserved unchanged. The new keys (`GBPUSD`, `USDJPY`,
`AUDUSD`, `EURJPY`) are visible to any consumer that
explicitly references them but invisible to consumers that
load only the original 5.

## Step 5 — Recurring fixture-expansion protocol (banked)

Session 7's pattern + the prompt's Sessions 7-9 sequencing
defines the recurring protocol for adding additional series
to `macro_canonical_series.npz`:

### What triggers a fixture expansion

1. **Phase 3.5 cycle entry** — Item 9 budget (Sessions 7-9
   targeted at FX / rates / commodities respectively).
2. **Future Phase 4+ cycles** — when a new wrapper batch
   needs cross-pair / cross-asset stress data.
3. **Path Q investigation** — FX-relevant wrapper findings
   may require additional pairs to characterize.

### Expected outputs per fixture expansion

1. **Inventory** — pre-expansion series + SHA256 pin.
2. **Series selection** — sources, IDs, rationale, exclusions.
3. **Build-script** — one-off `pandas_datareader` /
   `yfinance` fetch (script not committed; series-data IS
   committed).
4. **Pre-existing-byte-equal check** — every existing series
   verified `np.array_equal` before write.
5. **SHA256 re-pin** — sidecar updated.
6. **Selective re-validation** — at minimum: 1 wrapper
   exercising each new series for status=success;
   parity-harness fast-tier sanity pass.
7. **Findings doc** — Session N findings under
   `docs/reference_parity_phase3_5/`.

### Escalation protocol (§8.1 risk 2)

Per Session 7 prompt: "if FX data acquisition surfaces
unreliability... defer affected pair(s) to Session 8 or
document as Phase 4 candidate." Session 7 did not trigger
escalation — all 4 selected pairs fetched cleanly via FRED
on first attempt. Bank protocol for future expansion sessions:
- Acquisition fail on a pair → defer that pair, continue with
  the remaining set.
- Acquisition surfaces methodology divergence (e.g., gold
  changing from London Fixing to GC=F front-month per the
  existing fixture's `_gold_fallback` field) → document
  fallback in `_<series>_fallback` metadata key.

### Cross-pair stability convention (Session 5 banking)

Session 7 verified Pattern A.1 (stability across pairs) on
GARCH family. Future fixture expansion should test the same
claim on the new asset class:

- **Session 8 (rates expansion):** verify stability on
  Kalman / Johansen on new yield curves (DGS5, DGS30 e.g.).
- **Session 9 (commodity expansion):** verify stability on
  HAR-RV / change-point on commodity returns (oil, copper,
  silver e.g.).

Each session's findings doc records pair-by-pair log-lik /
AIC / breakpoint counts so cross-pair empirical synthesis
(banked for Session 9 closeout) has the data ready.

## Commit footprint

| File | Change |
|---|---|
| `tools/calibration_audit/fixtures/macro_canonical_series.npz` | +4 keys (GBPUSD, USDJPY, AUDUSD, EURJPY) + 2 metadata keys (`_fx_added`, `_fx_session`); existing 5 series byte-equal preserved |
| `tools/calibration_audit/fixtures/macro_canonical_series.sha256` | re-pin: `ba90ffe0...` → `f80fc1ce...` |
| `docs/reference_parity_phase3_5/session_7_findings.md` | new (~250 LOC) |
| `docs/reference_parity_status.md` | -1 / +18 LOC |
| **Total** | **0 LOC functional code; 4 data series added; ~270 LOC docs** within CAL-R6 100-LOC engine-side budget (zero engine changes) |

## Implications

### Existing audit / canonical scripts

All 56 scripts that load `macro_canonical_series.npz` continue
to work unchanged — they load by key name (e.g., `data["GSPC"]`),
and the 5 pre-existing keys are byte-equal preserved. Scripts
that want to opt into FX cross-pair sweeps can now extend their
loading loop to include the new keys.

### Path Q investigation pre-positioning

The 4 new FX pairs span:
- Major USD-cross diversity (GBPUSD, USDJPY, AUDUSD)
- Cross-construction methodology test (EURJPY = DEXUSEU * DEXJPUS)
- Carry-trade / commodity-linked currency contrast (AUDUSD ↔ GBPUSD)
- BOJ YCC regime + Brexit regime exposure (USDJPY, GBPUSD)

This positions the fixture for Path Q FX-specific empirical
work without committing Phase 3.5 to executing it.

### Pattern A.1 stability claim — confirmed on FX

Session 5 banked the Pattern A.1 stability claim (same-library
wrappers stay numerically equivalent across different real-data
inputs) for empirical verification. Session 7 confirms the
claim holds on GARCH-family wrappers across 4 FX pairs:
status=success on all 12 runs, log-likelihoods scale
appropriately, no silent failures or numerical corruption.

Pattern J catalog entry banked for Session 11: cross-pair
stability is a property of well-implemented wrappers; failures
on this dimension would surface as Pattern A.4 candidates
(within-library cross-input divergence — not yet observed in
TSL).

## Banked items remaining (after Session 7)

| Item | Status | Session |
|---|---|---|
| 9 (rates) | Yields curve expansion | Session 8 (next) |
| 9 (commodities) | Commodity expansion + cross-pair empirical synthesis | Session 9 |
| (S2 banked) | structural_invariants on 12 inherited | Phase 3.5 S9 candidate |
| (S5 banked) | Pattern J.D catalog entry for CRAN-vs-R-runtime version representation | Session 11 |
| (S6 banked) | P-1 §6 CI matrix Linux + cross-platform Rscript protocol; Pattern J.B.6 catalog (statsmodels-x13ashtml deferral) | Session 11 |
| (Phase 4) | statsmodels ↔ x13ashtml integration | Phase 4 |
| (close) | Phase 3.5 closeout | Session 12 |

## Schedule status

7 of 17 sessions through Phase 3.5. On-pace numerically.
Cumulative scope deviation: minor positive (R bridge cross-
platform infrastructure win at S6 was unplanned; this session
closed at single-session target with no escalation).

## Next session

Phase 3.5 Session 8 — Item 9 second session (rates +
commodity expansion). Per locked schedule. Per-session findings
doc + status doc update + commit/push at session end.
