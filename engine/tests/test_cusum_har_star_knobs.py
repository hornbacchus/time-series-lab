"""Fix B Tier 1c-3 - cusum + har_rv + star knobs (the final Tier 1 unit).

Four cell_type-style inert controls were FIXED by renaming the catalog keys to
the engine keys (backlog 25->21):
  cusum: threshold->cusum_h, drift->cusum_k
  star:  max_lag->ar_order, transition->star_type (+ its wrong options
         {logistic,exponential} -> the engine tokens {LSTAR,ESTAR,both})
plus genuine gaps exposed: cusum target/ph_delta/ph_lambda; har_rv cascade lags
(daily/weekly/monthly) + use_log (read-as-params, not hardcoded Corsi); star
delay/horizon. All wired via LITERAL get_param + blank->default (byte-identical).
star_type is preset-aware (Thorough = "both") -> a NULL default routes to cfg.
gamma (weakly-identified) stays UNEXPOSED (specification-only).

Run:
    pytest engine/tests/test_cusum_har_star_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402
import techniques.cusum_page_hinkley as cusum  # noqa: E402
import techniques.har_rv as har  # noqa: E402
import techniques.star_model as star  # noqa: E402

# level-shift series (for the change detector)
_SHIFT = [100 + (2 if i % 3 else -2) for i in range(60)] + [115 + (2 if i % 3 else -2) for i in range(40)]
# positive "realized variance" series
_RV = [abs(0.5 + 0.3 * math.sin(i / 7.0) + 0.2 * ((i * 37) % 11 - 5) / 5) for i in range(120)]
# regime-like nonlinear series
_NL = [(3 if i < 75 else -3) + 2 * math.sin(i / 5.0) + 0.5 * ((i * 53) % 13 - 6) / 6 for i in range(140)]


def _run(mod, tid, params, vals, preset="Fast"):
    raw = {"technique_id": tid, "preset": preset, "frequency": "Monthly",
           "series": [{"name": "y", "values": vals}], "params": params}
    return mod.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


class TestCUSUM(unittest.TestCase):
    def _ok(self, params):
        r = _run(cusum, "cusum_page_hinkley", params, _SHIFT)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_cusum_h_read_and_discrimination(self):
        lo = self._ok({"cusum_h": 2.0})
        hi = self._ok({"cusum_h": 20.0})
        self.assertEqual(_aud(lo, "cusum_h"), 2.0)            # READ (renamed from threshold)
        self.assertNotEqual(_aud(lo, "n_cusum_up"), _aud(hi, "n_cusum_up"))   # different detection

    def test_threshold_is_now_inert(self):
        # the OLD catalog key 'threshold' is no longer a control (renamed to
        # cusum_h) -> setting it has no effect (cusum_h stays the auto default).
        r = self._ok({"threshold": 2.0})
        self.assertNotEqual(_aud(r, "cusum_h"), 2.0)          # auto 5-sigma, not 2

    def test_target_and_ph_read(self):
        r = self._ok({"target": 105.0, "ph_lambda": 30.0})
        self.assertEqual(_aud(r, "target"), 105.0)            # READ (the user-settable reference)
        self.assertEqual(_aud(r, "ph_lambda"), 30.0)

    def test_blank_is_byte_identical(self):
        absent = self._ok({})
        blank = self._ok({"cusum_h": "", "cusum_k": ""})
        self.assertEqual(_aud(blank, "cusum_h"), _aud(absent, "cusum_h"))
        self.assertEqual(_aud(blank, "cusum_k"), _aud(absent, "cusum_k"))

    def test_negative_controls(self):
        for p, needle in (({"cusum_h": 0}, "cusum_h must be > 0"),
                          ({"cusum_h": -1}, "cusum_h must be > 0"),
                          ({"ph_lambda": -1}, "ph_lambda must be >= 0")):
            r = _run(cusum, "cusum_page_hinkley", p, _SHIFT)
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestHARRV(unittest.TestCase):
    def _ok(self, params):
        r = _run(har, "har_rv", params, _RV)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_cascade_lags_read_and_discrimination(self):
        five = self._ok({"weekly_lag": 5})
        ten = self._ok({"weekly_lag": 10})
        self.assertEqual(_aud(five, "weekly_lag"), 5)         # READ (not hardcoded Corsi)
        self.assertEqual(_aud(ten, "weekly_lag"), 10)
        self.assertNotEqual(_aud(five, "R2"), _aud(ten, "R2"))   # changes the fit

    def test_use_log_read_and_discrimination(self):
        off = self._ok({"use_log": False})
        on = self._ok({"use_log": True})
        self.assertFalse(_aud(off, "use_log"))
        self.assertTrue(_aud(on, "use_log"))
        self.assertNotEqual(_aud(off, "R2"), _aud(on, "R2"))

    def test_blank_is_byte_identical(self):
        absent = self._ok({})
        blank = self._ok({"weekly_lag": "", "monthly_lag": ""})
        self.assertEqual(_aud(blank, "weekly_lag"), _aud(absent, "weekly_lag"))
        self.assertEqual(_aud(blank, "monthly_lag"), _aud(absent, "monthly_lag"))

    def test_negative_controls(self):
        for p, needle in (({"daily_lag": 0}, "daily_lag must be >= 1"),
                          ({"weekly_lag": 0}, "weekly_lag must be >= 1")):
            r = _run(har, "har_rv", p, _RV)
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestSTAR(unittest.TestCase):
    def _ok(self, params, preset="Balanced"):
        r = _run(star, "star", params, _NL, preset)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_star_type_read_and_discrimination(self):
        lstar = self._ok({"star_type": "LSTAR"})
        estar = self._ok({"star_type": "ESTAR"})
        self.assertEqual(_aud(lstar, "star_type"), "LSTAR")   # READ (renamed from transition)
        self.assertEqual(_aud(estar, "star_type"), "ESTAR")
        self.assertNotEqual(_aud(lstar, "gamma"), _aud(estar, "gamma"))   # different transition

    def test_ar_order_delay_read(self):
        r = self._ok({"ar_order": 2, "delay": 2})
        self.assertEqual(_aud(r, "ar_order"), 2)              # READ (renamed from max_lag)
        self.assertEqual(_aud(r, "delay"), 2)

    def test_star_type_blank_preset_aware(self):
        # Thorough cfg star_type = "both" -> blank must route to cfg, NOT a fixed
        # token (a fixed default would silently downgrade Thorough to LSTAR).
        absent = self._ok({}, preset="Thorough")
        blank = self._ok({"star_type": ""}, preset="Thorough")
        self.assertEqual(_aud(blank, "star_type"), _aud(absent, "star_type"))
        self.assertEqual(_aud(blank, "ar_order"), _aud(absent, "ar_order"))

    def test_negative_controls(self):
        for p, needle in (({"ar_order": 0}, "ar_order must be >= 1"),
                          ({"delay": 0}, "delay must be >= 1"),
                          ({"horizon": 0}, "horizon must be >= 1"),
                          ({"star_type": "bogus"}, "Unknown star_type")):
            r = _run(star, "star", p, _NL, "Balanced")
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
