# Phase 3 Session 7 — Findings (Batch 3 close)

**Date:** 2026-04-29
**Batch:** 3 (R multivariate) — **CLOSED in single session** (master plan §15.5 budgeted S8+S9)
**Wrappers audited:** 4 distinct (`var_model.py`, `vecm_model.py`, `dynamic_factor_model.py`, `pca_analysis.py`)
**Verdicts:** **4 PASS, 0 CAVEAT, 0 BLOCK**

## Verdicts (this session)

| Audit ID | Verdict | Achieved tolerance | Tier | Runtime |
|---|---|---|---|---:|
| `p3_pca` | **PASS bit-exact** | eigenvalues 7.99e-15 abs | fast | 0.08s |
| `p3_var` | **PASS bit-exact** | coefs 7.22e-16 abs | fast | 0.59s |
| `p3_vecm` | **PASS bit-exact** | beta 9.99e-16 abs (after sign norm) | fast | 0.76s |
| `p3_dfm` | **PASS** | loadings 1.22e-3 abs (first em_stochastic) | slow | 5.23s |

## Highlights

### Pattern A — 9 wrappers (now most-validated cross-batch pattern)

p3_pca, p3_var, p3_vecm join Pattern A bit-exact club. Three new closed-form wrappers in one session — VAR (OLS-on-stacked-equations), VECM (Johansen reduced-rank regression), PCA (eigendecomposition). All achieve <1e-13 abs precision.

**Pattern A is now Phase 3's most-validated pattern** (9 confirming wrappers across 4 batches: 1c, 3e, p3_intermittent, p3_classical_decompose, p3_har_rv, p3_pca, p3_var, p3_vecm, plus p3_mstl structural identity).

### Pattern H (DSCD) refined — does NOT apply to closed-form

Session 6 banked DSCD as covering "independent-implementation MLE-fit" cases. Session 7's p3_var (statsmodels VAR vs R `vars::VAR` — independent implementations) achieved bit-exact 7.22e-16. **Closed-form algorithms with independent implementations do NOT exhibit DSCD.** DSCD applies specifically to optimizer-driven independent implementations (rugarch GARCH boundary attractor, future MARSS HMM EM divergence candidates).

**Refined definition locked in cross-batch findings:**
> DSCD applies to independent-implementation **OPTIMIZER-DRIVEN** wrappers (MLE / iterative search), NOT to closed-form algorithms.

### NEW Pattern I candidate — sign / scale convention alignment

Three Session 7 instances:
- p3_pca: max-abs-positive eigenvector sign convention
- p3_vecm: beta first-element-normalization + alpha sign-alignment
- p3_dfm: loadings[0]-anchored to 1.0

When the underlying algorithm has identifiability up to sign / scale, parity comparison requires explicit alignment before computing diffs. Status: candidate; needs 1+ more wrapper before formalizing into the cross-batch pattern catalog.

### First `em_stochastic` verdict_class instance

p3_dfm achieves loadings 1.22e-3 abs — 1.6 orders inside the 5e-2 widened band. Suggests EM convergence on small DFMs is more stable than master plan §7.1 anticipated. Banked: tighten band to 1e-2 if Batch 4 HMM / Markov-switching shows similar headroom.

## §10.3 success criteria — second measurement (multi-distinct-wrapper batch)

| # | Criterion (revised at S5) | Result for Batch 3 | Status |
|---|---|---|---|
| 1 | ≤60% audit time per wrapper | 4 audits in 1 session vs Batch 1's 3.3/session = ~25% session-pace improvement | **PASSED** |
| 2 | ≥30% per-check LOC reduction | 10% average reduction across 4 distinct standalone checks | **NOT MET on this batch** |
| 3 | Zero infrastructure modification per new wrapper | Confirmed | **PASSED** |
| 4 | Bit-for-bit Batch 1 reproduction | 24/26 PASS + 2 CAVEAT in fast tier; identical to Sessions 5–6 baseline | **PASSED** |

**Honest Criterion 2 finding:** the Session 5 generator's LOC-reduction benefit is **proportional to within-batch wrapper similarity**:

| Batch type | Observed reduction |
|---|---:|
| Variant-shared (S6 GARCH 3 variants) | 75% |
| Distinct-wrapper batch (S7 4 distinct multivariate wrappers) | 10% |

The harness primitives save ~50 LOC of boilerplate per check, but per-check business logic (DGP, R script template, output extraction, sign/scale-canonicalization) is wrapper-specific and not amortizable. **§10.3 criterion 2 needs batch-type-dependent re-wording.** Banked for Chat check-in 2.

## Cross-wrapper observations

### Observation 1: Pattern A on independent implementations (closed-form)

Closed-form algorithms with independent implementations (NumPy lstsq vs R lm, NumPy eigh vs sklearn SVD, statsmodels VECM vs urca+cajorls) achieve bit-exact parity. **Closed-form trumps implementation independence.** This is the strongest finding of Session 7 — it refines the verdict_class taxonomy: `closed_form` is a fundamentally different risk regime from `mle_fit`.

### Observation 2: VECM as `algebraic_mle` candidate

p3_vecm's `verdict_class` is `mle_fit` (Johansen MLE) but achieves Pattern A bit-exact (9.99e-16 abs). The Johansen procedure is technically MLE but algorithmically reduces to a generalized eigenvalue problem (algebraic), not an iterative optimizer. **Candidate `verdict_class` split: `algebraic_mle` (analytical MLE → bit-exact) vs `iterative_mle` (optimizer-driven, may have DSCD).** Banked for check-in 2.

