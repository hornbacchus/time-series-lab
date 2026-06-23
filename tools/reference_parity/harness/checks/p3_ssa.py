"""Phase 3 Batch 7 — SSA (Singular Spectrum Analysis) parity check.

Compares TSL ``engine/techniques/ssa_model.py`` (numpy SVD on
Hankel trajectory matrix) against a from-scratch reference
implementing the canonical Broomhead-King 1986 / Golyandina-
Zhigljavsky 2013 SSA algorithm. Both use numpy.linalg.svd
internally; Pattern A bit-exact target on eigenvalues, modulo
the sign-canonicalization that ``ssa_model.py:flip_sign_svd``
applies.

**Why self-parity vs ``pyts.decomposition``:** pyts has a
SingularSpectrumAnalysis estimator but its sklearn-style API
expects (n_samples, n_features) input shape and applies SSA
per-row, not per-time-series. Translating to a 1-D series
parity test is awkward; the from-scratch reference follows
Golyandina-Zhigljavsky 2013 directly.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_scalar, _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder


def _generate_ssa_dgp(
    *, seed: int, n: int = 200,
) -> np.ndarray:
    """Trend + sinusoidal + noise (standard SSA test fixture)."""
    rng = np.random.default_rng(seed)
    t = np.arange(n, dtype=np.float64)
    trend = 0.02 * t
    seasonal = 1.0 * np.sin(2 * np.pi * t / 12)
    noise = 0.3 * rng.standard_normal(n)
    return trend + seasonal + noise


def _ssa_reference(
    y: np.ndarray, *, L: int, n_components: int,
) -> dict[str, np.ndarray]:
    """Reference SSA implementation per Golyandina-Zhigljavsky
    2013. Same math as TSL ``ssa_model.py``."""
    n = len(y)
    K = n - L + 1
    # Step 1: trajectory matrix
    X = np.zeros((L, K))
    for i in range(K):
        X[:, i] = y[i:i + L]
    # Step 2: SVD
    U, sigma, Vt = np.linalg.svd(X, full_matrices=False)
    U = U[:, :n_components]
    sigma = sigma[:n_components]
    Vt = Vt[:n_components, :]
    # Sign normalize per max-abs-positive convention
    for i in range(n_components):
        max_abs_idx = int(np.argmax(np.abs(U[:, i])))
        if U[max_abs_idx, i] < 0:
            U[:, i] = -U[:, i]
            Vt[i, :] = -Vt[i, :]
    eigenvalues = sigma ** 2
    return {
        "singular_values": sigma,
        "eigenvalues": eigenvalues,
        "U": U,
        "Vt": Vt,
    }


class SsaParity(P3ParityCheck):
    """SSA parity vs from-scratch numpy reference."""

    technique_id = "p3_ssa"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "SSA is closed-form: build Hankel trajectory matrix, "
        "apply SVD, group eigentriples, diagonal-average "
        "back to time series. TSL and reference both call "
        "numpy.linalg.svd on identical Hankel matrix; "
        "eigenvalues are unique and singular vectors are "
        "unique up to sign. After sign-canonicalization, "
        "machine-precision parity expected."
    )

    DGP_N = 200
    L_FACTOR = 2  # window length L = N // L_FACTOR
    N_COMPONENTS = 10

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"y": _generate_ssa_dgp(
            seed=seed, n=self.DGP_N,
        )}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        # Phase 4a-harden #1: invoke the ENGINE (was a _ssa_reference MIRROR that
        # never ran engine code). The engine does not expose U/Vt (eigenvectors),
        # so the comparison realigns to the engine's PUBLISHED spectrum -- the
        # "Singular Values & Explained Variance" table (Singular Value 6dp,
        # Eigenvalue 4dp). window_length + n_components are pinned to the
        # reference's (L=N//2, 10) so the SVD is over the identical Hankel matrix.
        _ensure_engine_on_path()
        from techniques.base import RunContext  # type: ignore
        import techniques.ssa_model as ssa_mod  # type: ignore
        y = np.asarray(fixture["y"], dtype=np.float64)
        L = len(y) // self.L_FACTOR
        ctx = RunContext({
            "run_id": "p3_ssa", "technique_id": "ssa_model",
            "preset": "Balanced", "seed": 42, "frequency": "",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {"window_length": L, "n_components": self.N_COMPONENTS},
        })
        resp = ssa_mod.run(ctx, lambda *a, **k: None)
        if resp.get("status") != "success":
            raise RuntimeError(f"engine ssa_model failed: {resp.get('error_message')}")
        tbl = next(t for t in resp.get("tables", [])
                   if t.get("name") == "Singular Values & Explained Variance")
        rows = tbl["rows"]
        return {
            "singular_values": np.array([float(r[1]) for r in rows]),  # 6dp
            "eigenvalues": np.array([float(r[2]) for r in rows]),       # 4dp
            "engine_L": resp.get("audit_fields", {}).get("window_length"),
        }

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        y = np.asarray(fixture["y"], dtype=np.float64)
        L = len(y) // self.L_FACTOR
        out = _ssa_reference(y, L=L, n_components=self.N_COMPONENTS)
        return {
            "singular_values": out["singular_values"],
            "eigenvalues": out["eigenvalues"],
            "numpy_version": np.__version__,
        }

    def compare(
        self, tsl: dict[str, Any], ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []
        # Eigenvectors (U/Vt) are not exposed by the engine; compare the published
        # spectrum (singular values + eigenvalues) -- the SVD core of SSA. Engine
        # arm is 4-6dp-rounded (table floor), reference is full precision.
        for k in ("singular_values", "eigenvalues"):
            n_common = min(len(tsl[k]), len(ref[k]))
            primary[k] = _compare_vector(
                np.asarray(tsl[k])[:n_common], np.asarray(ref[k])[:n_common],
                ladder["primary"],
            )
            statuses.append(primary[k]["status"])
        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "n_obs": int(self.DGP_N),
                "L": int(self.DGP_N // self.L_FACTOR),
                "n_components": int(self.N_COMPONENTS),
                "numpy_version": ref.get("numpy_version", "unknown"),
            },
        )
