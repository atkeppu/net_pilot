import tkinter as tk
from tkinter import ttk, messagebox

from app_logic import disconnect_wifi
from .base_window import BaseTaskWindow
from .available_networks_tab import AvailableNetworksTab
from .saved_profiles_tab import SavedProfilesTab

class WifiConnectWindow(BaseTaskWindow):
    """A Toplevel window to browse and connect to Wi-Fi networks."""

    def __init__(self, context):
        super().__init__(context, title="Wi-Fi Networks", geometry="800x500")

        self._create_widgets()
        self.available_tab.refresh_list() # Initial refresh

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.status_label = ttk.Label(bottom_frame, text="Select a network...")
        self.status_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

        # Create tabs using the new dedicated classes, passing necessary dependencies
        self.available_tab = AvailableNetworksTab(self.notebook, self, self.task_queue, self.status_label)
        self.saved_tab = SavedProfilesTab(self.notebook, self, self.task_queue, self.status_label)

        self.notebook.add(self.available_tab, text="Available Networks")
        self.notebook.add(self.saved_tab, text="Saved Profiles")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _on_tab_change(self, event):
        """Callback for when the notebook tab changes."""
        selected_tab_index = self.notebook.index(self.notebook.select())
        if selected_tab_index == 1: # Saved Profiles tab
            self.saved_tab.refresh_list()

    def disconnect_from_wifi(self):
        """Initiates a Wi-Fi disconnection, shared by both tabs."""
        if messagebox.askyesno("Confirm Disconnect", "Are you sure you want to disconnect from the current Wi-Fi network?", parent=self):
            self.status_label.config(text="Disconnecting...")
            self.available_tab.set_button_state('disconnect', tk.DISABLED)
            self.saved_tab.set_button_state('disconnect', tk.DISABLED)
            self._run_background_task(self._execute_disconnect_in_thread, on_complete=self._on_disconnect_complete)

    def _execute_disconnect_in_thread(self):
        """Worker function for disconnection."""
        disconnect_wifi()
        self.task_queue.put({'type': 'disconnect_wifi_success'})

    def _on_disconnect_complete(self):
        """Re-enables disconnect buttons on completion."""
        self.available_tab.set_button_state('disconnect', tk.NORMAL)
        self.saved_tab.set_button_state('disconnect', tk.NORMAL)