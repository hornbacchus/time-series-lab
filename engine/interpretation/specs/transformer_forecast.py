"""
InterpretationSpec for transformer_forecast (neural sequence cohort).

Transformer encoder applied to a lag window.

Follow-up 3f: opt-in ``attention_exposure=True`` captures per-layer
attention weights during the t+1 forecast forward pass and exposes
two views (last-layer and cross-layer mean) with top-K ranked
forecast-position attention plus summary statistics (normalized
Shannon entropy, effective context length, dominant lag). Tier 1
gains a closer when applied (dominant lag + ECL + entropy band);
Tier 2 gains a methodology block (capture mechanism, two views,
summary-stat interpretation); Tier 2 also gains a fallback-
disclosure block when requested but not applied (sklearn_fallback
branch or runtime-error branch). Five new Tier 3 triggers (D1-D5)
cover highly-concentrated, highly-diffuse, seasonal-match,
layer-disagreement, and runtime-error / sklearn-fallback cases.

Results-dict keys consumed for attention exposure:

    attention_exposure_requested / attention_exposure_applied
    attention_exposure_fallback_reason
    attention_n_layers / attention_n_heads
    attention_context_length
    attention_top_k / attention_top_k_effective
    attention_last_layer_top_k (list of dicts)
    attention_cross_layer_top_k (list of dicts)
    attention_last_layer_entropy_normalized
    attention_last_layer_effective_context_length
    attention_last_layer_dominant_lag
    attention_cross_layer_entropy_normalized
    attention_cross_layer_effective_context_length
    attention_cross_layer_dominant_lag
"""

from typing import Optional

from interpretation.builder import InterpretationSpec
from interpretation.registry import register
from interpretation.specs._neural_sequence_common import (
    render_neural_tier1,
    render_neural_tier2_common,
    trigger_insufficient_neural_training,
    trigger_neural_convergence_not_reached,
    trigger_params_exceed_training_samples,
    trigger_backend_fallback_neural,
)

PRESET_GATED_KEYS = ()


# Follow-up 3f: seasonal-lag set for D3 ``dominant_lag_matches_
# seasonal`` trigger. Matches the wrapper's ``_SEASONAL_LAGS``.
_SEASONAL_LAGS = (4, 7, 12, 24, 52, 365)


def _entropy_band(H):
    """Classify normalized entropy into concentrated / balanced /
    diffuse bands. Returns a short adjective."""
    try:
        h = float(H)
    except Exception:
        return "unknown"
    if h < 0.3:
        return "concentrated"
    if h > 0.8:
        return "diffuse"
    return "balanced"


def _tier1(results: dict) -> str:
    d_model = int(results.get("d_model", 0) or 0)
    heads = int(results.get("n_heads", 0) or 0)
    enc_layers = int(results.get("n_encoder_layers", 0) or 0)
    dim_ff = int(results.get("dim_feedforward", 0) or 0)
    n_params = results.get("n_params")
    params_note = f", {int(n_params)} total parameters" if n_params else ""
    arch_desc = (
        f"Architecture: d_model={d_model}, {heads} attention head(s), "
        f"{enc_layers} encoder layer(s), feed-forward dim={dim_ff}"
        f"{params_note}"
    )
    base_tier1 = render_neural_tier1("Transformer", results, arch_desc)

    # Follow-up 3f: append closer when attention exposure applied.
    if bool(results.get("attention_exposure_applied", False)):
        try:
            dom = results.get("attention_last_layer_dominant_lag")
            ecl = results.get(
                "attention_last_layer_effective_context_length"
            )
            H = results.get(
                "attention_last_layer_entropy_normalized"
            )
            ll_topk = results.get("attention_last_layer_top_k") or []
            top_w = (
                float(ll_topk[0].get("weight"))
                if ll_topk and ll_topk[0].get("weight") is not None
                else None
            )
            H_str = f"{float(H):.3f}" if H is not None else "n/a"
            band = _entropy_band(H) if H is not None else "unknown"
            ecl_str = (
                f"{float(ecl):.1f}" if ecl is not None else "n/a"
            )
            w_str = (
                f"weight {top_w:.3f}" if top_w is not None
                else "weight n/a"
            )
            dom_str = str(int(dom)) if dom is not None else "n/a"
            base_tier1 = base_tier1 + (
                f" Last-layer attention dominantly on lag {dom_str} "
                f"({w_str}); effective context length {ecl_str} "
                f"steps; normalized entropy {H_str} ({band})."
            )
        except Exception:
            pass

    return base_tier1


