"""Bond Yield Forecast — Large Bayesian VAR with stochastic volatility for
U.S. Treasury yield forecasting, conditioned on economist projections.

Migrated from the standalone ``bvar-yield-forecaster`` repo at the
``v1.0.0-session-0-complete`` tag (Bond Yield Forecast Session 1).
The standalone repo retires post-Session-6 integration closeout.

The TSL technique dispatch entry point ``run(ctx, progress_callback)``
is implemented in ``_dispatch.py`` and re-exported here. The integration
plan §2.1 originally specified a sibling file
``engine/techniques/bond_yield_forecast.py`` for dispatch, but Python's
import system cannot resolve a module-name collision between a file
and a same-named package directory: ``importlib.import_module(
"techniques.bond_yield_forecast")`` always resolves to the package.
Implementing the dispatch as ``_dispatch.py`` and re-exporting from
``__init__.py`` produces the same effective contract — the registry
maps ``"bond_yield_forecast" -> "techniques.bond_yield_forecast"`` and
``mod.run`` resolves via this re-export.

The existing TSL ``engine/techniques/bvar.py`` is the small Phase 1/2
BVAR IRF/FEVD wrapper (technique_id ``1c_bvar_irf_fevd``) and is
unrelated to this subpackage; the two coexist.
"""

__version__ = "0.1.0"

# Re-export the dispatch entry point so engine_worker's registry-based
# `mod = importlib.import_module(module_path); mod.run(ctx, cb)` resolves
# correctly when module_path == "techniques.bond_yield_forecast".
from ._dispatch import run  # noqa: F401
