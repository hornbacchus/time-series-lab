"""3b HAR-CJ realized-volatility parity check.

Validates TSL's ``har_cj`` wrapper against a from-scratch
Python reimplementation of Andersen-Bollerslev-Diebold 2007
HAR-CJ + Huang-Tauchen 2005 BNS jump-detection test on a
seeded synthetic RV/BV/TQ fixture.

OLS is closed-form deterministic given identical design
matrix, so both implementations should match modulo the
Phase 1 audit B8 6-decimal rounding floor that TSL applies
to coefficient outputs (the "HAR-CJ Coefficients" table's
``Estimate`` column rounds to 6 decimals; ``R2`` audit field
rounds to 6 decimals).

**Architectural decisions (locked in Session 5 design):**
- Q1: Bundle the from-scratch reimplementation directly into
  this check file rather than a separate
  ``harness/references/`` directory.
- Q2: Paper-validation is a one-time Session 5 development
  claim documented below in ``_PAPER_VALIDATION_NOTE``.
- Q3: Tolerance ladder is per-coefficient absolute
  (1e-6 each) plus R^2 (1e-6) plus jump_count exact match
  (abs_tol=0).
- Q4: Fast tier (closed-form OLS + BNS test, ~1 second).

**Paper-validation status** (one-time, during Session 5
implementation):

The reimpl's structural validation (Phase 1 audit 3b R1)
checks:
- Continuous components positive (beta_cd, beta_cw,
  beta_cm > 0) — required by HAR's heterogeneous-market
  hypothesis.
- Continuous persistence sum in [0.5, 0.95] on a
  high-persistence RV fixture.
- R^2 > 0.3 on a paper-shaped synthetic fixture.

All three conditions hold on the seed=42 fixture (per Phase
1 audit 3b's report,
``tools/reference_parity/reports/3b_har_cj_audit.md``).
The paper's exact SPY data (1996-2005 daily) is unavailable
without licensing; structural sign + persistence-range
validation against ABD 2007 + Corsi 2009 conventions
suffices for methodology validation.
"""

from __future__ import annotations

import sys
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityCheck, ParityResult
from reference_parity.harness.tolerances import get_ladder


_PAPER_VALIDATION_NOTE = (
    "Paper-validated against Andersen-Bollerslev-Diebold 2007 "
    "+ Corsi 2009 structural conventions: continuous components "
    "positive (HAR heterogeneous-market hypothesis); continuous "
    "persistence sum in [0.5, 0.95] on high-persistence RV "
    "fixtures; R^2 > 0.3 on paper-shaped synthetic data. All "
    "three checks pass on the seed=42 fixture per Phase 1 audit "
    "3b. Phase 1 report: tools/reference_parity/reports/"
    "3b_har_cj_audit.md."
)


# Coefficient names matching TSL's "HAR-CJ Coefficients" output
# table column order (Intercept first, then 6 regressor coefs).
_BETA_NAMES = (
    "Intercept", "beta_cd", "beta_cw", "beta_cm",
    "beta_jd", "beta_jw", "beta_jm",
)

_TOLERANCE_KEYS = (
    "beta_intercept_abs_diff",
    "beta_rv_daily_abs_diff",
    "beta_rv_weekly_abs_diff",
    "beta_rv_monthly_abs_diff",
    "beta_j_daily_abs_diff",
    "beta_j_weekly_abs_diff",
    "beta_j_monthly_abs_diff",
)


def _ensure_engine_on_path() -> None:
    """Add ``engine/`` to sys.path so we can import TSL helpers."""
    import pathlib
    p = pathlib.Path(__file__).resolve()
    repo_root = None
    for parent in p.parents:
        if (parent / "engine").is_dir():
            repo_root = parent
            break
    if repo_root is None:
        raise RuntimeError(
            "Cannot locate engine/ from harness check module"
        )
    eng_path = str(repo_root / "engine")
    if eng_path not in sys.path:
        sys.path.insert(0, eng_path)


# ---------------------------------------------------------------------
# Reimplementation — ABD 2007 + Huang-Tauchen 2005
# ---------------------------------------------------------------------

