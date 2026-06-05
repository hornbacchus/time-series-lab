"""Net-migration scenario engine.

scenario_breakeven gives the change in monthly breakeven for a migration surprise:

    surprise = scenario_migration - base_migration          (annual persons)
    delta    = surprise * share_16plus * lfpr * (1 - u*) / 12   (persons/month)
             ~= +4,500/mo per +100k of annual net migration.

PORTED from the Breakeven Payrolls repo (826d1d0) VERBATIM except the anchor
fixture path: the standalone repo read repo_root()/tests/fixtures/...; the TSL
port reads the committed copy under this package's resources/ (D5). No math change.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .conventions import LFPR26

logger = logging.getLogger(__name__)

DEFAULT_LFPR = LFPR26 / 100.0  # 0.623954 -- validated; do not round to 0.625

# The committed reconciled reference path (copied from the source repo's
# tests/fixtures/fed_reference_path.csv per D5). The 2026 scenario anchor is read
# from here, read-only.
_ANCHOR_FIXTURE = Path(__file__).resolve().parent / "resources" / "fed_reference_path.csv"


def _as_fraction(x: float | None) -> float | None:
    if x is None:
        return None
    return x / 100.0 if x > 1.5 else x


CENSUS_BASE_MIGRATION = 320000      # the Census V2025 net-migration assumption
CENSUS_BASE_PACE_KMO = 90.0         # 2026 CNI16+ pop flow the Census base pace embeds


def pace(
    scenario_migration: float,
    *,
    base_pace_kmo: float = CENSUS_BASE_PACE_KMO,
    base_migration: float = CENSUS_BASE_MIGRATION,
    share_16plus: float = 0.91,
) -> float:
    """2026 monthly CNI 16+ population flow (k/mo) for a net-migration scenario.

    The Census V2025 base pace (90k/mo) already embeds +320k migration; subtract the
    16+ portion of the immigration surprise. pace(-370000) -> 37.675 k/mo.
    """
    return base_pace_kmo + (float(scenario_migration) - float(base_migration)) * float(share_16plus) / 12000.0


def active_2026_pace(params: dict, *, base_pace_kmo: float = CENSUS_BASE_PACE_KMO) -> float:
    """Resolve the 2026 population flow from params (scenarios.active_2026 preset).

    Falls back to the Census base pace if the active scenario is unset/null.
    """
    sc = params.get("scenarios", {})
    presets = sc.get("presets", {})
    name = sc.get("active_2026", "Brookings_mid")
    m = presets.get(name)
    if m is None:
        return base_pace_kmo
    base_m = presets.get("Census_V2025", CENSUS_BASE_MIGRATION)
    share = sc.get("defaults", {}).get("share_16plus", 0.91)
    return pace(m, base_pace_kmo=base_pace_kmo, base_migration=base_m, share_16plus=share)


def scenario_breakeven(
    base_migration: float,
    scenario_migration: float,
    *,
    lfpr: float = DEFAULT_LFPR,
    u_star: float = 0.044,
    share_16plus: float = 0.91,
    immigrant_lfpr: float | None = None,
) -> dict:
    """Change in monthly breakeven from a net-migration surprise.

    The optional immigrant-LFPR refinement applies a higher participation rate to
    the migration change ONLY; when set, the result flags ``immigrant_lfpr_applied``.
    """
    surprise = float(scenario_migration) - float(base_migration)
    eff_lfpr = _as_fraction(immigrant_lfpr) if immigrant_lfpr is not None else _as_fraction(lfpr)
    u = _as_fraction(u_star)
    delta = surprise * float(share_16plus) * float(eff_lfpr) * (1.0 - float(u)) / 12.0
    return {
        "surprise": surprise,
        "delta_per_month": delta,
        "lfpr_used": eff_lfpr,
        "u_star": u,
        "share_16plus": float(share_16plus),
        "immigrant_lfpr_applied": immigrant_lfpr is not None,
    }


def load_presets(params: dict) -> dict[str, float]:
    """Migration presets from params.yaml; null presets (e.g. MS_house) are skipped."""
    out: dict[str, float] = {}
    for k, v in params.get("scenarios", {}).get("presets", {}).items():
        if v is None:
            logger.info("scenario preset '%s' is null (TBD); skipping", k)
            continue
        out[k] = float(v)
    return out


def reconciled_2026_anchor_kmo(fixture_path: str | Path | None = None) -> float:
    """Active-scenario reconciled 2026 breakeven (k/mo), READ from the committed
    fed_reference_path.csv (the reconciled-pipeline output). Read-only: never recomputes
    or alters the reconciled series. Returns NaN (with a warning) if the fixture is absent.
    """
    p = Path(fixture_path) if fixture_path else _ANCHOR_FIXTURE
    if not p.exists():
        logger.warning("reconciled anchor unavailable: %s not found; absolute breakeven -> NaN", p)
        return float("nan")
    df = pd.read_csv(p)
    period_col = df.columns[0]
    mask = df[period_col].astype(str).str.startswith("2026")
    return float(df.loc[mask, "breakeven_published"].mean()) / 1000.0


def sensitivity_grid(
    params: dict, *, base_preset: str = "Census_V2025", immigrant_lfpr: float | None = None
) -> pd.DataFrame:
    """breakeven delta x {migration preset} x {u* definition} as a tidy frame."""
    presets = load_presets(params)
    if base_preset not in presets:
        raise KeyError(f"base_preset '{base_preset}' not in presets {list(presets)}")
    base = presets[base_preset]
    u_defs = params["unemployment"]["u_star_options"]
    defaults = params["scenarios"]["defaults"]
    lfpr = defaults.get("lfpr", DEFAULT_LFPR)
    share = defaults.get("share_16plus", 0.91)

    # Absolute columns: anchored on the reconciled active-scenario 2026 breakeven (read-only)
    # plus that row's delta vs the ACTIVE scenario -- all via the existing functions.
    active_name = params.get("scenarios", {}).get("active_2026", "Brookings_mid")
    active_migration = presets.get(active_name, base)
    anchor_kmo = reconciled_2026_anchor_kmo()

    rows = []
    for pname, pval in presets.items():
        for uname, uval in u_defs.items():
            r = scenario_breakeven(
                base, pval, lfpr=lfpr, u_star=uval, share_16plus=share, immigrant_lfpr=immigrant_lfpr
            )
            # absolute breakeven (k/mo) = reconciled anchor + delta(active -> this scenario)
            abs_delta = scenario_breakeven(
                active_migration, pval, lfpr=lfpr, u_star=uval, share_16plus=share,
                immigrant_lfpr=immigrant_lfpr,
            )["delta_per_month"]
            rows.append(
                {
                    "preset": pname,
                    "migration": pval,
                    "u_star_def": uname,
                    "u_star": r["u_star"],
                    "delta_per_month": r["delta_per_month"],
                    "immigrant_lfpr_applied": r["immigrant_lfpr_applied"],
                    "pace_kmo": pace(pval, share_16plus=share),
                    "breakeven_kmo": anchor_kmo + abs_delta / 1000.0,
                }
            )
    return pd.DataFrame(rows)
