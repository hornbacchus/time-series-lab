# Phase 5 Session 4-γ [PRE-FLIGHT] Investigation — caviar_sav engine + harness + tier + INVERTED audit (Categories 1-4)

**Date:** 2026-05-08
**Scope:** Pre-flight investigation findings (Categories 1-4)
per Q-S4-γ-preflight-overshoot=(B) 3-commit split with
standalone banking + (split-α) §1-§4 / §5-§7+disposition
categorical seam mirroring Q-S4-β-preflight-overshoot-split
precedent. Third + final per-wrapper sub-session of
heterogeneous group; INVERTED tolerance structural distinction
at §4 per B-Phase4-S9-3 codification. Synthesis findings
(Categories 5-7 + disposition) co-located at companion
synthesis doc `session_4_gamma_preflight_findings.md`.
**Status:** COMPLETE.

## §1 Engine state audit (Category 1)

**Engine module located:** `engine/techniques/caviar_quantile_dynamics.py`
(harness wrapper imports as `cqd` and calls `cqd.run(ctx, ...)`
with technique_id "caviar_quantile_dynamics" + SAV specification).

**Engine-side state audit:** Engine wrapper exposes
`christoffersen_pval` in audit_fields (line 370; rounded to 6
decimals) per Phase 4 codification + auxiliary diagnostics
(`christoffersen_stat`, `kupiec_pval`, `dq_pval`,
`n_violations`, `violation_ratio`). Christoffersen LR
independence test computed at line 158 via
`_christoffersen_test(violations, theta)` helper.

**Harness wrapper engine-call pattern:** Harness wrapper at
`tools/reference_parity/harness/checks/caviar_sav.py` calls
engine wrapper's `run()` method directly (lines 309-323) +
extracts audit_fields (line 329). Some audit_fields surfaced
to run_tsl output (`kupiec_pval`, `n_violations`,
`violation_ratio`, etc.); `christoffersen_pval` NOT surfaced.

**Engine work scope for S4-γ: ~0 LOC.** No engine modifications
required. S4-γ scope reduces to harness wrapper expansion +
allowlist addition + per-wrapper smoke test + INVERTED
semantic handling at smoke test assertion.

**No blocking issues** identified. Engine implementation
production-ready; reference (from-scratch reimpl per Q1 in
wrapper docstring; Engle-Manganelli 2004 algorithm); fixture
data (`3a_caviar_sav`) extant per Phase 1 codification.

## §2 Harness wrapper field-availability investigation (Category 2)

**Harness wrapper located:** `caviar_sav.py` (`CaviarSavParity`
class at line 250; `technique_id = "3a_caviar_sav"`;
`fixture_id = "3a_caviar_sav"`; `tier = "fast"`).

**`structural_invariants` declaration** (Phase 4 S9 dormant
declaration extant per P4-1.3 codification at lines 283-290):
- `intervals_test` invariant; `tolerance=0.05` (p-value floor);
  `tolerance_type="absolute"`

**`_check_intervals_test` checker (single-side per
`structural_invariants.py` line 1040):** Consumes
`tsl["chris_pvalue"]` (float, required; BLOCK if missing).
**INVERTED semantics:** PASS if `pvalue > floor (0.05)`;
CAVEAT if `floor/2 < p ≤ floor`; BLOCK if `p ≤ floor/2`.

**Field-availability investigation per S2-redux + S4-α + S4-β
protocol:**

`run_tsl()` (lines 338-356) currently returns dict with `beta`,
`loss`, `one_step_ahead_var`, `kupiec_pval`, `n_violations`,
etc. **Required field `chris_pvalue` NOT exposed at top level.**
Engine audit_fields contains `christoffersen_pval` (full name).

**Empirical investigation on real fixture (read-only execution):**
Computed via direct engine `run()` invocation:

| Field | Value | Disposition (vs floor=0.05) |
|---|---|---|
| christoffersen_pval | 1.0 | PASS (INVERTED: p > floor) |
| christoffersen_stat | 0.0 | aux (LR statistic) |
| kupiec_pval | 0.677587 | aux (Kupiec POF test) |
| dq_pval | 0.736036 | aux (Dynamic Quantile test) |

