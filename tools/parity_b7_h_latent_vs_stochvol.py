"""Phase 4.5 reference parity check for Follow-up B7.

Validates that the new h_posterior_mean field (latent log-volatility
posterior mean) agrees with R stochvol::svsample's $latent posterior
mean on the 2b audit fixture.

Tolerance ladder (Q5 + refinement):
  - Pearson corr(TSL h_post_mean, sv $latent mean) > 0.95
    → PASS (assert)
  - Mean-abs-diff(TSL - sv): supplementary diagnostic (reported
    only — priors differ on mu, absolute level shift expected)
  - RMS rel diff: supplementary (reported only)

Failure protocol:
  - Outcome 1 (corr > 0.95): exit 0; report all metrics in stdout.
  - Outcome 2 (0.85 ≤ corr < 0.95): exit 2; caller should re-run
    with --seed 43. If second run also lands in CAVEAT band,
    escalate to Outcome 3.
  - Outcome 3 (corr < 0.85, OR retry stays in CAVEAT): exit 1
    (BLOCK commit pending investigation).

Run after Phase 5 canonicals:
    python tools/parity_b7_h_latent_vs_stochvol.py
    python tools/parity_b7_h_latent_vs_stochvol.py --seed 43
"""

import argparse
import os
import pathlib
import sys
from unittest.mock import patch

# UTF-8 stdout/stderr (cp1252 default on Windows breaks unicode
# arrows in failure-mode descriptions and metric markers).
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT / "engine"))
sys.path.insert(0, str(_ROOT / "tools" / "reference_parity" / "scripts"))

import numpy as np

from techniques.base import RunContext
from techniques import stochastic_volatility as sv_mod
from techniques import _sv_mcmc as sv_mcmc

try:
    from rscript_bridge import rscript_call
except ImportError as exc:
    print(f"Cannot import rscript_bridge: {exc}", file=sys.stderr)
    print("Phase 4.5 requires the Phase 1 verification harness "
          "to be in place under tools/reference_parity/scripts/.",
          file=sys.stderr)
    sys.exit(2)


_FIXTURE_PATH = (
    _ROOT / "tools" / "reference_parity" / "fixtures" / "2b_sv_fixture.npz"
)


# ---------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------

def _load_fixture(seed: int = 42) -> np.ndarray:
    """Load 2b audit fixture (T=500, mu=-10, phi=0.98, sigma_eta=0.2,
    Gaussian innovations). For seed != 42, regenerate from scratch
    using the 2b generator with the new seed."""
    if seed == 42 and _FIXTURE_PATH.exists():
        d = np.load(_FIXTURE_PATH)
        return np.asarray(d["y"], dtype=np.float64)
    rng = np.random.default_rng(seed)
    T, mu, phi, sigma_eta = 500, -10.0, 0.98, 0.2
    h = np.zeros(T)
    h[0] = mu + rng.standard_normal() * sigma_eta / np.sqrt(
        max(1e-12, 1.0 - phi * phi)
    )
    for t in range(1, T):
        h[t] = mu + phi * (h[t - 1] - mu) + sigma_eta * rng.standard_normal()
    return np.exp(h / 2.0) * rng.standard_normal(T)


# ---------------------------------------------------------------------
# TSL via B6 cascade → Gibbs path
# ---------------------------------------------------------------------

