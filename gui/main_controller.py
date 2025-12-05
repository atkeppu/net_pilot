import logging
from tkinter import messagebox

from localization import get_string
from app_logic import get_adapter_details
from exceptions import NetworkManagerError

logger = logging.getLogger(__name__)

class MainController:
    """
    Handles the main application logic, data flow, and orchestration of UI components.
    Acts as the 'Controller' in a pseudo-MVC pattern for the main window.
    """
    def __init__(self, task_queue):
        self.task_queue = task_queue
        self.adapters_data = []
        self.selected_adapter_index = None

    def refresh_adapter_list(self):
        """Clears and re-populates the listbox with network adapters."""
        logger.info("Starting adapter list refresh...")
        try:
            self.task_queue.put({'type': 'status_update', 'text': get_string('status_refreshing_list')})
            self.task_queue.put({'type': 'clear_details'})
            self.adapters_data = get_adapter_details()
            self.task_queue.put({'type': 'populate_adapters', 'data': self.adapters_data})
            logger.info("Adapter list refresh completed successfully.")
        except NetworkManagerError as e:
            logger.error("Failed to get network adapters.", exc_info=True)
            self.task_queue.put({'type': 'generic_error', 'description': 'retrieving network adapters', 'error': e})
            logger.error("Adapter list refresh failed.")

    def on_adapter_select(self, selected_index: int):
        """Handler for when an adapter is selected in the listbox."""
        if not (0 <= selected_index < len(self.adapters_data)):
            logger.warning("Invalid index %d received from adapter list selection.", selected_index)
            self.selected_adapter_index = None
            return
        
        self.selected_adapter_index = selected_index
        selected_adapter = self.adapters_data[selected_index]
        
        # Send data to the queue for the UI to handle
        self.task_queue.put({'type': 'update_adapter_details', 'data': selected_adapter})

    def get_selected_adapter_name(self) -> str | None:
        """Returns the name of the currently selected adapter, or None."""
        if self.selected_adapter_index is None:
            return None
        return self.adapters_data[self.selected_adapter_index].get('Name')

    def get_speed_for_selected_adapter(self, speeds: dict) -> dict | None:
        """Gets the speed data for the currently selected adapter."""
        selected_adapter_name = self.get_selected_adapter_name()
        if not selected_adapter_name:
            return None
        adapter_speeds = speeds.get(selected_adapter_name)
        return adapter_speeds