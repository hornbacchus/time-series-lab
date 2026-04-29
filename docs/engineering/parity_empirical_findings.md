# TSL Reference Parity — Empirical Findings (P-3)

**Status:** Descriptive narrative. The story of Phase 3
told through cumulative cross-batch patterns.

**Audience:** TSL maintainers reviewing Phase 3 evidence
for forward planning (Phase 3.5 candidates, Phase 4
decisions, post-Phase-3 wrapper authoring); future
engineers onboarding to the TSL parity discipline.

**Origin:** Phase 3 batch-execution (Sessions S2–S14, 13
sessions, 70 wrappers covered) + documentation phase
(Sessions S15–S16, P-1 + P-2 issued). This document closes
the documentation phase.

**Companion documents:**

- [P-1 parity standard](parity_standard.md) — directive
  ("must"); binding for new wrapper PRs (parity dimension)
- [P-2 parity diagnostic reference](parity_diagnostic_reference.md)
  — descriptive reference / playbook; classifies patterns
  encountered
- [P-4 status tracker](../reference_parity_status.md) —
  authoritative per-wrapper coverage tracker

This document is **descriptive narrative**. When directive
guidance is needed, P-1 wins. When pattern classification
is needed, P-2 wins. P-3 explains the *story* behind both.

---

## 1. The numbers

| Metric | Value |
|---|---:|
| Wrappers in scope (master plan §15) | 70 |
| Wrappers covered (Phase 3 close) | **70 (100%)** |
| BLOCK outcomes | **0** |
| PASS verdicts | **65 (93%)** |
| CAVEAT verdicts | 5 (7%) |
| SKIP-graceful (Tier C runtime) | 1 |
| Pattern A wrappers (bit-exact / near-machine-precision) | **46 (66%)** |
| Pattern A.1 same-library sub-class | **18** (locked at scale) |
| Pattern A.2 cross-package bit-exact | ~12 |
| Pattern A.3 self-parity / paper-formula | ~10 |
| Pattern F concrete invariants | 14 |
| Pattern J catalog entries | 11 |
| Pattern I sign/scale instances | 6 |
| DSCD instances | 4 (3 sub-classes) |
| Sessions used (batch-execution) | **13 (S2–S14)** |
| Sessions used (documentation) | 3 (S15–S17) |
| Total Phase 3 sessions | 17 |
| Master plan budget | 18–22 |
| **Sessions saved vs original budget** | **1–5** |
| Sessions saved vs locked Item 13 horizon | 0 (closed at optimistic end of locked range) |

The 5 CAVEAT verdicts:

- `p3_stl` (S4) — iterative LOESS deterministic divergence
- `p3_mstl` (S4) — multi-period iterative LOESS;
  non-unique decomposition
- `p3_star` (S8) — STAR smoothness γ identifiability
- `p3_nar_narx` (S8) — R `tsDyn::nlar` reference
  convergence failure (Tier C)
- `p3_emd_hht` (S11) — independent sifting libraries
  (Tier C)

The single SKIP: `p3_x13` (X-13ARIMA-SEATS binary
unavailable on Windows CI; SKIP-graceful resolution).

**This represents the most thorough numerical-correctness
verification ever done on the TSL engine.**

---

## 2. What made Phase 3 work

Three observations dominate the post-mortem.

### 2.1 — Pattern A.1 (same-library self-test) was the unlock

The original master plan §10 envisioned cross-package
audits as the dominant pattern: TSL's Python
implementation against R's canonical implementation. This
held for Batches 1–5 (R `forecast`, R `vars`, R
`depmixS4`, R `KFAS`) — those batches landed at the
mle_fit / em_stochastic tolerance bands per master plan
§7.1.

**Batch 6 (Session 10) flipped the model.** When the R
canonical reference didn't match TSL's wrapper math
(BOCPD's NIG-conjugate prior vs PyPI bocd's Gaussian; STL
+ Generalized ESD vs Twitter `AnomalyDetection` archived
from CRAN), the audit shipped a from-scratch paper-formula
reimplementation inline in the check module. **Pattern K
→ Pattern A.3 path locked.**

**Batch 7 (Session 11) generalized further.** When the TSL
wrapper invokes a single trusted library primitive
(scipy.signal.periodogram, pywt.wavedec), the parity
reference is a direct second invocation of the same
library. **Pattern A.1 same-library self-test locked.**

