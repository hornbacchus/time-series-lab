"""DEPRECATED — superseded by harness 2b_mcmc_sv_gaussian check.

This script was the first ad-hoc Phase 4.5 reference
parity check, introduced with Follow-up B6 to validate
that the SV wrapper's Gibbs cascade preserves
inference quality vs R stochvol::svsample. Phase 2
Session 4 (commit 75aa182) absorbed equivalent
coverage into the parity harness as the
2b_mcmc_sv_gaussian check, which:

  - Uses the same 2b audit fixture (now harness-
    versioned at fixtures/2b_sv_gaussian.npz).
  - Forces the same Gibbs path via _check_c_compiler_
    available monkey-patch.
  - Uses the same R stochvol::svsample reference (now
    via harness RBridge instead of the deprecated
    rscript_bridge utility).
  - Applies the same three-outcome ladder (mu/phi
    PASS/CAVEAT thresholds + sigma_eta record-only)
    via tolerances.py.
  - Implements the same CAVEAT-reroll protocol
    (runner-managed, replacing manual --seed 43).

Use the harness instead:

    python -m reference_parity --technique 2b_mcmc_sv_gaussian
    python -m reference_parity --tier slow --json

This stub kept (vs deletion) so muscle-memory
invocations get a clear redirect. A future cleanup
commit may delete after migration period.

See:
  - docs/follow_up_workflow.md (Phase 4.5 section)
  - docs/follow_up_check_coverage.md (mapping table)
  - tools/reference_parity/MANIFEST.toml
"""

import sys


def main() -> int:
    print(
        "DEPRECATED: This script is superseded by the\n"
        "parity harness's 2b_mcmc_sv_gaussian check.\n"
        "\n"
        "Run instead:\n"
        "    python -m reference_parity --technique 2b_mcmc_sv_gaussian\n"
        "\n"
        "See docs/follow_up_workflow.md for the\n"
        "current Phase 4.5 workflow.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
