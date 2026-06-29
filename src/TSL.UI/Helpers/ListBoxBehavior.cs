using System.Windows;
using System.Windows.Controls;

namespace TSL.UI.Helpers
{
    /// <summary>
    /// Attached behavior: when <c>ScrollSelectionIntoView</c> is true on a ListBox,
    /// a programmatic SelectedItem change scrolls that item into view. WPF only
    /// auto-scrolls on keyboard/mouse selection, NOT on a bound SelectedItem set —
    /// so a clicked cross-reference link that selects a far-down technique would
    /// otherwise leave it out of the list viewport. Used on the Technique Explorer
    /// list (the secondary half of the scroll-on-navigation polish).
    /// </summary>
    public static class ListBoxBehavior
    {
        public static readonly DependencyProperty ScrollSelectionIntoViewProperty =
            DependencyProperty.RegisterAttached(
                "ScrollSelectionIntoView", typeof(bool), typeof(ListBoxBehavior),
                new PropertyMetadata(false, OnChanged));

        public static bool GetScrollSelectionIntoView(DependencyObject o) => (bool)o.GetValue(ScrollSelectionIntoViewProperty);
        public static void SetScrollSelectionIntoView(DependencyObject o, bool v) => o.SetValue(ScrollSelectionIntoViewProperty, v);

        private static void OnChanged(DependencyObject d, DependencyPropertyChangedEventArgs e)
        {
            if (!(d is ListBox lb)) return;
            // Unhook first (idempotent) so toggling never double-subscribes.
            lb.SelectionChanged -= OnSelectionChanged;
            if (e.NewValue is bool on && on)
                lb.SelectionChanged += OnSelectionChanged;
        }

        private static void OnSelectionChanged(object sender, SelectionChangedEventArgs e)
        {
            if (sender is ListBox lb && lb.SelectedItem != null)
                lb.ScrollIntoView(lb.SelectedItem);
        }
    }
}
