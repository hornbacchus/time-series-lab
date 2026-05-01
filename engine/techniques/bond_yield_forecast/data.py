"""Data ingestion, validation, and PCA factor extraction.

The pipeline reads a user-supplied Excel workbook with two sheets ("macro"
and "yields"), validates structure and content, applies the configured
sample window, and runs PCA on the yield panel to produce 3 factors
(level / slope / curvature) that the BVAR will model. No external APIs.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml
from sklearn.decomposition import PCA

logger = logging.getLogger(__name__)

_QUARTER_RE = re.compile(r"^\d{4}-Q[1-4]$")

_MACRO_BOUNDS = {
    "real_gdp_growth": (-20.0, 20.0),
    "headline_cpi": (-5.0, 25.0),
    "fed_funds_rate": (-2.0, 25.0),
}
_YIELD_BOUNDS = (-2.0, 25.0)
_DECIMAL_FORM_THRESHOLD = 0.5


class InputValidationError(ValueError):
    """Raised when the input workbook fails validation.

    Attributes
    ----------
    rule : str
        Short identifier for the failed rule (e.g. ``"missing_sheet"``).
    detail : str
        Human-readable description of what was wrong.
    location : str | None
        Sheet, column, and/or quarter where the failure was detected.
    """

    def __init__(self, rule: str, detail: str, *, location: str | None = None) -> None:
        loc_part = f" (at {location})" if location else ""
        super().__init__(f"[{rule}] {detail}{loc_part}")
        self.rule = rule
        self.detail = detail
        self.location = location


def load_config(path: str | Path) -> dict[str, Any]:
    """Read a YAML config file and return its parsed contents."""
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    for key in ("data", "model", "estimation", "forecast"):
        if key not in config:
            raise KeyError(f"Config at {path} is missing required top-level key '{key}'")
    logger.info("Loaded config from %s", path)
    return config


def load_input_workbook(
    path: str | Path,
    *,
    macro_sheet: str = "macro",
    yield_sheet: str = "yields",
) -> dict[str, pd.DataFrame]:
    """Read the macro and yield sheets from the user-supplied Excel workbook.

    Returns a dict ``{"macro_raw": df, "yields_raw": df}`` with the original
    human-readable column headers and string-typed quarter values as the
    index. Validation, type coercion, and column renaming happen later in
    ``validate_input``.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Input workbook not found at {path}. "
            f"See templates/input_template.xlsx for the required format."
        )

    xl = pd.ExcelFile(path, engine="openpyxl")
    available = set(xl.sheet_names)
    missing_sheets = [s for s in (macro_sheet, yield_sheet) if s not in available]
    if missing_sheets:
        raise InputValidationError(
            "missing_sheet",
            f"Workbook missing required sheet(s): {missing_sheets}. "
            f"Available: {sorted(available)}. "
            f"See templates/input_template.xlsx for the required format.",
        )

    macro_raw = pd.read_excel(xl, sheet_name=macro_sheet)
    yields_raw = pd.read_excel(xl, sheet_name=yield_sheet)

    for name, df in [("macro", macro_raw), ("yields", yields_raw)]:
        if df.columns.size == 0 or df.columns[0] != "Quarter":
            first = df.columns[0] if df.columns.size > 0 else "(empty)"
            raise InputValidationError(
                "missing_quarter_column",
                f"First column on '{name}' sheet must be 'Quarter'; got '{first}'",
                location=f"sheet='{name}'",
            )

    macro_raw = macro_raw.set_index("Quarter")
    yields_raw = yields_raw.set_index("Quarter")

    logger.info(
        "Loaded workbook %s: macro shape=%s, yields shape=%s",
        path,
        macro_raw.shape,
        yields_raw.shape,
    )
    return {"macro_raw": macro_raw, "yields_raw": yields_raw}


def _check_quarter_format(df: pd.DataFrame, sheet: str) -> None:
    for q in df.index:
        if not isinstance(q, str) or not _QUARTER_RE.match(q):
            raise InputValidationError(
                "bad_quarter_format",
                f"Quarter value {q!r} does not match YYYY-Q# format on sheet '{sheet}'",
                location=f"sheet='{sheet}', Quarter={q!r}",
            )


