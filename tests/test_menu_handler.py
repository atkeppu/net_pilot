import unittest
from unittest.mock import Mock, patch
import tkinter as tk

from gui.menu_handler import MenuHandler

class TestMenuHandler(unittest.TestCase):
    """Tests for the MenuHandler class."""

    def setUp(self):
        self.mock_context = Mock()
        # A root window must exist before creating Tkinter variables like StringVar.
        # We create a dummy root here for the test environment.
        self.root = tk.Tk()
        self.mock_context.root = self.root
        self.handler = MenuHandler(self.mock_context)

    @patch('gui.menu_handler.get_log_file_path', return_value="non_existent_file.log")
    @patch('gui.menu_handler.os.startfile', side_effect=FileNotFoundError)
    @patch('gui.menu_handler.messagebox.showerror')
    def test_open_log_file_not_found(self, mock_showerror, mock_startfile, mock_get_log_path):
        """Test that an error is shown if the log file is not found."""
        self.handler._open_log_file()
        mock_startfile.assert_called_once_with("non_existent_file.log")
        mock_showerror.assert_called_once()
        self.assertIn("Log file not found", mock_showerror.call_args[0][1])