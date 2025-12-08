import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

from app_logic import list_wifi_networks, get_current_wifi_details, connect_to_wifi_network
from localization import get_string

class AvailableNetworksTab(ttk.Frame):
    """
    UI and logic for the 'Available Networks' tab in the Wi-Fi window.
    """
    def __init__(self, parent_notebook, window, task_queue, status_label):
        super().__init__(parent_notebook)
        self.window = window
        self.task_queue = task_queue
        self.status_label = status_label
        self.wifi_data = []

        self._create_widgets()

    def _create_widgets(self):
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('ssid', 'signal', 'auth', 'encryption')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.heading('ssid', text=get_string('wifi_col_ssid'), command=lambda: self._sort_by_column('ssid', False))
        self.tree.heading('signal', text=get_string('wifi_col_signal'), command=lambda: self._sort_by_column('signal', True))
        self.tree.heading('auth', text=get_string('wifi_col_auth'), command=lambda: self._sort_by_column('auth', False))
        self.tree.heading('encryption', text=get_string('wifi_col_encrypt'), command=lambda: self._sort_by_column('encryption', False))
        self.tree.column('ssid', width=200); self.tree.column('signal', width=80, anchor=tk.CENTER)
        self.tree.column('auth', width=150); self.tree.column('encryption', width=100)
        self.tree.bind('<<TreeviewSelect>>', self._on_network_select)
        self.tree.bind('<Double-1>', lambda e: self.connect_to_network())
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.connect_frame = ttk.LabelFrame(self, text=get_string('wifi_button_connect'))
        ttk.Label(self.connect_frame, text=f"{get_string('wifi_col_password')}:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.connect_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.connect_frame.grid_columnconfigure(1, weight=1)

        action_frame = ttk.Frame(self)
        action_frame.pack(fill=tk.X)
        self.connect_button = ttk.Button(action_frame, text=get_string('wifi_button_connect'), command=self.connect_to_network, state=tk.DISABLED)
        self.disconnect_button = ttk.Button(action_frame, text=get_string('wifi_button_disconnect'), command=self.window.disconnect_from_wifi)
        self.refresh_button = ttk.Button(action_frame, text=get_string('wifi_button_refresh'), command=self.refresh_list)
        self.disconnect_button.pack(side=tk.RIGHT, padx=(5, 0)); self.connect_button.pack(side=tk.RIGHT, padx=(5, 0)); self.refresh_button.pack(side=tk.RIGHT)
        self.connect_frame.pack_forget()

    def refresh_list(self):
        self.status_label.config(text=get_string('status_refreshing_list'))
        self.set_button_state('refresh', tk.DISABLED)
        self.set_button_state('connect', tk.DISABLED)
        self.window.context.action_handler.diagnostics.fetch_wifi_networks(on_complete=self._on_refresh_complete)

    def _on_refresh_complete(self):
        self.set_button_state('refresh', tk.NORMAL)

    def populate_list(self, wifi_data, current_ssid):
        self.wifi_data = wifi_data
        self.tree.delete(*self.tree.get_children())
        if not self.wifi_data:
            self.tree.insert('', tk.END, values=(get_string('wifi_no_networks_found'), "", "", ""))
            self.tree.config(selectmode="none")
        else:
            self.tree.config(selectmode="browse")
            for i, network in enumerate(self.wifi_data):
                ssid = network.get('ssid', 'N/A')
                display_ssid = ssid + " (Connected)" if ssid and ssid == current_ssid else ssid
                self.tree.insert('', tk.END, iid=i, values=(display_ssid, f"{network.get('signal', 'N/A')}%", network.get('authentication', 'N/A'), network.get('encryption', 'N/A')))

    def _on_network_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item: return
        network = self.wifi_data[int(selected_item)]
        self.status_label.config(text=f"Selected: {network['ssid']}")
        self.set_button_state('connect', tk.NORMAL)
        if network.get('authentication', '').lower() != 'open':
            self.connect_frame.pack(fill=tk.X, pady=5); self.password_entry.focus()
        else:
            self.connect_frame.pack_forget()

    def connect_to_network(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning(get_string('netstat_selection_required'), get_string('wifi_select_to_connect'), parent=self.window)
            return
        network = self.wifi_data[int(selected_item)]
        ssid = network['ssid']
        authentication = network.get('authentication', 'N/A')
        encryption = network.get('encryption', 'N/A')
        
        password = None
        if network.get('authentication', '').lower() != 'open':
            password = self.password_var.get()
            if not password: # If password field is empty, but required, prompt the user.
                password = simpledialog.askstring(get_string('wifi_password_prompt_title'), get_string('wifi_password_prompt_msg', ssid=ssid), parent=self.window, show='*')
                if not password: return # User cancelled
        self.status_label.config(text=get_string('wifi_connect_status', ssid=ssid))
        self.set_button_state('connect', tk.DISABLED, get_string('wifi_connect_status', ssid='...'))
        self.set_button_state('refresh', tk.DISABLED)
        self.window._run_background_task(
            lambda: self._execute_connect_in_thread(ssid, authentication, encryption, password),
            on_complete=self.reset_connect_button
        )

    def _execute_connect_in_thread(self, ssid, auth, enc, pwd):
        """Worker function for connection."""
        connect_to_wifi_network(ssid, auth, enc, pwd)
        self.task_queue.put({'type': 'wifi_connect_success', 'ssid': ssid})

    def set_button_state(self, button_name, state, text=None):
        button = getattr(self, f"{button_name}_button", None)
        if button:
            button.config(state=state)
            if text: button.config(text=text)

    def reset_connect_button(self):
        self.set_button_state('connect', tk.NORMAL, get_string('wifi_button_connect'))
        self.set_button_state('refresh', tk.NORMAL)

    def _sort_by_column(self, col, reverse):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        def sort_key(item):
            try: return int(item[0].replace('%', ''))
            except (ValueError, AttributeError): return -1
        data.sort(key=sort_key if col == 'signal' else None, reverse=reverse)
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(col, command=lambda: self._sort_by_column(col, not reverse))