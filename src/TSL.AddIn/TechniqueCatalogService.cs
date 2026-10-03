using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using TSL.AddIn.Models;

namespace TSL.AddIn
{
    /// <summary>
    /// Loads and provides access to the canonical technique catalog.
    /// Both add-in and engine read the same file for consistency.
    /// </summary>
    public class TechniqueCatalogService
    {
        private static TechniqueCatalog _catalog;
        private static readonly object _lock = new object();

        // The last load: where it looked and, when it failed, why (A2 R8: the Technique
        // Explorer shows these instead of an empty list).
        internal static string LastLoadPath { get; private set; }
        internal static string LastLoadProblem { get; private set; }

        /// <summary>The Technique Explorer's message when the catalog did not load (A2 R8).</summary>
        internal static string ProblemMessage(string path, string error) =>
            "Time Series Lab could not load its list of techniques, so the Technique Explorer is empty.\n\n" +
            "It looked here:\n" + TSL.UI.HouseDialog.Indent(path ?? "(no location)") + "\n\n" +
            TSL.UI.HouseDialog.ErrorBlock(error ?? "(no description)") + "\n\n" +
            "Close Excel and start it again. If this message returns, tell Matthew Hornbach.";

        public static TechniqueCatalog GetCatalog()
        {
            lock (_lock)
            {
                if (_catalog != null) return _catalog;

                _catalog = LoadCatalog();
                return _catalog;
            }
        }

        public static void ReloadCatalog()
        {
            lock (_lock)
            {
                _catalog = LoadCatalog();
            }
        }

        public static TechniqueCatalogEntry GetTechnique(string id)
        {
            return GetCatalog().Techniques
                .FirstOrDefault(t => string.Equals(t.Id, id, StringComparison.OrdinalIgnoreCase));
        }

        public static List<TechniqueCatalogEntry> GetByCategory(string category)
        {
            return GetCatalog().Techniques
                .Where(t => string.Equals(t.Category, category, StringComparison.OrdinalIgnoreCase))
                .ToList();
        }

        public static List<string> GetCategories()
        {
            return GetCatalog().Techniques
                .Select(t => t.Category)
                .Distinct()
                .OrderBy(c => c)
                .ToList();
        }

        public static List<TechniqueCatalogEntry> Search(string query)
        {
            if (string.IsNullOrWhiteSpace(query)) return GetCatalog().Techniques;

            var q = query.ToLowerInvariant();
            return GetCatalog().Techniques
                .Where(t =>
                    (t.Name?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Summary?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Id?.ToLowerInvariant().Contains(q) ?? false) ||
                    (t.Tags?.Any(tag => tag.ToLowerInvariant().Contains(q)) ?? false))
                .ToList();
        }

        /// <summary>
        /// Load the technique description markdown for a given technique
        /// (resources\techniques_md\&lt;id&gt;.md under the add-in's layout root).
        /// </summary>
        public static string GetDescription(string techniqueId)
        {
            var mdPath = AddInLayout.FindFile(out _, "resources", "techniques_md", $"{techniqueId}.md");
            if (mdPath != null)
                return File.ReadAllText(mdPath);
            return "(No detailed description available.)";
        }

        private static TechniqueCatalog LoadCatalog()
        {
            // ONE location, from the add-in's layout (AddInLayout): no search list,
            // so a development build never reads an installed catalog or vice versa.
            var path = AddInLayout.FindFile(out var tried, "resources", "catalog", "techniques_catalog.json");
            LastLoadPath = path ?? tried;
            LastLoadProblem = null;
            if (path != null)
            {
                try
                {
                    var json = File.ReadAllText(path);
                    var catalog = JsonConvert.DeserializeObject<TechniqueCatalog>(json);
                    if (catalog?.Techniques == null)
                        throw new InvalidDataException("The file holds no list of techniques.");
                    Logger.Info($"Loaded technique catalog from {path}: {catalog.Techniques.Count} techniques");
                    return catalog;
                }
                catch (Exception ex)
                {
                    Logger.Error($"Failed to load catalog from {path}.", ex);
                    LastLoadProblem = ex.Message;
                }
            }
            else
            {
                Logger.Warn($"No technique catalog found (looked for {tried}); returning empty catalog.");
                // With no layout, nothing was looked up: "It looked here" lists where the
                // add-in expected its own files.
                LastLoadProblem = AddInLayout.Kind == LayoutKind.Unknown
                    ? "Time Series Lab could not find its own files, so it could not look for the list."
                    : "The file was not found.";
            }

            return new TechniqueCatalog { Version = "0.0.0", Techniques = new List<TechniqueCatalogEntry>() };
        }
    }
}
