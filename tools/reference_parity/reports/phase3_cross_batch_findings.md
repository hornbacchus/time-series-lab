# Phase 3 — Cross-Batch Findings (running document)

**Started:** 2026-04-28 (Phase 3 Session 6, Batch 2 entry close)
**Status:** Living document. Patterns added per session as they surface across batches; consolidated and refined into P-3 (`docs/engineering/parity_empirical_findings.md`) at Session 26.

This document tracks **findings that span multiple batches** — design tensions, methodological patterns, and verdict-class taxonomy refinements that emerge from cumulative Phase 3 evidence rather than within a single audit.

Per Chat check-in 1 disposition (post-Session 5): start this document at Batch 2 close (i.e., this commit) as the running record for cross-batch patterns.

---

## Pattern catalog (cumulative across batches)

### Pattern A — Closed-form recursion → bit-exact parity

**Status:** validated across 5 wrappers and 2 batches.

| Audit | Achieved | Wrapper |
|---|---:|---|
| `1c_bvar_irf_fevd` (Phase 1) | 4.58e-16 | `bvar.py` |
| `3e_mint_family` (Phase 1) | 4.66e-15 | `forecast_reconciliation.py` |
| `p3_intermittent` | 3.77e-15 | `intermittent_demand.py` |
| `p3_classical_decompose` | 7.11e-14 | `classical_decompose.py` |
| `p3_har_rv` (S6) | **8.88e-16** | `har_rv.py` |

**Generalization:** when both implementations execute closed-form arithmetic (no MLE optimization, no iterative LOESS), tolerance ≤ 1e-12 abs is achievable; the only noise sources are subprocess CSV roundtrip (`%.18e` format) and BLAS implementation differences (rare). For closed-form Phase 3 audits, pin Primary tolerances at 1e-10 or tighter.

### Pattern B — Single-implementation MLE-fit → 1e-3 to 1e-2 band

**Status:** validated across 4 wrappers (ARIMA family, TBATS).

Master plan §7.1 MLE-fit band (1e-3 abs / 1e-2 rel) is right-sized for cases where TSL and reference call the same fundamental optimizer family. Coefficient-level divergence ~1e-5 to 1e-4 absolute typical; 1e-3 to 1e-2 relative; well within band.

### Pattern C — State-space reformulation → widened band needed

**Status:** validated across 2 wrappers (ETS, Theta).

statsmodels and R `forecast` use mathematically-equivalent but implementationally-different state-space reformulations. Pre-emptive 5e-2 abs / 1e-1 rel band; achieved tolerance often tighter (e.g., Theta achieved 6.76e-04 — 3 orders inside band).

### Pattern D — AIC scale offsets → DOCUMENTED-DIVERGENCE Secondary tier

**Status:** validated on `p3_ets`.

Different log-likelihood scaling conventions across implementations produce ~1000-unit AIC offsets without indicating any actual model-fit divergence. Hyndman-Khandakar 2008 §6.4 documents this. Classify as `DOCUMENTED-DIVERGENCE` Secondary tier; doesn't propagate to overall verdict.

### Pattern E — Iterative-LOESS deterministic divergence → CAVEAT verdict

**Status:** validated on `p3_stl`, `p3_mstl`.

statsmodels and R LOESS implementations differ in inner-iteration convergence path; per-index divergence ~9e-2 abs is reproducible across seeds (deterministic; not MC noise). `reroll_on_caveat = False` (Session 5 default) prevents BLOCK escalation. CAVEAT verdict correctly signals "matches except in stated regime."

### Pattern F — Structural-identity diagnostic separate from per-component parity

**Status:** validated on `p3_mstl`; promoted to harness registry stub at Session 5 with 18 invariant types; **first concrete population at Session 6** (GARCH).

When the algorithm enforces a structural constraint (sum-to-y, eigenvalue stability, row-stochastic transition matrix, energy conservation), verify the constraint **separately** from per-component parity. Distinguishes "implementation bug" from "non-unique decomposition / boundary-attractor optimization."

Session 6 first concrete invariants:
- `garch_conditional_variance` — sigma2_t > 0 ∀t (verified across 3 GARCH variants)
- `garch_persistence` — alpha+beta < 1 (sGARCH/GJR) or |beta| < 1 (EGARCH)

