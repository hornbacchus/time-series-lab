# Bond Yield Forecast — Parity Audit Report

**Audit date:** 2026-05-01 (BYF-Mod-2 amendment)
**Audit script:** [`tools/reference_parity/harness/checks/p3_bond_yield_forecast.py`](../harness/checks/p3_bond_yield_forecast.py)
**Fixtures (TWO; BYF-Mod-2 extension):**
- `engine/techniques/bond_yield_forecast/tests/fixtures/test_input_canonical.xlsx`
  — 10-maturity legacy grid (3M, 6M, 1Y, 2Y, 3Y, 5Y, 7Y, 10Y, 20Y, 30Y);
  143 quarters × 6 BVAR variables; sha256
  `5c74081554badbdf324427c9a4457ea18b6f251e43c3b700cbead7904aaad0f3`.
- `engine/techniques/bond_yield_forecast/tests/fixtures/test_input_canonical_34mat.xlsx`
  — 34-maturity BYF-Mod-1 grid (1M, 3M, 6M, 9M, 1Y, 2Y, 3Y, 4Y, 5Y, 6Y,
  7Y, 8Y, 9Y, 10Y, 11Y..30Y); 143 quarters × 6 BVAR variables; sha256
  `dd30894f1829c0be6026778b3cb0473009267796ffcf3ea258644fa22cceedd9`.

Both fixtures use 8-quarter projection horizon and seed 20260427. The
34-mat fixture preserves the 10 anchor maturities verbatim from the
10-mat fixture and inserts 24 linearly interpolated maturities in
maturity-years space (per BYF-Mod-1 README addendum); the BVAR
variable count remains 6 (3 macro + 3 PCs) regardless of maturity
count — only the PCA-input panel width changes (10 vs 34 maturity
columns).

**verdict_class:** `mcmc` (P-1 v1.1.0 §5.1)
**Outcome:** **PASS** (20 of 20 checks PASS; 0 CAVEAT; 0 BLOCK
across both fixtures — 6 reproducibility + 4 invariants per fixture).

---

## 1. Reference selection rationale

### Plan §4.1 primary candidate (Pattern A.2): R `bvars` (Krueger)

**Status: UNAVAILABLE.** `install.packages("bvars", ...)` on R 4.5.3
returns:

```
Warning message: package 'bvars' is not available for this version of R.
Error in library(bvars): there is no package called 'bvars'
```

`bvars` is not on CRAN's R 4.5.3 binary distribution. Per integration plan
§4.1 fallback discipline ("if R `bvars` Pattern A.2 doesn't work
cleanly, do not force it"): we **do not force** the unavailable
reference.

### Plan §4.1 second-tier (Pattern A.3): self-parity paper-formula reimpl

A faithful from-scratch reimplementation of BVAR-SV (CCM-2019 +
KSC-1998 + Carter-Kohn 1994 + K-FS-2014) is approximately the same
LOC footprint as TSL's own implementation (~1000 LOC across 6+
modules at `engine/techniques/bond_yield_forecast/`). This is
materially out-of-budget for a single Session 4 audit script (~250
LOC envelope per Phase 3 batch precedent).

### Selected approach: Pattern A.1 self-parity + Pattern F invariants

Per Phase 3 precedent (`critical_slowing_down`, `p3_emd_hht`,
`p3_nar_narx` when no clean cross-reference is available), the most
honest combination is:

1. **Pattern A.1 same-implementation reproducibility self-parity.**
   Run TSL's BVAR-SV twice with identical seed; assert byte-identical
   output across all `BVARSVResults` arrays. This validates the
   deterministic-given-seed contract (numpy + numba random state
   pinning) — a necessary precondition for any subsequent
   cross-implementation work. Bit-exact across 6 array families
   (`coefficients`, `A_lower_triangular`, `log_volatilities`, `mu`,
   `omega`, `phi`) is the strict-tolerance test.

