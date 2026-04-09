using System.ComponentModel;
using System.Runtime.CompilerServices;

namespace TSL.UI.Helpers
{
    /// <summary>
    /// Base class for all ViewModels. Implements INotifyPropertyChanged with
    /// a convenient SetProperty helper that only raises the event when the
    /// value actually changes.
    /// </summary>
    public abstract class ViewModelBase : INotifyPropertyChanged
    {
        public event PropertyChangedEventHandler PropertyChanged;

        /// <summary>
        /// Raise PropertyChanged for the given property name.
        /// </summary>
        protected void OnPropertyChanged([CallerMemberName] string propertyName = null)
        {
            PropertyChanged?.Invoke(this, new PropertyChangedEventArgs(propertyName));
        }

        /// <summary>
        /// Set a backing field and raise PropertyChanged if the value changed.
        /// Returns true when the value was updated.
        /// </summary>
        protected bool SetProperty<T>(ref T field, T value, [CallerMemberName] string propertyName = null)
        {
            if (Equals(field, value)) return false;
            field = value;
            OnPropertyChanged(propertyName);
            return true;
        }
    }
}
