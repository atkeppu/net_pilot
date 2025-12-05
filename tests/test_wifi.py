import unittest
import json
from unittest.mock import patch

from logic.wifi import _parse_netsh_wlan_output, get_current_wifi_details, get_saved_wifi_profiles, list_wifi_networks, disconnect_wifi
from exceptions import NetworkManagerError

class TestWifiParser(unittest.TestCase):
    """
    Unit tests for the _parse_netsh_wlan_output function.
    """

    def test_parse_multiple_networks(self):
        """Test parsing a standard output with multiple networks."""
        mock_output = """
Interface name : Wi-Fi
There are 2 networks currently visible.

SSID 1 : MyHomeNetwork
    Network type            : Infrastructure
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 1a:2b:3c:4d:5e:6f
         Signal             : 99%

SSID 2 : CoffeeShop-Guest
    Network type            : Infrastructure
    Authentication          : Open
    Encryption              : None
    BSSID 1                 : aa:bb:cc:dd:ee:ff
         Signal             : 75%
"""
        expected = [
            {'ssid': 'MyHomeNetwork', 'authentication': 'WPA2-Personal', 'encryption': 'CCMP', 'signal': '99'},
            {'ssid': 'CoffeeShop-Guest', 'authentication': 'Open', 'encryption': 'None', 'signal': '75'}
        ]
        result = _parse_netsh_wlan_output(mock_output)
        self.assertEqual(result, expected)

    def test_parse_ignores_duplicate_ssids(self):
        """Test that duplicate SSIDs (from multiple BSSIDs) are ignored."""
        mock_output = """
SSID 1 : MyHomeNetwork
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 1a:2b:3c:4d:5e:6f
         Signal             : 99%

SSID 2 : MyHomeNetwork
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 1a:2b:3c:4d:5e:70
         Signal             : 50%
"""
        expected = [
            {'ssid': 'MyHomeNetwork', 'authentication': 'WPA2-Personal', 'encryption': 'CCMP', 'signal': '99'}
        ]
        result = _parse_netsh_wlan_output(mock_output)
        self.assertEqual(result, expected)
        self.assertEqual(len(result), 1)

    def test_parse_with_missing_signal(self):
        """Test parsing a network block where signal strength is missing."""
        mock_output = """
SSID 1 : HiddenNetwork
    Authentication          : WPA2-Personal
    Encryption              : CCMP
"""
        expected = [
            {'ssid': 'HiddenNetwork', 'authentication': 'WPA2-Personal', 'encryption': 'CCMP', 'signal': 'N/A'}
        ]
        result = _parse_netsh_wlan_output(mock_output)
        self.assertEqual(result, expected)

    def test_parse_with_empty_ssid(self):
        """Test parsing a network with an empty (hidden) SSID."""
        mock_output = """
SSID 1 : 
    Authentication          : WPA2-Personal
    Encryption              : CCMP
    BSSID 1                 : 1a:2b:3c:4d:5e:6f
         Signal             : 80%
"""
        expected = [
            {'ssid': '(Hidden Network)', 'authentication': 'WPA2-Personal', 'encryption': 'CCMP', 'signal': '80'}
        ]
        result = _parse_netsh_wlan_output(mock_output)
        self.assertEqual(result, expected)

    def test_parse_no_networks_found(self):
        """Test parsing when no networks are found."""
        mock_output = """
Interface name : Wi-Fi
There are 0 networks currently visible.
"""
        result = _parse_netsh_wlan_output(mock_output)
        self.assertEqual(result, [])

    def test_parse_empty_input(self):
        """Test parsing an empty string."""
        result = _parse_netsh_wlan_output("")
        self.assertEqual(result, [])

class TestListWifiNetworks(unittest.TestCase):
    """Unit tests for the list_wifi_networks function."""

    @patch('logic.wifi.run_system_command')
    @patch('logic.wifi._parse_netsh_wlan_output')
    def test_list_wifi_networks_success(self, mock_parser, mock_run_command):
        """Test a successful network scan."""
        mock_run_command.return_value.stdout = b"some netsh output"
        mock_parser.return_value = [{'ssid': 'TestNet'}]
        
        result = list_wifi_networks()
        
        self.assertEqual(result, [{'ssid': 'TestNet'}])
        mock_run_command.assert_called_once()
        mock_parser.assert_called_once_with("some netsh output")

    @patch('logic.wifi.run_system_command', side_effect=NetworkManagerError("no wireless interface"))
    def test_list_wifi_networks_no_interface(self, mock_run_command):
        """Test that an empty list is returned if no wireless interface is found."""
        result = list_wifi_networks()
        self.assertEqual(result, [])

    @patch('logic.wifi.run_system_command', side_effect=NetworkManagerError("location permission"))
    def test_list_wifi_networks_location_permission_denied(self, mock_run_command):
        """Test that a specific error is raised for location permission issues."""
        with self.assertRaises(NetworkManagerError) as cm:
            list_wifi_networks()
        self.assertEqual(cm.exception.code, 'LOCATION_PERMISSION_DENIED')

    @patch('logic.wifi.run_system_command', side_effect=NetworkManagerError("generic error"))
    def test_list_wifi_networks_generic_error(self, mock_run_command):
        """Test that a generic error is re-raised."""
        with self.assertRaisesRegex(NetworkManagerError, "generic error"):
            list_wifi_networks()

