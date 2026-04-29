# TSL Reference Parity Standard (P-1)

**Status:** Binding for any new wrapper PR that surfaces
numerical output. Authoritative directive.

**Audience:** TSL engineers (humans + Claude Code) adding
or modifying technique wrappers, parity checks, or the
parity harness itself.

**Origin:** Distilled from Phase 3 reference-parity audit
(Sessions S2–S14, 13 sessions, 70/70 wrappers covered, 0
BLOCK, 65 PASS, 5 CAVEAT, 1 SKIP-graceful). Companion
documents:

- [Parity Diagnostic Reference (P-2)](parity_diagnostic_reference.md)
  — wrapper-class invariants registry + Pattern J quirks
  catalog (descriptive)
- [Parity Empirical Findings (P-3)](parity_empirical_findings.md)
  — Phase 3 cross-batch synthesis (descriptive; created at
  Session 17)
- [Wrapper Development Standard](wrapper_development_standard.md)
  — sister directive for engine-side wrapper code (binding;
  established at CAI Phase 2 close)

This document is **directive** ("must"). P-2 + P-3 are
descriptive ("what we found"). When this document conflicts
with P-2 or P-3, **this document wins**.

---

## 1. Purpose and Scope

### 1.1 What this standard applies to

Every parity check under
`tools/reference_parity/harness/checks/` that audits a TSL
wrapper against an external reference implementation. The
check class subclasses `P3ParityCheck` (or its
predecessor `ParityCheck` for pre-Phase-3 entries) and
declares a `technique_id`, `tier`, `verdict_class`, and
optional `structural_invariants`.

Applies to:

- New parity checks for wrappers added after Phase 3 close
  (Phase 3.5 onward).
- Significant modifications to existing parity checks
  (tolerance ladder changes, reference re-selection,
  fixture re-roll).
- Any change to the parity harness infrastructure
  (`harness/runner.py`, `harness/check_base.py`,
  `harness/r_bridge.py`, `harness/py_invoke.py`).

Does NOT apply to:

- Engine-side wrapper code (covered by
  [Wrapper Development Standard](wrapper_development_standard.md))
- Interpretation specs (`engine/interpretation/specs/`)
- Per-technique canonical-validation scripts
  (`tools/validate_*_canonicals.py`)

### 1.2 Standard tier

Items below are split into two tiers (matching
`wrapper_development_standard.md` §1.2):

- **Binding (B):** Required. PRs that fail B-tier checks
  do not merge. CI workflow `parity-fast.yml` /
  `parity-slow.yml` must catch B-tier violations.
- **Aspirational (A):** Recommended. Encourage in code
  review, but PRs may merge with A-tier exceptions if
  documented in the audit report.

The pre-merge checklist (§8) is binding in full.

---

## 2. Four-Verdict Closure Rule (B)

Every parity check **must** close at one of four verdicts.
The harness emits these as runtime outcomes; per-batch
summaries and the master tracker (P-4) classify against
the same taxonomy.

### 2.1 Verdict taxonomy

| Verdict | Runtime outcome | Meaning |
|---|---|---|
| **PASS** | `PASS` | Output matches reference within stated tolerance on stated fixtures. |
| **CAVEAT** | `CAVEAT` | Matches except in stated regime (boundary, near-singular, MC noise band, finite-sample slack). Audit report MUST document the regime. |
| **DOCUMENTED-DIVERGENCE** | `CAVEAT` (with diagnostic) | Does not match; divergence is methodology-equivalent (different optimizer convention / prior / scale / parameterization), not a bug. Audit report MUST document the methodology difference. |
| **NO-REFERENCE** | `CAVEAT` (with diagnostic) OR `SKIP` | No clean external reference exists; correlation-based proxy or self-parity used. SKIP-graceful when reference is runtime-unavailable (missing binary, package install fails). |

### 2.2 Verdict ladder per master plan §3.1

