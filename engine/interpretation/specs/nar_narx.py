"""
InterpretationSpec for nar_narx (Feedforward MLP with AR lags).

Stands alone per D5 — NAR/NARX is a feedforward MLP with AR-lag
features, not a temporal sequence architecture. D5 framing: "Feedforward
neural forecaster (MLP with AR lags)". The only C7 neural spec with
native interpretability (permutation importance).
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


def _render_top_features(results: dict, k: int = 5) -> str:
    tf = results.get("top_features") or []
    if not tf:
        top = results.get("top_feature")
        return f"most important feature: {top}" if top else "feature importances unavailable"
    parts = []
    for entry in tf[:k]:
        try:
            nm = entry.get("name")
            imp = entry.get("importance")
            if nm is None or imp is None:
                continue
            parts.append(f"{nm}={FMT_COEF_UNSIGNED.format(float(imp))}")
        except Exception:
            continue
    if not parts:
        return "feature importances unavailable"
    return "top features by permutation importance: " + ", ".join(parts)


def _tier1(results: dict) -> str:
    name = str(results.get("series_name", "the series"))
    n = int(results.get("n_obs", 0))
    n_eff = int(results.get("n_effective", 0) or 0)
    rmse = results.get("rmse_insample")
    r2 = results.get("r_squared")
    ar_lags = int(results.get("ar_lags", 0) or 0)
    hidden = results.get("hidden_layers") or []
    activation = str(results.get("activation") or "relu")
    n_params = int(results.get("n_params", 0) or 0)
    iters = int(results.get("training_iters", 0) or 0)
    rmse_str = format_scale_aware(float(rmse)) if rmse is not None else "n/a"
    r2_str = FMT_COEF_UNSIGNED.format(float(r2)) if r2 is not None else "n/a"
    try:
        r2_f = float(r2) if r2 is not None else None
    except Exception:
        r2_f = None
    verdict = ""
    if r2_f is not None:
        if r2_f >= 0.9:
            verdict = " — strong fit"
        elif r2_f >= 0.7:
            verdict = ""
        elif r2_f >= 0.4:
            verdict = " — moderate fit"
        else:
            verdict = " — weak fit"
    model_name = str(results.get("model") or "NAR")
    exog = results.get("exogenous") or []
    exog_clause = f"with {len(exog)} exogenous regressor(s)" if exog else "with no exogenous regressors"
    return (
        f"Feedforward neural forecaster (MLP with AR lags) on "
        f"{format_series_reference(name)} ({n} observations). In-"
        f"sample RMSE {rmse_str}, R²={r2_str}{verdict}. Architecture: "
        f"hidden layer(s) {list(hidden)} with {activation} activation, "
        f"{ar_lags} AR lag features {exog_clause} → {n_params} total "
        f"parameters fitted on {n_eff} effective observations, "
        f"converged in {iters} iterations. {_render_top_features(results)}."
    )


def _tier2(results: dict) -> str:
    n_eff = int(results.get("n_effective", 0) or 0)
    ar_lags = int(results.get("ar_lags", 0) or 0)
    hidden = results.get("hidden_layers") or []
    activation = str(results.get("activation") or "relu")
    alpha_reg = results.get("alpha_reg")
    n_params = results.get("n_params")
    iters = int(results.get("training_iters", 0) or 0)
    exog = results.get("exogenous") or []
    has_exog = bool(exog)
    mode = "NARX" if has_exog else "NAR"
    exog_clause = (
        f"with {len(exog)} exogenous regressor(s): {', '.join(exog)}"
        if has_exog else "with no exogenous regressors (NAR mode)"
    )
    return (
        f"sklearn MLPRegressor with AR-lag features — feedforward "
        f"neural network, NOT a temporal architecture (unlike LSTM / "
        f"GRU / TCN / Transformer). Input: {ar_lags} AR lag feature(s) "
        f"of the endogenous series {exog_clause}. Hidden layer(s) "
        f"{list(hidden)} with {activation} activation; L2 "
        f"regularization α={alpha_reg}. Training: sklearn's Adam "
        f"optimizer with early_stopping=True; converged in {iters} "
        f"iterations on {n_eff} effective observations ({n_params} "
        f"total parameters). Multi-step forecast via iterative 1-step "
        f"+ bootstrap residual sampling for prediction intervals. "
        f"**Interpretability:** permutation importance exposed (the "
        f"only C7 neural wrapper with feature-level attribution — "
        f"LSTM / GRU / TCN / Transformer have none)."
    )


def _trigger_low_r2(results: dict) -> Optional[str]:
    r2 = results.get("r_squared")
    if r2 is None:
        return None
    try:
        v = float(r2)
    except Exception:
        return None
    if v >= 0.4:
        return None
    return (
        f"R²={v:.3f} suggests the AR-lag feedforward model explains "
        f"little of the target's variance. Consider (a) adding "
        f"exogenous regressors (NARX mode); (b) longer AR lags; "
        f"(c) a temporal architecture (LSTM / TCN) if sample size "
        f"supports it."
    )


def _trigger_insufficient_data(results: dict) -> Optional[str]:
    n_eff = results.get("n_effective")
    if n_eff is None:
        return None
    try:
        if int(n_eff) >= 100:
            return None
    except Exception:
        return None
    return (
        f"Effective training sample count {n_eff} is below the "
        f"100-observation rule of thumb for feedforward MLP "
        f"forecasters. Loss surface is poorly constrained; forecasts "
        f"may be unreliable."
    )


SPEC = InterpretationSpec(
    technique_id="nar_narx",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_low_r2,
        _trigger_insufficient_data,
    ),
    mode_aware=False,
)

register(SPEC)
