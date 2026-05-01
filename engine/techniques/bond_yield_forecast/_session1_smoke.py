"""Bond Yield Forecast Session 1 — post-migration smoke test.

Reproduces the BVAR CLI ``--forecast --scenario baseline`` cycle from
inside the TSL repo, using the migrated subpackage. Output is compared
byte-by-byte against the pre-migration baseline captured at
``bvar-yield-forecaster/output/session1_premigration_baseline/``.

Mirrors ``_legacy_cli.py.archive::main()`` --forecast path (line ~1185)
exactly so npz outputs are byte-identical:
  read_unified_workbook → build_panel(raw=...) → BVARSV.estimate() →
  ConditionalForecaster.forecast() → cf.to_yield_space(pca_dict) →
  save artifacts.

Invoke via ``PYTHONPATH=engine python -m
techniques.bond_yield_forecast._session1_smoke <out_dir>``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import yaml

from techniques.bond_yield_forecast.data import build_panel  # noqa: E402
from techniques.bond_yield_forecast.unified_input import read_unified_workbook  # noqa: E402
from techniques.bond_yield_forecast.estimation import BVARSV  # noqa: E402
from techniques.bond_yield_forecast.priors import MinnesotaPrior  # noqa: E402
from techniques.bond_yield_forecast.conditioning import ConditionalForecaster  # noqa: E402


def main(out_dir: Path) -> None:
    repo_root = Path(__file__).resolve().parent
    fixture = repo_root / "tests" / "fixtures" / "test_input_canonical.xlsx"
    config_path = repo_root / "config" / "default.yaml"

    with config_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    out_dir.mkdir(parents=True, exist_ok=True)

    # Mirror CLI line ~1194: read_unified_workbook for first scenario.
    bundle = read_unified_workbook(fixture, "baseline", config)

    # Mirror CLI line ~1208: build_panel from raw dict.
    panel_bundle = build_panel(
        config,
        raw=bundle["raw"],
        output_dir=out_dir / "data_processed",
    )
    panel = panel_bundle["panel"]
    pca_dict = panel_bundle["pca"]

    # Phase 1: BVAR-SV estimation (mirror lines ~1219-1247).
    variable_names = list(panel.columns)
    hp = config["model"]["hyperparameters"]["fixed"]
    prior = MinnesotaPrior(
        n_vars=len(variable_names),
        n_lags=int(config["model"]["lags"]),
        lambda_1=hp["lambda_1"], lambda_2=hp["lambda_2"],
        lambda_3=hp["lambda_3"], lambda_sc=hp["lambda_sc"],
        lambda_io=hp["lambda_io"],
        persistence_prior=config["model"]["persistence_prior"],
        variable_names=variable_names,
        training_data=panel,
    )
    bvar = BVARSV(
        data=panel,
        n_lags=int(config["model"]["lags"]),
        prior=prior,
        n_draws=int(config["estimation"]["n_draws"]),
        n_burn=int(config["estimation"]["n_burn"]),
        thinning=int(config["estimation"].get("thinning", 1)),
        seed=int(config["estimation"]["seed"]),
    )
    results = bvar.estimate()
    results.save(out_dir / "estimation_results.npz")

    # Phase 2: Conditional forecast on the baseline scenario (mirror lines ~1264-1280).
    scen_dir = out_dir / "baseline"
    scen_dir.mkdir(parents=True, exist_ok=True)
    forecaster = ConditionalForecaster(
        results=results,
        projections=bundle["projections"],
        config_section=config["conditioning"],
        seed=int(config["estimation"]["seed"]),
    )
    cf = forecaster.forecast()
    ycf = cf.to_yield_space(pca_dict)
    cf.save(scen_dir / "conditional_forecast.npz")
    ycf.save(scen_dir / "yield_curve_forecast.npz")

    print(f"Smoke output: {out_dir}")


if __name__ == "__main__":
    out_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("output_session1_postmigration")
    main(out_dir)
