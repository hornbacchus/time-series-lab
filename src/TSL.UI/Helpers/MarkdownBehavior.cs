using System;
using System.Collections.Generic;
using System.Text;
using System.Text.RegularExpressions;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Documents;
using System.Windows.Media;

namespace TSL.UI.Helpers
{
    /// <summary>
    /// Attached behavior that renders a BOUNDED markdown subset into a host
    /// <see cref="Panel"/>'s children as inline WPF elements — built for the
    /// Technique Explorer detail pane (the <c>resources/techniques_md/*.md</c>
    /// files, which were shown as raw <c>#</c>/<c>##</c> text before).
    ///
    /// Formatted PROPERLY (the prose furniture): <c>##</c>+ headers, <c>**bold**</c>,
    /// <c>*italic*</c>/<c>_italic_</c>, <c>-</c>/<c>*</c>/<c>1.</c> lists,
    /// inline <c>`code`</c>, paragraphs. The leading <c>#</c> title is skipped
    /// (it duplicates the pane's technique-name header).
    ///
    /// Degraded READABLY (transitional non-prose, until the content pass rewrites
    /// the files prose-only): code fences, GitHub <c>| col |</c> tables, and
    /// backtick math all render as monospace blocks/runs; blockquotes render
    /// indented-italic. Nothing shows as raw <c>#</c>/<c>|</c> soup.
    ///
    /// No external dependency — net48 WPF only. Defensive: any parse failure
    /// falls back to the raw text as a plain wrapped TextBlock.
    /// </summary>
    public static class MarkdownBehavior
    {
        // ── styling (matches the detail pane: body #424242, headers #212121) ──
        private const double BodySize = 12.0;
        private static readonly Brush BodyBrush = new SolidColorBrush(Color.FromRgb(0x42, 0x42, 0x42));
        private static readonly Brush HeaderBrush = new SolidColorBrush(Color.FromRgb(0x21, 0x21, 0x21));
        private static readonly Brush SubtleBrush = new SolidColorBrush(Color.FromRgb(0x75, 0x75, 0x75));
        private static readonly Brush MonoBg = new SolidColorBrush(Color.FromRgb(0xF5, 0xF5, 0xF5));
        private static readonly FontFamily MonoFont = new FontFamily("Consolas, Courier New, monospace");

        // inline: `code` | **bold** | *italic*  (order matters: code first so a
        // backtick-wrapped span's contents aren't re-parsed; ** before *).
        // NOTE: NO _italic_ — these docs are full of snake_case identifiers
        // (max_lag, auto_default) and `_..._` would falsely italicize across
        // them. Math is backtick-wrapped (consumed by the code branch first), so
        // its subscripts are safe; a rare literal _italic_ simply stays literal.
        private static readonly Regex InlineRx = new Regex(
            @"`[^`]+`|\*\*(?:.+?)\*\*|\*(?:.+?)\*", RegexOptions.Compiled);

        public static readonly DependencyProperty SourceProperty =
            DependencyProperty.RegisterAttached(
                "Source", typeof(string), typeof(MarkdownBehavior),
                new PropertyMetadata(null, OnSourceChanged));

        public static string GetSource(DependencyObject o) => (string)o.GetValue(SourceProperty);
        public static void SetSource(DependencyObject o, string v) => o.SetValue(SourceProperty, v);

        private static void OnSourceChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (!(d is Panel host)) return;
            host.Children.Clear();
            var md = e.NewValue as string;
            if (string.IsNullOrWhiteSpace(md)) return;
            try
            {
                foreach (var block in Render(md))
                    host.Children.Add(block);
            }
            catch
            {
                // Never let a parse bug blank the pane — fall back to raw text.
                host.Children.Clear();
                host.Children.Add(Paragraph(md));
            }
        }

        // ── block parser (line-oriented) ─────────────────────────────────────
        private static IEnumerable<UIElement> Render(string md)
        {
            var lines = md.Replace("\r\n", "\n").Replace("\r", "\n").Split('\n');
            int i = 0;
            while (i < lines.Length)
            {
                string raw = lines[i];
                string t = raw.TrimStart();

                // fenced code block ``` ... ```
                if (t.StartsWith("```"))
                {
                    var sb = new StringBuilder();
                    i++;
                    while (i < lines.Length && !lines[i].TrimStart().StartsWith("```"))
                    {
                        sb.AppendLine(lines[i]);
                        i++;
                    }
                    i++; // past the closing fence
                    yield return MonoBlock(sb.ToString().TrimEnd('\n'));
                    continue;
                }

                // GitHub table: consecutive lines beginning with '|' -> monospace
                // block (degraded; the separator |---|---| rows are dropped).
                if (t.StartsWith("|"))
                {
                    var sb = new StringBuilder();
                    while (i < lines.Length && lines[i].TrimStart().StartsWith("|"))
                    {
                        string row = lines[i].Trim();
                        if (!IsTableSeparator(row))
                            sb.AppendLine(StripInlineMarks(row));
                        i++;
                    }
                    yield return MonoBlock(sb.ToString().TrimEnd('\n'));
                    continue;
                }

                // blockquote
                if (t.StartsWith(">"))
                {
                    var sb = new StringBuilder();
                    while (i < lines.Length && lines[i].TrimStart().StartsWith(">"))
                    {
                        sb.Append(lines[i].TrimStart().TrimStart('>').Trim()).Append(' ');
                        i++;
                    }
                    yield return Quote(sb.ToString().Trim());
                    continue;
                }

                // header  #..######
                if (t.StartsWith("#"))
                {
                    int level = 0;
                    while (level < t.Length && t[level] == '#') level++;
                    string text = t.Substring(level).Trim();
                    i++;
                    if (level <= 1) continue;     // skip the title (= the pane header)
                    yield return Header(text, level);
                    continue;
                }

                // list (unordered - / * / +, or ordered N.)  — non-nested
                if (IsListItem(t))
                {
                    while (i < lines.Length && IsListItem(lines[i].TrimStart()))
                    {
                        yield return ListItem(lines[i].TrimStart());
                        i++;
                    }
                    continue;
                }

                // blank
                if (t.Length == 0) { i++; continue; }

                // paragraph: gather consecutive prose lines
                {
                    var sb = new StringBuilder();
                    while (i < lines.Length)
                    {
                        string p = lines[i];
                        string pt = p.TrimStart();
                        if (pt.Length == 0 || pt.StartsWith("#") || pt.StartsWith("|") ||
                            pt.StartsWith(">") || pt.StartsWith("```") || IsListItem(pt))
                            break;
                        if (sb.Length > 0) sb.Append(' ');
                        sb.Append(p.Trim());
                        i++;
                    }
                    yield return Paragraph(sb.ToString());
                }
            }
        }

