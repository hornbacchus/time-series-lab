# Bond Yield Forecast Session 6 — Closeout + §6 deferred cleanup + v1.2.0 candidates finalization

**Date:** 2026-05-01
**Scope:** Per integration plan §6 — final verification; §6
deferred cleanup (§6(a) build_panel docstring; §6(f) horizon=1
regression test; §6(h) numba JIT first-call latency
documentation); BVAR standalone repo retirement
(`v1.0.0-pre-tsl-integration` tag + README banner);
v1.2.0 amendment candidates document finalization
(extended from 5 to 10 candidates).
**Status:** COMPLETE — Bond Yield Forecast integration cycle
CLOSED.

## Pre-Session 6 verification gate

| Check | Status |
|---|---|
| Session 5 committed (38a5144) + CI install-matrix gap closed | ✓ |
| S4 audit verdict 10/10 PASS-A.1+F unchanged | ✓ |
| JIT warming integrated (cold 2.05s; cached <0.001s) | ✓ |
| P-4 status tracker entry phrased as PASS-A.1+F with explicit intra-implementation-only limitation | ✓ |
| Phase 4 v1.2.0 amendment candidates document created with 5 banked items | ✓ (extended at S6 to 10) |
| Migration tests 86/16 unchanged | ✓ |

## §6.1 — Final verification

Excel-side smoke test deferred to user (Auto-Mode shouldn't
drive interactive Excel). End-to-end dispatch smoke run via
`engine/techniques/bond_yield_forecast.run()` directly:

| Phase | Result |
|---|---|
| Pre-flight validation (without `input_workbook` param) | Correctly rejects with "Missing required parameter 'input_workbook'…" + Ribbon-action remediation hint |
| Pre-flight validation (`n_draws=500` below minimum 1000) | Correctly rejects with "Parameter 'n_draws'=500.0 is below minimum 1000. This guards against Session 0-validated failure modes…" |
| Successful run (canonical fixture; `n_draws=1000, n_burn=250, n_paths=50, horizon=8`) | status=success; wall-clock 7.32s; 4 tables emitted ("Yield Forecast", "Macro Conditioning Paths", "Convergence Diagnostics", "Run Metadata"); 19 audit fields; 0 warnings |

The 7.32s wall-clock at minimum-allowed chain config
(2× faster than the 20s audit-chain config which is itself
2× faster than the ~22s default-chain production config)
confirms the dispatch path is healthy across the chain-config
spectrum.

## §6.2 — §6 deferred cleanup items

### §6(a) — `build_panel(raw=...)` docstring

`engine/techniques/bond_yield_forecast/data.py:450` —
`build_panel()` signature now documents the `raw` parameter
explicitly with full shape contract:

- `raw["macro_raw"]`: pandas DataFrame; PeriodIndex quarterly;
  3 columns matching `config["data"]["macro_columns"]`
  (Real GDP Growth (Q/Q SAAR), Headline CPI Inflation (Q/Q
  annualized), Effective Federal Funds Rate (Q-end) by
  default).
- `raw["yields_raw"]`: pandas DataFrame; PeriodIndex
  quarterly; 10 columns matching
  `config["data"]["yield_columns"]` (3M, 6M, 1Y, 2Y, 3Y,
  5Y, 7Y, 10Y, 20Y, 30Y by default).

Caller documentation: notes that `_dispatch._build_panel_in_memory`
(TSL Excel-DNA in-memory path) and
`unified_input.read_unified_workbook` (bundled-template path)
are the two upstream constructors of `raw`.

### §6(f) — `posterior_predictive_unconditional` horizon=1 regression test

`engine/techniques/bond_yield_forecast/tests/test_estimation.py`
adds `test_bvarsv_unconditional_posterior_predictive_horizon_one`:
- Asserts shape `(n_kept * n_paths, 1, n_vars)` for the
  collapsed-horizon case.
- Asserts all-finite output.
- Asserts the first-period draw differs from the deterministic
  VAR mean `B @ [1, last_obs[::-1].ravel()]` — i.e., the SV
  innovation was actually applied (catches the
  silently-zeroed-innovation regression).

Validates BVAR Session 0 banked item §6(f).

### §6(h) — Numba JIT first-call latency documentation

`resources/techniques_md/bond_yield_forecast.md` § "Performance
characteristics" → new sub-section "First-call vs subsequent-
call latency (numba JIT)" with:
- Identifies the two `@jit(cache=True)` functions
  (`_ffbs.ffbs_one_equation`,
  `_conditional_inner.conditional_forecast_inner_loop`).
- Cold-cache cost: 2-5s; on-disk cache binds to
  (numba version, Python version, platform, source mtime).
- Warm-cache cost: <0.001s lookup.
- TSL integration: engine_worker startup invokes
  `_jit_warmer.warm_jit_caches()` once before the named-pipe
  server accepts connections; first user-facing click sees
  warm path.
- Cold-call latency cases: fresh deployment, numba upgrade,
  Python upgrade, ad-hoc invocations outside engine_worker.
