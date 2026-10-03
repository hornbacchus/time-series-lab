using System;
using System.Linq;
using System.Security;
using System.Text;
using TSL.UI;

namespace TSL.AddIn
{
    /// <summary>
    /// Tools > Defaults (A2 Defaults rulings, 2026-10-03), as Global Macro Charts' Tools >
    /// Defaults: one submenu per per-user choice - Preset and Results Destination - with a
    /// check mark on the saved value, read fresh each time the menu opens, and no separate
    /// settings page. The choices stay in config.json (SettingsManager). The ribbon
    /// callbacks in Ribbon.cs show what these return; nothing here touches Excel.
    /// </summary>
    internal static class DefaultsMenu
    {
        /// <summary>The caption area of the Defaults messages.</summary>
        internal const string Area = "Defaults";

        internal const string PresetTag = "preset:";
        internal const string DestinationTag = "dest:";

        // Supertips (the Defaults dispatch, 2026-10-03). Three clauses are corrected to the
        // built behavior: worksheet functions take their own preset argument (Balanced when
        // it is left out) and put their results in cells, so the preset and the destination
        // are those of a run in the task pane; and with "Same workbook as the data" a data
        // workbook that was never saved takes the results itself.
        internal const string MenuSupertip =
            "Choose the defaults Time Series Lab uses for every run in the task pane: the preset, and where results go.";

        internal const string PresetSupertip =
            "The preset each run in the task pane starts with: Fast, Balanced or Thorough.";

        internal const string DestinationSupertip =
            "New workbook: the results of each run in the task pane go to a new workbook saved next to the data " +
            "workbook, and the data workbook is not changed. Same workbook as the data: the Results and Audit " +
            "sheets of each run, and a hidden run record, are added to the workbook that holds the data, and " +
            "Time Series Lab does not save it. A data workbook inside the Time Series Lab program folder, or " +
            "(with New workbook) one that was never saved, sends its results to a new workbook in the Time " +
            "Series Lab folder in Documents. A CSV or text file, or a workbook that does not allow new sheets, " +
            "also gets a new workbook, saved next to it. The Bespoke tools always put their results in a new " +
            "workbook.";

        // Asked before "Same workbook as the data" is saved (A2 Part 4(iv), ratified wording).
        internal const string SameWorkbookQuestion =
            "Results can be added to the workbook that holds the data instead of a new workbook.\n\n" +
            "If AutoSave is on for that workbook, Excel saves the new Results, Audit and hidden " +
            "run-record sheets into the file at once, and Undo cannot remove them.\n\n" +
            "New workbook = keep the data workbook unchanged (the default)\n" +
            "Same workbook = add the results to the data workbook";

        /// <summary>
        /// The menu's content, built each time it opens (a dynamicMenu with
        /// invalidateContentOnDrop), so every check mark is read fresh.
        /// </summary>
        internal static string ContentXml()
        {
            var x = new StringBuilder();
            x.Append("<menu xmlns='http://schemas.microsoft.com/office/2009/07/customui'>");
            Submenu(x, "defPreset", "Preset", PresetSupertip);
            foreach (var preset in SettingsManager.Presets)
                Toggle(x, "defPreset" + preset, preset, PresetTag + preset);
            x.Append("</menu>");
            Submenu(x, "defResults", "Results Destination", DestinationSupertip);
            Toggle(x, "defResultsNew", "New workbook", DestinationTag + ResultsDestinations.NewWorkbook);
            Toggle(x, "defResultsSame", "Same workbook as the data", DestinationTag + ResultsDestinations.SameWorkbook);
            x.Append("</menu>");
            x.Append("</menu>");
            return x.ToString();
        }

        private static void Submenu(StringBuilder x, string id, string label, string supertip) =>
            x.Append("<menu id='").Append(id).Append("' label='").Append(Esc(label))
             .Append("' screentip='").Append(Esc(label)).Append("' supertip='").Append(Esc(supertip)).Append("'>");

        private static void Toggle(StringBuilder x, string id, string label, string tag) =>
            x.Append("<toggleButton id='").Append(id).Append("' label='").Append(Esc(label))
             .Append("' tag='").Append(Esc(tag))
             .Append("' getPressed='OnDefaultsGetPressed' onAction='OnDefaultsClick' />");

        private static string Esc(string s) => SecurityElement.Escape(s);

        /// <summary>The check mark: whether <paramref name="tag"/> is the saved value.</summary>
        internal static bool IsChecked(SettingsManager settings, string tag)
        {
            if (settings == null || string.IsNullOrEmpty(tag)) return false;
            if (tag.StartsWith(PresetTag, StringComparison.Ordinal))
                return string.Equals(settings.GetGlobalPreset(), tag.Substring(PresetTag.Length), StringComparison.Ordinal);
            if (tag.StartsWith(DestinationTag, StringComparison.Ordinal))
                return string.Equals(settings.GetResultsDestination(), tag.Substring(DestinationTag.Length), StringComparison.Ordinal);
            return false;
        }

        internal enum Outcome { Saved, Unchanged, Declined, Failed, NotAChoice }

        /// <summary>
        /// A click on a Defaults item (or on the Run group's Preset menu). A preset or "New
        /// workbook" is saved at once; "Same workbook as the data" first asks
        /// <see cref="SameWorkbookQuestion"/> through <paramref name="ask"/> (message, caption,
        /// first button, second button; 1, 2, or 0 for Cancel), captioned "Time Series Lab -
        /// Defaults", and only the second answer, "Same workbook", saves. A failed save leaves
        /// nothing changed and returns its error.
        /// </summary>
        internal static Outcome Choose(SettingsManager settings, string tag,
            Func<string, string, string, string, int> ask, out Exception error)
        {
            error = null;
            if (settings == null || string.IsNullOrEmpty(tag)) return Outcome.NotAChoice;

            if (tag.StartsWith(PresetTag, StringComparison.Ordinal))
            {
                var preset = tag.Substring(PresetTag.Length);
                if (!SettingsManager.Presets.Contains(preset, StringComparer.Ordinal)) return Outcome.NotAChoice;
                if (settings.GetGlobalPreset() == preset) return Outcome.Unchanged;
                return settings.TrySetGlobalPreset(preset, out error) ? Outcome.Saved : Outcome.Failed;
            }

            if (tag.StartsWith(DestinationTag, StringComparison.Ordinal))
            {
                var destination = tag.Substring(DestinationTag.Length);
                if (destination != ResultsDestinations.NewWorkbook && destination != ResultsDestinations.SameWorkbook)
                    return Outcome.NotAChoice;
                if (settings.GetResultsDestination() == destination) return Outcome.Unchanged;
                if (destination == ResultsDestinations.SameWorkbook &&
                    ask(SameWorkbookQuestion, HouseDialog.Title(Area), "New workbook", "Same workbook") != 2)
                    return Outcome.Declined;
                return settings.TrySetResultsDestination(destination, out error) ? Outcome.Saved : Outcome.Failed;
            }

            return Outcome.NotAChoice;
        }

        /// <summary>The failed-save message (the Defaults dispatch, item (c)).</summary>
        internal static string SaveErrorMessage(string settingsFile, string error) =>
            "Time Series Lab could not save this default. Nothing was changed.\n\n" +
            "The settings file:\n" + HouseDialog.Indent(settingsFile) + "\n\n" +
            HouseDialog.ErrorBlock(error) + "\n\n" +
            HouseDialog.TellMatthew;
    }
}
