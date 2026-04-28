# CAI Phase 2 — Empirical Findings

**Status:** Descriptive empirical synthesis. What the
Calibration Audit Initiative established across 28
sessions of wrapper auditing.

**Audience:** Engineers seeking the "what we learned"
narrative behind the directive standard. Strategic
reference for future TSL development.

**Companion documents:**
- [Wrapper Development Standard](wrapper_development_standard.md) — directive
- [Validation Patterns Reference](validation_patterns_reference.md) — diagnostic + fix patterns

---

## 1. CAI Phase 2 Summary

### 1.1 Cycle statistics

CAI Phase 2 ran 2026-04-25 through 2026-04-28. Final state:

| Metric | Value |
|---|---|
| Sessions completed | 28 (5 core + 23 extension) |
| Wrappers AUDITED | 83 / 83 (100%) |
| Wrappers DEFERRED | 0 (CSD deferral lifted in Session 28) |
| Severe findings | 40 (all fixed inline) |
| Operational findings | 42 (all fixed inline) |
| Cosmetic findings | 6 |
| Cumulative engine LOC delta | ~1600-1800 |
| Validation-presence pattern | 100% predictive across 77 extension wrappers |
| Canonical scripts | 86 |
| Full regression suite | 85/85 PASS as of Session 28 |
| pytest engine/tests/ | 96/96 PASS |
| Reference parity (CI) | PASS |

### 1.2 Failure mode distribution

The 88 findings (40 severe + 42 op + 6 cosmetic)
distribute across 5 failure modes:

| Mode | Severe | Operational | Total |
|---|---|---|---|
| 1. String acceptance via if/elif/else default | 18 | 1 | 19 |
| 2. HARMFUL try/except suppression | 5 | 0 | 5 |
| 3. Numeric range silent coercion | 1 | 24 | 25 |
| 4. String-handling chain fall-through | 6 | 0 | 6 |
| 5. Multi-parameter consistency violation | 5 | 2 | 7 |
| Other (legacy / cosmetic / spec-specific) | 5 | 15 | 20 |
| **Total** | **40** | **42** | **82** |

(Plus 6 cosmetic findings, mostly methodology
documentation gaps in cosmetic-grade audits 1-5.)

### 1.3 Methodology evolution narrative

CAI's methodology evolved across the 28 sessions as new
failure patterns emerged:

**Sessions 1-5 (core cycle):** Established three-technique
audit protocol (Sweep 0 + parameter sweep + real-data +
adversarial canonicals). Sessions 1-5 produced ZERO severe
wrapper findings — only cosmetic methodology
documentation gaps. Pattern was loose at this point.

**Session 6 (GARCH family):** First batch with severe
findings (dispatch + EGARCH formula). Validated that
extension cycle would surface real bugs.

**Sessions 7-13 (volatility + multivariate + ARIMA +
Markov + frequency):** Refined silent-string-acceptance
as the dominant bug class. Established CAL-R6 LOC budget
(≤100 inline, ≤2 files).

**Session 13 (frequency domain):** First multi-finding
batch — 3 severe findings. Pattern recognition crystallized:
custom string-handling chains + missing allowlist gates =
predictable bug surface.

**Sessions 14-15 (causality + change-points):** Confirmed
pattern. Started referring to "validation-presence
pattern" — wrappers WITH validation had 0 findings;
wrappers WITHOUT had bugs.

**Session 17 (stationarity tests):** PARADIGM SHIFT.
Discovered HARMFUL try/except suppression as a NEW
failure mode. Wrappers wrapping mature libraries
(statsmodels) but with their own try/except that
swallowed ValueError = bugs. Pattern refined: "validation
must reach the user in actionable form" not just "exist
somewhere in stack."

**Session 18 (state space):** Validated try/except
taxonomy. structural_ts had inner fallback but it was
SAFE-FALLBACK (retries with same input fails identically;
outer except surfaces clean error). Distinguished SAFE
from HARMFUL.

**Session 19 (missing data):** Extended pattern to
NUMERIC range coercion. Same architectural defect, just
on numeric instead of string parameters.

