# Phase 6+ Session 3 banking — sub-domain (iii) S8 None-handling fix + audit closure (B-Phase4-S7-1 substance-class closure under v1.3 settled framework)

**Date:** 2026-05-09
**Origin:** Phase 6+ Session 3 sub-domain (iii) S8 activation per
master plan §15 framing under v1.3 settled apparatus discipline
(§19.1 novel-substantive class). Closes Phase 4-banked
B-Phase4-S7-1 None-handling bug + clears Phase 5 bridge handoff
disposition (1) reserve sub-domain (iii) at S8-only scope per
Chat ratification.

## B-Phase6-S3-NONE-HANDLING-FIX-S8 — None-handling fix at 5 functions / 7 sites + audit closure + S9 NOT-MET disposition + soft-estimate-vs-empirical forward-looking guidance

Phase 4 S7 banked B-Phase4-S7-1 ("Pre-existing concrete-checker
None-handling bug" with soft-estimate "6 checkers / Phase 3
Sessions 6/8/9 attribution" + "~24 LOC bounded mechanical fix").
Phase 6+ S3 pre-flight empirical re-audit superseded the
soft-estimate per Chat ratification 1.

**Empirical scope (5 functions / 7 vulnerable sites):**

| # | Checker function | Field(s) | Phase 3 batch | Sites |
|---|---|---|---|---|
| 1 | `_check_var_eigenvalues` | `companion_eig_magnitudes` | S7 / Batch 3 | 1 |
| 2 | `_check_garch_conditional_variance` | `conditional_variance` | S6 / Batch 2 | 1 |
| 3 | `_check_hmm_row_sums` | `transition_matrix` | S8 / Batch 4 | 1 |
| 4 | `_check_hmm_emission_normalization` | `emission_means` + `emission_covars` | S8 / Batch 4 | 2 |
| 5 | `_check_conformal_interval_containment` | `lower` + `upper` | S13 / Batch 9 | 2 |

**Banking soft-estimate vs empirical discrepancy:** Banking
attributed S6/8/9; empirical includes S7 (var) + S13 (conformal)
NOT in S6/8/9 enumeration. Banking estimated 6 checkers; empirical
5 functions. Kalman S9 checkers (`_check_kalman_*`) already had
explicit None pre-checks at Phase 6+ S3 audit time (either always
correct or patched at later session). GARCH persistence uses
direct `tsl.get()` without `np.asarray()` conversion — different
pattern; has explicit None pre-check.

**Fix mechanism (Option A per-checker explicit pre-check;
ratified clean):**

Existing-pattern alignment with the dominant pattern in same file
(~8 other concrete checkers already use `if X is None: return
BLOCK` pre-check pattern). Per-site fix template:

```python
field_value = tsl.get("field_name")
if field_value is None:
    return {"name": inv.name, "status": "BLOCK",
            "error": "TSL output missing 'field_name' field"}
arr = np.asarray(field_value, dtype=np.float64)
if arr.size == 0:
    return {"name": inv.name, "status": "BLOCK",
            "error": "TSL output 'field_name' is empty"}
```

Fix preserves existing size-empty fallback; differentiates
None-input (field missing) from empty-array-input (field
present but empty array) at error message granularity.

Options B (helper function) + C (decorator) correctly rejected
at this scope per YAGNI + existing-pattern alignment + Reading B
instrumentation cleanliness arguments.

**Test enrichment (Chat ratification 4 + integration check):**
- 5 new synthetic tests: `test_phase6_s3_none_handling_<checker>`
  per fixed function; multi-field cases test BOTH None paths
- Tightened `test_checker_dispatch`: workaround acceptance of
  exceptions removed; all 19 concrete checkers MUST return BLOCK
  dict on empty input (strict-gating)
- Integration check: tightened assertion verified PASS under
  fixed-site behavior pre-commit; all 19 concrete checkers
  empirically return BLOCK dict format on None input

**Audit findings (Interpretation A thorough + B brief surface
check; ratified at Chat ratification 5):**

A — `structural_invariants.py` thorough audit: ZERO additional
concerns. All 19 concrete checkers + multi-field combined
None pre-checks (vecm_cointegration_rank, kalman_*,
wavelet_energy_conservation, fft_energy_conservation,
mcmc_convergence) verified clean.

B — dispatch + lifecycle brief surface check:
- `check_base.py:check_invariants` Q-Allowlist-3=(c) defensive
  layer (lines 209-253) with `_INVARIANT_REQUIRED_FIELDS`
  pre-dispatch check via `tsl_output.get(f) is None` pattern;
  returns INFO outcome WITHOUT dispatching when missing
- `runner.py` dispatch site (lines 226-232) clean; `_is_json_native`
  handles None for serialization
- **Defense-in-depth confirmed:** L1 (check_base.py defensive
  layer catches missing-or-None required fields BEFORE dispatch)
  + L2 (per-checker None pre-check in structural_invariants.py
  catches None inputs that bypass L1)

**S9 trigger evaluation: NOT MET.** Sub-domain (iii) closes at
S8. No cycle-architecture amendment surfaced; no separate
sub-session warranted. Interpretation C (parity-side checks
None-handling audit) remains deferred to S9 conditional or
out-of-cycle per CONSTRAINT 1.

**Forward-looking guidance — soft-estimate-vs-empirical pattern:**

B-Phase4-S7-1 banking soft-estimate ("6 checkers / S6/8/9") was
authored at Phase 4 S7 close under §11.8 trigger blast-radius
discipline (didn't enumerate to avoid scope expansion). Phase 6+
S3 pre-flight empirical audit took ~3 LOC of grep + manual scan
to produce authoritative count.

**Recommended pattern at v1.3 §19 apparatus discipline addition
candidate (next recalibration moment):** banking entries SHOULD
prefer empirical enumeration over soft-estimate framing when the
enumeration is bounded + audit-feasible at banking time, even
when fix is deferred. Soft-estimate framing creates downstream
audit overhead at activation time + risks inheritor following
soft-estimate as authoritative scope (would have led to wrong
session/wrong checker enumeration at S3 pre-flight without
empirical re-audit). Add to next recalibration moment via
§19.4 living calibration baseline file — NOT v1.3 §19 amendment
inline at this sub-session per CONSTRAINT 1 master-plan-amendment
exclusion.

**Cross-references** (per (mit-ii) brief):
- B-Phase4-S7-1 at `../reference_parity_phase4/session_7_findings.md`
  (Phase 4 origin; soft-estimate banking)
- v1.3 §15 sub-domain (i) extension at master plan
  (architectural pattern locus for substance-class amendment;
  parameter-aware exclusion mechanism precedent)
- v1.3 §19.1 sub-session class taxonomy compliance: novel-
  substantive class with full pre-flight earned (scope
  determination protocol Steps 1-5 STOP-AND-CONFIRM); banking
  earned at sub-session END (substance-class architectural-
  amendment-adjacent scope per §19.6); Q-disposition NOT
  triggered (§19.3 contested-decision threshold not met;
  pre-flight + ratifications proceeded under standard
  surface-to-Chat discipline)
- Commit 1 `f0cd074` (fix + tests + audit findings inline)
- Commit 2 (this entry; banking codification)

**Reading B confirmation instrumentation (first substance-class
post-observation):** see Code's closeout instrumentation report
in CI verification messaging; v1.3 §19.6 substance-class
discipline applied + anecdote → observation graduation
recommendation surfaced.

## Disposition

Phase 6+ S3 SHIPPED via 2-commit sequence (Commit 1 fix + tests
+ audit inline; Commit 2 banking codification). B-Phase4-S7-1
None-handling bug CLOSED across 5 functions / 7 sites. Audit
A + B surfaced ZERO concerns; S9 trigger NOT MET; sub-domain
(iii) closes at S8. Phase 5 bridge handoff disposition (1)
reserve sub-domain (iii) CLOSED at this sub-session per Chat
activation scope decision. Sub-domain (ii) + (iv) remain at
post-S3 disposition under settled framework.
