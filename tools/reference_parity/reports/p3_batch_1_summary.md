# Phase 3 Batch 1 — R `forecast` family: Per-Batch Summary

**Batch:** 1 (R `forecast` family)
**Sessions:** S2, S3, S4 (closing)
**Date:** 2026-04-28
**Wrappers audited:** 10 / 10 (Batch 1 complete)
**Verdicts:** **8 PASS, 2 CAVEAT, 0 BLOCK**

---

## 1. Coverage matrix

| # | Wrapper | Audit ID | Reference | Tier | Verdict | Tightest achieved tolerance | Session |
|---|---|---|---|---|---|---|---|
| 1 | `arima.py` | `p3_arima_manual` | R `forecast::Arima(method="ML")` | fast | **PASS** | AR/MA coefs ≤ 6e-6 abs | S2 |
| 2 | `arimax_sarimax.py` | `p3_arimax_sarimax` | R `forecast::Arima(xreg=...)` | fast | **PASS** | AR ≤ 3e-8, exog ≤ 5.5e-6 | S2 |
| 3 | `sarima.py` | `p3_sarima` | R `forecast::Arima(seasonal=...)` | fast | **PASS** | All coefs ≤ 1e-5 abs | S2 |
| 4 | `ets_hw.py` | `p3_ets` | R `forecast::ets` | fast | **PASS** (Sec AIC offset doc'd) | smoothing params 1e-2 abs | S3 |
| 5 | `theta_forecast.py` | `p3_theta` | R `forecast::thetaf` | fast | **PASS** | forecast 6.76e-04 abs | S3 |
| 6 | `intermittent_demand.py` | `p3_intermittent` | R `forecast::croston` | fast | **PASS** (bit-exact) | forecast **3.77e-15 abs** | S3 |
| 7 | `tbats_forecast.py` | `p3_tbats` | R `forecast::tbats` | slow | **PASS** | alpha 1.4e-4 abs | S3 |
| 8 | `classical_decompose.py` | `p3_classical_decompose` | R `stats::decompose` | fast | **PASS** (bit-exact) | components ≤ 7e-14 abs | S4 |
| 9 | `stl_decompose.py` | `p3_stl` | R `stats::stl` | fast | **CAVEAT** (impl-diff) | trend max 9e-2 abs | S4 |
| 10 | `mstl_decompose.py` | `p3_mstl` | R `forecast::mstl` | fast | **CAVEAT** (non-uniq) | components ~1.0 abs; **recon 7e-14** | S4 |

---

## 2. Verdict-class distribution

| Verdict | Count | Example wrappers |
|---|---:|---|
| PASS bit-exact (≤ 1e-12 abs) | 2 | `p3_intermittent`, `p3_classical_decompose` |
| PASS tight (1e-6 to 1e-2 abs) | 5 | `p3_arima_manual`, `p3_sarima`, `p3_arimax_sarimax`, `p3_theta`, `p3_tbats` |
| PASS with documented Secondary divergence | 1 | `p3_ets` (AIC scale offset) |
| CAVEAT (impl-diff, deterministic) | 2 | `p3_stl`, `p3_mstl` |
| BLOCK | 0 | — |

---

## 3. Empirical patterns observed

### Pattern A: Closed-form recursion → bit-exact parity

**Observed in:** `p3_intermittent` (Croston: 3.77e-15), `p3_classical_decompose` (additive decomp: 7.11e-14), `p3_mstl` *structural identity* (7.11e-14), and inherited from prior Verification Initiative (`3e_mint_family`: 4.66e-15, `1c_bvar_irf_fevd`: 4.58e-16).

**Generalization:** When the algorithm is closed-form arithmetic with no iterative optimizer, expect machine-precision parity. Pin Primary tolerances at 1e-10 (or tighter); the only noise source is subprocess CSV roundtrip noise (`%.18e` format).

### Pattern B: Single-implementation MLE-fit → 1e-3 to 1e-2 band

**Observed in:** `p3_arima_manual`, `p3_sarima`, `p3_arimax_sarimax`, `p3_tbats`. Both TSL (statsmodels / Python `tbats`) and R (`forecast::Arima` / `forecast::tbats`) optimize the same Gaussian innovation likelihood; convergence-criterion differences produce coefficient-level divergence in the 1e-5 to 1e-4 absolute range.

**Generalization:** Master plan §7.1 MLE-fit band (1e-3 abs / 1e-2 rel) is right-sized.

### Pattern C: State-space reformulation → widened band needed

**Observed in:** `p3_ets`, `p3_theta`. statsmodels and R use mathematically-equivalent but implementationally-different state-space reformulations.

**Generalization:** Pre-emptively widen to 5e-2 abs / 1e-1 rel for any wrapper with a known state-space-vs-classical reformulation pair.

### Pattern D: AIC scale offsets across implementations → DOCUMENTED-DIVERGENCE Secondary

**Observed in:** `p3_ets` (~1070 abs AIC offset). statsmodels SSE-based likelihood vs R state-space innovation variance differ by an additive constant (`n*log(2π)/2` typically dropped on one side). Methodology-equivalent per Hyndman-Khandakar 2008 §6.4.

**Generalization:** AIC/BIC divergence > 100 abs while underlying point estimates and forecasts agree at the Primary band → classify as `DOCUMENTED-DIVERGENCE` Secondary tier, non-propagating.

### Pattern E: STL/MSTL implementation differences → CAVEAT verdict, non-MC-noise

**Observed in:** `p3_stl` (max ~9e-2 abs per-index), `p3_mstl` (max ~1.0 abs per-component).

**Sub-pattern E1 (STL):** LOESS internals differ; per-index divergence reproducible across seeds. CAVEAT-reroll override needed (`on_caveat_reroll → False`).

**Sub-pattern E2 (MSTL):** Seasonal decomposition is non-unique; both implementations satisfy `y = trend + Σ seasonal + resid` at machine precision but pick different feasible points. CAVEAT verdict. Structural identity verified separately as a diagnostic metric.

**Generalization:** For deterministic but algorithmically-non-unique computations, override `on_caveat_reroll` to False and verify structural invariants separately. Session 5 generator should expose `reroll_on_caveat: false` config flag.

### Pattern F: R fitted-vector leading-observation conventions differ

**Observed in:** `p3_intermittent` (TSL `fitted[0]=0.8` vs R `fitted[0]=0.0` due to leading-zero padding convention).

**Generalization:** Secondary-tier fitted-vector comparisons should align by tail (most-recent values) rather than head; the recursion-from-first-event-onward is what matters for parity assertion.

### Pattern G: R model-object internals not always exposed

**Observed in:** `p3_intermittent` — `forecast::croston()$model` only contains `$alpha`, no internal state (z_hat, p_hat). Adapt the check to compare only user-visible outputs.

**Generalization:** When the R reference exposes a thin model object, fall back to comparing `$mean` (forecast) and `$fitted` (fitted) only. Internal-state comparisons require either computing internals from outputs or using a different reference.

---

## 4. Tolerance band review

Master plan §7.1 baseline tolerance classes mapped to Batch 1 wrappers:

| Class | Wrappers | Achieved median | Band right-sized? |
|---|---|---:|---|
| Closed-form analytical (1e-10) | `p3_intermittent`, `p3_classical_decompose` | 1e-13 | **Tighter possible** (could pin at 1e-12) |
| MLE-fit (1e-3) | ARIMA family, TBATS | 1e-5 to 1e-4 | **Tighter possible** (could pin at 1e-2 abs) |
| State-space reformulation (custom widened) | ETS, Theta | 1e-2 abs | Widened band correct |
| Iterative LOESS (custom widened) | STL, MSTL | 1e-1 to 1.0 abs | Widened band correct |

**Phase 3.5 candidate:** Re-pin Pattern A and Pattern B tolerances 1 order of magnitude tighter once we've observed enough fixtures to validate.

---

## 5. Open items carried forward

1. **TSB intermittent demand.** No canonical R reference in current MANIFEST (TBD-batch-1 `tsintermittent`). Logged in `docs/reference_parity_status.md` as Phase 3.5 candidate.
2. **statsmodels `ThetaModel.fit().fittedvalues` extraction.** Not exposed in public API; `p3_theta` reports nan for TSL-side in-sample RMSE. Future-work.
3. **STL/MSTL `recon_cross` invariant could be elevated to Primary.** Currently Diagnostic-tier. Worth considering for Session 5 when redesigning the comparison helper API.
4. **Multiplicative classical decomposition** not audited (only additive). Phase 3.5 candidate.
5. **Forecast-based MSTL parity** — compare h-step forecasts derived from each implementation's MSTL output (washes out per-component non-uniqueness). Phase 3.5 candidate.
6. **TBATS multi-seasonal fixture.** Current audit is single-period to keep runtime fast. Phase 3.5 candidate.

---

## 6. Batch 1 statistics

| Metric | Value |
|---|---:|
| Wrappers audited | 10 |
| Sessions used | 3 (S2, S3, S4) |
| New audit checks | 10 |
| New tolerance ladder entries | 10 |
| New per-wrapper audit reports | 10 |
| Cumulative LOC delta (harness/checks/p3_*.py) | ~2900 |
| Cumulative LOC delta (tolerances.py) | ~325 |
| Verdict distribution | 8 PASS / 2 CAVEAT / 0 BLOCK |
| Empirical patterns identified | 7 (A–G above) |
| Total fast-tier runtime added | ~15 sec |

---

## 7. Aggregate Phase 3 progress

| Metric | Value |
|---|---:|
| Phase 1+2 covered (Verification Initiative) | 12 wrappers |
| Phase 3 in-scope total | 70 deliverables |
| Phase 3 covered | **10 PASS / CAVEAT** (Batch 1 complete) |
| Phase 3 remaining | 60 |
| Phase 3 BLOCK | 0 |

---

## 8. Recommendations for Session 5 (generator abstraction) + Chat check-in 1

The Session 5 generator should encode the empirical patterns A–G as first-class config options:

```toml
# tools/reference_parity/configs/p3_<wrapper>.toml
[parity_check]
technique_id = "p3_<wrapper>"
tier = "fast"
fixture_id = ""               # or a sha-256-pinned fixture id
reroll_on_caveat = true       # false for deterministic Pattern E
verdict_class = "MLE_fit"     # or "closed_form", "state_space",
                              # "iterative_loess", etc.

[primary]
abs_tol = 1e-3
rel_tol = 1e-2

[secondary]
abs_tol = 1e-2
rel_tol = 5e-2
allow_block_propagation = false  # AIC scale offsets shouldn't fail audit

[structural_invariants]
# Optional: closed-form constraints to verify separately
# e.g. for MSTL: trend + sum(seasonal) + resid == y
```

The 10 manually-written checks in Batch 1 are the template source. Session 5 factors out:
- Fixture generation (reuse common DGPs across batches)
- TSL invocation (reuse `_ensure_engine_on_path`)
- Reference invocation (R via RBridge; Python via direct import — Session 5 adds PyBridge symmetry)
- Tolerance application (Pattern-classified ladder shapes)
- Verdict aggregation (any-BLOCK → BLOCK; any-CAVEAT + deterministic → CAVEAT; else PASS)
- Report emission (markdown template per wrapper + per-batch summary)
- P-4 status tracker auto-update

Estimated Session 5 LOC: ~800 in `tools/reference_parity/harness/generator.py` + supporting modules. Manual templates (Batch 1) remain as both validation source (Session 5 must reproduce manual results bit-identically) and sentinel test cases.

---

**End of Batch 1 summary. Session 5 next.** Chat check-in 1 follows Session 5 per master plan §15.3.
