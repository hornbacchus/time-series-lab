# Phase 6+ Session 1 banking — structural invariant parameter-aware exclusion mechanism (architectural amendment closing Phase 5 disposition (5) MCMC ess BLOCK)

**Date:** 2026-05-09
**Origin:** Phase 6+ Session 1 redrafted trigger after Code's
VERIFICATION-FIRST PROTOCOL surfaced premise errors in the
original coupled-fix trigger (slow-linux g++ provisioning + MCMC
ess BLOCK closure). Chat ratified Code's verification findings +
redrafted as architectural amendment Framing B (parameter-aware
exclusion at checker-family level). Sub-session executes 3-commit
sequence; this banking entry at Commit 3 (END) codifies the
amendment as Phase 6+ inheritance asset + establishes the Phase 6+
banking locus at NEW `docs/reference_parity_phase6/` directory.

## B-Phase6-S1-STRUCTURAL-INVARIANT-PARAMETER-AWARE-EXCLUSION — Parameter-aware exclusion mechanism for structural invariant checker family + sigma_eta non-gating wrapper opt-in + disposition (5) closure pattern

At Phase 5 close, MCMC ess BLOCK persisted on `2b_mcmc_sv_gaussian`
+ `2c_mcmc_sv_student_t` parity-slow real fixtures
(B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING +
B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK). Bridge findings
doc disposition (5) catalogued options (ess_min threshold
adjustment / chain length increase / sampler tuning / accept BLOCK
as parity-slow async backlog / suppress notification + defer)
without pre-committing path. Phase 6+ Session 1 selects
**architectural amendment path** addressing root discipline gap:

**Discipline gap identified at Phase 6+ Session 1 verification:**
- Parity-side `ess_min_check` is parameter-aware: declares
  `gates_outcome_for: ["mu", "phi"]` excluding sigma_eta from
  outcome gating (returns INFO not BLOCK on sigma_eta-only
  breach)
- Structural invariant `_check_mcmc_convergence` was NOT
  parameter-aware: blanket BLOCK on any ess_min < threshold/2
  regardless of which parameter (sigma_eta or mu/phi/nu)
- BLOCK propagation cascade: structural invariant BLOCK →
  omnibus BLOCK → workflow failure on parity-slow runs that
  the parity-side check correctly classified as INFO

**Root cause of mixing pathology:** Gibbs sampler sigma_eta
posterior exhibits lag-1 autocorrelation ~0.98 (pathological
mixing); ess on sigma_eta consequently low (~10-30 range)
regardless of chain length or seed. PyMC NUTS on AR-state-space
formulation forced via monkey-patch in
`tools/reference_parity/harness/checks/mcmc_sv_gaussian.py`
(lines 210-217) for parity-reference comparison; produces same
sigma_eta mixing pathology because it is intrinsic to the
factorized parameterization. Parity-side wisdom recognizes
sigma_eta is an inference-secondary parameter (volatility
process variance) where mu (level) and phi (persistence) gate
the substantive inference; sigma_eta breach is informational
not blocking.

**Amendment mechanism (Commit 1 `acebb96`):**

(a) `StructuralInvariant` dataclass extended at
`tools/reference_parity/harness/structural_invariants.py`:
```
non_gating_params: tuple = ()
```
Default empty tuple preserves prior strict-gating semantic
(backward-compat for non-opted-in wrappers + future wrappers
not requiring exclusion).

(b) `_check_mcmc_convergence` consumes `ess_min_param` from
tsl payload + applies non_gating_params exclusion: when
ess_min_param ∈ non_gating_params and raw status would be
BLOCK or CAVEAT, downgrade to PASS. Audit fields populated:
- `ess_status_raw`: original status before exclusion (always
  preserved for forensic analysis)
- `non_gating_param_excluded`: name of excluded param when
  exclusion applied; None otherwise

(c) Wrapper-side opt-in at `mcmc_sv_gaussian.py` +
`mcmc_sv_student_t.py`: structural_invariants tuple updated
to include `non_gating_params=("sigma_eta",)` with rationale
comment cross-referencing parity-side `ess_min_check.gates_outcome_for`
discipline. Other 6 allowlist wrappers (kalman, johansen, evt,
mint_family, transformer_attention, caviar_sav) unchanged;
default empty tuple preserves prior strict-gating.

