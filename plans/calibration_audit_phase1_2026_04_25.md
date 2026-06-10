# Calibration Audit Initiative — Phase 1 Design Audit

**Date:** 2026-04-25
**Project:** TSL (Time Series Lab)
**Plan file:** `plans\glistening-wishing-mountain.md`
**Origin:** Successor initiative to the Verification Initiative (closed at
commit `ee44ee4`). Whereas the Verification Initiative validated math
correctness via cross-implementation parity, the Calibration Audit
Initiative validates default-parameter sensibility via parameter sweeps,
real-data stress tests, and adversarial canonical extension.

This document is the complete specification handoff for Phase 2
(per-wrapper audits). Phase 1 (this document) locks initiative scope,
methodology, and per-wrapper audit plans. Phase 2 ships ~5 commits, one
audit per session.

---

## 0. Initiative scope and locked decisions

### 0.1 Working agreement context

This initiative ships under the "Claude drives" working agreement
established at the prior session boundary. Implications:

- Decisions made by Claude in advance, not asked. Override mechanism is
  user "no" or "different direction" at gate review.
- Each Phase 2 audit ships as a single commit per Template C from the
  Phase 3.1 workflow doc (commit `fe64405`).
- User reviews findings at gate, not at design.

### 0.2 Core distinction from verification initiative

| Dimension | Verification Initiative | Calibration Audit Initiative |
|---|---|---|
| Question | Does TSL agree with reference X at tolerance T? | Does TSL produce sensible outputs at default settings on inputs typical of intended use? |
| Methodology | Reference-implementation parity (R/Python packages) | Parameter sweep + real-data stress + adversarial canonical extension |
| Findings type | Quantitative — pass/fail at tolerance | Qualitative — judgment-based "sensible" vs. concerning |
| Output | Bitwise/MC tolerance verdicts | Severity-classified findings (severe/operational/cosmetic) |
| Phase 4.5 N/A criteria | When no reference exists | Always — calibration audit is its own validation track |

### 0.3 Locked decisions (Q-Cal-1, 2, 3)

| Q | Decision |
|---|---|
| Q-Cal-1 — Wrapper selection | 5 wrappers: Kalman, HAR-CJ, EVT-POT, Johansen, Stochastic Volatility |
| Q-Cal-2 — Real-data fixtures | Public real series saved to repo at `tools/calibration_audit/fixtures/macro_canonical_series.npz`. 5 series from FRED + Yahoo Finance, 10-year window 2015-04-25 to 2025-04-25. |
| Q-Cal-3 — Severity protocol | Severe (commit-blocker) / Operational (fix-or-defer) / Cosmetic (document-only) |

### 0.4 Non-decisions worth flagging

These could have been decisions but aren't, by design:

- **Audit-commit consolidation strategy.** Each per-wrapper audit ships
  as its own commit rather than one consolidated commit. Reason: if any
  audit surfaces severe findings that block its commit, the others can
  still ship.
- **Parameter-sweep granularity.** Left to per-wrapper audit plan in §3.
  Different wrappers have different parameter dimensionality.
- **Findings-tracking artifact.** Will be created as part of Phase 2
  Session 1 (first audit commit). Format: `docs/calibration_audit_status.md`
  parallel to `docs/follow_up_check_coverage.md`.

---

## 1. Audit methodology — three techniques per wrapper

### 1.1 Technique 1: Parameter sweep

For each user-settable parameter in the wrapper:
- Vary across plausible operational range (not full theoretical range —
  e.g., for a `bandwidth` parameter, sweep from 50 to 500 in steps of
  50, not 1 to 10000).
- Hold all other parameters at default.
- Run wrapper on a synthetic canonical input (typically the wrapper's
  C1 fixture or equivalent stable input).
- Plot or tabulate output against parameter value.
- Flag any of the following:
  - Non-monotonic behavior where monotonicity is expected
  - Sudden discontinuities or step changes
  - Implausible output magnitudes (NaN, Inf, or values outside expected
    range)
  - Cases where the parameter has NO effect on output (suggesting it's
    not actually wired through)

