# Bond Yield Forecast Session 5 — MANIFEST + CI integration + JIT warming + P-4 v1.1.x update

**Date:** 2026-05-01
**Scope:** Per integration plan §5 — manifest re-pin; CI
install matrix integration; JIT warming integration with
engine_worker startup; P-4 status tracker update; Phase 4
v1.2.0 amendment candidates document.
**Status:** COMPLETE.

## Pre-Session 5 verification gate

| Check | Status |
|---|---|
| Session 4 commit `4983522` + parity verdict PASS-A.1+F | ✓ |
| Audit script + report shipped at `p3_bond_yield_forecast_audit.md` | ✓ |
| `tolerances.py` ladder entry registered | ✓ |
| Migration tests 86 PASS + 16 SKIP unchanged | ✓ |
| Parity-fast 76/76 unchanged pre-session | ✓ |
| Existing `engine/techniques/bvar.py` UNCHANGED across BYF cycle | ✓ |

## Step 5.1 — MANIFEST + requirements verification

Per integration plan §5.1: confirm `numba`, `pyyaml`,
`openpyxl` are in MANIFEST.toml and `engine/requirements.txt`.
Both pinned at Session 1 (commit `95f5f01`); no further work.

Reviewed:
- `engine/requirements.txt` — `numba>=0.58`, `pyyaml>=6.0`,
  `openpyxl>=3.1` ✓
- `tools/reference_parity/harness/MANIFEST.toml` —
  `numba = "0.65.0"`, `PyYAML = "6.0.3"`,
  `openpyxl = "3.1.5"` ✓

`matplotlib` deliberately NOT added — zero usage in migrated
subpackage (only in archived `legacy_cli` removed at S1).
`pyarrow` NOT added — `_dispatch._build_panel_in_memory()`
bypass avoids the dataframe-roundtrip path that was the only
pyarrow consumer in the standalone repo.

## Step 5.2 — CI install matrix integration

Per integration plan §5.2: align `parity-fast.yml` and
`parity-slow.yml` with new dependencies.

### Tier classification deviation banked

Plan §5.2 directive: BYF audit "lives in slow-tier per §5.1
classification." Empirical wall-clock measured at Session 4:
**~20 seconds** (audit chain `n_draws=2000, n_burn=500`,
deliberately reduced from default `10000/3000` per integration
plan §5.1). Sits under the 30s fast-tier ceiling, well above
the ≥120s slow-tier floor.

**Decision:** Audit registered with `tier="fast"` in
`p3_bond_yield_forecast.py`. Fast-tier CI now runs BYF every
PR; slow-tier nightly is unaffected.

**Documented divergence from plan §5.1:** the §5.1 estimate
was based on default-chain config (~40s wall-clock); the
audit's reduced-chain design avoids the classification
ceiling. Plan §5.1 noted this trade-off as a Phase 4 re-bench
candidate; the runtime fits the fast-tier budget at the
chosen audit-chain config.

### Workflow file edits

`.github/workflows/parity-fast.yml`:
- Added `numba pyyaml openpyxl` to the Python install line.
- Added comment block citing BYF Session 5 deps and
  fast-tier classification rationale.

`.github/workflows/parity-slow.yml` — both Windows job AND
Linux job:
- Added same `numba pyyaml openpyxl` install entries.
- Slow-tier install must mirror fast-tier because BYF check
  imports happen at runner-discovery time regardless of
  tier (per Phase 3.5 Session 1 Item 4 protocol).

## Step 5.3 — JIT warming integration with engine_worker startup

Per integration plan §5.3: invoke
`engine.techniques.bond_yield_forecast._jit_warmer.warm_jit_caches()`
exactly once at process startup, before any background
threads spawn; warming should add <10s to engine_worker
startup; lazy-warming alternative banked if exceeded.

### Integration site

`engine/engine_worker.py:serve()` — inserted JIT warming
block immediately after the initial banner-logging (Python
version, platform, engine dir, network policy) and BEFORE
named-pipe creation. Wrapped in broad try/except so a missing
subpackage cannot crash engine startup; warm duration logged
for monitoring.

```python
try:
    _t_warm = time.time()
    from techniques.bond_yield_forecast._jit_warmer import (
        warm_jit_caches,
    )
    warm_jit_caches()
    _warm_dur = time.time() - _t_warm
    log.info(
        f"JIT caches warmed (bond_yield_forecast): {_warm_dur:.2f}s"
    )
except Exception as e:
    # Non-fatal — first BYF call will pay the JIT cost on demand.
    log.warning(
        f"JIT warming skipped (non-fatal): {type(e).__name__}: {e}"
    )
```

### Wall-clock measurement (dev hardware)

Cold cache: ~1.5s combined for both `_ffbs.ffbs_one_equation`
and `_conditional_inner.conditional_forecast_inner_loop`
(both branches: strict=True and strict=False per
`_jit_warmer.py:67-75`).

Warm cache (re-run after first invocation): <0.1s. Numba
on-disk cache binds to (numba version, Python version,
platform, source-file mtime) per `_jit_warmer.py:35-37`
docstring — fresh deployment re-compiles once, then hits
cache for the lifetime of the install.

**Net startup overhead: well within the plan's 10s budget.**
Lazy-warming alternative remains banked if a future
deployment surfaces hardware where cold-warm exceeds 10s.

## Step 5.4 — P-4 status tracker update

`docs/reference_parity_status.md`:
- Status banner appended with BYF integration sentence;
  v1.1.x increment language.
