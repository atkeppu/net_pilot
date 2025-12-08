import tkinter as tk
from tkinter import messagebox
import threading
import logging
from typing import Callable
import app_logic
from localization import get_string
from exceptions import NetworkManagerError

# Import window classes to avoid circular imports
from .netstat_window import NetstatWindow
from .traceroute_window import TracerouteWindow
from .dialogs import PublishWindow
from .wifi_window import WifiConnectWindow

logger = logging.getLogger(__name__)

class ActionHandler:
    """
    Handles user actions from the UI, typically by running tasks in the background
    and posting results to the main application queue.
    """
    def __init__(self, context, get_selected_adapter_name_func: Callable[[], str | None]):
        self.context = context
        self.get_selected_adapter_name_func = get_selected_adapter_name_func

    def run_background_task(self, task_func, *args, on_complete=None):
        """A generic wrapper to run a function in a background thread."""
        task_name = task_func.__name__
        logger.info("Starting background task: %s", task_name)

        def worker():
            try:
                task_func(*args)
                if on_complete:
                    self.context.task_queue.put({'type': 'ui_update', 'func': on_complete})
                logger.info("Background task '%s' completed successfully.", task_name)
            except NetworkManagerError as e:
                logger.error("A known error occurred in task '%s': %s", task_name, e, exc_info=True)
                self.context.task_queue.put({'type': 'generic_error', 'description': f"running task {task_name}", 'error': e})
                # Still call on_complete in case of a handled error to allow UI cleanup (e.g., re-enabling buttons)
                if on_complete:
                    self.context.task_queue.put({'type': 'ui_update', 'func': on_complete})
            except Exception as e:
                logger.critical("An unhandled error occurred in background task '%s'.", task_name, exc_info=True)
                self.context.task_queue.put({'type': 'unhandled_error', 'error': e})

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

    def toggle_selected_adapter(self, action: str):
        adapter_name = self.get_selected_adapter_name_func()
        if not adapter_name:
            messagebox.showwarning(get_string('netstat_selection_required'), get_string('wifi_select_to_connect'))
            return

        is_enable = action == 'enable'
        
        title_key = 'toggle_confirm_enable_title' if is_enable else 'toggle_confirm_disable_title'
        prompt_key = 'toggle_confirm_enable_prompt' if is_enable else 'toggle_confirm_disable_prompt'
        status_key = 'status_enable_attempt' if is_enable else 'status_disable_attempt'

        title = get_string(title_key)
        prompt = get_string(prompt_key, adapter_name=adapter_name)

        if messagebox.askyesno(title, prompt):
            self.context.root.status_var.set(get_string(status_key, adapter_name=adapter_name))
            self.run_background_task(self._execute_toggle_in_thread, adapter_name, action)
        else:
            self.context.root.status_var.set(get_string('status_op_cancelled'))

    def _execute_toggle_in_thread(self, adapter_name, action):
        app_logic.set_network_adapter_status_windows(adapter_name, action)
        self.context.task_queue.put({'type': 'toggle_success', 'adapter_name': adapter_name, 'action': action})

    def confirm_reset_network_stack(self):
        if messagebox.askyesno(get_string('menu_reset_stack'), "This will reset your network configuration and require a reboot. Are you sure?"):
            self.context.root.status_var.set(get_string('status_reset_attempt'))
            self.run_background_task(self._execute_reset_in_thread)

    def _execute_reset_in_thread(self):
        app_logic.reset_network_stack()
        self.context.task_queue.put({'type': 'reset_stack_success'})

    def flush_dns_cache(self):
        self.run_background_task(self._execute_flush_dns_in_thread)

    def _execute_flush_dns_in_thread(self):
        app_logic.flush_dns_cache()
        self.context.task_queue.put({'type': 'flush_dns_success'})

    def release_renew_ip(self):
        self.run_background_task(self._execute_release_renew_in_thread)

    def _execute_release_renew_in_thread(self):
        app_logic.release_renew_ip()
        self.context.task_queue.put({'type': 'release_renew_success'})

    def disconnect_current_wifi(self):
        if messagebox.askyesno("Confirm Disconnect", "Are you sure you want to disconnect from the current Wi-Fi network?"):
            self.run_background_task(self._execute_disconnect_wifi_in_thread)

    def _execute_disconnect_wifi_in_thread(self):
        app_logic.disconnect_wifi()
        self.context.task_queue.put({'type': 'disconnect_wifi_success'})

    def execute_disconnect_and_disable(self, adapter_name):
        self.run_background_task(self._execute_disconnect_and_disable_in_thread, adapter_name)

    def _execute_disconnect_and_disable_in_thread(self, adapter_name):
        for status_update in app_logic.disconnect_wifi_and_disable_adapter(adapter_name):
            self.context.task_queue.put({'type': 'status_update', 'text': status_update})

    def fetch_active_connections(self, on_complete: Callable | None = None):
        """Fetches active network connections in the background."""
        self.run_background_task(self._execute_fetch_connections_in_thread, on_complete=on_complete)

    def _execute_fetch_connections_in_thread(self):
        data = app_logic.get_active_connections()
        self.context.task_queue.put({'type': 'ui_update', 'func': lambda: self.context.queue_handler.handle_netstat_update(data)})

    def run_traceroute(self, target: str, on_complete: Callable | None = None):
        """Runs traceroute in the background, streaming results."""
        self.run_background_task(self._execute_trace_in_thread, target, on_complete=on_complete)

    def _execute_trace_in_thread(self, target: str):
        for line in app_logic.run_traceroute(target):
            self.context.task_queue.put({'type': 'ui_update', 'func': lambda l=line: self.context.queue_handler.handle_traceroute_update(l)})

    def fetch_wifi_networks(self, on_complete: Callable | None = None):
        """Fetches available Wi-Fi networks in the background."""
        self.run_background_task(self._execute_fetch_wifi_in_thread, on_complete=on_complete)

    def _execute_fetch_wifi_in_thread(self):
        data = app_logic.list_wifi_networks()
        current_ssid = (app_logic.get_current_wifi_details() or {}).get('ssid')
        self.context.task_queue.put({'type': 'wifi_list_success', 'data': data, 'current_ssid': current_ssid})

    def show_netstat_window(self):
        NetstatWindow(self.context)

    def show_traceroute_window(self):
        TracerouteWindow(self.context)

    def show_wifi_window(self):
        WifiConnectWindow(self.context)

    def show_publish_dialog(self):
        self.context.root.status_var.set(get_string('publish_checking_auth'))
        is_ok, message = app_logic.check_github_cli_auth()
        if not is_ok:
            self.context.root.status_var.set(get_string('publish_auth_failed'))
            messagebox.showerror(get_string('publish_auth_failed_title'), message)
        else:
            self.context.root.status_var.set(get_string('publish_ready'))
            PublishWindow(self.context)

    def publish_release(self, repo, tag, title, notes):
        self.run_background_task(self._execute_publish_in_thread, repo, tag, title, notes)

    def _execute_publish_in_thread(self, repo, tag, title, notes):
        release_url = app_logic.create_github_release(tag, title, notes, repo)
        self.context.task_queue.put({'type': 'status_update', 'text': get_string('publish_success', tag=tag)})