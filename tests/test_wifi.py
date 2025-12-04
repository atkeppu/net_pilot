import unittest
import sys
import os
import json
from unittest.mock import patch

# Add the project root to the Python path to allow importing from 'logic'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.wifi import _parse_netsh_wlan_output, get_current_wifi_details, get_saved_wifi_profiles
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
            {'ssid': '', 'authentication': 'WPA2-Personal', 'encryption': 'CCMP', 'signal': '80'}
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
        with self.assertRaises(NetworkManagerError):
            get_saved_wifi_profiles()

if __name__ == '__main__':
    unittest.main()