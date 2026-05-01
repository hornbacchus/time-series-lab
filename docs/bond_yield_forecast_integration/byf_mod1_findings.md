# Bond Yield Forecast Modification 1 (BYF-Mod-1) — Findings

**Date:** 2026-05-01
**Scope:** Maturity grid expansion 10 → 34; column-level sparse-input
auto-detection. Per BYF-Mod-1 trigger §"Locked decisions from Chat
planning session".
**Status:** COMPLETE.

## Pre-modification audit (§1.1) — touch-point inventory

| Surface | Touch needed | Reason |
|---|---|---|
| `config/default.yaml` `yield_variables` | Yes | declarative grid expansion |
| `data.py` `validate_input` | Yes | replace strict-presence loop with sparse-column auto-detection |
| `data.py` (new module-level) | Yes | header canonicalization helper + populated-subset resolver |
| `_dispatch.py` audit_fields | Yes | surface `n_maturities_populated` + `maturities_populated` for transparency |
| `_dispatch.py` summary text | Yes | replace `or 10` magic-number with dynamic count |
| `tests/test_data.py` | Yes (1-line) | length assertion 10 → 34 |
| `resources/templates/bond_yield_forecast_input_template.xlsx` | Yes | regenerate with 34 columns + README sparse-behavior docs |
| `unified_input.py` `write_unified_template` | No | already auto-expands from config["data"]["yield_variables"] |
| `conditioning.py` | No | uses shape-based indexing + `pca_dict["yield_names"]`; sparse-safe |
| `validation.py` | No | already defensive on missing keys via `try/except ValueError: pass` and `_bps_at()` returns "N/A" for missing |
| `data.py` `fit_pca` / `project_to_pcs` / `reconstruct_yields` | No | sklearn PCA accepts variable column count; downstream uses shape-based indexing |
| `engine/ExcelWriter.cs` | No | renders rows generically; no maturity-axis hardcoding |
| C# rebuild | No | no C# changes required |

The architecture's prior shape-based indexing meant the variable-N
adaptation was concentrated in `validate_input`'s column-presence
check. PCA, conditioning, validation, and dispatch downstream all work
unchanged on N≠10 inputs.

## Decisions made during execution

### Architecture: sparse detection lives in `validate_input`

The `_resolve_populated_yield_columns(yields_raw, expected_yield_cols)`
helper:
- Walks workbook columns, canonicalizing each header via
  `_canonicalize_maturity_header`.
- Filters to (a) headers matching the canonical 34-grid AND
  (b) columns with at least one non-NaN data value.
- Returns the filtered list ordered by config (1M < 3M < ... < 30Y) so
  column ordering is deterministic regardless of workbook header
  order.

Three failure modes raise `InputValidationError`:
- `unrecognized_maturity_header`: non-blank header with data that
  doesn't canonicalize to any of the 34 declared maturities (strict
  rejection of garbage headers; no silent acceptance).
- `no_populated_maturities`: zero declared maturities present.
- `insufficient_maturities`: fewer than `MIN_MATURITY_COUNT` (=3) —
  the PCA factor structure floor.

