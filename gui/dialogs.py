import tkinter as tk
from tkinter import ttk, messagebox
import logging

from localization import get_string
import app_logic
from .constants import APP_VERSION
from .utils import create_tooltip

logger = logging.getLogger(__name__)

class PublishWindow(tk.Toplevel):
    """
    A dialog window for creating a new GitHub release.
    """
    def __init__(self, context):
        super().__init__(context.root)
        self.context = context
        self.action_handler = self.context.action_handler
        self.parent = self.context.root

        self.title(get_string('publish_title'))
        self.geometry("500x450")
        self.resizable(False, False)

        self.transient(self.parent) # Keep this window on top of the main app
        self._build_ui()
        self._populate_defaults()

        # Center the window relative to the parent
        self.update_idletasks()
        x = self.parent.winfo_x() + (self.parent.winfo_width() // 2) - (self.winfo_width() // 2)
        y = self.parent.winfo_y() + (self.parent.winfo_height() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.grab_set() # Modal behavior

    def _build_ui(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Repository ---
        repo_label = ttk.Label(main_frame, text=get_string('publish_repo'))
        repo_label.grid(row=0, column=0, sticky="w", pady=(0, 2))
        self.repo_var = tk.StringVar()
        self.repo_entry = ttk.Entry(main_frame, textvariable=self.repo_var)
        self.repo_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # --- Version / Tag ---
        version_label = ttk.Label(main_frame, text=get_string('publish_version'))
        version_label.grid(row=2, column=0, sticky="w", pady=(0, 2))
        self.version_var = tk.StringVar()
        self.version_entry = ttk.Entry(main_frame, textvariable=self.version_var)
        self.version_entry.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        create_tooltip(self.version_entry, get_string('publish_version_tooltip'))

        # --- Release Title ---
        title_label = ttk.Label(main_frame, text=get_string('publish_release_title'))
        title_label.grid(row=4, column=0, sticky="w", pady=(0, 2))
        self.title_var = tk.StringVar()
        self.title_entry = ttk.Entry(main_frame, textvariable=self.title_var)
        self.title_entry.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        # --- Release Notes ---
        notes_label = ttk.Label(main_frame, text=get_string('publish_notes'))
        notes_label.grid(row=6, column=0, sticky="w", pady=(0, 2))
        self.notes_text = tk.Text(main_frame, height=8, wrap=tk.WORD, relief=tk.SOLID, borderwidth=1)
        self.notes_text.grid(row=7, column=0, columnspan=2, sticky="nsew", pady=(0, 10))

        # --- Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=8, column=0, columnspan=2, sticky="e", pady=(10, 0))

        self.publish_button = ttk.Button(button_frame, text=get_string('publish_button'), command=self._on_publish)
        self.publish_button.pack(side=tk.RIGHT, padx=(5, 0))
        self.cancel_button = ttk.Button(button_frame, text=get_string('publish_cancel'), command=self._on_close)
        self.cancel_button.pack(side=tk.RIGHT)

        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def _populate_defaults(self):
        """Fetches and sets default values for the form fields."""
        # Set default version and title
        self.version_var.set(f"v{APP_VERSION}")
        self.title_var.set(f"Release v{APP_VERSION}")

        # Fetch repository from git config
        repo_name = app_logic.get_repo_from_git_config()
        if repo_name:
            self.repo_var.set(repo_name)
            logger.info("Automatically detected repository: %s", repo_name)
        else:
            logger.warning("Could not detect repository from git config. User must enter it manually.")

    def _on_publish(self):
        """Callback for the 'Publish' button."""
        repo = self.repo_var.get().strip()
        tag = self.version_var.get().strip()
        title = self.title_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not all([repo, tag, title]):
            messagebox.showwarning(get_string('publish_missing_info'), get_string('publish_missing_info_msg'), parent=self)
            return

        # Delegate the actual publishing logic to the action handler
        self.action_handler.publish_release(repo, tag, title, notes)
        self._on_close()

    def _on_close(self):
        self.grab_release()
        self.destroy()