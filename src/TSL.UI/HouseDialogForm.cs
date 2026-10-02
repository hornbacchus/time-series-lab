using System;
using System.Drawing;
using System.Runtime.InteropServices;
using System.Windows.Forms;

namespace TSL.UI
{
    /// <summary>
    /// The house dialog's geometry in device pixels: Global Macro Charts' frmPrompt, from
    /// GMC's own report (A2 ratification Q9). Pure, so it can be exercised outside Excel.
    /// </summary>
    internal static class HouseDialogLayout
    {
        // frmPrompt, in points.
        public const float FormWidthPt = 280f;    // the whole form (about 373 px at 96 dpi)
        public const float LabelWidthPt = 256f;   // the prompt, word-wrapped
        public const float ButtonWidthPt = 232f;
        public const float ButtonHeightPt = 24f;
        public const float ButtonStepPt = 30f;    // buttons stacked at 30 pt steps; Cancel one step below the last

        // TSL's own choice (frmPrompt's margins are not recorded): above the text, between
        // the text (or text box) and the first button, and below the last button.
        public const float MarginPt = 12f;

        /// <summary>The message area never grows past this share of the screen's working height; it scrolls beyond.</summary>
        public const double MaxMessageShareOfScreen = 0.6;

        public static int Px(float points, float dpi) => (int)Math.Round(points * dpi / 72.0);

        internal sealed class Result
        {
            public Size Client;
            public Rectangle Message;
            public Rectangle TextBox;
            public Rectangle[] Buttons;
        }

        /// <summary>
        /// Lay out the dialog at <paramref name="dpi"/>. <paramref name="frameWidthPx"/> is the
        /// window frame's total horizontal thickness (outer minus client width), so the outer
        /// width is 280 pt. The text area is <paramref name="messageHeightPx"/> high; a text box
        /// (height &gt; 0) sits under it; then <paramref name="buttonCount"/> buttons, 232 x 24 pt,
        /// at 30 pt steps, centred.
        /// </summary>
        public static Result Compute(float dpi, int frameWidthPx, int messageHeightPx, int textBoxHeightPx, int buttonCount)
        {
            var buttonW = Px(ButtonWidthPt, dpi);
            var buttonH = Px(ButtonHeightPt, dpi);
            var step = Px(ButtonStepPt, dpi);
            var margin = Px(MarginPt, dpi);
            var labelW = Px(LabelWidthPt, dpi);
            var clientW = Math.Max(Px(FormWidthPt, dpi) - Math.Max(0, frameWidthPx), labelW);
            var labelX = (clientW - labelW) / 2;
            var buttonX = (clientW - buttonW) / 2;

            var result = new Result();
            var y = margin;
            result.Message = new Rectangle(labelX, y, labelW, Math.Max(0, messageHeightPx));
            y += result.Message.Height + margin;
            if (textBoxHeightPx > 0)
            {
                result.TextBox = new Rectangle(buttonX, y, buttonW, textBoxHeightPx);
                y += textBoxHeightPx + margin;
            }
            result.Buttons = new Rectangle[Math.Max(0, buttonCount)];
            for (var i = 0; i < result.Buttons.Length; i++)
                result.Buttons[i] = new Rectangle(buttonX, y + i * step, buttonW, buttonH);
            var bottom = result.Buttons.Length > 0 ? result.Buttons[result.Buttons.Length - 1].Bottom : y - margin;
            result.Client = new Size(clientW, bottom + margin);
            return result;
        }

        /// <summary>Centred on <paramref name="owner"/>, then moved fully inside <paramref name="workingArea"/>.</summary>
        public static Point CenterOn(Rectangle owner, Size window, Rectangle workingArea)
        {
            var x = owner.Left + (owner.Width - window.Width) / 2;
            var y = owner.Top + (owner.Height - window.Height) / 2;
            x = Math.Max(workingArea.Left, Math.Min(x, workingArea.Right - window.Width));
            y = Math.Max(workingArea.Top, Math.Min(y, workingArea.Bottom - window.Height));
            return new Point(x, y);
        }
    }

