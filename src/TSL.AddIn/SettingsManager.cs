using System;
using System.IO;
using System.Linq;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace TSL.AddIn
{
    /// <summary>
    /// Persists per-user settings at %LOCALAPPDATA%\TimeSeriesLab\config.json.
    /// The choices a colleague makes - the preset and where results go - are set in
    /// Tools > Defaults (A2 Defaults rulings, 2026-10-03; DefaultsMenu). An unknown or
    /// unreadable value reads as the shipped default and is never written back.
    /// </summary>
    public class SettingsManager
    {
        /// <summary>The presets, in menu order.</summary>
        internal static readonly string[] Presets = { "Fast", "Balanced", "Thorough" };

        /// <summary>The shipped preset.</summary>
        internal const string DefaultPreset = "Balanced";

        private readonly string _path;
        private JObject _data;

        // The file exists but could not be read: it is never overwritten (the Defaults
        // rulings), so a choice cannot be saved until the file is put right.
        private string _unreadableReason;

        public SettingsManager(string path)
        {
            _path = path;
            Load();
        }

        /// <summary>The settings file, for messages.</summary>
        internal string FilePath => _path;

        /// <summary>
        /// Read the file again, so a choice saved by another Excel window is shown (Tools >
        /// Defaults reads its check marks fresh each time it opens, and before each save). A
        /// file that cannot be opened just now (another process is writing or scanning it)
        /// keeps the values read before.
        /// </summary>
        internal void Reload() => Load(keepOnOpenFailure: true);

        private void Load(bool keepOnOpenFailure = false)
        {
            JObject data = null;
            string unreadable = null;
            try
            {
                data = ReadFile(out unreadable);
            }
            catch (Exception ex)
            {
                if (keepOnOpenFailure && _data != null && (ex is IOException || ex is UnauthorizedAccessException))
                {
                    Logger.Info($"The settings file could not be opened just now, so the values read before are kept: {ex.Message}");
                    return;
                }
                unreadable = ex.Message;
            }
            if (unreadable != null)
                Logger.Warn($"The settings file could not be read, so the shipped defaults are used and the file is not overwritten: {unreadable}");

            _data = data ?? new JObject
            {
                ["globalPreset"] = DefaultPreset,
                ["defaultSeed"] = 42,
                ["numericCoercion"] = true,
                ["threadUsage"] = "Auto",
                ["enginePriority"] = "BelowNormal",
                ["maxMissingPctWarning"] = 15.0,
                ["maxGapWarning"] = 10,
                ["fillMethod"] = "Kalman",
                ["weeklyMode"] = "ISO",
                ["businessDailySkipWeekends"] = true,
            };
            _unreadableReason = unreadable;
        }

        /// <summary>
        /// The file as it is now: null when there is none, or it is empty (nothing to keep).
        /// <paramref name="parseError"/> is set when it is there but is not settings JSON. An
        /// IOException or UnauthorizedAccessException means it could not be opened.
        /// </summary>
        private JObject ReadFile(out string parseError)
        {
            parseError = null;
            if (!File.Exists(_path)) return null;
            var text = File.ReadAllText(_path);
            if (string.IsNullOrWhiteSpace(text)) return null;
            try
            {
                return JObject.Parse(text);
            }
            catch (Exception ex)
            {
                parseError = ex.Message;
                return null;
            }
        }

        private static InvalidDataException NotOverwritten(string parseError) =>
            new InvalidDataException("The file could not be read, so it was not overwritten. " + parseError);

        public void Save()
        {
            Exception error;
            if (_unreadableReason != null)
                error = NotOverwritten(_unreadableReason);
            else if (TryWrite(_data, out error))
                return;
            Logger.Error("Failed to save settings.", error);
        }

        /// <summary>
        /// Write <paramref name="data"/> to the file whole or not at all: to a temporary file
        /// beside it, then over it (keeping the old file as a backup until the swap is done),
        /// so a failed save leaves the file as it was.
        /// </summary>
        private bool TryWrite(JObject data, out Exception error)
        {
            error = null;
            var temp = _path + ".tmp";
            var backup = _path + ".bak";
            try
            {
                var dir = Path.GetDirectoryName(_path);
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.WriteAllText(temp, data.ToString(Formatting.Indented));
                if (File.Exists(_path))
                {
                    if (File.Exists(backup)) File.Delete(backup);
                    File.Replace(temp, _path, backup);
                    try { File.Delete(backup); } catch { /* a leftover backup is harmless */ }
                }
                else
                {
                    File.Move(temp, _path);
                }
                return true;
            }
            catch (Exception ex)
            {
                // A replace that fails part-way can leave the old file only under the backup
                // name: put it back.
                string notRestored = null;
                try { if (!File.Exists(_path) && File.Exists(backup)) File.Move(backup, _path); }
                catch (Exception restoreEx) { notRestored = restoreEx.Message; }
                try { if (File.Exists(temp)) File.Delete(temp); } catch { /* best effort */ }
                error = notRestored == null
                    ? ex
                    : new IOException($"{ex.Message} The settings before this change are in {backup}: {notRestored}", ex);
                return false;
            }
        }

        /// <summary>
        /// Save one value into the file as it is now, so a choice saved meanwhile in another
        /// Excel window is kept; on failure nothing changes, in the file or here. A file that
        /// is there but cannot be read is never overwritten.
        /// </summary>
        private bool TrySet(string key, string value, out Exception error)
        {
            JObject current;
            try
            {
                current = ReadFile(out var parseError);
                if (parseError != null)
                {
                    error = NotOverwritten(parseError);
                    Logger.Error($"Could not save {key} = {value} to {_path}.", error);
                    return false;
                }
            }
            catch (Exception ex)
            {
                error = ex;
                Logger.Error($"Could not save {key} = {value} to {_path}: the file could not be opened.", ex);
                return false;
            }

            var updated = current ?? (JObject)_data.DeepClone();
            updated[key] = value;
            if (!TryWrite(updated, out error))
            {
                Logger.Error($"Could not save {key} = {value} to {_path}.", error);
                return false;
            }
            _data = updated;
            _unreadableReason = null;
            return true;
        }

        /// <summary>The preset: Fast, Balanced or Thorough; anything else reads as Balanced.</summary>
        public string GetGlobalPreset()
        {
            string value = null;
            try { value = _data.Value<string>("globalPreset"); }
            catch { /* not a string: the default */ }
            return Presets.FirstOrDefault(p => string.Equals(p, value, StringComparison.OrdinalIgnoreCase))
                   ?? DefaultPreset;
        }

        /// <summary>Save a preset (one of <see cref="Presets"/>); false, with the error, when it could not be saved.</summary>
        internal bool TrySetGlobalPreset(string preset, out Exception error)
        {
            if (!Presets.Contains(preset, StringComparer.Ordinal))
            {
                error = new ArgumentException($"Not a preset: {preset ?? "(none)"}");
                return false;
            }
            return TrySet("globalPreset", preset, out error);
        }

        /// <summary>
        /// Where a selection technique's results go (A2 U7): "NewWorkbook" (the default, and
        /// the value when the key is absent or unrecognized) or "SameWorkbook".
        /// </summary>
        public string GetResultsDestination()
        {
            string value = null;
            try { value = _data.Value<string>("resultsDestination"); }
            catch { /* not a string: the default */ }
            return string.Equals(value, ResultsDestinations.SameWorkbook, StringComparison.OrdinalIgnoreCase)
                ? ResultsDestinations.SameWorkbook
                : ResultsDestinations.NewWorkbook;
        }

        /// <summary>Save a results destination (one of <see cref="ResultsDestinations"/>); false, with the error, when it could not be saved.</summary>
        internal bool TrySetResultsDestination(string destination, out Exception error)
        {
            if (destination != ResultsDestinations.NewWorkbook && destination != ResultsDestinations.SameWorkbook)
            {
                error = new ArgumentException($"Not a results destination: {destination ?? "(none)"}");
                return false;
            }
            return TrySet("resultsDestination", destination, out error);
        }

        public int GetDefaultSeed() => _data.Value<int?>("defaultSeed") ?? 42;

        public void SetDefaultSeed(int seed)
        {
            _data["defaultSeed"] = seed;
            Save();
        }

        public bool GetNumericCoercion() => _data.Value<bool?>("numericCoercion") ?? true;

        public string GetFillMethod() => _data.Value<string>("fillMethod") ?? "Kalman";

        public double GetMaxMissingPctWarning() => _data.Value<double?>("maxMissingPctWarning") ?? 15.0;

        public int GetMaxGapWarning() => _data.Value<int?>("maxGapWarning") ?? 10;

        public T Get<T>(string key, T defaultValue = default)
        {
            var token = _data[key];
            if (token == null) return defaultValue;
            return token.ToObject<T>();
        }

        public void Set<T>(string key, T value)
        {
            _data[key] = JToken.FromObject(value);
            Save();
        }
    }

    /// <summary>The values of the resultsDestination setting in config.json (A2 U7).</summary>
    internal static class ResultsDestinations
    {
        /// <summary>A new workbook saved next to the data workbook (the default).</summary>
        internal const string NewWorkbook = "NewWorkbook";

        /// <summary>The workbook that holds the data; it is not saved.</summary>
        internal const string SameWorkbook = "SameWorkbook";
    }
}
