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

    def destroy(self):
        """Overrides the default destroy to unregister the window first."""
        self.logger.info("Destroying and unregistering window.")
        self.context.unregister_window(self)
        super().destroy()