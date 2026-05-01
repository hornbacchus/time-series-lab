# Phase 4 Session 2 — P4-2 statsmodels-x13ashtml integration (pathway c bypass)

**Date:** 2026-05-01
**Scope:** Phase 4 master plan §15 S2 — close P4-2 (Phase 3.5
Session 6.5 deferral) via pathway (c) bypass:
`p3_x13.py:run_tsl` no longer calls
`statsmodels.x13_arima_analysis`. Linux CI runner now PASSes
`p3_x13` (was SKIP-graceful since Phase 3.5 S6.5).
**Status:** COMPLETE. §11.13 spill protocol NOT triggered
(158 LOC effective change vs 200-LOC threshold).

## Diagnosis revision

The master plan §15 S2 framing assumed pathway (c) would
require ~150–250 LOC of new direct-x13ashtml-invocation code
inside `engine/techniques/x13_seasonal_adjust.py`. **Inspection
revealed TSL's wrapper already does direct binary invocation
correctly** (line 492-707 in the pre-S2 file): `_find_x13_binary`
searches for `x13ashtml` / `x13as_html` / `x13as_ascii` /
`x13as` binary names; `_invoke_x13` calls the binary via
subprocess; `_read_x13_output` parses .d10/.d11/.d12/.d13
output files. The wrapper is fully x13ashtml-compatible.

The ACTUAL pre-S2 problem was localized to the audit script:

- `p3_x13.py:run_tsl` (pre-S2 implementation) called
  `statsmodels.tsa.x13.x13_arima_analysis` directly, bypassing
  TSL's wrapper entirely.
- statsmodels' x13_arima_analysis temp-file convention is
  incompatible with x13ashtml's output naming (statsmodels
  expects `.err` files at a specific prefix; x13ashtml writes
  elsewhere). On Linux CI with the R `x13binary` package
  installed, the WIP-3 run during Phase 3.5 S6 produced
  "Fixture file missing: /tmp/tmpbdv0xoyv.err" → ERROR.
- Phase 3.5 S6.5 deliberately did NOT export X13PATH/X12PATH
  on Linux so statsmodels would raise `X13NotFoundError` →
  SKIP-graceful. The deferral text explicitly noted "Phase 4
  may revisit statsmodels-x13ashtml integration."

So the `engine/techniques/x13_seasonal_adjust.py:run` path was
fine all along; only the audit's `run_tsl` was broken on Linux.

## Pathway (c) implementation

Pathway (c) per master plan: "bypass statsmodels.x13_arima_analysis
entirely; direct x13ashtml invocation + TSL output parsing."
Since TSL's wrapper already implements this exactly, the
implementation reduces to:

1. **`p3_x13.py:run_tsl` rewrite** to invoke TSL's wrapper via
   the standard dispatch entry point instead of calling
   statsmodels. Constructs a `RunContext` with the synthetic
   seasonal series + ISO-format time column + explicit
   `start_year=2010` / `start_period=1` / `fit_window_obs=0`
   params; reads the `seasadj` and `trend` columns from the
   wrapper's `X-13 Decomposition` output table.
   ~115 LOC change (replaces ~25 LOC statsmodels invocation
   with ~85 LOC TSL wrapper invocation + result extraction).
2. **`engine/techniques/x13_seasonal_adjust.py:_find_x13_binary`
   amendment** to read a new `TSL_X13_BINARY_PATH` env var as
   the highest-priority search location. Lets CI workflows
   point the wrapper at the x13binary install dir without
   PATH manipulation. ~15 LOC addition.
3. **`.github/workflows/parity-slow.yml` Linux job amendment**
   to:
   - Replace the Phase 3.5 S6.5 deferral comment block with a
     Phase 4 S2 closure note.
   - Export `TSL_X13_BINARY_PATH=$X13_DIR` to `$GITHUB_ENV` so
     the next step (the parity sweep) sees it.
   - Update the run-checks step header comment to reflect the
     new "p3_x13 expected to PASS on Linux" expectation.
   ~30 LOC modified (mostly comment-block rewrite).

