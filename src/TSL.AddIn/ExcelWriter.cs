using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using ExcelDna.Integration;
using Microsoft.Office.Interop.Excel;
using Newtonsoft.Json;
using TSL.AddIn.Models;

namespace TSL.AddIn
{
    /// <summary>
    /// Writes run results to Excel: results sheet, audit sheet, and embedded JSON run record.
    /// </summary>
    public class ExcelWriter
    {
        private const string RunsSheetName = "_TSL_RUNS";

        /// <summary>Helper: typed Range from Cells indexer (COM returns object).</summary>
        private static Range C(Worksheet ws, int row, int col) => (Range)ws.Cells[row, col];

        /// <summary>
        /// Write a complete run result to the active workbook.
        /// Creates: results sheet, audit sheet, and embedded JSON record.
        /// </summary>
        public static WriteResult WriteRunResult(RunRequest request, RunResponse response)
        {
            var writeResult = new WriteResult();

            try
            {
                var app = (Application)ExcelDnaUtil.Application;
                var wb = app.ActiveWorkbook;
                if (wb == null)
                {
                    writeResult.ErrorMessage = "No active workbook.";
                    return writeResult;
                }

                app.ScreenUpdating = false;

                // Capture the sheet the user was on when they kicked off the
                // run. The results and audit sheets are inserted immediately
                // BEFORE this sheet so they land near the source data in the
                // tab strip (instead of being pushed to the far right at the
                // end of a long workbook). If the active sheet can't be
                // resolved, fall back to appending at the end.
                Worksheet sourceSheet = null;
                try { sourceSheet = app.ActiveSheet as Worksheet; }
                catch (Exception sheetEx)
                {
                    Logger.Info($"Could not resolve source sheet for insertion: {sheetEx.Message}");
                }

                try
                {
                    // Order matters: insert Audit FIRST (Before source), then
                    // Results FIRST (Before source). This leaves the tab
                    // strip as: ... | Results | Audit | Source | ...
                    writeResult.AuditSheetName = WriteAuditSheet(wb, request, response, sourceSheet);
                    writeResult.ResultSheetName = WriteResultsSheet(wb, request, response, sourceSheet);

                    // 3) Embedded JSON
                    EmbedJsonRunRecord(wb, request, response);

                    // 4) Activate the Results sheet so the user lands on the
                    // tables, not on the Audit sheet (which is the last one
                    // created and would otherwise become active by default).
                    if (!string.IsNullOrEmpty(writeResult.ResultSheetName))
                    {
                        try
                        {
                            var resultsSheet = (Worksheet)wb.Worksheets[writeResult.ResultSheetName];
                            resultsSheet.Activate();
                            // Park the cursor at A1 so the user sees the
                            // Summary block first when the sheet opens.
                            ((Range)resultsSheet.Cells[1, 1]).Select();
                        }
                        catch (Exception activateEx)
                        {
                            Logger.Info($"Could not activate results sheet: {activateEx.Message}");
                        }
                    }

                    writeResult.Success = true;
                }
                finally
                {
                    app.ScreenUpdating = true;
                }
            }
            catch (Exception ex)
            {
                writeResult.ErrorMessage = $"Failed to write results: {ex.Message}";
                Logger.Error("ExcelWriter.WriteRunResult failed.", ex);
            }

            return writeResult;
        }

