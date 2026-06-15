"""Fix B Tier 1c-1 - conformal_intervals method selector + per-method knobs.

conformal_intervals has THREE methods (split / cqr / enbpi) selected by
`conformal_method`, and is the most-validated technique (CONFORMAL-001). This
unit exposed the method selector + the method-conditional knobs, wired via
LITERAL get_param + blank->default, with method-applicability stated in each
catalog description (the renderer has no dynamic show/hide). It also added two
allowlist guards that previously SILENTLY coerced (conformal_method -> split,
enbpi_base -> gbr).

`confidence_level` was already exposed via the `coverage` alias (fix #5) and is
NOT re-added here.

What this proves (conformal is deterministic given a seed; no torch):
  * READ / not-inert  - the engine ECHOES each knob into audit_fields.
  * DISCRIMINATION    - two values change a deterministic output scalar, tested
                        UNDER the method where the knob is active.
  * METHOD-CONDITIONAL - the EnbPI knobs are NO-OPS on split (the verified map).
  * BYTE-IDENTICAL    - blank "" == omitting the knob (preset / default).
  * NEGATIVE controls - real-constraint guards fire, incl. the 2 new allowlists.

Run:
    pytest engine/tests/test_conformal_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402
import techniques.conformal_intervals as conf  # noqa: E402

# Deterministic series (no RNG in the DATA).
_SERIES = [100 + 0.3 * i + 8 * math.sin(2 * math.pi * i / 12) + 2 * math.sin(i * 1.7)
           for i in range(80)]


def _run(params, preset="Balanced"):
    raw = {"technique_id": "conformal_intervals", "preset": preset, "frequency": "Monthly",
           "series": [{"name": "y", "values": _SERIES}], "params": params}
    return conf.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


def _width(resp):
    a = resp.get("audit_fields") or {}
    for k in ("conformal_width", "cqr_mean_width", "enbpi_mean_width"):
        if k in a:
            return a[k]
    return None


def _ok(params):
    r = _run(params)
    assert r.get("status") == "success", _err(r)
    return r


class TestMethodSelector(unittest.TestCase):
    def test_methods_run_and_differ(self):
        split = _ok({"conformal_method": "split"})
        cqr = _ok({"conformal_method": "cqr"})
        enbpi = _ok({"conformal_method": "enbpi"})
        self.assertEqual(_aud(cqr, "conformal_method"), "cqr")       # READ
        self.assertEqual(_aud(enbpi, "conformal_method"), "enbpi")   # READ
        self.assertNotEqual(_width(split), _width(cqr))             # discrimination
        self.assertNotEqual(_width(cqr), _width(enbpi))
        self.assertNotEqual(_width(split), _width(enbpi))

    def test_default_is_split_byte_identical(self):
        d = _ok({})
        sp = _ok({"conformal_method": "split"})
        self.assertIsNotNone(_aud(d, "arima_order"))                # split path
        self.assertEqual(_width(d), _width(sp))                     # default == split

    def test_invalid_method_fails(self):
        r = _run({"conformal_method": "bogus"})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("Unknown conformal_method", _err(r))


class TestCalFraction(unittest.TestCase):
    """Applies to split + CQR (verified)."""

    def test_read_and_discrimination(self):
        a = _ok({"conformal_method": "split", "cal_fraction": 0.3})
        b = _ok({"conformal_method": "split", "cal_fraction": 0.7})
        self.assertNotEqual(_aud(a, "n_cal"), _aud(b, "n_cal"))     # changes the split

    def test_blank_is_byte_identical(self):
        absent = _ok({"conformal_method": "split"})
        blank = _ok({"conformal_method": "split", "cal_fraction": ""})
        self.assertEqual(_aud(blank, "n_cal"), _aud(absent, "n_cal"))
        self.assertEqual(_aud(blank, "conformal_quantile"), _aud(absent, "conformal_quantile"))

    def test_out_of_range_fails(self):
        for v in (1.5, 0):
            r = _run({"conformal_method": "split", "cal_fraction": v})
            self.assertEqual(r.get("status"), "failure", f"cal_fraction={v}")
            self.assertIn("(0, 1)", _err(r))


class TestNLags(unittest.TestCase):
    """Applies to CQR + EnbPI (verified); not read on split."""

    def test_read_cqr_and_enbpi(self):
        c = _ok({"conformal_method": "cqr", "n_lags": 5})
        e = _ok({"conformal_method": "enbpi", "n_lags": 7})
        self.assertEqual(_aud(c, "n_lags"), 5)
        self.assertEqual(_aud(e, "n_lags"), 7)

    def test_blank_is_byte_identical_cqr(self):
        absent = _ok({"conformal_method": "cqr"})
        blank = _ok({"conformal_method": "cqr", "n_lags": ""})
        self.assertEqual(_aud(blank, "n_lags"), _aud(absent, "n_lags"))

    def test_too_large_fails(self):
        r = _run({"conformal_method": "cqr", "n_lags": 999})
        self.assertEqual(r.get("status"), "failure")
        self.assertIn("n_lags must be in", _err(r))


class TestEnbpiKnobs(unittest.TestCase):
    """n_resamplings / block_length / enbpi_base apply to EnbPI (verified)."""

    def test_n_resamplings_read_and_discrimination(self):
        a = _ok({"conformal_method": "enbpi", "n_resamplings": 5})
        b = _ok({"conformal_method": "enbpi", "n_resamplings": 50})
        self.assertEqual(_aud(a, "n_resamplings"), 5)               # READ
        self.assertNotEqual(_aud(a, "enbpi_w"), _aud(b, "enbpi_w"))  # discrimination

    def test_enbpi_base_read_and_discrimination(self):
        g = _ok({"conformal_method": "enbpi", "enbpi_base": "gbr"})
        nn = _ok({"conformal_method": "enbpi", "enbpi_base": "neural"})
        self.assertEqual(_aud(g, "enbpi_base"), "gbr")              # READ
        self.assertEqual(_aud(nn, "enbpi_base"), "neural")
        self.assertNotEqual(_width(g), _width(nn))                  # different base learner

    def test_block_length_read(self):
        r = _ok({"conformal_method": "enbpi", "block_length": 15})
        self.assertEqual(_aud(r, "block_length"), 15)

    def test_negative_controls(self):
        for p, needle in (
            ({"enbpi_base": "bogus"}, "Unknown enbpi_base"),
            ({"n_resamplings": 0}, "must be >= 1"),
            ({"block_length": 0}, "must be >= 1"),
        ):
            r = _run({"conformal_method": "enbpi", **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestMethodConditional(unittest.TestCase):
    """The EnbPI-specific knobs are NO-OPS on split (the verified map -> the
    'Applies to the EnbPI method' disclosure is accurate)."""

    def test_enbpi_knobs_noop_on_split(self):
        base = _ok({"conformal_method": "split"})
        withk = _ok({"conformal_method": "split", "n_resamplings": 99,
                     "block_length": 20, "enbpi_base": "neural"})
        self.assertEqual(_width(base), _width(withk))


if __name__ == "__main__":
    unittest.main(verbosity=2)
