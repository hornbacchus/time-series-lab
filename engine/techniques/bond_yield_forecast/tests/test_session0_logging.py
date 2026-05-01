"""Tests for S0.2: re-entrant CLI helpers (logging file handler context).

Verifies that repeated CLI helper invocations do not accumulate
FileHandlers on the root logger; each call's log file gets only
that call's records.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytest


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_root_logger_handler_count_unchanged(tmp_path):
    """Root logger handler count is the same before and after a CLI helper call.

    The S0.2 context manager attaches a FileHandler for the helper's
    duration and detaches at function exit. No accumulation.
    """
    from cli.run_forecast import main

    project_root = Path(__file__).resolve().parent.parent
    workbook = project_root / "data" / "raw" / "bvar_inputs.xlsx"
    if not workbook.exists():
        pytest.skip(f"{workbook} not present; smoke skipped")

    root = logging.getLogger()
    handlers_before = list(root.handlers)
    rc = main([
        "--list-scenarios",
        "--input", str(workbook),
        "--working-dir", str(project_root),
    ])
    assert rc == 0
    handlers_after = list(root.handlers)
    assert handlers_before == handlers_after, (
        f"Root logger handlers changed across helper invocation. "
        f"Before: {handlers_before}, After: {handlers_after}"
    )


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_double_invocation_does_not_accumulate_handlers(tmp_path):
    """Two CLI helper invocations do not accumulate FileHandlers on root.

    Counts handlers before, runs the helper twice, counts after. The
    S0.2 _log_to_file context manager attaches a FileHandler for the
    helper's duration and detaches at function exit — if either run
    leaks a handler, the count will increase.

    Uses --process-data which calls into _process_data (does NOT use
    _log_to_file currently — it writes data/processed/ artifacts but
    not a per-run log file). So this test verifies the no-accumulation
    invariant holds for the helpers that DO use _log_to_file.
    """
    from cli.run_forecast import main

    project_root = Path(__file__).resolve().parent.parent
    workbook = project_root / "data" / "raw" / "bvar_inputs.xlsx"
    if not workbook.exists():
        pytest.skip(f"{workbook} not present; smoke skipped")

    out_a = tmp_path / "out_a"
    out_b = tmp_path / "out_b"

    root = logging.getLogger()
    n_handlers_before = len(root.handlers)

    rc_a = main([
        "--process-data",
        "--input", str(workbook),
        "--output-dir", str(out_a),
        "--working-dir", str(project_root),
    ])
    assert rc_a == 0

    rc_b = main([
        "--process-data",
        "--input", str(workbook),
        "--output-dir", str(out_b),
        "--working-dir", str(project_root),
    ])
    assert rc_b == 0

    n_handlers_after = len(root.handlers)
    assert n_handlers_after == n_handlers_before, (
        f"Handler count grew across two CLI invocations: "
        f"{n_handlers_before} -> {n_handlers_after}. "
        f"S0.2 should ensure detachment at helper exit. "
        f"Handlers now: {root.handlers}"
    )


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_log_to_file_context_manager_isolation(tmp_path):
    """_log_to_file attaches one FileHandler inside the with-block and
    detaches on exit. Direct unit test of the context manager.
    """
    from cli.run_forecast import _log_to_file

    log_path = tmp_path / "test.log"
    root = logging.getLogger()
    n_before = len(root.handlers)

    with _log_to_file(log_path):
        n_inside = len(root.handlers)
        logging.info("inside-with-block message")
        # Exactly one new handler should be attached (the FileHandler).
        assert n_inside == n_before + 1, (
            f"Expected 1 new handler inside with-block; got "
            f"{n_inside - n_before} new ({root.handlers})"
        )

    n_after = len(root.handlers)
    assert n_after == n_before, (
        f"Handler not detached after with-block: {n_before} -> {n_after}"
    )
    # The log file should contain the message we logged inside.
    assert log_path.exists()
    content = log_path.read_text(encoding="utf-8")
    assert "inside-with-block message" in content


# ---------------------------------------------------------------------------
# S0.8 — pandas display options + matplotlib backend re-entrancy
# ---------------------------------------------------------------------------


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_pandas_options_unchanged_after_process_data(tmp_path):
    """_process_data wraps display option mutations in pd.option_context
    so they do not leak across CLI invocations."""
    import pandas as pd
    from cli.run_forecast import main

    project_root = Path(__file__).resolve().parent.parent
    workbook = project_root / "data" / "raw" / "bvar_inputs.xlsx"
    if not workbook.exists():
        pytest.skip(f"{workbook} not present; smoke skipped")

    width_before = pd.get_option("display.width")
    max_cols_before = pd.get_option("display.max_columns")
    precision_before = pd.get_option("display.precision")

    rc = main([
        "--process-data",
        "--input", str(workbook),
        "--output-dir", str(tmp_path / "out"),
        "--working-dir", str(project_root),
    ])
    assert rc == 0

    assert pd.get_option("display.width") == width_before
    assert pd.get_option("display.max_columns") == max_cols_before
    assert pd.get_option("display.precision") == precision_before


@pytest.mark.skip(
    reason="CLI did not migrate to TSL (archived as _legacy_cli.py.archive); this test exercised CLI side-effects that are now reproduced via the TSL engine_worker dispatch path (Session 2+) instead."
)
def test_matplotlib_backend_unchanged_when_already_non_interactive(tmp_path):
    """_save_forecast_plots and _save_validation_plots respect a
    non-interactive backend already in place."""
    import matplotlib
    matplotlib.use("Agg")  # ensure non-interactive
    backend_before = matplotlib.get_backend()

    # Trigger _save_forecast_plots via the function directly with a
    # tiny YieldCurveForecast.
    from techniques.bond_yield_forecast.conditioning import (
        ConditionalForecaster, PosteriorMetadata, YieldCurveForecast,
    )
    # Build a minimal yc by reusing the test_conditioning fixture path.
    from techniques.bond_yield_forecast.tests.test_conditioning import (
        _build_small_conditional_forecast, _toy_pca_dict,
    )
    cf = _build_small_conditional_forecast()
    yc = cf.to_yield_space(_toy_pca_dict())
    from cli.run_forecast import _save_forecast_plots
    _save_forecast_plots(tmp_path / "plots", yc)

    backend_after = matplotlib.get_backend()
    assert backend_before == backend_after, (
        f"matplotlib backend changed across helper invocation: "
        f"{backend_before} -> {backend_after}"
    )
