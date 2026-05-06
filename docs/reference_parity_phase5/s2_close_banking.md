# Phase 5 S2-close banking — parity-slow workflow scope + Chat-Code halt coordination limitation

**Date:** 2026-05-05
**Origin:** Q-Forward-1=(b) brief pause for banking +
Q-Forward-2=(b) co-located banking entries + Q-Forward-3=(a)
standalone banking commit on top of `95756d1`. S2-β-redux
CLOSED at commits `1715cc3` + `95756d1` (CI green via
workflow run 25460924870); S2 first execution-class session
GENUINELY COMPLETE per parity-fast verification. Co-located
codification of 2 institutional learnings surfaced from S2
sequence work but not yet codified in institutional record;
per Q-banking-categorical discipline at
B-Phase5-S2-α-2-redux-Q-BANKING-DISCIPLINE-REFINEMENT
(`95756d1`).

## B-Phase5-PARITY-SLOW-WORKFLOW-SCOPE-CONTEXT — Parity-slow workflow scope: scheduled validation, not per-commit gate

At S2-α-2-redux closeout, parity-slow workflow Linux job
Cancelled status surfaced via overnight email for commit
`ffc08d3`. Initial Chat-side framing assumed parity-slow was
per-commit CI gate parallel to parity-fast; that framing was
wrong. GitHub Actions UI verification confirmed: Reference
Parity (slow) is a SCHEDULED workflow (not push-triggered),
running on cron schedule (~nightly). Run on `ffc08d3` was
scheduled overnight run that landed on master HEAD at
scheduled time, NOT triggered by S2-α-2-redux commit.
parity-slow is OUT-OF-SCOPE for per-commit CI verification;
per-commit gate is parity-fast (push-triggered). Linux job
Cancelled at `ffc08d3` parity-slow run #19 (4:12 AM EDT
scheduled run; Linux Cancelled + Windows succeeded 7m 17s)
deferred to backlog as separate investigation (mechanical
noise vs Linux-specific regression undetermined; not blocking
Phase 5 forward motion). Cross-references:
B-Phase5-S2-α-1-redux-CI-VERIFICATION-PROTOCOL at S2-α-1-redux
findings (parity-fast as per-commit gate; framing CORRECT as
banked); parity-slow workflow run #19 at `ffc08d3`.
Forward-looking: Phase 5 + Phase 6+ CI verification protocol
scoped to parity-fast for per-commit gate; parity-slow
concerns surfaced as async backlog items; future cycle
authors do NOT treat parity-slow status as gating per-commit
work; if parity-slow workflow trigger mechanics change (push-
triggered added; scope expansion), CI verification protocol
re-examined.

## B-Phase5-CHAT-CODE-HALT-COORDINATION-LIMITATION — Chat-Code halt coordination architectural gap

Halt instruction from Chat to Code does not propagate as
execution-blocking signal. Triggers ship with execution
authority; once Code begins execution, halt instructions
issued by Chat in subsequent messages require active user-
side relay + may not catch in-flight execution. Pattern
surfaced TWICE in Phase 5 sequence: (1) at original S2-α-1
dispatch regression diagnosis, halt instruction did not
reach Code; Code completed S2-β commits (`4bf5939` +
`f628572`) while Chat-side diagnostic exchange ongoing;
later required 5-revert sequence + banking commit `dd368b3`;
(2) at parity-slow surfacing post S2-β-redux trigger ship,
halt instruction did not catch S2-β-redux execution; Code
completed `1715cc3` + `95756d1` commits while Chat-side
diagnostic exchange ongoing (this case resolved without
revert because parity-slow ultimately out-of-scope for per-
commit gate per parity-slow workflow scope banking entry
above).

**Protocol refinement (going forward):** Chat-side halt
instructions framed as explicit "STOP-AND-CONFIRM" messages
with confirmation requirement. User-side relay verbatim.
Code confirms halt + waits for next disposition before any
further work. Standard halt format: "STOP. <halt reason>.
Confirm halt + await Chat disposition." This standardizes
halt protocol beyond the implicit verbal-halt pattern that
surfaced as insufficient. Cross-references: original S2-α-1
halt-and-revert sequence (5 reverts + banking `dd368b3`);
parity-slow surfacing exchange + S2-β-redux execution
despite halt; B-Phase5-S2-CI-VS-LOCAL-GATES-DIVERGENCE
banking (separate but related pattern of "validation surface
that exists but isn't part of effective gate"). Forward-
looking: protocol applies to S3+ Phase 5 sessions + Phase 6+
inheritance. Trigger structure unchanged (no pre-execution
checkpoint per Q-Parity-Slow-3 disposition); halt protocol
standardized via explicit "STOP-AND-CONFIRM" framing. Future
Chat-Code coordination architectural improvements (e.g., pre-
execution checkpoint per Q-Parity-Slow-3-(a) alternate;
trigger ack protocol; cancel-in-flight mechanism) reviewed
at Phase 5 close OR Phase 6+ design.

## Disposition

S2-close banking codified. S3 trigger drafting begins per
Q5=b-2 sequence. S3 (MCMC-stochastic-vol pair per master
plan v1.1 §15 S3) is FIRST session exercising v1.1 standing
discipline 3-criteria gate prospectively; S2 sequence
empirical observations (now empirically clean per refined
framework + per-wrapper field-availability protocol
validated at trio scope + verified-via-CI 5/5 redux commits)
inform S3 criterion 3 empirical-validation-envelope
assessment.
