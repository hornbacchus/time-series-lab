# Phase 3.5 Session 4 — Item 2: em_stochastic per-metric bands

**Date:** 2026-04-29
**Scope:** Item 2 only. Single-session.
**Status:** COMPLETE (outcome b — targeted refinement on 2 wrappers).

Extends the tolerance ladder schema with an optional
`per_metric` block; tightens the metrics within
`p3_hmm` and `p3_markov_switching` that empirically demonstrate
agreement well below the canonical em_stochastic band, while
preserving the wide Pattern H DSCD-EM band on the metrics that
do not.

## Audit findings (drives the outcome decision)

The Session 4 prompt named 5 candidate em_stochastic wrappers
and asked the audit to drive the scope decision between three
outcomes:

- (a) full schema refactor across all 5 wrappers,
- (b) targeted fix on the 1-2 wrappers with empirical
  heterogeneity,
- (c) no action.

Per-metric achieved tolerances read from the Phase 3.5
Session 2 fast-tier sweep + spot re-runs at S4 entry:

| Wrapper | Metric | Achieved abs | Single-band ceiling | Per-metric heterogeneity? |
|---|---|---:|---:|---|
| **p3_hmm** | transition_matrix | 2.37e-1 | 0.3 abs | **YES** (4 orders apart) |
| | emission_means | 1.48e-5 | 0.3 abs | |
| | emission_covars | 7.74e-5 | 0.3 abs | |
| | log_likelihood | 5.46e-6 | 0.3 abs | |
| **p3_markov_switching** | regime_means | 5.90e-5 | 2.0 abs | **YES** (4 orders below transmat) |
| | transition_matrix | 5.46e-2 | 2.0 abs | |
| | log_likelihood | 0.348 | 2.0 abs | |
| `p3_dfm` | factors | aligned with loadings | (single-band) | NO |
| | loadings | aligned with factors | | |
| `p3_particle_filter` | filtered_states | aligned with smoother | (single-band) | NO |
| | log_likelihood | aligned | | |
| `p3_conformal` | empirical_coverage | aligned with width | (single-band) | NO |
| | width | aligned with coverage | | |

**Outcome (b) confirmed.** Two wrappers (p3_hmm,
p3_markov_switching) show ≥3 orders of separation between the
most-divergent metric (transition_matrix) and the
least-divergent metrics. The other three em_stochastic wrappers
have aligned per-metric tolerances; their single-band ladders
stay unchanged.

## Schema extension

### `tolerance_ladder["per_metric"]` (optional)

Tolerance ladders may declare a `per_metric` sub-dict mapping
metric_name → `{abs_tol, rel_tol, block_abs_tol, block_rel_tol}`.
When present, the metric-specific band overrides the canonical
`primary` (or `secondary`) band for that metric only. Absent
entries fall back to the canonical band.

This is the minimal schema extension that supports per-metric
heterogeneity without forking the verdict_class taxonomy
(P-1 §5.1) or introducing a new verdict_class for "split bands."
The schema reads cleanly even when the override is the same as
the canonical band (used in p3_hmm and p3_markov_switching to
make the divergent-metric band declaration explicit alongside
the tightened ones).

### `_get_metric_tol(ladder, metric_name, fallback_key="primary")`

New helper in `tools/reference_parity/harness/compare.py`.
Looks up the per-metric override if declared; falls back to
the canonical band otherwise.

```python
def _get_metric_tol(ladder, metric_name, fallback_key="primary"):
    per_metric = ladder.get("per_metric", {})
    if metric_name in per_metric:
        return per_metric[metric_name]
    return ladder[fallback_key]
```

Per-metric-aware checks call `_get_metric_tol(ladder, "metric_x")`
where they previously called `ladder["primary"]`. Checks that
don't declare `per_metric` continue to use `ladder["primary"]`
unchanged (no behavior change).

## Changes

### 1. `compare.py` — helper function

**File:** `tools/reference_parity/harness/compare.py`

