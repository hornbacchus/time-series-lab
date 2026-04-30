# Phase 3.5 Session 11 — Amendment Plan (P-* v1.0.0 → v1.1.0)

**Source:** Phase 3.5 Sessions 1-9 banked items, consolidated
in Session 10 Stream 1 audit.
**Drafted:** Phase 3.5 Session 10 (this document is the
preparation-side artifact for Session 11 execution).
**Status:** READY FOR SESSION 11 EXECUTION.

This document maps every banked Phase 3.5 finding to the
target P-* v1.1.0 amendment (which document, which section).
It also flags items that depend on Session 10 Stream 2
preparation artifacts (those preparation artifacts live in
`session_10_findings.md` §Stream 2 prep).

## Consolidated banked-items inventory

10 banked items across Sessions 1-9 require P-* amendments at
Session 11. Phase 4 carry-forward items (3) listed but out
of Session 11 scope.

### Session 11 amendment targets (10 items)

| # | Source | Banked finding | Target document | Target section |
|---:|---|---|---|---|
| 1 | S1 | DOCUMENTED-DIVERGENCE wired end-to-end as runtime outcome (forward-provisioned, not triggered) | P-1 | §2.1 (verdict taxonomy — affirm production-locked status) |
| 2 | S2 | 12 pre-Phase-3 wrapper migration to P3ParityCheck contract; verdict_class mandatory on every check; 11-class taxonomy validated empirically | P-1 | §8.1 (required artifacts — affirm migration complete); §10 (empirical additions) |
| 3 | S3 | `single_impl_mle` production-locked (was candidate); p3_vecm migrated; 1 wrapper at 1e-5 abs / 1e-4 rel band; 13 orders headroom evidence | P-1 §5.1 (verdict_class taxonomy — mark single_impl_mle production-locked); P-2 §A.10 (single_impl_mle band documented + production-lock evidence cited) | (both) |
| 4 | S4 | em_stochastic per-metric bands schema extension; 2 wrappers (p3_hmm, p3_markov_switching) populated with per_metric blocks; granularity is metric-specific not wrapper-wide | P-1 §5.2 → §5.2.1 (NEW SUBSECTION: per-metric tolerance ladder schema); P-2 §A.6 (p3_hmm + p3_markov_switching per-metric tier docs); P-3 §3.3 (Pattern H per-metric finding) | (3 docs) |
| 5 | S5 | Manifest re-pin cadence + recurring quarterly protocol; 4 pin updates (PyWavelets minor; forecastHybrid minor; robustbase + dtw format-norms); selective re-validation methodology codified | P-1 §7.3 (quarterly re-pin window — formalize protocol); P-3 (no v1.1.0 entry needed; tools-level convention) | P-1 only |
| 6 | S6 | R bridge cross-platform Rscript resolution (`_resolve_rscript_exe()` 3-step fallback); Linux runner added to parity-slow.yml; X-13 PASS-on-Linux deferred to Phase 4 (statsmodels-x13ashtml integration) | P-1 §6 → §6.1 + §6.2 (Linux runner in CI matrix; cross-platform Rscript protocol); P-2 §B.6.3 (NEW: statsmodels-x13ashtml deferral as Pattern J.B catalog entry) | (2 docs) |
| 7 | S5+S7 | Pattern J catalog entry for CRAN-vs-R-runtime version representation (CRAN hyphen-suffix `0.99-7` vs R packageVersion() dot-format `0.99.7` — same version, different rendering) | P-2 §B.4 (NEW: §B.4.3 — CRAN-vs-R-runtime version representation) | P-2 only |
| 8 | S7+S9 | Pattern A.1 stability claim production-locked across 4 dimensions (implementation / version / cross-pair / cross-asset); 21 GARCH-family runs across 7 real-data series | P-3 §3.4 NEW (Pattern A.1 4-dimensions production-lock); P-1 §10.1 (cross-reference / strengthen claim) | P-3 + P-1 cross-ref |
| 9 | S8 | FEDFUNDS heterogeneous-frequency disclosure pattern; cross-construction (T10Y2Y) tools-level convention | (no P-* doc) — fixture-pool README convention | none |
| 10 | S7+S8+S9 | Macro fixture expansion 5 → 16 series; selective re-validation methodology; §4 Item 9 implicit-assumption mismatch documentation; 3 re-banking decisions tightening Pattern J catalog scope (CSD memory blow-up → Phase 4 not J.F; T10Y2Y → tools-level not J entry; GJR-vs-sGARCH → product backlog not P-3) | P-3 §X NEW SECTION (cross-pair empirical synthesis Sessions 7-9); P-3 §6 (mark Items #9, #10 closed); P-2 §B (Pattern J scoping rule) | P-3 (heaviest) + P-2 |

### Phase 4 carry-forward (NOT Session 11)

| # | Source | Item | Target |
|---:|---|---|---|
| P4-1 | S2/S9 | structural_invariants on 12 inherited (engine audit-field expansion + registry expansion) | Phase 4 master plan |
| P4-2 | S6 | statsmodels ↔ x13ashtml integration (TSL-side post-processor or pinned statsmodels patch) | Phase 4 master plan |
| P4-3 | S8 | CSD wrapper engineering (chunk surrogate dimension OR reduce default n_surrogates OR auto-cap per series length) | Phase 4 master plan |

---

## Per-document amendment plan

### P-4 status tracker (lightest)

**Effort:** ~30 LOC additions (timeline rows + Phase 3.5 cycle close summary + Phase 4 carry-forward).

| Section | Amendment |
|---|---|
| Header | Update version v1.0.0 → v1.1.0; update last-reviewed date |
| §Phase 3.5 candidates | Mark Items 1, 2, 3, 4, 5, 6, 7, 8, 9 closed with cross-reference to Session-N findings docs; add new §Phase 3.5 cycle close subsection |
| New §Phase 4 carry-forward | List 3 carry-forward items with rationale |
| Last-updated marker | Phase 3.5 closure entry |

**Drafting order:** START HERE — lightest amendment, sets the
narrative frame for the heavier P-1 / P-2 / P-3 work.

---

### P-1 parity standard (medium)

**Effort:** ~150 LOC additions across 5 sections.

| Section | Amendment | Source | LOC est |
|---|---|---|---:|
| Header | Version v1.0.0 → v1.1.0; revision history entry | meta | 5 |
| §2.1 (verdict taxonomy) | Affirm DOCUMENTED-DIVERGENCE production-lock; clarify "encountered as runtime outcome zero times in Phase 3 + Phase 3.5; remains forward-provisioned" | S1 | 10 |
| §5.1 (verdict_class taxonomy 11 classes) | Mark `single_impl_mle` as **production-locked** (was "candidate; Phase 3.5 banked"); add Phase 3.5 S3 evidence reference | S3 | 8 |
| §5.2 → NEW §5.2.1 (per-metric tolerance ladder schema) | NEW subsection: per-metric block schema (`per_metric` key in tolerance ladder); `_get_metric_tol()` helper; precedent on p3_hmm + p3_markov_switching; criterion for when to split into per-metric (≥1 order of separation between metrics within a wrapper) | S4 | 35 |
| §6 (CI tier classification) → §6.1 / §6.2 split | Restructure: §6.1 fast tier (Windows-only); §6.2 slow tier (Windows + Linux runners); document the slow-linux job's role; cross-platform Rscript resolution protocol (RSCRIPT_EXE env / manifest pin / shutil.which("Rscript") cascade) | S6 | 50 |
| §7.3 (quarterly re-pin window) | Formalize recurring quarterly protocol per Session 5: triggers (anchor / CI regression / contributor notice); expected output (drift report + dispositions + sentinel re-validation); escalation rules (Pattern H DSCD widening proceeds; TSL-side bug holds pin → Session N.5 wrapper-fix continuation) | S5 | 30 |
| §8.1 (required artifacts) | Affirm migration complete (Session 2 closure); 11-class taxonomy validated empirically | S2 | 5 |
| §10 (empirical additions) | Cross-reference §10.1 (Pattern A.1) to P-3 §3.4 NEW (production-lock evidence) | S7+S9 | 5 |
| §12 change log | v1.1.0 entry | meta | 5 |

**Cross-references TO P-2:** §5.1 → P-2 §A.10; §5.2.1 → P-2 §A.6.
**Cross-references TO P-3:** §10.1 → P-3 §3.4 NEW.

---

### P-2 parity diagnostic reference (medium-heavy)

**Effort:** ~180 LOC additions across 4 sections.

| Section | Amendment | Source | LOC est |
|---|---|---|---:|
| Header | Version v1.0.0 → v1.1.0; revision history entry | meta | 5 |
| §A.6 (em_stochastic) | Document per-metric tier split for p3_hmm + p3_markov_switching; per-metric bands table; cite empirical headroom evidence per metric; cross-reference to P-1 §5.2.1 | S4 | 50 |
| §A.10 (single_impl_mle — was "candidate; not yet locked") | Replace candidate-status text with **production-locked** at Phase 3.5 Session 3; documented band 1e-5 abs / 1e-4 rel; production-lock evidence (p3_vecm 9.99e-16 abs achieved; 13 orders inside old `mle_fit` band; 9 orders preserved inside new band); cross-reference to P-1 §5.1 | S3 | 25 |
| §B.4 → NEW §B.4.3 (CRAN-vs-R-runtime version representation) | NEW Pattern J.B entry: CRAN release format `0.99-7` (hyphen) vs R `packageVersion()` rendering `0.99.7` (dot); same version, different string representation; pin format normalization convention (use dot-format to match `--check-environment` output); precedent from S5 manifest re-pin | S5 | 30 |
| §B.6 → NEW §B.6.3 (statsmodels ↔ x13ashtml integration) | NEW Pattern J.B entry: statsmodels' `x13_arima_analysis` expects classic `x13as` binary's output convention (.err / .lkr / .txt at temp prefix); x13binary R package ships `x13ashtml` (HTML-aware build) with different output naming; integration deferred to Phase 4; SKIP-graceful preserved on both Windows + Linux; x13binary install + symlink scaffolding preserved in workflow for forward use | S6 | 40 |
| §B (Pattern J catalog scoping rule — NEW HEADER NOTE) | NEW prefix to §B explaining Pattern J's scoping rule per S9 re-banking decisions: J catalog is for **reference-library quirks** (behaviors of the reference that the TSL parity harness must accommodate); NOT TSL wrapper defects (→ Phase 4 wrapper-engineering candidates); NOT fixture conventions (→ tools-level docs); NOT applied empirical findings (→ product backlogs) | S9 | 25 |
| §A → §A.1-A.11 review pass | Sweep for any v1.0.0 references to "candidate / not locked" status that S3 invalidates | S3 | 5 |

**Cross-references TO P-1:** §A.6 → P-1 §5.2.1; §A.10 → P-1 §5.1.
**Cross-references TO P-3:** §B → P-3 §6.1 (Item #9 closure cross-link).

---

### P-3 parity empirical findings (heaviest)

**Effort:** ~250 LOC additions across 4 sections (includes
NEW §3.4 + heavy §6 update).

| Section | Amendment | Source | LOC est |
|---|---|---|---:|
| Header | Version v1.0.0 → v1.1.0; revision history entry | meta | 5 |
| §2 (what made Phase 3 work) | Add §2.4 NEW: "Master plan §4 Item 9 implicit-assumption mismatch — methodology evolution" — two-paragraph narrative explaining that parity harness uses synthetic DGP fixtures by design, NOT macro fixtures; macro fixture expansion correctly served wrapper-level re-validation, not parity-harness CI runtime; codifies the methodology distinction for future Phase work | S9 | 40 |
| §3 → §3.4 NEW (Pattern A.1 4-dimensions production-lock) | NEW subsection: Pattern A.1 stability claim now confirmed across 4 dimensions (implementation / version / cross-pair / cross-asset); aggregate quantitative evidence table (Phase 3 18 same-library wrappers + Phase 3.5 21 GARCH-family runs across 7 real-data series); citation chain to S7 + S8 + S9 findings docs; cross-reference to P-1 §10.1 | S7+S9 | 60 |
| §3 → §3.3 (DSCD) update | Pattern H per-metric finding: DSCD is metric-specific within em_stochastic (transition_matrix wide; emission_means / log_likelihood tight); split exposes per-component agreement at machine precision that single-band ladder concealed | S4 | 25 |
| §6 (Phase 3.5 candidates banked) | Restructure: mark Items #9 (single_impl_mle band tightening), #10 (per-metric bands), #6+7 (cross-batch findings doc), §6.5 (manifest re-pin cadence), §6.6 (DOCUMENTED-DIVERGENCE) as **CLOSED in Phase 3.5**; add §6.7 NEW (Pattern J.B.6 statsmodels-x13ashtml deferral); add §6.8 NEW (CSD wrapper engineering — Phase 4); add Phase 4 carry-forward subsection listing 3 items | S1+S3+S4+S5+S6+S8 | 80 |
| §7 (audit-engineering takeaways) → §7.4 NEW | Cross-pair empirical synthesis methodology codification: selective re-validation per-asset-class (NOT full sweep); in-process RunContext invocation outside parity harness; verdict criterion = `status="success"` + numerical sanity (GJR ≥ sGARCH, AIC ranking); failure classification (acquisition / wrapper engineering / data quality) | S7+S8+S9 | 40 |
| §9 change log | v1.1.0 entry | meta | 5 |

**Cross-references TO P-1:** §3.4 NEW → P-1 §10.1; §6 → P-1 §5.1, §5.2.1, §6.2, §7.3.
**Cross-references TO P-2:** §3.3 → P-2 §A.6; §6.7 → P-2 §B.6.3.

---

## Recommended drafting order within Session 11

Optimize for cross-reference resolution: amend the document
that will be referenced FIRST, then the documents referencing
it. This avoids back-references to unfinished sections.

1. **P-4 (status tracker)** — lightest; closes the narrative
   frame.
2. **P-1 §5.1** (`single_impl_mle` production-lock) — short
   amendment that P-2 §A.10 will reference.
3. **P-2 §A.10** (single_impl_mle band documentation) — pulls
   from P-1 §5.1.
4. **P-1 §5.2.1 NEW** (per-metric ladder schema) — short
   schema doc that P-2 §A.6 will reference.
5. **P-2 §A.6** (em_stochastic per-metric tier split) — pulls
   from P-1 §5.2.1.
6. **P-1 §6** (CI tier — Linux runner addition) — heaviest P-1
   amendment; pulls from S6 prep artifacts.
7. **P-1 §7.3** (manifest re-pin protocol).
8. **P-2 §B.4.3 NEW** (CRAN-vs-R-runtime version representation).
9. **P-2 §B.6.3 NEW** (statsmodels-x13ashtml deferral).
10. **P-2 §B header note** (Pattern J scoping rule — must come
    AFTER B.4.3 + B.6.3 are added so the rule's framing has
    concrete examples to reference).
11. **P-3 §3.3** (DSCD Pattern H per-metric).
12. **P-3 §3.4 NEW** (Pattern A.1 4-dimensions production-lock)
    — uses Stream 2 prep aggregate table.
13. **P-3 §2.4 NEW** (master plan §4 Item 9 mismatch narrative)
    — uses Stream 2 prep narrative draft.
14. **P-3 §6** (Phase 3.5 candidates closure + Phase 4 carry-
    forward) — references §3.3, §3.4 just added.
15. **P-3 §7.4 NEW** (cross-pair empirical synthesis
    methodology).
16. **P-1 §8.1** (migration complete).
17. **P-1 §10** (Pattern A.1 cross-ref strengthening).
18. **P-1 §2.1** (DOCUMENTED-DIVERGENCE production-lock affirm).
19. **All change logs** (P-1 §12, P-2 header, P-3 §9) — last
    sweep so log entries reflect actual diffs.

## Single-session feasibility for Session 11

Total estimated LOC: **~610 LOC additions across 4 documents**.

| Document | Estimated LOC | Sections |
|---|---:|---:|
| P-4 | 30 | 1 |
| P-1 | 150 | 9 |
| P-2 | 180 | 6 |
| P-3 | 250 | 6 |
| **Total** | **610** | **22 amendment sites** |

Comparable to Phase 3 Session 16 (P-2 v1.0.0 issuance, ~700 LOC
single session) and Phase 3 Session 17 (P-3 v1.0.0 issuance,
~600 LOC single session). **Single-session feasible.**

If Session 11 surfaces unexpected cross-document dependencies
(e.g., a P-1 amendment requires re-structuring P-2 §A entirely),
**Session 11.5 continuation is reserved** per Phase 3
documentation phase precedent. No structural changes to v1.0.0
section organization are anticipated based on this Session 10
audit; all amendments are subsection additions or in-place
updates.

## Items requiring Session 10 Stream 2 preparation artifacts

The following amendments depend on prep artifacts produced in
Session 10 Stream 2 (see `session_10_findings.md` §Stream 2):

| Amendment | Prep artifact required |
|---|---|
| P-1 §6.2 cross-platform Rscript protocol | Stream 2 §10-S2.C: protocol description in formal form (extracted from `_resolve_rscript_exe()` 3-step fallback) |
| P-2 §B.4.3 CRAN-vs-R-runtime version | Stream 2 §10-S2.A.1: concrete code snippet from `MANIFEST.toml` with example dot/hyphen normalization |
| P-2 §B.6.3 statsmodels-x13ashtml | Stream 2 §10-S2.A.2: concrete error trace + workaround scaffolding from `parity-slow.yml` |
| P-1 §5.2.1 per-metric ladder schema | Stream 2 §10-S2.B: formal schema description (extracted from `tolerances.py` p3_hmm + p3_markov_switching examples) |
| P-3 §3.4 Pattern A.1 4-dimensions | Stream 2 §10-S2.D: aggregate quantitative summary table |
| P-3 §2.4 master plan §4 Item 9 mismatch | Stream 2 §10-S2.E: two-paragraph narrative draft |

Session 11 should reference `session_10_findings.md` directly
when drafting these amendments rather than re-deriving from
session-N findings docs.

## Out of scope for Session 11

Per Session 10 prompt:
- Phase 4 master plan drafting — Session 12 closeout decision.
- Phase 4 candidate sub-items (structural_invariants, CSD
  engineering, statsmodels-x13ashtml integration) — Phase 4.

## Open questions for Session 11

None at Session 10 close. All 10 amendment items have clear
target documents + sections + prep artifacts. Session 11
executes from this plan without re-design.
