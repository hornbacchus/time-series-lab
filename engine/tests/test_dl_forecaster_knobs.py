"""Fix B Tier 1b - the 5 DL sequence forecasters' newly-exposed knobs.

Techniques: lstm_gru, tcn, nbeats, transformer, nhits. Each grew first-class +
advanced catalog controls (n_lags, learning_rate, hidden_size, n_layers,
model_type, kernel_size, n_blocks, theta_size, d_model, n_heads, n_encoder_layers,
dim_feedforward, dropout, n_stacks, pooling_sizes) wired via LITERAL get_param
reads with a blank -> preset-cfg fallback (byte-identical) and fail-fast guards.

What this proves, empirically, on the PyTorch path (torch is required here):
  * READ / not-inert - the engine ECHOES each knob into audit_fields; a distinct
    value round-trips, so the control is consumed (not a dead dialog field).
  * DISCRIMINATION - n_params is a deterministic architecture fingerprint; two
    values of an architecture knob yield different n_params (the knob really
    reconfigures the model, training nondeterminism aside).
  * BYTE-IDENTICAL blank - a blank "" routes to the preset cfg, identical to
    omitting the knob (the firm default-preservation invariant, control level).
  * NEGATIVE controls - the real-constraint guards fire (lr>0, epochs in
    [1,1000], dropout in [0,1), n_lags>=1, kernel_size>=1, len(pooling)==n_stacks,
    pooling>=1, the pre-existing d_model % n_heads). No false controls.

torch-only knobs (lstm model_type, tcn kernel_size, transformer d_model/n_heads/
dropout) are exercised here on the Thorough preset, whose cfg is use_torch=True.

Run:
    pytest engine/tests/test_dl_forecaster_knobs.py -v
"""
import math
import os
import sys
import unittest

_ENGINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from techniques.base import RunContext  # noqa: E402
import techniques.lstm_gru_forecast as lstm  # noqa: E402
import techniques.tcn_forecast as tcn  # noqa: E402
import techniques.nbeats_forecast as nbeats  # noqa: E402
import techniques.transformer_forecast as transformer  # noqa: E402
import techniques.nhits_forecast as nhits  # noqa: E402

try:
    import torch  # noqa: F401
    _HAS_TORCH = True
except Exception:
    _HAS_TORCH = False

# Deterministic series: trend + a 12-period seasonal (no randomness in the DATA;
# any run-to-run wobble comes only from training, which n_params is immune to).
_SERIES = [100 + 0.3 * i + 8 * math.sin(2 * math.pi * i / 12) for i in range(72)]


def _run(mod, tid, params, preset="Thorough"):
    raw = {"technique_id": tid, "preset": preset, "frequency": "Monthly",
           "series": [{"name": "y", "values": _SERIES}], "params": params}
    return mod.run(RunContext(raw), lambda *a, **k: None)


def _aud(resp, key):
    return (resp.get("audit_fields") or {}).get(key)


def _err(resp):
    return str(resp.get("error") or resp.get("error_message") or "")


# small, fast, torch-path config shared by the success runs
def _base(**over):
    p = {"horizon": 4, "n_lags": 6, "epochs": 3}
    p.update(over)
    return p


