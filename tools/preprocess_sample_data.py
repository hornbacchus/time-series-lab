"""
Preprocess TSL sample data CSVs for ordering and contiguity invariants.

This script is PERMANENT and IDEMPOTENT. Re-running on already-compliant
CSVs is a no-op: no file modification, no writeback. Run it any time a
sample-data CSV is added or updated to guarantee it conforms to the
two invariants:

  1. Rows are stored in DESCENDING chronological order (newest at top).
  2. The row sequence is contiguous at the detected frequency with no
     interior gaps. Most-recent contiguous tail is preserved; any
     observations on or before the most recent gap are dropped.

Calendar convention for daily series (per the 2026-04 sample-data audit):
  * NYSE-traded equity series → ``nyse_daily`` (NYSE trading-day calendar:
    federal holidays + Good Friday, minus Columbus Day and Veterans Day).
  * US fixed-income series → ``sifma_daily`` (SIFMA calendar: federal
    holidays + Good Friday; treasuries and bonds close on both).
  * Other daily series (non-financial) → ``daily`` (US federal business day).

Non-daily series use their natural frequency (annual / quarterly / monthly).

The 60-observation floor on the contiguous tail is enforced: if a CSV's
compliant tail falls below 60 observations, the script leaves the file
unchanged and prints a warning so the source can be fixed manually
rather than silently chopping the dataset to near-unusability.

Usage
-----
    python tools/preprocess_sample_data.py [--dry-run]

    --dry-run
        Print the summary without writing any files.

Exit code 0 on success; 1 if any CSV triggers the sub-60 floor.

See `engine/techniques/base.py` for the calendar and contiguity
helpers this script invokes.
"""

import argparse
import os
import sys

# Make engine/ importable for the base.py helpers.
_HERE = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, os.path.join(_PROJECT_ROOT, "engine"))

import pandas as pd  # noqa: E402

from techniques.base import enforce_contiguous_tail  # noqa: E402


# Per-CSV frequency + calendar convention. Keys are the CSV filenames
# (without directory); values are the ``freq`` argument to
# ``enforce_contiguous_tail``. Add a new row when a new sample CSV
# ships.
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


def _detect_order(df: pd.DataFrame, date_col: str) -> str:
    dates = pd.to_datetime(df[date_col])
    return "descending" if dates.iloc[0] > dates.iloc[-1] else "ascending"


def _process_one(csv_path: str, freq: str, dry_run: bool) -> dict:
    """Apply ordering + contiguity enforcement to a single CSV.

    Returns a dict summary with keys:
        path          — absolute path
        freq          — applied frequency convention
        before_rows   — row count before any change
        after_rows    — row count after truncation
        order_before  — "descending" or "ascending" pre-change
        dropped_range — (first_dropped, last_dropped) or None
        below_min     — bool; True when the helper refused truncation
        modified      — bool; True when the file content would change
    """
    df = pd.read_csv(csv_path)
    date_col = df.columns[0]
    before_rows = len(df)
    order_before = _detect_order(df, date_col)

    # Sort ascending internally for the helper's gap walk.
    df_asc = df.sort_values(date_col).reset_index(drop=True)

    truncated_asc, info = enforce_contiguous_tail(df_asc, freq)

    after_rows = len(truncated_asc)
    dropped_range = info.get("dropped_date_range")
    below_min = bool(info.get("below_min"))

    # Re-emit in DESCENDING order (newest-at-top) for writeback.
    truncated_desc = truncated_asc.sort_values(
        date_col, ascending=False
    ).reset_index(drop=True)

    # Idempotency check is on data-level changes only, NOT on byte
    # equality. pd.to_csv may produce trivially different formatting
    # from the original source (different float precision, quoting
    # style, line endings). We only rewrite when the actual data
    # changed — row count dropped or order reversed. This guarantees
    # that re-running on an already-compliant file is a no-op.
    row_count_changed = after_rows != before_rows
    order_changed = order_before != "descending"
    modified = (row_count_changed or order_changed) and not below_min

    if modified and not dry_run:
        proposed_content = truncated_desc.to_csv(index=False, lineterminator="\n")
        with open(csv_path, "w", newline="") as fh:
            fh.write(proposed_content)

    return {
        "path": csv_path,
        "freq": freq,
        "before_rows": before_rows,
        "after_rows": after_rows,
        "order_before": order_before,
        "dropped_range": dropped_range,
        "below_min": below_min,
        "modified": modified,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Enforce ordering + contiguity on TSL sample data CSVs."
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print the summary without writing any files.",
    )
    args = parser.parse_args()

    sample_dir = os.path.join(_PROJECT_ROOT, "resources", "sample_data")
    if not os.path.isdir(sample_dir):
        print(f"ERROR: sample data directory not found at {sample_dir}")
        return 2

    summaries = []
    for fname, freq in SAMPLE_DATA_FREQ.items():
        path = os.path.join(sample_dir, fname)
        if not os.path.isfile(path):
            print(f"WARN: {fname} referenced in SAMPLE_DATA_FREQ but not "
                  f"found at {path}")
            continue
        summaries.append(_process_one(path, freq, args.dry_run))

    # Print the per-file summary.
    any_below_min = False
    any_modified = False
    print()
    print(f"{'CSV':<32} {'FREQ':<14} {'BEFORE':>7}  {'AFTER':>7}  CHANGE")
    print("-" * 78)
    for s in summaries:
        fname = os.path.basename(s["path"])
        change_desc = ""
        if s["below_min"]:
            change_desc = "BELOW-MIN FLOOR — file unchanged, manual review needed"
            any_below_min = True
        elif s["modified"]:
            any_modified = True
            if s["dropped_range"] is not None:
                first, last = s["dropped_range"]
                change_desc = (
                    f"Dropped {s['before_rows'] - s['after_rows']} rows "
                    f"dated {first.date()} through {last.date()}"
                )
                if s["order_before"] == "ascending":
                    change_desc += "; also reversed order"
            elif s["order_before"] == "ascending":
                change_desc = "Reversed to descending order"
        else:
            change_desc = "(no change)"
        print(f"{fname:<32} {s['freq']:<14} {s['before_rows']:>7}  "
              f"{s['after_rows']:>7}  {change_desc}")

    print()
    if any_below_min:
        print("WARNING: one or more CSVs fell below the 60-observation tail "
              "floor. Files were left unmodified; investigate the flagged "
              "sources and fix manually before re-running this script.")
        return 1
    if args.dry_run:
        print("(dry-run: no files written)")
    elif not any_modified:
        print("All sample CSVs already compliant. No files modified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
