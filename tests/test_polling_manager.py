import unittest
import sys
import os
from unittest.mock import Mock, patch, call

# Add the project root to the Python path to allow importing from 'gui'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.polling_manager import PollingManager

class TestPollingManagerSpeedCalc(unittest.TestCase):
    """
    Unit tests for the PollingManager._calculate_speed_delta method.
    """

    def setUp(self):
        """Set up a PollingManager instance for testing."""
        # The context dependency is not needed for testing this specific method.
        self.polling_manager = PollingManager(context=None)

    def test_normal_speed_calculation(self):
        """Test a standard, successful speed calculation over 2 seconds."""
        last_stats = {'Adapter 1': {'received': 1000, 'sent': 500}}
        current_stats = {'Adapter 1': {'received': 2000, 'sent': 750}}
        time_delta = 2.0

        # Download: (2000 - 1000) / 2.0 = 500 Bps
        # Upload:   (750 - 500) / 2.0 = 125 Bps
        expected = {'Adapter 1': {'download': 500.0, 'upload': 125.0}}
        
        result = self.polling_manager._calculate_speed_delta(current_stats, last_stats, time_delta)
        self.assertEqual(result, expected)

    def test_counter_rollover_returns_zero(self):
        """Test that a negative delta (counter rollover) results in 0 speed for that metric."""
        last_stats = {'Adapter 1': {'received': 5000, 'sent': 1000}}
        current_stats = {'Adapter 1': {'received': 1000, 'sent': 1500}} # 'received' counter reset
        time_delta = 1.0

        # Download speed should be 0 due to negative delta.
        # Upload speed should be calculated normally: (1500 - 1000) / 1.0 = 500 Bps
        expected = {'Adapter 1': {'download': 0.0, 'upload': 500.0}}
        
        result = self.polling_manager._calculate_speed_delta(current_stats, last_stats, time_delta)
        self.assertEqual(result, expected)

    def test_zero_time_delta(self):
        """Test that a time_delta of zero or less returns an empty dict to prevent division by zero."""
        last_stats = {'Adapter 1': {'received': 1000, 'sent': 500}}
        current_stats = {'Adapter 1': {'received': 2000, 'sent': 750}}
        
        result_zero = self.polling_manager._calculate_speed_delta(current_stats, last_stats, 0)
        self.assertEqual(result_zero, {})

        result_negative = self.polling_manager._calculate_speed_delta(current_stats, last_stats, -1.0)
        self.assertEqual(result_negative, {})

    def test_empty_or_missing_stats(self):
        """Test that empty or missing stats dictionaries are handled gracefully."""
        last_stats = {'Adapter 1': {'received': 1000, 'sent': 500}}
        current_stats = {'Adapter 1': {'received': 2000, 'sent': 750}}

        # No last stats available
        self.assertEqual(self.polling_manager._calculate_speed_delta(current_stats, {}, 1.0), {})
        # No current stats available
        self.assertEqual(self.polling_manager._calculate_speed_delta({}, last_stats, 1.0), {})

    def test_new_adapter_appears(self):
        """Test that a newly appeared adapter is ignored in the first calculation."""
        last_stats = {'Adapter 1': {'received': 1000, 'sent': 500}}
        current_stats = {
            'Adapter 1': {'received': 2000, 'sent': 750},
            'Adapter 2': {'received': 500, 'sent': 500} # New adapter
        }
        
        result = self.polling_manager._calculate_speed_delta(current_stats, last_stats, 1.0)
        self.assertIn('Adapter 1', result)
        self.assertNotIn('Adapter 2', result)

    def test_invalid_data_in_stats(self):
        """Test that non-numeric or missing byte counts are skipped."""
        last_stats = {'Adapter 1': {'received': 1000, 'sent': 500}}
        current_stats = {
            'Adapter 1': {'received': None, 'sent': 'not-a-number'} # Invalid data
        }
        
        result = self.polling_manager._calculate_speed_delta(current_stats, last_stats, 1.0)
        self.assertNotIn('Adapter 1', result)

class TestPollingManagerLoop(unittest.TestCase):
    """
    Unit tests for the PollingManager's main polling loop.
    """

    def setUp(self):
        """Set up mocks and the PollingManager instance."""
        self.mock_context = Mock()
        self.mock_context.task_queue = Mock()
        self.mock_context.get_ping_target.return_value = "8.8.8.8"
        self.polling_manager = PollingManager(self.mock_context)
        self.polling_manager.start_all(diagnostics_interval=5, speed_interval=1)

    @patch('gui.polling_manager.time.sleep')
    @patch('gui.polling_manager.time.time')
    @patch('gui.polling_manager.get_raw_network_stats')
    @patch('gui.polling_manager.get_current_wifi_details')
    @patch('gui.polling_manager.get_network_diagnostics')
    def test_first_poll_runs_all_tasks(self, mock_get_diag, mock_get_wifi, mock_get_stats, mock_time, mock_sleep):
        """Test that the very first poll runs both heavy and light tasks."""
        # Arrange
        mock_time.return_value = 1000.0
        mock_get_diag.return_value = {'Public IP': '1.2.3.4'}
        mock_get_wifi.return_value = {'ssid': 'TestNet'}
        mock_get_stats.return_value = {'Wi-Fi': {'received': 100, 'sent': 50}}
        # Make the loop run only once by raising an exception
        mock_sleep.side_effect = InterruptedError

        # Act
        with self.assertRaises(InterruptedError):
            self.polling_manager._poll_loop()

        # Assert
        # Check that all data fetching functions were called
        mock_get_diag.assert_called_once()
        mock_get_wifi.assert_called_once()
        mock_get_stats.assert_called_once()

        # Check that all messages were put into the queue
        expected_calls = [
            call.put({'type': 'diagnostics_update', 'data': {'Public IP': '1.2.3.4'}}),
            call.put({'type': 'wifi_status_update', 'data': {'ssid': 'TestNet'}}),
            call.put({'type': 'speed_update', 'data': {}}) # Speed is empty on first run
        ]
        self.mock_context.task_queue.assert_has_calls(expected_calls, any_order=True)

    @patch('gui.polling_manager.time.sleep')
    @patch('gui.polling_manager.time.time')
    @patch('gui.polling_manager.get_raw_network_stats')
    @patch('gui.polling_manager.get_current_wifi_details')
    @patch('gui.polling_manager.get_network_diagnostics')
    def test_subsequent_poll_runs_only_light_tasks(self, mock_get_diag, mock_get_wifi, mock_get_stats, mock_time, mock_sleep):
        """Test that a subsequent poll (before interval) only runs speed calculation."""
        # Arrange
        # Simulate two loop runs: one at t=1000, one at t=1001
        mock_time.side_effect = [1000.0, 1001.0]
        mock_get_stats.return_value = {}
        # Make the loop run twice
        mock_sleep.side_effect = [None, InterruptedError]

        # Act
        with self.assertRaises(InterruptedError):
            self.polling_manager._poll_loop()

        # Assert
        # Heavy diagnostics should only be called on the first run
        mock_get_diag.assert_called_once()
        mock_get_wifi.assert_called_once()
        # Speed calculation runs every time
        self.assertEqual(mock_get_stats.call_count, 2)

        # Check that the queue got the speed_update message on the second run
        self.mock_context.task_queue.put.assert_called_with({'type': 'speed_update', 'data': {}})


if __name__ == '__main__':
    unittest.main()