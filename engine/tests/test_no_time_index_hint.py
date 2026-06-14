"""Guard: the no-time-index orientation hint fires for the right techniques.

Order-robustness diagnostic, ruling 4: when a DIRECTION-SENSITIVE technique
runs on a bare value column (a series but no detected date column), the engine
cannot orient the data (there is no date to read) and consumes raw row order.
``maybe_add_no_time_index_hint`` prepends a non-blocking hint to the response
so the user knows to include a date column. This must NOT fire for
order-invariant techniques (distribution/correlation/spectral), for
workbook-input techniques (no ``ctx.series``), when a time index IS present,
or on error responses.

Run:
    pytest engine/tests/test_no_time_index_hint.py -v
"""
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import (  # noqa: E402
    RunContext,
    maybe_add_no_time_index_hint,
    NO_TIME_INDEX_HINT,
)


def _ctx(tid, *, series=True, time=False):
    raw = {"technique_id": tid}
    raw["series"] = [{"name": "y", "values": [1.0, 2.0, 3.0, 4.0]}] if series else []
    if time:
        raw["time"] = ["2020-01-01", "2020-01-02", "2020-01-03", "2020-01-04"]
    return RunContext(raw)


def _resp(status="success", warnings=None):
    r = {"status": status}
    if warnings is not None:
        r["warnings"] = warnings
    return r


class TestNoTimeIndexHint(unittest.TestCase):

    def test_fires_for_direction_sensitive_no_time(self):
        for tid in ("arima", "var", "garch", "pelt_change_points", "granger_causality"):
            r = _resp()
            maybe_add_no_time_index_hint(_ctx(tid), r)
            self.assertIn(NO_TIME_INDEX_HINT, r.get("warnings", []), tid)

    def test_skips_order_invariant(self):
        for tid in ("pca_analysis", "evt_pot_gpd", "robust_estimators",
                    "fft_spectrum", "periodogram_spectral_density", "lomb_scargle",
                    "wavelet_transform", "ssa", "emd_hht"):
            r = _resp()
            maybe_add_no_time_index_hint(_ctx(tid), r)
            self.assertNotIn(NO_TIME_INDEX_HINT, r.get("warnings", []), tid)

    def test_skips_when_time_index_present(self):
        r = _resp()
        maybe_add_no_time_index_hint(_ctx("arima", time=True), r)
        self.assertNotIn(NO_TIME_INDEX_HINT, r.get("warnings", []))

    def test_skips_workbook_technique_without_series(self):
        # bond_yield_forecast reads a workbook, not ctx.series -> no hint.
        r = _resp()
        maybe_add_no_time_index_hint(_ctx("bond_yield_forecast", series=False), r)
        self.assertNotIn(NO_TIME_INDEX_HINT, r.get("warnings", []))

    def test_skips_error_response(self):
        r = _resp(status="failure")
        maybe_add_no_time_index_hint(_ctx("arima"), r)
        self.assertNotIn(NO_TIME_INDEX_HINT, r.get("warnings", []))

    def test_prepends_preserving_existing_and_idempotent(self):
        r = _resp(warnings=["pre-existing warning"])
        maybe_add_no_time_index_hint(_ctx("arima"), r)
        maybe_add_no_time_index_hint(_ctx("arima"), r)  # second call must not duplicate
        self.assertEqual(r["warnings"].count(NO_TIME_INDEX_HINT), 1)
        self.assertIn("pre-existing warning", r["warnings"])
        self.assertEqual(r["warnings"][0], NO_TIME_INDEX_HINT)  # prepended


if __name__ == "__main__":
    unittest.main(verbosity=2)
