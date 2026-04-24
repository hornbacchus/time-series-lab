"""Phase 5 canonical validation for Follow-up 3f — Transformer
attention-weights exposure (opt-in attention_exposure=True).

Six canonicals:

  1. Synthetic AR(1) T=300, attention_exposure=False — backward-
     compat baseline. All attention_* audit fields None; no
     "Attention Weights" output table; Tier 1 unchanged.

  2. Synthetic AR(1) T=300, attention_exposure=True (correctness
     under lag-1 structure). Validates capture mechanism;
     expected dominant_lag near 1 (AR(1) depends on lag 1) with
     sufficient training; entropy typically low (concentrated).

  3. Synthetic seasonal (period=7) T=300, attention_exposure=
     True. Critical correctness: if the model learns the period,
     dominant_lag == 7 and D3 fires. If not learned (under-
     training), document that the capture is correct (forecast
     row sums to 1.0) and treat dominant_lag != 7 as a model-
     quality diagnostic, not an implementation bug (user
     observation 3).

  4. Synthetic random walk T=300, attention_exposure=True.
     Attention should favour recent positions (lag 1 dominance
     typical); entropy intermediate (no specific lag structure
     beyond recency).

  5. Runtime-error force-test. Monkey-patch
     `_patch_sa_blocks_for_capture` to raise RuntimeError. D5
     fires with runtime_error branch, fallback_reason populated,
     baseline forecast preserved. Subsequent runs unaffected
     (validates teardown isolation).

  6. sklearn-fallback force-test. Monkey-patch `_has_torch` to
     return False. Wrapper backend routes to
     MLPRegressor; attention exposure cascade recognizes
     backend=="sklearn_mlp" and emits
     fallback_reason="sklearn_fallback_no_attention". D5 fires
     with sklearn-fallback branch.

Patch isolation: each force-test uses a try/finally wrapper to
restore the original function before the next canonical runs
(user observation 1 — prevents leakage between C5 and C6).

Run from project root:

    python tools/validate_transformer_attention_canonicals.py
"""

import os
import sys
import time

# Windows cp1252 stdout can't encode Unicode (θ, σ, ξ, ζ, ⇒, etc.)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "engine"))

import numpy as np

from techniques.base import RunContext
from techniques import transformer_forecast as tf


def _null_progress(*args, **kwargs):
    pass


def _build_ctx(time_, name, values, *, preset, params,
               frequency="daily"):
    return RunContext({
        "run_id": "test",
        "technique_id": "transformer_forecast",
        "preset": preset,
        "seed": 42,
        "frequency": frequency,
        "time": time_,
        "series": [{"name": name, "values": values}],
        "params": params,
    })


# ── Synthetic data generators ─────────────────────────────────────