**Session 20 (transfer_function):** Identified
multi-parameter consistency violations as a 5th failure
mode (Almon polynomial degree vs lag length).

**Sessions 21-23 (eval/uncertainty + multivariate +
tree forecasters):** Pattern stabilized. S21 was the
first ZERO-severe batch since S8 (5 wrappers, all
numeric-only); confirmed "low-string-surface" branch.

**Sessions 24-25 (neural sequence + specialized):**
Identified sibling-wrapper bug propagation: N-BEATS and
N-HiTS shared the same Follow-up 1a guard pattern with
identical try/except-pass defect.

**Sessions 26-28 (statistical ML + ets_hw + CSD):**
Cycle closure. Pattern remained 100% predictive
throughout. CSD (the deferred wrapper) had the BEST
pre-audit validation discipline — proved that good
engineering practice prevents the bug class.

### 1.4 LOC budget audit

Cycle total: ~1700 LOC across 83 wrappers. Average ~20
LOC per wrapper, but distribution is bimodal:

- Wrappers WITH pre-existing validation: ~0 LOC
- Wrappers WITHOUT validation: ~30-90 LOC each

The 36 wrappers in the "WITH validation OR low math"
branch consumed essentially zero engineering time during
CAI. The 41 wrappers in the "WITHOUT validation" branch
consumed essentially all of it.

This validates the prevention argument in the [Wrapper
Development Standard](wrapper_development_standard.md):
~20 LOC of validation gates at write-time saves the
findings + fixes + audit cycle later.

---

## 2. Cross-Method Empirical Artifacts

CAI Phase 2 produced empirical comparisons across
methods that are operationally useful for users
choosing among alternatives. These survive the audit
itself and document method capabilities.

### 2.1 GARCH variant ranking on 5-series macro panel

**Source:** Session 6 (commit `fcc73b3`).

Across (GSPC, DGS10, DGS2, DEXUSEU, GOLD) at T=2500,
default Balanced preset:

- **EGARCH** dominates 5/5 series by AIC (asymmetric
  log-volatility leverages financial data's
  asymmetric response to negative shocks).
- **GJR-GARCH** second in 5/5 (also captures asymmetry,
  slightly less flexibly than EGARCH).
- **GARCH(1,1)** third in 5/5 (no asymmetry).

Recommendation: default to EGARCH for financial returns
when Balanced/Thorough preset compute budget allows
(EGARCH is slower than GARCH due to log-link).

### 2.2 HAR-RV vs HAR-CJ on realized volatility

**Source:** Sessions 2 + 7.

HAR-RV (3 lag scales: daily, weekly, monthly) and
HAR-CJ (HAR-RV + jump component) are complementary:

- HAR-RV: faster, simpler, suits low-jump regimes.
- HAR-CJ: explicitly separates continuous variation
  from jump variation. Higher AIC on series with
  realized jumps; not always informative for series
  without.

On synthetic-jump fixtures, HAR-CJ's β_J coefficient
recovers the jump amplitude with low bias. On
no-jump series, β_J → 0 (correctly identifying
absence). HAR-RV stays biased upward (missing jump
absorbed into variance).

Recommendation: default to HAR-RV unless realized
jump variation is non-trivial (typical for crypto,
FX during stress).

### 2.3 Rates pair cointegration loss confirmed

**Source:** Sessions 4 (Johansen) + 9 (VECM) + 17
(stationarity panel).

(DGS2, DGS10) on a 10-year window has rank=0 cointegration:
no long-run equilibrium between 2-year and 10-year
yields over the window. This is consistent across all
three audit sessions:

- Johansen trace test at rank=0: not rejected.
- VECM r=0 estimation succeeds; r>=1 fits do not improve.
- ADF on DGS2-DGS10 spread: doesn't reject unit root.

Operational implication: applications relying on yield-
curve cointegration over the 10-year window should
add explicit cointegration testing rather than assume
the relationship persists.

### 2.4 ARIMA suitability for daily macro

**Source:** Session 10 (auto_arima).

auto_arima's selected models on 5-series macro panel:

