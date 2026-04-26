# Calibration Audit: evt_pot_gpd

**Audit date:** 2026-04-26
**Commit:** (assigned at E8)
**Auditor:** Claude (driven mode)
**Wrapper audited:** `engine/techniques/evt_pot_gpd.py`

## Summary

Third per-wrapper audit under the Calibration Audit Initiative
Phase 2 (CAI Phase 2 Session 3). Three audit techniques
executed (parameter sweep with 4 sub-sweeps centered on
threshold-percentile, real-data stress on 5 macro series,
adversarial canonical extension with 4 new cases).

**Findings: 0 severe / 0 operational / 1 cosmetic.** The
single cosmetic finding (F-E-T3-2-COSMETIC) documents the
well-known small-sample bias of the GPD MLE shape parameter
(Castillo & Padilla 2015). The wrapper's bootstrap 95% CI
correctly contains the truth on a known-Pareto fixture,
demonstrating that uncertainty estimates are calibrated even
when the point estimate is biased.

**No findings on the wrapper itself.** evt_pot_gpd's GPD
fitting, threshold-quantile handling, declustering cascade,
sample-size guard (n_exceedances < 10), and bootstrap CIs
all behave correctly across the entire sweep matrix and on
all 5 macro series. The wrapper appropriately refuses to fit
on degenerate inputs and produces wide CIs on small samples,
preventing silent overconfidence.

## Technique 1: Parameter Sweep

Four sub-sweeps over the wrapper's user-settable parameters
on a synthetic AR(1)+GARCH baseline (T=2000, Student-t(df=4)
innovations, seed=42) — designed to produce heavy-tailed data
where xi should land in (0, 0.5) at typical percentiles.

### Sweep 1: `threshold_quantile` (CENTERPIECE)

**Range tested:** {0.80, 0.85, 0.90, 0.925, 0.95, 0.975, 0.99, 0.995}
**Default value:** 0.975

| q | xi | sigma | n_exceedances | KS p-value | elapsed_s |
|---|---|---|---|---|---|
| 0.80 | 0.176 | 0.544 | 400 | 0.747 | 6.06 |
| 0.85 | 0.210 | 0.539 | 300 | 0.820 | 8.17 |
| 0.90 | 0.208 | 0.590 | 200 | 0.541 | 7.56 |
| 0.925 | 0.272 | 0.554 | 150 | 0.657 | 8.00 |
| 0.95 | 0.437 | 0.479 | 100 | 0.881 | 7.94 |
| 0.975 | 0.211 | 0.889 | 50 | 0.954 | 7.22 |
| 0.99 | 0.485 | 0.704 | 20 | 0.957 | 8.66 |
| 0.995 | 0.239 | 1.352 | 10 | 0.765 | 12.18 |

**Observations:**
- All 8 percentiles converge successfully (no GPD-fit failures).
- xi varies from 0.18 to 0.49 across the sweep — a 2.7×
  variation typical of GPD MLE on small effective samples.
- **No sign flips.** All xi estimates are positive (data is
  genuinely heavy-tailed; expected sign is consistent).
- KS p-values uniformly > 0.5 (good GPD fit at all thresholds).
- Runtime per call 6-12s (bootstrap-dominated; Balanced preset
  uses 500 bootstrap samples).
- N_exceedances scales linearly with (1 - q) as expected.

**Findings:** None. The xi instability across percentiles is
the expected behavior of GPD MLE — well-documented as
threshold-selection sensitivity and the practitioner's
fundamental challenge in EVT (Coles 2001 §4.3).

### Sweep 2: `tail` (upper vs lower)

| tail | xi | sigma | n_exceedances |
|---|---|---|---|
| upper | 0.211 | 0.889 | 50 |
| lower | 0.022 | 0.813 | 50 |

Asymmetry between tails is expected on the heavy-tailed
synthetic baseline. Both tails fit cleanly.

**Findings:** None.

### Sweep 3: `decluster` (False vs True)

| decluster | xi (pre) | xi (post) | extremal_index_θ | K (post) | elapsed_s |
|---|---|---|---|---|---|
| False | 0.437 | — | — | — | 8.81 |
| True | 0.437 | 0.429 | 0.775 | 78 | 17.70 |

Ferro-Segers extremal index θ=0.775 indicates moderate volatility
clustering. K=78 cluster peaks identified from N_u=100
exceedances (reduction ratio 0.78). xi post-declustering shifts
mildly (0.437 → 0.429). The cascade fires cleanly.

**Findings:** None.

### Sweep 4: `confidence_levels`

| label | levels | VaR values |
|---|---|---|
| default | [0.95, 0.99, 0.999] | [1.20, 2.67, 5.87] |
| conservative | [0.99, 0.999, 0.9999] | [2.67, 5.87, 11.05] |
| liberal | [0.90, 0.95, 0.99] | [0.70, 1.20, 2.67] |
| single_99 | [0.99] | [2.67] |

VaR values scale appropriately with quantile level. Internal
consistency: VaR at 0.99 produces 2.67 across all three sets
that include it.

**Findings:** None.

## Technique 2: Real-Data Stress Test

