using System;
using System.Collections.Generic;
using System.Linq;
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

                try
                {
                    // 1) Results sheet
                    writeResult.ResultSheetName = WriteResultsSheet(wb, request, response);

                    // 2) Audit sheet
                    writeResult.AuditSheetName = WriteAuditSheet(wb, request, response);

                    // 3) Embedded JSON
                    EmbedJsonRunRecord(wb, request, response);

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

        private static string WriteResultsSheet(Workbook wb, RunRequest request, RunResponse response)
        {
            var timestamp = DateTime.Now.ToString("yyyyMMdd_HHmmss");
            var sheetName = TruncateSheetName($"TSL_{request.TechniqueId}_{timestamp}");

            var ws = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
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

            // 4) Output tables
            foreach (var table in response.Tables)
            {
                C(ws, row, 1).Value2 = table.Name;
                C(ws, row, 1).Font.Bold = true;
                C(ws, row, 1).Font.Size = 12;
                row++;

                // Headers
                for (int c = 0; c < table.Columns.Length; c++)
                {
                    C(ws, row, c + 1).Value2 = table.Columns[c];
                    C(ws, row, c + 1).Font.Bold = true;
                    C(ws, row, c + 1).Interior.Color = 0xD9E1F2; // Light blue
                }
                row++;

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

            // Auto-fit columns
            ws.Columns.AutoFit();

            return sheetName;
        }

        private static string WriteAuditSheet(Workbook wb, RunRequest request, RunResponse response)
        {
            var sheetName = TruncateSheetName($"AUDIT_{request.RunId}");
            var ws = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
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

        public class WriteResult
        {
            public bool Success { get; set; }
            public string ResultSheetName { get; set; }
            public string AuditSheetName { get; set; }
            public string ErrorMessage { get; set; }
        }
    }
}
