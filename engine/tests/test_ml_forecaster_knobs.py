"""Fix B Tier 1b-bis - the 5 ML forecasters' newly-exposed/wired knobs.

Techniques: gradient_boosting, quantile_regression, echo_state, gaussian_process,
svr - sklearn/library-backed, DETERMINISTIC given a seed (no torch training), so
discrimination is clean and exact.

This unit (per the ratified STEP-0):
  * exposed read-but-unexposed gaps (GB max_depth/learning_rate, QR n_lags/
    n_estimators/max_depth/learning_rate, ESN input_scaling/ridge_alpha/warmup,
    GP kernel/normalize, SVR epsilon) via LITERAL get_param + blank->preset cfg;
  * WIRED 3 net-new reads of standard expert hyperparameters (GB subsample, GP
    gp_alpha, SVR gamma) - blank -> the same preset value the engine used before;
  * FIXED 2 cell_type-style inert controls (GB catalog max_lag->n_lags; removed
    GP's dead max_lag) - backlog 27->25;
  * FIXED the quantiles silent-drop (string was ignored -> preset) via
    parse_float_list + each in (0,1) + the preserved "ensure 0.5" logic;
  * DROPPED inert n_lags from echo_state + gaussian_process (no lag concept).

What this proves:
  * READ / not-inert  - the engine ECHOES each knob into audit_fields.
  * DISCRIMINATION    - two values of a knob change a deterministic output scalar.
  * BYTE-IDENTICAL    - blank "" == omitting the knob (preset cfg).
  * NEGATIVE controls - the real-constraint guards fire. No false controls.

Run:
    pytest engine/tests/test_ml_forecaster_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402
import techniques.gradient_boosting_forecast as gb  # noqa: E402
import techniques.quantile_regression_model as qr  # noqa: E402
import techniques.echo_state_network as esn  # noqa: E402
import techniques.gaussian_process_forecast as gp  # noqa: E402
import techniques.svr_forecast as svr  # noqa: E402

# Deterministic series: trend + two seasonal components (no RNG in the DATA, so
# any run-to-run difference comes purely from the knobs under test).
_SERIES = [100 + 0.3 * i + 8 * math.sin(2 * math.pi * i / 12) + 2 * math.sin(i * 1.7)
           for i in range(72)]


def _run(mod, tid, params, preset="Balanced"):
    raw = {"technique_id": tid, "preset": preset, "frequency": "Monthly",
           "series": [{"name": "y", "values": _SERIES}], "params": params}
    return mod.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


class TestGradientBoosting(unittest.TestCase):
    def _ok(self, params):
        r = _run(gb, "gradient_boosting_forecast", params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_read_and_discrimination(self):
        base = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 30, "max_depth": 2})
        self.assertEqual(_aud(base, "n_lags"), 6)            # READ (renamed from max_lag)
        self.assertEqual(_aud(base, "max_depth"), 2)         # READ
        more = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 120, "max_depth": 2})
        deep = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 30, "max_depth": 5})
        self.assertNotEqual(_aud(base, "forecast_end_value"), _aud(more, "forecast_end_value"))  # n_estimators
        self.assertNotEqual(_aud(base, "forecast_end_value"), _aud(deep, "forecast_end_value"))  # max_depth

    def test_subsample_wired(self):
        half = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 60, "subsample": 0.5})
        full = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 60, "subsample": 1.0})
        self.assertEqual(_aud(half, "subsample"), 0.5)       # READ (wired net-new)
        self.assertNotEqual(_aud(half, "forecast_end_value"), _aud(full, "forecast_end_value"))

    def test_blank_is_byte_identical(self):
        absent = self._ok({"horizon": 4, "n_lags": 6})
        blank = self._ok({"horizon": 4, "n_lags": 6, "max_depth": "", "subsample": ""})
        self.assertEqual(_aud(blank, "max_depth"), _aud(absent, "max_depth"))
        self.assertEqual(_aud(blank, "subsample"), _aud(absent, "subsample"))

    def test_negative_controls(self):
        for p, needle in (
            ({"learning_rate": 0}, "must be > 0"),
            ({"subsample": 1.5}, "(0, 1]"),
            ({"max_depth": 0}, "must be >= 1"),
            ({"n_estimators": 0}, "must be >= 1"),
        ):
            r = _run(gb, "gradient_boosting_forecast", {"horizon": 4, "n_lags": 6, **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestQuantileRegression(unittest.TestCase):
    def _ok(self, params):
        r = _run(qr, "quantile_regression", params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_quantiles_string_parsed(self):
        # the bug fix: a string was silently dropped -> preset; now parsed.
        r = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 25, "quantiles": "0.1,0.5,0.9"})
        self.assertEqual(_aud(r, "n_quantiles"), 3)                       # parsed, not 7-preset
        self.assertEqual(sorted(_aud(r, "quantiles")), [0.1, 0.5, 0.9])   # echoed
        # 0.5 auto-added when missing
        r2 = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 25, "quantiles": "0.2,0.8"})
        self.assertIn(0.5, _aud(r2, "quantiles"))

    def test_read_and_discrimination(self):
        a = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 25, "max_depth": 2})
        b = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 100, "max_depth": 2})
        self.assertEqual(_aud(a, "n_lags"), 6)               # READ
        self.assertNotEqual(_aud(a, "train_rmse_median"), _aud(b, "train_rmse_median"))  # n_estimators

    def test_blank_is_byte_identical(self):
        absent = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 25})
        blank = self._ok({"horizon": 4, "n_lags": 6, "n_estimators": 25, "quantiles": "", "max_depth": ""})
        self.assertEqual(_aud(blank, "n_quantiles"), _aud(absent, "n_quantiles"))   # blank -> preset
        self.assertEqual(_aud(blank, "max_depth"), _aud(absent, "max_depth"))

    def test_negative_controls(self):
        for p, needle in (
            ({"quantiles": "0.1,1.5"}, "(0, 1)"),
            ({"quantiles": "a,b"}, "comma-separated numbers"),
            ({"learning_rate": 0}, "must be > 0"),
        ):
            r = _run(qr, "quantile_regression", {"horizon": 4, "n_lags": 6, "n_estimators": 25, **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestEchoState(unittest.TestCase):
    def _ok(self, params):
        r = _run(esn, "echo_state_network", params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_read_and_discrimination(self):
        small = self._ok({"horizon": 4, "reservoir_size": 20, "input_scaling": 0.5})
        big = self._ok({"horizon": 4, "reservoir_size": 80, "input_scaling": 0.5})
        self.assertEqual(_aud(small, "reservoir_size"), 20)      # READ
        self.assertEqual(_aud(small, "input_scaling"), 0.5)      # READ (new gap)
        self.assertNotEqual(_aud(small, "forecast_end_value"), _aud(big, "forecast_end_value"))

    def test_blank_is_byte_identical(self):
        absent = self._ok({"horizon": 4, "reservoir_size": 30})
        blank = self._ok({"horizon": 4, "reservoir_size": 30, "input_scaling": "", "ridge_alpha": "", "warmup": ""})
        self.assertEqual(_aud(blank, "input_scaling"), _aud(absent, "input_scaling"))
        self.assertEqual(_aud(blank, "ridge_alpha"), _aud(absent, "ridge_alpha"))
        self.assertEqual(_aud(blank, "warmup"), _aud(absent, "warmup"))

    def test_negative_controls(self):
        for p, needle in (
            ({"ridge_alpha": 0}, "must be > 0"),
            ({"reservoir_size": 0}, "must be >= 1"),
            ({"input_scaling": 0}, "must be > 0"),
        ):
            r = _run(esn, "echo_state_network", {"horizon": 4, "reservoir_size": 20, **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestGaussianProcess(unittest.TestCase):
    def _ok(self, params):
        r = _run(gp, "gaussian_process_forecast", params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_kernel_dropdown_and_discrimination(self):
        rbf = self._ok({"horizon": 4, "kernel": "rbf"})
        matern = self._ok({"horizon": 4, "kernel": "matern"})
        self.assertEqual(_aud(rbf, "kernel_type"), "rbf")        # READ
        self.assertNotEqual(_aud(rbf, "forecast_end_value"), _aud(matern, "forecast_end_value"))

    def test_gp_alpha_wired(self):
        lo = self._ok({"horizon": 4, "gp_alpha": 1e-8})
        hi = self._ok({"horizon": 4, "gp_alpha": 1e-1})
        self.assertEqual(_aud(lo, "gp_alpha"), 1e-8)            # READ (wired net-new)
        self.assertNotEqual(_aud(lo, "forecast_end_value"), _aud(hi, "forecast_end_value"))

    def test_normalize_read(self):
        on = self._ok({"horizon": 4, "normalize": True})
        off = self._ok({"horizon": 4, "normalize": False})
        self.assertTrue(_aud(on, "normalized"))
        self.assertFalse(_aud(off, "normalized"))

    def test_blank_is_byte_identical(self):
        absent = self._ok({"horizon": 4})
        blank = self._ok({"horizon": 4, "gp_alpha": ""})
        self.assertEqual(_aud(blank, "gp_alpha"), _aud(absent, "gp_alpha"))

    def test_negative_controls(self):
        for p, needle in (
            ({"gp_alpha": 0}, "must be > 0"),
            ({"kernel": "bogus"}, "Unknown kernel"),
        ):
            r = _run(gp, "gaussian_process_forecast", {"horizon": 4, **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


class TestSVR(unittest.TestCase):
    def _ok(self, params):
        r = _run(svr, "svr_forecast", params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_read_and_discrimination(self):
        rbf = self._ok({"horizon": 4, "max_lag": 6, "kernel": "rbf"})
        lin = self._ok({"horizon": 4, "max_lag": 6, "kernel": "linear"})
        self.assertEqual(_aud(rbf, "kernel"), "rbf")            # READ
        self.assertNotEqual(_aud(rbf, "forecast_end_value"), _aud(lin, "forecast_end_value"))

    def test_epsilon_and_gamma_wired(self):
        a = self._ok({"horizon": 4, "max_lag": 6, "epsilon": 0.2, "gamma": "scale"})
        self.assertEqual(_aud(a, "epsilon"), 0.2)               # READ (new gap)
        self.assertEqual(_aud(a, "gamma"), "scale")             # READ (wired net-new)
        auto = self._ok({"horizon": 4, "max_lag": 6, "gamma": "auto"})
        self.assertEqual(_aud(auto, "gamma"), "auto")           # token round-trips
        # numeric gamma sets the rbf bandwidth -> different forecast (scale~auto
        # coincide on standardized features, so use explicit numeric values).
        narrow = self._ok({"horizon": 4, "max_lag": 6, "kernel": "rbf", "gamma": 0.001})
        wide = self._ok({"horizon": 4, "max_lag": 6, "kernel": "rbf", "gamma": 5.0})
        self.assertEqual(_aud(narrow, "gamma"), "0.001")        # echoed as str(gamma)
        self.assertNotEqual(_aud(narrow, "forecast_end_value"), _aud(wide, "forecast_end_value"))

    def test_sigmoid_kernel_accepted(self):
        r = self._ok({"horizon": 4, "max_lag": 6, "kernel": "sigmoid"})
        self.assertEqual(_aud(r, "kernel"), "sigmoid")          # the added option

    def test_blank_is_byte_identical(self):
        absent = self._ok({"horizon": 4, "max_lag": 6})
        blank = self._ok({"horizon": 4, "max_lag": 6, "epsilon": "", "gamma": ""})
        self.assertEqual(_aud(blank, "epsilon"), _aud(absent, "epsilon"))
        self.assertEqual(str(_aud(blank, "gamma")), str(_aud(absent, "gamma")))

    def test_negative_controls(self):
        for p, needle in (
            ({"C": 0}, "must be > 0"),
            ({"epsilon": -1}, "must be >= 0"),
            ({"gamma": "bogus"}, "scale"),
            ({"kernel": "bogus"}, "Unknown kernel"),
        ):
            r = _run(svr, "svr_forecast", {"horizon": 4, "max_lag": 6, **p})
            self.assertEqual(r.get("status"), "failure", f"{p}: {r.get('status')}")
            self.assertIn(needle, _err(r))


if __name__ == "__main__":
    unittest.main(verbosity=2)
