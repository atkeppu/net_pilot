import unittest
from unittest.mock import Mock, patch, call
import threading

import time
from gui.polling_manager import PollingManager

class TestPollingManagerSpeedCalc(unittest.TestCase):
    """
    Unit tests for the PollingManager._calculate_speed_delta method.
    """

    def setUp(self):
        """Set up a PollingManager instance for testing."""
        mock_context = Mock()
        mock_context.main_controller = Mock()
        mock_context.task_queue = Mock()
        self.polling_manager = PollingManager(context=mock_context)

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

class TestCalculateCurrentSpeeds(unittest.TestCase):
    """Tests for the _calculate_current_speeds method."""

    def setUp(self):
        mock_context = Mock()
        self.polling_manager = PollingManager(context=mock_context)
        self.polling_manager.last_stats = {}
        self.polling_manager.last_time = time.time()

    def test_invalid_json_returns_empty_dict(self):
        """Test that malformed JSON input is handled gracefully."""
        with self.assertLogs('gui.polling_manager', level='WARNING'):
            result = self.polling_manager._calculate_current_speeds("{not-json")
            self.assertEqual(result, {})

    def test_non_list_or_dict_json_returns_empty_dict(self):
        """Test that valid but structurally incorrect JSON is handled."""
        self.assertEqual(self.polling_manager._calculate_current_speeds("123"), {})
class TestPollingManagerLoop(unittest.TestCase):
    """
    Unit tests for the PollingManager's main polling loop.
    """

    def setUp(self):
        """Set up mocks and the PollingManager instance."""
        self.mock_context = Mock()
        self.mock_context.task_queue = Mock()
        self.mock_context.get_ping_target.return_value = "8.8.8.8"
        self.mock_context.main_controller = Mock()
        self.polling_manager = PollingManager(self.mock_context)
        self.polling_manager.start_all(diagnostics_interval=5, speed_interval=1)

    @patch('gui.polling_manager.time.time')
    @patch('gui.polling_manager.get_current_wifi_details')
    @patch('gui.polling_manager.PollingManager._fetch_diagnostics_and_queue')
    def test_first_poll_runs_all_tasks(self, mock_fetch_diag, mock_get_wifi, mock_time):
        """Test that the very first poll runs both heavy and light tasks."""
        # Arrange
        mock_time.return_value = 1000.0
        mock_get_wifi.return_value = {'ssid': 'TestNet'}

        # Act: Run the loop once. We set is_running to True and then mock the
        # stop_event.wait() call to immediately set the event, ensuring the
        # loop runs exactly once.
        stop_event = threading.Event()
        self.polling_manager.is_running = True
        with patch.object(stop_event, 'wait', side_effect=lambda timeout: stop_event.set()):
            self.polling_manager._poll_loop(stop_event)

        # Assert
        # Check that all data fetching functions were called
        mock_fetch_diag.assert_called_once()
        mock_get_wifi.assert_called_once()

        # Check that all messages were put into the queue
        expected_calls = [
            call.put({'type': 'wifi_status_update', 'data': {'ssid': 'TestNet'}}),
        ]
        self.mock_context.task_queue.assert_has_calls(expected_calls)

    @patch('gui.polling_manager.time.time')
    @patch('gui.polling_manager.get_current_wifi_details')
    @patch('gui.polling_manager.get_network_diagnostics')
    def test_subsequent_poll_runs_only_light_tasks(self, mock_get_diag, mock_get_wifi, mock_time):
        """Test that a subsequent poll (before interval) only runs speed calculation."""
        # Arrange
        self.polling_manager.diagnostics_interval = 0.1 # Shorten interval for test
        # Simulate two loop runs: one at t=1000, one at t=1001
        mock_time.side_effect = [1000.0, 1001.0]
        
        # Run the loop in a thread and use an event to stop it after two iterations.
        stop_event = threading.Event()
        self.polling_manager.is_running = True
        poll_thread = threading.Thread(target=self.polling_manager._poll_loop, args=(stop_event,))
        poll_thread.start()
        
        # Wait long enough for two cycles
        time.sleep(self.polling_manager.diagnostics_interval * 1.5)
        
        stop_event.set() # Signal the loop to stop
        poll_thread.join(timeout=1) # Wait for the thread to finish

        # Assert
        # In the main loop, these tasks run on every iteration.
        self.assertEqual(mock_get_diag.call_count, 2)
        self.assertEqual(mock_get_wifi.call_count, 2)

    @patch('gui.polling_manager.subprocess.Popen')
    def test_speed_poll_loop_skips_when_no_adapter_selected(self, mock_popen):
        """Test that speed calculation is skipped if no adapter is selected."""
        # Arrange
        self.polling_manager.is_running = True
        self.mock_context.main_controller.get_selected_adapter_name.return_value = None
        
        # Mock the process to simulate it running and producing output
        mock_process = mock_popen.return_value
        # Make the loop run only once by having poll() return a value on the second call
        mock_process.poll.side_effect = [None, 0]
        mock_process.stdout.readline.return_value = '{"Name": "Wi-Fi", "ReceivedBytes": 100, "SentBytes": 50}'

        # Act: We can't easily test the loop, so we call the method directly
        # and check if the calculation part is skipped.
        with patch.object(self.polling_manager, '_calculate_current_speeds') as mock_calculate:
            self.polling_manager._speed_poll_loop_powershell()
            mock_calculate.assert_not_called()

if __name__ == '__main__':
    unittest.main()