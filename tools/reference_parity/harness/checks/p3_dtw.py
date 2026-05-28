"""Phase 3 Batch 10 — DTW (Dynamic Time Warping) parity check.

TSL ``engine/techniques/dtw_alignment_lag.py`` (custom numpy DTW
with Sakoe-Chiba window constraint at preset window_frac + z-
normalization + step_pattern variant (symmetric1 / symmetric2) +
subsample trigger for series > 500 + forward DP + backtrack path
extraction + per-x-index time-varying lag extraction via x_to_y
dict + per-x averaging + carry-forward heuristic + lag segmentation
via running-mean change-point heuristic + multi-table output) vs
from-scratch paper-formula reimpl mirroring engine pipeline
verbatim.

Rewritten at SC8-side Cat 3 remediation cycle session 8/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC8 = SECOND Tier B session** + **FIRST
cycle session forward-amending an existing §2.5 entry (S17)** vs
SC1-SC7 which all created new §2.5 entries.

**Helper identity verification (Step 1 of SC8 workflow):** Engine
`dtw_alignment_lag.py` exposes `run` + `_dtw` (forward DP + backtrack)
+ `_segment_lags` (change-point segmentation) + `build_interpretation`.
NO tree-family helpers (`_prepare_series` / `_create_features` /
`_create_forecast_features`). Tier B Layer 2 family-shared helpers
from SC1 NOT APPLICABLE per SC7 forward-instrumentation + SC8 helper-
identity confirmation. Bespoke per-session reimplementation:
`_reference_dtw_forward_dp` mirrors engine `_dtw` lines 416-491 +
`_reference_segment_lags` mirrors engine `_segment_lags` lines
494-525 + `_reference_dtw_alignment_lag` mirrors engine `run()`
body verbatim.

**Pre-rewrite degeneracy (Cat 3 DEGENERATE-VACUOUS classification):**
Original harness used local helper `_dtw_distance` (lines 36-45)
implementing UNCONSTRAINED DP with squared Euclidean local cost +
NO window constraint + NO z-normalization + NO step_pattern variant
+ NO backtrack + NO time-varying lag extraction + NO segmentation +
NO multi-table output. Both arms compared a single scalar
`dtw_distance` value (TSL arm = harness `_dtw_distance`; REF arm =
dtaidistance.dtw.distance) — degenerate self-parity bypassing engine
code path entirely. Cat 3 surfaced at inventory verification 12d3785
+ Gate 1 finding + triage close confirmation. S17 §2.5 entry pre-
rewrite parity claim documented Layer 1 dtaidistance.dtw cross-
package PASS but Layer 2 engine DTW core + Layer 3 post-processing
were explicitly flagged as NOT parity-validated.

**Forward-amendment scope:** This SC8 commit produces engine-
invocation parity (TSL arm invokes engine via RunContext at Balanced
preset; reference arm bespoke reimpl mirrors engine pipeline
verbatim) covering Layer 2 + Layer 3 sub-components 3a/3b/3c that
the pre-rewrite S17 entry explicitly flagged as expert-review-
required. S17 §2.5 entry forward-amended at this commit to
supersede the pre-rewrite Layer 1-only parity claim with the post-
rewrite Layer 1+2+3 parity claim.

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic DP (numpy DTW is
deterministic at fixed input + tie-breaking convention).
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


# Engine preset Balanced config (engine `dtw_alignment_lag.py`
# line 51). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "window_frac": 0.20,
    "subsample": 2,
}


def _generate_dtw_pair(
    *, seed: int, n: int = 100, warp_factor: float = 1.2,
) -> tuple[np.ndarray, np.ndarray]:
    """Two warped sinusoids — preserved DGP from pre-rewrite scope."""
    rng = np.random.default_rng(seed)
    t = np.arange(n)
    base = np.sin(2 * np.pi * t / 20)
    x = base + 0.05 * rng.standard_normal(n)
    t2 = (t * warp_factor) % n
    y_idx = np.clip(t2.astype(int), 0, n - 1)
    y = base[y_idx] + 0.05 * rng.standard_normal(n)
    return x, y


def _reference_dtw_forward_dp(x, y, window, step_pattern):
    """Reference reimpl of engine `_dtw` at engine lines 416-491
    verbatim modulo progress_callback. Forward DP + backtrack
    producing distance + cost matrix + warping path. Tie-breaking
    convention: `min(choices, key=lambda c: c[0])` — stable tie-
    break (Python's min returns first-encountered minimum) per
    engine line 488. Reference uses identical convention.
    """
    nx = len(x)
    ny = len(y)
    D = np.full((nx + 1, ny + 1), np.inf)
    D[0, 0] = 0.0

    for i in range(1, nx + 1):
        j_start = max(1, i - window)
        j_end = min(ny, i + window)
        for j in range(j_start, j_end + 1):
            cost = (x[i - 1] - y[j - 1]) ** 2
            if step_pattern == "symmetric1":
                D[i, j] = cost + D[i - 1, j - 1]
            else:
                D[i, j] = cost + min(
                    D[i - 1, j - 1],
                    D[i - 1, j],
                    D[i, j - 1],
                )

    distance = (
        float(np.sqrt(D[nx, ny]))
        if np.isfinite(D[nx, ny])
        else float("inf")
    )

    # Backtrack per engine lines 469-491
    path = []
    i, j = nx, ny
    while i > 0 or j > 0:
        path.append((i - 1, j - 1))
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            if step_pattern == "symmetric1":
                i -= 1
                j -= 1
            else:
                choices = [
                    (D[i - 1, j - 1], i - 1, j - 1),
                    (D[i - 1, j], i - 1, j),
                    (D[i, j - 1], i, j - 1),
                ]
                _, i, j = min(choices, key=lambda c: c[0])
    path.reverse()
    return distance, D[1:, 1:], path


def _reference_segment_lags(local_lags, threshold=2.0):
    """Reference reimpl of engine `_segment_lags` at engine lines
    494-525 verbatim. Running-mean + deviation-threshold change-
    point segmentation."""
    n = len(local_lags)
    if n == 0:
        return []
    segments = []
    seg_start = 0
    for i in range(1, n):
        seg_mean = np.mean(local_lags[seg_start:i])
        if (
            abs(local_lags[i] - seg_mean) > threshold
            and i - seg_start > 5
        ):
            segments.append({
                "start": seg_start,
                "end": i,
                "mean_lag": float(np.mean(local_lags[seg_start:i])),
                "std_lag": float(np.std(local_lags[seg_start:i])),
            })
            seg_start = i
    segments.append({
        "start": seg_start,
        "end": n,
        "mean_lag": float(np.mean(local_lags[seg_start:n])),
        "std_lag": float(np.std(local_lags[seg_start:n])),
    })
    return segments


def _reference_dtw_alignment_lag(
    x_vals: np.ndarray, y_vals: np.ndarray,
    *, seed: int, preset_cfg: dict = None,
    normalize: bool = True, step_pattern: str = "symmetric2",
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `dtw_alignment_lag.run()`
    pipeline at engine lines 56-413 verbatim (Balanced preset path).
    Bespoke per-session implementation per SC8 Tier B.2 — Layer 2
    family helpers NOT APPLICABLE.

    Pipeline (engine lines referenced inline):
    - Drop NaN per series independently (engine lines 101-102)
    - Resolve preset + apply subsample if min(nx,ny) > 500 (engine
      lines 141-152); for our n=100 fixture, scale_factor=1
    - z-normalize if normalize=True (engine lines 158-164)
    - Compute Sakoe-Chiba window (engine line 167)
    - Forward DP + backtrack via _dtw (engine line 172 → _dtw at
      lines 416-491)
    - Scale path by scale_factor (engine lines 179-181)
    - Build x_to_y dict + per-x averaging + carry-forward heuristic
      (engine lines 185-198)
    - Compute summary stats (engine lines 201-205)
    - Path-length ratio + normalized DTW (engine lines 208-213)
    - Segment lags via _segment_lags (engine line 216)
    """
    cfg = preset_cfg or _ENGINE_BALANCED_PRESET
    np.random.seed(seed)

    # Drop NaN independently per engine lines 101-102
    x_clean = x_vals[~np.isnan(x_vals)]
    y_clean = y_vals[~np.isnan(y_vals)]
    nx = len(x_clean)
    ny = len(y_clean)

    window_frac = float(cfg["window_frac"])
    subsample = int(cfg["subsample"])

    # Subsample trigger: only if min(nx, ny) > 500 (engine line 141)
    if subsample > 1 and min(nx, ny) > 500:
        x_work = x_clean[::subsample]
        y_work = y_clean[::subsample]
        scale_factor = subsample
    else:
        x_work = x_clean.copy()
        y_work = y_clean.copy()
        scale_factor = 1

    nxw = len(x_work)
    nyw = len(y_work)

    # z-normalize per engine lines 158-164
    if normalize:
        x_mu, x_sigma = np.mean(x_work), np.std(x_work)
        y_mu, y_sigma = np.mean(y_work), np.std(y_work)
        if x_sigma > 1e-10:
            x_work = (x_work - x_mu) / x_sigma
        if y_sigma > 1e-10:
            y_work = (y_work - y_mu) / y_sigma

    # Sakoe-Chiba window per engine line 167
    window_size = max(1, int(window_frac * max(nxw, nyw)))

    # Forward DP + backtrack
    dtw_dist, _cost_matrix, path = _reference_dtw_forward_dp(
        x_work, y_work, window_size, step_pattern,
    )

    # Scale path back per engine lines 179-181
    path_x = np.array([p[0] for p in path]) * scale_factor
    path_y = np.array([p[1] for p in path]) * scale_factor

    # x_to_y dict + averaging per engine lines 185-196
    x_to_y = {}
    for px, py in zip(path_x, path_y):
        px_int = int(px)
        if px_int not in x_to_y:
            x_to_y[px_int] = []
        x_to_y[px_int].append(int(py))

    local_lags = np.zeros(nx)
    for xi in range(nx):
        if xi in x_to_y:
            matches = x_to_y[xi]
            local_lags[xi] = np.mean(matches) - xi
        elif xi > 0:
            local_lags[xi] = local_lags[xi - 1]

    # Summary stats per engine lines 201-205
    mean_lag = float(np.mean(local_lags))
    std_lag = float(np.std(local_lags))
    max_lag = float(np.max(local_lags))
    min_lag = float(np.min(local_lags))
    median_lag = float(np.median(local_lags))

    # Distortion + normalized DTW per engine lines 208-213
    path_len = len(path)
    diag_len = max(nxw, nyw)
    distortion_ratio = path_len / diag_len
    dtw_normalized = dtw_dist / path_len if path_len > 0 else dtw_dist

    # Segment lags per engine line 216
    lag_segments = _reference_segment_lags(local_lags, threshold=2.0)

    return {
        "dtw_distance": float(dtw_dist),
        "dtw_normalized": float(dtw_normalized),
        "mean_lag": mean_lag,
        "median_lag": median_lag,
        "std_lag": std_lag,
        "min_lag": min_lag,
        "max_lag": max_lag,
        "distortion_ratio": float(distortion_ratio),
        "path_length": int(path_len),
        "n_segments": int(len(lag_segments)),
        "window_size_scaled": int(window_size * scale_factor),
    }


class DtwParity(P3ParityCheck):
    """DTW alignment lag parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.dtw_alignment_lag.run() via
    RunContext with TWO series (X + Y warped sinusoid pair) + Balanced
    preset (window_frac=0.20 + subsample=2 + normalize=True default +
    step_pattern=symmetric2 default). Reference arm reimplements the
    full engine pipeline bespoke per SC8 Tier B.2 (Layer 2 family
    helpers NOT APPLICABLE) covering Layer 1 (DTW DP core) + Layer 2
    (window + normalize + step_pattern variants + pre-processing
    helpers) + Layer 3 sub-components 3a (backtrack) + 3b (lag
    extraction with x_to_y dict + per-x averaging + carry-forward) +
    3c (lag segmentation via running-mean change-point heuristic).
    Forward-amendment of S17 §2.5 entry per Tier 2 incremental
    pattern; pre-rewrite scalar dtw_distance-only parity superseded.
    """

    technique_id = "p3_dtw"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "DTW is closed-form dynamic programming with deterministic "
        "recurrence + deterministic tie-breaking via Python's min(). "
        "Engine and reference reimpl follow identical pipeline "
        "(NaN drop + subsample-trigger + z-normalize + Sakoe-Chiba "
        "window + symmetric2 step pattern + forward DP + backtrack "
        "+ x_to_y per-x averaging + carry-forward + segment_lags); "
        "outputs match at machine precision modulo engine output-"
        "rounding floor at distance (4-decimal) + normalized (6-"
        "decimal) + lag stats (2-decimal) + distortion (3-decimal). "
        "SC8 Tier B.2 bespoke per-session reimpl covering Layer 2 + "
        "Layer 3 sub-components flagged at pre-rewrite S17 entry as "
        "expert-review-required."
    )

    DGP_N = 100

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        x, y = _generate_dtw_pair(seed=seed, n=self.DGP_N)
        return {"x": x, "y": y}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Invoke engine wrapper via RunContext with 2-series input
        (X + Y) at Balanced preset; extract DTW summary stats from
        engine audit_fields."""
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.dtw_alignment_lag as dtw_mod  # type: ignore

        np.random.seed(42)
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_dtw_parity",
            "technique_id": "dtw_alignment_lag",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(x))),
            "series": [
                {"name": "x", "values": x.tolist()},
                {"name": "y", "values": y.tolist()},
            ],
            "params": {},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = dtw_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL dtw_alignment_lag failed: "
                f"{resp.get('error_message')}"
            )
        audit = resp.get("audit_fields", {})
        return {
            "dtw_distance": float(audit.get("dtw_distance", float("nan"))),
            "dtw_normalized": float(audit.get("dtw_normalized", float("nan"))),
            "mean_lag": float(audit.get("mean_lag", float("nan"))),
            "median_lag": float(audit.get("median_lag", float("nan"))),
            "std_lag": float(audit.get("std_lag", float("nan"))),
            "min_lag": float(audit.get("min_lag", float("nan"))),
            "max_lag": float(audit.get("max_lag", float("nan"))),
            "distortion_ratio": float(audit.get("distortion_ratio", float("nan"))),
            "path_length": int(audit.get("path_length", 0)),
            "n_segments": int(audit.get("n_segments", 0)),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        x = np.asarray(fixture["x"], dtype=np.float64)
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        return _reference_dtw_alignment_lag(
            x, y, seed=42, preset_cfg=_ENGINE_BALANCED_PRESET,
            normalize=True, step_pattern="symmetric2",
        )

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8:
        # - dtw_distance: 4-decimal (engine line 376)
        # - dtw_normalized: 6-decimal (engine line 377)
        # - lag stats (mean/median/std/min/max): 2-decimal (engine 378-382)
        # - distortion_ratio: 3-decimal (engine line 383)
        # - path_length / n_segments: integer
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["dtw_distance"] = _compare_scalar(
            tsl["dtw_distance"], round(ref["dtw_distance"], 4),
            ladder["primary"],
        )
        statuses.append(primary["dtw_distance"]["status"])

        primary["dtw_normalized"] = _compare_scalar(
            tsl["dtw_normalized"], round(ref["dtw_normalized"], 6),
            ladder["primary"],
        )
        statuses.append(primary["dtw_normalized"]["status"])

        primary["mean_lag"] = _compare_scalar(
            tsl["mean_lag"], round(ref["mean_lag"], 2),
            ladder["primary"],
        )
        statuses.append(primary["mean_lag"]["status"])

        primary["median_lag"] = _compare_scalar(
            tsl["median_lag"], round(ref["median_lag"], 2),
            ladder["primary"],
        )
        statuses.append(primary["median_lag"]["status"])

        primary["std_lag"] = _compare_scalar(
            tsl["std_lag"], round(ref["std_lag"], 2),
            ladder["primary"],
        )
        statuses.append(primary["std_lag"]["status"])

        primary["min_lag"] = _compare_scalar(
            tsl["min_lag"], round(ref["min_lag"], 2),
            ladder["primary"],
        )
        statuses.append(primary["min_lag"]["status"])

        primary["max_lag"] = _compare_scalar(
            tsl["max_lag"], round(ref["max_lag"], 2),
            ladder["primary"],
        )
        statuses.append(primary["max_lag"]["status"])

        primary["distortion_ratio"] = _compare_scalar(
            tsl["distortion_ratio"], round(ref["distortion_ratio"], 3),
            ladder["primary"],
        )
        statuses.append(primary["distortion_ratio"]["status"])

        primary["path_length"] = {
            "status": (
                "PASS" if tsl["path_length"] == ref["path_length"]
                else "BLOCK"
            ),
            "tsl": int(tsl["path_length"]),
            "ref": int(ref["path_length"]),
        }
        statuses.append(primary["path_length"]["status"])

        primary["n_segments"] = {
            "status": (
                "PASS" if tsl["n_segments"] == ref["n_segments"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_segments"]),
            "ref": int(ref["n_segments"]),
        }
        statuses.append(primary["n_segments"]["status"])

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
                "window_frac": float(_ENGINE_BALANCED_PRESET["window_frac"]),
                "subsample": int(_ENGINE_BALANCED_PRESET["subsample"]),
                "normalize": True,
                "step_pattern": "symmetric2",
            },
        )
