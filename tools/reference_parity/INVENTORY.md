# TSL Reference Parity — Infrastructure Inventory (Phase 3 Session 1)

**Date:** 2026-04-28
**Author:** Phase 3 Session 1 (auto mode, post-handoff bootstrap)
**Status:** Authoritative for Phase 3 execution. Drives Sessions 2–4 (Batch 1 manual templates) and Session 5 (generator abstraction).

This document enumerates the as-built infrastructure under `tools/reference_parity/` and reconciles the Phase 3 master plan's "~71 wrappers" estimate against the actual `engine/techniques/*.py` inventory minus the 12 wrappers already covered by the prior Verification Initiative. It also locks the in-scope wrapper list per batch and the R/Python package version pins for Phase 3 expansion.

---

## 1. Actual file inventory under `tools/reference_parity/`

### 1.1 Top-level layout

```
tools/reference_parity/
├── __init__.py                    # public docstring; module re-export point (no symbols)
├── __main__.py                    # `python -m reference_parity` entrypoint → harness.runner.main
├── INVENTORY.md                   # this document
├── fixtures/                      # 18 fixtures + 12 sha256 sidecars + _tmp/
├── harness/                       # Phase 2 durable harness (8 modules + checks/)
├── reports/                       # 12 per-audit reports + 1 retrospective synthesis + JSONL log
└── scripts/                       # Phase 1 legacy audit scripts (now deprecated; see §1.4)
```

### 1.2 `harness/` — Phase 2 durable parity infrastructure (~7,061 LOC)

| File | LOC | Role |
|---|---:|---|
| `harness/__init__.py` | 14 | Package marker |
| `harness/base.py` | 195 | `ParityCheck` ABC, `ParityResult` dataclass, `Outcome`/`Tier` Literals, `aggregate_outcomes` |
| `harness/runner.py` | 481 | CLI runner (`--tier {fast,slow}`, `--technique <id>`, `--check-environment`, `--seed`, `--json`); auto-discovery of `ParityCheck` subclasses; CAVEAT re-roll protocol with seed bumping |
| `harness/manifest.py` | 107 | TOML loader → typed `Manifest` dataclass; `is_stale()` enforces quarterly refresh cadence |
| `harness/r_bridge.py` | 583 | `RBridge` class — see §2 |
| `harness/fixtures.py` | 288 | `FixtureLoader` with SHA-256 verification + format dispatch (`.npz` / `.pt`); `_canonical_seed` metadata extraction (replaces per-check `SEED_OFFSET` workaround) |
| `harness/tolerances.py` | 667 | Centralized `TOLERANCE_LADDERS` dict with three ladder types: `absolute` / `three_outcome` / `correlation`; per-entry `justification` traces back to a Phase 1 audit report |
| `harness/MANIFEST.toml` | 112 | Pinned R + Python reference-package versions; `last_review=2026-04-25 / next_review=2026-07-25` |
| `harness/checks/` | 12 modules | One `ParityCheck` subclass per audited technique (see §1.3) |

The harness is the durable Phase 3 substrate. New parity audits land as new modules under `harness/checks/`; the runner auto-discovers them via subclass-walking on `ParityCheck`.

### 1.3 `harness/checks/` — 12 promoted Verification Initiative checks (+1 smoke probe)

