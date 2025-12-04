import tkinter as tk
from tkinter import messagebox
import os
import logging

from logger_setup import get_log_file_path, LOG_FILE_NAME
from .constants import APP_VERSION, APP_AUTHOR

logger = logging.getLogger(__name__)

class MenuHandler:
    """Handles the creation and callbacks for the main application menu."""
    def __init__(self, app, action_handler):
        self.app = app
        self.action_handler = action_handler

        # Define the menu structure as data
        self.menu_structure = [
            {
                "label": "Tools",
                "items": [
                    {"label": "Reset Network Stack...", "command": self.action_handler.confirm_reset_network_stack},
                    {"label": "Release & Renew IP", "command": self.action_handler.release_renew_ip},
                    {"label": "Flush DNS Cache", "command": self.action_handler.flush_dns_cache},
                    {"type": "separator"},
                    {"label": "Active Connections...", "command": self.action_handler.show_netstat_window},
                    {"label": "Trace Route...", "command": self.action_handler.show_traceroute_window},
                    {"label": "Wi-Fi Networks...", "command": self.action_handler.show_wifi_window},
                    {"type": "separator"},
                    {"label": "Publish Release...", "command": self.action_handler.show_publish_dialog},
                ]
            },
            {
                "label": "Help",
                "items": [
                    {"label": "Open Log File", "command": self._open_log_file},
                    {"type": "separator"},
                    {"label": "About...", "command": self._show_about_dialog},
                ]
            }
        ]

    def create_menu(self):
        """Creates the main menu bar for the application."""
        menubar = tk.Menu(self.app)
        self._build_menu_from_data(menubar, self.menu_structure)
        self.app.config(menu=menubar)

    def _build_menu_from_data(self, parent_menu, menu_data):
        """Recursively builds a menu from a data structure."""
        for menu_item in menu_data:
            if menu_item.get("items"):  # This is a cascade menu
                new_menu = tk.Menu(parent_menu, tearoff=0)
                self._build_menu_from_data(new_menu, menu_item["items"])
                parent_menu.add_cascade(label=menu_item["label"], menu=new_menu)
            elif menu_item.get("type") == "separator":
                parent_menu.add_separator()
            else:  # This is a command item
                parent_menu.add_command(label=menu_item["label"], command=menu_item.get("command"))

    def _show_about_dialog(self):
        """Displays the about information box."""
        messagebox.showinfo("About NetPilot", f"NetPilot\n\nVersion: {APP_VERSION}\nAuthor: {APP_AUTHOR}")

    def _open_log_file(self):
        """Opens the log file with the default system editor."""
        log_path = get_log_file_path()
        try:
            os.startfile(log_path)
            logger.info("Opened log file: %s", log_path)
        except FileNotFoundError:
            messagebox.showerror("Error", f"Log file not found at:\n{log_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Could not open log file.\n\nError: {e}")