**Output:** parameter sweep table per parameter, with findings classified.

### 1.2 Technique 2: Real-data stress test

For each of 5 canonical macro series (see §2):
- Run wrapper at default preset (Balanced) with default parameters.
- Inspect outputs:
  - Coefficient signs match economic intuition where applicable
  - Forecast values within plausible range for the series type
  - Diagnostics (Tier 3 triggers) fire on series with known structural
    features (e.g., COVID period in equity returns should plausibly fire
    volatility-regime triggers)
  - Audit fields populate consistently across series
  - Runtime is acceptable (≤30s for fast operations, ≤5min for MCMC)

**Output:** real-data findings table per series-wrapper combination.

### 1.3 Technique 3: Adversarial canonical extension

For each wrapper:
- Identify canonical cases NOT currently tested. Standard adversarial
  templates:
  - Very short series (T = minimum + 1 vs. minimum - 1)
  - Very long series (T = 100,000)
  - Series with NaN gaps (1%, 5%, 10% missing)
  - Series with single outlier (5σ event injected)
  - Series with structural break (mean shift mid-series)
  - Series at boundary of stationarity (near-unit-root AR coefficient)
  - Series with deterministic trend (calibration-relevant for detrending
    wrappers)
- Build canonical for each adversarial case.
- Run wrapper; document expected vs. observed behavior.

**Output:** new adversarial canonicals appended to wrapper's existing
canonical file; findings logged.

---

## 2. Real-data fixture specification

### 2.1 Series list

| Series ID | Source | Description | Type |
|---|---|---|---|
| DGS10 | FRED | 10-Year Treasury Constant Maturity Rate | Daily, percent |
| DGS2 | FRED | 2-Year Treasury Constant Maturity Rate | Daily, percent |
| DEXUSEU | FRED | US/Euro Foreign Exchange Rate | Daily, USD per EUR |
| GSPC | Yahoo Finance (^GSPC) | S&P 500 daily close | Daily, USD |
| GOLDAMGBD228NLBM | FRED | Gold Fixing Price 10:30 AM London | Daily, USD/oz |

### 2.2 Time window

**Start:** 2015-04-25
**End:** 2025-04-25
**Length:** ~2520 trading days per series (~10 years)
**Rationale:** Decade window covers multiple regime contexts (post-GFC
recovery, COVID volatility shock, post-COVID inflation regime, recent
rate-hike cycle, current cycle stabilization). Ends 2025-04-25, exactly
one year before audit work starts, providing buffer against late
revisions to recent FRED data.

### 2.3 Acquisition protocol

```python
# tools/calibration_audit/fixtures/_generate_macro_fixtures.py
import pandas_datareader.data as pdr
import yfinance as yf
import pandas as pd
import numpy as np

START = "2015-04-25"
END = "2025-04-25"

# FRED series
fred_series = ["DGS10", "DGS2", "DEXUSEU", "GOLDAMGBD228NLBM"]
fred_data = {}
for sid in fred_series:
    s = pdr.DataReader(sid, "fred", START, END)
    fred_data[sid] = s.iloc[:, 0].dropna().values

# Yahoo Finance
gspc = yf.Ticker("^GSPC").history(start=START, end=END)["Close"].values

# Save as npz
np.savez(
    "tools/calibration_audit/fixtures/macro_canonical_series.npz",
    DGS10=fred_data["DGS10"],
    DGS2=fred_data["DGS2"],
    DEXUSEU=fred_data["DEXUSEU"],
    GOLDAMGBD228NLBM=fred_data["GOLDAMGBD228NLBM"],
    GSPC=gspc,
    _start=START,
    _end=END,
    _source_doc="calibration_audit_real_data_fixtures",
)
```

### 2.4 Storage and reproducibility

- File: `tools/calibration_audit/fixtures/macro_canonical_series.npz`
- SHA256 sidecar: `tools/calibration_audit/fixtures/macro_canonical_series.sha256`
- Generation script: not committed (one-off; series-data IS committed)
- Approximate size: 100KB total

