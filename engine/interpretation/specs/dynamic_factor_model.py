"""
InterpretationSpec for dynamic_factor_model (DFM).

NEW Tier 1 shape — named-loading-per-factor, richer than SSA's ordinal
group labels. Cites the 2-3 strongest-loading series per factor (and a
weak-loading anchor) using ``interpret_correlation_strength`` bands
(Decision D12 reuse).

Decision D3 Option A: dominant-series-per-factor extraction happens
spec-side; the wrapper exports loadings_per_factor + communalities but
not a pre-cooked dominant-series field.

Decision D4: factor sign convention (largest-loading normalized to
positive) disclosed in Tier 2.

Results-dict keys consumed:

    variables              : list[str]
    n_variables / k_factors / factor_order / error_order
    aic / bic / log_likelihood
    variance_explained_pct : float (0-100)
    n_observations / horizon
    loadings_per_factor    : list[list[float]], length=k_factors,
                             each inner list length=n_variables
    communalities          : list[float], length=n_variables
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.primitives import (
    format_scale_aware,
    interpret_correlation_strength,
    FMT_RHO,
)
from interpretation.registry import register

PRESET_GATED_KEYS = ()


def _rank_series_by_loading(loadings, variables):
    """Return list of (variable, loading, |loading|) sorted desc by |loading|."""
    rows = []
    try:
        for i, v in enumerate(loadings):
            rows.append((str(variables[i]), float(v), abs(float(v))))
    except Exception:
        return []
    rows.sort(key=lambda r: r[2], reverse=True)
    return rows


def _factor_loading_summary(loadings, variables, factor_idx_1based) -> str:
    """Render per-factor dominant + weak clause."""
    ranked = _rank_series_by_loading(loadings, variables)
    if not ranked:
        return f"Factor {factor_idx_1based}: loadings unavailable"
    # Top 2 as "strongest"; last as "weakest" anchor (only if n_vars >= 3)
    strong_parts = []
    for i, (name, val, _) in enumerate(ranked[:2]):
        band = interpret_correlation_strength(val)["band"]
        strong_parts.append(f"{name} ({FMT_RHO.format(val)}, {band})")
    text = f"Factor {factor_idx_1based} loads strongest on " + " and ".join(strong_parts)
    if len(ranked) >= 3:
        name_w, val_w, _ = ranked[-1]
        band_w = interpret_correlation_strength(val_w)["band"]
        text += (
            f"; weakest on {name_w} ({FMT_RHO.format(val_w)}, {band_w})"
        )
    return text


def _tier1(results: dict) -> str:
    variables = list(results.get("variables") or [])
    n_vars = int(results.get("n_variables", len(variables)))
    k = int(results.get("k_factors", 1))
    n_obs = int(results.get("n_observations", 0))
    ve_pct = float(results.get("variance_explained_pct", 0.0))
    loadings_per_factor = results.get("loadings_per_factor") or []

    names_quoted = ", ".join(f"'{v}'" for v in variables) if variables else f"{n_vars} series"

    factor_word = "factor" if k == 1 else "factors"
    factor_summaries = []
    for f_idx in range(min(k, len(loadings_per_factor))):
        factor_summaries.append(
            _factor_loading_summary(
                loadings_per_factor[f_idx], variables, f_idx + 1
            )
        )
    summary_block = ". ".join(factor_summaries) + "." if factor_summaries else ""

    # Variance commentary
    if ve_pct >= 70:
        ve_adj = "strong common component"
    elif ve_pct >= 40:
        ve_adj = "moderate common component"
    elif ve_pct >= 20:
        ve_adj = "weak common component"
    else:
        ve_adj = "very weak common component — series may be near-independent"
    idio_pct = max(0.0, 100.0 - ve_pct)

    return (
        f"Dynamic Factor Model with {k} latent {factor_word} on {n_vars} "
        f"series ({names_quoted}) over {n_obs} observations. "
        f"{summary_block} "
        f"The factor{'s explain' if k != 1 else ' explains'} "
        f"{ve_pct:.1f}% of panel variance ({ve_adj}); the remaining "
        f"{idio_pct:.1f}% is idiosyncratic (series-specific)."
    )


def _tier2(results: dict) -> str:
    k = int(results.get("k_factors", 1))
    factor_order = int(results.get("factor_order", 0) or 0)
    error_order = int(results.get("error_order", 0) or 0)
    n_obs = int(results.get("n_observations", 0))
    aic = results.get("aic")
    bic = results.get("bic")
    ll = results.get("log_likelihood")
    aic_str = format_scale_aware(float(aic)) if aic is not None else "not reported"
    bic_str = format_scale_aware(float(bic)) if bic is not None else "not reported"
    ll_str = format_scale_aware(float(ll)) if ll is not None else "not reported"

    factor_word = "common factor" if k == 1 else "common factors"
    err_clause = (
        f"idiosyncratic components with AR({error_order}) dynamics"
        if error_order > 0 else
        "white-noise idiosyncratic components"
    )

    # Decision D4 — sign convention disclosure
    sign_disclosure = (
        " Factor signs are normalized so that the largest-loading series "
        "loads positively; flip-invariance of dynamic factor models is "
        "resolved by this convention and does not affect interpretation."
    )

    return (
        f"State-space Dynamic Factor Model (Stock-Watson 1989 formulation) "
        f"via statsmodels DynamicFactor with Kalman filter / MLE estimation. "
        f"k={k} {factor_word} with AR({factor_order}) dynamics, {err_clause}. "
        f"The panel may have been auto-transformed to stationary form "
        f"(e.g. log-differences) to enforce DFM identification — refer to "
        f"the wrapper's warnings for the exact transformation applied. "
        f"{sign_disclosure} AIC {aic_str}, BIC {bic_str}, log-likelihood "
        f"{ll_str} on {n_obs} observations. Number-of-factors (k={k}) was "
        f"user-specified; no Bai-Ng IC or eigenvalue-ratio criterion "
        f"automatic selection is applied by this wrapper. For comparative "
        f"rank selection, refit with k={k+1} and compare AIC / BIC / "
        f"variance-explained."
    )


def _trigger_low_variance_explained(results: dict) -> Optional[str]:
    try:
        ve = float(results.get("variance_explained_pct", 100.0))
    except Exception:
        return None
    if ve >= 30.0:
        return None
    return (
        f"Common factors explain only {ve:.1f}% of panel variance — "
        f"the series are weakly linked. A factor model may not be the "
        f"best framing; consider per-series univariate models or "
        f"cross-correlation analysis to identify the strongest pairs "
        f"before factorizing."
    )


def _trigger_dominant_loading_asymmetry(results: dict) -> Optional[str]:
    """Fires when, for any factor, max|loading| / max(min|loading|, tol)
    exceeds 5 — indicating the factor is effectively loaded on one series.
    """
    loadings_per_factor = results.get("loadings_per_factor") or []
    if not loadings_per_factor:
        return None
    variables = list(results.get("variables") or [])
    for f_idx, loadings in enumerate(loadings_per_factor):
        abs_vals = []
        try:
            abs_vals = [abs(float(v)) for v in loadings]
        except Exception:
            continue
        if len(abs_vals) < 2:
            continue
        max_v = max(abs_vals)
        min_nonzero = min(v for v in abs_vals if v > 1e-6) if any(v > 1e-6 for v in abs_vals) else 0
        if min_nonzero <= 0:
            continue
        if max_v / min_nonzero <= 5:
            continue
        dom_idx = abs_vals.index(max_v)
        dom_name = variables[dom_idx] if dom_idx < len(variables) else f"series {dom_idx+1}"
        return (
            f"Factor {f_idx+1} is loaded asymmetrically — '{dom_name}' dominates "
            f"with |loading|={max_v:.2f} while the smallest non-zero loading is "
            f"{min_nonzero:.2f} (ratio > 5×). The factor behaves close to a "
            f"proxy for '{dom_name}'; consider whether a univariate model on "
            f"that series would be more informative."
        )
    return None


def _trigger_idiosyncratic_ar_on_many_series(results: dict) -> Optional[str]:
    err_order = int(results.get("error_order", 0) or 0)
    n_vars = int(results.get("n_variables", 0))
    if err_order <= 0 or n_vars < 4:
        return None
    return (
        f"Idiosyncratic AR dynamics are enabled (error_order={err_order}) on "
        f"{n_vars} series; this relaxes the strict-factor assumption. If the "
        f"EM algorithm had convergence issues, the idiosyncratic AR terms may "
        f"be compensating for true cross-sectional residual correlation rather "
        f"than modeling series-specific persistence."
    )


SPEC = InterpretationSpec(
    technique_id="dynamic_factor_model",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        _trigger_low_variance_explained,
        _trigger_dominant_loading_asymmetry,
        _trigger_idiosyncratic_ar_on_many_series,
    ),
    mode_aware=False,
)

register(SPEC)
