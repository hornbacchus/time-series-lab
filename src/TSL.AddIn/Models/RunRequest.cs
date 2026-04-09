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
    }

    public class SeriesData
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("values")]
        public double?[] Values { get; set; }
    }

    public class FillConfig
    {
        [JsonProperty("method")]
        public string Method { get; set; } = "Kalman";

        [JsonProperty("flag_filled")]
        public bool FlagFilled { get; set; } = true;
    }
}
