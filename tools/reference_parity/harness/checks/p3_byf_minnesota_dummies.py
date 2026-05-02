"""Phase 4 Session 4 — BYF Minnesota dummy-observation Pattern A.3 audit.

Closes BYF v1.2.0 amendment candidate #2: the Minnesota-prior
dummy-observation construction is the highest-risk single component
in the BVAR-SV pipeline (per BYF S4 reference-selection). This
audit verifies TSL's
``engine/techniques/bond_yield_forecast/priors.py:MinnesotaPrior._compute_dummies()``
against a Pattern A.3 from-scratch reimplementation following
Doan-Litterman-Sims 1984 §3 + Sims-Zha 1998 extensions verbatim.

**Pattern A.3 = self-parity paper-formula reimpl.** The reference
is a from-scratch reimplementation of the canonical formulas;
the comparison is bit-exact (closed-form arithmetic on identical
hyperparameter inputs should produce element-wise identical
arrays). Divergence at any element surfaces a wrapper bug in the
prior construction.

**Five dummy blocks per the standard Sims-Zha 1998 / BGR construction:**

  Block A (coefficient priors): n*p rows
    Y_d[r, k] = persistence[k] * sigma[k] * lag_decay / lambda_1
    X_d[r, 1 + (l-1)*n + k] = sigma[k] * lag_decay / lambda_1
    where lag_decay = l ** lambda_3, l = 1..p, r = (l-1)*n + k

  Block B (covariance prior / scale of Sigma): n rows
    Y_d[r, k] = sigma[k]
    X_d[r, :] = 0
    where r = n*p + k

  Block C (intercept diffuse): 1 row (only if lambda_4 > 0)
    X_d[r, 0] = 1.0 / lambda_4
    Y_d[r, :] = 0
    where r = n*p + n

  Block D (sum-of-coefficients): n rows (only if lambda_sc > 0)
    Y_d[r, k] = lambda_sc * persistence[k] * y_bar[k]
    X_d[r, 1 + (l-1)*n + k] = lambda_sc * y_bar[k] for l=1..p
    where r = n*p + n + 1 + k

  Block E (initial-observation): 1 row (only if lambda_io > 0)
    Y_d[r, j] = lambda_io * y_bar[j]
    X_d[r, 0] = lambda_io
    X_d[r, 1 + (l-1)*n + j] = lambda_io * y_bar[j] for l=1..p, j=1..n
    where r = n*p + n + 1 + n

**verdict_class:** ``closed_form`` (no estimation, no MCMC; pure
matrix construction from configuration).

**Tier:** ``fast`` (matrix construction; <1s wall-clock).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._pattern_a_helpers import (
    compare_array_pair,
    synthesize_minnesota_config,
)
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _reference_minnesota_dummies(
    *,
    n_vars: int,
    n_lags: int,
    sigma: np.ndarray,
    y_bar: np.ndarray,
    persistence: np.ndarray,
    lambda_1: float,
    lambda_3: float,
    lambda_4: float,
    lambda_sc: float,
    lambda_io: float,
) -> tuple[np.ndarray, np.ndarray]:
    """From-scratch Pattern A.3 reimpl of the Sims-Zha 1998 / BGR
    Minnesota dummy-observation construction.

    Reference: Doan-Litterman-Sims 1984 §3 (original Minnesota
    coefficient prior) + Sims-Zha 1998 (sum-of-coefficients +
    initial-observation extensions) + BGR-2010 (consolidated
    dummy-form presentation).

    No reuse of TSL's ``priors.py:MinnesotaPrior``. This is the
    reference implementation against which TSL is checked.
    """
    n, p = int(n_vars), int(n_lags)
    n_kp1 = 1 + n * p  # intercept + n_vars * n_lags coefficients

    # Row counts per block (matches TSL's `dummy_block_counts`)
    n_block_a = n * p
    n_block_b = n
    n_block_c = 1 if lambda_4 > 0 else 0
    n_block_d = n if lambda_sc > 0 else 0
    n_block_e = 1 if lambda_io > 0 else 0
    n_d = n_block_a + n_block_b + n_block_c + n_block_d + n_block_e

    Y_d = np.zeros((n_d, n))
    X_d = np.zeros((n_d, n_kp1))

    # Block A: coefficient priors
    # Per DLS-1984 §3: prior std on the coefficient of variable k,
    # lag l, in equation k is sigma[k] / (lag_decay * lambda_1).
    # In dummy form: Y_d[r, k] = persistence[k] * scale,
    # X_d[r, position_lag_l_k] = scale, where scale = sigma[k] *
    # lag_decay / lambda_1 (so the implied prior std = 1/scale =
    # lambda_1 / (sigma[k] * lag_decay)).
    for l in range(1, p + 1):
        lag_decay = float(l) ** lambda_3
        for k in range(n):
            r = (l - 1) * n + k
            scale = sigma[k] * lag_decay / lambda_1
            Y_d[r, k] = persistence[k] * scale
            X_d[r, 1 + (l - 1) * n + k] = scale

    offset = n_block_a

    # Block B: covariance prior (scale of Sigma)
    # Per BGR-2010: dummy rows that pin the diagonal of the prior
    # innovation covariance to sigma[k]^2.
    for k in range(n):
        r = offset + k
        Y_d[r, k] = sigma[k]
        # X_d[r, :] left as zero
    offset += n_block_b

    # Block C: intercept diffuse (1 row if lambda_4 > 0)
    if n_block_c > 0:
        X_d[offset, 0] = 1.0 / lambda_4
        # Y_d[offset, :] left as zero
        offset += n_block_c

    # Block D: sum-of-coefficients (n rows; Sims-Zha 1998 unit-root
    # restriction). Encodes the prior belief that long-run
    # coefficients sum to persistence * (1 - 0) for level series.
    if n_block_d > 0:
        for k in range(n):
            r = offset + k
            Y_d[r, k] = lambda_sc * persistence[k] * y_bar[k]
            for l in range(1, p + 1):
                X_d[r, 1 + (l - 1) * n + k] = lambda_sc * y_bar[k]
        offset += n_block_d

    # Block E: initial-observation (1 row; Sims-Zha 1998
    # cointegration-friendly prior). Encodes the prior belief that
    # the initial observation is a stable starting point.
    if n_block_e > 0:
        r = offset
        for j in range(n):
            Y_d[r, j] = lambda_io * y_bar[j]
        X_d[r, 0] = lambda_io
        for l in range(1, p + 1):
            for j in range(n):
                X_d[r, 1 + (l - 1) * n + j] = lambda_io * y_bar[j]
        offset += n_block_e

    assert offset == n_d, (
        f"Reference reimpl row-count mismatch: offset={offset} vs "
        f"n_d={n_d}"
    )
    return Y_d, X_d


class BYFMinnesotaDummiesParity(P3ParityCheck):
    """BYF candidate #2 — Minnesota dummy-observation Pattern A.3 audit."""

    technique_id = "p3_byf_minnesota_dummies"
    tier = "fast"
    fixture_id = ""  # synthetic config; no on-disk fixture
    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Minnesota dummy-observation construction is closed-form "
        "matrix arithmetic over the hyperparameter set "
        "(lambda_1/3/4/sc/io, sigma, y_bar, persistence). Same "
        "configuration must produce element-wise identical "
        "(Y_d, X_d) arrays across implementations; bit-exact "
        "tolerance applies (Pattern A.3 self-parity reimpl per "
        "Doan-Litterman-Sims 1984 §3 + Sims-Zha 1998)."
    )
    reroll_on_caveat = False  # deterministic given config

    # Two configurations exercising different dimensionalities
    CONFIGS = (
        {"n_vars": 3, "n_lags": 2, "seed": 42},
        {"n_vars": 6, "n_lags": 4, "seed": 43},
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        # Pre-compute both Minnesota config dicts so run_tsl /
        # run_reference share identical inputs.
        return {
            f"config_{i}": synthesize_minnesota_config(
                n_vars=cfg["n_vars"],
                n_lags=cfg["n_lags"],
                seed=cfg["seed"],
            )
            for i, cfg in enumerate(self.CONFIGS)
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.bond_yield_forecast.priors import MinnesotaPrior

        out: dict[str, Any] = {}
        for cfg_key, cfg in fixture.items():
            prior = MinnesotaPrior(
                n_vars=cfg["n_vars"],
                n_lags=cfg["n_lags"],
                lambda_1=cfg["lambda_1"],
                lambda_2=cfg["lambda_2"],
                lambda_3=cfg["lambda_3"],
                lambda_4=cfg["lambda_4"],
                lambda_sc=cfg["lambda_sc"],
                lambda_io=cfg["lambda_io"],
                # MinnesotaPrior also wants sigma + y_bar +
                # persistence + variable_names + training_data.
                # Build a minimal training_data shaped to provide
                # the required summary stats; MinnesotaPrior
                # recomputes sigma and y_bar from training_data
                # unless overridden, but BYF's signature accepts
                # explicit overrides via the persistence_prior dict
                # and computes sigma/y_bar from training_data
                # internally — so we must construct a synthetic
                # panel whose univariate AR-1 residual std matches
                # cfg["sigma"] and whose mean matches cfg["y_bar"].
                # Simpler: bypass training_data, set persistence
                # explicitly, and override the
                # internal sigma + y_bar by direct attribute set
                # AFTER construction.
                persistence_prior={
                    f"v{k}": float(cfg["persistence"][k])
                    for k in range(cfg["n_vars"])
                },
                variable_names=[f"v{k}" for k in range(cfg["n_vars"])],
                training_data=_build_synthetic_training_data(cfg),
            )
            # Override any internally-computed sigma / y_bar with the
            # synthetic config values so TSL and reference operate on
            # bit-identical inputs to the dummy construction. The
            # override path is used because MinnesotaPrior recomputes
            # these from training_data; the audit's purpose is to
            # check the dummy construction GIVEN identical inputs.
            prior.sigma = cfg["sigma"]
            prior.y_bar = cfg["y_bar"]
            # Re-run the dummy construction with the overridden values
            prior._Y_d, prior._X_d = prior._compute_dummies()
            Y_d, X_d = prior.dummy_observations()
            out[cfg_key] = {
                "Y_d": Y_d,
                "X_d": X_d,
            }
        return out

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for cfg_key, cfg in fixture.items():
            Y_d, X_d = _reference_minnesota_dummies(
                n_vars=cfg["n_vars"],
                n_lags=cfg["n_lags"],
                sigma=cfg["sigma"],
                y_bar=cfg["y_bar"],
                persistence=cfg["persistence"],
                lambda_1=cfg["lambda_1"],
                lambda_3=cfg["lambda_3"],
                lambda_4=cfg["lambda_4"],
                lambda_sc=cfg["lambda_sc"],
                lambda_io=cfg["lambda_io"],
            )
            out[cfg_key] = {"Y_d": Y_d, "X_d": X_d}
        return out

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any]
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        for cfg_key in tsl.keys():
            for arr_key in ("Y_d", "X_d"):
                metric_name = f"{cfg_key}::{arr_key}"
                primary[metric_name] = compare_array_pair(
                    tsl[cfg_key][arr_key],
                    ref[cfg_key][arr_key],
                    abs_tol=ladder["primary"]["abs_tol"],
                    rel_tol=ladder["primary"]["rel_tol"],
                    name=metric_name,
                )
        statuses = [v["status"] for v in primary.values()]
        outcome = (
            "BLOCK" if "BLOCK" in statuses
            else "CAVEAT" if "CAVEAT" in statuses
            else "PASS"
        )
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_configs": len(tsl),
                "config_shapes": [
                    {
                        "n_vars": fixture_cfg["n_vars"],
                        "n_lags": fixture_cfg["n_lags"],
                    }
                    for fixture_cfg in (
                        synthesize_minnesota_config(
                            n_vars=cfg["n_vars"],
                            n_lags=cfg["n_lags"],
                            seed=cfg["seed"],
                        )
                        for cfg in self.CONFIGS
                    )
                ],
            },
        )


def _build_synthetic_training_data(cfg: dict[str, Any]):
    """Produce a minimal pandas DataFrame matching the
    n_vars / n_lags from cfg, suitable for ``MinnesotaPrior``'s
    constructor. The TSL constructor uses training_data to compute
    its own sigma / y_bar; we override these post-construction so
    the comparison operates on identical inputs to the dummy
    construction. See ``run_tsl`` above for the override flow.
    """
    import pandas as pd

    n_vars = int(cfg["n_vars"])
    # Provide enough rows so MinnesotaPrior's internal AR-1 fits
    # don't choke. T = max(50, 5 * n_lags).
    T = max(50, 5 * int(cfg["n_lags"]))
    rng = np.random.default_rng(int(cfg.get("_seed", 0)))
    data = rng.standard_normal((T, n_vars))
    return pd.DataFrame(
        data,
        columns=[f"v{k}" for k in range(n_vars)],
    )
