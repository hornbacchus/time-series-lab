# Phase 3 Session 2 — Findings

**Date:** 2026-04-28
**Batch:** 1 (R `forecast` family)
**Wrappers audited:** 3 / 10 in Batch 1 (`arima.py`, `sarima.py`, `arimax_sarimax.py`)
**Sessions remaining in Batch 1:** 2 (S3, S4)

## Verdicts

| Audit ID | Wrapper | Verdict | Runtime |
|---|---|---|---:|
| `p3_arima_manual` | `engine/techniques/arima.py` (manual order) | **PASS** | 3.4s |
| `p3_sarima` | `engine/techniques/sarima.py` | **PASS** | 2.2s |
| `p3_arimax_sarimax` | `engine/techniques/arimax_sarimax.py` | **PASS** | 2.0s |

All three audits PASS at the master plan §7.1 "MLE-fit (deterministic optimizer)" tolerance band (Primary: abs_tol=1e-3, rel_tol=1e-2; Secondary: abs_tol=1e-2, rel_tol=5e-2). Achieved tolerances on the Primary tier are 4–6 orders of magnitude tighter than the band — both statsmodels and R `forecast::Arima` converge to numerically equivalent MLE estimates given identical fixtures.

## Cross-wrapper observation: sigma² methodology equivalence

All three audits show a consistent ~0.5–1.7% relative divergence on `sigma²` between TSL (statsmodels) and R `forecast::Arima`. Root cause: definitional difference in σ² convention.

- **statsmodels:** `sigma² = ML estimate` (likelihood-derived directly).
- **R `forecast::Arima`:** `fit$sigma2 = sum(residuals²) / (n − k_pars + k_const)` (unbiased-style divisor).

Both are valid σ² conventions; the difference is the divisor (MLE vs unbiased). Within Secondary tier tolerance (5e-2 rel) for all three audits. **Not a bug; methodology-equivalent per master plan §3.1's `DOCUMENTED-DIVERGENCE` semantics, but lands inside the PASS band so no separate divergence report needed.**

For Sessions 3–4 (ETS / Theta / STL family), apply the same heuristic: σ²-class divergences in the 1–2% band on Secondary outputs are typically methodology-equivalent and do not need investigation unless they exceed 5e-2 rel.

## Manual harness pattern lock (Session 2 deliverable per master plan §15.2)

The structural template for Sessions 3–4 (and the remainder of Batch 1) is:

1. **Module layout:** one `harness/checks/p3_<wrapper>.py` per wrapper.
2. **DGP generator:** module-level `_generate_*_dgp` function; seeded; reproducible from seed alone (no on-disk fixture needed for stationary synthetic DGPs).
3. **`fixture_id = ""`** (runtime-generated; saves SHA256 sidecar overhead while preserving reproducibility from the runner-supplied seed).
4. **`setup_fixture(seed)`** returns `{"y": ..., "order": ..., "horizon": ..., ...}`.
5. **`run_tsl`** invokes the underlying statistical library directly (statsmodels / scipy / etc.) to extract coefficient breakdowns explicitly via `param_names`, AND exercises the public TSL wrapper for sanity (`audit_fields` cross-check).
6. **`run_reference`** calls `RBridge.rscript_call` (or future `PyBridge`) with reference-library R/Python code; outputs CSV per metric.
7. **`compare`** builds Primary + Secondary metric dicts via `_compare_scalar` / `_compare_vector` helpers (defined in `p3_arima.py`; re-imported by sibling checks).
8. **Tolerance ladder** registered in `harness/tolerances.py` with shape `{"type": "tiered_outputs", "primary": {abs_tol, rel_tol, block_abs_tol, block_rel_tol}, "secondary": {...}, "justification": "..."}`.
9. **`ParityResult.diagnostics`** carries reference-version snapshot (via `capture_versions_for=...`), fixture metadata, and wrapper-AIC sanity check.
10. **Audit report** at `tools/reference_parity/reports/p3_<wrapper>_audit.md` — see existing 3 for template.
11. **Status tracker row** in `docs/reference_parity_status.md`.

`_compare_scalar` / `_compare_vector` produce three-state status (PASS / CAVEAT / BLOCK) based on abs and rel tolerances + 10× block thresholds. The `compare` method aggregates: any-BLOCK → BLOCK, any-CAVEAT → CAVEAT, all-PASS → PASS.