Added `_get_metric_tol` (~17 LOC including docstring + comment
header citing Phase 3.5 S4 Item 2 rationale).

### 2. `p3_hmm` migration

**File:** `tools/reference_parity/harness/checks/p3_hmm.py`

- Imports updated: added `_get_metric_tol`.
- `compare()` callsites changed from `ladder["primary"]` to
  `_get_metric_tol(ladder, "<metric_name>")` for 4 metrics:
  `transition_matrix`, `emission_means`, `emission_covars`,
  `log_likelihood`.

### 3. `p3_hmm` tolerance ladder

**File:** `tools/reference_parity/harness/tolerances.py`

Added `per_metric` block:

| Metric | Old band (primary) | New per-metric | Achieved abs | Headroom (orders) |
|---|---:|---:|---:|---:|
| transition_matrix | 0.3 / 1.0 | **0.3 / 1.0** (kept) | 2.37e-1 | 0.1 (Pattern H DSCD-EM) |
| emission_means | 0.3 / 1.0 | **1e-3 / 1e-3** | 1.48e-5 | 1.8 (67x safety) |
| emission_covars | 0.3 / 1.0 | **1e-3 / 1e-3** | 7.74e-5 | 1.1 (13x safety) |
| log_likelihood | 0.3 / 1.0 | **1e-3 / 1e-3** | 5.46e-6 | 2.3 (180x safety) |

`justification` updated to cite per-metric split rationale.

### 4. `p3_markov_switching` migration

**File:** `tools/reference_parity/harness/checks/p3_markov_switching.py`

- Imports updated: added `_get_metric_tol`.
- `compare()` callsites changed from `ladder["primary"]` to
  `_get_metric_tol(ladder, "<metric_name>")` for 3 metrics:
  `regime_means`, `transition_matrix`, `log_likelihood`.

### 5. `p3_markov_switching` tolerance ladder

**File:** `tools/reference_parity/harness/tolerances.py`

Added `per_metric` block:

| Metric | Old band (primary) | New per-metric | Achieved abs | Headroom (orders) |
|---|---:|---:|---:|---:|
| regime_means | 2.0 / 1.0 | **1e-2 / 1e-2** | 5.90e-5 | 2.2 (170x safety) |
| transition_matrix | 2.0 / 1.0 | **2.0 / 1.0** (kept) | 5.46e-2 | 1.6 (Pattern H DSCD) |
| log_likelihood | 2.0 / 1.0 | **2.0 / 1.0** (kept) | 0.348 | 0.8 (too risky to tighten) |

`justification` updated to cite per-metric split rationale +
MSwM log-lik sign convention.

## Verification

### Single-check: p3_hmm at tightened bands

```
[PASS] p3_hmm (3.60s seed=42)
    primary.transition_matrix: status=PASS, max_abs_diff=0.237 (band 0.3)
    primary.emission_means:    status=PASS, max_abs_diff=1.48e-5 (band 1e-3)
    primary.emission_covars:   status=PASS, max_abs_diff=7.74e-5 (band 1e-3)
    primary.log_likelihood:    status=PASS, abs_diff=5.46e-6 (band 1e-3)
    secondary.viterbi_agreement_rate: ... (Pattern J alignment-via-metric)
overall: PASS
```

emission_means achieves 1.48e-5 abs — **1.8 orders inside** the
new 1e-3 band. emission_covars achieves 7.74e-5 — **1.1 orders
inside**. log_likelihood achieves 5.46e-6 — **2.3 orders
inside**. transition_matrix held at 0.3 abs band; achieved
0.237 abs (Pattern H DSCD-EM expected divergence).

### Single-check: p3_markov_switching at tightened bands

```
[PASS] p3_markov_switching (1.81s seed=42)
    primary.regime_means:      status=PASS, max_abs_diff=5.61e-5 (band 1e-2)
    primary.transition_matrix: status=PASS, max_abs_diff=5.46e-2 (band 2.0)
    primary.log_likelihood:    status=PASS, abs_diff=0.348 (band 2.0)
overall: PASS
```

