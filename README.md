# Time Series Lab

An Excel add-in for time series analysis, built as an Excel-DNA XLL for Excel 365 (Windows, 64-bit).

## Features

- **81 techniques** across 13 categories: decomposition, forecasting, stationarity tests, multivariate analysis, state space models, regime switching, volatility/risk, frequency domain, change points, causality, evaluation, missing data, and ML/deep learning
- **15 worksheet functions (UDFs)** in two lanes: AUTO (live recalculation) and THOROUGH (handle-based, manual recompute)
- **Task Pane UI** with technique explorer, recommender wizard, data readiness scoring, and UDF browser
- **Full audit trail** — every run produces a plain-English summary, diagnostics, and a machine-readable JSON record for reproducibility

## Architecture

Two-process model:

- **Process A** (Excel) — .NET Framework 4.8 add-in with WPF/WinForms UI, ribbon, and UDFs
- **Process B** (Python) — out-of-process engine connected via Windows Named Pipes with a JSON message protocol

## Project Structure

```
src/TSL.AddIn/       C# add-in: ribbon, UDFs, engine client, Excel writer
src/TSL.UI/          WPF MVVM views hosted in WinForms (explorer, run, recommender, etc.)
src/TSL.Installer/   ClickOnce WPF installer with registry auto-load
engine/              Python worker + technique modules
resources/catalog/   Technique and UDF JSON registries
resources/techniques_md/  Technique documentation (markdown)
tools/               Build, packaging, and code generation scripts
```

## Requirements

- Windows 10/11 with Excel 365 (64-bit)
- .NET Framework 4.8
- Visual Studio 2022 (for building)
- Python 3.11 (embedded runtime included in installer)

## Building

```powershell
# Full build + installer package
.\tools\build_pack.ps1

# Solution only (requires VS MSBuild)
msbuild TimeSeriesLab.sln -p:Configuration=Release -p:Platform=x64
```

## Technique Categories

| Category | Count | Examples |
|----------|-------|---------|
| Decomposition | 4 | STL, X-13ARIMA-SEATS, HP Filter |
| Forecasting (Classical) | 8 | Auto ARIMA, ETS, Theta, Prophet |
| Stationarity Tests | 3 | ADF, KPSS, Zivot-Andrews |
| Multivariate | 6 | VAR, VECM, PCA, Dynamic Factor |
| State Space | 6 | Structural TS (UCM), Local Level, Local Linear Trend |
| Regimes / Nonlinear | 5 | Markov Switching, SETAR, HMM |
| Volatility / Risk | 7 | GARCH, EGARCH, Value-at-Risk |
| Frequency Domain | 6 | FFT, Wavelet, Spectral Analysis |
| Change Points / Anomalies | 5 | BOCPD, PELT, Isolation Forest |
| Causality / Lead-Lag | 6 | Granger, Cross-Correlation, DTW |
| Evaluation | 5 | Forecast Reconciliation, Diebold-Mariano |
| Missing Data | 3 | Kalman Imputation, MICE |
| ML / Deep Learning | 7 | LSTM, XGBoost, LightGBM, Random Forest |