Subsequent batches populate Kalman covariance ordering, HMM row-stochasticity, wavelet Parseval, FFT roundtrip, conformal nominal coverage, bootstrap distributional centering.

### Pattern G — R fitted-vector leading-observation conventions differ

**Status:** validated on `p3_intermittent`.

Secondary-tier fitted-vector comparisons should align by tail (most-recent values) not head; the recursion-from-first-event-onward is what matters for parity assertion.

---

### Pattern H — DSCD: Documented Sub-Class Divergence within MLE-fit (Session 6 first surface)

**Status:** **NEW — first surfaced at Session 6 GARCH audit. Banked for verdict_class enum review at Chat check-in 2.**

**Definition.** Within the `mle_fit` verdict_class, two sub-regimes exist:

1. **Single-implementation MLE-fit** (e.g., `p3_arima_manual`, `p3_sarima`, `p3_arimax_sarimax`, `p3_tbats`): TSL backend (`statsmodels`, `tbats`) and reference (`forecast::Arima`, `forecast::tbats`) share lineage or use very similar optimizer initialization heuristics. Both reliably converge to the global MLE optimum on standard fixtures. Achieved tolerance: 1e-5 to 1e-4 abs (4–6 orders of magnitude tighter than the §7.1 1e-3 band).

2. **Optimizer-divergent MLE-fit** (e.g., `p3_sgarch`, `p3_gjr_garch`, `p3_egarch`): TSL backend (`arch`) and reference (`rugarch`) are independent implementations using different optimizer families (arch's SLSQP with simulated-annealing pre-pass vs rugarch's `solnp` / hybrid). On finite-sample fixtures, the two can land at **different local optima** of the same likelihood surface — typically rugarch's default `hybrid` solver lands at the boundary attractor (alpha+beta≈1) ~30% of runs while arch reliably finds the global optimum. Achieved tolerance after seeded global-search reference (`gosolnp` with `n.restarts=10`, `n.sim=2000`, `rseed=20260428`): 1e-4 to 1e-3 abs — at the §7.1 band's boundary, not deep inside it.

**Evidence (Session 6 sGARCH audit):**

| Run | Reference solver | rugarch outcome | TSL log-lik | Ref log-lik | Verdict |
|---|---|---|---:|---:|---|
| Initial | `solver='hybrid'` (default) | boundary local optimum (alpha+beta=0.999) | −1751.69 | −1758.10 | BLOCK |
| Resolved | `solver='gosolnp', n.restarts=10, rseed=20260428` | global optimum | −1751.69 | −1751.71 | PASS |

The 6.4-likelihood-unit gap between rugarch's default-solver output and the global optimum demonstrates that DSCD is **first-class** — independent implementations differ not by 1e-5 but by 1e+0 or worse on the same fixture, depending on optimizer luck.

**Implications for verdict_class enum.** The Session 5 enum has `mle_fit` as a single class; Session 6 evidence suggests splitting into:

- `single_impl_mle_fit` — tolerance 1e-3 abs; achieved typically 1e-5 to 1e-4 abs.
- `optimizer_divergent_mle_fit` — tolerance 1e-2 abs (current GARCH band); requires reference-side global-search solver pinning (`gosolnp` for rugarch; equivalent for other independent-impl pairs).

**Decision: BANKED for Chat check-in 2** per Session 6 prompt. Don't modify enum at Session 6. Revisit with Batch 3+ evidence (VAR/VECM via `vars` package — likely DSCD; BVAR via `BVAR` — likely single-impl).

**Operational impact for Batches 3–10.** When auditing wrappers where TSL and reference are independent implementations, **the reference solver must be configured with explicit global-search** (e.g., `gosolnp` for rugarch, `optim(method="L-BFGS-B")` with multi-start for `vars`, `pomp` with multiple particle initializations). Default solvers can land at boundary local optima silently, producing false BLOCKs.

---

## Verdict-class headroom evidence (cumulative)

Per Chat check-in 1 banked item, this section tracks empirical tolerance-vs-band ratios per verdict_class to inform potential enum splits at later check-ins.

