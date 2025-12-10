import tkinter as tk
from tkinter import messagebox
import threading
import logging
from pathlib import Path
from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from .app_context import AppContext

import app_logic
from localization import get_string
from exceptions import NetworkManagerError

# Import window classes to avoid circular imports
from .netstat_window import NetstatWindow
from .traceroute_window import TracerouteWindow
from publish_dialog import PublishDialog
from .wifi_window import WifiConnectWindow

logger = logging.getLogger(__name__)

class BaseActionHandler:
    """Base class for action handlers providing common functionality."""
    def __init__(self, context: 'AppContext', get_selected_adapter_name_func: Callable[[], str | None]):
        self.context = context
        self.get_selected_adapter_name_func = get_selected_adapter_name_func
        self.app_logic = app_logic

    def run_background_task(self, task_func, *args, on_complete: Callable | None = None, on_error: Callable | None = None):
        """A generic wrapper to run a function in a background thread."""
        task_name = task_func.__name__
        logger.info("Starting background task: %s", task_name)

        def worker():
            try:
                result = task_func(*args)
                if on_complete:
                    # Pass result to the on_complete callback if it's not None
                    self.context.task_queue.put({'type': 'ui_update', 'func': lambda: on_complete(result)})
                logger.info("Background task '%s' completed successfully.", task_name)
            except NetworkManagerError as e:
                logger.error("A known error occurred in task '%s': %s", task_name, e, exc_info=True)
                self.context.task_queue.put({'type': 'generic_error', 'description': f"running task {task_name}", 'error': e})
                # Still call on_complete in case of a handled error to allow UI cleanup (e.g., re-enabling buttons)
                if on_complete:
                    self.context.task_queue.put({'type': 'ui_update', 'func': on_complete})
                if on_error:
                    self.context.task_queue.put({'type': 'ui_update', 'func': lambda: on_error(e)})
            except Exception as e:
                logger.critical("An unhandled error occurred in background task '%s'.", task_name, exc_info=True)
                self.context.task_queue.put({'type': 'unhandled_error', 'error': e})

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()

class NetworkActionsHandler(BaseActionHandler):
    """Handles core network-related actions."""
    def __init__(self, context: 'AppContext', get_selected_adapter_name_func: Callable[[], str | None]):
        super().__init__(context, get_selected_adapter_name_func)

    def toggle_adapter(self, action: str):
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
        else:
            self.context.root.status_var.set(get_string('status_op_cancelled'))

    def _execute_reset_in_thread(self):
        app_logic.reset_network_stack()
        self.context.task_queue.put({'type': 'reset_stack_success'})

    def flush_dns(self):
        self.run_background_task(self._execute_flush_dns_in_thread)

    def _execute_flush_dns_in_thread(self):
        app_logic.flush_dns_cache()
        self.context.task_queue.put({'type': 'flush_dns_success'})

    def renew_ip(self):
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

class DiagnosticsActionsHandler(BaseActionHandler):
    """Handles actions related to diagnostics and data fetching."""
    def __init__(self, context: 'AppContext', get_selected_adapter_name_func: Callable[[], str | None]):
        super().__init__(context, get_selected_adapter_name_func)

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

class UIWindowsHandler(BaseActionHandler):
    """Handles opening and managing UI windows."""
    def __init__(self, context: 'AppContext', get_selected_adapter_name_func: Callable[[], str | None]):
        super().__init__(context, get_selected_adapter_name_func)

    def open_netstat_window(self):
        NetstatWindow(self.context)

    def open_traceroute_window(self):
        TracerouteWindow(self.context)

    def open_wifi_window(self):
        WifiConnectWindow(self.context)

    def open_publish_dialog(self):
        """Opens the publish dialog."""
        self.context.status_var.set(get_string('publish_checking_auth'))
        is_ok, message = self.app_logic.check_github_cli_auth()
        if is_ok:
            self.context.status_var.set(get_string('publish_ready'))
            PublishDialog(self.context)
        else:
            logger.error("GitHub CLI auth check failed: %s", message)
            self.context.status_var.set(get_string('publish_auth_failed'))
            messagebox.showerror(get_string('publish_auth_failed_title'), message)