Empty headers, or headers in the 34-grid where the column data is
entirely NaN, are silently dropped (the locked sparse-column UX:
"you may delete or leave empty any maturity columns you do not have
data for").

### Header canonicalization scope

`_canonicalize_maturity_header` accepts case-insensitive,
whitespace-/separator-tolerant variants of:
- `"<n>Y"` for 1 ≤ n ≤ 30 (year suffix variants: `Y`, `Yr`, `year`, `years`)
- `"<n>M"` for 1 ≤ n ≤ 11 (month suffix variants: `M`, `mo`, `month`, `months`)

Canonical form is `"NM"` for sub-year months, `"NY"` for years. This
matches the canonical column-header form already in use in
`config/default.yaml` and the sample template.

### Byte-identical numerical equivalence verified (§1.10b-early)

Per plan §1.10b critical check: ran the post-modification code on the
canonical 10-maturity test fixture. All 80 yield-forecast rows + 24
macro-paths + 174 convergence-diagnostics rows + audit_fields
(excluding `timestamp_utc` and the `runtime_seconds` row in
`Run Metadata` per Session 0 Refinement 3) are **bit-exact** versus
the pre-modification baseline `output/byf_mod1_pre/baseline.json`
(sha256 `fd8608b4…0454c468`).

The only diffs are:
- `audit_fields["timestamp_utc"]` — clock-driven.
- `Run Metadata` row 7 cell `["runtime_seconds", 1.85]` →
  `[..., 1.82]` — clock-driven.
- New audit field `n_maturities_populated` = 10 (additive, not a
  numerical-array diff).
- New audit field `maturities_populated` =
  `['treasury_3m', ..., 'treasury_30y']` (additive).

Numerical-array equivalence confirmed: zero mismatches in the BVAR-SV
draws, conditional-forecast draws, PCA loadings, or convergence
diagnostics. The sparse-column code path on legacy 10-maturity input
produces identical numerical output to pre-modification code.

### 34-maturity smoke test (§1.10b-late)

Regenerated sample template runs end-to-end through the dispatch:
- 1000 draws / 250 burn / 50 paths/draw / horizon=8 / seed=20260427
- Wall-clock: ~7s (warm JIT)
- 272 yield-forecast rows produced (8 horizons × 34 maturities)
- All medians finite + in plausible band [0, 15]%
- `audit_fields["n_maturities_populated"] = 34`
- `audit_fields["maturities_populated"] = [treasury_1m, ..., treasury_30y]`

## Banked findings for BYF-Mod-2

### B-Mod1-1 — Dispatch attribute-name mismatch on maturity labels

**Origin:** Surfaced during smoke-test development at §1.8.

`_dispatch.py:321` reads:
```python
maturity_names = list(getattr(yield_forecast, "yield_names", [])) or [
    f"Maturity_{i}" for i in range(n_mat)
]
```

But `conditioning.py:766-775` constructs `YieldCurveForecast(...,
maturity_names=list(pca_dict["yield_names"]), ...)` — i.e., the
attribute is `maturity_names`, NOT `yield_names`. The fallback `or
[f"Maturity_{i}" for i in range(n_mat)]` triggers, producing
unhelpful labels like `Maturity_0` in the user-facing Yield Forecast
table instead of canonical `treasury_3m` / `treasury_10y` names.

**Pre-existing bug** (verified: same `Maturity_0` labels in the
pre-Mod-1 baseline `output/byf_mod1_pre/baseline.json`). NOT introduced
by Mod-1; surfaced by writing tests that previously didn't assert on
the label format.

**Recommended fix in BYF-Mod-2:** change `_dispatch.py:321` to read
`getattr(yield_forecast, "maturity_names", [])`. One-line change;
makes the user-visible table labels meaningful. Will affect
byte-identical output of the legacy 10-maturity baseline, so should
be applied alongside the Mod-2 parity audit re-run (which re-anchors
the bit-exact reproducibility comparison anyway).

### B-Mod1-2 — Pattern F PCA explained-variance threshold may need recalibration on 34-mat input

**Origin:** Plan §1.10 escalation triggers; banked for Mod-2.

The current `p3_bond_yield_forecast` audit's Pattern F invariant
asserts PCA explained-variance ratio ≥ 99% (Litterman-Scheinkman 1991
threshold) on a 3-PC truncation. With 34 maturities (vs prior 10),
the 3-PC truncation captures relatively LESS of the variance because
the higher-frequency variation across more maturities is now in the
4th-N PCs. Threshold may need to relax to ≥ 95% or similar; the Mod-2
parity audit re-run will measure and recalibrate.

Not actioned in Mod-1 because no audit re-run is in scope.

## File topology summary

| File | Action | LOC delta |
|---|---|---|
| `engine/techniques/bond_yield_forecast/config/default.yaml` | yield_variables 10 → 34 entries | +85 |
| `engine/techniques/bond_yield_forecast/data.py` | header canonicalization + sparse resolver + integration in validate_input | +160 |
| `engine/techniques/bond_yield_forecast/_dispatch.py` | summary text + audit_fields transparency | +15 |
| `engine/techniques/bond_yield_forecast/tests/test_data.py` | length assertion 10 → 34 | +5 |
| `engine/techniques/bond_yield_forecast/tests/test_sparse_columns.py` | NEW — 13 tests | +290 |
| `engine/techniques/bond_yield_forecast/tests/test_full_grid_smoke.py` | NEW — 2 smoke tests | +135 |
| `engine/techniques/bond_yield_forecast/resources/templates/bond_yield_forecast_input_template.xlsx` | regenerated 11 → 35 columns + README addendum | (.xlsx binary; ~10 KB on disk) |
| `docs/bond_yield_forecast_integration/byf_mod1_findings.md` | NEW (this file) | ~210 |
| **Total** | | **~900 LOC** (excl. .xlsx binary) |

## Verification gates

| Gate | Status |
|---|---|
| `engine/tests/` pytest | ✅ 96/96 PASS preserved |
| `engine/techniques/bond_yield_forecast/tests/` pytest | ✅ 102 PASS + 16 SKIP (was 87 PASS + 16 SKIP; +15 = 13 sparse + 2 smoke) |
| 10-maturity byte-identical equivalence | ✅ PASS (numerical arrays bit-exact vs `output/byf_mod1_pre/baseline.json`) |
| 34-maturity smoke | ✅ PASS (272 rows, finite medians, plausible band) |
| 7-maturity sparse subset smoke | ✅ PASS (via `test_sparse_subset_smoke_forecast`) |
| Parity harness `--check-environment` | ✅ clean |
| Existing `engine/techniques/bvar.py` | ✅ UNCHANGED across BYF-Mod-1 |

## Next session

**BYF-Mod-2** — re-run parity audit on the new 34-maturity grid; update
`tools/reference_parity/harness/checks/p3_bond_yield_forecast.py` and
`tools/reference_parity/reports/p3_bond_yield_forecast_audit.md`;
update `docs/reference_parity_status.md` P-4 entry with the new
verdict; address banked findings B-Mod1-1 (dispatch attribute mismatch)
and B-Mod1-2 (Pattern F PCA threshold recalibration).
