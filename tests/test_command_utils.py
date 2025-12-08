import unittest
from unittest.mock import patch, MagicMock
import subprocess

from logic.command_utils import (_safe_decode, run_system_command, run_ps_command,
                                 run_external_ps_script)
from exceptions import NetworkManagerError

class TestSafeDecode(unittest.TestCase):
    """Tests for the _safe_decode utility function."""

    def test_decode_utf8(self):
        self.assertEqual(_safe_decode(b'hello'), 'hello')

    def test_decode_oem(self):
        # Simulate a common OEM character like 'ä'
        self.assertEqual(_safe_decode(b'\x84'), 'ä')

    @patch('logic.command_utils._decode_with_encoding')
    def test_decode_fallback_to_ascii_ignore(self, mock_decode_with_encoding):
        """Test that the final ascii fallback is used if both utf-8 and oem fail."""
        # Arrange: Make the first two decode attempts (utf-8, oem) fail,
        # and the final one (ascii) succeed.
        mock_decode_with_encoding.side_effect = [
            UnicodeDecodeError('mock', b'', 0, 1, 'mock reason'), # Fails for 'utf-8'
            UnicodeDecodeError('mock', b'', 0, 1, 'mock reason'), # Fails for 'oem'
            '????' # The result of the ascii decode with replacement
        ]
        # Act & Assert
        self.assertEqual(_safe_decode(b'\xde\xad\xbe\xef'), '????')

    def test_decode_none_or_empty(self):
        """Test that None or empty bytes are handled correctly."""
        self.assertEqual(_safe_decode(None), '')
        self.assertEqual(_safe_decode(b''), '')

class TestRunSystemCommand(unittest.TestCase):
    """Tests for the run_system_command function."""

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_success(self, mock_popen):
        """Test a successful command execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b'success output', b'')
        mock_popen.return_value.__enter__.return_value = mock_process

        result = run_system_command(["echo", "hello"], "Test success")

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'success output')

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_timeout(self, mock_popen):
        """Test that a TimeoutExpired exception is caught and wrapped."""
        mock_process = MagicMock()
        mock_process.communicate.side_effect = subprocess.TimeoutExpired(cmd="ping", timeout=10)
        mock_popen.return_value.__enter__.return_value = mock_process

        with self.assertRaisesRegex(NetworkManagerError, "The operation timed out"):
            run_system_command(["ping"], "Test ping")

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_file_not_found(self, mock_popen):
        """Test that a FileNotFoundError is caught and wrapped."""
        mock_popen.side_effect = FileNotFoundError

        with self.assertRaisesRegex(NetworkManagerError, "Command 'nonexistent' not found"):
            run_system_command(["nonexistent"], "Test")

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_failure_with_stderr(self, mock_popen):
        """Test that a command failure with stderr raises a formatted error."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'some output', b'error details')
        mock_popen.return_value.__enter__.return_value = mock_process

        with self.assertRaises(NetworkManagerError) as cm:
            run_system_command(["failing_cmd"], "Test failure")

        # The user-facing error should prioritize stderr
        self.assertIn("Test failure: error details", str(cm.exception))

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_failure_without_stderr(self, mock_popen):
        """Test that a command failure without stderr falls back to a generic message."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        # Simulate no output on stdout or stderr
        mock_process.communicate.return_value = (b'', b'')
        mock_popen.return_value.__enter__.return_value = mock_process

        with self.assertRaises(NetworkManagerError) as cm:
            run_system_command(["failing_cmd"], "Test failure")

        self.assertIn("An unknown error occurred.", str(cm.exception))

    @patch('logic.command_utils.subprocess.Popen')
    def test_command_failure_with_encoded_command_logging(self, mock_popen):
        """Test that EncodedCommand is not fully logged."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.communicate.return_value = (b'', b'error')
        mock_popen.return_value.__enter__.return_value = mock_process

        with self.assertLogs('logic.command_utils', level='DEBUG') as cm, \
             self.assertRaises(NetworkManagerError):
            run_system_command(["powershell", "-EncodedCommand", "longbase64string"], "Test failure")
        
        # Check that the logged command was shortened
        self.assertIn("Executing system command: powershell -EncodedCommand <...>",
                      cm.output[0])
        # Check that the full error is still logged
        self.assertIn("longbase64string", cm.output[1])

class TestRunPsCommand(unittest.TestCase):
    """Tests for PowerShell command runners."""

    @patch('logic.command_utils.run_system_command')
    def test_run_ps_command_success(self, mock_run_system):
        """Test a successful PowerShell command execution."""
        mock_run_system.return_value.stdout = b'Success'
        result = run_ps_command("Get-Process")
        self.assertEqual(result, "Success")
        self.assertIn("-EncodedCommand", mock_run_system.call_args[0][0])

    @patch('logic.command_utils.run_system_command', side_effect=NetworkManagerError("PS Error"))
    def test_run_ps_command_failure(self, mock_run_system):
        """Test that an error from run_system_command is propagated."""
        with self.assertRaisesRegex(NetworkManagerError, "PS Error"):
            run_ps_command("Get-Process")

    @patch('logic.command_utils.open', new_callable=unittest.mock.mock_open, read_data='Get-Host')
    @patch('logic.command_utils.run_ps_command')
    def test_run_external_ps_script_success(self, mock_run_ps, mock_open):
        """Test running an external script file successfully."""
        run_external_ps_script("test_script.ps1")
        mock_open.assert_called_once()
        mock_run_ps.assert_called_with('Get-Host')

    @patch('logic.command_utils.open', new_callable=unittest.mock.mock_open, read_data='Get-Host')
    @patch('logic.command_utils.run_ps_command')
    def test_run_external_ps_script_with_args(self, mock_run_ps, mock_open):
        """Test running an external script with arguments."""
        run_external_ps_script("test_script.ps1", ps_args=["$var=1"])
        # Check that the arguments are prepended to the script content
        expected_script_content = "$var=1;\nGet-Host"
        mock_run_ps.assert_called_with(expected_script_content)

    @patch('logic.command_utils.os.path.dirname', return_value='/fake/dir')
    @patch('logic.command_utils.open')
    def test_run_external_ps_script_file_not_found(self, mock_open, mock_dirname):
        """Test that a FileNotFoundError for the script file is wrapped."""
        mock_open.side_effect = FileNotFoundError
        with self.assertRaisesRegex(NetworkManagerError, "PowerShell script 'test.ps1' not found"):
            run_external_ps_script("test.ps1")

if __name__ == '__main__':
    unittest.main()