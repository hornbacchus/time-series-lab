# Reference-Parity Harness — Contributor Guide

Phase 2 of the retrospective correctness verification initiative.
This guide explains how to add a new parity check to the harness,
how to interpret outcomes, and the maintenance cadence the
harness depends on.

## Architecture

Code lives under `tools/reference_parity/harness/`:

| File | Role |
|---|---|
| `MANIFEST.toml` | Pinned R + Python reference versions; quarterly review cadence |
| `manifest.py` | TOML loader |
| `base.py` | `ParityCheck` ABC + `ParityResult` dataclass + outcome aggregator |
| `tolerances.py` | Centralised tolerance ladders, one entry per technique |
| `fixtures.py` | `FixtureLoader` with SHA-256 verification |
| `r_bridge.py` | Class-based R subprocess bridge driven by manifest |
| `runner.py` | CLI + check discovery + CAVEAT re-roll orchestration |
| `checks/` | Per-technique check modules (one `ParityCheck` subclass each) |

Phase 1 audit infrastructure (`fixtures/`, `reports/`,
`scripts/`) coexists in `tools/reference_parity/` but is
intentionally untracked. The Phase 2 harness consumes Phase 1's
fixtures (with newly-written `.sha256` sidecars).

## Adding a new parity check

### Step 1 — Generate the fixture

Use `FixtureLoader.write_with_sha`:

```python
from reference_parity.harness.fixtures import FixtureLoader
import numpy as np

loader = FixtureLoader()
data = {"y": np.random.default_rng(42).standard_normal(500)}
npz_path, sha_path, sha = loader.write_with_sha("my_technique", data)
print(f"wrote {npz_path}; sha={sha}")
```

This writes `tools/reference_parity/fixtures/my_technique.npz`
plus a `.sha256` sidecar. The runner will hash-verify the .npz
on every load.

### Step 2 — Register a tolerance ladder

Add an entry to `harness/tolerances.py`:

```python
"my_technique": {
    "type": "absolute",            # or "three_outcome", "correlation"
    "abs_tol": 1e-8,
    "rel_tol": 1e-8,
    "justification": (
        "Closed-form OLS regression. Phase 1 audit X "
        "(reports/X_my_audit.md) measured max abs diff 4e-15 "
        "vs reference; 1e-8 leaves 7 orders of magnitude of "
        "headroom for subprocess CSV roundtrip."
    ),
},
```

The `justification` field MUST cite the Phase 1 audit report
that established the empirical baseline. Adding a check without
this is a contributor-guide violation.

### Step 3 — Implement the check class

Create `harness/checks/my_technique.py`:

```python
from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder
import numpy as np


class MyTechniqueParity(ParityCheck):
    technique_id = "my_technique"     # matches tolerances + fixture
    tier = "fast"                      # or "slow"
    fixture_id = "my_technique"        # stem of the .npz file

    def setup_fixture(self, seed):
        # Runner already loaded + hash-verified the on-disk
        # fixture; merge any runtime-generated data here.
        return {}

    def run_tsl(self, fixture):
        # Invoke the TSL wrapper; return canonical numeric outputs.
        ...
        return {"y_hat": y_hat}

    def run_reference(self, fixture):
        # Invoke the external reference (R via RBridge or Python via import).
        manifest = Manifest.load()
        bridge = RBridge(manifest)
        outputs, versions = bridge.rscript_call(
            r_code=r"...",
            inputs={"y": fixture["y"]},
            output_names=["y_hat"],
            capture_versions_for=["forecast"],
        )
        return {"y_hat": outputs["y_hat"], "versions": versions}

    def compare(self, tsl, ref):
        ladder = get_ladder(self.technique_id)
        diff = float(np.max(np.abs(tsl["y_hat"] - ref["y_hat"])))
        ok = diff <= ladder["abs_tol"]
        return ParityResult(
            technique_id=self.technique_id,
            outcome="PASS" if ok else "BLOCK",
            metrics={"max_abs_diff": diff},
        )
```

The runner discovers your class automatically — no registration
boilerplate.

### Step 4 — Run locally

```
python -m reference_parity --technique my_technique
python -m reference_parity --tier fast --json
```