@unittest.skipUnless(_HAS_TORCH, "PyTorch required for the DL forecaster torch path")
class TestReadAndDiscrimination(unittest.TestCase):
    """Each exposed architecture knob is READ (echoed) and DISCRIMINATES (n_params)."""

    def _ok(self, mod, tid, params):
        r = _run(mod, tid, params)
        self.assertEqual(r.get("status"), "success", _err(r))
        return r

    def test_lstm_hidden_layers_modeltype(self):
        small = self._ok(lstm, "lstm_gru_forecast", _base(hidden_size=7, n_layers=1))
        big = self._ok(lstm, "lstm_gru_forecast", _base(hidden_size=19, n_layers=1))
        deep = self._ok(lstm, "lstm_gru_forecast", _base(hidden_size=7, n_layers=2))
        self.assertEqual(_aud(small, "hidden_size"), 7)        # READ
        self.assertEqual(_aud(small, "n_lags"), 6)             # READ
        self.assertNotEqual(_aud(small, "n_params"), _aud(big, "n_params"))    # hidden_size
        self.assertNotEqual(_aud(small, "n_params"), _aud(deep, "n_params"))   # n_layers
        # model_type lstm vs gru: different cell -> different param count
        g = self._ok(lstm, "lstm_gru_forecast", _base(model_type="GRU"))
        l = self._ok(lstm, "lstm_gru_forecast", _base(model_type="LSTM"))
        self.assertEqual(str(_aud(g, "model_type")).lower(), "gru")
        self.assertNotEqual(_aud(g, "n_params"), _aud(l, "n_params"))

    def test_tcn_kernel_channels(self):
        k2 = self._ok(tcn, "tcn_forecast", _base(kernel_size=2, n_channels=8))
        k4 = self._ok(tcn, "tcn_forecast", _base(kernel_size=4, n_channels=8))
        c16 = self._ok(tcn, "tcn_forecast", _base(kernel_size=2, n_channels=16))
        self.assertEqual(_aud(k2, "kernel_size"), 2)           # READ
        self.assertNotEqual(_aud(k2, "n_params"), _aud(k4, "n_params"))   # kernel_size
        self.assertNotEqual(_aud(k2, "n_params"), _aud(c16, "n_params"))  # n_channels

    def test_nbeats_blocks_hidden_theta(self):
        b1 = self._ok(nbeats, "nbeats_forecast", _base(n_blocks=1, hidden_size=16, theta_size=8))
        b3 = self._ok(nbeats, "nbeats_forecast", _base(n_blocks=3, hidden_size=16, theta_size=8))
        h = self._ok(nbeats, "nbeats_forecast", _base(n_blocks=1, hidden_size=24, theta_size=8))
        t = self._ok(nbeats, "nbeats_forecast", _base(n_blocks=1, hidden_size=16, theta_size=12))
        self.assertEqual(_aud(b1, "n_blocks"), 1)              # READ
        self.assertEqual(_aud(b1, "hidden_size"), 16)         # READ
        self.assertNotEqual(_aud(b1, "n_params"), _aud(b3, "n_params"))   # n_blocks
        self.assertNotEqual(_aud(b1, "n_params"), _aud(h, "n_params"))    # hidden_size
        self.assertNotEqual(_aud(b1, "n_params"), _aud(t, "n_params"))    # theta_size

    def test_transformer_dmodel_layers_ff(self):
        a = self._ok(transformer, "transformer_forecast",
                     _base(d_model=8, n_heads=2, n_encoder_layers=1, dim_feedforward=16))
        d = self._ok(transformer, "transformer_forecast",
                     _base(d_model=16, n_heads=2, n_encoder_layers=1, dim_feedforward=16))
        L = self._ok(transformer, "transformer_forecast",
                     _base(d_model=8, n_heads=2, n_encoder_layers=2, dim_feedforward=16))
        ff = self._ok(transformer, "transformer_forecast",
                      _base(d_model=8, n_heads=2, n_encoder_layers=1, dim_feedforward=32))
        self.assertEqual(_aud(a, "d_model"), 8)               # READ
        self.assertEqual(_aud(a, "n_encoder_layers"), 1)      # READ
        self.assertEqual(_aud(a, "dim_feedforward"), 16)      # READ
        self.assertNotEqual(_aud(a, "n_params"), _aud(d, "n_params"))    # d_model
        self.assertNotEqual(_aud(a, "n_params"), _aud(L, "n_params"))    # n_encoder_layers
        self.assertNotEqual(_aud(a, "n_params"), _aud(ff, "n_params"))   # dim_feedforward

    def test_nhits_stacks_blocks_hidden_pooling(self):
        s2 = self._ok(nhits, "nhits_forecast", _base(n_stacks=2, n_blocks=1, hidden_size=16,
                                                     pooling_sizes="2,1"))
        s3 = self._ok(nhits, "nhits_forecast", _base(n_stacks=3, n_blocks=1, hidden_size=16,
                                                     pooling_sizes="2,1,1"))
        h = self._ok(nhits, "nhits_forecast", _base(n_stacks=2, n_blocks=1, hidden_size=24,
                                                    pooling_sizes="2,1"))
        self.assertEqual(_aud(s2, "n_stacks"), 2)             # READ
        self.assertEqual(list(_aud(s2, "pooling_sizes")), [2, 1])   # READ (parsed list)
        self.assertNotEqual(_aud(s2, "n_params"), _aud(s3, "n_params"))   # n_stacks
        self.assertNotEqual(_aud(s2, "n_params"), _aud(h, "n_params"))    # hidden_size
        # pooling actually downsamples -> changes the forecast (no param-count change)
        flat = self._ok(nhits, "nhits_forecast", _base(n_stacks=2, n_blocks=1, hidden_size=16,
                                                       pooling_sizes="1,1"))
        self.assertNotEqual(_aud(s2, "forecast_end_value"), _aud(flat, "forecast_end_value"))


