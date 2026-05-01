"""BYF-Mod-1 (2026-05-01) — sparse-column auto-detection tests.

Validates the seven scenarios called out in the modification plan §1.8:

    1. Full 34-column input parses correctly (all 34 maturities used).
    2. Sparse 7-column subset parses correctly; downstream sees only 7
       maturities; PCA fits on 7; loadings shape (7, 3).
    3. Below-floor rejection: N=2 populated maturities -> clear error
       referencing the PCA factor structure floor.
    4. Zero-population rejection: BondYield_Yields header-only -> clear
       error.
    5. Header text variants canonicalize: "1Y" / "1Yr" / "1-year" /
       "1 Year" all -> "1Y".
    6. Unrecognized headers rejected with clear error (no silent
       acceptance of "garbage").
    7. Partial column data rejection: header present, some rows blank
       -> clear error pointing at row-level sparsity (out of scope).

Tests build small in-memory DataFrames (no .xlsx round-trip needed)
and exercise ``data.validate_input`` + ``data._resolve_populated_yield_columns``
directly.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from techniques.bond_yield_forecast.data import (
    InputValidationError,
    MIN_MATURITY_COUNT,
    _canonicalize_maturity_header,
    _resolve_populated_yield_columns,
    validate_input,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


_DEFAULT_MACRO_COLS = [
    "Real GDP Growth (Q/Q SAAR)",
    "Headline CPI Inflation (Q/Q annualized)",
    "Fed Funds Rate (quarterly average)",
]
_FULL_34_HEADERS = [
    "1M", "3M", "6M", "9M",
    "1Y", "2Y", "3Y", "4Y", "5Y", "6Y", "7Y", "8Y", "9Y", "10Y",
    "11Y", "12Y", "13Y", "14Y", "15Y", "16Y", "17Y", "18Y", "19Y", "20Y",
    "21Y", "22Y", "23Y", "24Y", "25Y", "26Y", "27Y", "28Y", "29Y", "30Y",
]


def _config_with_full_grid():
    """Construct a config-like dict matching default.yaml's 34-maturity grid.

    Includes only the keys ``data.macro_variables`` and
    ``data.yield_variables`` since those are the keys ``validate_input``
    uses; downstream sample/PCA validation isn't exercised here.
    """
    macro_vars = {
        "real_gdp_growth": {"column": _DEFAULT_MACRO_COLS[0], "units": "percent"},
        "headline_cpi": {"column": _DEFAULT_MACRO_COLS[1], "units": "percent"},
        "fed_funds_rate": {"column": _DEFAULT_MACRO_COLS[2], "units": "percent"},
    }
    yield_vars = {}
    # Map each canonical header to a treasury_<n><unit> key.
    for hdr in _FULL_34_HEADERS:
        if hdr.endswith("M"):
            n = int(hdr[:-1])
            key = f"treasury_{n}m"
            years = n / 12.0
        else:
            n = int(hdr[:-1])
            key = f"treasury_{n}y"
            years = float(n)
        yield_vars[key] = {"column": hdr, "maturity_years": round(years, 4)}
    return {
        "data": {
            "macro_variables": macro_vars,
            "yield_variables": yield_vars,
            "sample": {"start": "1990-Q1", "end": "1990-Q4"},
        },
    }


def _build_workbook_panel(yield_headers, n_quarters=8, *, with_data=None):
    """Construct (macro_raw, yields_raw) DataFrames with synthetic data.

    Returns the dict shape that ``validate_input`` expects:
    ``{"macro_raw": ..., "yields_raw": ...}``.

    ``with_data``: optional dict {header -> [values_per_quarter]} to
    override the default constant-3.5 yield value. Headers in
    ``yield_headers`` not in ``with_data`` get the default.
    """
    quarters = [f"1990-Q{(i % 4) + 1}" for i in range(n_quarters)]
    quarters = [
        f"{1990 + i // 4}-Q{(i % 4) + 1}" for i in range(n_quarters)
    ]
    macro_raw = pd.DataFrame(
        {col: np.linspace(2.0, 3.0, n_quarters) for col in _DEFAULT_MACRO_COLS},
        index=pd.Index(quarters, name="Quarter"),
    )
    rng = np.random.default_rng(42)
    yields_data = {}
    for hdr in yield_headers:
        if with_data is not None and hdr in with_data:
            yields_data[hdr] = with_data[hdr]
        else:
            yields_data[hdr] = (3.5 + 0.1 * rng.standard_normal(n_quarters)).tolist()
    yields_raw = pd.DataFrame(yields_data, index=pd.Index(quarters, name="Quarter"))
    return {"macro_raw": macro_raw, "yields_raw": yields_raw}


# ---------------------------------------------------------------------------
# Header canonicalization
# ---------------------------------------------------------------------------


def test_canonicalize_maturity_header_canonical_forms():
    assert _canonicalize_maturity_header("1M") == "1M"
    assert _canonicalize_maturity_header("3M") == "3M"
    assert _canonicalize_maturity_header("9M") == "9M"
    assert _canonicalize_maturity_header("1Y") == "1Y"
    assert _canonicalize_maturity_header("10Y") == "10Y"
    assert _canonicalize_maturity_header("30Y") == "30Y"


def test_canonicalize_maturity_header_variants():
    # Year variants
    for variant in ("1y", "1 Y", "1Yr", "1 yr", "1-year", "1 year", "1Year"):
        assert _canonicalize_maturity_header(variant) == "1Y", variant
    # Month variants
    for variant in ("3m", "3 m", "3mo", "3-month", "3 Month", "3 months"):
        assert _canonicalize_maturity_header(variant) == "3M", variant


def test_canonicalize_maturity_header_rejects_garbage():
    for bad in ("garbage", "treasury_3m", "3.5Y", "Q1", "", None,
                "0Y", "31Y", "12M"):  # 12M canonical form is "1Y"; not accepted
        assert _canonicalize_maturity_header(bad) is None, bad


# ---------------------------------------------------------------------------
# Test 1: full 34-column input
# ---------------------------------------------------------------------------


def test_full_34_column_input_parses_correctly():
    config = _config_with_full_grid()
    raw = _build_workbook_panel(_FULL_34_HEADERS)
    result = validate_input(raw, config)
    assert result["yields"].shape[1] == 34, (
        f"Expected 34 yield columns; got {result['yields'].shape[1]}"
    )
    expected_keys = [
        spec_key for spec_key, _ in _config_with_full_grid()["data"][
            "yield_variables"
        ].items()
    ]
    assert list(result["yields"].columns) == expected_keys


# ---------------------------------------------------------------------------
# Test 2: sparse subset
# ---------------------------------------------------------------------------


def test_sparse_column_subset_parses_correctly():
    config = _config_with_full_grid()
    sparse_headers = ["3M", "6M", "1Y", "2Y", "5Y", "10Y", "30Y"]
    raw = _build_workbook_panel(sparse_headers)
    result = validate_input(raw, config)
    assert result["yields"].shape[1] == 7, (
        f"Expected 7 yield columns; got {result['yields'].shape[1]}"
    )
    expected_canonical_keys = [
        "treasury_3m", "treasury_6m", "treasury_1y", "treasury_2y",
        "treasury_5y", "treasury_10y", "treasury_30y",
    ]
    assert list(result["yields"].columns) == expected_canonical_keys


# ---------------------------------------------------------------------------
# Test 3: below-floor rejection
# ---------------------------------------------------------------------------


def test_minimum_3_columns_required():
    config = _config_with_full_grid()
    raw = _build_workbook_panel(["3M", "10Y"])  # only 2 maturities
    with pytest.raises(InputValidationError, match=r"insufficient_maturit"):
        validate_input(raw, config)


# ---------------------------------------------------------------------------
# Test 4: zero-population rejection
# ---------------------------------------------------------------------------


def test_zero_columns_rejected():
    config = _config_with_full_grid()
    # Workbook has no yield columns at all (empty headers)
    raw = {
        "macro_raw": pd.DataFrame(
            {col: [1.0, 2.0] for col in _DEFAULT_MACRO_COLS},
            index=pd.Index(["1990-Q1", "1990-Q2"], name="Quarter"),
        ),
        "yields_raw": pd.DataFrame(
            index=pd.Index(["1990-Q1", "1990-Q2"], name="Quarter"),
        ),
    }
    with pytest.raises(InputValidationError, match=r"no_populated_maturit"):
        validate_input(raw, config)


# ---------------------------------------------------------------------------
# Test 5: header variants canonicalize
# ---------------------------------------------------------------------------


def test_header_text_variants_canonicalized():
    config = _config_with_full_grid()
    # Mix: "1Yr" should normalize to "1Y"; "3-month" -> "3M"; etc.
    headers = ["3-month", "6 Month", "1Yr", "5Y", "10 Year"]
    raw = _build_workbook_panel(headers)
    result = validate_input(raw, config)
    assert result["yields"].shape[1] == 5, (
        f"Expected 5 yield columns; got {result['yields'].shape[1]}"
    )
    expected_canonical_keys = [
        "treasury_3m", "treasury_6m", "treasury_1y",
        "treasury_5y", "treasury_10y",
    ]
    assert list(result["yields"].columns) == expected_canonical_keys


# ---------------------------------------------------------------------------
# Test 6: unrecognized header rejected
# ---------------------------------------------------------------------------


def test_unrecognized_header_rejected():
    config = _config_with_full_grid()
    raw = _build_workbook_panel(["3M", "6M", "1Y", "garbage_header", "10Y"])
    with pytest.raises(InputValidationError, match=r"unrecognized_maturit"):
        validate_input(raw, config)


# ---------------------------------------------------------------------------
# Test 7: partial column data
# ---------------------------------------------------------------------------


def test_partial_column_data_rejected():
    """Header present + some rows NaN within the populated column.

    Fails inside the existing ``_check_interior_nan`` validator (raises
    ``InputValidationError("interior_nan", ...)``). BYF-Mod-1 does not
    add a new check here; row-level sparsity remains out of scope and
    surfaces via the existing interior-nan guard.
    """
    config = _config_with_full_grid()
    # 6 quarters, but treasury_5y has NaN in quarter 3.
    n = 6
    quarters = [f"1990-Q{(i % 4) + 1}" for i in range(n)]
    quarters = [f"{1990 + i // 4}-Q{(i % 4) + 1}" for i in range(n)]
    yields_data = {hdr: [3.0] * n for hdr in ["3M", "6M", "1Y", "5Y", "10Y"]}
    yields_data["5Y"][2] = np.nan  # interior NaN
    raw = {
        "macro_raw": pd.DataFrame(
            {c: list(range(n)) for c in _DEFAULT_MACRO_COLS},
            index=pd.Index(quarters, name="Quarter"),
        ).astype(float),
        "yields_raw": pd.DataFrame(
            yields_data, index=pd.Index(quarters, name="Quarter"),
        ),
    }
    with pytest.raises(InputValidationError, match=r"interior_nan"):
        validate_input(raw, config)


# ---------------------------------------------------------------------------
# Direct test of _resolve_populated_yield_columns
# ---------------------------------------------------------------------------


def test_resolve_populated_yield_columns_orders_by_config():
    """When the workbook lists headers out of config order, the returned
    list must be sorted by config order (not workbook order)."""
    yields = pd.DataFrame({
        "30Y": [4.0, 4.1],
        "1Y": [3.0, 3.1],
        "10Y": [3.5, 3.6],
        "5Y": [3.2, 3.3],
    })
    expected = [s["column"] for s in _config_with_full_grid()["data"][
        "yield_variables"
    ].values()]  # canonical order: 1M, 3M, 6M, 9M, 1Y, ..., 30Y
    populated, rewrite = _resolve_populated_yield_columns(yields, expected)
    assert populated == ["1Y", "5Y", "10Y", "30Y"]
    assert rewrite == {"30Y": "30Y", "1Y": "1Y", "10Y": "10Y", "5Y": "5Y"}


def test_resolve_populated_yield_columns_drops_empty_columns():
    """Header present but data column entirely NaN -> dropped."""
    yields = pd.DataFrame({
        "3M": [3.0, 3.1, 3.2],
        "6M": [np.nan, np.nan, np.nan],  # entirely empty
        "1Y": [3.5, 3.6, 3.7],
        "5Y": [3.7, 3.8, 3.9],
    })
    expected = [s["column"] for s in _config_with_full_grid()["data"][
        "yield_variables"
    ].values()]
    populated, _ = _resolve_populated_yield_columns(yields, expected)
    # 6M is dropped because all-NaN
    assert "6M" not in populated
    assert populated == ["3M", "1Y", "5Y"]


def test_min_maturity_count_constant():
    """The methodological floor is 3 (PCA factor structure)."""
    assert MIN_MATURITY_COUNT == 3
