using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using ExcelDna.Integration;
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
        /// Load the technique description markdown for a given technique.
        /// </summary>
        public static string GetDescription(string techniqueId)
        {
            var paths = GetCatalogSearchPaths();
            foreach (var basePath in paths)
            {
                var dir = Path.GetDirectoryName(basePath);
                if (string.IsNullOrEmpty(dir)) continue;
                var mdPath = Path.Combine(dir, "..", "techniques_md", $"{techniqueId}.md");
                if (File.Exists(mdPath))
                    return File.ReadAllText(mdPath);
            }
            return "(No detailed description available.)";
        }

        private static TechniqueCatalog LoadCatalog()
        {
            var paths = GetCatalogSearchPaths();

            foreach (var path in paths)
            {
                if (File.Exists(path))
                {
                    try
                    {
                        var json = File.ReadAllText(path);
                        var catalog = JsonConvert.DeserializeObject<TechniqueCatalog>(json);
                        Logger.Info($"Loaded technique catalog from {path}: {catalog.Techniques.Count} techniques");
                        return catalog;
                    }
                    catch (Exception ex)
                    {
                        Logger.Error($"Failed to load catalog from {path}.", ex);
                    }
                }
            }

            Logger.Warn("No technique catalog found; returning empty catalog.");
            return new TechniqueCatalog { Version = "0.0.0", Techniques = new List<TechniqueCatalogEntry>() };
        }

        private static List<string> GetCatalogSearchPaths()
        {
            var paths = new List<string>();

            // Installed location
            paths.Add(Path.Combine(AddIn.AppDataPath, "resources", "catalog", "techniques_catalog.json"));

            // Relative to the loaded XLL (most reliable when running packed).
            try
            {
                var xllPath = ExcelDnaUtil.XllPath;
                if (!string.IsNullOrEmpty(xllPath))
                {
                    var xllDir = Path.GetDirectoryName(xllPath);
                    if (!string.IsNullOrEmpty(xllDir))
                    {
                        // Co-located
                        paths.Add(Path.Combine(xllDir, "resources", "catalog", "techniques_catalog.json"));
                        // Dev build: src\TSL.AddIn\bin\x64\Release\net48\publish\ -> project root
                        paths.Add(Path.Combine(xllDir, "..", "..", "..", "..", "..", "..", "resources", "catalog", "techniques_catalog.json"));
                        // Dev build: src\TSL.AddIn\bin\x64\Release\net48\ -> project root
                        paths.Add(Path.Combine(xllDir, "..", "..", "..", "..", "..", "resources", "catalog", "techniques_catalog.json"));
                    }
                }
            }
            catch { /* ExcelDnaUtil unavailable at design-time */ }

            // Dev location (relative to assembly). Assembly.Location can be empty
            // or an invalid path string when loaded from a packed XLL — wrap defensively.
            try
            {
                var asmLoc = typeof(TechniqueCatalogService).Assembly.Location;
                if (!string.IsNullOrEmpty(asmLoc))
                {
                    var asmDir = Path.GetDirectoryName(asmLoc);
                    if (!string.IsNullOrEmpty(asmDir))
                    {
                        paths.Add(Path.Combine(asmDir, "..", "..", "..", "..", "resources", "catalog", "techniques_catalog.json"));
                        paths.Add(Path.Combine(asmDir, "resources", "catalog", "techniques_catalog.json"));
                    }
                }
            }
            catch { /* Assembly.Location may throw for embedded assemblies */ }

            return paths;
        }
    }
}