```
PASS → CAVEAT → DOCUMENTED-DIVERGENCE → NO-REFERENCE
```

A check that cannot achieve PASS must explicitly classify at
the next tier; never silently downgrade. The four-tier
ladder is exhaustive — no other verdicts are valid.

### 2.3 Empirical note (Phase 3)

**DOCUMENTED-DIVERGENCE was not encountered as a distinct
runtime outcome in Phase 3.** All methodology-equivalent
divergences either:

1. Resolved to PASS via tolerance widening + Pattern J
   catalog entry (e.g., scipy / astropy Lomb-Scargle
   normalization → alignment-via-metric resolution).
2. Resolved to CAVEAT with a regime-specific diagnostic
   note (e.g., 5 cumulative CAVEATs: STL/MSTL iterative
   LOESS, STAR / NAR-NARX optimizer divergence, EMD-HHT
   sifting-library divergence).

This is consistent with the master plan's prediction that
DOCUMENTED-DIVERGENCE would be rare. Phase 3 closure
empirically validates that the CAVEAT category absorbs the
DOCUMENTED-DIVERGENCE band in practice; **DOCUMENTED-
DIVERGENCE remains a valid verdict** for completeness but
is not actively expected.

### 2.4 SKIP-graceful runtime convention (B)

When a check's TSL backend or reference implementation
depends on a host-system binary (X-13ARIMA-SEATS), R
package with binary requirements, or otherwise non-
installable dependency, the check **must** raise
`ImportError` (or a subclass) from `run_tsl` /
`run_reference`. The harness translates `ImportError` to a
`SKIP` outcome.

**Pattern (Session 14, p3_x13 precedent):**

```python
def run_tsl(self, fixture):
    from statsmodels.tsa.x13 import x13_arima_analysis
    from statsmodels.tools.sm_exceptions import X13NotFoundError
    try:
        res = x13_arima_analysis(...)
    except X13NotFoundError as e:
        # Re-raise as ImportError so harness SKIPs gracefully.
        raise ImportError(
            f"X-13 binary not found on system PATH; "
            f"p3_x13 SKIPped: {e}"
        ) from e
    return ...
```

`SKIP` is informative-not-failing. CI exit code maps
`SKIP` → 0 (CI green) per §6.4.

---

## 3. Output-Surface Discipline (B)

Every parity check **must** classify its compared outputs
into three tiers, matching master plan §4. Tier
classification controls verdict propagation.

### 3.1 Three-tier output taxonomy

| Tier | Examples | Verdict propagation |
|---|---|---|
| **Primary** | Headline numerical outputs the user consumes (forecasts, fitted parameters, test statistics, p-values, IRF/FEVD matrices, posterior means) | **Drives** the overall outcome. Any BLOCK on Primary → check BLOCK. Any CAVEAT on Primary → check CAVEAT (unless escalated). |
| **Secondary** | Diagnostic / informational outputs (AIC, BIC, log-likelihood when not the headline metric, condition numbers, SSE, total variance) | Reported but **does not propagate** to overall outcome. Useful for diagnosing Primary CAVEAT root causes. |
| **Diagnostic** | Structural-invariant residuals (Parseval identity, eigenvalue stability, transition-matrix row sums, conformal coverage) | Verified separately via the structural-invariants registry (§4.4). Pattern F. Diagnostic CAVEAT is informative; does not propagate by default. |

### 3.2 Tolerance ladder structure (B)

Each check declares a tolerance ladder in
`harness/tolerances.py` keyed by `technique_id`. The ladder
**must** include:

- A `primary` block with `abs_tol`, `rel_tol`,
  `block_abs_tol`, `block_rel_tol`.
- (Optional) A `secondary` block with the same shape;
  typically 5–10× looser than `primary` per master plan
  §7.2.
- A `justification` field citing either the audit report
  or the master plan §7 reference for the band.

### 3.3 Tier propagation rules