- New section **"Bond Yield Forecast Integration
  (post-Phase-3.5; +1 wrapper)"** between Batch 10 and the
  "Phase 3 batch-execution COMPLETE" header. Single-row
  table with EXPLICIT verdict characterization
  ("PASS-A.1+F (intra-implementation reproducibility +
  Pattern F structural invariants); intra-implementation
  only, no cross-implementation reference validation") per
  plan §5.4 directive. Verifies-vs-does-not-verify summary
  reproduced from audit-report §4.1-4.4. Phase 4 v1.2.0
  amendment candidates summarized + linked.
- BYF cycle session disposition table (S1-S5) for traceability.
- "Total parity checks under CI" updated **82 → 83**
  (77 fast + 6 slow; 70 Phase 3 + 12 pre-Phase-3 inherited
  + 1 BYF integration).
- "Last updated" line bumped to 2026-05-01 with BYF S5
  context preceding the Phase 3.5 close banner.

## Step 5.5 — calibration_audit_status.md cross-reference

`docs/calibration_audit_status.md`:
- New row in **Multivariate Systems** table:
  `bond_yield_forecast` with status **POST-CAI-INTEGRATION**.
  Findings doc link points to BYF integration plan + Session
  2-4 findings; parity-side audit report linked separately.
- New status legend entry **POST-CAI-INTEGRATION** documents
  the disposition: wrapper integrated AFTER CAI Phase 2 cycle
  close (2026-04-28) so did NOT flow through the CAI per-
  wrapper audit protocol; equivalent calibration discipline
  was applied via the integration plan's testing (S2 dispatch
  test 8/8 PASS) and parity-audit phases (S4 PASS-A.1+F).
- Counts updated: total wrappers **83 → 84**;
  POST-CAI-INTEGRATION = 1 (BYF); other categories unchanged.

This preserves the cross-document accounting integrity:
P-4's "83 parity checks" and CAI's "84 wrappers" are
internally consistent — the CAI wrapper count is
denominator-of-record for wrapper inventory; P-4's 83 counts
parity-audit deliverables specifically.

## Step 5.6 — Phase 4 v1.2.0 amendment candidates document

`docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md`
(new, ~190 LOC) — banks 5 candidates:

| # | Candidate | Type | Cost | Phase 4 priority |
|---:|---|---|---|---|
| 1 | R `BVAR` constant-vol Pattern A.2 | Audit + doc | ~1 session | Medium |
| 2 | Minnesota dummy-observation Pattern A.3 | Audit + doc | ~0.5 session | High (highest value-per-LOC) |
| 3 | `stochvol` rpy2 partial A.2 (SV component) | Audit + doc | ~0.5 session | Medium |
| 4 | P-2 §B.6 `bvars`-availability entry | Doc-only | <0.25 session | Low (trigger-when-available) |
| 5 | P-1 v1.2.0 docstring-convention amendment | Doc + engine backfill | ~1 session | High (cycle-time savings) |

**All 5 carry forward to Phase 4 master plan** — none are
actioned in the BYF integration cycle. Candidates #2 and #5
flagged as highest priority (highest value-per-LOC and
cycle-time savings respectively).

Candidate #5 is the surprise high-value find: BYF S4 burned
3 audit-script iterations resolving wrapper-internal
convention misreads (PCA loadings transposed; intercept at
column FIRST not LAST; truncated PCA roundtrip intentionally
lossy). A `Conventions` docstring-section requirement in
P-1 v1.2.0 would have prevented all three. ROI is measured
in audit-author hours saved across every future BYF-class
integration.

## Verification gates

| Gate | Status |
|---|---|
| Migration tests (102 collected) | 86 passed + 16 skipped — unchanged across S2-S5 |
| Fast-tier sweep (77 with BYF) | 72 PASS + 5 CAVEAT, 0 BLOCK — unchanged from S4 |
| Existing `engine/techniques/bvar.py` | UNCHANGED across full BYF cycle |
| Catalog JSON | unchanged from S2 (no new params) |
| `--check-environment` | clean |
| Engine_worker JIT warm (cold cache) | ~1.5s — well within plan §5.3 10s budget |
| Engine_worker JIT warm (warm cache) | <0.1s |

## File topology

| File | Action | LOC |
|---|---|---|
| `.github/workflows/parity-fast.yml` | install line + comment block | +1 line edit + ~12 LOC comment |
| `.github/workflows/parity-slow.yml` | install lines (Windows + Linux jobs) + comment blocks | +2 line edits + ~16 LOC comments |
| `engine/engine_worker.py` | JIT warming block in `serve()` post-banner pre-pipe | +28 LOC (incl. 19 LOC docstring rationale) |
| `docs/reference_parity_status.md` | BYF section + count update + status banner | +30 LOC additions, ~3 LOC edits |
| `docs/calibration_audit_status.md` | BYF row + POST-CAI-INTEGRATION status legend + count update | +12 LOC additions, ~3 LOC edits |
| `docs/bond_yield_forecast_integration/phase4_v1_2_0_amendment_candidates.md` | new doc | ~190 LOC |
| `docs/bond_yield_forecast_integration/session_5_findings.md` | new doc (this file) | ~210 LOC |
| **Total** | | **~520 LOC across 7 files** |

## Schedule status

Bond Yield Forecast cycle: **5 of 6 TSL-side sessions
complete.** Session 6 follows per locked plan §"Session 6":
final closeout + §6 deferred cleanup + retire
`bvar-yield-forecaster` standalone repo.

## Next session

Bond Yield Forecast Session 6 — closeout per integration
plan §6: deferred cleanup; v1.2.0 amendment candidates
banking confirmation; retire standalone `bvar-yield-
forecaster` repo at `v1.0.0-session-0-complete` tag with
TSL-pointer README.
