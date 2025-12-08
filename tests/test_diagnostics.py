import unittest
from unittest.mock import patch, MagicMock, call
import io
import json

import requests
from logic.diagnostics import run_traceroute, get_network_diagnostics, get_raw_network_stats, get_active_connections
from exceptions import NetworkManagerError

class TestTraceroute(unittest.TestCase):
    """
    Unit tests for the run_traceroute function.
    """

    @patch('logic.diagnostics.run_ps_command')
    def test_run_traceroute_success(self, mock_run_ps_command):
        """Test a successful traceroute execution, yielding each line."""
        # Arrange: Simulate the generator output from the PowerShell command.
        expected = [
            "Tracing route to 8.8.8.8",
            "  1    <1 ms    <1 ms    <1 ms  192.168.1.1",
            "  2     *        *        *     Request timed out.",
            "Trace complete."
        ]
        mock_run_ps_command.return_value = iter(expected)

        # Act: Collect the yielded lines from the function.
        result = list(run_traceroute("8.8.8.8"))

        # Assert
        self.assertEqual(result, expected)
        mock_run_ps_command.assert_called_once()
        self.assertIn("Test-NetConnection -ComputerName '8.8.8.8' -TraceRoute",  # noqa: E501
                      mock_run_ps_command.call_args[0][0])  # noqa: E501

    def test_run_traceroute_invalid_target(self):
        """Test that an invalid target raises a NetworkManagerError."""
        # Arrange: An invalid target string with special characters.
        invalid_target = "8.8.8.8; rm -rf /"

        # Act & Assert: Check that the correct exception is raised.
        with self.assertRaises(NetworkManagerError) as cm:
            # We need to consume the generator to trigger the exception.
            list(run_traceroute(invalid_target))
        
        self.assertIn("Invalid target specified", str(cm.exception))

    @patch('logic.diagnostics.run_ps_command')
    def test_run_traceroute_command_error(self, mock_run_ps_command):
        """Test that a NetworkManagerError from the command is propagated."""
        # Arrange: Configure the mock to raise NetworkManagerError.
        mock_run_ps_command.side_effect = NetworkManagerError("PowerShell execution failed.")

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            list(run_traceroute("8.8.8.8"))
        
        self.assertIn("PowerShell execution failed", str(cm.exception))

class TestDiagnosticsJsonParsing(unittest.TestCase):
    """
    Unit tests for JSON parsing in the diagnostics module.
    """

    @patch('logic.diagnostics.run_external_ps_script')
    def test_get_active_connections_invalid_json(self, mock_run_script):
        """Test that get_active_connections raises an error on invalid JSON."""
        mock_run_script.return_value = "{not-json"
        # Check that an error is logged and the correct exception is raised.
        with self.assertLogs('logic.diagnostics', level='ERROR'), self.assertRaises(NetworkManagerError):
            get_active_connections() # type: ignore

    @patch('logic.diagnostics.run_external_ps_script')
    def test_get_raw_network_stats_invalid_json(self, mock_run_script):
        """Test that get_raw_network_stats returns an empty dict on invalid JSON."""
        mock_run_script.return_value = "[{not-json}]"
        # Check that an error is logged and the function returns an empty dict.
        with self.assertLogs('logic.diagnostics', level='ERROR'):
            self.assertEqual(get_raw_network_stats(), {})

    @patch('logic.diagnostics.run_external_ps_script')
    def test_get_active_connections_single_object(self, mock_run_script):
        """Test that a single JSON object is correctly wrapped in a list."""
        # Arrange
        mock_data = {"Proto": "TCP", "Local": "127.0.0.1:123"}
        mock_run_script.return_value = json.dumps(mock_data)

        # Act
        result = get_active_connections()

        # Assert
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], mock_data)

    @patch('logic.diagnostics.run_external_ps_script')
    def test_get_active_connections_empty_response(self, mock_run_script):
        """Test that an empty JSON list from the script returns an empty list."""
        mock_run_script.return_value = "[]"
        result = get_active_connections()
        self.assertEqual(result, [])

class TestGetNetworkDiagnostics(unittest.TestCase):
    """Unit tests for the get_network_diagnostics function."""

    @patch('logic.diagnostics.run_system_command')
    @patch('logic.diagnostics.requests.get')
    def test_get_network_diagnostics_all_fail(self, mock_requests_get, mock_run_command):
        """Test that diagnostics function handles failures in all sub-tasks gracefully."""
        # Arrange: all external calls fail
        mock_requests_get.side_effect = requests.RequestException("Connection failed")
        # Simulate both ipconfig and ping failing
        mock_run_command.side_effect = NetworkManagerError(  # noqa: E501
            "Command failed")  # noqa: E501

        # Act
        result = get_network_diagnostics()

        # Assert: The function should return the default error values
        self.assertEqual(mock_run_command.call_count, 3) # ipconfig, ping gateway, ping external
        self.assertEqual(result['Public IP'], "Error")
        self.assertEqual(result['Gateway'], "N/A")
        self.assertEqual(result['DNS Servers'], "N/A")
        self.assertEqual(result['Gateway Latency'], "No Response")
        self.assertEqual(result['External Latency'], "No Response")

    @patch('logic.diagnostics.run_system_command')
    @patch('logic.diagnostics.requests.get')
    def test_get_network_diagnostics_parsing(self, mock_requests_get, mock_run_command):
        """Test successful parsing of ipconfig output."""
        # Arrange
        mock_requests_get.return_value.text = "1.2.3.4"
        ipconfig_output = """
   Default Gateway . . . . . . . . . : 192.168.1.1
   DNS Servers . . . . . . . . . . . : 8.8.8.8
                                       8.8.4.4
""".encode('oem')
        # Simulate successful ipconfig, then successful pings
        mock_run_command.side_effect = [
            MagicMock(stdout=ipconfig_output),  # for ipconfig  # noqa: E501
            MagicMock(stdout=b"Average = 10ms"),  # for gateway ping  # noqa: E501
            MagicMock(stdout=b"Average = 25ms")   # for external ping  # noqa: E501
        ]

        result = get_network_diagnostics(external_target="example.com")

        self.assertEqual(result['Gateway'], "192.168.1.1")
        self.assertEqual(result['DNS Servers'], "8.8.8.8, 8.8.4.4")
        self.assertEqual(result['Gateway Latency'], "10 ms")
        self.assertEqual(result['External Latency'], "25 ms")

if __name__ == '__main__':
    unittest.main()