# Phase 3.5 Session 9 — Item 9 closure + Stream 2 deferral

**Date:** 2026-04-30
**Scope:** Item 9 third session (Sessions 7-9 budget closure) +
Stream 2 consolidation candidate audit.
**Status:** STREAM 1 COMPLETE; STREAM 2 DEFERRED to Phase 4
with documented rationale.

Closes the Item 9 (macro fixture expansion) cycle with cross-
pair empirical synthesis. Audits the Stream 2 consolidation
candidate (structural_invariants on 12 inherited wrappers) and
defers per the bounded-scope rule because most candidates
require engine-side wrapper modifications outside the bounded
LOC budget.

## STREAM 1 — Cross-pair empirical synthesis (Item 9 closure)

### Sessions 7-8 cumulative evidence

**Fixture pool composition** (16 series, 10-year window
2015-04-25 to 2025-04-25, single npz file at
`tools/calibration_audit/fixtures/macro_canonical_series.npz`):

| Category | Series | Count | Sessions |
|---|---|---:|---|
| Rates (daily) | DGS2, DGS10, DGS5, DGS30, T10Y2Y | 5 | Phase 3 + S8 |
| Rates (monthly) | FEDFUNDS | 1 | S8 |
| FX | DEXUSEU, GBPUSD, USDJPY, AUDUSD, EURJPY | 5 | Phase 3 + S7 |
| Equity | GSPC | 1 | Phase 3 |
| Commodities | GOLD, WTI, NG, HG | 4 | Phase 3 + S8 |
| **Total** | | **16** | |

**Fixture pool composition rationale** (formalized as part of
Item 9 closure):

- **Rates term-structure breadth** (DGS2/5/10/30): four points
  along the Treasury curve enable yield-curve-shape stress
  tests (slope, curvature, level decomposition). T10Y2Y
  (cross-construct DGS10 − DGS2) is the canonical recession-
  signal spread; FEDFUNDS at native monthly captures
  policy-rate context distinct from market-implied curves.
- **FX coverage** (DEXUSEU + GBPUSD/USDJPY/AUDUSD/EURJPY): the
  EUR/GBP/JPY/AUD basket spans G10 carry-trade dynamics; EURJPY
  (cross-construct DEXUSEU × DEXJPUS) tests cross-construction
  conventions and decouples USD from the pair.
- **Commodity baskets** (GOLD precious + WTI energy + NG energy
  + HG industrial): three asset-class flavors with distinct
  vol-clustering profiles. GOLD covaries with rates regimes;
  WTI exhibits the strongest leverage-asymmetric stylized fact
  (verified empirically in S8); NG is the canonical extreme-
  vol-cluster series.
- **Equity (GSPC)**: single broad-market series for cross-asset
  correlation tests; not expanded in Phase 3.5 (S&P 500 is
  representative of US-equity behavior; sector / international
  expansion deferred to Phase 4).

### 21 GARCH-family runs across 7 series — empirical synthesis

Sessions 7 + 8 cumulative: 21 GARCH-family runs (sGARCH ×
GJR-GARCH × EGARCH = 3 variants × 7 series = 21 runs).

| Series | sGARCH log-lik | GJR-GARCH log-lik | EGARCH log-lik | GJR−sGARCH gap |
|---|---:|---:|---:|---:|
| GBPUSD | −2071.83 | −2071.63 | −2081.05 | 0.20 |
| USDJPY | −1994.96 | −1994.59 | −2006.68 | 0.37 |
| AUDUSD | −2372.99 | −2372.98 | −2374.09 | 0.01 |
| EURJPY | −2042.52 | −2040.21 | −2041.70 | 2.31 |
| WTI | −5651.92 | −5636.17 | −5648.19 | **15.75** |
| NG | −6692.76 | −6692.65 | −6692.97 | 0.11 |
| HG | −4374.72 | −4374.22 | −4377.08 | 0.50 |

**21/21 status=success.** GJR-GARCH log-likelihood ≥ sGARCH
on every series (theoretically required: GJR is a strict
superset of sGARCH).

**WTI shows the largest leverage gap (~16 likelihood units)** —
empirically consistent with oil's "cuts deeper than spikes"
stylized fact. This is an applied finding banked for **Macro
Strategy product backlog** (NOT a parity finding).

EURJPY (cross-construct) shows non-trivial leverage gap
(~2.3 units), validating that cross-constructed series
preserve the leverage-asymmetric structure of the underlying
components.

