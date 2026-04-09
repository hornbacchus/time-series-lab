using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using ExcelDna.Integration;
using Microsoft.Office.Interop.Excel;

namespace TSL.AddIn
{
    /// <summary>
    /// Robust time index auto-detection. Scores candidate columns on parseability,
    /// monotonicity, uniqueness, and regularity. Prompts user if ambiguous.
    /// </summary>
    public class TimeIndexDetector
    {
        public class CandidateScore
        {
            public int ColumnIndex { get; set; }
            public string ColumnLetter { get; set; }
            public string HeaderName { get; set; }
            public double ParseableRatio { get; set; }
            public double MonotonicRatio { get; set; }
            public double UniquenessRatio { get; set; }
            public double RegularityScore { get; set; }
            public double OverallScore { get; set; }
            public string SuggestedFrequency { get; set; }
        }

        public class DetectionResult
        {
            public CandidateScore BestCandidate { get; set; }
            public List<CandidateScore> AllCandidates { get; set; } = new List<CandidateScore>();
            public string[] ParsedDates { get; set; }
            public bool RequiresUserSelection { get; set; }
            public string Message { get; set; }
        }

        private const double MinAcceptableScore = 0.6;

        /// <summary>
        /// Detect time index from the selection context.
        /// Checks: leftmost column of first area, up to 5 left, up to 2 right.
        /// </summary>
        public DetectionResult Detect(Range firstArea, int dataStartRow, int dataRowCount)
        {
            var result = new DetectionResult();
            var sheet = firstArea.Worksheet;
            int refCol = firstArea.Column;

            // Build candidate column list
            var candidateCols = new List<int>();

            // Leftmost column of first area
            candidateCols.Add(refCol);

            // Up to 5 columns to the left
            for (int i = 1; i <= 5 && refCol - i >= 1; i++)
                candidateCols.Add(refCol - i);

            // Up to 2 columns to the right of the last column
            int lastCol = firstArea.Column + firstArea.Columns.Count - 1;
            for (int i = 1; i <= 2; i++)
                candidateCols.Add(lastCol + i);

            // Score each candidate
            foreach (var col in candidateCols.Distinct())
            {
                var score = ScoreCandidate(sheet, col, dataStartRow, dataRowCount);
                if (score != null)
                    result.AllCandidates.Add(score);
            }

            // Sort by overall score
            result.AllCandidates = result.AllCandidates
                .OrderByDescending(c => c.OverallScore)
                .ToList();

            if (result.AllCandidates.Count > 0 &&
                result.AllCandidates[0].OverallScore >= MinAcceptableScore)
            {
                result.BestCandidate = result.AllCandidates[0];
                result.ParsedDates = ParseColumnAsDates(sheet, result.BestCandidate.ColumnIndex,
                    dataStartRow, dataRowCount);
                result.Message = $"Auto-detected time index: column {result.BestCandidate.ColumnLetter} " +
                                 $"(\"{result.BestCandidate.HeaderName}\") with confidence " +
                                 $"{result.BestCandidate.OverallScore:P0}";
            }
            else
            {
                result.RequiresUserSelection = true;
                result.Message = "Could not confidently detect a time index column. " +
                                 "Please select the date/time column.";
            }

            return result;
        }

        private CandidateScore ScoreCandidate(Worksheet sheet, int col, int startRow, int rowCount)
        {
            var values = new List<object>();
            var dates = new List<DateTime>();
            var rawDoubles = new List<double>();

            for (int r = 0; r < rowCount; r++)
            {
                var val = ((Range)sheet.Cells[startRow + r, col]).Value2;
                values.Add(val);

                var dt = TryParseDate(val);
                if (dt.HasValue)
                {
                    dates.Add(dt.Value);
                    rawDoubles.Add(dt.Value.ToOADate());
                }
            }

            if (values.Count == 0) return null;

            double parseableRatio = (double)dates.Count / values.Count;

            // Monotonicity
            double monotonicCount = 0;
            for (int i = 1; i < rawDoubles.Count; i++)
            {
                if (rawDoubles[i] >= rawDoubles[i - 1]) monotonicCount++;
            }
            double monotonicRatio = rawDoubles.Count > 1
                ? monotonicCount / (rawDoubles.Count - 1)
                : 1.0;

            // Uniqueness
            double uniquenessRatio = dates.Count > 0
                ? (double)dates.Select(d => d.Date).Distinct().Count() / dates.Count
                : 0;

            // Regularity (low variance of deltas, with weekend-gap handling)
            double regularityScore = ComputeRegularity(dates);

            // Overall: weighted combination
            double overall = parseableRatio * 0.35
                           + monotonicRatio * 0.25
                           + uniquenessRatio * 0.20
                           + regularityScore * 0.20;

            // Header
            string header = "?";
            if (startRow > 1)
            {
                var h = ((Range)sheet.Cells[startRow - 1, col]).Value2;
                if (h != null) header = h.ToString().Trim();
            }

            return new CandidateScore
            {
                ColumnIndex = col,
                ColumnLetter = GetColumnLetter(col),
                HeaderName = header,
                ParseableRatio = parseableRatio,
                MonotonicRatio = monotonicRatio,
                UniquenessRatio = uniquenessRatio,
                RegularityScore = regularityScore,
                OverallScore = overall,
                SuggestedFrequency = SuggestFrequency(dates),
            };
        }

