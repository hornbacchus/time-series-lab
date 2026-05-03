# Phase 4 Session 11b-1 (re-commit) — `tools/validate_install_matrix.py` (Option B split, 1 of 3)

**Date:** 2026-05-03
**Scope:** First of three sub-sessions in S11b three-way
split. Lands tightened `tools/validate_install_matrix.py`
validation script. Re-commit per Path B disposition after
the original S11b-1 commit (28f6983) was reverted for
substantive scope spill misclassified as documentation-
density measurement-variance.
**Status:** COMPLETE.

## Why this is a re-commit (Path B disposition)

The original S11b-1 commit (28f6983) landed `validate_install_matrix.py`
at +274 LOC — 37% over the §13.1 default 200 LOC budget,
well outside the §13.4 codified 5-10% marginal-tolerance band
(200-220 LOC). The commit's findings doc self-classified the
overshoot as "documentation-density measurement-variance" and
banked B-Phase4-S11b-1-1 as a candidate amendment introducing
a "tooling-script ceiling" analogous to §13.3 test-LOC ceiling.

**That classification did not survive scrutiny.** §13.4
marginal-tolerance covers measurement variance (Markdown
formatting LOC noise; edit-vs-replace LOC accounting), not
content-density variance. The ~120 LOC of inline rationale in
the original commit was content the script could exist
without — that's substantive scope, not measurement variance.
The right disposition was to split per §13.2 / §13.4 OR to
tighten the content; the commit landed before this was caught.

User Path B disposition (verbatim):

> "The §13.4 marginal-tolerance band covers measurement
> variance (Markdown formatting LOC noise; edit-vs-replace
> LOC accounting), not content-density variance. ~120 LOC
> of inline rationale is content the script could exist
> without; that's not measurement variance, it's substantive
> scope. The right disposition was to split per §13.2 /
> §13.4, but the commit landed before this was caught."

> "Decline §13.6 tooling-script-density amendment as
> institutional precedent. The discipline as codified is
> correct; the original S11b-1 commit was the violation.
> Goalpost-moving codification to legitimize a violated
> commit is the failure mode §13.4 marginal-tolerance was
> specifically not designed to enable."

## Path B execution

| Step | Action | Result |
|---|---|---|
| 1 | `git revert 28f6983 --no-edit` | Revert commit `3b04bf9` created; -548 LOC (script + original findings doc removed) |
| 2 | Reformat `tools/validate_install_matrix.py` | Module docstring covering Rule 1 + Rule 2 + NOT-enforced caveat + belt-and-suspenders pattern reference (~38 LOC); per-function docstrings tightened to 1-2 lines; inline comments minimized; ~120 LOC of inline rationale removed |
| 3 | Verify script still passes | 193 LOC; live state check exit 0; unit tests 10/10 PASS |
| 4 | Re-commit as S11b-1 | This commit (193 LOC; under 200 default) |

**Net result:** S11b-1's logical scope is preserved (validation
script with two enforcement rules + parsing helpers); LOC
reduced from 274 to 193 (-81 LOC, 30% reduction). The removed
content was operational-rationale documentation that belongs
in this findings doc / P-1 §13.5.4 cross-references rather
than inline in the script source.

## What changed (re-commit content)

### `tools/validate_install_matrix.py` NEW (+193 LOC)

Validation script enforcing P-1 §8.5 install-matrix gate.

#### Module-docstring contract (~38 LOC)

Documents the two enforcement rules + NOT-enforced caveat +
Linux-only allowlist semantics + belt-and-suspenders pattern
reference. The rationale density is appropriate at the script
header (where future cycle authors look first); detailed
case study material lives in P-1 §13.5.4 + this findings doc.

#### Code logic (~155 LOC)