        private static string WriteResultsSheet(Workbook wb, RunRequest request, RunResponse response,
            Worksheet sourceSheet = null)
        {
            var techShortName = GetTechniqueShortName(request.TechniqueId);
            var sheetName = MakeUniqueSheetName(wb, TruncateSheetName($"{techShortName} Results"));

            Worksheet ws;
            if (sourceSheet != null)
                ws = (Worksheet)wb.Worksheets.Add(Before: sourceSheet);
            else
                ws = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
            ws.Name = sheetName;

            int row = 1;

            // 1) Plain English Summary
            C(ws, row, 1).Value2 = "Summary";
            C(ws, row, 1).Font.Bold = true;
            C(ws, row, 1).Font.Size = 14;
            row++;

            C(ws, row, 1).Value2 = response.PlainEnglishSummary ?? "(No summary available)";
            ws.Range[C(ws, row, 1), C(ws, row, 6)].Merge();
            C(ws, row, 1).WrapText = true;
            row += 2;

            // 2) Warnings
            if (response.Warnings != null && response.Warnings.Count > 0)
            {
                C(ws, row, 1).Value2 = "Warnings";
                C(ws, row, 1).Font.Bold = true;
                C(ws, row, 1).Font.Color = 255; // Red
                row++;
                foreach (var warning in response.Warnings)
                {
                    C(ws, row, 1).Value2 = $"  - {warning}";
                    C(ws, row, 1).Font.Color = 255;
                    row++;
                }
                row++;
            }

            // 3) Diagnostics block
            if (response.AuditFields != null && response.AuditFields.ContainsKey("diagnostics"))
            {
                C(ws, row, 1).Value2 = "Diagnostics";
                C(ws, row, 1).Font.Bold = true;
                row++;

                var diag = response.AuditFields["diagnostics"];
                if (diag is Newtonsoft.Json.Linq.JObject diagObj)
                {
                    foreach (var prop in diagObj)
                    {
                        C(ws, row, 1).Value2 = prop.Key;
                        C(ws, row, 2).Value2 = prop.Value?.ToString();
                        row++;
                    }
                }
                row++;
            }

            // 4) Output tables. Capture input NumberFormat once so we can
            // apply it to the numeric columns of every time-series table
            // (raw series, Seasonally Adjusted, Trend, Seasonal, Irregular
            // etc. all share the source's units and therefore format).
            string seriesFormat = null;
            string timeFormat = null;
            var primarySeriesName = "";
            if (request?.Series != null && request.Series.Count > 0)
            {
                seriesFormat = request.Series[0].NumberFormat;
                timeFormat = request.Series[0].TimeNumberFormat;
                primarySeriesName = request.Series[0].Name ?? "";
            }

            foreach (var table in response.Tables)
            {
                C(ws, row, 1).Value2 = table.Name;
                C(ws, row, 1).Font.Bold = true;
                C(ws, row, 1).Font.Size = 12;
                row++;

                int headerRow = row;

                // Headers
                for (int c = 0; c < table.Columns.Length; c++)
                {
                    C(ws, row, c + 1).Value2 = table.Columns[c];
                    C(ws, row, c + 1).Font.Bold = true;
                    C(ws, row, c + 1).Interior.Color = 0xD9E1F2; // Light blue
                }
                row++;

                int firstDataRow = row;

                // Data rows
                if (table.Rows != null)
                {
                    foreach (var dataRow in table.Rows)
                    {
                        for (int c = 0; c < dataRow.Length && c < table.Columns.Length; c++)
                        {
                            C(ws, row, c + 1).Value2 = dataRow[c];
                        }
                        row++;
                    }
                }
                int lastDataRow = row - 1;

                // Apply NumberFormat to the body of each column, based on
                // column name + captured source formats. "Time" / "Date" /
                // "Timestamp" columns get the source time format. Columns
                // whose name matches the input series OR is one of the
                // standard decomposition components get the source series
                // format. Everything else (ratios, lags, coefficients) is
                // left at Excel's default — they do not share the source
                // series' units.
                if (lastDataRow >= firstDataRow)
                {
                    var sharedUnitsColumns = new HashSet<string>(
                        new[] {
                            primarySeriesName, "Seasonally Adjusted", "Trend",
                            "Seasonal", "Irregular", "Fitted", "Forecast",
                            "Level", "Lower", "Upper", "Residual",
                        },
                        StringComparer.OrdinalIgnoreCase);
                    sharedUnitsColumns.Remove(""); // just in case name is blank

                    for (int c = 0; c < table.Columns.Length; c++)
                    {
                        var colName = (table.Columns[c] ?? "").Trim();
                        var bodyRange = ws.Range[C(ws, firstDataRow, c + 1),
                                                 C(ws, lastDataRow, c + 1)];
                        try
                        {
                            bool isTime = string.Equals(colName, "Time", StringComparison.OrdinalIgnoreCase)
                                       || string.Equals(colName, "Date", StringComparison.OrdinalIgnoreCase)
                                       || string.Equals(colName, "Timestamp", StringComparison.OrdinalIgnoreCase);
                            if (isTime && !string.IsNullOrEmpty(timeFormat))
                                bodyRange.NumberFormat = timeFormat;
                            else if (sharedUnitsColumns.Contains(colName)
                                     && !string.IsNullOrEmpty(seriesFormat))
                                bodyRange.NumberFormat = seriesFormat;
                        }
                        catch { /* best-effort formatting */ }
                    }
                }
                row++;
            }

            // 5) Charting Suggestions
            if (!string.IsNullOrEmpty(response.ChartingSuggestions))
            {
                C(ws, row, 1).Value2 = "Charting Suggestions";
                C(ws, row, 1).Font.Bold = true;
                row++;
                C(ws, row, 1).Value2 = response.ChartingSuggestions;
                ws.Range[C(ws, row, 1), C(ws, row, 6)].Merge();
                C(ws, row, 1).WrapText = true;
            }

            // Auto-fit columns, then cap width. Columns.AutoFit() on a sheet
            // that contains merged cells (our Summary / Charting Suggestions
            // rows span A:F) will widen column A to fit the entire merged
            // text — producing a single gigantic column that hides the data
            // table columns offscreen. Cap each used column at a sensible
            // maximum so the table stays readable. Excel column-width units
            // are ~ the width of one "0" character in the default font.
            ws.Columns.AutoFit();
            const double maxWidth = 22.0;
            for (int c = 1; c <= 8; c++)
            {
                var col = (Range)ws.Columns[c];
                try
                {
                    // ColumnWidth can be DBNull after AutoFit on a merged
                    // range; guard with a default of 10.
                    double w = col.ColumnWidth is double d ? d : 10.0;
                    if (w > maxWidth) col.ColumnWidth = maxWidth;
                }
                catch { /* best-effort */ }
            }

            return sheetName;
        }

