import unittest
from unittest.mock import patch
import json

from logic.adapters import (get_adapter_details, set_network_adapter_status_windows,
                            disconnect_wifi_and_disable_adapter)
from exceptions import NetworkManagerError

class TestSetAdapterStatus(unittest.TestCase):
    """
    Unit tests for the set_network_adapter_status_windows function.
    """

    @patch('logic.adapters.run_ps_command')
    def test_setNetworkAdapterStatus_whenActionIsEnable_shouldCallEnableNetAdapter(
            self, mock_run_ps_command):
        """Test a successful call to enable an adapter."""
        # Arrange
        adapter_name = "Wi-Fi"
        action = "enable"
        expected_script = f"Enable-NetAdapter -Name '{adapter_name}' -Confirm:$false"

        # Act
        set_network_adapter_status_windows(adapter_name, action)

        # Assert
        mock_run_ps_command.assert_called_once_with(expected_script)

    @patch('logic.adapters.run_ps_command')
    def test_setNetworkAdapterStatus_whenActionIsDisable_shouldCallDisableNetAdapter(
            self, mock_run_ps_command):
        """Test a successful call to disable an adapter."""
        # Arrange
        adapter_name = "Ethernet"
        action = "disable"
        expected_script = f"Disable-NetAdapter -Name '{adapter_name}' -Confirm:$false"

        # Act
        set_network_adapter_status_windows(adapter_name, action)

        # Assert
        mock_run_ps_command.assert_called_once_with(expected_script)

    def test_setNetworkAdapterStatus_withInvalidAction_shouldRaiseValueError(self):
        """Test that an invalid action string raises a ValueError."""
        with self.assertRaises(ValueError):
            set_network_adapter_status_windows("Wi-Fi", "destroy")

    @patch('logic.adapters.run_ps_command')
    def test_setNetworkAdapterStatus_whenAdapterIsAlreadyInState_shouldRaiseNetworkManagerError(
            self, mock_run_ps_command):
        """Test handling of the 'already in state' error from PowerShell."""
        # Arrange
        error_message = "The object is already in the state 'Enabled'."
        mock_run_ps_command.side_effect = NetworkManagerError(error_message)

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            set_network_adapter_status_windows("Wi-Fi", "enable")
        
        self.assertIn("Adapter 'Wi-Fi' is already enabled", str(cm.exception))

    @patch('logic.adapters.run_ps_command')
    def test_setNetworkAdapterStatus_whenDisablingConnectedWifi_shouldRaiseSpecificError(
            self, mock_run_ps_command):
        """Test handling of the 'cannot be disabled' error when connected."""
        # Arrange
        error_message = "The adapter cannot be disabled while it is connected."
        mock_run_ps_command.side_effect = NetworkManagerError(error_message)

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            set_network_adapter_status_windows("Wi-Fi", "disable")
        
        self.assertEqual(cm.exception.code, 'WIFI_CONNECTED_DISABLE_FAILED')
        self.assertIn("Cannot disable 'Wi-Fi' while it is connected", str(cm.exception))

    @patch('logic.adapters.run_ps_command')
    def test_setNetworkAdapterStatus_onGenericError_shouldWrapExceptionWithContext(
            self, mock_run_ps_command):
        """Test that a generic NetworkManagerError is wrapped with more context."""
        # Arrange
        original_error = NetworkManagerError("A generic PowerShell error occurred.")
        mock_run_ps_command.side_effect = original_error

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            set_network_adapter_status_windows("Wi-Fi", "disable")
        
        # Check that the new exception message contains the action and adapter name
        self.assertIn("Failed to disable adapter 'Wi-Fi'", str(cm.exception))
        # Check that the original exception is chained
        self.assertIs(cm.exception.__cause__, original_error)

class TestGetAdapterDetails(unittest.TestCase):
    """
    Unit tests for the get_adapter_details function, focusing on JSON parsing.
    """

    @patch('logic.adapters.run_external_ps_script')
    def test_getAdapterDetails_withInvalidJson_shouldRaiseNetworkManagerError(
            self, mock_run_script):
        """Test that invalid JSON from PowerShell raises a NetworkManagerError."""
        # Arrange
        mock_run_script.return_value = "This is not valid JSON"

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            get_adapter_details()
        
        self.assertIn("Failed to parse adapter details", str(cm.exception))


class TestDisconnectAndDisable(unittest.TestCase):
    """
    Unit tests for the disconnect_wifi_and_disable_adapter workflow.
    """

    @patch('logic.adapters.set_network_adapter_status_windows')
    @patch('logic.adapters.get_current_wifi_details')
    @patch('logic.adapters.disconnect_wifi')
    @patch('time.sleep')
    def test_disconnectAndDisable_onSuccess_shouldCompleteAllSteps(
            self, mock_sleep, mock_disconnect, mock_get_details, mock_set_status):
        """Test the ideal success case where disconnect is confirmed quickly."""
        # Arrange: Simulate that after one check, the connection is gone.
        mock_get_details.side_effect = [{'ssid': 'Test'}, None]
        adapter_name = "Wi-Fi"

        # Act
        result_generator = disconnect_wifi_and_disable_adapter(adapter_name)
        messages = list(result_generator)

        # Assert
        self.assertEqual(mock_disconnect.call_count, 1)
        self.assertLessEqual(mock_get_details.call_count, 2) # Should be 2 calls
        mock_set_status.assert_called_once_with(adapter_name, 'disable')
        self.assertIn("Successfully disabled 'Wi-Fi'.", messages)

    @patch('logic.adapters.get_current_wifi_details')
    @patch('logic.adapters.disconnect_wifi')
    @patch('time.sleep')
    def test_disconnectAndDisable_whenDisconnectTimesOut_shouldRaiseError(
            self, mock_sleep, mock_disconnect, mock_get_details):
        """Test that an error is raised if disconnection is not confirmed in time."""
        # Arrange: Simulate that the connection never drops.
        mock_get_details.return_value = {'ssid': 'Test'}

        # Act & Assert
        with self.assertRaisesRegex(NetworkManagerError, "Failed to confirm Wi-Fi disconnection"):
            list(disconnect_wifi_and_disable_adapter("Wi-Fi"))

if __name__ == '__main__':
    unittest.main()