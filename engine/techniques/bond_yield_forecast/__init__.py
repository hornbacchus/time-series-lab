"""Bond Yield Forecast — Large Bayesian VAR with stochastic volatility for
U.S. Treasury yield forecasting, conditioned on economist projections.

Migrated from the standalone ``bvar-yield-forecaster`` repo at the
``v1.0.0-session-0-complete`` tag (Bond Yield Forecast Session 1).
The standalone repo retires post-Session-6 integration closeout.

The TSL technique entry point ``run(ctx, progress_callback)`` lives at
``engine/techniques/bond_yield_forecast.py`` (Session 2 scope); this
subpackage is the implementation.

The existing TSL ``engine/techniques/bvar.py`` is the small Phase 1/2
BVAR IRF/FEVD wrapper (technique_id ``1c_bvar_irf_fevd``) and is
unrelated to this subpackage; the two coexist.
"""

__version__ = "0.1.0"