| File | technique_id | tier | fixture_id | wrapper(s) covered |
|---|---|---|---|---|
| `_smoke.py` | `_smoke_test` | fast | (runtime-generated) | None — harness end-to-end probe (R `mean` vs numpy `mean`) |
| `bvar_irf_fevd.py` | `1c_bvar_irf_fevd` | fast | `1c_bvar` | `bvar.py` |
| `caviar_sav.py` | `3a_caviar_sav` | fast | `3a_caviar_sav` | `caviar_quantile_dynamics.py` |
| `critical_slowing_down.py` | `critical_slowing_down` | fast | `critical_slowing_down_saddle_node` | `critical_slowing_down.py` |
| `evt_ferro_segers.py` | `3c_evt_ferro_segers` | fast | `3c_evt_garch` (+ iid sibling) | `evt_pot_gpd.py` |
| `har_cj.py` | `3b_har_cj` | fast | `3b_har_cj` | `har_cj.py` |
| `johansen_bartlett.py` | `3d_johansen_bartlett` | fast | `3d_johansen` | `johansen_cointegration.py` |
| `kalman_filter.py` | `2a_kalman_filter_smoother` | fast | `2a_kalman_phase1` | `kalman_filter.py` + `kalman_smoother.py` |
| `mcmc_sv_gaussian.py` | `2b_mcmc_sv_gaussian` | slow | `2b_sv_gaussian` | `stochastic_volatility.py` (Gaussian path) |
| `mcmc_sv_student_t.py` | `2c_mcmc_sv_student_t` | slow | `2c_sv_student_t` | `stochastic_volatility.py` (Student-t path) |
| `mint_family.py` | `3e_mint_family` | fast | `3e_mint` | `forecast_reconciliation.py` (all 4 methods: `ols`, `wls_variance`, `mint_shrinkage`, `mint_sample`) |
| `transformer_attention.py` | `3f_transformer_attention` | fast | `3f_transformer_attention` | `transformer_forecast.py` (attention-capture path only) |

**Distinct wrappers covered by harness checks:** 11 modules; 12 if `kalman_filter.py` and `kalman_smoother.py` are counted separately (the same check exercises both via the dual-path `MARSS::MARSS` reference). The handoff's "12 wrappers" estimate matches the latter convention.

**Tier discipline as-built:**
- Fast tier: 10 checks (closed-form, OLS, FFT-style, deterministic-MLE, attention-capture).
- Slow tier: 2 checks (`2b_mcmc_sv_gaussian`, `2c_mcmc_sv_student_t` — both ~5–10 minute MCMC runs).

### 1.4 `scripts/` — REMOVED at Phase 3.5 Session 1

**Phase 3.5 update (2026-04-29):** The 12 deprecated Phase 1 audit
scripts + `rscript_bridge.py` + `test_rscript_bridge.py` were
**removed** at Phase 3.5 Session 1 (Item 5 cleanup). Justification:

- Files were never tracked under git (Phase 1 plan discipline kept
  the entire `tools/reference_parity/` tree untracked at first;
  only the Phase 2/3 harness was promoted to git).
- All 12 audit scripts depended on `scripts/rscript_bridge.py`,
  which raised `ImportError` on import in Phase 2 — making the
  scripts non-functional.
- Phase 3 promoted all relevant audits to `harness/checks/p3_*.py`
  (per-wrapper) AND retained Phase 1 audit reports under
  `tools/reference_parity/reports/<phase1_id>_audit.md` as
  historical record.
- Cross-references in `harness/tolerances.py` `justification`
  fields cite the Phase 1 audit IDs (e.g., `1c_bvar_irf_fevd`)
  not file paths — unaffected by the deletion.

**Historical record (for archaeological reference):** the 12
audit scripts were:

```
audit_1a_regression.py        audit_2c_student_t_sv.py   audit_3d_johansen.py
audit_1b_tbats.py             audit_3a_caviar.py         audit_3e_mint.py
audit_1c_bvar_irf.py          audit_3b_har_cj.py         audit_3f_attention.py
audit_2a_kalman.py            audit_3c_ferro_segers.py
audit_2b_mcmc_sv.py
rscript_bridge.py  ← function-based prototype superseded by harness/r_bridge.py:RBridge
test_rscript_bridge.py
```

The per-audit reports under `reports/<phase1_id>_audit.md` remain
in place as the durable Phase 1 record. They are NOT under git
but are preserved in local checkouts.

### 1.5 `fixtures/` — 18 fixture files + sidecars