2. **Pattern F structural invariants.** Mathematical-property checks
   that hold regardless of implementation:
   - **var_companion_eig**: VAR companion-form max |eigenvalue| < 1
     (BVAR stationarity).
   - **sv_stationarity**: |φᵢ| < 1 per equation (geometric drift on
     log-volatility).
   - **pca_explained_variance**: 3-PC truncation captures ≥99% of
     yield-curve variance (Litterman-Scheinkman 1991
     level/slope/curvature decomposition).
   - **coef_finite**: posterior-mean coefficients contain no NaN/Inf.

This combination matches Phase 3's `critical_slowing_down` audit
pattern (no clean cross-reference; combined Pattern A.1 + Pattern F
verification).

---

## 2. Audit configuration

| Setting | Value | Rationale |
|---|---|---|
| Fixtures (TWO) | `test_input_canonical.xlsx` (10-mat) + `test_input_canonical_34mat.xlsx` (34-mat) | BYF-Mod-2 extended audit coverage to both legacy 10-mat and BYF-Mod-1 34-mat grids |
| Audit seed | 20260427 | Matches BVAR Session 0 fixture seed |
| `n_draws` | 2000 (reduced from default 10000) | Audit-runtime budget; reproducibility doesn't depend on chain length |
| `n_burn` | 500 (reduced from default 3000) | Same |
| Tier | fast (~17s wall-clock; 4 BVAR-SV cycles total) | Two cycles per fixture × 2 fixtures |
| `verdict_class` | `mcmc` | CCM-2019 Gibbs + KSC mixture + ASIS interweaving |
| Pattern A.1 abs_tol | 1e-15 | Machine-epsilon ceiling; bit-exact in practice |
| Pattern F invariants | Property-level (PASS / CAVEAT / BLOCK by threshold) | No tolerance band per check; thresholds documented per invariant |

---

## 3. Results — fixture_10mat (legacy)

### 3.1 Pattern A.1 reproducibility self-parity (6 arrays)

| Array | Shape | dtype | max_abs_diff | max_rel_diff | n_compared | Status |
|---|---|---|---:|---:|---:|---|
| `coefficients` | (1500, 6, 25) | f64 | **0.0** | **0.0** | 225,000 | **PASS** |
| `A_lower_triangular` | (1500, 6, 6) | f64 | **0.0** | **0.0** | 54,000 | **PASS** |
| `log_volatilities` | (1500, 139, 6) | f64 | **0.0** | **0.0** | 1,251,000 | **PASS** |
| `mu` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |
| `omega` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |
| `phi` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |

**1,557,000 elements bit-exact across two TSL invocations.** Numpy
+ numba random state is fully deterministic given the pinned seed +
JIT-cached gufunc artifacts. This is the strongest reproducibility
claim achievable: the wrapper is 100% deterministic given seed +
config.

### 3.2 Pattern F structural invariants (4 checks)

| Invariant | Measurement | Threshold | Status |
|---|---:|---:|---|
| **VAR companion-form max\|eig\|** | 0.9477 | < 0.999 PASS / < 1.0 CAVEAT | **PASS** |
| **SV \|phi\| (max across 6 equations)** | 0.9957 | < 0.999 PASS / < 1.0 CAVEAT | **PASS** |
| **PCA explained-variance ratio (3 PCs)** | 0.99910 | ≥ 0.99 PASS | **PASS** |
| **Posterior-mean coef finiteness** | 0 non-finite | 0 PASS / >0 BLOCK | **PASS** |

**SV phi posterior means per equation:**

| Variable | φᵢ posterior mean |
|---|---:|
| Real GDP Growth | 0.9957 |
| CPI Inflation | 0.9909 |
| Fed Funds Rate | 0.9588 |
| PC1 (level) | 0.8498 |
| PC2 (slope) | 0.7918 |
| PC3 (curvature) | 0.7958 |

All φᵢ < 1, confirming the SV log-volatility process is geometrically
stationary in the posterior mean. The macro variables (GDP, CPI, FFR)
are near-unit-root in volatility (φ ~0.96-0.996), which is empirically
expected for U.S. macro data — high persistence but bounded inside the
unit circle.

**VAR companion eigenvalues:** max |λ| = 0.948 across 24 eigenvalues
(6 variables × 4 lags) — BVAR posterior shrinkage produces a stable
companion form. The Minnesota prior is doing its job: shrinking
toward random-walk-with-drift while preserving stationarity.