### Step 5 — Add a unit test (optional but encouraged)

Add a unit test to `engine/tests/test_harness.py` that
mock-patches the R bridge and asserts your `compare()` method
produces the expected outcome on a synthetic input.

## Outcome interpretation

| Outcome | Meaning | Exit code |
|---|---|---|
| **PASS** | Within tolerance ladder | 0 |
| **SKIP** | Reference unavailable (R missing, package missing, Python import failed) | 0 |
| **CAVEAT** | First-run breach of a band threshold; runner auto-reruns once with `seed+1`. PASS-on-retry promotes to PASS | 2 (only if escalates) |
| **BLOCK** | Exceeded tolerance, OR CAVEAT-on-retry. Commit blocked pending investigation | 1 |
| **ERROR** | Unexpected exception (fixture missing, bug in check code, etc.) | 3 |

The runner aggregates outcomes across all checks: BLOCK > ERROR
> CAVEAT > SKIP > PASS. The aggregated outcome determines the
overall exit code.

## Manifest refresh cadence

`MANIFEST.toml` is reviewed **quarterly**. The
`refresh.last_review` and `refresh.next_review` fields drive an
automatic stale-detection in `Manifest.is_stale()`. When the
next-review date passes:

1. Run `python -m reference_parity --check-environment` to see
   which packages have drifted.
2. Decide: bump pins to current installed versions, OR pin the
   environment back to manifest values.
3. Update `last_review` to today; advance `next_review` by 90
   days.
4. Re-run the full fast tier; investigate any new CAVEAT/BLOCK
   outcomes (a package update may have changed numerical output
   within tolerance band).

## Fixture-hash-mismatch handling

If you see `FixtureHashMismatchError`, the on-disk `.npz` no
longer matches the `.sha256` sidecar. Options:

1. **Intentional regeneration**: re-run your fixture generator,
   then call `FixtureLoader.write_with_sha` to rewrite both
   files. Commit both together.
2. **Accidental modification**: revert the `.npz` from git
   history. The `.sha256` was correct.
3. **Legitimate refresh**: bump fixture seed / parameters in the
   generator, write_with_sha, and update the check's tolerance
   if the new fixture exposes a different parity profile.

Never edit the `.sha256` file by hand — it must be the SHA of
the committed `.npz`.

## R installation requirement

The harness's R-side checks require:

- R 4.5.x installed (path pinned in `MANIFEST.toml` `r.rscript_exe`)
- User library at the path pinned in `MANIFEST.toml` `r.libs_user`
- The R packages listed in `MANIFEST.toml` `[r.packages]`

When R is unavailable, R-dependent checks return SKIP rather
than ERROR. Python-only checks (e.g., the smoke test if it were
re-implemented as numpy-only) continue to run.

CI-side, the `parity-fast` workflow installs only the fast-tier
R packages (~3 packages); the `parity-slow` workflow installs
the full manifest set (~15 packages).

## Troubleshooting

- **All R-dependent checks return SKIP**: run
  `python -m reference_parity --check-environment` to see
  whether R or specific packages are missing.
- **A check returns ERROR with `Fixture file missing`**:
  generate the fixture per Step 1 above; the `.npz` is not
  committed yet.
- **A check reports `nan_present` on `mint_sample`**: this is
  expected on perfectly-coherent hierarchies (Phase 1 B1). The
  harness reports it as PASS with `status: nan_present`
  diagnostic, not as a failure.

## Fixture authoring discipline

When porting a parity test from a Phase 1 audit script, generate
fixtures by replicating the audit's exact generator code, not by
re-deriving from related canonical helpers. During Phase 2 Session 1,
the 3e fixture was initially built from the canonicals'
`_synth_2level` helper (constant `phi=0.5`) rather than the Phase 1
audit's pattern (per-series `phis = [0.3, 0.5, 0.7, 0.85]`, top =
exact sum of bottoms with `noise_on_top=False`). The mismatch
surfaced as 0.028 `mint_shrinkage` divergence vs Phase 1's
`4.66e-15` baseline. Re-deriving with the audit's exact pattern
restored machine precision. When in doubt, copy the audit's
generator function verbatim into the parity check rather than
calling a similar helper.
