# `engine/techniques/` — developer notes

Each technique wrapper in this directory is a standalone module exposing
a `run(ctx, progress_callback) -> dict` entry point. Dispatch to a wrapper
goes through `engine/techniques/registry.py::TECHNIQUE_REGISTRY`. Shared
plumbing (`RunContext`, `make_table`, `make_response`,
`make_error_response`, `format_significance_disclosure`, etc.) lives in
`engine/techniques/base.py`.

## Cross-wrapper conventions

- **Time-axis ownership.** The wrapper owns alignment between the input
  DatetimeIndex and every output row (§4.1 of the design mandate).
  Statsmodels-returned arrays alternate between `ndarray` and
  `pandas.Series` depending on input type — the wrapper must not rely
  on whatever type statsmodels chose. See `NOTES_statsmodels_params.md`
  for the canonical pattern on parameter-table construction.
- **Significance disclosure.** Every wrapper that emits a statistical
  verdict or test-backed output populates `test_name`,
  `critical_value_formula`, and `ac_corrected` in `audit_fields`, via
  the `format_significance_disclosure(...)` helper. Enforced by
  `engine/tests/test_identification_conventions.py::
  TestSignificanceDisclosureConvention`.
- **Parameters-table naming.** Wrappers that surface a fit's estimated
  coefficients use `"Estimated Parameters"` as the table name. Enforced
  by test fixtures that substring-match on that literal.
- **Forecast-table time column.** Wrappers that extend beyond the input
  series use `"Time"` as the first-column header, populated with date
  strings produced by extending the input DatetimeIndex at the detected
  frequency (not integer step numbers). See the
  `_build_forecast_time_axis` helper pattern in `structural_ts.py`.

## Internal notes

| File | Scope |
|---|---|
| [`NOTES_statsmodels_params.md`](./NOTES_statsmodels_params.md) | Canonical pattern for iterating `statsmodels` fit `params` / `bse` / `pvalues` across ndarray-vs-Series alternation. Required reading before writing any new statsmodels-backed wrapper (ARIMA family, state-space, VAR/VECM, Markov-switching, GARCH, etc.). |

When adding a new cross-wrapper convention or lessons-learned note,
drop a new `NOTES_*.md` in this directory and add a row to the table
above so future authors encounter it when exploring
`engine/techniques/`.
