# Phase 4 Session 11b-3 — CI step + pre-commit hook installer (closes B-Phase4-S5-4)

**Date:** 2026-05-03
**Scope:** Third of three sub-sessions in S11b three-way
split. Lands the operational-enforcement infrastructure
that completes the §8.5 install-matrix gate from prose-only
discipline to belt-and-suspenders gate (CI step ≡ post-PR-
open gate; pre-commit hook ≡ local gate). Closes B-Phase4-
S5-4 in full and ends the S11b sub-session series.
**Status:** COMPLETE.

## Why this is the third sub-session

S11b's three-way split per Option B disposition. S11b-1
(re-commit `715e06a`) landed the validation script alone
(193 LOC). S11b-2 (commit `712397f`) landed tests +
parity-slow.yml dtw fix (212 LOC). S11b-3 (this) lands the
CI step + pre-commit hook installer + hook script (~121
LOC).

Sequence-ordering constraint per B-Phase4-S11b-1-2:
S11b-2's dtw fix landed on master at commit `712397f` BEFORE
S11b-3's CI step lands. The new CI step validates `MANIFEST
→ parity-slow.yml`; without dtw in slow-tier, CI would have
gone red on first run. Constraint satisfied.

## What changed

### `.github/workflows/parity-fast.yml` — CI step add (+11 LOC)

New CI step inserted between "Set up Python" and "Install
Python deps":

```yaml
- name: Validate install-matrix consistency (P-1 §8.5)
  # Phase 4 Session 11b: operational enforcement of P-1 §8.5
  # install-matrix gate. Belt-and-suspenders pattern — local
  # pre-commit hook catches gaps before commit; this CI step
  # catches gaps if the local hook missed (or wasn't
  # installed). Runs BEFORE pip install so a missing entry
  # fails fast without the slow-but-doomed install attempt.
  # See B-Phase4-S5-4 banked observation; S5 self-validating-
  # irony case study (P-1 §13.5.4).
  run: python tools/validate_install_matrix.py
