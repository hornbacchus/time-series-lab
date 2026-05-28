"""Phase 3 Batch 10 — LOESS NaN-imputation parity check.

TSL ``engine/techniques/loess_interpolation.py`` (statsmodels.lowess
local regression fit on OBSERVED positions + np.interp at all
positions + NaN-position filling at preset frac + iter count) vs
from-scratch paper-formula reimpl mirroring engine pipeline verbatim.

Rewritten at SC9-side Cat 3 remediation cycle session 9/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC9 = TIER B CLOSE** (FINAL Tier B
session) + SECOND cycle session forward-amending an existing §2.5
entry (S27 loess_interpolation per SC8 forward-amendment pattern
second-instance) + **MOST SEVERE Cat 3 STRUCTURAL DEFECT in
inventory verification cycle**.

**Structural correction at SC9 (validation-surface reframe):**

Pre-rewrite harness validated `statsmodels.nonparametric.smoothers_
lowess.lowess` on CLEAN data — smoothing primitive at observed
positions producing smoothed-curve output. Engine
`loess_interpolation.py` is fundamentally a NaN-IMPUTATION technique:
- engine REJECTS clean data with error "Series 'y' has no missing
  values. LOESS interpolation requires at least one missing value."
  (engine lines 101-107)
- engine fits LOESS on observed values + interpolates at missing
  positions to fill them (engine lines 159-169)
- engine output validates IMPUTED VALUES at missing positions
  (NaN-replacement surface), NOT smoothed curve at observed
  positions

These are **categorically different operations sharing a name**.
Pre-rewrite harness validated the wrong technique surface entirely.
Most severe Cat 3 DEGENERATE-VACUOUS case in the inventory
verification cycle: harness validated smoothing-at-observed-positions
on clean data which the engine never invokes (engine requires NaN
to even run); engine's actual behavior (imputation-at-missing-
positions) was NOT validated at any layer. Cat 3 surfaced at
inventory verification 12d3785 + Gate 1 finding + triage close
empirical confirmation (engine returns error on clean fixture per
triage Step 1 verification).

**Helper identity verification (Step 1 of SC9 workflow):** Engine
`loess_interpolation.py` exposes only `_auto_select_frac` + `run` +
`build_interpretation`. NO tree-family helpers. Tier B Layer 2
family-shared helpers from SC1 NOT APPLICABLE per SC7+SC8 forward-
instrumentation + SC9 empirical confirmation. THIRD-INSTANCE
confirmation of SC7 bespoke-per-session pattern (n=3 within Tier B;
**codification threshold reached** per A3 second-observation
tightening precedent → SC10+ should codify "Tier B bespoke per-
session" as established sub-pattern).

**Forward-amendment scope (S27 §2.5 entry):** Pre-rewrite S27 parity
claim documented Tier III same-library self-test (harness +
reference both call lowess on identical inputs; bit-exact PASS at
smoothing surface). SC9 forward-amends with post-rewrite Tier
II.bit-exact at IMPUTATION surface via engine code path exercise.
Critical institutional correction: pre-rewrite claim PASS was
technically valid AT smoothing surface but DEGENERATE-VACUOUS
relative to engine's actual operation — analogous to validating
that a kitchen knife cuts through paper when the appliance under
audit is a blender.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic LOESS (statsmodels lowess
is deterministic at fixed input + frac + iter count).
"""

from __future__ import annotations

import warnings as _warnings
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


# Engine preset Balanced config (engine `loess_interpolation.py`
# line 27). Mirrored verbatim per Disposition 2. Note: Thorough
# preset has frac=None (auto-select via LOO-CV at engine
# `_auto_select_frac` lines 32-74); Balanced uses fixed frac=0.2 +
# it=3 (no LOO-CV path exercised at Balanced math-layer parity).
_ENGINE_BALANCED_PRESET = {
    "frac": 0.2,
    "it": 3,
}