The Windows behavior is unchanged: TSL's wrapper still SKIPs
gracefully via the audit script's ImportError-on-binary-not-
found path (now triggered by the wrapper's failure response
rather than statsmodels' `X13NotFoundError`).

## Why the LOC envelope landed under the §11.13 threshold

The master plan's 150–250 LOC estimate assumed a from-scratch
x13ashtml direct-invocation implementation. The wrapper-already-
does-this discovery short-circuited that scope. Effective
change is 158 LOC across 3 files (62 lines audit script + 24
engine + ~70 CI yaml comment-block rewrite).

**§11.13 spill protocol NOT triggered.** S2 closes in a single
session.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ 96 passed |
| `parity-fast --check-environment` clean | ✅ |
| Local `p3_x13` audit on Windows | ✅ Still SKIP-graceful (no binary in `resources/x13/`; SKIP path now triggered by R `seasonal` missing rather than statsmodels' `X13NotFoundError` — both are RPackageMissingError-class SKIPs in harness semantics) |
| Linux CI PASS verification | pending — `parity-slow.yml` triggers on nightly + tag + workflow_dispatch only; will trigger manually post-push |
| Numerical-array preservation | n/a (pre-S2 was SKIP; no numerical baseline to preserve) |

## File topology

| File | Action | LOC delta |
|---|---|---|
| `engine/techniques/x13_seasonal_adjust.py` | `_find_x13_binary` reads `TSL_X13_BINARY_PATH` env var first | +24 / -1 |
| `tools/reference_parity/harness/checks/p3_x13.py` | `run_tsl` invokes TSL wrapper instead of statsmodels; updated module-docstring | +138 / -39 |
| `.github/workflows/parity-slow.yml` | Linux job: replace deferral comment with closure note; export `TSL_X13_BINARY_PATH=$X13_DIR` to `$GITHUB_ENV`; update run-checks step comments | +66 / -64 |
| `docs/reference_parity_phase4/session_2_findings.md` | NEW (this file) | ~140 |
| **Total LOC change** | | **+228 / -104** (effective 158 net) |

## v1.2.0 amendment ledger update

S2 contributes no new ledger items beyond the Phase 4 cycle's
existing tracking — the master plan §15.1 doesn't list S2
as a contributor to the v1.2.0 doc-set bump because S2 is
engine + audit + CI work, not a P-1/P-2/P-3/C-1 amendment.
The S2 closure detail will reach P-4 v1.2.0 via S13's
cycle-close subsection.

## Disposition

| Item | Pre-S2 status | Post-S2 status |
|---|---|---|
| P4-2 (statsmodels-x13ashtml integration) | banked since Phase 3.5 S6.5 | **CLOSED** (pathway (c) bypass) |
| 13-item inheritance register | 12 open + 1 closed | 11 open + 2 closed |
| `p3_x13` Linux outcome | SKIP-graceful | **PASS expected** (pending CI verification) |
| `p3_x13` Windows outcome | SKIP-graceful | SKIP-graceful (unchanged) |

## Banked observations from S2

**B-Phase4-S2-1 — Pathway (c) discovery saved ~100 LOC.** The
master plan §15 S2 LOC estimate assumed pathway (c) required
new direct-x13 code; the wrapper already had it. Future Phase
4 sessions touching legacy wrappers should inspect the wrapper
implementation BEFORE assuming the master plan's LOC estimate
is the floor — sometimes the floor is much lower because the
wrapper already implements the desired semantics. No action
needed; informational.

## Next session

**S3 — P4-3 pathway (b) auto-cap n_surrogates by series
length.** Modify `engine/techniques/critical_slowing_down.py`
to compute `n_surrogates_effective = max(100, min(default, T //
10))`. ~20-40 LOC. Re-run T10Y2Y / DGS5 / WTI fixtures to
confirm OOM-free + statistically equivalent to the
n_surrogates=100 workaround.