def _reimpl_har_cj(
    rv: np.ndarray,
    bv: np.ndarray,
    tq: np.ndarray,
    M: int,
    *,
    alpha: float = 0.01,
    daily_lag: int = 1,
    weekly_lag: int = 5,
    monthly_lag: int = 22,
    h_ahead: int = 1,
    use_log: bool = False,
) -> dict[str, Any]:
    """From-scratch HAR-CJ regression per ABD 2007 + Huang-
    Tauchen 2005.

    BNS z-statistic:

        Z_t = (RV_t - BV_t) / sqrt(theta * max(TQ_t, BV_t^2) / M)

    where theta = (pi/2)^2 + pi - 5 ~= 0.609.

    Decomposition (with z-threshold):

        J_t = max(RV_t - BV_t, 0)  if z_t > z_alpha else 0
        C_t = RV_t - J_t

    HAR-CJ regression:

        y_t = beta_0 + beta_cd C_{t-1}
              + beta_cw mean(C[t-5:t])
              + beta_cm mean(C[t-22:t])
              + beta_jd J_{t-1}
              + beta_jw mean(J[t-5:t])
              + beta_jm mean(J[t-22:t]) + eps_t

    Returns the coefficient vector (length 7), R^2,
    persistence sums, and jump count. Identical inputs +
    identical OLS routine (numpy.linalg.lstsq) yield bitwise-
    reproducible coefficients.
    """
    from scipy.stats import norm

    n = len(rv)
    theta = (np.pi / 2) ** 2 + np.pi - 5
    var_z = theta * np.maximum(tq, bv ** 2) / M
    var_z = np.maximum(var_z, 1e-20)
    z = (rv - bv) / np.sqrt(var_z)
    z_thresh = float(norm.ppf(1 - alpha))
    is_jump = z > z_thresh
    j = np.where(is_jump, np.maximum(rv - bv, 0), 0.0)
    c = rv - j

    if use_log:
        rv_w = np.log(np.where(rv > 0, rv, np.finfo(float).eps))
        c_w = np.log(np.where(c > 0, c, np.finfo(float).eps))
        j_w = np.log(j + 1e-10)
    else:
        rv_w = rv
        c_w = c
        j_w = j

    start = monthly_lag
    end = len(rv_w) - (h_ahead - 1) if h_ahead > 1 else len(rv_w)
    T = end - start

    y = np.zeros(T)
    X_cd = np.zeros(T)
    X_cw = np.zeros(T)
    X_cm = np.zeros(T)
    X_jd = np.zeros(T)
    X_jw = np.zeros(T)
    X_jm = np.zeros(T)
    for t_idx in range(T):
        t = start + t_idx
        if h_ahead > 1:
            y[t_idx] = np.mean(rv_w[t:t + h_ahead])
        else:
            y[t_idx] = rv_w[t]
        X_cd[t_idx] = np.mean(c_w[t - daily_lag:t])
        X_cw[t_idx] = np.mean(c_w[t - weekly_lag:t])
        X_cm[t_idx] = np.mean(c_w[t - monthly_lag:t])
        X_jd[t_idx] = np.mean(j_w[t - daily_lag:t])
        X_jw[t_idx] = np.mean(j_w[t - weekly_lag:t])
        X_jm[t_idx] = np.mean(j_w[t - monthly_lag:t])

    X = np.column_stack(
        [np.ones(T), X_cd, X_cw, X_cm, X_jd, X_jw, X_jm]
    )
    beta, _residuals, _rank, _ = np.linalg.lstsq(X, y, rcond=None)
    y_pred = X @ beta
    ss_res = float(np.sum((y - y_pred) ** 2))
    ss_tot = float(np.sum((y - np.mean(y)) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    cont_sum = float(beta[1] + beta[2] + beta[3])
    jump_sum = float(beta[4] + beta[5] + beta[6])
    n_jumps = int(is_jump.sum())
    return {
        "beta": np.asarray(beta, dtype=np.float64),
        "beta_names": list(_BETA_NAMES),
        "r_squared": float(r2),
        "continuous_persistence_sum": cont_sum,
        "jump_persistence_sum": jump_sum,
        "n_jumps": n_jumps,
        "jump_fraction": n_jumps / n,
        "T_effective": T,
    }


# ---------------------------------------------------------------------
# Parity check class
# ---------------------------------------------------------------------

class HarCjParity(ParityCheck):
    """HAR-CJ realized-volatility parity vs from-scratch ABD
    2007 + Huang-Tauchen 2005 reimplementation.

    OLS is closed-form deterministic given identical design
    matrix; both implementations should match modulo Phase 1
    audit B8 6-decimal rounding floor on TSL's output table.
    """

    technique_id = "3b_har_cj"
    tier = "fast"
    fixture_id = "3b_har_cj"

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        return {"_seed": int(seed)}

    # -----------------------------------------------------------------
    # TSL side
    # -----------------------------------------------------------------

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.base import RunContext
        from techniques import har_cj as h

        rv = np.asarray(fixture["rv"], dtype=np.float64).reshape(-1)
        bv = np.asarray(fixture["bv"], dtype=np.float64).reshape(-1)
        tq = np.asarray(fixture["tq"], dtype=np.float64).reshape(-1)
        T = int(np.asarray(fixture.get("T", len(rv))))
        M = int(np.asarray(fixture.get("M", 78)))
        seed = int(fixture.get("_seed", 42))

        time_ = [f"d{i}" for i in range(T)]
        ctx = RunContext({
            "run_id": f"parity_3b_seed{seed}",
            "technique_id": "har_cj",
            "preset": "Balanced",
            "seed": seed,
            "frequency": "daily",
            "time": time_,
            "series": [
                {"name": "RV", "values": rv.tolist()},
                {"name": "BV", "values": bv.tolist()},
                {"name": "TQ", "values": tq.tolist()},
            ],
            "params": {
                "M": M,
                "jump_alpha": 0.01,
                "use_log": False,
            },
        })
        res = h.run(ctx, lambda *a, **k: None)
        if res.get("status") != "success":
            raise RuntimeError(
                f"TSL har_cj run failed: "
                f"{res.get('error_message')}"
            )
        a = res.get("audit_fields", {}) or {}

        # Coefficients are exposed via the "HAR-CJ Coefficients"
        # output table, NOT in audit_fields directly. Read from
        # the table's "Estimate" column (rounded to 6 decimals
        # per Phase 1 audit B8).
        coef_table = None
        for tbl in res.get("tables") or []:
            if tbl.get("name") == "HAR-CJ Coefficients":
                coef_table = tbl
                break
        if coef_table is None:
            raise RuntimeError(
                "TSL har_cj did not produce 'HAR-CJ Coefficients' "
                "output table; cannot extract coefficient vector."
            )
        rows = coef_table.get("rows") or []
        if len(rows) != 7:
            raise RuntimeError(
                f"Expected 7 coefficient rows in HAR-CJ "
                f"Coefficients table; got {len(rows)}: {rows}"
            )
        beta_vec = np.asarray(
            [float(r[1]) for r in rows], dtype=np.float64,
        )
        jump_count = a.get("jump_days_count")
        if jump_count is None:
            raise RuntimeError(
                "TSL har_cj did not expose jump_days_count in "
                "audit_fields."
            )
        return {
            "beta": beta_vec,
            "r_squared": float(a.get("R2"))
            if a.get("R2") is not None else None,
            "jump_count": int(jump_count),
            "jump_fraction": a.get("jump_days_fraction"),
            "continuous_persistence_sum": a.get(
                "continuous_persistence_sum",
            ),
            "jump_persistence_sum": a.get("jump_persistence_sum"),
        }

    # -----------------------------------------------------------------
    # Reference side — from-scratch reimplementation
    # -----------------------------------------------------------------

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import scipy
        rv = np.asarray(fixture["rv"], dtype=np.float64).reshape(-1)
        bv = np.asarray(fixture["bv"], dtype=np.float64).reshape(-1)
        tq = np.asarray(fixture["tq"], dtype=np.float64).reshape(-1)
        M = int(np.asarray(fixture.get("M", 78)))

        reimpl = _reimpl_har_cj(
            rv, bv, tq, M=M,
            alpha=0.01, daily_lag=1, weekly_lag=5,
            monthly_lag=22, h_ahead=1, use_log=False,
        )
        return {
            "beta": np.asarray(reimpl["beta"], dtype=np.float64),
            "beta_names": list(reimpl["beta_names"]),
            "r_squared": float(reimpl["r_squared"]),
            "jump_count": int(reimpl["n_jumps"]),
            "jump_fraction": float(reimpl["jump_fraction"]),
            "continuous_persistence_sum": float(
                reimpl["continuous_persistence_sum"],
            ),
            "jump_persistence_sum": float(
                reimpl["jump_persistence_sum"],
            ),
            "T_effective": int(reimpl["T_effective"]),
            "scipy_version": scipy.__version__,
            "numpy_version": np.__version__,
        }

    # -----------------------------------------------------------------
    # Compare — per-coefficient absolute tolerance
    # -----------------------------------------------------------------

    def compare(
        self,
        tsl: dict[str, Any],
        ref: dict[str, Any],
    ) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        metrics: dict[str, Any] = {}
        any_block = False

        tsl_beta = np.asarray(tsl["beta"], dtype=np.float64)
        ref_beta = np.asarray(ref["beta"], dtype=np.float64)

        if tsl_beta.shape != ref_beta.shape:
            metrics["beta_shape_mismatch"] = {
                "status": "BLOCK",
                "tsl_shape": list(tsl_beta.shape),
                "ref_shape": list(ref_beta.shape),
            }
            return ParityResult(
                technique_id=self.technique_id,
                outcome="BLOCK",
                metrics=metrics,
                diagnostics={
                    "tsl_beta_names": "from HAR-CJ Coefficients table",
                    "ref_beta_names": list(ref.get("beta_names", [])),
                },
            )

        # Per-coefficient absolute-tolerance check.
        for i, (name, key) in enumerate(zip(_BETA_NAMES, _TOLERANCE_KEYS)):
            tol = float(ladder[key]["abs_tol"])
            d = abs(float(tsl_beta[i]) - float(ref_beta[i]))
            ok = d <= tol
            metrics[key] = {
                "status": "PASS" if ok else "BLOCK",
                "coefficient_name": name,
                "tsl_value": float(tsl_beta[i]),
                "ref_value": float(ref_beta[i]),
                "abs_diff": d,
                "tolerance": tol,
            }
            if not ok:
                any_block = True

        # R^2 absolute-tolerance check.
        r2_tol = float(ladder["r_squared_abs_diff"]["abs_tol"])
        if tsl["r_squared"] is None or ref["r_squared"] is None:
            metrics["r_squared_abs_diff"] = {
                "status": "BLOCK",
                "note": "TSL or reimpl R^2 is None.",
                "tsl_value": tsl.get("r_squared"),
                "ref_value": ref.get("r_squared"),
            }
            any_block = True
        else:
            r2_diff = abs(
                float(tsl["r_squared"]) - float(ref["r_squared"])
            )
            r2_ok = r2_diff <= r2_tol
            metrics["r_squared_abs_diff"] = {
                "status": "PASS" if r2_ok else "BLOCK",
                "tsl_value": float(tsl["r_squared"]),
                "ref_value": float(ref["r_squared"]),
                "abs_diff": r2_diff,
                "tolerance": r2_tol,
            }
            if not r2_ok:
                any_block = True

        # Jump count exact match.
        jc_tol = float(ladder["jump_count_match"]["abs_tol"])
        tsl_jc = int(tsl.get("jump_count", -1))
        ref_jc = int(ref.get("jump_count", -1))
        jc_diff = abs(tsl_jc - ref_jc)
        jc_ok = jc_diff <= jc_tol
        metrics["jump_count_match"] = {
            "status": "PASS" if jc_ok else "BLOCK",
            "tsl_count": tsl_jc,
            "ref_count": ref_jc,
            "abs_diff": jc_diff,
            "tolerance": jc_tol,
            "note": (
                "BNS test deterministic given RV/BV/TQ + alpha; "
                "exact match required (any divergence is a bug "
                "in one BNS implementation)."
            ),
        }
        if not jc_ok:
            any_block = True

        outcome = "BLOCK" if any_block else "PASS"

        diagnostics = {
            "tsl_beta": tsl_beta.tolist(),
            "ref_beta": ref_beta.tolist(),
            "beta_names": list(_BETA_NAMES),
            "tsl_continuous_persistence_sum": tsl.get(
                "continuous_persistence_sum",
            ),
            "ref_continuous_persistence_sum": ref.get(
                "continuous_persistence_sum",
            ),
            "tsl_jump_persistence_sum": tsl.get("jump_persistence_sum"),
            "ref_jump_persistence_sum": ref.get("jump_persistence_sum"),
            "ref_T_effective": ref.get("T_effective"),
            "scipy_version": ref.get("scipy_version", "unknown"),
            "numpy_version": ref.get("numpy_version", "unknown"),
            "paper_validation_note": _PAPER_VALIDATION_NOTE,
        }

        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics=metrics,
            diagnostics=diagnostics,
        )
