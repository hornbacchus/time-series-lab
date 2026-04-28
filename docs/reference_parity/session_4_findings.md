# Phase 3 Session 4 — Findings (Batch 1 close)

**Date:** 2026-04-28
**Batch:** 1 (R `forecast` family) — **CLOSED**
**Wrappers audited this session:** 3 (`mstl_decompose.py`, `classical_decompose.py`, `stl_decompose.py`)
**Batch 1 cumulative:** 10 / 10 deliverables (8 PASS + 2 CAVEAT + 0 BLOCK)

## Verdicts (this session)

| Audit ID | Wrapper | Verdict | Tier | Runtime |
|---|---|---|---|---:|
| `p3_classical_decompose` | `classical_decompose.py` | **PASS** (bit-exact 7.11e-14) | fast | 0.4–2.2s |
| `p3_stl` | `stl_decompose.py` | **CAVEAT** (per-index ~9e-2 abs; impl-diff) | fast | 0.6–4.0s |
| `p3_mstl` | `mstl_decompose.py` | **CAVEAT** (non-unique decomposition; structural identity 7.11e-14) | fast | 1.7–4.2s |

Cumulative Batch 1: **8 PASS + 2 CAVEAT + 0 BLOCK** across 10 wrappers.

## Key findings

### `p3_classical_decompose` — bit-exact PASS

Classical additive decomposition (centered MA + group seasonal averages) is closed-form arithmetic. statsmodels `seasonal_decompose` and R `stats::decompose` produce numerically equivalent trend/seasonal/residual decompositions at machine precision (≤7.11e-14 abs across all components). Confirms Session 3 Observation 1 for the third time in Phase 3 (after Croston 3.77e-15 and BVAR-IRF 4.58e-16 inherited from Phase 1).

### `p3_stl` — CAVEAT verdict, deterministic implementation difference

statsmodels `STL` and R `stats::stl` both implement Cleveland et al. 1990 STL but with different LOESS internals, inner-iteration convergence criteria, and trend-extraction defaults. Even when default configuration is matched as closely as possible (`s.window=13`, `s.degree=1`, `inner=2`, `outer=0`, `robust=FALSE`), per-index divergence reaches ~9e-2 absolute on trend, seasonal, and residual components.

**Verdict CAVEAT** correctly signals "matches except in stated regime" per master plan §3.1. Override `on_caveat_reroll → False` because the divergence is reproducible across seeds (deterministic computation; not Monte Carlo noise).

### `p3_mstl` — non-unique decomposition; structural identity bit-exact

Multi-period STL has *two* sources of non-uniqueness:
1. STL's iterative LOESS (inherited from `p3_stl`).
2. Per-period iteration ordering and seasonal-component extraction.

statsmodels MSTL and R forecast::mstl converge to different (equally valid) feasible points in the constraint set `y = trend + Σ seasonal_k + resid`. Per-component divergence ~1.0 absolute observed.

**Critical diagnostic:** the structural identity holds at machine precision on both sides (`recon_cross_max_abs_diff = 7.11e-14`). Both implementations decompose the **same** input faithfully — they just choose different feasible decompositions.

This is the **first audit in Phase 3 where the verdict reflects algorithmic non-uniqueness rather than implementation error**. Distinct from `p3_stl`'s "same algorithm, different LOESS internals" pattern.

## Cross-wrapper observations (this session — Patterns E and F surfaced from Session 3)

### Pattern E (refined): Deterministic CAVEAT vs MC-noise CAVEAT

The runner's CAVEAT-reroll protocol bumps to BLOCK if reroll fails. This is correct for Monte Carlo / stochastic checks (MCMC, EM-fit) where seed+1 should land in PASS band on retry. But for **deterministic** computations (STL, MSTL, decomposition), reroll reproduces the same divergence.

**Override pattern** locked: `def on_caveat_reroll(self, first_result): return False` for deterministic-but-implementation-differing checks. Document in class docstring referencing master plan §3.1.

This is the first non-trivial subclass-level harness override in Phase 3. Session 5 generator should expose this as a per-check config flag (`reroll_on_caveat: false`).

### Pattern F (new): Structural-identity diagnostic separate from per-component parity

For wrappers where the underlying algorithm enforces a structural constraint (e.g., `y = trend + sum(seasonal) + resid` for MSTL, or `forecast = z_hat / p_hat` for Croston), verify the constraint **separately** from per-component parity. This:

1. Confirms both implementations are doing the right thing computationally.
2. Distinguishes "implementation bug" from "non-unique decomposition."
3. Provides a much tighter parity assertion than per-component (machine precision vs methodology-band).

Implemented in `p3_mstl.compare`: `recon_cross_max_abs_diff` diagnostic shows TSL and R reconstruct the same y at 7.11e-14 abs, even though per-component divergence is ~1.0 abs.