        // ── block builders ───────────────────────────────────────────────────
        private static TextBlock Header(string text, int level)
        {
            var tb = new TextBlock
            {
                FontSize = level == 2 ? BodySize + 1 : BodySize,
                FontWeight = FontWeights.Bold,
                Foreground = HeaderBrush,
                TextWrapping = TextWrapping.Wrap,
                Margin = new Thickness(0, 10, 0, 3),
            };
            AppendInlines(tb.Inlines, text);
            return tb;
        }

        private static TextBlock Paragraph(string text)
        {
            var tb = new TextBlock
            {
                FontSize = BodySize,
                Foreground = BodyBrush,
                TextWrapping = TextWrapping.Wrap,
                LineHeight = 18,
                Margin = new Thickness(0, 0, 0, 8),
            };
            AppendInlines(tb.Inlines, text);
            return tb;
        }

        private static TextBlock ListItem(string raw)
        {
            // raw begins with a bullet (-, *, +) or "N." — keep an ordered number,
            // normalise a bullet to "•".
            string prefix, rest;
            var m = Regex.Match(raw, @"^(\d+)\.\s+(.*)$");
            if (m.Success) { prefix = m.Groups[1].Value + ". "; rest = m.Groups[2].Value; }
            else { prefix = "• "; rest = raw.TrimStart('-', '*', '+').TrimStart(); }

            var tb = new TextBlock
            {
                FontSize = BodySize,
                Foreground = BodyBrush,
                TextWrapping = TextWrapping.Wrap,
                LineHeight = 18,
                Margin = new Thickness(12, 0, 0, 4),
            };
            tb.Inlines.Add(new Run(prefix));
            AppendInlines(tb.Inlines, rest);
            return tb;
        }

        private static Border MonoBlock(string text)
        {
            var tb = new TextBlock
            {
                Text = text,
                FontFamily = MonoFont,
                FontSize = BodySize - 1,
                Foreground = BodyBrush,
                TextWrapping = TextWrapping.Wrap,
            };
            return new Border
            {
                Background = MonoBg,
                CornerRadius = new CornerRadius(3),
                Padding = new Thickness(8, 6, 8, 6),
                Margin = new Thickness(0, 0, 0, 8),
                Child = tb,
            };
        }

        private static TextBlock Quote(string text)
        {
            var tb = new TextBlock
            {
                FontSize = BodySize,
                FontStyle = FontStyles.Italic,
                Foreground = SubtleBrush,
                TextWrapping = TextWrapping.Wrap,
                LineHeight = 18,
                Margin = new Thickness(12, 0, 0, 8),
            };
            AppendInlines(tb.Inlines, text);
            return tb;
        }

        // ── inline parser:  **bold**  *italic*  _italic_  `code`  ─────────────
        private static void AppendInlines(InlineCollection inlines, string text)
        {
            if (string.IsNullOrEmpty(text)) return;
            int pos = 0;
            foreach (Match m in InlineRx.Matches(text))
            {
                if (m.Index > pos)
                    inlines.Add(new Run(text.Substring(pos, m.Index - pos)));
                string tok = m.Value;
                if (tok.Length >= 2 && tok[0] == '`')
                {
                    inlines.Add(new Run(tok.Substring(1, tok.Length - 2))
                    { FontFamily = MonoFont, Foreground = HeaderBrush });
                }
                else if (tok.StartsWith("**"))
                {
                    inlines.Add(new Bold(new Run(tok.Substring(2, tok.Length - 4))));
                }
                else // *italic*
                {
                    inlines.Add(new Italic(new Run(tok.Substring(1, tok.Length - 2))));
                }
                pos = m.Index + m.Length;
            }
            if (pos < text.Length)
                inlines.Add(new Run(text.Substring(pos)));
        }

        // ── small helpers ────────────────────────────────────────────────────
        private static bool IsListItem(string t)
        {
            if (t.StartsWith("- ") || t.StartsWith("* ") || t.StartsWith("+ ")) return true;
            return Regex.IsMatch(t, @"^\d+\.\s");
        }

        private static bool IsTableSeparator(string row)
        {
            // e.g. |---|---|  or | :--- | ---: |
            foreach (char c in row)
                if (c != '|' && c != '-' && c != ':' && c != ' ') return false;
            return row.IndexOf('-') >= 0;
        }

        private static string StripInlineMarks(string s) =>
            s.Replace("**", "").Replace("`", "");
    }
}
