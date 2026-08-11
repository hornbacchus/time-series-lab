"""Phase 3 (Bespoke) — Breakeven Payrolls parity check.

CROSS-SOURCE reproduction: TSL's ``engine/techniques/breakeven_payroll`` reads the
12-tab Breakeven Payrolls workbook, runs the ported math, and must reproduce the
authoritative Breakeven Payrolls repo's reconciled output (the frozen
``tests/fixtures/fed_reference_path.csv`` @ 99c03ba; preset-only re-port 2026-08-08, path math unchanged since 826d1d0). This is the analogue of the
cross-package R checks, but the reference is the source repo's own frozen fixture
rather than an independent library — the source IS the authority.

Assertions:
  * TIGHT full-path parity over the MA-stable region (1962Q1-2026Q4): the
    workbook-path quarterly breakeven reproduces fed_reference_path.csv to ~float
    level (measured 0.19 jobs/mo). The 1960Q1-1961Q1 13-month-MA edge is excluded
    (the template bakes HPLFS from 1960; no reconciliation anchor falls there).
    LOAD-BEARING.
  * TIGHT scenario grid (12 rows: the 10 v1 rows value-identical + 2 CBO_Feb2026): reproduces the source ``sensitivity_grid``
    (frozen-literal closed form) — Brookings-mid/Fed 7.2386, MS-house 50.6638.
    LOAD-BEARING.
  * LOOSE anchor overlay: the 6 reconciliation anchors vs the repo's round targets
    (intentionally generous; reported, not gated).

The diff-splice contract: the CNP16OV append segment must carry its May-2025
(HPLFS-handoff) observation as the first increment's diff base. The pinned fixture
``breakeven_payroll_input_v2026-06-03.xlsx`` honors that (vintage realtime_end
2026-05-30).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from reference_parity.harness.base import ParityResult
from reference_parity.harness.check_base import P3ParityCheck
from reference_parity.harness.compare import _compare_vector
from reference_parity.harness.path_setup import _ensure_engine_on_path
from reference_parity.harness.tolerances import get_ladder

_REPO_ROOT = Path(__file__).resolve().parents[4]
_FIXTURE = _REPO_ROOT / "tools" / "reference_parity" / "fixtures" / "breakeven_payroll_input_v2026-06-03.xlsx"
_RES = _REPO_ROOT / "engine" / "techniques" / "breakeven_payroll" / "resources"
_REF_PATH = _RES / "fed_reference_path.csv"
_REF_GRID = _RES / "scenario_grid_reference.csv"
_TARGETS = _RES / "fed_reference_targets.yaml"

# MA-stable region start (exclude the 1960Q1-1961Q1 13-month-MA truncation edge).
_STABLE_START = "1962Q1"
_GRID_KEYS = [
    ("Census_V2025", "noncyclical"), ("Census_V2025", "cbo_actual"),
    ("Brookings_low", "noncyclical"), ("Brookings_low", "cbo_actual"),
    ("Brookings_mid", "noncyclical"), ("Brookings_mid", "cbo_actual"),
    ("Brookings_high", "noncyclical"), ("Brookings_high", "cbo_actual"),
    ("MS_house", "noncyclical"), ("MS_house", "cbo_actual"),
    # Preset-only re-port @ 99c03ba (fixture v2, 12 rows):
    ("CBO_Feb2026", "noncyclical"), ("CBO_Feb2026", "cbo_actual"),
]
# The LIVE bundled v2 template (10 tabs) — the three-way preset assert's
# template arm reads THIS file's gross_migration_sums tab. The pinned 12-tab
# parity fixture workbook above stays byte-frozen (no sums tab) by ruling.
_BUNDLED_TEMPLATE = (_REPO_ROOT / "engine" / "techniques" / "breakeven_payroll"
                     / "resources" / "templates"
                     / "breakeven_payroll_input_template.xlsx")


def _period_key(s: str) -> str:
    return str(s).replace("-Q", "Q").replace("-", "Q") if "Q" not in str(s).replace("-Q", "Q") \
        else str(s).replace("-Q", "Q")


class BreakevenPayrollParity(P3ParityCheck):
    """Cross-source reproduction of the Breakeven Payrolls reconciled path + grid."""

    technique_id = "p3_breakeven_payroll"
    tier = "fast"
    fixture_id = ""  # fixture loaded by absolute path (binary xlsx; no sha sidecar)

    verdict_class = "closed_form"
    verdict_class_rationale = (
        "The breakeven path is deterministic closed-form arithmetic — population "
        "diff-splice + exact product-rule labor-force decomposition + the identity "
        "be = delta_lf*(1-u*) aggregated to quarterly with a 5-quarter centered MA — "
        "over the workbook's CBO-quarterly potential-LFPR/u* and CNP16OV-bridged "
        "population; the scenario grid is a closed-form migration-surprise identity "
        "over frozen literals. No optimization, no sampling. The TSL port and the "
        "authoritative source share the identical (verbatim-ported) math, so on the "
        "same pinned vintage the workbook path reproduces the source's reconciled "
        "fed_reference_path.csv to machine/float level (measured 0.19 jobs/mo)."
    )

    def setup_fixture(self, seed: int) -> dict[str, Any]:
        for p in (_FIXTURE, _REF_PATH, _REF_GRID, _TARGETS):
            if not p.exists():
                raise FileNotFoundError(f"breakeven parity fixture/reference missing: {p}")
        return {
            "workbook": str(_FIXTURE),
            "ref_path_csv": str(_REF_PATH),
            "ref_grid_csv": str(_REF_GRID),
            "targets_yaml": str(_TARGETS),
            "_perturb": None,  # negative-control hook (None = real run)
        }

    # ---- TSL side -------------------------------------------------------- #
    def run_tsl(self, fixture: dict[str, Any]) -> dict[str, Any]:
        _ensure_engine_on_path()
        from techniques.breakeven_payroll import compute
        from techniques.breakeven_payroll.workbook_input import read_workbook

        inp = read_workbook(fixture["workbook"])

        # Negative-control hook: optionally corrupt one input so the runner /
        # discrimination test can confirm the check BLOCKs on a wrong build.
        pert = fixture.get("_perturb")
        if pert == "drop_may_anchor":
            # Drop the May-2025 (HPLFS-handoff) CNP16OV anchor -> the Jun
            # diff-splice base vanishes and the Jun bridge increment is lost
            # (the exact contract bug the May anchor fixes; shifts 2025Q1 ~1.8k).
            inp["cnp16ov"] = inp["cnp16ov"].iloc[1:]
        elif pert == "perturb_cbo":
            inp["u_star"] = inp["u_star"] + 0.10  # +0.10pp on noncyclical u*

        out = compute(inp)
        qp = out["quarterly_persons"]
        grid = out["grid"]
        gmap = {(r["preset"], r["u_star_def"]): float(r["breakeven_kmo"])
                for _, r in grid.iterrows()}

        # Three-way CBO_Feb2026 preset assert, arms 1+2 (arm 3 = the reference
        # literal in run_reference). Arm 2 reads the LIVE bundled v2 template's
        # gross_migration_sums tab — NOT the byte-frozen 12-tab parity fixture
        # workbook (which deliberately has no sums tab; ruling 2026-08-08).
        from techniques.breakeven_payroll._dispatch import FROZEN_PRESETS
        from techniques.breakeven_payroll.migration import derived_preset_from_sums
        from techniques.breakeven_payroll.workbook_input import read_gross_migration_sums
        gm = read_gross_migration_sums(_BUNDLED_TEMPLATE)
        return {
            "path": {f"{p.year}Q{p.quarter}": float(v) for p, v in qp.items()},
            "grid": {f"{a}|{b}": gmap[(a, b)] for a, b in _GRID_KEYS},
            "preset_literal": float(FROZEN_PRESETS["CBO_Feb2026"]),
            "preset_template_derived": (
                float(derived_preset_from_sums(gm)) if gm is not None else None),
        }

    # ---- reference side (the source repo's frozen output) ---------------- #
    def run_reference(self, fixture: dict[str, Any]) -> dict[str, Any]:
        import csv

        path: dict[str, float] = {}
        with open(fixture["ref_path_csv"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                per = list(row.values())[0]
                path[str(per).replace("-Q", "Q")] = float(row["breakeven_published"])
        grid: dict[str, float] = {}
        with open(fixture["ref_grid_csv"], newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                grid[f"{row['preset']}|{row['u_star_def']}"] = float(row["breakeven_kmo"])
        return {"path": path, "grid": {f"{a}|{b}": grid[f"{a}|{b}"] for a, b in _GRID_KEYS},
                # Arm 3: the SOURCE repo's params entry (test-asserted equal to
                # its code derivation there; committed vintage @ 99c03ba).
                "preset_reference": 573959.0}

    # ---- compare --------------------------------------------------------- #
    def compare(self, tsl: dict[str, Any], ref: dict[str, Any]) -> ParityResult:
        ladder = get_ladder(self.technique_id)

        def _qnum(k: str) -> int:
            y, q = k.split("Q")
            return int(y) * 4 + int(q)

        stable = _qnum(_STABLE_START)
        common = sorted(set(tsl["path"]) & set(ref["path"]), key=_qnum)
        stable_keys = [k for k in common if _qnum(k) >= stable]
        tsl_path = np.array([tsl["path"][k] for k in stable_keys])
        ref_path = np.array([ref["path"][k] for k in stable_keys])
        path_cmp = _compare_vector(tsl_path, ref_path, ladder["path"])

        gkeys = [f"{a}|{b}" for a, b in _GRID_KEYS]
        tsl_grid = np.array([tsl["grid"][k] for k in gkeys])
        ref_grid = np.array([ref["grid"][k] for k in gkeys])
        grid_cmp = _compare_vector(tsl_grid, ref_grid, ladder["grid"])

        # Loose anchor overlay (reported, not gated).
        import yaml
        targets = yaml.safe_load(Path(_TARGETS).read_text(encoding="utf-8")) or {"targets": {}}
        t = targets.get("targets", {})
        anchors = []
        path_series = {k: tsl["path"][k] for k in tsl["path"]}
        for spec in list(t.get("decade_averages", [])) + list(t.get("points", [])):
            if "window" in spec:
                a, b = [_qnum(str(x).replace("-Q", "Q")) for x in spec["window"]]
                vals = [v for k, v in path_series.items() if a <= _qnum(k) <= b]
                comp = float(np.mean(vals)) if vals else float("nan")
            else:
                pk = str(spec["period"]).replace("-Q", "Q")
                comp = float(path_series.get(pk, float("nan")))
            ref_v = float(spec["reference"])
            tol = float(spec.get("abs_tol", ladder.get("anchor_abs_tol", 15000.0)))
            ok = abs(comp - ref_v) <= tol if comp == comp else False
            anchors.append({"id": spec["id"], "computed": round(comp), "reference": round(ref_v),
                            "abs_diff": round(abs(comp - ref_v)) if comp == comp else None,
                            "abs_tol": round(tol), "status": "PASS" if ok else "CHECK"})

        # Three-way CBO_Feb2026 preset assert (<=1e-6): engine frozen literal ==
        # LIVE-bundled-template derivation == source-repo reference literal.
        lit = tsl.get("preset_literal")
        drv = tsl.get("preset_template_derived")
        refp = ref.get("preset_reference")
        three_ok = (lit is not None and drv is not None and refp is not None
                    and abs(lit - refp) <= 1e-6 and abs(drv - refp) <= 1e-6)
        preset_cmp = {
            "status": "PASS" if three_ok else "BLOCK",
            "literal": lit, "template_derived": drv, "reference": refp,
            "template_arm_source": "bundled v2 template gross_migration_sums tab",
        }

        statuses = [path_cmp["status"], grid_cmp["status"], preset_cmp["status"]]
        outcome = "BLOCK" if "BLOCK" in statuses else ("CAVEAT" if "CAVEAT" in statuses else "PASS")
        return ParityResult(
            technique_id=self.technique_id,
            outcome=outcome,
            metrics={"path": path_cmp, "grid": grid_cmp,
                     "cbo_feb2026_preset_threeway": preset_cmp},
            diagnostics={
                "n_quarters_compared": len(stable_keys),
                "stable_region": f"{_STABLE_START}..{stable_keys[-1] if stable_keys else '?'}",
                "path_max_abs_diff_jobs_mo": float(path_cmp.get("max_abs_diff", float("nan"))),
                "grid_max_abs_diff_kmo": float(grid_cmp.get("max_abs_diff", float("nan"))),
                "tie_outs": {"Brookings_mid|noncyclical": tsl["grid"]["Brookings_mid|noncyclical"],
                             "MS_house|noncyclical": tsl["grid"]["MS_house|noncyclical"]},
                "anchors": anchors,
            },
        )
