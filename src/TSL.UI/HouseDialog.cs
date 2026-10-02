using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows.Forms;

namespace TSL.UI
{
    /// <summary>
    /// The house dialog (docs/HOUSE_STYLE.md; A2 Part 4(i), geometry per ratification Q9).
    /// Every add-in message, question and free-text prompt goes through here, never a
    /// native MessageBox or input box: tools/check_house_dialogs.py fails the gate on any
    /// other dialog call outside this file and HouseDialogForm.cs.
    ///
    /// No icon - the caption carries severity. A message has one full-width OK (Enter, Esc
    /// and the close box all dismiss it). A question has word-labelled buttons stacked full
    /// width, the first the default, and a dedicated Cancel last (Esc and the close box mean
    /// Cancel). Cancel returns false, 0 or null.
    ///
    /// Modality is the MessageBox calls' it replaces: ShowDialog owned by Excel's main
    /// window, on Excel's thread, so Excel is disabled while the dialog is open. A call from
    /// another thread is passed to the thread that called Initialize.
    /// </summary>
    public static class HouseDialog
    {
        public const string Product = "Time Series Lab";
        public const string AboutCaption = "About " + Product;
        public const string ErrorSuffix = " - Error";
        public const string OkLabel = "OK";
        public const string CancelLabel = "Cancel";
        public const string TellMatthew = "Tell Matthew Hornbach.";

        private static Func<IntPtr> _ownerWindow;
        private static Action<string> _log;
        private static Control _marshal;

        /// <summary>
        /// Call once at AutoOpen, on Excel's main thread: <paramref name="ownerWindow"/>
        /// returns Excel's main window (each dialog is owned by it and centred on it), and
        /// <paramref name="log"/> receives one line per dialog shown and per answer.
        /// </summary>
        public static void Initialize(Func<IntPtr> ownerWindow, Action<string> log)
        {
            _ownerWindow = ownerWindow;
            _log = log;
            if (_marshal == null)
            {
                var control = new Control();
                var _ = control.Handle; // create the handle on this (Excel's) thread
                _marshal = control;
            }
        }

        // ── Messages and questions ──────────────────────────────────────

        /// <summary>A message with one full-width OK. <paramref name="isError"/> appends " - Error" to the caption.</summary>
        public static void ShowHouseAlert(string message, string title, bool isError = false)
        {
            Show(message, Caption(title, isError), new[] { OkLabel }, withCancel: false, requireArea: false,
                textInput: false, initialText: null, out _);
        }

        /// <summary>A question with one action and Cancel: true for the action, false for Cancel, Esc or the close box.</summary>
        public static bool ShowConfirm(string message, string title, string confirmLabel)
        {
            return Show(message, Caption(title, false), new[] { confirmLabel }, withCancel: true, requireArea: true,
                textInput: false, initialText: null, out _) == 1;
        }

        /// <summary>A question with two choices and Cancel: 1 or 2, or 0 for Cancel, Esc or the close box.</summary>
        public static int ShowChoice2(string message, string title, string label1, string label2)
        {
            return Show(message, Caption(title, false), new[] { label1, label2 }, withCancel: true, requireArea: true,
                textInput: false, initialText: null, out _);
        }

        /// <summary>A question with three choices and Cancel: 1 to 3, or 0 for Cancel, Esc or the close box.</summary>
        public static int ShowChoice3(string message, string title, string label1, string label2, string label3)
        {
            return Show(message, Caption(title, false), new[] { label1, label2, label3 }, withCancel: true,
                requireArea: true, textInput: false, initialText: null, out _);
        }

        /// <summary>The house text box (OK and Cancel): the text entered, or null for Cancel, Esc or the close box.</summary>
        public static string ShowTextInput(string message, string title, string initial = "")
        {
            var result = Show(message, Caption(title, false), new[] { OkLabel }, withCancel: true, requireArea: true,
                textInput: true, initialText: initial ?? "", out var text);
            return result == 1 ? text : null;
        }

        // ── Captions (pure) ─────────────────────────────────────────────

        /// <summary>
        /// "Time Series Lab", or "Time Series Lab - &lt;area&gt;" with the area written
        /// exactly as its ribbon button is labelled.
        /// </summary>
        public static string Title(string area = null) =>
            string.IsNullOrWhiteSpace(area) ? Product : Product + " - " + area.Trim();

        /// <summary>The caption shown: the title, plus " - Error" for an error.</summary>
        public static string Caption(string title, bool isError)
        {
            var baseTitle = string.IsNullOrWhiteSpace(title) ? Product : title.Trim();
            return isError ? baseTitle + ErrorSuffix : baseTitle;
        }

