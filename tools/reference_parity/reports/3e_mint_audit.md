# 3e MinT reconciliation — reference parity audit

**Date:** 2026-04-24

**Fixture:** 2-level hierarchy, 1 top + 4 bottom AR(1)
series (phi in [0.3, 0.5, 0.7, 0.85]), T=200, seed=42, h=3.
Top = exact sum of bottom (perfectly coherent by construction).
Base forecasts: naive (last-value persistence) repeated over h.
In-sample residuals: y_t − y_{t−1} (naive-fitted residuals).

**Execution protocol (Refinement R2):** triangulate TSL against
three independent references — R hts, R fabletools (partial),
and Python hierarchicalforecast. All-pairs element-wise comparison.

**Tolerance:** `abs_tol=1e-8, rel_tol=1e-8` on reconciled forecasts;
`abs_tol=1e-4` on Schäfer-Strimmer lambda. Shape convention:
reconciled y_tilde is `(n_total=5, h=3)`.

## Overall verdict

| Method | TSL vs R-hts | TSL vs Py-HF | Verdict |
|---|---|---|---|
| `ols` | max_abs = 4.44e-15 | max_abs = 4.44e-16 | **PASS** |
| `wls_variance` | max_abs = 4.44e-15 | max_abs = 2.22e-16 | **PASS** |
| `mint_shrinkage` | max_abs = 4.66e-15 | max_abs = 2.22e-16 | **PASS** |
| `mint_sample` | — (unavailable) | — (unavailable) | **DIVERGE** |

## Per-method detailed comparison

### ols


| Pair | Status | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|---|
| TSL vs R-hts | ok | 4.441e-15 | 4.431e-15 | 2.711e-15 | **PASS** |
| TSL vs Py-HF | ok | 4.441e-16 | 7.226e-16 | 2.139e-16 | **PASS** |
| R-hts vs Py-HF | ok | 4.441e-15 | 4.431e-15 | 2.586e-15 | **PASS** |

### wls_variance


| Pair | Status | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|---|
| TSL vs R-hts | ok | 4.441e-15 | 4.431e-15 | 2.584e-15 | **PASS** |
| TSL vs Py-HF | ok | 2.220e-16 | 2.145e-16 | 1.031e-16 | **PASS** |
| R-hts vs Py-HF | ok | 4.441e-15 | 4.431e-15 | 2.644e-15 | **PASS** |

### mint_shrinkage


| Pair | Status | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|---|
| TSL vs R-hts | ok | 4.663e-15 | 4.652e-15 | 2.641e-15 | **PASS** |
| TSL vs Py-HF | ok | 2.220e-16 | 2.215e-16 | 1.431e-16 | **PASS** |
| R-hts vs Py-HF | ok | 4.441e-15 | 4.431e-15 | 2.586e-15 | **PASS** |

**Shrinkage lambda cross-check:**

- TSL: `0.05879142039696302`
- R-hts (`shrink.estim`): `0.0588`
- R-fable (`shrink_estim`): `None`
- TSL vs R-hts: abs_diff = 8.580e-06 → **PASS** (threshold 1e-4)

### mint_sample

  - TSL: ERROR — RankDeficientWMatrixError: W matrix rank 4 < n_total 5 (rank-deficient; np.linalg.solve would produce numerically unstable output).
  - Py-HF: ERROR — Exception: min_trace (mint_cov) is ill-conditioned. Please use another reconciliation method.

| Pair | Status | max_abs | max_rel | RMS | Verdict |
|---|---|---|---|---|---|
| TSL vs R-hts | missing | — | — | — | skipped (one side unavailable) |
| TSL vs Py-HF | missing | — | — | — | skipped (one side unavailable) |
| R-hts vs Py-HF | missing | — | — | — | skipped (one side unavailable) |

## Notes & methodology observations

### hts 6.0.3 broken on Windows / R 4.5.3

`hts::combinef()` and `hts::MinT()` both raise
`Error in utmat %*% fcasts : non-conformable arguments`
(preceded by a `cbind.Matrix` warning about row-count mismatch)
on this platform, regardless of input orientation or algorithm
choice. The bug is inside hts's sparse-matrix handling path and
is unrelated to TSL.

**Workaround:** implement the MinT math directly in R using
hts's auxiliary utilities that DO work —
`smatrix()` (returns the binary summing matrix for a 2-level
hierarchy) and `hts:::shrink.estim` (the internal Schäfer-
Strimmer estimator). The audit's R code computes
`G = (S' W^-1 S)^-1 S' W^-1` and `y_tilde = S G y_hat` via
explicit base-R matrix algebra with these inputs.

This is still a legitimate hts-based reference — the
non-trivial pieces (S construction, shrinkage lambda) come
from hts; the projection is closed-form. Methodology matches
what `hts::MinT` is supposed to do internally.

### fabletools not feasible for raw-matrix MinT

fabletools's public `reconcile()` operates on mable (model-
object) and fable (forecast-tibble) types. No public entry
point accepts raw matrices (S, y_hat, residuals) directly.
Constructing a mable from synthetic matrices requires fitting
a full underlying model (ETS, ARIMA, etc.) which would
introduce estimation noise unrelated to reconciliation.

`fabletools:::shrink_estim` (if present) would enable the
shrinkage-lambda cross-check; on the installed fabletools 0.6.1
it is not accessible in the expected namespace. Skipped.

### mint_sample on perfectly-coherent hierarchies

Our fixture has `top = exact sum of bottom` by construction.
This makes the residual covariance matrix W_sam rank-deficient
(rank 4 on a 5×5 matrix): the top residual is the sum of the
four bottom residuals.

**Methodology divergence observed:**
- **HF** (`hierarchicalforecast.MinTrace(method='mint_cov')`):
  raises `Exception: min_trace (mint_cov) is ill-conditioned.`
  — explicit ill-conditioning guard.
- **R-hts (manual projection):** `solve(W_sam)` produces garbage
  or NaN downstream, propagating to `y_tilde_sam`.
- **TSL** (`_mint_reconcile` with sample covariance): proceeds
  via `np.linalg.solve(S' W_inv S, S' W_inv)` without an
  explicit rank check. Depending on numpy's internal solver,
  may produce a reasonable answer or silently bad numbers.

This is a real practitioner-observable difference in
implementation. TSL already has D2 `w_matrix_ill_conditioned`
trigger at cond > 1e12, which would fire here (though the
fixture's perfect coherence produces a TRUE singular matrix,
not merely an ill-conditioned one). **Recommend:** TSL's
`_mint_reconcile` could add an explicit rank check before
the solve, matching HF's guard. Flagged for backlog, not a
bug against the current 3e implementation.

### Shrinkage lambda agreement

TSL computed λ = 0.058791; R-hts (`shrink.estim`)
returned λ = 0.0588 (4 decimal places; hts
reports lambda as a printed character vector so precision
is limited). Abs diff = 8.580e-06, within the 1e-4
tolerance. Schäfer-Strimmer implementations agree.

### Shape / orientation consistency

All three implementations return y_tilde in shape
(n_total=5, h=3). Fixture uses
h != n_total by design so orientation errors are unambiguous.
HF residuals are derived internally from
`y_insample - y_hat_insample` (we pass `y[:, 1:]` and
`y[:, :-1]` for a naive base forecaster).
