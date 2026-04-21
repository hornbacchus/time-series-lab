"""
Technique-id → :class:`InterpretationSpec` lookup.

Specs self-register by calling :func:`register` at import time. The
:func:`get_spec` function is the canonical lookup and returns ``None``
for unregistered techniques (the builder's placeholder-fallback path).

This batch (Prompt A) registers exactly one spec: ``adf_test``. Prompts
B and C will add the other 66 via their own ``specs/*.py`` files,
each importing and calling ``register(...)`` at module load.
"""

from typing import Dict, Optional

from interpretation.builder import InterpretationSpec


_REGISTRY: Dict[str, InterpretationSpec] = {}


def register(spec: InterpretationSpec) -> None:
    """Register a spec under its ``technique_id``.

    Duplicate registration is a programmer error — it silently clobbers
    the earlier entry, which would make the user-visible voice
    non-deterministic across imports. Raise so the test suite catches
    it immediately.
    """
    if spec.technique_id in _REGISTRY:
        raise ValueError(
            f"InterpretationSpec for '{spec.technique_id}' is already "
            f"registered. Each technique must have exactly one spec."
        )
    _REGISTRY[spec.technique_id] = spec


def get_spec(technique_id: str) -> Optional[InterpretationSpec]:
    """Return the registered spec, or ``None`` if not registered."""
    return _REGISTRY.get(str(technique_id))


def list_registered() -> list:
    """Return a sorted list of registered technique ids. For tooling."""
    return sorted(_REGISTRY.keys())


# Import specs here so they self-register. Order-insensitive.
# Prompt A + B (8 specs):
from interpretation.specs import adf_test as _adf                      # noqa: F401, E402
from interpretation.specs import granger_causality as _granger         # noqa: F401, E402
from interpretation.specs import rolling_ccf_lag as _rolling_ccf       # noqa: F401, E402
from interpretation.specs import vecm_model as _vecm                   # noqa: F401, E402
from interpretation.specs import var_model as _var                     # noqa: F401, E402
from interpretation.specs import garch_model as _garch                 # noqa: F401, E402
from interpretation.specs import markov_switching as _markov           # noqa: F401, E402
from interpretation.specs import pca_analysis as _pca                  # noqa: F401, E402

# Prompt C1 (26 specs):
# Decomposition (4)
from interpretation.specs import classical_decompose as _classical_decompose          # noqa: F401, E402
from interpretation.specs import stl_decompose as _stl_decompose                      # noqa: F401, E402
from interpretation.specs import mstl_decompose as _mstl_decompose                    # noqa: F401, E402
from interpretation.specs import x13_seasonal_adjust as _x13_seasonal_adjust          # noqa: F401, E402
# Missing Data (3)
from interpretation.specs import denton_chowlin_disaggregation as _denton_chowlin     # noqa: F401, E402
from interpretation.specs import kalman_imputation as _kalman_imputation              # noqa: F401, E402
from interpretation.specs import loess_interpolation as _loess_interpolation          # noqa: F401, E402
# Change Points / Anomalies (5)
from interpretation.specs import bocpd as _bocpd                                      # noqa: F401, E402
from interpretation.specs import cusum_page_hinkley as _cusum_ph                      # noqa: F401, E402
from interpretation.specs import intervention_analysis as _intervention               # noqa: F401, E402
from interpretation.specs import pelt_change_points as _pelt                          # noqa: F401, E402
from interpretation.specs import stl_esd_anomaly as _stl_esd                          # noqa: F401, E402
# Stationarity standalone (2)
from interpretation.specs import kpss_test as _kpss                                   # noqa: F401, E402
from interpretation.specs import pp_test as _pp                                       # noqa: F401, E402
# Causality remainder (4)
from interpretation.specs import cross_correlation_lag as _ccf_lag                    # noqa: F401, E402
from interpretation.specs import prewhitened_ccf_lag as _prewhitened_ccf              # noqa: F401, E402
from interpretation.specs import dtw_alignment_lag as _dtw                            # noqa: F401, E402
from interpretation.specs import gcc_phat_delay as _gcc_phat                          # noqa: F401, E402
# Regimes remainder (3 — NAR_NARX deferred to C7)
from interpretation.specs import hmm as _hmm                                          # noqa: F401, E402
from interpretation.specs import star_model as _star                                  # noqa: F401, E402
from interpretation.specs import tar_setar as _tar_setar                              # noqa: F401, E402
# Evaluation / Uncertainty (5)
from interpretation.specs import block_bootstrap as _block_bootstrap                  # noqa: F401, E402
from interpretation.specs import conformal_intervals as _conformal                    # noqa: F401, E402
from interpretation.specs import forecast_combination as _fc_combo                    # noqa: F401, E402
from interpretation.specs import robust_estimators as _robust                         # noqa: F401, E402
from interpretation.specs import rolling_origin_cv as _rolling_cv                     # noqa: F401, E402

# Prompt C2 (7 specs, 5 wrappers):
# Forecasting classical — one spec per user-facing technique_id.
from interpretation.specs import arima as _arima_spec                                 # noqa: F401, E402
from interpretation.specs import auto_arima as _auto_arima_spec                       # noqa: F401, E402
from interpretation.specs import ets as _ets_spec                                     # noqa: F401, E402
from interpretation.specs import holt_winters as _holt_winters_spec                   # noqa: F401, E402
from interpretation.specs import theta as _theta_spec                                 # noqa: F401, E402
from interpretation.specs import intermittent_demand as _intermittent_spec            # noqa: F401, E402
from interpretation.specs import prophet as _prophet_spec                             # noqa: F401, E402

# Prompt C3 (4 specs, 4 wrappers):
# State Space family — kalman_filter and kalman_smoother deferred to
# a separate wrapper-creation prompt per Phase 1 topology discovery.
from interpretation.specs import local_level as _local_level_spec                     # noqa: F401, E402
from interpretation.specs import local_linear_trend as _local_linear_trend_spec       # noqa: F401, E402
from interpretation.specs import structural_ts as _structural_ts_spec                 # noqa: F401, E402
from interpretation.specs import particle_filter as _particle_filter_spec             # noqa: F401, E402

# Prompt C4 (7 specs, 7 wrappers):
# Frequency Domain family — 4 distinct Tier 1 shapes across 7 specs.
from interpretation.specs import fft_spectrum as _fft_spectrum_spec                   # noqa: F401, E402
from interpretation.specs import periodogram_spectral_density as _periodogram_spec    # noqa: F401, E402
from interpretation.specs import lomb_scargle as _lomb_scargle_spec                   # noqa: F401, E402
from interpretation.specs import wavelet_transform as _wavelet_transform_spec         # noqa: F401, E402
from interpretation.specs import wavelet_coherence as _wavelet_coherence_spec         # noqa: F401, E402
from interpretation.specs import ssa_model as _ssa_model_spec                         # noqa: F401, E402
from interpretation.specs import emd_hht as _emd_hht_spec                             # noqa: F401, E402
