"""
Regression invariants for TSL sample data CSVs shipped in
``resources/sample_data/``.

Enforces three platform-wide properties that must hold on every
sample CSV:

T1. Reverse chronological order — first row holds the most recent
    date; last row holds the oldest.
T2. Uniform inter-row deltas at the detected frequency — no
    interior gaps. For daily financial series, calendar awareness
    is routed through the per-series ``SAMPLE_DATA_FREQ`` mapping
    maintained alongside ``tools/preprocess_sample_data.py``:
    ``nyse_daily`` for NYSE equities, ``sifma_daily`` for US
    Treasuries and other fixed-income markets.
T3. Contiguous tail length >= 60 observations — canary against
    accidentally chopping a CSV down to near-unusability by a
    contiguity rule misconfiguration.

Three dataset-specific tests anchor the NYSE / SIFMA distinction
and the 9/11 gap detection.

Run:
    pytest engine/tests/test_sample_data_ordering_and_contiguity.py -v
"""
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

import pandas as pd  # noqa: E402
import numpy as np  # noqa: E402

from techniques.base import (  # noqa: E402
    enforce_contiguous_tail,
    nyse_bday,
    sifma_bday,
    NYSE_CALENDAR,
    SIFMA_CALENDAR,
)


_REPO_ROOT = os.path.abspath(os.path.join(_ENGINE_DIR, ".."))
_SAMPLE_DIR = os.path.join(_REPO_ROOT, "resources", "sample_data")


# Must stay in sync with tools/preprocess_sample_data.py::SAMPLE_DATA_FREQ.
# Any divergence between the two means the on-disk CSVs were
# preprocessed under a different rule than the tests validate.
SAMPLE_DATA_FREQ = {
    "airline_passengers.csv":      "monthly",
    "core_pce.csv":                "quarterly",
    "dfm_coincident.csv":          "monthly",
    "dfm_coincident_growth.csv":   "monthly",
    "gdp_ip_disaggregation.csv":   "monthly",
    "intermittent_demand.csv":     "monthly",
    "macro_var.csv":               "quarterly",
    "nile_river.csv":              "annual",
    "nonfarm_payroll_nsa.csv":     "monthly",
    "nonfarm_payroll_sa.csv":      "monthly",
    "real_gdp.csv":                "quarterly",
    "sp500_returns.csv":           "nyse_daily",
    "sunspots.csv":                "monthly",
    "treasury_yields.csv":         "sifma_daily",
}

_MIN_TAIL = 60


def _load(fname: str) -> pd.DataFrame:
    path = os.path.join(_SAMPLE_DIR, fname)
    return pd.read_csv(path, parse_dates=[0])


class TestReverseChronologicalOrder(unittest.TestCase):
    """T1 — every sample CSV is stored newest-at-top. Excel-side
    display inherits this ordering directly from file order."""

    def test_all_sample_csvs_descending(self):
        failures = []
        for fname in SAMPLE_DATA_FREQ:
            df = _load(fname)
            first = df.iloc[0, 0]
            last = df.iloc[-1, 0]
            if not (first > last):
                failures.append(
                    f"{fname}: first row {first.date()} should be later than "
                    f"last row {last.date()} (file must be descending)"
                )
        self.assertFalse(
            failures,
            "Sample CSVs not in reverse chronological order:\n  "
            + "\n  ".join(failures)
        )


class TestStrictlyDescendingByRow(unittest.TestCase):
    """T1b — every sample CSV must be strictly DESCENDING row-by-row, not just
    endpoint-ordered. T1 (above) checks only first>last, and T2/T3 re-sort
    internally via enforce_contiguous_tail — so a lexicographic/string-sort
    scramble (the historical preprocess_sample_data bug, treasury 361a/5784d)
    slips past all of them. This walks every adjacent row pair on-disk."""

    def test_all_sample_csvs_strictly_descending(self):
        failures = []
        for fname in SAMPLE_DATA_FREQ:
            df = _load(fname)
            diffs = df.iloc[:, 0].diff().dropna()
            n_nondesc = int((diffs >= pd.Timedelta(0)).sum())
            if n_nondesc:
                failures.append(
                    f"{fname}: {n_nondesc} non-descending row step(s) "
                    f"(interior scramble; rows must run strictly newest -> oldest)"
                )
        self.assertFalse(
            failures,
            "Sample CSVs not strictly descending row-by-row (interior scramble "
            "the endpoint/contiguity tests cannot see):\n  "
            + "\n  ".join(failures)
        )


class TestUniformInterRowDeltas(unittest.TestCase):
    """T2 — the row sequence in every sample CSV is contiguous at its
    declared frequency. The contiguity helper returns the original
    DataFrame untouched (rows_dropped = 0) when the input is
    already gap-free."""

    def test_all_sample_csvs_contiguous(self):
        failures = []
        for fname, freq in SAMPLE_DATA_FREQ.items():
            df = _load(fname)
            _truncated, info = enforce_contiguous_tail(df, freq)
            if info["rows_dropped"] != 0 or info["most_recent_gap_date"] is not None:
                failures.append(
                    f"{fname} ({freq}): gap detected at "
                    f"{info['most_recent_gap_date']}; would need to drop "
                    f"{info['rows_dropped']} rows to restore contiguity"
                )
        self.assertFalse(
            failures,
            "Sample CSVs are not fully contiguous at their declared "
            "frequency — re-run tools/preprocess_sample_data.py:\n  "
            + "\n  ".join(failures)
        )