| Pattern | Count | Format |
|---|---:|---|
| `<phase1_id>_fixture.npz` (Phase 1 audit-script bound) | 9 | `.npz`, no sidecar; loaded by deprecated `scripts/audit_*.py` |
| `<harness_id>.npz` + `.sha256` (harness-bound) | 8 | `.npz` + sidecar containing 64-char hex digest, single-line, trailing newline |
| `2a_kalman_phase1.npz` + sidecar | 1 | Reused from Phase 1 by harness check |
| `3f_transformer_attention.pt` + `.sha256` | 1 | `.pt` (torch.save dict); loaded via `FixtureLoader._load_pt` |
| `critical_slowing_down_saddle_node.npz` + sidecar | 1 | Added in Phase 2 cleanup post-CSD audit |
| `_tmp/` | — | RBridge tempfile root (auto-managed; gitignored) |

**SHA-256 pin format example** (`fixtures/3e_mint.sha256`):
```
8cad91e4387f67b9e14f3db5428129ee1765f4c14cb6b860fbdeda602d7d7bbe
```
Single-line, hex digest, trailing newline. Written by `FixtureLoader.write_with_sha()`; verified by `FixtureLoader.load()` before any check runs.

**Phase 3 convention** (per master plan §16.4): new fixtures land at `fixtures/p3_dgp_<wrapper>.npz` with a sibling `.sha256`. Existing reusable fixtures (e.g., the 5-series macro pack) are **referenced by id, not duplicated**.

### 1.6 `reports/` — 13 audit reports + 1 JSONL log

Per-audit `*.md` reports for the 12 Verification Initiative audits, plus `retrospective_audit_2026_04_25_FINAL.md` synthesizing across them. `_rscript_call_log.jsonl` is the rolling per-call audit trail emitted by `RBridge._log_call`.

**Phase 3 convention** (per master plan §16.3): new reports land at `reports/p3_<wrapper>_audit.md` (per-wrapper) and `reports/p3_batch_<N>_summary.md` (per-batch).

---

## 2. `r_bridge.py` status

### 2.1 Status: **IMPLEMENTED** (as `harness/r_bridge.py`, 583 LOC)

The Phase 1 prototype (`scripts/rscript_bridge.py`, function-based) was promoted to a class-based, manifest-driven `RBridge` in `harness/r_bridge.py` during Phase 2 Session 1. The Phase 1 module is **deprecated and now raises `ImportError`** on import.

**API surface (public):**

```python
class RBridge:
    def __init__(
        self,
        manifest: Manifest,
        *,
        log_path: pathlib.Path | None = None,
        tmp_dir: pathlib.Path | None = None,
    ) -> None: ...

    def check_environment(self) -> dict[str, Any]:
        """Returns r_version, r_packages_installed, r_packages_divergences vs manifest."""

    def rscript_call(
        self,
        r_code: str,
        inputs: Mapping[str, np.ndarray] | None = None,
        output_names: Sequence[str] = (),
        *,
        keep_tempfiles: bool = False,
        timeout_sec: int = 120,
        capture_versions_for: Sequence[str] = (),
    ) -> tuple[dict[str, np.ndarray], dict[str, str]]:
        """Returns (outputs, version_metadata)."""
```

**Exception hierarchy:**
- `RBridgeError` (base, `RuntimeError` subclass with `stdout`/`stderr`/`returncode`/`tempfile_paths`/`r_code` attrs)
  - `RNotAvailableError` — Rscript not found → runner translates to `SKIP`
  - `RPackageMissingError` — package missing from `libs_user` → runner translates to `SKIP`
  - `RSubprocessTimeoutError` — `subprocess.TimeoutExpired` mapped
  - `RScriptExecutionError` — non-zero R exit code