### 2.5 Decision flag

Public real macro data added to repo. Anyone with repo access can see
which series TSL gets calibration-audited against. Series are individually
trivial (no proprietary information). Mentioned for explicit visibility;
override if synthetic-only fixtures preferred.

---

## 3. Per-wrapper audit plans

### 3.1 Kalman filter / smoother

**Wrapper file:** `engine/techniques/kalman_filter.py` and
`kalman_smoother.py`

**Why audit:** Foundational; outputs propagate to many downstream uses.
Math validated at parity (2a, abs_tol=1e-8). Calibration not yet
stress-tested.

**Parameter sweep — Technique 1:**
- `process_noise_var` (sigma_eta²): sweep 0.01, 0.1, 1.0, 10.0
- `observation_noise_var` (sigma_eps²): sweep 0.01, 0.1, 1.0, 10.0
- Initial state mean: sweep 0.0, mean(y), median(y)
- Initial state variance: sweep 0.01, 1.0, 100.0 (diffuse)

**Sensitivity hypothesis:** initial-state variance affects early-state
estimates; should converge to steady-state regardless. Findings to flag:
non-convergence within first 50 timesteps; oscillation; sign-flips on
filtered/smoothed states across initial-condition variations.

**Real-data stress — Technique 2:**
- DGS10: random-walk-like; expect filter to track closely
- DGS2: similar to DGS10 but more variation
- DEXUSEU: mean-reverting; expect tracking with reasonable smoothing
- GSPC: trending with volatility clusters; calibration-challenging
- GOLDAMGBD228NLBM: regime-switching behavior; calibration-challenging

**Adversarial canonicals — Technique 3:**
- T = 5 (minimum viable): does filter handle correctly?
- NaN gaps at 5%: does the wrapper degrade gracefully?
- Single 10σ outlier injected: does smoother properly downweight?
- Near-unit-root AR signal: does Kalman decompose properly?

**Audit commit budget:** ~600 LOC (script + new canonicals + findings doc)

### 3.2 HAR-CJ realized volatility

**Wrapper file:** `engine/techniques/har_cj.py`

**Why audit:** Realized volatility is calibration-sensitive. B8 finding
(output rounding floor at 1e-6) is calibration-adjacent. Lag structure
+ jump-detection threshold parameter interactions plausible.

**Parameter sweep — Technique 1:**
- `daily_lag`, `weekly_lag`, `monthly_lag` (default 1, 5, 22): sweep
  alternative configurations
- `jump_threshold` (BNS ratio test α): sweep 0.001, 0.01, 0.05, 0.1
- `min_periods_for_estimation`: sweep 50, 100, 200

**Sensitivity hypothesis:** jump-detection threshold has nonlinear
impact on coefficient estimates because it changes which days enter the
"jump" regressor vs. the "continuous" regressor. Non-monotonic behavior
plausible.

**Real-data stress — Technique 2:**
- GSPC: daily-return-derived realized vol; canonical use case
- DGS10: rates volatility; less canonical but valid
- DEXUSEU: FX volatility; calibration-challenging because lower
  unconditional volatility

**Adversarial canonicals — Technique 3:**
- Series with NO jumps: does jump-coefficient go to zero?
- Series with ALL jumps (5σ events every 10 days): pathological
- Mid-series volatility regime change: do coefficients adapt?
- Output rounding floor exposure: T=1500 with tiny coefficients

**Audit commit budget:** ~500 LOC

### 3.3 EVT-POT (Peaks Over Threshold + Ferro-Segers)

**Wrapper file:** `engine/techniques/evt_pot_gpd.py`

**Why audit:** Tail risk is high-stakes. Threshold-percentile choice
+ block size are highly impactful and not currently calibrated for macro
use specifically.

**Parameter sweep — Technique 1:**
- `threshold_percentile`: sweep 0.90, 0.95, 0.975, 0.99
- `min_exceedances`: sweep 20, 50, 100
- `extremal_index_method`: keep at "ferro_segers" (validated 3c) but
  document behavior