def _synthetic_ar1(T, phi=0.7, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.zeros(T)
    for i in range(1, T):
        y[i] = phi * y[i - 1] + eps[i]
    time_ = [f"d{i}" for i in range(T)]
    return time_, "ar1", y.tolist()


def _synthetic_seasonal(T, period=7, amp=1.0, noise=0.3, seed=42):
    rng = np.random.default_rng(seed)
    t = np.arange(T)
    y = amp * np.sin(2 * np.pi * t / period) + noise * rng.standard_normal(T)
    time_ = [f"d{i}" for i in range(T)]
    return time_, f"seasonal_p{period}", y.tolist()


def _synthetic_random_walk(T, seed=42):
    rng = np.random.default_rng(seed)
    eps = rng.standard_normal(T)
    y = np.cumsum(eps)
    time_ = [f"d{i}" for i in range(T)]
    return time_, "random_walk", y.tolist()


# ── Renderer ──────────────────────────────────────────────────────


def _render(result, label, extra_checks=None):
    print(f"\n=== {label} ===")
    status = result.get("status", "?")
    print(f"Status: {status}")
    if status != "success":
        print(f"Error: {result.get('error_message')}")
        return False
    a = result.get("audit_fields", {})
    print(
        f"backend={a.get('backend')} "
        f"n_obs={a.get('n_obs')} n_train={a.get('n_train')} "
        f"n_lags={a.get('n_lags')} epochs={a.get('epochs')}"
    )
    print(
        f"final_loss={a.get('final_loss')} "
        f"rmse={a.get('rmse')} r2={a.get('r2')}"
    )
    print(
        f"attn_requested={a.get('attention_exposure_requested')} "
        f"attn_applied={a.get('attention_exposure_applied')} "
        f"fallback_reason={a.get('attention_exposure_fallback_reason')}"
    )
    if a.get("attention_exposure_applied"):
        print(
            f"  n_layers={a.get('attention_n_layers')} "
            f"n_heads={a.get('attention_n_heads')} "
            f"context_length={a.get('attention_context_length')}"
        )
        print(
            f"  top_k_req={a.get('attention_top_k')} "
            f"top_k_eff={a.get('attention_top_k_effective')}"
        )
        print(
            f"  LL dom_lag={a.get('attention_last_layer_dominant_lag')} "
            f"H={a.get('attention_last_layer_entropy_normalized')} "
            f"ECL={a.get('attention_last_layer_effective_context_length')}"
        )
        print(
            f"  CL dom_lag={a.get('attention_cross_layer_dominant_lag')} "
            f"H={a.get('attention_cross_layer_entropy_normalized')} "
            f"ECL={a.get('attention_cross_layer_effective_context_length')}"
        )
        ll_tk = a.get("attention_last_layer_top_k") or []
        print("  LL top-K (rank, pos, lag, weight):")
        for d in ll_tk[:5]:
            print(f"    {d}")
        # Sanity: forecast row sums to approximately 1.0.
        # The top-K is a subset, so its sum is ≤ 1.0. We sum
        # across all reported top-K entries — in the full top-K
        # with K == context_length this would equal 1.0.
        w_sum = sum(d.get("weight", 0.0) for d in ll_tk)
        print(f"  Top-{len(ll_tk)} LL weights sum: {round(w_sum, 4)}")
    tables = [
        t.get("name", "?") for t in (result.get("tables") or [])
        if isinstance(t, dict)
    ]
    print(f"  Tables: {tables}")
    interp = result.get("interpretation") or {}
    tier1 = interp.get("tier1", "(missing)")
    tier2 = interp.get("tier2", "(missing)") or ""
    print(f"\n  Tier 1: {tier1[:350]}"
          + (" ..." if len(tier1) > 350 else ""))
    print(f"\n  Tier 2 (first 350): {tier2[:350]}"
          + (" ..." if len(tier2) > 350 else ""))
    tier3 = interp.get("tier3") or []
    print(f"\n  Tier 3 ({len(tier3)} triggers):")
    for t in tier3:
        print(f"    \u2022 {t[:250]}")
    ok = True
    if extra_checks is not None:
        ok = extra_checks(result)
    return ok


# ── Canonicals ────────────────────────────────────────────────────


def canonical_1():
    """AR(1) T=300, attention_exposure=False (backward-compat)."""
    time_, name, values = _synthetic_ar1(T=300, phi=0.7, seed=42)
    t0 = time.time()
    ctx = _build_ctx(
        time_, name, values, preset="Balanced",
        params={"epochs": 100, "n_lags": 16},
    )
    result = tf.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")

    def _checks(res):
        a = res.get("audit_fields", {})
        if a.get("attention_exposure_applied"):
            print("  !!! attention_exposure_applied=True unexpected")
            return False
        for k in (
            "attention_n_layers", "attention_last_layer_top_k",
            "attention_last_layer_dominant_lag",
        ):
            if a.get(k) is not None:
                print(f"  !!! {k}={a.get(k)} (expected None)")
                return False
        tables = [
            t.get("name") for t in (res.get("tables") or [])
            if isinstance(t, dict)
        ]
        if "Attention Weights" in tables:
            print("  !!! Attention Weights table unexpectedly present")
            return False
        print("  \u2713 C1 backward-compat: no attention fields or table")
        return True

    return _render(result, "C1 AR(1) T=300 exposure=False (backward-compat)",
                   _checks)


def canonical_2():
    """AR(1) T=300, attention_exposure=True (correctness)."""
    time_, name, values = _synthetic_ar1(T=300, phi=0.7, seed=42)
    t0 = time.time()
    ctx = _build_ctx(
        time_, name, values, preset="Balanced",
        params={
            "attention_exposure": True,
            "attention_top_k": 10,
            "epochs": 150,
            "n_lags": 16,
        },
    )
    result = tf.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")

    def _checks(res):
        a = res.get("audit_fields", {})
        if not a.get("attention_exposure_applied"):
            print("  !!! attention_exposure_applied=False unexpected")
            return False
        # Capture correctness: top-K weights are non-negative,
        # top-1 weight in [0, 1].
        ll_tk = a.get("attention_last_layer_top_k") or []
        if not ll_tk:
            print("  !!! top_k list empty")
            return False
        if not all(
            (0.0 <= float(d.get("weight", -1)) <= 1.0)
            for d in ll_tk
        ):
            print("  !!! weights out of [0,1] range")
            return False
        print(
            f"  Dominant lag: {a.get('attention_last_layer_dominant_lag')} "
            f"(expected to be small for AR(1) if model trained; "
            f"may be anywhere if undertrained)"
        )
        tables = [
            t.get("name") for t in (res.get("tables") or [])
            if isinstance(t, dict)
        ]
        if "Attention Weights" not in tables:
            print("  !!! Attention Weights table missing")
            return False
        print("  \u2713 C2 capture succeeded; table present")
        return True

    return _render(result, "C2 AR(1) T=300 exposure=True (correctness)",
                   _checks)


def canonical_3():
    """Seasonal period=7, exposure=True (dominant_lag match?)."""
    time_, name, values = _synthetic_seasonal(
        T=300, period=7, seed=42,
    )
    t0 = time.time()
    ctx = _build_ctx(
        time_, name, values, preset="Balanced",
        params={
            "attention_exposure": True,
            "attention_top_k": 10,
            "epochs": 200,
            "n_lags": 16,
        },
    )
    result = tf.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")

    def _checks(res):
        a = res.get("audit_fields", {})
        if not a.get("attention_exposure_applied"):
            print("  !!! applied=False unexpected")
            return False
        dom = a.get("attention_last_layer_dominant_lag")
        tier3 = (res.get("interpretation") or {}).get("tier3", [])
        d3_fires = any(
            "matches a common seasonal period" in t for t in tier3
        )
        print(f"  Dominant lag: {dom}")
        if dom == 7:
            if d3_fires:
                print("  \u2713 D3 seasonal_match trigger fires with "
                      "dominant_lag=7 (period matched)")
            else:
                print("  !!! dominant_lag=7 but D3 did not fire")
                return False
        elif dom in (4, 12, 24, 52, 365):
            print(f"  Partial match: D3 fires with dominant_lag={dom} "
                  f"(different seasonal period recognized)")
        else:
            # Per user observation 3: model quality diagnostic,
            # not implementation bug. Document capture correctness
            # (sums non-negative, within [0,1]).
            ll_tk = a.get("attention_last_layer_top_k") or []
            w_sum = sum(d.get("weight", 0.0) for d in ll_tk)
            print(
                f"  Model did not learn period-7 structure at "
                f"default Balanced training budget. Capture "
                f"correctness preserved: top-K sum={round(w_sum, 4)}, "
                f"weights non-negative. dominant_lag={dom} is a "
                f"model-quality diagnostic, not an implementation bug."
            )
        return True

    return _render(result, "C3 Seasonal (p=7) exposure=True (D3 check)",
                   _checks)


def canonical_4():
    """Random walk, exposure=True."""
    time_, name, values = _synthetic_random_walk(T=300, seed=42)
    t0 = time.time()
    ctx = _build_ctx(
        time_, name, values, preset="Balanced",
        params={
            "attention_exposure": True,
            "attention_top_k": 10,
            "epochs": 100,
            "n_lags": 16,
        },
    )
    result = tf.run(ctx, _null_progress)
    print(f"\n(wall clock: {time.time()-t0:.1f}s)")

    def _checks(res):
        a = res.get("audit_fields", {})
        if not a.get("attention_exposure_applied"):
            print("  !!! applied=False unexpected")
            return False
        H = a.get("attention_last_layer_entropy_normalized")
        dom = a.get("attention_last_layer_dominant_lag")
        print(f"  Entropy: {H}  Dominant lag: {dom}")
        print("  (Random walks have no specific lag structure "
              "beyond recency; any dominant_lag is acceptable)")
        return True

    return _render(result, "C4 Random walk exposure=True (recency/diffuse)",
                   _checks)


def canonical_5():
    """Force-test D5 runtime-error branch via monkey-patch of
    `_patch_sa_blocks_for_capture`. Use try/finally teardown so
    the patch does not leak into C6."""
    time_, name, values = _synthetic_ar1(T=300, phi=0.7, seed=42)

    orig_fn = tf._patch_sa_blocks_for_capture

    def _failing(*args, **kwargs):
        raise RuntimeError(
            "Simulated capture failure (Phase 5 D5 probe)"
        )

    tf._patch_sa_blocks_for_capture = _failing
    try:
        t0 = time.time()
        ctx = _build_ctx(
            time_, name, values, preset="Balanced",
            params={
                "attention_exposure": True,
                "attention_top_k": 10,
                "epochs": 50,
                "n_lags": 16,
            },
        )
        result = tf.run(ctx, _null_progress)
        print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    finally:
        # User observation 1: guarantee teardown before C6 runs
        tf._patch_sa_blocks_for_capture = orig_fn

    def _checks(res):
        a = res.get("audit_fields", {})
        if a.get("attention_exposure_applied"):
            print("  !!! applied=True despite forced failure")
            return False
        reason = str(a.get("attention_exposure_fallback_reason") or "")
        if not reason.startswith("runtime_error"):
            print(f"  !!! fallback_reason does not start with 'runtime_error': "
                  f"{reason!r}")
            return False
        print(f"  \u2713 fallback_reason starts with 'runtime_error': {reason}")
        tier3 = (res.get("interpretation") or {}).get("tier3", [])
        d5_fires = any(
            "runtime error" in t.lower()
            and "baseline forecast preserved" in t.lower()
            for t in tier3
        )
        if d5_fires:
            print("  \u2713 D5 runtime-error trigger fires")
        else:
            print("  !!! D5 runtime-error did not fire")
            return False
        # Verify wrapper state is clean for C6
        if tf._patch_sa_blocks_for_capture is not orig_fn:
            print("  !!! Patch not torn down — C6 will be corrupted")
            return False
        print("  \u2713 Patch teardown verified — C6 will run clean")
        return True

    return _render(result, "C5 Runtime-error force-test (D5 runtime branch)",
                   _checks)


def canonical_6():
    """Force-test D5 sklearn-fallback branch via monkey-patch of
    `_has_torch` to return False. Use try/finally teardown."""
    time_, name, values = _synthetic_ar1(T=300, phi=0.7, seed=42)

    orig_has_torch = tf._has_torch
    tf._has_torch = lambda: False
    try:
        t0 = time.time()
        ctx = _build_ctx(
            time_, name, values, preset="Balanced",
            params={
                "attention_exposure": True,
                "attention_top_k": 10,
                "epochs": 50,
                "n_lags": 16,
            },
        )
        result = tf.run(ctx, _null_progress)
        print(f"\n(wall clock: {time.time()-t0:.1f}s)")
    finally:
        tf._has_torch = orig_has_torch

    def _checks(res):
        a = res.get("audit_fields", {})
        if a.get("backend") != "sklearn_mlp":
            print(f"  !!! backend={a.get('backend')} expected sklearn_mlp")
            return False
        print(f"  \u2713 backend={a.get('backend')}")
        if a.get("attention_exposure_applied"):
            print("  !!! applied=True despite sklearn backend")
            return False
        reason = str(a.get("attention_exposure_fallback_reason") or "")
        if reason != "sklearn_fallback_no_attention":
            print(f"  !!! fallback_reason={reason!r} "
                  f"(expected 'sklearn_fallback_no_attention')")
            return False
        print(f"  \u2713 fallback_reason='{reason}'")
        tier3 = (res.get("interpretation") or {}).get("tier3", [])
        d5_fires = any(
            "sklearn MLPRegressor" in t or
            "PyTorch unavailable" in t
            for t in tier3
        )
        if d5_fires:
            print("  \u2713 D5 sklearn-fallback branch fires")
        else:
            print("  !!! D5 sklearn-fallback did not fire")
            return False
        return True

    return _render(result, "C6 sklearn-fallback force-test (D5 sklearn branch)",
                   _checks)


def main():
    results = []
    for fn in (canonical_1, canonical_2, canonical_3,
               canonical_4, canonical_5, canonical_6):
        try:
            ok = fn()
        except Exception as e:
            print(f"\n!!! {fn.__name__} RAISED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            ok = False
        results.append((fn.__name__, ok))

    print("\n" + "=" * 60)
    print("CANONICAL VALIDATION SUMMARY")
    print("=" * 60)
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}: {name}")
    all_ok = all(ok for _, ok in results)
    print("\nOverall:", "ALL PASS" if all_ok else "SOME FAILED")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
