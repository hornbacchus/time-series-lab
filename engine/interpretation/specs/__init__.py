"""Technique-specific :class:`InterpretationSpec` definitions.

Each module in this package defines one spec and calls
:func:`engine.interpretation.registry.register` at import time. The
registry module imports all specs in this package so they self-register
on first use of the interpretation layer.
"""