**PCA explained variance:** 99.91% with 3 components — confirms the
Litterman-Scheinkman level/slope/curvature decomposition is appropriate
for the canonical Treasury fixture. The 3-PC truncation is
**intentionally lossy** (it's a dimension reduction, not a perfect
representation); the truncated reconstruction residual of ~0.41
(absolute, in yield units) is informational only — not a bug.

---

## 3-bis. Results — fixture_34mat (BYF-Mod-1 grid)

### 3-bis.1 Pattern A.1 reproducibility self-parity (6 arrays)

| Array | Shape | dtype | max_abs_diff | max_rel_diff | n_compared | Status |
|---|---|---|---:|---:|---:|---|
| `coefficients` | (1500, 6, 25) | f64 | **0.0** | **0.0** | 225,000 | **PASS** |
| `A_lower_triangular` | (1500, 6, 6) | f64 | **0.0** | **0.0** | 54,000 | **PASS** |
| `log_volatilities` | (1500, 139, 6) | f64 | **0.0** | **0.0** | 1,251,000 | **PASS** |
| `mu` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |
| `omega` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |
| `phi` | (1500, 6) | f64 | **0.0** | **0.0** | 9,000 | **PASS** |

**1,557,000 elements bit-exact across two TSL invocations.** Same
deterministic-given-seed contract holds on the denser 34-maturity
grid: PCA fits a different loadings matrix (3 × 34 instead of 3 ×
10), but the BVAR-SV operates on the same 6-dim panel (3 macro + 3
PCs) so post-PCA the chain dimensions are identical. Numerical
arrays match bit-for-bit between two same-seed runs on the 34-mat
input, confirming the BYF-Mod-1 sparse-column code path preserves
seed-pinning correctness on the variable-N input case.

### 3-bis.2 Pattern F structural invariants (4 checks)

| Invariant | Measurement | Threshold | Status |
|---|---:|---:|---|
| **VAR companion-form max\|eig\|** | 0.9988 | < 0.999 PASS / < 1.0 CAVEAT | **PASS** (boundary; see note) |
| **SV \|phi\| (max across 6 equations)** | 0.9956 | < 0.999 PASS / < 1.0 CAVEAT | **PASS** |
| **PCA explained-variance ratio (3 PCs)** | 0.99916 | ≥ 0.99 PASS | **PASS** |
| **Posterior-mean coef finiteness** | 0 non-finite | 0 PASS / >0 BLOCK | **PASS** |

**SV phi posterior means per equation (34-mat):**

| Variable | φᵢ posterior mean |
|---|---:|
| Real GDP Growth | 0.9956 |
| CPI Inflation | 0.9923 |
| Fed Funds Rate | 0.9404 |
| PC1 (level) | 0.7767 |
| PC2 (slope) | 0.7892 |
| PC3 (curvature) | 0.7971 |

**VAR companion eigenvalues (34-mat):** max |λ| = 0.9988 — clears
the 0.999 PASS threshold by a thin margin. This is a meaningful
empirical observation: **the 34-mat input drives the system closer
to the unit circle than the 10-mat input** (0.948 → 0.9988). The
extra 24 maturity columns enter the BVAR via the PCA factor
structure (level/slope/curvature scores derived from a 34-column
input vs 10-column input); the resulting macro+PC panel is more
strongly persistent. The companion form remains stationary
(< 1.0); the Minnesota prior continues to do its job. Worth
documenting for any future BYF-Mod cycle that materially changes
the maturity grid composition (e.g., adding maturities below 1M
or with non-uniform spacing).

**PCA explained variance (34-mat):** 99.92% — slightly HIGHER than
the 10-mat case (99.91%). Counterintuitive at first glance —
denser maturity grids typically capture LESS variance in a 3-PC
truncation because higher-frequency shape variation enters the 4th-
N PCs. Here, however, the BYF-Mod-1 sample template's 24 inserted
maturities are LINEARLY INTERPOLATED in maturity-years space
between the 10 anchor maturities (per BYF-Mod-1 README addendum);
linear interpolation does not introduce variance orthogonal to the
existing level/slope/curvature factor structure, so the 3-PC
truncation continues to capture ≥99% of the (slightly redenser)
variance. The 99% threshold remains methodologically appropriate
for both fixtures.