**Carry-forward features from Phase 1:**
- numpy ↔ R CSV roundtrip via `np.savetxt(fmt='%.18e')` (full double precision)
- `{{INPUT_<name>}}` / `{{OUTPUT_<name>}}` placeholder syntax in R code
- `.libPaths` prolog injection (now conditional on manifest's `libs_user` existing — falls back to runner-supplied `R_LIBS_USER` on CI)
- Phase 1 B2 fix preserved: `_count_header_rows` consumes post-substitution text (where R "NA" tokens have already become "nan") so all-NA first rows aren't mis-classified as headers
- Per-call JSONL audit log → `reports/_rscript_call_log.jsonl`

**Phase 2 promotion features:**
- Manifest-driven `rscript_exe` and `libs_user` resolution
- `check_environment()` for `--check-environment` CLI subcommand
- `capture_versions_for=` parameter snapshots referenced R package versions into the result tuple's `version_metadata` dict
- `_resolve_libs_user()` warns once per instance when manifest path doesn't exist (CI-friendly)

### 2.2 Call sites (10 harness checks)

All non-Python references go through `RBridge.rscript_call`:

```
harness/checks/_smoke.py                  : R base mean
harness/checks/bvar_irf_fevd.py           : R vars::irf, vars::fevd
harness/checks/caviar_sav.py              : R quantreg-driven from-scratch reimpl
harness/checks/critical_slowing_down.py   : (Python ewstools, NOT R-based)
harness/checks/evt_ferro_segers.py        : R extRemes::extremalindex
harness/checks/har_cj.py                  : R HARModel (when installed) — currently script-fallback
harness/checks/johansen_bartlett.py       : R urca::ca.jo
harness/checks/kalman_filter.py           : R dlm::dlmFilter + KFAS::KFS
harness/checks/mcmc_sv_gaussian.py        : R stochvol::svsample
harness/checks/mcmc_sv_student_t.py       : R stochvol::svtsample
harness/checks/mint_family.py             : R hts::MinT (with HF Python cross-check)
harness/checks/transformer_attention.py   : (PyTorch native, NOT R-based)
```

### 2.3 Recommendation: **EXTEND, do not replace**

For Session 5 generator abstraction:
- Keep `RBridge` as the R subprocess primitive. It's well-engineered (manifest-driven, exception hierarchy mapped to runner outcomes, audit-trail logged, CI-aware libs_user fallback).
- Build a parallel `PyBridge` utility in Session 5 for Python-import references (Batches 7–9). Symmetry with `RBridge` keeps the harness mental model uniform.
- Generator's per-wrapper config (`tools/reference_parity/configs/p3_<wrapper>.toml` per master plan §16.5) declares `reference_kind: r | py` and dispatches to the right bridge.

**No refactoring of `RBridge` is needed before Session 5.** Existing call sites already follow the harness contract.

---

## 3. CI workflows

### 3.1 `parity-fast.yml` — content + structure

Triggers: `pull_request` + `push` to `master`. Runs on `windows-latest`, `timeout-minutes: 10`.

Step-by-step:
1. `actions/checkout@v4`
2. `actions/setup-python@v5` with `python-version: "3.14"`
3. `pip install`: `numpy scipy pandas hierarchicalforecast statsmodels torch==2.11.0 ewstools==2.1.2`
4. `r-lib/actions/setup-r@v2` with `r-version: "4.5.3"`
5. `Rscript install.packages(c("hts", "forecast", "vars", "urca", "extRemes", "dlm", "KFAS"), repos="https://cloud.r-project.org")` — fast-tier subset (7 R packages)
6. `python -m reference_parity --tier fast --json > parity-fast.json` (with `set +e` + manual exit-code capture so JSON is visible in logs on failure; `PYTHONPATH: ${{ github.workspace }}/tools`)
7. `actions/upload-artifact@v4` for `parity-fast.json` (always)

**Runtime per audit (observed from JSONL log + tier discipline):** typically 2–15s per check on local Windows; CI runtime 5–30s per check. Fast tier total budget: ≤10 minutes for all 10 fast-tier checks. Currently well within budget.

### 3.2 `parity-slow.yml` — content + structure

Triggers: nightly cron `0 6 * * *` UTC + push to tags `v*` + `workflow_dispatch`. Runs on `windows-latest`, `timeout-minutes: 30`.

Step-by-step (mirrors fast tier structure):
1. checkout / setup-python / setup-r
2. `pip install`: `numpy scipy pandas hierarchicalforecast pyextremes tbats arch pmdarima statsmodels pymc arviz` (broader than fast; pymc + arviz for slow-tier MCMC)
3. `Rscript install.packages` for full 15-package R manifest: `hts stochvol urca extRemes forecast vars tseries fable fabletools evir POT rugarch dlm KFAS quantreg`
4. `python -m reference_parity --tier slow --json > parity-slow.json`
5. Upload artifact

**Runtime per audit:** MCMC checks 5–10 min each; other slow-tier candidates not yet active. Total budget: ≤30 minutes.

### 3.3 Phase 3 expansion path

Both workflows already exist and are healthy. Phase 3 expansion via:
- **Per-batch Python deps:** as new Python references land (Batches 7–9), append to the corresponding `pip install` step. Prefer adding to slow tier first; promote to fast after measured runtime supports.
- **Per-batch R deps:** as new R references land (Batches 1–6), append to the corresponding `install.packages` call. Same fast/slow split discipline.
- **Tier reassignment:** new check modules set `tier = "fast"` or `tier = "slow"` directly on the `ParityCheck` subclass; the runner picks them up via `discover_checks` automatically. No workflow changes needed beyond adding the package install line.
- **Manifest sync:** when a workflow installs a package, mirror the version pin into `harness/MANIFEST.toml`. Quarterly review (per `refresh.next_review`) reconciles any drift.

**Recommendation:** keep two workflow files (don't merge). The fast tier's PR-blocking semantics depend on its runtime budget; consolidating into one nightly + on-demand workflow would lose the per-PR CI gate on the closed-form / cheap-MLE tier.

---

## 4. R package install pattern + version pins

### 4.1 As-built install pattern (per `parity-slow.yml`)

```r
install.packages(
  c("<pkg1>", "<pkg2>", ...),
  repos = "https://cloud.r-project.org"
)
```

No explicit version pinning at the install step; CRAN serves whatever is current. Version reconciliation happens at runtime via `RBridge.check_environment()` → compares installed version to `harness/MANIFEST.toml` pinned values; surfaces divergences in the `--check-environment` JSON output.

This pattern is cheap to extend (append new package names per batch) and self-healing on fresh CI runners (always picks up latest CRAN). The downside — silent version drift between local dev and CI — is mitigated by the manifest's `last_review`/`next_review` cadence and the runtime divergence report.

### 4.2 Existing pin format (`harness/MANIFEST.toml`)

TOML with three top-level sections: `[refresh]` (cadence + notes), `[r]` (version + rscript_exe + libs_user + `[r.packages]` table), `[python]` (version + `[python.packages]` table). Manifest is loaded by `harness/manifest.py` (Python 3.11+ stdlib `tomllib`).

Snapshot of currently-pinned versions (verified installed locally; same set as what CI installs):

**R 4.5.3** + 15 packages: `hts=6.0.3`, `stochvol=3.2.9`, `urca=1.3.4`, `extRemes=2.2.1`, `forecast=9.0.2`, `vars=1.6.1`, `tseries=0.10.61`, `fable=0.5.0`, `fabletools=0.6.1`, `evir=1.7.4`, `POT=1.1.11`, `rugarch=1.5.5`, `dlm=1.1.6.1`, `KFAS=1.6.0`, `quantreg=6.1`.

**Python 3.14** + 11 packages: `hierarchicalforecast=1.5.1`, `pyextremes=2.5.0`, `tbats=1.1.3`, `arch=8.0.0`, `pmdarima=2.1.1`, `statsmodels=0.14.6`, `pymc=5.28.4`, `arviz=0.23.4`, `torch=2.11.0+cpu`, `ewstools=2.1.2`. (Plus `numpy`, `scipy`, `pandas` not pinned — assumed stable on Python 3.14.)

### 4.3 Recommendation: **CONSOLIDATE — single MANIFEST.toml**

The master plan's Appendix B references `tools/reference_parity/manifests/r_packages_p3.txt` and `py_packages_p3.txt` as separate plain-text manifests. **Do not create those.** The existing `harness/MANIFEST.toml` already serves the same purpose with strictly better ergonomics:

- **Single source of truth** for both R + Python versions (vs two parallel files).
- **Typed loader** (`harness/manifest.py`) with cadence enforcement (`is_stale()`).
- **Runtime divergence report** via `--check-environment`.
- **CI-aware** via `_resolve_libs_user()` fallback.

Phase 3 expansion appends new entries to `[r.packages]` and `[python.packages]` in-place. The next quarterly review (2026-07-25) re-pins everything in one pass.

The master plan's Appendix B should be revised to point to `harness/MANIFEST.toml` as the manifest, NOT to non-existent `manifests/*.txt` files. (Done in this session — see §6 below.)

---

## 5. Existing fixture SHA256 pin format + audit script structural pattern

### 5.1 Fixture pin format

See §1.5. `<id>.sha256` is a single-line hex digest with trailing newline; `<id>.npz` (or `.pt`) is the canonical binary; loaded + verified via `FixtureLoader.load(id)`. Phase 3 fixtures follow the same pattern with the `p3_dgp_<wrapper>` prefix.

### 5.2 Audit script structural pattern (target template source for Sessions 2–4)

The 12 deprecated `scripts/audit_*.py` scripts are **NOT** the right template — they predate the harness API and import the deprecated `rscript_bridge`. Instead, the **Session 2 manual templates derive from `harness/checks/*.py`**, which embody the durable contract.

**Reference template structure** (e.g., `harness/checks/mint_family.py`):

```python
class WrapperParity(ParityCheck):
    technique_id = "p3_<wrapper>"          # Stable id; matches --technique CLI flag
    tier = "fast"                          # or "slow" per Section 12 master plan
    fixture_id = "p3_dgp_<wrapper>"        # FixtureLoader id (no extension)

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # Either reads from disk via FixtureLoader OR generates from seed.
        ...

    def run_tsl(self, fixture: dict) -> dict:
        # Invoke TSL wrapper; extract Primary + Secondary outputs per master plan §4.
        ...

    def run_reference(self, fixture: dict) -> dict:
        # Invoke R reference via RBridge.rscript_call OR Python reference via direct import.
        # May raise RNotAvailableError / RPackageMissingError / ImportError → runner SKIPs.
        ...

    def compare(self, tsl: dict, ref: dict) -> ParityResult:
        # Apply tolerance ladder from harness/tolerances.py via get_ladder(self.technique_id).
        # Return partially-populated ParityResult; runner fills duration/seed/sha/versions.
        ...
```

**Per-wrapper sizing** (observed from existing 11 checks): 337–509 LOC, median ~400. Most LOC sits in `setup_fixture` (DGP code) and `compare` (per-output ladder application). `run_tsl` and `run_reference` are typically 30–80 LOC each.

**Tolerance ladder addition:** each new check adds an entry to `harness/tolerances.py` `TOLERANCE_LADDERS` with `type` + thresholds + `justification` field tying to the per-audit report.

**Session 5 generator scope** abstracts the ~80% of structure that's identical across checks (fixture load → TSL invoke → reference invoke → tolerance application → result emission), leaving the ~20% per-check variation (DGP, R code, output mapping) in `configs/p3_<wrapper>.toml`.

---

## 6. Concrete delta: `~71 wrappers` reconciled

### 6.1 Total wrapper count

`engine/techniques/*.py` minus `_*.py` / `test_*.py` / `registry.py` / `base.py`:
**81 wrapper modules.**

### 6.2 Already covered by Verification Initiative (12 wrappers)

| Wrapper module | Audit ID | Harness check |
|---|---|---|
| `bvar.py` | 1c | `bvar_irf_fevd.py` |
| `caviar_quantile_dynamics.py` | 3a | `caviar_sav.py` |
| `critical_slowing_down.py` | (Phase 2 cleanup) | `critical_slowing_down.py` |
| `evt_pot_gpd.py` | 3c | `evt_ferro_segers.py` |
| `forecast_reconciliation.py` | 3e | `mint_family.py` (covers all 4 methods: ols, wls_variance, mint_shrinkage, mint_sample) |
| `har_cj.py` | 3b | `har_cj.py` |
| `johansen_cointegration.py` | 3d | `johansen_bartlett.py` |
| `kalman_filter.py` | 2a | `kalman_filter.py` (joint with kalman_smoother) |
| `kalman_smoother.py` | 2a | `kalman_filter.py` (joint check) |
| `stochastic_volatility.py` | 2b + 2c | `mcmc_sv_gaussian.py` + `mcmc_sv_student_t.py` |
| `tbats_forecast.py` | 1b | (audit-script only; NOT yet in harness — see note below) |
| `transformer_forecast.py` | 3f | `transformer_attention.py` |

**Note on tbats_forecast.py:** the Phase 1 audit-script (`scripts/audit_1b_tbats.py`) ran against the now-deprecated bridge; the tolerance ladder + report were produced, but no harness/check has been authored. **Phase 3 Batch 1 should treat tbats_forecast.py as IN SCOPE for harness promotion** (write `harness/checks/tbats_forecast.py` from scratch using the existing audit-script's tolerance findings as the reference baseline). Not a new audit — a promotion of existing work into the durable harness.

**Note on 1a regression audit:** the `audit_1a_regression.py` script was a non-parity regression sweep covering bug-fix verification on 5 DL wrappers (TCN, LSTM/GRU, NBEATS, NHits, Transformer). It does **not** establish parity for any wrapper. Those 5 wrappers' parity is uncovered (Transformer's *attention capture* is covered by 3f; the *forecast output* of Transformer is not). Phase 3 Batch 9 covers all 5.

### 6.3 In-scope for Phase 3 (69 wrappers)

`81 − 12 = 69` wrappers. Plus tbats_forecast.py harness promotion brings it to **70 audit deliverables across 10 batches**. (The handoff's "~71" was within the ±3 uncertainty bound the master plan §17.1 risk #5 acknowledged.)

Final per-batch assignment (revised from master plan Appendix A based on actual filesystem inventory):

| Batch | Theme | Wrappers | Count |
|---|---|---|---:|
| 1 | R `forecast` family | `arima.py`, `arimax_sarimax.py`, `sarima.py`, `ets_hw.py`, `theta_forecast.py`, `intermittent_demand.py`, `mstl_decompose.py`, `classical_decompose.py`, `stl_decompose.py`, `tbats_forecast.py` (harness promotion) | 10 |
| 2 | R volatility | `garch_model.py` (single wrapper, 4 variants via `vol` param: GARCH/GJR-GARCH/EGARCH/IGARCH), `har_rv.py` | 2 |
| 3 | R multivariate | `var_model.py`, `vecm_model.py`, `dynamic_factor_model.py`, `pca_analysis.py` | 4 |
| 4 | R Markov / nonlinear | `hmm_model.py`, `markov_switching.py`, `tar_setar.py`, `star_model.py`, `nar_narx.py` | 5 |
| 5 | R state space | `local_level.py`, `local_linear_trend.py`, `structural_ts.py`, `particle_filter.py`, `kalman_imputation.py` | 5 |
| 6 | R change-points / stationarity | `adf_test.py`, `kpss_test.py`, `pp_test.py`, `bocpd.py`, `cusum_page_hinkley.py`, `intervention_analysis.py`, `pelt_change_points.py`, `stl_esd_anomaly.py`, `x13_seasonal_adjust.py` | 9 |
| 7 | Python spectral | `fft_spectrum.py`, `periodogram_spectral_density.py`, `lomb_scargle.py`, `wavelet_transform.py`, `wavelet_coherence.py` (Tier B), `emd_hht.py`, `ssa_model.py` | 7 |
| 8 | Python ML | `random_forest_forecast.py`, `gradient_boosting_forecast.py`, `xgboost_forecast.py`, `lightgbm_forecast.py`, `svr_forecast.py`, `quantile_regression_model.py`, `robust_estimators.py` | 7 |
| 9 | Python DL | `lstm_gru_forecast.py` (single wrapper, 2 variants), `tcn_forecast.py`, `nbeats_forecast.py`, `nhits_forecast.py`, `autoencoder_anomaly.py`, `echo_state_network.py`, `gaussian_process_forecast.py`, `prophet_forecast.py`, `conformal_intervals.py` | 9 |
| 10 | Misc + Tier C | `granger_causality.py`, `cross_correlation_lag.py`, `prewhitened_ccf_lag.py`, `rolling_ccf_lag.py`, `gcc_phat_delay.py`, `dtw_alignment_lag.py`, `transfer_function.py`, `block_bootstrap.py`, `forecast_combination.py`, `rolling_origin_cv.py`, `denton_chowlin_disaggregation.py`, `loess_interpolation.py` | 12 |

**Total in-scope:** **70 audit deliverables** (69 unaudited wrappers + 1 harness promotion of tbats_forecast.py).

### 6.4 Adjustments from master plan Appendix A (initial draft)

| Original master plan claim | Reality from filesystem | Correction applied |
|---|---|---|
| Batch 1 ~9 wrappers | 10 (adds `stl_decompose.py` + `tbats_forecast.py`) | +1 |
| Batch 2 ~6 wrappers (sgarch, gjr_garch, egarch, igarch as 4 separate) | 1 wrapper (`garch_model.py`) covers all 4 variants via `vol` param dispatch (CAI Session 6 finding) | −4 |
| Batch 3 ~6 wrappers including `forecast_reconciliation_ols_wls` | 4 (forecast_reconciliation already fully covered by 3e MinT family check; OLS/WLS not a separate audit) | −2 |
| Batch 4 ~7 wrappers including critical_slowing_down | 5 (CSD already covered in harness; no `tar_setar` + `star` doublecount) | −2 |
| Batch 5 ~4 wrappers | 5 (kalman_imputation moved here from Batch 10 — same KFAS reference as 2a) | +1 |
| Batch 6 ~8 wrappers | 9 (adds `x13_seasonal_adjust.py` — uses R `seasonal`) | +1 |
| Batch 9 ~10 wrappers (lstm + gru as 2 separate) | 9 (`lstm_gru_forecast.py` is one wrapper) | −1 |
| Batch 10 ~7-11 wrappers | 12 (CCF family expanded to 3 distinct wrappers; kalman_imputation moved to Batch 5; loess kept here) | net consolidation |

Net master plan revisions: see §7 below for in-place edits to Appendices A and B.

---

## 7. Master plan revisions applied this session

Per session prompt, Appendices A and B of `plans/reference_parity_phase3_master_plan.md` were revised in place:

- **Appendix A:** all "wrapper-name placeholder" entries replaced with actual filenames. Per-batch assignment finalized per §6.3 above. Total adjusted from "~71" to **70** in-scope audit deliverables.
- **Appendix B:** "(Session 1 to confirm latest stable)" placeholders replaced with concrete versions where the package is installed locally; remaining packages flagged as `(install at Batch <N> start)` with rationale. Manifest path updated to point to `tools/reference_parity/harness/MANIFEST.toml` (single source of truth) instead of the non-existent `tools/reference_parity/manifests/r_packages_p3.txt` + `py_packages_p3.txt`.

---

## 8. Open items surfaced this session (none blocking)

1. **HARModel R package install path** — `parity-slow.yml` does not include `HARModel` because the existing `har_cj.py` harness check uses a from-scratch reimplementation (the package is non-trivial to install on Windows CI runners without RTools). Phase 3 Batch 2's `har_rv.py` audit will face the same constraint; plan ahead by referencing the existing `har_cj.py` reimpl pattern. Logged here, not escalated.
2. **`pomp` (particle filter reference)** — also non-trivial to install on Windows without RTools. Batch 5's `particle_filter.py` audit may need a Python `particles` reference instead, OR a from-scratch reimplementation per the Engle-Manganelli pattern. Decide at Batch 5 start.
3. **`scripts/` cleanup** — 12 deprecated audit scripts + `rscript_bridge.py` could be deleted, but the deletion would break references in some `harness/tolerances.py` `justification` fields. Defer to Phase 3 closeout (Session 27) as a one-line cleanup commit.
4. **`hierarchicalforecast` Python pin drift** — manifest pins `1.5.1`; Phase 3 Batch 3 reuses for cross-checks. Quarterly re-pin (`refresh.next_review = 2026-07-25`) will refresh.

---

**End of inventory.** Sessions 2–4 (Batch 1) execute against this document + master plan §15.2 directly.
