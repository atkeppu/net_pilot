import tkinter as tk
from tkinter import messagebox
import threading
from typing import Callable

from exceptions import NetworkManagerError

# Import all necessary functions from the app_logic facade
from app_logic import (
    reset_network_stack, flush_dns_cache, release_renew_ip,
    set_network_adapter_status_windows, disconnect_wifi_and_disable_adapter,
    disconnect_wifi
)

from .netstat_window import NetstatWindow
from .traceroute_window import TracerouteWindow
from .wifi_window import WifiConnectWindow
from .publish_window import PublishWindow

class ActionHandler:
    """
    Handles user-initiated actions from the main window,
    such as menu commands and button clicks that trigger background tasks.
    """
    def __init__(self, context, get_selected_adapter_name_func):
        self.context = context
        self.task_queue = context.task_queue
        self.get_selected_adapter_name = get_selected_adapter_name_func

    def _run_background_task(self, task_func: Callable, *args, on_complete: Callable | None = None, **kwargs):
        """
        A generic helper to run a background task in a thread, with centralized error handling.
        This is similar to the implementation in BaseTaskWindow.
        """
        self.context.root.update_idletasks() # Ensure UI is updated before starting task
        def worker():
            try:
                task_func(*args, **kwargs)
            except NetworkManagerError as e:
                self.task_queue.put({'type': 'generic_error', 'description': 'performing action', 'error': e})
            except Exception as e:
                self.task_queue.put({'type': 'unhandled_error', 'error': e})
            finally:
                if on_complete and callable(on_complete):
                    self.task_queue.put({'type': 'ui_update', 'func': on_complete})

        threading.Thread(target=worker, daemon=True).start()

    def confirm_reset_network_stack(self):
        prompt = "This will reset the network stack (Winsock) and requires a REBOOT.\n\nDo you want to proceed?"
        if messagebox.askyesno("Confirm Network Stack Reset", prompt, icon='warning'):
            self.context.root.status_var.set("Resetting network stack...")
            self._run_background_task(self._execute_reset_in_thread)

    def flush_dns_cache(self):
        self.context.root.status_var.set("Flushing DNS cache...")
        self._run_background_task(self._execute_flush_dns_in_thread) # type: ignore

    def release_renew_ip(self):
        self.context.root.status_var.set("Releasing and renewing IP address...")
        self._run_background_task(self._execute_release_renew_in_thread) # type: ignore

    def disconnect_current_wifi(self):
        if messagebox.askyesno("Confirm Disconnect", "Are you sure you want to disconnect from the current Wi-Fi network?"):
            # The button state is handled by the QueueHandler on success/error
            self.context.root.status_var.set("Disconnecting from Wi-Fi...")
            self._run_background_task(self._execute_disconnect_wifi_in_thread)

    def toggle_selected_adapter(self, desired_action: str):
        adapter_name = self.get_selected_adapter_name()
        if not adapter_name:
            messagebox.showwarning("Selection Required", "Please select an adapter from the list first.")
            return

        prompt = f"Are you sure you want to {desired_action} the adapter '{adapter_name}'?"

        if messagebox.askyesno("Confirm Action", prompt):
            self.context.root.status_var.set(f"Attempting to {desired_action} '{adapter_name}'...")
            self._run_background_task(self._execute_toggle_in_thread, adapter_name, desired_action)
        else:
            self.context.root.status_var.set("Operation cancelled.")

    def execute_disconnect_and_disable(self, adapter_name: str):
        """
        Initiates the multi-step workflow to disconnect and then disable an adapter.
        """
        self._run_background_task(self._execute_disconnect_and_disable_in_thread, adapter_name)

    # --- Worker Methods for Background Tasks ---

    def _execute_reset_in_thread(self):
        reset_network_stack()
        self.task_queue.put({'type': 'reset_stack_success'})

    def _execute_flush_dns_in_thread(self):
        flush_dns_cache()
        self.task_queue.put({'type': 'flush_dns_success'})

    def _execute_release_renew_in_thread(self):
        release_renew_ip()
        self.task_queue.put({'type': 'release_renew_success'})

    def _execute_disconnect_wifi_in_thread(self):
        disconnect_wifi()
        self.task_queue.put({'type': 'disconnect_wifi_success'})

    def _execute_toggle_in_thread(self, adapter_name: str, action: str):
        set_network_adapter_status_windows(adapter_name, action)
        self.task_queue.put({'type': 'toggle_success', 'adapter_name': adapter_name, 'action': action})

    def _execute_disconnect_and_disable_in_thread(self, adapter_name: str):
        for status_message in disconnect_wifi_and_disable_adapter(adapter_name):
            self.task_queue.put({'type': 'status_update', 'text': status_message})
        self.task_queue.put({'type': 'toggle_success', 'adapter_name': adapter_name, 'action': 'disable'})

    def show_netstat_window(self): NetstatWindow(self.context)
    def show_traceroute_window(self): TracerouteWindow(self.context)
    def show_wifi_window(self): WifiConnectWindow(self.context)
    def show_publish_dialog(self): PublishWindow(self.context)