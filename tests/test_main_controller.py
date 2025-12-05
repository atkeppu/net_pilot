import unittest
from unittest.mock import Mock, patch, call
import logging

from localization import get_string
from gui.main_controller import MainController
from exceptions import NetworkManagerError

class TestMainController(unittest.TestCase):
    """
    Unit tests for the MainController class.
    """

    def setUp(self):
        """Set up a MainController instance with a mock task_queue for each test."""
        self.mock_task_queue = Mock()
        self.controller = MainController(self.mock_task_queue)

    @patch('gui.main_controller.get_adapter_details')
    def test_refresh_adapter_list_success(self, mock_get_details):
        """Test successful refresh of the adapter list."""
        # Arrange
        mock_adapters = [{'Name': 'Wi-Fi'}, {'Name': 'Ethernet'}]
        mock_get_details.return_value = mock_adapters

        # Act
        self.controller.refresh_adapter_list()

        # Assert
        self.assertEqual(self.controller.adapters_data, mock_adapters)
        
        # Check that the correct messages were put into the queue
        expected_calls = [
            call.put({'type': 'status_update', 'text': get_string('status_refreshing_list')}),
            call.put({'type': 'clear_details'}),
            call.put({'type': 'populate_adapters', 'data': mock_adapters})
        ]
        self.mock_task_queue.assert_has_calls(expected_calls, any_order=False)

    @patch('gui.main_controller.get_adapter_details')
    def test_refresh_adapter_list_failure(self, mock_get_details):
        """Test failure during adapter list refresh."""
        # Arrange
        error = NetworkManagerError("Test error")
        mock_get_details.side_effect = error

        # Act & Assert: Check that an error is logged.
        with self.assertLogs('gui.main_controller', level='ERROR'):
            self.controller.refresh_adapter_list()

        # Assert
        expected_calls = [
            call.put({'type': 'status_update', 'text': get_string('status_refreshing_list')}),
            call.put({'type': 'clear_details'}),
            call.put({'type': 'generic_error', 'description': 'retrieving network adapters', 'error': error})
        ]
        self.mock_task_queue.assert_has_calls(expected_calls, any_order=False)

    def test_on_adapter_select(self):
        """Test selecting a valid adapter."""
        # Arrange
        self.controller.adapters_data = [{'Name': 'Wi-Fi'}, {'Name': 'Ethernet'}]
        selected_index = 1

        # Act
        self.controller.on_adapter_select(selected_index)

        # Assert
        self.assertEqual(self.controller.selected_adapter_index, selected_index)
        self.mock_task_queue.put.assert_called_once_with({
            'type': 'update_adapter_details',
            'data': {'Name': 'Ethernet'}
        })

    def test_on_adapter_select_invalid_index(self):
        """Test selecting an invalid adapter index."""
        # Arrange
        self.controller.adapters_data = [{'Name': 'Wi-Fi'}]
        
        # Act & Assert: Check that a warning is logged for the invalid index.
        with self.assertLogs('gui.main_controller', level='WARNING'):
            self.controller.on_adapter_select(99) # Invalid index

        # Assert
        self.assertIsNone(self.controller.selected_adapter_index)
        self.mock_task_queue.put.assert_not_called()

    def test_get_selected_adapter_name(self):
        """Test getting the name of the selected adapter."""
        # Arrange
        self.controller.adapters_data = [{'Name': 'Wi-Fi'}, {'Name': 'Ethernet'}]
        self.controller.selected_adapter_index = 0

        # Act & Assert
        self.assertEqual(self.controller.get_selected_adapter_name(), 'Wi-Fi')
        
        # Test when nothing is selected
        self.controller.selected_adapter_index = None
        self.assertIsNone(self.controller.get_selected_adapter_name())

    def test_get_speed_for_selected_adapter(self):
        """Test getting speed data for the selected adapter."""
        self.controller.adapters_data = [{'Name': 'Wi-Fi'}]
        self.controller.selected_adapter_index = 0
        speeds = {'Wi-Fi': {'download': 123}, 'Ethernet': {'download': 456}}

        # Should return data for 'Wi-Fi'
        self.assertEqual(self.controller.get_speed_for_selected_adapter(speeds), {'download': 123})

        # Should return None if nothing is selected
        self.controller.selected_adapter_index = None
        self.assertIsNone(self.controller.get_speed_for_selected_adapter(speeds))

if __name__ == '__main__':
    unittest.main()