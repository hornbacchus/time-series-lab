using System;
using System.Collections.Concurrent;
using System.Security.Cryptography;
using System.Text;
using TSL.AddIn.Models;

namespace TSL.AddIn
{
    /// <summary>
    /// Session-stable store for THOROUGH run results, keyed by workbook + handle string.
    /// </summary>
    public class ResultStore
    {
        // Key: (WorkbookName, HandleString) -> RunResponse
        private readonly ConcurrentDictionary<string, RunResponse> _store
            = new ConcurrentDictionary<string, RunResponse>();

        /// <summary>
        /// Generate a handle string for a THOROUGH run.
        /// Format: TSL.THR.{TechniqueId}.{Timestamp}.{Hash}
        /// </summary>
        public static string GenerateHandle(string techniqueId, string preset, string optionsJson,
            string dataHash, int triggerValue)
        {
            var hashInput = $"{techniqueId}|{preset}|{optionsJson}|{dataHash}|{triggerValue}";
            var hash = ComputeShortHash(hashInput);
            var timestamp = DateTime.Now.ToString("yyyyMMddHHmmss");
            return $"TSL.THR.{techniqueId}.{timestamp}.{hash}";
        }

        /// <summary>
        /// Store a run response under a handle.
        /// </summary>
        public void Store(string workbookName, string handle, RunResponse response)
        {
            var key = MakeKey(workbookName, handle);
            _store[key] = response;
            Logger.Info($"Stored result: {handle} for workbook {workbookName}");
        }

        /// <summary>
        /// Retrieve a stored response by handle.
        /// </summary>
        public RunResponse Get(string workbookName, string handle)
        {
            var key = MakeKey(workbookName, handle);
            _store.TryGetValue(key, out var response);
            return response;
        }

        /// <summary>
        /// Check if a handle exists and has a valid result.
        /// </summary>
        public string GetStatus(string workbookName, string handle)
        {
            var key = MakeKey(workbookName, handle);
            if (!_store.TryGetValue(key, out var response))
                return "MISSING (Click Re-run Thorough)";

            if (response.Status == "failure")
                return $"ERROR: {response.ErrorMessage}";

            return $"OK (Last run: {ExtractTimestamp(handle)})";
        }

        /// <summary>
        /// Get a specific table from a stored result.
        /// </summary>
        public OutputTable GetTable(string workbookName, string handle, string tableName)
        {
            var response = Get(workbookName, handle);
            if (response?.Tables == null) return null;

            foreach (var table in response.Tables)
            {
                if (string.Equals(table.Name, tableName, StringComparison.OrdinalIgnoreCase))
                    return table;
            }
            return null;
        }

        /// <summary>
        /// Get a specific value from a stored result's artifacts.
        /// </summary>
        public object GetValue(string workbookName, string handle, string key)
        {
            var response = Get(workbookName, handle);
            if (response?.Artifacts == null) return null;

            response.Artifacts.TryGetValue(key, out var value);
            return value;
        }

        private static string MakeKey(string workbookName, string handle)
        {
            return $"{workbookName}||{handle}";
        }

        private static string ExtractTimestamp(string handle)
        {
            // TSL.THR.<technique>.<timestamp>.<hash>
            var parts = handle.Split('.');
            if (parts.Length >= 4)
            {
                var ts = parts[3];
                if (ts.Length == 14)
                {
                    return $"{ts.Substring(0, 4)}-{ts.Substring(4, 2)}-{ts.Substring(6, 2)} " +
                           $"{ts.Substring(8, 2)}:{ts.Substring(10, 2)}:{ts.Substring(12, 2)}";
                }
            }
            return "unknown";
        }

        private static string ComputeShortHash(string input)
        {
            using (var sha = SHA256.Create())
            {
                var bytes = sha.ComputeHash(Encoding.UTF8.GetBytes(input));
                return BitConverter.ToString(bytes, 0, 4).Replace("-", "").ToLowerInvariant();
            }
        }
    }
}
