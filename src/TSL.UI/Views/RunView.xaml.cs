using System.Collections.Specialized;
using System.Windows.Controls;

namespace TSL.UI.Views
{
    /// <summary>
    /// Code-behind for RunView.xaml.
    /// </summary>
    public partial class RunView : UserControl
    {
        public RunView()
        {
            InitializeComponent();

            // Auto-scroll the progress log to the latest line as the engine
            // streams stages, so the newest message is always visible without
            // manual scrolling (the diagnostic window during long runs).
            ((INotifyCollectionChanged)ProgressLogList.Items).CollectionChanged +=
                OnProgressLogChanged;
        }

        private void OnProgressLogChanged(object sender, NotifyCollectionChangedEventArgs e)
        {
            if (e.Action == NotifyCollectionChangedAction.Add && ProgressLogList.Items.Count > 0)
                ProgressLogList.ScrollIntoView(ProgressLogList.Items[ProgressLogList.Items.Count - 1]);
        }
    }
}
