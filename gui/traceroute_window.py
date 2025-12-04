import tkinter as tk
from tkinter import ttk, messagebox
import queue
import threading

from app_logic import run_traceroute
from exceptions import NetworkManagerError


class TracerouteWindow(tk.Toplevel):
    """A Toplevel window to run and display traceroute results."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Trace Route")
        self.geometry("600x400")

        self.transient(master)
        self.grab_set()

        self.queue = queue.Queue()
        self._create_widgets()
        self.after(100, self._process_queue)

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

        threading.Thread(target=self._execute_trace_in_thread, args=(target,), daemon=True).start()

    def _execute_trace_in_thread(self, target):
        try:
            for line in run_traceroute(target):
                self.queue.put({'type': 'line', 'data': line})
        except NetworkManagerError as e:
            self.queue.put({'type': 'error', 'message': str(e)})
        finally:
            # Signal that the process is complete
            self.queue.put({'type': 'done'})

    def _process_queue(self):
        try:
            while True:
                message = self.queue.get_nowait()
                msg_type = message.get('type')

                self.output_text.config(state=tk.NORMAL)
                if msg_type == 'done':
                    self.start_button.config(state=tk.NORMAL)
                elif msg_type == 'line':
                    self.output_text.insert(tk.END, message.get('data', '') + "\n")
                elif msg_type == 'error':
                    self.output_text.insert(tk.END, f"\nERROR: {message.get('message', 'Unknown error')}\n")
                
                self.output_text.see(tk.END)  # Auto-scroll
                self.output_text.config(state=tk.DISABLED)
        except queue.Empty:
            pass
        finally:
            self.after(100, self._process_queue)