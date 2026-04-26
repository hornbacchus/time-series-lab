# Calibration Audit: VAR + VECM family

**Audit date:** 2026-04-26
**Commit:** (assigned at V10)
**Auditor:** Claude (driven mode)
**Wrappers audited:**
  - `engine/techniques/var_model.py` (vector autoregression)
  - `engine/techniques/vecm_model.py` (vector error correction)
**Cross-references:**
  - Session 4 (`johansen_findings_2026_04_25.md`) — Johansen
    rank determination (rates pair rank=0 on 10-year window)
  - Verification initiative 1c — BVAR IRF/FEVD math given
    fixed coefficients (NOT re-derived here; audit focuses
    on calibration concerns)

## Summary

Fourth extension audit (CAI Phase 2 Session 9). Multivariate
batch — same architectural pattern as Session 6 (GARCH family
batch).

**Findings: 1 severe (FIXED INLINE) / 0 operational / 0
cosmetic.** The single severe finding (F-VV-DETERMINISTIC) is
a Session-6-style silent input-acceptance bug in VECM, fixed
inline within CAL-R6 budget (~25 LOC, 1 file).

**Pattern observation extends Session 8.** Session 8
established that wrappers with explicit input allowlist
validation produce 0 findings (caviar). Session 9 confirms
the contrapositive: VECM lacked explicit `deterministic`
validation; statsmodels silently treats unknown strings as
`'n'`; TSL's audit_fields reported the user's invalid value.
This is the silent-acceptance failure mode — the exact
counterpart to Session 6's silent-dispatch failure mode.

VAR was clean. The asymmetry (VAR clean, VECM with finding)
is attributable to:
- VAR's `trend` parameter is validated by statsmodels
  itself (statsmodels VAR rejects `trend='zzz'` with
  `"trend 'zzz' not supported for VAR"`)
- VECM's `deterministic` parameter is silently coerced by
  statsmodels (the package treats unknown strings as `'n'`
  without raising)

So whether allowlist validation is a wrapper concern or
upstream concern depends on the upstream package. **The
defensive lesson: don't rely on upstream packages for input
validation; do it in the wrapper.**

## Sweep 0 — Variant dispatch + input-validation probe

| Probe | Behavior | Pre-fix verdict |
|---|---|---|
| VAR + valid params | success | OK |
| VECM + valid params | success | OK |
| VAR with `trend='zzz'` | failure with `"trend 'zzz' not supported for VAR"` | OK (statsmodels rejects) |
| VECM with `deterministic='zzz'` | **success** (silent fallback to 'n') | **SEVERE** ❌ |
| VECM with `coint_rank=5` on k=2 | failure with `"index 3 is out of bounds"` | Acceptable (clear error) |

The VECM `deterministic` finding is the only severe case.
After applying the fix, post-fix VECM with `'zzz'` returns:
```
status=failure, err_msg=Unknown deterministic 'zzz'.
Must be one of: n, co, ci, lo, li.
```

## Technique 1: Parameter Sweep

### Sweep 1.1: VAR lag_order on synthetic VAR(1) DGP

Bivariate VAR(1) DGP, T=500, max eigenvalue ≈ 0.7.

| lag param | selected | AIC | max_root_modulus |
|---|---|---|---|
| 1 | 1 | -0.053 | 0.657 |
| 2 | 2 | -0.041 | 0.623 |
| 5 | 5 | -0.033 | 0.732 |
| 10 | 10 | 0.019 | 0.833 |
| auto | 1 | -0.053 | 0.657 |

Auto-selection correctly picks lag=1 (matches the DGP).
max_root_modulus stays well below 1 across all lag choices —
no spurious non-stationary fits.

**Findings:** None.

### Sweep 1.2: VAR trend specifications on drift-free DGP

| trend | AIC | BIC | max_root_modulus |
|---|---|---|---|
| n | -0.059 | -0.025 | 0.662 |
| c | -0.053 | -0.003 | 0.657 |
| ct | -0.045 | 0.022 | 0.657 |
| ctt | -0.038 | 0.046 | 0.647 |

All 4 trend specs run cleanly with finite IC. BIC favors
`'n'` (correctly identifying the drift-free DGP); AIC
slightly favors `'n'` too. Max-root-modulus uniformly < 0.7
— stable across specs.

**Findings:** None.

### Sweep 1.3: VECM coint_rank on rank-1 DGP

Bivariate cointegrated DGP (β=0.5), T=500.

| rank param | applied | trace_stat (vs CV ≈ 12.3) | half_life |
|---|---|---|---|
| auto (None) | 1 | 219.6 | 9.2 |
| 1 | 1 | 219.6 | 9.2 |
| 2 | 2 | 219.6 | 6.8 |

