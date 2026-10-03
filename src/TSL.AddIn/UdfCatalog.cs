using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json.Linq;
using TSL.UI;
using TSL.UI.ViewModels;

namespace TSL.AddIn
{
    /// <summary>
    /// The add-in's worksheet functions for Help &gt; UDF Formula Guide (A2 E2b ruling 1):
    /// resources\catalog\udf_catalog.json, which tools\generate_udf_catalog.ps1 generates from
    /// the C# ExcelFunction / ExcelArgument attributes and the pack ships. An argument typed
    /// "object" is optional (Excel-DNA passes ExcelMissing; the function applies its default).
    /// </summary>
    internal static class UdfCatalog
    {
        internal sealed class LoadResult
        {
            public List<UdfEntry> Entries { get; set; } = new List<UdfEntry>();

            /// <summary>Why the guide is empty (a house message), or null when it loaded.</summary>
            public string Message { get; set; }
        }

        internal static LoadResult Load()
        {
            var path = AddInLayout.FindFile(out var tried, "resources", "catalog", "udf_catalog.json");
            if (path == null)
            {
                Logger.Warn($"No worksheet-function catalog found (looked for {tried}).");
                return new LoadResult { Message = MissingMessage(tried) };
            }
            try
            {
                var entries = Parse(File.ReadAllText(path));
                Logger.Info($"Loaded worksheet-function catalog from {path}: {entries.Count} functions.");
                return new LoadResult { Entries = entries };
            }
            catch (Exception ex)
            {
                Logger.Error($"Failed to read the worksheet-function catalog {path}.", ex);
                return new LoadResult { Message = UnreadableMessage(path, ex.Message) };
            }
        }

        internal static string MissingMessage(string tried) =>
            "Time Series Lab could not find its list of worksheet functions, so this guide is empty.\n\n" +
            "It looked here:\n" + HouseDialog.Indent(tried ?? "(no location)") + "\n\n" +
            HouseDialog.TellMatthew;

        internal static string UnreadableMessage(string path, string error) =>
            "Time Series Lab could not read its list of worksheet functions, so this guide is empty.\n\n" +
            "The file:\n" + HouseDialog.Indent(path) + "\n\n" +
            HouseDialog.ErrorBlock(error) + "\n\n" +
            HouseDialog.TellMatthew;

        /// <summary>The catalog's "udfs" array as browser entries (pure: no file, no Excel).</summary>
        internal static List<UdfEntry> Parse(string json)
        {
            var root = JObject.Parse(json);
            var udfs = root["udfs"] as JArray ?? throw new InvalidDataException("The catalog has no \"udfs\" list.");
            var entries = new List<UdfEntry>();
            foreach (var u in udfs.OfType<JObject>())
            {
                var name = (string)u["name"];
                if (string.IsNullOrWhiteSpace(name)) continue;
                var parameters = (u["arguments"] as JArray ?? new JArray()).OfType<JObject>()
                    .Select(a => new UdfParameterInfo
                    {
                        Name = (string)a["name"] ?? "",
                        Type = (string)a["type"] ?? "",
                        Description = HouseDialog.Ascii((string)a["description"] ?? ""),
                        Optional = string.Equals((string)a["type"], "object", StringComparison.Ordinal),
                    }).ToList();
                entries.Add(new UdfEntry
                {
                    Name = name,
                    Category = HouseDialog.Ascii((string)u["category"] ?? ""),
                    Description = HouseDialog.Ascii((string)u["description"] ?? ""),
                    Parameters = parameters,
                    Signature = Signature(name, parameters),
                    Example = FormulaTemplate(name, parameters),
                    ReturnType = "",
                });
            }
            return entries;
        }

        /// <summary>NAME(a, b, [c]): optional arguments in brackets.</summary>
        internal static string Signature(string name, IEnumerable<UdfParameterInfo> parameters) =>
            name + "(" + string.Join(", ", parameters.Select(p => p.Optional ? "[" + p.Name + "]" : p.Name)) + ")";

        /// <summary>
        /// The formula Copy puts on the clipboard (ruling 1(c)) and the Explorer shows: the
        /// function with its required arguments' names, to be replaced with ranges or values.
        /// </summary>
        internal static string FormulaTemplate(string name, IEnumerable<UdfParameterInfo> parameters) =>
            "=" + name + "(" + string.Join(", ", parameters.Where(p => !p.Optional).Select(p => p.Name)) + ")";
    }
}
