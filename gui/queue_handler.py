import tkinter as tk
from tkinter import messagebox
import logging
import os

from .wifi_queue_handler import WifiQueueHandler

logger = logging.getLogger(__name__)

class QueueHandler:
    """
    Handles messages from the background task queue, updating the UI accordingly.
    """
    def __init__(self, context, ui_frames: dict):
        self.context = context
        self.status_var = context.root.status_var
        self.controller = context.main_controller
        self.ui_frames = ui_frames
        self.wifi_handler = WifiQueueHandler(context)
        self.handler_map = self._create_handler_map()

    def _create_handler_map(self):
        return {
            'toggle_success': self._handle_toggle_success,
            'toggle_error': self._handle_toggle_error,
            'diagnostics_update': self._handle_diagnostics_update,
            'wifi_status_update': lambda msg: self.ui_frames['wifi_status'].update_status(msg['data']),
            'status_update': lambda msg: self.status_var.set(msg['text']),
            'speed_update': self._handle_speed_update,
            'reset_stack_success': self._handle_reset_stack_success,
            'reset_stack_error': lambda msg: self._handle_generic_error("resetting network stack", msg['error']),
            'flush_dns_success': self._handle_flush_dns_success,
            'flush_dns_error': lambda msg: self._handle_generic_error("flushing DNS cache", msg['error']),
            'release_renew_success': self._handle_release_renew_success,
            'release_renew_error': lambda msg: self._handle_generic_error("renewing IP address", msg['error']),
            'disconnect_wifi_success': self._handle_disconnect_wifi_success,
            'disconnect_wifi_error': self._handle_disconnect_wifi_error,
            # Generic handlers for Toplevel windows
            'ui_update': self._handle_ui_update,
            'unhandled_error': lambda msg: self._handle_generic_error("in a background task", msg['error']),
            'generic_error': lambda msg: self._handle_generic_error(msg['description'], msg['error']),
            # New handlers for decoupled MainController
            'populate_adapters': lambda msg: self.ui_frames['adapter_list'].populate(msg['data']),
            'clear_details': lambda msg: self.ui_frames['adapter_details'].clear(),
            'update_adapter_details': self._handle_update_adapter_details,
        }

    def process_message(self, message):
        logger.debug("Processing queue message: %s", message.get('type'))
        # First, try to let the specialized Wi-Fi handler process the message.
        if self.wifi_handler.process_message(message):
            return # Message was handled by the Wi-Fi handler.

        # If not handled, try the main handler.
        handler = self.handler_map.get(message.get('type'))
        if handler: # type: ignore
            handler(message) # type: ignore
        else:
            logger.warning("No handler found for queue message type: %s", message['type'])

    def _handle_toggle_success(self, message):
        action = message.get('action', 'changed')
        adapter = message.get('adapter_name', 'adapter')
        self.status_var.set(f"Successfully {action}d '{adapter}'. Refreshing list...")
        self.context.root.after(500, self.controller.refresh_adapter_list)

    def _handle_toggle_error(self, message):
        adapter, action, error = message['adapter_name'], message['action'], message['error']
        logger.error("Failed to toggle adapter '%s' to state '%s'.", adapter, action, exc_info=error)
        self.controller.refresh_adapter_list() # Refresh to show the actual current state

        if hasattr(error, 'code') and error.code == 'WIFI_CONNECTED_DISABLE_FAILED':
            if messagebox.askyesno("Action Required", f"Could not disable '{adapter}' because it is connected to a network.\n\nDo you want to automatically disconnect from Wi-Fi and then disable the adapter?", icon='question'):
                self.status_var.set("Attempting automated two-step action...")
                self.context.action_handler.execute_disconnect_and_disable(adapter)
            else:
                self.status_var.set("Operation cancelled by user.")
        elif "is already" in str(error):
            messagebox.showinfo("Information", str(error))
            self.status_var.set("Operation not needed.")
        else:
            messagebox.showerror("Execution Error", f"Operation failed:\n\n{error}")
            self.status_var.set(f"Failed to change status for '{adapter}'.")

    def _handle_diagnostics_update(self, message):
        self.ui_frames['diagnostics'].update_diagnostics(message['data'])

    def _handle_speed_update(self, message):
        all_speeds = message['data']
        adapter_speeds = self.controller.get_speed_for_selected_adapter(all_speeds)
        
        if adapter_speeds:
            download = adapter_speeds.get('download', 0)
            upload = adapter_speeds.get('upload', 0)
            self.ui_frames['adapter_details'].update_speeds(download, upload)
        else:
            self.ui_frames['adapter_details'].update_speeds(0, 0)

    def _handle_update_adapter_details(self, message):
        self.ui_frames['adapter_details'].update_details(message['data'])
        self.ui_frames['adapter_details'].update_button_states(message['data'].get('admin_state'))

    def _handle_reset_stack_success(self, message):
        messagebox.showinfo("Success", "Network stack has been reset.\nPlease reboot your computer for the changes to take effect.")
        self.status_var.set("Network stack reset. Reboot required.")

    def _handle_flush_dns_success(self, message):
        messagebox.showinfo("Success", "Successfully flushed the DNS resolver cache.")
        self.status_var.set("DNS cache flushed.")

    def _handle_release_renew_success(self, message):
        messagebox.showinfo("Success", "Successfully released and renewed IP addresses. Refreshing adapter list.")
        self.status_var.set("IP addresses renewed.")
        self.controller.refresh_adapter_list()

    def _handle_disconnect_wifi_success(self, message):
        # This can be triggered from main window or wifi window, so check for parent
        parent = self.context.open_windows.get('WifiConnectWindow') or self.context.root
        messagebox.showinfo("Success", "Successfully disconnected from the Wi-Fi network.", parent=parent)
        self.status_var.set("Wi-Fi disconnected.")
        
        # Also refresh the wifi window if it's open
        wifi_window = self.context.open_windows.get('WifiConnectWindow')
        if wifi_window:
            wifi_window.status_label.config(text="Disconnected.")
            wifi_window.available_tab.refresh_list()

    def _handle_disconnect_wifi_error(self, message):
        self._handle_generic_error("disconnecting from Wi-Fi", message['error'])
        self.ui_frames['wifi_status'].disconnect_button.config(state=tk.NORMAL)

    def _handle_generic_error(self, action_description, error):
        # Check for specific, actionable error codes first.
        if hasattr(error, 'code') and error.code == "LOCATION_PERMISSION_DENIED":
            parent_window = self.context.open_windows.get('WifiConnectWindow') or self.context.root
            if messagebox.askyesno("Permission Required", f"{error}\n\nDo you want to open the Location Settings page now?", parent=parent_window):
                os.startfile("ms-settings:privacy-location")
            return

        messagebox.showerror("Error", f"Failed while {action_description}:\n\n{error}")
        self.status_var.set(f"Error {action_description}.")

    def _handle_ui_update(self, message):
        """Executes a function on the UI thread."""
        if callable(message.get('func')):
            message['func']()
