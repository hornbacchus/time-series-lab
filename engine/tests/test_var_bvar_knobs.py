"""Fix B Tier 1c-2 - var + bvar (the system techniques) knobs.

VAR exposed trend + irf_periods + the SVAR identification SELECTOR (3 of 4
schemes; sign_restrictions/proxy_instrument matrix/array inputs are BANKED for
a C# matrix-editor/column-picker unit) + sr_n_draws + a fixed-lag override,
plus an allowlist guard on svar_identification (was a silent fallthrough ->
cholesky). BVAR exposed the Minnesota lambda2/lambda3 + irf_horizon +
include_constant + n_draws, and ADDED the n_draws>=1 positivity guard (the
discharged SV/bvar-ordering note: n_draws<1 produced empty/degenerate bands).

Wired via LITERAL get_param + blank->default (byte-identical). Both techniques
are deterministic given a seed (no torch).

Run:
    pytest engine/tests/test_var_bvar_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402
import techniques.var_model as var  # noqa: E402
import techniques.bvar as bvar  # noqa: E402


def _lcg(seed):
    x = seed % (2 ** 31)
    out = []
    for _ in range(300):
        x = (1103515245 * x + 12345) % (2 ** 31)
        out.append(x / 2 ** 31 - 0.5)
    return out


def _mseries(n=90):
    # 3 well-conditioned (independent-noise) stationary series -> non-singular
    # covariance (phase-shifted pure sines are collinear and break the VAR fit).
    out = []
    for k, (name, seed) in enumerate((("y1", 7), ("y2", 101), ("y3", 9973))):
        nz = _lcg(seed)
        out.append({"name": name,
                    "values": [50 + 0.1 * i + 4 * math.sin(2 * math.pi * i / (8 + 2 * k)) + 3.0 * nz[i]
                               for i in range(n)]})
    return out


def _vrun(params, preset="Fast"):
    raw = {"technique_id": "var", "preset": preset, "frequency": "Monthly",
           "series": _mseries(), "params": params}
    return var.run(RunContext(raw), lambda *a, **k: None)


def _brun(params, preset="Balanced"):
    raw = {"technique_id": "bvar", "preset": preset, "frequency": "Monthly",
           "series": _mseries(), "params": params}
    return bvar.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


class TestVAR(unittest.TestCase):
    def _ok(self, params):
        r = _vrun(params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_trend_read_and_discrimination(self):
        n = self._ok({"trend": "n"})
        ct = self._ok({"trend": "ct"})
        self.assertEqual(_aud(n, "trend"), "n")          # READ
        self.assertEqual(_aud(ct, "trend"), "ct")
        self.assertNotEqual(_aud(n, "aic"), _aud(ct, "aic"))   # different model

    def test_irf_periods_read(self):
        r = self._ok({"irf_periods": 7})
        self.assertEqual(_aud(r, "irf_periods"), 7)

    def test_svar_scheme_read_and_discrimination(self):
        chol = self._ok({"svar_identification": "cholesky"})
        bq = self._ok({"svar_identification": "blanchard_quah"})
        sign = self._ok({"svar_identification": "sign_restriction"})
        self.assertEqual(_aud(chol, "svar_identification"), "cholesky")   # READ
        self.assertEqual(_aud(bq, "svar_identification"), "blanchard_quah")
        self.assertTrue(_aud(bq, "bq_computed"))                          # scheme actually ran
        self.assertTrue(_aud(sign, "sign_restriction_computed"))

    def test_fixed_lag_override(self):
        r = self._ok({"lag": 2})
        self.assertEqual(_aud(r, "var_order"), 2)        # pins the order

    def test_sr_n_draws_read(self):
        # sign-restriction-only knob, tested UNDER the sign scheme
        few = self._ok({"svar_identification": "sign_restriction", "sr_n_draws": 200})
        many = self._ok({"svar_identification": "sign_restriction", "sr_n_draws": 1000})
        self.assertNotEqual(_aud(few, "sr_n_retained"), _aud(many, "sr_n_retained"))

    def test_blank_is_byte_identical(self):
        absent = self._ok({})
        blank = self._ok({"irf_periods": "", "trend": ""})
        self.assertEqual(_aud(blank, "irf_periods"), _aud(absent, "irf_periods"))
        self.assertEqual(_aud(blank, "trend"), _aud(absent, "trend"))

    def test_negative_controls(self):
        bad_scheme = _vrun({"svar_identification": "bogus"})
        self.assertEqual(bad_scheme.get("status"), "failure")
        self.assertIn("Unknown svar_identification", _err(bad_scheme))
        for p, needle in (({"irf_periods": 0}, "irf_periods must be >= 1"),
                          ({"lag": 0}, "lag must be >= 1"),
                          ({"svar_identification": "sign_restriction", "sr_n_draws": 0}, "sr_n_draws must be >= 1")):
            r = _vrun(p)
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestBVAR(unittest.TestCase):
    def _ok(self, params):
        r = _brun(params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_lambda2_read_and_discrimination(self):
        lo = self._ok({"lambda2": 0.1})
        hi = self._ok({"lambda2": 0.9})
        self.assertEqual(_aud(lo, "lambda2"), 0.1)       # READ
        self.assertNotEqual(_aud(lo, "own_shock_share_longest_horizon"),
                            _aud(hi, "own_shock_share_longest_horizon"))   # shapes the prior

    def test_lambda3_irf_horizon_read(self):
        r = self._ok({"lambda3": 2.0, "irf_horizon": 10})
        self.assertEqual(_aud(r, "lambda3"), 2.0)
        self.assertEqual(_aud(r, "irf_horizon"), 10)

    def test_include_constant_discrimination(self):
        on = self._ok({"include_constant": True})
        off = self._ok({"include_constant": False})
        self.assertNotEqual(_aud(on, "total_params"), _aud(off, "total_params"))

    def test_n_draws_read(self):
        r = self._ok({"n_draws": 200})
        self.assertEqual(_aud(r, "n_draws"), 200)

    def test_blank_is_byte_identical(self):
        absent = self._ok({})
        blank = self._ok({"lambda2": "", "n_draws": ""})
        self.assertEqual(_aud(blank, "lambda2"), _aud(absent, "lambda2"))
        self.assertEqual(_aud(blank, "n_draws"), _aud(absent, "n_draws"))

    def test_negative_controls(self):
        for p, needle in (({"n_draws": 0}, "n_draws must be >= 1"),     # the discharged guard
                          ({"lambda2": 0}, "lambda2 must be > 0"),
                          ({"lambda3": -1}, "lambda3 must be > 0"),
                          ({"irf_horizon": 0}, "irf_horizon must be >= 1")):
            r = _brun(p)
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
