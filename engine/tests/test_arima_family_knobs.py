"""Fix B Tier 1a — ARIMA-family manual-path knobs + the _validation helper.

Covers (1) the shared _validation primitives directly; (2) the live string-parse
CLASS BUG fix — arima/sarima exposed order/seasonal_order as catalog STRINGS but
parsed them list-only, so a dialog-typed "2,1,2" made arima CRASH and sarima
silently DEFAULT; the helper's parse_int_tuple fixes both; (3) the seasonal
m>1 cross-field guard. auto_arima search knobs are Tier 1a-bis (not here).

Run:
    pytest engine/tests/test_arima_family_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

import techniques.arima as arima  # noqa: E402
import techniques.sarima as sarima  # noqa: E402
import techniques.arimax_sarimax as arimax  # noqa: E402
from techniques.base import RunContext  # noqa: E402
from techniques._validation import (  # noqa: E402
    ParamError, parse_int_tuple, require, check_seasonal, check_order_bounds,
)

_SEASONAL = [100 + 0.4 * i + 12 * math.sin(2 * math.pi * i / 12) + 2 * math.cos(i / 3.0)
             for i in range(144)]


def _run(mod, tid, params):
    raw = {"technique_id": tid, "preset": "Balanced", "frequency": "Monthly",
           "series": [{"name": "y", "values": _SEASONAL}], "params": params}
    return mod.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


class TestValidationHelper(unittest.TestCase):
    def test_parse_string_list_tuple(self):
        self.assertEqual(parse_int_tuple("2,1,2", 3, "x"), (2, 1, 2))
        self.assertEqual(parse_int_tuple([2, 1, 2], 3, "x"), (2, 1, 2))
        self.assertEqual(parse_int_tuple((0, 1, 1, 12), 4, "x"), (0, 1, 1, 12))

    def test_empty_absent_route_to_default(self):
        self.assertIsNone(parse_int_tuple("", 3, "x"))
        self.assertIsNone(parse_int_tuple(None, 3, "x"))
        self.assertEqual(parse_int_tuple("", 4, "x", default=(0, 0, 0, 0)), (0, 0, 0, 0))

    def test_auto_routes_to_default_only_when_allowed(self):
        self.assertIsNone(parse_int_tuple("auto", 3, "x", allow_auto=True))
        with self.assertRaises(ParamError):
            parse_int_tuple("auto", 3, "x")  # not allowed -> parse attempt -> fail

    def test_malformed_raises(self):
        for bad in ("a,b,c", "1,2", "1,2,3,4"):
            with self.assertRaises(ParamError):
                parse_int_tuple(bad, 3, "x")

    def test_require(self):
        require(True, "ok")
        with self.assertRaises(ParamError):
            require(False, "boom")

    def test_check_seasonal(self):
        check_seasonal(P=0, D=0, Q=0, m=1)        # non-seasonal: fine
        check_seasonal(P=1, D=0, Q=0, m=12)       # seasonal w/ m>1: fine
        with self.assertRaises(ParamError):
            check_seasonal(P=1, D=0, Q=0, m=1)    # seasonal order but m=1
        with self.assertRaises(ParamError):
            check_seasonal(seasonal=True, m=1)

    def test_check_order_bounds(self):
        check_order_bounds(p=2, max_p=5, cap_p=7)
        with self.assertRaises(ParamError):
            check_order_bounds(p=5, max_p=2)       # max < component
        with self.assertRaises(ParamError):
            check_order_bounds(max_p=99, cap_p=7)  # over cap


class TestArimaParseFix(unittest.TestCase):
    def test_order_string_honored_not_crashed(self):
        r = _run(arima, "arima", {"order": "2,1,2"})
        self.assertEqual(r.get("status"), "success", _err(r))
        self.assertIn("2,1,2", str(_aud(r, "order")))

    def test_seasonal_order_string_honored(self):
        r = _run(arima, "arima", {"order": "1,1,1", "seasonal_order": "1,1,1,12"})
        self.assertEqual(r.get("status"), "success", _err(r))
        self.assertIn("1,1,1,12", str(_aud(r, "seasonal_order")))

    def test_malformed_order_fails_clean(self):
        r = _run(arima, "arima", {"order": "a,b,c"})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("integers", _err(r))

    def test_seasonal_m_guard_negative_control(self):
        # P=1 but m=1 -> contradictory seasonal spec -> fail-fast
        r = _run(arima, "arima", {"order": "1,1,1", "seasonal_order": "1,0,0,1"})
        self.assertEqual(r.get("status"), "failure")


class TestSarimaParseFix(unittest.TestCase):
    def test_order_string_honored_not_defaulted(self):
        r = _run(sarima, "sarima", {"order": "2,1,2", "seasonal_order": "1,1,1,12"})
        self.assertEqual(r.get("status"), "success", _err(r))
        self.assertIn("2,1,2", str(_aud(r, "order")))   # NOT silently (1,1,1)

    def test_trend_accepted(self):
        r = _run(sarima, "sarima", {"order": "1,1,1", "seasonal_order": "0,0,0,0", "trend": "c"})
        self.assertEqual(r.get("status"), "success", _err(r))


class TestArimaxParseFix(unittest.TestCase):
    def test_seasonal_order_string_runs(self):
        r = _run(arimax, "arimax_sarimax", {"order": "1,1,1", "seasonal_order": "1,1,1,12"})
        self.assertEqual(r.get("status"), "success", _err(r))


class TestAutoArimaSearchKnobs(unittest.TestCase):
    """Tier 1a-bis: auto_arima search knobs (d/m/max_*/ic). The start_p/q fix
    makes max_p<2 usable (was a pmdarima crash); caps fail-fast; d-range guard;
    d2/max_d1 is VALID (d pins differencing, max_d moot)."""

    def _auto(self, params):
        p = {"seasonal": False}
        p.update(params)
        raw = {"technique_id": "auto_arima", "preset": "Balanced", "frequency": "",
               "series": [{"name": "y", "values": _SEASONAL}], "params": p}
        return arima.run(RunContext(raw), lambda *a, **k: None)

    def test_max_p_1_no_crash(self):            # the start_p/q prerequisite fix
        r = self._auto({"max_p": 1, "max_q": 1})
        self.assertEqual(r.get("status"), "success", _err(r))

    def test_max_p_over_cap_fail_fast(self):
        r = self._auto({"max_p": 50})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("maximum", _err(r))

    def test_d_out_of_range_fail_fast(self):
        r = self._auto({"d": 5})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("between 0 and 3", _err(r))

    def test_d2_maxd1_is_valid(self):           # correction 2: NOT a fail-fast
        r = self._auto({"d": 2, "max_d": 1})
        self.assertEqual(r.get("status"), "success", _err(r))

    def test_ic_hqic_valid(self):               # the new dropdown option
        r = self._auto({"ic": "hqic"})
        self.assertEqual(r.get("status"), "success", _err(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
