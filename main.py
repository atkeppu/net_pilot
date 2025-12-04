import sys
import tkinter as tk
from tkinter import messagebox
import logging

from logic.system import is_admin
from gui.main_window import NetworkManagerApp, AppContext
from logger_setup import setup_logging

def _show_startup_error_and_exit(title: str, message: str):
    """Displays a critical error message during startup and exits the application."""
    # Create a hidden root window for the messagebox to prevent visual glitches.
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror(title, message)
    root.destroy()
    sys.exit(1)

def _run_pre_flight_checks():
    """Performs critical startup checks before initializing the UI."""
    logging.info("Performing pre-flight checks...")
    if sys.platform != "win32":
        logging.error("Unsupported OS detected: %s", sys.platform)
        _show_startup_error_and_exit("Unsupported OS", "This application is designed for Windows only.")

    if not is_admin():
        logging.warning("Application not running with admin rights.")
        _show_startup_error_and_exit("Admin Rights Required", "This application requires administrative privileges. Please run as administrator.")
    logging.info("Pre-flight checks passed. Initializing main application.")

def main():
    """Main function to run the application."""
    setup_logging()
    logging.info("Application starting up.")

    try:
        _run_pre_flight_checks()
        context = AppContext()
        app = NetworkManagerApp(context)
        app.mainloop()
        logging.info("Application shut down gracefully.")
    except tk.TclError as e:
        logging.critical("A critical UI error occurred.", exc_info=True)
        messagebox.showerror("UI Error", f"A critical error occurred with the user interface components. Please check the log file.\n\nError: {e}")
    except Exception as e:
        logging.critical("An unhandled exception occurred in the main application loop.", exc_info=True)
        messagebox.showerror("Fatal Error", "A critical error occurred and the application must close. Please check the log file for details.")

if __name__ == "__main__":
    main()