| Function | LOC | Purpose |
|---|---|---|
| `parse_manifest()` | ~6 | Read MANIFEST.toml; return (python_pkgs, r_pkgs) |
| `_normalize()` | ~8 | Lowercase + strip pip-version-pin + quotes |
| `parse_pip_install_lines()` | ~10 | Extract Python packages from canonical `python -m pip install` form |
| `parse_r_install_packages()` | ~16 | Extract R packages from `install.packages(c(...))` blocks |
| `_parse_slow_tier_jobs()` | ~10 | Split slow-tier YAML into Windows + Linux jobs |
| `_check_manifest_in_surface()` | ~7 | Rule 1 enforcement |
| `_check_fast_subset_of_slow()` | ~8 | Rule 2 enforcement |
| `main()` | ~50 | Orchestrate parse + checks; print violations; exit 0/1 |

Each function has a 1-2 line docstring (essential contract
only). Detailed rationale (e.g., why fast-tier is intentionally
a subset; why x13binary is in install but not MANIFEST) lives
in the module-level docstring + this findings doc + P-1
§13.5.4 cross-references.

#### Live state validation surface

Running the script against current MANIFEST.toml + workflow
files (with the dtw fix landing at S11b-2 in the working
tree) returns exit code 0:

```
MANIFEST.toml: 23 Python packages, 21 R packages
OK — install matrix consistent: MANIFEST coverage in
slow-tier (Win+Linux); fast-tier subset of slow-tier.
```

Pre-S11b state (before the dtw fix landing at S11b-2): the
script flagged a real gap — R `dtw` package pinned in
MANIFEST.toml (Phase 3 Session 14 Batch 10) but missing from
both slow-tier R install lines. Documented as a §8.5
application case study in S11b-2 findings doc.

## §13.4 spill compliance — clean

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| §13.4 marginal-overshoot tolerance band | 5-10% (200-220 LOC) |
| **S11b-1 actual (re-commit)** | **+193 net LOC** on `tools/validate_install_matrix.py` |
| Position vs default | UNDER by 7 LOC (3.5% headroom) |
| Position vs marginal band | UNDER (clean default; band not engaged) |
| §13.4 acknowledgment | NONE NEEDED |

Clean commit. No spill banking.

## B-Phase4-S11b-1-1 banking — corrected framing

**Original (incorrect) framing in commit 28f6983:**
"Documentation-density overshoot beyond marginal-tolerance
band. Tooling scripts with substantial inline rationale
documentation exhibit different LOC density vs prose docs.
Future §13.4 amendment may want to add 'tooling-script
ceiling' analogous to §13.3 test-LOC ceiling."

**Corrected framing (this re-commit):** the original S11b-1
commit at 274 LOC was substantive scope spill, not
measurement-variance. ~120 LOC of inline rationale was
content the script could exist without; that's substantive
scope addition, not LOC-counting noise. The discipline as
codified is correct; the violation was the original commit's
classification, not the codified §13.4 band.

**Lesson banked:** tooling scripts with substantial design
rationale should default to:
1. Module-level docstring covering essential contract +
   high-level design rationale (~30-40 LOC).
2. Per-function 1-2 line docstrings (essential contract).
3. Inline comments only for non-obvious code paths
   (~3-5 LOC each).
4. Cross-references to external docs (P-1 §x.y, findings
   doc §x.y) for detailed case study material.

The pattern keeps tooling scripts under §13.1 default
budget without compromising operational documentation —
the documentation lives WHERE FUTURE CYCLE AUTHORS LOOK
FOR IT (module docstring at script-top; project-level docs
for case studies) rather than embedded in inline comments
that bloat LOC count without serving the actual reading
pattern.

**Decline of §13.6 tooling-script-density amendment** (per
user disposition): the discipline as codified is correct;
codifying a "tooling-script ceiling" to legitimize the
violated commit would be goalpost-moving. The §13.4
marginal-tolerance principle was specifically NOT designed
to enable that pattern.

## B-Phase4-S11b-1-2 — preserved unchanged

