import queue
import logging
import tkinter as tk

from .action_handler import ActionHandler
from .queue_handler import QueueHandler
from .polling_manager import PollingManager
from .main_controller import MainController
from .constants import APP_VERSION

logger = logging.getLogger(__name__)

class AppContext:
    """
    Acts as the central 'brain' of the application, holding shared state and
    orchestrating the main components (handlers, controllers).
    This non-GUI class decouples the application logic from the main window.
    """
    def __init__(self):
        self.task_queue = queue.Queue()
        self.status_var = None # Will be initialized later
        self.open_windows = {} # Tracks open Toplevel windows
        
        # These will be initialized after the UI is created.
        # MainController is also initialized later as it depends on the full context.
        self.main_controller = None
        self.action_handler = None
        self.queue_handler = None
        self.polling_manager = None
        self.root = None # The main tk.Tk() window

        self.diagnostics_frame = None # Will hold reference to the diagnostics UI frame

    def initialize_components(self, root, ui_frames: dict, status_var: tk.StringVar):
        """
        Initializes all the handler and controller components that depend on UI elements.
        """
        self.root = root
        self.status_var = status_var
        self.diagnostics_frame = ui_frames['diagnostics']

        # Create components that depend on the full context.
        self.main_controller = MainController(task_queue=self.task_queue)
        self.action_handler = ActionHandler(
            context=self,
            get_selected_adapter_name_func=self.main_controller.get_selected_adapter_name
        )
        self.queue_handler = QueueHandler(
            context=self,
            ui_frames=ui_frames
        )
        self.polling_manager = PollingManager(self)

        logger.info("Application context and all components initialized.")

    def get_ping_target(self) -> str:
        """Provides the current ping target from the UI to other components."""
        return self.diagnostics_frame.get_ping_target() if self.diagnostics_frame else "8.8.8.8"

    def get_app_version(self) -> str:
        """Returns the application's version string."""
        return APP_VERSION

    def register_window(self, window_instance):
        """Registers an open Toplevel window instance."""
        window_key = window_instance.__class__.__name__
        self.open_windows[window_key] = window_instance
        logger.info("Window registered: %s", window_key)

    def unregister_window(self, window_instance):
        """Unregisters a Toplevel window instance when it's closed."""
        window_key = window_instance.__class__.__name__
        if window_key in self.open_windows:
            del self.open_windows[window_key]
            logger.info("Window unregistered: %s", window_key)