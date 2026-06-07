"""Phase 7+ — bond_yield_forecast COMMISSION, ARM 3 (FINAL): the emitted
yield PATHS (the published numbers).

★ NO independent cross-package/cross-source reference exists for the
conditional yield-curve forecast paths: R `bvars` is unavailable; the
standalone bvar-yield-forecaster repo was migrated-then-retired (same lineage,
not independent); there is no external authority for yield forecasts (unlike
breakeven's Fed reconciliation). So Arm 3 validates the emitted paths by a
VERIFIED DEFINING INVARIANT + HONEST DISCLOSURE — the third-case pattern
applied to a sub-surface with no available reference. This is NOT cross-package
and is not dressed as such; it is the honest, massively-improved replacement
for the prior blanket "cross-ref" record.

The LOAD-BEARING check — conditioning-exactness, discrimination wired IN-HARNESS:
- In STRICT mode (`enforce_strict_match=True`) the conditioned macro path is hit
  EXACTLY (`macro_t = projection_t.copy()`): max|macro_paths − projection| <
  1e-10 → PASS.
- NEGATIVE CONTROL (active, in-harness): SOFT mode (`enforce_strict_match=False`,
  projection treated as noisy) does NOT pin the macros → the divergence is large
  → discrimination fires. Computed in-harness and asserted (the conformal/proxy/
  breakeven pattern), NOT merely cited from the engine's test suite.
- PCA reconstruction-exactness: `yield_paths == pc_paths @ loadings.T + mean`
  (deterministic identity) — a structural check.

The engine fit mirrors the engine's own `tests/test_conditioning.py` toy
construction (tiny stable VAR(1), short chain) — faithful + fast + deterministic.

Pattern-F disposition (the M5 component): conditioning-exactness is here promoted
to a VERIFIED load-bearing functional check (in-harness control). The BVAR-fit
structural invariants (companion |eig|<1, SV |phi|<1, PCA explained-variance≥99%)
remain DISCLOSED Pattern-F diagnostics in the existing `p3_bond_yield_forecast`
(honest-downgrade — not upgraded here with manufactured controls on a toy fit;
they are fit-layer, not emitted-paths). See the §2 amendment.
"""

from __future__ import annotations

import warnings as _w
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_T = 80
_N_DRAWS = 120
_N_BURN = 40
_HORIZON = 4
_MACROS = ["macro_a", "macro_b"]


def _toy_panel(seed: int):
    import pandas as pd
    rng = np.random.default_rng(seed)
    cols = ["macro_a", "macro_b", "pc1", "pc2"]
    Y = np.zeros((_T, 4))
    Y[0] = rng.standard_normal(4) * 0.3
    for t in range(1, _T):
        Y[t] = 0.5 * Y[t - 1] + rng.standard_normal(4) * 0.4
    idx = pd.period_range("1990-Q1", periods=_T, freq="Q-DEC")
    return pd.DataFrame(Y, index=idx, columns=cols)


def _pca_dict():
    return {
        "loadings": np.array([[1.0, 0.0], [0.5, 0.7], [0.2, -0.3]]),
        "mean": np.array([3.0, 3.5, 4.0]),
        "explained_variance_ratio": np.array([0.7, 0.3]),
        "yield_names": ["3M", "1Y", "10Y"],
        "component_names": ["pc1", "pc2"],
    }


def _config(strict: bool):
    return {
        "horizon": _HORIZON, "n_paths_per_draw": 5, "n_draws_subsample": 30,
        "macro_variables": list(_MACROS), "enforce_strict_match": strict,
        "projection_uncertainty": {"macro_a": 0.5, "macro_b": 0.5},
        "workbook_sheet": "projections",
    }


