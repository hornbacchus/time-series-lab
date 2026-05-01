# Bond Yield Forecast Integration — Phase 4 v1.2.0 Amendment Candidates

**Date issued:** 2026-05-01 (BYF Session 5)
**Source:** Bond Yield Forecast Integration cycle (Sessions 1-5)
**Purpose:** Bank candidate amendments to the P-1/P-2/P-3/P-4
v1.1.0 doc set surfaced during BYF integration. Each candidate
is dispositioned for Phase 4 master-plan triage; nothing here
is actioned in the BYF cycle itself.

This document is a forward-provisioning artifact — Phase 4
sequencing decides which candidates promote to v1.2.0
issuance and which defer further. It is the BYF-cycle
counterpart to Phase 3.5's "Phase 4 carry-forward" block in
[`docs/reference_parity_status.md`](../reference_parity_status.md).

---

## 1. R `BVAR` (Kuschnig & Vashold) — constant-volatility cross-check

**Origin:** BYF Session 4 audit reference-selection step.

**Background.** Plan §4.1's primary candidate (R `bvars` /
Krueger 2018) was UNAVAILABLE for R 4.5.3
(`install.packages("bvars")` returns "package 'bvars' is not
available for this version of R"). Pattern A.1 self-parity +
Pattern F was selected per §4.1 fallback discipline. Result:
PASS-A.1+F (10/10 checks PASS), but the verdict explicitly
does NOT verify cross-implementation parity (see
[audit report §4.2](../../tools/reference_parity/reports/p3_bond_yield_forecast_audit.md)).

**Candidate amendment.** Investigate R `BVAR` (Kuschnig &
Vashold 2021, JSS — distinct from Krueger's `bvars`) as a
cross-implementation reference for the **constant-volatility
sub-case** (turn off TSL's stochastic-volatility component;
compare Minnesota-prior coefficient posteriors only). This is
NOT a full cross-check of TSL's BVAR-SV — `BVAR` does not
support stochastic volatility — but it would surface bugs in
the Minnesota-prior dummy-observation construction, which is
the single largest correctness risk in the wrapper.

**Tolerance class.** `mcmc` per P-1 §5.1; cross-implementation
band would be 5e-3 abs / 5e-2 rel on posterior means at
N≥10000.

**Disposition.** **Phase 4 candidate.** Resource cost: ~1
session (~250-LOC audit script + R env verification + write
report). Promotes BYF verdict from PASS-A.1+F to PASS at
inter-implementation parity for the constant-vol sub-case.

**Doc impact.** Adds a P-2 §C.4 entry (Pattern A.2 sub-case);
P-4 BYF row gains a secondary verdict line "constant-vol
sub-case: PASS-A.2 vs R `BVAR`".

---

## 2. Partial Pattern A.3 — Minnesota dummy-observation reimpl (standalone audit fragment)

**Origin:** BYF Session 4 plan §4.1 second-tier candidate;
ruled out at Session 4 as out-of-LOC-budget for full BVAR-SV
reimpl.

**Background.** A faithful from-scratch BVAR-SV reimpl
(CCM-2019 + KSC-1998 + CK-1994 + K-FS-2014) is ~1000 LOC
across 6+ modules (same order as TSL's own implementation).
The Minnesota-prior dummy-observation construction in
isolation is much smaller — ~50 LOC for the dummy-Y / dummy-X
matrix construction per Litterman 1986 + Doan-Litterman-Sims
1984 — and is the single most error-prone step in the BVAR
estimation chain.

**Candidate amendment.** Build a Pattern A.3 audit fragment
that compares TSL's `_dummy_observations_minnesota()` output
(the dummy-Y and dummy-X arrays, before any sampling step)
against a from-scratch reimpl following Doan-Litterman-Sims
1984 §3 verbatim. Strict bit-exact comparison
(`abs_tol=1e-15`); failure surfaces exact-formula deviations
in the Minnesota construction.

**Tolerance class.** `closed_form` (closed-form matrix
construction; no optimizer / sampler / MCMC noise).

**Disposition.** **Phase 4 candidate.** Resource cost: ~0.5
session. Higher value-per-LOC than candidate #1 because it
isolates the highest-risk component without requiring a full
cross-implementation env.

**Doc impact.** P-2 §D.4 (Pattern A.3 sub-case); P-4 BYF
secondary verdict line.

---

## 3. `stochvol` rpy2 partial Pattern A.2 — SV component only

**Origin:** BYF Session 4 §"Banked items".

**Background.** TSL's BVAR-SV stochastic-volatility component
follows Kim-Shephard-Chib 1998 with ASIS interweaving
(Kastner-Frühwirth-Schnatter 2014). R `stochvol::svsample`
implements an equivalent KSC sampler; Phase 1 audit 2b
already established cross-implementation parity for
standalone SV at the `mcmc` tolerance band (5% mu /
documented sigma_eta prior divergence).

**Candidate amendment.** Wire a partial Pattern A.2 audit
that extracts TSL's per-equation log-volatility posterior
means after BVAR-SV converges, then re-runs `stochvol::
svsample` on the per-equation residuals separately.
Cross-check should land within the 2b audit's tolerance
band. Distinct from candidate #1: this isolates the SV
sub-component, not the BVAR-coefficient sub-component.

**Tolerance class.** `mcmc` per the 2b audit tolerance ladder
(5% mu / 10% phi / sigma_eta record-only).

**Disposition.** **Phase 4 candidate.** Resource cost: ~0.5
session. Bridges the BYF-side h-posterior to the existing
2b audit infrastructure without re-establishing
cross-implementation env.

**Doc impact.** P-2 §C.4 (Pattern A.2); P-3 §3.4 (Pattern A.1
locked-at-scale extends to A.2 partial-component sub-cases).

---

## 4. P-2 §B.6 entry — R `bvars` if it becomes available for a future R release

**Origin:** BYF Session 4 §4.1 reference-selection
documentation.

**Background.** Plan §4.1's primary candidate is currently
unavailable. CRAN package availability is non-deterministic
across R versions; `bvars` may resurface in a future R
release (it built on R 3.6 and 4.0 historically per CRAN
archive metadata).

**Candidate amendment.** Add P-2 §B.6 catalog entry
documenting:
- The reference-availability check protocol when revisiting
  BYF audits.
- A trigger condition: if `bvars` becomes available, schedule
  a Pattern A.2 cross-check audit alongside the next major
  BYF amendment.
- The methodology-equivalence fingerprint (Krueger's
  `bvars` uses CCM-2019 with normal-Wishart prior; TSL uses
  CCM-2019 with independent normal-inverse-Wishart per
  current `_priors.py`).

**Disposition.** **Phase 4 doc-only candidate** (no audit-
script work; pure documentation amendment to P-2). Lowest
resource cost.

**Doc impact.** P-2 §B.6 single entry.

---

## 5. P-1 v1.2.0 docstring-convention amendment candidate (motivated by S4 audit-script iterations)

**Origin:** BYF Session 4 §"Mid-session corrections" — three
audit-script iterations were required before final PASS:
1. PCA loadings convention misread (`pca.components_.T` vs
   standard sklearn convention).
2. Companion-form intercept position misread (FIRST column
   per `estimation._build_lag_design line 167: X[:, 0] = 1`,
   not LAST as standard texts assume).
3. PCA roundtrip semantics — replaced "residual < 1e-10"
   invariant with "explained-variance ≥ 99%" because TSL's
   BVAR uses a TRUNCATED (3-of-10) PCA.

All three are **audit-script learning, not BVAR/wrapper
bugs.** The wrapper's internal conventions are correct; my
audit-side computations needed alignment with what the
migrated subpackage actually implements.

**Candidate amendment.** P-1 v1.2.0 docstring convention
amendment requiring wrappers with non-standard internal
conventions (PCA loadings stored transposed; design-matrix
intercept-column position; truncated decompositions where
the standard textbook formula is intentionally lossy) to
include a `Conventions` docstring section documenting:
- Storage convention (e.g., "`loadings = pca.components_.T`,
  shape (n_features, n_components), DIFFERENT from sklearn's
  `pca.components_` convention").
- Non-default semantics (e.g., "intercept stored at index
  `X[:, 0]`, not last column").
- Intentional lossiness flags (e.g., "this PCA is truncated
  3-of-10; reconstruction residual is intentionally non-zero
  per Litterman-Scheinkman 1991").

This would have prevented all three S4 audit iterations.

**Disposition.** **Phase 4 doc + light-engine candidate.**
P-1 amendment is doc-only; retro-applying the convention to
~10 wrappers across the engine for the worst offenders
(PCA-using wrappers; design-matrix wrappers with non-trailing
intercepts; truncated-decomposition wrappers) is ~100 LOC
across ~10 docstrings. Worth the cost: every future
audit-script author saves the same iteration cycles.

**Doc impact.** P-1 v1.2.0 §3.4 (output-surface discipline)
amendment; engine-side docstring backfill.

---

## 6. File / package collision protocol — formalize at C-1

**Origin:** BYF Session 2.

**Background.** Initial S2 design placed dispatch logic at
`engine/techniques/bond_yield_forecast.py` adjacent to the
`engine/techniques/bond_yield_forecast/` subpackage. Python's
import resolver picks the package over the file at the same
parent — silent shadowing, no warning. Symptom: importing
`techniques.bond_yield_forecast` returned the package
namespace; the dispatch's `run()` function was unreachable.
**Fix:** moved logic to `_dispatch.py` inside the subpackage
+ `__init__.py` re-export `from ._dispatch import run`.

**Candidate amendment.** C-1 Wrapper Development Standard
v1.0.0 (current) does not address this collision pattern. v2
candidate adds a §"Wrapper module-vs-package layout" section
mandating:
- If a wrapper has only single-file content, place at
  `engine/techniques/<id>.py`.
- If a wrapper requires multiple modules (subpackage), place
  at `engine/techniques/<id>/__init__.py` + `_dispatch.py`
  (or equivalent), and the `__init__.py` MUST re-export the
  dispatch entry point.
- NEVER co-locate `<id>.py` and `<id>/` at the same level.

The collision is silent at import time but manifests as
`AttributeError: module 'techniques.<id>' has no attribute
'run'` — diagnosable but easy to misread as a missing-export
issue when it's actually a layout issue.

**Disposition.** **Phase 4 doc-only candidate** (C-1
amendment; no engine work). Single new section in C-1 v2;
existing wrappers all conform to the rule by structural
accident (no co-located file+package pair currently exists).

**Doc impact.** C-1 v2 §"Wrapper module-vs-package layout"
(new section).

---

## 7. Sheet-naming auto-detection pattern — bank for future bundled-workbook wrappers

**Origin:** BYF Session 3 (carry-forward item A from S2).

**Background.** BYF's dispatch reads a 3-sheet `.xlsx`
workbook with an opinionated naming scheme
(`BondYield_Macro` / `BondYield_Yields` /
`BondYield_Projections`). Two operational realities collided
at S3:
1. The migrated subpackage retained the standalone repo's
   default config which assumed differently-named sheets
   (`Macro` / `Yields` / `Projections` without the
   `BondYield_` prefix).
2. The new TSL-shipped sample template uses the prefixed
   scheme to coexist with other workbook-driven wrappers
   without sheet-name collisions.

**Fix landed at S3:** `_resolve_workbook_sheet_config()`
auto-detects which scheme is in use by openpyxl-listing the
workbook's sheet names and matching against both schemes.
Falls back gracefully with a clear error if neither matches.

**Candidate amendment.** Future workbook-driven wrappers
(per the integration plan-archived discussion of yield-curve
shock decomposition + scenario-stress wrappers) will face the
same scheme-evolution problem. C-1 v2 banks the pattern as a
recommended approach for any wrapper with bundled
`.xlsx` input:
- Prefix sheet names with the wrapper's catalog ID.
- Implement an auto-detection helper paralleling
  `_resolve_workbook_sheet_config`.
- Keep the helper local to the wrapper (don't extract
  prematurely; only ~3 wrappers will have bundled-workbook
  input at most, per master-plan inventory).

**Disposition.** **Phase 4 doc-only candidate** (C-1 v2
recipe entry). Light-touch addition — does not block any
specific wrapper.

**Doc impact.** C-1 v2 §"Bundled-workbook input wrappers" or
§"Recipe collection" entry.

---

## 8. Layered-validation pattern — promote to C-1 standard

**Origin:** BYF Session 3 (carry-forward item B; re-entrancy
regression).

**Background.** S3 surfaced a re-entrancy regression: the
dispatch's pre-flight validation set state on the wrapper-
level config dict that persisted across calls in long-lived
engine_worker processes. Second invocation in the same
process saw stale validated-config and either short-circuited
validation (returning success without re-checking) or
crashed on type-mismatch when the new request differed in
shape.

**Fix landed at S3:** validation now creates a fresh local
config dict per request via `dict(config)` shallow copy,
then mutates the copy. Wrapper-level state holds nothing
that crosses request boundaries.

**Candidate amendment.** This pattern (request-local config
materialization, no cross-request state in pre-flight) is
implicit C-1 discipline but not codified. C-1 v2 candidate
adds a §"Layered validation" section formalizing:
- Pre-flight validation operates on a request-local config
  copy, never on persistent module state.
- Validation outputs flow forward via return value, not
  side-effect on outer-scope mutable structures.
- Subsequent layers (catalog-bound type coercion, range
  validation, semantic validation) each receive their own
  copy of the working config to avoid downstream-mutates-
  upstream coupling.

**Disposition.** **Phase 4 doc-only candidate** (C-1 v2
amendment). The pattern is testable via the existing
re-entrancy regression test (BYF S3 added; persists in
`tests/test_dispatch.py`); making it a standard formalizes
the discipline so other long-lived-process wrappers don't
recreate the bug.

**Doc impact.** C-1 v2 §"Layered validation" (new section);
optionally extend P-1 §pre-flight discipline cross-ref.

---

## 9. Tier classification deviation — audit-script vs production-default runtime

**Origin:** BYF Session 5 (deviation from plan §5.2's slow-
tier directive).

**Background.** Integration plan §5.1 classified BYF as
slow-tier on the basis of expected default-chain wall-clock
(~40s @ `n_draws=10000, n_burn=3000`). Session 5 measured
actual audit wall-clock at ~20s using the audit-chain config
(`n_draws=2000, n_burn=500`) — comfortably under the 30s
fast-tier ceiling. The audit was registered with
`tier="fast"` in `p3_bond_yield_forecast.py`.

**Two distinct runtimes co-exist:**
- **Audit-script runtime (~20s):** what CI parity-fast.yml
  measures and gates on. Reduced-chain config — sufficient
  for Pattern A.1 self-parity (which doesn't depend on chain
  length) + Pattern F invariants (property-level checks
  unaffected by chain length).
- **Production-default runtime (~25s on warm-JIT;
  ~22s reported in markdown perf table):** what users
  actually run via the Ribbon dropdown at default chain
  config (`n_draws=10000, n_burn=3000`). This is what the
  user-facing markdown documents.

Both fit fast-tier as currently measured. **Plan §5.1's
slow-tier classification was based on a mis-estimate of
default runtime; the actual ~22s default-config runtime is
also fast-tier.** The audit-script reduced-chain choice was
a defensive belt-and-suspenders move that turned out
unnecessary; if a future BYF amendment lifts the chain
config back toward defaults, both audit-script and
production-default fit fast-tier.

**Candidate amendment.** P-1 v1.2.0 §6.1 "Tier
classification" candidate adds a clarification:
- **CI tier classification is by AUDIT-SCRIPT runtime, not
  production-default runtime.** CI gates on what runs in CI;
  production-default runtime is documented separately in the
  user-facing markdown.
- When the two diverge significantly (audit reduced-chain to
  hit fast-tier; production runs longer), both numbers go in
  the wrapper markdown perf table.

**Disposition.** **Phase 4 doc-only candidate** (P-1
v1.2.0 amendment). Clarifies an implicit convention; doesn't
require any wrapper changes.

**Doc impact.** P-1 v1.2.0 §6.1 amendment + cross-reference
in P-2 §A.

---

## 10. Install-matrix-updates-ship-with-wrapper-addition discipline

**Origin:** BYF Session 5 + Phase 3.5 Session 6 retrospective.

**Background.** S4's CI run **failed with exit-3 ERROR** on
`p3_bond_yield_forecast` because `parity-fast.yml`'s install
line did not include `openpyxl` (a BYF dependency). The
install-matrix update landed at S5 (commit `38a5144`),
closing the gap. Phase 3.5 Session 6 surfaced the same
class of failure for `x13binary` on Linux runners.

**Pattern:** any wrapper-addition PR that introduces new
runtime dependencies MUST update both:
- `engine/requirements.txt` (engine-side runtime install).
- `tools/reference_parity/harness/MANIFEST.toml` (parity-
  harness pin).
- BOTH `parity-fast.yml` AND `parity-slow.yml` install
  matrices (the slow-tier install must mirror fast-tier
  because per Phase 3.5 S1 Item 4 protocol, all check
  classes import at runner-discovery time regardless of
  tier).

**Candidate amendment.** P-1 v1.2.0 §pre-merge-checklist
extension: "If wrapper introduces new runtime dependencies,
verify install lines updated across all 4 surfaces
(requirements.txt, MANIFEST.toml, parity-fast.yml,
parity-slow.yml × Windows job + Linux job)."

C-1 v2 cross-reference: when adding a wrapper that depends
on a non-stdlib package not already in TSL's install matrix,
the dependency-addition checklist gates the PR.

**Disposition.** **Phase 4 doc-only candidate** (P-1 + C-1
amendment). Extends Phase 3.5 Session 6 retrospective; BYF
S4-S5 is the second instance of the same failure class.
Codifying the discipline at standard-doc level prevents a
third instance.

**Doc impact.** P-1 v1.2.0 §pre-merge checklist; C-1 v2
cross-reference.

---

## Summary disposition

| # | Candidate | Type | Cost | Phase 4 priority |
|---:|---|---|---|---|
| 1 | R `BVAR` constant-vol Pattern A.2 | Audit + doc | ~1 session | Medium |
| 2 | Minnesota dummy-observation Pattern A.3 | Audit + doc | ~0.5 session | High (highest value-per-LOC) |
| 3 | `stochvol` rpy2 partial A.2 (SV component) | Audit + doc | ~0.5 session | Medium |
| 4 | P-2 §B.6 `bvars`-availability entry | Doc-only | <0.25 session | Low (trigger-when-available) |
| 5 | P-1 v1.2.0 docstring-convention amendment (incl. PCA storage / intercept position / truncation lossiness explicit annotations from S4 retrospective) | Doc + engine backfill | ~1 session | High (cycle-time savings) |
| 6 | C-1 v2 §"Wrapper module-vs-package layout" (file/package collision; S2 retrospective) | Doc-only | <0.25 session | Low |
| 7 | C-1 v2 §"Bundled-workbook input wrappers" recipe (sheet-naming auto-detection; S3 retrospective) | Doc-only | <0.25 session | Low |
| 8 | C-1 v2 §"Layered validation" (request-local config; S3 retrospective re-entrancy) | Doc-only | <0.25 session | Medium |
| 9 | P-1 v1.2.0 §6.1 tier-classification clarification (audit-script vs production-default; S5 retrospective) | Doc-only | <0.25 session | Medium |
| 10 | P-1 v1.2.0 §pre-merge install-matrix gate (S4-S5 + Phase 3.5 S6 retrospective) | Doc-only | <0.25 session | High (failure-prevention) |

**All 10 carry forward to Phase 4 master plan** — none are
actioned in the BYF integration cycle. Phase 4 sequencing
will triage these alongside any Phase 3.5 / parity-cycle
carry-forward items already documented in
[`docs/reference_parity_status.md`](../reference_parity_status.md)
§"Phase 4 carry-forward".

**Highest-priority cluster (#2, #5, #10):** these three items
share a "lessons learned codification" theme — cycle-time
savings on future audits (#5), failure-prevention on future
PRs (#10), and high-value-per-LOC cross-implementation
verification (#2). Phase 4 sequencing should consider
bundling them into an early Phase 4 documentation-amendment
session.

---

## Cross-references

- BYF integration plan §"Session 5" — directs Step 5.6 to
  surface these candidates as a discrete document.
- BYF Session 4 findings doc — original surfacing context
  for candidates #1-#3 + #5.
- [`tools/reference_parity/reports/p3_bond_yield_forecast_audit.md`](../../tools/reference_parity/reports/p3_bond_yield_forecast_audit.md)
  §5 "Banked items" — overlapping inventory; this document
  is the canonical Phase 4 forward-provisioning artifact.
- P-1 / P-2 / P-3 / P-4 v1.1.0 — current authoritative
  parity standard / diagnostic / empirical / coverage docs;
  candidates above all increment toward v1.2.0.
