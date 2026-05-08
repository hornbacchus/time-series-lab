# Phase 5 Session 4-γ [PRE-FLIGHT] Synthesis — caviar_sav smoke semantic + allowlist context + execution scope (Categories 5-7 + disposition)

**Date:** 2026-05-08
**Scope:** Pre-flight synthesis findings (Categories 5-7 +
disposition) per Q-S4-γ-preflight-overshoot=(B) 3-commit split
+ (split-α) §1-§4 / §5-§7+disposition categorical seam.
Investigation findings (Categories 1-4) co-located at companion
investigation doc `session_4_gamma_preflight_investigation.md`.
Synthesis references investigation findings; reader should
consult both docs for complete pre-flight scope. Standalone
banking commit (recalibration V2 + mitigation activation) at
companion banking findings doc per (structure-γ).
**Status:** COMPLETE.

## §5 Smoke test semantic determination (Category 5)

Per B-Phase5-S3-SMOKE-TEST-SEMANTICS-INVARIANT-CLASS-DIVERGENCE:

`caviar_sav` `verdict_class = "mle_fit"` — this is the PARITY
verdict class (CAViaR-SAV uses Nelder-Mead optimization on
non-smooth quantile loss; multiple local optima per Engle-
Manganelli 2004 + Phase 1 audit B9). The STRUCTURAL INVARIANT
`intervals_test` is a separate check on Christoffersen LR
independence test (deterministic statistical test on VaR
violations given fitted CAViaR-SAV model output).

**INVERTED interaction with smoke test semantic:** smoke test
asserts PASS-deterministic where PASS = pvalue > floor.
Empirical investigation (companion investigation doc §2)
confirms pval=1.0 (well above floor 0.05); deterministic per
Christoffersen LR test on real fixture. **Distinct dimension
from closed-form-deterministic vs MCMC-stochastic
bifurcation:** INVERTED tolerance semantic is orthogonal to
smoke test class semantic; smoke test PASS-deterministic still
applies (deterministic outcome; just INVERTED comparison
direction).

**Smoke test semantic for structural invariant: closed-form
deterministic (INVERTED comparison).** PASS-deterministic
assertion appropriate per S2-redux + S4-α + S4-β closed-form
pattern; INVERTED interaction handled at checker level (smoke
test asserts on `r["status"] == "PASS"` outcome regardless of
underlying comparison direction).

## §6 Allowlist addition decision context (Category 6)

Context for S4-γ execution allowlist addition decision:
- **Field availability:** Case (i) variant; harness wrapper
  expansion ~5-10 LOC required (rename mapping
  `christoffersen_pval` → `chris_pvalue` at run_tsl top level)
- **Tier classification:** fast-tier; direct CI parity-fast
  impact (mirrors S4-α + S4-β)
- **Field VALUE satisfaction:** verified empirically
  (christoffersen_pval=1.0; PASS per INVERTED 1.0 > floor 0.05)
- **Smoke test semantic:** PASS-deterministic per closed-form
  structural invariant class (INVERTED comparison handled at
  checker; orthogonal to smoke test class semantic)
- **INVERTED architectural surface:** routine identification;
  no concerns surface; dispatch + lifecycle infrastructure
  preserved
- **Architectural decision:** field rename mapping (no
  representative-choice question; single scalar value per
  wrapper run)
- **Optional:** `intervals_test → ("chris_pvalue",)` defensive
  map entry at check_base.py would mirror analog defensive
  layer at S2 trio + S3 wrappers; Q-S4-3=(α) standard per-
  wrapper protocol delegates to execution-time decision per
  "DO NOT modify check_base.py" precedent at S3/S4-α/S4-β;
  deferred to S4-γ execution authoring + Chat disposition if
  surface warrants

## §7 S4-γ execution scope determination (Category 7)

**S4-γ envelope projection** under no-engine-work scope + Case
(i) variant harness expansion:

| Class | Projection |
|---|---|
| Implementation (allowlist + harness rename mapping) | ~6-13 LOC |
| Tests (per-wrapper smoke + 8-wrapper allowlist gating update) | ~25-30 LOC |
| Findings doc | ~30-50 LOC |
| Banking (per Q-banking-categorical strict) | 0-100 LOC depending on surfacings (third-consecutive Case (i) candidate; INVERTED interaction empirical observation candidate) |

**Combined estimate: ~60-195 LOC** — clean per §13.1 default
200 LOC by 2-70% headroom (banking-heavy upper bound engages
marginal-tolerance band; cascading split pre-authorized at
marginal band per recalibration banking).

Per B-Phase5-Q-OVERSHOOT-EXECUTION-RECALIBRATION baseline
~200-260 LOC upper estimate; S4-γ may land within or below
recalibrated upper bound; **S4-γ execution serves as
recalibration verification opportunity** per V1 banking
forward-looking sub-item (c).

**Critical empirical-validation envelope assessment:** S2-redux
+ S3 + S4-α + S4-β sequence empirical record (12/12 prior-
session commits clean with cascading-split discipline at
marginal-tolerance band engagement; per-wrapper field-
availability protocol validated at trio + pair + single-wrapper
× 2 scope across Cases 0/(i)/(iii)) supports S4-γ projection
accuracy.

**Per-wrapper default applies:** S4-γ single sub-session per
caviar_sav. After S4-γ execution closes + CI green, **sub-
domain (i) per-wrapper integration COMPLETE** (8-wrapper
allowlist active across 3 invariant classes: closed-form
deterministic + MCMC stochastic + INVERTED tolerance per
S4-γ).

**§13.4 compliance:** Synthesis commit delta verified at
staging time per Code's chunking judgment.

## Disposition

S4-γ [PRE-FLIGHT] audit COMPLETE (investigation + synthesis +
recalibration V2 banking + mitigation activation across 3
commits). Investigation surfaced (per companion investigation
doc):
- Engine work scope: 0 LOC (engine `christoffersen_pval` field
  pre-existing per Phase 4 codification)
- Harness wrapper expansion: Case (i) variant; ~5-10 LOC for
  rename mapping
- Field VALUE satisfies INVERTED invariant tolerance trivially
  (christoffersen_pval=1.0; PASS deterministic on real fixture)
- Tier classification: fast-tier; direct CI parity-fast impact
- INVERTED tolerance: confirmed; handled at checker level;
  dispatch + lifecycle infrastructure preserved; no
  architectural concerns surface
- Smoke test semantic: PASS-deterministic per closed-form
  invariant class (INVERTED orthogonality preserved)
- Third Case (i) observation in Phase 5 sequence (heterogeneous
  group default = Case (i) hypothesis empirically validated at
  3/3 sub-sessions); banking codification deferred to S4-γ
  execution if Code judges substantive

S4-γ execution trigger ahead per Chat dispositions pending
post-pre-flight closure per established discipline. After S4-γ
execution closes + CI green, **sub-domain (i) per-wrapper
integration COMPLETE.** S5 cross-wrapper acceptance trigger
ahead per master plan v1.2 §15 S5 framing; S5 trigger drafting
follows S4-γ execution closure per established cycle-wide
protocol.