- Lazy-warming alternative banked for hardware where
  cold-warm exceeds 10s (current dev-hardware: 2.05s).

## §6.3 — BVAR standalone repo retirement

**Standalone repo location:**
`C:/Users/matth/OneDrive/Projects/bvar-yield-forecaster`.

| Action | Status |
|---|---|
| README banner committed | ✓ Commit `ce8bd4b` on master (fast-forward from `bd7c6a0`) |
| `v1.0.0-pre-tsl-integration` tag created at `ce8bd4b` | ✓ Local tag created |
| Existing `v1.0.0-session-0-complete` tag retained at `bd7c6a0` | ✓ Last functional / pre-banner commit |
| Push retirement commit + tag to GitHub | ⚠ Pending — surface to user; standalone-repo writes need explicit authorization |
| Mark GitHub repo as Archived | ⚠ Pending — manual GitHub UI step |

The README banner (53-line block at top) explicitly states
the repo is RETIRED, points to TSL's
`engine/techniques/bond_yield_forecast/`, lists all 6
integration findings docs, explains the migration rationale,
and notes that issues/PRs against the standalone repo will
not be actioned. Historical README content preserved as-is
below the banner for forensic reference.

**Two tags now point at the retirement boundary:**
- `v1.0.0-session-0-complete` @ `bd7c6a0` — byte-identical
  pre-migration baseline (functional code; no banner).
- `v1.0.0-pre-tsl-integration` @ `ce8bd4b` — retirement marker
  (= baseline + retirement banner).

### Legacy archives in TSL repo — keep in place

The TSL subpackage carries
`engine/techniques/bond_yield_forecast/_legacy_cli.py.archive`
(1841 LOC) and `_legacy_data.archive/` (36 KB). Both are
git-tracked since S1; neither imports in any active code
path. **Five test files reference them in SKIP-test rationale
strings:**
- `tests/test_session0_logging.py` (5 SKIPs)
- `tests/test_session0_paths.py` (2 SKIPs)
- `tests/test_session0_warnings.py` (3 SKIPs)
- `tests/test_unified_input.py` (3 SKIPs)
- `_dispatch.py` docstring reference (1 mention)

Removing the archives would not break the SKIPs (which SKIP
unconditionally) but would break the documentary chain — the
SKIP rationale strings cite the .archive filenames as
forensic context. Cost-benefit: keeping the archives costs
~37 KB of inert content; removing them weakens the audit
trail.

**Decision: keep in place.** Per Auto-Mode policy on
delete-data actions, this needs explicit user authorization
to remove regardless. If the user wants them removed in a
follow-up, the change is mechanical (delete + update SKIP
rationale strings to past-tense in the same commit).

## §6.4 — v1.2.0 amendment candidates extension

`docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md`
extended from 5 candidates (S5 baseline) to 10 candidates:

| # | Candidate | Origin | Type | Phase 4 priority |
|---:|---|---|---|---|
| 1 | R `BVAR` constant-vol Pattern A.2 | S4 | Audit + doc | Medium |
| 2 | Minnesota dummy-observation Pattern A.3 | S4 | Audit + doc | High |
| 3 | `stochvol` rpy2 partial A.2 (SV component) | S4 | Audit + doc | Medium |
| 4 | P-2 §B.6 `bvars`-availability entry | S4 | Doc-only | Low |
| 5 | P-1 v1.2.0 docstring-convention amendment (incl. PCA / intercept / truncation annotations) | S4 | Doc + engine backfill | High |
| **6** | **C-1 v2 §"Wrapper module-vs-package layout"** (file/package collision) | **S2** | **Doc-only** | **Low** |
| **7** | **C-1 v2 §"Bundled-workbook input wrappers" recipe** (sheet-naming auto-detection) | **S3** | **Doc-only** | **Low** |
| **8** | **C-1 v2 §"Layered validation"** (request-local config; re-entrancy fix) | **S3** | **Doc-only** | **Medium** |
| **9** | **P-1 v1.2.0 §6.1 tier-classification clarification** (audit-script vs production-default runtime) | **S5** | **Doc-only** | **Medium** |
| **10** | **P-1 v1.2.0 §pre-merge install-matrix gate** (BYF S4-S5 + Phase 3.5 S6 retrospective) | **S5+S6** | **Doc-only** | **High** |

**Highest-priority cluster identified:** #2, #5, #10 — share a
"lessons-learned codification" theme. #5 saves cycle-time on
future audits; #10 prevents recurrence of the install-matrix
failure class (now seen twice: Phase 3.5 S6 x13binary, BYF
S4-S5 openpyxl); #2 unlocks high-value-per-LOC cross-
implementation verification for the Minnesota prior. Phase 4
sequencing should consider bundling these in an early
documentation-amendment session.

## §6.5 — Tier classification clarification (absorbed into candidate #9)

