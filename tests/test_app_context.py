import unittest
from unittest.mock import Mock, patch

from gui.app_context import AppContext

class TestAppContext(unittest.TestCase):
    """Tests for the AppContext class."""

    def setUp(self):
        """Set up a fresh AppContext for each test."""
        self.context = AppContext()

    def test_initialization(self):
        """Test that components are initialized as expected."""
        self.assertIsNotNone(self.context.task_queue)
        self.assertIsNotNone(self.context.main_controller)
        self.assertIsNotNone(self.context.action_handler)
        self.assertIsNone(self.context.queue_handler)
        self.assertIsNone(self.context.polling_manager)

    @patch('gui.app_context.QueueHandler')
    @patch('gui.app_context.PollingManager')
    def test_initialize_components(self, mock_polling_manager, mock_queue_handler):
        """Test that UI-dependent components are initialized correctly."""
        mock_root = Mock()
        mock_status_var = Mock()
        mock_ui_frames = {'diagnostics': Mock()}

        self.context.initialize_components(mock_root, mock_ui_frames, mock_status_var)

        self.assertIs(self.context.root, mock_root)
        mock_queue_handler.assert_called_once_with(context=self.context, ui_frames=mock_ui_frames)
        mock_polling_manager.assert_called_once_with(self.context)

    def test_window_registration(self):
        """Test that window registration and unregistration works."""
        mock_window = Mock()
        mock_window.__class__.__name__ = "TestWindow"

        self.context.register_window(mock_window)
        self.assertIn("TestWindow", self.context.open_windows)
        self.assertIs(self.context.open_windows["TestWindow"], mock_window)

        self.context.unregister_window(mock_window)
        self.assertNotIn("TestWindow", self.context.open_windows)