- Equity log returns (GSPC) → white-noise (0,0,0)
- FX log returns (DEXUSEU) → near-white-noise (1,0,0)
- Commodity log returns (GOLD) → near-white-noise
- Yield levels (DGS10, DGS2) → random walk (0,1,0)

Operational implication: ARIMA family on daily macro
returns is essentially a complicated way to compute the
mean. Use ARIMA when explicit AR or MA structure is
expected (lower-frequency series, calendar effects);
default to simpler models for daily macro.

### 2.5 Intermittent demand variant performance

**Source:** Session 11 (intermittent_demand).

On synthetic intermittent fixtures (~70% zeros):

- Croston's method: classic, low computational cost.
- Syntetos-Boylan: bias-corrected Croston; better for
  high-intermittency series.
- TSB (Teunter-Syntetos-Babai): handles obsolescence;
  best for series with possibility of going to zero.

All three audit clean (no severe findings). Choice
depends on application: spare parts → SBA or TSB;
demand forecasting → Croston.

### 2.6 Transfer function ↔ Granger causality cross-validation

**Source:** Sessions 14 (Granger) + 20 (transfer_function).

On (GSPC log returns → DGS10 yield changes), both methods
identify the same lag structure (b=1, r=1). On (DGS2 →
DGS10), neither shows significant causality at any lag,
consistent with the rates pair cointegration loss
findings (§2.3).

The two methods are complementary: Granger tests
predictive content (statistical), TF estimates the
specific impulse response (structural). Use Granger
to detect, TF to model.

### 2.7 Autoencoder vs STL+ESD anomaly comparison

**Source:** Sessions 15 (stl_esd_anomaly) + 25
(autoencoder_anomaly).

On GSPC log returns at T=200:

- stl_esd_anomaly: 17 anomalies flagged (sensitive).
- autoencoder_anomaly (small hidden_dim=16): 0
  anomalies flagged (insensitive at small capacity).

The methods detect different signal types:
- STL+ESD detects observations with extreme
  RESIDUAL after seasonal decomposition. Captures
  outliers per-observation.
- Autoencoder detects WINDOWS with high
  reconstruction error. Captures regime shifts in
  multi-step patterns.

Recommendation: STL+ESD for outlier detection
(individual observations); autoencoder for regime/
pattern anomaly detection (windows). They are
complementary, not competitive.

### 2.8 Stationarity test panel on rates pair

**Source:** Session 17.

(GSPC log returns) — all 3 tests agree: stationary.
(DGS10 yield level) — ADF/PP borderline reject UR;
KPSS rejects stationarity. Joint verdict: CONFLICTING
(Tier 3 trigger fires). Typical of near-unit-root
series.

This pattern is well-established in the literature
but worth documenting that the wrapper-level joint
triage works as advertised on real macro data.

### 2.9 PCA dominant level factor on macro

**Source:** Session 22 (pca_analysis).

PCA on 5-series macro panel (GSPC, DGS10, DGS2,
DEXUSEU, GOLD) over T=300 extracts a dominant first
principal component capturing ~50% of total variance.
This PC is interpretable as a "macro level" factor:
yields and equity returns are highly correlated, and
the first PC captures their common direction.

Subsequent PCs split into yield-curve slope (PC2) and
FX/commodity vs equity (PC3). Consistent with macro
PCA literature.

### 2.10 N-BEATS / N-HiTS sibling propagation

**Source:** Sessions 24 + 25.

N-BEATS' Follow-up 1a guard pattern silently fell
through to preset on invalid `stack_types`. The
identical pattern was found in N-HiTS' `pooling_sizes`
guard during the next session's audit. Both fixes
propagated correctly via explicit allowlist gates.

This is the only sibling-wrapper bug propagation
observed in the cycle. Lesson: when adapting a
follow-up fix from one wrapper to a structurally
similar sibling, audit the sibling explicitly rather
than copying the fix pattern blindly.

### 2.11 ETS-on-macro auto-selection

**Source:** Session 27 (ets_hw).

ets_hw with default auto-selection on macro (T=300)
selected `trend='add', seasonal='add'` for ALL 5
series. This is consistent with ETS's tendency to
overfit when given degrees of freedom; the
information criterion (AIC) varies but the
specification doesn't change.