def _tier2(results: dict) -> str:
    arch_note = (
        "Transformer encoder applied to a lag window. Self-attention "
        "computes weighted averages of past timesteps via learned "
        "query / key / value projections."
    )

    # Follow-up 3f: methodology block when attention exposure applied.
    attn_clause = ""
    if bool(results.get("attention_exposure_applied", False)):
        try:
            n_layers = results.get("attention_n_layers")
            n_heads = results.get("attention_n_heads")
            L = results.get("attention_context_length")
            K_eff = results.get("attention_top_k_effective")
            K_req = results.get("attention_top_k")
            clip_note = ""
            if K_req is not None and K_eff is not None:
                try:
                    if int(K_req) != int(K_eff):
                        clip_note = (
                            f" (clipped to context length from "
                            f"requested {int(K_req)})"
                        )
                except Exception:
                    pass
            ll_dom = results.get("attention_last_layer_dominant_lag")
            cl_dom = results.get("attention_cross_layer_dominant_lag")
            ll_H = results.get(
                "attention_last_layer_entropy_normalized"
            )
            cl_H = results.get(
                "attention_cross_layer_entropy_normalized"
            )
            ll_H_str = (
                f"{float(ll_H):.3f}" if ll_H is not None else "n/a"
            )
            cl_H_str = (
                f"{float(cl_H):.3f}" if cl_H is not None else "n/a"
            )
            ll_dom_str = (
                str(int(ll_dom)) if ll_dom is not None else "n/a"
            )
            cl_dom_str = (
                str(int(cl_dom)) if cl_dom is not None else "n/a"
            )
            attn_clause = (
                f" Attention exposure (Follow-up 3f): captured per-"
                f"layer attention weights via a forward-hook + "
                f"_sa_block patch that forces need_weights=True, "
                f"average_attn_weights=True across {n_layers} encoder "
                f"layer(s), {n_heads} head(s) (head-averaged), over a "
                f"context length of {L} steps (= the n_lags "
                f"parameter). Two views reported in the Attention "
                f"Weights output table: last-layer (most directly "
                f"responsible for prediction) and cross-layer mean "
                f"(aggregate pattern). Forecast-position row "
                f"extracted — what past positions drive the t+1 "
                f"prediction; top-{K_eff} positions{clip_note} "
                f"tabulated. Summary statistics: normalized Shannon "
                f"entropy (H / log(L), low \u21d2 concentrated, "
                f"high \u21d2 diffuse); effective context length "
                f"(\u03a3 lag_i \u00b7 w_i, how far back attention "
                f"extends on average); dominant lag (argmax). Last-"
                f"layer dominant lag = {ll_dom_str} (H = {ll_H_str}); "
                f"cross-layer dominant lag = {cl_dom_str} "
                f"(H = {cl_H_str})."
            )
        except Exception:
            attn_clause = ""

    # Follow-up 3f: fallback disclosure when requested but not
    # applied — branches on sklearn_fallback vs runtime_error.
    fallback_clause = ""
    if (bool(results.get("attention_exposure_requested", False))
            and not bool(
                results.get("attention_exposure_applied", False)
            )):
        reason = str(
            results.get("attention_exposure_fallback_reason") or ""
        )
        if reason == "sklearn_fallback_no_attention":
            fallback_clause = (
                " Attention exposure was requested but the backend "
                "is sklearn MLPRegressor (PyTorch unavailable); "
                "attention weights are not defined for the fallback "
                "architecture. Baseline forecast preserved."
            )
        elif reason.startswith("runtime_error"):
            fallback_clause = (
                f" Attention exposure was requested but raised an "
                f"unexpected runtime error ({reason}). Baseline "
                f"forecast preserved."
            )

    arch_note = arch_note + attn_clause + fallback_clause
    if not attn_clause and not fallback_clause:
        # When attention exposure is not active at all (default
        # opt-out), preserve the pre-3f honest-disclosure pointer
        # that points users at the new opt-in feature.
        arch_note = arch_note + (
            " Attention weights can be extracted as an "
            "interpretability axis via the opt-in "
            "attention_exposure=True parameter — see the Attention "
            "Weights output table and Tier 3 triggers for details."
        )
    return render_neural_tier2_common(
        results, "Transformer sequence forecaster", arch_note,
    )


def _trigger_backend(results: dict) -> Optional[str]:
    return trigger_backend_fallback_neural(results)


# ── Follow-up 3f Tier 3 triggers (D1-D5) ───────────────────────────


def _trigger_attention_highly_concentrated(
    results: dict,
) -> Optional[str]:
    """D1 (3f) — last-layer normalized entropy < 0.3."""
    if not bool(results.get("attention_exposure_applied", False)):
        return None
    H = results.get("attention_last_layer_entropy_normalized")
    if H is None:
        return None
    try:
        h = float(H)
    except Exception:
        return None
    if h >= 0.3:
        return None
    return (
        f"Last-layer attention is highly concentrated (normalized "
        f"entropy {h:.3f} < 0.3): the model relies on very few "
        f"past positions for its prediction. This may indicate "
        f"spurious reliance on specific lags, insufficient model "
        f"capacity, or genuine lag-dominance (e.g., AR(1) "
        f"structure). Inspect the Attention Weights table to "
        f"confirm which positions dominate."
    )


