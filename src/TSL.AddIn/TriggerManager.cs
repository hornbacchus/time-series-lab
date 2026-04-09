using System;
using ExcelDna.Integration;
using Microsoft.Office.Interop.Excel;

namespace TSL.AddIn
{
    /// <summary>
    /// Manages the THOROUGH trigger token. THOROUGH formulas include a trigger parameter
    /// that references TSL_TRIGGER(). The ribbon "Re-run Thorough" button increments the
    /// token, which forces all THOROUGH formulas to recompute.
    ///
    /// Implementation:
    /// - Hidden sheet _TSL_META with cell A1 = integer trigger token
    /// - Named range TSL_TRIGGER_TOKEN = _TSL_META!$A$1
    /// </summary>
    public static class TriggerManager
    {
        private const string MetaSheetName = "_TSL_META";
        private const string TriggerRangeName = "TSL_TRIGGER_TOKEN";

        /// <summary>
        /// Gets the current trigger token value for the active workbook.
        /// Creates the hidden sheet and named range if they don't exist.
        /// </summary>
        public static int GetTriggerValue()
        {
            try
            {
                var app = (Application)ExcelDnaUtil.Application;
                var wb = app.ActiveWorkbook;
                if (wb == null) return 0;

                EnsureMetaSheet(wb);

                Worksheet metaSheet = (Worksheet)wb.Sheets[MetaSheetName];
                var val = metaSheet.Range["A1"].Value2;
                return val is double d ? (int)d : 0;
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to get trigger value.", ex);
                return 0;
            }
        }

        /// <summary>
        /// Increments the trigger token, causing all THOROUGH formulas to recompute.
        /// </summary>
        public static void IncrementTrigger()
        {
            try
            {
                var app = (Application)ExcelDnaUtil.Application;
                var wb = app.ActiveWorkbook;
                if (wb == null) return;

                EnsureMetaSheet(wb);

                Worksheet metaSheet = (Worksheet)wb.Sheets[MetaSheetName];
                var current = metaSheet.Range["A1"].Value2;
                var newVal = (current is double d ? (int)d : 0) + 1;
                metaSheet.Range["A1"].Value2 = newVal;

                Logger.Info($"Trigger incremented to {newVal}");
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to increment trigger.", ex);
            }
        }

        private static void EnsureMetaSheet(Workbook wb)
        {
            Worksheet metaSheet = null;

            // Check if sheet exists
            foreach (Worksheet ws in wb.Worksheets)
            {
                if (ws.Name == MetaSheetName)
                {
                    metaSheet = ws;
                    break;
                }
            }

            if (metaSheet == null)
            {
                // Create hidden meta sheet
                metaSheet = (Worksheet)wb.Worksheets.Add(After: wb.Worksheets[wb.Worksheets.Count]);
                metaSheet.Name = MetaSheetName;
                metaSheet.Range["A1"].Value2 = 0;
                metaSheet.Visible = XlSheetVisibility.xlSheetVeryHidden;

                // Create named range
                wb.Names.Add(TriggerRangeName, metaSheet.Range["A1"]);

                Logger.Info("Created _TSL_META sheet and TSL_TRIGGER_TOKEN named range.");
            }
        }
    }
}
