using System;
using System.Collections.Generic;
using System.Linq;
using ExcelDna.Integration;
using Microsoft.Office.Interop.Excel;

namespace TSL.AddIn
{
    /// <summary>
    /// Extracts series data from non-adjacent Excel selections.
    /// Default: each selected column = one series. Row-mode override supported.
    /// Must be called from COM-safe thread (ribbon/pane), NOT from UDF threads.
    /// </summary>
    public class SelectionService
    {
        public class ExtractedSeries
        {
            public string Name { get; set; }
            public string Address { get; set; }
            public double?[] Values { get; set; }
            public int MissingCount { get; set; }
            public int Length => Values?.Length ?? 0;
            public double MissingPct => Length == 0 ? 0 : (double)MissingCount / Length * 100;

            /// <summary>
            /// Excel NumberFormat string of the column's first numeric cell
            /// (e.g. "#,##0.00"). Used later to format the output cells so
            /// they match the user's chosen input formatting.
            /// </summary>
            public string NumberFormat { get; set; }
        }

        public class SelectionResult
        {
            public List<ExtractedSeries> Series { get; set; } = new List<ExtractedSeries>();
            public string[] TimeCandidate { get; set; }
            public string TimeCandidateAddress { get; set; }
            public List<string> Warnings { get; set; } = new List<string>();
            public bool Success { get; set; }
            public string ErrorMessage { get; set; }
        }

        private readonly bool _numericCoercion;

        public SelectionService(bool numericCoercion = true)
        {
            _numericCoercion = numericCoercion;
        }

        /// <summary>
        /// Extract series from the current Excel selection. Handles non-adjacent ranges.
        /// </summary>
        public SelectionResult ExtractFromSelection(bool rowMode = false)
        {
            var result = new SelectionResult();

            try
            {
                var app = (Application)ExcelDnaUtil.Application;
                Range selection = app.Selection as Range;

                if (selection == null)
                {
                    result.ErrorMessage = "No range selected. Please select data columns first.";
                    return result;
                }

                // Process each area (supports non-adjacent selections)
                foreach (Range area in selection.Areas)
                {
                    if (rowMode)
                    {
                        ExtractRows(area, result);
                    }
                    else
                    {
                        ExtractColumns(area, result);
                    }
                }

                if (result.Series.Count == 0)
                {
                    result.ErrorMessage = "No numeric data found in selection. Select columns containing numbers.";
                    return result;
                }

                result.Success = true;
            }
            catch (Exception ex)
            {
                result.ErrorMessage = $"Selection extraction failed: {ex.Message}";
                Logger.Error("Selection extraction failed.", ex);
            }

            return result;
        }

