import tkinter as tk
from tkinter import ttk

from localization import get_string


class WifiStatusFrame(ttk.LabelFrame):
    """
    A frame that displays the status of the current Wi-Fi connection
    and provides a disconnect button.
    """

    def __init__(self, parent, on_disconnect_callback, **kwargs):
        super().__init__(parent, text=get_string('wifi_status_title'), **kwargs)
        self.on_disconnect_callback = on_disconnect_callback

        # Data-driven structure for UI elements.
        # Each tuple contains: (Localization Key, Data Key)
        self.status_map = [
            ('wifi_status_ssid', "ssid"),
            ('wifi_status_signal', "signal"),
            ('wifi_status_ip', "ipv4"),
        ]

        self.wifi_labels = {}
        self._create_widgets()

    def _create_widgets(self):
        self.disconnect_button = ttk.Button(self, text=get_string('wifi_button_disconnect'), command=self.on_disconnect_callback, state=tk.DISABLED)
        self.disconnect_button.grid(row=0, column=2, rowspan=len(self.status_map), padx=10, pady=5, sticky="ns")

        for i, (label_key, _) in enumerate(self.status_map):
            display_text = get_string(label_key)
            ttk.Label(self, text=f"{display_text}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(self, text="N/A", anchor=tk.W)
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.wifi_labels[label_key] = value_label
        
        self.grid_columnconfigure(1, weight=1)

    def update_status(self, wifi_data: dict | None):
        """Updates the labels with current Wi-Fi data."""
        is_connected = bool(wifi_data)
        details = wifi_data or {}
        self.disconnect_button.config(state=tk.NORMAL if is_connected else tk.DISABLED)

        for label_key, key in self.status_map:
            default_value = get_string('wifi_status_not_connected') if key == "ssid" else "-"
            value = details.get(key, default_value)
            self.wifi_labels[label_key].config(text=value)