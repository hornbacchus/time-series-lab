"""Shared pytest fixtures for the Bond Yield Forecast test suite (post-TSL migration)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

# Add TSL's engine/ directory to sys.path so `techniques.bond_yield_forecast.X`
# imports resolve. This mirrors the pattern in engine/tests/test_identification_conventions.py
# (TSL's existing convention for test-local sys.path setup).
_ENGINE_DIR = str(Path(__file__).resolve().parents[3])
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.bond_yield_forecast._synthetic import synthetic_panel  # noqa: E402
from techniques.bond_yield_forecast.data import load_config  # noqa: E402

# PROJECT_ROOT in the post-migration layout is the subpackage root
# (engine/techniques/bond_yield_forecast/), since config/, tests/,
# and resources/ are siblings under that directory.
PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def sample_config():
    """Parsed default.yaml from the project's config directory."""
    return load_config(PROJECT_ROOT / "config" / "default.yaml")


@pytest.fixture
def fixture_workbook_path():
    """Path to tests/fixtures/sample_input.xlsx; skips if not generated yet."""
    p = PROJECT_ROOT / "tests" / "fixtures" / "sample_input.xlsx"
    if not p.exists():
        pytest.skip(
            f"Test fixture not generated yet at {p}. "
            f"Run: python tools/generate_template.py"
        )
    return p


@pytest.fixture
def template_workbook_path():
    """Path to templates/input_template.xlsx; skips if not generated yet."""
    p = PROJECT_ROOT / "templates" / "input_template.xlsx"
    if not p.exists():
        pytest.skip(
            f"Template not generated yet at {p}. "
            f"Run: python tools/generate_template.py"
        )
    return p


@pytest.fixture
def clean_raw_dataframes():
    """Clean in-memory equivalent of load_input_workbook output (string Quarter index)."""
    macro_df, yields_df = synthetic_panel(20, seed=7)
    return {
        "macro_raw": macro_df.set_index("Quarter"),
        "yields_raw": yields_df.set_index("Quarter"),
    }
