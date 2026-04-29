# Phase 3.5 Session 1 — Bundled CI cleanup + forward provision

**Date:** 2026-04-29
**Scope:** Items 4 + 5 + 7 per Session 1 prompt. Single-session.
**Status:** COMPLETE.

This is the first Phase 3.5 session. Three items bundled in a
single commit per locked discipline (carry-forward from Phase 3
Session 6 hardening).

## Item 4 — `parity-slow.yml` install matrix cleanup

**Diagnosis (from Phase 3 Session 18 closeout):** the slow-tier
workflow's install matrix was stale — missing `prophet`,
`dtaidistance`, `reservoirpy`, plus several other deps that
fast-tier had picked up across Sessions S6–S14. Slow-tier
checks would SKIP on missing deps (informative-not-failing),
masking real coverage gaps in the nightly run.

**Action:** aligned the slow-tier Python + R install matrices
with the fast-tier matrices.

**Python additions** (12 packages):
- torch==2.11.0 (parity with fast-tier)
- ewstools==2.1.2 (parity with fast-tier)
- ruptures (p3_pelt; harness-discovery dep)
- astropy (p3_lomb_scargle; discovery dep)
- PyWavelets (p3_wavelet_transform / p3_wavelet_coherence; discovery dep)
- EMD-signal (p3_emd_hht; discovery dep)
- pyts (discovery dep)
- xgboost (p3_xgboost; discovery dep)
- lightgbm (p3_lightgbm; discovery dep)
- reservoirpy (p3_esn; discovery dep)
- prophet (p3_prophet; **genuine slow-tier reference**)
- dtaidistance (p3_dtw; discovery dep)

**R additions** (4 packages):
- robustbase (p3_robust_estimators; discovery dep)
- lmtest (p3_granger; discovery dep)
- tempdisagg (p3_denton_chowlin; discovery dep)
- forecastHybrid (p3_forecast_combination cross-check candidate; discovery dep)

**`seasonal` (X-13) deliberately omitted** — requires X-13 binary;
p3_x13 SKIPs gracefully on Windows runner.

**Why discovery deps matter:** every check class imports at
runner startup regardless of tier (the harness's `discover_checks()`
walks the `harness/checks/` package and imports each module).
Missing a fast-tier dep on a slow-tier runner causes the runner
to fail at discovery time before any slow-tier check runs.
Aligning the matrices ensures discovery succeeds on both tiers.

## Item 5 — `scripts/` cleanup

**Diagnosis (from Phase 3 Session 18 closeout):** 12 deprecated
Phase 1 audit scripts under `tools/reference_parity/scripts/`
were superseded by Phase 3 `harness/checks/p3_*.py`. Plus
`rscript_bridge.py` (deprecated function-based prototype) and
`test_rscript_bridge.py`. All 14 files raised `ImportError`
at runtime since Phase 2 Session 1.

**Status:** none of the scripts were tracked under git
(per Phase 1 plan discipline; never promoted to master).

**Action:**
- Deleted local files:
  - 12 audit scripts (audit_1a_regression.py, audit_1b_tbats.py,
    audit_1c_bvar_irf.py, audit_2a_kalman.py, audit_2b_mcmc_sv.py,
    audit_2c_student_t_sv.py, audit_3a_caviar.py, audit_3b_har_cj.py,
    audit_3c_ferro_segers.py, audit_3d_johansen.py, audit_3e_mint.py,
    audit_3f_attention.py)
  - rscript_bridge.py
  - test_rscript_bridge.py
  - __pycache__ directory
- Removed empty `tools/reference_parity/scripts/` directory.
- Updated `tools/reference_parity/INVENTORY.md` §1.4 from
  "DEPRECATED" status to "REMOVED at Phase 3.5 Session 1"
  with historical-record note.
- Updated `tools/reference_parity/harness/r_bridge.py`
  module docstring to remove dangling reference to the
  removed scripts/ path; replaced with INVENTORY.md cross-
  reference.

**Cross-references verified:**
- `harness/tolerances.py` `justification` fields cite Phase 1
  audit IDs (e.g., `1c_bvar_irf_fevd`) — NOT file paths.
  Unaffected.
- `INVENTORY.md` §1.4 explicitly notes the deletion + preserves
  the historical script list for archaeological reference.
- Phase 1 audit reports under `tools/reference_parity/reports/<phase1_id>_audit.md`
  remain in place (not under git either; preserved in local
  checkouts as the durable Phase 1 record).

**Runtime dependency check:** none of the tracked harness
files imported from `scripts/`. Only docstring/comment
references existed; cleaned up where they pointed at the
now-removed paths.

## Item 7 — DOCUMENTED-DIVERGENCE first-instance reservation

**Diagnosis (from Phase 3 P-1 §2.3 + P-3 §6.6):** P-1 codifies
DOCUMENTED-DIVERGENCE as a valid runtime outcome but Phase 3
batch-execution did not surface a single instance (CAVEAT
absorbed all such cases). The verdict is reserved for first-
instance use in post-Phase-3 work; the runtime path was not
fully wired during Phase 3.

