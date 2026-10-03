using System;
using System.Globalization;
using System.Reflection;

namespace TSL.AddIn
{
    /// <summary>
    /// The add-in's build identity, "&lt;describe&gt; / &lt;yyyy-MM-dd HH:mm&gt;": `git describe
    /// --long --always --dirty` of the tree it was built from and the time the DLL was
    /// compiled (the build machine's local time), baked into AssemblyInformationalVersion by
    /// the TslBuildStamp target in TSL.AddIn.csproj. Read from assembly metadata, so it works
    /// when Excel-DNA loads the DLL from bytes. The full stamp is shown by About's Build line,
    /// returned by =TSL_VERSION(), written into every Audit sheet's Versions block, and (via
    /// build_pack) is the packed engine's engine_version.
    /// </summary>
    internal static class BuildInfo
    {
        public const string Unstamped = "DEV-UNSTAMPED";

        /// <summary>Between the describe part and the build time.</summary>
        public const string Separator = " / ";

        public const string BuildTimeFormat = "yyyy-MM-dd HH:mm";

        /// <summary>The full stamp, "&lt;describe&gt; / &lt;yyyy-MM-dd HH:mm&gt;".</summary>
        public static string Stamp { get; } = ReadStamp();

        /// <summary>The git describe part of the stamp (what build_pack compares with git describe).</summary>
        public static string Describe => Split(Stamp).Describe;

        /// <summary>The build time part ("yyyy-MM-dd HH:mm"), or null when the stamp carries none.</summary>
        public static string BuildTime => Split(Stamp).BuildTime;

        /// <summary>True when the build had no git describe (judged on the describe part).</summary>
        public static bool IsUnstamped => string.Equals(Describe, Unstamped, StringComparison.Ordinal);

        /// <summary>
        /// Split a stamp into its describe part (the text before the first " / ", or the whole
        /// stamp when there is none; DEV-UNSTAMPED when empty) and its build time (the text
        /// after it when that is a valid yyyy-MM-dd HH:mm, else null). Pure.
        /// </summary>
        internal static (string Describe, string BuildTime) Split(string stamp)
        {
            var text = (stamp ?? "").Trim();
            if (text.Length == 0) return (Unstamped, null);
            var cut = text.IndexOf(Separator, StringComparison.Ordinal);
            if (cut < 0) return (text, null);
            var describe = text.Substring(0, cut).Trim();
            var time = text.Substring(cut + Separator.Length).Trim();
            return (describe.Length == 0 ? Unstamped : describe, IsBuildTime(time) ? time : null);
        }

        /// <summary>True for exactly "yyyy-MM-dd HH:mm" naming a real date and time.</summary>
        internal static bool IsBuildTime(string text) =>
            !string.IsNullOrEmpty(text) && text.Length == BuildTimeFormat.Length &&
            DateTime.TryParseExact(text, BuildTimeFormat, CultureInfo.InvariantCulture, DateTimeStyles.None, out _);

        private static string ReadStamp()
        {
            try
            {
                var value = typeof(BuildInfo).Assembly
                    .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?
                    .InformationalVersion;
                return string.IsNullOrWhiteSpace(value) ? Unstamped : value.Trim();
            }
            catch
            {
                return Unstamped;
            }
        }
    }
}
