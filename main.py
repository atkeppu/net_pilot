import sys
import tkinter as tk
from tkinter import messagebox
import logging

from logic.system import is_admin
from gui.main_window import NetworkManagerApp
from logger_setup import setup_logging

def main():
    """Main function to run the application."""
    # Set up logging as the very first step.
    setup_logging()
    logging.info("Application starting up.")
    
    # Perform pre-flight checks before creating the main window.
    # Create a hidden root window for messageboxes to prevent visual glitches.
    root = tk.Tk()
    root.withdraw() # Hide the root window

    if sys.platform != "win32":
        logging.error("Unsupported OS detected: %s", sys.platform)
        messagebox.showerror("Unsupported OS", "This application is designed for Windows only.")
        root.destroy()
        return

    if not is_admin():
        logging.warning("Application not running with admin rights.")
        messagebox.showerror("Admin Rights Required", "This application requires administrative privileges. Please run as administrator.")
        root.destroy()
        return
    
    # If checks pass, destroy the temporary root and run the main app.
    root.destroy()
    logging.info("Pre-flight checks passed. Initializing main application.")

    try:
        app = NetworkManagerApp()
        app.mainloop()
        logging.info("Application shut down gracefully.")
    except Exception as e:
        logging.critical("An unhandled exception occurred in the main application loop.", exc_info=True)
        messagebox.showerror("Fatal Error", f"A critical error occurred. Please check the log file for details.\n\nError: {e}")

if __name__ == "__main__":
    main()