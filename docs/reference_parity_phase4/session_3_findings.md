# Phase 4 Session 3 — P4-3 CSD wrapper memory scaling (pathway b auto-cap)

**Date:** 2026-05-01
**Scope:** Phase 4 master plan §15 S3 — close P4-3 (Phase 3.5 Session 8
deferral) via pathway (b) auto-cap. Adds series-length-aware
n_surrogates cap to `engine/techniques/critical_slowing_down.py`
plus two transparency audit fields.
**Status:** COMPLETE.

## What changed

`engine/techniques/critical_slowing_down.py`:

1. **Auto-cap formula** at the parameter-resolution site
   (replacing the prior `n_surrogates = int(ctx.get_param(
   "n_surrogates", cfg["n_surrogates"]))` line):

   ```python
   n_surrogates_user = ctx.get_param("n_surrogates")
   n_surrogates_default_per_preset = int(cfg["n_surrogates"])
   if n_surrogates_user is not None:
       n_surrogates = int(n_surrogates_user)
       n_surrogates_auto_capped = False
   else:
       n_surrogates_capped = max(
           _MIN_SURROGATES_FLOOR,
           min(n_surrogates_default_per_preset, T // 10),
       )
       n_surrogates_auto_capped = (
           n_surrogates_capped < n_surrogates_default_per_preset
       )
       n_surrogates = n_surrogates_capped
   ```

   `_MIN_SURROGATES_FLOOR = 100` — methodological floor for
   stable empirical p-value estimation.

2. **Two new transparency audit fields** populated alongside
   the existing `n_surrogates`:
   - `n_surrogates_default_per_preset` — what the preset
     would have given absent the cap (transparency for the
     user comparing effective vs default).
   - `n_surrogates_auto_capped` — boolean indicating whether
     the cap fired.

3. **Docstring on `_PRESET_CONFIG`** explaining the cap
   formula + Phase 3.5 S8 OOM origin context.

`engine/tests/test_interpretation_contract.py`:

- T14 fixture (`_MINIMAL_INPUT`) gains the two new None-default
  keys so the spec null-guards via `.get()`.
- T15 allowlist gains the two chained-underscore tokens
  defensively (already disqualified by the adjacent-underscore
  lookaround on the T15 regex; allowlisting keeps intent
  explicit).

## Why pathway (b) (not (a) cap-default or (c) chunking)

Per master plan §15 S3 locked decision: pathway (b) auto-cap by
series length. Compromise between (a) cap-default (~10 LOC; too
blunt — also caps short-series cases that previously had
headroom) and (c) chunk surrogate dim (~100-180 LOC; complex;
numerical-equivalence verification required).

Pathway (b) preserves preset-default behaviour on long-enough
series (T≥10000 for Balanced) while scaling smoothly down to
the methodological floor (100) for the OOM-prone case.

## Behaviour table — empirical verification

Confirmed via local smoke test on representative T values
(Balanced preset, default `n_surrogates=1000`,
`compute_pvalues=True`):