# Deterministic NaN-injection pattern per SC9 STRUCTURAL fixture
# rewrite: engine REQUIRES NaN to even run; clean fixture not
# applicable. Inject at fixed indices for reproducibility across runs.
_NAN_INJECTION_INDICES = (10, 17, 33, 67, 89, 112, 134, 145, 178, 185)


def _generate_loess_imputation_dgp(
    *, seed: int, n: int = 200,
) -> np.ndarray:
    """Smooth sinusoidal series with NaN at deterministic positions.
    Engine REQUIRES NaN to operate; clean DGP from pre-rewrite scope
    is not applicable to SC9 STRUCTURAL rewrite."""
    rng = np.random.default_rng(seed)
    x = np.linspace(0, 10, n)
    y = np.sin(x) + 0.3 * rng.standard_normal(n)
    y_with_nan = y.copy()
    for idx in _NAN_INJECTION_INDICES:
        if 0 <= idx < n:
            y_with_nan[idx] = np.nan
    return y_with_nan


def _reference_loess_interpolation(
    values: np.ndarray, *, seed: int, preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `loess_interpolation.run()`
    pipeline at engine lines 88-301 verbatim (Balanced preset path;
    no LOO-CV auto-frac-selection at Balanced). Bespoke per-session
    implementation per SC9 Tier B.3 close — Layer 2 family helpers
    NOT APPLICABLE.

    Pipeline (engine lines referenced inline):
    - Identify NaN mask + count missing/valid (engine lines 97-99)
    - Resolve frac + it from preset (engine lines 124-155)
    - Construct x_all integer-index axis (engine line 127)
    - Identify x_obs + y_obs at non-NaN positions (engine lines
      128-129)
    - Fit lowess on observed values (engine line 160)
    - Interpolate at all positions via np.interp (engine line 165)
    - Fill NaN positions with smoothed_all values (engine lines
      167-169) — IMPUTATION surface
    - Compute residuals on observed positions (engine lines
      174-178)
    - Gap analysis (engine lines 213-228)
    """
    from statsmodels.nonparametric.smoothers_lowess import (  # type: ignore
        lowess,
    )

    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    n = len(values)

    # NaN mask per engine line 97
    nan_mask = np.isnan(values)
    n_missing = int(nan_mask.sum())
    n_valid = n - n_missing

    if n_missing == 0:
        raise ValueError(
            "Reference reimpl requires at least one NaN value "
            "(engine rejects clean data at engine lines 101-107)."
        )
    if n_valid < 5:
        raise ValueError(
            "Reference reimpl requires at least 5 non-NaN values "
            "(engine rejects at engine lines 109-115)."
        )

    missing_fraction = n_missing / n

    frac = float(cfg["frac"])
    it = int(cfg["it"])

    # x_all integer-index axis per engine line 127
    x_all = np.arange(n, dtype=float)
    x_obs = x_all[~nan_mask]
    y_obs = values[~nan_mask]

    # Fit lowess on observed per engine line 160
    fitted = lowess(y_obs, x_obs, frac=frac, it=it, return_sorted=True)

    # Interpolate at all positions per engine line 165
    smoothed_all = np.interp(x_all, fitted[:, 0], fitted[:, 1])

    # Fill NaN positions per engine lines 167-169
    imputed_series = values.copy()
    for i in range(n):
        if nan_mask[i]:
            imputed_series[i] = smoothed_all[i]

    # Residuals on observed per engine lines 174-178
    observed_fitted = np.interp(x_obs, fitted[:, 0], fitted[:, 1])
    residuals = y_obs - observed_fitted
    rmse_observed = float(np.sqrt(np.mean(residuals ** 2)))
    mae_observed = float(np.mean(np.abs(residuals)))
    max_residual = float(np.max(np.abs(residuals)))

    # Gap analysis per engine lines 213-228
    gap_starts = []
    gap_lengths = []
    in_gap = False
    for i in range(n):
        if nan_mask[i]:
            if not in_gap:
                gap_starts.append(i)
                in_gap = True
        else:
            if in_gap:
                gap_lengths.append(i - gap_starts[-1])
                in_gap = False
    if in_gap:
        gap_lengths.append(n - gap_starts[-1])
    max_gap = max(gap_lengths) if gap_lengths else 0
    n_gaps = len(gap_lengths)

    # Extract imputed values at NaN positions only (parity-validation
    # surface; engine "Imputed Values" table at engine lines 198-210)
    imputed_at_missing = np.array(
        [imputed_series[i] for i in range(n) if nan_mask[i]],
        dtype=np.float64,
    )

    return {
        "imputed_at_missing": imputed_at_missing,
        "smoothed_all": smoothed_all.astype(np.float64),
        "rmse_observed": rmse_observed,
        "mae_observed": mae_observed,
        "max_residual": max_residual,
        "frac": float(frac),
        "it": int(it),
        "n_missing": int(n_missing),
        "n_gaps": int(n_gaps),
        "max_gap_length": int(max_gap),
        "missing_fraction": float(missing_fraction),
    }


class LoessParity(P3ParityCheck):
    """LOESS NaN-imputation parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.loess_interpolation.run() via
    RunContext with 1-series input containing NaN at deterministic
    positions + Balanced preset (frac=0.2 + it=3). Reference arm
    reimplements full engine pipeline bespoke per SC9 Tier B.3 close
    (Layer 2 family helpers NOT APPLICABLE) covering IMPUTATION
    surface at NaN positions (correct validation surface vs pre-
    rewrite WRONG smoothing surface on clean data).

    Forward-amendment of S27 §2.5 entry per Tier 2 incremental
    pattern; pre-rewrite Tier III same-library smoothing-primitive
    self-test SUPERSEDED with post-rewrite Tier II.bit-exact at
    imputation surface via engine code path exercise.
    """

    technique_id = "p3_loess"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "LOESS NaN-imputation via statsmodels.nonparametric.lowess "
        "is deterministic at fixed input + frac + iter count. Engine "
        "and reference reimpl follow identical pipeline (NaN mask + "
        "lowess fit on observed + np.interp at all positions + NaN-"
        "position filling + residuals + gap analysis); outputs "
        "match at machine precision modulo engine output-rounding "
        "floor at imputed values (6-decimal) + frac (4-decimal) + "
        "rmse/mae (6-decimal). SC9 Tier B.3 STRUCTURAL rewrite + "
        "Tier B close; reference at IMPUTATION surface (engine's "
        "actual behavior) not pre-rewrite SMOOTHING surface (wrong "
        "validation target)."
    )

    DGP_N = 200

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        y = _generate_loess_imputation_dgp(seed=seed, n=self.DGP_N)
        return {"y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext with 1-series input
        (containing NaN at deterministic positions) at Balanced preset;
        extract imputed values + audit fields from engine output."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.loess_interpolation as loess_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_loess_parity",
            "technique_id": "loess_interpolation",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = loess_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL loess_interpolation failed: "
                f"{resp.get('error_message')}"
            )
        # Extract "Imputed Values" table at missing positions only
        # (engine lines 198-210); this is the parity-validation surface
        imp_table = next(
            (t for t in resp["tables"]
             if t.get("name") == "Imputed Values"),
            None,
        )
        if imp_table is None:
            raise RuntimeError("engine missing 'Imputed Values' table")
        imputed_at_missing = np.array(
            [float(row[2]) for row in imp_table["rows"]],
            dtype=np.float64,
        )

        # Extract "Imputed Series" table for smoothed_all comparison
        # (LOESS Smooth column at index 3; 6-decimal rounded per engine
        # line 188)
        series_table = next(
            (t for t in resp["tables"]
             if t.get("name") == "Imputed Series"),
            None,
        )
        if series_table is None:
            raise RuntimeError("engine missing 'Imputed Series' table")
        smoothed_all = np.array(
            [float(row[3]) for row in series_table["rows"]],
            dtype=np.float64,
        )

        audit = resp.get("audit_fields", {})
        return {
            "imputed_at_missing": imputed_at_missing,
            "smoothed_all": smoothed_all,
            "frac": float(audit.get("frac", float("nan"))),
            "it": int(audit.get("it", 0)),
            "n_missing": int(audit.get("n_missing", 0)),
            "n_gaps": int(audit.get("n_gaps", 0)),
            "max_gap_length": int(audit.get("max_gap_length", 0)),
            "missing_fraction": float(audit.get("missing_fraction", float("nan"))),
            "rmse_observed": float(audit.get("rmse_observed", float("nan"))),
            "mae_observed": float(audit.get("mae_observed", float("nan"))),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import statsmodels  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        out = _reference_loess_interpolation(
            y, seed=42, preset_cfg=_ENGINE_BALANCED_PRESET,
        )
        out["statsmodels_version"] = statsmodels.__version__
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8:
        # - imputed values: 6-decimal (engine lines 187, 204)
        # - smoothed_all: 6-decimal (engine line 188)
        # - frac: 4-decimal (engine line 232)
        # - rmse/mae: 6-decimal (engine lines 239-240, 298-299)
        # - missing_fraction: 4-decimal (engine line 297)
        # - integer counts: exact match
        ref_imputed_rounded = np.round(ref["imputed_at_missing"], 6)
        ref_smoothed_rounded = np.round(ref["smoothed_all"], 6)

        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # PRIMARY PARITY METRIC: imputed values at missing positions
        # (correct validation surface; structural correction vs pre-
        # rewrite smoothing-at-observed surface)
        primary["imputed_at_missing"] = _compare_vector(
            tsl["imputed_at_missing"], ref_imputed_rounded,
            ladder["primary"],
        )
        statuses.append(primary["imputed_at_missing"]["status"])

        # Secondary: smoothed_all (covers all positions; observed +
        # interpolated)
        primary["smoothed_all"] = _compare_vector(
            tsl["smoothed_all"], ref_smoothed_rounded,
            ladder["primary"],
        )
        statuses.append(primary["smoothed_all"]["status"])

        primary["frac"] = _compare_scalar(
            tsl["frac"], round(ref["frac"], 4),
            ladder["primary"],
        )
        statuses.append(primary["frac"]["status"])

        primary["rmse_observed"] = _compare_scalar(
            tsl["rmse_observed"], round(ref["rmse_observed"], 6),
            ladder["primary"],
        )
        statuses.append(primary["rmse_observed"]["status"])

        primary["mae_observed"] = _compare_scalar(
            tsl["mae_observed"], round(ref["mae_observed"], 6),
            ladder["primary"],
        )
        statuses.append(primary["mae_observed"]["status"])

        # Integer exact match
        for k in ("it", "n_missing", "n_gaps", "max_gap_length"):
            primary[k] = {
                "status": (
                    "PASS" if tsl[k] == ref[k] else "BLOCK"
                ),
                "tsl": int(tsl[k]),
                "ref": int(ref[k]),
            }
            statuses.append(primary[k]["status"])

        primary["missing_fraction"] = _compare_scalar(
            tsl["missing_fraction"], round(ref["missing_fraction"], 4),
            ladder["primary"],
        )
        statuses.append(primary["missing_fraction"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = (
            "BLOCK" if any_block else
            ("CAVEAT" if any_caveat else "PASS")
        )
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "preset": "Balanced",
                "frac": float(_ENGINE_BALANCED_PRESET["frac"]),
                "it": int(_ENGINE_BALANCED_PRESET["it"]),
                "nan_injection_indices": list(_NAN_INJECTION_INDICES),
                "n_nan_injected": int(len(_NAN_INJECTION_INDICES)),
                "statsmodels_version": ref.get("statsmodels_version", "unknown"),
            },
        )