        private DateTime? TryParseDate(object val)
        {
            if (val == null) return null;

            // Excel serial date (OA date)
            if (val is double d)
            {
                try
                {
                    if (d > 1 && d < 200000) // reasonable date range
                        return DateTime.FromOADate(d).Date;
                }
                catch { }
            }

            // String date
            if (val is string s)
            {
                s = s.Trim();
                if (DateTime.TryParse(s, CultureInfo.InvariantCulture,
                    DateTimeStyles.None, out var dt))
                {
                    return dt.Date;
                }

                // Try common formats
                var formats = new[]
                {
                    "yyyy-MM-dd", "MM/dd/yyyy", "dd/MM/yyyy", "yyyy/MM/dd",
                    "yyyyMMdd", "dd-MMM-yyyy", "MMM-yyyy", "yyyy-MM",
                    "M/d/yyyy", "d/M/yyyy"
                };

                if (DateTime.TryParseExact(s, formats, CultureInfo.InvariantCulture,
                    DateTimeStyles.None, out dt))
                {
                    return dt.Date;
                }
            }

            return null;
        }

        private double ComputeRegularity(List<DateTime> dates)
        {
            if (dates.Count < 3) return 0.5;

            var deltas = new List<double>();
            for (int i = 1; i < dates.Count; i++)
            {
                var delta = (dates[i] - dates[i - 1]).TotalDays;
                // Normalize: treat 3-day gaps (Fri-Mon) as 1-day for business daily
                if (delta == 3 && dates[i - 1].DayOfWeek == DayOfWeek.Friday)
                    delta = 1;
                if (delta > 0)
                    deltas.Add(delta);
            }

            if (deltas.Count == 0) return 0;

            var median = Median(deltas);
            if (median == 0) return 0;

            var normalizedVariance = deltas.Select(d => Math.Pow((d - median) / median, 2)).Average();

            // Lower variance = higher regularity
            return Math.Max(0, 1.0 - Math.Sqrt(normalizedVariance));
        }

        public static string SuggestFrequency(List<DateTime> dates)
        {
            if (dates.Count < 2) return "Unknown";

            var deltas = new List<double>();
            for (int i = 1; i < dates.Count; i++)
            {
                deltas.Add((dates[i] - dates[i - 1]).TotalDays);
            }

            var median = Median(deltas);

            if (median <= 1.5)
            {
                // Check for weekend gaps (business daily)
                bool hasWeekendGaps = deltas.Any(d => d >= 2.5 && d <= 3.5);
                bool hasWeekendData = dates.Any(d => d.DayOfWeek == DayOfWeek.Saturday || d.DayOfWeek == DayOfWeek.Sunday);
                if (hasWeekendGaps && !hasWeekendData)
                    return "BusinessDaily";
                return "CalendarDaily";
            }

            if (median >= 5 && median <= 8) return "Weekly";
            if (median >= 25 && median <= 35) return "Monthly";
            if (median >= 85 && median <= 95) return "Quarterly";
            if (median >= 350 && median <= 380) return "Annual";

            return "Irregular";
        }

        private static double Median(List<double> values)
        {
            var sorted = values.OrderBy(v => v).ToList();
            int n = sorted.Count;
            if (n == 0) return 0;
            if (n % 2 == 0)
                return (sorted[n / 2 - 1] + sorted[n / 2]) / 2.0;
            return sorted[n / 2];
        }

        private string[] ParseColumnAsDates(Worksheet sheet, int col, int startRow, int rowCount)
        {
            var result = new string[rowCount];
            for (int r = 0; r < rowCount; r++)
            {
                var val = ((Range)sheet.Cells[startRow + r, col]).Value2;
                var dt = TryParseDate(val);
                result[r] = dt?.ToString("yyyy-MM-dd") ?? "";
            }
            return result;
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