The sequence-ordering constraint (S11b-2's dtw fix MUST
land before S11b-3's CI step) is preserved as institutional
precedent. Still relevant for the remaining sub-sessions.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| `parity-fast` tier outcome distribution unchanged | n/a (script alone; no CI integration yet) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| Validation script runs clean against current state | ✅ exit 0 |
| New script unit tests | n/a at S11b-1 (tests land at S11b-2) |
| CI green on `parity-fast.yml` post-push | pending |

## v1.2.0 amendment ledger update

S11b-1 contributes to operational tooling, NOT to v1.2.0
doc-set. No v1.2.0 ledger entry.

**Cumulative ledger after S11b-1 (unchanged):**

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
| `tools/validate_install_matrix.py` | NEW (re-commit; tightened) | +193 |
| `docs/reference_parity_phase4/session_11b_1_findings.md` | NEW (re-commit; updated) | ~165 |
| **Total (commit-counted; excludes findings doc)** | | **+193 LOC** |

## Disposition

| Item | Pre-S11b-1 status | Post-S11b-1 status |
|---|---|---|
| B-Phase4-S5-4 (install-matrix operational enforcement) | banked | **PARTIAL** — validation script CLOSED; CI integration + tests + workflow gap fix deferred to S11b-2/S11b-3 |
| 13-item inheritance register | 1 open + 12 closed | **1 open + 12 closed** (B-Phase4-S5-4 is operational item, not in original 13) |
| Original commit 28f6983 (substantive-scope misclassification) | committed (CI PASS) | **REVERTED** (revert commit 3b04bf9; institutional discipline preserved at substance level) |
| Phase 4 cycle progress | 11 of 13 sessions (85%) | **(no full-session count change; sub-sub-session)** |

## Banked observations from S11b-1 (re-commit)

**B-Phase4-S11b-1-1 (corrected) — Tooling-script
documentation density discipline.** Tooling scripts with
substantial design rationale should distribute documentation
across:
- Module-level docstring (essential contract + high-level
  rationale; ~30-40 LOC).
- Per-function 1-2 line docstrings (essential contract).
- Inline comments only for non-obvious paths (~3-5 LOC).
- Cross-references to external project-level docs for
  detailed case study material.

The pattern keeps scripts under §13.1 default budget AND
puts documentation where future cycle authors look for it
(module docstring at script-top; project docs for case
studies). NOT a §13.6 amendment candidate; this is the
existing discipline applied correctly.

**B-Phase4-S11b-1-2 (preserved) — Three-way split
sequence-ordering constraint.** S11b-2's dtw fix MUST
land BEFORE S11b-3's CI step (otherwise CI red on master
because parity-slow.yml on master wouldn't have dtw entry
yet). Still relevant for remaining sub-sessions.

**B-Phase4-S11b-1-3 (NEW) — Revert-and-re-commit
discipline for misclassified spill.** When a sub-session
commits with substantive overshoot misclassified as
measurement-variance, the right disposition is **revert +
re-commit with tightened content**, NOT codify a §13
amendment that legitimizes the misclassification. Two-
commit footprint (revert + re-commit) on master is
acceptable; the audit trail value of preserving the
revert outweighs the noise. Bank as institutional
precedent for future cycles.

## Next sub-session

**S11b-2 — Tests + workflow gap fix.**

| File | LOC |
|---|---|
| `tools/test_validate_install_matrix.py` (NEW) | +195 |
| `.github/workflows/parity-slow.yml` (dtw entry on Windows + Linux jobs) | +17 |
| **Total** | **+212** |

§13.3 spill check on tests alone: 195 LOC > 150 ceiling
(30% over). Per the corrected B-Phase4-S11b-1-1 framing,
the test file's 195 LOC may also be substantive overshoot
candidate for tightening rather than acknowledgment-banking.
Will surface to Chat at S11b-2 if spill threshold crossed
substantively.