All 5 macro series ran successfully at default Balanced preset
with default `threshold_quantile=0.975`. Preprocessing per
series:
- **GSPC, DEXUSEU:** 100·log returns, lower tail (loss tail)
- **GOLD:** 100·log returns, upper tail (upside crisis spikes)
- **DGS10, DGS2:** yield first-differences, upper tail

| Series | Preprocessing | Tail | T | xi | sigma | n_exc | exc_rate | KS p | elapsed_s |
|---|---|---|---|---|---|---|---|---|---|
| GSPC | log_returns | lower | 2514 | 0.255 | 0.939 | 63 | 0.0251 | 0.754 | 5.69 |
| DGS10 | yield_diffs | upper | 2500 | 0.059 | 0.031 | 58 | 0.0232 | 0.135 | 8.51 |
| DGS2 | yield_diffs | upper | 2500 | -0.163 | 0.063 | 61 | 0.0244 | 0.560 | 8.22 |
| DEXUSEU | log_returns | lower | 2498 | 0.010 | 0.293 | 63 | 0.0252 | 0.896 | 7.28 |
| GOLD | log_returns | upper | 2512 | 0.072 | 0.713 | 63 | 0.0251 | 0.996 | 5.81 |

**Observations:**
- All 5 series converge with finite xi, sigma, KS p-values.
- Exceedance rates within 0.023-0.025 — close to the nominal
  1 − 0.975 = 0.025. Wrapper's threshold logic correct.
- **xi signs:** 4 of 5 positive (GSPC, DGS10, DEXUSEU, GOLD —
  consistent with heavy-tailed return distributions). DGS2
  shows xi=-0.163 (bounded right tail; plausible since yield
  changes are volatility-coupled and policy-floor truncated).
- KS p-values: DGS10 borderline at 0.135 (does not reject
  GPD; weakest fit of the 5). All others > 0.55 indicate
  good GPD fits.
- Runtime well under the 30s budget — slowest call DGS10 at
  8.5s on T=2500.

**Baseline established** for future-session regression
anchoring. Subsequent CAI sessions revisiting evt_pot_gpd on
these series can use the xi/sigma/KS-p values as anchors at
the documented preprocessing + Balanced preset combo.

**Findings:** None.

## Technique 3: Adversarial Canonical Extension

Four new canonicals appended as `canonical_6` through
`canonical_9` in `tools/validate_evt_declustering_canonicals.py`
(per existing 1-5 numbering convention; CAL-R4).

### canonical_6 (C-CAL-1): Gaussian baseline N(0,1) T=2000

**Adversarial scenario:** Gaussian (true xi=0); tests GPD MLE
behavior on a thin-tailed input.
**Expected behavior:** xi within finite-sample bias range
(±0.5 envelope on T=2000 Gaussian).
**Observed behavior:** status=success, xi=-0.302, n_exc=50,
KS p=0.994. xi within envelope; GPD fit accepted by KS.

**Findings:** None. xi=-0.30 on Gaussian is within the
documented finite-sample bias range for GPD MLE on thin-tailed
data (the GPD is misspecified for Gaussian tails which decay
faster than any Pareto power; the MLE absorbs this via a
negative shape estimate).

### canonical_7 (C-CAL-2): Known Pareto a=2 (xi=0.5) T=2000

**Adversarial scenario:** Pareto with α=2 (so true xi=1/α=0.5);
tests GPD MLE recovery and bootstrap CI calibration on a
known heavy-tailed input.
**Expected behavior:** Point xi may be biased (small-N MLE),
but bootstrap 95% CI must contain the truth.
**Observed behavior:** status=success, xi point=0.156,
bootstrap 95% CI [-0.274, 0.526], **truth xi=0.5 IS inside the
CI** (uncertainty calibrated despite biased point).

**Findings:** F-E-T3-2-COSMETIC (cosmetic) — see findings table.

### canonical_8 (C-CAL-3): Mixture 95% N(0,1) + 5% Pareto T=1500

**Adversarial scenario:** Heterogeneous body+tail distribution;
demonstrates threshold-dependence of EVT.
**Expected behavior:** Low threshold (q=0.85) — Gaussian body
contaminates; KS rejects GPD. High threshold (q=0.99) — pure
Pareto tail emerges; KS accepts GPD.
**Observed behavior:** status=success at both thresholds.
- q=0.85: xi=0.263, KS p=8×10⁻⁶ (REJECTS GPD; body contamination)
- q=0.99: xi=0.287, KS p=0.919 (clean GPD on pure tail)

**Findings:** None. The threshold-dependence is the expected
property; the wrapper correctly surfaces the KS p-value so
users can detect body contamination via the goodness-of-fit
diagnostic.

### canonical_9 (C-CAL-4): Short series degeneracy T=150 Pareto(1.5)

**Adversarial scenario:** T=150 with heavy-tailed Pareto(1.5);
tests whether the wrapper silently produces overconfident
estimates on degenerate inputs.
**Expected behavior:** Either (a) status=failure on the
n_exceedances < 10 guard, OR (b) status=success with bootstrap
CI wide enough (width ≥ 0.3) to NOT silently overconfident-
estimate.
**Observed behavior:** status=failure with explicit error
message: *"Only 8 exceedances above threshold 6.8048. Need
at least 10 for reliable GPD fitting."* The wrapper's hard
guard (`n_exceed < 10` at line 120 of `evt_pot_gpd.py`)
fired correctly.