def _to_period_index(string_index: pd.Index, sheet: str) -> pd.PeriodIndex:
    try:
        return pd.PeriodIndex(
            [pd.Period(q, freq="Q-DEC") for q in string_index], freq="Q-DEC"
        )
    except Exception as exc:
        raise InputValidationError(
            "bad_quarter_format",
            f"Failed to parse Quarter values on sheet '{sheet}': {exc}",
            location=f"sheet='{sheet}'",
        ) from exc


def _check_index_quality(df: pd.DataFrame, sheet: str) -> None:
    if df.index.duplicated().any():
        dup = sorted(set(df.index[df.index.duplicated()]))
        raise InputValidationError(
            "duplicate_quarter",
            f"Sheet '{sheet}' has duplicate quarter(s): {dup}",
            location=f"sheet='{sheet}'",
        )
    if not df.index.is_monotonic_increasing:
        raise InputValidationError(
            "non_monotonic",
            f"Sheet '{sheet}' Quarter index is not monotonically increasing",
            location=f"sheet='{sheet}'",
        )
    expected = pd.period_range(df.index.min(), df.index.max(), freq="Q-DEC")
    missing = sorted(set(expected) - set(df.index))
    if missing:
        raise InputValidationError(
            "quarter_gap",
            f"Sheet '{sheet}' missing quarter(s) inside its span; first missing: {missing[0]}",
            location=f"sheet='{sheet}', missing={missing[0]}",
        )


def _check_numeric(df: pd.DataFrame, sheet: str) -> pd.DataFrame:
    out = df.copy()
    for col in out.columns:
        converted = pd.to_numeric(out[col], errors="coerce")
        was_present = out[col].notna()
        became_nan = converted.isna()
        bad_mask = was_present & became_nan
        if bad_mask.any():
            first_q = out.index[bad_mask][0]
            first_val = out.loc[first_q, col]
            raise InputValidationError(
                "non_numeric",
                f"Non-numeric value {first_val!r} in column '{col}' on sheet '{sheet}'",
                location=f"sheet='{sheet}', column='{col}', quarter={first_q}",
            )
        out[col] = converted
    return out


def _check_interior_nan(
    df: pd.DataFrame, sheet: str, sample_start: pd.Period, sample_end: pd.Period
) -> None:
    in_window = df.loc[
        (df.index >= sample_start) & (df.index <= sample_end)
    ]
    if not in_window.isna().any().any():
        return
    for q in in_window.index:
        row = in_window.loc[q]
        bad = row[row.isna()].index.tolist()
        if bad:
            raise InputValidationError(
                "interior_nan",
                f"NaN value in column '{bad[0]}' at quarter {q} on sheet '{sheet}' inside the sample window",
                location=f"sheet='{sheet}', column='{bad[0]}', quarter={q}",
            )


def _resolve_sample_window(
    macro: pd.DataFrame, yields: pd.DataFrame, config: dict
) -> tuple[pd.Period, pd.Period]:
    start = pd.Period(config["data"]["sample"]["start"], freq="Q-DEC")
    end_cfg = config["data"]["sample"]["end"]
    if end_cfg == "latest":
        macro_complete = macro.dropna(how="any").index
        yields_complete = yields.dropna(how="any").index
        if len(macro_complete) == 0 or len(yields_complete) == 0:
            end = max(macro.index.max(), yields.index.max())
        else:
            end = min(macro_complete.max(), yields_complete.max())
    else:
        end = pd.Period(end_cfg, freq="Q-DEC")
    return start, end


def _emit_sanity_warnings(
    macro: pd.DataFrame, yields: pd.DataFrame, macro_rename: dict[str, str]
) -> None:
    for col, series in macro.items():
        key = macro_rename.get(col)
        if key in _MACRO_BOUNDS:
            lo, hi = _MACRO_BOUNDS[key]
            bad = series[(series < lo) | (series > hi)]
            for q, val in bad.items():
                logger.warning(
                    "Out-of-bounds %s value: %.4f at %s (expected [%.1f, %.1f])",
                    col,
                    val,
                    q,
                    lo,
                    hi,
                )

    lo, hi = _YIELD_BOUNDS
    for col, series in yields.items():
        bad = series[(series < lo) | (series > hi)]
        for q, val in bad.items():
            logger.warning(
                "Out-of-bounds yield %s=%.4f at %s (expected [%.1f, %.1f])",
                col,
                val,
                q,
                lo,
                hi,
            )

    abs_max = yields.abs().max(axis=1)
    suspect = abs_max[abs_max < _DECIMAL_FORM_THRESHOLD]
    for q in suspect.index:
        logger.warning(
            "Yields at %s look like decimal form (all |y| < %.2f); expected percent. "
            "Did you forget to multiply by 100?",
            q,
            _DECIMAL_FORM_THRESHOLD,
        )


