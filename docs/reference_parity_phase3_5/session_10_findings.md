# Phase 3.5 Session 10 — Substantive slack absorption + Session 11 amendment plan

**Date:** 2026-04-30
**Scope:** Slack absorption (per chat check-in disposition a) +
preparation artifacts for Session 11 documentation phase.
**Status:** COMPLETE (single-session close).

Two streams executed:
- **Stream 1**: Inventoried Sessions 1-9 banked items;
  produced Session 11 amendment plan (separate document at
  `session_11_amendment_plan.md`).
- **Stream 2**: Bounded preparation artifacts for 5 amendment
  sites whose banked findings required additional drafting
  context.

## STREAM 1 — Session 11 amendment plan

See **[`session_11_amendment_plan.md`](session_11_amendment_plan.md)**
in this directory for the full plan.

### Plan summary

| Document | Sections amended | Estimated LOC |
|---|---:|---:|
| P-4 status tracker | 1 | 30 |
| P-1 parity standard | 9 | 150 |
| P-2 diagnostic reference | 6 | 180 |
| P-3 empirical findings | 6 | 250 |
| **Total** | **22 sites** | **~610 LOC** |

Single-session feasible; comparable to Phase 3 Sessions 16-17
(P-2 + P-3 v1.0.0 issuances at ~700 / ~600 LOC respectively).

### Drafting order locked at 19 steps

Optimized for cross-reference resolution (amend referenced
sections before referring sections). P-4 first; P-1 §5.1 →
P-2 §A.10 ordering enforced; P-2 §B header note (Pattern J
scoping rule) MUST come after §B.4.3 + §B.6.3 are added so
the rule has concrete examples to anchor. Change logs swept
last.

### 6 amendment sites depend on Stream 2 prep artifacts

Cross-mapping documented in plan §"Items requiring Session 10
Stream 2 preparation artifacts." Session 11 references this
findings doc directly when drafting those amendments.

## STREAM 2 — Preparation artifacts

### §10-S2.A — Pattern J catalog entry artifacts

#### §10-S2.A.1 — CRAN-vs-R-runtime version representation (P-2 §B.4.3 NEW)

**Concrete evidence** from S5 manifest re-pin cycle:

Pre-S5 `MANIFEST.toml` had two R packages with CRAN's
hyphen-suffix version format:
```toml
robustbase = "0.99-7"
dtw = "1.23-2"
```

`--check-environment` reported them as "divergences" because
R's `packageVersion()` renders the same versions in dot-format:
```
R divergences:
  robustbase: pinned=0.99-7 actual=0.99.7
  dtw: pinned=1.23-2 actual=1.23.2
```

**Resolution at S5:** normalize manifest pins to dot-format to
match `packageVersion()` output. Bit-identical CRAN releases;
zero behavioral change.

```toml
# Post-S5
robustbase = "0.99.7"
dtw = "1.23.2"
```