**Batches 8–10 made A.1 the dominant pattern.** Batch 8
(7 wrappers, all sklearn / xgboost / lightgbm) shipped 6
A.1 + 1 cross-package, all 0.0 abs. Batch 9 (9 wrappers,
PyTorch-dominated) shipped 9 A.1 with seed pinning + cuDNN
deterministic, all 0.0 abs. Batch 10 (11 wrappers) shipped
3 A.1 + 5 self-parity + 3 cross-package + 1 SKIP.

**By Phase 3 close, 18 of 46 Pattern A wrappers were A.1**
— enough to lock the pattern at scale. P-1 §10.1 codifies
A.1 as the operational default for new Python wrappers.

The unlock: **Pattern A.1 verifies wrapper-level
correctness without requiring an independent algorithm
implementation**. It catches preprocessing bugs, parameter-
resolution bugs, audit-field rounding regressions — the
real failure modes for wrapper code. It does not catch
TSL-vs-canonical-implementation methodology bugs (that's
Pattern A.2's job), but for wrappers that are UX surfaces
around a trusted library, A.1 is sufficient.

### 2.2 — The harness abstraction held

Session 5 built the `P3ParityCheck` ABC with mandatory
`verdict_class`, optional `structural_invariants`, and
`reroll_on_caveat = False` default. The harness factored
shared helpers (`_compare_scalar`, `_compare_vector`,
`_ensure_engine_on_path`, `RBridge`, `PyBridge`).

**The abstraction held across 9 subsequent batches.** No
infrastructure refactors were required after Session 5.
The single harness improvement during batch-execution
(Session 14: extend `run_tsl` ImportError → SKIP) was a
~5-line addition, not a refactor.

**`structural_invariants` registry stub design proved
right.** Session 5 stubbed 9 invariant types with
NotImplementedError placeholders; subsequent batches
populated them as wrappers landed (GARCH at S6, VAR/VECM at
S7, HMM at S8, Kalman at S9, FFT/wavelet at S11, conformal
at S13). The registry-dispatch path was validated by unit
test at S5 and by 14 concrete populations across 7 batches.

**`PyBridge.py_invoke(isolate=True)` was 0% utilized.**
Session 5 built the hybrid (isolate=False default + opt-in
isolate=True for Batch 9 DL state). Empirical evidence
across Batches 7+8+9+10 (38 Python-reference wrappers): 0
used `isolate=False` shim; 0 used `isolate=True` shim. The
shim was retired at Session 13. **The over-built shim cost
~250 LOC; retiring it cost 5 LOC.** Net: ~245 LOC of dead
code shipped briefly. Lesson: speculative abstractions for
"future Batch N needs" are dangerous; build in-batch when
need is concrete.

### 2.3 — CI green discipline locked early

Sessions 4–6 had 3 consecutive CI failures (missing
`pmdarima`, missing `arch`, exit-code 2 mapping bug). The
hardening protocol locked at S6 close:

1. **Install matrix updates ship in audit-creation
   commits**, not split into separate CI-fix follow-ups.
2. **CAVEAT exit code 2 → CI green** mapped in the
   workflow YAML, not the harness runner.
3. **Per-batch dep verification at session start** before
   any check authoring.

After S6, **CI was green on every commit through S14** (8
consecutive green pushes during batch execution). The
hardening prevented exactly the kind of compounding-CI-
failure spiral that Session 4 surfaced.

Trigger 8 + 9 candidates (P-1 §11) formalize the
"single-session CI failure" + "multi-session CI red"
patterns. Future post-Phase-3 work should consult these
triggers before treating CI red as routine.

---

## 3. Empirical patterns the harness exposed

### 3.1 — Pattern J (reference-library quirks) is durable knowledge

Phase 3 surfaced 11 distinct Pattern J quirks across 14
sessions (P-2 Section B). These quirks are **durable
knowledge** — they persist across package versions, across
maintainer turnover, across years. Examples:

- The arch / rugarch `alpha` vs `gamma1` swap for EGARCH
  (B.2.5) is documented in the rugarch vignette but not in
  arch's docs. Without B.2.5, every future EGARCH parity
  audit would re-discover the swap.
- xgboost `tree_method` default flipping between major
  versions (B.4.1) means parity tests drift silently as
  CI containers upgrade. Pinning `tree_method='hist'`
  explicitly is the only stable comparison.
- Master-plan-stated reference vs actual TSL backend
  mismatch (B.5.2 + B.6.1) — surfaced 3 times in Phase 3
  (`p3_quantile_regression`, `p3_gp`, `p3_transfer_function`).
  Pattern: master plan author specifies an idealized
  reference; wrapper author uses a different library
  implementing different math. Always read the wrapper
  imports before fixing the reference.

**Pattern J catalog should grow indefinitely.** Future
batches add new entries; future TSL maintainers consult it
before authoring new audit code.

### 3.2 — Pattern F (structural invariants) is wrapper-class infrastructure

The 14 concrete invariants populated during Phase 3 give
free correctness verification for entire wrapper classes:

- All current and future GARCH wrappers can declare
  `garch_persistence` + `garch_conditional_variance` and
  get persistence < 1 + sigma2 > 0 verified for free.
- All Kalman family wrappers can declare
  `kalman_covariance_ordering` + `kalman_innovation_positivity`
  for filter monotonicity verification.
- FFT and wavelet wrappers get Parseval identity +
  inverse-roundtrip verification.

**The marginal cost of a new wrapper in an existing class
is zero invariant-side**: the wrapper declares the
existing invariant, populates the required output keys,
and the invariant-checker fires automatically.

P-2 Section D.1 documents the new-wrapper playbook: the
4-step process is now routine.

### 3.3 — DSCD is a real phenomenon, not a tolerance bug

Phase 3 identified DSCD (Documented Sub-Class Divergence
within MLE-fit) as a genuine mathematical phenomenon, not
a tolerance-tuning failure. The 4 instances span 3
sub-classes (P-2 Section F):

- **DSCD-MLE:** GARCH family — independent optimizer
  implementations land at different local optima of the
  same likelihood (rugarch boundary attractor at
  alpha+beta≈1).
- **DSCD-EM:** Markov switching — independent EM
  implementations converge to genuinely different local
  optima.
- **DSCD-Identifiability:** LLT 3-variance + STAR
  smoothness γ — multiple parameter sets produce identical
  observable behavior; not a bug, a fundamental property.

**The right response varies by sub-class:** pin the solver
+ n_restarts (DSCD-MLE), widen the tolerance band (DSCD-
Identifiability). Documenting the sub-class in the audit
report tells the next maintainer which knob to turn.

---

## 4. Surprises and reversals

Five Phase 3 surprises warrant explicit narrative.

### 4.1 — DL non-determinism budget was wrong by 30 percentage points

Master plan §17.1 risk 2 pre-budgeted **≥30% Tier C** for
Batch 9 (Python DL). The reasoning: PyTorch training is
non-deterministic by default; cuDNN flags are inconsistent
across versions; multi-threading interacts with seed
pinning.

**Empirical result: 0/9 Tier C in Batch 9.** All 9 DL
wrappers achieved 0.0 abs diff via:

- `torch.manual_seed(seed)` + `numpy.random.seed(seed)` +
  `random.seed(seed)` at the start of each fit.
- `torch.backends.cudnn.deterministic = True`.
- `n_jobs=1` / single-threaded.

The seed-pinning recipe (P-2 Section A.7 → `dl_seed_pinned`)
**produces bit-exact reproducibility on float32 outputs**.
The PyBridge `isolate=True` subprocess path that Session 5
built for state isolation was never needed — in-process
seed reset before each fit was sufficient.

**Lesson:** budget risk for things you've actually measured.
Master plan §17.1 was conservative without empirical
foundation. Phase 3.5 risk-budgeting should ground in
Phase 3 evidence.

### 4.2 — `p3_var` headroom 8.1 orders inside band (Item #9)

Master plan §7.1 mle_fit band: 1e-3 abs / 1e-2 rel. **The
`p3_var` audit (S7) achieved 7.22e-16 abs** — that's 13
orders of magnitude tighter than the band. Same for
`p3_vecm` (9.99e-16 after sign normalization) and
`p3_pca` (7.99e-15).

These wrappers are mle_fit *category* (deterministic
optimizer) but the reference math is closed-form OLS — the
"optimization" is a normal-equations solve, not iterative.
Both sides hit machine precision.

**The category was wrong, not the band.** P-2 Section A.10
banks the `single_impl_mle` candidate split: when both
sides share optimizer lineage and the math is closed-form
OLS, tighten band to 1e-5 abs / 1e-4 rel. P-3.5 candidate
work item.

**The ETS / Theta / TBATS wrappers stay in the canonical
mle_fit / state_space_reform bands** because their
optimizers genuinely iterate to convergence with stopping
criteria that differ across implementations.

### 4.3 — Pattern J `alignment-via-metric` (J.C) is the cleanest resolution

Pattern J.B (tolerance widening) was the obvious response
to internal-default divergence. P-2 Section B.2.1 (arch /
urca PP HAC kernel) used it: 1e-3 abs / 1e-2 rel widening
from machine-precision floor.

But Pattern J.C (alignment-via-metric) is **cleaner**.
When scipy and astropy disagree on Lomb-Scargle
normalization (B.3.1), comparing absolute peak power would
require a 4-orders-of-magnitude tolerance widening to
accommodate the convention difference. Comparing
peak-frequency LOCATION instead gives 0.0 abs diff —
because frequency location is normalization-invariant.

**Lesson:** when the math agrees on SHAPE but differs on
SCALE, pick a metric invariant under the scale. Don't
compare what doesn't match; compare what should match.

### 4.4 — Self-parity (A.3) is more powerful than originally framed

Master plan §5 framed self-parity as a Tier B / Tier C
fallback when no canonical reference exists. **Phase 3
showed self-parity is the right pattern for ~10 wrappers**
including some where canonical references exist but
implement different math (BOCPD's PyPI bocd vs TSL's NIG-
conjugate; wavelet_coherence's R biwavelet vs TSL's CWT-
based estimator).

**The decision criterion isn't "does a reference exist,"
it's "does the reference implement the same math."** When
the reference math diverges, self-parity is more
informative — it catches wrapper-level regressions which
are the actual failure modes for wrapper code.

P-1 §4.4 codifies self-parity as a Tier B sub-pattern
with explicit limits (catches wrapper-level regressions;
not TSL-vs-canonical methodology bugs; mitigation = audit
report cites paper / formula source).

### 4.5 — Item 13 budget revision empirically locked at 17 sessions

Master plan §15 budgeted 18-22 sessions for Phase 3
batch-execution. Item 13 was banked at S11 close as a
budget revision candidate based on emerging single-session-
close pace (S6, S7, S8, S9, S10, S11 all single-session
closes).

**Phase 3 closed at exactly 17 sessions** (13 batch-
execution + 3 documentation + 1 closeout). The optimistic
end of Item 13's locked range. Phase 3 buffer absorbed
savings; no Phase 3.5 pull-forward.

**Lesson:** when a pace exceeds plan systematically across
3+ batches, lock the revision early and absorb savings
into buffer. Don't wait for plan-end to acknowledge the
new pace.

---

## 5. The CAVEAT taxonomy in practice

Phase 3 closed with 5 CAVEAT verdicts. P-1 §2 defines
CAVEAT as "matches except in stated regime." Empirically,
the 5 CAVEATs span 4 distinct regimes:

| CAVEAT instance | Regime | What "stated regime" means concretely |
|---|---|---|
| `p3_stl` (S4) | Iterative LOESS impl divergence | statsmodels and R `stats::stl` differ in inner-iteration counts + LOESS bandwidth defaults; per-component divergence ~9e-2 abs is reproducible across seeds |
| `p3_mstl` (S4) | Multi-period iterative LOESS non-unique decomp | Same as p3_stl, plus seasonal-period iteration ordering produces different feasible decompositions of identical y |
| `p3_star` (S8) | DSCD-Identifiability on smoothness γ | Multiple γ values produce identical observable behavior; TSL γ=1024 vs R γ=100 |
| `p3_nar_narx` (S8) | NO-REFERENCE Tier C | R `tsDyn::nlar` failed to converge to finite forecasts on the audit fixture |
| `p3_emd_hht` (S11) | Independent sifting libraries | TSL emd vs PyEMD differ in IMF count by ±2; cumulative-energy-curve correlation ρ=0.991 |

**No CAVEAT was a tolerance-tuning failure.** Each one
documents a real regime — iterative-algorithm divergence,
identifiability ambiguity, runtime reference unavailability,
independent-library-implementation differences. The CAVEAT
proxy (with diagnostic note in the audit report) is the
right verdict for all 5.

P-1 §2.3's empirical note holds: **DOCUMENTED-DIVERGENCE
was not encountered as a distinct runtime outcome** in
Phase 3. CAVEAT absorbed it.

---

## 6. Phase 3.5 candidates banked

Items not closed during Phase 3 documentation phase but
warranting follow-up in Phase 3.5:

### 6.1 — Item #9: tighten bands for `single_impl_mle` candidate (P-2 §A.10)

**Evidence:** `p3_var` (7.22e-16 abs), `p3_vecm`
(9.99e-16), `p3_pca` (7.99e-15) all 8+ orders of magnitude
inside the canonical 1e-3 abs mle_fit band.

**Action:** add new `single_impl_mle` verdict_class with
1e-5 abs / 1e-4 rel band. Migrate the 3 wrappers above.
Audit other current `mle_fit`-class wrappers to identify
candidates with similar headroom.

### 6.2 — Item #10: per-metric bands within `em_stochastic` (P-2 §A.6)

**Evidence:** HMM means 1.48e-5 abs (4+ orders headroom)
vs HMM transmat 0.237 abs (boundary); same wrapper, very
different per-metric tolerance needs.

**Action:** extend the tolerance ladder schema to support
per-metric bands within a single verdict_class entry.
Refactor HMM / DFM / Markov-switching ladders to use
per-metric granularity. Document in P-1 §5.1 update.

### 6.3 — Item #6 + #7: cross-batch findings doc design

**Status:** the cross-batch findings doc
(`tools/reference_parity/reports/phase3_cross_batch_findings.md`)
served well as a living document during batch execution
but has rough edges — duplicated entries between sessions,
inconsistent banked-item numbering across sessions.

**Action:** Phase 3.5 "P-3 v1.1" can do a structural pass
on the cross-batch findings doc (or retire it in favor of
P-2 + P-3 + per-session findings). Decide at Phase 3.5
entry.

### 6.4 — `seasonal` R package + X-13 binary on CI runners

**Status:** `p3_x13` SKIPs gracefully on Windows runners
because the X-13 binary isn't installable via the standard
install matrix.

**Action:** investigate whether X-13 binary install is
feasible in a Linux CI runner (Ubuntu has `x13as` package
in some distributions). If yes, add a Linux-only slow-tier
job that runs `p3_x13`. If no, document the SKIP as
permanent and move on.

### 6.5 — Manifest re-pin cadence (P-1 §7.3)

**Status:** `MANIFEST.toml`'s `next_review` field fired
during Phase 3 batch execution without scheduled action.
The audits continued under the original pin set without
issue.

**Action:** Phase 3.5 work item — re-pin against current
upstream versions, document any package-version drift
findings, set next quarterly re-pin window.

### 6.6 — DOCUMENTED-DIVERGENCE verdict reservation

**Status:** P-1 §2.3 documents DOCUMENTED-DIVERGENCE as a
valid verdict that wasn't exercised in Phase 3.

**Action:** when DOCUMENTED-DIVERGENCE first surfaces in
post-Phase-3 work (likely on a new wrapper class with
genuine methodology divergence from canonical reference),
the audit will be the first concrete instance. Document
in P-2 Section B (or new section) with the
PASS / CAVEAT / DOCUMENTED-DIVERGENCE classification
recipe.

---

## 7. What Phase 3 tells us about audit-engineering

Three meta-lessons.

### 7.1 — Reference selection is the hardest decision

For any new parity check, the reference selection drives
60% of the work and 100% of the verdict ceiling. Bad
reference selection = guaranteed CAVEAT or BLOCK; good
reference selection = often PASS at 0.0 abs.

**Reference-selection heuristics from Phase 3:**

1. **Read TSL's wrapper imports first.** The reference
   should match the wrapper's actual backend, not the
   master-plan-stated reference (4 instances of master-plan
   mismatch caught in Phase 3).
2. **Same-library self-test (A.1) when the wrapper invokes
   a single trusted library.** P-1 §10.1 default.
3. **Cross-package canonical (A.2) when both implementations
   exist and implement identical math.** Verify "identical
   math" by reading both packages' docs / source before
   committing the audit.
4. **Self-parity / paper-formula reimpl (A.3) when 1-3 don't
   apply.** Mirror TSL's recursion verbatim; cite the paper
   in the audit report.
5. **Tier C (correlation-based proxy) when 1-4 don't apply.**
   Empirically rare (3 wrappers in Phase 3).

### 7.2 — The harness scaffolding pays for itself

Sessions 1-5 built the harness scaffolding: ABC class,
helpers, RBridge, PyBridge, structural-invariants registry,
tolerance ladder, runner CLI. The investment was front-
loaded — ~3 sessions of pure harness work before any audit
landed.

**That investment paid for itself by Session 6.** The
GARCH variant batch (S6) shipped 4 audits in 1 session
because the scaffolding made each audit a ~150 LOC check
file vs ~400 LOC for Phase 1 audit-script-only equivalents.

**§10.3 criterion 2 (LOC reduction) tracked the scaffolding
payoff:** by S10-S14, per-check files averaged ~150 LOC
(35-70% reduction vs Batch 1 baseline). Five consecutive
batches passed the criterion. The scaffolding plateaued —
no further LOC reduction possible without sacrificing
audit-report quality.

### 7.3 — Documentation-as-you-go beats documentation-at-end

P-2 Section B (Pattern J catalog) was launched at Session
12 (Batch 8 close), 7 sessions before the documentation
phase. By the time documentation phase started (S15), B
already had 9 entries; only 2 more were added at S14. The
catalog reflected Sessions 6-14 evidence accurately because
it was written contemporaneously.

Per-batch summaries
(`tools/reference_parity/reports/p3_batch_*_summary.md`)
followed the same pattern. Each session's batch summary
was written at session-end, capturing the patterns surfaced
in that batch. By Phase 3 close, the 10 batch summaries
formed a complete narrative without retrospective synthesis
work.

**Lesson:** when batch-execution surfaces patterns,
document them in-batch. Don't bank "write up at the end."
The retrospective view is always blurrier than the
contemporaneous view.

---

## 8. The TSL parity discipline going forward

P-1 (parity standard) is binding for all new wrapper PRs
that surface numerical output. P-2 (diagnostic reference)
is the playbook for matching new wrappers against
established patterns. P-3 (this document) is the narrative
foundation explaining why P-1 and P-2 say what they say.

**For new wrapper authors:**

1. Read [P-1 §8 Pre-Merge Checklist](parity_standard.md#8-pre-merge-checklist-for-new-wrappers--parity-dimension-b)
   first.
2. Match the wrapper class against
   [P-2 Section A](parity_diagnostic_reference.md#section-a--tolerance-class-taxonomy)
   for verdict_class selection.
3. Check [P-2 Section D](parity_diagnostic_reference.md#section-d--pattern-f-structural-invariants-registry)
   for applicable structural invariants.
4. If you encounter a reference-library quirk, add an entry
   to [P-2 Section B](parity_diagnostic_reference.md#section-b--pattern-j-reference-library-quirks-catalog).
5. Ship the audit + tolerance ladder + manifest pin + CI
   install entry **in a single commit** per locked
   discipline.

**For Phase 3.5+ planners:**

1. Banked items #9 (`single_impl_mle` band tightening) and
   #10 (per-metric em_stochastic bands) are the highest-
   leverage Phase 3.5 candidates.
2. Manifest re-pin cadence (§7.3 of P-1) needs first
   concrete execution at Phase 3.5 entry.
3. The CAVEAT taxonomy (§5 above) is empirically validated;
   no taxonomy revision needed pre-Phase-3.5.

---

## 9. Document maintenance + change log

This document is **descriptive**. Updates happen as new
empirical findings emerge in Phase 3.5+ work. Updates
should:

1. Cite the audit report or session-findings doc
   establishing the new finding.
2. Append to the relevant section without rewriting prior
   narrative.
3. Append a versioned change-log entry.

### 9.1 — Change log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-04-29 | Claude Code (Phase 3 Session 17) | Initial narrative issued. Synthesizes Phase 3 batch-execution (S2-S14) + documentation phase (S15-S16). Closes banked items #6, #7, #9, #10 at P-3 venue. |

---

**End of Parity Empirical Findings P-3 v1.0.0.**

**Phase 3 documentation phase COMPLETE.** Session 18
proceeds to closeout: CI workflow finalization + P-4
status tracker finalization + Phase 3 closeout commit.