**Case determination:** Case (i) variant — required field NOT
exposed at run_tsl top level; engine has field under DIFFERENT
NAME (`christoffersen_pval` engine vs `chris_pvalue` checker
expected). Harness wrapper expansion required (~5-10 LOC; rename
mapping `christoffersen_pval` → `chris_pvalue` at run_tsl top
level). **Third Case (i) observation in Phase 5 sequence**
(prior at S4-α mint_family + S4-β transformer_attention per
B-Phase5-S4-β-CASE-i-CONSECUTIVE-OBSERVATION).

**Architectural decision (deferred to S4-γ execution-time
authoring):** field rename mapping is structurally simpler than
S4-α multi-method representative choice + S4-β multi-layer
representative choice. There is exactly ONE Christoffersen
p-value per wrapper run (single scalar; no aggregation needed).
Code's recommendation: direct rename `christoffersen_pval` →
`chris_pvalue` extracted from `audit_fields["christoffersen_pval"]`.
No representative-choice question.

## §3 Tier classification + parity-slow latent risk (Category 3)

**Tier classification:** `tier = "fast"` (line 262). Direct CI
parity-fast impact upon allowlist addition (mirrors S4-α
mint_family + S4-β transformer_attention scenarios; distinct
from S3 MCMC SV slow-tier).

**Parity-slow latent risk per B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK:**
N/A for fast-tier wrapper. Field VALUE satisfaction MUST be
verified pre-allowlist-add — verified per §2
(christoffersen_pval=1.0; INVERTED semantics: 1.0 > floor 0.05
trivially → PASS).

**No latent CI risk identified.** Fast-tier allowlist addition
safe given empirical field VALUE INVERTED-PASS satisfaction.

## §4 INVERTED tolerance verification (Category 4) — S4-γ STRUCTURAL DISTINCTION

Per B-Phase4-S9-3 codification: INVERTED tolerance applies to
caviar_sav. **Pre-flight VERIFIES INVERTED status from wrapper
code reading + checker code reading.**

**INVERTED status confirmed:** `_check_intervals_test` at
`structural_invariants.py` lines 1075-1080:

```python
if pvalue_f > floor:
    status = "PASS"
elif pvalue_f > floor / 2:
    status = "CAVEAT"
else:
    status = "BLOCK"
```

**Tolerance semantics:** larger p-values are PASS (opposite of
standard "smaller residuals are PASS"). Per checker docstring
(line 1060-1062): "most invariants treat smaller residuals as
PASS; here, LARGER p-values are PASS. The threshold is
interpreted as a floor, not a ceiling." Per wrapper comment
(line 281-282): "INVERTED semantics — larger p-value is the
desired outcome."

**Architectural surface assessment:**
- **Dispatch infrastructure:** passes raw `tsl_output` dict to
  lifecycle method `check_invariants()`; checker called by
  invariant_type registry lookup. Dispatch infrastructure
  **agnostic to INVERTED semantics** — handles all invariant
  types uniformly via registry dispatch.
- **Lifecycle method (`check_invariants`):** `_INVARIANT_REQUIRED_FIELDS`
  defensive check verifies field presence; `intervals_test`
  not yet registered in defensive map (see synthesis doc §6
  architectural decision). Lifecycle method itself does NOT
  need INVERTED-aware extension (handled at checker level).
- **Checker (`_check_intervals_test`):** handles INVERTED
  semantics internally via PASS-if-greater-than-floor logic.
  CAVEAT/BLOCK thresholds also INVERTED (floor/2 cutoff for
  BLOCK; opposite of standard 10× threshold pattern).
- **Smoke test semantic:** asserts PASS-deterministic where
  PASS = pvalue > floor (deterministic on real fixture per §2
  empirical pval=1.0 well above floor=0.05).

**INVERTED handling routine; no architectural concerns surface
beyond identification.** Standard per-wrapper protocol per
Q-S4-3=(α) applies; INVERTED is wrapper-specific implementation
detail handled at checker level; dispatch + lifecycle
infrastructure preserved.

**Mitigation paths N/A** — no architectural concerns surface
warranting Chat surfacing.

**§13.4 compliance:** Investigation commit delta verified at
staging time per Code's chunking judgment (3-commit cascading
split per Q-S4-γ-preflight-overshoot=(B) disposition).