- A BLOCK on `secondary` does NOT propagate to overall
  outcome. **It is reported in the metrics dict for audit
  trail visibility.**
- A CAVEAT on a `Diagnostic` (Pattern F structural
  invariant) does NOT propagate by default. The check
  author may opt-in to propagation via the invariant
  declaration if the diagnostic carries hard-fail semantics
  (e.g., conformal coverage <50% nominal indicates a real
  bug).

---

## 4. Reference Availability Tier Policy (B)

Each parity check selects a reference implementation. The
reference choice determines the tier:

### 4.1 Tier A — Canonical external reference

Reference is a widely-used external implementation of the
same algorithm (R `forecast::Arima`, scipy.signal, PyTorch
nn.LSTM, sklearn, R `urca`, R `KFAS`, R `tempdisagg`, etc.).

**Verdict expectation:** PASS at machine precision (closed-
form math) or PASS at MLE-fit band (1e-3 abs / 1e-2 rel)
per master plan §7.1.

### 4.2 Tier B — Paper-formula reimplementation

No installable reference exists OR the existing reference
implements different math (different prior, different
sampling scheme, different parameterization). Reference is
a from-scratch implementation of the algorithm directly
from the paper, inline in the check module (~30–80 LOC).

**Required discipline:**

1. The reimplementation **must** mirror TSL's recursion
   verbatim (same variable names where practical; same
   stopping criteria; same boundary handling).
2. The audit report **must** cite the paper / formula
   source (e.g., "Knapp-Carter 1976 for GCC-PHAT";
   "Adams-MacKay 2007 for BOCPD").
3. The reimplementation lives in the check module file,
   not as a separate package.

### 4.3 Tier C — NO-REFERENCE

No installable reference, no clean paper formula, OR the
algorithm class is inherently non-deterministic / non-
unique (DL hyperparameter search, EM with multiple optima,
deep neural training).

**Verdict expectation:** CAVEAT with correlation-based
proxy (Pearson correlation on output curves; cumulative-
energy curves; output-count agreement within ±1 per master
plan §5).