For interpretive use, force `seasonal=None` on
returns (no daily seasonal in monthly-aggregated
returns) and let ARIMA / SES handle the residual.

### 2.12 CSD on macro: 4 normal + 1 critical

**Source:** Session 28.

Critical Slowing Down indicator on 5-series macro
(T=2000):

- GSPC, DGS10, DGS2, GOLD: state=normal (no
  spurious warnings).
- DEXUSEU log returns: state=critical (EWS=6.57).

The DEXUSEU finding is a notable operational signal.
Possible interpretations:
1. Genuine signal of a regime shift in EUR/USD
   volatility over the window (worth investigating
   manually before taking as production-grade).
2. Wrapper sensitivity to autocorrelated FX returns
   at this window length.

The remaining 4-of-5 normal results confirm CSD's
specificity (no false alarms on stable regimes).
The synthetic bifurcation control (approaching-fold
DGP) correctly flagged critical (EWS=3.43), confirming
sensitivity.

---

## 3. Validated Engineering Principles

### 3.1 Validation-presence pattern (100% predictive)

A wrapper produces zero CAI findings if and only if at
least one of:

1. **Explicit wrapper-layer validation:** allowlist gates
   for strings, range gates for numerics, consistency
   checks for multi-param surfaces.
2. **Low-string-surface:** numeric/bool parameters only,
   no if/elif/else dispatch chains.
3. **Upstream validates AND no try/except suppression:**
   library raises on invalid input AND wrapper does NOT
   catch the exception in a way that swallows it.

Empirical evidence: across 77 extension wrappers, the
pattern correctly predicted finding presence/absence in
every observed case.

**Engineering implication:** writing the validation gate
at wrapper-write time (when context is fresh) costs
~20 LOC. Skipping it costs the gate + audit + fix +
canonical-test + commit + CI cycle later, plus the
production-incident risk between when the wrapper ships
and when the audit runs. The cost-benefit is heavily in
favor of write-time gating.

### 3.2 Wrapper-layer validation must not depend on upstream alone

**Lesson source:** Sessions 13 + 17.

Some wrappers in CAI Phase 2 wrapped mature libraries
(statsmodels) and added their own pre-processing layer
that short-circuited the library's validation.
Specifically:

- Session 13 found wrappers that called `.lower()` and
  `[:3]` slicing on user strings before passing to
  statsmodels. This collapsed valid strings AND invalid
  strings into the same library call, making the
  library's validation irrelevant.

- Session 17 found wrappers that caught `ValueError` from
  statsmodels in a `_run_*_single` helper and stored the
  error, returning `status="success"` from the outer
  `run()`. The library's validation reached the wrapper
  but never the user.

**Engineering implication:** the predicate is "does
validation reach the user in actionable form" — not "is
there validation somewhere in the call stack."

### 3.3 audit_fields must reflect actual computation

**Lesson source:** Sessions 9 (VECM) + 16 (X-13) +
27 (ETS) + 28 (CSD).

When a wrapper silently coerces an invalid parameter to
a default, audit_fields must record the COERCED value,
not the user's input. Better still, the wrapper rejects
the invalid input outright (per Section 3.2 above) so
audit_fields naturally reflects the actual computation.

This was the most common audit-field-discrepancy bug
class. The fix is the same as the silent-coercion fix:
add an allowlist gate. Once the gate is in place,
coercion can't happen, and audit_fields can't lie.

### 3.4 Sibling-wrapper bug propagation discipline

**Lesson source:** Sessions 24 + 25 (N-BEATS + N-HiTS).

When a follow-up fix is adapted from one wrapper to a
structurally similar sibling (same architecture family,
same param structure), the sibling MUST be audited
explicitly rather than presumed clean from the
parent's fix.

In N-BEATS / N-HiTS, the Follow-up 1a guard pattern
was applied to both wrappers separately, but the
guard's silent fall-through defect was identical in
both. The N-BEATS fix in Session 24 didn't propagate
to N-HiTS; Session 25 had to apply the same fix
again.

