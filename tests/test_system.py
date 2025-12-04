import unittest
from unittest.mock import patch, Mock, call
import logging

# Add project root to path to allow importing from 'logic'
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.system import release_renew_ip, reset_network_stack, flush_dns_cache, terminate_process_by_pid
from exceptions import NetworkManagerError

# Disable logging during tests to keep the output clean
logging.disable(logging.CRITICAL)

class TestSystemModule(unittest.TestCase):
    """
    Unit tests for functions in the logic.system module.
    """

    @patch('logic.system.run_system_command')
    def test_resetNetworkStack_onSuccess_shouldCallNetsh(self, mock_run_command):
        """Test that reset_network_stack calls the correct netsh command."""
        reset_network_stack()
        mock_run_command.assert_called_once_with(['netsh', 'winsock', 'reset'], "Failed to reset network stack.")

    @patch('logic.system.run_system_command')
    def test_flushDnsCache_onSuccess_shouldCallIpconfig(self, mock_run_command):
        """Test that flush_dns_cache calls the correct ipconfig command."""
        flush_dns_cache()
        mock_run_command.assert_called_once_with(['ipconfig', '/flushdns'], "Failed to flush DNS cache.")

    @patch('logic.system.run_system_command')
    def test_terminateProcess_onSuccess_shouldCallTaskkill(self, mock_run_command):
        """Test a successful process termination."""
        terminate_process_by_pid(1234)
        mock_run_command.assert_called_once_with(['taskkill', '/F', '/T', '/PID', '1234'], "Failed to terminate process with PID 1234.")

    def test_terminateProcess_withSystemPid_shouldRaiseError(self):
        """Test that attempting to terminate a critical system process raises an error."""
        with self.assertRaises(NetworkManagerError) as cm:
            terminate_process_by_pid(4) # System process
        self.assertIn("not allowed", str(cm.exception))

    # --- Tests for release_renew_ip ---

    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_onSuccess_shouldCallBothCommands(self, mock_run_command):
        """Test the ideal success case where both release and renew succeed."""
        # Arrange: Both commands return a successful result.
        mock_run_command.return_value = Mock(returncode=0)

        # Act
        release_renew_ip()

        # Assert: Check that both commands were called correctly.
        self.assertEqual(mock_run_command.call_count, 2)
        mock_run_command.assert_has_calls([
            call(['ipconfig', '/release'], "IP address release command finished.", check=False),
            call(['ipconfig', '/renew'], "Failed to renew IP address.")
        ])

    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_whenReleaseFailsWithKnownError_shouldStillAttemptRenew(self, mock_run_command):
        """Test that a non-critical failure on 'release' still allows 'renew' to proceed."""
        # Arrange: 'release' fails with a known safe error, 'renew' succeeds.
        release_result = Mock(returncode=1, stdout=b'', stderr=b'The media is disconnected.')
        renew_result = Mock(returncode=0)
        mock_run_command.side_effect = [release_result, renew_result]

        # Act
        release_renew_ip()

        # Assert: Both commands are still called.
        self.assertEqual(mock_run_command.call_count, 2)

    @patch('logging.warning')
    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_whenReleaseFailsWithUnknownError_shouldLogWarning(self, mock_run_command, mock_log_warning):
        """Test that an unexpected 'release' failure logs a warning."""
        # Arrange: 'release' fails with an unknown error.
        release_result = Mock(returncode=1, stdout=b'', stderr=b'An unexpected error occurred.')
        renew_result = Mock(returncode=0)
        mock_run_command.side_effect = [release_result, renew_result]

        # Act
        release_renew_ip()

        # Assert: A warning was logged.
        mock_log_warning.assert_called_once()
        self.assertIn("unexpected non-zero exit code", mock_log_warning.call_args[0][0])

    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_whenRenewFailsWithDhcpError_shouldRaiseSpecificError(self, mock_run_command):
        """Test that a DHCP-specific error during 'renew' raises a specific exception."""
        # Arrange: 'renew' command raises an error indicating a DHCP server issue.
        dhcp_error = NetworkManagerError("An error occurred while renewing interface Wi-Fi: unable to contact your DHCP server.")
        mock_run_command.side_effect = [
            Mock(returncode=0),  # Successful release
            dhcp_error           # Failed renew
        ]

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            release_renew_ip()
        
        self.assertEqual(cm.exception.code, 'DHCP_SERVER_UNREACHABLE')
        self.assertIn("Unable to contact the DHCP server", str(cm.exception))

    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_whenRenewFailsWithAdapterDisabledError_shouldRaiseSpecificError(self, mock_run_command):
        """Test that a 'renew' failure due to a disabled adapter raises a specific exception."""
        # Arrange: 'renew' command raises an error indicating a disabled adapter.
        disabled_error = NetworkManagerError("An error occurred: no adapter is in the state permissible for this operation.")
        mock_run_command.side_effect = [
            Mock(returncode=0),  # Successful release
            disabled_error       # Failed renew
        ]

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            release_renew_ip()
        
        self.assertEqual(cm.exception.code, 'ADAPTER_DISABLED')
        self.assertIn("One or more network adapters are disabled", str(cm.exception))


    @patch('logic.system.run_system_command')
    def test_releaseRenewIp_whenRenewFailsWithGenericError_shouldReraiseOriginalError(self, mock_run_command):
        """Test that a generic 'renew' failure re-raises the original exception."""
        # Arrange: 'renew' command raises a generic error.
        generic_error = NetworkManagerError("A generic failure.")
        mock_run_command.side_effect = [
            Mock(returncode=0),  # Successful release
            generic_error        # Failed renew
        ]

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            release_renew_ip()
        
        # The re-raised exception should be the original one.
        self.assertIs(cm.exception, generic_error)
        self.assertIsNone(cm.exception.code)


if __name__ == '__main__':
    unittest.main()