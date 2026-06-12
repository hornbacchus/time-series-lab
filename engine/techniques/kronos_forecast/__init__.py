"""Kronos Forecast — TSL Bespoke technique #3 (EXPERIMENTAL, unexposed at K1).

Wraps the Kronos financial foundation model (upstream
github.com/shiyu-coder/Kronos @ 67b630e6; model NeoQuasar/Kronos-base @
2b554741; tokenizer @ 0e011738) as an experimental showcase tool. The
evaluation record travels with the tool: out-of-sample evaluation (Jul 2025 -
Jun 2026, KXAF_CLOSEOUT_MEMO.md in the Kronos repo @ 68dcff9) found no
confirmed predictive or distributional value; the tool ships visibly
EXPERIMENTAL by design. One live unconfirmed lead (IEF direction) re-tests
2026-12-01 under a locked protocol (RATES_RERUN_PROTOCOL.md).

Architecture (the Breakeven Payrolls bespoke pattern): workbook-input
(`input_workbook` param -> the kronos_input template sheet), compute via a
SUBPROCESS into the pinned Kronos venv (three incompatible Pythons make
in-process import impossible: TSL packed 3.11.9 / dev 3.14.x / Kronos venv
3.12.10 + torch 2.12.0+cpu) -- pins asserted at run, never silently upgraded.
Close paths ONLY are rendered (the model emits structurally invalid OHLC bars
at material rates; the close channel was the only one validated as always-sane).
"""

from ._dispatch import run

__all__ = ["run"]