**Sensitivity hypothesis:** GPD parameter estimates (shape, scale) are
notoriously sensitive to threshold choice. Tail-quantile estimates can
vary by 50%+ across threshold-percentile choices. Document the
sensitivity profile.

**Real-data stress — Technique 2:**
- GSPC daily returns: equity tail risk canonical use
- DEXUSEU log returns: FX tail risk
- DGS10 daily changes: rates tail risk
- Cross-series: do tail-quantile estimates have right ordering
  (equity > FX > rates typically)?

**Adversarial canonicals — Technique 3:**
- Pure Gaussian series: shape parameter should ≈ 0
- Heavy-tailed (Student-t df=3) series: shape parameter should > 0
- Series with single dominant outlier: does Ferro-Segers correctly
  identify cluster?
- Series at threshold-exceedance boundary (exactly min_exceedances)

**Audit commit budget:** ~600 LOC

### 3.4 Johansen cointegration

**Wrapper file:** `engine/techniques/johansen_cointegration.py`

**Why audit:** Yield-curve cointegration is core to user's work.
Small-sample Reimers correction (3d) was math-validated but not
stress-tested across rank-determination scenarios.

**Parameter sweep — Technique 1:**
- `det_order`: sweep -1, 0, 1 (deterministic component options)
- `lag_order`: sweep 1, 2, 5, 10
- `small_sample_correction`: True vs. False
- `confidence_level`: 0.90, 0.95, 0.99

**Sensitivity hypothesis:** rank determination is sensitive to lag
order and deterministic-component choice. Document the sensitivity
profile across realistic configurations.

**Real-data stress — Technique 2:**
- (DGS10, DGS2): yield curve cointegration; canonical use case;
  expected rank = 1
- (DGS10, GOLDAMGBD228NLBM): less standard; rank determination
  uncertain
- (DEXUSEU, GSPC, DGS10): three-variable system; rank determination
  more complex

**Adversarial canonicals — Technique 3:**
- Two random walks (no cointegration): rank should = 0
- Two perfectly cointegrated series: rank should = 1; test small-sample
  correction sensitivity
- Three-variable system with rank = 2 (two cointegrating relationships)
- Boundary: T = 50 (small sample where Reimers correction matters most)

**Audit commit budget:** ~600 LOC

### 3.5 Stochastic Volatility

**Wrapper file:** `engine/techniques/stochastic_volatility.py`

**Why audit:** Heavily revised in B6/B7 across verification initiative.
Calibration check on post-revision behavior is overdue. Backend cascade
(B6) and h-latent posterior exposure (B7) are recent additions.

**Parameter sweep — Technique 1:**
- `inference_method`: "quasi_ml" vs "mcmc"
- `mcmc_backend`: "auto", "pymc", "gibbs"
- `innovations`: "gaussian" vs "student_t"
- For MCMC: `draws` 1000, 5000, 10000; `burnin` 200, 1000

**Sensitivity hypothesis:** quasi-ML and MCMC posterior means should
agree at moderate T but may diverge at small T or near-stationarity
boundary. Compare across innovations choice.

**Real-data stress — Technique 2:**
- GSPC daily returns: equity SV canonical use case; expect
  high persistence (φ > 0.9)
- DEXUSEU log returns: FX SV; lower volatility regime
- DGS10 daily changes: rates SV; calibration-challenging because
  volatility-of-volatility may be near-zero in stable rate regimes

**Adversarial canonicals — Technique 3:**
- Constant-volatility series: phi should ≈ 0 or be flagged as
  ill-identified
- Two-regime volatility series: does posterior accommodate?
- Very short series (T = 100): quasi-ML vs MCMC tradeoff
- Backend-cascade exercise: force pymc with no g++; verify B6 path
  produces correct outputs

**Audit commit budget:** ~700 LOC (MCMC variants take more canonical
space)

---

## 4. Findings classification and protocol

### 4.1 Severity tiers

