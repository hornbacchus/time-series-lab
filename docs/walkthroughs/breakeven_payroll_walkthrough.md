# Breakeven Payrolls — TSL Use-Case Walkthrough

*The third TSL use-case walkthrough, after Bond Yield Forecast and VAR. A Bespoke technique: a faithful replication of the breakeven-employment estimate, with a migration-scenario engine and a signal-vs-noise read on the monthly payrolls print.*

---

## At a glance

**What it answers:** How many jobs a month does the economy need to add just to hold the unemployment rate constant — and how does that number move as the net-migration outlook changes?

**The one-line takeaway:** Under the plausible range of 2026 net-migration scenarios, breakeven payrolls span roughly **−18k to +51k per month** — and that entire band sits *inside* the **±101k** measurement noise of a single monthly nonfarm-payroll print. A single payroll number can't tell you which migration regime you're in.

**How you run it:** Bespoke ribbon group → **Breakeven Payrolls** → **Open Input Template** (a working copy opens) → set the migration knob → **Run**. Results open in a separate file; your template is never touched.

**What it is — and isn't:** a *faithful, deterministic replication* of the Murray–Vidangos breakeven-employment methodology (FEDS Notes, 2026-04-02), ported from a standalone repo and validated to reproduce its reconciled output to **0.19 jobs/month**. It is identity-driven accounting arithmetic — not an econometric model, no regression, no simulation. The numbers are reproducible bit-for-bit on the pinned data vintage.

---

## User Guide — five moves

### Move 1 — Open the input template

Bespoke ribbon → **Breakeven Payrolls** ▾ → **Open Input Template**.

