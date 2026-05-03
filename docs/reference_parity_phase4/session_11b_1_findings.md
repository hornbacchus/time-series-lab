# Phase 4 Session 11b-1 — `tools/validate_install_matrix.py` script (Option B split, 1 of 3)

**Date:** 2026-05-03
**Scope:** First of three sub-sessions in S11b three-way
split. Lands the `tools/validate_install_matrix.py`
validation script alone. Tests + workflow gap fix at
S11b-2; CI step + pre-commit hook integration at S11b-3.
**Status:** COMPLETE.

## Why this is a sub-session (Option B three-way split)

Per Phase 4 master plan §15 S11 + B-Phase4-S5-4 trigger:
S11b operationally enforces P-1 §8.5 install-matrix gate
(belt-and-suspenders pattern with local pre-commit hook +
CI step). Pre-commit §13.4 spill check returned +386 LOC
engine/audit/doc + +195 LOC tests = +581 combined LOC vs
trigger projection ~125-150 + ~30 = ~180 LOC.

§13.2 bundled-category exception check failed on per-
category LOC (criterion 3): the validation script alone is
274 LOC > 200 default; the test file alone is 195 LOC > 150
test ceiling. Two of three §13.2 criteria fail; per the
binding rule "ALL THREE required", §13.4 split applies.

User Decision (Option B): three-way per-component split
following the trigger's pre-identified natural seam.

| Sub-session | Scope | LOC | Status |
|---|---|---|---|
| S11b-1 | `tools/validate_install_matrix.py` (this) | +274 | (this commit) |
| S11b-2 | tests + workflow gap fix (`tools/test_validate_install_matrix.py` + `parity-slow.yml` dtw entry) | +212 | (next sub-session) |
| S11b-3 | CI step + pre-commit hook (`parity-fast.yml` + `tools/install_hooks.ps1` + `tools/git_hooks/pre-commit`) | +95 | (after S11b-2) |
| **S11b total** | | **+581** | (sequenced commits) |

## What changed

### `tools/validate_install_matrix.py` NEW (~274 LOC)

Validation script that operationally enforces P-1 §8.5
install-matrix gate. Per the script's module docstring,
two enforcement rules:

1. **MANIFEST → slow-tier (full coverage).** Every package
   pinned in `MANIFEST.toml` must appear in BOTH
   `parity-slow.yml` jobs (Windows + Linux). Slow-tier
   install runs the full reference manifest because every
   check class imports at runner-discovery time regardless
   of tier (Phase 3.5 Session 1 Item 4 protocol).

2. **fast-tier ⊂ slow-tier (subset preservation).** Every
   package in `parity-fast.yml` install lines must also
   appear in slow-tier install lines. Fast-tier is
   intentionally a subset of slow-tier; an addition that
   lands on fast but not slow (the BVAR S5 case) is the
   gap the §8.5 gate exists to catch.