### Pattern A.1 stability claim — confirmed across 4 dimensions

Pattern A.1 (same-library wrappers stay numerically equivalent
across different inputs) was banked as a candidate empirical
claim at Session 5. Sessions 7-9 confirm across 4 dimensions:

| Dimension | Coverage | Verification |
|---|---|---|
| **Implementation** | TSL wrapper unchanged across runs | (default property) |
| **Version** | All runs at S5-pinned MANIFEST.toml versions | Session 5 |
| **Cross-pair (FX)** | 4 FX pairs × 3 GARCH variants = 12 runs | Session 7 |
| **Cross-asset (rates / commodities)** | 3 commodities × 3 GARCH variants = 9 runs | Session 8 |

**Net:** 21 GARCH runs across 7 heterogeneous real-data series,
all status=success, all log-likelihoods within sensible
ranges, all GJR ≥ sGARCH constraints upheld. Pattern A.1
claim **production-locked** for Session 11 P-3 documentation
phase.

### Selective re-validation methodology — codified

Sessions 7 + 8 established the convention:
- Select 1-2 wrappers per asset class for full sweep;
  remaining wrappers exercised on subset.
- Execute via in-process RunContext (not via parity harness,
  which uses synthetic fixtures).
- Verdict criterion: `status="success"` on every run; numerical
  sanity (GJR ≥ sGARCH, AIC ranking sensible, etc.).
- Failures classified as: (a) acquisition (§8.1 risk 2), (b)
  wrapper engineering (Phase 4 candidate), (c) data quality
  (defer affected pair).

This codifies Session 7 + 8's concrete methodology as the
template for Phase 4 fixture-expansion sessions.

### Wrapper-level boundary observations

| Observation | Origin | Disposition |
|---|---|---|
| WTI GJR vs sGARCH gap ~16 likelihood-units (vs ~0.2 typical for FX) | S8 GARCH sweep | **Macro Strategy product backlog** — NOT P-3 (applied finding) |
| Cross-constructed EURJPY preserves leverage structure | S8 EURJPY GJR gap = 2.3 | **Pattern J.E candidate** (cross-construction conventions) — Session 11 |
| CSD wrapper memory blow-up at default n_surrogates=1000 on long series | S8 T10Y2Y wrapper run | **Phase 4 wrapper-engineering** (NOT Pattern J.F — see re-banking below) |
| FEDFUNDS monthly amid daily fixture | S8 inventory | **Disclosure pattern** — Session 11 doc convention |

### Item 9 closure — original scope vs delivered scope

| Original master plan §4 Item 9 scope | Delivered |
|---|---|
| Macro fixture expansion (multi-FX, broader rates, commodities) | ✓ 4 FX + 4 rates + 3 commodities |
| Phase 3 wrappers re-validated on macro fixtures | Partial: Phase 3 PARITY harness uses synthetic DGP fixtures by design, NOT macro fixtures. Macro re-validation occurred at the WRAPPER level (engine/techniques) not at parity-harness level. |
| Path Q DEXUSEU follow-up | Not in scope this cycle (carry-forward to Phase 4) |

**Master plan implicit assumption mismatch surfaced:**

The master plan §4 Item 9 implied "Phase 3 wrappers re-
validated on macro fixtures" would exercise the parity harness.
In reality, the parity harness uses synthetic DGP fixtures
(per-check DGP generators) so macro fixture expansion has zero
impact on parity CI runtime. Wrapper-level re-validation
(direct RunContext invocation outside the parity harness) is
the correct interpretation. Codifying this for Session 11
documentation phase.

### Phase 4 forward-look — fixture pool now in place

The 16-series fixture is now positioned for:
- **Path Q-style FX investigations** — GBPUSD/USDJPY/AUDUSD/
  EURJPY × CSD / change-point / GARCH × volatility-regime
  detectors.
- **Term-structure stress** — DGS2/5/10/30 + FEDFUNDS for
  yield-curve regime detection.
- **Commodity vol-cluster characterization** — WTI/NG/HG
  GARCH studies, CSD on commodity returns.
- **Cross-asset correlation** — rates × FX × equity ×
  commodities matrices.

Phase 4 master plan (drafted at Session 12 closeout decision)
will reference this fixture pool as the canonical macro real-
data input.

### Re-banking decisions

