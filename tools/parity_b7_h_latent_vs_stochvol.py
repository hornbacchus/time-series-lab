"""DEPRECATED — superseded by harness 2b_mcmc_sv_gaussian check.

This script was the second ad-hoc Phase 4.5 reference
parity check, introduced with Follow-up B7 to validate
the new h_posterior_mean audit field against R
stochvol::svsample's $latent posterior summary on the
2b audit fixture. Phase 2 Session 4 (commit 75aa182)
absorbed equivalent h-correlation coverage into the
parity harness as a diagnostic inside the
2b_mcmc_sv_gaussian check.

Use the harness instead:

    python -m reference_parity --technique 2b_mcmc_sv_gaussian
    python -m reference_parity --tier slow --json

For Student-t SV variant coverage, run:

    python -m reference_parity --technique 2c_mcmc_sv_student_t

The harness check exposes h_posterior_mean Pearson
correlation against the stochvol latent series as an
in-check diagnostic; the original B7 ladder
(corr > 0.95 PASS / 0.85-0.95 CAVEAT / < 0.85 BLOCK)
is preserved via the harness's three-outcome
tolerance vocabulary.

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
        "parity harness's 2b_mcmc_sv_gaussian check\n"
        "(h_posterior_mean diagnostic).\n"
        "\n"
        "Run instead:\n"
        "    python -m reference_parity --technique 2b_mcmc_sv_gaussian\n"
        "\n"
        "For Student-t SV variant:\n"
        "    python -m reference_parity --technique 2c_mcmc_sv_student_t\n"
        "\n"
        "See docs/follow_up_workflow.md for the\n"
        "current Phase 4.5 workflow.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
