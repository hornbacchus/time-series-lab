"""
InterpretationSpec for rolling_origin_cv.

Per S6: Tier 1 uses neutral framing "below 1.0, so the model
outperforms the naive baseline" rather than editorializing.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


# In-spec MASE strength bands. TODO: promote to C.9 primitive if a
# second spec in C2-C7 needs MASE-strength banding.
def _mase_band(mase: float) -> str:
    m = float(mase)
    if m < 0.6:
        return "strong-performance"
    if m < 1.0:
        return "standard-performance"
    if m < 1.5:
        return "weak-performance"
    return "worse-than-naive"


def _iqr_stability_band(std_over_mean: float) -> str:
    r = float(std_over_mean)
    if r < 0.2:
        return "stable"
    if r < 0.5:
        return "moderately variable"
    return "volatile"


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    model_name = str(results.get("model_name", "the model"))
    n_folds = int(results.get("n_folds", 0))
    mean_mase = float(results.get("mean_mase", 0.0))
    std_mase = float(results.get("std_mase", 0.0))
    avg_coverage = results.get("avg_coverage")
    target_coverage = results.get("target_coverage")
    mase_band = _mase_band(mean_mase)
    mase_direction = (
        "below 1.0, so the model outperforms the naive baseline"
        if mean_mase < 1.0 else
        "at or above 1.0, so the model does not outperform the naive baseline"
    )
    stability = ""
    if mean_mase > 0:
        ratio = std_mase / mean_mase
        stability = _iqr_stability_band(ratio)
    stability_clause = f", std across folds {FMT_COEF_UNSIGNED.format(std_mase)} ({stability})"
    coverage_clause = ""
    if avg_coverage is not None and target_coverage is not None:
        cov_pct = 100.0 * float(avg_coverage)
        target_pct = 100.0 * float(target_coverage)
        gap_pct = cov_pct - target_pct
        direction = (
            "above target" if gap_pct > 2 else
            "below target" if gap_pct < -2 else
            "near target"
        )
        coverage_clause = (
            f" Coverage of {int(target_pct)}% intervals: "
            f"{cov_pct:.0f}% ({direction})."
        )
    return (
        f"Rolling-origin {n_folds}-fold CV of {model_name} on "
        f"{format_series_reference(name)}: mean MASE "
        f"{FMT_COEF_UNSIGNED.format(mean_mase)} ({mase_band} band, "
        f"{mase_direction}){stability_clause}.{coverage_clause}"
    )


def _tier2(results: dict) -> str:
    n_folds = int(results.get("n_folds", 0))
    min_train = results.get("min_train_size")
    step = results.get("step_size")
    horizon = results.get("test_horizon")
    mase_min = results.get("min_mase")
    mase_max = results.get("max_mase")
    mean_mase = results.get("mean_mase")
    std_mase = results.get("std_mase")
    mean_smape = results.get("mean_smape")
    mean_mae = results.get("mean_mae")
    avg_coverage = results.get("avg_coverage")
    target_coverage = results.get("target_coverage")
    fold_config = (
        f"{n_folds} rolling-origin folds with minimum training size "
        f"{int(min_train)}, step size {int(step)}, test horizon {int(horizon)} each"
        if (min_train is not None and step is not None and horizon is not None)
        else f"{n_folds} rolling-origin folds"
    )
    mase_range = (
        f"[{FMT_COEF_UNSIGNED.format(float(mase_min))}, "
        f"{FMT_COEF_UNSIGNED.format(float(mase_max))}]"
        if (mase_min is not None and mase_max is not None) else "reported in the data tables"
    )
    mase_line = (
        f"Per-fold MASE range {mase_range}, mean "
        f"{FMT_COEF_UNSIGNED.format(float(mean_mase))}, std "
        f"{FMT_COEF_UNSIGNED.format(float(std_mase))}."
        if (mean_mase is not None and std_mase is not None)
        else "MASE summary in the data tables."
    )
    metrics_line = ""
    if mean_smape is not None:
        metrics_line += f" sMAPE mean {float(mean_smape):.1f}%."
    if mean_mae is not None:
        metrics_line += f" MAE mean {FMT_COEF_UNSIGNED.format(float(mean_mae))}."
    coverage_line = ""
    if avg_coverage is not None and target_coverage is not None:
        cov_pct = 100.0 * float(avg_coverage)
        target_pct = 100.0 * float(target_coverage)
        coverage_line = (
            f" {int(target_pct)}%-interval coverage {cov_pct:.0f}% "
            f"(target {int(target_pct)}%)."
        )
    ratio_line = ""
    if mean_mase is not None and std_mase is not None and float(mean_mase) > 0:
        ratio = float(std_mase) / float(mean_mase)
        stability = _iqr_stability_band(ratio)
        ratio_line = (
            f" Std/mean MASE ratio {ratio:.2f} — {stability}; "
            f"fold-to-fold "
            f"{'stability indicates the model is not regime-dependent on this sample' if stability == 'stable' else 'variability reflects regime-dependent predictability or small holdout windows'}."
        )
    return (
        f"{fold_config}. {mase_line}{metrics_line}{coverage_line}{ratio_line}"
    )


def _trigger_volatile_folds(results: dict) -> Optional[str]:
    mean_mase = results.get("mean_mase")
    std_mase = results.get("std_mase")
    if mean_mase is None or std_mase is None or float(mean_mase) <= 0:
        return None
    if float(std_mase) / float(mean_mase) <= 0.3:
        return None
    return (
        f"Fold-to-fold std/mean MASE ratio "
        f"{float(std_mase) / float(mean_mase):.2f} exceeds 0.3 — "
        f"performance is volatile across folds. The sample has "
        f"regime-dependent predictability; pooled CV score masks "
        f"substantial within-sample variation."
    )


def _trigger_worse_than_naive(results: dict) -> Optional[str]:
    mean_mase = results.get("mean_mase")
    if mean_mase is None or float(mean_mase) <= 1:
        return None
    return (
        f"Mean MASE {FMT_COEF_UNSIGNED.format(float(mean_mase))} "
        f"exceeds 1.0 — naive forecast beats this model. Reconsider "
        f"the specification; on this series the model is not adding "
        f"value over the seasonal-naive baseline."
    )


def _trigger_miscalibrated_coverage(results: dict) -> Optional[str]:
    avg_coverage = results.get("avg_coverage")
    target_coverage = results.get("target_coverage")
    if avg_coverage is None or target_coverage is None:
        return None
    gap = 100.0 * (float(avg_coverage) - float(target_coverage))
    if abs(gap) <= 10:
        return None
    direction = "above" if gap > 0 else "below"
    return (
        f"Interval coverage "
        f"{100.0 * float(avg_coverage):.0f}% is {abs(gap):.0f} points "
        f"{direction} the {100.0 * float(target_coverage):.0f}% "
        f"target — intervals are materially miscalibrated. Review the "
        f"uncertainty specification; the intervals do not deliver "
        f"their nominal coverage on this data."
    )


SPEC = InterpretationSpec(
    technique_id="rolling_origin_cv",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_volatile_folds,
        _trigger_worse_than_naive,
        _trigger_miscalibrated_coverage,
    ),
    mode_aware=False,
)

register(SPEC)
