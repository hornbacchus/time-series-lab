using System.Collections.Generic;
using Newtonsoft.Json;

namespace TSL.AddIn.Models
{
    public class TechniqueCatalogEntry
    {
        [JsonProperty("id")]
        public string Id { get; set; }

        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("category")]
        public string Category { get; set; }

        [JsonProperty("summary")]
        public string Summary { get; set; }

        [JsonProperty("description_file")]
        public string DescriptionFile { get; set; }

        [JsonProperty("min_series")]
        public int MinSeries { get; set; } = 1;

        [JsonProperty("max_series")]
        public int? MaxSeries { get; set; }

        [JsonProperty("supports_auto_udf")]
        public bool SupportsAutoUdf { get; set; }

        [JsonProperty("auto_udf_name")]
        public string AutoUdfName { get; set; }

        [JsonProperty("presets")]
        public List<string> Presets { get; set; } = new List<string> { "Fast", "Balanced", "Thorough" };

        [JsonProperty("parameters")]
        public List<TechniqueParameter> Parameters { get; set; } = new List<TechniqueParameter>();

        [JsonProperty("output_tables")]
        public List<string> OutputTables { get; set; } = new List<string>();

        [JsonProperty("tags")]
        public List<string> Tags { get; set; } = new List<string>();
    }

    public class TechniqueParameter
    {
        [JsonProperty("name")]
        public string Name { get; set; }

        [JsonProperty("label")]
        public string Label { get; set; }

        [JsonProperty("type")]
        public string Type { get; set; }

        [JsonProperty("default")]
        public object Default { get; set; }

        [JsonProperty("required")]
        public bool Required { get; set; }

        [JsonProperty("advanced")]
        public bool Advanced { get; set; }

        [JsonProperty("description")]
        public string Description { get; set; }

        [JsonProperty("options")]
        public List<string> Options { get; set; }
    }

    public class TechniqueCatalog
    {
        [JsonProperty("version")]
        public string Version { get; set; }

        [JsonProperty("techniques")]
        public List<TechniqueCatalogEntry> Techniques { get; set; } = new List<TechniqueCatalogEntry>();
    }
}
