"""Tests for S0.5: structured warnings hierarchy.

Verifies the three subclasses fire at their intended sites and that the
prior stderr-print double-output is gone.
"""

from __future__ import annotations

import warnings

import pandas as pd
import pytest

from techniques.bond_yield_forecast.exceptions import (
    BVARWarning,
    ConvergenceWarning,
    ProjectionAtBoundWarning,
    ValidationDomainWarning,
)


def _bad_diag_df():
    """Synthetic convergence-diagnostics DataFrame with overall < 90%
    AND a parameter group < 80%, to trigger ConvergenceWarning."""
    rows = []
    # 10 omega params, all converged (100%)
    for i in range(10):
        rows.append({
            "parameter": f"omega[v{i}]",
            "parameter_group": "omega",
            "converged": True,
        })
    # 10 mu params, only 5 converged (50% — below 80% group floor)
    for i in range(10):
        rows.append({
            "parameter": f"mu[v{i}]",
            "parameter_group": "mu",
            "converged": i < 5,
        })
    # 10 phi params, 7 converged (70% — below 80% floor)
    for i in range(10):
        rows.append({
            "parameter": f"phi[v{i}]",
            "parameter_group": "phi",
            "converged": i < 7,
        })
    df = pd.DataFrame(rows).set_index("parameter")
    return df


def test_convergence_warning_subclass_chain():
    """ConvergenceWarning subclasses BVARWarning subclasses UserWarning."""
    assert issubclass(ConvergenceWarning, BVARWarning)
    assert issubclass(BVARWarning, UserWarning)


def test_projection_at_bound_warning_subclass_chain():
    assert issubclass(ProjectionAtBoundWarning, BVARWarning)


def test_validation_domain_warning_subclass_chain():
    assert issubclass(ValidationDomainWarning, BVARWarning)


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_convergence_warning_fires_on_low_pass_rate(capsys):
    """_print_convergence_summary emits a ConvergenceWarning when overall
    pass rate < 90% AND there's a group below 80%."""
    from cli.run_forecast import _print_convergence_summary

    diag = _bad_diag_df()
    with pytest.warns(ConvergenceWarning) as record:
        _print_convergence_summary(diag)
    assert len(record) >= 1
    # The warning message includes overall and per-group detail.
    msg = str(record[0].message)
    assert "overall convergence" in msg
    # Verify NO stderr "WARNING:" double-output (S0.5 requirement).
    captured = capsys.readouterr()
    assert "WARNING: overall convergence" not in captured.err
    assert "WARNING: at least one parameter group" not in captured.err


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_no_convergence_warning_when_pass_rates_are_clean():
    """If overall pass >= 90% AND all groups >= 80%, no warning fires."""
    from cli.run_forecast import _print_convergence_summary

    rows = [
        {"parameter": f"x{i}", "parameter_group": "g", "converged": True}
        for i in range(20)
    ]
    diag = pd.DataFrame(rows).set_index("parameter")
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        _print_convergence_summary(diag)  # would raise if warning fires


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_projection_at_bound_warning_fires(capsys):
    """_print_optimization_summary emits ProjectionAtBoundWarning when
    opt_result['warnings_hard'] is non-empty."""
    from cli.run_forecast import _print_optimization_summary

    fake_opt_result = {
        "method": "glp_composite",
        "panel_dimensions": {"T": 100, "n": 6, "n_lags": 4},
        "recommended": {
            "lambda_1": 0.5, "lambda_2": 1.0, "lambda_3": 1.0,
            "lambda_sc": 1.0, "lambda_io": 10.0,
            "log_marginal_likelihood": -1000.0, "source": "numerical",
        },
        "warnings_hard": [
            "WARNING: optimal lambda_io = 10 is at the upper bound (0.0, 10.0).",
        ],
        "warnings_soft": [],
        "runtime_seconds": 1.0,
    }
    with pytest.warns(ProjectionAtBoundWarning) as record:
        _print_optimization_summary(fake_opt_result)
    assert len(record) >= 1
    assert "lambda_io" in str(record[0].message)
    # Confirm no stderr double-output.
    captured = capsys.readouterr()
    assert "lambda_io = 10 is at the upper bound" not in captured.err
