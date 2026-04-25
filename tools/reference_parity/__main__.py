"""Module entry-point so ``python -m reference_parity`` works.

Delegates to ``harness.runner.main``.
"""

import sys

from reference_parity.harness.runner import main


if __name__ == "__main__":
    sys.exit(main())
