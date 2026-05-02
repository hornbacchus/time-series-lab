# Phase 4 Session 8 — P4-1.2 Kalman/VECM engine audit-field expansion

**Date:** 2026-05-02
**Scope:** Phase 4 master plan §15 S8 — engine-side audit-field
expansion to surface preconditions for the structural-invariants
registry's Kalman covariance-ordering + VECM rank-invariance
checkers (concrete since Phase 3 Sessions 7-9; idle for lack of
audit-field surface).
**Status:** COMPLETE.

## What changed

### `engine/techniques/kalman_filter.py` + `kalman_smoother.py`

Both wrappers now expose three new `audit_fields` keys:

| Field | Source | Shape | Purpose |
|---|---|---|---|
| `filtered_state_cov` | `fit.filtered_state_cov` | (T, k, k) | One-step posterior covariance per t |
| `predicted_state_cov` | `fit.predicted_state_cov` | (T, k, k) | Predictive covariance per t |
| `smoothed_state_cov` | `fit.smoothed_state_cov` | (T, k, k) | Two-sided smoothed covariance per t |

Wrapped in `try/except` so any statsmodels API drift downgrades
gracefully — fields default to `None` rather than failing the
whole run. `np.asarray(...).tolist()` conversion ensures
JSON-serializable output (matches existing audit-field
convention for tensor surfaces).

These three fields satisfy the precondition for the
`kalman_covariance_ordering` invariant (`structural_invariants.py:373`,
populated at Phase 3 Session 9) — specifically the three-way
recursive covariance contraction property
P_{t|t-1} ≥ P_{t|t} ≥ P_{t|T}.

### `engine/techniques/johansen_cointegration.py`

Two new `audit_fields` keys (both alias the existing `trace_rank`
value):

| Field | Equivalent to | Purpose |
|---|---|---|
| `determined_rank_trace` | `trace_rank` | Master-plan-mandated name (§15 S8) |
| `cointegrating_rank` | `trace_rank` | Registry-checker-expected name (`vecm_cointegration_rank` checker reads this key per `structural_invariants.py:241`) |

Both fields are alias-redundant by design for backward
compatibility — `trace_rank` continues to work for any existing
consumer; the two new aliases bridge the master plan name +
registry contract.

### `engine/tests/test_interpretation_contract.py`

T14 fixture additions:
- Kalman section (`_MINIMAL_INPUT`, line ~1808): three new
  None-defaulted keys (`filtered_state_cov`,
  `predicted_state_cov`, `smoothed_state_cov`).
- Johansen section (`_MINIMAL_INPUT`, line ~1513): two new
  integer keys (`determined_rank_trace=1`, `cointegrating_rank=1`)
  matching the existing `trace_rank=1` value.

T15 allowlist additions: 5 new chained-underscore tokens (Kalman
×3 + Johansen ×2) added to the (c8) Follow-up 2a allowlist
group with `(c8b)` and `(c8c)` sub-comments. The chained-
underscore form is already disqualified by the T15 regex's
adjacent-underscore lookaround; allowlisting keeps intent
explicit per established defensive-allowlist discipline.

## §11.8 trigger investigation (NOT crossed)