NOT enforced: "every MANIFEST package must be in fast-tier".
Fast-tier is documented as a subset per `parity-fast.yml`
"Install fast-tier R packages" step comment ("Subset
matching the fast tier of MANIFEST.toml. Slow tier (full N
packages) lives in parity-slow.yml.").

#### Implementation structure

| Function | Purpose | LOC |
|---|---|---|
| `parse_manifest()` | Read MANIFEST.toml; return `(python_pkgs, r_pkgs)` sets | ~7 |
| `_normalize()` | Lowercase + strip pip-version-pin + quotes | ~10 |
| `parse_pip_install_lines()` | Extract Python packages from `python -m pip install` lines (canonical command form; rejects prose mentions of "pip install" in YAML comments) | ~22 |
| `parse_r_install_packages()` | Extract R packages from `install.packages(c(...))` blocks; handles multi-line + R `#` comment tolerance | ~24 |
| `_parse_slow_tier_jobs()` | Split slow-tier YAML into Windows + Linux jobs by `slow-linux:` marker | ~18 |
| `_check_manifest_in_surface()` | Rule 1 enforcement; return list of violation strings | ~10 |
| `_check_fast_subset_of_slow()` | Rule 2 enforcement; return list of violation strings | ~10 |
| `main()` | Orchestrate parse + checks; print violations to stderr; exit 0/1 | ~50 |
| **Total code logic** | | **~150** |

The remaining ~120 LOC is module docstring + per-function
docstrings + inline rationale comments documenting the
design decisions, BVAR S5 case study citation, Linux-only
allowlist semantics, and belt-and-suspenders pattern
reference (P-1 §13.5.4).

#### Live state validation surface

Running the script against current MANIFEST.toml +
workflow files (with this S11b sequence's full working-
tree edits in place — i.e., the dtw fix landing at S11b-2)
returns exit code 0 with message:

```
MANIFEST.toml: 23 Python packages, 21 R packages
OK — install matrix consistent: MANIFEST coverage in
slow-tier (Win+Linux); fast-tier ⊂ slow-tier.
```

Pre-S11b state (before the dtw fix landing at S11b-2): the
script flagged a real gap — R `dtw` package pinned in
MANIFEST.toml (Phase 3 Session 14 Batch 10) but missing
from both slow-tier R install lines (Windows + Linux).
This is documented as a §8.5 application case study in
S11b-2 findings doc.

## §13.4 spill compliance — B-Phase4-S11b-1-1 acknowledgment

| Aspect | Value |
|---|---|
| §13.1 default budget | 200 net LOC |
| §13.4 marginal-overshoot tolerance band (S11a-2-2 codification) | 5-10% (200-220 LOC) |
| **S11b-1 actual** | **+274 net LOC** on `tools/validate_install_matrix.py` |
| Overshoot vs default | +74 LOC (37% over) |
| Position vs marginal band | OUTSIDE (37% > 10%) |
| Classification | **documentation-density measurement-variance** |

**B-Phase4-S11b-1-1 banking** (institutional precedent for
documentation-density overshoot beyond marginal-tolerance
band):

> The validation script's actual code logic is ~150 LOC
> (well under 200 default). The remaining ~120 LOC is
> module docstring + per-function docstrings + inline
> rationale comments. This is **measurement-variance
> overshoot in spirit** (the script's logical scope matches
> the trigger; LOC inflated by codifying rationale inline
> rather than externally). However, the magnitude (37%
> over default; well outside the 5-10% marginal-tolerance
> band codified at S11a-2-2) does NOT fit the marginal-
> overshoot pattern.

§13.4-marginal-overshoot acknowledged: actual +274 net LOC
vs threshold 200 LOC; 37% over; OUTSIDE codified marginal-
tolerance band (5-10%); classified as documentation-density
measurement-variance because:

1. Single-component scope (one validation script for one
   §8.5 gate); cannot artificially split into multiple
   files without creating false logical seams.
2. ~120 LOC is module docstring + per-function docstrings
   + inline rationale comments documenting the BVAR S5
   case study, Linux-only allowlist semantics, two
   enforcement rules with explicit "not enforced" framing,
   and belt-and-suspenders pattern reference.
3. The inline documentation is operationally useful for
   future cycle authors who will read the script source
   when triaging gate failures or extending the rules.
4. Externalizing the rationale to docs would create a
   read-the-doc-then-read-the-script lookup pattern that
   slows triage; co-locating the rationale beats it.

**Why this is NOT substantive overshoot:**
- No additional concerns added beyond the script.
- No scope creep mid-implementation.
- The trigger's "validation script ~80-100 LOC" projection
  did not anticipate the documentation density of the
  actual implementation.

**Forward-looking implication for §13.4:** the 5-10%
marginal-overshoot band codified at S11a-2-2 was sized for
prose documents (P-1 §13.5 retrospective examples block;
~5-10% over 200 corresponds to typical doc-density variance).
Tooling scripts with substantial inline rationale documentation
exhibit different LOC density vs prose docs. A future §13.4
amendment may want to add a "tooling-script ceiling"
analogous to §13.3 test-LOC ceiling — possibly 300 LOC or
~50% over default — to recognize the legitimate documentation-
density inflation pattern. Bank for Phase 4.5+ or Phase 5
consideration; NOT a Phase 4 amendment (would itself be a
new institutional decision triggering its own session).

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ verified pre-commit (96 passed in 50.88s) |
| `parity-fast --check-environment` clean | ✅ verified pre-commit |
| `parity-fast` tier outcome distribution unchanged | n/a (script alone; no CI integration yet) |
| Numerical-array byte-identical equivalence | n/a (no engine code touched) |
| Validation script runs clean against current state | ✅ exit 0 with the dtw fix in working tree (lands S11b-2) |
| New script unit tests | n/a at S11b-1 (tests land at S11b-2) |
| CI green on `parity-fast.yml` post-push | pending |

S11b-1 lands the script alone; no CI behavioral change
(the script is callable but not invoked anywhere yet). CI
integration lands at S11b-3.

## v1.2.0 amendment ledger update

S11b-1 contributes to operational tooling, NOT to v1.2.0
doc-set. The script lives under `tools/`, not `docs/`. No
v1.2.0 ledger entry.

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
| `tools/validate_install_matrix.py` | NEW | +274 |
| `docs/reference_parity_phase4/session_11b_1_findings.md` | NEW (this file) | ~210 |
| **Total (commit-counted; excludes findings doc)** | | **+274 LOC** |

## Disposition

| Item | Pre-S11b-1 status | Post-S11b-1 status |
|---|---|---|
| B-Phase4-S5-4 (install-matrix operational enforcement) | banked | **PARTIAL** — validation script CLOSED; CI integration + tests + workflow gap fix deferred to S11b-2/S11b-3 |
| 13-item inheritance register | 1 open + 12 closed | **1 open + 12 closed** (B-Phase4-S5-4 is operational item, not in original 13) |
| Phase 4 cycle progress | 11 of 13 sessions (85%) | **(no full-session count change; sub-sub-session)** |

## Banked observations from S11b-1

**B-Phase4-S11b-1-1 — Documentation-density overshoot
beyond marginal-tolerance band.** Tooling scripts with
substantial inline rationale documentation exhibit different
LOC density vs prose docs. The script's actual code logic
is ~150 LOC (under 200 default) but the file is 274 LOC
because of ~120 LOC of inline documentation. This pattern
falls OUTSIDE the §13.4 marginal-tolerance 5-10% band
(which was sized for prose documents at S11a-2-2). For
future cycle authors: tooling scripts with this pattern
should either (a) externalize rationale to a sibling .md
file with a single-line script reference, (b) honor the
§13.4 spill protocol with explicit acknowledgment, or
(c) propose a §13.4 amendment adding a "tooling-script
ceiling" analogous to §13.3 test-LOC ceiling. This S11b-1
takes path (b); paths (a) or (c) are alternatives for
future tooling-script sessions. Bank for §13 future-cycle
consideration.

**B-Phase4-S11b-1-2 — Three-way pre-commit split with
sequence-ordering constraints.** S11b's three-way split
has a sequencing constraint: S11b-2's dtw fix MUST land
BEFORE S11b-3's CI step lands, otherwise the new CI step
would fail on master because parity-slow.yml on master
wouldn't have the dtw entry yet. The trigger's natural-seam
recommendation (script + tests at S11b-1; CI + hook at
S11b-2) does NOT reflect this constraint. Decision (Option
B) split into 3 with the dtw fix bundled with tests at
S11b-2 (not S11b-1) handles the constraint. Bank as
institutional precedent: when a multi-sub-session split
involves both new infrastructure and a fix-of-surfaced-gap,
the gap fix must land BEFORE the infrastructure that would
fail without it.

## Next sub-session

**S11b-2 — Tests + workflow gap fix.**

| File | LOC |
|---|---|
| `tools/test_validate_install_matrix.py` (NEW) | +195 |
| `.github/workflows/parity-slow.yml` (dtw entry on Windows + Linux jobs) | +17 |
| **Total** | **+212** |

§13.3 spill check on tests alone: 195 LOC > 150 ceiling
(30% over). Per the same B-Phase4-S11b-1-1 documentation-
density framing, the test file's 195 LOC reflects 9 test
functions × ~20 LOC each (test fixture setup + assertions +
helper) — standard test density at the script's coverage
need.

Likely needs another acknowledgment-banking discipline
similar to S11b-1; will surface to Chat at S11b-2 if
spill threshold crossed.

After S11b-2, S11b-3 lands the CI step + pre-commit hook
infrastructure (~95 LOC §13.1; clean).
