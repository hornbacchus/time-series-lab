# Bond Yield Forecast Modification 2 (BYF-Mod-2) — Findings

**Date:** 2026-05-01
**Scope:** Re-run parity audit on BYF-Mod-1 34-maturity grid;
resolve two banked findings (B-Mod1-1 dispatch attribute fix;
B-Mod1-2 PCA threshold measurement); update P-4 status tracker;
single commit at session close. Per BYF-Mod-2 trigger §"Locked
decisions from Chat planning session".
**Status:** COMPLETE. Modification cycle 1 (Mod-1 + Mod-2)
closed; **PASS on both fixtures**.

## Executive verdict

| Fixture | n_mat | A.1 elements bit-exact | VAR max\|eig\| | SV max\|φ\| | PCA EVR (3 PC) | Verdict |
|---|---|---|---|---|---|---|
| `fixture_10mat` (legacy) | 10 | 1,557,000 | 0.948 | 0.996 | **99.91%** | **PASS** |
| `fixture_34mat` (BYF-Mod-1 grid) | 34 | 1,557,000 | 0.999 (boundary) | 0.996 | **99.92%** | **PASS** |
| **TOTAL** | — | **3,114,000** | — | — | — | **PASS** |

Two-fixture audit wall-clock: **16.53s** (4 BVAR-SV cycles total).
Fits fast-tier comfortably.

## Banked-finding resolutions

### B-Mod1-1 — Dispatch attribute-name mismatch — **RESOLVED**

**Origin:** BYF-Mod-1 §1.8 surfacing during smoke-test development.

`_dispatch.py:_build_yield_forecast_table` line 321 read
`getattr(yield_forecast, "yield_names", [])` — but the
`YieldCurveForecast` dataclass exposes per-maturity labels via
`maturity_names` (set by `ConditionalForecast.to_yield_space` at
`conditioning.py:768` from `pca_dict["yield_names"]`). The
nonexistent-attribute lookup fell through to the placeholder
`Maturity_0..Maturity_N` labels, masking the canonical
`treasury_3m..treasury_30y` names in the user-visible Yield
Forecast table.

**Fix (BYF-Mod-2 commit):** dual-attribute lookup at
`_dispatch.py:321` — `maturity_names` primary,
`yield_names` secondary (forward-compat for any downstream that
might emit it), placeholder `Maturity_N` fallback last. Same
fix applied at line ~615 (`yield_names_used` derivation for
audit_fields summary text).

**Regression test:**
`engine/techniques/bond_yield_forecast/tests/test_dispatch_maturity_names.py`
(new file) — two assertions:

1. `test_dispatch_renders_treasury_maturity_names_not_placeholders`:
   runs BYF on the canonical 10-maturity fixture; asserts the
   Yield Forecast table's Maturity column contains the canonical
   labels `[treasury_3m, ..., treasury_30y]` and NOT any
   `Maturity_N` placeholder.
2. `test_dispatch_audit_fields_maturities_populated`:
   asserts `audit_fields["maturities_populated"]` and
   `audit_fields["n_maturities_populated"]` carry the same
   canonical labels and count.

Both PASS at this commit.

**Numerical impact:** zero. Verified at Step 2.9 — re-running the
10-maturity smoke after the B-Mod1-1 fix lands and comparing to
the pre-Mod-2 baseline produces **zero numerical-cell mismatches**
in the Yield Forecast / Macro Conditioning Paths / Convergence
Diagnostics tables. The fix touches only the Maturity-column
LABEL strings, not numerical content. Pre-existing cycle-baseline
preservation discipline preserved.

### B-Mod1-2 — Pattern F PCA explained-variance threshold recalibration — **MEASURED, NO CHANGE**

**Origin:** BYF-Mod-1 §1.8 + Mod-2 plan §2.5.

**Empirical measurement** on the 34-maturity fixture:

| Fixture | n_mat | PC1 | PC2 | PC3 | sum (3 PCs) |
|---|---|---:|---:|---:|---:|
| `fixture_10mat` | 10 | 93.1777% | 6.3460% | 0.3860% | **99.9098%** |
| `fixture_34mat` | 34 | 93.2929% | 6.3209% | 0.3025% | **99.9164%** |

The 34-mat fixture's 3-PC truncation captures **99.92%** of yield-
panel variance — slightly HIGHER than the 10-mat fixture's 99.91%.

This is counterintuitive at first read: denser maturity grids
typically capture LESS variance in a 3-PC truncation because
high-frequency shape variation enters PCs 4+. Here, however, the
BYF-Mod-1 sample template's 24 inserted maturities are LINEARLY
INTERPOLATED in maturity-years space between the 10 anchor
maturities (per BYF-Mod-1 README addendum). Linear interpolation
introduces no variance orthogonal to the existing
level/slope/curvature factor structure that the 3-PC truncation
already captures. So the measured EVR is essentially preserved
(very slight uptick driven by the interpolated columns being
mathematically more aligned with the dominant factors than
real-world inter-maturity variation would be).

**Per BYF-Mod-2 §2.5 decision tree:**
> If measured ratio ≥ 99%: keep threshold at 99% (current value
> still meaningful).

**Disposition: NO THRESHOLD CHANGE.** Both fixtures use
`PCA_EXPLAINED_VAR_MIN = 0.99` — clears with comfortable margin
(0.91pp on 10-mat; 0.92pp on 34-mat).

