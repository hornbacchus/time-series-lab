"""Tests for src/bvar/data.py — data ingestion, validation, and PCA."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast._synthetic import synthetic_panel
from techniques.bond_yield_forecast.data import (
    InputValidationError,
    align_panel,
    build_panel,
    fit_pca,
    load_config,
    load_input_workbook,
    project_to_pcs,
    reconstruct_yields,
    validate_input,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


# ----------------------------------------------------------------------
# 1. load_config
# ----------------------------------------------------------------------


def test_load_config_parses_default_yaml():
    config = load_config(PROJECT_ROOT / "config" / "default.yaml")
    for key in ("data", "model", "estimation", "forecast"):
        assert key in config, f"missing top-level key '{key}'"
    assert len(config["data"]["macro_variables"]) == 3
    # BYF-Mod-1 (2026-05-01): declarative grid expanded 10 → 34
    # maturities (1M-30Y; monthly under 1Y plus annual at every
    # integer year through 30Y). Runtime usage is data-driven via
    # ``_resolve_populated_yield_columns`` — workbook may populate
    # any subset of these 34, with N>=3 enforced.
    assert len(config["data"]["yield_variables"]) == 34
    for spec in config["data"]["macro_variables"].values():
        assert "column" in spec and "units" in spec
    for spec in config["data"]["yield_variables"].values():
        assert "column" in spec and "maturity_years" in spec
    assert config["data"]["pca"]["n_components"] == 3
    assert config["data"]["pca"]["component_names"] == [
        "pc1_level",
        "pc2_slope",
        "pc3_curvature",
    ]


# ----------------------------------------------------------------------
# 2. load_input_workbook
# ----------------------------------------------------------------------


def test_load_input_workbook_reads_template(template_workbook_path):
    raw = load_input_workbook(template_workbook_path)
    assert "macro_raw" in raw
    assert "yields_raw" in raw
    assert "Real GDP Growth (Q/Q SAAR)" in raw["macro_raw"].columns
    assert "Headline CPI Inflation (Q/Q annualized)" in raw["macro_raw"].columns
    assert "Fed Funds Rate (quarterly average)" in raw["macro_raw"].columns
    for label in ["3M", "6M", "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y"]:
        assert label in raw["yields_raw"].columns


# ----------------------------------------------------------------------
# 3-10. validate_input
# ----------------------------------------------------------------------


def test_validate_input_passes_clean_data(sample_config, clean_raw_dataframes):
    result = validate_input(clean_raw_dataframes, sample_config)
    assert "macro" in result and "yields" in result
    assert "real_gdp_growth" in result["macro"].columns
    assert "headline_cpi" in result["macro"].columns
    assert "fed_funds_rate" in result["macro"].columns
    assert "treasury_3m" in result["yields"].columns
    assert "treasury_30y" in result["yields"].columns
    assert isinstance(result["macro"].index, pd.PeriodIndex)
    assert result["macro"].index.freqstr.startswith("Q")
    assert isinstance(result["yields"].index, pd.PeriodIndex)
    assert not result["macro"].isna().any().any()
    assert not result["yields"].isna().any().any()


def test_validate_input_fails_missing_sheet(sample_config, clean_raw_dataframes):
    raw = {"macro_raw": clean_raw_dataframes["macro_raw"]}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "missing_sheet"


def test_validate_input_fails_missing_column(sample_config, clean_raw_dataframes):
    macro = clean_raw_dataframes["macro_raw"].drop(
        columns=["Real GDP Growth (Q/Q SAAR)"]
    )
    raw = {"macro_raw": macro, "yields_raw": clean_raw_dataframes["yields_raw"]}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "missing_column"
    assert "Real GDP Growth (Q/Q SAAR)" in str(exc_info.value)


def test_validate_input_fails_bad_quarter_format(sample_config, clean_raw_dataframes):
    macro = clean_raw_dataframes["macro_raw"].copy()
    new_index = list(macro.index)
    new_index[2] = "1990 Q3"  # space instead of dash
    macro.index = pd.Index(new_index, name="Quarter")
    raw = {"macro_raw": macro, "yields_raw": clean_raw_dataframes["yields_raw"]}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "bad_quarter_format"
    assert "1990 Q3" in str(exc_info.value)


def test_validate_input_fails_quarter_gap(sample_config, clean_raw_dataframes):
    macro = clean_raw_dataframes["macro_raw"].drop(index="1990-Q3")
    yields = clean_raw_dataframes["yields_raw"].drop(index="1990-Q3")
    raw = {"macro_raw": macro, "yields_raw": yields}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "quarter_gap"


def test_validate_input_fails_non_numeric(sample_config, clean_raw_dataframes):
    macro = clean_raw_dataframes["macro_raw"].copy()
    col = "Real GDP Growth (Q/Q SAAR)"
    new_values = list(macro[col].values)
    new_values[2] = "N/A"
    macro[col] = new_values
    raw = {"macro_raw": macro, "yields_raw": clean_raw_dataframes["yields_raw"]}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "non_numeric"
    assert "N/A" in str(exc_info.value)


def test_validate_input_fails_interior_nan(sample_config, clean_raw_dataframes):
    macro = clean_raw_dataframes["macro_raw"].copy()
    col = "Real GDP Growth (Q/Q SAAR)"
    macro.loc["1991-Q1", col] = np.nan
    raw = {"macro_raw": macro, "yields_raw": clean_raw_dataframes["yields_raw"]}
    with pytest.raises(InputValidationError) as exc_info:
        validate_input(raw, sample_config)
    assert exc_info.value.rule == "interior_nan"
    assert "1991Q1" in str(exc_info.value) or "1991-Q1" in str(exc_info.value)


def test_validate_input_warns_out_of_bounds(
    sample_config, clean_raw_dataframes, caplog
):
    yields = clean_raw_dataframes["yields_raw"].copy()
    yields.loc["1991-Q1", :] = yields.loc["1991-Q1", :] / 100.0  # decimal-form error
    raw = {
        "macro_raw": clean_raw_dataframes["macro_raw"],
        "yields_raw": yields,
    }
    with caplog.at_level(logging.WARNING, logger="bvar.data"):
        validate_input(raw, sample_config)
    messages = [rec.getMessage() for rec in caplog.records]
    assert any(
        "decimal form" in m for m in messages
    ), f"expected 'decimal form' in warnings, got: {messages}"


# ----------------------------------------------------------------------
# 11-12. PCA: recovery and round-trip
# ----------------------------------------------------------------------


def _yield_panel_with_period_index(n_quarters: int, seed: int) -> pd.DataFrame:
    _, yields_df = synthetic_panel(n_quarters=n_quarters, seed=seed)
    yields_df = yields_df.set_index("Quarter")
    yields_df.index = pd.PeriodIndex(
        [pd.Period(q, freq="Q-DEC") for q in yields_df.index], freq="Q-DEC"
    )
    return yields_df


def test_fit_pca_recovers_known_loadings():
    yields = _yield_panel_with_period_index(60, seed=11)
    pca = fit_pca(
        yields,
        n_components=3,
        component_names=["pc1_level", "pc2_slope", "pc3_curvature"],
    )
    L = pca["loadings"]

    assert (L[:, 0] > 0).all(), f"PC1 loadings should all be positive; got {L[:, 0]}"
    assert L[-1, 1] > L[0, 1], (
        f"PC2 should have positive slope (long > short); "
        f"got first={L[0, 1]}, last={L[-1, 1]}"
    )
    mid = L.shape[0] // 2
    assert L[mid, 2] > 0, f"PC3 should be positive at intermediate maturity; got {L[mid, 2]}"

    total_var = float(pca["explained_variance_ratio"].sum())
    assert total_var > 0.999, f"explained variance ratio sum {total_var} should exceed 0.999"


def test_project_and_reconstruct_round_trip():
    yields = _yield_panel_with_period_index(60, seed=11)
    pca = fit_pca(
        yields,
        n_components=3,
        component_names=["pc1_level", "pc2_slope", "pc3_curvature"],
    )
    pcs = project_to_pcs(yields, pca)
    recon = reconstruct_yields(pcs, pca)
    assert list(recon.columns) == list(yields.columns)
    assert (recon.index == yields.index).all()

    max_err = float(np.max(np.abs(yields.to_numpy() - recon.to_numpy())))
    assert max_err < 0.01, (
        f"Round-trip max abs error {max_err} should be < 0.01 (1 bp). "
        f"Synthetic data is exactly rank 3; reconstruction must be near-exact."
    )


# ----------------------------------------------------------------------
# 13. build_panel end-to-end
# ----------------------------------------------------------------------


@pytest.mark.skip(
    reason="build_panel(output_dir=...) writes parquet outputs (panel.parquet, "
           "yield_panel.parquet) which require pyarrow. This is the BVAR CLI's "
           "data-export path; the TSL dispatch path uses read_unified_workbook() "
           "directly without the parquet roundtrip. pyarrow is not in TSL's "
           "hard-dep set; if a future Phase 4 use case needs parquet output "
           "from process_data(), pin pyarrow in MANIFEST.toml."
)
def test_build_panel_full_pipeline(sample_config, fixture_workbook_path, tmp_path):
    output_dir = tmp_path / "processed"
    result = build_panel(
        sample_config, input_path=fixture_workbook_path, output_dir=output_dir
    )

    assert set(result.keys()) == {"panel", "yield_panel", "pca", "sample"}

    panel = result["panel"]
    expected_cols = [
        "real_gdp_growth",
        "headline_cpi",
        "fed_funds_rate",
        "pc1_level",
        "pc2_slope",
        "pc3_curvature",
    ]
    assert list(panel.columns) == expected_cols
    assert isinstance(panel.index, pd.PeriodIndex)
    assert panel.index.freqstr.startswith("Q")
    assert not panel.isna().any().any()

    yield_panel = result["yield_panel"]
    assert len(yield_panel.columns) == 10
    assert "treasury_3m" in yield_panel.columns
    assert "treasury_30y" in yield_panel.columns

    sample_start, sample_end = result["sample"]
    assert sample_start <= panel.index[0]
    assert panel.index[-1] <= sample_end

    assert (output_dir / "panel.parquet").exists()
    assert (output_dir / "yield_panel.parquet").exists()
    assert (output_dir / "pca.npz").exists()

    var_total = float(result["pca"]["explained_variance_ratio"].sum())
    assert var_total > 0.99, f"explained variance ratio sum {var_total} should exceed 0.99"


# ----------------------------------------------------------------------
# 14. align_panel
# ----------------------------------------------------------------------


def test_align_panel_trims_and_raises():
    idx = pd.period_range("2020-Q1", periods=10, freq="Q-DEC")
    df = pd.DataFrame(
        {
            "a": [np.nan, np.nan, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, np.nan, np.nan],
            "b": [np.nan, np.nan, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, np.nan, np.nan],
        },
        index=idx,
    )
    trimmed = align_panel(df)
    assert len(trimmed) == 6
    assert trimmed.index[0] == pd.Period("2020-Q3", freq="Q-DEC")
    assert trimmed.index[-1] == pd.Period("2021-Q4", freq="Q-DEC")
    assert not trimmed.isna().any().any()

    df2 = df.copy()
    df2.loc[pd.Period("2021-Q1", freq="Q-DEC"), "a"] = np.nan
    with pytest.raises(ValueError, match="Interior NaN"):
        align_panel(df2)
