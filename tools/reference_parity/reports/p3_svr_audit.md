# Phase 3 Batch 8 — `p3_svr` Audit

**Wrapper:** `engine/techniques/svr_forecast.py`
**Reference:** direct `sklearn.svm.SVR` in-process (sklearn 1.8.0)
**Verdict:** **PASS** (Pattern A same-library bit-exact)
**Tolerance class:** closed_form
**Date:** 2026-04-29

## Result

| Metric | abs diff | status |
|---|---:|---|
| `in_sample_preds` | 0.0 | PASS (exact) |
| `intercept` | 0.0 | PASS (exact) |
| `n_support_match` | — | PASS (TSL=178, ref=178) |

**Outcome:** byte-identical agreement on predictions,
intercept, and support-vector count. sklearn SVR's libsvm
SMO optimizer is deterministic from a fixed initialization
(no random state in the optimizer; convergence is
deterministic given identical inputs + hyperparameters).

## Fixture

- DGP: AR(1), φ=0.6, σ=1.0, T=200, seed=42
- 6 lag features (StandardScaler-transformed; SVR is
  scale-sensitive)
- Fast preset: kernel='rbf', C=1.0, epsilon=0.1, gamma='scale'

## Pattern H DSCD ruled out

Original Batch 8 hypothesis (per S12 prompt): SVR vs sklearn
likely DSCD-MLE due to cross-library optimizer divergence.
**Empirical result:** ruled out — same-library means same
libsvm SMO; bit-exact parity, no DSCD divergence. Pattern H
DSCD remains 4 wrappers cumulatively (LLT identifiability +
Markov switching + GARCH boundary attractor + ETS scale
offset; no Batch 8 addition).