class ByfPathsParity(P3ParityCheck):
    """Emitted yield-paths conditioning-exactness invariant + honest disclosure
    (bond_yield commission, Arm 3 — no independent reference exists)."""

    technique_id = "p3_byf_paths"
    tier = "fast"  # toy stable VAR(1) + short chain ~2-3s
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The emitted yield paths have NO independent cross-package/cross-source "
        "reference (R bvars unavailable; standalone repo same-lineage/retired; "
        "no external authority). Validated by a VERIFIED defining invariant "
        "(strict-mode conditioning pins the conditioned macros exactly, "
        "<1e-10; soft mode is the in-harness negative control, unpinned) + "
        "PCA-reconstruction exactness (deterministic identity) + honest "
        "disclosure (self-parity determinism in the existing check). The "
        "third-case pattern on a sub-surface with no available reference — NOT "
        "cross-package, not dressed as such."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.bond_yield_forecast.estimation import BVARSV
        from techniques.bond_yield_forecast.priors import MinnesotaPrior
        from techniques.bond_yield_forecast.conditioning import EconomistProjections
        import pandas as pd
        panel = _toy_panel(seed=0)
        prior = MinnesotaPrior(
            n_vars=4, n_lags=1, training_data=panel,
            persistence_prior={"macro_a": 0.5, "macro_b": 0.5, "pc1": 0.9, "pc2": 0.5},
            variable_names=list(panel.columns))
        with _w.catch_warnings():
            _w.simplefilter("ignore")
            results = BVARSV(panel, n_lags=1, prior=prior, n_draws=_N_DRAWS,
                             n_burn=_N_BURN, seed=0).estimate()
        rng = np.random.default_rng(5)
        fut = pd.period_range(panel.index[-1] + 1, periods=_HORIZON, freq="Q-DEC")
        proj_df = pd.DataFrame({"macro_a": rng.standard_normal(_HORIZON) * 0.2,
                                "macro_b": rng.standard_normal(_HORIZON) * 0.2}, index=fut)
        proj = EconomistProjections(proj_df, macro_variables=list(_MACROS))
        return {"results": results, "proj": proj, "pca": _pca_dict()}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.bond_yield_forecast.conditioning import ConditionalForecaster
        results, proj, pca = fixture["results"], fixture["proj"], fixture["pca"]
        proj_arr = np.asarray(proj.to_array(list(_MACROS)), float)  # (H, n_macro)

        def _run(strict):
            with _w.catch_warnings():
                _w.simplefilter("ignore")
                return ConditionalForecaster(results=results, projections=proj,
                                             config_section=_config(strict), seed=0).forecast()

        cf_strict = _run(True)
        cf_soft = _run(False)
        strict_maxdiff = float(np.max(np.abs(
            np.asarray(cf_strict.macro_paths, float) - proj_arr[None, :, :])))
        soft_maxdiff = float(np.max(np.abs(
            np.asarray(cf_soft.macro_paths, float) - proj_arr[None, :, :])))

        # PCA reconstruction exactness: engine to_yield_space vs the identity.
        yf = cf_strict.to_yield_space(pca)
        yield_engine = np.asarray(yf.yield_paths, float)
        comp = list(pca["component_names"])
        pc_idx = [cf_strict.target_names.index(c) for c in comp]
        pc_paths = np.asarray(cf_strict.target_paths, float)[:, :, pc_idx]
        recon = pc_paths @ np.asarray(pca["loadings"], float).T + np.asarray(pca["mean"], float)
        pca_maxdiff = float(np.max(np.abs(yield_engine - recon)))
        return {"strict_maxdiff": strict_maxdiff, "soft_maxdiff": soft_maxdiff,
                "pca_maxdiff": pca_maxdiff,
                "macro_shape": list(np.asarray(cf_strict.macro_paths).shape)}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        ladder = get_ladder(self.technique_id)
        return {"strict_tol": float(ladder["conditioning_strict"]["abs_tol"]),
                "soft_min_divergence": float(ladder["conditioning_soft_control"]["min_divergence"]),
                "pca_tol": float(ladder["pca_reconstruction"]["abs_tol"])}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        # Load-bearing invariant: strict mode pins the conditioned macros exactly.
        strict_ok = tsl["strict_maxdiff"] < ref["strict_tol"]
        primary["conditioning_exactness_strict"] = {
            "status": "PASS" if strict_ok else "BLOCK",
            "max_abs_diff": tsl["strict_maxdiff"], "tol": ref["strict_tol"]}
        statuses.append(primary["conditioning_exactness_strict"]["status"])

        # Active in-harness negative control: soft mode must NOT pin (discriminates).
        disc = tsl["soft_maxdiff"] > ref["soft_min_divergence"]
        primary["conditioning_discrimination_soft"] = {
            "status": "PASS" if disc else "BLOCK",
            "soft_max_diff": tsl["soft_maxdiff"],
            "min_divergence": ref["soft_min_divergence"],
            "note": ("negative control: soft mode unpinned -> the strict-pin "
                     "invariant is verified-discriminating in-harness")}
        statuses.append(primary["conditioning_discrimination_soft"]["status"])

        # Structural: PCA reconstruction identity.
        pca_ok = tsl["pca_maxdiff"] < ref["pca_tol"]
        primary["pca_reconstruction"] = {
            "status": "PASS" if pca_ok else "BLOCK",
            "max_abs_diff": tsl["pca_maxdiff"], "tol": ref["pca_tol"]}
        statuses.append(primary["pca_reconstruction"]["status"])

        any_block = any(s == "BLOCK" for s in statuses)
        outcome = "BLOCK" if any_block else "PASS"
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "reference": ("NONE — no independent cross-package/cross-source "
                              "reference exists (R bvars unavailable; standalone "
                              "repo same-lineage/retired). Verified defining "
                              "invariant + honest disclosure (third-case)."),
                "strict_pin_max_diff": tsl["strict_maxdiff"],
                "soft_control_max_diff": tsl["soft_maxdiff"],
                "pca_recon_max_diff": tsl["pca_maxdiff"],
                "macro_paths_shape": tsl["macro_shape"],
                "disclosure": ("emitted yield paths = self-parity determinism "
                               "(existing Pattern A.1) + verified conditioning-"
                               "exactness + PCA-recon exactness; NO cross-package."),
            },
        )