The user prompt for S6 asked for tier-classification
clarification:
(a) Confirm S5 deviation documented with empirical
    justification — **YES**, in `session_5_findings.md` §"Tier
    classification deviation banked" + `phase4_v1_2_0_amendment_candidates.md`
    candidate #9.
(b) Clarify whether the 20s measurement reflects audit-script
    or production-default config — **AUDIT-SCRIPT** chain
    config (`n_draws=2000, n_burn=500`); production-default is
    `n_draws=10000, n_burn=3000` (~22s on warm-JIT per the
    user-facing markdown perf table).
(c) If audit-script and production-default runtimes diverge
    significantly, document both — **DONE** (markdown perf
    table + audit script tolerances both reflect the
    measurements they were written against; the clarification
    that "CI tier classification is by audit-script runtime,
    not production-default runtime" is now codified in
    candidate #9 for P-1 v1.2.0 amendment).

**Both runtimes fit fast-tier as currently configured** —
audit-script ~20s, production-default ~22s. §5.1's slow-tier
classification was a defensive estimate; the actual
measurements support fast-tier on both surfaces. No change
to the audit-script `tier="fast"` registration.

## Verification gates (pre-commit)

| Gate | Status |
|---|---|
| New horizon=1 regression test | ✓ PASS in 0.91s |
| Migration tests (102 collected) | ✓ 86 PASS + 16 SKIP unchanged from S2-S5 |
| Engine pytest (96 tests) | ✓ pre-existing 96/96 PASS state preserved |
| Fast-tier sweep (77 with BYF) | ✓ pre-existing 72 PASS + 5 CAVEAT, 0 BLOCK state preserved |
| Existing `engine/techniques/bvar.py` | ✓ UNCHANGED across full BYF cycle (S1-S6) |
| Catalog JSON | ✓ unchanged from S2 (no new params) |
| Standalone repo working tree | ✓ clean (committed at `ce8bd4b`) |

## File topology

| File | Action | LOC |
|---|---|---|
| `engine/techniques/bond_yield_forecast/data.py` | `build_panel(raw=...)` docstring expansion (§6(a)) | +35 |
| `engine/techniques/bond_yield_forecast/tests/test_estimation.py` | `test_bvarsv_unconditional_posterior_predictive_horizon_one` (§6(f)) | +37 |
| `resources/techniques_md/bond_yield_forecast.md` | First-call vs subsequent-call latency sub-section (§6(h)) | +50 (replaces 5 prior LOC) |
| `docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md` | Candidates #6-#10 + extended summary table | +220 |
| `docs/bond_yield_forecast_integration/session_6_findings.md` | New (this file) | ~250 |
| `C:/Users/matth/OneDrive/Projects/bvar-yield-forecaster/README.md` | Retirement banner | +53 (separate repo; commit `ce8bd4b`) |
| **Total (TSL repo only)** | | **~590 LOC across 5 files** |

## Schedule status

Bond Yield Forecast cycle: **6 of 6 TSL-side sessions COMPLETE.**

**Session disposition:**

| Session | Topic | Commit | Findings doc |
|---|---|---|---|
| 1 | BVAR migration | `95f5f01` | `session_1_findings.md` |
| 2 | Dispatch + 5-place integration | `075fa2e` | `session_2_findings.md` |
| 3 | Sample template + Ribbon dropdown | `39fd4e6` | `session_3_findings.md` |
| 4 | Parity audit at P-1 v1.1.0 | `4983522` | `session_4_findings.md` |
| 5 | MANIFEST + CI + JIT warming | `38a5144` | `session_5_findings.md` |
| 6 | Closeout (this commit) | (pending) | `session_6_findings.md` |

**Next:** Phase 4 master plan drafting begins. The handoff doc
is the v1.2.0 amendment candidates document at
`docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md`
— Phase 4 sequencing inherits 10 banked candidates plus the
3 carry-forward items from Phase 3.5 (P4-1 structural
invariants on 12 inherited wrappers; P4-2
statsmodels-x13ashtml integration; P4-3 CSD wrapper
n_surrogates engineering).

## Final cycle outcomes (BYF S1-S6)

- ✅ 84-wrapper coverage state (83 CAI + 1 BYF post-CAI-
  integration; 83 parity checks @ 77 fast + 6 slow)
- ✅ BVAR-SV bond-yield forecaster fully integrated into TSL
  Excel-DNA add-in with 5-place coordination (registry +
  catalog + markdown + dispatch + ribbon)
- ✅ Pattern A.1 self-parity + Pattern F invariants verdict
  PASS-A.1+F documented honestly with intra-implementation-
  only limitation
- ✅ R bvars Pattern A.2 unavailability handled per plan §4.1
  fallback discipline ("do not force the unavailable
  reference")
- ✅ Numba JIT integrated; cold-warm 2.05s in engine_worker
  startup well within 10s budget
- ✅ Standalone bvar-yield-forecaster repo retired with README
  banner + dual tagging
- ✅ 10 v1.2.0 amendment candidates banked for Phase 4
- ✅ Phase 4 master plan drafting handoff doc complete
