"""Breakeven Payrolls — TSL workbook-input dispatch.

Reads the 10-tab breakeven_payroll_input_template.xlsx, reconstructs the inputs the
source repo's fetchers produced, runs the SAME ported math (build_population +
breakeven_from_inputs for the path; sensitivity_grid for the scenario grid), and
assembles TSL output tables.

D1: the historical PATH uses the workbook's cbo_quarterly potential_lfpr + u_star
(data-derived in both repos). The SCENARIO-GRID scalars are the repo's FROZEN
LITERALS (assembled here), NOT recomputed from cbo_annual.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import yaml

from techniques.base import make_error_response, make_response, make_table

from .breakeven import breakeven_from_inputs
from .conventions import FROZEN_STITCH, LFPR26
from .metrics import iter_targets, metric_value, scope
from .population import build_population
from .scenarios import pace, sensitivity_grid

logger = logging.getLogger(__name__)

_RES = Path(__file__).resolve().parent / "resources"

# Frozen scenario presets (D1 — the repo's params.yaml literals; the migration
# preset grid is reference/frozen, the user knob is net_migration_all_ages).
FROZEN_PRESETS = {
    "Census_V2025": 320000.0,
    "Brookings_low": -925000.0,
    "Brookings_mid": -370000.0,
    "Brookings_high": 185000.0,
    "MS_house": 590000.0,
    # Preset-only re-port @ 99c03ba (CFL-525): CBO's own pub-61879 2026
    # all-ages net, derived in the SOURCE repo from the committed gross-
    # migration file (its params entry is test-asserted equal there). The
    # frozen literal keeps the grid deterministic and user-edit-proof; when
    # the v2 template's gross_migration_sums tab is present, compute()
    # re-derives from it and raises on mismatch (the desk-side
    # reconcile-don't-hardcode guard).
    "CBO_Feb2026": 573959.0,
}
# Frozen u* definitions (D1) — NOT recomputed from cbo_annual.
FROZEN_USTAR_OPTIONS = {"noncyclical": 0.044, "cbo_actual": 0.0456}
PROJECTION_START = "2026-01-01"


# The reconciled reference scenario. The committed fed_reference_path.csv (and its
# 2026 anchor 7.24 k/mo) was reconciled at the Fed-default Brookings-mid. The
# scenario GRID is always anchored here — it is the fixed reference comparison
# (each preset's breakeven relative to the reconciled baseline), independent of
# the user's active 2026 knob (which drives only the PATH's 2026 block).
_GRID_REFERENCE_SCENARIO = "Brookings_mid"


def _build_params(inp: dict) -> dict:
    share = inp["scalars"]["share_16plus"]
    return {
        "unemployment": {"u_star_options": dict(FROZEN_USTAR_OPTIONS)},
        "scenarios": {
            "presets": dict(FROZEN_PRESETS),
            "active_2026": _GRID_REFERENCE_SCENARIO,
            "defaults": {"lfpr": LFPR26 / 100.0, "u_star": FROZEN_USTAR_OPTIONS["noncyclical"],
                         "share_16plus": share},
        },
    }


def compute(inp: dict) -> dict:
    """Pure compute seam (no RunContext) — usable standalone + by the parity check."""
    # Reconcile-don't-hardcode guard (re-port @ 99c03ba): when the v2
    # template's gross_migration_sums tab is present, the CBO_Feb2026 frozen
    # literal must equal the tab-derived all-ages 2026 net. A mismatch means
    # the baked sums and the preset literal have drifted apart (a botched
    # template regen or a stale re-port) — fail LOUD, not silent.
    gm = inp.get("gross_migration_sums")
    if gm is not None:
        from .migration import derived_preset_from_sums
        derived = derived_preset_from_sums(gm)
        frozen = FROZEN_PRESETS["CBO_Feb2026"]
        if abs(derived - frozen) > 1e-6:
            raise ValueError(
                f"CBO_Feb2026 preset drift: frozen literal {frozen} != "
                f"template-derived {derived} (gross_migration_sums tab)")
    params = _build_params(inp)
    base = inp["scalars"]["pop_base_v2025_dec2025"]
    base_pace = inp["scalars"]["census_base_pace"]

    # The active 2026 population flow comes from the USER's net-migration knob
    # (scenario_inputs.net_migration_all_ages), via the same pace(M) identity the
    # grid uses — NOT a preset-name snap. A blank cell defaults to -370000
    # (Brookings-mid, the Fed default) in the reader, reproducing the reconciled
    # 7.24 k/mo. Any value (e.g. 560000 -> 108.2 k/mo) now drives the 2026 block.
    active_migration = float(inp["scenario"]["net_migration_all_ages"])
    mc = pace(active_migration, base_pace_kmo=base_pace,
              base_migration=inp["scalars"]["census_migration_ref"],
              share_16plus=inp["scalars"]["share_16plus"])

    pop = build_population(inp["hplfs"], inp["cnp16ov"], monthly_change_thousands=mc,
                           base_thousands=base, through="2026-12")
    res = breakeven_from_inputs(pop, inp["potential_lfpr"], inp["u_star"], FROZEN_STITCH,
                                projection_start=PROJECTION_START, projection_flow=mc)
    quarterly_persons = (res.quarterly["breakeven_smoothed"] * 1000.0).dropna()
    grid = sensitivity_grid(params)
    return {"quarterly_persons": quarterly_persons, "monthly": res.monthly,
            "grid": grid, "pace_2026_kmo": mc, "active_migration": active_migration,
            "ustar_basis": inp["scenario"].get("ustar_basis", "noncyclical"),
            "params": params}


def _anchor_rows(qp: pd.Series) -> tuple[list, list]:
    tpath = _RES / "fed_reference_targets.yaml"
    if not tpath.exists():
        return [], []
    targets = yaml.safe_load(tpath.read_text(encoding="utf-8")) or {"targets": {}}
    rows = []
    for t in iter_targets(targets):
        ref = float(t["reference"])
        tol = float(t.get("abs_tol", 12000.0))
        val = metric_value(qp, t)
        if val != val:
            st, diff = "CAVEAT", None
        else:
            diff = abs(val - ref)
            st = "PASS" if diff <= tol else ("CAVEAT" if diff <= 2 * tol else "BLOCK")
        rows.append([t["id"], scope(t), None if val != val else round(val), round(ref),
                     None if diff is None else round(diff), round(tol), st])
    cols = ["Anchor", "Scope", "Computed (jobs/mo)", "Reference", "Abs diff", "Abs tol", "Status"]
    return cols, rows


def run(ctx, progress_callback) -> dict:
    """TSL dispatch. ``ctx.params['input_workbook']`` = path to the 10-tab template."""
    try:
        from .workbook_input import read_workbook

        progress_callback("Reading input workbook", 5)
        wb_path = ctx.get_param("input_workbook")
        if not wb_path or not Path(str(wb_path)).exists():
            return make_error_response(
                ctx, f"Input workbook not found: {wb_path!r}",
                error_fixes=["Open the Breakeven Payrolls template, fill the data, save it, then Run."],
            )
        inp = read_workbook(wb_path)

        # Units guardrail (pop x lfpr/100 ~= potential_lf) — a sanity check, warn-only.
        warns: list[str] = []
        try:
            last_lfpr = float(inp["potential_lfpr"].dropna().iloc[-1])
            last_pop = float(inp["hplfs"]["pn16"].dropna().iloc[-1])
            implied_lf = last_pop * last_lfpr / 100.0
            if not (0.4 * last_pop < implied_lf < 0.8 * last_pop):
                warns.append(f"Units guardrail: implied LF {implied_lf:,.0f}k from pop {last_pop:,.0f}k x "
                             f"lfpr {last_lfpr:.2f}% looks off — check column units.")
        except Exception as ge:  # noqa: BLE001
            logger.info("units guardrail skipped: %s", ge)

        progress_callback("Computing breakeven path + scenarios", 45)
        out = compute(inp)
        qp = out["quarterly_persons"]
        grid = out["grid"]

        progress_callback("Assembling tables", 85)
        tables = []

        # 1) Breakeven path (quarterly), 2026 flagged FORECAST.
        path_rows = []
        for p, v in qp.items():
            yr = p.year
            path_rows.append([f"{yr}-Q{p.quarter}", round(float(v)),
                              "FORECAST" if yr >= 2026 else "Historical"])
        tables.append(make_table("Breakeven Payrolls (Quarterly)",
                                 ["Quarter", "Breakeven (jobs/mo)", "Type"], path_rows))

        # 2) Scenario grid (12 rows since the 99c03ba re-port).
        gcols = ["preset", "migration", "u_star_def", "u_star", "delta_per_month", "pace_kmo", "breakeven_kmo"]
        grows = [[r["preset"], int(r["migration"]), r["u_star_def"], round(float(r["u_star"]), 4),
                  round(float(r["delta_per_month"]), 1), round(float(r["pace_kmo"]), 3),
                  round(float(r["breakeven_kmo"]), 2)] for _, r in grid.iterrows()]
        tables.append(make_table("Scenario Grid (breakeven k/mo by migration x u*)", gcols, grows))

        # 3) Reconciliation anchors (the loose round-target sanity overlay; D3).
        acols, arows = _anchor_rows(qp)
        if arows:
            tables.append(make_table("Reconciliation Anchors (vs Fed reference)", acols, arows))

        # 4) Signal vs noise overlay (scenario band vs +/-CI payroll band + bias).
        ci_half = 1.645 * inp["scalars"]["ces_se_monthly_nfp_change"]  # ~100.8k
        be_lo = float(grid["breakeven_kmo"].min()) * 1000.0
        be_hi = float(grid["breakeven_kmo"].max()) * 1000.0
        snr_rows = [
            ["Scenario breakeven band (min..max across grid)", f"{be_lo:,.0f} .. {be_hi:,.0f}", "jobs/mo"],
            ["Payroll measurement band (+/- 1.645 x CES SE)", f"+/- {ci_half * 1000:,.0f}", "jobs/mo"],
            ["Benchmark-revision bias line", f"{-71.0 * 1000:,.0f}", "jobs/mo"],
            ["Reading", "the scenario band is narrower than the +/-100k measurement band — "
                        "a single NFP print is mostly noise vs the breakeven", ""],
        ]
        tables.append(make_table("Signal vs Noise (band vs measurement error)",
                                 ["Quantity", "Value", "Units"], snr_rows))

        # Summary. The "2026 breakeven" is the ACTIVE path's own 2026 average
        # (it reflects the user's net-migration knob), NOT the fixed grid
        # reference cell.
        active_migration = out["active_migration"]
        be26 = float(qp[qp.index.year == 2026].mean()) / 1000.0 if (qp.index.year == 2026).any() \
            else float("nan")
        is_default = abs(active_migration - (-370000.0)) < 1.0
        scen_desc = ("Fed default: Brookings-mid -370,000" if is_default
                     else f"user net migration: {active_migration:,.0f}")
        summary = (
            f"Breakeven payrolls reconstructed from the workbook ({len(qp)} quarters, "
            f"{qp.index.min()}..{qp.index.max()}). 2026 block projected at "
            f"{out['pace_2026_kmo']:.1f}k/mo ({scen_desc}; u* basis {out['ustar_basis']}). "
            f"2026 breakeven ~ {be26:.1f}k/mo. Reference scenario grid (vs the Fed-reconciled "
            f"baseline) spans {grid['breakeven_kmo'].min():.1f}..{grid['breakeven_kmo'].max():.1f} k/mo."
        )

        return make_response(
            ctx, tables=tables, plain_english_summary=summary, warnings=warns,
            audit_fields={
                "n_quarters": int(len(qp)),
                "path_start": str(qp.index.min()),
                "path_end": str(qp.index.max()),
                "active_net_migration": active_migration,
                "pace_2026_kmo": round(float(out["pace_2026_kmo"]), 3),
                "breakeven_2026_kmo": round(be26, 2),
                "ustar_basis": out["ustar_basis"],
                "grid_reference_scenario": out["params"]["scenarios"]["active_2026"],
            },
            charting_suggestions=(
                "Line chart of Breakeven (jobs/mo) by Quarter, 2026 dashed (FORECAST). "
                "Overlay the +/-100k payroll measurement band to read a monthly NFP print as signal vs noise."
            ),
        )
    except Exception as e:  # noqa: BLE001
        logger.exception("breakeven_payroll dispatch failed")
        return make_error_response(ctx, f"Breakeven Payrolls failed: {e}")