**Findings:** None. **This is the explicit safety property
we wanted to verify** — the wrapper does NOT silently
overfit on too-small samples. The error message also
points users to actionable remediation (lower
threshold_quantile or provide longer series).

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-E-T3-2-COSMETIC | Cosmetic | GPD MLE point xi=0.156 off Pareto truth=0.5 by 0.34 at default q=0.975 / N_exc=50; bootstrap 95% CI correctly contains truth | Documented; no wrapper change. Known small-N bias per Castillo & Padilla 2015. |

No findings on the wrapper itself. evt_pot_gpd's GPD fitting,
threshold logic, sample-size guard, and bootstrap CI machinery
all behave correctly.

## Threshold-selection guidance for users

Surfaced from this audit's calibration findings (T1 Sweep 1 +
canonical_8 mixture-distribution case + literature):

1. **Default threshold_quantile=0.975** is reasonable for typical
   financial return series at T≥1000 — produces ~25 exceedances
   per 1000 observations, balancing bias vs variance per
   Coles 2001 §4.3.

2. **Run a threshold-quantile sweep** before fixing the threshold.
   The wrapper's "Mean Excess Function" and "Threshold-Stability"
   tables (already produced; see `n_thresholds_plot` config)
   show xi/sigma stability across thresholds. A "stable plateau"
   indicates the GPD assumption holds; instability indicates
   the threshold is too low (body contaminating) or too high
   (sample-size noise dominating).

3. **Inspect the KS p-value** as a goodness-of-fit screen.
   Canonical_8 demonstrates: a low p-value (< 0.05) at moderate
   thresholds is a clear signal of body contamination —
   raise the threshold until p > 0.05.

4. **At small effective samples (N_exc < 100), trust the
   bootstrap 95% CI, not the xi point estimate.** Castillo &
   Padilla 2015 document substantial small-N bias on the GPD
   shape MLE; canonical_7 demonstrates this directly. Wide CIs
   are correctly calibrated, point estimates may be biased.

5. **At T < 200 with q ≥ 0.95**, expect the n_exceedances < 10
   guard to fire. This is intentional — EVT requires sufficient
   tail observations. Either lower the threshold (more bias,
   less variance) or accept that the data is too short for
   reliable GPD fitting.

6. **For volatility-clustered series (financial returns),
   consider `decluster=True`** to apply Ferro-Segers intervals
   declustering. The audit's T1 Sweep 3 confirmed extremal
   index θ ≈ 0.775 on the AR(1)+GARCH baseline, indicating
   moderate clustering — declustering shifts xi mildly but
   produces more conservative (cluster-peak-based) VaR estimates
   that better reflect the true tail risk of clustered processes.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | Wrapper params verified by inspecting `engine/techniques/evt_pot_gpd.py`: actual user-settable params are `tail`, `threshold_value`, `threshold_quantile`, `confidence_levels`, `decluster`. Handoff §3.3's `declustering_method`, `cluster_separation`, `min_exceedances` are NOT user params — declustering uses internal Ferro-Segers, cluster ID is internal logic, min_exceedances is enforced via the hard `n_exceed < 10` guard at line 120. Sweep design adjusted: 4 sweeps cover the actual user surface. |
| **CAL-R3** | `docs/calibration_audit_status.md` updated: evt_pot_gpd PENDING → AUDITED with link to this findings doc. |
| **CAL-R4** | Existing canonicals 1-5 in `validate_evt_declustering_canonicals.py`. New adversarial cases appended as 6-9 matching convention; docstrings tag them C-CAL-1 through C-CAL-4 for cross-reference. |
| **CAL-R5** | Real-data baselines for the 5 macro series under the documented preprocessing + Balanced preset combo recorded in Technique 2 table; subsequent CAI sessions revisiting evt_pot_gpd can use as regression anchors. |
| **CAL-R6** | No fixes required. 0 severe / 0 operational findings. The single cosmetic finding documents a literature-known property; no code change. |

## Recommended follow-ups

None required. The wrapper is clean.

For future calibration cycles:

- Consider exposing bootstrap CIs in `audit_fields` (currently
  CIs are in the GPD Parameters output table only). This would
  make programmatic uncertainty extraction easier for downstream
  callers but is a documentation-only improvement, not a
  correctness issue.
- Consider documenting the threshold-selection guidance from
  this findings doc in `resources/techniques_md/evt_pot_gpd.md`
  if the wrapper's user-facing markdown does not already cover
  it. (Out of scope for this commit; check at next markdown
  sweep.)
- Phase 1 verification initiative's 3c parity test (Ferro-Segers
  extremal index) already validates the declustering math at
  1e-6 tolerance vs `extRemes::extremalindex`. The CAI complement
  here (Sweep 3 + canonical exposure) confirms the cascade
  integration with default-parameter behavior.