def run_tsl_gibbs_h(y: np.ndarray, seed: int) -> np.ndarray:
    """Invoke TSL Gibbs cascade via mocked no-g++ environment;
    return the new h_posterior_mean audit field as a (T,) array.
    Asserts that the cascade actually fired so we know we're
    measuring the Gibbs path (not accidentally NUTS)."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    with patch.object(
        sv_mcmc, "_check_c_compiler_available", return_value=False,
    ):
        ctx = RunContext({
            "run_id": f"parity_b7_seed{seed}",
            "technique_id": "stochastic_volatility",
            "preset": "Balanced",
            "seed": int(seed),
            "frequency": "daily",
            "time": list(range(len(y))),
            "series": [{"name": "y", "values": y.tolist()}],
            "params": {
                "inference_method": "mcmc",
                "mcmc_backend": None,  # auto → cascade to Gibbs
            },
        })
        res = sv_mod.run(ctx, lambda *a, **k: None)
    if res.get("status") != "success":
        raise RuntimeError(
            f"TSL run failed: {res.get('error_message')}"
        )
    a = res.get("audit_fields", {})
    if a.get("mcmc_backend_applied") != "gibbs":
        raise RuntimeError(
            f"Expected backend_applied='gibbs' (B6 cascade); "
            f"got {a.get('mcmc_backend_applied')}"
        )
    if a.get("h_posterior_mean") is None:
        raise RuntimeError(
            "h_posterior_mean is None on the MCMC path — B7 "
            "wiring failure. Check _sv_mcmc_gibbs.fit() return "
            "dict and stochastic_volatility.py audit-field "
            "population."
        )
    return np.asarray(a["h_posterior_mean"], dtype=np.float64)


# ---------------------------------------------------------------------
# R stochvol reference
# ---------------------------------------------------------------------

def run_stochvol_h(y: np.ndarray) -> np.ndarray:
    """Run R stochvol::svsample on the same fixture; extract
    rowMeans(fit$latent) as the per-position posterior mean of h_t.

    fit$latent is a draws-by-T or T-by-draws matrix depending on
    stochvol version; defensively transpose if dims don't match
    length(y)."""
    r_code = r"""
    suppressPackageStartupMessages(library(stochvol))
    y <- as.numeric(read.csv("{{INPUT_y}}", header=FALSE)$V1)
    fit <- svsample(
        y, draws=10000, burnin=1000,
        priormu=c(0, 100),
        priorphi=c(20, 1.5),
        priorsigma=1,
        quiet=TRUE
    )
    latent <- as.matrix(fit$latent)
    if (nrow(latent) != length(y)) {
        latent <- t(latent)
    }
    h_mean <- rowMeans(latent)
    write.csv(
        data.frame(h=h_mean),
        "{{OUTPUT_h}}",
        row.names=FALSE
    )
    """
    out = rscript_call(
        r_code,
        inputs={"y": y.reshape(-1, 1)},
        output_names=["h"],
        timeout_sec=240,
    )
    arr = np.asarray(out["h"]).reshape(-1)
    return arr.astype(np.float64)


# ---------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------

def evaluate_parity(tsl_h: np.ndarray, sv_h: np.ndarray) -> dict:
    """Compute the three metrics: Pearson correlation (PRIMARY,
    asserted), mean absolute difference and RMS relative difference
    (supplementary, reported only)."""
    if len(tsl_h) != len(sv_h):
        raise RuntimeError(
            f"Length mismatch: TSL {len(tsl_h)} vs stochvol {len(sv_h)}"
        )
    # Pearson correlation — central, location-invariant
    a_centered = tsl_h - tsl_h.mean()
    b_centered = sv_h - sv_h.mean()
    denom = (np.sqrt(np.sum(a_centered ** 2))
             * np.sqrt(np.sum(b_centered ** 2)))
    corr = float(np.sum(a_centered * b_centered) / max(denom, 1e-12))
    # Supplementary diagnostics
    mad = float(np.mean(np.abs(tsl_h - sv_h)))
    rms = float(np.sqrt(np.mean((tsl_h - sv_h) ** 2)))
    sv_rms = float(np.sqrt(np.mean(sv_h ** 2)))
    rms_rel = rms / max(sv_rms, 1e-12)
    return {
        "corr": corr,
        "mad": mad,
        "rms": rms,
        "rms_rel": rms_rel,
    }


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main(seed: int = 42) -> int:
    print(f"=== Phase 4.5 latent parity check (B7 Gibbs) ===")
    print(f"    seed={seed}; fixture: 2b audit (T=500, mu=-10, "
          f"phi=0.98, sigma_eta=0.2, Gaussian)")
    print()

    print("[B7.4.5.1] Loading fixture...")
    y = _load_fixture(seed=seed)
    print(f"           T={len(y)}, mean={y.mean():+.5f}, "
          f"std={y.std():.5f}")
    print()

    print("[B7.4.5.2] Running TSL Gibbs (B6 cascade → Gibbs)...")
    tsl_h = run_tsl_gibbs_h(y, seed=seed)
    print(f"           TSL h_post_mean: T={len(tsl_h)}, range "
          f"[{tsl_h.min():+.4f}, {tsl_h.max():+.4f}], "
          f"mean={tsl_h.mean():+.4f}")
    print()

    print("[B7.4.5.3] Running R stochvol::svsample reference...")
    sv_h = run_stochvol_h(y)
    print(f"           stochvol $latent mean: T={len(sv_h)}, "
          f"range [{sv_h.min():+.4f}, {sv_h.max():+.4f}], "
          f"mean={sv_h.mean():+.4f}")
    print()

    print("[B7.4.5.4] Evaluating parity ladder...")
    e = evaluate_parity(tsl_h, sv_h)
    print(f"           Pearson corr: {e['corr']:.4f}  "
          f"(threshold 0.95 PASS / 0.85 BLOCK)")
    print(f"           Mean abs diff: {e['mad']:.4f}  "
          f"(supplementary; absolute-level shift expected from "
          f"prior divergence on mu)")
    print(f"           RMS rel diff:  {e['rms_rel']:.4f}  "
          f"(supplementary)")
    print()

    if e["corr"] >= 0.95:
        print("Phase 4.5: PASS (Outcome 1 — corr > 0.95).")
        print()
        print("Commit-message stub:")
        print(f"  Latent parity vs stochvol $latent: "
              f"Pearson corr={e['corr']:.4f}, "
              f"mean abs diff={e['mad']:.4f}, "
              f"RMS rel diff={e['rms_rel']:.4f}.")
        return 0

    if e["corr"] >= 0.85:
        print("Phase 4.5: CAVEAT (Outcome 2 — corr in [0.85, 0.95)).")
        print()
        print("Re-run protocol: invoke this script once more "
              "with --seed 43 to distinguish MC noise from "
              "systematic divergence.")
        print(f"  python tools/parity_b7_h_latent_vs_stochvol.py "
              f"--seed 43")
        return 2

    print("Phase 4.5: BLOCK (Outcome 3 — corr < 0.85).")
    print()
    print("Three-cause diagnosis order (per Phase 2 plan):")
    print("  1. Welford accumulator bug in TSL — verify via unit "
          "test on synthetic deterministic chains.")
    print("  2. PyMC h-extraction divergence vs Gibbs — compare "
          "both backends on identical fixture.")
    print("  3. stochvol latent-series convention difference — "
          "check row-vs-col, time-orientation, posterior-mean-"
          "of-h vs posterior-mean-of-exp(h/2).")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    sys.exit(main(seed=args.seed))