```

Position rationale: runs BEFORE pip install (currently the
first heavy step). A missing-entry CI failure halts the
build before the slow-but-doomed Python install attempt;
operator gets a clear gap message immediately rather than
buried under install logs.

Linux-runner cross-platform consideration: `parity-fast.yml`
runs on `windows-latest` (per current workflow config).
The validation script is pure Python (uses `tomllib` from
stdlib) and produces identical exit codes / output across
Windows + Linux. No cross-platform concern.

### `tools/install_hooks.ps1` — installer NEW (+67 LOC)

PowerShell installer (Windows-primary per repo conventions).
Action: copies `tools/git_hooks/pre-commit` to
`.git/hooks/pre-commit`. Per S11b-3 trigger requirement,
includes:

- **Existence check.** If `.git/hooks/pre-commit` already
  exists, the installer:
  - Compares content; if identical, prints
    "Skipped (already up-to-date)" and continues.
  - If different, prints a warning naming the file +
    explicit instruction for manual overwrite (`rm` then
    re-run installer); does NOT silently overwrite.
- **Linux/macOS contributor instruction.** Trailing print
  documents the equivalent install pattern: `cp
  tools/git_hooks/pre-commit .git/hooks/pre-commit; chmod
  +x .git/hooks/pre-commit`.
- **Operational verification recipe.** Closing block
  prints how to verify operationally: stage a MANIFEST
  change, attempt commit, observe hook refusal.
- **Idempotent.** Re-running on identical state is a no-op
  (skip-as-up-to-date branch).

Net LOC count is 67 (vs original ~41 in S11b prep) due to
the warn-if-exists logic per trigger requirement; this is
trigger-mandated content, not scope creep.

### `tools/git_hooks/pre-commit` — hook script NEW (+43 LOC)

Bash-style script with shebang line (works under Git's hook
execution on both Windows-Git-Bash and Linux/macOS bash).

**Trigger condition:** detects when any of the following
files appear in staged changes:
- `tools/reference_parity/harness/MANIFEST.toml`
- `.github/workflows/parity-fast.yml`
- `.github/workflows/parity-slow.yml`

Hook exits early with code 0 if no trigger file changed
(most commits skip this check entirely; <100ms overhead
when triggered).

**Validation invocation:** runs
`python tools/validate_install_matrix.py`. On script exit
non-zero, hook propagates non-zero exit; commit blocked
with the script's clear error message identifying which
surface needs updating. On script exit zero, hook completes
silently and commit proceeds.

**Cross-platform Python resolution:** prefers
`C:/Python314/python.exe` (TSL convention); falls back to
`python3` or `python` on PATH for Linux/macOS contributors.

## Verification — synthetic gap test (per trigger)

Per S11b-3 trigger explicit requirement: "verify the CI
step + hook operationally enforce, not just exist".

### Validation script synthetic gap test

Procedure:
1. Backup `MANIFEST.toml` to `/tmp/MANIFEST.toml.backup`.
2. Inject `synthetic_test_pkg = "99.0.0"` into
   `[python.packages]` table via Python script (proper
   TOML insertion within the table, NOT file-end append
   which lands under a different table).
3. Run `python tools/validate_install_matrix.py`.
4. Restore MANIFEST.toml from backup.
5. Re-run validation script.

Result:
```
=== synthetic gap exit code: 1 (expect 1) ===
=== restored exit code: 0 (expect 0) ===
```

Validation script correctly:
- Detects the synthetic gap (exits 1)
- Names the missing package in the error message
  ("Python package 'synthetic_test_pkg' in MANIFEST.toml
  but missing from parity-slow.yml (Python install)")
- Returns to clean state on restore (exits 0)

### Pre-commit hook synthetic gap test

Procedure:
1. Inject synthetic gap as above.
2. `git add tools/reference_parity/harness/MANIFEST.toml`.
3. Run `bash tools/git_hooks/pre-commit` directly
   (simulates Git's hook execution).

Result:
```
pre-commit: validating P-1 §8.5 install-matrix consistency...
ERROR: install-matrix gaps detected (P-1 §8.5):
  Python package 'synthetic_test_pkg' in MANIFEST.toml
  but missing from parity-slow.yml (Python install)