| verdict_class | Wrapper | Band Primary abs_tol | Achieved abs | Headroom (orders) |
|---|---|---:|---:|---:|
| `closed_form` | `p3_intermittent` | 1e-6 | 3.77e-15 | 9 |
| `closed_form` | `p3_classical_decompose` | 1e-10 | 7.11e-14 | 4 |
| `closed_form` | `p3_har_rv` | 1e-10 | 8.88e-16 | 6 |
| `mle_fit` (single-impl) | `p3_arima_manual` | 1e-3 | 5.24e-06 | 2.3 |
| `mle_fit` (single-impl) | `p3_sarima` | 1e-3 | 5.77e-06 | 2.2 |
| `mle_fit` (single-impl) | `p3_arimax_sarimax` | 1e-3 | 3.30e-08 | 4.5 |
| `mle_fit` (single-impl) | `p3_tbats` | 1e-2 | 1.37e-04 | 1.9 |
| `mle_fit` (DSCD candidate) | `p3_sgarch` | 1e-2 | 6.09e-04 | 1.2 |
| `mle_fit` (DSCD candidate) | `p3_gjr_garch` | 1e-2 | 7.79e-04 | 1.1 |
| `mle_fit` (DSCD candidate) | `p3_egarch` | 5e-2 (widened) | 1.62e-04 | 2.5 |
| `state_space_reform` | `p3_ets` | 5e-2 | 2.62e-02 | 0.3 |
| `state_space_reform` | `p3_theta` | 1e-2 | 6.76e-04 | 1.2 |
| `iterative_loess` | `p3_stl` | 5e-2 | 9.23e-02 | -0.3 (CAVEAT) |
| `iterative_loess` | `p3_mstl` | 5e-1 | 1.14 | -0.4 (CAVEAT) |

**Reading the table:** higher headroom (positive orders of magnitude) means the band is loose relative to achieved precision. Negative headroom means the audit landed in CAVEAT band (tolerance was crossed but block threshold wasn't).

**DSCD evidence so far (3 wrappers):** GARCH variants achieve 1.1–2.5 orders of headroom — substantially tighter than `iterative_loess` but looser than `mle_fit` single-impl (2.2–4.5 orders). Confirms hypothesis that DSCD warrants its own sub-class. Threshold for declaring the split: 4+ wrappers consistently in the 1–2.5 range while single-impl stays at 2+ orders. Batches 3–4 should provide that evidence.

---

## Reference-solver configuration patterns (cumulative)

Per pattern H, the reference-side optimizer choice matters as much as the algorithmic choice. Cumulative configurations:

| Reference | Default solver | Phase 3 override | Rationale |
|---|---|---|---|
| R `forecast::Arima` | `method='CSS-ML'` (default) | `method='ML'` | Apples-to-apples vs statsmodels MLE-only path |
| R `forecast::ets` | `opt.crit='lik'` (default) | unchanged | Default already aligns |
| R `forecast::tbats` | default hybrid | unchanged | tbats lineage same as Python tbats |
| R `forecast::croston` | (no optimizer; closed-form) | N/A | |
| R `stats::stl` | `inner=2, outer=0` (default) | match TSL `inner_iter`/`outer_iter` explicitly | LOESS inner-iteration count varies |
| R `forecast::mstl` | default | unchanged | |
| R `stats::decompose` | (no optimizer; closed-form) | N/A | |
| R `rugarch::ugarchfit` | `solver='hybrid'` | `solver='gosolnp', n.restarts=10, n.sim=2000, rseed=20260428` | **DSCD discovery; default solver lands at boundary local optima** |
| R `lm` | (closed-form) | N/A | |

**Rule of thumb (Session 6 articulation):** when the reference is from an independent-implementation library family (DSCD candidate), use a global-search solver with seeded restarts. When the reference is in the same library family as TSL (single-impl), default solver typically suffices.

---

## Phase 3 progress snapshot (Session 6 close)

| Metric | Value |
|---|---:|
| Phase 1+2 covered | 12 wrappers |
| Phase 3 in-scope | 70 deliverables |
| Phase 3 Batch 1 covered (S2-S4) | 10 (8 PASS + 2 CAVEAT) |
| Phase 3 Batch 2 covered (S6) | **4** (4 PASS) |
| **Phase 3 cumulative covered** | **14** |
| Phase 3 remaining | 56 |
| Phase 3 BLOCK | 0 |
| Patterns surfaced | A–H (8 cumulative; H new at S6) |
| Banked for check-in 2 | verdict_class enum split, DSCD diagnostic axis registration |

---

**End of cross-batch findings, Session 6 entry.** Subsequent sessions append new patterns / refined evidence as they emerge.
