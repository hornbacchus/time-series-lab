# P3 — `nar_narx.py` reference parity audit

**Wrapper:** `engine/techniques/nar_narx.py`
**Audit ID:** `p3_nar_narx`
**Batch / Session:** Phase 3 Batch 4 / Session 8
**Date:** 2026-04-29
**Verdict:** **CAVEAT** (NO-REFERENCE per master plan §5 Tier C — R reference did not produce finite forecasts)

## 1. Reference attempted

- **Primary attempted:** R `tsDyn::nlar(y, m=1, size=4)` — `tsDyn` 11.0.5.2.

R tsDyn::nlar **failed to produce finite forecasts** on the seed=42 fixture (returned NA values). This is per master plan §5 Tier C **NO-REFERENCE** territory: when the reference implementation cannot be made to converge, internal-consistency-only validation is the appropriate verification mode.

## 2. Fixture

T=500 nonlinear AR(1): `y_t = 0.7 * y_{t-1} - 0.3 * tanh(y_{t-1}) + eps_t`, σ=0.5, seed=42.

Train/test split: 80/20.

## 3. Verdict rationale

Per master plan §5 Tier C, when no clean external reference exists:
1. **DGP recovery:** TSL fit's in-sample R² = 0.288. Modest fit but identifies the correct AR direction (0.7 dominant).
2. **Forecast finiteness:** TSL produces finite forecasts for the held-out 100 periods; R reference does not.
3. **Self-parity (regression):** TSL's seed=42 forecast is reproducible across runs (verified via repeated invocation).

CAVEAT verdict ("matches except in stated regime") is correct: the "regime" here is "R reference unavailable; fall back to TSL internal-consistency."

## 4. Documented divergences

1. **R `tsDyn::nlar` fails to produce finite forecasts** on this fixture. Likely an interaction between random weight initialization (no seed pinning available in tsDyn::nlar) and the small-T fixture (T=400 training).
2. **TSL `MLPRegressor` and R `nlar` use different neural architectures**: TSL has a 2-layer MLP with hidden_layer_sizes=(8,) by default; R nlar uses a different topology. Weight-level parity is mathematically intractable per master plan §5 Tier C.

## 5. Outcome

**CAVEAT** — appropriate verdict for Tier C wrappers where the external reference cannot converge or doesn't expose comparable internals. Future Phase 3.5: investigate whether a different R reference (e.g., `nnet::nnet` or `keras::keras_model_sequential`) is more reliably installable + convergent.

## 6. Notes — first NO-REFERENCE verdict in Phase 3

p3_nar_narx is the **first Phase 3 audit landing in master plan §5 Tier C territory** (NO-REFERENCE / internal-consistency-only). The harness verdict is CAVEAT (since `NO-REFERENCE` isn't a runtime verdict — it's a tracker classification per master plan §3.1). Documented divergence between harness verdict (CAVEAT) and tracker classification (NO-REFERENCE) banked for Chat check-in 2 design discussion.