**B-Mod1-2 disposition:** measurement confirmed Pattern F PCA
threshold of 99% remains correct on the BYF-Mod-1 34-mat fixture.
**No threshold change.** Per BYF-Mod-2 §2.5 decision tree (≥99%
measured → keep 99% threshold). If a future BYF-Mod cycle replaces
the synthetic-interpolation 34-mat fixture with empirically-sourced
Treasury data carrying real high-frequency curve variation, this
threshold may need re-measurement.

---

## 3-ter. Combined verdict

| Fixture | Reproducibility (6 arrays) | Pattern F (4 invariants) | Overall |
|---|---:|---:|---|
| `fixture_10mat` | 6/6 PASS (1.557M elements bit-exact) | 4/4 PASS | **PASS** |
| `fixture_34mat` | 6/6 PASS (1.557M elements bit-exact) | 4/4 PASS | **PASS** |
| **Total** | **12/12 PASS (3.114M elements bit-exact)** | **8/8 PASS** | **PASS** |

### 3.3 Overall outcome

| Statuses | Count |
|---|---:|
| PASS | 10 |
| CAVEAT | 0 |
| BLOCK | 0 |
| ERROR | 0 |

**Verdict: PASS.**

---

## 4. Methodological discussion

### 4.1 What this audit verifies

- **Determinism contract:** TSL's Bond Yield Forecast pipeline produces
  bit-exact identical posteriors given the same seed + config on BOTH
  the legacy 10-maturity input and the BYF-Mod-1 34-maturity input
  (BYF-Mod-2 extension). Numba caching does not invalidate determinism
  across calls. RNG state does not leak between invocations. The
  BYF-Mod-1 sparse-column auto-detection code path preserves seed-
  pinning correctness on variable-N inputs.
- **Mathematical correctness (property-level):** the BVAR is stationary
  in companion form on both fixtures (max |λ| = 0.948 on 10-mat;
  0.999 boundary on 34-mat — the denser grid drives the system closer
  to but not beyond the unit circle, documented in §3-bis.2); the SV
  process is stationary on both; the PCA truncation preserves the
  dominant variance structure on both (99.91% on 10-mat; 99.92% on
  34-mat; threshold preserved at 99%); coefficients are finite on
  both.

### 4.2 What this audit does NOT verify

- **Cross-implementation parity.** TSL is the only implementation in
  the test. A bug shared between the two TSL invocations (e.g., a
  miscoded prior dummy, a wrong KSC mixture component) would NOT be
  caught here. R `bvars` would be the natural cross-reference but is
  unavailable for R 4.5.3. Phase 4 candidate: investigate alternative
  R packages (`BVAR`, Kuschnig & Vashold, for constant-vol comparison)
  or invest in a partial Pattern A.3 reimpl of one component (e.g.,
  Minnesota dummy-observation construction in isolation).
- **Posterior calibration.** The audit doesn't verify that the
  posterior means / credible bands are well-calibrated against held-
  out data. Calibration is a separate audit class (CAI Phase 2
  pattern) outside Phase 3 parity scope.
- **Conditional-forecast correctness.** The audit covers BVAR-SV
  estimation only; the conditional-forecast machinery
  (`ConditionalForecaster.forecast()`) is exercised end-to-end by the
  Session 2 dispatch test (Case 6) but not directly invariant-checked
  here.

### 4.3 First-instance use of DOCUMENTED-DIVERGENCE: NOT triggered

The integration plan §4.5 listed DOCUMENTED-DIVERGENCE as a possible
verdict (Phase 3.5 Session 1 wired the verdict-runtime mapping for
forward provision). It is **not triggered** by this audit:
the chosen reference strategy (self-parity) doesn't produce
methodological divergence by construction. DOCUMENTED-DIVERGENCE
remains forward-provisioned and not yet exercised at runtime in any
Phase 3 / Phase 3.5 / BYF integration audit.

### 4.4 verdict_class assignment