class TestContiguousTailAtLeast60(unittest.TestCase):
    """T3 — every sample CSV has at least 60 observations in its
    contiguous tail. Canary against a calendar-rule misconfiguration
    chopping a dataset to near-unusability."""

    def test_all_sample_csvs_tail_at_least_60(self):
        failures = []
        for fname, freq in SAMPLE_DATA_FREQ.items():
            df = _load(fname)
            _truncated, info = enforce_contiguous_tail(
                df, freq, min_tail=_MIN_TAIL,
            )
            tail = info["tail_length"]
            if tail < _MIN_TAIL:
                failures.append(
                    f"{fname} ({freq}): contiguous tail is {tail} "
                    f"observations, below the {_MIN_TAIL}-obs floor"
                )
        self.assertFalse(
            failures,
            "Sample CSVs fell below the 60-observation tail floor — "
            "investigate the source and calendar convention:\n  "
            + "\n  ".join(failures)
        )


class TestNYSECalendarDistinction(unittest.TestCase):
    """Anchors the NYSE-vs-SIFMA calendar distinction with
    concrete dates. Regression guard against a future pandas update
    or rule-list edit that silently collapses the two calendars."""

    def test_nyse_closes_good_friday_opens_columbus_day(self):
        bd = nyse_bday()
        # 2024-03-28 (Thu) + 1 NYSE bday = 2024-04-01 (Mon), skipping
        # Good Friday (Mar 29) AND the weekend. Federal calendar
        # would return 2024-03-29 (Fri).
        self.assertEqual(
            (pd.Timestamp("2024-03-28") + bd).date(),
            pd.Timestamp("2024-04-01").date(),
            "NYSE must treat Good Friday as non-trading",
        )
        # 2024-10-11 (Fri) + 1 NYSE bday = 2024-10-14 (Mon, Columbus
        # Day). Federal calendar would skip to 2024-10-15.
        self.assertEqual(
            (pd.Timestamp("2024-10-11") + bd).date(),
            pd.Timestamp("2024-10-14").date(),
            "NYSE must treat Columbus Day as a trading day",
        )

    def test_sifma_closes_columbus_veterans_and_good_friday(self):
        bd = sifma_bday()
        # SIFMA: Columbus Day 2024 (Mon Oct 14) is closed, so
        # 2024-10-11 (Fri) + 1 SIFMA bday = 2024-10-15 (Tue).
        self.assertEqual(
            (pd.Timestamp("2024-10-11") + bd).date(),
            pd.Timestamp("2024-10-15").date(),
            "SIFMA must treat Columbus Day as non-trading",
        )
        # Veterans Day 2024 is Mon Nov 11. SIFMA closed.
        self.assertEqual(
            (pd.Timestamp("2024-11-08") + bd).date(),
            pd.Timestamp("2024-11-12").date(),
            "SIFMA must treat Veterans Day as non-trading",
        )
        # Good Friday 2024 is Mar 29. SIFMA closed.
        self.assertEqual(
            (pd.Timestamp("2024-03-28") + bd).date(),
            pd.Timestamp("2024-04-01").date(),
            "SIFMA must treat Good Friday as non-trading",
        )


class TestSp500FullyContiguousUnderNYSE(unittest.TestCase):
    """Positive control — under the NYSE calendar, sp500_returns is
    fully contiguous. Regression guard that the NYSE calendar does
    NOT produce false gaps on Columbus Day or Veterans Day."""

    def test_sp500_no_truncation_under_nyse(self):
        df = _load("sp500_returns.csv")
        _truncated, info = enforce_contiguous_tail(df, "nyse_daily")
        self.assertEqual(
            info["rows_dropped"], 0,
            f"sp500_returns should be fully contiguous under NYSE "
            f"calendar; got rows_dropped={info['rows_dropped']}, "
            f"most_recent_gap={info['most_recent_gap_date']}"
        )
        self.assertIsNone(
            info["most_recent_gap_date"],
            "No gap should be detected in sp500_returns under NYSE",
        )
        self.assertEqual(
            info["tail_length"], len(df),
            "Full dataset is the contiguous tail",
        )


class TestTreasuryYieldsDetects9_11Gap(unittest.TestCase):
    """Positive control — under the SIFMA calendar, treasury_yields
    truncation preserves exactly the post-9/11 contiguous segment,
    dropping the earlier (1962 to pre-gap) portion. The gap itself
    is the week after Sept 11, 2001 when the NYSE and bond markets
    were closed.

    After running tools/preprocess_sample_data.py, treasury_yields.csv
    on disk should contain ONLY the post-gap rows. The helper's
    rows_dropped should be 0 because the preprocessing already
    enforced the truncation."""

    def test_post_9_11_tail_only(self):
        df = _load("treasury_yields.csv")
        dates = pd.to_datetime(df[df.columns[0]])
        # Earliest date on disk should be on or after the gap-resume.
        # Gap ends at 2001-09-10; the first post-gap date in the
        # source CSV is 2001-09-13 (when NYSE actually reopened it
        # was 2001-09-17, but the CSV as shipped has 09-13; the test
        # requires only that the earliest date is strictly after the
        # gap date).
        self.assertGreater(
            dates.min(), pd.Timestamp("2001-09-10"),
            f"treasury_yields earliest date should be after the "
            f"9/11 gap (2001-09-10); got {dates.min().date()}. "
            f"Re-run tools/preprocess_sample_data.py to truncate."
        )
        # And the helper should confirm no further gaps.
        _truncated, info = enforce_contiguous_tail(df, "sifma_daily")
        self.assertEqual(
            info["rows_dropped"], 0,
            f"After preprocessing, treasury_yields should be gap-free "
            f"under SIFMA; got rows_dropped={info['rows_dropped']}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
