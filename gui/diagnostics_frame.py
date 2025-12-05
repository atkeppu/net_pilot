import tkinter as tk
from tkinter import ttk

from localization import get_string

DEFAULT_PING_TARGET = "8.8.8.8"

class DiagnosticsFrame(ttk.LabelFrame):
    """
    A frame that displays network diagnostic information like public IP,
    gateway latency, and allows setting a custom ping target.
    """

    def __init__(self, parent, **kwargs):
        super().__init__(parent, text=get_string('diagnostics_title'), **kwargs)

        # Data-driven structure for UI elements.
        # Each tuple contains: (Localization Key, API Key from PowerShell)
        self.diag_map = [
            ('diag_public_ip', "Public IP"),
            ('diag_gateway', "Gateway"),
            ('diag_gateway_latency', "Gateway Latency"),
            ('diag_external_latency', "External Latency"),
            ('diag_dns_servers', "DNS Servers"),
        ]

        self.diag_labels = {}
        self.ping_target_var = tk.StringVar(value=DEFAULT_PING_TARGET)
        self._create_widgets()

    def _create_widgets(self):
        # Build labels dynamically from the diag_map
        for i, (label_key, _) in enumerate(self.diag_map):
            display_text = get_string(label_key)
            ttk.Label(self, text=f"{display_text}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(self, text=get_string('status_fetching'), anchor=tk.W)
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.diag_labels[label_key] = value_label

        ttk.Label(self, text=f"{get_string('diag_ping_target')}:").grid(row=len(self.diag_map), column=0, sticky=tk.W, padx=5, pady=2)
        ping_target_entry = ttk.Entry(self, textvariable=self.ping_target_var)
        ping_target_entry.grid(row=len(self.diag_map), column=1, sticky=tk.EW, padx=5, pady=2)

        self.grid_columnconfigure(1, weight=1)

    def update_diagnostics(self, data: dict):
        """Updates the diagnostic labels with new data."""
        for label_key, api_key in self.diag_map:
            value = data.get(api_key, "N/A")
            self.diag_labels[label_key].config(text=value)

    def get_ping_target(self) -> str:
        """Returns the current value of the ping target entry."""
        return self.ping_target_var.get() or DEFAULT_PING_TARGET