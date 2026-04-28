# P3 — `tbats_forecast.py` reference parity audit (harness promotion)

**Wrapper:** `engine/techniques/tbats_forecast.py`
**Audit ID:** `p3_tbats`
**Batch / Session:** Phase 3 Batch 1 / Session 3
**Date:** 2026-04-28
**Verdict:** **PASS**
**Promotion source:** `tools/reference_parity/scripts/audit_1b_tbats.py` (Phase 1; now-deprecated due to `rscript_bridge.py` deprecation)

## 1. Reference

- **Primary:** R `forecast::tbats(y)` — `forecast` 9.0.2.

Methodology equivalence note: Python `tbats` 1.1.3 (Skorupa) and R `forecast::tbats` are independent implementations of the De Livera-Hyndman-Snyder 2011 TBATS framework. The Python package mirrors R conventions but uses different optimizer initialization and state-space starting values; smoothing parameters and Box-Cox lambda may differ by 1e-3 to 1e-2 absolute due to convergence-path divergence.

## 2. Fixture

Synthetic seasonal AR(1) with single seasonality m=12 (reused from `p3_theta` DGP generator):

| Parameter | Value |
|---|---|
| `seed` | 42 |
| `n` | 120 |
| `phi` (AR1) | 0.6 |
| `sigma` | 1.0 |
| `m` | 12 |
| seasonal amplitude | 2.0 |
| trend slope | 0.05 |
| `horizon` | 12 |

TBATS configuration (both sides):
- `use_box_cox=False`
- `use_arma_errors=False`
- `use_damped_trend=False`
- `use_trend=True`

Single-seasonality fixture chosen to keep runtime under 30s; multi-seasonal TBATS audited in a Phase 3.5 candidate if needed.

## 3. Output-tier mapping

| Tier | Outputs |
|---|---|
| **Primary** | 12-step point forecast |
| **Secondary** | smoothing parameter alpha, trend smoothing beta, AIC |
| **Diagnostic** | Box-Cox lambda (None when `use_box_cox=False`) |

## 4. Tolerance ladder

Master plan §7.1 MLE-fit band, widened per Phase 1 audit-script's empirical findings:

| Tier | abs_tol | rel_tol |
|---|---:|---:|
| Primary | 1e-2 | 5e-2 |
| Secondary | 5.0 | 1e-1 |

## 5. Achieved metrics (seed=42)

### Primary

| Metric | TSL (Python tbats) | Reference (R) | max_abs_diff | max_rel_diff | Status |
|---|---:|---:|---:|---:|---|
| forecast h=1 | 60.7256 | 60.6728 | 1.60e-01 | 2.71e-03 | PASS via rel_tol |

Forecast paths agree at 0.27% relative across all 12 horizons.

### Secondary

| Metric | TSL | Reference | abs_diff | rel_diff | Status |
|---|---:|---:|---:|---:|---|
| alpha | 0.9264 | 0.9262 | 1.37e-04 | 1.48e-04 | PASS |
| beta | −0.00435 | −0.00469 | 3.45e-04 | 7.35e-02 | PASS |
| AIC | 588.16 | 591.25 | 3.08 | 5.21e-03 | PASS |

The optimizer-init difference between Python `tbats` 1.1.3 and R `forecast::tbats` produces alpha agreement at 1.4e-4 absolute and AIC agreement at ~3 units (well within 5.0 tolerance). The forecast paths land within 0.3% relative — exactly the regime the Phase 1 audit-script's tolerance ladder anticipated.

## 6. Documented divergences

**None on Primary tier.** All Secondary metrics PASS within the band. The harness promotion successfully reproduces the Phase 1 audit-script's findings.

## 7. Runtime

6.7 seconds locally. Slow-tier eligible (TBATS fitting alone is ~6s; future multi-seasonal fixtures may push to 30s+).

`tier = "slow"` set on the check class because TBATS doesn't fit the closed-form / cheap-MLE profile of the rest of Batch 1. Excluded from `parity-fast.yml` schedule; runs in `parity-slow.yml` nightly.

## 8. Reference version snapshot

- R: 4.5.3
- `forecast`: 9.0.2
- Python `tbats`: 1.1.3

## 9. Outcome

**PASS.** TBATS forecasts and smoothing parameters reproduce R `forecast::tbats` within the §7.1 MLE-fit band on the single-seasonal fixture. The Phase 1 audit-script's tolerance findings are preserved as the harness baseline.

## 10. Notes

This is a **harness promotion**, not a new audit. The Phase 1 work (`scripts/audit_1b_tbats.py`) established the tolerance ladder; this harness check formalizes it as a durable `ParityCheck` subclass, runnable via `python -m reference_parity --technique p3_tbats` and integrated into the slow-tier CI workflow.

Phase 1 sklearn shim: TSL's `tbats_forecast.py` installs a process-wide compatibility shim translating `force_all_finite=True` (tbats 1.1.3 API) → `ensure_all_finite=True` (sklearn 1.6+ API). The harness check imports `techniques.tbats_forecast` first to trigger the shim, then imports `tbats.TBATS` directly. Without the shim, the audit would fail on `TypeError: check_array() got an unexpected keyword argument 'force_all_finite'`.