        /// <summary>
        /// True for a house caption: "About Time Series Lab", "Time Series Lab" or
        /// "Time Series Lab - &lt;Area&gt;", each but About optionally followed by
        /// " - Error"; printable ASCII, no doubled or edge spaces. A question
        /// (<paramref name="requireArea"/>) must carry an area.
        /// </summary>
        public static bool IsHouseCaption(string caption, bool requireArea = false)
        {
            if (string.IsNullOrEmpty(caption)) return false;
            if (caption == AboutCaption) return !requireArea;
            foreach (var ch in caption)
                if (ch < 0x20 || ch > 0x7E) return false;
            if (caption != caption.Trim() || caption.Contains("  ")) return false;

            var rest = caption.EndsWith(ErrorSuffix, StringComparison.Ordinal)
                ? caption.Substring(0, caption.Length - ErrorSuffix.Length)
                : caption;
            if (rest == Product) return !requireArea;
            if (!rest.StartsWith(Product + " - ", StringComparison.Ordinal)) return false;
            var area = rest.Substring(Product.Length + 3);
            return area.Length > 0 && area != "Error" && !area.StartsWith("-", StringComparison.Ordinal) &&
                   !area.EndsWith(" -", StringComparison.Ordinal);
        }

        // ── Text (pure) ─────────────────────────────────────────────────

        private static readonly Regex Contraction = new Regex(
            @"\b\w+n't\b|\b\w+'(re|ll|ve|m|d)\b|\b(it|that|there|what|here|who|let)'s\b",
            RegexOptions.IgnoreCase | RegexOptions.CultureInvariant);

        private static readonly Regex FirstPerson = new Regex(@"\bI\b|\b(we|We|our|Our|us|me|my|My)\b",
            RegexOptions.CultureInvariant);

        /// <summary>
        /// The house text rules a program can see (docs/HOUSE_STYLE.md, Text): plain ASCII
        /// (the About box alone may carry the copyright sign (U+00A9)), no exclamation marks, contractions or first
        /// person, one blank line between blocks, no trailing spaces. The character and word
        /// rules apply to the add-in's own prose only: a line indented four spaces is a path,
        /// a value or raw Excel/Python error text (Indent, ErrorBlock), which the house style
        /// allows as it is. Empty when the text passes. Shown dialogs log any departure;
        /// nothing is blocked.
        /// </summary>
        public static IList<string> TextProblems(string message, bool allowCopyright = false)
        {
            var problems = new List<string>();
            if (string.IsNullOrWhiteSpace(message))
            {
                problems.Add("empty text");
                return problems;
            }
            var prose = string.Join("\n", message.Split('\n').Where(line => !line.StartsWith("    ", StringComparison.Ordinal)));
            foreach (var ch in prose)
            {
                if ((ch > 0x7E || (ch < 0x20 && ch != '\n')) && !(allowCopyright && ch == '\u00A9'))
                {
                    problems.Add($"non-ASCII or control character U+{(int)ch:X4}");
                    break;
                }
            }
            if (prose.IndexOf('!') >= 0) problems.Add("exclamation mark");
            var contraction = Contraction.Match(prose);
            if (contraction.Success) problems.Add($"contraction \"{contraction.Value}\"");
            var firstPerson = FirstPerson.Match(prose);
            if (firstPerson.Success) problems.Add($"first person \"{firstPerson.Value}\"");
            if (message.Contains("\n\n\n")) problems.Add("more than one blank line between blocks");
            if (message.StartsWith("\n", StringComparison.Ordinal) || message.EndsWith("\n", StringComparison.Ordinal))
                problems.Add("leading or trailing blank line");
            if (message.Split('\n').Any(line => line.Length > 0 && char.IsWhiteSpace(line[line.Length - 1])))
                problems.Add("trailing spaces");
            return problems;
        }

        /// <summary>
        /// A path or value on its own lines, each indented four spaces (house Text rule).
        /// Folded to ASCII; blank lines inside the value are dropped so the value stays one block.
        /// </summary>
        public static string Indent(string value)
        {
            var lines = Ascii(value ?? "").Replace("\r\n", "\n").Replace('\r', '\n').Split('\n')
                .Select(line => line.TrimEnd())
                .Where(line => line.Length > 0)
                .ToList();
            if (lines.Count == 0) lines.Add("(none)");
            return string.Join("\n", lines.Select(line => "    " + line));
        }

        /// <summary>Raw Excel, .NET or Python error text, after a plain sentence: "The error was:" and the text indented.</summary>
        public static string ErrorBlock(string error) =>
            "The error was:\n" + Indent(string.IsNullOrWhiteSpace(error) ? "(no description)" : error);