=== Hook exit code: 1 (expect 1) ===
```

Pre-commit hook correctly:
- Triggers on staged MANIFEST.toml change
- Invokes validation script
- Propagates the script's exit code 1
- Would block the commit (Git aborts on non-zero hook exit)

Both validation script + pre-commit hook are operationally
functional, not just structurally present. **B-Phase4-S5-4
operational enforcement is now belt-and-suspenders complete.**

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| **S11b-3 actual** | **+121 net LOC** (workflow +11; installer +67; hook +43) |
| Position vs default | UNDER by 79 LOC (~40% headroom) |
| §13.4 marginal-overshoot tolerance band | 5-10% (200-220 LOC) |
| Position vs marginal band | well under; band not engaged |

Clean commit. The +26 LOC overshoot vs trigger projection
(~95) reflects the warn-if-exists logic added to
`install_hooks.ps1` per trigger explicit requirement
("warn if .git/hooks/pre-commit already exists; do not
silently overwrite"). Trigger-mandated content; not scope
creep.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 33.03s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| Validation script unit tests | ✅ 10/10 PASS |
| Validation script live state | ✅ exit 0 |
| Synthetic gap test (script) | ✅ PASS — detects gap + restores clean |
| Synthetic gap test (hook) | ✅ PASS — triggers on staged MANIFEST + propagates exit |
| New CI step runs cleanly on parity-fast.yml | pending CI verification post-push |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S11b-3 contributes operational tooling (CI step + hook
infrastructure), NOT v1.2.0 doc-set content.

**Cumulative ledger after S11b-3 (unchanged for doc-set):**

| Doc | LOC accumulator |
|---|---|
| P-1 | ~490 |
| P-2 | ~261 |
| P-3 | ~245 |
| C-1 | ~205 |
| **Total** | **~1201 LOC** (S12a/S12b split confirmed) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `.github/workflows/parity-fast.yml` | New CI step | +11 |
| `tools/install_hooks.ps1` | NEW (PowerShell installer) | +67 |
| `tools/git_hooks/pre-commit` | NEW (hook script) | +43 |
| `docs/reference_parity_phase4/session_11b_3_findings.md` | NEW (this file) | ~165 |
| **Total (commit-counted; excludes findings doc)** | | **+121 LOC** |

## Disposition

| Item | Pre-S11b-3 status | Post-S11b-3 status |
|---|---|---|
| B-Phase4-S5-4 (install-matrix operational enforcement) | PARTIAL (script + tests + dtw fix CLOSED at S11b-1/S11b-2) | **CLOSED** — CI step + pre-commit hook installer + hook script all live; synthetic gap test verified; belt-and-suspenders complete |
| 13-item inheritance register | 1 open + 12 closed | **1 open + 12 closed** (B-Phase4-S5-4 is operational item, NOT in original 13; BYF #5 still open for S11c) |
| S11b sub-session series | partial: 2 of 3 sub-sessions (S11b-1 + S11b-2) | **CLOSED** — all 3 sub-sessions complete |
| Phase 4 cycle progress | 11 of 13 sessions (85%) | **12 of 13 sessions (92%)** — S11 fully closed (S11a + S11b complete); only S11c (BYF #5) + S12 (v1.2.0 doc-set) + S13 (cycle close) remain |

## S11 closure (full session topology)

S11 was pre-split per Decision 14 into S11a (doc patches),
S11b (operational enforcement; this sub-series), S11c
(engine docstring backfill). S11a + S11b are now both
CLOSED:

| Sub-series | Sub-sessions | Total LOC | Commits |
|---|---|---|---|
| S11a | 4 (S11a-1 + S11a-2-1 + S11a-2-2 + S11a-3) | +645 | 4 |
| S11b | 3 (S11b-1 re-commit + S11b-2 + S11b-3) + 1 revert | +526 | 4 (incl. revert) |
| **S11 total (S11a + S11b)** | **7 sub-sessions + 1 revert** | **+1171** | **8 commits** |

Outstanding for Phase 4 closure:
- S11c (BYF #5: P-1 §3.4 docstring convention + ~10-wrapper engine docstring backfill) — last engine-touch session
- S12 (v1.2.0 doc-set issuance: P-1, P-2, P-3) — S12a/S12b split confirmed per §11.11
- S13 (P-4 v1.2.0 + cycle close)

## Banked observations from S11b-3

**B-Phase4-S11b-3-1 — Synthetic gap test as standard
verification step for operational-enforcement infrastructure.**
S11b-3's CI step + pre-commit hook were verified operationally
by injecting a synthetic gap, confirming both the script
and hook detect it, then restoring. This pattern should be
the standard for any future operational-enforcement
infrastructure session. Bank as institutional precedent for
Phase 4.5+ runner-integration sessions and for any session
codifying a new gate-script.

**B-Phase4-S11b-3-2 — Belt-and-suspenders empirically
validated.** The S5 self-validating-irony case study (P-1
§13.5.4) banked B-Phase4-S5-4 explicitly because prose
discipline alone was insufficient (S5 missed §8.5 within
the same cycle that S1 codified it). S11b-3 closes the loop:
prose-only §8.5 → script + tests + CI + hook all live. The
discipline now has both:
  - Belt: pre-commit hook (catches local commit; <100ms overhead)
  - Suspenders: parity-fast.yml CI step (catches PR open even
    if local hook not installed)

Future sessions adding new dependencies will be operationally
gated, not just prose-disciplined. Bank as institutional
precedent for any future P-1 / C-1 standard codification:
operational enforcement should accompany the prose discipline
when feasible; B-Phase4-S5-4 model is reusable.

## Next session

**S11c — BYF #5 P-1 §3.4 docstring convention + engine
docstring backfill.**

Per Phase 4 master plan §15 S11c: codify a docstring
convention in P-1 §3.4 + apply it to ~10 engine wrappers
(BYF dispatch + related techniques). Last engine-touch
session before v1.2.0 doc-set issuance at S12.

Trigger: ready to fire after S11b-3 CI confirms green.
