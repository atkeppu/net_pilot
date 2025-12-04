import tkinter as tk
from tkinter import ttk, messagebox
import os

from app_logic import create_github_release
from exceptions import NetworkManagerError
from .base_window import BaseTaskWindow

# Import constants from the central constants file
from .constants import APP_VERSION, GITHUB_REPO, APP_NAME


class PublishWindow(BaseTaskWindow):
    """
    A Toplevel window for creating a new GitHub release.
    """
    def __init__(self, context):
        super().__init__(context, title="Publish to GitHub", geometry="450x350")

        self._create_widgets()

    def _create_widgets(self):
        """Creates and places all UI widgets in the window."""
        frame = ttk.Frame(self, padding="10")
        frame.pack(fill=tk.BOTH, expand=True)

        # --- Configuration ---
        asset_path = os.path.join("dist", f"{APP_NAME}.exe")

        # --- Dialog content ---
        ttk.Label(frame, text="You are about to create a new release on GitHub.").pack(pady=5)

        info_text = (
            f"Repository: {GITHUB_REPO}\n"
            f"Version Tag: v{APP_VERSION}\n"
            f"Asset to Upload: {asset_path}"
        )
        ttk.Label(frame, text=info_text, justify=tk.LEFT).pack(pady=10, anchor=tk.W)

        if not os.path.exists(asset_path):
            warning_label = ttk.Label(
                frame,
                text=f"Info: Asset file not found at '{asset_path}'.\nRelease will be created without it.",
                foreground="orange"
            )
            warning_label.pack(pady=5)
        
        ttk.Label(frame, text="Release Notes (optional):").pack(anchor=tk.W)
        self.notes_text = tk.Text(frame, height=4, width=50)
        self.notes_text.pack(pady=5, fill=tk.X, expand=True)
        self.notes_text.insert("1.0", f"Official release of version {APP_VERSION}.")

        # --- Status and Action Buttons ---
        self.status_label = ttk.Label(frame, text="Ready to publish.")
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        button_frame = ttk.Frame(frame)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        self.publish_button = ttk.Button(button_frame, text="Publish Release", command=self._do_publish)
        self.publish_button.pack(side=tk.RIGHT)
        
        ttk.Button(button_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)

    def _do_publish(self):
        """Handles the actual publishing logic."""
        notes = self.notes_text.get("1.0", tk.END).strip()
        self.publish_button.config(state=tk.DISABLED)
        self.status_label.config(text="Publishing, please wait...")
        
        # Use the base class's _run_background_task to run our worker method
        self._run_background_task(self._publish_worker, notes, on_complete=self._on_publish_complete)

    def _publish_worker(self, notes: str):
        """The actual task to run in a background thread."""
        # The try/except block is now handled by the BaseTaskWindow.
        # We just need to perform the successful action.
        url = create_github_release(APP_VERSION, notes)
        self.task_queue.put({'type': 'ui_update', 'func': lambda: self.handle_publish_success(url)})

    def handle_publish_success(self, url: str):
        """UI update on successful publish."""
        messagebox.showinfo("Success", f"Successfully created release!\n\nURL: {url}", parent=self)
        self.destroy()

    def _on_publish_complete(self):
        """Re-enables the publish button and resets status on completion (especially on error)."""
        self.publish_button.config(state=tk.NORMAL)
        self.status_label.config(text="Publishing failed.")