trace_stat far exceeds 5% critical value — strong cointegration
signal. Auto-rank correctly selects 1. With rank=2 forced
(over-parameterization), the wrapper still runs but reports
a different half-life (over-parameterization compresses the
correction speed).

**Findings:** None.

### Sweep 1.4: Real-data lag selection on trivariate macro

(DGS2 yield diffs, DGS10 yield diffs, GSPC log returns).

| lag param | selected | AIC | max_root_modulus |
|---|---|---|---|
| auto | 8 | -12.33 | 0.848 |
| 1 | 1 | -12.30 | 0.149 |
| 5 | 5 | -12.31 | 0.613 |
| 10 | 10 | -12.34 | 0.886 |

AIC auto-selects lag=8. max_root_modulus rises with lag (more
parameters, more borderline-stationary fits) but stays below
1. Wrapper correctly reports the trade-off.

**Findings:** None.

## Technique 2: Real-Data Stress

### Bivariate (DGS2, DGS10): VAR + VECM

| Wrapper | Lag | AIC | max_root | rank | trace | half_life |
|---|---|---|---|---|---|---|
| VAR | 5 | -12.59 | **0.9996** | — | — | — |
| VECM | 5 | — | — | 1 (auto) | 6.08 / cv 15.49 | **560.5** |

**Cross-reference Session 4 Johansen finding:** Session 4
audited the same rates pair on the same 10-year window and
found rank=0 (no cointegration) — trace_stat 6.08 vs CV
15.49 (fails to reject r=0). Session 9's VECM audit confirms
the same trace_stat. **VECM auto-coerces to rank=1 with the
warning "No cointegrating relations detected... Using rank=1
anyway"** (line 153-158 of vecm_model.py). The half-life of
560 days (~2.2 years) is the result of the coercion: when
no cointegration exists, the forced rank=1 produces a near-
zero adjustment coefficient, and half_life = -log(2)/log(1+α)
diverges.

**This coerce-with-warning behavior is pre-existing and
documented; not a Session 9 finding.** The user gets the
warning + the divergent half_life as honest signals that
cointegration is weak/absent.

VAR's max_root_modulus=0.9996 on the rates pair levels is
**very close to but below 1** — the levels are I(1) random-
walk-like, and VAR-on-levels appropriately produces near-
unit-root dynamics. The wrapper does NOT silently emit an
unstable fit (it stays just under 1.0 and the wrapper would
warn at >= 1.0 per the persistence-trigger logic). Operational
guidance: users analyzing yield levels should consider VECM
or a differenced VAR; this audit's tier-3 triggers in the
spec already cover that.

### Trivariate (DGS2, DGS10, GSPC log returns)

| Wrapper | Lag | max_root / trace | rank |
|---|---|---|---|
| VAR | 8 | max_root=0.9995 | — |
| VECM | 8 | trace=258.9 | 1 (auto) |

Trivariate VECM rejects rank=0 strongly (trace=258.9). VAR
again sits just under unit-root — same observation as
bivariate.

**Findings:** None on either wrapper at this level.

## Technique 3: Adversarial Canonical Extension

### canonical_6 (C-CAL-1): Constant series

VAR on iid N(0,1) at T=300:
- max_root_modulus=0.085 — correctly small on iid data
- No spurious dynamics detected.

### canonical_7 (C-CAL-2): Independent random walks

VAR: max_root=0.993 — correctly detects non-stationarity.
VECM: rank_applied=1 (forced from rank=0), trace=5.5 vs CV
15.5, **rank=0→1 coercion warning fires**.

### canonical_8 (C-CAL-3): Short series T=50

Both VAR and VECM run cleanly at T=50 — neither hits the
3*k+5 = 11 (VAR) or 4*k+5 = 13 (VECM) hard guard at this
size.

### canonical_9 (C-CAL-4): VAR lag=15 on T=100

The wrapper internally caps `max_lag = min(lag, n//(k+1)-1,
n//3)`. For T=100, k=2, the cap is `min(15, 32, 33) = 15` —
so the user's lag=15 is honored. status=success, max_root=0.97.

**Findings:** None on adversarial canonicals.

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| F-VV-DETERMINISTIC | Severe | VECM accepted any string for `deterministic` (statsmodels silently treats unknown values as 'n'); TSL's audit_fields reported the user's invalid value | **Fixed inline** — added explicit allowlist validation (~25 LOC, 1 file) |

No findings on the VAR wrapper. No findings on VECM math.
Cumulative engine-side fix LOC: 25 (within CAL-R6 budget).

