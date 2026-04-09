using System;
using System.Collections.Generic;
using System.Security.Cryptography;
using System.Text;
using ExcelDna.Integration;
using TSL.AddIn.Models;

namespace TSL.AddIn.Functions
{
    /// <summary>
    /// Shared utilities for AUTO and THOROUGH UDF functions:
    /// hashing, extraction, optional-parameter coercion, table formatting.
    /// </summary>
    internal static class UdfHelpers
    {
        // ── Optional parameter coercion ──────────────────────────────

        internal static bool IsMissing(object val)
            => val is ExcelMissing || val is ExcelEmpty || val == null;

        internal static string Optional(object val, string defaultVal)
            => IsMissing(val) ? defaultVal : val.ToString();

        internal static int OptionalInt(object val, int defaultVal)
        {
            if (IsMissing(val)) return defaultVal;
            if (val is double d) return (int)d;
            if (int.TryParse(val.ToString(), out int i)) return i;
            return defaultVal;
        }

        // ── Extraction ──────────────────────────────────────────────

        /// <summary>
        /// Extract the first column of a range as date strings (OLE date -> yyyy-MM-dd).
        /// Used by both AUTO and THOROUGH for time index extraction.
        /// </summary>
        internal static string[] ExtractTimeStrings(object[,] range)
        {
            int rows = range.GetLength(0);
            var result = new string[rows];
            for (int r = 0; r < rows; r++)
            {
                var val = range[r, 0];
                if (val is double d)
                {
                    try { result[r] = DateTime.FromOADate(d).ToString("yyyy-MM-dd"); }
                    catch { result[r] = val.ToString(); }
                }
                else if (val != null)
                    result[r] = val.ToString();
                else
                    result[r] = "";
            }
            return result;
        }

        /// <summary>
        /// Extract the first column of a range as nullable doubles.
        /// </summary>
        internal static double?[] ExtractSingleColumn(object[,] range)
        {
            int rows = range.GetLength(0);
            var result = new double?[rows];
            for (int r = 0; r < rows; r++)
            {
                var val = range[r, 0];
                if (val is double d) result[r] = d;
                else if (val is int i) result[r] = i;
                else result[r] = null;
            }
            return result;
        }

        /// <summary>
        /// Extract every column of a 2D range as a list of SeriesData.
        /// </summary>
        internal static List<SeriesData> ExtractSeriesFromMatrix(object[,] range)
        {
            int rows = range.GetLength(0);
            int cols = range.GetLength(1);
            var series = new List<SeriesData>(cols);

            for (int c = 0; c < cols; c++)
            {
                var values = new double?[rows];
                for (int r = 0; r < rows; r++)
                {
                    var val = range[r, c];
                    if (val is double d) values[r] = d;
                    else if (val is int i) values[r] = i;
                    else values[r] = null;
                }
                series.Add(new SeriesData { Name = $"Series_{c + 1}", Values = values });
            }

            return series;
        }

        /// <summary>
        /// Collect non-missing extra data range parameters into a list of 2D arrays.
        /// Handles both multi-cell (object[,]) and single-cell (scalar) inputs.
        /// </summary>
        internal static List<object[,]> CollectExtraRanges(params object[] ranges)
        {
            var result = new List<object[,]>();
            foreach (var r in ranges)
            {
                if (IsMissing(r)) continue;

                if (r is object[,] matrix)
                {
                    result.Add(matrix);
                }
                else if (r is double || r is int || r is long)
                {
                    // Single-cell range: Excel-DNA delivers as a scalar
                    var wrap = new object[1, 1];
                    wrap[0, 0] = r;
                    result.Add(wrap);
                }
            }
            return result;
        }

        // ── Hashing ─────────────────────────────────────────────────

        /// <summary>
        /// SHA-256 hash of a string, truncated to 16 hex chars.
        /// </summary>
        internal static string Sha256Short(string input)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(input));
                return BitConverter.ToString(bytes, 0, 8).Replace("-", "").ToLowerInvariant();
            }
        }

        /// <summary>
        /// Hash a 2D range (data only, no time column).
        /// </summary>
        internal static string HashRange(object[,] data)
        {
            var sb = new StringBuilder();
            for (int r = 0; r < data.GetLength(0); r++)
                for (int c = 0; c < data.GetLength(1); c++)
                    sb.Append(data[r, c]?.ToString() ?? "").Append('|');
            return Sha256Short(sb.ToString());
        }

        /// <summary>
        /// Hash time + data ranges together (for THOROUGH caching).
        /// </summary>
        internal static string HashTimeAndData(object[,] time, object[,] data)
        {
            var sb = new StringBuilder();
            for (int r = 0; r < time.GetLength(0); r++)
                sb.Append(time[r, 0]?.ToString() ?? "").Append('|');
            for (int r = 0; r < data.GetLength(0); r++)
                for (int c = 0; c < data.GetLength(1); c++)
                    sb.Append(data[r, c]?.ToString() ?? "").Append('|');
            return Sha256Short(sb.ToString());
        }

        // ── Table formatting ─────────────────────────────────────────

        /// <summary>
        /// Format a RunResponse table as a 2D object array for Excel spill.
        /// </summary>
        internal static object FormatTableForSpill(RunResponse response, string tableName)
        {
            if (response.Tables == null || response.Tables.Count == 0)
                return response.PlainEnglishSummary ?? "No results.";

            OutputTable table = null;
            foreach (var t in response.Tables)
            {
                if (string.Equals(t.Name, tableName, StringComparison.OrdinalIgnoreCase))
                {
                    table = t;
                    break;
                }
            }

            if (table == null && response.Tables.Count > 0)
                table = response.Tables[0];

            if (table == null)
                return response.PlainEnglishSummary ?? "No results.";

            int cols = table.Columns.Length;
            int rows = (table.Rows?.Length ?? 0) + 1;
            var result = new object[rows, cols];

            for (int c = 0; c < cols; c++)
                result[0, c] = table.Columns[c];

            if (table.Rows != null)
            {
                for (int r = 0; r < table.Rows.Length; r++)
                {
                    for (int c = 0; c < cols && c < table.Rows[r].Length; c++)
                    {
                        var val = table.Rows[r][c];
                        result[r + 1, c] = val is Newtonsoft.Json.Linq.JValue jv ? jv.Value : val;
                    }
                }
            }

            return result;
        }

        // ── Workbook name ───────────────────────────────────────────

        internal static string GetWorkbookName()
        {
            try
            {
                var app = (Microsoft.Office.Interop.Excel.Application)ExcelDnaUtil.Application;
                return app.ActiveWorkbook?.Name ?? "Unknown";
            }
            catch
            {
                return "Unknown";
            }
        }
    }
}