| Tier | Definition | Action |
|---|---|---|
| **Severe** | Wrapper produces materially wrong outputs at common use patterns (real-data stress test fails, parameter sweep produces NaN/Inf/sign-flip on default-adjacent settings) | **Commit-blocker.** Fix in audit commit. Investigate root cause. |
| **Operational** | Wrapper produces misleading outputs at edge cases (non-monotonic behavior on parameter sweep, real-data stress produces unintuitive but non-catastrophic outputs) | **Fix if cheap (≤50 LOC); defer otherwise.** Logged in findings markdown with severity tag. |
| **Cosmetic** | Wrapper produces unintuitive outputs at rare edge cases (adversarial canonicals reveal corner-case behavior) | **Document only.** Logged in findings markdown. |

### 4.2 Findings document template

Per-wrapper audit produces a single markdown findings file at:
`docs/calibration_audit/{wrapper_name}_findings_{date}.md`

Template:

```markdown
# Calibration Audit: {wrapper_name}
**Audit date:** {date}
**Commit:** {short_sha}
**Auditor:** Claude (driven mode)

## Summary
{1-paragraph TL;DR with finding counts by severity}

## Technique 1: Parameter Sweep
### {parameter_name}
**Range tested:** {range}
**Default value:** {default}
**Output behavior:** {description}
**Findings:** {classified by severity}

## Technique 2: Real-Data Stress Test
### {series_name}
**Series:** {description}
**Wrapper output summary:** {key audit fields with values}
**Findings:** {classified}

## Technique 3: Adversarial Canonical Extension
### {canonical_name}
**Adversarial scenario:** {description}
**Expected behavior:** {what should happen}
**Observed behavior:** {what did happen}
**Findings:** {classified}

## Findings table

| ID | Severity | Description | Disposition |
|---|---|---|---|
| {wrapper}-CAL-001 | Severe | ... | Fixed in this commit (LOC: ...) |
| {wrapper}-CAL-002 | Operational | ... | Deferred (logged for follow-up) |
| {wrapper}-CAL-003 | Cosmetic | ... | Documented only |

## Recommended follow-ups
{Items requiring future commits to address; ordered by urgency}
```

### 4.3 Tracking artifact

A new file `docs/calibration_audit_status.md` parallel to
`docs/follow_up_check_coverage.md` tracks which wrappers have been
calibration-audited. Created in Phase 2 Session 1.

Initial state (after this initiative completes):

```
| Wrapper | Calibration Audit Status | Findings | Audit Commit |
|---|---|---|---|
| kalman_filter | AUDITED | {n_severe}/{n_operational}/{n_cosmetic} | {sha} |
| har_cj | AUDITED | ... | ... |
| evt_pot_gpd | AUDITED | ... | ... |
| johansen_cointegration | AUDITED | ... | ... |
| stochastic_volatility | AUDITED | ... | ... |
| critical_slowing_down | DEFERRED (too new) | - | - |
| {other 65 wrappers} | UNAUDITED | - | - |
```

---

## 5. Phase 2 execution sequence

### 5.1 Session structure

Each Phase 2 session covers ONE wrapper. Per-session structure:

1. Load Phase 1 design audit (this doc) for the target wrapper
2. Acquire real-data fixtures if not already present (Session 1 only)
3. Build audit script per Technique 1 + 2 + 3
4. Execute audit; collect findings
5. Classify findings by severity
6. Apply fixes for Severe + cheap Operational findings
7. Add adversarial canonicals to existing canonical file
8. Write findings markdown
9. Update tracking artifact
10. Run all existing canonicals to verify no regression
11. Commit per Template C

### 5.2 Session ordering

Recommended order:

1. **Session 1: Kalman.** Establishes pattern; foundational wrapper;
   includes fixture acquisition.
2. **Session 2: HAR-CJ.** Pattern-established; calibration-sensitive;
   tests real-data stress methodology.
3. **Session 3: EVT-POT.** High-stakes findings expected; threshold
   sensitivity is well-known so methodology is well-suited.
4. **Session 4: Johansen.** Specific to user's work; rank-determination
   is calibration-rich.
5. **Session 5: Stochastic Volatility.** Most complex; benefits from
   pattern-establishment in earlier sessions.

