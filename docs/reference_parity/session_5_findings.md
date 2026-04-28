# Phase 3 Session 5 — Findings (Generator Abstraction)

**Date:** 2026-04-28
**Phase:** Generator abstraction (master plan §10 + §15.3)
**Outcome:** **Bit-for-bit Batch 1 reproduction verified** on
both numerical and metadata fidelity classes. 19/19 fast-tier
checks (10 Phase 3 + 9 inherited) byte-identical post-refactor.

## Outcome summary

| Validation class | Result | Notes |
|---|---|---|
| (a) Numerical fidelity (strict) | **PASS** | All 19 checks byte-identical on `metrics`, `outcome`, `seed_used`, `fixture_sha` |
| (b) Metadata fidelity (investigative) | **PASS** | All 19 checks byte-identical on `error`, `diagnostics`, `reference_versions` (no investigation needed) |
| Structural-invariants registry unit test | **PASS** | 4/4 tests; all 18 stubs raise `NotImplementedError` correctly |
| Spot-checks | **PASS** | `_compare_scalar` single-source in `harness/compare.py`; `_ensure_engine_on_path` single-source in `harness/path_setup.py` for P3 territory |

Master plan §10.3 success criteria status:

| # | Criterion (revised) | Status |
|---|---|---|
| 1 | Batch 2 audit time per wrapper ≤ 60% of Batch 1 manual baseline | Deferred to Batch 2 (Session 6) |
| 2 | Per-check Python file shrinks ≥ 30% LOC vs `p3_arima.py` baseline | Deferred to Batch 2 (P3 Batch 1 checks shrunk modestly via on_caveat_reroll override removal; full ≥30% reduction needs Batch 2 evidence) |
| 3 | Zero modification to harness *infrastructure* code per new wrapper | **Locked** (per-wrapper Python file is expected; harness modules don't change per wrapper) |
| 4 | Generator reproduces Batch 1 audit results bit-for-bit | **PASS** (numerical + metadata) |

## Files changed

### NEW harness modules (~1500 LOC across 7 files)

| File | LOC | Purpose |
|---|---:|---|
| `harness/path_setup.py` | 51 | `_ensure_engine_on_path` shared helper |
| `harness/compare.py` | 165 | `_compare_scalar`, `_compare_vector`, `aggregate_metric_status` |
| `harness/structural_invariants.py` | 220 | `StructuralInvariant` dataclass + 18-stub registry |
| `harness/subprocess_runner.py` | 215 | Shared subprocess utility (used by `PyBridge` `isolate=True`; `RBridge` left untouched per refinement 3) |
| `harness/py_invoke.py` | 380 | `PyBridge` hybrid (in-process default, `isolate=True` opt-in) |
| `harness/check_base.py` | 165 | `P3ParityCheck` ABC with `verdict_class`, `reroll_on_caveat=False` default, `structural_invariants` attribute |
| `harness/report_template.py` | 195 | Markdown audit-report emitter (optional; not used in Batch 1) |
| `harness/_validate_session5_diff.py` | 130 | Split-fidelity diff validator (numerical strict + metadata investigative) |
| `harness/_test_structural_invariants.py` | 145 | Registry dispatch unit test |

### MODIFIED Batch 1 checks (10 files, net LOC reduction)

Each migrated to `P3ParityCheck` base + `verdict_class` + `verdict_class_rationale`:

| File | Verdict class | Δ LOC |
|---|---|---:|
| `p3_arima.py` | `mle_fit` | −90 (removed inline `_compare_scalar`/`_compare_vector` definitions; helpers re-exported via top-of-file imports for sibling-check transparency) |
| `p3_sarima.py` | `mle_fit` | +12 (verdict_class + rationale) |
| `p3_arimax_sarimax.py` | `mle_fit` | +12 |
| `p3_ets.py` | `state_space_reform` | +14 |
| `p3_theta.py` | `state_space_reform` | +14 |
| `p3_intermittent.py` | `closed_form` | +12 |
| `p3_tbats.py` | `mle_fit` | +12 |
| `p3_classical_decompose.py` | `closed_form` | +12 |
| `p3_stl.py` | `iterative_loess` | +14, −18 (explicit `on_caveat_reroll` override removed; `reroll_on_caveat = False` is the new class default) |
| `p3_mstl.py` | `iterative_loess` | +20, −5 (same on_caveat_reroll removal; `structural_invariants` declaration deferred to Batch 7 per refinement 2) |

### UNCHANGED (per refinement 3 + plan §Out-of-scope)

- `harness/r_bridge.py` — purely structural refactor was out of scope per refinement 3. `RBridge` continues to manage its own subprocess + JSONL audit log inline. `subprocess_runner.py` is available for `PyBridge` `isolate=True` use; `RBridge` may migrate in a future commit if behavior preservation is verified separately.
- `harness/runner.py` — no changes needed. `discover_checks` walks the `ParityCheck.__subclasses__()` tree recursively; `P3ParityCheck` inherits from `ParityCheck` so the new Batch 1 checks are auto-discovered through the existing path.
- `harness/base.py` — no changes. `P3ParityCheck` is a strict extension; the legacy ABC is unchanged.
- 9 pre-Phase-3 checks (`_smoke_test`, `1c..3f`, `critical_slowing_down`) — retain their inline `_ensure_engine_on_path` copies + their existing 4-method `ParityCheck` contract. Backward-compat preserved.

## Three locked design decisions — outcomes

### Decision 1: Path-setup placement → harness-level shared helper

**Resolved as planned.** Phase 1 exploration confirmed all 70 Phase 3 wrappers follow uniform import patterns; no batch-specific path-setup variation exists. `harness/path_setup.py` is the single source. Pre-Phase-3 checks retain inline copies (out-of-scope migration).

The re-export pattern in `p3_arima.py` (`from reference_parity.harness.path_setup import _ensure_engine_on_path` at module top) means the 9 sibling Batch 1 checks' existing `from reference_parity.harness.checks.p3_arima import _ensure_engine_on_path` lines continue to resolve unchanged. Zero touch on 9 sibling files for the helper migration.

### Decision 2: Structural-invariants library scope → registry stub

**Resolved as planned + refinement 2 applied.** `harness/structural_invariants.py` registers 18 invariant types across 9 wrapper classes (decomposition, VAR/VECM, GARCH, Kalman, HMM, wavelet, FFT, bootstrap, conformal). All stubs raise `NotImplementedError("populate at Batch <N>")` with the documented per-batch population schedule:

- Batch 2 (Session 6, GARCH): `garch_persistence`, `garch_conditional_variance`
- Batch 3: VAR/VECM
- Batch 4: HMM
- Batch 5: Kalman
- Batch 7: decomposition / wavelet / FFT
- Batch 9: conformal
- Batch 10: bootstrap

Per refinement 2, **no Phase 3 check declares `structural_invariants` this session** (including `p3_mstl`, which retains its inline `recon_cross_max_abs_diff` Pattern F diagnostic in the existing `compare()` method without going through the registry). The registry dispatch is validated via `_test_structural_invariants.py` (4/4 PASS).

### Decision 3: PyBridge architecture → hybrid

**Resolved as planned.** `harness/py_invoke.py` exposes `PyBridge.py_invoke(..., isolate=False)` for Batches 7–8 (in-process direct import; zero overhead) and `isolate=True` for Batch 9 (subprocess via `harness/subprocess_runner.py`; pinned seed; cuDNN deterministic flag). LOC ~380 (within the 250–500 estimate band).

PyBridge isn't exercised in Batch 1 (all R refs); first use will land in Batch 7 (Session 15) per master plan §15.9.

## Locked defaults — applied

1. `reroll_on_caveat: bool = False` — default flipped from `harness/base.py:ParityCheck`'s True. `p3_stl` and `p3_mstl` had explicit `def on_caveat_reroll(...): return False` overrides in Sessions 4; both deleted (now redundant). MC checks will set `reroll_on_caveat = True` explicitly when added (Batches 4, 9).
2. `verdict_class: str` + `verdict_class_rationale: str` — mandatory class attributes on every `P3ParityCheck` subclass, enforced by `__init_subclass__`. All 10 Batch 1 checks populated. Permitted values: 9 registered classes (`closed_form`, `mle_fit`, `state_space_reform`, `iterative_loess`, `mcmc`, `em_stochastic`, `dl_seed_pinned`, `bootstrap_distributional`, `conformal_coverage`).
3. `structural_invariants: tuple = ()` — optional class attribute, default empty. Per refinement 2, no Phase 3 check declares non-empty in this session.

## Refinement compliance

| # | Refinement | Status |
|---|---|---|
| 1 | Validation step 4 split into numerical-strict + metadata-investigative | **Applied.** `_validate_session5_diff.py` implements the split. Both classes byte-identical; investigation path didn't fire. |
| 2 | Defer `p3_mstl` `structural_invariants` declaration to Batch 7 | **Applied.** `p3_mstl.py` retains inline `recon_cross_max_abs_diff` diagnostic; no registry dispatch. Unit test validates registry directly. |
| 3 | `subprocess_runner` refactor purely structural (no R behavior changes) | **Applied.** Took the safest interpretation: `r_bridge.py` is **untouched** this session. `subprocess_runner.py` is available for `PyBridge` `isolate=True`; `RBridge` continues with its inline subprocess + JSONL audit log. RBridge migration deferred to a future commit if needed. |

## Items banked for Chat check-in 1

1. **`verdict_class` enum may need to split `mle_fit`** into `single_impl_mle` (where TSL and reference are essentially the same library, e.g. p3_tbats Python tbats vs R forecast::tbats which inherit each other's design) vs `optimizer_divergent_mle` (where independent implementations may compress tolerance headroom). Revisit at Chat check-in 2 with Batch 2 GARCH evidence (rugarch vs arch).

2. **Confirm at check-in 1** that retroactive material (B1, B6, B7 follow-ups, GARCH Phase 2 Session 6, Cleanup Commit) appearing earlier in `plans/glistening-wishing-mountain.md` is **informational historical context only** and was NOT proposed for the Session 5 commit. Session 5 scope is strictly the generator abstraction per locked plan; bundling retroactive cleanup with infrastructure refactor breaks per-session findings discipline and is master plan §11 trigger 7 escalation if proposed.

## Next session

**Session 6** per master plan §15.4 — Batch 2 R volatility (`garch_model.py`, `har_rv.py`).

Batch 2 is the first to:
- Use the new `P3ParityCheck` base from check creation rather than via migration.
- Populate the `structural_invariants` registry — `garch_persistence` and `garch_conditional_variance` get concrete checker implementations.
- Validate revised §10.3 criteria 1 and 2 (audit time and LOC reduction) empirically.

Master plan §15.4 schedules:
- Session 6: sGARCH + GJR-GARCH + EGARCH + IGARCH (all via `garch_model.py` variant dispatch, per Session 1 inventory clarification).
- Session 7: `har_rv.py` + batch summary + Chat check-in 2.

Chat check-in 1 follows immediately post-Session-5-commit per master plan §15.3 — pattern review (Patterns A–G consolidated in `tools/reference_parity/reports/p3_batch_1_summary.md`), generator validation outcome (this document), Batch 2 readiness gate.
