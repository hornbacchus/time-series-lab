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
