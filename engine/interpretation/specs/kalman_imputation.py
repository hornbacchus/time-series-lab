"""
InterpretationSpec for kalman_imputation.

Tier 1 leads with imputation count / percent and the model type;
highlights that imputation uncertainty widens toward gap interiors.
Tier 2 discloses the state-space model and the posterior-variance
interpretation of per-value SE.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_series_reference,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    n_missing = int(results.get("n_missing", 0))
    pct = (100.0 * n_missing / n) if n > 0 else 0.0
    model_type = str(results.get("model_type", "local linear trend"))
    n_gaps = int(results.get("n_gaps", 0))
    avg_se = results.get("avg_imputation_se")
    se_clause = (
        f"average imputation SE {FMT_COEF_UNSIGNED.format(float(avg_se))}"
        if avg_se is not None else "per-value SE reported in the data tables"
    )
    return (
        f"{n_missing} of {n} observations ({pct:.0f}%) imputed in "
        f"{format_series_reference(name)} using Kalman smoother "
        f"({model_type}) across {n_gaps} gap segment{'s' if n_gaps != 1 else ''}. "
        f"The {se_clause}; single-point interpolation is tight but "
        f"gaps longer than 5 periods carry meaningful uncertainty."
    )


def _tier2(results: dict) -> str:
    model_type = str(results.get("model_type", "local linear trend"))
    n_gaps = int(results.get("n_gaps", 0))
    max_gap = int(results.get("max_gap", 0))
    rmse = results.get("rmse")
    aic = results.get("aic")
    rmse_clause = (
        f"RMSE on observed data {FMT_COEF_UNSIGNED.format(float(rmse))}"
        if rmse is not None else "RMSE not reported"
    )
    aic_clause = (
        f"AIC {FMT_COEF_UNSIGNED.format(float(aic))}" if aic is not None
        else "AIC not reported"
    )
    return (
        f"State-space model: {model_type}. Gap geometry: {n_gaps} "
        f"gaps, max gap length {max_gap} periods. Imputation "
        f"uncertainty comes from the Kalman smoother posterior "
        f"variance: SE at gap-interior points is typically 2-3× SE at "
        f"gap edges. Model diagnostics: {rmse_clause}, {aic_clause}. "
        f"Consider alternative specifications (local level only, "
        f"structural with cycle) if the residual ACF rejects white-"
        f"noise."
    )


def _trigger_high_missing_fraction(results: dict) -> Optional[str]:
    n = int(results.get("n_obs", 0))
    n_missing = int(results.get("n_missing", 0))
    if n == 0:
        return None
    frac = n_missing / n
    if frac < 0.5:
        return None
    return (
        f"More than half the series ({100.0 * frac:.0f}%) was "
        f"imputed. Fit quality is weak when most of the data is "
        f"imputed from the state-space model itself; use the "
        f"imputed series with caution and validate against "
        f"auxiliary data sources if available."
    )


def _trigger_long_interior_gap(results: dict) -> Optional[str]:
    n = int(results.get("n_obs", 0))
    max_gap = int(results.get("max_gap", 0))
    if n == 0 or max_gap < 0.1 * n:
        return None
    return (
        f"Max gap length {max_gap} exceeds 10% of the series length. "
        f"Long interior gaps dominate the imputation; single-series "
        f"Kalman smoothing may be unreliable. Consider imputing with "
        f"an auxiliary series (e.g., via a regression component in a "
        f"structural model)."
    )


SPEC = InterpretationSpec(
    technique_id="kalman_imputation",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(_trigger_high_missing_fraction, _trigger_long_interior_gap),
    mode_aware=False,
)

register(SPEC)