def validate_input(
    raw: dict[str, pd.DataFrame], config: dict
) -> dict[str, pd.DataFrame]:
    """Validate raw workbook contents, raise on failure, return cleaned panels.

    Returned DataFrames have a ``PeriodIndex`` (freq='Q-DEC') and column
    names matching the config keys (``real_gdp_growth``, ``treasury_3m``,
    etc.) rather than the human-readable workbook headers.
    """
    if "macro_raw" not in raw or "yields_raw" not in raw:
        missing = [k for k in ("macro_raw", "yields_raw") if k not in raw]
        raise InputValidationError(
            "missing_sheet",
            f"Raw workbook dict missing key(s): {missing}",
        )

    macro = raw["macro_raw"].copy()
    yields = raw["yields_raw"].copy()

    macro_specs = config["data"]["macro_variables"]
    yield_specs = config["data"]["yield_variables"]
    expected_macro_cols = [s["column"] for s in macro_specs.values()]
    expected_yield_cols = [s["column"] for s in yield_specs.values()]

    for col in expected_macro_cols:
        if col not in macro.columns:
            raise InputValidationError(
                "missing_column",
                f"Macro sheet missing required column '{col}'",
                location="sheet='macro'",
            )
    for col in expected_yield_cols:
        if col not in yields.columns:
            raise InputValidationError(
                "missing_column",
                f"Yields sheet missing required column '{col}'",
                location="sheet='yields'",
            )

    extra_macro = [c for c in macro.columns if c not in expected_macro_cols]
    if extra_macro:
        logger.warning("Extra columns in macro sheet ignored: %s", extra_macro)
    extra_yields = [c for c in yields.columns if c not in expected_yield_cols]
    if extra_yields:
        logger.warning("Extra columns in yields sheet ignored: %s", extra_yields)

    macro = macro[expected_macro_cols]
    yields = yields[expected_yield_cols]

    _check_quarter_format(macro, "macro")
    _check_quarter_format(yields, "yields")

    macro.index = _to_period_index(macro.index, "macro")
    yields.index = _to_period_index(yields.index, "yields")

    _check_index_quality(macro, "macro")
    _check_index_quality(yields, "yields")

    if not macro.index.equals(yields.index):
        sym = sorted(set(macro.index) ^ set(yields.index))
        sample = sym[:5] + (["..."] if len(sym) > 5 else [])
        raise InputValidationError(
            "index_mismatch",
            f"Macro and yields sheets have different Quarter indexes; symmetric difference: {sample}",
        )

    macro = _check_numeric(macro, "macro")
    yields = _check_numeric(yields, "yields")

    sample_start, sample_end = _resolve_sample_window(macro, yields, config)
    _check_interior_nan(macro, "macro", sample_start, sample_end)
    _check_interior_nan(yields, "yields", sample_start, sample_end)

    macro_rename = {s["column"]: n for n, s in macro_specs.items()}
    yield_rename = {s["column"]: n for n, s in yield_specs.items()}
    _emit_sanity_warnings(macro, yields, macro_rename)

    macro = macro.rename(columns=macro_rename)
    yields = yields.rename(columns=yield_rename)

    logger.info(
        "Validated input: macro %s, yields %s, sample [%s, %s]",
        macro.shape,
        yields.shape,
        sample_start,
        sample_end,
    )
    return {"macro": macro, "yields": yields}


