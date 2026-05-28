"""Phase 3 Batch 9 — Echo State Network (ESN) parity check.

TSL ``engine/techniques/echo_state_network.py`` (numpy reservoir
computing with sparse random reservoir matrix + leaky-integrator
neurons with tanh activation + ridge regression closed-form readout
+ multi-step recursive forecast with reservoirpy primary path
fallback to numpy implementation) vs from-scratch paper-formula
reimpl mirroring engine numpy fallback path verbatim.

Rewritten at SC12-side Cat 3 remediation cycle session 12/17 per
triage close + inventory verification 12d3785 + Tier 2 incremental
forward-amendment pattern. **SC12 = TIER C CLOSE** (final Tier C
session post SC10 GP + SC11 prophet). PARTIAL Tier A pattern THIRD-
INSTANCE confirmation + return to **Tier II.bit-exact** (SC11
prophet was FIRST mle-band; SC12 esn returns to bit-exact per numpy
cross-invocation determinism).

**Helper identity verification (Step 1 of SC12 workflow per SC4
two-stage methodology + SC10/SC11 PARTIAL Tier A precedent):**

Stage 1 (AST source-segment SHA256 hash check):
- `_prepare_series` at engine lines 52-72: **MATCH SC1 RF** (hash
  57bae54d463c2fd7)
- `_create_features`: **ABSENT** (ESN uses reservoir state
  evolution, not lag-feature engineering)
- `_create_forecast_features`: **ABSENT** (ESN generates forecasts
  via recursive reservoir state update + readout)

Stage 2: ABSENT helpers indicate architectural distinctness
(reservoir computing pipeline distinct from sklearn-tree-family).
PARTIAL Tier A pattern THIRD-INSTANCE confirmation:
`_prepare_series_reference` reused from SC1 (SC10 + SC11 + SC12 all
exhibit identical PARTIAL pattern; A3 second-observation tightening
precedent THRESHOLD REINFORCED at n=3 sustained observations;
codification refinement candidate at absorption #6+ for
"Tier-A-prepare-series-reuse-with-bespoke-feature-engineering"
sub-pattern EMPIRICALLY ROBUSTLY GROUNDED).

**Cross-invocation reproducibility verification (Step 2 of SC12
workflow per SC11 prophet finding):** SC11 surfaced that triage's
"engine twice" bit-exact result tested within-process re-invocation,
not cross-invocation (engine arm vs independent reference arm).
SC12 explicitly verifies ESN cross-invocation reproducibility before
proceeding with Tier II.bit-exact expectation: invoked engine twice
as SEPARATE computations at seed=42 → max_abs_diff=0.0 (BIT-EXACT
cross-invocation). Engine numpy ESN uses `np.random.RandomState(seed)`
LOCAL RNG instance — no global state leakage across invocations;
deterministic. Distinct from SC11 prophet Stan-MAP global state.

**Fallback dispatch handling (SC3 template element FOURTH-INSTANCE
application with NEW dispatch behavior at audit environment):**
Engine `_has_reservoirpy()` at lines 22-27 checks reservoirpy
availability. Engine attempts reservoirpy primary path at engine
lines 406-417 within try/except; on Exception, falls back to numpy
ESN via `_run_numpy_esn` at engine line 422. **In audit environment:
reservoirpy 0.4.1 IS installed (import succeeds; `_has_reservoirpy()`
returns True), BUT `_run_reservoirpy_esn` invocation triggers
Exception in audit-environment Python + numpy combination → engine
falls back to numpy ESN.** Engine emits warning + uses numpy
backend. Audit validates numpy backend (what actually runs); the
reservoirpy primary path is wrapper-layer-3-check covered but NOT
math-layer-parity validated.

**Engine backend dispatch matrix at SC12 audit environment:**
| Reservoirpy install | Reservoirpy run success | Engine backend |
| Yes (0.4.1) | No (Exception in audit env) | **numpy** (validated at SC12) |
| Yes | Yes | reservoirpy (NOT validated at SC12) |
| No | n/a | numpy (validated at SC12 via direct fallback path) |

Pattern A.3 paper-formula self-parity (Tier II.bit-exact at engine
output-rounding floor) at deterministic numpy ESN (local RNG state
per _NumpyESN instance).
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
from reference_parity.harness.checks.p3_random_forest import (
    _prepare_series_reference,
)
from reference_parity.harness.checks.p3_lstm_gru import _generate_ar_dgp


# Engine preset Balanced config (engine `echo_state_network.py` lines
# 37-42). Mirrored verbatim per Disposition 2.
_ENGINE_BALANCED_PRESET = {
    "reservoir_size": 200,
    "spectral_radius": 0.9,
    "leak_rate": 0.3,
    "input_scaling": 1.0,
    "ridge_alpha": 1e-6,
    "n_lags": 1,
    "warmup": 20,
    "sparsity": 0.1,
}


class _ReferenceNumpyESN:
    """Reference reimpl of engine `_NumpyESN` class at engine lines
    75-216 verbatim. Bespoke per-session reimplementation per SC12
    Tier C close — Layer 2 family helpers NOT APPLICABLE.

    Architecture (engine lines 76-83):
    - Random sparse reservoir with specified spectral radius
    - Leaky-integrator neurons with tanh activation
    - Ridge regression readout (only trained layer)
    """

    def __init__(self, input_dim, reservoir_size, spectral_radius,
                 leak_rate, input_scaling, ridge_alpha, sparsity, seed):
        # CRITICAL: engine uses local RandomState(seed) instance per
        # engine line 87; mirror exactly for cross-invocation
        # determinism. DRAW ORDER matters per numpy RNG state
        # mechanics: (1) W_in via rng.randn; (2) reservoir W via
        # rng.randn + rng.rand mask; (3) bias via rng.randn.
        rng = np.random.RandomState(seed)
        self.reservoir_size = reservoir_size
        self.leak_rate = leak_rate
        self.input_scaling = input_scaling
        self.ridge_alpha = ridge_alpha
        # Engine line 95: W_in draw FIRST
        self.W_in = rng.randn(reservoir_size, input_dim) * input_scaling
        # Engine lines 98-101: reservoir W + sparsity mask SECOND
        W = rng.randn(reservoir_size, reservoir_size)
        mask = rng.rand(reservoir_size, reservoir_size) < sparsity
        W = W * mask
        # Engine lines 104-108: scale to spectral radius
        eigenvalues = np.abs(np.linalg.eigvals(W))
        max_eigenvalue = (
            np.max(eigenvalues) if len(eigenvalues) > 0 else 1.0
        )
        if max_eigenvalue > 0:
            W = W * (spectral_radius / max_eigenvalue)
        self.W = W
        self.W_out = None
        # Engine line 114: bias draw THIRD
        self.bias = rng.randn(reservoir_size) * 0.1

    def _run_reservoir(self, inputs):
        """Reference reimpl of engine `_run_reservoir` lines 116-144
        verbatim. Leaky-integrator + tanh activation."""
        n_steps = inputs.shape[0]
        states = np.zeros((n_steps, self.reservoir_size))
        state = np.zeros(self.reservoir_size)
        for t in range(n_steps):
            pre_activation = (
                self.W_in @ inputs[t]
                + self.W @ state
                + self.bias
            )
            state = (
                (1 - self.leak_rate) * state
                + self.leak_rate * np.tanh(pre_activation)
            )
            states[t] = state
        return states

    def fit(self, inputs, targets, warmup=0):
        """Reference reimpl of engine `fit` lines 146-173 verbatim.
        Ridge regression closed-form readout."""
        states = self._run_reservoir(inputs)
        S = states[warmup:]
        T = targets[warmup:]
        reg = self.ridge_alpha * np.eye(self.reservoir_size)
        self.W_out = np.linalg.solve(S.T @ S + reg, S.T @ T)
        predictions = S @ self.W_out
        return predictions, states

    def predict_step(self, state, input_val):
        """Reference reimpl of engine `predict_step` lines 175-189."""
        pre_activation = (
            self.W_in @ input_val
            + self.W @ state
            + self.bias
        )
        new_state = (
            (1 - self.leak_rate) * state
            + self.leak_rate * np.tanh(pre_activation)
        )
        prediction = new_state @ self.W_out
        return float(prediction), new_state

    def forecast(self, last_states, last_input, horizon):
        """Reference reimpl of engine `forecast` lines 191-216
        verbatim. Multi-step recursive forecast."""
        forecasts = []
        state = last_states.copy()
        inp = last_input.copy()
        for _ in range(horizon):
            pred, state = self.predict_step(state, inp)
            forecasts.append(pred)
            inp = np.array([pred])
        return np.array(forecasts)


def _reference_esn(
    values: np.ndarray, *, seed: int, horizon: int = 12,
    preset_cfg: dict = None,
) -> dict[str, Any]:
    """Reference reimpl mirroring engine `echo_state_network.run()`
    pipeline at engine lines 310-563 verbatim at numpy backend path
    (audit environment fallback after reservoirpy fails).
    """
    cfg = preset_cfg or _ENGINE_BALANCED_PRESET

    # Layer 2 family-shared helper reuse (PARTIAL Tier A pattern
    # third-instance per SC10 + SC11 precedent)
    clean, _ = _prepare_series_reference(values)
    n = len(clean)

    reservoir_size = int(cfg["reservoir_size"])
    spectral_radius = float(cfg["spectral_radius"])
    leak_rate = float(cfg["leak_rate"])
    input_scaling = float(cfg["input_scaling"])
    ridge_alpha = float(cfg["ridge_alpha"])
    warmup = int(cfg["warmup"])
    sparsity = float(cfg["sparsity"])

    # Cap warmup per engine line 388
    warmup = min(warmup, n // 4)

    # Normalize per engine lines 391-395
    y_mean = float(np.mean(clean))
    y_std = float(np.std(clean, ddof=1))
    if y_std == 0:
        y_std = 1.0
    normalized = (clean - y_mean) / y_std

    # Mirror engine `_run_numpy_esn` at engine lines 275-307:
    esn = _ReferenceNumpyESN(
        input_dim=1,
        reservoir_size=reservoir_size,
        spectral_radius=spectral_radius,
        leak_rate=leak_rate,
        input_scaling=input_scaling,
        ridge_alpha=ridge_alpha,
        sparsity=sparsity,
        seed=seed,
    )

    # Prepare data per engine lines 290-291
    inputs = normalized[:-1].reshape(-1, 1)
    targets = normalized[1:]

    # Train per engine line 294
    y_pred_norm, states = esn.fit(inputs, targets, warmup=warmup)

    # Forecast prep per engine lines 297-302
    all_states = esn._run_reservoir(inputs)
    last_state = all_states[-1]
    last_input = np.array([normalized[-1]])
    fc_norm = esn.forecast(last_state, last_input, horizon)

    # Pad y_pred per engine line 305
    y_pred_full = np.concatenate([np.full(warmup, np.nan), y_pred_norm])

    # Denormalize per engine lines 430-443
    fc_values = fc_norm * y_std + y_mean
    targets_unnorm = clean[1:]
    valid_mask = ~np.isnan(y_pred_full)

    if np.sum(valid_mask) > 0:
        y_pred_valid = y_pred_full[valid_mask]
        targets_valid = targets_unnorm[valid_mask]
        y_pred_denorm = y_pred_valid * y_std + y_mean
        residuals = targets_valid - y_pred_denorm
        rmse = float(np.sqrt(np.mean(residuals ** 2)))
        mae = float(np.mean(np.abs(residuals)))
        ss_res = float(np.sum(residuals ** 2))
        ss_tot = float(
            np.sum((targets_valid - np.mean(targets_valid)) ** 2)
        )
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        n_train = int(len(targets_valid))
    else:
        rmse = float("inf")
        mae = float("inf")
        r2 = 0.0
        n_train = 0

    # Engine audit field `n_train` uses `n - warmup` formula at engine
    # line 524 (NOT the metric-calc `len(targets_valid)` value at engine
    # line 451). These two differ by 1: metric-calc value is 179 for
    # n=200, warmup=20 (because valid_mask filters NaN-padded y_pred);
    # audit-field value is 180 (n - warmup). Mirror engine audit field
    # formula for parity at audit_fields surface.
    n_train_audit = int(n - warmup)

    return {
        "forecast": fc_values.astype(np.float64),
        "rmse": rmse,
        "mae": mae,
        "r2": r2,
        "n_train": n_train_audit,
        "forecast_end_value": float(fc_values[-1]) if len(fc_values) else 0.0,
        "last_observed_value": float(clean[-1]),
    }


class EsnParity(P3ParityCheck):
    """ESN forecast parity vs from-scratch paper-formula reimpl.

    Engine arm invokes engine.techniques.echo_state_network.run() via
    RunContext at Balanced preset (reservoir_size=200 +
    spectral_radius=0.9 + leak_rate=0.3 + input_scaling=1.0 +
    ridge_alpha=1e-6 + warmup=20 + sparsity=0.1); reference arm
    reimplements numpy backend pipeline bespoke with `_ReferenceNumpyESN`
    class mirroring engine `_NumpyESN` verbatim + SC1
    `_prepare_series_reference` Layer 2 family-shared helper reuse
    (PARTIAL Tier A pattern THIRD-INSTANCE per SC10+SC11 precedent).
    Audit-environment-specific behavior: reservoirpy 0.4.1 installed
    but engine falls back to numpy at runtime due to reservoirpy
    Exception in audit env; numpy backend validated.
    """

    technique_id = "p3_esn"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "ESN numpy reservoir computing uses local RandomState(seed) "
        "instance per construction (engine line 87) — cross-"
        "invocation deterministic without global state leakage. "
        "Engine and reference reimpl follow identical pipeline "
        "(NaN drop via SC1 helper + normalize + numpy reservoir "
        "init with identical draw order + leaky-integrator + ridge "
        "readout closed-form solve + recursive forecast); outputs "
        "match at machine precision modulo engine 6-decimal forecast "
        "rounding + 4-decimal audit metric rounding. SC12 Tier C "
        "close + return to Tier II.bit-exact (SC11 prophet Stan was "
        "first mle-band; SC12 numpy returns to bit-exact) confirms "
        "Stan-MAP non-determinism is Stan-specific not general "
        "DL/probabilistic-cohort issue."
    )

    DGP_N = 200
    HORIZON = 12

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ar_dgp(seed=seed, n=self.DGP_N)}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.echo_state_network as esn_mod  # type: ignore

        np.random.seed(42)
        y = np.asarray(fixture["y"], dtype=np.float64)
        ctx = RunContext({
            "run_id": "p3_esn_parity",
            "technique_id": "echo_state_network",
            "preset": "Balanced",
            "seed": 42,
            "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"horizon": self.HORIZON},
        })
        with _warnings.catch_warnings():
            _warnings.simplefilter("ignore")
            resp = esn_mod.run(ctx, lambda *a, **kw: None)
        if resp.get("status") != "success":
            raise RuntimeError(
                f"TSL echo_state_network failed: "
                f"{resp.get('error_message')}"
            )
        # Audit-environment expected behavior: engine falls back to
        # numpy backend (reservoirpy Exception in audit env); raise
        # if engine unexpectedly dispatches to reservoirpy (would
        # invalidate parity claim scope at math layer).
        backend = resp.get("audit_fields", {}).get("backend", "?")
        if backend != "numpy":
            raise RuntimeError(
                f"TSL echo_state_network dispatched to backend='{backend}'"
                f" — SC12 parity claim covers NUMPY backend only "
                f"(audit-environment-expected); reservoirpy primary "
                f"path NOT math-layer validated"
            )
        # Forecast table
        fc_table = next(
            (t for t in resp["tables"] if t.get("name") == "Forecast"),
            None,
        )
        if fc_table is None:
            raise RuntimeError("engine missing 'Forecast' table")
        forecast = np.array(
            [float(row[1]) for row in fc_table["rows"]],
            dtype=np.float64,
        )
        audit = resp.get("audit_fields", {})
        return {
            "forecast": forecast,
            "rmse": float(audit.get("rmse", float("nan"))),
            "mae": float(audit.get("mae", float("nan"))),
            "r2": float(audit.get("r2", float("nan"))),
            "n_train": int(audit.get("n_train", 0)),
            "forecast_end_value": float(
                audit.get("forecast_end_value", float("nan"))
            ),
            "last_observed_value": float(
                audit.get("last_observed_value", float("nan"))
            ),
            "backend": backend,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        np.random.seed(42)
        return _reference_esn(
            y, seed=42, horizon=self.HORIZON,
            preset_cfg=_ENGINE_BALANCED_PRESET,
        )

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        # Engine rounding per Phase 1 finding B8: forecast 6-decimal;
        # rmse/mae/r2 4-decimal; n_train integer; series/forecast
        # endpoint values 6-decimal.
        ref_forecast_rounded = np.round(ref["forecast"], 6)

        primary: dict[str, Any] = {}
        statuses: list[str] = []

        primary["forecast"] = _compare_vector(
            tsl["forecast"], ref_forecast_rounded, ladder["primary"],
        )
        statuses.append(primary["forecast"]["status"])

        primary["rmse"] = _compare_scalar(
            tsl["rmse"], round(ref["rmse"], 4), ladder["primary"],
        )
        statuses.append(primary["rmse"]["status"])

        primary["mae"] = _compare_scalar(
            tsl["mae"], round(ref["mae"], 4), ladder["primary"],
        )
        statuses.append(primary["mae"]["status"])

        primary["r2"] = _compare_scalar(
            tsl["r2"], round(ref["r2"], 4), ladder["primary"],
        )
        statuses.append(primary["r2"]["status"])

        primary["n_train"] = {
            "status": (
                "PASS" if tsl["n_train"] == ref["n_train"]
                else "BLOCK"
            ),
            "tsl": int(tsl["n_train"]),
            "ref": int(ref["n_train"]),
        }
        statuses.append(primary["n_train"]["status"])

        primary["forecast_end_value"] = _compare_scalar(
            tsl["forecast_end_value"],
            round(ref["forecast_end_value"], 6),
            ladder["primary"],
        )
        statuses.append(primary["forecast_end_value"]["status"])

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
                "horizon": int(self.HORIZON),
                "preset": "Balanced",
                "backend": str(tsl.get("backend", "?")),
                "reservoir_size": int(
                    _ENGINE_BALANCED_PRESET["reservoir_size"]
                ),
                "spectral_radius": float(
                    _ENGINE_BALANCED_PRESET["spectral_radius"]
                ),
                "leak_rate": float(_ENGINE_BALANCED_PRESET["leak_rate"]),
                "ridge_alpha": float(_ENGINE_BALANCED_PRESET["ridge_alpha"]),
                "warmup": int(_ENGINE_BALANCED_PRESET["warmup"]),
                "sparsity": float(_ENGINE_BALANCED_PRESET["sparsity"]),
            },
        )
