# Reference Parity Framework Reference — successor onboarding asset for sub-domain (i)+ work

**Purpose:** This doc enables a successor Code instance with no
prior cycle context to ship their first sub-session. Operational
discipline first; reference depth as appendix. Section ordering
optimizes for first-time-shipper utility, not cycle cataloging.

Sections:
- §1 Quick-start — concrete action sequence
- §2 Operational discipline — chunking + smoke test + CI + gates
- §3 Pattern recipes — per-wrapper integration + cross-wrapper
  acceptance + banking, with worked examples
- §4 Banking pointer index — situation-keyed access pattern
- §5 Reference — master plan link + cycle-architecture appendix

---

## §1 Quick-start

Concrete action sequence for shipping a first sub-session.
Execute top-to-bottom; no forward references to §2-§5 needed
for this section.

### 1.1 Working directory

```bash
cd "C:/Users/matth/OneDrive/Projects/Time Series Lab"
```

(Adjust path if successor inheritance moves the repo location.)

### 1.2 Pre-commit gates

Run all three before any commit (doc-only or code-modification):

```bash
PYTHONPATH=tools "C:/Python314/python.exe" -m reference_parity --check-environment
"C:/Python314/python.exe" tools/validate_install_matrix.py
"C:/Python314/python.exe" -m pytest engine/tests/ -q
```

Expected: R/Python packages match MANIFEST; install-matrix OK;
96/96 pytest PASS. If any gate fails, do NOT commit; investigate
or surface to Chat.

### 1.3 Sub-session opening protocol

Before authoring:
- Read the trigger you received from Chat
- Read the most recent prior closeout report
- `git status` — verify working tree clean (only historical
  scratch acceptable as untracked)
- `git rev-parse HEAD` — verify master HEAD matches expectation
  per trigger reference

### 1.4 First commit pattern (HEREDOC + co-author trailer)

```bash
git add <files>
git commit -m "$(cat <<'EOF'
<title summarizing the commit>

<body with disposition references; brief cross-references>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
git push origin master
```

### 1.5 Closeout protocol

After commit(s) push:
- `gh run list --workflow=parity-fast.yml --limit 3` — locate
  workflow run for your commit
- `gh run watch <run-id> --exit-status` — wait for END commit
  CI completion
- Report: commit SHA(s) + workflow run ID + CI green status on
  END commit per multi-commit-sequence framing

For multi-commit sequences, CI verification at sequence END
(intermediate commits informational only).

---

## §2 Operational discipline

### 2.1 Chunking thresholds

- **§13.1 default:** 200 LOC clean per single commit
- **§13.1 marginal-tolerance band:** 200-220 LOC; (mit-i)
  cascading split pre-authorized at this band per Phase 5
  standing
- **§13.4 hard threshold:** >220 LOC; surface to Chat per
  UPDATED CONSTRAINT 4 (do NOT trim post-hoc)

For multi-section docs, cascading split at categorical seam
(content-type or file-boundary) keeps each commit clean per
§13.1 default.

### 2.2 Smoke test semantic decision tree by invariant class

Before authoring per-wrapper smoke test, identify invariant
class:

- **Closed-form deterministic** (e.g., kalman, johansen, evt,
  mint, transformer attention normalization): assert
  PASS-deterministic. Invariant outcome is mathematically
  determined; smoke test verifies dispatch fires + outcome
  PASS on real fixture.

- **MCMC stochastic** (e.g., mcmc_sv_gaussian,
  mcmc_sv_student_t): loose-assertion. Invariant outcome may
  be PASS / CAVEAT / BLOCK depending on chain quality at
  fixture; smoke test verifies dispatch fires + valid status
  returned. BLOCK on real fixture is NOT a smoke test failure
  for this class.

- **INVERTED tolerance** (e.g., caviar_sav christoffersen
  p-value): PASS-deterministic + INVERTED orthogonality.
  Checker handles INVERTED comparison internally (PASS if
  pvalue > floor; CAVEAT/BLOCK at lower tail); smoke test
  asserts on outcome status not raw value direction.

If smoke test fails on real fixture for closed-form class,
investigate (likely real bug). If MCMC class returns BLOCK,
verify chain configuration but do NOT treat as test failure.

### 2.3 CI verification protocol

- **Doc-only commits:** pre-commit gates sufficient regression
  verification; environmental CI failure (billing/spending
  limit) deferrable per
  Q-S5-CI-environmental-1=(β) substantive interpretation
- **Code-modification commits:** STRICT CI verification
  required; environmental failure blocks commit until
  resolution
- Watch: `gh run watch <run-id> --exit-status` on END commit
- Multi-commit-sequence: CI verification at sequence END
  (intermediate commits informational only)
- Workflow exit codes: 0 (PASS/SKIP) → green; 1 (BLOCK) → red;
  2 (CAVEAT) → green-mapped; 3 (ERROR) → red; 4
  (DOCUMENTED-DIVERGENCE) → green-mapped

### 2.4 Pre-commit gates per §19

Run all four; commit only if all pass:

