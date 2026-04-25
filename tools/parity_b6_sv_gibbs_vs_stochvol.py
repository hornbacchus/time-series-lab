"""Phase 4.5 reference parity check for Follow-up B6.

Validates that the B6 cascade (g++ probe → auto-downgrade to Gibbs)
does not silently break SV inference quality. Uses the 2b audit
fixture from Phase 1's retrospective audit.

Reference: R `stochvol::svsample` via the existing
`tools/reference_parity/scripts/rscript_bridge.py` utility.

Tolerance ladder (locked in B6 Phase 2 review):
  - mu rel_diff < 5%   → PASS (assert)
  - phi rel_diff < 10% → PASS (assert)
  - sigma_eta record-only (prior-divergence-driven; not bug)
  - ESS > 500 on mu and phi (assert when ess_min_param ∈ {mu, phi})

Failure protocol (Phase 2 plan):
  - Outcome 1 (both PASS): exit 0; report rel_diffs in stdout.
  - Outcome 2 (one of mu/phi exceeds): exit 0 if a re-run with
    seed=43 also passes that one. Caller (Phase 5 driver) is
    responsible for invoking the re-run.
  - Outcome 3 (both exceed, OR re-run fails): exit non-zero;
    blocks commit pending investigation.

This module exposes `main(seed=42)` for re-run-with-different-seed
support per Outcome 2. Default invocation (no args) uses seed=42.

Run after Phase 5 canonicals:
    python tools/parity_b6_sv_gibbs_vs_stochvol.py
    python tools/parity_b6_sv_gibbs_vs_stochvol.py --seed 43
"""

import argparse
import os
import pathlib
import sys
from unittest.mock import patch

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


def _load_2b_fixture(seed: int = 42):
    """Reuse the Phase 1 audit-2b fixture: T=500, mu=-10, phi=0.98,
    sigma_eta=0.2, Gaussian innovations, default seed=42.

    For a re-run-with-different-seed under Outcome 2, regenerate
    the synthetic series from scratch with the new seed (the
    on-disk fixture is the seed=42 baseline)."""
    if seed == 42 and _FIXTURE_PATH.exists():
        data = np.load(_FIXTURE_PATH)
        return np.asarray(data["y"], dtype=np.float64)

    # Regenerate with the requested seed (matches 2b's generator)
    rng = np.random.default_rng(seed)
    T = 500
    mu = -10.0
    phi = 0.98
    sigma_eta = 0.2
    h = np.zeros(T)
    h[0] = mu + rng.standard_normal() * sigma_eta / np.sqrt(
        max(1e-12, 1.0 - phi * phi)
    )
    for t in range(1, T):
        h[t] = mu + phi * (h[t - 1] - mu) + sigma_eta * rng.standard_normal()
    y = np.exp(h / 2.0) * rng.standard_normal(T)
    return y