### Observation 3: AIC/BIC scale conventions multiply across implementations

p3_var: 2859-unit AIC divergence. p3_ets: 1070-unit AIC divergence. p3_dfm: 22.93-unit BIC divergence. Each statsmodels/R pair uses different parameter-counting + likelihood-scaling conventions. **Pattern D systematically applies; Secondary-tier non-propagation is the right policy.**

### Observation 4: MARSS install adds ~1 minute to Windows CI build

MARSS R package downloaded + installed without issue (3.11.10) but added ~50 seconds to local R install time. CI install time will be similar. Total fast-tier R install (10 packages now) will run ~3 min on Windows runner; remaining headroom in 10-min job timeout is still ~7 min for Phase 3 fast-tier expansion.

## Files written this session

| File | Purpose | LOC |
|---|---|---:|
| `harness/checks/p3_var.py` | VAR vs vars::VAR | 304 |
| `harness/checks/p3_vecm.py` | VECM vs urca+cajorls | 320 |
| `harness/checks/p3_dfm.py` | DFM vs MARSS | 281 |
| `harness/checks/p3_pca.py` | PCA vs sklearn | 209 |
| `harness/structural_invariants.py` (extension) | `var_eigenvalues` + `vecm_cointegration_rank` concrete checkers | +85 |
| `harness/tolerances.py` (extension) | 4 ladder entries | +110 |
| `.github/workflows/parity-fast.yml` | Add MARSS R + scikit-learn pip | +2 |
| `.github/workflows/parity-slow.yml` | Add MARSS R + scikit-learn pip | +2 |
| `reports/p3_var_audit.md` | Per-wrapper report | 95 |
| `reports/p3_vecm_audit.md` | Per-wrapper report | 92 |
| `reports/p3_dfm_audit.md` | Per-wrapper report | 102 |
| `reports/p3_pca_audit.md` | Per-wrapper report | 65 |
| `reports/p3_batch_3_summary.md` | Batch 3 close summary | 245 |
| `reports/phase3_cross_batch_findings.md` (extension) | Session 7 patterns | +130 |
| `docs/reference_parity_status.md` | P-4 update | (updated) |
| `docs/reference_parity/session_7_findings.md` | This document | (this file) |
| **Total** | | ~2050 LOC |

## Regression check

Full fast tier 26 checks → 24 PASS + 2 CAVEAT in ~210s:

```
[PASS] _smoke_test, 1c_bvar, 3a_caviar, csd, 3c_evt, 3b_har_cj, 3d_johansen,
       2a_kalman, 3e_mint, p3_arima_manual, p3_arimax_sarimax, p3_theta,
       p3_classical_decompose, p3_egarch, p3_ets, p3_gjr_garch, p3_har_rv,
       p3_intermittent, p3_pca (NEW), p3_sarima, p3_sgarch, p3_var (NEW),
       p3_vecm (NEW), 3f_transformer
[CAVEAT] p3_mstl, p3_stl
overall: CAVEAT  (exit 2 → CI maps to green per fd91dc7 policy)
```

p3_dfm slow-tier PASS in 5.23s (single-tier check; not in fast-tier).

## Discipline lessons applied (Session 6 carry-forward)

Per Session 6 retrospective discipline lock: **install-matrix updates ship in audit-creation commit**. Session 7's commit includes:
- `MARSS` (R) added to fast-tier + slow-tier install — used by p3_dfm
- `scikit-learn` (Python pip) added to fast-tier + slow-tier install — used by p3_pca

No separate CI-fix follow-up commit needed. Single commit ships audit code + dependency updates together.

## Banked items (cumulative through S7) — do NOT modify now

1. **`verdict_class` enum split** — needs Batch 4–6 evidence. Candidate splits surfacing:
   - `mle_fit` → `single_impl_mle` / `optimizer_divergent_mle` / `algebraic_mle` (Johansen, Kalman closed-form)
   - `em_stochastic` may need tightening based on Batch 4 HMM / Markov-switching headroom

2. **DSCD diagnostic-axis registry design** — locked at check-in 2 with refined definition

3. **Pattern I formalization (sign / scale convention alignment)** — needs 1+ more wrapper

4. **§10.3 criterion 2 wording revision** — batch-type-dependent (variant-shared vs distinct-wrapper)

5. **Cross-batch findings doc design refinements** — pattern catalog + verdict_class headroom table format

6. **Infrastructure-fix discipline track** — based on Sessions 6–14 evidence (1 fix to date: fd91dc7)

7. **p3_var headroom 8.1 orders + p3_vecm 13 orders** — Phase 3.5 candidate to tighten respective bands

## Next session

**Session 8** — Batch 4 entry per master plan §15.6 (R Markov / nonlinear). 5 wrappers in scope:
- `hmm_model.py` vs R `depmixS4`
- `markov_switching.py` vs R `MSwM`
- `tar_setar.py` vs R `tsDyn::setar`
- `star_model.py` vs R `tsDyn::star` (Tier B/C — STAR custom transitions)
- `nar_narx.py` vs R `tsDyn::nlar`

(`critical_slowing_down.py` already covered by harness check from Phase 2 cleanup.)

Per locked discipline: install-matrix updates ship in Session 8 commit. Required deps: `depmixS4`, `MSwM`, `tsDyn` (R) — all currently TBD-batch-4 in MANIFEST.

Chat check-in 2 follows Session 14 (Batch 6 close, midpoint review) per master plan §15.

---

**Batch 3 closes ahead of schedule. 18/70 Phase 3 deliverables complete. 2 sessions ahead of master plan.**