@unittest.skipUnless(_HAS_TORCH, "PyTorch required for the DL forecaster torch path")
class TestBlankIsByteIdentical(unittest.TestCase):
    """A blank "" routes to the preset cfg, identical to omitting the knob."""

    def _echo_eq(self, mod, tid, key, audkey=None, **base_over):
        audkey = audkey or key
        absent = _run(mod, tid, _base(**base_over))
        blank = _run(mod, tid, _base(**{key: "", **base_over}))
        self.assertEqual(absent.get("status"), "success", _err(absent))
        self.assertEqual(blank.get("status"), "success", _err(blank))
        self.assertEqual(_aud(blank, audkey), _aud(absent, audkey),
                         f"{tid}: blank {key} did not match the preset default")
        # and the architecture is identical
        self.assertEqual(_aud(blank, "n_params"), _aud(absent, "n_params"))

    def test_lstm_blank_hidden_size(self):
        self._echo_eq(lstm, "lstm_gru_forecast", "hidden_size")

    def test_tcn_blank_kernel_size(self):
        self._echo_eq(tcn, "tcn_forecast", "kernel_size")

    def test_nbeats_blank_hidden_size(self):
        self._echo_eq(nbeats, "nbeats_forecast", "hidden_size")

    def test_transformer_blank_dim_feedforward(self):
        self._echo_eq(transformer, "transformer_forecast", "dim_feedforward")

    def test_nhits_blank_hidden_size(self):
        # Pin a known-compatible pooling/n_stacks/n_lags shape: the default
        # Thorough pooling [8,4,1] is fragile at small n_lags (banked finding),
        # unrelated to the hidden_size blank==absent invariant under test here.
        self._echo_eq(nhits, "nhits_forecast", "hidden_size",
                      n_stacks=2, pooling_sizes="2,1", n_lags=8)


@unittest.skipUnless(_HAS_TORCH, "PyTorch required for the DL forecaster torch path")
class TestNegativeControls(unittest.TestCase):
    """Real-constraint guards fire fast (before training). No false controls."""

    def _fail(self, mod, tid, params, needle=None):
        r = _run(mod, tid, params)
        self.assertEqual(r.get("status"), "failure", f"expected failure, got {r.get('status')}")
        if needle:
            self.assertIn(needle, _err(r))
        return r

    def test_lr_must_be_positive(self):
        self._fail(lstm, "lstm_gru_forecast", _base(learning_rate=0), "must be > 0")
        self._fail(nbeats, "nbeats_forecast", _base(learning_rate=-1), "must be > 0")

    def test_epochs_range(self):
        self._fail(lstm, "lstm_gru_forecast", _base(epochs=5000), "between 1 and 1000")
        self._fail(transformer, "transformer_forecast", _base(epochs=0), "between 1 and 1000")

    def test_n_lags_min(self):
        self._fail(tcn, "tcn_forecast", _base(n_lags=0), "must be >= 1")

    def test_kernel_size_min(self):
        self._fail(tcn, "tcn_forecast", _base(kernel_size=0), "must be >= 1")

    def test_dropout_range(self):
        self._fail(transformer, "transformer_forecast", _base(dropout=1.5), "must be in [0, 1)")

    def test_dmodel_divisible_by_heads(self):
        # pre-existing engine guard (untouched this unit): 50 % 4 != 0
        self._fail(transformer, "transformer_forecast", _base(d_model=50, n_heads=4))

    def test_pooling_len_must_match_n_stacks(self):
        self._fail(nhits, "nhits_forecast",
                   _base(n_stacks=3, pooling_sizes="2,1"), "n_stacks")

    def test_pooling_entries_positive(self):
        self._fail(nhits, "nhits_forecast",
                   _base(n_stacks=3, pooling_sizes="0,1,1"), "must all be >= 1")

    def test_pooling_malformed_parse(self):
        self._fail(nhits, "nhits_forecast",
                   _base(n_stacks=2, pooling_sizes="a,b"), "comma-separated integers")


if __name__ == "__main__":
    unittest.main(verbosity=2)
