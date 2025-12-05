import tkinter as tk
from tkinter import ttk, messagebox
import logging

from app_logic import run_traceroute
from localization import get_string
from exceptions import NetworkManagerError
from .base_window import BaseTaskWindow

logger = logging.getLogger(__name__)

class TracerouteWindow(BaseTaskWindow):
    """A Toplevel window to run and display traceroute results."""

    def __init__(self, context):
        super().__init__(context, title=get_string('traceroute_title'), geometry="600x400")
        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(input_frame, text=get_string('traceroute_target')).pack(side=tk.LEFT, padx=(0, 5))
        self.target_var = tk.StringVar(value="8.8.8.8")
        target_entry = ttk.Entry(input_frame, textvariable=self.target_var)
        target_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.start_button = ttk.Button(input_frame, text=get_string('traceroute_button_start'), command=self.start_trace)
        self.start_button.pack(side=tk.LEFT, padx=(5, 0))

        # Output text area
        text_frame = ttk.Frame(main_frame)
        text_frame.pack(fill=tk.BOTH, expand=True)
        self.output_text = tk.Text(text_frame, wrap=tk.WORD, state=tk.DISABLED, height=15)
        self.output_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=self.output_text.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.output_text.config(yscrollcommand=scrollbar.set)

    def start_trace(self):
        target = self.target_var.get()
        if not target:
            messagebox.showwarning(get_string('traceroute_input_required'), get_string('traceroute_input_required_msg'), parent=self)
            return

        self.start_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        # Add an immediate indicator that the process has started.
        self.append_line(get_string('traceroute_starting', target=target))
        self.append_line("-" * 40) # Visual separator

        logger.info("Starting traceroute to target: %s", target)
        self.context.action_handler.run_traceroute(
            target,
            on_complete=self.on_trace_done
        )

    def append_line(self, line: str):
        """Appends a line of text to the output widget."""
        # Prevent errors if the window is closed while the trace is running.
        if not self.output_text.winfo_exists():
            return
        self.output_text.config(state=tk.NORMAL)
        self.output_text.insert(tk.END, line + "\n")
        self.output_text.see(tk.END)  # Auto-scroll
        self.output_text.config(state=tk.DISABLED)

    def on_trace_done(self):
        """Re-enables the start button when the trace is complete."""
        # Check if the widget still exists before trying to configure it.
        # This prevents an error if the window was closed during the trace.
        logger.info("Traceroute task completed.")
        if self.start_button.winfo_exists():
            self.start_button.config(state=tk.NORMAL)