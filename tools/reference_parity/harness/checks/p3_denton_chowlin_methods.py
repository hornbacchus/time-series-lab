"""Phase 7+ deeper-validation, scope-extension UNIT 4 —
denton_chowlin_disaggregation per-METHOD parity check (additive;
``p3_denton_chowlin`` unchanged).

★ The ribbon-DEFAULT Chow-Lin method-path had ZERO parity evidence:
``p3_denton_chowlin`` re-implements proportional Denton INLINE (a check-side
KKT mirror) vs R and NEVER invokes the engine — so it validated only
Denton-via-mirror, and Chow-Lin (the default ``method``) not at all. (Its
"Chow-Lin GLS" docstring is stale drift, like ccf's "prewhitened" docstring;
the old check is left UNCHANGED.) This check is the engine's first real
parity evidence for BOTH methods, ENGINE-INVOKED via RunContext.

Two cross-package arms vs R ``tempdisagg::td`` (pure B.i — single primitive
per method, trivial decision; the adding-up constraint is structurally
guaranteed by construction [Denton KKT; Chow-Lin BLUE C.L=I] → TAUTOLOGICAL,
so NO adding-up functional-check arm; the cross-package carries the
discrimination):
  - Denton arm (rigor-closer): engine method="denton" vs tempdisagg
    denton-cholette (~ 0 + ind, conversion="sum"). Closes the mirror-not-engine
    gap. Measured bit-exact (6.8e-07 at the 6-dp emitted precision).
  - Chow-Lin arm (the primary gap): engine method="chowlin", rho PINNED 0.5,
    vs tempdisagg chow-lin-fixed (fixed.rho=0.5), §5.2 identical-parameterization
    — design [intercept + high-freq trend + indicator], conversion="sum". The
    1/(1-rho^2) AR(1) scaling cancels in the BLUE distribution L = V C'(CVC')^-1
    → measured bit-exact (5.0e-07).

★ rho-AUTO — now a GATED cross-package arm (UPGRADED post engine-improvement #1,
the continuous-optimizer fix). Pre-fix the engine used a 20-point GRID over an
UNPROFILED (sigma^2=1) objective whose argmax sat ~0.14 from tempdisagg's
profiled-sigma^2 continuous chow-lin-maxlog (grid 0.42 vs continuous 0.28) — an
OBJECTIVE mismatch, NOT grid coarseness (the grid already nearly converged to
its own, wrong, optimum). Post-fix the engine optimizes the CONCENTRATED
(profiled-sigma^2) likelihood continuously over rho in [0, 0.999] -> auto-rho
reproduces tempdisagg (measured gap 1.3e-7) and the auto SERIES matches
cross-package (~1e-6). The arm now GATES (was disclosure-only). The validated
fixed-rho arm is unchanged (byte-identical 4.99e-07 — the regression sentinel).
"""

from __future__ import annotations

from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.checks._disagg_components import tempdisagg_reference
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_N_LOW = 12
_RATIO = 3
_PIN_RHO = 0.5


def _disagg_dgp(seed: int):
    rng = np.random.default_rng(seed)
    n_high = _N_LOW * _RATIO
    ind = np.cumsum(rng.standard_normal(n_high)) + 50.0
    agg = np.array([ind[i * _RATIO:(i + 1) * _RATIO].sum() + 5.0 * rng.standard_normal()
                    for i in range(_N_LOW)])
    return agg.astype(float), ind.astype(float)


def _engine(method: str, agg, ind, params: dict):
    from techniques.base import RunContext  # type: ignore
    import techniques.denton_chowlin_disaggregation as dc  # type: ignore
    ctx = RunContext({
        "run_id": f"p3_dc_methods_{method}",
        "technique_id": "denton_chowlin_disaggregation",
        "preset": "Balanced", "seed": 42, "frequency": "",
        "time": list(range(len(agg))),
        "series": [{"name": "agg", "values": list(map(float, agg))},
                   {"name": "ind", "values": list(map(float, ind))}],
        "params": {"method": method, "conversion_ratio": _RATIO, **params},
    })
    resp = dc.run(ctx, lambda *a, **k: None)
    if resp.get("status") != "success":
        raise RuntimeError(f"engine {method} failed: {resp.get('error_message')}")
    t = next(t for t in resp["tables"] if t["name"] == "Disaggregated Series")
    y = np.array([float(r[3]) for r in t["rows"]])
    return y, resp.get("audit_fields", {})


