# Breakeven Payrolls

**Category:** Multivariate Systems
**Algorithm:** Labor-force-accounting breakeven payrolls — the monthly
nonfarm-payroll gain that holds the unemployment rate constant — built from
CBO potential labor-force participation and the noncyclical (u*) rate, the
civilian-population (CNP16OV)-bridged labor-force level, an exact product-rule
decomposition, and a net-migration scenario engine. Ported from the
authoritative Breakeven Payrolls research repo and reference-parity validated
against its reconciled path.

## What it does

Breakeven Payrolls computes the monthly payroll growth that keeps the labor
market in balance, and how it moves with net immigration:

1. Builds the monthly civilian noninstitutional population (16+) by splicing
   the harmonized HPLFS history with FRED CNP16OV month-over-month changes
   (diff-splice at the moving-average boundary), then projects 2026 forward at
   the scenario-implied pace.
2. Forms potential labor force = (13-month centered MA of population) x
   (CBO potential LFPR), and decomposes its change with the exact product rule
   into population-growth and participation-trend contributions.
3. Computes breakeven = delta(labor force) x (1 - u*), aggregated to quarterly
   and smoothed with a 5-quarter centered moving average (the 2026 standalone
   block is shown raw, not blended across the 2025 immigration surge).
4. Runs a net-migration scenario grid (Brookings / Census / MS-house presets x
   two u* definitions) giving the breakeven number under each migration path,
   and a signal-vs-noise overlay (the scenario band vs the +/-100k payroll
   measurement band and the benchmark-revision bias line).

## Input

A workbook-input technique (NOT a cell selection). Use the **Open Input
Template** ribbon item to drop a pinned, ready-to-run .xlsx: the CBO and
population data are baked in; the yellow **scenario_inputs** tab is yours to
set (the 2026 net-migration assumption — the Fed default of -370,000 reproduces
the near-zero 2026 breakeven). Edit, save, then **Run Breakeven Payrolls**.
The data is pinned by default (no live fetch at run time); you update it over
time by appending new CNP16OV observations to the population tab.

## Output

A separate results workbook (your input is never modified) with: the quarterly
breakeven payrolls path (2026 flagged FORECAST), the 10-row net-migration
scenario grid, the reconciliation anchors, and the signal-vs-noise overlay.

## Validation

Reference-parity validated (closed-form, cross-source): the workbook path
reproduces the source repo's reconciled fed_reference_path.csv to ~0.2 jobs/mo
across the moving-average-stable region, and the scenario grid matches the
source sensitivity grid (Brookings-mid/Fed ~7.2k/mo, MS-house ~50.7k/mo).
