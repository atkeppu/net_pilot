import tkinter as tk
from tkinter import ttk
import logging
from localization import get_string
from functools import partial
from queue import Empty

# Import helper classes
from .menu_handler import MenuHandler
from .app_context import AppContext

# Import UI components
from .adapter_details_frame import AdapterDetailsFrame
from .adapter_list_frame import AdapterListFrame
from .wifi_status_frame import WifiStatusFrame
from .diagnostics_frame import DiagnosticsFrame
 
# --- Constants for UI timings and defaults ---
QUEUE_POLL_INTERVAL_MS = 100
DIAGNOSTICS_REFRESH_INTERVAL_S = 5
SPEED_POLL_INTERVAL_S = 0.5 # Update speed twice per second for better responsiveness
DEFAULT_PING_TARGET = "8.8.8.8"

logger = logging.getLogger(__name__)

class NetworkManagerApp(tk.Tk):
    def __init__(self, context: AppContext):
        super().__init__()
        self.context = context
        # Set the root window in the context immediately, so other components can use it.
        self.context.root = self

        self._is_closing = False  # Flag to indicate if the app is closing

        self.title(get_string('app_title'))
        self.geometry("550x850")
        try:
            self.iconbitmap('icon.ico')
        except tk.TclError as e:
            logger.warning("icon.ico not found. Skipping icon. Error: %s", e)

        # --- Initialize Core UI and Context Components ---
        # The status_var is a core UI element, so it's created here.
        self.status_var = tk.StringVar(value=get_string('status_initializing'))
        self.ui_frames: dict[str, ttk.Frame] = {}

        # --- Setup UI Components ---
        self._setup_ui_frames(self.ui_frames) # Populate the ui_frames dictionary.

        # --- Initialize Handlers and Controllers ---
        # Pass the root window, frames, and the status_var to the context.
        MenuHandler(self.context).create_menu()

        # --- Finalize UI and Start Application ---
        self._create_status_bar()
        self.after(200, self._initial_load)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

    def _setup_ui_frames(self, ui_frames: dict):
        """Sets up the main UI layout and widgets."""
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        ui_frames['adapter_list'] = AdapterListFrame(main_frame, on_select_callback=lambda index: self.context.main_controller.on_adapter_select(index))
        ui_frames['adapter_list'].pack(fill=tk.BOTH, expand=True, pady=5)
        ui_frames['adapter_details'] = AdapterDetailsFrame(
            main_frame,
            on_connect_callback=partial(self.context.action_handler.network.toggle_adapter, 'enable'),
            on_disconnect_callback=partial(self.context.action_handler.network.toggle_adapter, 'disable'),
            on_status_update_callback=self.status_var.set
        )
        ui_frames['adapter_details'].pack(fill=tk.X, pady=5)

        ui_frames['wifi_status'] = WifiStatusFrame(main_frame, on_disconnect_callback=self.context.action_handler.disconnect_current_wifi)
        ui_frames['wifi_status'].pack(fill=tk.X, pady=5)

        ui_frames['diagnostics'] = DiagnosticsFrame(main_frame)
        ui_frames['diagnostics'].pack(fill=tk.X, pady=5)

    def _create_status_bar(self):
        status_bar = ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=2)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _initial_load(self):
        """Sets the initial loading message and schedules the background tasks to start."""
        self.status_var.set(get_string('status_refreshing_list', default="Refreshing adapter list..."))
        # Schedule the actual background work to start after the UI has had a moment to update.
        self.after(50, self._start_background_tasks)

    def _start_background_tasks(self):
        """Starts the polling manager and the UI queue processing."""
        # The PollingManager will now start itself after a short delay.
        self.context.polling_manager.start_all(DIAGNOSTICS_REFRESH_INTERVAL_S, SPEED_POLL_INTERVAL_S)
        # Start processing the queue for UI updates.
        logger.info("Starting UI queue processing.")
        self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue)

    def _process_queue(self):
        """Process messages from the worker thread queue."""
        try:
            while not self.context.task_queue.empty():
                message = self.context.task_queue.get_nowait()
                self.context.queue_handler.process_message(message)
                self.update_idletasks()

        except Empty:
            pass
        finally:
            # Only reschedule if the application is not in the process of closing
            if not self._is_closing:
                self.after(QUEUE_POLL_INTERVAL_MS, self._process_queue)

    def _on_closing(self):
        """Handles the window close event."""
        self._is_closing = True
        self.destroy()