`mcmc` per master plan §7.1 + plan §4.2 expectation. The strict
abs_tol=1e-15 reflects what's achievable at the same-implementation
reproducibility level, not the typical mcmc inter-implementation
divergence (which would be on the order of 5e-3 abs / 5e-2 rel).
This is the appropriate band for Pattern A.1 self-parity even within
the `mcmc` class — when the two invocations are the same
implementation, bit-exactness is the right standard.

---

## 5. Banked items

| Banked | Phase 4 / Session disposition |
|---|---|
| Investigate R `BVAR` (Kuschnig & Vashold) for constant-vol cross-check | Phase 4 |
| Partial Pattern A.3: Minnesota dummy-observation reimpl as standalone audit fragment | Phase 4 |
| Conditional-forecast invariant: smoothness across maturities at each horizon | Phase 4 (deferred from §3.4 above; not added in S4) |
| Stochvol cross-check via rpy2 (BVAR `validation.py`): could be incorporated as a Pattern A.2 candidate for the SV component only | Phase 4 |
| Master plan §15.12 reference adjustments: add a P-2 §B.6 entry for BYF if R bvars becomes available in a future R release | Session 11 / Phase 4 documentation |

---

## 6. Tolerance ladder — recorded post-audit

Final tolerance ladder for `p3_bond_yield_forecast` (in
`tools/reference_parity/harness/tolerances.py`):

```python
"p3_bond_yield_forecast": {
    "type": "tiered_outputs",
    "primary": {
        "abs_tol": 1e-15,        # Pattern A.1 bit-exact
        "rel_tol": 1e-15,
        "block_abs_tol": 1e-10,
        "block_rel_tol": 1e-10,
    },
    "secondary": {
        "abs_tol": 5e-3,         # reserved for Phase 4 Pattern A.3
        "rel_tol": 5e-2,
        ...
    },
}
```

No per-metric ladder needed (all reproducibility metrics share the
machine-epsilon band; structural invariants are property-level with
no abs/rel tolerance).

---

## 7. Verdict summary line (for P-4 status tracker)

**`p3_bond_yield_forecast`** | mcmc | bit-exact (1e-15) Pattern A.1 self-parity + Pattern F invariants on TWO fixtures (10-mat + 34-mat) | fast | **PASS** | this report

---

## 8. BYF-Mod-1 / BYF-Mod-2 modification cycle effects on this audit

This audit underwent two amendments during the post-integration
modification cycle:

**BYF-Mod-1 (commit `3d15bf3`, 2026-05-01)** expanded the declarative
maturity grid from 10 to 34 maturities and added column-level sparse-
input auto-detection. The integration plan §4.5 verdict at BYF-Mod-1
close was indirectly affirmed by the unchanged 10-maturity fixture
continuing to PASS (CI run 25226399543 green) — but Mod-1 deferred
the 34-maturity audit-coverage extension and Pattern F threshold
recalibration to BYF-Mod-2.

**BYF-Mod-2 (this commit, 2026-05-01)** extends audit coverage to
both fixtures (Option A per BYF-Mod-2 §2.4 — single audit script,
single P-4 entry). Two banked findings from BYF-Mod-1 resolved:

- **B-Mod1-1** (`_dispatch.py:321` attribute mismatch): one-line fix
  swapping the primary lookup from the nonexistent `yield_names` to
  the canonical `maturity_names`. User-visible Yield Forecast table
  Maturity column now reads `treasury_3m...treasury_30y` instead of
  placeholder `Maturity_0...Maturity_N`. Verified via regression
  test in `tests/test_dispatch_maturity_names.py`.

- **B-Mod1-2** (PCA explained-variance threshold recalibration on
  34-mat grid): empirical measurement found 99.92% on 34-mat vs
  99.91% on 10-mat. Per BYF-Mod-2 §2.5 decision tree (≥99% measured
  → keep 99% threshold). **No threshold change.** Documented in
  §3-bis.2 above.

The Mod-1 modification cycle did not affect Pattern A.1 reproducibility
or Pattern F invariants on the legacy 10-maturity input — verified
via numerical-array byte-identical equivalence at Mod-1 §1.10b
(commit `3d15bf3`) and confirmed at Mod-2 §2.9.