class TestGetCurrentWifiDetails(unittest.TestCase):
    """
    Unit tests for the get_current_wifi_details function.
    """

    @patch('logic.wifi.run_ps_command')
    def test_success_case_returns_dict(self, mock_run_ps_command):
        """Test that a valid JSON output from PowerShell is parsed correctly."""
        # Arrange
        mock_data = {
            "interface_name": "Wi-Fi",
            "ssid": "MyTestNetwork",
            "signal": "99%",
            "ipv4": "192.168.1.123"
        }
        mock_run_ps_command.return_value = json.dumps(mock_data)

        # Act
        result = get_current_wifi_details()

        # Assert
        self.assertEqual(result, mock_data)

    @patch('logic.wifi.run_ps_command')
    def test_not_connected_returns_none(self, mock_run_ps_command):
        """Test that an empty response (not connected) results in None."""
        # Arrange
        mock_run_ps_command.return_value = "" # PS script exits without output if not connected

        # Act
        result = get_current_wifi_details()

        # Assert
        self.assertIsNone(result)

    @patch('logic.wifi.run_ps_command')
    def test_network_error_returns_none(self, mock_run_ps_command):
        """Test that a NetworkManagerError is caught and results in None."""
        # Arrange
        mock_run_ps_command.side_effect = NetworkManagerError("PS command failed")

        # Act & Assert
        self.assertIsNone(get_current_wifi_details())

    @patch('logic.wifi.run_ps_command', side_effect=json.JSONDecodeError("bad json", "", 0))
    def test_invalid_json_returns_none(self, mock_run_ps_command):
        """Test that a JSONDecodeError is caught and results in None."""
        self.assertIsNone(get_current_wifi_details())

class TestDisconnectWifi(unittest.TestCase):
    """Unit tests for the disconnect_wifi function."""

    @patch('logic.wifi.run_system_command')
    def test_disconnect_already_disconnected(self, mock_run_command):
        """Test that the 'not connected' error is handled gracefully."""
        mock_run_command.side_effect = NetworkManagerError("not connected to a network")
        # No exception should be raised
        disconnect_wifi()
        mock_run_command.assert_called_once()

    @patch('logic.wifi.run_system_command')
    def test_disconnect_generic_error(self, mock_run_command):
        """Test that a generic error during disconnect is re-raised."""
        mock_run_command.side_effect = NetworkManagerError("some other failure")
        with self.assertRaisesRegex(NetworkManagerError, "some other failure"):
            disconnect_wifi()
class TestGetSavedWifiProfiles(unittest.TestCase):
    """
    Unit tests for the get_saved_wifi_profiles function.
    """

    @patch('logic.wifi.run_ps_command')
    def test_success_case_with_profiles(self, mock_run_ps_command):
        """Test that a valid JSON output with profiles is parsed correctly."""
        # Arrange
        mock_data = [
            {"ssid": "MyHomeNetwork", "password": "MyPassword123"},
            {"ssid": "CoffeeShop-Guest", "password": "N/A"},
            {"ssid": "Work-Network", "password": "(Password not stored or accessible)"}
        ]
        mock_run_ps_command.return_value = json.dumps(mock_data)

        # Act
        result = get_saved_wifi_profiles()

        # Assert
        self.assertEqual(result, mock_data)

    @patch('logic.wifi.run_ps_command')
    def test_no_profiles_found(self, mock_run_ps_command):
        """Test that an empty list is returned when no profiles are found."""
        # Arrange
        mock_run_ps_command.return_value = "[]"

        # Act
        result = get_saved_wifi_profiles()

        # Assert
        self.assertEqual(result, [])

    @patch('logic.wifi.run_ps_command')
    def test_network_error_raises_exception(self, mock_run_ps_command):
        """Test that a NetworkManagerError from the command is re-raised."""
        # Arrange
        mock_run_ps_command.side_effect = NetworkManagerError("PS command failed")

        # Act & Assert
        # Check that an error is logged and the correct exception is raised.
        with self.assertLogs('logic.wifi', level='ERROR'), self.assertRaises(NetworkManagerError):
            get_saved_wifi_profiles() # type: ignore

    @patch('logic.wifi.run_ps_command', side_effect=json.JSONDecodeError("bad json", "", 0))
    def test_invalid_json_raises_exception(self, mock_run_ps_command):
        """Test that a JSONDecodeError is wrapped in NetworkManagerError."""
        with self.assertLogs('logic.wifi', level='ERROR'), self.assertRaises(NetworkManagerError):
            get_saved_wifi_profiles()

if __name__ == '__main__':
    unittest.main()