class GitHubActionsHandler(BaseActionHandler):
    """Handles actions related to GitHub integration."""
    def __init__(self, context: 'AppContext', get_selected_adapter_name_func: Callable[[], str | None]):
        super().__init__(context, get_selected_adapter_name_func)

    def publish_release(self, repo: str, tag: str, title: str, notes: str, on_complete: Callable | None = None, on_error: Callable | None = None):
        """
        Validates assets and starts the background task for creating a GitHub release.
        
        Args:
            repo: The repository name (e.g., 'owner/repo').
            tag: The git tag for the release (e.g., 'v1.3.1').
            title: The title of the release.
            notes: The release notes content.
            on_complete: An optional callback to run on the UI thread after successful completion.
            on_error: An optional callback to run on the UI thread if an error occurs.
        """
        # Find the assets to upload. The build script places them in the 'dist' folder.
        version = tag.lstrip('v')
        dist_path = self.app_logic.get_project_or_exe_root() / "dist"

        # Find assets dynamically instead of constructing an expected filename.
        # This is more robust if the version is changed in the dialog.
        installer_path = next(dist_path.glob('*-setup.exe'), None)
        exe_path = dist_path / "NetPilot.exe"

        assets_to_upload = []
        # Prioritize the installer. If it exists, upload only that.
        # Otherwise, fall back to uploading the standalone executable.
        if installer_path and installer_path.is_file():
            assets_to_upload.append(str(installer_path))
        elif exe_path.is_file():
            assets_to_upload.append(str(exe_path))

        if not assets_to_upload:
            # Provide a more generic error message since we don't know the exact expected name anymore.
            messagebox.showerror("Asset Not Found", f"Could not find a release file (installer or .exe) to upload in the 'dist' directory.\n\nPlease run the build script first.")
            return

        self.run_background_task(self._execute_publish_in_thread, repo, tag, title, notes, assets_to_upload, on_complete=on_complete, on_error=on_error)

    def _execute_publish_in_thread(self, repo: str, tag: str, title: str, notes: str, asset_paths: list[str] | None = None):
        release_url = app_logic.create_github_release(tag, title, notes, repo, asset_paths)
        
        # After a successful release, update the local VERSION file with the new tag.
        try:
            from logger_setup import get_project_or_exe_root
            version_path = get_project_or_exe_root() / "VERSION"
            new_version = tag.lstrip('v')
            version_path.write_text(new_version, encoding="utf-8")
            logger.info("Successfully updated VERSION file to %s after release.", new_version)
        except (IOError, FileNotFoundError) as e:
            logger.error("Failed to update VERSION file after release: %s", e)
            
        self.context.task_queue.put({'type': 'publish_success', 'url': release_url, 'tag': tag})

    def generate_changelog_and_update_dialog(self, version: str, update_callback: Callable[[str], None]):
        """
        Runs the changelog generation in a background thread and uses a callback
        to update the publish dialog's text widget upon completion.
        """
        self.run_background_task(self._execute_generate_changelog_in_thread, version, update_callback)

    def _execute_generate_changelog_in_thread(self, version: str, update_callback: Callable[[str], None]):
        """
        Worker function that calls the changelog generation logic and then
        schedules the UI update via the queue.
        """
        self.app_logic.generate_changelog(version)
        # Use the centralized path helper to ensure the correct path is used.
        changelog_path = self.app_logic.get_project_or_exe_root() / "CHANGELOG.md"
        changelog_content = changelog_path.read_text(encoding='utf-8')
        self.context.task_queue.put({'type': 'ui_update', 'func': lambda: update_callback(changelog_content)})

class ActionHandler:
    """
    Main facade for all UI actions. It instantiates and delegates to specialized
    sub-handlers for better organization.
    """
    def __init__(self, context, get_selected_adapter_name_func: Callable[[], str | None]):
        self.network = NetworkActionsHandler(context, get_selected_adapter_name_func)
        self.diagnostics = DiagnosticsActionsHandler(context, get_selected_adapter_name_func)
        self.windows = UIWindowsHandler(context, get_selected_adapter_name_func)
        self.github = GitHubActionsHandler(context, get_selected_adapter_name_func)

        # For convenience, expose the generic run_background_task at the top level
        self.run_background_task = self.network.run_background_task

    # Expose methods from sub-handlers for direct access, e.g., self.action_handler.toggle_adapter()
    def __getattr__(self, name):
        if hasattr(self.network, name): return getattr(self.network, name)
        if hasattr(self.diagnostics, name): return getattr(self.diagnostics, name)
        if hasattr(self.windows, name): return getattr(self.windows, name)
        if hasattr(self.github, name): return getattr(self.github, name)
        raise AttributeError(f"'{self.__class__.__name__}' object has no attribute '{name}'")