1. `parity-fast --check-environment` — R/Python package
   versions match MANIFEST
2. `engine/tests/` pytest — 96/96 PASS preserved
3. `_test_structural_invariants.py` — 7/7 PASS preserved
4. `validate_install_matrix.py` — install-matrix consistency
   (P-1 §8.5)

For execution-class commits adding wrappers/dispatch, also run
local parity-fast tier (`PYTHONPATH=tools python -m
reference_parity --tier fast`) and verify NO new BLOCK +
allowlist gating preserved + new wrapper PASS with invariant
firing.

---

## §3 Pattern recipes

Recipe-with-worked-example for the three integration patterns:
per-wrapper integration, cross-wrapper acceptance,
banking-when-warranted.

### 3.1 Per-wrapper integration recipe

**Step 1 — Identify Case** per per-wrapper field-availability
protocol:
- **Case 0** — required field already exposed at `run_tsl()`
  top level. No harness expansion; only allowlist + smoke
  test.
- **Case (i)** — required field NOT exposed. Harness wrapper
  expansion required, with two variants:
  - *Representative-choice*: select specific layer/family
    member for invariant check (exemplar:
    `mint_shrinkage` / Layer 0)
  - *Rename mapping*: map engine field name to harness
    expected field name (exemplar:
    `engine.christoffersen_pval` →
    `harness.chris_pvalue`)
- **Case (iii)** — engine `audit_fields` exposed but harness
  needs extraction at `run_tsl()` boundary
- **Cases (ii) + (iv)** — unobserved across Phase 5; reserved
  for future empirical observation

**Step 2 — Allowlist add:** append `<technique_id>` to
`_INVARIANTS_DISPATCH_ALLOWLIST` in
`tools/reference_parity/harness/runner.py`.

**Step 3 — Harness expansion** (Case (i) / (iii) only): edit
`tools/reference_parity/harness/checks/<wrapper>.py` to expose
required field at `run_tsl()` top level via representative
choice OR rename mapping.

**Step 4 — Smoke test:** add `test_<wrapper>_real_dispatch` in
`_test_s2_alpha_invariants_dispatch.py` per invariant class
semantic (§2.2).

**Step 5 — Findings doc** at
`docs/reference_parity_phase5/session_<N>_findings.md` per
~150-200 LOC class baseline.

**Worked example — S4-α `3e_mint_family` Case (i)
representative-choice:** field `mint_shrinkage_lambda` not
exposed at `run_tsl()` top level (Case (i)). Harness expansion
selected `mint_shrinkage` family member as representative
(closed-form deterministic). Smoke test asserts
PASS-deterministic. Banked Case (i) representative-choice
variant per Q-banking-categorical strict.

**Worked example — S4-γ `3a_caviar_sav` INVERTED Case (i)
rename mapping:** engine exposes `christoffersen_pval` but
harness checker expects `chris_pvalue`. Harness expansion =
rename map at `run_tsl()` boundary. INVERTED tolerance handled
at checker level; smoke test PASS-deterministic on outcome
status.

### 3.2 Cross-wrapper acceptance recipe

Per-class aggregation per S5 3-class structure (closed-form /
MCMC stochastic / INVERTED). Single-class cross-wrapper test
per class; aggregate via `aggregate_outcomes` ranking.

**Steps:**
1. Add per-class cross-wrapper test (e.g.,
   `test_cross_wrapper_acceptance_<class>`) in
   `_test_s2_alpha_invariants_dispatch.py`
2. Iterate over wrappers in class; collect outcomes; aggregate
3. Assert per class semantic (PASS-deterministic for
   closed-form + INVERTED; loose for MCMC stochastic)
4. Update `test_allowlist_gating` if new wrapper added to
   allowlist

**Worked example — S5 cross-wrapper acceptance:** 14 dispatch
tests including 8 per-wrapper smoke + 1 allowlist gating + 1
BLOCK propagation + 4 cross-wrapper acceptance variants
(closed-form 5-wrapper + MCMC stochastic 2-wrapper + INVERTED
1-wrapper + S2-redux 3-wrapper preserved subset). 8-wrapper
allowlist baseline + 3 invariant class coverage.

### 3.3 Banking-when-warranted recipe

Banking entry codified per Q-banking-categorical strict
classes:
- Architectural decisions surfaced during execution
- Dispatch infrastructure changes (allowlist mechanism;
  lifecycle method; field-availability protocol Cases
  enumeration)
- Allowlist mechanism amendments
- API-changing decisions

**Format (S1-A-1-c):** banking ID + title + category + content
+ forward-looking guidance + cross-references via (mit-ii)
brief mentions. Lives in
`docs/reference_parity_phase5/<scope>_banking.md` (standalone)
OR inline at findings doc per Q4 disposition.

**Worked example — S2-α-2-redux lifecycle method extension:**
`check_invariants(tsl, ref=None, fixture=None)` multi-side
signature surfaced as architectural decision during execution
(VECM cointegrating rank requires both tsl + ref). Banked per
Q-banking-categorical strict per API-changing class with
forward-looking guidance for future multi-side invariants.