def _sign_normalize(loadings: np.ndarray) -> np.ndarray:
    """Apply a deterministic sign convention to PCA loadings.

    PC1 (level): all loadings positive — flip if column sum is negative.
    PC2 (slope): long maturity > short maturity — flip if last < first.
    PC3 (curvature): positive at intermediate maturity — flip if middle < 0.
    """
    out = loadings.copy()
    if out[:, 0].sum() < 0:
        out[:, 0] *= -1.0
    if out[-1, 1] < out[0, 1]:
        out[:, 1] *= -1.0
    mid = out.shape[0] // 2
    if out[mid, 2] < 0:
        out[:, 2] *= -1.0
    return out


def fit_pca(
    yield_panel: pd.DataFrame, n_components: int, component_names: list[str]
) -> dict[str, Any]:
    """Fit PCA on a yield panel and return loadings + summary statistics.

    Sign-normalizes the loadings deterministically so output is reproducible
    across sklearn versions and platforms.
    """
    if n_components != 3:
        raise ValueError(f"This step only supports n_components=3 (got {n_components})")
    if len(component_names) != n_components:
        raise ValueError(
            f"component_names must have length {n_components}; got {len(component_names)}"
        )

    Y = yield_panel.to_numpy(dtype=float)
    pca = PCA(n_components=n_components)
    pca.fit(Y)
    loadings = _sign_normalize(pca.components_.T)

    result = {
        "loadings": loadings,
        "mean": pca.mean_.copy(),
        "explained_variance_ratio": pca.explained_variance_ratio_.copy(),
        "yield_names": list(yield_panel.columns),
        "component_names": list(component_names),
    }
    logger.info(
        "PCA fit: %dx%d, explained variance = %s",
        Y.shape[0],
        Y.shape[1],
        np.round(result["explained_variance_ratio"], 4).tolist(),
    )
    return result


def project_to_pcs(
    yield_panel: pd.DataFrame, pca_dict: dict[str, Any]
) -> pd.DataFrame:
    """Project yield observations onto principal components."""
    centered = yield_panel.to_numpy(dtype=float) - pca_dict["mean"]
    scores = centered @ pca_dict["loadings"]
    return pd.DataFrame(
        scores, index=yield_panel.index, columns=pca_dict["component_names"]
    )


def reconstruct_yields(
    pc_panel: pd.DataFrame, pca_dict: dict[str, Any]
) -> pd.DataFrame:
    """Reconstruct yield levels from principal-component scores."""
    yields = pc_panel.to_numpy(dtype=float) @ pca_dict["loadings"].T + pca_dict["mean"]
    return pd.DataFrame(
        yields, index=pc_panel.index, columns=pca_dict["yield_names"]
    )


def align_panel(df: pd.DataFrame) -> pd.DataFrame:
    """Trim leading/trailing all-NaN rows to the longest contiguous window.

    Raises ``ValueError`` if any interior NaN remains — interior NaN is a
    data-quality bug, not something to silently drop.
    """
    mask = df.notna().all(axis=1)
    if not mask.any():
        raise ValueError("No row in the panel has all variables present")
    first = mask.idxmax()
    last = mask[::-1].idxmax()
    trimmed = df.loc[first:last]
    if trimmed.isna().any().any():
        missing = trimmed.isna().sum()
        missing_dict = {k: int(v) for k, v in missing.items() if v > 0}
        raise ValueError(f"Interior NaN in sample window: {missing_dict}")
    return trimmed


