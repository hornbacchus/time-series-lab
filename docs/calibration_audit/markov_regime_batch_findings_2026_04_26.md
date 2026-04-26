# Calibration Audit: Markov / Regime family batch (Session 12)

**Audit date:** 2026-04-26
**Commit:** (assigned at commit step)
**Auditor:** Claude (driven mode)
**Wrappers audited (5):**
  - `engine/techniques/hmm_model.py` (hmmlearn)
  - `engine/techniques/markov_switching.py` (statsmodels)
  - `engine/techniques/tar_setar.py` (handles `tar` + `setar`)
  - `engine/techniques/star_model.py` (LSTAR/ESTAR)
  - `engine/techniques/nar_narx.py` (handles `nar` + `narx`;
    sklearn MLPRegressor)

## Summary

Seventh extension audit (CAI Phase 2 Session 12). Largest
batch yet — 5 wrappers in one session.

**Findings: 1 severe (FIXED INLINE) / 0 operational / 0
cosmetic.** Total cumulative engine-fix LOC: 20.

The single severe finding (F-MR-STAR-TYPE) follows the
exact Session 9/10 silent-acceptance pattern: STAR accepted
any string for `star_type` (uppercased and threaded through
to the internal `_fit_star` function which defaulted to
LSTAR for unknown values), reporting the user's invalid
input in audit_fields. Fixed with explicit allowlist check.

## Sweep 0 — Per-wrapper dispatch + input-validation matrix

| Wrapper | Probe | Result |
|---|---|---|
| HMM | baseline (hmm) | ✅ success |
| HMM | invalid covariance_type='zzz' | ✅ failure (hmmlearn rejects via fit-restart cascade) |
| markov_switching | baseline | ✅ success |
| tar_setar | dispatch via technique_id='setar' | ✅ success |
| **star** | baseline (LSTAR) | ✅ success |
| **star** | **invalid star_type='zzz'** | **PRE-FIX: SUCCESS WITH audit='ZZZ'** ❌ → **POST-FIX: failure with allowlist error** ✅ |
| nar_narx | dispatch via technique_id='nar' | ✅ success |
| nar_narx | NARX path with exog | ✅ success |

## Severe finding

### F-MR-STAR-TYPE (severe; fixed inline)

**Title:** `star` accepted invalid `star_type` strings silently;
audit_fields reported the user's invalid value.

**Reproduction (pre-fix):**
```python
ctx = RunContext({..., "technique_id": "star",
                  "params": {"star_type": "zzz", "ar_order": 1}})
res = star_mod.run(ctx, ...)
# res.status = "success"
# res.audit_fields["star_type"] = "ZZZ"  (uppercased user input)
```

**Root cause:** `star_model.py` line 87 (pre-fix):
```python
star_type = ctx.get_param("star_type", cfg["star_type"]).upper()
# ... no validation ...
types_to_fit = ["LSTAR", "ESTAR"] if star_type == "BOTH" else [star_type]
```
When `star_type="ZZZ"`, `types_to_fit=["ZZZ"]` and the
internal `_fit_star` function defaulted to LSTAR-style fitting
without raising. The audit_field then reported "ZZZ".

**Fix:** ~20 LOC at line 87. Explicit allowlist check
parallel to caviar's `specification` validation pattern:
```python
_STAR_TYPES = ("LSTAR", "ESTAR", "BOTH")
if star_type not in _STAR_TYPES:
    return make_error_response(ctx, f"Unknown star_type '{star_type}'...")
```

**Verification post-fix:**
- canonical_5 in `validate_star_canonicals.py` is the
  permanent regression guard
- Audit's Sweep 0 confirms post-fix rejection works

## Technique 1: Parameter sweeps (compact)

5 wrappers × ~2 sweeps each on synthetic fixtures:

| Sweep | Best by IC | Comment |
|---|---|---|
| HMM n_components ∈ {2, 3} | n=2 wins (AIC=1316 vs 1322) | correctly identifies 2-regime DGP |
| markov_switching k_regimes ∈ {2, 3} | k=2 wins (AIC=1314 vs 1319) | |
| tar_setar n_regimes ∈ {2, 3} | n=2 wins on threshold DGP | |
| STAR star_type {LSTAR, ESTAR} | identical AIC (-30.9) on this fixture | both transition functions can fit; expected |
| NAR ar_lags ∈ {2, 5} | both succeed | runtime <1s |

## Technique 2: Real-data stress (subsampled to T=500)

5 wrappers × 2 series (GSPC log returns, DGS10 yield level):

