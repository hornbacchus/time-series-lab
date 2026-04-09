using System;
using System.Collections.Generic;
using ExcelDna.Integration;
using Newtonsoft.Json;
using TSL.AddIn.Models;

namespace TSL.AddIn.Functions
{
    /// <summary>
    /// AUTO-lane UDF functions. These recompute with Excel recalculation.
    /// Category prefix: "Time Series Lab – AUTO (recomputes)"
    /// Description prefix: "AUTO:"
    /// Allowed presets: Fast/Balanced only.
    /// </summary>
    public static class AutoFunctions
    {
        [ExcelFunction(
            Name = "TSL_VERSION",
            Category = "Time Series Lab",
            Description = "Returns the Time Series Lab add-in version string.")]
        public static object TSL_VERSION()
        {
            try
            {
                var version = typeof(AutoFunctions).Assembly.GetName().Version;
                return $"Time Series Lab v{version}";
            }
            catch (Exception ex)
            {
                return $"ERROR: {ex.Message}";
            }
        }

        [ExcelFunction(
            Name = "TSL_SEASONAL_ADJUST",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: Decompose a time series and return the seasonally adjusted values. Spills results.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_SEASONAL_ADJUST(
            [ExcelArgument(Name = "time_range", Description = "Range of date values")] object[,] timeRange,
            [ExcelArgument(Name = "value_range", Description = "Range of numeric values")] object[,] valueRange,
            [ExcelArgument(Name = "method", Description = "Method: STL (default), Classical, MSTL")] object method,
            [ExcelArgument(Name = "frequency", Description = "Frequency: Auto (default), BusinessDaily, Weekly, Monthly, etc.")] object frequency,
            [ExcelArgument(Name = "preset", Description = "Preset: Fast or Balanced (default). Use Task Pane for Thorough.")] object preset)
        {
            var methodStr = UdfHelpers.Optional(method, "STL");
            var freqStr = UdfHelpers.Optional(frequency, "Auto");
            var presetStr = ValidateAutoPreset(UdfHelpers.Optional(preset, "Balanced"));
            if (presetStr == null) return ExcelError.ExcelErrorValue;

            var time = UdfHelpers.ExtractTimeStrings(timeRange);
            var values = UdfHelpers.ExtractSingleColumn(valueRange);
            return RunAuto("stl_decompose", presetStr, time,
                new List<SeriesData> { new SeriesData { Name = "Y", Values = values } },
                new Dictionary<string, object> { { "method", methodStr }, { "frequency", freqStr } },
                "seasonally_adjusted");
        }

        [ExcelFunction(
            Name = "TSL_GRANGER",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: Granger causality test. Returns F-statistic, p-value, and decision. Spills results.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_GRANGER(
            [ExcelArgument(Name = "x_range", Description = "Range of potential cause series")] object[,] xRange,
            [ExcelArgument(Name = "y_range", Description = "Range of potential effect series")] object[,] yRange,
            [ExcelArgument(Name = "max_lag", Description = "Maximum lags to test (default 12)")] object maxLag,
            [ExcelArgument(Name = "preset", Description = "Preset: Fast or Balanced (default)")] object preset)
        {
            var maxLagInt = UdfHelpers.OptionalInt(maxLag, 12);
            var presetStr = ValidateAutoPreset(UdfHelpers.Optional(preset, "Balanced"));
            if (presetStr == null) return ExcelError.ExcelErrorValue;

            var xVals = UdfHelpers.ExtractSingleColumn(xRange);
            var yVals = UdfHelpers.ExtractSingleColumn(yRange);
            return RunAuto("granger_causality", presetStr, null,
                new List<SeriesData>
                {
                    new SeriesData { Name = "X", Values = xVals },
                    new SeriesData { Name = "Y", Values = yVals },
                },
                new Dictionary<string, object> { { "max_lag", maxLagInt } },
                "granger_results");
        }

        [ExcelFunction(
            Name = "TSL_LAG_FIND",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: Find the lead-lag relationship between two series. Returns best lag and correlation.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_LAG_FIND(
            [ExcelArgument(Name = "x_range", Description = "Range of first series")] object[,] xRange,
            [ExcelArgument(Name = "y_range", Description = "Range of second series")] object[,] yRange,
            [ExcelArgument(Name = "max_lag", Description = "Maximum lags to search (default 30)")] object maxLag,
            [ExcelArgument(Name = "method", Description = "Method: PrewhitenedCCF (default), RawCCF, GCC_PHAT")] object method)
        {
            var maxLagInt = UdfHelpers.OptionalInt(maxLag, 30);
            var methodStr = UdfHelpers.Optional(method, "PrewhitenedCCF");

            var xVals = UdfHelpers.ExtractSingleColumn(xRange);
            var yVals = UdfHelpers.ExtractSingleColumn(yRange);
            return RunAuto("prewhitened_ccf_lag", "Balanced", null,
                new List<SeriesData>
                {
                    new SeriesData { Name = "X", Values = xVals },
                    new SeriesData { Name = "Y", Values = yVals },
                },
                new Dictionary<string, object> { { "max_lag", maxLagInt }, { "method", methodStr } },
                "lag_results");
        }

        [ExcelFunction(
            Name = "TSL_ADF",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: Augmented Dickey-Fuller stationarity test. Returns test statistic and p-value.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_ADF(
            [ExcelArgument(Name = "value_range", Description = "Range of numeric values")] object[,] valueRange)
        {
            var values = UdfHelpers.ExtractSingleColumn(valueRange);
            return RunAuto("adf_test", "Balanced", null,
                new List<SeriesData> { new SeriesData { Name = "Y", Values = values } },
                new Dictionary<string, object>(), "adf_results");
        }

        [ExcelFunction(
            Name = "TSL_KPSS",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: KPSS stationarity test. Returns test statistic and p-value.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_KPSS(
            [ExcelArgument(Name = "value_range", Description = "Range of numeric values")] object[,] valueRange)
        {
            var values = UdfHelpers.ExtractSingleColumn(valueRange);
            return RunAuto("kpss_test", "Balanced", null,
                new List<SeriesData> { new SeriesData { Name = "Y", Values = values } },
                new Dictionary<string, object>(), "kpss_results");
        }

        [ExcelFunction(
            Name = "TSL_FORECAST",
            Category = "Time Series Lab – AUTO (recomputes)",
            Description = "AUTO: Forecast a time series. Returns forecasted values with prediction intervals. Spills.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_FORECAST(
            [ExcelArgument(Name = "time_range", Description = "Range of date values")] object[,] timeRange,
            [ExcelArgument(Name = "value_range", Description = "Range of numeric values")] object[,] valueRange,
            [ExcelArgument(Name = "horizon", Description = "Number of periods to forecast")] int horizon,
            [ExcelArgument(Name = "preset", Description = "Preset: Fast or Balanced (default)")] object preset,
            [ExcelArgument(Name = "model", Description = "Model: Auto (default), ARIMA, ETS, Theta")] object model)
        {
            var presetStr = ValidateAutoPreset(UdfHelpers.Optional(preset, "Balanced"));
            if (presetStr == null) return ExcelError.ExcelErrorValue;
            var modelStr = UdfHelpers.Optional(model, "Auto");
            var techniqueId = modelStr.ToLowerInvariant() == "auto" ? "auto_arima" : modelStr.ToLowerInvariant();

            var time = UdfHelpers.ExtractTimeStrings(timeRange);
            var values = UdfHelpers.ExtractSingleColumn(valueRange);
            return RunAuto(techniqueId, presetStr, time,
                new List<SeriesData> { new SeriesData { Name = "Y", Values = values } },
                new Dictionary<string, object> { { "horizon", horizon }, { "model", modelStr } },
                "forecasts");
        }

        [ExcelFunction(
            Name = "TSL_TRIGGER",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "Returns the current THOROUGH trigger token. Use in THOROUGH formulas.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_TRIGGER()
        {
            return TriggerManager.GetTriggerValue();
        }

        // ── Helpers ───────────────────────────────────────────

        private static string ValidateAutoPreset(string preset)
        {
            if (string.Equals(preset, "Thorough", StringComparison.OrdinalIgnoreCase))
                return null; // AUTO functions cannot use Thorough
            return preset;
        }

        /// <summary>
        /// Unified AUTO async runner. Builds hash, dispatches to engine, formats result.
        /// </summary>
        private static object RunAuto(string techniqueId, string preset, string[] time,
            List<SeriesData> series, Dictionary<string, object> parms, string resultTable)
        {
            // Build cache hash from all inputs
            var hashInput = $"{techniqueId}|{preset}|{JsonConvert.SerializeObject(parms)}";
            if (time != null)
                foreach (var t in time) hashInput += $"|{t}";
            foreach (var s in series)
                foreach (var v in s.Values) hashInput += $"|{v?.ToString() ?? "NA"}";
            var hash = UdfHelpers.Sha256Short(hashInput);

            return ExcelAsyncUtil.Run(nameof(RunAuto), new object[] { hash }, () =>
            {
                try
                {
                    AddIn.Engine.EnsureRunning();

                    var request = new RunRequest
                    {
                        RunId = $"udf_{Guid.NewGuid():N}",
                        TechniqueId = techniqueId,
                        Preset = preset,
                        Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                        Time = time,
                        Series = series,
                        Params = parms,
                        FillConfig = new FillConfig(),
                    };

                    var response = AddIn.Engine.RunAsync(request).GetAwaiter().GetResult();

                    if (response.Status == "failure")
                        return $"ERROR: {response.ErrorMessage}";

                    return UdfHelpers.FormatTableForSpill(response, resultTable);
                }
                catch (Exception ex)
                {
                    Logger.Error($"AUTO UDF '{techniqueId}' failed.", ex);
                    return $"ERROR: {ex.Message}";
                }
            });
        }
    }
}