**Engineering implication:** when adding a fix to one
wrapper, search the codebase for the same pattern in
sibling wrappers. The validation-presence pattern is
an architectural property; same architecture =
same vulnerability surface.

### 3.5 Mid-audit reclassification discipline

**Lesson source:** Session 5 (KSC-ESS reclassification).

Findings get classified as severe / operational / cosmetic
during initial review. Sometimes the initial classification
is wrong: an apparent severe bug turns out to be
specification mismatch, or a methodology limitation.

Discipline: when an initial finding looks severe,
investigate root cause before classifying. Specifically
check:
- Is this a wrapper bug, or a methodology artifact?
- Is it a documented limitation of the underlying
  algorithm?
- Did the audit script have a bug that produced a false
  signal?

But: do NOT downgrade real operational concerns by
default. "Investigate before classifying" is not "always
reclassify down." Session 6's GARCH dispatch + EGARCH
persistence findings were initially flagged severe;
investigation confirmed they were genuinely severe (5
of 5 macro EGARCH cells reported spurious persistence
> 1).

### 3.6 Same-bug-class commit bundling protocol

**Lesson source:** Sessions 17 + 22 (5-finding bundles).

Standard CAL-R6 protocol caps single commits at 3
severe findings. Sessions 17 and 22 bundled 5 findings
each because:

1. Same bug class — all silent string acceptance with
   identical fix pattern.
2. Same files — splitting would mean editing the same
   files twice.
3. Cumulative LOC under budget.
4. Clean closure of the wrapper family.

The "defer 4th+" rule is for SPRAWLING UNRELATED bugs
(e.g., 4 bugs across 4 unrelated wrappers); same-bug-
class bundling is acceptable up to ~5 findings if it
fits within budget.

### 3.7 Numeric range coercions are same-class as string acceptance

**Lesson source:** Session 19.

Initially CAI was framed around "silent string
acceptance" as the dominant bug class. Session 19
established that numeric range silent coercions
(horizon=-1 → 1, alpha=2.0 → 0.05) have the same
architectural defect: silently changing the user's
intent without surfacing actionable error.

The fix pattern is the same: explicit gate returning
make_error_response. The bug-class taxonomy expanded to
5 modes accordingly.

### 3.8 try/except SAFE patterns are the rule, not the exception

**Lesson source:** Sessions 18 (structural_ts) + 24
(neural sklearn fallback).

A common reflex when writing wrappers is to add
try/except around library calls to avoid crashes.
This is generally GOOD — but the except clause must
produce an actionable user response.

The 4-class taxonomy (SAFE-PROPAGATE / SAFE-FALLBACK /
SAFE-RERAISE / HARMFUL) covers all observed wrapper
patterns. The HARMFUL pattern is rare (5 wrappers in
all of CAI), and is forbidden by the new standard.
The SAFE patterns are the dominant cases and should
be encouraged.

### 3.9 Solo audit pattern: 9 canonicals, full-depth Sweeps

**Lesson source:** Sessions 7 / 8 / 20 / 27 / 28.

Solo audits (1 wrapper per session) afford more
thorough Sweep 1-3 testing than batch audits. Pattern:

- Sweep 0: full validation matrix (all 5 failure
  modes)
- Sweep 1: parameter sweep with 3-4 sub-sweeps
- Sweep 2: 3-5 macro series + control synthetic
  fixture
- Sweep 3: 5 base canonicals + 4 adversarial canonicals
  (9 total)

Solo audits produce more findings per wrapper than
batch audits, but the per-finding effort is lower
because context is fresh.

### 3.10 Documentation is leverage

**Lesson source:** Session 29 (this).

CAI Phase 2 produced ~30 per-session findings docs,
each rich with diagnostic detail. Without
consolidation, that knowledge is discoverable but
not actionable — engineers writing new wrappers
must read 30 docs to extract the patterns.

This document and its companions ([Standard](wrapper_development_standard.md),
[Reference](validation_patterns_reference.md))
distill the institutional knowledge into ~3500
lines of operational documentation. The leverage is
~10x: a 600-line standard prevents future repeat of
patterns that consumed 1700 LOC of fixes.

