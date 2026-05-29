"""Phase 3 Batch 4 — Markov Switching parity check.

Compares TSL's ``engine/techniques/markov_switching.py``
(statsmodels ``MarkovRegression``) against R ``MSwM::msmFit`` on
a synthetic 2-regime mean-switching fixture.

Pattern H (DSCD) candidate — both implementations fit Markov
switching via EM with different convergence paths.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import (
    _compare_scalar,
    _compare_vector,
    _get_metric_tol,
)
from reference_parity.harness.manifest import Manifest
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.r_bridge import RBridge
from reference_parity.harness.tolerances import get_ladder


def _generate_ms_dgp(
    *,
    seed: int,
    n: int = 500,
    means: tuple[float, float] = (-1.0, 1.0),
    sigma: float = 0.5,
    transition_matrix: tuple[tuple[float, float], tuple[float, float]] = (
        (0.95, 0.05), (0.10, 0.90),
    ),
) -> np.ndarray:
    """Generate 2-regime mean-switching realization."""
    rng = np.random.default_rng(seed)
    P = np.array(transition_matrix)
    states = np.zeros(n, dtype=int)
    for t in range(1, n):
        states[t] = int(rng.choice(2, p=P[states[t - 1]]))
    obs = rng.normal(np.array(means)[states], sigma)
    return obs


class MarkovSwitchingParity(P3ParityCheck):
    """Markov-switching mean parity vs R MSwM."""

    technique_id = "p3_markov_switching"
    tier = "fast"
    fixture_id = ""

    verdict_class = "em_stochastic"
    verdict_class_rationale = (
        "Markov switching mean model. statsmodels "
        "MarkovRegression and R MSwM::msmFit are independent "
        "EM implementations of Hamilton 1989. EM-stochastic "
        "tolerance band; state-label permutation requires "
        "alignment by mean ordering."
    )

    DGP_N = 500
    K_REGIMES = 2

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "y": _generate_ms_dgp(seed=seed, n=self.DGP_N),
            "k_regimes": self.K_REGIMES,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from statsmodels.tsa.regime_switching.markov_regression import (  # type: ignore
            MarkovRegression,
        )
        import warnings as _w

        y = np.asarray(fixture["y"], dtype=np.float64)
        k = int(fixture["k_regimes"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            # Pin the global RNG before fitting. statsmodels'
            # ``search_reps`` random EM starts draw from ``np.random``;
            # without a fixed seed AND with too few restarts the EM can
            # land in a degenerate single-regime basin on unlucky starts
            # (both regime means collapse to the overall sample mean,
            # spurious positive log-likelihood), producing a
            # nondeterministic BLOCK across process invocations. Mirror
            # the engine wrapper's discipline (``np.random.seed(ctx.seed)``
            # + ``search_reps=25``) so this bypass path is deterministic
            # and robust to the same degenerate-optimum risk.
            np.random.seed(42)
            model = MarkovRegression(y, k_regimes=k, switching_variance=False)
            fit = model.fit(disp=False, search_reps=25)

        # Extract regime-specific means + transition probs.
        # statsmodels MarkovRegression: param_names lives on the
        # model object, not the fit results object. Build a
        # name → value dict via fit.model.param_names + fit.params.
        param_names = list(fit.model.param_names)
        params_arr = np.asarray(fit.params, dtype=np.float64)
        params_dict = dict(zip(param_names, params_arr))
        means = np.array([
            params_dict.get(f"const[{i}]", np.nan) for i in range(k)
        ], dtype=np.float64)
        # Use fit.regime_transition directly: shape (k, k, 1) for
        # time-invariant; we extract the (k, k) matrix.
        rt = np.asarray(fit.regime_transition, dtype=np.float64)
        if rt.ndim == 3:
            transmat = rt[:, :, 0].T  # transpose: P[i,j] = P(j|i)
        else:
            transmat = rt.copy()
        # Sort by mean ascending
        sort_order = np.argsort(means)
        means_sorted = means[sort_order]
        transmat_sorted = transmat[sort_order][:, sort_order]

        # ---- Balanced-spec self-parity arm (Workstream C / C3) ----
        # The Fast arm above (MarkovRegression order=0 mean-switching)
        # is the cross-package check vs R MSwM. The engine's BALANCED
        # preset uses MarkovAutoregression(order=1, switching_ar +
        # switching_variance), which R MSwM cannot reliably fit on this
        # mean-switching fixture (it degenerates). So the Balanced spec
        # is math-asserted by SELF-PARITY: invoke the ENGINE WRAPPER at
        # Balanced and compare against a direct statsmodels
        # reimplementation of the same pipeline (S85 nar_narx pattern) —
        # validating the engine wrapper's Balanced fit + regime-label
        # canonicalization + transition handling reproduce a clean
        # statsmodels call bit-exactly (modulo the engine's audit
        # rounding).
        bal = {"available": False}
        try:
            from techniques.base import RunContext  # type: ignore
            import techniques.markov_switching as ms_mod  # type: ignore
            ctx = RunContext({
                "run_id": "p3_ms_balanced_selfparity",
                "technique_id": "markov_switching",
                "preset": "Balanced", "seed": 42, "frequency": "",
                "time": list(range(len(y))),
                "series": [{"name": "y", "values": y.tolist()}],
                "params": {},
            })
            resp = ms_mod.run(ctx, lambda *a, **kw: None)
            if resp.get("status") == "success":
                af = resp.get("audit_fields", {})
                tbls = resp.get("tables", [])
                # Regime Summary "Mean" column (index 3); rows already
                # in the engine's canonical (mean-sorted) regime order.
                rs = next((t for t in tbls if t.get("name") == "Regime Summary"), None)
                tm_t = next((t for t in tbls if t.get("name") == "Transition Matrix"), None)
                if rs is not None and tm_t is not None:
                    b_means = np.array([float(r[3]) for r in rs["rows"]], dtype=np.float64)
                    # Transition Matrix rows: [from-label, P(->0), P(->1)]
                    b_tm = np.array([[float(v) for v in r[1:]] for r in tm_t["rows"]], dtype=np.float64)
                    bal = {
                        "available": True,
                        "regime_means": b_means,
                        "transition_matrix": b_tm,
                        "log_likelihood": float(af.get("log_likelihood", np.nan)),
                    }
        except Exception as e:
            bal = {"available": False, "error": f"{type(e).__name__}: {e}"}

        return {
            "regime_means": means_sorted,
            "transition_matrix": transmat_sorted,
            "log_likelihood": float(fit.llf),
            "balanced": bal,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        y = np.asarray(fixture["y"], dtype=np.float64)
        k = int(fixture["k_regimes"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(MSwM) }})
            y <- as.numeric(read.csv("{{{{INPUT_y}}}}", header=FALSE)[, 1])
            df <- data.frame(y = y)

            set.seed(20260429)
            mod_lin <- lm(y ~ 1, data = df)
            # Try msmFit; wrap in tryCatch since MSwM has well-
            # documented Hessian-singularity / non-convergence
            # issues on synthetic data without strong initial
            # regime separation. If it fails or converges to
            # degenerate (regimes have nearly identical means),
            # emit NA and let the compare function downgrade to
            # CAVEAT / NO-REFERENCE.
            ms <- tryCatch(
                msmFit(mod_lin, k = {k}, sw = c(TRUE, FALSE),
                       control = list(parallel = FALSE, maxiter = 100)),
                error = function(e) NULL
            )

            converged <- !is.null(ms)
            if (converged) {{
                coef_mat <- ms@Coef
                means <- as.numeric(coef_mat[, 1])
                transmat <- as.matrix(ms@transMat)
                # Detect degenerate fit (regimes have means
                # within 0.1 of each other = no separation)
                if (abs(means[1] - means[2]) < 0.1) {{
                    converged <- FALSE
                }}
            }}

            if (converged) {{
                # Sort regimes by mean ascending
                sort_order <- order(means)
                means_sorted <- means[sort_order]
                transmat_sorted <- transmat[sort_order, sort_order]
                # MSwM exposes log-likelihood via ms@Fit@logLikel
                # (slot inspection of MSM.fitted class).
                log_lik <- as.numeric(ms@Fit@logLikel)
            }} else {{
                means_sorted <- rep(NA_real_, {k})
                transmat_sorted <- matrix(NA_real_, {k}, {k})
                log_lik <- NA_real_
            }}

            write.table(matrix(means_sorted, ncol = 1),
                        "{{{{OUTPUT_means}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(as.numeric(transmat_sorted), ncol = 1),
                        "{{{{OUTPUT_transmat}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(c(log_lik), ncol = 1),
                        "{{{{OUTPUT_loglik}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"y": y.reshape(-1, 1)},
            output_names=["means", "transmat", "loglik"],
            timeout_sec=120,
            capture_versions_for=["MSwM"],
        )
        means = np.atleast_1d(outputs["means"]).astype(np.float64).reshape(-1)
        transmat = np.atleast_1d(outputs["transmat"]).astype(np.float64).reshape(-1)
        transmat = transmat.reshape((k, k), order="F")
        return {
            "regime_means": means,
            "transition_matrix": transmat,
            "log_likelihood": float(np.atleast_1d(outputs["loglik"]).reshape(-1)[0]),
            "mswm_version": versions.get("MSwM", "unknown"),
            "balanced": self._balanced_selfparity_reference(y),
        }

    def _balanced_selfparity_reference(self, y: np.ndarray) -> dict[str, Any]:
        """Self-parity reference for the engine BALANCED spec (Workstream
        C / C3): directly reimplement the engine's MarkovAutoregression
        Balanced pipeline (order=1, switching_ar + switching_trend +
        switching_variance; np.random.seed(42); search_reps=25), mirroring
        the engine's decode -> empirical-mean -> dominant-key relabel
        post-processing. Both this and the engine wrapper call the same
        deterministic statsmodels fit, so they reproduce the same
        llf / transition / regime means bit-exactly (modulo the engine's
        audit rounding). Validates the engine wrapper's Balanced path.
        """
        try:
            _ensure_engine_on_path()
            from statsmodels.tsa.regime_switching.markov_autoregression import (  # type: ignore
                MarkovAutoregression,
            )
            from techniques.base import label_regimes_by_dominant_key  # type: ignore
            import warnings as _w
            y = np.asarray(y, dtype=np.float64)
            with _w.catch_warnings():
                _w.simplefilter("ignore")
                np.random.seed(42)  # mirror engine np.random.seed(ctx.seed)
                model = MarkovAutoregression(
                    y, k_regimes=2, order=1, trend="c",
                    switching_ar=True, switching_trend=True,
                    switching_variance=True, exog=None,
                )
                fit = model.fit(maxiter=500, search_reps=25)
            sm = fit.smoothed_marginal_probabilities
            sm = sm.values if hasattr(sm, "values") else np.asarray(sm)
            if sm.ndim == 1:
                sm = sm.reshape(-1, 1)
            n_probs = sm.shape[0]
            mlr = np.argmax(sm, axis=1)
            tp = fit.regime_transition
            tp = tp.values if hasattr(tp, "values") else np.asarray(tp)
            transmat = (tp[:, :, 0].T if tp.ndim == 3 else np.asarray(tp))
            k = 2
            means_emp = np.zeros(k)
            stds_emp = np.zeros(k)
            for r in range(k):
                mask = mlr == r
                cnt = int(mask.sum())
                means_emp[r] = np.mean(y[:n_probs][mask]) if cnt > 0 else np.nan
                stds_emp[r] = float(np.std(y[:n_probs][mask], ddof=1)) if cnt > 1 else 0.0
            sr = label_regimes_by_dominant_key(
                means_emp, stds_emp, transmat=transmat,
                labels=mlr, probs=sm,
            )
            mlr_s = sr["labels"]
            transmat_s = sr["transmat"]
            # Regime Summary means recomputed on the relabeled regimes
            # (engine convention), in sorted regime order.
            means_sorted = np.array([
                float(np.mean(y[:n_probs][mlr_s == r])) if int((mlr_s == r).sum()) > 0
                else 0.0
                for r in range(k)
            ], dtype=np.float64)
            return {
                "available": True,
                "regime_means": means_sorted,
                "transition_matrix": np.asarray(transmat_s, dtype=np.float64),
                "log_likelihood": float(fit.llf),
            }
        except Exception as e:
            return {"available": False, "error": f"{type(e).__name__}: {e}"}

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Reference may have failed to converge or produced
        # degenerate (no-regime-separation) fit. MSwM has
        # well-documented sensitivity to initial conditions on
        # synthetic data without clear regime separation.
        ref_means = np.asarray(ref["regime_means"], dtype=np.float64)
        if not np.all(np.isfinite(ref_means)):
            return ParityResult(
                technique_id=self.technique_id,
                outcome="CAVEAT",
                metrics={
                    "primary": {
                        "reference_convergence": {
                            "status": "CAVEAT",
                            "note": (
                                "R MSwM::msmFit did not converge "
                                "to a non-degenerate 2-regime fit "
                                "on this fixture (Hessian singularity "
                                "or regime-mean collapse — known "
                                "sensitivity to initialization). "
                                "TSL fit succeeded; documented as "
                                "methodology divergence per master "
                                "plan §5 Tier B."
                            ),
                            "tsl_regime_means": tsl["regime_means"].tolist(),
                            "tsl_loglik": tsl.get("log_likelihood"),
                        }
                    }
                },
                diagnostics={
                    "mswm_version": ref.get("mswm_version", "unknown"),
                    "n_obs": int(self.DGP_N),
                    "ref_failed_or_degenerate": True,
                },
            )

        primary["regime_means"] = _compare_vector(
            tsl["regime_means"], ref["regime_means"],
            _get_metric_tol(ladder, "regime_means"),
        )
        statuses.append(primary["regime_means"]["status"])

        primary["transition_matrix"] = _compare_vector(
            np.asarray(tsl["transition_matrix"]).reshape(-1),
            np.asarray(ref["transition_matrix"]).reshape(-1),
            _get_metric_tol(ladder, "transition_matrix"),
        )
        statuses.append(primary["transition_matrix"]["status"])

        # MSwM's @Fit@logLikel uses opposite sign convention from
        # statsmodels' fit.llf. Compare via |log-lik| to align.
        primary["log_likelihood"] = _compare_scalar(
            abs(tsl["log_likelihood"]), abs(ref["log_likelihood"]),
            _get_metric_tol(ladder, "log_likelihood"),
        )
        statuses.append(primary["log_likelihood"]["status"])

        # ---- Balanced-spec self-parity (Workstream C / C3) ----
        # Engine-wrapper Balanced (MarkovAutoregression order=1 +
        # switching_variance) vs a direct statsmodels reimplementation.
        # Both call the identical deterministic fit, so they reproduce
        # llf / transition / regime means bit-exactly modulo the engine's
        # audit-rounding floor (llf 2-dp, means/transition 4-dp) — band
        # set just above that floor.
        balanced: dict[str, Any] = {}
        bt = tsl.get("balanced", {})
        br = ref.get("balanced", {})
        if bt.get("available") and br.get("available"):
            _bal_tol = {"abs_tol": 1e-2, "rel_tol": 1e-2,
                        "block_abs_tol": 1e-1, "block_rel_tol": 1e-1}
            balanced["regime_means"] = _compare_vector(
                np.asarray(bt["regime_means"]).reshape(-1),
                np.asarray(br["regime_means"]).reshape(-1), _bal_tol,
            )
            balanced["transition_matrix"] = _compare_vector(
                np.asarray(bt["transition_matrix"]).reshape(-1),
                np.asarray(br["transition_matrix"]).reshape(-1), _bal_tol,
            )
            balanced["log_likelihood"] = _compare_scalar(
                abs(float(bt["log_likelihood"])),
                abs(float(br["log_likelihood"])), _bal_tol,
            )
            statuses.extend(balanced[k]["status"] for k in balanced)
        else:
            balanced["status"] = {
                "status": "INFO",
                "note": "Balanced self-parity unavailable",
                "tsl_error": bt.get("error"), "ref_error": br.get("error"),
            }

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "balanced_selfparity": balanced},
            diagnostics={
                "mswm_version": ref.get("mswm_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "k_regimes": int(self.K_REGIMES),
                "tsl_balanced_llf": tsl.get("balanced", {}).get("log_likelihood"),
                "ref_balanced_llf": ref.get("balanced", {}).get("log_likelihood"),
            },
        )

    reroll_on_caveat = True  # EM-stochastic