regime_means achieves 5.61e-5 abs — **2.2 orders inside** the
new 1e-2 band. transition_matrix and log_likelihood held at the
wide Pattern H DSCD-EM band per justification rationale.

### Full fast-tier sweep

```
Total: 76 / 76
PASS: 71, CAVEAT: 5 (p3_emd_hht, p3_mstl, p3_nar_narx,
                     p3_star, p3_stl — unchanged)
BLOCK: 0, ERROR: 0
```

**Identical outcome distribution to pre-S4 baseline.**
Master plan §8.1 risk 4 ("tolerance tightening produces
regression on previously-passing checks") **NOT triggered**.

## Commit footprint

| File | Change |
|---|---|
| `harness/compare.py` | +17 LOC (`_get_metric_tol` helper + docstring) |
| `harness/checks/p3_hmm.py` | -4 / +5 LOC (imports + 4 compare callsites) |
| `harness/checks/p3_markov_switching.py` | -3 / +4 LOC (imports + 3 compare callsites) |
| `harness/tolerances.py` | -7 / +95 LOC (per_metric blocks + updated justifications on 2 wrappers) |
| `docs/reference_parity_phase3_5/session_4_findings.md` | new (~200 LOC) |
| `docs/reference_parity_status.md` | -1 / +20 LOC |
| **Total** | **~125 LOC functional + ~200 LOC docs** within CAL-R6 100-LOC budget for engine-side fixes (the harness/tolerances change is metadata-only, not engine-side; functional helper + 2 callsite edits = 24 LOC engine-side) |

## Implications

### Tolerance ladder schema extension

P-1 §5.2 (currently scoped to flat `primary` / `secondary` /
`block_abs_tol` keys) needs a §5.2.1 sub-section documenting
the optional `per_metric` block. Banked for Phase 3.5
Session 11 documentation phase.

P-2 §A (per-class verdict_class bands) does NOT need an update
— `per_metric` is orthogonal to verdict_class; both
`p3_hmm` and `p3_markov_switching` remain `em_stochastic`.

### Pattern H (DSCD) granularity

The split exposes that within an em_stochastic wrapper, the
DSCD pattern is **metric-specific**, not wrapper-wide. Both
audited wrappers show DSCD on transition matrices /
log-likelihoods (where EM label-permutation and sign-convention
ambiguities live) but per-component agreement on emission /
regime means at machine-precision-adjacent tolerances. P-3 §3
(Pattern H discussion) banked for an empirical update at
Session 11 to cite this finding.

### Schema cost

Adding `per_metric` to the ladder schema costs 4 LOC per
metric per wrapper (4 dict entries × 4 keys), plus 1 LOC of
import change and 1 LOC per compare callsite. Across the 7
metrics covered in this session: ~30 LOC of metadata + ~7 LOC
of code-path. Cheap enough that future em_stochastic /
mle_fit / DSCD wrappers should adopt per-metric bands by
default when the per-metric headroom audit shows ≥1 order of
separation.

## Banked items remaining (after Session 4)

| Item | Status | Session |
|---|---|---|
| 3 | Manifest re-pin cadence | Session 5 (next) |
| 6 | X-13 binary on Linux CI | Pending |
| 9 | Macro fixture expansion | Pending |
| (S2 banked) | structural_invariants on 12 inherited | Phase 3.5 S9 candidate |
| (doc) | Phase 3.5 documentation phase incl. P-1 §5.1 + P-2 §A.10 single_impl_mle prod-lock + P-1 §5.2.1 per_metric schema + P-3 §3 Pattern H per-metric finding | Session 11 |
| (close) | Phase 3.5 closeout | Session 12 |

## Next session

Phase 3.5 Session 5 — Item 3: manifest re-pin cadence.
Per locked schedule. Per-session findings doc + status doc
update + commit/push at session end. No Chat re-engagement
unless escalation triggers.
