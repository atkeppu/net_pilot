import tkinter as tk
from tkinter import messagebox
import logging
import sys
import os

import logger_setup
from localization import initialize_language, get_string, set_language
from logic.system import is_admin, relaunch_as_admin
from gui.main_window import NetworkManagerApp
from gui.app_context import AppContext

def main():
    """Main entry point for the application."""
    # --- 1. Initial Setup ---
    # Set up logging as the very first thing.
    log_file_path = logger_setup.setup_logging()
    logger = logging.getLogger(__name__)
    logger.info("-----------------------------------------------------")
    logger.info("Application starting up.")

    # Initialize language settings
    initialize_language()

    # --- 2. Pre-flight Checks ---
    logger.info("Performing pre-flight checks...")
    if sys.platform != "win32":
        logger.critical("Unsupported OS: %s", sys.platform)
        messagebox.showerror(get_string('unsupported_os_title'),
                             get_string('unsupported_os_message'))
        return

    if not is_admin():
        logger.warning(
            "Application not running with admin rights. "
            "Attempting automatic relaunch.")
        try:
            # Directly attempt to relaunch as admin without asking the user.
            # The OS will show a UAC prompt, which the user can accept or deny.
            relaunch_as_admin()
        except Exception as e:
            logger.critical("Failed to relaunch with admin rights.", exc_info=True)
            message = (get_string('relaunch_failed_message') + get_string(
                'log_file_hint', log_file_path=log_file_path))
            messagebox.showerror(get_string('relaunch_failed_title'), message)
        # The current non-admin instance will exit, regardless of whether the
        # relaunch succeeds.
        return

    logger.info("Pre-flight checks passed. Initializing main application.")

    # --- 3. Application Initialization ---
    try:
        # The AppContext holds the shared state and logic handlers.
        context = AppContext()

        # Initialize core components that depend on the UI being created.
        # This must be done after the app and its frames are instantiated
        # but before the mainloop starts.
        app = NetworkManagerApp(context)
        context.initialize_components(app, app.ui_frames, app.status_var)

        # Start the Tkinter event loop.
        app.mainloop()

    except Exception as e:
        logger.critical("An unhandled exception occurred in the main application.",
                        exc_info=True)
        message = (get_string('fatal_error_message') + get_string(
            'log_file_hint', log_file_path=log_file_path))
        messagebox.showerror(get_string('fatal_error_title'), message)
    finally:
        logger.info("Application shut down gracefully.\n")

if __name__ == "__main__":
    main()