        private void ExtractColumns(Range area, SelectionResult result)
        {
            var sheet = area.Worksheet;
            int startRow = area.Row;
            int startCol = area.Column;
            int numRows = area.Rows.Count;
            int numCols = area.Columns.Count;

            for (int c = 0; c < numCols; c++)
            {
                int col = startCol + c;
                var values = new List<double?>();
                int missingCount = 0;
                string numberFormat = null;
                int firstNumericRow = -1;

                for (int r = 0; r < numRows; r++)
                {
                    int row = startRow + r;
                    var cellValue = ((Range)sheet.Cells[row, col]).Value2;
                    var parsed = ParseNumeric(cellValue);
                    values.Add(parsed);
                    if (!parsed.HasValue)
                    {
                        missingCount++;
                    }
                    else if (firstNumericRow < 0)
                    {
                        firstNumericRow = row;
                    }
                }

                // Grab the Excel number format from the first numeric cell.
                // The header row often has format "General" or different from
                // the data, so sniff from real data. "General" is treated as
                // "no opinion" so we leave NumberFormat null in that case
                // and let the writer fall through to its own defaults.
                if (firstNumericRow > 0)
                {
                    try
                    {
                        var nf = ((Range)sheet.Cells[firstNumericRow, col]).NumberFormat as string;
                        if (!string.IsNullOrEmpty(nf) && !string.Equals(nf, "General",
                            StringComparison.OrdinalIgnoreCase))
                        {
                            numberFormat = nf;
                        }
                    }
                    catch { /* NumberFormat can throw on merged ranges */ }
                }

                // Determine header name. Three sources, tried in order:
                //   1. The cell directly above the first selected row (the
                //      user selected just the data and the header sits above).
                //   2. The first cell of the selection itself, if it's a
                //      non-numeric string (the user selected the column
                //      including its header row — common when you Ctrl-Space
                //      or click the column letter).
                //   3. "Col_<letter>" fallback, preserved as a last resort
                //      so we never end up with an empty name in outputs.
                string header = null;
                if (startRow > 1)
                {
                    var headerCell = ((Range)sheet.Cells[startRow - 1, col]).Value2;
                    if (headerCell != null)
                    {
                        var headerStr = headerCell.ToString().Trim();
                        if (!string.IsNullOrEmpty(headerStr) && !IsNumericLike(headerStr))
                        {
                            header = headerStr;
                        }
                    }
                }

                if (string.IsNullOrEmpty(header) && numRows > 0)
                {
                    var firstCell = ((Range)sheet.Cells[startRow, col]).Value2;
                    if (firstCell != null)
                    {
                        var firstStr = firstCell.ToString().Trim();
                        if (!string.IsNullOrEmpty(firstStr) && !IsNumericLike(firstStr))
                        {
                            header = firstStr;
                        }
                    }
                }

                if (string.IsNullOrEmpty(header))
                {
                    header = $"Col_{GetColumnLetter(col)}";
                }

                var colAddress = $"{GetColumnLetter(col)}{startRow}:{GetColumnLetter(col)}{startRow + numRows - 1}";

                result.Series.Add(new ExtractedSeries
                {
                    Name = header,
                    Address = colAddress,
                    Values = values.ToArray(),
                    MissingCount = missingCount,
                    NumberFormat = numberFormat,
                });
            }
        }

        private void ExtractRows(Range area, SelectionResult result)
        {
            var sheet = area.Worksheet;
            int startRow = area.Row;
            int startCol = area.Column;
            int numRows = area.Rows.Count;
            int numCols = area.Columns.Count;

            for (int r = 0; r < numRows; r++)
            {
                int row = startRow + r;
                var values = new List<double?>();
                int missingCount = 0;

                for (int c = 0; c < numCols; c++)
                {
                    int col = startCol + c;
                    var cellValue = ((Range)sheet.Cells[row, col]).Value2;
                    var parsed = ParseNumeric(cellValue);
                    values.Add(parsed);
                    if (!parsed.HasValue) missingCount++;
                }

                // Header: leftmost cell in row (if text)
                string header = null;
                if (startCol > 1)
                {
                    var headerCell = ((Range)sheet.Cells[row, startCol - 1]).Value2;
                    if (headerCell != null)
                    {
                        var headerStr = headerCell.ToString().Trim();
                        if (!string.IsNullOrEmpty(headerStr) && !IsNumericLike(headerStr))
                            header = headerStr;
                    }
                }

                if (string.IsNullOrEmpty(header))
                    header = $"Row_{row}";

                result.Series.Add(new ExtractedSeries
                {
                    Name = header,
                    Address = $"{GetColumnLetter(startCol)}{row}:{GetColumnLetter(startCol + numCols - 1)}{row}",
                    Values = values.ToArray(),
                    MissingCount = missingCount,
                });
            }
        }

        private double? ParseNumeric(object cellValue)
        {
            if (cellValue == null) return null;
            if (cellValue is double d) return d;
            if (cellValue is int i) return i;
            if (cellValue is long l) return l;

            if (_numericCoercion && cellValue is string s)
            {
                s = s.Trim();
                if (double.TryParse(s, System.Globalization.NumberStyles.Any,
                    System.Globalization.CultureInfo.InvariantCulture, out double parsed))
                {
                    return parsed;
                }
            }

            return null; // Non-numeric -> NA
        }

        private static bool IsNumericLike(string s)
        {
            return double.TryParse(s, System.Globalization.NumberStyles.Any,
                System.Globalization.CultureInfo.InvariantCulture, out _);
        }

        private static string GetColumnLetter(int colNumber)
        {
            string result = "";
            while (colNumber > 0)
            {
                int mod = (colNumber - 1) % 26;
                result = (char)('A' + mod) + result;
                colNumber = (colNumber - 1) / 26;
            }
            return result;
        }
    }
}
