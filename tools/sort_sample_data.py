"""Sort the dated sample-data CSVs ascending by date (oldest -> newest).

The Station-A acceptance audit found EVERY dated CSV in resources/sample_data/
out of canonical order: 13 cleanly reverse-chronological (newest-first) and
treasury_yields genuinely SCRAMBLED (361 ascending vs 5784 descending steps).
Ascending is the canonical convention (what a human reads top-to-bottom and
what an order-sensitive technique consumes when no time-index column is
selected -- a descending load would feed the series backwards).

This is a PURE ROW REORDER: header, columns, and every value are preserved
exactly; only row order changes. Each file's pre/post row MULTISET is asserted
equal before saving (same rows, new order) -- a value/column change aborts.

Reproducible (the style_bespoke_templates.py precedent): re-runnable; an
already-ascending file is rewritten identically (idempotent). Pairs with
check_sample_data_ordering.py, which enforces the convention going forward.
"""

import csv
import os
import sys

from check_sample_data_ordering import DATE_FORMATS, detect_date_column, parse_date  # noqa: E402

D = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "resources", "sample_data")


def sort_file(path):
    with open(path, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))
    if len(rows) < 2:
        return None
    header, data = rows[0], rows[1:]
    dcol = detect_date_column(header, data)
    if dcol is None:
        return None  # not a dated CSV -- leave it
    before = sorted(map(tuple, data))
    keyed = [(parse_date(r[dcol]), r) for r in data]
    if any(k is None for k, _ in keyed):
        sys.exit(f"FATAL {os.path.basename(path)}: unparseable date(s) -- aborting (no reorder).")
    keyed.sort(key=lambda kr: kr[0])
    new_data = [r for _, r in keyed]
    after = sorted(map(tuple, new_data))
    if before != after:
        sys.exit(f"FATAL {os.path.basename(path)}: row multiset changed -- aborting (would alter values).")
    # Preserve the source line terminator convention (\n).
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(header)
        w.writerows(new_data)
    return len(new_data)


def main():
    sorted_n = skipped = 0
    for fn in sorted(os.listdir(D)):
        if not fn.endswith(".csv"):
            continue
        n = sort_file(os.path.join(D, fn))
        if n is None:
            print(f"  skip (no date col): {fn}"); skipped += 1
        else:
            print(f"  sorted ascending ({n} rows, values preserved): {fn}"); sorted_n += 1
    print(f"\n{sorted_n} dated CSVs sorted; {skipped} non-dated skipped.")


if __name__ == "__main__":
    main()