**Future-cycle caveat documented in audit report §3-bis.2:** if
a future BYF-Mod cycle replaces the synthetic-interpolation
34-mat fixture with empirically-sourced Treasury data carrying
real high-frequency curve variation, the threshold may need
re-measurement. Banking that as a forward-provisioning note.

## VAR companion-eigenvalue boundary observation (34-mat)

**New empirical observation surfaced by Step 2.6 audit run:**
`fixture_34mat::invariant::var_companion_eig` measured **max|λ| =
0.9988** vs `fixture_10mat::invariant::var_companion_eig` at 0.948.

The 34-mat input drives the BVAR system **closer to the unit
circle** than the 10-mat input — by ~0.05 in companion-eigenvalue
space. The companion form remains stationary (< 1.0); the
audit's PASS threshold (< 0.999) is cleared by 0.0002 — narrow
margin but not a violation.

**Mechanism:** the BVAR variable count is constant at 6 (3 macro
+ 3 PCs); only the PCA-input panel width changes. Different PCA
loadings × scores result from the 34-input vs 10-input
configuration, which feeds different BVAR conditional-mean
shrinkage paths through the Minnesota prior. The denser input
produces PCs with slightly different time-series persistence
characteristics, manifesting as the eigenvalue shift.

**Documentation:** audit report §3-bis.2 records this
observation. Not banked as a finding (system remains stationary;
PASS threshold cleared); recorded for any future BYF-Mod cycle
that materially changes maturity-grid composition (e.g., adding
maturities below 1M or non-uniform spacing) so the audit-author
recognizes the eigenvalue shift as a known consequence of the
maturity grid rather than a regression.

## File topology summary

| File | Action | LOC delta |
|---|---|---|
| `engine/techniques/bond_yield_forecast/_dispatch.py` | B-Mod1-1 dual-attribute lookup at line 321 + matching update at audit_fields summary derivation | ~14 |
| `engine/techniques/bond_yield_forecast/tests/fixtures/test_input_canonical_34mat.xlsx` | NEW — copied from BYF-Mod-1 sample template; pinned via SHA256 in audit script + report | (33 KB binary) |
| `engine/techniques/bond_yield_forecast/tests/test_dispatch_maturity_names.py` | NEW — 2 regression tests for B-Mod1-1 | +135 |
| `tools/reference_parity/harness/checks/p3_bond_yield_forecast.py` | rewrite to cover both fixtures (Option A); per-fixture metric prefixing | +110 / -65 |
| `tools/reference_parity/reports/p3_bond_yield_forecast_audit.md` | extended with §3-bis (34-mat results) + §8 BYF-Mod-1/Mod-2 cycle history | +90 |
| `docs/reference_parity_status.md` | P-4 entry updated to two-fixture coverage; status banner v1.1.0 → v1.1.1 | +18 / -7 |
| `docs/bond_yield_forecast_integration/byf_mod2_findings.md` | NEW (this file) | ~210 |
| **Total (excluding .xlsx binary)** | | **~570 LOC** |

## Verification gates

| Gate | Status |
|---|---|
| `engine/tests/` pytest | ✅ 96/96 PASS preserved |
| `engine/techniques/bond_yield_forecast/tests/` pytest | ✅ **104 PASS** + 16 SKIP (was 102+16 at Mod-1; +2 from `test_dispatch_maturity_names.py`) |
| Parity audit `--technique p3_bond_yield_forecast` | ✅ **PASS** on both fixtures (12 reproducibility checks + 8 invariants = 20/20) |
| 10-maturity numerical-array preservation vs pre-Mod-2 baseline | ✅ Zero mismatches (B-Mod1-1 fix is label-only) |
| `engine/techniques/bvar.py` | ✅ UNCHANGED across BYF-Mod-1 + BYF-Mod-2 |
| `--check-environment` | ✅ clean |

## Modification cycle close

**Modification cycle 1** (BYF-Mod-1 commit `3d15bf3` + BYF-Mod-2
this commit) closed cleanly:

- 34-maturity declarative grid with sparse-column auto-detection
  shipped (Mod-1).
- Parity audit extended to two-fixture coverage with measured
  Pattern F thresholds (Mod-2).
- Two banked findings resolved (B-Mod1-1 dispatch fix shipped;
  B-Mod1-2 measurement confirmed no threshold change needed).
- P-4 status tracker reflects new state at v1.1.1.

**No new banked items pending.** All Mod-1 banked items either
resolved here (B-Mod1-1, B-Mod1-2) or already in the existing
Phase 4 v1.2.0 amendment candidates document (which absorbs any
future cross-implementation parity work).

The wrapper count remains 84; the parity check count remains 83
(BYF audit covers two fixtures within one P-4 entry).

## Next session

User-driven. The post-cycle wrapper is now production-ready with:
- Full 34-maturity declarative grid (any sparse subset 3 ≤ N ≤ 34
  accepted).
- User-visible Yield Forecast table with canonical maturity labels.
- Two-fixture audit coverage proving sparse-column code path
  correctness across both legacy and dense-grid inputs.

Next BYF tweak request would be a fresh modification cycle
(BYF-Mod-3 / -4 / etc.) following the same Mod-1 (implementation)
+ Mod-2 (audit + docs) two-session pattern this cycle established.