**Audit report MUST document:**
- Why no Tier A or Tier B reference was viable.
- The proxy metric used (e.g., "Pearson correlation on
  cumulative energy curve").
- The PASS / CAVEAT / BLOCK threshold for the proxy.

### 4.4 Self-parity audit pattern (formalized at Session 14)

**Subclass of Tier B.** When TSL's wrapper math is the
reference (because the upstream library is broadly trusted
and the wrapper's value-add is its UX surface, not the
algorithm), the reference is a direct second invocation of
the same library with identical arguments — OR an inline
reimplementation that mirrors the wrapper's recursion.

**Empirical validation (Phase 3):** 5+ wrappers resolved
this way (BOCPD, CUSUM/PH, STL+ESD, wavelet_coherence,
SSA), all achieving 0.0 abs diff. Plus 18 wrappers in the
same-library sub-class (Pattern A.1 — direct sklearn /
xgboost / lightgbm / pywt / scipy / pymc / reservoirpy /
prophet self-test).

**Self-parity catches:** wrapper-level preprocessing bugs,
parameter-resolution bugs, audit-field rounding regressions.

**Self-parity does NOT catch:** TSL-vs-canonical-
implementation methodology bugs (i.e., if TSL implements
the algorithm wrong AND the inline reimplementation also
implements it wrong, the check passes).

**Mitigation:** the audit report MUST cite the paper /
formula source explicitly. Future contributors reviewing
the report can cross-check the math against the cited
paper independently.

---

## 5. Tolerance Bands per Class (B)

Tolerance bands are class-conditional. The class is
declared via the `verdict_class` attribute on the check
subclass (mandatory per Session 5 lock).

### 5.1 verdict_class taxonomy (11 classes — locked Session 14)

| Class | Band (Primary) | Examples |
|---|---|---|
| `closed_form` | 1e-10 abs / 1e-10 rel | FFT, PCA, OLS, classical decomposition, periodogram |
| `mle_fit` | 1e-3 abs / 1e-2 rel | ARIMA, SARIMA, ARIMAX, TBATS, Theta |
| `state_space_reform` | 5e-2 abs / 1e-1 rel (widened) | ETS, structural TS |
| `iterative_loess` | 5e-2 abs / 5e-2 rel (widened; CAVEAT-acceptable) | STL, MSTL |
| `mcmc` | 5e-3 abs / 5e-2 rel (three-outcome) | SV-Gaussian, SV-Student-t (Phase 1 audits) |
| `em_stochastic` | 1e-2 abs / 5e-2 rel (widened to 0.3 / 1.0 for HMM transition matrix) | HMM, Markov-switching, DFM, EMD/HHT |
| `dl_seed_pinned` | 1e-6 abs / 1e-5 rel | LSTM/GRU, TCN, NBEATS, NHITS, autoencoder, ESN |
| `bootstrap_distributional` | (planned) | (Batch 10 used self-parity; not exercised) |
| `conformal_coverage` | 1e-12 abs (predictions); slack tolerance on coverage | conformal_intervals |
| `single_impl_mle` (S12 split candidate) | 1e-5 abs / 1e-4 rel (tightened) | (banked; 8.1+ orders headroom evidence at S7 p3_var) |
| `optimizer_divergent_mle` (S12 split candidate) | 1e-3 abs / 1e-2 rel (master plan §7.1 baseline) | GARCH family (rugarch boundary attractor) |

The `single_impl_mle` / `optimizer_divergent_mle` split is
**a candidate refinement** banked at check-in 1.5; not yet
locked. Use `mle_fit` as default until the split is
formalized.

### 5.2 §10.3 criterion 2 — three sub-criteria (locked S12)

For per-batch §10.3 reporting, criterion 2 (LOC reduction
vs Batch 1 baseline) splits by batch composition:

| Sub-criterion | Threshold | Applies to |
|---|---|---|
| **2a** | ≥50% LOC reduction | Variant-shared batches (e.g., Batch 2 GARCH variants share fixture + R-script body) |
| **2b** | ≥10% LOC reduction | Distinct-wrapper R-subprocess batches (Batch 3, 4, 5 — most refs are R-subprocess; bridge plumbing dominates per-check LOC) |
| **2c** | ≥30% LOC reduction | Distinct-wrapper Python in-process / self-parity batches (Batch 6+ once self-parity references became the dominant pattern) |

**Empirical validation:** five consecutive batches (S10
through S14) passed both criteria 1 and 2. Pattern locked
across the full Phase 3 execution.

### 5.3 Tolerance ladder change protocol (B)

A change to an existing tolerance ladder entry **must**:

1. Cite the audit report or empirical evidence justifying
   the change.
2. Be reviewed by at least one TSL maintainer in the PR.
3. Append a versioned justification line to the existing
   entry, NOT replace it. (The ladder file is the
   authoritative trail; do not rewrite history.)

---

## 6. CI Tier Classification (B)

Every check declares `tier = "fast"` or `tier = "slow"`
matching the harness's CI workflow split.

### 6.1 Fast tier

Target runtime under 10 minutes total. Includes:

- All closed-form arithmetic checks (FFT, OLS, PCA,
  periodogram, etc.)
- Cheap MLE-fit checks (ARIMA, ETS, Theta) on small
  fixtures
- Same-library self-parity DL checks (LSTM, NBEATS, etc.)
  with seed pinning + small training (3–5 epochs)
- Rolling-origin CV, bootstrap, conformal (deterministic
  given seed)

### 6.2 Slow tier

Target runtime under 30 minutes total. Includes:

- MCMC checks with full sample-count posteriors (2b, 2c
  Phase 1 audits)
- TBATS multi-component fitting on long series
- Prophet (cmdstanpy MAP fits ~2s each; pushed to slow per
  master plan §12.2)
- X-13 (when binary available)

### 6.3 skip-CI tier

Reserved. Currently empty; was reserved for any check
requiring proprietary data or licenses. None of the 76
current checks fall in this tier.

### 6.4 Exit-code policy (B)

The harness runner exit codes:

- `0` — All PASS / SKIP only → CI green
- `2` — Any CAVEAT, no BLOCK → mapped to `0` in the
  workflow YAML → CI green
- `1` — Any BLOCK → CI red
- `3` — ERROR or fatal environment mismatch → CI red

`parity-fast.yml` and `parity-slow.yml` map exit code 2 →
0 via shell logic. **CAVEAT verdicts do not fail CI.**
This is empirical lesson from Sessions 5/6 — CAVEAT is the
documented verdict for "matches except in stated regime"
per master plan §3.1; gating CI on CAVEAT would block
correct-but-non-bit-exact merges.

---

## 7. Reference-Version Pinning Protocol (B)

`tools/reference_parity/harness/MANIFEST.toml` is the
authoritative single source of truth for pinned reference
package versions across both R and Python.

### 7.1 Manifest structure

- `[r.packages]` — pinned R package versions
- `[python.packages]` — pinned Python package versions
- `[refresh.last_review]` / `[refresh.next_review]` —
  quarterly re-pin cadence (master plan §13.3)

### 7.2 Adding a new dep (B)

When a new parity check requires an installable reference:

1. Install locally; verify the check runs end-to-end.
2. Add the version pin to `MANIFEST.toml` under
   `[r.packages]` or `[python.packages]`.
3. Add the dep to `parity-fast.yml` (or `parity-slow.yml`)
   install matrix.
4. **Both the manifest pin and the CI install ship in the
   same commit as the check** (per locked discipline,
   sessions 4–6 hardening).

### 7.3 Quarterly re-pin window

Per master plan §13.3, the manifest's `next_review` field
governs a quarterly re-pin cadence. **Empirical note:**
during Phase 3 execution (Sessions 2–14), `next_review`
fired during batch execution without scheduled action. The
batches continued under the original pin set without
issue. Re-pinning cadence will be revisited in **Phase 3.5
or as part of P-4 (status tracker) maintenance**;
out-of-scope for P-1.

---

## 8. Pre-Merge Checklist for New Wrappers — Parity Dimension (B)

Every PR adding a new TSL wrapper or significantly
modifying an existing one **must** satisfy the following
parity-dimension checklist. PRs that fail any item do not
merge.

### 8.1 Required artifacts

- [ ] **Parity check class** subclassing `P3ParityCheck`
      lives at
      `tools/reference_parity/harness/checks/p3_<wrapper>.py`.
- [ ] `verdict_class` declared (one of the 11 classes from
      §5.1).
- [ ] `verdict_class_rationale` declared (1–3 sentences
      citing why this class fits the wrapper).
- [ ] `tier` declared (`"fast"` or `"slow"`).
- [ ] `structural_invariants` declared if applicable
      (Pattern F; see P-2 for the registered invariant
      types).
- [ ] Tolerance ladder entry in
      `harness/tolerances.py` with `justification` field
      citing the audit report.

### 8.2 Required documentation

- [ ] Per-wrapper audit report at
      `tools/reference_parity/reports/p3_<wrapper>_audit.md`.
      Format: see existing reports for the lean template
      (verdict, reference, key metrics, fixture, diagnostics,
      Pattern J entries if any).
- [ ] Status tracker entry in
      `docs/reference_parity_status.md` under the relevant
      batch's coverage matrix.
- [ ] Per-batch summary updated if this is the last
      wrapper in a batch
      (`tools/reference_parity/reports/p3_batch_<N>_summary.md`).

### 8.3 Required CI state

- [ ] CI green on `parity-fast.yml` (if `tier="fast"`) OR
      `parity-slow.yml` (if `tier="slow"`).
- [ ] CAVEAT verdict permitted; CAVEAT exit-code maps to
      CI green per §6.4.
- [ ] BLOCK verdict NOT permitted; if a check produces
      BLOCK, root-cause investigation is required before
      merge.

### 8.4 Required cross-references

- [ ] Pattern J catalog entry in
      `docs/engineering/parity_diagnostic_reference.md`
      Appendix B if the check surfaces a new reference-
      library quirk (e.g., parameter-name swap, default-
      flip across versions, normalization-convention
      mismatch).
- [ ] Engine-side wrapper standard
      ([wrapper_development_standard.md](wrapper_development_standard.md))
      compliance independently verified (separate dimension;
      this checklist covers parity only).

---

## 9. Cross-Reference to Wrapper Development Standard (C-1)

The
[Wrapper Development Standard](wrapper_development_standard.md)
governs the **engine-side wrapper code** (parameter
allowlists, error-response shape, audit-field schema,
interpretation-spec compliance, Tier 14/15 / T14 / T15
contract checks). It established at CAI Phase 2 close (28
audit sessions, 88 findings, 5 dominant failure modes
fixed).

This document (P-1) governs the **parity-dimension only**
— how the wrapper is verified against an external
reference implementation. Both standards are binding for
new wrappers; they cover orthogonal concerns:

| Dimension | Standard |
|---|---|
| Parameter allowlist gates, error-response shape, audit-field schema, interpretation-spec contract | [Wrapper Development Standard](wrapper_development_standard.md) |
| Reference selection, tolerance bands, verdict closure, CI tier classification, manifest pinning | **This document (P-1)** |

When a PR fails one or both, neither merges. The two
standards do not conflict; they're additive.

---

## 10. Empirical Additions Phase 3 Surfaced

The following operational defaults are based on Phase 3
empirical evidence and are now binding on new checks:

### 10.1 Pattern A.1 (same-library audit pattern) as default for new Python wrappers

When the TSL wrapper invokes a single Python library
primitive (sklearn, xgboost, lightgbm, scipy, pywt,
PyEMD, reservoirpy, prophet, etc.) with seed-pinning
discipline, the **default reference is a direct
in-process invocation of the same library** with identical
arguments.

**Empirical validation:** 18 wrappers achieved 0.0 abs
diff via this pattern (Pattern A.1 sub-class):

- Batch 6: p3_pelt
- Batch 7: p3_periodogram, p3_wavelet_transform
- Batch 8: p3_random_forest, p3_gradient_boosting,
  p3_xgboost, p3_lightgbm, p3_svr, p3_quantile_regression
- Batch 9: p3_lstm_gru, p3_tcn, p3_nbeats, p3_nhits,
  p3_autoencoder, p3_esn, p3_gp, p3_prophet
- Batch 10: p3_loess

**Decision rule for new wrappers:** if the wrapper uses a
single Python library AND the library is broadly trusted,
use Pattern A.1. Don't invent a cross-package reference
when the wrapper is a UX surface around the canonical
implementation.

### 10.2 Self-parity audit pattern for Tier B/C resolution

When no Tier A reference is viable (no installable canonical
implementation exists, or the candidate references implement
different math), use a from-scratch paper-formula
reimplementation inline in the check module (~30–80 LOC).

**Empirical validation (5+ wrappers):**

- p3_bocpd (Adams-MacKay 2007 NIG-conjugate)
- p3_cusum_page_hinkley (identical recursion)
- p3_stl_esd (statsmodels STL + Rosner 1983 GESD)
- p3_wavelet_coherence (CWT-based smoothed coherence)
- p3_ssa (Golyandina-Zhigljavsky 2013)
- p3_gcc_phat (Knapp-Carter 1976)
- p3_transfer_function (distributed-lag OLS)
- p3_block_bootstrap, p3_forecast_combination,
  p3_rolling_origin_cv (deterministic loops)

### 10.3 PyBridge: subprocess-isolation only post-Session 13

`PyBridge.py_invoke` retired its `isolate=False` shim at
Session 13. **PyBridge is now subprocess-isolation-only**
(`isolate=True` for stateful PyTorch/etc. references). For
in-process Python references, **use direct import** — the
established Pattern A.1 path.

```python
# WRONG (post-S13): isolate=False raises PyBridgeError
bridge = PyBridge()
out, _ = bridge.py_invoke(my_ref, fixture, isolate=False)

# RIGHT (Pattern A.1):
def run_reference(self, fixture):
    from sklearn.ensemble import RandomForestRegressor
    rf = RandomForestRegressor(...)
    rf.fit(...)
    return {"preds": rf.predict(...)}
```

**Empirical evidence:** 0/14 wrappers used the
`isolate=False` shim across Batches 7+8; 0/9 used it in
Batch 9; 0/11 used it in Batch 10. The shim was retired
because no production check needed it.

### 10.4 CAVEAT exit-code → CI green policy

Per Sessions 5/6 retro: CAVEAT verdicts MUST NOT fail CI.
The harness emits exit code 2 for CAVEAT-only runs; the
workflow YAML maps exit 2 → 0 via shell `if`-block. CAVEAT
is the documented verdict for "matches except in stated
regime" per master plan §3.1; gating CI on CAVEAT would
block correct-but-non-bit-exact merges.

This is implemented in `parity-fast.yml` and
`parity-slow.yml`. Do not modify.

---

## 11. Trigger Candidates (carried from Sessions 5/6 retro)

The following CI-failure patterns warrant root-cause
investigation regardless of their apparent cause:

### Trigger 8 candidate — "CI failure on previously-passing local check"

**Symptom:** A check passes locally on the developer's
machine but fails in CI.

**Likely root causes:**
- Package version drift between local and CI environment
  (typically the CI image has older / newer minor versions
  than the developer's local install)
- OS-specific behavior (Windows-only path issues; Linux-
  only timing assumptions)
- Workflow YAML drift (e.g., missing dep added locally but
  not pinned in `MANIFEST.toml` / install matrix)

**Required action:** fix-only commit before subsequent
session work. Do NOT batch the fix with new feature work.
Add the missing pin to `MANIFEST.toml` AND the install
matrix in the same commit.

### Trigger 9 candidate — "CI failing across multiple consecutive sessions"

**Symptom:** CI workflow has been red across 2+ consecutive
session pushes; root cause not yet identified.

**Required action:** root-cause investigation regardless of
cause attribution. Open a dedicated "CI red triage" commit
that:

1. Re-runs the failing check locally with the exact CI
   environment (matching Python / R versions).
2. Diffs the local install vs the CI install matrix.
3. Adds missing pins / install entries to fix the failure.
4. Documents the root cause in
   `tools/reference_parity/reports/_ci_triage_log.md` (new
   file) with date, symptom, root cause, fix.

**Empirical evidence:** Sessions 4-6 had 3 consecutive CI
failures (missing `pmdarima`, `arch`, exit-code 2 mapping
bug). Resolved at commit `fd91dc7`. Trigger 9 was not
formalized at the time; this section formalizes it.

---

## 12. Document Maintenance

This document is **directive**. Changes must:

1. Be reviewed by at least one TSL maintainer.
2. Cite empirical evidence from a Phase 3 (or later) audit
   report or session-findings doc.
3. Append a versioned section to the change log below; do
   not silently rewrite directive sections.

### 12.1 Change log

| Version | Date | Author | Change |
|---|---|---|---|
| 1.0.0 | 2026-04-29 | Claude Code (Phase 3 Session 15) | Initial directive issued. Distilled from Phase 3 batch-execution (S2–S14, 70 wrappers, 0 BLOCK). |

---

**End of Parity Standard P-1 v1.0.0.**