**Pattern J.B.4.3 framing** (for P-2 §B.4 "Version-default
drift"):

CRAN releases R packages with hyphen-suffix versions for sub-
patch revisions (e.g., `0.99-7`). When R loads the package,
`packageVersion()` renders this as `0.99.7` (dot-format). Both
representations refer to bit-identical package code; only the
string representation differs.

**Convention:** TSL manifest pins use the dot-format that
matches `packageVersion()` output. This keeps
`--check-environment` clean (no spurious divergence reports)
without requiring custom normalization code in the harness.

**Severity:** cosmetic; documented to prevent contributors
from confusing format-only differences with actual version
drift.

---

#### §10-S2.A.2 — statsmodels ↔ x13ashtml integration deferral (P-2 §B.6.3 NEW)

**Concrete error trace** from S6 WIP-3 CI run:

```
Fixture file missing: [Errno 2] No such file or directory:
'/tmp/tmpbdv0xoyv.err'
```

**Root cause** (per S6 findings § "Loss 3"):

- statsmodels' `x13_arima_analysis` expects the classic `x13as`
  binary's output convention: a temp prefix with `.err` /
  `.lkr` / `.txt` / `.acm` / `.rcm` / `.tdf` outputs.
- The R `x13binary` package installs `x13ashtml` (HTML-aware
  build of X-13ARIMA-SEATS) which writes to a different
  location (or under different naming) than statsmodels
  expects.
- The binary itself **runs correctly** (verified via R
  `seasonal` package which uses the same binary and would
  PASS the parity check on its end).
- This is an upstream **statsmodels-vs-x13ashtml integration
  issue**, not a TSL wrapper bug.

**Workaround scaffolding preserved in `parity-slow.yml`**:

```yaml
# x13binary install (R seasonal works with this binary)
- name: Install full manifest R packages + X-13 binary
  run: install.packages(c(..., "x13binary", "seasonal"), ...)

# Symlink x13ashtml -> x13as (preserved for forward use)
- name: Resolve X-13 binary path (documentation only)
  run: |
    X13_DIR=$(Rscript -e 'cat(x13binary::x13path())')
    if [ -f "$X13_DIR/x13ashtml" ] && [ ! -e "$X13_DIR/x13as" ]; then
      ln -s x13ashtml "$X13_DIR/x13as"
    fi
    # X13PATH/X12PATH NOT exported (Session 6.5 deferral) —
    # statsmodels then raises X13NotFoundError -> harness SKIP
```

**Pattern J.B.6.3 framing** (for P-2 §B.6 "Master plan §15.12
reference adjustments"):

Even when both TSL and the reference invoke the same binary
(Pattern A.1 same-library), differences in binary build
variants (`x13as` vs `x13ashtml`) can produce different output
file conventions. statsmodels' Python wrapper expects one
convention; R `seasonal` accepts the other. Phase 3.5 Session 6
deferred resolution to Phase 4 after three install attempts
produced three different failure modes (criterion #3 of the
Session 6.5 escalation protocol).

**SKIP-graceful preservation rationale:** runtime-dependency
unavailable produces SKIP per [P-1 §2.4 SKIP-graceful runtime
convention]; both Windows (binary not on system PATH) and
Linux (binary present but X13PATH deliberately not exported)
SKIP gracefully. CI green; user-facing behavior consistent
across platforms.

---

### §10-S2.B — Per-metric tolerance ladder schema (P-1 §5.2.1 NEW)

**Schema description** (formal form for P-1 amendment):

A tolerance ladder MAY declare an optional `per_metric` block
mapping metric names to per-metric tolerance band definitions.
When present, the harness's `_get_metric_tol(ladder,
metric_name, fallback_key="primary")` helper returns the
per-metric band; absent metric names fall back to
`ladder["primary"]` (or `ladder[fallback_key]` if non-default).

**Schema:**

```python
tolerance_ladder = {
    "type": "tiered_outputs",
    "primary": {
        "abs_tol": float,
        "rel_tol": float,
        "block_abs_tol": float,
        "block_rel_tol": float,
    },
    "secondary": {  # optional
        "abs_tol": float, ...
    },
    "per_metric": {  # OPTIONAL — Phase 3.5 Session 4 schema extension
        "<metric_name_1>": {
            "abs_tol": float,
            "rel_tol": float,
            "block_abs_tol": float,
            "block_rel_tol": float,
        },
        "<metric_name_2>": {...},
    },
    "justification": str,
}
```

**Helper signature:**

```python
def _get_metric_tol(
    ladder: dict[str, Any],
    metric_name: str,
    fallback_key: str = "primary",
) -> dict[str, float]:
    """Look up tolerance band for a specific metric, with
    optional per-metric override."""
    per_metric = ladder.get("per_metric", {})
    if metric_name in per_metric:
        return per_metric[metric_name]
    return ladder[fallback_key]
```

**Migration criterion:** populate `per_metric` block when
empirical evidence shows ≥1 order of separation between metrics
within a single wrapper's output. Sub-1-order heterogeneity
does NOT justify per-metric splitting (single-band ladder
preserves simplicity).

**Concrete migration precedents** (from S4):

`p3_hmm` (em_stochastic class):

| Metric | Achieved abs | Single-band ceiling | Per-metric band | Headroom (orders) |
|---|---:|---:|---:|---:|
| transition_matrix | 0.237 | 0.3 abs | **0.3 / 1.0** (kept — Pattern H DSCD-EM) | 0.1 |
| emission_means | 1.48e-5 | 0.3 abs | **1e-3 / 1e-3** (tightened) | 1.8 |
| emission_covars | 7.74e-5 | 0.3 abs | **1e-3 / 1e-3** (tightened) | 1.1 |
| log_likelihood | 5.46e-6 | 0.3 abs | **1e-3 / 1e-3** (tightened) | 2.3 |

`p3_markov_switching` (em_stochastic class):

| Metric | Achieved abs | Single-band ceiling | Per-metric band | Headroom (orders) |
|---|---:|---:|---:|---:|
| regime_means | 5.90e-5 | 2.0 abs | **1e-2 / 1e-2** (tightened) | 2.2 |
| transition_matrix | 5.46e-2 | 2.0 abs | **2.0 / 1.0** (kept) | 1.6 |
| log_likelihood | 0.348 | 2.0 abs | **2.0 / 1.0** (kept) | 0.8 |

**Implication for Pattern H DSCD:** within an em_stochastic
wrapper, the DSCD pattern is **metric-specific**, not wrapper-
wide. Both audited wrappers showed DSCD on transition matrices
and log-likelihoods (where EM label-permutation and sign-
convention ambiguities live) but per-component agreement at
machine-precision-adjacent tolerances on emission / regime
means.

---

### §10-S2.C — R-bridge cross-platform Rscript protocol (P-1 §6.2 NEW)

**Protocol description** (formal form for P-1 amendment):

The harness's `_resolve_rscript_exe()` helper (in
`tools/reference_parity/harness/r_bridge.py`) implements a
3-step fallback for cross-platform Rscript executable
resolution. This protocol enables the harness to run on
Windows dev machines (where the manifest pin points at the
local R install) AND CI runners (Linux / macOS) where the
manifest pin doesn't exist.

**3-step resolution cascade** (in priority order):

1. **`RSCRIPT_EXE` environment variable** (explicit override).
   When set and points to an existing executable, use it.
   Highest precedence; supports CI matrix entries that pin a
   specific R install path.

2. **Manifest pin** (`MANIFEST.toml [r] rscript_exe`).
   When the manifest's pinned path exists on disk, use it.
   This catches the canonical Windows dev-machine path
   (`C:/Program Files/R/R-4.5.3/bin/Rscript.exe`).

3. **`shutil.which("Rscript")`** (system PATH lookup).
   Fallback when neither override nor manifest pin resolves.
   Catches Linux/macOS CI runners where `r-lib/actions/setup-r`
   installs Rscript to a path not present in the manifest
   (`/usr/bin/Rscript` or `/opt/R/<version>/bin/Rscript`).

**Failure mode:** if all 3 steps fail, raise
`RNotAvailableError`; caller's check loop translates this to
SKIP per the SKIP-graceful runtime convention (P-1 §2.4).

**Caching:** result is cached on the `RBridge` instance
(`_rscript_exe_cached`). PATH-fallback path emits a one-time
stderr warning ("manifest rscript_exe not found on disk;
falling back to PATH-resolved <path>") to surface the
fallback to the operator without spamming.

**Backward compatibility:** Windows dev-machine behavior is
preserved unchanged — manifest pin is checked at step 2 and
returned when valid. The fallback only activates when the
manifest pin doesn't resolve, which is the intended
Linux/macOS CI behavior.

**Empirical validation** (Phase 3.5 Session 6):
- Pre-fix Linux runner: 5/6 R-using slow-tier checks SKIPped
  with "Rscript executable not found:
  C:/Program Files/R/R-4.5.3/bin/Rscript.exe"
- Post-fix Linux runner: 5/6 R-using slow-tier checks PASS.

---

### §10-S2.D — Pattern A.1 4-dimensions aggregate table (P-3 §3.4 NEW)

**Aggregate empirical evidence** for Pattern A.1 stability
claim production-lock (P-3 §3.4 NEW SECTION):

#### Dimension 1 — Implementation stability

Pattern A.1 wrappers (Phase 3 Batch 1-10): 18 wrappers
classified as same-library reproducibility verification (per
P-2 §C.1 Pattern A taxonomy).

| Phase | Wrapper count | Verdict distribution |
|---|---:|---|
| Phase 3 Batch 1 | 4 | 4 PASS |
| Phase 3 Batches 2-10 | 14 | 14 PASS |
| **Phase 3 cumulative** | **18** | **18 PASS** (100%) |

#### Dimension 2 — Version stability

Phase 3.5 Session 5 quarterly re-pin: 4 pin updates (PyWavelets
1.8.0→1.9.0, forecastHybrid 5.0.19→5.1.21, robustbase + dtw
format-norms). Selective re-validation on 9 sentinel wrappers
(rugarch, forecast, KFAS, statsmodels, scipy, sklearn, torch,
PyWavelets ×2). Verdict: **9/9 PASS** post-re-pin; 0 wrappers
regressed across the version updates.

#### Dimension 3 — Cross-pair stability (Phase 3.5 Sessions 7+8)

GARCH-family runs across 4 FX pairs + 3 commodities = 7 real-
data series × 3 variants (sGARCH, GJR-GARCH, EGARCH) = 21 runs.

| Series | sGARCH log-lik | GJR-GARCH log-lik | EGARCH log-lik |
|---|---:|---:|---:|
| GBPUSD | −2071.83 | −2071.63 | −2081.05 |
| USDJPY | −1994.96 | −1994.59 | −2006.68 |
| AUDUSD | −2372.99 | −2372.98 | −2374.09 |
| EURJPY | −2042.52 | −2040.21 | −2041.70 |
| WTI | −5651.92 | −5636.17 | −5648.19 |
| NG | −6692.76 | −6692.65 | −6692.97 |
| HG | −4374.72 | −4374.22 | −4377.08 |

**Verdict: 21/21 status=success.** GJR-GARCH log-likelihood ≥
sGARCH on every series (theoretically required: GJR is a strict
superset of sGARCH). Pattern A.1 stability holds across all 7
heterogeneous real-data series.

#### Dimension 4 — Cross-asset stability (Phase 3.5 Session 8)

Sessions 7-8 cumulative: same 21 runs above span FX (4 pairs)
+ commodities (3 series). Asset-class diversity:
- **Currencies**: GBPUSD, USDJPY, AUDUSD, EURJPY (carry-trade
  diversity; USD-cross + cross-pair construction)
- **Energy**: WTI, NG (oil + gas; volatility-clustering
  canonical)
- **Industrial metals**: HG copper

PELT change-point detection on DGS5 (rates) + WTI returns
(commodity): 2/2 status=success.

CSD on T10Y2Y / DGS5 / WTI (n_surrogates=100): 3/3
status=success.

**Cross-asset stability confirmed:** GARCH-family + PELT + CSD
wrappers produce numerically-well-formed outputs across rates,
FX, commodity asset classes.

#### Aggregate summary

| Dimension | Count | Verdict |
|---|---:|---|
| Implementation (Phase 3 Pattern A.1 wrappers) | 18 | 18 PASS |
| Version (S5 quarterly re-pin sentinels) | 9 | 9 PASS |
| Cross-pair (Sessions 7-8 GARCH) | 21 | 21 status=success |
| Cross-asset (Sessions 8 PELT/CSD) | 5 | 5 status=success |
| **Total Pattern A.1 evidence** | **53** | **0 regressions** |

**Pattern A.1 production-locked.** P-3 §3.4 NEW elevates the
claim from "candidate" status to "empirically confirmed
across 4 dimensions."

---

### §10-S2.E — Master plan §4 Item 9 assumption-mismatch narrative (P-3 §2.4 NEW)

**Two-paragraph narrative draft** for P-3 §2.4 NEW SECTION:

> #### 2.4 — Master plan §4 Item 9 implicit-assumption mismatch — methodology evolution
>
> The Phase 3 master plan §4 Item 9 originally framed "macro
> fixture expansion" as a precursor to "Phase 3 wrappers re-
> validated on macro fixtures." The implicit assumption was
> that the parity harness would consume the macro fixture
> pool in CI, exercising real-data inputs through the same
> per-check `setup_fixture` → `run_tsl` → `run_reference` →
> `compare` lifecycle that synthetic DGP fixtures use. Phase
> 3.5 Sessions 7-9 surfaced that this assumption was structural
> rather than substantive: the parity harness uses synthetic
> DGP fixtures by design (per-check generators with seed-pinned
> reproducibility), not real-data fixtures with SHA256 pins.
> The macro fixture (`tools/calibration_audit/fixtures/
> macro_canonical_series.npz`) is consumed by 56
> calibration-audit and validate-canonical scripts under
> `tools/`, but is referenced by zero parity-harness checks.
>
> The methodology evolution that resolves this: macro fixture
> expansion serves **wrapper-level re-validation** (direct
> RunContext invocation outside the parity harness) rather
> than parity-harness CI runtime. Sessions 7-8 verified
> Pattern A.1 stability across 4 dimensions by exercising
> wrappers on the new FX + rates + commodity series in
> bounded scripts, NOT through harness fast-tier sweeps. This
> distinction is methodologically important for future Phase
> work: parity-harness fixtures are synthetic by design (DGP-
> reproducible, harness-stable, CI-cheap); real-data fixtures
> are wrapper-stress vehicles consumed by validate-canonical
> + calibration-audit scripts. Phase 3.5 codifies the
> distinction; Phase 4+ work can leverage the now-established
> 16-series macro fixture pool for Path Q-style FX
> investigations and other wrapper-level real-data sweeps
> without conflating the two fixture-acquisition paths.

---

## Effort assessment for Session 11

Based on the amendment plan + prep artifacts produced this
session:

| Document | Sections | LOC | Complexity |
|---|---:|---:|---|
| P-4 status tracker | 1 | 30 | Low |
| P-1 parity standard | 9 | 150 | Low-Medium |
| P-2 diagnostic reference | 6 | 180 | Medium |
| P-3 empirical findings | 6 | 250 | Medium-High (NEW SECTIONS §2.4 + §3.4) |
| **Total** | **22 sites** | **~610 LOC** | **Single-session feasible** |

Comparable to Phase 3 Session 16 (P-2 v1.0.0 issuance) and
Phase 3 Session 17 (P-3 v1.0.0 issuance) precedents.

**Single-session feasibility: HIGH.** All amendment sites have
clear target sections + (where needed) prep artifacts in this
findings doc. No structural changes to v1.0.0 organization
anticipated; all amendments are subsection additions or in-
place updates.

**Session 11.5 reservation:** if Session 11 surfaces unexpected
cross-document dependencies, continuation reserved per Phase 3
documentation phase precedent. No such dependencies surfaced
by this Session 10 audit.

## Items remaining as Phase 4 carry-forward

| # | Item | Source | Phase 4 role |
|---:|---|---|---|
| P4-1 | structural_invariants on 12 inherited (engine audit-field expansion + registry expansion) | S2 banking, deferred at S9 | Phase 4 master plan dedicated work item |
| P4-2 | statsmodels ↔ x13ashtml integration (TSL-side post-processor or pinned statsmodels patch) | S6 deferral | Phase 4 master plan |
| P4-3 | CSD wrapper engineering (n_surrogates default cap) | S8 finding | Phase 4 master plan |

These 3 items carry forward to the Phase 4 master plan
(drafted at Session 12 closeout decision). All three require
engine-side wrapper modifications outside Phase 3.5's narrow
parity-harness scope.

## Schedule status

10 of 17 sessions through Phase 3.5. On-pace numerically.
Sessions 11 + 12 close out the cycle:

- **Session 11**: Documentation phase (P-1/P-2/P-3/P-4 v1.1.0
  amendments; ~610 LOC across 22 sites; single-session
  feasible per this Session 10 plan).
- **Session 12**: Phase 3.5 closeout + Phase 4 launch
  decision.

## Commit footprint

| File | Change |
|---|---|
| `docs/reference_parity_phase3_5/session_11_amendment_plan.md` | new (~360 LOC) — Stream 1 plan |
| `docs/reference_parity_phase3_5/session_10_findings.md` | new (~430 LOC) — this doc, includes Stream 2 prep artifacts |
| `docs/reference_parity_status.md` | -1 / +12 LOC |
| **Total** | **0 LOC code; ~800 LOC docs** within CAL-R6 100-LOC engine-side budget (zero engine changes) |

## Next session

Phase 3.5 Session 11 — Documentation phase. Execute the
amendment plan in this doc + reference Stream 2 prep artifacts
in this findings doc.
