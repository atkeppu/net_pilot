import unittest
from unittest.mock import patch, MagicMock
import sys
from logic.system import (is_admin, reset_network_stack, flush_dns_cache,
                          release_renew_ip, terminate_process_by_pid,
                          relaunch_as_admin)
from exceptions import NetworkManagerError

class TestIsAdmin(unittest.TestCase):
    """Unit tests for the is_admin function."""

    @patch('sys.platform', 'win32')
    def test_is_admin_true_on_windows_with_admin(self):
        """Test is_admin returns True on Windows when user is an admin."""
        # Mokataan ctypes-kirjaston Windows-spesifinen kutsu
        with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=1):
            self.assertTrue(is_admin())

    @patch('sys.platform', 'win32')
    def test_is_admin_false_on_windows_without_admin(self):
        """Test is_admin returns False on Windows when user is not an admin."""
        with patch('ctypes.windll.shell32.IsUserAnAdmin', return_value=0):
            self.assertFalse(is_admin())

    def test_is_admin_false_on_non_windows(self):
        """Test is_admin returns False on non-Windows platforms."""
        with patch('sys.platform', 'linux'), \
             patch('ctypes.windll', new_callable=MagicMock) as mock_windll:
            self.assertFalse(is_admin())
            mock_windll.shell32.IsUserAnAdmin.assert_not_called()
 
    @patch('sys.platform', 'win32')
    def test_is_admin_handles_attribute_error(self):
        """Test is_admin returns False if IsUserAnAdmin function is missing."""
        with patch('ctypes.windll.shell32.IsUserAnAdmin', side_effect=AttributeError):
            self.assertFalse(is_admin())

class TestSystemCommands(unittest.TestCase):
    """Unit tests for other system command functions."""

    @patch('logic.system.run_system_command')
    def test_reset_network_stack(self, mock_run):
        """Test that reset_network_stack calls the correct netsh command."""
        reset_network_stack()
        mock_run.assert_called_once_with(
            ['netsh', 'winsock', 'reset'], "Failed to reset network stack.")

    @patch('logic.system.run_system_command')
    def test_flush_dns_cache(self, mock_run):
        """Test that flush_dns_cache calls the correct ipconfig command."""
        flush_dns_cache()
        mock_run.assert_called_once_with(
            ['ipconfig', '/flushdns'], "Failed to flush DNS cache.")

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_success(self, mock_run):
        """Test a successful IP release and renew sequence."""
        # Simulate both commands succeeding
        mock_run.return_value = MagicMock(returncode=0)
        release_renew_ip()

        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(
            ['ipconfig', '/release'], "IP address release command finished.", check=False)
        mock_run.assert_any_call(
            ['ipconfig', '/renew'], "Failed to renew IP address.")

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_release_fails_with_other_error(self, mock_run):
        """Test that a non-critical but unexpected error in 'release' is logged as a warning."""
        # Simulate 'release' failing with a different error, and 'renew' succeeding.
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr=b"some other random error"),
            MagicMock(returncode=0)
        ]
        with self.assertLogs('logic.system', level='WARNING') as cm:
            release_renew_ip()
            self.assertIn("unexpected non-zero exit code", cm.output[0])
        self.assertEqual(mock_run.call_count, 2)

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_release_fails_gracefully(self, mock_run):
        """Test that renew is still called if release fails with a non-critical error."""
        # Simulate 'release' failing with a known safe error, and 'renew' succeeding.
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr=b"media is disconnected"),
            MagicMock(returncode=0)
        ]

        release_renew_ip()

        self.assertEqual(mock_run.call_count, 2)
        mock_run.assert_any_call(
            ['ipconfig', '/renew'], "Failed to renew IP address.")

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_renew_fails_with_dhcp_error(self, mock_run):
        """Test that a specific DHCP error during renew is correctly identified."""
        # Simulate 'release' succeeding, but 'renew' failing with a DHCP error.
        mock_run.side_effect = [
            MagicMock(returncode=0),
            NetworkManagerError("unable to contact your dhcp server")
        ]

        with self.assertRaises(NetworkManagerError) as cm:
            release_renew_ip()

        self.assertEqual(cm.exception.code, 'DHCP_SERVER_UNREACHABLE')

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_renew_fails_with_adapter_disabled_error(self, mock_run):
        """Test that a specific 'adapter disabled' error during renew is
        correctly identified."""
        # Simulate 'release' succeeding, but 'renew' failing with the specific error.
        mock_run.side_effect = [
            MagicMock(returncode=0),
            NetworkManagerError("no adapter is in the state permissible")
        ]
        with self.assertRaises(NetworkManagerError) as cm:
            release_renew_ip()
        self.assertEqual(cm.exception.code, 'ADAPTER_DISABLED')

    @patch('logic.system.run_system_command')
    def test_release_renew_ip_renew_fails_with_generic_error(self, mock_run):
        """Test that a generic error during renew is re-raised."""
        # Simulate 'release' succeeding, but 'renew' failing with a generic error.
        mock_run.side_effect = [
            MagicMock(returncode=0),
            NetworkManagerError("A generic failure.")
        ]
        with self.assertRaisesRegex(NetworkManagerError, "A generic failure.") as cm:
            release_renew_ip()
        self.assertIsNone(cm.exception.code) # Ensure it's not a specific coded error

    @patch('logic.system.run_system_command')
    def test_terminate_process_by_pid_success(self, mock_run):
        """Test a successful process termination."""
        pid_to_kill = 1234
        terminate_process_by_pid(pid_to_kill)
        mock_run.assert_called_once_with(['taskkill',
                                          '/F',
                                          '/T',
                                          '/PID',
                                          str(pid_to_kill)],
                                         f"Failed to terminate process with PID {pid_to_kill}.")

    def test_terminate_process_by_pid_critical_process(self):
        """Test that terminating critical system PIDs is blocked."""
        with self.assertRaisesRegex(NetworkManagerError, "system-critical processes is not allowed"):
            terminate_process_by_pid(0)
        with self.assertRaisesRegex(NetworkManagerError, "system-critical processes is not allowed"):
            terminate_process_by_pid(4)

    @patch('logic.system.run_system_command', side_effect=NetworkManagerError("Taskkill failed."))
    def test_terminate_process_by_pid_failure(self, mock_run):
        """Test that an error from taskkill is propagated."""
        with self.assertRaisesRegex(NetworkManagerError, "Taskkill failed."):
            terminate_process_by_pid(1234)


if __name__ == '__main__':
    unittest.main()