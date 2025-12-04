import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from app_logic import get_saved_wifi_profiles, connect_with_profile_name, delete_wifi_profile

class SavedProfilesTab(ttk.Frame):
    """
    UI and logic for the 'Saved Profiles' tab in the Wi-Fi window.
    """
    def __init__(self, parent_notebook, window, task_queue, status_label):
        super().__init__(parent_notebook)
        self.window = window
        self.task_queue = task_queue
        self.status_label = status_label

        self._create_widgets()

    def _create_widgets(self):
        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        columns = ('ssid', 'password')
        self.tree = ttk.Treeview(tree_frame, columns=columns, show='headings')
        self.tree.heading('ssid', text='SSID (Profile Name)')
        self.tree.heading('password', text='Password')
        self.tree.column('ssid', width=250); self.tree.column('password', width=300)
        self.tree.bind('<Double-1>', lambda e: self.connect_to_profile())
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, pady=5)
        export_button = ttk.Button(button_frame, text="Export to File...", command=self._export_profiles)
        export_button.pack(side=tk.LEFT)

        copy_button = ttk.Button(button_frame, text="Copy Password", command=self._copy_password)
        delete_button = ttk.Button(button_frame, text="Delete Profile", command=self.delete_profile)
        self.connect_button = ttk.Button(button_frame, text="Connect", command=self.connect_to_profile)
        self.disconnect_button = ttk.Button(button_frame, text="Disconnect", command=self.window.disconnect_from_wifi)
        copy_button.pack(side=tk.RIGHT); delete_button.pack(side=tk.RIGHT, padx=(0, 5))
        self.connect_button.pack(side=tk.RIGHT, padx=(0, 5)); self.disconnect_button.pack(side=tk.RIGHT, padx=(0, 5))

    def refresh_list(self):
        self.status_label.config(text="Fetching saved profiles...")
        self.window._run_background_task(self._execute_refresh_in_thread)

    def _execute_refresh_in_thread(self):
        """Worker function to get saved profiles."""
        data = get_saved_wifi_profiles()
        self.task_queue.put({'type': 'wifi_saved_profiles_success', 'data': data})

    def populate_list(self, profiles_data):
        self.tree.delete(*self.tree.get_children())
        if not profiles_data:
            self.tree.insert('', tk.END, values=("No saved profiles found.", ""))
            self.tree.config(selectmode="none")
        else:
            self.tree.config(selectmode="browse")
            for profile in profiles_data:
                self.tree.insert('', tk.END, values=(profile['ssid'], profile['password']))

    def connect_to_profile(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a profile to connect to.", parent=self.window)
            return
        profile_name = self.tree.item(selected_item)['values'][0]
        self.status_label.config(text=f"Connecting using profile '{profile_name}'...")
        self.set_button_state('connect', tk.DISABLED, "Connecting...")
        self.window._run_background_task(
            lambda: self._execute_connect_in_thread(profile_name),
            on_complete=self.reset_connect_button
        )

    def _execute_connect_in_thread(self, profile_name):
        connect_with_profile_name(profile_name)
        self.task_queue.put({'type': 'wifi_connect_success', 'ssid': profile_name})

    def delete_profile(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a profile to delete.", parent=self.window)
            return
        profile_name = self.tree.item(selected_item)['values'][0]
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the profile '{profile_name}'?", icon='warning', parent=self.window):
            self.status_label.config(text=f"Deleting profile '{profile_name}'...")
            self.window._run_background_task(lambda: self._execute_delete_in_thread(profile_name))

    def _execute_delete_in_thread(self, profile_name):
        delete_wifi_profile(profile_name)
        self.task_queue.put({'type': 'wifi_delete_profile_success', 'profile_name': profile_name})

    def _export_profiles(self):
        if not self.tree.get_children(): return
        filepath = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text Files", "*.txt")], initialfile="wifi_profiles.txt")
        if not filepath: return
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("Saved Wi-Fi Profiles\n" + "=" * 30 + "\n\n")
                for item_id in self.tree.get_children():
                    ssid, password = self.tree.item(item_id)['values']
                    f.write(f"SSID:     {ssid}\nPassword: {password}\n\n")
            messagebox.showinfo("Export Successful", f"Successfully exported profiles to:\n{filepath}", parent=self.window)
        except IOError as e:
            messagebox.showerror("Export Failed", f"An error occurred while writing to the file:\n{e}", parent=self.window)

    def _copy_password(self):
        selected_item = self.tree.focus()
        if not selected_item: return
        item = self.tree.item(selected_item)
        password = item['values'][1]
        if password and "N/A" not in password and "(" not in password:
            self.window.clipboard_clear(); self.window.clipboard_append(password)
            self.status_label.config(text=f"Password for '{item['values'][0]}' copied to clipboard.")

    def set_button_state(self, button_name, state, text=None):
        button = getattr(self, f"{button_name}_button", None)
        if button: button.config(state=state); button.config(text=text) if text else None

    def reset_connect_button(self):
        self.set_button_state('connect', tk.NORMAL, "Connect")