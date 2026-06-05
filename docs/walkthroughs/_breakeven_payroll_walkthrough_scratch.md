# Breakeven Payrolls — walkthrough GROUND TRUTH (scratch for Chat to author from)

*Not prose — the surfaced material + worked-example numbers, mirroring the VAR scratch. Chat writes the
final `Breakeven_Payrolls_Walkthrough.md` (the 3rd use-case, after BVAR @ d8ac5dc and VAR @ 27ff19c).*

## What it is (one line)
The monthly nonfarm-payroll gain that holds the labor market in balance — derived from CBO potential LFPR
and the noncyclical (u*) rate over a CNP16OV-bridged population — and how it moves with net immigration.
Ported from the standalone Breakeven Payrolls research repo (@ 826d1d0); reference-parity validated.

## Interface (how a user runs it)
- **Bespoke ribbon member #2** (after Bond Yield Forecast): Time Series Lab ribbon → **Bespoke** group →
  **Breakeven Payrolls ▾** → **Open Input Template** / **Run Breakeven Payrolls**. Workbook-input (NOT a
  cell selection).
- **Open Input Template** now opens a **WORKING COPY** in `Documents\Time Series Lab\` (post-S5 fix — the
  bundled template is never edited). The pinned template (vintage 2026-05-30) has CBO + population baked in;
  the **yellow `scenario_inputs` tab** is the user's knob.
- **The knob:** `scenario_inputs.net_migration_all_ages` = 2026 net international migration (persons/yr).
  Default −370,000 (Brookings-mid) reproduces the Fed's near-zero breakeven. (`ustar_basis` = noncyclical
  / actual is display-only; the path uses the structural noncyclical u*.)
- **Run** → results in a **separate auto-named file** (the input is never modified). Four tables:
  (1) Breakeven Payrolls (Quarterly) — the path, 2026 flagged FORECAST; (2) Scenario Grid — 10 rows
  (5 migration presets × 2 u* defs); (3) Reconciliation Anchors; (4) Signal vs Noise.
- Data is **pinned by default** (no live FRED at run time); the user updates it over time by appending new
  CNP16OV to `population_monthly` (see the handoff-anchor contract below).

## ★ Worked examples — the knob moves the number (run 2026-06-03 vintage, seed n/a, deterministic)
| net_migration (k/yr) | scenario | 2026 pace (k/mo) | **2026 breakeven (k/mo)** |
|---|---|---|---|
| −925 | Brookings-low | −4.4 | **−17.9** (labor force shrinks → negative) |
| **−370** | **Brookings-mid (Fed DEFAULT)** | 37.7 | **7.2** (the validated near-zero) |
| +185 | Brookings-high | 79.8 | **32.3** |
| +320 | Census V2025 | 90.0 | **38.4** |
| +560 | (Matthew's example) | 108.2 | **49.3** |
| +590 | MS-house | 110.5 | **50.6** |
- The 2026 path breakeven at migration M equals that scenario's grid cell (coherent). The **same data, one
  knob** → the breakeven sweeps from −18 to +51 k/mo. Pre-2026 history is identical across scenarios (only
  the 2026 projected block responds to the knob). The headline story: immigration is the dominant 2026
  breakeven driver.
- Bug-history note (optional color): the knob was silently ignored until 2aa712f (it snapped any non-preset
  value to the Brookings-mid default); now any value drives the 2026 block.

## ★ The signal-vs-noise headline (the DELIVERABLE — §3.4 of the migration spec)
- Scenario breakeven band (grid min..max): **−17.9 .. +50.7 k/mo**.
- Single-print payroll **measurement band: ±100.8 k/mo** (= 1.645 × CES SE 61.3 = the 90% CI on one NFP
  print).
- Benchmark-revision **bias: −71 k/mo**.
- ★ **The entire breakeven signal (−18..+51 k/mo across the full plausible migration range) sits INSIDE the
  ±101k measurement band of a single monthly payroll print.** A given month's NFP number is mostly NOISE
  relative to the breakeven — you can't read one print as "above/below breakeven" with confidence; the
  breakeven is a slow-moving structural number, the print is a noisy draw around it.
- **Chart:** `docs/walkthroughs/breakeven_signal_vs_noise.png` (breakeven vs net migration, with the
  shaded ±101k band + the −71k bias line — the whole curve inside the band). Staged, same-dir relative ref.

## Architecture (for the technical section)
- Workbook-input technique `engine/techniques/breakeven_payroll/`: a **verbatim port** of the source repo's
  frozen math (`conventions` [FROZEN_STITCH 13/5, LFPR26 62.3954, V2025 base 274585], `stitch`,
  `population` [diff-splice + exact product-rule decomposition], `breakeven` [be = Δlf·(1−u*) + 5q centered
  MA], `scenarios` [pace(M) + sensitivity_grid], `potential_gdp`, `tolerances`) + a NEW TSL layer
  (`workbook_input.py` reads the 12/9-tab template; `_dispatch.py` run()).
- The standalone repo's data-acquisition layer (live/cached FRED + CBO + HPLFS) is REPLACED by the workbook
  reader: history + baked CBO/population come from the tabs; the active 2026 pace comes from the knob via
  `scenarios.pace(M)`.
- Output via the shared separate-file ExcelWriter (input never mutated).

## Validation (the technical-appendix story)
- **Cross-source reproduction** (the NEW pattern — first instance; see trust inventory §2.5): no external
  library implements this analysis, so the reference is the **source repo's own reconciled
  `fed_reference_path.csv` @ 826d1d0** — the analogue of the cross-package R checks, with the original
  standalone repo as the independent implementation.
- **`p3_breakeven_payroll`** (verdict_class `closed_form`): TIGHT full-path **0.19 jobs/mo** over the
  260-quarter MA-stable region (1962Q1→2026Q4); TIGHT grid **0.0** (Brookings-mid/Fed 7.2386, MS-house
  50.6638); all 6 reconciliation anchors PASS (avg_1970s 189,377; avg_2010s 74,862; pt_late_2020 47,734;
  avg_2023_24 152,835; avg_2025 87,095; avg_2026 7,239).
- **Discrimination (GREEN is meaningful):** BLOCKs on dropping the May-2025 handoff anchor (7,960 jobs/mo)
  and a +0.10pp CBO u* perturbation (211 jobs/mo).

## Provenance + caveats (carry into the walkthrough)
- **Provenance:** ported from the Breakeven Payrolls repo @ 826d1d0; methodology ref Murray & Vidangos,
  FEDS Notes 2026-04-02 (per the template `_meta`).
- **Handoff-anchor contract rule (user-updatable model):** when extending `population_monthly`'s CNP16OV
  append region over time, the segment must retain the **handoff-month anchor** — the CNP16OV value at the
  last HPLFS month (here May-2025), which is the diff-splice base for the first bridge increment. Without
  it the first increment is dropped (avg_2025 → 85,718 vs 87,095). The pinned template carries it.
- **Projected→realized 2026 caveat:** parity validates ONLY the reconciled replication. The 2026 block is a
  PROJECTION; as real data arrives there is no benchmark for the projected→realized evolution — validated
  by construction/sanity, not against a reference.
- **Frozen scenario-grid scalars (D1):** u* 0.044/0.0456, LFPR26 62.3954, census base 320k / pace 90 are
  the source's frozen literals (so the grid reproduces the Fed-reconciled comparison exactly); the
  historical path's u*/LFPR are CBO-quarterly-derived.

## Numbers source
`output/_breakeven_walkthrough_numbers.txt` (the sweep + signal-vs-noise, regenerable). Chart at the path
above. All deterministic on the pinned 2026-06-03 vintage fixture.