def build_panel(
    config: dict[str, Any],
    *,
    input_path: str | Path | None = None,
    output_dir: str | Path = "data/processed",
    raw: dict[str, pd.DataFrame] | None = None,
) -> dict[str, Any]:
    """Run the full data pipeline: load → validate → window → PCA → save.

    Either ``input_path`` (or ``config["data"]["input_file"]``) or ``raw``
    must be supplied. ``raw`` lets callers (e.g., the unified-workbook
    reader, or TSL's in-memory dispatch path
    ``_dispatch._build_panel_in_memory``) skip the file-load step when they
    already have the macro and yields DataFrames in hand.

    Parameters
    ----------
    config
        BVAR-SV configuration dict (see ``config/default.yaml``).
    input_path
        Path to a 3-sheet input workbook. Mutually exclusive with ``raw``.
    output_dir
        Directory for the parquet/npz artifacts written at the end of the
        pipeline.
    raw
        BYF Session 6 cleanup §6(a) — explicit shape contract.
        Optional dict that bypasses the file-load step. Required keys:

        - ``"macro_raw"`` : ``pandas.DataFrame``
            Macro panel pre-validation. Index = ``pandas.PeriodIndex`` at
            quarterly frequency (or convertible via
            ``pandas.PeriodIndex(freq="Q")``); columns = the 3 macro
            variable names declared in ``config["data"]["macro_columns"]``
            ("Real GDP Growth (Q/Q SAAR)", "Headline CPI Inflation (Q/Q
            annualized)", "Effective Federal Funds Rate (Q-end)" by
            default). Values are quarterly observations, NaN allowed at
            head/tail; no interior gaps after sample-window resolution.
        - ``"yields_raw"`` : ``pandas.DataFrame``
            Yield panel pre-validation. Same index convention as
            ``macro_raw``; columns = the 10 maturity names declared in
            ``config["data"]["yield_columns"]`` ("3M", "6M", "1Y", "2Y",
            "3Y", "5Y", "7Y", "10Y", "20Y", "30Y" by default). Values
            are end-of-quarter par yields in percent.

        Both DataFrames must align on a common index range; the pipeline
        concatenates them column-wise and resolves the sample window per
        ``config["data"]["sample_window"]`` afterwards. Callers (notably
        ``_dispatch._build_panel_in_memory`` for the TSL Excel-DNA
        in-memory path, and ``unified_input.read_unified_workbook`` for
        the bundled-template path) construct ``raw`` from upstream
        sources without round-tripping through .xlsx.

    Returns
    -------
    dict with keys:
        - ``panel``       : DataFrame, 3 macro + 3 PC columns (BVAR observable)
        - ``yield_panel`` : DataFrame, in-sample 10-maturity yields
        - ``pca``         : dict with loadings, mean, variance ratio, names
        - ``sample``      : (start_period, end_period) tuple
    """
    if raw is None:
        input_path = Path(input_path) if input_path else Path(config["data"]["input_file"])
        if not input_path.exists():
            raise FileNotFoundError(
                f"Input workbook not found at {input_path}. "
                f"See templates/input_template.xlsx for the required format."
            )
        raw = load_input_workbook(
            input_path,
            macro_sheet=config["data"]["macro_sheet"],
            yield_sheet=config["data"]["yield_sheet"],
        )
    clean = validate_input(raw, config)
    macro_df, yield_df = clean["macro"], clean["yields"]

    sample_start, sample_end = _resolve_sample_window(macro_df, yield_df, config)
    logger.info("Sample window resolved: %s to %s", sample_start, sample_end)

    macro_df = macro_df.loc[sample_start:sample_end]
    yield_df = yield_df.loc[sample_start:sample_end]

    macro_cols = list(macro_df.columns)
    yield_cols = list(yield_df.columns)
    joined = pd.concat([macro_df, yield_df], axis=1)
    joined = align_panel(joined)
    macro_df = joined[macro_cols]
    yield_df = joined[yield_cols]

    pca_dict = fit_pca(
        yield_df,
        n_components=config["data"]["pca"]["n_components"],
        component_names=config["data"]["pca"]["component_names"],
    )
    pc_panel = project_to_pcs(yield_df, pca_dict)

    panel = pd.concat([macro_df, pc_panel], axis=1)

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    panel_path = output_dir / "panel.parquet"
    yield_path = output_dir / "yield_panel.parquet"
    pca_path = output_dir / "pca.npz"
    panel.to_parquet(panel_path)
    yield_df.to_parquet(yield_path)
    np.savez(
        pca_path,
        loadings=pca_dict["loadings"],
        mean=pca_dict["mean"],
        explained_variance_ratio=pca_dict["explained_variance_ratio"],
        yield_names=np.array(pca_dict["yield_names"]),
        component_names=np.array(pca_dict["component_names"]),
    )

    logger.info(
        "Saved: %s, %s, %s. Panel shape=%s. PC variance: %s",
        panel_path,
        yield_path,
        pca_path,
        panel.shape,
        np.round(pca_dict["explained_variance_ratio"], 4).tolist(),
    )

    return {
        "panel": panel,
        "yield_panel": yield_df,
        "pca": pca_dict,
        "sample": (sample_start, sample_end),
    }