        private static string WriteAuditSheet(Workbook wb, RunRequest request, RunResponse response,
            Worksheet sourceSheet = null)
        {
            var techShortName = GetTechniqueShortName(request.TechniqueId);
            var sheetName = MakeUniqueSheetName(wb, TruncateSheetName($"{techShortName} Audit"));
            Worksheet ws;
            if (sourceSheet != null)
                ws = (Worksheet)wb.Worksheets.Add(Before: sourceSheet);
            else
                ws = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
            ws.Name = sheetName;

            int row = 1;

            void WriteSection(string title, Dictionary<string, string> fields)
            {
                C(ws, row, 1).Value2 = title;
                C(ws, row, 1).Font.Bold = true;
                C(ws, row, 1).Font.Size = 12;
                C(ws, row, 1).Interior.Color = 0xE2EFDA; // Light green
                C(ws, row, 2).Interior.Color = 0xE2EFDA;
                row++;

                foreach (var kv in fields)
                {
                    C(ws, row, 1).Value2 = kv.Key;
                    C(ws, row, 1).Font.Bold = true;
                    C(ws, row, 2).Value2 = kv.Value;
                    row++;
                }
                row++;
            }

            // Inputs
            WriteSection("Inputs", new Dictionary<string, string>
            {
                { "Workbook", wb.Name },
                { "Run ID", request.RunId },
                { "Technique", request.TechniqueId },
                { "Preset", request.Preset },
                { "Series Count", request.Series?.Count.ToString() ?? "0" },
                { "Series Names", string.Join(", ", request.Series?.Select(s => s.Name) ?? Enumerable.Empty<string>()) },
                { "Time Points", request.Time?.Length.ToString() ?? "0" },
            });

            // Frequency & Resampling
            WriteSection("Frequency & Resampling", new Dictionary<string, string>
            {
                { "Frequency", request.Frequency ?? "Auto" },
                { "Fill Method", request.FillConfig?.Method ?? "Kalman" },
                { "Flag Filled", request.FillConfig?.FlagFilled.ToString() ?? "true" },
            });

            // Parameters
            var paramFields = new Dictionary<string, string>();
            if (request.Params != null)
            {
                foreach (var kv in request.Params)
                    paramFields[kv.Key] = kv.Value?.ToString() ?? "";
            }
            if (paramFields.Count > 0)
                WriteSection("Parameters", paramFields);

            // Seed & Determinism
            WriteSection("Determinism", new Dictionary<string, string>
            {
                { "Seed", request.Seed.ToString() },
            });

            // Engine audit fields (from response)
            if (response.AuditFields != null)
            {
                var auditStr = new Dictionary<string, string>();
                foreach (var kv in response.AuditFields)
                    auditStr[kv.Key] = kv.Value?.ToString() ?? "";
                WriteSection("Engine Audit Fields", auditStr);
            }

            // Versions
            if (response.EngineVersions != null)
            {
                WriteSection("Versions", new Dictionary<string, string>
                {
                    { "Add-in Version", typeof(ExcelWriter).Assembly.GetName().Version.ToString() },
                    { "Engine Version", response.EngineVersions.EngineVersion ?? "?" },
                    { "Python Version", response.EngineVersions.PythonVersion ?? "?" },
                    { "Packages Hash", response.EngineVersions.PackagesHash ?? "?" },
                });
            }

            // Warnings
            if (response.Warnings != null && response.Warnings.Count > 0)
            {
                WriteSection("Warnings", response.Warnings
                    .Select((w, i) => new KeyValuePair<string, string>($"Warning {i + 1}", w))
                    .ToDictionary(kv => kv.Key, kv => kv.Value));
            }

            // Errors
            if (response.Status == "failure")
            {
                var errFields = new Dictionary<string, string>
                {
                    { "Error", response.ErrorMessage ?? "Unknown error" },
                };
                if (response.ErrorFixes != null)
                {
                    for (int i = 0; i < response.ErrorFixes.Count; i++)
                        errFields[$"Fix {i + 1}"] = response.ErrorFixes[i];
                }
                WriteSection("Errors", errFields);
            }

            ws.Columns.AutoFit();
            return sheetName;
        }