## Pattern observation update

Comparing across all extension sessions:

| Session | Wrapper | Math complexity | Variant ambiguity | Input validation? | Findings |
|---|---|---|---|---|---|
| 6 | garch family | High | High (catalog→wrapper dispatch) | No (silent dispatch) | 2 severe (fixed) |
| 7 | har_rv | Low | None | N/A (single spec) | 0 |
| 8 | caviar | Medium | Low | **Yes (`if spec not in ...`)** | 0 |
| 9 | **var** | High | Medium | **Yes (statsmodels VAR rejects)** | **0** |
| 9 | **vecm** | High | Medium | **No (statsmodels silently coerces)** | **1 severe (fixed)** |

The refined pattern from Session 8 holds: explicit input
validation is the operational equivalent of a parity test.
Session 9 sharpens it: the validation can come from EITHER
the wrapper OR the upstream package, but if neither validates,
the silent-acceptance failure mode manifests. **VECM had
neither; Session 9 added the wrapper-level check.**

## Cross-reference: Session 4 Johansen + Verification 1c BVAR

- **Session 4 (`johansen_findings_2026_04_25.md`)** found
  rank=0 on the rates pair 10-year window with trace=6.08 vs
  CV=15.49. Session 9's VECM audit reproduces this trace_stat
  exactly (same window, same data, different wrapper). This
  cross-validation is reassuring: both wrappers agree on the
  Johansen test outcome. **VECM's force-coerce-to-rank=1 +
  warning is the correct behavior**: a VECM-with-rank=0 model
  is mathematically a differenced VAR, which the user can
  obtain by running `var` on `np.diff(prices)`. Forcing
  rank=1 + warning is a more informative output than silently
  rejecting the request.
- **Verification initiative 1c** validated BVAR IRF/FEVD math
  given fixed coefficients at machine precision vs R `vars::
  irf/fevd`. Session 9 did NOT re-derive that; instead it
  audits VAR's calibration (lag selection defaults, trend
  spec sensitivity, real-data behavior). Complementary
  coverage; no overlap.

## R-resolutions

| ID | Resolution |
|---|---|
| **CAL-R2** | VAR params verified: `horizon`, `irf_periods`, `trend` (default 'c'; statsmodels-validated allowlist), `max_lag` (preset Fast=4/Balanced=8/Thorough=16), `ic` ('aic'), `lag`. Hard guard: n < 3*k + 5. VECM params verified: `horizon`, `deterministic` (default 'ci'; **wrapper allowlist added in Session 9 fix**), `significance_level`, `max_lag` (preset Fast=4/Balanced=8/Thorough=12), `lag`, `coint_rank` (None=auto; coerces 0→1 with warning). |
| **CAL-R3** | Status doc updated: `var` PENDING → AUDITED, `vecm` PENDING → AUDITED. Cycle table extended; AUDITED count 11 → 13. |
| **CAL-R4** | New canonical scripts created from scratch: `tools/validate_var_canonicals.py` (9 canonicals: 5 base + 4 C-CAL) and `tools/validate_vecm_canonicals.py` (9 canonicals: 5 base including allowlist-fix verification + 4 C-CAL). |
| **CAL-R5** | Real-data baselines for bivariate (DGS2, DGS10) and trivariate (DGS2, DGS10, GSPC) macro systems recorded. Session 4 Johansen rate-pair rank=0 finding cross-validated. |
| **CAL-R6** | 1 inline fix applied (~25 LOC, 1 file). Cumulative engine-side LOC: 25. Within ≤100 LOC session budget. |

## Recommended follow-ups

None required. Both wrappers clean post-fix.

For future cycles:

- The "VAR-on-yield-levels max_root ≈ 0.9996" observation
  isn't a wrapper bug but is operationally noteworthy. The
  wrapper's interpretation spec already triggers a warning
  at high persistence; consider tightening the trigger
  threshold from 1.0 to 0.99 to alert users when fits are
  near-unit-root (operationally similar but not yet
  unstable). Out of scope for this commit.
- VECM's auto-coerce rank=0→1 + warning is a documented
  user-facing convenience. Consider adding an explicit
  `allow_rank_zero` parameter (default False, preserving
  current coerce-with-warning) so power users can request
  raw rank=0 (which becomes a differenced-VAR model). Out
  of scope.
- Verification initiative could add VAR/VECM parity tests
  against R `vars::VAR` and R `vars::vec2var` / `urca::ca.jo`
  + manual VECM. Currently only BVAR has 1c parity testing;
  VAR/VECM rely on calibration audit + this session's
  baselines for empirical sanity-checking.