| T | n_surrogates effective | Mechanism |
|---:|---:|---|
| 200 | **100** | floor (T//10 = 20 < 100) |
| 1000 | **100** | floor (T//10 = 100; max(100, min(1000, 100)) = 100) |
| 2000 | **200** | T//10 (2000//10 = 200; auto-cap fires) |
| 2500 | **250** | T//10 (2500//10 = 250; auto-cap fires; **closes Phase 3.5 S8 T10Y2Y T=2501 OOM case**) |
| 11000 | 1000 | preset default (T//10 = 1100 > 1000; cap does NOT fire; deterministic from formula — empirical verification skipped due to ~minutes-long surrogate compute time on long series) |

User-supplied `n_surrogates` values bypass the cap entirely
(explicit user opt-in to managing their own memory
constraints).

## Why the CSD parity audit is unaffected

`tools/reference_parity/harness/checks/critical_slowing_down.py`
runs with `compute_pvalues=False` (line 145), bypassing the
surrogate-generation path entirely. The audit compares
deterministic Kendall taus + rolling indicator series, not
empirical p-values. Auto-cap on `n_surrogates` therefore does
NOT perturb the audit's numerical output.

Verified: post-S3 audit run shows `max_abs_diff` values of
2.2e-16 (rolling_ar1) / 1.2e-17 (rolling_variance) /
0.0 (tau_ar1) / 0.0 (tau_variance) — bit-exact PASS unchanged
from pre-S3 baseline.

## Verification gates per master plan §19

| Gate | Status |
|---|---|
| `engine/tests/` pytest 96/96 PASS preserved | ✅ 96 passed |
| `parity-fast --check-environment` clean | ✅ |
| Per-wrapper test suite (`critical_slowing_down`) | ✅ T14 + T15 contract tests pass with new fields |
| CSD parity audit PASS preserved | ✅ 2.2e-16 abs diff (unchanged from pre-S3) |
| Numerical-array preservation on `compute_pvalues=False` paths | ✅ deterministic; unaffected by surrogate-count change |
| `parity-fast` outcome distribution | (will verify post-push CI) |

## Numerical-behaviour change analysis

**On `compute_pvalues=False` paths:** zero numerical change.
Surrogate generation bypassed.

**On `compute_pvalues=True` paths with T < 10000 + Balanced
preset:** empirical p-values now derived from a smaller
surrogate sample. Concrete examples:
- T=200: 100 surrogates instead of 1000. P-value granularity
  drops from 0.001 to 0.01.
- T=2000: 200 surrogates instead of 1000. P-value granularity
  drops from 0.001 to 0.005.

**Impact on user-facing outputs:** p-value precision degrades
slightly on short series; on the OOM-prone long series it
makes the wrapper actually run instead of OOM-killing. The
master plan's "statistically equivalent to the n_surrogates=
100 workaround" criterion is met because all auto-cap values
are ≥ 100, the empirically-validated workaround floor.

## File topology

| File | Action | LOC delta |
|---|---|---|
| `engine/techniques/critical_slowing_down.py` | auto-cap formula + two new audit fields + `_MIN_SURROGATES_FLOOR` constant + `_PRESET_CONFIG` docstring expansion | +65 / -4 |
| `engine/tests/test_interpretation_contract.py` | T14 fixture + T15 allowlist | +14 / -3 |
| `docs/reference_parity_phase4/session_3_findings.md` | NEW (this file) | ~150 |
| **Total LOC change** | | **+229 / -7** (~75 LOC code/test; rest is docs) |

LOC well within standard CAL-R6 100-LOC budget for a solo audit
(plan estimate was 20-40 LOC; actual code change ~75 LOC due
to the two transparency-field additions + docstring expansion;
still well under the standard budget). §11.13 spill protocol
N/A (S3-specific, not a multi-session split point).

## v1.2.0 amendment ledger update

S3 contributes no new entries to the v1.2.0 doc-set ledger —
the changes are engine + test + docs/findings only, not
P-1/P-2/P-3 amendments. The S3 closure detail will reach P-4
v1.2.0 via S13's cycle-close subsection.

## Disposition

| Item | Pre-S3 status | Post-S3 status |
|---|---|---|
| P4-3 (CSD wrapper memory scaling) | banked since Phase 3.5 S8 | **CLOSED** (pathway b auto-cap) |
| 13-item inheritance register | 11 open + 2 closed | **10 open + 3 closed** |
| Phase 4 cycle progress | 2 of 13 sessions complete | **3 of 13 sessions complete** |

## Banked observations from S3

**B-Phase4-S3-1 — Two transparency audit fields preserve
forward observability without breaking back-compat.** The
addition of `n_surrogates_default_per_preset` +
`n_surrogates_auto_capped` follows the BYF-Mod-1 pattern
(`n_maturities_populated` + `maturities_populated`):
when adding wrapper-level adaptive logic, expose both the
user-visible effective value AND the would-have-been default,
so users diagnosing unexpected behaviour can see exactly
what the cap did. Informational; future Phase 5 wrapper-
adaptive-logic work should follow this pattern.

## Next session

**S4 — Pattern A audit scaffold + #2 Minnesota dummy-obs
Pattern A.3 fragment.** First of three Pattern A audit
sessions (S4–S6). Introduces shared scaffold helpers under
`tools/reference_parity/harness/checks/_pattern_a_helpers.py`;
applies to the smallest of the three audits (#2 Minnesota
dummy-Y/X reimpl per Doan-Litterman-Sims 1984 §3 verbatim).
Bumps P-2 §C.3/§C.4 amendment ledger.