Recommendation: maintain the 3 engineering docs as
TSL evolves. Update on cycle closure of any future
audit. Treat them as the authoritative wrapper-
engineering reference.

---

## 4. Methodology Notes

### 4.1 Three-technique audit structure

CAI Phase 2 settled on a 3-technique audit per wrapper:

1. **Sweep 0:** input validation matrix. For each user-
   facing param, test invalid values; for each multi-
   parameter surface, test inconsistent combinations.
   Catches all 5 failure modes.

2. **Technique 1:** compressed parameter sweep on
   synthetic fixtures with known DGP. Validates that
   the wrapper exercises the parameter as advertised.
   E.g., AR(1) phi sweep should produce
   monotonically-changing AR1 estimates.

3. **Technique 2:** real-data stress test on macro
   fixtures. Validates that the wrapper handles
   realistic input quirks (missing values, fat tails,
   autocorrelation, structural breaks).

4. **Technique 3 (per-wrapper):** adversarial
   canonicals — edge cases that should produce graceful
   behavior. Constant series, white noise, short
   series, pathological inputs.

### 4.2 Sweep 0 is highest leverage

Sweep 0 produced the vast majority of CAI findings
(~85 of 88 total). Techniques 1-3 mostly verified
that fixed wrappers continued to work correctly — they
caught zero new severe findings post-Sweep-0 across
the cycle.

**Engineering implication:** for new wrapper PRs, a
Sweep 0-style probe is the MINIMUM required test.
Techniques 2-3 can be deferred to canonical-test
script.

### 4.3 Audit-script template patterns

The audit script template stabilized around Session 12
and remained consistent through Session 28:

```python
def sweep_0_validation():
    findings = []
    # Per-wrapper probe matrix
    return findings

def technique_1_param_sweeps():
    rows = []
    # Per-wrapper sub-sweeps
    return rows

def technique_2_real_data():
    rows = []
    # Macro fixtures + per-wrapper applicability
    return rows

def technique_3_adversarial():
    findings = []  # if any C-CAL severity findings
    return findings

def main():
    # Aggregate findings
    # Print summary, write JSON
    return 0 if no severe findings else 1
```

This template is reusable for future audit cycles.

### 4.4 LOC budget protocol

CAL-R6 budgets:
- Solo audit: ≤100 LOC inline fixes
- Multi-wrapper batch (4+ wrappers): ≤150 LOC

Cumulative LOC across the cycle: ~1700, distributed:
- ~0 LOC for 36 wrappers (clean)
- ~1700 LOC for 41 wrappers (had findings)
- Average ~40 LOC per wrapper with findings

The 150-LOC cap is rarely the binding constraint in
practice. Same-bug-class bundling (§3.6) gives
flexibility when needed.

### 4.5 Status doc as cycle tracker

`docs/calibration_audit_status.md` served as the master
status tracker throughout CAI Phase 2. It tracked:
- Per-wrapper audit status (PENDING / AUDITED /
  DEFERRED)
- Per-session cycle table (commit hashes, finding
  counts)
- Per-category roadmap (Multivariate, ML/DL, etc.)
- Cumulative totals

Maintained pattern: update at session close, before
commit. Don't let it lag.

---

## 5. Summary

CAI Phase 2 closed at 100% wrapper coverage with 88
findings (40 severe + 42 op + 6 cosmetic) all fixed
inline. The validation-presence pattern was 100%
predictive across 77 extension wrappers across 5
failure modes. Wrappers with explicit validation
gates produced zero findings; wrappers without had
predictable bugs.

The institutional knowledge from CAI is now consolidated
into three engineering documents:

1. **[Wrapper Development Standard](wrapper_development_standard.md)** — directive (binding for new PRs)
2. **[Validation Patterns Reference](validation_patterns_reference.md)** — diagnostic + fix patterns
3. **CAI Empirical Findings** (this) — descriptive narrative

These docs replace the ~30 per-session findings docs
under `docs/calibration_audit/` as the primary
engineering reference. The per-session docs remain as
the audit trail for future re-investigation.

---

**Last revised:** 2026-04-28 (Session 29).
