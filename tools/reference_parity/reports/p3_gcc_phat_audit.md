# Phase 3 Batch 10 — `p3_gcc_phat` Audit

**Wrapper:** `engine/techniques/gcc_phat_delay.py`
**Reference:** from-scratch self-parity (Knapp-Carter 1976 formula)
**Verdict:** **PASS** (Pattern A bit-exact)
**Date:** 2026-04-29

| Metric | abs diff | status |
|---|---:|---|
| `delay` | 0.0 | PASS (exact, integer) |

GCC-PHAT delay is integer-valued (argmax of normalized cross-
power-spectrum inverse FFT). Bit-exact match expected; both
arms compute the same Knapp-Carter 1976 formula. True delay 5
samples; both arms recover -5 (sign convention: negative
means y leads x).

DGP: delayed pair (T=512, true_delay=5, σ=0.05 noise, seed=42).
