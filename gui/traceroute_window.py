import tkinter as tk
from tkinter import ttk, messagebox

from app_logic import run_traceroute
from exceptions import NetworkManagerError
from .base_window import BaseTaskWindow


class TracerouteWindow(BaseTaskWindow):
    """A Toplevel window to run and display traceroute results."""

    def __init__(self, context):
        super().__init__(context, title="Trace Route", geometry="600x400")
        self._create_widgets()

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Input frame
        input_frame = ttk.Frame(main_frame)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(input_frame, text="Target:").pack(side=tk.LEFT, padx=(0, 5))
        self.target_var = tk.StringVar(value="8.8.8.8")
        target_entry = ttk.Entry(input_frame, textvariable=self.target_var)
        target_entry.pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.start_button = ttk.Button(input_frame, text="Start", command=self.start_trace)
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
            messagebox.showwarning("Input Required", "Please enter a target host or IP address.", parent=self)
            return

        self.start_button.config(state=tk.DISABLED)
        self.output_text.config(state=tk.NORMAL)
        self.output_text.delete('1.0', tk.END)
        self.output_text.config(state=tk.DISABLED)

        self._run_background_task(self._execute_trace_in_thread, target, on_complete=self.on_trace_done)

    def _execute_trace_in_thread(self, target):
        try:
            for line in run_traceroute(target):
                # Post a UI update function to the main queue
                self.task_queue.put({'type': 'ui_update', 'func': lambda l=line: self.append_line(l)})
        except NetworkManagerError as e:
            # BaseTaskWindow's error handling will catch this and post a generic_error.
            # We can still append the error line for immediate feedback in the output.
            self.task_queue.put({'type': 'ui_update', 'func': lambda err=e: self.append_line(f"\nERROR: {err}\n")})

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
        if self.start_button.winfo_exists():
            self.start_button.config(state=tk.NORMAL)