A **working copy** opens — named `Breakeven_Payrolls_input_working_<timestamp>.xlsx`, in `Documents\Time Series Lab\`. This is deliberate: the copy is yours to edit and keep; the shipped template stays pristine, so you can always re-open a clean one. Work in the copy.

The template ships **pinned** to a fixed data vintage (the 2026-06-03 snapshot), so out of the box, Open → Run reproduces the validated Fed reference number with no setup. You only touch data when you choose to update it over time (Move 5).

### Move 2 — Set the scenario knob

Go to the **`scenario_inputs`** tab (the yellow cells — "the knobs you set"). The one that drives the headline:

- **`net_migration_all_ages`** — your 2026 net international migration assumption, in persons/year. The default is **−370,000** (the Brookings-mid case, which reproduces the Fed's near-zero 2026 breakeven).

The tab also lists **migration presets** for reference — Census V2025 (+320k), Brookings-high (+185k), Brookings-mid (−370k, the default), Brookings-low (−925k), and an MS-house case (+590k). Type any value you like; you're not limited to the presets.

A second knob, **`ustar_basis`**, selects which unemployment-rate basis the display uses (`noncyclical` vs `cbo_actual`) — a small (~0.16pp) difference shown in the scenario grid's two columns. Leave it on `noncyclical` for the faithful reproduction.

### Move 3 — Run

Bespoke → **Breakeven Payrolls** ▾ → **Run Breakeven Payrolls**.

A **separate results file** opens. Your working copy (and the bundled template) are untouched — results never write back into your input. The results carry four tables (Move 4).

### Move 4 — Read the four output tables

**1. Breakeven Payrolls (Quarterly)** — the historical breakeven path, quarter by quarter, back to 1960. The 2026 quarters are flagged **FORECAST** (they're projected, not observed). With the default knob, 2026 reads ≈ **7.2k/month** — the Fed's near-zero result.

**2. Scenario Grid** — the breakeven number across the full migration range, the reference comparison. This is the analytical core:

| Migration scenario | Net migration (persons/yr) | Breakeven (k/month) |
|---|---:|---:|
| Brookings-low | −925,000 | **−17.9** |
| Brookings-mid (Fed default) | −370,000 | **7.2** |
| Brookings-high | +185,000 | **32.3** |
| Census V2025 | +320,000 | **38.4** |
| (your input, e.g.) | +560,000 | **49.3** |
| MS-house | +590,000 | **50.6** |

Read it as: **every +100k of annual net migration raises the breakeven by roughly +4.5k/month.** Labor-force growth feeds directly into how many jobs are needed to hold the unemployment rate flat.

**3. Reconciliation Anchors** — six historical checkpoints (1970s, 2010s, late-2020, 2023–24, 2025, 2026) confirming the path reproduces the Fed reference. These are the validation receipts.

**4. Signal vs Noise** — the headline chart and the reason this technique earns its place (see below).

### Move 5 — Update over time (the operating model)

This is the use case the technique is built for: **watch the breakeven number evolve as real data arrives.**

As new months of population data print, you append them to the working copy's `population_monthly` tab, re-run, and the breakeven number updates. Over 2026, the projected quarters get progressively replaced by realized data, and the estimate firms up.

**★ One contract rule when you append:** the population data has two source segments (the historical series and the CNP16OV bridge), spliced at a handoff month. When you extend the bridge, **the new segment must retain its handoff-month anchor** — the first appended month needs the prior month present as its difference base, or the splice drops an increment and the recent path shifts. (This is the seam the port's validation specifically locked down; the template ships correctly anchored, and you preserve that anchor when you extend it.)

---

## The headline: signal vs noise

This is the finding that makes the technique worth running, not just the breakeven number itself.

The breakeven estimate has a **plausible range** — across the full span of credible 2026 net-migration scenarios (Brookings-low at −925k to the MS-house +590k), breakeven payrolls run from about **−18k to +51k per month**. That's a ~69k-wide band, and it captures genuine disagreement about the migration outlook.

Now put that against the **measurement noise** in the data you'd use to read it. A single monthly nonfarm-payroll print carries a 90% confidence interval of roughly **±101k** (±1.645 × the ~61k CES standard error) — *and* the establishment-survey benchmark revision has been running around **−71k**. So the noise in one month's payroll number is *larger than the entire spread of breakeven scenarios.*

**The implication for reading the data:** when a payroll print lands, you cannot use it to identify which migration regime you're in — the scenarios are closer together than the measurement error is wide. A +50k print is consistent with the high-migration breakeven *and* with a low-migration world that got a noisy draw. The breakeven question is real and the migration sensitivity is real, but a single month's payrolls is mostly noise against it. You need multiple prints, or you reason from the migration outlook directly rather than back-solving it from the jobs number.

That's a genuinely useful thing for a desk to internalize: it reframes how much weight to put on any one payroll surprise.

---

## Technical Appendix

### What the technique computes

Breakeven payrolls = the monthly nonfarm-payroll gain that holds the unemployment rate constant, given the growth of the potential labor force. The core identity:

- **Potential labor force** = working-age population × the (CBO-projected) potential labor-force participation rate.
- Its **monthly change** (an exact product rule on population × participation) gives the labor-force growth that must be matched.
- **Breakeven** = that labor-force growth scaled by (1 − u*), where u* is the noncyclical (structural) unemployment rate — the share of new entrants that translates into employment rather than measured unemployment.

The historical path runs this on CBO quarterly series (potential LFPR and u*) and a spliced monthly population series, with a 13-month centered moving average on population and a 5-quarter centered average on the breakeven series. The 2026 block is projected forward from a base population at a migration-dependent pace.

**The migration elasticity** (≈ +4.5k/month breakeven per +100k annual net migration) falls out of the identity: `Δbreakeven = Δmigration × 0.91 (the 16+ share) × LFPR × (1 − u*) / 12`.

### Architecture — how it ports into TSL

The technique is a **workbook-input Bespoke member** (like Bond Yield Forecast): you don't select cells, you point it at a structured input workbook. The TSL build reuses the standalone repo's computation modules essentially verbatim — the splice, the population build, the product-rule breakeven, the scenario engine — and replaces the standalone's live-data-acquisition layer (FRED fetches, fallbacks) with a workbook reader. The shipped template carries a pinned data snapshot, so the technique runs with no network dependency: **read workbook → compute → write a separate results file.**

The scenario knob reads from the workbook's `scenario_inputs` tab and feeds the same migration-pace formula the scenario grid uses, so the active 2026 projection and the grid are coherent (your input's breakeven matches its grid cell).

### Provenance

Ported from the standalone Breakeven Payrolls repository (commit `99c03ba` — preset-only re-port 2026-08-08 adding the CBO_Feb2026 scenario preset + the gross_migration_sums template tab; path math unchanged since the original `826d1d0` port), itself a faithful replication of Murray & Vidangos, *"The Breakeven Rate of Payroll Employment Growth,"* FEDS Notes, 2026-04-02. The conventions (moving-average windows, the product-rule decomposition, the December population-control seam, the frozen scenario-grid scalars) are preserved exactly from the source — the technique reproduces a *specific, validated* pipeline, not a re-derivation.

### Validation — cross-source reproduction

This technique introduced a new validation pattern to TSL's trust inventory: **cross-source reproduction.** Where most TSL techniques validate against an independent implementation in a different package (e.g. an R library), here the independent reference is the *original standalone repository's reconciled output* (`fed_reference_path.csv`).

The parity check (`p3_breakeven_payroll`, `verdict_class = closed_form`) asserts:

- **Tight full-path parity** — the TSL workbook path reproduces the source's reconciled quarterly breakeven series over 1962-Q1 → 2026 to a maximum difference of **0.19 jobs/month** (float-level; the residual is Excel cell-storage rounding, not logic).
- **Tight scenario grid** — the 10-row migration × u* grid reproduces the source's grid (the Brookings-mid tie-out at 7.24, MS-house at 50.66, all rows) to **0.0**.
- **The six historical anchors** as a ballpark overlay.

The check is **discrimination-verified** — it does not merely pass on the correct build, it *fails* (BLOCKs) on deliberately-broken ones: dropping the population splice's handoff anchor pushes the path to 7,960 jobs/month (caught); perturbing a CBO input by 0.10pp pushes it to 211 jobs/month (caught). A parity check that can't fail proves nothing; this one provably catches the exact errors it guards against.

### Limitations and honest caveats

- **The 2026 block is projected, not observed.** It is flagged FORECAST in the output. The reconciliation validates the *all-projected* 2026 case against the Fed reference; there is **no benchmark yet** for the projected→realized transition as actual 2026 data fills in. That evolving figure is validated *by construction* (it runs the same identity on more-realized data), not against an external reference — until a future Fed-style update prints with realized 2026 data to anchor it. Treat the earliest-2026 evolving number as the least-settled quantity.
- **Faithful-locked, not a free desk model.** The methodology conventions are fixed (engine constants), reproducing the published methodology. Only the scenario inputs (migration, the u* basis) are user-editable. This is deliberate — it preserves the validation guarantee. The scenario-grid scalars are frozen literals from the source (the exact values the validated reconciliation used), so the technique reproduces *that* pipeline byte-for-byte rather than re-deriving the anchors from the current data vintage.
- **The migration sensitivity is the mechanical identity, not a forecast.** The grid shows what breakeven *would be* under each migration assumption; it does not forecast which assumption is right. The value is in sizing the sensitivity and the signal-vs-noise framing, not in predicting migration.
- **Pinned vintage.** The shipped template carries a fixed 2026-06-03 data snapshot. To refresh, you update the data in the working copy (the operating model) — the technique does not fetch live data at run time.
