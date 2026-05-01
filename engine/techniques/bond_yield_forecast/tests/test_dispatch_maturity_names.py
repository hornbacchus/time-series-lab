"""BYF-Mod-2 (B-Mod1-1, 2026-05-01) — regression test for the dispatch
attribute-name fix in ``_dispatch.py``.

Pre-fix bug: ``_build_yield_forecast_table`` read
``yield_forecast.yield_names`` (nonexistent attribute) and fell
through to placeholder ``Maturity_0..Maturity_N`` labels in the user-
visible Yield Forecast table. The conditioning module's
``YieldCurveForecast`` dataclass exposes the canonical labels via
``maturity_names`` (set from ``pca_dict["yield_names"]`` at
``conditioning.py:768``).

Fix: dual-attribute lookup at ``_dispatch.py:321`` —
``maturity_names`` primary, ``yield_names`` secondary
(forward-compat), placeholder ``Maturity_N`` fallback last.

Asserted invariants:
  - On the canonical 10-maturity fixture, the Yield Forecast table's
    Maturity column reads canonical ``treasury_3m..treasury_30y``
    (NOT placeholder ``Maturity_0..Maturity_9``).
  - The ``maturities_populated`` audit field surfaces the same
    canonical labels.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_ENGINE_DIR = str(pathlib.Path(__file__).resolve().parents[3])
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext
from techniques import bond_yield_forecast as byf


_CANONICAL_FIXTURE = (
    pathlib.Path(__file__).resolve().parent
    / "fixtures" / "test_input_canonical.xlsx"
)

_EXPECTED_10MAT_LABELS = [
    "treasury_3m", "treasury_6m", "treasury_1y", "treasury_2y",
    "treasury_3y", "treasury_5y", "treasury_7y", "treasury_10y",
    "treasury_20y", "treasury_30y",
]


@pytest.fixture
def _canonical_run_result():
    """Run BYF dispatch with reduced-chain config; return the response."""
    if not _CANONICAL_FIXTURE.exists():
        pytest.skip(f"Canonical fixture missing: {_CANONICAL_FIXTURE}")
    ctx = RunContext({
        "run_id": "test_dispatch_maturity_names",
        "technique_id": "bond_yield_forecast",
        "preset": "Balanced",
        "seed": 20260427,
        "frequency": "quarterly",
        "time": [],
        "series": [],
        "params": {
            "input_workbook": str(_CANONICAL_FIXTURE),
            "n_draws": 1000,
            "n_burn": 250,
            "n_paths_per_draw": 50,
            "n_draws_subsample": 1000,
        },
    })
    res = byf.run(ctx, lambda *a, **k: None)
    assert res.get("status") == "success", (
        f"BYF dispatch failed: {res.get('error_message')}"
    )
    return res


def test_dispatch_renders_treasury_maturity_names_not_placeholders(
    _canonical_run_result,
):
    """B-Mod1-1 regression: Yield Forecast table Maturity column must
    contain canonical ``treasury_*`` labels, not ``Maturity_N``.

    Captures the user-visible label correctness that the pre-Mod-2
    dispatch (with the attribute-name typo) silently failed: tables
    rendered with placeholder ``Maturity_0..Maturity_9`` masking the
    canonical labels.
    """
    res = _canonical_run_result
    forecast_table = next(
        (t for t in res.get("tables", [])
         if "Yield Forecast" in (t.get("name") or "")),
        None,
    )
    assert forecast_table is not None, "Yield Forecast table missing"
    # Maturity column index is 2 (Scenario, Horizon, Maturity, ...)
    maturity_labels = sorted(
        {row[2] for row in forecast_table["rows"]}
    )
    # Must NOT contain any placeholder labels.
    placeholders = [m for m in maturity_labels if m.startswith("Maturity_")]
    assert not placeholders, (
        f"Forecast table Maturity column contains placeholder labels "
        f"(B-Mod1-1 regressed); placeholders={placeholders}"
    )
    # Must contain the expected canonical 10-maturity labels.
    expected_set = set(_EXPECTED_10MAT_LABELS)
    actual_set = set(maturity_labels)
    missing = expected_set - actual_set
    extra = actual_set - expected_set
    assert not missing, (
        f"Canonical maturity labels missing from Forecast table: {missing}"
    )
    assert not extra, (
        f"Unexpected maturity labels in Forecast table: {extra}"
    )


def test_dispatch_audit_fields_maturities_populated(
    _canonical_run_result,
):
    """BYF-Mod-1: audit_fields["maturities_populated"] should expose
    the same canonical labels."""
    res = _canonical_run_result
    audit = res.get("audit_fields") or {}
    populated = list(audit.get("maturities_populated") or [])
    assert populated == _EXPECTED_10MAT_LABELS, (
        f"audit_fields[maturities_populated] mismatch.\n"
        f"  expected: {_EXPECTED_10MAT_LABELS}\n"
        f"  got:      {populated}"
    )
    n_pop = audit.get("n_maturities_populated")
    assert n_pop == 10, (
        f"audit_fields[n_maturities_populated]={n_pop} (expected 10)"
    )
