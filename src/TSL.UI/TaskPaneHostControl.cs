using System;
using System.Windows.Forms;
using System.Windows.Forms.Integration;
using TSL.UI.ViewModels;
using TSL.UI.Views;

namespace TSL.UI
{
    /// <summary>
    /// WinForms UserControl that hosts the WPF MainView inside an ElementHost.
    /// This is the root control placed in the Excel Custom Task Pane.
    /// All public methods delegate to the underlying MainViewModel so the
    /// AddIn layer never needs to know about WPF internals.
    /// </summary>
    public class TaskPaneHostControl : UserControl
    {
        private readonly ElementHost _elementHost;
        private readonly MainView _mainView;
        private readonly MainViewModel _viewModel;

        public TaskPaneHostControl()
        {
            // Create the ViewModel
            _viewModel = new MainViewModel();

            // Create the WPF View and wire up its DataContext
            _mainView = new MainView
            {
                DataContext = _viewModel
            };

            // Create the ElementHost bridge
            _elementHost = new ElementHost
            {
                Dock = DockStyle.Fill,
                Child = _mainView
            };

            // Add to this WinForms control
            Controls.Add(_elementHost);

            // Set sensible defaults
            BackColor = System.Drawing.Color.White;
            MinimumSize = new System.Drawing.Size(300, 400);
        }

        // ── Public ViewModel reference ──────────────────────────────

        /// <summary>
        /// Provides direct access to the MainViewModel for the AddIn layer
        /// to wire up events and push data.
        /// </summary>
        public MainViewModel ViewModel => _viewModel;

        // ── Public navigation API (matches TaskPaneManager calls) ───

        /// <summary>
        /// Navigate to a specific technique in the explorer.
        /// </summary>
        public void NavigateToTechnique(string techniqueId)
        {
            if (string.IsNullOrEmpty(techniqueId)) return;
            InvokeOnUIThread(() => _viewModel.NavigateToTechnique(techniqueId));
        }

        /// <summary>
        /// Navigate to the technique explorer.
        /// </summary>
        public void NavigateToExplorer()
        {
            InvokeOnUIThread(() => _viewModel.NavigateToExplorer());
        }

        /// <summary>
        /// Navigate to the recommender wizard.
        /// </summary>
        public void NavigateToRecommender()
        {
            InvokeOnUIThread(() => _viewModel.NavigateToRecommender());
        }

        /// <summary>
        /// Navigate to the recommender wizard with a pre-selected goal.
        /// </summary>
        public void NavigateToRecommenderWithGoal(string goal)
        {
            if (string.IsNullOrEmpty(goal)) return;
            InvokeOnUIThread(() => _viewModel.NavigateToRecommenderWithGoal(goal));
        }

        /// <summary>
        /// Navigate to the technique explorer filtered to a specific category.
        /// </summary>
        public void NavigateToExplorerWithCategory(string category)
        {
            if (string.IsNullOrEmpty(category)) return;
            InvokeOnUIThread(() => _viewModel.NavigateToExplorerWithCategory(category));
        }

        /// <summary>
        /// Navigate to the data readiness view.
        /// </summary>
        public void NavigateToDataReadiness()
        {
            InvokeOnUIThread(() => _viewModel.NavigateToDataReadiness());
        }

        /// <summary>
        /// Navigate to the settings view.
        /// </summary>
        public void NavigateToSettings()
        {
            InvokeOnUIThread(() => _viewModel.NavigateToSettings());
        }

        /// <summary>
        /// Navigate to the UDF browser view.
        /// </summary>
        public void NavigateToUdfBrowser()
        {
            InvokeOnUIThread(() => _viewModel.NavigateToUdfBrowser());
        }

        /// <summary>
        /// Trigger a run of the currently selected technique.
        /// </summary>
        public void RunCurrentTechnique()
        {
            InvokeOnUIThread(() => _viewModel.RunCurrentTechnique());
        }

        /// <summary>
        /// Replace the built-in stub catalog with the real catalog.
        /// </summary>
        public void LoadTechniqueCatalog(System.Collections.Generic.IEnumerable<TSL.UI.ViewModels.TechniqueItem> techniques)
        {
            if (techniques == null) return;
            InvokeOnUIThread(() => _viewModel.LoadTechniqueCatalog(techniques));
        }

        /// <summary>
        /// Update the global preset from the ribbon.
        /// </summary>
        public void SetPreset(string preset)
        {
            if (string.IsNullOrEmpty(preset)) return;
            InvokeOnUIThread(() => _viewModel.Preset = preset);
        }

        /// <summary>
        /// Update the selection status bar from the AddIn's SelectionService.
        /// </summary>
        public void UpdateSelectionStatus(int seriesCount, int pointCount, string frequency)
        {
            InvokeOnUIThread(() => _viewModel.UpdateSelectionStatus(seriesCount, pointCount, frequency));
        }

        // ── Thread marshalling ──────────────────────────────────────

        private void InvokeOnUIThread(Action action)
        {
            if (IsDisposed) return;

            if (InvokeRequired)
            {
                try
                {
                    Invoke(action);
                }
                catch (ObjectDisposedException)
                {
                    // Control was disposed between the check and the invoke
                }
            }
            else
            {
                action();
            }
        }

        // ── Cleanup ─────────────────────────────────────────────────

        protected override void Dispose(bool disposing)
        {
            if (disposing)
            {
                _elementHost?.Dispose();
            }
            base.Dispose(disposing);
        }
    }
}
