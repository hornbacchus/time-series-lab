"""Litterman (1986) / Sims-Zha (1998) Minnesota prior in moments and dummy form.

VAR layout: B has shape (n_vars, n_vars*n_lags+1). Rows are equations.
Columns are [constant, lag1_var1, ..., lag1_varN, lag2_var1, ..., lagP_varN].

Citations:
    Litterman, R. (1986). "Forecasting with Bayesian Vector Autoregressions —
        Five Years of Experience." Journal of Business and Economic Statistics
        4(1):25-38.
    Sims, C. and Zha, T. (1998). "Bayesian methods for dynamic multivariate
        models." International Economic Review 39(4):949-968.
    Banbura, M., Giannone, D., Reichlin, L. (2010). "Large Bayesian vector
        auto regressions." Journal of Applied Econometrics 25(1):71-92 —
        formal dummy-observation construction.

Implementation note on lambda_2 (cross-variable shrinkage):
    The moments form (`prior_moments`) implements lambda_2 exactly. The
    dummy form (`dummy_observations`) follows the standard BGR construction
    which encodes cross-shrinkage via the sigma_i / sigma_j ratio without
    an explicit lambda_2 multiplier. The two representations agree exactly
    when lambda_2 == 1; they diverge as lambda_2 moves from 1. The Step 2.5
    Octave/MATLAB validation harness compares against the moments form.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _ar1_residual_std(data: pd.DataFrame) -> np.ndarray:
    sigma = np.empty(data.shape[1])
    values = data.to_numpy(dtype=float)
    for i in range(values.shape[1]):
        y = values[:, i]
        X = np.column_stack([np.ones(len(y) - 1), y[:-1]])
        Y = y[1:]
        beta, *_ = np.linalg.lstsq(X, Y, rcond=None)
        residuals = Y - X @ beta
        sigma[i] = float(np.std(residuals, ddof=2))
    return sigma


def _resolve_persistence(
    persistence_prior: np.ndarray | dict | list | None,
    variable_names: list[str],
    n_vars: int,
) -> np.ndarray:
    if persistence_prior is None:
        return np.zeros(n_vars)
    if isinstance(persistence_prior, dict):
        if variable_names is None:
            raise ValueError(
                "variable_names is required when persistence_prior is a dict"
            )
        try:
            return np.array(
                [float(persistence_prior[name]) for name in variable_names]
            )
        except KeyError as exc:
            raise KeyError(
                f"persistence_prior dict missing entry for variable {exc}; "
                f"required: {variable_names}"
            ) from exc
    arr = np.asarray(persistence_prior, dtype=float)
    if arr.shape != (n_vars,):
        raise ValueError(
            f"persistence_prior must be length {n_vars}; got shape {arr.shape}"
        )
    return arr


class MinnesotaPrior:
    """Litterman/Sims-Zha Minnesota prior on a VAR with ``n_vars`` equations.

    Hyperparameters (all positive):
        lambda_1   overall tightness on lag coefficients
        lambda_2   cross-variable shrinkage (cross prior std multiplied by lambda_2)
        lambda_3   lag decay (prior std at lag l divided by l^lambda_3)
        lambda_4   intercept tightness (effectively diffuse at default 1e5)
        lambda_sc  weight on sum-of-coefficients dummy
        lambda_io  weight on initial-observation dummy

    Either ``training_data`` (DataFrame) or both ``sigma`` and ``y_bar``
    must be supplied. ``training_data`` is the canonical input; sigma is
    computed via OLS AR(1) on each variable.
    """

    def __init__(
        self,
        n_vars: int,
        n_lags: int = 4,
        lambda_1: float = 0.2,
        lambda_2: float = 0.5,
        lambda_3: float = 1.0,
        lambda_4: float = 1e5,
        lambda_sc: float = 1.0,
        lambda_io: float = 1.0,
        sigma: np.ndarray | None = None,
        y_bar: np.ndarray | None = None,
        persistence_prior: np.ndarray | dict | list | None = None,
        variable_names: list[str] | None = None,
        training_data: pd.DataFrame | None = None,
    ):
        if n_vars <= 0 or n_lags <= 0:
            raise ValueError("n_vars and n_lags must be positive")

        # S0.3 — parameter zero-divide guards. lambda_1 is a divisor in
        # the dummy-observation construction (X_d[r, c] = sigma[k] * lag_decay
        # / lambda_1). lambda_4 is a divisor in the diffuse-intercept dummy
        # (X_d[offset, 0] = 1.0 / lambda_4). lambda_2 multiplies cross-equation
        # variance in the moments form; zero collapses it to a degenerate
        # singular prior. lambda_3 is the lag-decay exponent (lag_decay =
        # l ** lambda_3); zero disables decay (mathematically valid but
        # likely unintended). lambda_sc and lambda_io are explicitly
        # allowed to be 0 (used by the loose-prior-limit test in
        # validation.py to disable SoC / IO dummies).
        if lambda_1 <= 0:
            raise ValueError(
                "lambda_1 must be positive (default 0.2). lambda_1 is the "
                "overall tightness on lag coefficients and is used as a "
                "divisor in the dummy-observation construction; non-positive "
                "values produce division-by-zero or sign-flipped priors."
            )
        if lambda_2 <= 0:
            raise ValueError("lambda_2 must be positive (default 0.5).")
        if lambda_3 <= 0:
            raise ValueError("lambda_3 must be positive (default 1.0).")
        if lambda_4 <= 0:
            raise ValueError(
                "lambda_4 must be positive (default 1e5; near-zero produces "
                "division-by-zero in dummy-observation construction)."
            )
        if lambda_sc < 0:
            raise ValueError(
                "lambda_sc must be non-negative (default 1.0; "
                "0 disables the sum-of-coefficients dummy)."
            )
        if lambda_io < 0:
            raise ValueError(
                "lambda_io must be non-negative (default 1.0; "
                "0 disables the initial-observation dummy)."
            )

        if variable_names is None and training_data is not None:
            variable_names = list(training_data.columns)
        if variable_names is None:
            variable_names = [f"v{i}" for i in range(n_vars)]
        if len(variable_names) != n_vars:
            raise ValueError(
                f"variable_names has length {len(variable_names)}, expected {n_vars}"
            )

        if sigma is None or y_bar is None:
            if training_data is None:
                raise ValueError(
                    "Must supply either training_data, or both sigma and y_bar"
                )
            sigma = _ar1_residual_std(training_data) if sigma is None else np.asarray(sigma, dtype=float)
            y_bar = (
                training_data.mean(axis=0).to_numpy(dtype=float)
                if y_bar is None
                else np.asarray(y_bar, dtype=float)
            )

        sigma = np.asarray(sigma, dtype=float)
        y_bar = np.asarray(y_bar, dtype=float)
        if sigma.shape != (n_vars,):
            raise ValueError(f"sigma must be length {n_vars}; got {sigma.shape}")
        if y_bar.shape != (n_vars,):
            raise ValueError(f"y_bar must be length {n_vars}; got {y_bar.shape}")

        persistence_arr = _resolve_persistence(
            persistence_prior, variable_names, n_vars
        )

        self.n_vars = n_vars
        self.n_lags = n_lags
        self.lambda_1 = float(lambda_1)
        self.lambda_2 = float(lambda_2)
        self.lambda_3 = float(lambda_3)
        self.lambda_4 = float(lambda_4)
        self.lambda_sc = float(lambda_sc)
        self.lambda_io = float(lambda_io)
        self.sigma = sigma
        self.y_bar = y_bar
        self.persistence = persistence_arr
        self.variable_names = list(variable_names)

        self._n_kp1 = n_vars * n_lags + 1
        self._B_mean, self._V_B = self._compute_moments()
        self._S_prior, self._nu_prior = self._compute_iw_prior()
        self._Y_d, self._X_d = self._compute_dummies()

        logger.info(
            "MinnesotaPrior(n_vars=%d, n_lags=%d): %d dummy rows = %s",
            n_vars,
            n_lags,
            self._Y_d.shape[0],
            self.dummy_block_counts,
        )

    @property
    def dummy_block_counts(self) -> dict[str, int]:
        return {
            "coefficients": self.n_vars * self.n_lags,
            "covariance": self.n_vars,
            "intercept": 1,
            "sum_of_coefficients": self.n_vars,
            "initial_observation": 1,
        }

    def _compute_moments(self) -> tuple[np.ndarray, np.ndarray]:
        n, p = self.n_vars, self.n_lags
        n_kp1 = self._n_kp1

        B_mean = np.zeros((n, n_kp1))
        for i in range(n):
            B_mean[i, 1 + i] = self.persistence[i]

        V_B = np.zeros((n, n_kp1, n_kp1))
        for i in range(n):
            V_B[i, 0, 0] = (self.lambda_4 * self.sigma[i]) ** 2
            for l in range(1, p + 1):
                lag_decay = float(l) ** self.lambda_3
                for j in range(n):
                    pos = 1 + (l - 1) * n + j
                    if j == i:
                        std = self.lambda_1 / lag_decay
                    else:
                        std = (
                            self.lambda_1
                            * self.lambda_2
                            * self.sigma[i]
                            / (lag_decay * self.sigma[j])
                        )
                    V_B[i, pos, pos] = std * std
        return B_mean, V_B

    def _compute_iw_prior(self) -> tuple[np.ndarray, int]:
        nu_prior = self.n_vars + 2
        S_prior = np.diag(self.sigma ** 2) * (nu_prior - self.n_vars - 1)
        if not np.any(S_prior):
            S_prior = np.diag(self.sigma ** 2)
        return S_prior, nu_prior

    def _compute_dummies(self) -> tuple[np.ndarray, np.ndarray]:
        n, p = self.n_vars, self.n_lags
        n_kp1 = self._n_kp1
        counts = self.dummy_block_counts
        n_d = sum(counts.values())

        Y_d = np.zeros((n_d, n))
        X_d = np.zeros((n_d, n_kp1))

        # Block A: coefficient priors (n*p rows)
        for l in range(1, p + 1):
            lag_decay = float(l) ** self.lambda_3
            for k in range(n):
                r = (l - 1) * n + k
                scale = self.sigma[k] * lag_decay / self.lambda_1
                Y_d[r, k] = self.persistence[k] * scale
                X_d[r, 1 + (l - 1) * n + k] = scale

        offset = counts["coefficients"]

        # Block B: covariance prior (n rows)
        for k in range(n):
            r = offset + k
            Y_d[r, k] = self.sigma[k]
        offset += counts["covariance"]

        # Block C: diffuse intercept (1 row)
        if self.lambda_4 > 0:
            X_d[offset, 0] = 1.0 / self.lambda_4
        offset += counts["intercept"]

        # Block D: sum-of-coefficients (n rows, weight lambda_sc)
        for k in range(n):
            r = offset + k
            Y_d[r, k] = self.lambda_sc * self.persistence[k] * self.y_bar[k]
            for l in range(1, p + 1):
                X_d[r, 1 + (l - 1) * n + k] = self.lambda_sc * self.y_bar[k]
        offset += counts["sum_of_coefficients"]

        # Block E: initial-observation (1 row, weight lambda_io)
        r = offset
        for j in range(n):
            Y_d[r, j] = self.lambda_io * self.y_bar[j]
        X_d[r, 0] = self.lambda_io
        for l in range(1, p + 1):
            for j in range(n):
                X_d[r, 1 + (l - 1) * n + j] = self.lambda_io * self.y_bar[j]
        offset += counts["initial_observation"]

        assert offset == n_d
        return Y_d, X_d

    def dummy_observations(self) -> tuple[np.ndarray, np.ndarray]:
        """Return (Y_d, X_d) Litterman-Sims-Zha dummy observations.

        Total row count: ``n*p + 2*n + 2`` rows decomposed per the
        ``dummy_block_counts`` property:
            Block A (coefficient priors):     n*p
            Block B (covariance prior):       n
            Block C (intercept diffuse):      1
            Block D (sum-of-coefficients):    n
            Block E (initial-observation):    1
        """
        return self._Y_d.copy(), self._X_d.copy()

    def prior_moments(self) -> dict[str, Any]:
        """Return analytical prior moments.

        Keys:
          ``B_mean``  (n_vars, n_kp+1) — prior mean of B per equation
          ``V_B``     (n_vars, n_kp+1, n_kp+1) — per-equation prior covariance
                      (diagonal in Minnesota); ``V_B[i]`` is equation i's matrix
          ``S_prior`` (n_vars, n_vars) — IW scale matrix
          ``nu_prior`` (int) — IW degrees of freedom
        """
        return {
            "B_mean": self._B_mean.copy(),
            "V_B": self._V_B.copy(),
            "S_prior": self._S_prior.copy(),
            "nu_prior": int(self._nu_prior),
        }

    def inspect(self) -> dict[str, Any]:
        """Return a JSON-serializable summary of the prior."""
        return {
            "n_vars": self.n_vars,
            "n_lags": self.n_lags,
            "lambda_1": self.lambda_1,
            "lambda_2": self.lambda_2,
            "lambda_3": self.lambda_3,
            "lambda_4": self.lambda_4,
            "lambda_sc": self.lambda_sc,
            "lambda_io": self.lambda_io,
            "variable_names": list(self.variable_names),
            "sigma": self.sigma.tolist(),
            "y_bar": self.y_bar.tolist(),
            "persistence": self.persistence.tolist(),
            "dummy_block_counts": dict(self.dummy_block_counts),
            "dummy_count_total": int(sum(self.dummy_block_counts.values())),
        }

    def to_json(self) -> str:
        return json.dumps(self.inspect())