Per S8 trigger discipline ("schema-breaking changes to
P3ParityCheck or its audit-field consumers would escalate. If
the new audit_fields require schema migration in ways the audit
harness doesn't already support, surface to Chat before
proceeding"):

**No schema migration needed.** All three new Kalman fields
(plus two Johansen aliases) are additive — `audit_fields` is a
free-form `dict[str, Any]` and consumers read fields via
`.get()` calls. No `P3ParityCheck` API change. No existing
audit-field consumer breaks. Existing tests + parity audits
remain bit-exact (verified post-edit on Kalman + Johansen
canonical fixtures: PASS at 3.6e-7 abs / 0.0 abs respectively).

§11.8 trigger NOT crossed. Single session.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ 96 passed (T14 + T15 updates land cleanly) |
| `parity-fast --check-environment` clean | ✅ |
| `2a_kalman_filter_smoother` parity audit | ✅ PASS (bit-exact unchanged: 3.64e-7 abs vs KFAS) |
| `3d_johansen_bartlett` parity audit | ✅ PASS (bit-exact unchanged: 0.0 abs on Bartlett factor) |
| Numerical-array preservation on canonical fixtures | ✅ verified on both Kalman + Johansen audits |

## S9 preparation — MCMC diagnostic field-coverage catalog

Per S8 trigger heads-up ("S9 will wire inherited wrappers to
declare invariants. The mcmc_convergence omnibus pattern means
some wrappers may compute only ess_min while others have full
{ess_min, rhat_max, geweke_max_abs_z}"):

| Inherited wrapper | `ess_min` | `rhat_max` | `geweke_max_abs_z` | S9 wiring approach |
|---|---|---|---|---|
| `stochastic_volatility.py` | ✅ exposed (line 649; via `_sv_mcmc.py` diagnostics dict) | ✅ exposed (line 647) | ❌ NOT exposed | Declare with all 3; geweke=None will skip check (PASS contribution per S7 omnibus design) |
| `bond_yield_forecast/_dispatch.py` (BVAR-SV) | ❌ NOT in audit_fields top-level | ❌ NOT exposed | ❌ NOT exposed | S9: extract from `BVARSVResults.convergence_diagnostics()` DataFrame; surface min/max across param groups |

**S9 implementation note:** the BVAR-SV inner sampler computes
per-parameter-group Geweke z-scores via `convergence_diagnostics()`
(produces a DataFrame with mean/std/geweke_z/ess columns) but
does not elevate min/max statistics to top-level `audit_fields`.
S9 needs to add 3 lines extracting `ess_min`, `rhat_max`,
`geweke_max_abs_z` from this DataFrame into the BYF dispatch's
audit_fields output.

The S7 `mcmc_convergence` omnibus design correctly handles the
partial-coverage case: `rhat_max=None` and `geweke_max_abs_z=None`
are treated as PASS contribution (skip-the-check), so wrappers
exposing only `ess_min` get a meaningful single-criterion
verdict. This validates B-Phase4-S7-2 — the omnibus design
choice was the right call for the diversity of MCMC-wrapper
diagnostic surface coverage.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `engine/techniques/kalman_filter.py` | Add 3 new audit_fields entries with try/except guard | +33 |
| `engine/techniques/kalman_smoother.py` | Mirror the same 3 audit_fields entries | +27 |
| `engine/techniques/johansen_cointegration.py` | Add 2 alias audit_fields entries (determined_rank_trace + cointegrating_rank) | +14 |
| `engine/tests/test_interpretation_contract.py` | T14 fixture additions (Kalman ×3 + Johansen ×2) + T15 allowlist additions (5 tokens) | +24 |
| `docs/reference_parity_phase4/session_8_findings.md` | NEW (this file) | ~150 |
| **Total** | | **~250 LOC** |

Engine-only LOC (kalman_filter + kalman_smoother + johansen +
test): ~98 LOC. Within master plan estimate (~80-120 engine + ~30
test).

## v1.2.0 amendment ledger update

S8 contributes to the P-2 v1.1.x → v1.2.0 ledger per master plan §15.1:

- **P-2 §C.5/§C.6 NEW** Kalman covariance-ordering audit-field
  schema documentation (~25 LOC; pending S12 issuance).
- **P-2 §C.5/§C.6 NEW** VECM rank-invariance audit-field alias
  documentation (~15 LOC; pending S12 issuance).

Accumulated v1.2.0 amendment LOC at S8 close:
- P-1: ~75 (S1 §8.5)
- P-2: ~175 (S4 §C.3/§C.4 + S5 §C.2 + S6 §C.2 + S7 §C.5/§C.6 + S8 §C.5/§C.6)
- P-3: ~55 (S5 §3.4 + S6 §3.4)
- C-1: ~50 (S1 §4.6)
- **Total: ~355 LOC** (under §11.11 ceiling 600)

## Disposition

| Item | Pre-S8 status | Post-S8 status |
|---|---|---|
| P4-1 (structural_invariants on 12 inherited wrappers) | partial: registry done | **PARTIAL** — registry done; engine fields done; S9 wires inherited wrappers + O-2 tightening |
| 13-item inheritance register | 6.67 open + 6.33 closed | **6.33 open + 6.67 closed** (P4-1 2/3 progress) |
| Phase 4 cycle progress | 7 of 13 sessions complete | **8 of 13 sessions complete** (62%) |
| Engine pytest baseline | 96/96 PASS | 96/96 PASS preserved |
| Kalman + Johansen parity audits | PASS | **PASS preserved bit-exact** |

## Banked observations from S8

**B-Phase4-S8-1 — Audit-field alias pattern.** Johansen now
exposes `trace_rank`, `determined_rank_trace`, and
`cointegrating_rank` — three names for the same value. This is
cosmetic redundancy for compatibility (master plan name +
registry contract + backward compat). For Phase 5 / v1.2.0
refinement: consider deprecating `trace_rank` in favor of the
canonical `determined_rank_trace` once a deprecation window
passes (or vice versa, depending on which name P-2 §C catalog
canonicalizes). Informational; no immediate action.

**B-Phase4-S8-2 — BYF diagnostics elevation.** S9 needs to
extract `ess_min` / `rhat_max` / `geweke_max_abs_z` from
`BVARSVResults.convergence_diagnostics()` into BYF's top-level
`audit_fields`. This is ~5 LOC additive engine work; not in S8
scope (master plan §15 S8 covers Kalman + VECM only). Banked
for S9 to action alongside the wrapper-wiring work.

## Next session

**S9 — P4-1.3 wire 12 inherited wrappers + O-2 Pattern F
tightening.** Per master plan §15 S9: declare
`structural_invariants` tuples on the 12 inherited wrappers
that match the now-populated registry. Specifically:
- `stochastic_volatility.py`: declare `mcmc_convergence` invariant
- `bond_yield_forecast/_dispatch.py`: extract `ess_min` etc.
  per B-Phase4-S8-2; declare `mcmc_convergence` invariant
- `evt_pot_gpd.py`: declare `evt_extremal_index` invariant
- `forecast_reconciliation.py`: declare `mint_coherence` invariant
- `transformer_forecast.py`: declare `attention_normalization`
  invariant
- `caviar_quantile_dynamics.py`: declare `intervals_test`
  invariant
- `kalman_filter.py` / `kalman_smoother.py`: declare
  `kalman_covariance_ordering` invariant (now S8-enabled)
- `johansen_cointegration.py`: declare `vecm_cointegration_rank`
  invariant (now S8-enabled)

Plus O-2 Pattern F tightening: companion max\|eig\| PASS
threshold from <0.999 to <0.9995 (early-warning band; <1.0
still BLOCK). ~150 LOC + tests.

**§11.8 trigger remains ACTIVE** for S9.
