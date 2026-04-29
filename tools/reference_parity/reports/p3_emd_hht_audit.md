# Phase 3 Batch 7 — `p3_emd_hht` Audit

**Wrapper:** `engine/techniques/emd_hht.py`
**Reference:** `PyEMD.EMD` (EMD-signal 1.9.0, Laszuk)
**Verdict:** **CAVEAT** (Pattern J / Tier C — different
sifting libraries; ±2 IMF count divergence with 0.99
correlation on energy curve)
**Tolerance class:** em_stochastic
**Date:** 2026-04-29

## Result

### Primary metrics

| Metric | Status | Detail |
|---|---|---|
| `reconstruction_identity_tsl` | PASS | max abs residual 1.11e-16 |
| `reconstruction_identity_ref` | PASS | max abs residual 0.0 |
| `n_imfs_match` | **CAVEAT** | TSL=8, ref=6, abs_diff=2 |
| `cum_energy_curve_correlation` | PASS | Pearson 0.991 |

**Outcome:** CAVEAT verdict driven by IMF-count divergence.
TSL's numpy-fallback sifter (mirrors AOE Quinn `emd`-package
algorithm) extracts 8 IMFs; PyEMD (Laszuk) extracts 6 IMFs
on the same signal. Both implementations satisfy reconstruction
identity at machine precision (sum(IMFs) + residual = original
signal exactly). The cumulative-energy curve agrees at
ρ=0.991 — both implementations concentrate energy in similar
frequency bands despite different IMF granularity.

## Fixture

- DGP: chirp (5→25 Hz over [0,1]) + low-freq sinusoid
  (1.5 Hz) + linear trend + N(0, 0.01) noise, T=512,
  seed=42
- Both arms configured with max_iter=200, max_imfs=8

## Diagnostics

- TSL n_imfs: 8
- PyEMD n_imfs: 6
- ρ(cum_energy_curve): 0.991 (well above 0.85 PASS threshold)
- PyEMD version: 1.9.0
- TSL `emd` package: NOT INSTALLED (uses `_numpy_emd`
  fallback)

## Pattern J / NO-REFERENCE Tier C classification

Per master plan §5 Tier C, EMD/HHT lacks a canonical
reference: the AOE Quinn `emd`, Laszuk `PyEMD`, MATLAB
`emd`, and R `EMD` packages all implement Huang 1998 with
slightly different envelope-extension heuristics, sifting
stop criteria, and edge handling. Per-IMF bitwise parity is
mathematically intractable. Comparison via:

1. Reconstruction identity (machine precision on both sides)
   — verifies neither implementation drops energy.
2. IMF count agreement (±1 PASS, ±2 CAVEAT, ±3+ BLOCK) —
   verifies sifting stops at compatible coarseness.
3. Cumulative-energy-curve Pearson correlation (>= 0.85
   PASS) — verifies energy is distributed across IMFs in
   correlated patterns even when granularity differs.

CAVEAT verdict is informative-not-bug — documents the known
methodology divergence. `reroll_on_caveat = False` (default
per Session 5 lock) means no retry; verdict stays CAVEAT
deterministically.
