# Post-Phase-5-cycle-close parity-slow slow-linux runner provisioning fragility — banking entry

**Date:** 2026-05-09
**Origin:** Post-Phase-5-cycle-close operational hygiene
sub-session per Q-parity-slow-remediation=A. Diagnostic
investigation surfaced curl-cascade R package compile failure
on slow-linux job; Option A targeted patch applied at Commit 1
(`301ad4d`); banking entry at this commit (Commit 2; END)
codifies recurrent provisioning fragility pattern + Phase 6+
inheritance.

## B-Phase5-POST-CLOSE-PARITY-SLOW-LINUX-PROVISIONING-FRAGILITY — Slow-linux runner provisioning fragility recurrent pattern + Option A targeted patch + Phase 6+ architectural redesign optionality

At post-Phase-5-cycle-close diagnostic investigation, Reference
Parity (slow) workflow nightly failures empirically observed
across 3-run streak (last green `25484605216` 2026-05-07; first
failure `25484605216`+1 2026-05-06; recent `25595720371`
2026-05-09). Diagnosis identified curl-cascade R package compile
failure on slow-linux Ubuntu runner: `curl/curl.h: No such
file or directory` during R `curl` package source compilation;
cascades to `quantmod` / `tseries` / `tsDyn` failures (slow-tier
exclusive R packages with curl transitive dependency). Root
cause: `libcurl4-openssl-dev` system header missing on Ubuntu
runner; R needs source-compile path for curl package (no
precompiled binary available for runner R version on Linux).

**Recurrent failure pattern empirically observed:**
- 2026-04-30 `25140911421`: fixture file missing (different
  failure mode; not curl-cascade)
- 2026-05-06 onward: curl-cascade pattern (3-run streak)
- 2026-05-06 `25423968727`: slow-linux job cancelled (runner
  unavailability; environmental flakiness)

Pattern indicates **recurrent provisioning fragility on
slow-linux runner**, NOT a single-cause issue. Different
failure modes surface across runs; underlying fragility is
runner provisioning + dependency management on ephemeral
Ubuntu runners.

**Option A targeted patch applied (Commit 1 `301ad4d`):**
Added `apt-get install -y libcurl4-openssl-dev libssl-dev
libxml2-dev` step BEFORE Set up R on slow-linux job in
`.github/workflows/parity-slow.yml`. Verification via manual
workflow trigger (`25601501228`): curl-cascade RESOLVED — R
package install completed past curl step into substantive
parity test execution. Workflow still failed but at "Run
slow-tier parity checks" step (substantive content failure on
2b/2c MCMC SV BLOCK per Phase 5 latent risk
B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING +
B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK), NOT at
curl-cascade. **Targeted patch success criterion met.**

**Underlying fragility NOT resolved:** Next failure mode
emergence empirically expected per recurrent pattern. Current
patch is bounded fix targeting one specific failure mode (curl
compile dependency); does not address architectural fragility
of ephemeral Ubuntu runner provisioning model.

**Cross-references** (per (mit-ii) brief):
B-Phase5-PARITY-SLOW-WORKFLOW-SCOPE-CONTEXT at
`s2_close_banking.md` (parity-slow async backlog framing;
out-of-scope for per-commit gate);
B-Phase5-S3-ALLOWLIST-VS-PARITY-SLOW-LATENT-RISK +
B-Phase5-S3-MCMC-SV-ESS-EMPIRICAL-FINDING at
`s3_execution_banking.md` (substantive parity-slow failure
modes anticipated by Phase 5 banking; both non-blocking by
design); diagnostic findings at plan file
`C:/Users/matth/.claude/plans/glistening-wishing-mountain.md`;
Commit 1 `301ad4d` (workflow YAML patch); manual trigger
verification run `25601501228` (curl-cascade resolution
confirmed; substantive failures persist per Phase 5
anticipation).

**Forward-looking — Phase 6+ inheritance:**

Phase 6+ Chat optionality preserved on architectural redesign
(NOT pre-committed by this banking entry; inheritance asset
candidate input for cycle-architecture recalibration agenda):

- (a) **Docker image with system packages baked in** —
  pre-built container image with libcurl/libssl/libxml2/
  x13binary system dependencies; eliminates per-run apt-get
  step + per-run R source compilation overhead
- (b) **Linux-via-WSL on Windows runner** — single Windows
  runner with WSL Ubuntu for x13binary support; eliminates
  separate slow-linux job entirely
- (c) **Eliminate slow-linux job entirely** — accept x13binary
  scope loss; rely on slow-Windows + parity-fast for cycle
  coverage
- (d) **Continue per-failure-mode targeted patches** (current
  approach) — apply Option A-class bounded fixes as failure
  modes emerge; no architectural change

Recurrence frequency observed at ~2-week intervals (2026-04-30
→ 2026-05-06 → 2026-05-09); if pattern holds, next failure
mode emergence ~2026-05-23 baseline expectation. Phase 6+
cycle-architecture recalibration may disposition (a)/(b)/(c)/
(d) per cycle scope + agenda.

**Operational hygiene framing:** This sub-session is
post-Phase-5-cycle-close operational hygiene. Phase 5 cycle
institutional close at `761ae89` (master plan v1.2 + §17/§18
closure note authoritative) NOT amended. Banking entry preserved
in Phase 5 docs directory (`docs/reference_parity_phase5/`)
for inheritance navigation continuity; future Phase 6+ docs
directory established per Phase 6+ Chat disposition.

## Disposition

Post-Phase-5-cycle-close parity-slow slow-linux provisioning
fragility codified as Phase 6+ inheritance asset. Option A
targeted patch successful at curl-cascade resolution per
manual trigger verification (`25601501228`). Substantive
parity-slow failures (MCMC SV BLOCK on ess) persist per Phase
5 latent risk anticipation; NOT blocking per Phase 5 banking
framing (parity-slow async backlog out-of-scope for per-commit
gate). Phase 6+ Chat optionality preserved on architectural
redesign (paths a-d above) at cycle-architecture recalibration.
