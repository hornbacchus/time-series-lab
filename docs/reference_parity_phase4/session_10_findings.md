# Phase 4 Session 10 — C-1 v2 doc bundle (BYF candidates #6, #7, #8)

**Date:** 2026-05-01
**Scope:** Per Phase 4 master plan §15 S10 — codify three
wrapper-structural patterns surfaced during BYF Sessions 2-3
as binding C-1 standards. Bumps C-1 to v2.0.0 (major version
bump for new top-level section group).
**Status:** COMPLETE.

## Why these three patterns now

Phase 4 is a closure cycle, not a discovery cycle. Each of
the three new C-1 sections corresponds to a BYF integration
finding that was banked at integration-time as a "C-1 v2
candidate" precisely because the failure class is structural
(not scoped to BYF) and warrants codification before the
next wrapper introduces the same hazard.

The three failure classes are uniformly:
- **Invisible to local-only verification.** Local installs
  and single-process testing succeed; the failure surfaces
  in long-lived `engine_worker` processes, in cross-platform
  CI, or in user-supplied workbook variants.
- **Diagnosable post-hoc but easy to misread at the time.**
  Each has a generic-sounding error symptom (`AttributeError`,
  sheet-not-found, second-call-failure) that masks the
  structural root cause.
- **Cheaply preventable at PR-time** with the right
  checklist item — but only if the standard codifies the
  pattern.

## Document amendments

### C-1 §6 (NEW top-level section): Wrapper Structural Patterns

Three subsections, all binding (B-tier):

| § | Title | Origin | LOC |
|---|---|---|---|
| 6.1 | Module-vs-package layout | BYF S2 | ~50 |
| 6.2 | Bundled-workbook input wrappers | BYF S3 | ~50 |
| 6.3 | Layered validation: request-local config copy | BYF S3 | ~55 |

Each subsection follows the same shape:
1. Origin reference (BYF session).
2. Failure-class statement (what goes wrong, why, when).
3. Required pattern (concrete rule, sometimes with code-
   shaped or topology-shaped requirements).
4. Retrospective (what happened in BYF, with file pointer
   to the integration-cycle findings doc for full
   diagnosis).

§6.3 ends with a cross-reference to P-1 §8.5 (install-matrix
gate) explicitly linking the two structural-discipline
sections (engine-side §6.3 layered validation + parity-side
§8.5 install matrix). Both protect against failure classes
invisible to local-only testing — that's the unifying theme
across both standards' Phase 4 amendments.

### C-1 §7-§8 renumbering

Old §6 References → new §7 References (added one more
reference: `bond_yield_forecast_integration/session_2_findings.md`
and `session_3_findings.md` as origin material for §6).

Old §7 Standard amendment process → new §8. Added formal
**version history** block:

- **v1.0.0** (2026-04-28, Session 29): post-CAI Phase 2
  cycle closure baseline.
- **v1.1.0** (2026-05-01, Phase 4 Session 1): added §4.6
  dependency-addition checklist (B-14 four-surface install
  matrix gate).
- **v2.0.0** (2026-05-01, Phase 4 Session 10): added §6
  Wrapper Structural Patterns (module-vs-package layout,
  bundled-workbook input, layered validation). Major
  version bump reflects new top-level section group.

The **major version bump** (v1.x → v2.0.0) is justified by
the addition of a new top-level section that introduces
binding (B-tier) requirements that PR authors must verify.
Per the standard's own amendment philosophy (§8 "Existing
wrappers that violate the standard are NOT automatically
grandfathered"), the bump is meaningful: any future PR
modifying an existing wrapper must now also conform to §6.
A minor-version bump (v1.2.0) would understate the
binding-surface change.

## v1.2.0 amendment ledger update

Per master plan §15.1, S10's amendments accumulate into the
P-1/P-2/P-3 v1.1.x → v1.2.0 issuance scheduled for S12.
After this session:

