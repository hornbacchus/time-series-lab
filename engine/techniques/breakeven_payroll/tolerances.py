"""Reconciliation tolerance ladders.

PROVISIONAL: the authoritative per-target tolerances live in
``tests/fixtures/fed_reference_targets.yaml`` and override these. This module is
the in-code default + justification, decoupled from the evolving params.yaml.
"""

from __future__ import annotations

TOLERANCE_LADDERS: dict[str, dict] = {
    "fed_breakeven_path": {
        "type": "absolute",
        "primary": {"abs_tol": 12000.0},
        "caveat_multiplier": 2.0,  # CAVEAT band = (abs_tol, caveat_multiplier * abs_tol]
        "per_metric": {
            "avg_1970s": {"abs_tol": 15000.0},
            "avg_2010s": {"abs_tol": 12000.0},
            "pt_late_2020": {"abs_tol": 15000.0},
            "avg_2023_24": {"abs_tol": 12000.0},
            "avg_2025": {"abs_tol": 12000.0},
            "avg_2026": {"abs_tol": 10000.0},  # full-year 2026 average; the < 10k gate
        },
        "justification": (
            "Provisional decade-avg +/-10-15k; 2026 full-year average < 10k. "
            "Finalized against the Phase-1 targets YAML."
        ),
    },
}


def metric_abs_tol(check_id: str, metric_id: str, default_abs: float = 12000.0) -> float:
    ladder = TOLERANCE_LADDERS.get(check_id, {})
    pm = ladder.get("per_metric", {}).get(metric_id, {})
    return float(pm.get("abs_tol", ladder.get("primary", {}).get("abs_tol", default_abs)))


def caveat_multiplier(check_id: str) -> float:
    return float(TOLERANCE_LADDERS.get(check_id, {}).get("caveat_multiplier", 2.0))
