import tkinter as tk
from tkinter import ttk

from .utils import format_speed


class AdapterDetailsFrame(ttk.LabelFrame):
    """
    A frame that displays the details of a selected network adapter and provides
    action buttons (Connect/Disconnect).
    """

    def __init__(self, parent, on_connect_callback, on_disconnect_callback, on_status_update_callback, **kwargs):
        super().__init__(parent, text="Adapter Details", **kwargs)
        self.on_connect_callback = on_connect_callback
        self.on_disconnect_callback = on_disconnect_callback
        self.on_status_update_callback = on_status_update_callback

        # Data-driven structure for UI elements.
        # Each tuple contains: (Display Label, Data Key, Optional Formatter Function)
        self.detail_map = [
            ("Description", 'InterfaceDescription'),
            ("MAC Address", 'MacAddress'),
            ("IPv4 Address", 'IPv4Address'),
            ("IPv6 Address", 'IPv6Address'),
            ("Link Speed", 'LinkSpeed', lambda speed: f"{int(speed) / 1_000_000:.0f} Mbps" if isinstance(speed, (int, float)) else (speed or "0")),
            ("Download Speed", 'download_speed', format_speed), # Special key for polled data
            ("Upload Speed", 'upload_speed', format_speed),     # Special key for polled data
            ("Driver Version", 'DriverVersion'),
            ("Driver Date", 'DriverDate'),
        ]

        self.details_labels = {}
        self.clicked_widget = None
        self._create_context_menu()
        self._create_widgets()

    def _create_widgets(self):
        # Build labels dynamically from the detail_map
        for i, (label_text, *_) in enumerate(self.detail_map): # Use * to unpack remaining elements
            ttk.Label(self, text=f"{label_text}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(self, text="-", anchor=tk.W)
            value_label.bind("<Button-3>", self._show_context_menu) # Bind right-click
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.details_labels[label_text] = value_label

        action_button_frame = ttk.Frame(self)
        action_button_frame.grid(row=len(self.detail_map), column=0, columnspan=2, pady=5)
        self.connect_button = ttk.Button(action_button_frame, text="Connect", command=self.on_connect_callback, state=tk.DISABLED)
        self.connect_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.disconnect_button = ttk.Button(action_button_frame, text="Disconnect", command=self.on_disconnect_callback, state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def _create_context_menu(self):
        """Creates the right-click context menu for copying text."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self._copy_to_clipboard)

    def _show_context_menu(self, event):
        """Displays the context menu at the cursor's position."""
        self.clicked_widget = event.widget
        self.context_menu.post(event.x_root, event.y_root)

    def _copy_to_clipboard(self):
        """Copies the text from the right-clicked label to the clipboard."""
        if self.clicked_widget:
            text_to_copy = self.clicked_widget.cget("text")
            if text_to_copy and text_to_copy != "-":
                self.clipboard_clear()
                self.clipboard_append(text_to_copy)
                self.on_status_update_callback(f"Copied '{text_to_copy}' to clipboard.")

    def update_details(self, adapter):
        """Populates the detail labels with data from an adapter dictionary."""
        for config in self.detail_map:
            label, key, formatter = (config + (None,))[:3] # Unpack with default for formatter
            
            # Skip polled speed fields in this initial update
            if key in ['download_speed', 'upload_speed']: continue
            
            raw_value = adapter.get(key)
            display_value = formatter(raw_value) if formatter and raw_value is not None else (raw_value or '-')
            self.details_labels[label].config(text=display_value)

        # Reset speeds, they are updated by the poller
        self.update_speeds(0, 0)

    def update_button_states(self, admin_state: str | None):
        """Updates the Connect/Disconnect button states based on adapter status."""
        if admin_state == 'Disabled':
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
        elif admin_state == 'Enabled':
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)

    def update_speeds(self, download_bps: float, upload_bps: float):
        """Formats and updates only the speed-related labels."""
        self.details_labels["Download Speed"].config(text=format_speed(download_bps) if download_bps is not None else '-')
        self.details_labels["Upload Speed"].config(text=format_speed(upload_bps) if upload_bps is not None else '-')

    def clear(self):
        """Resets all detail labels and buttons to their default state."""
        for label in self.details_labels.values():
            label.config(text="-")
        self.update_button_states(None)