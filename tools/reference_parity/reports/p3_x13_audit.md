# Phase 3 Batch 10 — `p3_x13` Audit

**Wrapper:** `engine/techniques/x13_seasonal_adjust.py`
**Reference:** R `seasonal::seas` (NOT installed — Tier C)
**Verdict:** **SKIP** (graceful — X-13 binary unavailable on host)
**Date:** 2026-04-29

## Result

The harness translates `X13NotFoundError` (raised by
`statsmodels.tsa.x13.x13_arima_analysis` when the X-13 binary
is missing from the host PATH) into an `ImportError`, which
the runner's SKIP-on-import-error path translates to a SKIP
outcome. **Informative-not-failing.**

## Rationale

X-13ARIMA-SEATS requires a binary distributed by the US
Census Bureau. Installation is non-trivial on Windows
(separate download from Census Bureau; PATH configuration);
the R `seasonal` package wraps the same binary. CI runners
(both Windows and Linux) typically lack this binary unless
explicitly provisioned.

Per Session 1 inventory, X-13 was flagged as a deferred /
Tier C candidate. Session 14 confirms this disposition:

- Master plan §15.12 referenced `R seasonal` as the parity
  reference.
- R `seasonal` was NOT installed on the local R library
  during Session 14 deps verification.
- Both arms (TSL via `statsmodels.tsa.x13` and reference via
  R `seasonal`) require the same X-13 binary.
- Without the binary, both arms fail; SKIP is the correct
  verdict.

## Harness improvement (Session 14)

The runner's SKIP-on-import-error semantics — historically
applied only to `run_reference` — were extended to also cover
`run_tsl` in Session 14. This generalizes the established
"missing-dependency = SKIP, broken-implementation = ERROR"
discipline to TSL-side dependencies, as needed by binary-
dependent wrappers like X-13.

The pattern is now general-purpose: any wrapper whose Python
backend depends on a host binary (X-13, custom CLI tools)
can raise ImportError on missing-binary detection and the
runner produces SKIP.

## Pattern J catalog entry

Documented as B.6.2 in
`docs/engineering/parity_diagnostic_reference.md` Appendix
B — "X-13 binary not installable on Windows CI; seasonal
package unusable in CI matrix; resolution via SKIP-graceful
ImportError translation."

## Re-running this check

To enable parity execution:
- Windows: install X-13ARIMA-SEATS binary from
  https://www.census.gov/data/software/x13as.html and add
  to system PATH
- Linux: install via package manager
  (`sudo apt install x13as` on Debian/Ubuntu)
- Linux/macOS: build from source

Then `R> install.packages("seasonal")` and rerun the check.
