using System;
using System.IO;

namespace TSL.AddIn
{
    /// <summary>
    /// Whether this machine has Kronos Forecast's own torch environment. It exists only
    /// where it was built (the owner's machine); everywhere else Kronos Forecast is hidden,
    /// by this one test: the ribbon's Bespoke &gt; Kronos Forecast menu and its Technique
    /// Explorer entry (A2 U6, K3). MIRRORS engine/techniques/kronos_forecast/_dispatch.py
    /// KRONOS_PYTHON (TSL_KRONOS_PYTHON, else the default below) - keep the two in step.
    /// The engine inherits Excel's environment (EngineClient does not override this
    /// variable), so the add-in sees the same value the engine will.
    /// </summary>
    internal static class KronosEnvironment
    {
        internal const string TechniqueId = "kronos_forecast";

        private const string DefaultPython = @"C:\KronosDev\venv-kronos\Scripts\python.exe";

        internal static bool IsAvailable()
        {
            try
            {
                var path = Environment.GetEnvironmentVariable("TSL_KRONOS_PYTHON") ?? DefaultPython;
                return File.Exists(path);
            }
            catch
            {
                return false;
            }
        }
    }
}