Session 5 generator abstraction will factor out (a) `_compare_*` helpers into `harness/compare.py`, (b) `_ensure_engine_on_path` into `harness/_check_helpers.py`, (c) the per-check config (DGP params, R code, output mapping) into `tools/reference_parity/configs/p3_<wrapper>.toml`. Until Session 5, follow the manual template.

## Open items (logged, non-blocking)

1. **`tbats_forecast.py` harness promotion** — Phase 1 audit-script (`scripts/audit_1b_tbats.py`) produced a tolerance ladder but was never promoted to a `harness/checks/` module. Slot for Session 3 or 4 (master plan Appendix A Batch 1 #10). The audit script depends on the deprecated `scripts/rscript_bridge.py`; a from-scratch `p3_tbats.py` is the right path, using the existing report's tolerance findings as baseline.
2. **TSL `arima.py` auto-arima path** — `technique_id = "auto_arima"` exercises `pmdarima.auto_arima` rather than statsmodels MLE directly. Order-search is a heuristic stepwise/grid procedure and not guaranteed to land on the same order as `forecast::auto.arima` even on identical fixtures. Treat as a **separate concern**: a parity audit for `auto_arima` would compare against R `forecast::auto.arima` on a fixture where the optimal order is unambiguous (e.g., generated from a single ARMA structure with strong signal). Defer; not part of master plan Batch 1's headline coverage. The covered manual-order path establishes parity for the underlying MLE math.
3. **Forecast-output non-zero diff at horizon=1** — both `p3_arima_manual` and `p3_sarima` show small (<1e-4 absolute) differences in the first forecast value due to the AR/MA coefficient differences propagating one step. PASS band absorbs this; flagged for awareness when extending to longer horizons.

## Files written this session

| File | Purpose | LOC |
|---|---|---:|
| `tools/reference_parity/harness/checks/p3_arima.py` | ARIMA manual-order parity | 397 |
| `tools/reference_parity/harness/checks/p3_sarima.py` | SARIMA parity | 297 |
| `tools/reference_parity/harness/checks/p3_arimax_sarimax.py` | ARIMAX/SARIMAX parity | 333 |
| `tools/reference_parity/harness/tolerances.py` (extension) | 3 ladder entries | +95 |
| `tools/reference_parity/reports/p3_arima_audit.md` | Per-wrapper audit report | 102 |
| `tools/reference_parity/reports/p3_sarima_audit.md` | Per-wrapper audit report | 81 |
| `tools/reference_parity/reports/p3_arimax_sarimax_audit.md` | Per-wrapper audit report | 92 |
| `docs/reference_parity_status.md` | P-4 status tracker (NEW) | 78 |
| `docs/reference_parity/session_2_findings.md` | This document | (this file) |
| **Total** | | ~1500 |

## Regression check

Full fast tier ran end-to-end:

```
[PASS] _smoke_test (0.27s)
[PASS] 1c_bvar_irf_fevd (2.37s)
[PASS] 3a_caviar_sav (4.09s)
[PASS] critical_slowing_down (9.61s)
[PASS] 3c_evt_ferro_segers (36.36s)
[PASS] 3b_har_cj (0.36s)
[PASS] 3d_johansen_bartlett (0.54s)
[PASS] 2a_kalman_filter_smoother (1.43s)
[PASS] 3e_mint_family (3.79s)
[PASS] p3_arima_manual (3.40s)
[PASS] p3_arimax_sarimax (1.95s)
[PASS] p3_sarima (2.19s)
[PASS] 3f_transformer_attention (9.09s)
overall: PASS
```

13/13 PASS. Total runtime ~75s (well within 10-min fast-tier budget).

## Next session

**Session 3** per master plan §15.2:
- ETS (`ets_hw.py`) vs R `forecast::ets`
- Theta (`theta_forecast.py`) vs R `forecast::thetaf`
- Intermittent demand (`intermittent_demand.py`, covers Croston/SBA/TSB) vs R `forecast::croston` + R `tsintermittent`
- (Possibly) tbats_forecast.py harness promotion if scope-bandwidth permits

Session 3 executes against master plan §15.2 directly; no Chat re-engagement.
