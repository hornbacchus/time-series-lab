using System.Collections.Generic;
using Newtonsoft.Json;

namespace TSL.AddIn.Models
{
    public class RunResponse
    {
        [JsonProperty("run_id")]
        public string RunId { get; set; }

        [JsonProperty("status")]
        public string Status { get; set; }

        [JsonProperty("plain_english_summary")]
        public string PlainEnglishSummary { get; set; }

        [JsonProperty("tables")]
        public List<OutputTable> Tables { get; set; } = new List<OutputTable>();

        [JsonProperty("artifacts")]
        public Dictionary<string, object> Artifacts { get; set; } = new Dictionary<string, object>();

        [JsonProperty("warnings")]
        public List<string> Warnings { get; set; } = new List<string>();

        [JsonProperty("audit_fields")]
        public Dictionary<string, object> AuditFields { get; set; } = new Dictionary<string, object>();

        [JsonProperty("engine_versions")]
        public EngineVersions EngineVersions { get; set; }

        [JsonProperty("charting_suggestions")]
        public string ChartingSuggestions { get; set; }

        [JsonProperty("error_message")]
        public string ErrorMessage { get; set; }

        [JsonProperty("error_fixes")]
        public List<string> ErrorFixes { get; set; }
    }

    public class OutputTable
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("columns")]
        public string[] Columns { get; set; }

        [JsonProperty("rows")]
        public object[][] Rows { get; set; }
    }

    public class EngineVersions
    {
        [JsonProperty("python_version")]
        public string PythonVersion { get; set; }

        [JsonProperty("packages_hash")]
        public string PackagesHash { get; set; }

        [JsonProperty("engine_version")]
        public string EngineVersion { get; set; }

        [JsonProperty("packages_freeze")]
        public string PackagesFreeze { get; set; }
    }

    public class ProgressEvent
    {
        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("stage")]
        public string Stage { get; set; }

        [JsonProperty("pct")]
        public int? Pct { get; set; }

        [JsonProperty("message")]
        public string Message { get; set; }
    }
}