def _trigger_attention_highly_diffuse(
    results: dict,
) -> Optional[str]:
    """D2 (3f) — last-layer normalized entropy > 0.8."""
    if not bool(results.get("attention_exposure_applied", False)):
        return None
    H = results.get("attention_last_layer_entropy_normalized")
    if H is None:
        return None
    try:
        h = float(H)
    except Exception:
        return None
    if h <= 0.8:
        return None
    return (
        f"Last-layer attention is highly diffuse (normalized "
        f"entropy {h:.3f} > 0.8): the model spreads attention "
        f"nearly uniformly across past positions. This may "
        f"indicate an undertrained model, near-random "
        f"initialization, or a series with no strong lag "
        f"structure. Consider increasing epochs or inspecting the "
        f"training-loss curve before trusting the forecast."
    )


def _trigger_dominant_lag_matches_seasonal(
    results: dict,
) -> Optional[str]:
    """D3 (3f) — informational: dominant lag matches common
    seasonal period."""
    if not bool(results.get("attention_exposure_applied", False)):
        return None
    dom = results.get("attention_last_layer_dominant_lag")
    if dom is None:
        return None
    try:
        d = int(dom)
    except Exception:
        return None
    if d not in _SEASONAL_LAGS:
        return None
    # Informative label for the matched period
    labels = {
        4: "quarterly",
        7: "weekly",
        12: "monthly (or annual monthly)",
        24: "daily hourly (or bi-annual)",
        52: "annual weekly",
        365: "annual daily",
    }
    label = labels.get(d, "seasonal")
    return (
        f"Last-layer dominant attention lag = {d}, which matches "
        f"a common seasonal period ({label}). The model may have "
        f"learned seasonal structure at this lag. Informational "
        f"only — confirm against the series' known seasonality."
    )


def _trigger_last_layer_cross_layer_disagreement(
    results: dict,
) -> Optional[str]:
    """D4 (3f) — top-1 position differs between last-layer and
    cross-layer views (strict exact-position match, per Q7)."""
    if not bool(results.get("attention_exposure_applied", False)):
        return None
    ll = results.get("attention_last_layer_top_k") or []
    cl = results.get("attention_cross_layer_top_k") or []
    if not ll or not cl:
        return None
    try:
        ll_top_pos = int(ll[0]["position"])
        cl_top_pos = int(cl[0]["position"])
    except Exception:
        return None
    if ll_top_pos == cl_top_pos:
        return None
    try:
        ll_lag = int(ll[0].get("lag", -1))
        cl_lag = int(cl[0].get("lag", -1))
    except Exception:
        return None
    return (
        f"Last-layer top-1 attention (position {ll_top_pos}, "
        f"lag {ll_lag}) differs from cross-layer mean top-1 "
        f"(position {cl_top_pos}, lag {cl_lag}). The final layer "
        f"uses different information than earlier layers on "
        f"average. Research-relevant — may indicate specialized "
        f"final-layer processing or noisy lower-layer attention."
    )


def _trigger_attention_exposure_runtime_error(
    results: dict,
) -> Optional[str]:
    """D5 (3f) — exposure requested but cascade declined.
    Branches: sklearn_fallback_no_attention vs runtime_error."""
    if not bool(results.get("attention_exposure_requested", False)):
        return None
    if bool(results.get("attention_exposure_applied", False)):
        return None
    reason = str(
        results.get("attention_exposure_fallback_reason") or ""
    )
    if reason == "sklearn_fallback_no_attention":
        return (
            "Attention exposure was requested but the wrapper fell "
            "back to the sklearn MLPRegressor backend (PyTorch "
            "unavailable on this system). Attention weights are "
            "not defined for the MLP architecture; baseline "
            "forecast preserved. Install PyTorch to enable."
        )
    if reason.startswith("runtime_error"):
        return (
            f"Attention exposure was requested but raised an "
            f"unexpected runtime error ({reason}). Baseline "
            f"forecast preserved; please report a reproducible "
            f"example."
        )
    return None


SPEC = InterpretationSpec(
    technique_id="transformer_forecast",
    tier1_builder=_tier1,
    tier2_builder=_tier2,
    tier3_triggers=(
        # C7 legacy triggers
        _trigger_backend,
        trigger_insufficient_neural_training,
        trigger_neural_convergence_not_reached,
        trigger_params_exceed_training_samples,
        # Follow-up 3f D1-D5
        _trigger_attention_highly_concentrated,
        _trigger_attention_highly_diffuse,
        _trigger_dominant_lag_matches_seasonal,
        _trigger_last_layer_cross_layer_disagreement,
        _trigger_attention_exposure_runtime_error,
    ),
    mode_aware=False,
)

register(SPEC)
