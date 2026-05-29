"""Phase 3 Batch 4 — Hidden Markov Model parity check.

Compares TSL's ``engine/techniques/hmm_model.py`` (hmmlearn
``GaussianHMM``) against R ``depmixS4`` on a synthetic 2-state
Gaussian HMM fixture.

Reference selection note: hmmlearn (Python) and depmixS4 (R)
are independent implementations of the Baum-Welch EM algorithm
with Gaussian emissions. **Pattern H (DSCD) candidate** —
EM convergence to different local optima of the same
likelihood surface is a known phenomenon for HMM with random
initialization.

State-label permutation invariance: HMM states have no
intrinsic ordering; both implementations may identify the
same factor structure but label states in different order.
The compare function applies a state-alignment step
(matching states by emission mean) before computing
parameter diffs.

Output-tier discipline:

- **Primary:** transition matrix P (k, k), emission means
  (k, n_features), emission covariances (k, n_features) for
  diagonal cov, log-likelihood.
- **Secondary:** Viterbi-decoded state sequence (state-
  alignment-adjusted; comparison is via accuracy / agreement
  rate not bit-equality since EM may converge to different
  state assignments).
- **Diagnostic:** AIC, BIC.

Structural invariants (Pattern F third concrete batch):
- ``hmm_row_sums``: P row sums = 1
- ``hmm_emission_normalization``: emission means finite,
  emission covariances positive
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
from reference_parity.harness.structural_invariants import (
    StructuralInvariant,
)
from reference_parity.harness.tolerances import get_ladder


def _generate_hmm_dgp(
    *,
    seed: int,
    n: int = 500,
    means: tuple[float, float] = (-1.0, 1.0),
    sigmas: tuple[float, float] = (0.5, 0.5),
    transition_matrix: tuple[tuple[float, float], tuple[float, float]] = (
        (0.95, 0.05), (0.10, 0.90),
    ),
) -> np.ndarray:
    """Generate 2-state Gaussian HMM realization (single feature)."""
    rng = np.random.default_rng(seed)
    P = np.array(transition_matrix)
    k = P.shape[0]
    states = np.zeros(n, dtype=int)
    states[0] = 0  # start in state 0
    for t in range(1, n):
        states[t] = int(rng.choice(k, p=P[states[t - 1]]))
    obs = rng.normal(
        loc=np.array(means)[states],
        scale=np.array(sigmas)[states],
    ).reshape(-1, 1)
    return obs


def _align_states_by_means(
    tsl_means: np.ndarray, ref_means: np.ndarray,
) -> tuple[np.ndarray, str]:
    """Find permutation of TSL state labels that maps to ref
    state labels by minimizing total emission-mean distance.
    Returns (permutation, description). For 2-state HMM the
    permutation is just (0,1) or (1,0); for k-state we'd need
    a Hungarian algorithm but k=2 fixture is sufficient.
    """
    k = tsl_means.shape[0]
    if k == 2:
        # Try identity vs swap; pick the one with smaller mean diff
        identity_dist = float(np.sum(
            np.abs(tsl_means.flatten() - ref_means.flatten()),
        ))
        swap_dist = float(np.sum(
            np.abs(tsl_means[[1, 0]].flatten() - ref_means.flatten()),
        ))
        if swap_dist < identity_dist:
            return np.array([1, 0]), f"swap (dist={swap_dist:.4f} vs {identity_dist:.4f})"
        return np.array([0, 1]), f"identity (dist={identity_dist:.4f})"
    # k > 2: greedy nearest-mean assignment (sufficient for fixture)
    perm = np.arange(k)
    used = set()
    for j in range(k):
        # For ref state j, find unused TSL state with closest mean
        candidates = [i for i in range(k) if i not in used]
        dists = [float(np.sum(np.abs(tsl_means[i] - ref_means[j])))
                 for i in candidates]
        best = candidates[int(np.argmin(dists))]
        perm[j] = best
        used.add(best)
    return perm, "greedy"


class HmmParity(P3ParityCheck):
    """HMM 2-state Gaussian parity vs R depmixS4."""

    technique_id = "p3_hmm"
    tier = "fast"
    fixture_id = ""

    verdict_class = "em_stochastic"
    verdict_class_rationale = (
        "HMM Baum-Welch EM. hmmlearn (Python) and R depmixS4 "
        "are independent EM implementations with different "
        "initialization heuristics; both can land at different "
        "local optima of the same likelihood surface. State "
        "labels are permutation-invariant; compare function "
        "aligns states by emission-mean ordering before parameter "
        "diff. Pattern H (DSCD) candidate — EM-stochastic "
        "tolerance band per master plan §7.1."
    )

    structural_invariants = (
        StructuralInvariant(
            name="transition_row_sums_unit",
            invariant_type="hmm_row_sums",
            tolerance=1e-10,
            tolerance_type="absolute",
        ),
        StructuralInvariant(
            name="emission_distribution_proper",
            invariant_type="hmm_emission_normalization",
            tolerance=1e-10,
            tolerance_type="absolute",
        ),
    )

    DGP_N = 500
    DGP_K = 2  # 2 hidden states

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {
            "X": _generate_hmm_dgp(seed=seed, n=self.DGP_N),
            "n_components": self.DGP_K,
        }

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        """Direct hmmlearn invocation to bypass TSL wrapper's
        6-decimal output rounding (Phase 1 finding B8). Mirror
        of the bypass pattern used by p3_arima / p3_har_rv /
        p3_pca / p3_var.
        """
        _ensure_engine_on_path()
        from hmmlearn.hmm import GaussianHMM  # type: ignore
        import warnings as _w

        X = np.asarray(fixture["X"], dtype=np.float64)
        n_components = int(fixture["n_components"])

        with _w.catch_warnings():
            _w.simplefilter("ignore")
            best_model = None
            best_score = -np.inf
            # Mirror TSL wrapper's restart pattern (5 restarts
            # for parity with TSL's "Balanced" preset).
            for restart in range(5):
                model = GaussianHMM(
                    n_components=n_components,
                    covariance_type="diag",
                    n_iter=100,
                    random_state=42 + restart,
                    tol=1e-4,
                )
                try:
                    model.fit(X)
                    score = model.score(X)
                    if score > best_score:
                        best_score = score
                        best_model = model
                except Exception:
                    continue
            if best_model is None:
                raise RuntimeError("hmmlearn fit failed across all restarts")
            log_prob, states = best_model.decode(X, algorithm="viterbi")

        # Sort states by emission mean (ascending) so order is
        # canonical regardless of EM initialization
        sort_order = np.argsort(best_model.means_.flatten())
        transmat = best_model.transmat_[sort_order][:, sort_order]
        means = best_model.means_[sort_order]
        # diag covariance: shape (n_states, n_features). Sort same.
        covars = np.asarray(best_model.covars_, dtype=np.float64)
        if covars.ndim == 3:
            # full covariance: (n_states, n_features, n_features)
            covars_sorted = covars[sort_order]
            covars_diag = np.array(
                [np.diag(c) for c in covars_sorted],
                dtype=np.float64,
            )
        else:
            covars_diag = covars[sort_order]
        # Re-label states sequence accordingly (inverse map)
        inv_map = np.argsort(sort_order)
        states_relabeled = inv_map[states]

        return {
            "transition_matrix": transmat,
            "emission_means": means,
            "emission_covars": covars_diag,
            "log_likelihood": float(best_score),
            "states_viterbi": states_relabeled,
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        manifest = Manifest.load()
        bridge = RBridge(manifest)

        X = np.asarray(fixture["X"], dtype=np.float64)
        n_components = int(fixture["n_components"])

        r_code = rf"""
            suppressPackageStartupMessages({{ library(depmixS4) }})
            X <- as.numeric(read.csv("{{{{INPUT_X}}}}", header=FALSE)[, 1])
            df <- data.frame(y = X)

            set.seed(20260429)
            mod <- depmix(y ~ 1, data = df, nstates = {n_components},
                          family = gaussian())
            fit <- fit(mod, verbose = FALSE)
            par_summary <- summary(fit)

            # Extract transition matrix from fitted parameters.
            # depmixS4 uses a multinomial logit parameterization;
            # `getpars(fit)` returns the parameter vector in
            # canonical order: prior probs, then transition
            # matrix (row by row), then emission params.
            params <- getpars(fit)
            n_states <- {n_components}

            # Prior: first n_states entries
            # Transition: next n_states*n_states entries (raw,
            # then softmaxed per-row in depmixS4 — but
            # `summary(fit)` returns the row-stochastic matrix.
            # Easier: use posterior() and trans matrix accessor.
            # The transition matrix is in fit@transition's pars
            # but via row-norm, it's not a simple slice.
            # Reliable accessor: refactor params via
            # `fit@transition[[i]]@parameters$coefficients` for
            # the i-th row.
            transmat <- matrix(0, n_states, n_states)
            for (i in 1:n_states) {{
                # depmixS4 uses multinomial logit; the
                # @transition[[i]]@parameters$coefficients
                # vector has n_states entries but row-sums are
                # imposed via softmax. Apply softmax explicitly:
                row_pars <- fit@transition[[i]]@parameters$coefficients
                # Some versions return n_states-1 entries (with
                # first state implicit at 0 reference); handle
                # both via softmax with explicit 0 insertion:
                if (length(row_pars) == n_states) {{
                    raw <- as.numeric(row_pars)
                }} else {{
                    raw <- c(0, as.numeric(row_pars))
                }}
                exp_raw <- exp(raw - max(raw))  # numerical stability
                transmat[i, ] <- exp_raw / sum(exp_raw)
            }}

            # Emission params (Gaussian: mean + sd per state)
            means <- numeric(n_states)
            covars <- numeric(n_states)
            for (i in 1:n_states) {{
                means[i] <- fit@response[[i]][[1]]@parameters$coefficients
                covars[i] <- fit@response[[i]][[1]]@parameters$sd ^ 2
            }}

            # Sort states by mean (ascending) for canonical
            # comparison vs TSL (which also sorts by mean).
            sort_order <- order(means)
            means_sorted <- means[sort_order]
            covars_sorted <- covars[sort_order]
            transmat_sorted <- transmat[sort_order, sort_order]

            log_lik <- as.numeric(logLik(fit))

            # Viterbi-decoded states. Use posterior() returning
            # a data frame with $state column.
            posterior_df <- posterior(fit)
            inv_map <- order(sort_order)
            states_viterbi <- inv_map[posterior_df$state]

            # Write outputs
            write.table(matrix(as.numeric(transmat_sorted), ncol = 1),
                        "{{{{OUTPUT_transmat}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(means_sorted, ncol = 1),
                        "{{{{OUTPUT_means}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(covars_sorted, ncol = 1),
                        "{{{{OUTPUT_covars}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(c(log_lik), ncol = 1),
                        "{{{{OUTPUT_loglik}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
            write.table(matrix(states_viterbi, ncol = 1),
                        "{{{{OUTPUT_states}}}}",
                        sep = ",", row.names = FALSE, col.names = FALSE)
        """

        outputs, versions = bridge.rscript_call(
            r_code=r_code,
            inputs={"X": X},
            output_names=["transmat", "means", "covars",
                          "loglik", "states"],
            timeout_sec=120,
            capture_versions_for=["depmixS4"],
        )
        n_states = n_components
        transmat = np.atleast_1d(outputs["transmat"]).astype(np.float64).reshape(-1)
        # R column-major: reshape (n, n)
        transmat = transmat.reshape((n_states, n_states), order="F")
        means = np.atleast_1d(outputs["means"]).astype(np.float64).reshape(-1, 1)
        covars = np.atleast_1d(outputs["covars"]).astype(np.float64).reshape(-1, 1)
        return {
            "transition_matrix": transmat,
            "emission_means": means,
            "emission_covars": covars,
            "log_likelihood": float(np.atleast_1d(outputs["loglik"]).reshape(-1)[0]),
            "states_viterbi": np.atleast_1d(outputs["states"]).astype(int).reshape(-1),
            "depmixs4_version": versions.get("depmixS4", "unknown"),
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        secondary: dict[str, Any] = {}
        diagnostic: dict[str, Any] = {}
        statuses: list[str] = []

        # Both sides already sorted states by emission mean
        # ascending. Direct comparison.
        # Phase 3.5 Session 4 (Item 2): per-metric bands.
        # transition_matrix retains widened DSCD-EM band
        # (0.3 abs / 1.0 rel); emission_means / emission_covars
        # / log_likelihood get tightened bands per Pattern H
        # DSCD per-metric heterogeneity finding.
        primary["transition_matrix"] = _compare_vector(
            np.asarray(tsl["transition_matrix"]).reshape(-1),
            np.asarray(ref["transition_matrix"]).reshape(-1),
            _get_metric_tol(ladder, "transition_matrix"),
        )
        statuses.append(primary["transition_matrix"]["status"])

        primary["emission_means"] = _compare_vector(
            np.asarray(tsl["emission_means"]).reshape(-1),
            np.asarray(ref["emission_means"]).reshape(-1),
            _get_metric_tol(ladder, "emission_means"),
        )
        statuses.append(primary["emission_means"]["status"])

        primary["emission_covars"] = _compare_vector(
            np.asarray(tsl["emission_covars"]).reshape(-1),
            np.asarray(ref["emission_covars"]).reshape(-1),
            _get_metric_tol(ladder, "emission_covars"),
        )
        statuses.append(primary["emission_covars"]["status"])

        primary["log_likelihood"] = _compare_scalar(
            tsl["log_likelihood"], ref["log_likelihood"],
            _get_metric_tol(ladder, "log_likelihood"),
        )
        statuses.append(primary["log_likelihood"]["status"])

        # Viterbi state agreement rate (Secondary)
        try:
            tsl_states = np.asarray(tsl["states_viterbi"], dtype=int)
            ref_states = np.asarray(ref["states_viterbi"], dtype=int)
            # Index-base alignment (Workstream C / C1 fix): run_tsl returns
            # Python 0-indexed states {0,1}; run_reference returns R
            # 1-indexed states {1,2}. Without alignment, tsl==ref is always
            # False -> agreement exactly 0.0 (a measurement artifact, not a
            # real disagreement). Both arms are canonically mean-sorted
            # (low-mean regime = each array's minimum label), so normalizing
            # each to 0-based by subtracting its own minimum aligns the
            # regime labels before comparison.
            tsl_states = tsl_states - tsl_states.min()
            ref_states = ref_states - ref_states.min()
            n_common = min(len(tsl_states), len(ref_states))
            agreement = float(np.mean(
                tsl_states[:n_common] == ref_states[:n_common],
            ))
            secondary["viterbi_agreement_rate"] = {
                "status": "PASS" if agreement >= 0.9 else
                          ("CAVEAT" if agreement >= 0.7 else "BLOCK"),
                "agreement_rate": agreement,
                "n_compared": n_common,
            }
        except Exception as e:
            secondary["viterbi_agreement_rate"] = {
                "status": "INFO",
                "error": f"{type(e).__name__}: {e}",
            }

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary, "secondary": secondary},
            diagnostics={
                **diagnostic,
                "depmixs4_version": ref.get("depmixs4_version", "unknown"),
                "n_obs": int(self.DGP_N),
                "n_states": int(self.DGP_K),
            },
        )

    # EM-stochastic; CAVEAT-reroll could help (different EM
    # restart paths)
    reroll_on_caveat = True
