import tkinter as tk
from tkinter import ttk

from localization import get_string


class AdapterListFrame(ttk.LabelFrame):
    """
    A frame that contains the list of network adapters and its associated scrollbar.
    It handles displaying the list and notifying the parent of a selection via a callback.
    """

    def __init__(self, parent, on_select_callback, **kwargs):
        super().__init__(parent, text=get_string('available_adapters_title'), **kwargs)
        self.on_select_callback = on_select_callback

        self.adapter_listbox = tk.Listbox(self, height=10)
        self.adapter_listbox.bind('<<ListboxSelect>>', self._on_select)
        self.adapter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self.adapter_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.adapter_listbox.config(yscrollcommand=scrollbar.set)

    def _on_select(self, event):
        """Internal handler to process selection and call the parent's callback."""
        selected_indices = self.adapter_listbox.curselection()
        if selected_indices:
            # Pass the selected index to the parent controller
            self.on_select_callback(selected_indices[0])

    def populate(self, adapters_data):
        """Clears and populates the listbox with adapter data."""
        self.adapter_listbox.delete(0, tk.END)
        if not adapters_data:
            self.adapter_listbox.insert(tk.END, get_string('no_adapters_found'))
        else:
            for adapter in adapters_data:
                display_text = f"{adapter.get('Name', 'N/A')} ({adapter.get('admin_state', 'N/A')})"
                self.adapter_listbox.insert(tk.END, display_text)