    /// <summary>
    /// The house dialog form (shown only by HouseDialog): no icon, system colours and font,
    /// the text word-wrapped at 256 pt, buttons stacked full width. Result is 1..n for the
    /// content buttons and 0 for Cancel, Esc or the close box. Ctrl+C copies the caption and
    /// text, as a native message box does.
    /// </summary>
    internal sealed class HouseDialogForm : Form
    {
        private readonly string _messageText;
        private readonly IntPtr _owner;
        private readonly Panel _messagePanel;
        private readonly Label _message;
        private readonly TextBox _input;
        private readonly Button[] _buttons;
        private readonly int _contentCount;

        public int Result { get; private set; }
        public string InputText { get; private set; }

        public HouseDialogForm(string caption, string message, string[] labels, int contentCount, bool withCancel,
            bool textInput, string initialText, IntPtr owner)
        {
            _messageText = message ?? "";
            _owner = owner;
            _contentCount = contentCount;

            SuspendLayout();
            Text = caption;
            FormBorderStyle = FormBorderStyle.FixedDialog;
            ShowIcon = false;
            MinimizeBox = false;
            MaximizeBox = false;
            ShowInTaskbar = false;
            StartPosition = FormStartPosition.Manual;
            // Create the window on Excel's monitor, so the DPI read in OnLoad is that monitor's.
            if (owner != IntPtr.Zero)
            {
                try { Location = Screen.FromHandle(owner).WorkingArea.Location; }
                catch { /* the owner is gone: lay out on the primary monitor */ }
            }
            AutoScaleMode = AutoScaleMode.None;
            Font = SystemFonts.MessageBoxFont;
            BackColor = SystemColors.Control;
            ForeColor = SystemColors.ControlText;
            KeyPreview = true;

            _messagePanel = new Panel { AutoScroll = true, TabStop = false };
            _message = new Label
            {
                AutoSize = false,
                UseMnemonic = false,
                Text = _messageText,
                TextAlign = ContentAlignment.TopLeft,
            };
            _messagePanel.Controls.Add(_message);
            Controls.Add(_messagePanel);

            var tabIndex = 0;
            if (textInput)
            {
                _input = new TextBox { Text = initialText ?? "", TabIndex = tabIndex++ };
                Controls.Add(_input);
            }

            _buttons = new Button[labels.Length];
            for (var i = 0; i < labels.Length; i++)
            {
                var index = i;
                var button = new Button
                {
                    Text = labels[i],
                    UseMnemonic = false,
                    FlatStyle = FlatStyle.System,
                    TabIndex = tabIndex++,
                    DialogResult = DialogResult.None,
                };
                button.Click += (s, e) => OnButton(index);
                _buttons[i] = button;
                Controls.Add(button);
            }

            // Enter = the first content button; Esc = Cancel (a message: its one OK).
            AcceptButton = _buttons[0];
            CancelButton = withCancel ? _buttons[_buttons.Length - 1] : _buttons[0];
            ResumeLayout(false);
        }

        private void OnButton(int index)
        {
            Result = index < _contentCount ? index + 1 : 0;
            if (Result == 1 && _input != null) InputText = _input.Text;
            DialogResult = Result > 0 ? DialogResult.OK : DialogResult.Cancel;
            Close();
        }

        protected override void OnLoad(EventArgs e)
        {
            base.OnLoad(e);
            var dpi = DpiOf(this);
            Arrange(dpi);
            // Moving onto Excel's monitor can change the window's DPI (per-monitor-aware
            // threads): lay out again at the new one.
            var moved = DpiOf(this);
            if (Math.Abs(moved - dpi) > 0.5f)
                Arrange(moved);
        }

