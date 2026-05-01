# Phase 4 Session 1 — Pre-merge install-matrix gate (BYF candidate #10)

**Date:** 2026-05-01
**Scope:** Per Phase 4 master plan §15 S1 — codify the install-matrix
discipline that surfaced as a recurring failure class across two
prior cycles. Adds P-1 §8.5 (parity-dimension checklist item) and
C-1 §4.6 (engine-dimension companion checklist item).
**Status:** COMPLETE.

## Why this is the first session of Phase 4

S1 is front-loaded because every subsequent engine session in the
cycle (S2 P4-2 statsmodels-x13ashtml, S3 P4-3 CSD memory cap, S7-S9
P4-1 structural_invariants population, S11 #5 docstring backfill)
introduces new code that risks the same failure pattern unless the
gate exists. Codifying the discipline at session 1 makes it
binding for all subsequent Phase 4 work and for any post-Phase-4
wrapper additions.

## Failure class codified

A wrapper-addition PR introduces a new runtime dependency. The
dependency is added to **some** install surfaces but not **all**
of the CI-relevant surfaces. The omission is invisible to
local-only verification (every local install path resolves the
dependency from site-packages regardless of which TSL surface
declares it), but lands as red CI on the next workflow run that
triggers the missing-dependency import path.

Two prior instances of this exact failure class:

| Instance | Cycle | Symptom | Resolution |
|---|---|---|---|
| `x13binary` | Phase 3.5 Session 6 | Linux nightly `parity-slow.yml` red on first scheduled run after merge — Linux job missing the `x13binary` install entry | Linux job install-line amendment (`parity-slow.yml`); commit cited in `docs/reference_parity_phase3_5/session_6_findings.md` |
| `openpyxl` | BYF S4 → S5 | Fast-tier CI run 25213149549 exit 3 ERROR on commit `4983522` — `parity-fast.yml` Windows job missing `openpyxl` install (BYF dispatch's pre-flight workbook validator imports openpyxl) | Install-matrix amendment + `numba pyyaml openpyxl` added to all four surfaces in commit `38a5144`; documented in `docs/bond_yield_forecast_integration/session_5_findings.md` |

Two distinct failures, two distinct surfaces (Linux slow-tier vs
Windows fast-tier), but the same root cause: an install-line
omission on at least one of the four CI-relevant surfaces.

## The four surfaces

The new gate lists **all four** surfaces explicitly:

1. **`engine/requirements.txt`** — engine-side runtime install
   (used by `engine_worker` and any local `pip install -r`).
2. **`tools/reference_parity/harness/MANIFEST.toml`** —
   parity-harness pinned versions (used by
   `--check-environment`; loaded via `harness/manifest.py`).
3. **`.github/workflows/parity-fast.yml`** — fast-tier CI install
   line (Windows job; runs on every PR + push to master).
4. **`.github/workflows/parity-slow.yml`** — slow-tier CI install
   line; **both** the Windows job AND the Linux job must be
   updated.

The four-surface check is the minimum sufficient gate to catch
the entire failure class. Three-surface checks were insufficient
in both prior instances (Phase 3.5 S6 omitted Linux job alone;
BYF S4 omitted Windows fast-tier alone).

## Document amendments

### P-1 §8.5 (NEW)

Located at `docs/engineering/parity_standard.md` between §8.4
(Required cross-references) and §9 (Cross-Reference to Wrapper
Development Standard). The new section:

- States the failure class with both retrospective citations.
- Lists the four surfaces with their distinct purposes.
- Articulates rationale ("any single missed surface produces
  an asymmetric failure that slips through local testing but
  lands red in CI").
- Cross-references C-1 §4.6 as the engine-dimension companion.

~75 LOC.

### C-1 §4.6 (NEW)

Located at `docs/engineering/wrapper_development_standard.md`
between §4.5 (Aspirational) and §5 (Canonical Test Suite
Requirement). The new section:

- New checklist item **B-14** mandating the four-surface
  verification.
- Cites the same two retrospective instances.
- Cross-references P-1 §8.5 as the parity-dimension companion.
- "Both must hold for any wrapper PR introducing a new
  dependency."

~50 LOC.

## v1.2.0 amendment ledger update

Per master plan §15.1, S1's amendments accumulate into the
P-1 v1.1.x → v1.2.0 issuance scheduled for S12. After this
session:

| Doc | Section | Source | LOC |
|---|---|---|---|
| P-1 | §8.5 (NEW) | S1 (this session) | ~75 |
| C-1 | §4.6 (NEW) | S1 (this session) | ~50 |

Total accumulated amendment LOC at S1 close: **~125**. Under
the §11.11 trigger ceiling of 600.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | (no engine-code touches; pytest unaffected; verifying as final pre-commit check) |
| Per-wrapper test suites unchanged (no wrappers touched) | (n/a; doc-only session) |
| `parity-fast` `--check-environment` clean | (no MANIFEST.toml changes; environment stable) |
| `parity-fast` tier outcome distribution unchanged | (n/a; doc-only session) |
| Numerical-array byte-identical equivalence | (n/a; no engine code touched) |
| CI green on `parity-fast.yml` post-push | pending |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `docs/engineering/parity_standard.md` | New §8.5 between §8.4 and §9 | +75 |
| `docs/engineering/wrapper_development_standard.md` | New §4.6 between §4.5 and §5 | +50 |
| `plans/reference_parity_phase4_master_plan.md` | NEW (Phase 4 master plan canonical project-repo file) | ~440 |
| `docs/reference_parity_phase4/session_1_findings.md` | NEW (this file) | ~120 |
| **Total** | | **~685 LOC** |

The plan file LOC dominates the topology because S1 is also the
implicit "cycle setup" session that materializes the canonical
plan file from the plan-mode draft (per the post-plan-mode
handoff). Per Phase 3.5 / BYF cycle precedent, plan files are
not subject to the per-session CAL-R6 LOC budget; the codified
amendments themselves are well within the routine doc-only
budget (~125 LOC for the two checklist additions).

## Disposition

| Item | Pre-S1 status | Post-S1 status |
|---|---|---|
| BYF candidate #10 (P-1 §pre-merge install-matrix gate) | banked | **CLOSED** (lands at v1.2.0 issuance per S12) |
| 13-item inheritance register | 13 open | 12 open + 1 closed |

## Next session

**S2 — P4-2 pathway (c) bypass statsmodels.x13_arima_analysis.**
Direct `x13ashtml` invocation from
`engine/techniques/x13_seasonal_adjust.py`; TSL-side parser for
x13ashtml output. Expected ~150-250 LOC. Linux runner now PASSes
`p3_x13` (was SKIP-graceful). §11.13 spill protocol applies if
S2 commits exceed 200 LOC.
