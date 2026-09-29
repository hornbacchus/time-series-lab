using System.Reflection;

namespace TSL.AddIn
{
    /// <summary>
    /// The add-in's build identity: `git describe --long --always --dirty` of the
    /// tree it was built from, baked into AssemblyInformationalVersion by the
    /// TslBuildStamp target in TSL.AddIn.csproj. Read from assembly metadata, so it
    /// works when Excel-DNA loads the DLL from bytes. Shown by About, returned by
    /// =TSL_VERSION(), and written into every Audit sheet's Versions block.
    /// </summary>
    internal static class BuildInfo
    {
        public const string Unstamped = "DEV-UNSTAMPED";

        public static string Stamp { get; } = ReadStamp();

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
