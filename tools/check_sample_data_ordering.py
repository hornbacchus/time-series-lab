"""Guard: every dated CSV in resources/sample_data/ must be ascending by date.

The durable invariant behind the Station-A sort fix (the inert /
default-path / catalog-subset-of-registry guard pattern): the audit found a
CLASS (all 14 dated samples disordered), so without a guard the next sample
CSV added or regenerated silently reopens it. This asserts ascending
(oldest -> newest) order; exit 1 listing any non-ascending dated CSV.

Robust date detection (the audit's first parser failed on the real
%d-%b-%Y format): tries multiple formats and finds the date column by header
name or by parsing column 0. NON-dated CSVs are skipped cleanly (no false
positives). An ALLOWLIST carries any file that legitimately should not be
ascending (none today) with a documented reason.

Usage:
    python check_sample_data_ordering.py            # exit 1 if any non-ascending
    python check_sample_data_ordering.py --report   # full per-file table
"""

import csv
import datetime
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_D = os.path.join(os.path.dirname(_HERE), "resources", "sample_data")

DATE_FORMATS = ("%d-%b-%Y", "%Y-%m-%d", "%Y-%m", "%b-%Y", "%Y/%m/%d",
                "%m/%d/%Y", "%d/%m/%Y", "%Y")

# Files that legitimately need NOT be ascending (documented exclusions).
ALLOWLIST: dict[str, str] = {}

_DATE_HINTS = ("date", "time", "month", "period", "year", "observation")


def parse_date(s):
    s = (s or "").strip()
    for f in DATE_FORMATS:
        try:
            return datetime.datetime.strptime(s, f)
        except ValueError:
            pass
    return None


def detect_date_column(header, data):
    """Header-name hint first; else the column whose first value parses."""
    for i, h in enumerate(header):
        if any(k in (h or "").lower() for k in _DATE_HINTS):
            if data and len(data[0]) > i and parse_date(data[0][i]):
                return i
    if data and data[0] and parse_date(data[0][0]):
        return 0
    return None


def audit():
    out = []  # (file, dated?, ascending?, detail)
    for fn in sorted(os.listdir(_D)):
        if not fn.endswith(".csv"):
            continue
        with open(os.path.join(_D, fn), encoding="utf-8-sig", newline="") as fh:
            rows = list(csv.reader(fh))
        if len(rows) < 2:
            out.append((fn, False, None, "empty")); continue
        dcol = detect_date_column(rows[0], rows[1:])
        if dcol is None:
            out.append((fn, False, None, "no date column")); continue
        ds = [parse_date(r[dcol]) for r in rows[1:] if len(r) > dcol]
        bad = sum(1 for d in ds if d is None)
        ds = [d for d in ds if d]
        asc = sum(1 for a, b in zip(ds, ds[1:]) if b > a)
        desc = sum(1 for a, b in zip(ds, ds[1:]) if b < a)
        eq = sum(1 for a, b in zip(ds, ds[1:]) if b == a)
        ascending = (desc == 0 and bad == 0)
        out.append((fn, True, ascending, f"{asc}a/{desc}d/{eq}eq" + (f" parse-fail={bad}" if bad else "")))
    return out


def main(argv):
    report = "--report" in argv
    rows = audit()
    dated = [r for r in rows if r[1]]
    print("# check_sample_data_ordering - dated sample CSVs must be ascending")
    print(f"# dated: {len(dated)} | non-dated skipped: {len(rows) - len(dated)} | "
          f"allowlisted: {len(ALLOWLIST)}")
    if report:
        for fn, isd, asc, detail in rows:
            tag = "(skip)" if not isd else ("ASC ✓" if asc else "NOT-ASC")
            print(f"  {fn:40s} {tag:8s} {detail}")
    violations = [fn for fn, isd, asc, _ in rows if isd and not asc and fn not in ALLOWLIST]
    if violations:
        print("\n## [FAIL] non-ascending dated sample CSV(s):")
        for fn in violations:
            print(f"  {fn}")
        print("\nSort ascending with tools/sort_sample_data.py (pure row reorder), "
              "or add an ALLOWLIST entry with a reason if non-ascending is intended.")
        return 1
    print("\n## [PASS] all dated sample CSVs are ascending (oldest -> newest).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