**Verification (Commit 2 `906177e`):**

3 synthetic input tests at `_test_s2_alpha_invariants_dispatch.py`:
1. `test_mcmc_convergence_non_gating_param_exclusion_sigma_eta`
   — sigma_eta breach + non_gating_params=("sigma_eta",) →
   raw BLOCK downgraded to PASS; audit fields populated
2. `test_mcmc_convergence_block_preserved_on_non_excluded_param`
   — defensive: mu breach + same non_gating_params → BLOCK
   preserved; exclusion is parameter-targeted not blanket
3. `test_mcmc_convergence_default_no_exclusion_preserves_strict_gating`
   — backward-compat: default empty non_gating_params → BLOCK
   preserved; pre-Phase-6+ semantic intact

Existing 14 dispatch tests preserved; net dispatch test total: 17
(14 baseline + 3 synthetic).

**Pre-commit gates clean across both Commits 1+2:** pytest 106/106
PASS; parity-fast --check-environment PASS; 17 dispatch tests PASS;
parity-fast tier overall=CAVEAT (prior baseline; p3_var aic/bic
BLOCK pre-existing; MCMC SV runs slow-tier only).

**Cross-references** (per (mit-ii) brief):
- `B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING` +
  `B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK` at
  `../reference_parity_phase5/s3_execution_banking.md` (Phase 5
  empirical findings + latent risk this amendment closes)
- Bridge findings doc disposition (5) at
  `../reference_parity_phase5/phase_6_inheritance_preparation_findings.md`
  §3 (Phase 5 inheritance disposition catalog; this banking
  entry codifies path selection)
- Commit 1 `acebb96` (mechanism: dataclass extension + checker
  parameter-aware logic + 2b/2c wrapper opt-in)
- Commit 2 `906177e` (3 synthetic tests verifying mechanism)
- Commit 3 (this entry; banking codification + Phase 6+ banking
  locus establishment)
- Parity-side `ess_min_check.gates_outcome_for` discipline at
  parity-side check definition (parameter-aware exclusion
  precedent this amendment mirrors at structural invariant
  family)

**YAGNI scope discipline at this sub-session:** Parameter-aware
exclusion mechanism applied to `_check_mcmc_convergence` ONLY at
this commit; not generalized to other structural invariant
checkers (closed-form deterministic / INVERTED orthogonality
families) absent empirical demand. Future sub-sessions may extend
the mechanism if discipline gap surfaces in another checker
family; mechanism design supports extension via `non_gating_params`
tuple field consumption pattern.

**Forward-looking — parity-slow workflow trigger verification
PENDING:** Manual parity-slow workflow trigger at next user
disposition will verify disposition (5) closes empirically:
sigma_eta ess breach should now produce PASS or CAVEAT (not
BLOCK) at omnibus aggregation; underlying ess_min still surfaced
in audit + raw status preserved for forensic. Empirical closure
confirmed → disposition (5) SHIPPED. Empirical persistence of
BLOCK (unexpected; would indicate ess_min_param payload missing
from wrapper output OR aggregation pipeline bug) → re-open
investigation at next sub-session.

**Phase 6+ banking locus established:** This banking entry
inaugurates `docs/reference_parity_phase6/` directory as Phase 6+
banking locus per chat-instance-seam recalibration institutional
pattern (Phase 5 closeout + bridge findings doc disposition
deferred Phase 6+ banking directory creation to first Phase 6+
substantive sub-session). Phase 6+ subsequent sub-sessions extend
this directory; framework reference doc §4 banking pointer index
extension to include Phase 6+ entries deferred to Phase 6+ Chat
disposition (per inheritance asset preservation discipline; do
not back-edit Phase 5 framework reference doc absent recalibration
agenda).

## Disposition

Phase 5 disposition (5) MCMC ess BLOCK closure mechanism shipped
at Phase 6+ Session 1 via architectural amendment (parameter-aware
exclusion at structural invariant checker family). Mechanism +
tests + banking codified at Commits 1+2+3 (`acebb96` + `906177e` +
this commit). Parity-slow workflow empirical closure verification
PENDING manual trigger at next user disposition. Phase 6+ banking
locus established at NEW `docs/reference_parity_phase6/` directory.