        /// <summary>Size and place everything for <paramref name="dpi"/>, centred on Excel's window.</summary>
        private void Arrange(float dpi)
        {
            var frameWidth = Width - ClientSize.Width;
            var labelWidth = HouseDialogLayout.Px(HouseDialogLayout.LabelWidthPt, dpi);
            var work = WorkingArea();

            var textHeight = MeasureMessage(labelWidth);
            var maxHeight = Math.Max(HouseDialogLayout.Px(HouseDialogLayout.ButtonHeightPt, dpi),
                (int)(work.Height * HouseDialogLayout.MaxMessageShareOfScreen));
            var scrolls = textHeight > maxHeight;
            if (scrolls) textHeight = MeasureMessage(labelWidth - SystemInformation.VerticalScrollBarWidth);
            var viewHeight = Math.Min(textHeight, maxHeight);

            var inputHeight = _input?.PreferredHeight ?? 0;
            var layout = HouseDialogLayout.Compute(dpi, frameWidth, viewHeight, inputHeight, _buttons.Length);

            ClientSize = layout.Client;
            _messagePanel.Bounds = layout.Message;
            _message.Bounds = new Rectangle(0, 0,
                scrolls ? layout.Message.Width - SystemInformation.VerticalScrollBarWidth : layout.Message.Width,
                textHeight);
            if (_input != null) _input.Bounds = layout.TextBox;
            for (var i = 0; i < _buttons.Length; i++) _buttons[i].Bounds = layout.Buttons[i];

            Location = HouseDialogLayout.CenterOn(OwnerRectangle(work), Size, work);
        }

        protected override void OnShown(EventArgs e)
        {
            base.OnShown(e);
            if (_input != null)
            {
                _input.Focus();
                _input.SelectAll();
            }
            else
            {
                _buttons[0].Focus();
            }
        }

        protected override void OnKeyDown(KeyEventArgs e)
        {
            // Ctrl+C copies the caption and text (as a native message box does), unless the
            // text box has a selection of its own to copy.
            if (e.Modifiers == Keys.Control && e.KeyCode == Keys.C &&
                (_input == null || !_input.Focused || _input.SelectionLength == 0))
            {
                try
                {
                    Clipboard.SetText(Text + "\r\n\r\n" + _messageText.Replace("\n", "\r\n"));
                    e.Handled = true;
                }
                catch
                {
                    // The clipboard is busy: nothing to copy now.
                }
            }
            base.OnKeyDown(e);
        }

        private int MeasureMessage(int width)
        {
            var size = _message.GetPreferredSize(new Size(Math.Max(1, width), 0));
            return size.Height + 2;
        }

        private Rectangle WorkingArea()
        {
            try
            {
                return _owner != IntPtr.Zero ? Screen.FromHandle(_owner).WorkingArea : Screen.FromControl(this).WorkingArea;
            }
            catch
            {
                return Screen.PrimaryScreen.WorkingArea;
            }
        }

        private Rectangle OwnerRectangle(Rectangle fallback)
        {
            if (_owner != IntPtr.Zero && GetWindowRect(_owner, out var r) && r.Right > r.Left && r.Bottom > r.Top)
                return Rectangle.FromLTRB(r.Left, r.Top, r.Right, r.Bottom);
            return fallback;
        }

        private static float DpiOf(Control control)
        {
            try
            {
                var dpi = GetDpiForWindow(control.Handle);
                if (dpi > 0) return dpi;
            }
            catch (EntryPointNotFoundException)
            {
                // Windows before 10 (1607): fall back to the device context.
            }
            using (var g = control.CreateGraphics())
                return g.DpiX;
        }

        [StructLayout(LayoutKind.Sequential)]
        private struct RECT
        {
            public int Left, Top, Right, Bottom;
        }

        [DllImport("user32.dll", SetLastError = true)]
        [return: MarshalAs(UnmanagedType.Bool)]
        private static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);

        [DllImport("user32.dll")]
        private static extern uint GetDpiForWindow(IntPtr hwnd);
    }
}
