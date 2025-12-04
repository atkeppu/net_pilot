import tkinter as tk
from tkinter import ttk, messagebox
import queue
import threading

from app_logic import get_active_connections, terminate_process_by_pid
from exceptions import NetworkManagerError


class NetstatWindow(tk.Toplevel):
    """A Toplevel window to display active network connections (netstat)."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Active Network Connections")
        self.geometry("700x500")

        self.transient(master)
        self.grab_set()

        self.queue = queue.Queue()
        self.filter_var = tk.StringVar(value="All")
        self.connections_data = []

        self._create_widgets()
        self.after(100, self._process_queue)
        self.refresh_connections()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Filter Frame ---
        filter_frame = ttk.Frame(main_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(filter_frame, text="Filter by protocol:").pack(side=tk.LEFT, padx=(0, 10))
        ttk.Radiobutton(filter_frame, text="All", variable=self.filter_var, value="All", command=self._apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="TCP", variable=self.filter_var, value="TCP", command=self._apply_filter).pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(filter_frame, text="UDP", variable=self.filter_var, value="UDP", command=self._apply_filter).pack(side=tk.LEFT, padx=5)

        # Treeview for displaying connections
        columns = ('proto', 'local', 'foreign', 'state', 'process')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings')
        self.tree.heading('proto', text='Proto', command=lambda: self._sort_by_column('proto', False))
        self.tree.heading('local', text='Local Address', command=lambda: self._sort_by_column('local', False))
        self.tree.heading('foreign', text='Foreign Address', command=lambda: self._sort_by_column('foreign', False))
        self.tree.heading('state', text='State', command=lambda: self._sort_by_column('state', False))
        self.tree.heading('process', text='Process Name', command=lambda: self._sort_by_column('process', False))
        self.tree.column('proto', width=60, anchor=tk.W)
        self.tree.column('local', width=200, anchor=tk.W)
        self.tree.column('foreign', width=200, anchor=tk.W)
        self.tree.column('state', width=100, anchor=tk.W)
        self.tree.column('process', width=120, anchor=tk.W)

        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scrollbar.set)

        button_frame = ttk.Frame(self)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        self.refresh_button = ttk.Button(button_frame, text="Refresh", command=self.refresh_connections)
        self.refresh_button.pack(side=tk.RIGHT, padx=(5, 0))
        terminate_button = ttk.Button(button_frame, text="Terminate Process", command=self._terminate_selected_process)
        terminate_button.pack(side=tk.RIGHT)

    def refresh_connections(self):
        """Starts a background thread to fetch connection data."""
        self.refresh_button.config(state=tk.DISABLED)
        threading.Thread(target=self._execute_refresh_in_thread, daemon=True).start()

    def _execute_refresh_in_thread(self):
        """Worker function to get connections and put them in the queue."""
        try:
            connections = get_active_connections()
            self.queue.put({'type': 'connections_data', 'data': connections})
        except NetworkManagerError as e:
            self.queue.put({'type': 'error', 'message': f"Could not get active connections:\n\n{e}"})

    def _process_queue(self):
        """Processes messages from the background thread."""
        try:
            message = self.queue.get_nowait()
            if message['type'] == 'connections_data':
                self.connections_data = message['data']
                self._apply_filter()
                self.refresh_button.config(state=tk.NORMAL)
            elif message['type'] == 'error':
                messagebox.showerror("Error", message['message'], parent=self)
                self.refresh_button.config(state=tk.NORMAL)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)

    def _apply_filter(self):
        """Populates the treeview based on the current data and filter."""
        for i in self.tree.get_children():
            self.tree.delete(i)
        
        filter_value = self.filter_var.get()
        for i, conn in enumerate(self.connections_data):
            conn['internal_id'] = i
            if filter_value == "All" or conn.get('Proto', '').lower() == filter_value.lower():
                self.tree.insert('', tk.END, iid=i, values=(
                    conn.get('Proto', 'N/A'),
                    conn.get('Local', 'N/A'),
                    conn.get('Foreign', 'N/A'),
                    conn.get('State', 'N/A'),
                    conn.get('ProcessName', 'N/A')
                ))

    def _sort_by_column(self, col, reverse):
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        data.sort(reverse=reverse)
        for index, (val, child) in enumerate(data):
            self.tree.move(child, '', index)
        self.tree.heading(col, command=lambda: self._sort_by_column(col, not reverse))

    def _terminate_selected_process(self):
        selected_item = self.tree.focus()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select a connection from the list first.", parent=self)
            return

        internal_id = int(selected_item)
        selected_conn = next((c for c in self.connections_data if c.get('internal_id') == internal_id), None)

        if not selected_conn or 'PID' not in selected_conn or 'ProcessName' not in selected_conn:
            messagebox.showerror("Error", "Could not retrieve process information for the selected connection.", parent=self)
            return

        pid = selected_conn['PID']
        process_name = selected_conn['ProcessName']

        prompt = f"Are you sure you want to terminate the process '{process_name}' (PID: {pid})?"
        if messagebox.askyesno("Confirm Termination", prompt, icon='warning', parent=self):
            try:
                terminate_process_by_pid(pid)
                messagebox.showinfo("Success", f"Process '{process_name}' (PID: {pid}) has been terminated.", parent=self)
                self.refresh_connections()
            except NetworkManagerError as e:
                messagebox.showerror("Termination Failed", str(e), parent=self)