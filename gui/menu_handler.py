import tkinter as tk
from tkinter import messagebox
import os
import sys
import logging
import ctypes

from localization import set_language, get_string, LANG_CODE_KEY
from logger_setup import get_log_file_path
from logic.system import is_admin
from .constants import APP_VERSION, APP_AUTHOR

logger = logging.getLogger(__name__)

class MenuHandler:
    """Handles the creation and callbacks for the main application menu."""
    def __init__(self, context):
        self.context = context
        self.action_handler = self.context.action_handler
        self.app = context.root

        self.language_var = tk.StringVar(value=get_string(LANG_CODE_KEY, default='en')) # Use a key that returns 'en' or 'fi'
        # Define the menu structure as data
        self.menu_structure = [
            {
                "label": get_string('menu_tools'),
                "items": [
                    {"label": get_string('menu_reset_stack'), "command": self.action_handler.confirm_reset_network_stack},
                    {"label": get_string('menu_release_renew'), "command": self.action_handler.release_renew_ip},
                    {"label": get_string('menu_flush_dns'), "command": self.action_handler.flush_dns_cache},
                    {"type": "separator"},
                    {"label": get_string('menu_connections'), "command": self.action_handler.show_netstat_window},
                    {"label": get_string('menu_traceroute'), "command": self.action_handler.show_traceroute_window},
                    {"label": get_string('menu_wifi'), "command": self.action_handler.show_wifi_window},
                    {"type": "separator"},
                    {
                        "label": get_string('menu_language'),
                        "items": [
                            {"label": get_string('menu_lang_en'), "type": "radiobutton", "variable": self.language_var, "value": "en", "command": self._on_language_change},
                            {"label": get_string('menu_lang_fi'), "type": "radiobutton", "variable": self.language_var, "value": "fi", "command": self._on_language_change},
                        ]
                    },
                    {"type": "separator"},
                    {"label": get_string('menu_publish'), "command": self.action_handler.show_publish_dialog},
                ]
            },
            {
                "label": get_string('menu_help'),
                "items": [
                    {"label": get_string('menu_open_log'), "command": self._open_log_file},
                    {"type": "separator"},
                    {"label": get_string('menu_about'), "command": self._show_about_dialog},
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
            elif menu_item.get("type") == "radiobutton":
                # Correctly add a radiobutton item
                parent_menu.add_radiobutton(label=menu_item["label"], variable=menu_item.get("variable"), value=menu_item.get("value"), command=menu_item.get("command"))
            else:  # This is a command item
                parent_menu.add_command(label=menu_item["label"], command=menu_item.get("command"))




    def _show_about_dialog(self):
        """Displays the about information box."""
        message_content = get_string(
            'about_message_content',
            app_name="NetPilot", version=APP_VERSION, author=APP_AUTHOR
        )
        messagebox.showinfo(get_string('about_title'), message_content)

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

    def _on_language_change(self):
        """Handles the language selection change."""
        new_lang = self.language_var.get()
        # Get current language before changing it
        current_lang = get_string(LANG_CODE_KEY, default='en')

        if new_lang != current_lang:
            set_language(new_lang)
            
            # Ask the user if they want to restart now
            should_restart = messagebox.askyesno(
                get_string('language_restart_prompt_title'),
                get_string('language_restart_prompt_message'),
                parent=self.app
            )

            if should_restart:
                logger.info("User opted to restart after language change.")
                self.app.destroy() # Close the app gracefully
                # Relaunch the application
                # Note: This re-launches with the same privileges.
                # If admin was required, it should already be running as admin.
                os.execv(sys.executable, [sys.executable] + sys.argv)