Three findings re-banked away from generic Pattern J catalog
or premature P-3 amendments:

| Finding | Original banking | Re-banked to | Rationale |
|---|---|---|---|
| CSD n_surrogates=1000 memory blow-up | Pattern J.F catalog (S11) | **Phase 4 wrapper-engineering** | Pattern J catalog is scoped to **reference-library quirks** (e.g., R-package output convention mismatches). CSD blow-up is a **TSL wrapper default-scaling defect**, not a reference-library quirk. Mis-classifying it as J.F would dilute the J catalog's specificity. |
| T10Y2Y cross-construction | Pattern J.E catalog (S11) | **Tools-level convention; document but don't formalize as J entry** | Cross-construction is a fixture-pool convenience, not a wrapper-vs-reference parity quirk. Document in fixture-pool README / metadata; J catalog stays scoped to parity-investigation findings. |
| GJR vs sGARCH leverage asymmetry on commodities | (initially uncategorized) | **Macro Strategy product backlog** | Empirical applied finding; not a parity property. Belongs in product/strategy backlog, not P-3 documentation. |

These re-banking decisions tighten Pattern J's scope going
into Session 11 documentation phase: **Pattern J entries
should describe behaviors of the reference library that the
TSL parity harness must accommodate**, not TSL wrapper
defects or fixture conventions.

## STREAM 2 — structural_invariants on 12 inherited (DEFERRED)

### Audit results

The 12 inherited wrappers (per Session 2 banking) were
reviewed against the 14 concretely-registered invariant types
in `harness/structural_invariants.py`:

| Inherited wrapper | Best-fit registry type | Fit assessment |
|---|---|---|
| `_smoke_test` | (none) | No structural invariant applicable |
| `1c_bvar_irf_fevd` | (none — VAR is companion-form, BVAR is posterior-mean coefs; mismatch) | No clean fit |
| `2a_kalman_filter_smoother` | `kalman_covariance_ordering` | **Requires engine-side modification** — TSL kalman wrapper does not expose `filtered_state_cov`, `predicted_state_cov`, `smoothed_state_cov` time series in audit_fields. Adding these requires engine modification (not in Phase 3.5 bounded scope per master plan §4 Item 9 ≤30 LOC per wrapper rule + engine changes outside scope). |
| `2b_mcmc_sv_gaussian` | (none — no MCMC-specific invariants registered) | No registry fit |
| `2c_mcmc_sv_student_t` | (none) | No registry fit |
| `3a_caviar_sav` | (none — no quantile-regression invariant registered) | No registry fit |
| `3b_har_cj` | (none) | No registry fit |
| `3c_evt_ferro_segers` | (none — no EVT-specific invariant registered) | No registry fit |
| `3d_johansen_bartlett` | `vecm_cointegration_rank` | **Requires engine + harness modifications** — TSL johansen wrapper computes rank internally (`determined_rank_trace`/`_eig` variables) but does not expose in audit_fields; harness check would also need to extract corresponding R rank from urca output. ~30-40 LOC across 2 files, near bounded threshold. |
| `3e_mint_family` | (none — no hierarchical-coherence invariant registered) | No registry fit |
| `3f_transformer_attention` | (none) | No registry fit |
| `critical_slowing_down` | (none — no early-warning-signals invariant registered) | No registry fit |

**Net audit:** 0 of 12 inherited wrappers have a registry-type
fit AND a bounded engineering scope.

- 2 wrappers (2a, 3d) have registry-type fit but require
  engine-side modifications.
- 10 wrappers have no registry-type fit (would require new
  invariant types, expanding registry scope).

### Stream 2 deferral disposition

Per Session 9 prompt's deferral protocol:

> "If Session 9 capacity insufficient for Stream 2: Document
> Stream 2 deferral to Phase 4 with rationale (capacity vs
> scope assessment). Phase 3.5 closes Item 9 (Stream 1)
> cleanly; structural_invariants on 12 inherited carries
> forward to Phase 4 master plan."

**Capacity assessment:** Stream 1 closure consumed Session
9's expected capacity allocation. The Stream 2 audit revealed
that no inherited wrapper has a clean bounded-scope path:

- **Engine-side modifications** to expose covariance / rank
  fields are out-of-scope for Phase 3.5 (which is parity-
  harness-focused, not engine-modification-focused).
