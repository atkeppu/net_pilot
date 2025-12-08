import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pathlib import Path
import logging

from gui.base_window import BaseTaskWindow
from gui.utils import create_tooltip
from localization import get_string
from logger_setup import get_project_or_exe_root
from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

class PublishDialog(BaseTaskWindow):
    """
    A dialog window for creating a new GitHub release.
    """
    def __init__(self, context):
        # The parent is automatically handled by BaseTaskWindow via context.root # noqa: E501
        super().__init__(context, title=get_string("publish_title"),
                         geometry="600x550")

        self.repo_var = tk.StringVar()
        self.version_var = tk.StringVar()
        self.title_var = tk.StringVar()

        self._create_widgets()
        self._initialize_fields()
        self._load_changelog()

    def _create_widgets(self):
        """Creates and lays out the widgets for the dialog."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # --- Input Fields ---
        fields_frame = ttk.Frame(main_frame)
        fields_frame.pack(fill=tk.X, pady=(0, 10))
        fields_frame.columnconfigure(1, weight=1)

        # Repository
        ttk.Label(fields_frame, text=get_string('publish_repo')).grid(
            row=0, column=0, sticky="w", padx=5, pady=2)
        repo_entry = ttk.Entry(fields_frame, textvariable=self.repo_var)
        repo_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=2)

        # Version / Tag
        ttk.Label(fields_frame, text=get_string('publish_version')).grid(
            row=1, column=0, sticky="w", padx=5, pady=2)
        version_entry = ttk.Entry(fields_frame, textvariable=self.version_var)
        version_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=2)
        create_tooltip(version_entry, get_string('publish_version_tooltip'))

        # Release Title
        ttk.Label(fields_frame, text=get_string('publish_release_title')).grid(
            row=2, column=0, sticky="w", padx=5, pady=2)
        title_entry = ttk.Entry(fields_frame, textvariable=self.title_var)
        title_entry.grid(row=2, column=1, sticky="ew", padx=5, pady=2)

        # --- Release Notes ---
        ttk.Label(main_frame, text=get_string('publish_notes')).pack(anchor='w', padx=5)
        self.notes_text = scrolledtext.ScrolledText(
            main_frame, wrap=tk.WORD, height=10, relief=tk.SOLID, borderwidth=1)
        self.notes_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # --- Buttons ---
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)

        # --- Progress Bar and Status ---
        self.progress_frame = ttk.Frame(main_frame)
        self.progress_label = ttk.Label(
            self.progress_frame, text="Publishing, please wait...")
        self.progress_bar = ttk.Progressbar(self.progress_frame, mode='indeterminate')

        self.publish_button = ttk.Button(button_frame,
                                         text=get_string('publish_button'),
                                         command=self._on_publish)
        self.publish_button.grid(row=0, column=0, padx=5, sticky="e")

        self.cancel_button = ttk.Button(button_frame,
                                        text=get_string('publish_cancel'),
                                        command=self.destroy)
        self.cancel_button.grid(row=0, column=1, padx=5, sticky="w")

        self.progress_frame.pack(fill=tk.X, pady=(10, 0), padx=5)

    def _initialize_fields(self):
        """Populates the input fields with default values."""
        repo = self.context.action_handler.app_logic.get_repo_from_git_config()
        if repo:
            self.repo_var.set(repo)

        # Read the version directly from the file each time the dialog is opened
        # to ensure it's always up-to-date, especially after running build.py.
        try:
            version_path = get_project_or_exe_root() / "VERSION"
            version = version_path.read_text(encoding="utf-8").strip()
            if version:
                self.version_var.set(f"v{version}")
                self.title_var.set(f"NetPilot v{version}")
        except (FileNotFoundError, IOError) as e:
            logger.warning(
                "Could not read VERSION file to populate publish dialog: %s", e)
            self.version_var.set("v0.0.0")
            self.title_var.set("NetPilot v0.0.0")

    def _load_changelog(self):
        """Finds and loads the content of CHANGELOG.md into the notes text widget."""
        self.notes_text.delete("1.0", tk.END)
        try:
            # Use the robust helper to find the project root.
            changelog_file = get_project_or_exe_root() / "CHANGELOG.md"

            if changelog_file.is_file():
                content = changelog_file.read_text(encoding='utf-8')
                current_tag = self.version_var.get()
                current_version_in_dialog = current_tag.lstrip('v')

                # Check if the changelog title matches the current version in the dialog.
                # If not, it's stale and should be regenerated.
                if f"Muutokset versiossa {current_version_in_dialog}" in content:  # noqa: E501
                    self.notes_text.insert(tk.END, content)
                    self.context.status_var.set(get_string('publish_ready'))
                else:
                    # The changelog is for a different version. Regenerate it.
                    logger.info(
                        "Stale CHANGELOG.md detected. Regenerating for version %s.",
                        current_version_in_dialog)
                    self.context.action_handler.generate_changelog_and_update_dialog(
                        current_version_in_dialog,
                        lambda new_content: self.notes_text.insert(tk.END, new_content)
                    )
            else:
                default_text = (
                    "- CHANGELOG.md not found.\n- Run 'python build.py' to "
                    "generate release notes from recent commits.\n- "
                    "Alternatively, write or paste the release notes manually here.")
                self.notes_text.insert(tk.END, default_text)
        except Exception as e:
            logger.error("Failed to load changelog", exc_info=True)
            self.notes_text.insert(tk.END, f"Error loading changelog:\n{e}")
        finally:
            # Hide progress bar initially
            self.progress_frame.pack_forget()
    
    def _on_publish(self):
        """Handles the logic for publishing the release."""
        repo = self.repo_var.get().strip()
        tag = self.version_var.get().strip()
        title = self.title_var.get().strip()
        notes = self.notes_text.get("1.0", tk.END).strip()

        if not all((repo, tag, title)):
            messagebox.showerror(get_string('publish_missing_info'),
                                 get_string('publish_missing_info_msg'))
            return

        # Show progress bar and disable buttons
        self.progress_frame.pack(fill=tk.X, pady=(10, 0), padx=5)
        self.progress_label.pack(fill=tk.X)
        self.progress_bar.pack(fill=tk.X, pady=(5, 0))
        self.progress_bar.start()

        self.publish_button.config(state=tk.DISABLED)
        self.cancel_button.config(state=tk.DISABLED)

        # The on_complete callback will now be handled by the QueueHandler,
        # which will close this window upon success.
        self.context.action_handler.publish_release(
            repo, tag, title, notes, on_complete=self.destroy)