        private static void EmbedJsonRunRecord(Workbook wb, RunRequest request, RunResponse response)
        {
            try
            {
                Worksheet runsSheet = null;

                // Find or create hidden runs sheet
                foreach (Worksheet ws in wb.Worksheets)
                {
                    if (ws.Name == RunsSheetName)
                    {
                        runsSheet = ws;
                        break;
                    }
                }

                if (runsSheet == null)
                {
                    runsSheet = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
                    runsSheet.Name = RunsSheetName;
                    runsSheet.Visible = XlSheetVisibility.xlSheetVeryHidden;
                    C(runsSheet, 1, 1).Value2 = "run_id";
                    C(runsSheet, 1, 2).Value2 = "timestamp";
                    C(runsSheet, 1, 3).Value2 = "json";
                }

                // Find next empty row
                int nextRow = runsSheet.UsedRange.Rows.Count + 1;
                if (nextRow < 2) nextRow = 2;

                var record = new
                {
                    request = new
                    {
                        request.RunId,
                        request.TechniqueId,
                        request.Preset,
                        request.Seed,
                        request.Frequency,
                        SeriesNames = request.Series?.Select(s => s.Name).ToArray(),
                        TimePoints = request.Time?.Length,
                    },
                    response = new
                    {
                        response.Status,
                        response.PlainEnglishSummary,
                        TableNames = response.Tables?.Select(t => t.Name).ToArray(),
                        response.Warnings,
                        response.EngineVersions,
                    },
                };

                var json = JsonConvert.SerializeObject(record, Formatting.None);

                C(runsSheet, nextRow, 1).Value2 = request.RunId;
                C(runsSheet, nextRow, 2).Value2 = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                C(runsSheet, nextRow, 3).Value2 = json;

                Logger.Info($"Embedded run record for {request.RunId}");
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to embed JSON run record.", ex);
            }
        }

