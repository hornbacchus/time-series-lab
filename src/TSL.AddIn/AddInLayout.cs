using System;
using System.IO;
using ExcelDna.Integration;
using TSL.UI;

namespace TSL.AddIn
{
    /// <summary>Which on-disk layout the loaded add-in belongs to.</summary>
    public enum LayoutKind
    {
        /// <summary>Neither shape recognised - every content lookup fails and says so.</summary>
        Unknown,
        /// <summary>
        /// &lt;root&gt;\addin\&lt;xll&gt; with &lt;root&gt;\engine\engine_worker.py beside it: an
        /// install (%LOCALAPPDATA%\TimeSeriesLab), a per-build folder
        /// (&lt;any&gt;\builds\&lt;stamp&gt;), or build\pack loaded in place.
        /// </summary>
        Installed,
        /// <summary>The XLL sits under a repository checkout (a TimeSeriesLab.sln above it).</summary>
        Development,
    }

    /// <summary>
    /// The ONE place the add-in decides where its content files live
    /// (engine, resources, docs). The layout is decided once, from the loaded
    /// XLL's own location, and there is no fallback between layouts: a
    /// development build never reads an installed copy and an installed build
    /// never reads a repository. The relative paths are identical in both
    /// layouts (the pack mirrors the repository for engine\, resources\ and
    /// docs\), so every lookup is Root + one relative path.
    /// Per-user state (logs, config.json, engine.pid) is NOT content and stays
    /// on AddIn.AppDataPath.
    /// </summary>
    public static class AddInLayout
    {
        private const int MaxDevWalkUp = 8;

        private static readonly Lazy<(LayoutKind Kind, string Root, string XllPath)> _layout =
            new Lazy<(LayoutKind, string, string)>(() => Detect(SafeXllPath()));

        public static LayoutKind Kind => _layout.Value.Kind;

        /// <summary>The content root, or null when the layout is Unknown.</summary>
        public static string Root => _layout.Value.Root;

        /// <summary>The loaded XLL's full path (empty if Excel-DNA could not supply it).</summary>
        public static string XllPath => _layout.Value.XllPath;

        public static string KindLabel =>
            Kind == LayoutKind.Installed ? "Installed" :
            Kind == LayoutKind.Development ? "Development tree" : "Unrecognized";

        /// <summary>
        /// Classify a layout from an XLL path. Pure (file-system reads only), so the
        /// rule can be reasoned about and exercised independently of Excel.
        /// Installed: the XLL's folder's PARENT holds engine\engine_worker.py - the
        /// parent is the root, whatever it is called (%LOCALAPPDATA%\TimeSeriesLab,
        /// &lt;any&gt;\builds\&lt;stamp&gt;, build\pack). Development: a TimeSeriesLab.sln
        /// within MaxDevWalkUp folders above the XLL - that folder is the root.
        /// </summary>
        public static (LayoutKind Kind, string Root, string XllPath) Detect(string xllPath)
        {
            if (string.IsNullOrEmpty(xllPath))
                return (LayoutKind.Unknown, null, xllPath ?? "");

            string xllDir;
            try { xllDir = Path.GetDirectoryName(Path.GetFullPath(xllPath)); }
            catch { return (LayoutKind.Unknown, null, xllPath); }
            if (string.IsNullOrEmpty(xllDir))
                return (LayoutKind.Unknown, null, xllPath);

            var parent = Directory.GetParent(xllDir);
            if (parent != null &&
                File.Exists(Path.Combine(parent.FullName, "engine", "engine_worker.py")))
                return (LayoutKind.Installed, parent.FullName, xllPath);

            var dir = new DirectoryInfo(xllDir);
            for (int i = 0; dir != null && i <= MaxDevWalkUp; i++, dir = dir.Parent)
            {
                if (File.Exists(Path.Combine(dir.FullName, "TimeSeriesLab.sln")))
                    return (LayoutKind.Development, dir.FullName, xllPath);
            }

            return (LayoutKind.Unknown, null, xllPath);
        }

        /// <summary>Root + a relative path, or null when the layout is Unknown.</summary>
        public static string PathOf(params string[] relative)
        {
            var root = Root;
            if (root == null) return null;
            var parts = new string[relative.Length + 1];
            parts[0] = root;
            Array.Copy(relative, 0, parts, 1, relative.Length);
            return Path.Combine(parts);
        }

        /// <summary>
        /// Resolve a content file. Returns its full path when it exists; otherwise
        /// null, with <paramref name="tried"/> naming the exact path that was checked
        /// (or what could not be worked out) for the user-facing message.
        /// </summary>
        public static string FindFile(out string tried, params string[] relative)
        {
            var path = PathOf(relative);
            if (path == null)
            {
                tried = UnknownLayoutDescription();
                return null;
            }
            tried = path;
            return File.Exists(path) ? path : null;
        }

        /// <summary>
        /// The one "file not found" text: names what was wanted, the exact path tried and
        /// where the add-in was loaded from (house style: each path on its own indented
        /// lines). It says what happened; the caller adds the state and what to do. Never
        /// advises a reinstall on a guess.
        /// </summary>
        internal static string MissingMessage(string what, string tried)
        {
            if (Kind == LayoutKind.Unknown)
            {
                // No layout: nothing was looked up, so say what the add-in expected instead.
                return $"Time Series Lab could not find the {what}, because it could not find its own files.\n\n" +
                       "It expected one of these:\n" + HouseDialog.Indent(UnknownLayoutDescription()) + "\n\n" +
                       "The add-in was loaded from:\n" + HouseDialog.Indent(XllPath);
            }
            return $"Time Series Lab could not find the {what}.\n\n" +
                   "It looked here:\n" + HouseDialog.Indent(tried) + "\n\n" +
                   "The add-in was loaded from:\n" + HouseDialog.Indent(XllPath) + "\n\n" +
                   "Layout:\n" + HouseDialog.Indent(KindLabel);
        }

        /// <summary>
        /// Log and show MissingMessage as a house error for the action <paramref name="area"/>
        /// (its ribbon label); the single site for a content miss.
        /// </summary>
        internal static void ReportMissing(string area, string what, string tried,
            string whatToDo = HouseDialog.TellMatthew)
        {
            var message = MissingMessage(what, tried) + "\n\nNothing was changed. " + whatToDo;
            Logger.Warn(message.Replace("\n", " | "));
            HouseDialog.ShowHouseAlert(message, HouseDialog.Title(area), isError: true);
        }

        /// <summary>
        /// The two places the add-in looks for its own files (one per line): the installed
        /// engine worker beside the add-in's folder, or a repository's TimeSeriesLab.sln.
        /// </summary>
        private static string UnknownLayoutDescription()
        {
            var xll = XllPath;
            string worker = "<the add-in's folder>\\..\\engine\\engine_worker.py";
            try
            {
                var xllDir = string.IsNullOrEmpty(xll) ? null : Path.GetDirectoryName(xll);
                if (!string.IsNullOrEmpty(xllDir))
                    worker = Path.GetFullPath(Path.Combine(xllDir, "..", "engine", "engine_worker.py"));
            }
            catch
            {
                // keep the placeholder
            }
            return worker + "\n" + "a TimeSeriesLab.sln in a folder above the add-in";
        }

        private static string SafeXllPath()
        {
            try { return ExcelDnaUtil.XllPath ?? ""; }
            catch { return ""; }
        }
    }
}
