# Phase 5 S2 Revert Banking — B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE

**Date:** 2026-05-05
**Origin:** Decision Q-Revert-1=(a) + Q-Revert-2=(b) halt-and-revert
of S2 sequence after CI failure regression at `f771ec6`.

## B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE — Local pre-commit gates fail to exercise CI parity-fast workflow against real TSL output

S2 sequence (5 commits `f771ec6` → `c329b83` → `54cc440` →
`4bf5939` → `f628572`) committed under Q5=b-2 resume sequence
with local pre-commit gates passing (engine/tests/ pytest
96/96; check-environment clean; install-matrix exit 0;
standalone smoke tests with synthetic invariant-satisfying
inputs PASS). All 5 commits FAILED CI parity-fast workflow
because `runner.py` step 4.5 dispatch +
`P3ParityCheck.check_invariants` lifecycle method fire
`structural_invariants` checks against REAL TSL outputs
across ALL wrappers with declared invariants — not just
kalman + johansen + evt as smoke tests synthesized. 6
wrappers BLOCKED on missing invariant fields:
- `2a_kalman_filter_smoother`: missing `filtered_state_cov`
  / `predicted_state_cov`
- `3a_caviar_sav`: missing `chris_pvalue`
- `3c_evt_ferro_segers`: missing `theta`
- `3d_johansen_bartlett`: missing rank field (tsl=None,
  ref=None)
- `3e_mint_family`: missing `coherence_residual`
- `3f_transformer_attention`: missing `attention_matrix`

Reverts (in reverse chronological order; default `git revert
--no-edit` messages preserve audit trail per B-Phase4-
S11b-1-3 discipline): `9b81510` (reverts `f628572`) +
`6b3f6af` (reverts `4bf5939`) + `dc84e4c` (reverts
`54cc440`) + `c075476` (reverts `c329b83`) + `a28036f`
(reverts `f771ec6` ROOT CAUSE). Master content-equivalent
to `5eeb752` (Path 30E pre-flight resume; CI green
CONFIRMED).

**Cross-reference:** §19 master plan v1.1 pre-commit gates
spec; `trigger_templates_v1.md` §3 test boilerplate
accounting + §6 execution-class projection multiplier
guidance + §7 recursive-pattern protection;
B-Phase5-S2-α-INFRASTRUCTURE-COLOCATION pattern reverted.

**Forward-looking:** future Phase 5 sessions require
**explicit CI green verification before subsequent commits
proceed** in resume sequences. Synthetic smoke tests
populate audit-field inputs that REAL TSL `run_tsl()`
outputs do not — the dispatch path that the runner exercises
in CI parity-fast workflow tests against real wrapper output,
not synthetic test inputs. Local pre-commit gates per §19
DO NOT exercise the runner's full dispatch path against
real TSL outputs; CI verification is the only authoritative
signal for runner integration changes that affect cross-
wrapper dispatch behavior. Path 34B-γ framework refinement
empirical validation at execution-class scope requires CI
verification, not just local gates.

## Disposition

S2 revert sequence COMPLETE (5 reverts pushed). Phase 5
HALTED per Decision Q-Revert-1=(a) + Q-Revert-2=(b).
Awaiting explicit Chat-side disposition before any further
Phase 5 work. Master HEAD at `a28036f` (content-equivalent
to `5eeb752` Path 30E pre-flight resume).
