using System.Collections.Generic;
using Newtonsoft.Json;

namespace TSL.AddIn.Models
{
    public class RunRequest
    {
        [JsonProperty("run_id")]
        public string RunId { get; set; }

        [JsonProperty("technique_id")]
        public string TechniqueId { get; set; }

        [JsonProperty("preset")]
        public string Preset { get; set; }

        [JsonProperty("seed")]
        public int Seed { get; set; }

        [JsonProperty("frequency")]
        public string Frequency { get; set; }

        [JsonProperty("resample_config")]
        public Dictionary<string, string> ResampleConfig { get; set; }

        [JsonProperty("fill_config")]
        public FillConfig FillConfig { get; set; }

        [JsonProperty("time")]
        public string[] Time { get; set; }

        [JsonProperty("series")]
        public List<SeriesData> Series { get; set; }

        [JsonProperty("exog")]
        public List<SeriesData> Exog { get; set; }

        [JsonProperty("params")]
        public Dictionary<string, object> Params { get; set; }

        /// <summary>
        /// Name of the ORIGINAL INPUT workbook this run was launched against
        /// (e.g. "BondYield_input.xlsx"), captured at launch when that workbook
        /// is genuinely active. Used by ExcelWriter to name the separate results
        /// file after the input source — NOT after whatever workbook is active
        /// when results are written (after a prior run the results workbook is
        /// active, which would compound the name). [JsonIgnore]: add-in only,
        /// never sent to Python.
        /// </summary>
        [JsonIgnore]
        public string SourceWorkbookName { get; set; }

        /// <summary>
        /// Directory of the original input workbook (Workbook.Path; "" if the
        /// input was never saved). The results file is written here so
        /// consecutive runs always land in the input's folder. [JsonIgnore].
        /// </summary>
        [JsonIgnore]
        public string SourceWorkbookPath { get; set; }
    }

    public class SeriesData
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("values")]
        public double?[] Values { get; set; }

        /// <summary>
        /// Excel NumberFormat string of the source cells (e.g. "#,##0.00",
        /// "General", "0.00%"). Captured from the first data cell of the
        /// source column and applied to every numeric output column whose
        /// units match the input (raw series, Seasonally Adjusted, Trend,
        /// Seasonal, Irregular, etc.). Not round-tripped through Python —
        /// carried on the request so ExcelWriter can read it back.
        /// </summary>
        [JsonIgnore]
        public string NumberFormat { get; set; }

        /// <summary>
        /// Excel NumberFormat string of the source time column's first
        /// data cell (e.g. "m/d/yyyy", "dd-mmm-yyyy"). Applied to the
        /// Time column of output tables so the user's chosen date format
        /// is preserved. [JsonIgnore] because Python doesn't use it.
        /// </summary>
        [JsonIgnore]
        public string TimeNumberFormat { get; set; }
    }

    public class FillConfig
    {
        [JsonProperty("method")]
        public string Method { get; set; } = "Kalman";

        [JsonProperty("flag_filled")]
        public bool FlagFilled { get; set; } = true;
    }
}
