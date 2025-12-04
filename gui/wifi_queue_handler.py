import tkinter as tk
from tkinter import messagebox
import os

class WifiQueueHandler:
    """
    Handles messages from the task queue specifically for the WifiConnectWindow.
    """
    def __init__(self, context):
        self.context = context
        self.handler_map = self._create_handler_map()

    def _create_handler_map(self):
        return {
            'wifi_list_success': self._handle_list_success,
            'wifi_connect_success': self._handle_connect_success,
            'wifi_saved_profiles_success': self._handle_saved_profiles_success,
            'wifi_delete_profile_success': self._handle_delete_profile_success,
        }

    def process_message(self, msg: dict):
        """Processes a message if it's relevant to the Wi-Fi window."""
        handler = self.handler_map.get(msg['type'])
        if handler:
            handler(msg)
            return True # Message was handled
        return False # Message was not for this handler

    def _get_window(self):
        """Helper to safely get the WifiConnectWindow instance."""
        return self.context.open_windows.get('WifiConnectWindow')

    def _handle_list_success(self, msg):
        window = self._get_window()
        if window:
            window.available_tab.populate_list(msg['data'], msg.get('current_ssid'))
            window.status_label.config(text="Scan complete. Select a network.")

    def _handle_connect_success(self, msg):
        window = self._get_window()
        if window:
            messagebox.showinfo("Success", f"Successfully connected to '{msg['ssid']}'.", parent=window)
            window.status_label.config(text=f"Connected to {msg['ssid']}.")
            window.available_tab.reset_connect_button()
            window.saved_tab.reset_connect_button()
            window.available_tab.refresh_list()

    def _handle_saved_profiles_success(self, msg):
        window = self._get_window()
        if window:
            window.saved_tab.populate_list(msg['data'])
            window.status_label.config(text="Saved profiles loaded.")

    def _handle_delete_profile_success(self, msg):
        window = self._get_window()
        if window:
            messagebox.showinfo("Success", f"Profile '{msg['profile_name']}' has been deleted.", parent=window)
            window.saved_tab.refresh_list()