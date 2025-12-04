import tkinter as tk
import threading
from typing import Callable
import logging
from abc import ABC

from exceptions import NetworkManagerError

QUEUE_POLL_INTERVAL_MS = 100

class BaseTaskWindow(tk.Toplevel, ABC):
    """
    An abstract base class for Toplevel windows that run background tasks.

    It encapsulates the common logic for using a queue to communicate between
    a background worker thread and the Tkinter UI thread, ensuring the UI
    remains responsive.
    """
    def __init__(self, context, title: str, geometry: str):
        super().__init__(context.root)
        self.context = context
        self.task_queue = context.task_queue # Use the main application queue
        self.logger = logging.getLogger(self.__class__.__name__)

        self.title(title)
        self.geometry(geometry)
        self.transient(context.root)
        self.grab_set()

        # Register the window with the context and handle its closing
        self.context.register_window(self)
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _run_background_task(self, task_func: Callable, *args, on_complete: Callable | None = None, **kwargs):
        """Runs a given function in a background thread."""
        def worker():
            try:
                task_func(*args, **kwargs)
            except NetworkManagerError as e:
                # Handle known application errors by posting a specific error message.
                self.logger.warning("A known error occurred in background task: %s", e)
                self.task_queue.put({'type': 'generic_error', 'description': 'performing background task', 'error': e})
            except Exception as e:
                # Put any unhandled exception into the queue for the UI thread to handle
                self.logger.error("Unhandled exception in background task.", exc_info=True)
                self.task_queue.put({'type': 'unhandled_error', 'error': e})
            finally:
                # Optionally, run a completion callback on the UI thread.
                # This is useful for re-enabling buttons, etc.
                if on_complete and callable(on_complete):
                    self.task_queue.put({'type': 'ui_update', 'func': on_complete})

        threading.Thread(target=worker, daemon=True).start()

    def destroy(self):
        """Overrides the default destroy to unregister the window first."""
        self.logger.info("Destroying and unregistering window.")
        self.context.unregister_window(self)
        super().destroy()