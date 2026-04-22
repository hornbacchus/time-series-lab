"""
InterpretationSpec for svr_forecast.

Inherits C2 forecaster Tier 1; Tier 2 substitutes SV-structure
disclosure (kernel + C + ε + γ + #SVs + SV ratio) for tree-style
feature importances. D8: feature-scaling and gamma="scale" fixed
convention disclosed. D11-refined: overfitting_by_memorization trigger.
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.primitives import (
    FMT_COEF_UNSIGNED,
    format_scale_aware,
    format_series_reference,
)

PRESET_GATED_KEYS = ()


SV_MEMORIZATION_RATIO = 0.80
OVERFITTING_RATIO = 2.0


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    horizon = int(results.get("horizon", 0))
    kernel = str(results.get("kernel") or "rbf").upper()
    train_rmse = results.get("train_rmse")
    cv_rmse = results.get("cv_rmse")
    n_train = int(results.get("n_train", 0))
    n_sv = int(results.get("n_support_vectors", 0) or 0)
    sv_ratio = results.get("sv_ratio", 0.0)
    C = results.get("C")
    epsilon = results.get("epsilon")
    gamma = results.get("gamma")
    train_str = format_scale_aware(float(train_rmse)) if train_rmse is not None else "n/a"
    cv_str = format_scale_aware(float(cv_rmse)) if cv_rmse is not None else "n/a"
    try:
        ratio = float(cv_rmse) / float(train_rmse) if train_rmse and float(train_rmse) > 0 else None
        ratio_str = f" (ratio {ratio:.2f}×)" if ratio is not None else ""
    except Exception:
        ratio_str = ""
    try:
        sv_pct = int(round(float(sv_ratio) * 100))
    except Exception:
        sv_pct = 0
    sv_health = "healthy"
    if sv_pct >= int(SV_MEMORIZATION_RATIO * 100):
        sv_health = "overfitting-by-memorization"
    elif sv_pct >= 50:
        sv_health = "elevated"
    return (
        f"SVR forecast of {format_series_reference(name)} ({n} "
        f"observations) over {horizon} periods using a {kernel} kernel. "
        f"Fit RMSE {train_str} on {n_train} training samples; 3-fold "
        f"CV RMSE {cv_str}{ratio_str}. Support-vector structure: "
        f"{n_sv} support vectors of {n_train} training samples "
        f"({sv_pct}%) — {sv_health}. Hyperparameters: C={C}, "
        f"ε={epsilon}, γ={gamma!r}."
    )


def _tier2(results: dict) -> str:
    kernel = str(results.get("kernel") or "rbf")
    C = results.get("C")
    epsilon = results.get("epsilon")
    gamma = results.get("gamma")
    n_lags = int(results.get("n_lags", 0) or 0)
    n_features = int(results.get("n_features", 0) or 0)
    return (
        f"Support Vector Regression via scikit-learn with {kernel} "
        f"kernel. Hyperparameters: C={C} (regularization), ε={epsilon} "
        f"(insensitive-tube half-width — residuals within ±ε incur no "
        f"loss), γ={gamma!r} fixed (the #1 SVR sensitivity — not "
        f"user-configurable in this wrapper). **Feature scaling "
        f"applied internally:** StandardScaler on both X and y; users "
        f"providing pre-scaled inputs should be aware of double-"
        f"scaling risk. {n_lags} lag features + rolling statistics → "
        f"{n_features} features. Multi-step forecast via recursive "
        f"1-step feed-forward. **RBF extrapolation:** the RBF kernel "
        f"decays to zero outside the neighborhood of training support "
        f"vectors, so predictions collapse toward the global mean at "
        f"long horizons — long-horizon forecasts should be treated "
        f"cautiously. **Limited interpretability:** SVR with non-"
        f"linear kernel has no native feature importance; support "
        f"vectors are training observations weighted by dual "
        f"coefficients, not features."
    )


def _trigger_overfitting_short_series(results: dict) -> Optional[str]:
    train = results.get("train_rmse")
    cv = results.get("cv_rmse")
    if train is None or cv is None:
        return None
    try:
        tv = float(train)
        cv_v = float(cv)
        if tv <= 0 or cv_v / tv < OVERFITTING_RATIO:
            return None
        ratio = cv_v / tv
    except Exception:
        return None
    return (
        f"CV RMSE is {ratio:.2f}× train RMSE — significant overfitting. "
        f"Consider reducing C, widening ε, or reducing feature count."
    )


def _trigger_overfitting_by_memorization(results: dict) -> Optional[str]:
    """D11-refined — fires when n_support_vectors > 80% × n_train.

    When most training observations become support vectors, the SVM has
    effectively memorized the training set rather than learning a
    compact decision boundary."""
    n_sv = results.get("n_support_vectors")
    n_train = results.get("n_train")
    if n_sv is None or n_train is None:
        return None
    try:
        sv = int(n_sv)
        nt = int(n_train)
        if nt <= 0 or sv / nt < SV_MEMORIZATION_RATIO:
            return None
    except Exception:
        return None
    pct = int(round(100 * sv / nt))
    return (
        f"Support-vector count ({sv}) is {pct}% of the training set "
        f"({nt}) — above the 80% overfitting-by-memorization threshold. "
        f"The SVM has effectively stored most training points as "
        f"support vectors rather than learning a compact decision "
        f"boundary. Consider increasing C, widening ε, or using a "
        f"simpler kernel."
    )


def _trigger_rbf_long_horizon(results: dict) -> Optional[str]:
    kernel = str(results.get("kernel") or "").lower()
    horizon = int(results.get("horizon", 0) or 0)
    if kernel != "rbf" or horizon <= 3:
        return None
    return (
        f"Horizon {horizon} with RBF kernel — extrapolation uncertainty "
        f"grows as predictions drift from support-vector neighborhood. "
        f"RBF forecasts collapse toward training mean at long "
        f"horizons; interpret with caution beyond 3 steps."
    )


SPEC = InterpretationSpec(
    technique_id="svr_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_overfitting_short_series,
        _trigger_overfitting_by_memorization,
        _trigger_rbf_long_horizon,
    ),
    mode_aware=False,
)

register(SPEC)