### 5.3 Per-session commit message template

```
Calibration audit: {wrapper_name}

Audit findings (severity classification per CAI Phase 1 §4.1):
  Severe: {count} (fixed in this commit)
  Operational: {count} ({n_fixed} fixed, {n_deferred} deferred)
  Cosmetic: {count} (documented only)

Methodology applied (CAI Phase 1 §1):
  Technique 1: parameter sweep on {n_params} parameters
  Technique 2: real-data stress on {n_series} canonical series
  Technique 3: {n_canonicals} adversarial canonicals added

Fixes applied:
  - {LOC}: {description}
  ...

Deferred for follow-up:
  - {finding ID}: {one-line description}
  ...

Files: {n} new/modified, +{ins}/-{del} LOC.
Existing canonicals: {n}/{n} PASS (no regression).
New adversarial canonicals: {n}/{n} PASS.
Phase 4 invariants: {n}/{n} PASS (no regression).
```

---

## 6. Items Code must determine at apply time

Following the CSD handoff R1-R8 pattern:

| ID | Item | Resolution |
|---|---|---|
| **CAL-R1** | Real-data fixture acquisition success | Run fixture-generation script; verify FRED + Yahoo APIs return data; if FRED API requires key, use `pandas_datareader` with appropriate auth or fall back to direct CSV download from FRED website |
| **CAL-R2** | Wrapper-specific parameter API verification | Each wrapper's `ctx.params` dict structure must be verified against actual wrapper code; default values may differ from §3 sketches |
| **CAL-R3** | Tracking artifact location | Confirm `docs/calibration_audit_status.md` doesn't conflict with existing tracking artifacts; create on Session 1 |
| **CAL-R4** | Adversarial canonical naming convention | Existing canonical files use C1-C6 (or C1-C7 for forecast_reconciliation post-B1). New adversarial canonicals append (C8, C9, C10, etc.). Verify per-wrapper |
| **CAL-R5** | Real-data stress baseline | First wrapper audited (Kalman) establishes "what does sensible output look like on these series"; subsequent wrappers calibrate against same series |
| **CAL-R6** | Fix-vs-defer cost threshold | "Cheap" defined as ≤50 LOC for the fix. If a fix would require ≥50 LOC OR touches >2 files, classify as "deferred operational" regardless |

---

## 7. Phase 0 (immediate next step) — coverage count refresh

Before Phase 2 starts, Code must refresh exact uncovered-wrapper count.
This is the deferred item from the planning conversation.

**Phase 0 directive (paste to Code):**

```
PROJECT: TSL (Time Series Lab)
LOCATION: C:\Users\matth\OneDrive\Projects\Time Series Lab
PLAN FILE: plans\glistening-wishing-mountain.md
HANDOFF FILE: plans\calibration_audit_phase1_2026_04_25.md

INITIATIVE: Calibration Audit (CAI) Phase 0 — coverage refresh

Read CAI Phase 1 design audit document.

Phase 0 task: refresh exact uncovered-wrapper count by:
1. Reading resources/catalog/techniques_catalog.json — count entries
2. Reading docs/follow_up_check_coverage.md — list mapped wrappers
3. Computing intersection — list of uncovered wrappers
4. Group by category (forecasting / volatility / structural / DL / etc.)
5. Report to user

Output:
- Total wrapper count
- Mapped (Phase 4.5-covered) count
- Unmapped (uncovered) count and list
- Category breakdown

This is read-only inspection, no commits. Plan mode: ON for review,
OFF when generating the report.
```

---

## 8. End-of-handoff

This document is self-contained. Phase 2 sessions follow per §5.

The "Claude drives" working agreement applies. Override mechanism:
user says "no" or "different direction" at any gate. Default
assumption: Claude proceeds.

If a gate fails (e.g., real-data fixture acquisition fails because
FRED API is unreachable), Code stops and reports per the standard
§16-equivalent pattern. Claude evaluates and proposes a path forward.

— End of Calibration Audit Initiative Phase 1 design audit —