        private static string TruncateSheetName(string name)
        {
            // Excel sheet names max 31 chars, no special chars
            name = name.Replace(":", "").Replace("/", "").Replace("\\", "")
                .Replace("?", "").Replace("*", "").Replace("[", "").Replace("]", "");
            if (name.Length > 31) name = name.Substring(0, 31);
            return name;
        }

        /// <summary>
        /// Get a concise, user-readable short name for the technique, suitable for
        /// use as a sheet name prefix (e.g. "PCA", "VAR", "Seasonal Adjust").
        /// Falls back to a title-cased variant of the technique_id.
        /// </summary>
        private static string GetTechniqueShortName(string techniqueId)
        {
            const string suffixReserve = " Results"; // 8 chars; also fits " Audit" (6)
            try
            {
                var entry = TechniqueCatalogService.GetTechnique(techniqueId);
                var name = entry?.Name;
                if (!string.IsNullOrEmpty(name))
                {
                    // If the full name plus suffix fits within Excel's 31-char cap, use it
                    if (name.Length + suffixReserve.Length <= 31) return name;

                    // Otherwise derive an acronym from capitalised word initials
                    var words = name.Split(new[] { ' ', '-', '_' },
                        StringSplitOptions.RemoveEmptyEntries);
                    if (words.Length >= 2)
                    {
                        var sb = new StringBuilder();
                        foreach (var w in words)
                            if (w.Length > 0 && char.IsLetter(w[0]))
                                sb.Append(char.ToUpper(w[0]));
                        if (sb.Length >= 2 && sb.Length + suffixReserve.Length <= 31)
                            return sb.ToString();
                    }

                    // Final fallback: truncate
                    return name.Substring(0, Math.Min(31 - suffixReserve.Length, name.Length));
                }
            }
            catch { /* catalog unavailable; fall through */ }

            return ToTitleCase(techniqueId ?? "Run");
        }

        private static string ToTitleCase(string s)
        {
            if (string.IsNullOrEmpty(s)) return "Run";
            var parts = s.Replace("_", " ").Split(' ');
            for (int i = 0; i < parts.Length; i++)
            {
                if (parts[i].Length > 0)
                    parts[i] = char.ToUpper(parts[i][0]) + parts[i].Substring(1);
            }
            return string.Join(" ", parts);
        }

        /// <summary>
        /// Return a sheet name that is unique within the workbook, appending
        /// " (2)", " (3)" etc. if the base name already exists. Respects the
        /// 31-char Excel sheet-name limit.
        /// </summary>
        private static string MakeUniqueSheetName(Workbook wb, string baseName)
        {
            bool Exists(string n)
            {
                foreach (Worksheet s in wb.Worksheets)
                {
                    if (string.Equals(s.Name, n, StringComparison.OrdinalIgnoreCase))
                        return true;
                }
                return false;
            }

            if (!Exists(baseName)) return baseName;

            for (int i = 2; i < 1000; i++)
            {
                var suffix = $" ({i})";
                var trunc = baseName;
                if (trunc.Length + suffix.Length > 31)
                    trunc = trunc.Substring(0, 31 - suffix.Length);
                var candidate = trunc + suffix;
                if (!Exists(candidate)) return candidate;
            }

            // Ultimate fallback: stamp with time
            return TruncateSheetName(baseName + "_" + DateTime.Now.ToString("HHmmss"));
        }

        public class WriteResult
        {
            public bool Success { get; set; }
            public string ResultSheetName { get; set; }
            public string AuditSheetName { get; set; }
            public string ErrorMessage { get; set; }
        }
    }
}
