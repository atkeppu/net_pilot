import tkinter as tk
from tkinter import ttk, messagebox
import logging
import os
import threading
import queue
import time
import sys

# Relative imports since we are in a package
from app_logic import (
    get_adapter_details, set_network_adapter_status_windows, get_network_diagnostics,
    get_raw_network_stats, reset_network_stack, flush_dns_cache, release_renew_ip,
    disconnect_wifi, get_current_wifi_details, create_github_release
)
from logger_setup import get_log_file_path, LOG_FILE_NAME
from exceptions import NetworkManagerError

# Import the window classes from the same package
from .netstat_window import NetstatWindow
from .traceroute_window import TracerouteWindow
from .wifi_window import WifiConnectWindow
from .publish_window import PublishWindow
from .constants import APP_VERSION, APP_AUTHOR, GITHUB_REPO

# --- Constants for UI timings and defaults ---
QUEUE_POLL_INTERVAL_MS = 100
DIAGNOSTICS_REFRESH_INTERVAL_S = 5
SPEED_POLL_INTERVAL_S = 1
DEFAULT_PING_TARGET = "8.8.8.8"

logger = logging.getLogger(__name__)


class NetworkManagerApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NetPilot")
        self.geometry("550x800")
        try:
            # This will fail if icon.ico is not found, but the app will still run.
            self.iconbitmap('icon.ico')
        except tk.TclError as e:
            logger.warning("icon.ico not found. Skipping icon. Error: %s", e)

        self.adapters_data = []
        self.task_queue = queue.Queue()
        self._create_context_menu()
        self._create_menu()
        self._setup_ui()
        self._setup_queue_handlers()
        self.after(200, self._initial_load) # Start loading data after UI is ready and handlers are set

    def _create_context_menu(self):
        """Creates the right-click context menu for copying text."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="Copy", command=self._copy_to_clipboard)
        self.clicked_widget = None

    def _create_menu(self):
        """Creates the main menu bar for the application."""
        menubar = tk.Menu(self)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Reset Network Stack...", command=self._confirm_reset_network_stack)
        tools_menu.add_command(label="Release & Renew IP", command=self._release_renew_ip)
        tools_menu.add_command(label="Trace Route...", command=self._show_traceroute_window)
        tools_menu.add_command(label="Active Connections...", command=self._show_netstat_window)
        tools_menu.add_separator()
        tools_menu.add_command(label="Wi-Fi Networks...", command=self._show_wifi_window)
        tools_menu.add_command(label="Flush DNS Cache", command=self._flush_dns_cache)
        menubar.add_cascade(label="Tools", menu=tools_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Open Log File", command=self._open_log_file)
        help_menu.add_separator()
        help_menu.add_command(label="About...", command=self._show_about_dialog)
        menubar.add_cascade(label="Help", menu=help_menu)
        self.config(menu=menubar)

    def _show_about_dialog(self):
        """Displays the about information box."""
        messagebox.showinfo(
            "About NetPilot",
            f"NetPilot\n\nVersion: {APP_VERSION}\nAuthor: {APP_AUTHOR}"
        )

    def _open_log_file(self):
        """Opens the log file with the default system editor."""
        log_path = get_log_file_path()
        try:
            os.startfile(log_path)
            logger.info("Opened log file: %s", log_path)
        except FileNotFoundError:
            logger.error("Log file not found at: %s", log_path)
            messagebox.showerror("Error", f"Log file not found at:\n{log_path}")
        except Exception as e:
            logger.error("Failed to open log file '%s'.", LOG_FILE_NAME, exc_info=True)
            messagebox.showerror("Error", f"Could not open log file.\n\nError: {e}")

    def _setup_ui(self):
        """Sets up the main UI layout and widgets."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        self._create_adapter_list_frame(main_frame)
        self._create_details_frame(main_frame)
        self._create_wifi_frame(main_frame)
        self._create_diagnostics_frame(main_frame)
        self._create_status_bar()

    def _create_adapter_list_frame(self, parent):

        list_frame = ttk.LabelFrame(parent, text="Available Adapters")
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        self.adapter_listbox = tk.Listbox(list_frame, height=10)
        self.adapter_listbox.bind('<<ListboxSelect>>', self._on_adapter_select)
        self.adapter_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.adapter_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.adapter_listbox.config(yscrollcommand=scrollbar.set)

    def _create_details_frame(self, parent):
        details_frame = ttk.LabelFrame(parent, text="Adapter Details")
        details_frame.pack(fill=tk.X, pady=5)
        
        self.details_labels = {}
        details_to_show = [
            "Description", "MAC Address", "IPv4 Address", "IPv6 Address", "Link Speed (Mbps)",
            "Download Speed", "Upload Speed", "Driver Version", "Driver Date"
        ]
        for i, detail in enumerate(details_to_show):
            ttk.Label(details_frame, text=f"{detail}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(details_frame, text="-", anchor=tk.W)
            value_label.bind("<Button-3>", self._show_context_menu) # Bind right-click
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.details_labels[detail] = value_label
        
        # --- Action buttons for the selected adapter ---
        action_button_frame = ttk.Frame(details_frame)
        action_button_frame.grid(row=len(details_to_show), column=0, columnspan=2, pady=5)
        self.connect_button = ttk.Button(action_button_frame, text="Connect", command=lambda: self.toggle_selected_adapter('enable'), state=tk.DISABLED)
        self.connect_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)
        self.disconnect_button = ttk.Button(action_button_frame, text="Disconnect", command=lambda: self.toggle_selected_adapter('disable'), state=tk.DISABLED)
        self.disconnect_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=5)

    def _create_wifi_frame(self, parent):
        wifi_frame = ttk.LabelFrame(parent, text="Current Wi-Fi Connection")
        wifi_frame.pack(fill=tk.X, pady=5)

        self.wifi_labels = {}
        self.wifi_disconnect_button = ttk.Button(wifi_frame, text="Disconnect", command=self._disconnect_current_wifi, state=tk.DISABLED)
        self.wifi_disconnect_button.grid(row=0, column=2, rowspan=3, padx=10, pady=5, sticky="ns")

        wifi_details_to_show = ["SSID", "Signal", "IP Address"]
        for i, detail in enumerate(wifi_details_to_show):
            ttk.Label(wifi_frame, text=f"{detail}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(wifi_frame, text="N/A", anchor=tk.W)
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.wifi_labels[detail] = value_label
        wifi_frame.grid_columnconfigure(1, weight=1)

    def _create_diagnostics_frame(self, parent):
        diag_frame = ttk.LabelFrame(parent, text="Network Diagnostics")
        diag_frame.pack(fill=tk.X, pady=5)

        self.diag_labels = {}
        diag_to_show = ["Public IP", "Gateway", "Gateway Latency", "External Latency", "DNS Servers"]
        for i, detail in enumerate(diag_to_show):
            ttk.Label(diag_frame, text=f"{detail}:").grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            value_label = ttk.Label(diag_frame, text="Fetching...", anchor=tk.W)
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5, pady=2)
            self.diag_labels[detail] = value_label
        
        # Add entry for custom ping target
        ttk.Label(diag_frame, text="Ping Target:").grid(row=len(diag_to_show), column=0, sticky=tk.W, padx=5, pady=2)
        self.ping_target_var = tk.StringVar(value=DEFAULT_PING_TARGET)
        ping_target_entry = ttk.Entry(diag_frame, textvariable=self.ping_target_var)
        ping_target_entry.grid(row=len(diag_to_show), column=1, sticky=tk.EW, padx=5, pady=2)

    def _create_status_bar(self):
        self.status_var = tk.StringVar(value="Initializing...")
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _initial_load(self):
        """Performs the initial data loading and starts polling."""
        self.status_var.set("Loading initial data...")
        self._start_diagnostic_polling()
        self.refresh_adapter_list()
        self._start_speed_polling()
        self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue) # Start the main queue processor

    def refresh_adapter_list(self):
        """Clears and re-populates the listbox with network adapters."""
        self.status_var.set("Refreshing adapter list...")
        self.update_idletasks()
        self.adapter_listbox.delete(0, tk.END)
        self._clear_details()

        try:
            self.adapters_data = get_adapter_details()
            if not self.adapters_data:
                self.adapter_listbox.insert(tk.END, "No adapters found.")
                self.status_var.set("No network adapters found.")
            else:
                for adapter in self.adapters_data:
                    display_text = f"{adapter.get('Name', 'N/A')} ({adapter.get('admin_state', 'N/A')})"
                    self.adapter_listbox.insert(tk.END, display_text)
                self.status_var.set("Ready. Select an adapter.")
        except NetworkManagerError as e:
            logger.error("Failed to get network adapters.", exc_info=True)
            messagebox.showerror("Error", f"Could not retrieve network adapters:\n\n{e}")
            self.status_var.set("Error fetching adapters.")

    def _on_adapter_select(self, event):
        """Handler for when an adapter is selected in the listbox."""
        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            return

        selected_adapter = self.adapters_data[selected_indices[0]]
        
        # Update the main action button text and state
        current_state = selected_adapter.get('admin_state')
        if current_state == 'Disabled':
            self.connect_button.config(state=tk.NORMAL)
            self.disconnect_button.config(state=tk.DISABLED)
        elif current_state == 'Enabled':
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.NORMAL)
        else:
            self.connect_button.config(state=tk.DISABLED)
            self.disconnect_button.config(state=tk.DISABLED)

        self.details_labels["Description"].config(text=selected_adapter.get('InterfaceDescription', '-'))
        self.details_labels["MAC Address"].config(text=selected_adapter.get('MacAddress', '-'))
        self.details_labels["IPv4 Address"].config(text=selected_adapter.get('IPv4Address') or '-')
        self.details_labels["IPv6 Address"].config(text=selected_adapter.get('IPv6Address') or '-')

        # Update LinkSpeed
        try:
            link_speed_bps = int(selected_adapter.get('LinkSpeed', 0))
            link_speed_mbps = link_speed_bps / 1_000_000 if link_speed_bps else 0
        except (ValueError, TypeError):
            link_speed_mbps = 0

        self.details_labels["Link Speed (Mbps)"].config(text=f"{link_speed_mbps:.0f}")
        self.details_labels["Driver Version"].config(text=selected_adapter.get('DriverVersion', '-'))
        self.details_labels["Driver Date"].config(text=selected_adapter.get('DriverDate', '-'))
        
        # Speeds are updated by a separate poller, set to a waiting state
        self.details_labels["Download Speed"].config(text="0.0 kbps")
        self.details_labels["Upload Speed"].config(text="0.0 kbps")

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
                self.status_var.set(f"Copied '{text_to_copy}' to clipboard.")
            else:
                self.status_var.set("Nothing to copy.")

    def _clear_details(self):
        """Clears all detail labels."""
        for label in self.details_labels.values():
            label.config(text="-")
        self.connect_button.config(state=tk.DISABLED)
        self.disconnect_button.config(state=tk.DISABLED)

    def _start_diagnostic_polling(self):
        """Starts a background thread to continuously poll network diagnostics."""
        for label in self.diag_labels.values():
            label.config(text="Fetching...")
        threading.Thread(target=self._poll_diagnostics, daemon=True).start()

    def _poll_diagnostics(self):
        """Worker function to continuously get diagnostics and put them in the queue."""
        import time
        while True:
            target = self.ping_target_var.get() or "8.8.8.8" # Fallback to default
            diag_data = get_network_diagnostics(external_target=target)
            wifi_data = get_current_wifi_details()
            self.task_queue.put({'type': 'diagnostics_update', 'data': diag_data})
            self.task_queue.put({'type': 'wifi_status_update', 'data': wifi_data})
            time.sleep(DIAGNOSTICS_REFRESH_INTERVAL_S)

    def _update_diag_labels(self, data):
        for key, value in data.items():
            if key in self.diag_labels:
                self.diag_labels[key].config(text=value)

    def _update_wifi_status_labels(self, data):
        """Updates the labels in the Wi-Fi status frame."""
        if data:
            self.wifi_disconnect_button.config(state=tk.NORMAL)
            self.wifi_labels["SSID"].config(text=data.get('ssid', 'N/A'))
            self.wifi_labels["Signal"].config(text=data.get('signal', 'N/A'))
            self.wifi_labels["IP Address"].config(text=data.get('ipv4', 'N/A'))
        else:
            # Not connected or no Wi-Fi adapter
            self.wifi_disconnect_button.config(state=tk.DISABLED)
            self.wifi_labels["SSID"].config(text="Not Connected")
            self.wifi_labels["Signal"].config(text="-")
            self.wifi_labels["IP Address"].config(text="-")

    def _disconnect_current_wifi(self):
        """Handles the Wi-Fi disconnect action from the main window."""
        if messagebox.askyesno("Confirm Disconnect", "Are you sure you want to disconnect from the current Wi-Fi network?"):
            self.status_var.set("Disconnecting from Wi-Fi...")
            self.wifi_disconnect_button.config(state=tk.DISABLED)
            threading.Thread(target=self._execute_disconnect_wifi_in_thread, daemon=True).start()

    def _execute_disconnect_wifi_in_thread(self):
        try:
            disconnect_wifi()
            self.task_queue.put({'type': 'disconnect_wifi_success'})
        except NetworkManagerError as e:
            self.task_queue.put({'type': 'disconnect_wifi_error', 'error': e})

    def _execute_disconnect_and_disable_in_thread(self, adapter_name: str):
        """
        Worker function to first disconnect from Wi-Fi, then disable the specified adapter.
        """
        try:
            self.task_queue.put({'type': 'status_update', 'text': 'Step 1: Disconnecting from Wi-Fi...'})
            disconnect_wifi()
            
            # Actively wait for the disconnection to be confirmed by the system
            import time
            for _ in range(5): # Wait up to 5 seconds
                if get_current_wifi_details() is None:
                    break # Disconnection confirmed
                time.sleep(1)
            else:
                # If the loop finishes without breaking, disconnection was not confirmed
                raise NetworkManagerError("Failed to confirm Wi-Fi disconnection in time.")

            self.task_queue.put({'type': 'status_update', 'text': f"Step 2: Disabling adapter '{adapter_name}'..."})
            set_network_adapter_status_windows(adapter_name, 'disable')

            # Use the existing success message for a consistent experience
            self.task_queue.put({'type': 'toggle_success', 'adapter': adapter_name, 'action': 'disable'})
        except NetworkManagerError as e:
            self.task_queue.put({'type': 'toggle_error', 'error': e, 'adapter': adapter_name, 'action': 'disable'})

    def _start_speed_polling(self):
        """Starts the background thread for polling network speeds."""
        threading.Thread(target=self._poll_network_speeds, daemon=True).start()

    def _poll_network_speeds(self):
        """Worker function to continuously poll speeds and calculate the delta."""
        logger.info("Starting speed polling thread.")
        
        last_stats = {}
        last_time = time.time()
        
        while True:
            try:
                # Wait for the specified interval
                time.sleep(SPEED_POLL_INTERVAL_S)

                current_stats = get_raw_network_stats()
                current_time = time.time()
                time_delta = current_time - last_time

                # Avoid division by zero and skip first run
                if time_delta > 0 and last_stats:
                    calculated_speeds = {}
                    for adapter_name, stats in current_stats.items():
                        if adapter_name in last_stats:
                            last = last_stats[adapter_name]
                            
                            # Calculate bytes transferred during the interval
                            received_delta = stats.get('received', 0) - last.get('received', 0)
                            sent_delta = stats.get('sent', 0) - last.get('sent', 0)

                            # Calculate speed in Bytes per second
                            download_bps = received_delta / time_delta if received_delta > 0 else 0
                            upload_bps = sent_delta / time_delta if sent_delta > 0 else 0
                            
                            calculated_speeds[adapter_name] = {
                                'download': download_bps,
                                'upload': upload_bps
                            }
                    
                    # Send the calculated speeds to the UI thread
                    self.task_queue.put({'type': 'speed_update', 'data': calculated_speeds})
                
                # Update state for the next iteration
                last_stats = current_stats
                last_time = current_time

            except Exception:
                logger.critical("Speed polling thread crashed!", exc_info=True)
                time.sleep(5) # Wait before retrying to avoid spamming logs

    def _update_speed_labels(self, speeds):
        """Updates the speed labels if an adapter is selected."""
        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            return # Don't update if nothing is selected

        selected_adapter_name = self.adapters_data[selected_indices[0]].get('Name')
        adapter_speeds = speeds.get(selected_adapter_name)

        if adapter_speeds:
            download_speed = self._format_speed(adapter_speeds.get('download', 0))
            upload_speed = self._format_speed(adapter_speeds.get('upload', 0))
            self.details_labels["Download Speed"].config(text=download_speed)
            self.details_labels["Upload Speed"].config(text=upload_speed)
        else:
            self.details_labels["Download Speed"].config(text="0.0 kbps")
            self.details_labels["Upload Speed"].config(text="0.0 kbps")

    def _format_speed(self, Bps):
        """Formats speed from Bytes/sec to a readable string (kbps/Mbps)."""
        if Bps < 125000: # Under 1 Mbps (125,000 Bytes/sec)
            return f"{Bps * 8 / 1000:.1f} kbps"
        else:
            return f"{Bps * 8 / 1000000:.2f} Mbps"

    def _execute_toggle_in_thread(self, adapter_name, action):
        """Worker function to be run in a separate thread."""
        try:
            set_network_adapter_status_windows(adapter_name, action)
            self.task_queue.put({'type': 'toggle_success', 'adapter': adapter_name, 'action': action})
        except NetworkManagerError as e:
            self.task_queue.put({'type': 'toggle_error', 'error': e, 'adapter': adapter_name, 'action': action})

    def _setup_queue_handlers(self):
        """Maps queue message types to their handler methods."""
        self.queue_handlers = {
            'toggle_success': self._handle_toggle_success,
            'toggle_error': self._handle_toggle_error,
            'diagnostics_update': lambda msg: self._update_diag_labels(msg['data']),
            'wifi_status_update': lambda msg: self._update_wifi_status_labels(msg['data']),
            'status_update': lambda msg: self.status_var.set(msg['text']),
            'speed_update': lambda msg: self._update_speed_labels(msg['data']),
            'reset_stack_success': self._handle_reset_stack_success,
            'reset_stack_error': lambda msg: self._handle_generic_error("resetting network stack", msg['error']),
            'flush_dns_success': self._handle_flush_dns_success,
            'flush_dns_error': lambda msg: self._handle_generic_error("flushing DNS cache", msg['error']),
            'release_renew_success': self._handle_release_renew_success,
            'release_renew_error': lambda msg: self._handle_generic_error("renewing IP address", msg['error']),
            'disconnect_wifi_success': self._handle_disconnect_wifi_success,
            'disconnect_wifi_error': self._handle_disconnect_wifi_error,
        }

    def _process_queue(self):
        """Process messages from the worker thread queue."""
        try:
            message = self.task_queue.get_nowait()
            handler = self.queue_handlers.get(message['type'])
            if handler:
                handler(message)
            else:
                logger.warning("No handler found for queue message type: %s", message['type'])
            self.update_idletasks()

        except queue.Empty:
            pass # No messages in queue
        finally:
            self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue) # Schedule the next check

    # --- Queue Handler Methods ---

    def _handle_toggle_success(self, message):
        adapter, action = message['adapter'], message['action']
        self.status_var.set(f"Successfully {action}d '{adapter}'. Refreshing...")
        self.after(500, self.refresh_adapter_list)

    def _handle_toggle_error(self, message):
        adapter, action, error = message['adapter'], message['action'], message['error']
        logger.error("Failed to toggle adapter '%s' to state '%s'.", adapter, action, exc_info=error)
        self._on_adapter_select(None) # Re-evaluate button states

        if hasattr(error, 'code') and error.code == 'WIFI_CONNECTED_DISABLE_FAILED':
            if messagebox.askyesno("Action Required", f"Could not disable '{adapter}' because it is connected to a network.\n\nDo you want to automatically disconnect from Wi-Fi and then disable the adapter?", icon='question'):
                self.status_var.set("Attempting automated two-step disconnection...")
                threading.Thread(target=self._execute_disconnect_and_disable_in_thread, args=(adapter,), daemon=True).start()
            else:
                self.status_var.set("Operation cancelled by user.")
        elif "is already" in str(error):
            messagebox.showinfo("Information", str(error))
            self.status_var.set("Operation not needed.")
        else:
            messagebox.showerror("Execution Error", f"Operation failed:\n\n{error}")
            self.status_var.set(f"Failed to change status for '{adapter}'.")

    def _handle_reset_stack_success(self, message):
        messagebox.showinfo("Success", "Network stack has been reset.\nPlease reboot your computer for the changes to take effect.")
        self.status_var.set("Network stack reset. Reboot required.")

    def _handle_flush_dns_success(self, message):
        messagebox.showinfo("Success", "Successfully flushed the DNS resolver cache.")
        self.status_var.set("DNS cache flushed.")

    def _handle_release_renew_success(self, message):
        messagebox.showinfo("Success", "Successfully released and renewed IP addresses. Refreshing adapter list.")
        self.status_var.set("IP addresses renewed.")
        self.refresh_adapter_list()

    def _handle_disconnect_wifi_success(self, message):
        messagebox.showinfo("Success", "Successfully disconnected from the Wi-Fi network.")
        self.status_var.set("Wi-Fi disconnected.")

    def _handle_disconnect_wifi_error(self, message):
        self._handle_generic_error("disconnecting from Wi-Fi", message['error'])
        self.wifi_disconnect_button.config(state=tk.NORMAL) # Re-enable on failure

    def _handle_generic_error(self, action_description, error):
        messagebox.showerror("Error", f"Failed while {action_description}:\n\n{error}")
        self.status_var.set(f"Error {action_description}.")

    def toggle_selected_adapter(self, desired_action: str):
        """Enables or disables the currently selected adapter."""
        selected_indices = self.adapter_listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("Selection Required", "Please select an adapter from the list first.")
            return

        adapter_name = self.adapters_data[selected_indices[0]]['Name']
        
        prompt = f"Are you sure you want to {desired_action} the adapter '{adapter_name}'?"

        if messagebox.askyesno("Confirm Action", prompt):
            # Disable buttons to prevent concurrent operations
            self.connect_button.config(state="disabled")
            self.disconnect_button.config(state="disabled")
            self.status_var.set(f"Attempting to {desired_action} '{adapter_name}'...")
            threading.Thread(target=self._execute_toggle_in_thread, args=(adapter_name, desired_action), daemon=True).start()
        else:
            self.status_var.set("Operation cancelled.")

    def _run_background_task(self, task_func, status_message, success_type, error_type):
        """A generic helper to run a background task and post results to the queue."""
        self.status_var.set(status_message)
        self.update_idletasks()
        
        def worker():
            try:
                task_func()
                self.task_queue.put({'type': success_type})
            except NetworkManagerError as e:
                self.task_queue.put({'type': error_type, 'error': e})
        
        threading.Thread(target=worker, daemon=True).start()

    def _confirm_reset_network_stack(self):
        """Shows a confirmation dialog before resetting the network stack."""
        prompt = "This will reset the network stack (Winsock) and requires a REBOOT.\n\nDo you want to proceed?"
        if messagebox.askyesno("Confirm Network Stack Reset", prompt, icon='warning'):
            self._run_background_task(reset_network_stack, "Resetting network stack...", 'reset_stack_success', 'reset_stack_error')

    def _flush_dns_cache(self):
        """Triggers the DNS cache flush operation."""
        self._run_background_task(flush_dns_cache, "Flushing DNS cache...", 'flush_dns_success', 'flush_dns_error')

    def _release_renew_ip(self):
        """Triggers the IP release/renew operation."""
        self._run_background_task(release_renew_ip, "Releasing and renewing IP address...", 'release_renew_success', 'release_renew_error')

    def _show_netstat_window(self):
        """Opens the Netstat window."""
        NetstatWindow(self)

    def _show_traceroute_window(self):
        """Opens the Traceroute window."""
        TracerouteWindow(self)

    def _show_wifi_window(self):
        """Opens the Wi-Fi connection window."""
        WifiConnectWindow(self)

    def _show_publish_dialog(self):
        """
        Opens the GitHub publish dialog window.
        """
        PublishWindow(self)