import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import queue
import os

from app_logic import (
    list_wifi_networks, get_current_wifi_details, connect_to_wifi_network,
    disconnect_wifi, get_saved_wifi_profiles, connect_with_profile_name,
    delete_wifi_profile
)
from exceptions import NetworkManagerError

# --- Constants for Queue Message Types ---
LIST_SUCCESS = 'list_success'
LIST_ERROR = 'list_error'
CONNECT_SUCCESS = 'connect_success'
CONNECT_ERROR = 'connect_error'
DISCONNECT_SUCCESS = 'disconnect_success'
DISCONNECT_ERROR = 'disconnect_error'
SAVED_PROFILES_SUCCESS = 'saved_profiles_success'
SAVED_PROFILES_ERROR = 'saved_profiles_error'
DELETE_PROFILE_SUCCESS = 'delete_profile_success'
DELETE_PROFILE_ERROR = 'delete_profile_error'

# --- UI Constants ---
QUEUE_POLL_INTERVAL_MS = 100


class WifiConnectWindow(tk.Toplevel):
    """A Toplevel window to browse and connect to Wi-Fi networks."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Wi-Fi Networks")
        self.geometry("800x500")

        self.transient(master)
        self.grab_set()

        self.wifi_data = []
        self.queue = queue.Queue()

        self._create_widgets()
        self._setup_queue_handlers()
        self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue)
        self.refresh_available_wifi_list()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        available_tab = ttk.Frame(notebook)
        saved_tab = ttk.Frame(notebook)
        notebook.add(available_tab, text="Available Networks")
        notebook.add(saved_tab, text="Saved Profiles")
        notebook.bind("<<NotebookTabChanged>>", self._on_tab_change)

        self._create_available_networks_tab(available_tab)
        self._create_saved_profiles_tab(saved_tab)

        bottom_frame = ttk.Frame(self)
        bottom_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        self.status_label = ttk.Label(bottom_frame, text="Select a network...")
        self.status_label.pack(side=tk.LEFT, expand=True, fill=tk.X)

    def _create_available_networks_tab(self, parent_frame):
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('ssid', 'signal', 'auth', 'encryption')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.heading('ssid', text='SSID', command=lambda: self._sort_by_column(self.tree, 'ssid', False))
        self.tree.heading('signal', text='Signal', command=lambda: self._sort_by_column(self.tree, 'signal', True))
        self.tree.heading('auth', text='Authentication', command=lambda: self._sort_by_column(self.tree, 'auth', False))
        self.tree.heading('encryption', text='Encryption', command=lambda: self._sort_by_column(self.tree, 'encryption', False))
        self.tree.column('ssid', width=200)
        self.tree.column('signal', width=80, anchor=tk.CENTER)
        self.tree.column('auth', width=150)
        self.tree.column('encryption', width=100)
        self.tree.bind('<<TreeviewSelect>>', self._on_network_select)
        self.tree.bind('<Double-1>', lambda e: self.connect_to_network()) # Double-click to connect
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.connect_frame = ttk.LabelFrame(parent_frame, text="Connect to Selected Network")
        self.connect_frame.pack(fill=tk.X)

        ttk.Label(self.connect_frame, text="Password:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.password_var = tk.StringVar()
        self.password_entry = ttk.Entry(self.connect_frame, textvariable=self.password_var, show="*")
        self.password_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.EW)
        self.connect_frame.grid_columnconfigure(1, weight=1)

        action_frame = ttk.Frame(parent_frame)
        action_frame.pack(fill=tk.X)
        self.connect_button = ttk.Button(action_frame, text="Connect", command=self.connect_to_network, state=tk.DISABLED)
        self.disconnect_button = ttk.Button(action_frame, text="Disconnect", command=self.disconnect_from_wifi)
        self.disconnect_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.connect_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.refresh_button = ttk.Button(action_frame, text="Refresh", command=self.refresh_available_wifi_list)
        self.refresh_button.pack(side=tk.RIGHT)

        self.connect_frame.pack_forget()

    def _create_saved_profiles_tab(self, parent_frame):
        tree_frame = ttk.Frame(parent_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('ssid', 'password')
        self.saved_tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.saved_tree.heading('ssid', text='SSID (Profile Name)')
        self.saved_tree.heading('password', text='Password')
        self.saved_tree.column('ssid', width=250)
        self.saved_tree.column('password', width=300)
        self.saved_tree.bind('<Double-1>', lambda e: self._connect_to_saved_profile()) # Double-click to connect
        self.saved_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.saved_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.saved_tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(parent_frame)
        button_frame.pack(fill=tk.X, pady=5)
        export_button = ttk.Button(button_frame, text="Export to File...", command=self._export_saved_profiles)
        export_button.pack(side=tk.LEFT)

        copy_button = ttk.Button(button_frame, text="Copy Password", command=self._copy_selected_password)
        copy_button.pack(side=tk.RIGHT)
        delete_button = ttk.Button(button_frame, text="Delete Profile", command=self._delete_selected_profile)
        delete_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.saved_connect_button = ttk.Button(button_frame, text="Connect", command=self._connect_to_saved_profile)
        self.saved_connect_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.saved_disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self.disconnect_from_wifi)
        self.saved_disconnect_button.pack(side=tk.RIGHT, padx=(0, 5))

    def _on_tab_change(self, event):
        selected_tab = event.widget.index(event.widget.select())
        if selected_tab == 1:
            self.refresh_saved_profiles_list()

    def refresh_available_wifi_list(self):
        self.status_label.config(text="Scanning for Wi-Fi networks...")
        self._set_buttons_state(tk.DISABLED, self.refresh_button, self.connect_button)
        
        def task():
            return {
                'data': list_wifi_networks(),
                'current_ssid': (get_current_wifi_details() or {}).get('ssid')
            }
        
        self._run_background_task(task, LIST_SUCCESS, LIST_ERROR)

    def refresh_saved_profiles_list(self):
        self.status_label.config(text="Fetching saved profiles...")
        self._run_background_task(get_saved_wifi_profiles, SAVED_PROFILES_SUCCESS, SAVED_PROFILES_ERROR)

    def _set_buttons_state(self, state, *buttons):
        """Helper to set the state of multiple buttons."""
        for button in buttons:
            if button:
                button.config(state=state)

    def _on_network_select(self, event):
        selected_item = self.tree.focus()
        if not selected_item:
            return
        internal_id = int(selected_item)
        network = self.wifi_data[internal_id]
        self.status_label.config(text=f"Selected: {network['ssid']}")
        self.connect_button.config(state=tk.NORMAL)
        if network.get('authentication', '').lower() != 'open':
            self.connect_frame.pack(fill=tk.X, pady=5)
            self.password_entry.focus()
        else:
            self.connect_frame.pack_forget()

    def connect_to_network(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a network from the list to connect.", parent=self)
            return
        internal_id = int(selected_item)
        network = self.wifi_data[internal_id]
        ssid = network['ssid']
        password = self.password_var.get() if network.get('authentication', '').lower() != 'open' else None
        self.status_label.config(text=f"Connecting to {ssid}...")
        self._set_buttons_state(tk.DISABLED, self.connect_button, self.refresh_button)
        self.connect_button.config(text="Connecting...")
        
        task = lambda: connect_to_wifi_network(ssid, password)
        self._run_background_task(task, CONNECT_SUCCESS, CONNECT_ERROR, ssid=ssid)

    def disconnect_from_wifi(self):
        if messagebox.askyesno("Confirm Disconnect", "Are you sure you want to disconnect from the current Wi-Fi network?", parent=self):
            self.status_label.config(text="Disconnecting...")
            self._set_buttons_state(tk.DISABLED, self.disconnect_button, self.saved_disconnect_button)
            self._run_background_task(disconnect_wifi, DISCONNECT_SUCCESS, DISCONNECT_ERROR)

    def _connect_to_saved_profile(self):
        selected_item = self.saved_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a profile to connect to.", parent=self)
            return
        item = self.saved_tree.item(selected_item)
        profile_name = item['values'][0]
        self.status_label.config(text=f"Connecting using profile '{profile_name}'...")
        self.saved_connect_button.config(state=tk.DISABLED, text="Connecting...")
        
        task = lambda: connect_with_profile_name(profile_name)
        self._run_background_task(task, CONNECT_SUCCESS, CONNECT_ERROR, ssid=profile_name)

    def _delete_selected_profile(self):
        selected_item = self.saved_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a profile to delete.", parent=self)
            return
        item = self.saved_tree.item(selected_item)
        profile_name = item['values'][0]
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the profile '{profile_name}'?", icon='warning', parent=self):
            self.status_label.config(text=f"Deleting profile '{profile_name}'...")
            
            task = lambda: delete_wifi_profile(profile_name)
            self._run_background_task(task, DELETE_PROFILE_SUCCESS, DELETE_PROFILE_ERROR, profile_name=profile_name)

    def _export_saved_profiles(self):
        if not self.saved_tree.get_children():
            messagebox.showwarning("No Data", "There are no saved profiles to export.", parent=self)
            return
        filepath = filedialog.asksaveasfilename(
            title="Save Wi-Fi Profiles",
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            initialfile="wifi_profiles.txt"
        )
        if not filepath:
            return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Saved Wi-Fi Profiles\n" + "=" * 30 + "\n\n")
                for item_id in self.saved_tree.get_children():
                    item = self.saved_tree.item(item_id)
                    ssid, password = item['values']
                    f.write(f"SSID:     {ssid}\nPassword: {password}\n\n")
            messagebox.showinfo("Export Successful", f"Successfully exported profiles to:\n{filepath}", parent=self)
        except IOError as e:
            messagebox.showerror("Export Failed", f"An error occurred while writing to the file:\n{e}", parent=self)

    def _copy_selected_password(self):
        selected_item = self.saved_tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a profile from the list first.", parent=self)
            return
        item = self.saved_tree.item(selected_item)
        password = item['values'][1]
        if password and "N/A" not in password and "(" not in password:
            self.clipboard_clear()
            self.clipboard_append(password)
            self.status_label.config(text=f"Password for '{item['values'][0]}' copied to clipboard.")

    def _sort_by_column(self, treeview, col, reverse):
        """Sorts a treeview column when the header is clicked."""
        # Get data from the column
        data = [(treeview.set(child, col), child) for child in treeview.get_children('')]

        # Handle special sorting for signal strength (numeric)
        if col == 'signal':
            # Convert '95%' to integer 95 for sorting
            def sort_key(item):
                try:
                    return int(item[0].replace('%', ''))
                except (ValueError, AttributeError):
                    return -1 # Put non-numeric values at the bottom
            data.sort(key=sort_key, reverse=reverse)
        else:
            data.sort(reverse=reverse)

        for index, (val, child) in enumerate(data):
            treeview.move(child, '', index)
        
        treeview.heading(col, command=lambda: self._sort_by_column(treeview, col, not reverse))

    def _run_background_task(self, task_func, success_type, error_type, **kwargs):
        """A generic helper to run a background task and post results to the queue."""
        def worker():
            try:
                result = task_func()
                # If the task returns data, include it in the message
                if isinstance(result, dict):
                    kwargs.update(result)
                elif result is not None:
                    kwargs['data'] = result
                
                self.queue.put({'type': success_type, **kwargs})
            except NetworkManagerError as e:
                self.queue.put({'type': error_type, 'error': e, **kwargs})
        
        threading.Thread(target=worker, daemon=True).start()

    def _setup_queue_handlers(self):
        """Maps queue message types to their handler methods."""
        self.queue_handlers = {
            LIST_SUCCESS: self._handle_list_success,
            LIST_ERROR: self._handle_list_error,
            CONNECT_SUCCESS: self._handle_connect_success,
            CONNECT_ERROR: self._handle_connect_error,
            DISCONNECT_SUCCESS: self._handle_disconnect_success,
            DISCONNECT_ERROR: self._handle_disconnect_error,
            DELETE_PROFILE_SUCCESS: self._handle_delete_profile_success,
            DELETE_PROFILE_ERROR: self._handle_generic_error("deleting profile"),
            SAVED_PROFILES_SUCCESS: self._handle_saved_profiles_success,
            SAVED_PROFILES_ERROR: self._handle_generic_error("fetching saved profiles"),
        }

    def _process_queue(self):
        try:
            msg = self.queue.get_nowait()
            handler = self.queue_handlers.get(msg['type'])
            if handler:
                handler(msg)
        except queue.Empty:
            pass
        finally:
            self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue)

    # --- Queue Handler Methods ---

    def _handle_list_success(self, msg):
        self.wifi_data = msg['data']
        current_ssid = msg.get('current_ssid')
        self.tree.delete(*self.tree.get_children())
        if not self.wifi_data:
            self.tree.insert('', tk.END, values=("No Wi-Fi networks found.", "", "", ""))
            self.tree.config(selectmode="none") # Prevent selection of the placeholder
        else:
            self.tree.config(selectmode="browse")
            for i, network in enumerate(self.wifi_data):
                ssid = network.get('ssid', 'N/A')
                display_ssid = ssid + " (Connected)" if ssid and ssid == current_ssid else ssid
                self.tree.insert('', tk.END, iid=i, values=(
                    display_ssid, f"{network.get('signal', 'N/A')}%",
                    network.get('authentication', 'N/A'), network.get('encryption', 'N/A')
                ))
        self.status_label.config(text="Scan complete. Select a network.")
        self._set_buttons_state(tk.NORMAL, self.refresh_button, self.disconnect_button, self.saved_disconnect_button)

    def _handle_list_error(self, msg):
        error = msg['error']
        if hasattr(error, 'code') and error.code == "LOCATION_PERMISSION_DENIED":
            if messagebox.askyesno("Permission Required", f"{error}\n\nDo you want to open the Location Settings page now?", parent=self):
                os.startfile("ms-settings:privacy-location")
        else:
            messagebox.showerror("Error", f"Could not list Wi-Fi networks:\n\n{error}", parent=self)
        self.status_label.config(text="Error scanning for networks.")
        self._set_buttons_state(tk.NORMAL, self.refresh_button)

    def _handle_connect_success(self, msg):
        messagebox.showinfo("Success", f"Successfully connected to '{msg['ssid']}'.", parent=self)
        self.status_label.config(text=f"Connected to {msg['ssid']}.")
        self.connect_button.config(text="Connect")
        self.saved_connect_button.config(text="Connect")
        self.refresh_available_wifi_list() # Refresh to show "(Connected)" status

    def _handle_connect_error(self, msg):
        messagebox.showerror("Connection Failed", str(msg['error']), parent=self)
        self.status_label.config(text="Connection failed. Try again.")
        self.connect_button.config(text="Connect", state=tk.NORMAL)
        self.saved_connect_button.config(text="Connect", state=tk.NORMAL)
        self._set_buttons_state(tk.NORMAL, self.refresh_button)

    def _handle_disconnect_success(self, msg):
        messagebox.showinfo("Success", "Successfully disconnected from the Wi-Fi network.", parent=self)
        self.status_label.config(text="Disconnected.")
        self.refresh_available_wifi_list()

    def _handle_disconnect_error(self, msg):
        self._handle_generic_error("disconnecting")(msg)
        self._set_buttons_state(tk.NORMAL, self.disconnect_button, self.saved_disconnect_button)

    def _handle_delete_profile_success(self, msg):
        messagebox.showinfo("Success", f"Profile '{msg['profile_name']}' has been deleted.", parent=self)
        self.refresh_saved_profiles_list()

    def _handle_saved_profiles_success(self, msg):
        self.saved_tree.delete(*self.saved_tree.get_children())
        if not msg['data']:
            self.saved_tree.insert('', tk.END, values=("No saved profiles found.", ""))
            self.saved_tree.config(selectmode="none")
        else:
            self.saved_tree.config(selectmode="browse")
            for profile in msg['data']:
                self.saved_tree.insert('', tk.END, values=(profile['ssid'], profile['password']))
        self.status_label.config(text="Saved profiles loaded.")

    def _handle_generic_error(self, action_description):
        def handler(msg):
            messagebox.showerror("Error", f"Failed while {action_description}:\n\n{msg['error']}", parent=self)
            self.status_label.config(text=f"Error {action_description}.")
        return handler