**Generalization:** Phase 3 audits should add a structural-identity diagnostic when the algorithm has one. Examples for upcoming batches:
- VAR / VECM: companion form A_p satisfies certain stability conditions → invariant.
- Forecast reconciliation OLS: reconciled forecasts sum to base (top-down hierarchy invariant) — already tested in 3e.
- Kalman filter: filtered state covariance P_t|t matches the standard recursion — structurally invariant.

## Open items (logged, non-blocking)

1. **STL trend boundary handling.** `p3_stl` shows max divergence at series start/end where LOESS is most sensitive to boundary handling. Could add a "trim-edges" comparison variant for tighter parity in the interior. Logged for Session 5 generator design consideration.

2. **MSTL period-ordering.** R `forecast::mstl` iterates periods in increasing order (smallest first). statsmodels MSTL has historically used the same order. Worth explicitly verifying both are now consistent (statsmodels may have changed in recent versions).

3. **Multiplicative classical decomposition** not audited (only additive). Same closed-form arithmetic; bit-exact parity expected. Phase 3.5 candidate.

4. **MSTL forecast-based parity.** Compare h-step forecasts derived from MSTL components rather than per-component decomposition. Forecast operation re-applies structural identity, washing out per-component non-uniqueness. Phase 3.5 candidate.

## Files written this session

| File | Purpose | LOC |
|---|---|---:|
| `harness/checks/p3_classical_decompose.py` | Classical decomposition parity | 145 |
| `harness/checks/p3_stl.py` | STL parity (with `on_caveat_reroll` override) | 199 |
| `harness/checks/p3_mstl.py` | MSTL parity (with structural identity diagnostic) | 213 |
| `harness/tolerances.py` (extension) | 3 ladder entries | +95 |
| `reports/p3_classical_decompose_audit.md` | Per-wrapper report | 73 |
| `reports/p3_stl_audit.md` | Per-wrapper report | 81 |
| `reports/p3_mstl_audit.md` | Per-wrapper report | 105 |
| `reports/p3_batch_1_summary.md` | Per-batch summary (NEW) | 184 |
| `docs/reference_parity_status.md` (update) | P-4 tracker | (updated) |
| `docs/reference_parity/session_4_findings.md` | This document | (this file) |
| **Total** | | ~1320 |

## Regression check

Full fast tier 19 checks → 17 PASS + 2 CAVEAT in 58s:

```
[PASS] _smoke_test, 1c_bvar, 3a_caviar, csd, 3c_evt, 3b_har_cj,
       3d_johansen, 2a_kalman, 3e_mint, p3_arima_manual, p3_sarima,
       p3_arimax_sarimax, p3_ets, p3_theta, p3_intermittent,
       p3_classical_decompose (NEW), 3f_transformer
[CAVEAT] p3_stl (NEW), p3_mstl (NEW)
overall: CAVEAT
```

Overall: CAVEAT (exit code 2). PASS+CAVEAT verdicts both run in CI per master plan §3.3 — no escalation needed. The CAVEAT signal is informative, not failing.

## Batch 1 close

**8 PASS + 2 CAVEAT + 0 BLOCK = Batch 1 closes successfully.**

Per-batch summary committed at `tools/reference_parity/reports/p3_batch_1_summary.md` with:
- 7 empirical patterns (A–G) consolidated across Sessions 2–4.
- Verdict-class distribution + tolerance band review.
- Phase 3.5 carry-forward candidates.
- Recommendations for Session 5 generator abstraction (Pattern-classified config schema).

## Next session

**Session 5** per master plan §15.3:

> **Session 5 (Generator abstraction).** Per Section 10. Deliverable: `tools/reference_parity/harness/` populated; Batch 1 audits re-run via generator producing bit-identical results.
>
> **Chat check-in 1** after Session 5: pattern review, generator validation, Batch 2 readiness.

Generator scope (per master plan §10.2):
- `harness/compare.py` — factor `_compare_scalar` / `_compare_vector` helpers.
- `harness/r_invoke.py` — minor extension on `RBridge` (already mature).
- `harness/py_invoke.py` — NEW: parallel utility for Python-import references (Batches 7–9).
- `harness/report_template.py` — markdown emission template.
- `tools/reference_parity/configs/p3_<wrapper>.toml` — per-wrapper config schema.

Generator success criterion (per master plan §10.3): generator must reproduce Batch 1 audit results bit-for-bit when re-run on Batch 1 wrappers. Manual templates remain as reference + sentinel test cases.

Chat check-in 1 follows Session 5; Batch 2 begins with Session 6 (R volatility — `garch_model.py` + `har_rv.py`).