| Series | Wrapper | AIC | Runtime |
|---|---|---|---|
| GSPC | hmm | 1274 | 0.8s |
| GSPC | markov_switching | 1267 | 0.9s |
| GSPC | setar | -75 | 0.1s |
| GSPC | star | 2.2 | 1.0s |
| GSPC | nar | — | 0.9s |
| DGS10 | hmm | -197 | 0.5s |
| DGS10 | markov_switching | -198 | 0.4s |
| DGS10 | setar | -2739 | 0.0s |
| DGS10 | star | -2751 | 1.2s |
| DGS10 | nar | — | 1.0s |

All 10 cells succeed. Runtimes all under 1.5s. AIC
inter-comparison meaningful within wrapper but NOT across
wrappers (different dependent-variable construction in
different wrapper conventions).

## Technique 3: Adversarial canonicals

| C-CAL | Case | Outcomes |
|---|---|---|
| 1 | Constant series y=5.0 T=200 (5 wrappers) | hmm/setar/nar succeed; markov_switching+star fail (cleanly — variance==0 boundary) |
| 2 | 3-state HMM on 2-regime DGP | success; over-parameterization handled |
| 3 | Short series T=80 (hmm+setar) | both succeed |
| 4 | Random walk T=300 (setar+star) | both succeed (no nonlinear structure detected) |

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-MR-STAR-TYPE | Severe | STAR accepted invalid star_type='zzz' silently with audit_fields reporting 'ZZZ' | **Fixed inline** (~20 LOC, 1 file) |

No findings on hmm, markov_switching, tar_setar, or nar_narx.

## Validation-presence pattern update

| Session | Wrapper | Validation? | Findings |
|---|---|---|---|
| Sessions 6-11 (cumulative) | 13 wrappers | mixed | 5 severe (all fixed) |
| 12 | hmm | Yes (hmmlearn validates internally) | 0 |
| 12 | markov_switching | Yes (statsmodels validates) | 0 |
| 12 | tar_setar | Yes (n_regimes int conversion) | 0 |
| 12 | **star** | **No (no allowlist; pre-fix silent accept)** | **1 severe (fixed)** |
| 12 | nar_narx | Yes (sklearn validates) | 0 |

**Cumulative tally across 18 wrappers in 7 extension sessions:**
- WITH validation OR low math complexity: **12 wrappers → 0 findings**
- WITHOUT validation: **6 wrappers → 6 severe findings (all fixed inline)**

Pattern's predictive power remains 100%. Session 12 confirms:
- Wrappers wrapping a robust upstream library (statsmodels,
  hmmlearn, sklearn) inherit upstream validation and ship
  clean.
- Wrappers with custom string-spec parameters (and no
  wrapper-side allowlist) ship with silent-acceptance bugs —
  **every single time** — until audited.

## Cross-wrapper comparison: regime detection methodology

| Use case | Recommended | Why |
|---|---|---|
| Hidden-state regime detection (state probabilities desired) | `hmm` | Returns posterior state probabilities; HMM is the canonical hidden-state model |
| Parametric regime switching with known number of regimes | `markov_switching` | Explicit regime count; more interpretable parameters than HMM |
| Threshold-based regime detection (regime depends on observable) | `tar_setar` | Explicit threshold; deterministic dispatch |
| Smooth transition between regimes | `star` (LSTAR/ESTAR) | Continuous transition; useful when regime change isn't abrupt |
| Nonlinear function approximation (no regime structure) | `nar_narx` | MLP-based universal approximator; black-box but flexible |

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | All 5 wrapper APIs verified. STAR allowlist validation added inline. |
| **CAL-R3** | Status doc updated: 5 rows AUDITED. Cycle table extended; AUDITED count 19 → 24. |
| **CAL-R4** | 5 NEW canonical scripts created from scratch, 6 canonicals each = 30 canonicals total. Compact (vs 9 in prior sessions) to manage 5-wrapper batch runtime. |
| **CAL-R5** | Real-data baselines for 5 wrappers × 2 series = 10 cells recorded. |
| **CAL-R6** | 1 inline fix (~20 LOC, 1 file). Cumulative engine-side LOC: 20. Within ≤100 LOC budget. |

## Recommended follow-ups

None required. All 5 wrappers clean post-fix.

For future cycles:
- The Markov/Regime extension batch is now closed.
- HMM wrapper has hmmlearn validation; if hmmlearn version
  upgrades change validation behavior, retest.
- STAR's allowlist validation could be extended to other
  string-valued params (none currently exist beyond
  star_type).
- Verification initiative could add parity tests for
  regime-detection wrappers vs R `MSwM`, `tsDyn`, or
  reference Python implementations. Currently no
  verification parity for any of these 5 wrappers.
