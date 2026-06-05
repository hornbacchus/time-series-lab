"""Breakeven Payrolls — TSL Bespoke technique (ported from the Breakeven Payrolls
repo @ 826d1d0). Workbook-input: reads the 12-tab template, runs the ported math,
writes the breakeven path + scenario grid + signal-vs-noise overlay.

The core math modules (conventions, stitch, population, breakeven, scenarios,
potential_gdp, tolerances) are VERBATIM ports of the authoritative source; the
workbook reader + dispatch are the TSL-specific layer.
"""

from ._dispatch import compute, run

__all__ = ["run", "compute"]