        /// <summary>
        /// Fold the typographic characters raw error text and engine text can carry (dashes,
        /// curly quotes, ellipsis, comparison signs, non-breaking spaces, tabs) to plain ASCII.
        /// Any other character is kept.
        /// </summary>
        public static string Ascii(string text)
        {
            if (string.IsNullOrEmpty(text)) return text ?? "";
            var sb = new StringBuilder(text.Length);
            foreach (var ch in text)
            {
                switch (ch)
                {
                    case '\u2010': case '\u2011': case '\u2012': case '\u2013': case '\u2014': case '\u2015':
                    case '\u2212': case '\u2022': case '\u00B7':
                        sb.Append('-'); break;
                    case '\u2018': case '\u2019': case '\u201A': case '\u2032':
                        sb.Append('\''); break;
                    case '\u201C': case '\u201D': case '\u201E': case '\u2033':
                        sb.Append('"'); break;
                    case '\u2026': sb.Append("..."); break;
                    case '\u2265': sb.Append(">="); break;
                    case '\u2264': sb.Append("<="); break;
                    case '\u2260': sb.Append("!="); break;
                    case '\u00D7': sb.Append('x'); break;
                    case '\u00B1': sb.Append("+/-"); break;
                    case '\u2192': sb.Append("->"); break;
                    case '\u00A0': case '\u2007': case '\u2009': case '\u202F': sb.Append(' '); break;
                    case '\t': sb.Append("    "); break;
                    default: sb.Append(ch); break;
                }
            }
            return sb.ToString();
        }

        // ── Showing ─────────────────────────────────────────────────────

        /// <summary>
        /// Show one house dialog and return 1..n for the content buttons, 0 for Cancel, Esc
        /// or the close box. Logs the caption and text, any house-style departure, and the answer.
        /// </summary>
        private static int Show(string message, string caption, string[] contentLabels, bool withCancel,
            bool requireArea, bool textInput, string initialText, out string text)
        {
            string entered = null;
            var marshal = _marshal;
            int result;
            if (marshal != null && !marshal.IsDisposed && marshal.InvokeRequired)
            {
                result = (int)marshal.Invoke((Func<int>)(() =>
                    ShowHere(message, caption, contentLabels, withCancel, requireArea, textInput, initialText, out entered)));
            }
            else
            {
                result = ShowHere(message, caption, contentLabels, withCancel, requireArea, textInput, initialText, out entered);
            }
            text = entered;
            return result;
        }

        private static int ShowHere(string message, string caption, string[] contentLabels, bool withCancel,
            bool requireArea, bool textInput, string initialText, out string text)
        {
            text = null;
            message = (message ?? "").Replace("\r\n", "\n").Replace('\r', '\n');
            Log($"[dialog] {caption}: {message.Replace("\n", " | ")}");
            if (!IsHouseCaption(caption, requireArea))
                Log($"[dialog] caption departs from the house style: \"{caption}\"");
            var problems = TextProblems(message, allowCopyright: caption == AboutCaption);
            if (problems.Count > 0)
                Log($"[dialog] text departs from the house style: {string.Join("; ", problems)}");

            var labels = withCancel ? contentLabels.Concat(new[] { CancelLabel }).ToArray() : contentLabels;
            var owner = OwnerHandle();
            int result;
            var unanswerable = false;
            try
            {
                using (var form = new HouseDialogForm(caption, message, labels, contentLabels.Length, withCancel,
                           textInput, initialText, owner))
                {
                    if (owner != IntPtr.Zero) form.ShowDialog(new OwnerWindow(owner));
                    else form.ShowDialog();
                    result = form.Result;
                    text = form.InputText;
                }
            }
            catch (Exception ex)
            {
                // The house form could not be shown: never lose the message. Fall back to
                // the native box (no icon), which only this helper may use. It has only OK
                // (and Cancel), so it never stands in for a choice the user cannot see.
                Log($"[dialog] the house dialog could not be shown ({ex.GetType().Name}: {ex.Message}); " +
                    "showing a native message box instead.");
                DialogResult Native(string text, MessageBoxButtons buttons) => owner != IntPtr.Zero
                    ? MessageBox.Show(new OwnerWindow(owner), text, caption, buttons)
                    : MessageBox.Show(text, caption, buttons);
                if (textInput || contentLabels.Length > 1)
                {
                    Native(message + "\n\n" + (textInput ? "The text box" : "The choices") +
                           " for this question could not be shown, so nothing was chosen and nothing was changed. " +
                           TellMatthew, MessageBoxButtons.OK);
                    result = 0;
                    unanswerable = true;
                }
                else if (withCancel)
                {
                    result = Native(message + "\n\nOK = " + contentLabels[0], MessageBoxButtons.OKCancel) == DialogResult.OK ? 1 : 0;
                }
                else
                {
                    Native(message, MessageBoxButtons.OK);
                    result = 1;
                }
            }

            if (withCancel)
                Log($"[dialog] {caption}: answered " +
                    (unanswerable ? "nothing (the question's choices could not be shown)"
                        : result > 0 && result <= contentLabels.Length ? contentLabels[result - 1]
                        : "Cancel (Cancel, Esc or the close box)"));
            return result;
        }

        private static IntPtr OwnerHandle()
        {
            try { return _ownerWindow?.Invoke() ?? IntPtr.Zero; }
            catch { return IntPtr.Zero; }
        }

        private static void Log(string line)
        {
            try { _log?.Invoke(line); }
            catch { /* logging never breaks a dialog */ }
        }

        private sealed class OwnerWindow : IWin32Window
        {
            public OwnerWindow(IntPtr handle) { Handle = handle; }
            public IntPtr Handle { get; }
        }
    }
}
