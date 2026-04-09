using System;
using System.IO;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;

namespace TSL.AddIn
{
    /// <summary>
    /// Persists per-user settings at %LOCALAPPDATA%\TimeSeriesLab\config.json.
    /// </summary>
    public class SettingsManager
    {
        private readonly string _path;
        private JObject _data;

        public SettingsManager(string path)
        {
            _path = path;
            Load();
        }

        private void Load()
        {
            if (File.Exists(_path))
            {
                try
                {
                    _data = JObject.Parse(File.ReadAllText(_path));
                    return;
                }
                catch
                {
                    Logger.Warn("Settings file corrupted; using defaults.");
                }
            }

            _data = new JObject
            {
                ["globalPreset"] = "Balanced",
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
        }

        public void Save()
        {
            try
            {
                File.WriteAllText(_path, _data.ToString(Formatting.Indented));
            }
            catch (Exception ex)
            {
                Logger.Error("Failed to save settings.", ex);
            }
        }

        public string GetGlobalPreset() => _data.Value<string>("globalPreset") ?? "Balanced";

        public void SetGlobalPreset(string preset)
        {
            _data["globalPreset"] = preset;
            Save();
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
}