class DentonChowLinMethodsParity(P3ParityCheck):
    """Per-method (Denton + Chow-Lin) engine-invoked cross-package parity
    vs tempdisagg — closes the Chow-Lin-path + mirror-not-engine gaps."""

    technique_id = "p3_denton_chowlin_methods"
    tier = "fast"
    fixture_id = ""

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "Temporal disaggregation is closed-form: Denton is a hard-constrained "
        "QP, Chow-Lin a GLS regression + BLUE distribution. Both engine methods "
        "validated cross-package vs R tempdisagg::td at identical parameters "
        "(Denton denton-cholette; Chow-Lin chow-lin-fixed at a pinned rho + "
        "matched [intercept,trend,indicator] design) — measured bit-exact at the "
        "6-dp emitted precision. B.i pure parameter coverage; adding-up is "
        "structurally guaranteed (tautological), so no functional-check arm."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        agg, ind = _disagg_dgp(seed)
        return {"agg": agg, "ind": ind}

    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        agg, ind = fixture["agg"], fixture["ind"]
        y_denton, _ = _engine("denton", agg, ind, {})
        y_cl_fixed, _ = _engine("chowlin", agg, ind, {"rho": _PIN_RHO})
        y_cl_auto, au_auto = _engine("chowlin", agg, ind, {"rho": "auto"})
        return {"denton": y_denton, "cl_fixed": y_cl_fixed,
                "cl_auto": y_cl_auto, "eng_rho_auto": float(au_auto.get("rho"))}

    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        agg, ind = fixture["agg"], fixture["ind"]
        rd = tempdisagg_reference(agg, ind, method="denton-cholette",
                                  ratio=_RATIO, intercept=False, trend=False)
        rc = tempdisagg_reference(agg, ind, method="chow-lin-fixed", ratio=_RATIO,
                                  fixed_rho=_PIN_RHO, intercept=True, trend=True)
        rm = tempdisagg_reference(agg, ind, method="chow-lin-maxlog", ratio=_RATIO,
                                  intercept=True, trend=True)
        return {"denton": rd["disagg"], "cl_fixed": rc["disagg"],
                "cl_maxlog_series": rm["disagg"], "rho_continuous": rm["rho"],
                "tempdisagg_version": rc.get("tempdisagg_version", "unknown")}

    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)
        primary: dict[str, Any] = {}
        statuses: list[str] = []

        def _arm(key, band_key):
            n = min(len(tsl[key]), len(ref[key]))
            primary[key] = _compare_vector(tsl[key][:n], ref[key][:n], ladder[band_key])
            statuses.append(primary[key]["status"])

        _arm("denton", "denton")
        _arm("cl_fixed", "chowlin")

        # rho-auto CROSS-PACKAGE arm — UPGRADED from a disclosure to a GATED arm
        # post engine-improvement #1 (the continuous-optimizer fix): the engine's
        # auto-rho now reproduces tempdisagg chow-lin-maxlog AND the auto series
        # matches cross-package. Gates the outcome.
        auto_band = ladder["chowlin_auto"]
        rho_gap = abs(tsl["eng_rho_auto"] - ref["rho_continuous"])
        na = min(len(tsl["cl_auto"]), len(ref["cl_maxlog_series"]))
        series_cmp = _compare_vector(
            tsl["cl_auto"][:na], ref["cl_maxlog_series"][:na], auto_band)
        rho_status = "PASS" if rho_gap < float(auto_band["rho_abs_tol"]) else "BLOCK"
        arm_status = ("BLOCK" if "BLOCK" in (series_cmp["status"], rho_status)
                      else ("CAVEAT" if "CAVEAT" in (series_cmp["status"], rho_status)
                            else "PASS"))
        primary["chowlin_auto"] = {
            "status": arm_status,
            "engine_auto_rho": round(tsl["eng_rho_auto"], 6),
            "tempdisagg_continuous_rho": round(ref["rho_continuous"], 6),
            "rho_gap": rho_gap, "rho_status": rho_status,
            "series_status": series_cmp["status"],
            "auto_series_max_abs_diff": series_cmp.get("max_abs_diff"),
            "note": ("continuous-ML auto-rho cross-package vs tempdisagg "
                     "chow-lin-maxlog (post grid->continuous engine fix #1)"),
        }
        statuses.append(arm_status)

        any_block = any(s == "BLOCK" for s in statuses)
        any_caveat = any(s == "CAVEAT" for s in statuses)
        outcome = ("BLOCK" if any_block else
                   ("CAVEAT" if any_caveat else "PASS"))
        return ParityResult(
            technique_id=self.technique_id, outcome=outcome,
            metrics={"primary": primary},
            diagnostics={
                "tempdisagg_version": ref.get("tempdisagg_version", "unknown"),
                "n_low": _N_LOW, "ratio": _RATIO, "pinned_rho": _PIN_RHO,
                "denton_max_abs_diff": primary["denton"].get("max_abs_diff"),
                "chowlin_fixed_max_abs_diff": primary["cl_fixed"].get("max_abs_diff"),
                "chowlin_auto_rho_gap": rho_gap,
                "chowlin_auto_status": arm_status,
                "adding_up": "structural by construction (tautological; no arm)",
            },
        )