| Doc | Section | Source | LOC |
|---|---|---|---|
| C-1 | §6.1 (NEW) | S10 (this session, #6) | ~50 |
| C-1 | §6.2 (NEW) | S10 (this session, #7) | ~50 |
| C-1 | §6.3 (NEW) | S10 (this session, #8) | ~55 |
| C-1 | §7 (refs added) | S10 (this session) | ~3 |
| C-1 | §8 (version history) | S10 (this session) | ~15 |

S10 commits ~173 LOC to `wrapper_development_standard.md`
(556 → 709 line count delta = +153 LOC including blank-line
spacing; the +173 estimate above attributes lines per
subsection without the spacing overhead).

**Cumulative cycle ledger after S10:**

| Source | Doc | LOC |
|---|---|---|
| S1 | P-1 §8.5 | ~75 |
| S1 | C-1 §4.6 | ~50 |
| S4 | P-2 §C.3/§C.4 | ~40 |
| S5 | P-2 §C.2 | ~30 (banked for S12) |
| S6 | P-2 §C.2 + P-3 §3.4 | ~25 + ~40 |
| S10 | C-1 §6 (this session) | ~155 |
| **Total** | | **~415** |

Under the §11.11 trigger ceiling of 600 (P-1+P-2+P-3+P-4
combined; C-1 tracked separately as a different doc family).

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | n/a (no engine code touched) |
| Per-wrapper test suites unchanged | n/a (no wrappers touched) |
| `parity-fast` `--check-environment` clean | n/a (no MANIFEST.toml changes; doc-only session) |
| `parity-fast` tier outcome distribution unchanged | n/a (doc-only) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

Doc-only session; verification surface is the doc itself
plus post-push CI confirming no Markdown-side regressions
(none expected; no Markdown is parsed by CI).

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/wrapper_development_standard.md` | New §6 (3 subsections) + renumber §7-§8 + version history block | +153 |
| `docs/reference_parity_phase4/session_10_findings.md` | NEW (this file) | ~135 |
| **Total** | | **~288 LOC** |

## Disposition

| Item | Pre-S10 status | Post-S10 status |
|---|---|---|
| BYF candidate #6 (file/package collision protocol) | banked | **CLOSED** (C-1 v2.0.0 §6.1) |
| BYF candidate #7 (sheet-naming auto-detection pattern) | banked | **CLOSED** (C-1 v2.0.0 §6.2) |
| BYF candidate #8 (layered-validation pattern) | banked | **CLOSED** (C-1 v2.0.0 §6.3) |
| 13-item inheritance register | 5 open + 8 closed | 2 open + 11 closed |

The 2 remaining open items are:
- BYF candidate #4 (P-2 §B.6.4 bvars-availability trigger
  entry) — scheduled for S11.
- BYF candidate #5 (P-1 v1.2.0 docstring-convention
  amendment + engine backfill) — scheduled for S11.
- BYF candidate #9 (P-1 v1.2.0 §6.1 tier-classification
  clarification) — scheduled for S11.
- BYF Mod-2 O-1 (near-unit-root VAR companion margin
  observation) — scheduled for S11 (banking-only entry into
  P-3 §3.4).

(That is in fact 4 items, not 2 — the count above corrects
the cycle-closure register: 4 items remaining for S11
disposition + S12/S13 doc-set issuance closeouts. Inheritance
register tracking continues in S11 findings.)

## Banked observations

**B-Phase4-S10-1 — C-1 major version bump precedent.**
Phase 4 S10 is the first cycle session to issue a major
version bump on a non-parity-doc (C-1 v1.x → v2.0.0).
Major-version criteria for C-1 are now: **addition of a
new top-level section introducing binding (B-tier)
requirements**. Minor versions (v1.x): subsection
additions, checklist-item additions within an existing
section, or non-binding aspirational additions. Patch
versions: factual corrections, link fixes, formatting.
Bank for S12 P-1 issuance — P-1's own version-bump
criteria may want to mirror this precedent.

**B-Phase4-S10-2 — Section §6.3 cross-reference to P-1
§8.5.** §6.3's closing paragraph cross-references P-1 §8.5
(install-matrix gate) as a sister discipline. This is the
first explicit cross-document section-to-section linkage
between C-1 and P-1 outside §4.6 (which already links to
P-1 §8.5 via the original install-matrix amendment). The
two sections together codify the unifying theme "failure
classes invisible to local-only testing" — bank for P-1
v1.2.0 §pre-merge introduction or §1 framing material to
acknowledge the cross-doc theme explicitly.

## Next session

**S11 — Standalone doc patches + #5 docstring backfill +
O-1 banking.** Three items:
- #4 P-2 §B.6.4 bvars-availability trigger entry (~25 LOC).
- #5 P-1 §3.4 docstring-convention amendment (~40 LOC) +
  engine docstring backfill on ~10 wrappers (~140 LOC
  engine).
- #9 P-1 §6.1 tier-classification clarification (~20 LOC).
- O-1 banking: P-3 §3.4 NEW finding entry "near-unit-root
  VAR companion margin observation (BYF-Mod-2 34-mat;
  informational, not Pattern)" (~25 LOC).

S11 is the cycle's last engine-touch session before the
v1.2.0 doc-set issuance at S12 + cycle close at S13. Engine
docstring touches require running BYF and impacted
wrapper test suites for sanity; verification gates per §19
fully apply.