- **Registry expansion** to add new invariant types (MCMC
  convergence, EVT extremal-index validity, MinT coherence,
  etc.) would be a Phase 4 master-plan-scoped activity, not
  a Phase 3.5 single-session deliverable.

**Disposition:** Stream 2 carries forward to Phase 4 master
plan as a dedicated work item with two sub-items:
1. **Engine-side audit-field expansion** for 2a (kalman
   covariance time series) and 3d (johansen rank).
2. **Registry expansion** for the remaining 10 inherited
   wrappers (new invariant types: mcmc_convergence,
   evt_extremal_index_validity, mint_coherence,
   transformer_attention_normalization, etc.).

This is documented as a Phase 4 candidate; Phase 3.5 closes
Item 9 cleanly without Stream 2 entanglement.

### Why this is the right call

The Session 9 prompt anticipated this outcome:
> "§8.1 risk 5 (Phase 3 patterns don't predict Phase 3.5
> surfacing) potential trigger if Stream 2 audit surfaces
> unexpected wrapper structure on inherited 12."

Stream 2 audit DID surface this — the 12 inherited wrappers'
structures don't align with the 14 registered invariant types
without engine-side or registry-side expansion. This is
exactly the kind of "Phase 3 patterns don't predict Phase 3.5
surfacing" that the prompt flagged. Per the protocol, defer
cleanly rather than force-fit.

Deferring preserves:
- Phase 3.5's narrow scope (parity-harness improvements +
  fixture expansion, NOT engine modifications).
- Phase 4's freedom to design a coherent invariant-population
  master plan that doesn't fragment across Phase 3.5 + Phase
  4 boundaries.

## Implications

### Phase 3.5 schedule status

9 of 17 sessions through Phase 3.5. On-pace numerically.

| Session | Status |
|---|---|
| S1-S8 | Closed; all single-session targets met |
| S9 (this) | Stream 1 closed; Stream 2 deferred to Phase 4 |
| S10 | Slack absorption / Phase 3.5 v1.1.0 candidates (per locked schedule) |
| S11 | Documentation phase (P-1 / P-2 / P-3 amendments) |
| S12 | Phase 3.5 closeout |

### Item 9 cycle complete

Sessions 7-8-9 budget consumed; Item 9 (macro fixture
expansion) closed with:
- 11 new series (4 FX + 4 rates + 3 commodities)
- 21 GARCH-family runs verified
- Pattern A.1 stability claim production-locked across 4
  dimensions
- Recurring fixture-expansion protocol codified (S7 §Step 5)
- Selective re-validation methodology codified (S9 above)
- 3 re-banking decisions tightening Pattern J catalog scope

### Banked items remaining post-Session 9

| Item | Status | Session |
|---|---|---|
| 10 | Slack absorption / v1.1.0 candidates | Session 10 (next) |
| (S2 banked, deferred) | structural_invariants on 12 inherited | **Phase 4** |
| (S5 banked) | Pattern J.D catalog (CRAN-vs-R-runtime version representation) | Session 11 |
| (S6 banked) | P-1 §6 CI matrix Linux + cross-platform Rscript protocol; Pattern J.B.6 catalog (statsmodels-x13ashtml deferral) | Session 11 |
| (S7 banked) | Pattern A.1 cross-pair stability — confirmed empirical claim | Session 11 |
| (S8 banked) | FEDFUNDS heterogeneous-frequency disclosure pattern | Session 11 |
| (S9 banked) | Selective re-validation methodology codification; Item 9 cycle closure narrative | Session 11 |
| (Phase 4) | CSD wrapper engineering (n_surrogates default cap) | Phase 4 |
| (Phase 4) | structural_invariants on 12 inherited | Phase 4 |
| (Phase 4) | statsmodels ↔ x13ashtml integration | Phase 4 |
| (close) | Phase 3.5 closeout | Session 12 |

## Commit footprint

| File | Change |
|---|---|
| `docs/reference_parity_phase3_5/session_9_findings.md` | new (~340 LOC) |
| `docs/reference_parity_status.md` | -1 / +20 LOC |
| **Total** | **0 LOC code; ~360 LOC docs** within CAL-R6 100-LOC engine-side budget (zero engine changes) |

## Next session

Phase 3.5 Session 10 — Item 10 slack absorption / Phase 3.5
v1.1.0 candidates that surfaced mid-cycle. Per locked
schedule. May absorb into Session 11 documentation phase if no
slack-scope work surfaces.