**Action:** wired DOCUMENTED-DIVERGENCE as a first-class runtime
outcome end-to-end:

### Changes

| File | Change |
|---|---|
| `harness/base.py` | Added `DOCUMENTED-DIVERGENCE` to `Outcome` literal type; added to `_OUTCOME_PRIORITY` dict at rank 3 (between CAVEAT=2 and ERROR=4); updated module docstring + `aggregate_outcomes` docstring |
| `harness/runner.py` | Updated module docstring (exit codes); `_exit_code_for()` returns 4 for DOCUMENTED-DIVERGENCE |
| `.github/workflows/parity-fast.yml` | Added exit code 4 → 0 mapping in shell `elif` block; updated header comment |
| `.github/workflows/parity-slow.yml` | Same as fast |

### Rationale for exit code 4

CAVEAT uses exit 2; ERROR uses 3. Using a fresh exit code (4)
instead of sharing exit 2 with CAVEAT keeps the two outcomes
distinguishable in CI logs and human-readable summaries.

### Sanity tests (6/6 passed)

In-process Python tests verified:

1. `Outcome` literal includes `DOCUMENTED-DIVERGENCE` ✓
2. `_OUTCOME_PRIORITY['DOCUMENTED-DIVERGENCE'] == 3` ✓
3. `aggregate_outcomes([PASS, DD, PASS]) == 'DOCUMENTED-DIVERGENCE'` ✓
4. Outcome ranking: BLOCK > ERROR > DD > CAVEAT > PASS > SKIP ✓
5. `_exit_code_for('DOCUMENTED-DIVERGENCE') == 4` ✓
6. `ParityResult(outcome='DOCUMENTED-DIVERGENCE')` accepts ✓

### No current wrapper triggers DD

Per locked Phase 3 evidence (P-1 §2.3 + P-3 §5): Phase 3
batch-execution did not surface a single DOCUMENTED-DIVERGENCE
instance. CAVEAT absorbed all 5 methodology-equivalent
divergences (p3_stl, p3_mstl, p3_star, p3_nar_narx,
p3_emd_hht). This commit is forward-provisioning; no current
wrapper changes verdict from CAVEAT to DD.

When DD first surfaces in post-Phase-3 work (most likely on
a new wrapper class with genuine methodology divergence from
canonical reference), the audit will be the first concrete
instance. Per P-3 §6.6, P-2 will document the
PASS / CAVEAT / DOCUMENTED-DIVERGENCE classification recipe
at that time.

## Verification

- Full fast-tier sweep: 76/76 in 102.4s (71 PASS + 5 CAVEAT;
  unchanged from Phase 3 close).
- DOCUMENTED-DIVERGENCE sanity tests: 6/6 PASS.
- `Outcome` literal type widening verified backward-compatible
  (no existing check produces DD; runner exit-code mapping
  preserved for all existing outcomes).

## Commit footprint

| File | Lines added/changed |
|---|---:|
| `tools/reference_parity/INVENTORY.md` | -19 / +25 |
| `tools/reference_parity/harness/r_bridge.py` (docstring) | -2 / +3 |
| `tools/reference_parity/harness/base.py` | -7 / +37 |
| `tools/reference_parity/harness/runner.py` | -7 / +24 |
| `.github/workflows/parity-fast.yml` | -10 / +21 |
| `.github/workflows/parity-slow.yml` | -10 / +25 |
| `docs/reference_parity_status.md` | -1 / +5 |
| `docs/reference_parity_phase3_5/session_1_findings.md` | new |
| **Total** | **~150 LOC** matching prompt estimate |

## Banked items remaining (8)

Per locked Phase 3.5 schedule:

| Item | Description | Session |
|---|---|---|
| 1 | `single_impl_mle` band tightening | Pending |
| 2 | em_stochastic per-metric bands | Pending |
| 3 | Manifest re-pin cadence | Pending |
| 6 | X-13 binary on Linux CI | Pending |
| 8 | 12 pre-Phase-3 wrapper migration | Session 2 (next) |
| 9 | Macro fixture expansion | Pending |
| (doc) | Phase 3.5 documentation phase | Session 11 |
| (close) | Phase 3.5 closeout | Session 12 |

## Next session

Phase 3.5 Session 2 — Item 8 entry: 12 pre-Phase-3 wrapper
migration. Promotes the 12 inherited Phase 1/2 audit IDs
(1c, 2a, 2b, 2c, 3a, 3b, 3c, 3d, 3e, 3f, _smoke_test,
critical_slowing_down) to the P3ParityCheck v3 contract
(verdict_class declaration; structural_invariants
declaration; etc.). Per locked schedule.

No Chat re-engagement required between Sessions 1 and 6
unless escalation triggers per §8.1 risks. Midpoint check-in
post-Session 6 if scope deviates >25% from session estimates.
