"""Per-technique parity-check modules.

Each module defines one or more ``ParityCheck`` subclasses with
class attribute ``technique_id`` and ``tier``. The runner
discovers them at import time via ``runner.discover_checks``.
"""

__all__ = []