def run_tsl_gibbs_via_b6_cascade(y: np.ndarray, seed: int) -> dict:
    """Invoke the TSL post-B6 wrapper with simulated no-g++
    environment so the auto-cascade (B6 D10) selects the Gibbs
    backend. Confirms the cascade actually fired before
    extracting posteriors."""
    sv_mcmc._check_c_compiler_available.cache_clear()
    with patch.object(
        sv_mcmc, "_check_c_compiler_available", return_value=False,
    ):
        ctx = RunContext({
            "run_id": f"parity_b6_seed{seed}",
            "technique_id": "stochastic_volatility",
            "preset": "Balanced",  # 2b audit's preset
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
        # Sanity: cascade actually fired (B6 D10 path)
        if a.get("mcmc_backend_applied") != "gibbs":
            raise RuntimeError(
                f"Expected backend_applied='gibbs' (B6 cascade); "
                f"got {a.get('mcmc_backend_applied')}"
            )
        if a.get("mcmc_backend_fallback_reason") != "c_compiler_unavailable":
            raise RuntimeError(
                f"Expected fallback_reason='c_compiler_unavailable'; "
                f"got {a.get('mcmc_backend_fallback_reason')}"
            )
        return {
            "mu": a["mu_posterior_mean"],
            "phi": a["phi_posterior_mean"],
            "sigma_eta": a["sigma_eta_posterior_mean"],
            "ess_min": a["ess_min"],
            "ess_min_param": a["ess_min_param"],
        }


def run_stochvol_reference(y: np.ndarray) -> dict:
    """R stochvol::svsample reference (10000 draws, 1000 burn).

    Priors aligned with 2b audit:
      priormu = c(0, 100), priorphi = c(20, 1.5), priorsigma = 1.
    """
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
    para <- fit$para[[1]]  # first chain (default 1 chain)
    means <- data.frame(
        mu        = mean(para[, "mu"]),
        phi       = mean(para[, "phi"]),
        sigma_eta = mean(para[, "sigma"])
    )
    write.csv(means, "{{OUTPUT_means}}", row.names=FALSE)
    """
    out = rscript_call(
        r_code,
        inputs={"y": y.reshape(-1, 1)},
        output_names=["means"],
        timeout_sec=180,
    )
    means = out["means"]
    # Defensive: rscript_bridge may parse the header row or not
    # depending on whether there are NA cells; row count should
    # be 1, columns mu/phi/sigma_eta.
    arr = np.asarray(means)
    if arr.ndim == 1:
        arr = arr.reshape(1, -1)
    if arr.shape[0] >= 2 and arr.shape[1] == 3:
        # Header row included; take the data row
        arr = arr[-1:, :]
    return {
        "mu":        float(arr[0, 0]),
        "phi":       float(arr[0, 1]),
        "sigma_eta": float(arr[0, 2]),
    }


def evaluate_parity(tsl: dict, sv: dict) -> dict:
    """Compute relative differences and apply the Q6 tolerance
    ladder. Returns a dict with the diffs and per-check pass/
    fail booleans."""
    def _rel(a, b):
        denom = max(abs(a), abs(b), 1e-12)
        return abs(a - b) / denom

    mu_rel = _rel(tsl["mu"], sv["mu"])
    phi_rel = _rel(tsl["phi"], sv["phi"])
    sig_rel = _rel(tsl["sigma_eta"], sv["sigma_eta"])
    return {
        "mu_rel": mu_rel,
        "phi_rel": phi_rel,
        "sigma_eta_rel": sig_rel,
        "mu_pass": mu_rel < 0.05,
        "phi_pass": phi_rel < 0.10,
        # ESS only fails if ess_min_param is mu OR phi
        "ess_pass": (
            tsl["ess_min"] is None
            or float(tsl["ess_min"]) >= 500
            or tsl["ess_min_param"] not in ("mu", "phi")
        ),
    }


def main(seed: int = 42) -> int:
    print(f"=== Phase 4.5 reference parity check (B6 Gibbs cascade) ===")
    print(f"    seed={seed}; fixture: 2b audit (T=500, mu=-10, "
          f"phi=0.98, sigma_eta=0.2, Gaussian)")
    print()

    print("[B6.4.5.1] Loading fixture...")
    y = _load_2b_fixture(seed=seed)
    print(f"           T={len(y)}, mean={y.mean():+.5f}, "
          f"std={y.std():.5f}")
    print()

    print("[B6.4.5.2] Running TSL with mocked no-g++ (forces "
          "B6 cascade → Gibbs)...")
    tsl = run_tsl_gibbs_via_b6_cascade(y, seed=seed)
    print(f"           TSL Gibbs: mu={tsl['mu']:+.4f}, "
          f"phi={tsl['phi']:.4f}, sigma_eta={tsl['sigma_eta']:.4f}")
    print(f"           ESS_min={tsl['ess_min']} on {tsl['ess_min_param']}")
    print()

    print("[B6.4.5.3] Running R stochvol::svsample reference...")
    sv = run_stochvol_reference(y)
    print(f"           stochvol: mu={sv['mu']:+.4f}, "
          f"phi={sv['phi']:.4f}, sigma_eta={sv['sigma_eta']:.4f}")
    print()

    print("[B6.4.5.4] Evaluating parity ladder...")
    eval_ = evaluate_parity(tsl, sv)
    print(f"           mu rel_diff       = {eval_['mu_rel']:.4f}  "
          f"(threshold 5%)   → {'PASS' if eval_['mu_pass'] else 'FAIL'}")
    print(f"           phi rel_diff      = {eval_['phi_rel']:.4f}  "
          f"(threshold 10%)  → {'PASS' if eval_['phi_pass'] else 'FAIL'}")
    print(f"           sigma_eta rel_diff= {eval_['sigma_eta_rel']:.4f}  "
          f"(record-only, prior-driven)")
    print(f"           ESS check         → "
          f"{'PASS' if eval_['ess_pass'] else 'FAIL'}")
    print()

    failures = []
    if not eval_["mu_pass"]:
        failures.append(
            f"mu rel_diff = {eval_['mu_rel']:.4f} >= 5% threshold"
        )
    if not eval_["phi_pass"]:
        failures.append(
            f"phi rel_diff = {eval_['phi_rel']:.4f} >= 10% threshold"
        )
    if not eval_["ess_pass"]:
        failures.append(
            f"ESS_min = {tsl['ess_min']} < 500 on "
            f"{tsl['ess_min_param']}"
        )

    if failures:
        n = sum([not eval_["mu_pass"], not eval_["phi_pass"]])
        # Outcome classification
        if n >= 2:
            outcome = "Outcome 3 — BOTH mu AND phi exceed thresholds"
        elif n == 1:
            outcome = "Outcome 2 — single threshold breach (CAVEAT)"
        else:
            outcome = "Outcome 3 — ESS breach"
        print(f"FAIL ({outcome}):")
        for f in failures:
            print(f"  - {f}")
        if n == 1:
            print()
            print("Re-run protocol: per Phase 4.5 failure protocol, "
                  "the runner should invoke this script once more "
                  "with --seed 43 to distinguish MC noise from "
                  "systematic divergence.")
        return 1

    print("Phase 4.5: PASS (Outcome 1 — both thresholds clear).")
    print()
    print(f"Commit-message stub:")
    print(f"  Reference parity vs stochvol Gibbs: "
          f"mu rel_diff {eval_['mu_rel']*100:.2f}%, "
          f"phi rel_diff {eval_['phi_rel']*100:.2f}%, "
          f"sigma_eta record-only.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    sys.exit(main(seed=args.seed))
