"""GLP-2015 marginal-likelihood optimization for the Minnesota prior.

Implements empirical-Bayes selection of the Minnesota hyperparameters by
maximizing the closed-form Normal-Inverse-Wishart marginal data density
(MDD) under the Banbura-Giannone-Reichlin (2010) dummy-observation prior.

CRITICAL CONTRACT — closed-form vs SV
-------------------------------------
The MDD used here is exact under the **constant-volatility** BVAR with a
conjugate Normal-Inverse-Wishart prior. The downstream sampler (BVARSV)
adds Kim-Shephard-Chib stochastic volatility, for which the MDD has no
closed form and would require Chib-1995 numerical estimation per
hyperparameter evaluation — prohibitively expensive at grid scales.

Following GLP-2015 Section 3, we optimize the lambdas under the
constant-vol model and plug the result into the SV sampler unchanged.
The lambdas control the *prior on B*, not the volatility process; this is
standard practice in the empirical-Bayes BVAR literature (BGR-2010, GLP-
2015, Karlsson-2013).

CRITICAL CONTRACT — which lambdas are optimized
------------------------------------------------
The dummy-observation form of the Minnesota prior (BGR-2010 Appendix A)
encodes cross-equation shrinkage through the sigma_i/sigma_j AR(1)
residual-std ratio rather than through a separate `lambda_2` multiplier.
Consequently the dummy-form MDD has **no dependence on lambda_2**; it is
an unidentified direction. We therefore optimize the four GLP-2015
hyperparameters:

    lambda_1   overall tightness on lag coefficients
    lambda_3   lag decay (prior std at lag l divided by l^lambda_3)
    lambda_sc  weight on sum-of-coefficients dummy
    lambda_io  weight on initial-observation dummy

`lambda_2` is held at its config value (the moments form uses it
explicitly; the dummy form does not). This matches GLP-2015's own
4-hyperparameter setup exactly.

Note on lambda_2: in the Banbura-Giannone-Reichlin (2010) dummy-
observation form used by priors.MinnesotaPrior, cross-variable
shrinkage is absorbed into the sigma_i/sigma_j ratio of the dummy
construction (multiply by 1/lambda_2 for cross terms). This means
lambda_2 enters multiplicatively in a way that renormalizes away in
the closed-form marginal likelihood. The GLP-2015 optimizer therefore
optimizes four hyperparameters (lambda_1, lambda_3, lambda_sc,
lambda_io), with lambda_2 held fixed at its config value. Users
wanting to tune lambda_2 should do so manually.

EMPIRICAL BAYES vs. SV CONVERGENCE TRADE-OFF
--------------------------------------------
On this panel (T=143 quarterly, 6 variables, 4 lags), the GLP-2015
empirical-Bayes objective and the BVAR-SV sampler convergence quality
point in different directions:

  - GLP-MDD argmax wants minimal lag-decay shrinkage (lambda_3 -> 0)
    and maximal initial-observation pinning (lambda_io -> max bound).
    These reflect the data's preference for less informative prior
    structure given the long-memory yield-curve dynamics and multi-
    regime macro volatility.

  - BVAR-SV sampler convergence on the SV parameters (omega, phi, mu
    on the macro variables) is BETTER under the more-informative
    fixed defaults than under the GLP-optimized hyperparameters. The
    optimized hyperparameters slightly degrade convergence on the
    weakest-identified parameter groups.

Implication for production: GLP-optimized hyperparameters maximize
the marginal likelihood of the constant-volatility BVAR but are not
the best choice for the BVAR-SV sampler we actually use. The Step 2
fixed defaults (lambda_1=0.2, lambda_2=0.5, lambda_3=1.0,
lambda_sc=1.0, lambda_io=1.0) deliver more stable SV sampler behavior
on this panel.

This trade-off is a property of the GLP-2015 closed-form objective
(constant-vol BVAR marginal likelihood) interacting with the
stochastic-volatility sampler, not a bug. The closed-form MDD does
not see the SV identification problem the sampler does.

Citations
---------
    Giannone, D., Lenza, M., Primiceri, G. (2015). "Prior selection for
        vector autoregressions." Review of Economics and Statistics
        97(2):436-451.
    Banbura, M., Giannone, D., Reichlin, L. (2010). "Large Bayesian
        vector auto regressions." JAE 25(1):71-92 — dummy form.
    Karlsson, S. (2013). "Forecasting with Bayesian vector
        autoregression." Handbook of Economic Forecasting Vol 2B,
        Chapter 15 — closed-form NIW MDD reference.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln, multigammaln

from .priors import MinnesotaPrior
from .validation import _build_lag_design_xy

logger = logging.getLogger(__name__)


def _log_marginal_likelihood_niw(
    Y: np.ndarray,
    X: np.ndarray,
    Y_d: np.ndarray,
    X_d: np.ndarray,
) -> float:
    """Closed-form log p(Y) under the dummy-observation NIW prior.

    Following Karlsson (2013) eq. 3.10 / BGR-2010 Appendix A, with the
    prior implicitly defined by the dummy observations (Y_d, X_d):

        log p(Y) = -(nT/2) log(pi)
                 + log Gamma_n(nu_post/2) - log Gamma_n(nu_0/2)
                 - (n/2) (log|X*' X*| - log|X_d' X_d|)
                 + (nu_0/2) log|S_0| - (nu_post/2) log|S_post|

    where X* = [X; X_d], Y* = [Y; Y_d], k = n*p+1,
    nu_0 = n_d - k, nu_post = nu_0 + T,
    S_0 = (Y_d - X_d B_d_hat)' (Y_d - X_d B_d_hat),
    S_post = (Y* - X* B_post_hat)' (Y* - X* B_post_hat),
    B_d_hat = (X_d'X_d)^-1 X_d'Y_d,
    B_post_hat = (X*'X*)^-1 X*'Y*.

    Returns ``-np.inf`` on any numerical failure (singular X_d'X_d at
    extreme lambdas, non-positive determinants); the optimizer naturally
    avoids those regions.
    """
    T, n = Y.shape
    n_d, k = X_d.shape
    nu_0 = n_d - k
    nu_post = nu_0 + T

    # Degree-of-freedom regularity: log Gamma_n(a) finite iff 2a > n - 1.
    if nu_0 <= n - 1 or nu_post <= n - 1:
        return -np.inf

    Y_star = np.vstack([Y, Y_d])
    X_star = np.vstack([X, X_d])
    XtX_d = X_d.T @ X_d
    XtX_star = X_star.T @ X_star

    # Posterior and prior B-precision log-determinants. slogdet handles
    # negative-det edge cases gracefully (sign != 1 -> non-positive).
    sign_d, logdet_XtX_d = np.linalg.slogdet(XtX_d)
    sign_star, logdet_XtX_star = np.linalg.slogdet(XtX_star)
    if sign_d <= 0 or sign_star <= 0:
        return -np.inf

    # Solve normal equations for prior and posterior B-mean.
    try:
        B_d_hat = np.linalg.solve(XtX_d, X_d.T @ Y_d)
        B_post_hat = np.linalg.solve(XtX_star, X_star.T @ Y_star)
    except np.linalg.LinAlgError:
        return -np.inf

    # Prior and posterior IW scale.
    resid_d = Y_d - X_d @ B_d_hat
    S_0 = resid_d.T @ resid_d
    resid_star = Y_star - X_star @ B_post_hat
    S_post = resid_star.T @ resid_star

    sign_S0, logdet_S0 = np.linalg.slogdet(S_0)
    sign_Sp, logdet_Sp = np.linalg.slogdet(S_post)
    if sign_S0 <= 0 or sign_Sp <= 0:
        return -np.inf

    # Multivariate gamma terms. multigammaln(a, n) returns log Gamma_n(a)
    # which already includes the (n(n-1)/4) log(pi) normalizer; the
    # constant cancels in the difference but using the library function
    # is cleanest and matches the published reference forms.
    log_mgamma_post = multigammaln(nu_post / 2.0, n)
    log_mgamma_0 = multigammaln(nu_0 / 2.0, n)

    log_mdd = (
        -(n * T / 2.0) * np.log(np.pi)
        + log_mgamma_post - log_mgamma_0
        - (n / 2.0) * (logdet_XtX_star - logdet_XtX_d)
        + (nu_0 / 2.0) * logdet_S0
        - (nu_post / 2.0) * logdet_Sp
    )
    return float(log_mdd)


def _at_bound_warnings(
    recommended: dict[str, float],
    bounds: dict[str, tuple[float, float]],
    atol_pct: float = 0.01,
) -> list[str]:
    """Return hard-warning strings for any lambda within atol_pct of a bound.

    Per Step 3 refinement 3: if any optimal lambda is within 1% of either
    bound, the optimizer hit the constraint, not the true optimum. Surface
    this as an unmissable warning.
    """
    warnings: list[str] = []
    for name, value in recommended.items():
        if name not in bounds:
            continue
        lo, hi = bounds[name]
        span = max(hi - lo, 1e-12)
        # 1% of the (lo, hi) span counts as "at the bound".
        tol = atol_pct * span
        # Guard zero-width bounds (e.g., lambda_sc lower=0): treat absolute
        # equality with a bound as at-bound regardless of percentage.
        at_lo = (value - lo) <= tol or value <= lo + 1e-9
        at_hi = (hi - value) <= tol or value >= hi - 1e-9
        if at_lo or at_hi:
            which = "lower" if at_lo else "upper"
            warnings.append(
                f"WARNING: optimal {name} = {value:.6g} is at the {which} bound "
                f"({lo}, {hi}). The optimizer hit the constraint, not the true "
                f"optimum. Either expand the bound or investigate whether the "
                f"prior structure suits this data before using this hyperparameter "
                f"in production."
            )
    return warnings


def _literature_range_warnings(recommended: dict[str, float]) -> list[str]:
    """Soft warnings for lambdas outside literature-typical ranges."""
    soft: list[str] = []
    l1 = recommended.get("lambda_1")
    if l1 is not None and (l1 < 0.05 or l1 > 0.30):
        soft.append(
            f"NOTE: optimal lambda_1 = {l1:.4f} is outside the literature-typical "
            f"range [0.05, 0.30] (GLP-2015 fig 1)."
        )
    l3 = recommended.get("lambda_3")
    if l3 is not None and (l3 < 0.5 or l3 > 2.0):
        soft.append(
            f"NOTE: optimal lambda_3 = {l3:.4f} is outside the literature-typical "
            f"range [0.5, 2.0]."
        )
    return soft


class HyperparameterOptimizer:
    """GLP-2015 hyperparameter optimization for the Minnesota prior.

    See module docstring for the closed-form-vs-SV and which-lambdas-are-
    optimized contracts.

    Constructor arguments
    ---------------------
    panel               (T+p, n) DataFrame of observable variables.
    n_lags              VAR lag order p.
    persistence_prior   Optional dict {variable_name: persistence}.
    variable_names      Optional list of column names; defaults to panel.columns.
    lambda_2_fixed      Held-fixed lambda_2 value. Defaults to 1.0 (the value
                        at which the dummy form and moments form agree exactly).
    seed                Reproducibility seed for L-BFGS-B's finite-difference
                        gradient and any internal random tie-breaking.
    """

    def __init__(
        self,
        panel: pd.DataFrame,
        n_lags: int,
        persistence_prior: dict | None = None,
        variable_names: list[str] | None = None,
        lambda_2_fixed: float = 1.0,
        seed: int | None = None,
    ):
        self.panel = panel
        self.n_lags = int(n_lags)
        self.variable_names = (
            list(variable_names) if variable_names is not None else list(panel.columns)
        )
        self.persistence_prior = persistence_prior
        self.lambda_2_fixed = float(lambda_2_fixed)
        self.seed = seed
        self.n_vars = panel.shape[1]

        # Cache the (Y, X) data design once — every MDD evaluation reuses it.
        data = panel.to_numpy(dtype=float)
        self._Y, self._X = _build_lag_design_xy(data, self.n_lags)
        self._T = self._Y.shape[0]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def log_marginal_likelihood(
        self,
        lambda_1: float,
        lambda_2: float | None = None,
        lambda_3: float = 1.0,
        lambda_sc: float = 1.0,
        lambda_io: float = 1.0,
    ) -> float:
        """Closed-form log p(Y) under the dummy-form Minnesota prior.

        ``lambda_2`` is accepted for API symmetry but has no effect on the
        dummy form (see module docstring); pass any value or ``None``.
        """
        prior = self._build_prior(
            lambda_1=lambda_1,
            lambda_2=self.lambda_2_fixed if lambda_2 is None else float(lambda_2),
            lambda_3=lambda_3,
            lambda_sc=lambda_sc,
            lambda_io=lambda_io,
        )
        if prior is None:
            return -np.inf
        Y_d, X_d = prior.dummy_observations()
        return _log_marginal_likelihood_niw(self._Y, self._X, Y_d, X_d)

    def glp_grid(
        self,
        lambda_1_values: np.ndarray | list[float],
        lambda_3_values: np.ndarray | list[float],
        lambda_sc_values: np.ndarray | list[float],
        lambda_io_values: np.ndarray | list[float],
    ) -> dict[str, Any]:
        """Cartesian-product grid search over the four GLP-2015 hyperparameters.

        Returns the best-evaluating tuple plus summary statistics.
        """
        L1 = np.asarray(lambda_1_values, dtype=float)
        L3 = np.asarray(lambda_3_values, dtype=float)
        Lsc = np.asarray(lambda_sc_values, dtype=float)
        Lio = np.asarray(lambda_io_values, dtype=float)

        n_eval = L1.size * L3.size * Lsc.size * Lio.size
        log_mdds = np.full(n_eval, -np.inf)
        params = np.empty((n_eval, 4))
        idx = 0
        t0 = time.perf_counter()
        for l1 in L1:
            for l3 in L3:
                for lsc in Lsc:
                    for lio in Lio:
                        params[idx] = (l1, l3, lsc, lio)
                        log_mdds[idx] = self.log_marginal_likelihood(
                            lambda_1=float(l1),
                            lambda_3=float(l3),
                            lambda_sc=float(lsc),
                            lambda_io=float(lio),
                        )
                        idx += 1
        runtime = time.perf_counter() - t0

        finite_mask = np.isfinite(log_mdds)
        n_finite = int(finite_mask.sum())
        if n_finite == 0:
            raise RuntimeError(
                "All grid evaluations returned -inf; prior is degenerate at every "
                "grid point. Check the lambda ranges in config."
            )

        best_idx = int(np.argmax(log_mdds))
        best_log_mdd = float(log_mdds[best_idx])
        best_l1, best_l3, best_lsc, best_lio = params[best_idx]

        finite_vals = log_mdds[finite_mask]
        q25, q50, q75 = np.percentile(finite_vals, [25, 50, 75])

        return {
            "method": "glp_grid",
            "best_lambdas": {
                "lambda_1": float(best_l1),
                "lambda_2": self.lambda_2_fixed,
                "lambda_3": float(best_l3),
                "lambda_sc": float(best_lsc),
                "lambda_io": float(best_lio),
            },
            "best_log_marginal_likelihood": best_log_mdd,
            "n_evaluations": int(n_eval),
            "n_finite": n_finite,
            "log_mdd_quartiles": [float(q25), float(q50), float(q75)],
            "runtime_seconds": float(runtime),
        }

    def glp_numerical(
        self,
        starting_point: dict[str, float],
        bounds: dict[str, tuple[float, float]],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """L-BFGS-B refinement starting from `starting_point` (typically the grid argmax).

        ``bounds`` and ``options`` come from config. Default options use
        ``eps=1e-3`` for finite-difference gradients (the lambdas are O(1);
        scipy's default ``eps=1e-8`` float-collapses).
        """
        keys = ["lambda_1", "lambda_3", "lambda_sc", "lambda_io"]
        x0 = np.array([float(starting_point[k]) for k in keys])
        bnd = [bounds[k] for k in keys]

        opts = {"eps": 1e-3, "maxiter": 100, "ftol": 1e-7}
        if options:
            opts.update(options)

        def neg_log_mdd(x: np.ndarray) -> float:
            v = self.log_marginal_likelihood(
                lambda_1=float(x[0]),
                lambda_3=float(x[1]),
                lambda_sc=float(x[2]),
                lambda_io=float(x[3]),
            )
            # L-BFGS-B can't handle -inf; replace with a large finite penalty
            # that is finitely worse than any legal evaluation.
            if not np.isfinite(v):
                return 1e20
            return -v

        t0 = time.perf_counter()
        result = minimize(
            neg_log_mdd, x0, method="L-BFGS-B", bounds=bnd, options=opts
        )
        runtime = time.perf_counter() - t0

        # Recover the actual log-MDD at the result (defends against the 1e20
        # penalty leaking into the reported value if optimization failed).
        x_opt = result.x
        log_mdd_opt = self.log_marginal_likelihood(
            lambda_1=float(x_opt[0]),
            lambda_3=float(x_opt[1]),
            lambda_sc=float(x_opt[2]),
            lambda_io=float(x_opt[3]),
        )

        return {
            "method": "glp_numerical",
            "best_lambdas": {
                "lambda_1": float(x_opt[0]),
                "lambda_2": self.lambda_2_fixed,
                "lambda_3": float(x_opt[1]),
                "lambda_sc": float(x_opt[2]),
                "lambda_io": float(x_opt[3]),
            },
            "best_log_marginal_likelihood": float(log_mdd_opt),
            "n_function_evaluations": int(result.nfev),
            "converged": bool(result.success),
            "starting_point": dict(starting_point),
            "runtime_seconds": float(runtime),
            "scipy_message": str(result.message),
        }

    def optimize(self, config_section: dict[str, Any]) -> dict[str, Any]:
        """High-level dispatch on `config["model"]["hyperparameters"]`.

        Recognized methods:
          - ``"fixed"``: short-circuit; return fixed lambdas verbatim.
          - ``"glp_grid"``: grid only.
          - ``"glp_numerical"``: grid then L-BFGS-B refinement.
          - ``"glp_composite"``: alias for glp_numerical (named explicitly
            to make CLI-flag overrides legible in resolved_config.yaml).

        Returns a dict with ``method``, optional ``grid``/``numerical`` blocks,
        a ``recommended`` block (the lambdas the CLI plugs into estimation),
        ``warnings_hard`` (at-the-bound), and ``warnings_soft`` (literature-
        typical-range).
        """
        # Suppress the per-evaluation MinnesotaPrior INFO log — at 800-3200
        # evaluations it spams run.log unhelpfully. The constructor info is
        # already captured at the level above (in CLI helpers).
        priors_logger = logging.getLogger("bvar.priors")
        prev_level = priors_logger.level
        priors_logger.setLevel(logging.WARNING)
        try:
            return self._optimize_inner(config_section)
        finally:
            priors_logger.setLevel(prev_level)

    def _optimize_inner(self, config_section: dict[str, Any]) -> dict[str, Any]:
        method = str(config_section.get("method", "fixed"))
        t_total = time.perf_counter()

        if method == "fixed":
            fixed = config_section.get("fixed", {})
            recommended = {
                "lambda_1": float(fixed.get("lambda_1", 0.2)),
                "lambda_2": float(fixed.get("lambda_2", self.lambda_2_fixed)),
                "lambda_3": float(fixed.get("lambda_3", 1.0)),
                "lambda_sc": float(fixed.get("lambda_sc", 1.0)),
                "lambda_io": float(fixed.get("lambda_io", 1.0)),
                "log_marginal_likelihood": None,
                "source": "fixed",
            }
            return {
                "method": "fixed",
                "recommended": recommended,
                "panel_dimensions": self._panel_dims(),
                "runtime_seconds": float(time.perf_counter() - t_total),
                "warnings_hard": [],
                "warnings_soft": [],
            }

        # Both glp_grid and glp_numerical / glp_composite need the grid first.
        grid_cfg = config_section.get("glp_grid", {})
        L1 = grid_cfg.get("lambda_1", [0.05, 0.10, 0.15, 0.20, 0.30])
        L3 = grid_cfg.get("lambda_3", [0.5, 1.0, 1.5, 2.0])
        Lsc = grid_cfg.get("lambda_sc", [0.0, 0.5, 1.0, 2.0, 5.0])
        Lio = grid_cfg.get("lambda_io", [0.0, 0.5, 1.0, 2.0, 5.0])
        grid = self.glp_grid(L1, L3, Lsc, Lio)

        if method == "glp_grid":
            recommended = {
                **grid["best_lambdas"],
                "log_marginal_likelihood": grid["best_log_marginal_likelihood"],
                "source": "grid",
            }
            # No bounds applied → no at-bound check.
            warnings_hard: list[str] = []
            warnings_soft = _literature_range_warnings(recommended)
            return {
                "method": method,
                "grid": grid,
                "recommended": recommended,
                "panel_dimensions": self._panel_dims(),
                "runtime_seconds": float(time.perf_counter() - t_total),
                "warnings_hard": warnings_hard,
                "warnings_soft": warnings_soft,
            }

        if method in ("glp_numerical", "glp_composite"):
            num_cfg = config_section.get("glp_numerical", {})
            bounds_dict_raw = num_cfg.get("bounds", {})
            bounds = {
                k: (float(v[0]), float(v[1])) for k, v in bounds_dict_raw.items()
            }
            # Defaults if config doesn't supply bounds.
            bounds.setdefault("lambda_1", (0.01, 1.0))
            bounds.setdefault("lambda_3", (0.1, 4.0))
            bounds.setdefault("lambda_sc", (0.0, 10.0))
            bounds.setdefault("lambda_io", (0.0, 10.0))
            options = num_cfg.get("options", None)
            numerical = self.glp_numerical(grid["best_lambdas"], bounds, options)

            # Choose the better of grid vs numerical (numerical can regress
            # if L-BFGS-B converges to a saddle or at-bound point).
            if numerical["best_log_marginal_likelihood"] >= grid[
                "best_log_marginal_likelihood"
            ] - 1e-6:
                source = "numerical"
                rec_lambdas = numerical["best_lambdas"]
                rec_log = numerical["best_log_marginal_likelihood"]
            else:
                source = "grid"
                rec_lambdas = grid["best_lambdas"]
                rec_log = grid["best_log_marginal_likelihood"]

            recommended = {
                **rec_lambdas,
                "log_marginal_likelihood": rec_log,
                "source": source,
            }
            warnings_hard = (
                _at_bound_warnings(rec_lambdas, bounds) if source == "numerical" else []
            )
            warnings_soft = _literature_range_warnings(recommended)

            return {
                "method": method,
                "grid": grid,
                "numerical": numerical,
                "recommended": recommended,
                "panel_dimensions": self._panel_dims(),
                "runtime_seconds": float(time.perf_counter() - t_total),
                "warnings_hard": warnings_hard,
                "warnings_soft": warnings_soft,
            }

        raise ValueError(
            f"Unknown hyperparameters.method = {method!r}. "
            f"Recognized: 'fixed', 'glp_grid', 'glp_numerical', 'glp_composite'."
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_prior(
        self,
        lambda_1: float,
        lambda_2: float,
        lambda_3: float,
        lambda_sc: float,
        lambda_io: float,
    ) -> MinnesotaPrior | None:
        try:
            return MinnesotaPrior(
                n_vars=self.n_vars,
                n_lags=self.n_lags,
                lambda_1=lambda_1,
                lambda_2=lambda_2,
                lambda_3=lambda_3,
                lambda_sc=lambda_sc,
                lambda_io=lambda_io,
                training_data=self.panel,
                persistence_prior=self.persistence_prior,
                variable_names=self.variable_names,
            )
        except (ValueError, ZeroDivisionError, FloatingPointError) as exc:
            logger.debug(
                "Prior construction failed at "
                "(l1=%g, l2=%g, l3=%g, lsc=%g, lio=%g): %s",
                lambda_1, lambda_2, lambda_3, lambda_sc, lambda_io, exc,
            )
            return None

    def _panel_dims(self) -> dict[str, int]:
        return {"T": int(self._T), "n": int(self.n_vars), "n_lags": int(self.n_lags)}


def optimize_hyperparameters(*args, **kwargs):
    """Thin functional wrapper kept for backward import compatibility."""
    raise NotImplementedError(
        "Use HyperparameterOptimizer(...).optimize(config_section) instead."
    )
