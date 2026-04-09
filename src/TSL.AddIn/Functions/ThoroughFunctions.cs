using System;
using System.Collections.Generic;
using System.Text;
using ExcelDna.Integration;
using Newtonsoft.Json;
using TSL.AddIn.Models;

namespace TSL.AddIn.Functions
{
    /// <summary>
    /// THOROUGH-lane UDF functions. Handle-based, manual recompute via trigger.
    /// Category: "Time Series Lab – THOROUGH (manual handles)"
    /// Description prefix: "THOROUGH:"
    /// </summary>
    public static class ThoroughFunctions
    {
        [ExcelFunction(
            Name = "TSL_RUN_THR",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Run any technique manually. Returns a handle string (TSL.THR.*). Recomputes only when trigger changes. Use data_range_2..5 for non-adjacent columns.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_RUN_THR(
            [ExcelArgument(Name = "technique_id", Description = "Technique ID from catalog (e.g., 'auto_arima')")] string techniqueId,
            [ExcelArgument(Name = "time_range", Description = "Range of date values")] object[,] timeRange,
            [ExcelArgument(Name = "data_range", Description = "Range of data values (single or multi-column)")] object[,] dataRange,
            [ExcelArgument(Name = "trigger", Description = "REQUIRED: Use TSL_TRIGGER() to control manual recompute")] int trigger,
            [ExcelArgument(Name = "options_json", Description = "Optional JSON string of parameters")] object optionsJson,
            [ExcelArgument(Name = "data_range_2", Description = "Optional: additional non-adjacent data columns")] object dataRange2,
            [ExcelArgument(Name = "data_range_3", Description = "Optional: additional non-adjacent data columns")] object dataRange3,
            [ExcelArgument(Name = "data_range_4", Description = "Optional: additional non-adjacent data columns")] object dataRange4,
            [ExcelArgument(Name = "data_range_5", Description = "Optional: additional non-adjacent data columns")] object dataRange5)
        {
            var optStr = UdfHelpers.IsMissing(optionsJson) ? "{}" : optionsJson.ToString();
            var extraRanges = UdfHelpers.CollectExtraRanges(dataRange2, dataRange3, dataRange4, dataRange5);

            // Build data hash for caching (include extra ranges)
            var dataHash = UdfHelpers.HashTimeAndData(timeRange, dataRange);
            if (extraRanges.Count > 0)
            {
                var hashBuilder = new StringBuilder(dataHash);
                foreach (var extra in extraRanges)
                    hashBuilder.Append('|').Append(UdfHelpers.HashRange(extra));
                dataHash = hashBuilder.ToString();
            }

            var handle = ResultStore.GenerateHandle(techniqueId, "Thorough", optStr, dataHash, trigger);

            // Check if result already cached
            var wbName = UdfHelpers.GetWorkbookName();
            var existing = AddIn.Results.Get(wbName, handle);
            if (existing != null) return handle;

            // Run async
            return ExcelAsyncUtil.Run(nameof(TSL_RUN_THR), new object[] { handle }, () =>
            {
                try
                {
                    var time = UdfHelpers.ExtractTimeStrings(timeRange);
                    var series = UdfHelpers.ExtractSeriesFromMatrix(dataRange);

                    foreach (var extra in extraRanges)
                        series.AddRange(UdfHelpers.ExtractSeriesFromMatrix(extra));

                    // Renumber series globally to avoid duplicate names
                    if (extraRanges.Count > 0)
                    {
                        for (int s = 0; s < series.Count; s++)
                            series[s].Name = $"Series_{s + 1}";
                    }

                    var parms = new Dictionary<string, object>();
                    if (!string.IsNullOrEmpty(optStr) && optStr != "{}")
                    {
                        parms = JsonConvert.DeserializeObject<Dictionary<string, object>>(optStr)
                                ?? new Dictionary<string, object>();
                    }

                    var request = new RunRequest
                    {
                        RunId = $"thr_{Guid.NewGuid():N}",
                        TechniqueId = techniqueId,
                        Preset = "Thorough",
                        Seed = AddIn.Settings?.GetDefaultSeed() ?? 42,
                        Time = time,
                        Series = series,
                        Params = parms,
                        FillConfig = new FillConfig(),
                    };

                    var response = AddIn.Engine.RunAsync(request).GetAwaiter().GetResult();
                    AddIn.Results.Store(wbName, handle, response);

                    return handle;
                }
                catch (Exception ex)
                {
                    Logger.Error("THOROUGH run failed.", ex);
                    return $"ERROR: {ex.Message}";
                }
            });
        }

        [ExcelFunction(
            Name = "TSL_FORECAST_THR",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Forecast with full model search. Returns a handle. Use TSL_TABLE() to extract results.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_FORECAST_THR(
            [ExcelArgument(Name = "time_range", Description = "Range of date values")] object[,] timeRange,
            [ExcelArgument(Name = "value_range", Description = "Range of numeric values")] object[,] valueRange,
            [ExcelArgument(Name = "horizon", Description = "Forecast horizon (periods)")] int horizon,
            [ExcelArgument(Name = "trigger", Description = "REQUIRED: Use TSL_TRIGGER()")] int trigger,
            [ExcelArgument(Name = "model", Description = "Model: Auto (default)")] object model)
        {
            var modelStr = UdfHelpers.IsMissing(model) ? "Auto" : model.ToString();
            var opts = JsonConvert.SerializeObject(new { horizon, model = modelStr });
            return TSL_RUN_THR("auto_arima", timeRange, valueRange, trigger, opts,
                ExcelMissing.Value, ExcelMissing.Value, ExcelMissing.Value, ExcelMissing.Value);
        }

        // ── Accessor functions ──────────────────────────────────────────

        [ExcelFunction(
            Name = "TSL_TABLE",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Extract a named table from a handle result. Spills.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_TABLE(
            [ExcelArgument(Name = "handle", Description = "Handle from TSL_RUN_THR or TSL_FORECAST_THR")] string handle,
            [ExcelArgument(Name = "table_name", Description = "Name of the output table to extract")] string tableName)
        {
            var wbName = UdfHelpers.GetWorkbookName();
            var response = AddIn.Results.Get(wbName, handle);
            if (response == null) return "MISSING (Click Re-run Thorough)";
            return UdfHelpers.FormatTableForSpill(response, tableName);
        }

        [ExcelFunction(
            Name = "TSL_VALUE",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Extract a single value from a handle result's artifacts.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_VALUE(
            [ExcelArgument(Name = "handle", Description = "Handle string")] string handle,
            [ExcelArgument(Name = "key", Description = "Artifact key")] string key)
        {
            var wbName = UdfHelpers.GetWorkbookName();
            var val = AddIn.Results.GetValue(wbName, handle, key);
            if (val == null) return "MISSING";
            if (val is Newtonsoft.Json.Linq.JValue jv) return jv.Value;
            return val;
        }

        [ExcelFunction(
            Name = "TSL_STATUS",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Check status of a handle. Returns OK/STALE/MISSING/ERROR with timestamp.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_STATUS(
            [ExcelArgument(Name = "handle", Description = "Handle string")] string handle)
        {
            if (string.IsNullOrEmpty(handle) || !handle.StartsWith("TSL.THR."))
                return "INVALID HANDLE";
            return AddIn.Results.GetStatus(UdfHelpers.GetWorkbookName(), handle);
        }

        [ExcelFunction(
            Name = "TSL_WARNINGS",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Get warnings from a handle result. Spills vertically.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_WARNINGS(
            [ExcelArgument(Name = "handle", Description = "Handle string")] string handle)
        {
            var response = AddIn.Results.Get(UdfHelpers.GetWorkbookName(), handle);
            if (response == null) return "MISSING";
            if (response.Warnings == null || response.Warnings.Count == 0)
                return "No warnings.";

            var result = new object[response.Warnings.Count, 1];
            for (int i = 0; i < response.Warnings.Count; i++)
                result[i, 0] = response.Warnings[i];
            return result;
        }

        [ExcelFunction(
            Name = "TSL_RUNINFO",
            Category = "Time Series Lab – THOROUGH (manual handles)",
            Description = "THOROUGH: Get run metadata from a handle (technique, preset, seed, versions). Spills.",
            HelpTopic = "TimeSeriesLab_UserGuide")]
        public static object TSL_RUNINFO(
            [ExcelArgument(Name = "handle", Description = "Handle string")] string handle)
        {
            var response = AddIn.Results.Get(UdfHelpers.GetWorkbookName(), handle);
            if (response == null) return "MISSING";

            var info = new List<string[]>
            {
                new[] { "Status", response.Status },
                new[] { "Run ID", response.RunId ?? "?" },
            };

            if (response.EngineVersions != null)
            {
                info.Add(new[] { "Engine Version", response.EngineVersions.EngineVersion ?? "?" });
                info.Add(new[] { "Python Version", response.EngineVersions.PythonVersion ?? "?" });
            }

            if (response.AuditFields != null && response.AuditFields.ContainsKey("seed"))
                info.Add(new[] { "Seed", response.AuditFields["seed"].ToString() });

            var result = new object[info.Count, 2];
            for (int i = 0; i < info.Count; i++)
            {
                result[i, 0] = info[i][0];
                result[i, 1] = info[i][1];
            }
            return result;
        }
    }
}
