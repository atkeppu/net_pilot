import unittest
from unittest.mock import patch, mock_open, MagicMock, call
from pathlib import Path
import sys
import subprocess
import io

import build
from build import (
    increment_version, get_app_version, find_iscc, find_upx,
    create_version_file, run_inno_setup, create_git_info_file,
    get_pyinstaller_command
)

class TestBuildScript(unittest.TestCase):

    @patch('pathlib.Path.write_text')
    @patch('pathlib.Path.read_text', return_value='1.2.3')
    def test_increment_version(self, mock_read, mock_write):
        """Test version incrementing for major, minor, and patch."""
        increment_version('patch')
        mock_write.assert_called_with('1.2.4', encoding='utf-8')

        increment_version('minor')
        mock_write.assert_called_with('1.3.0', encoding='utf-8')

        increment_version('major')
        mock_write.assert_called_with('2.0.0', encoding='utf-8')

    @patch('pathlib.Path.read_text', side_effect=FileNotFoundError)
    def test_increment_version_file_not_found(self, mock_read):
        """Test that increment_version raises RuntimeError if VERSION file is not found."""
        with self.assertRaises(RuntimeError):
            increment_version('patch')

    @patch('pathlib.Path.read_text', return_value='1.2.3')
    def test_get_app_version_success(self, mock_read):
        """Test successful reading of the app version."""
        self.assertEqual(get_app_version(), '1.2.3')

    @patch('pathlib.Path.read_text', side_effect=FileNotFoundError)
    def test_get_app_version_file_not_found(self, mock_read):
        """Test that get_app_version raises RuntimeError if VERSION file is not found."""
        with self.assertRaises(RuntimeError):
            get_app_version()

    @patch('os.environ.get', return_value=r'C:\Program Files (x86)')
    @patch('pathlib.Path.is_file', return_value=True)
    def test_find_iscc_found(self, mock_is_file, mock_environ):
        """Test finding the Inno Setup compiler."""
        expected_path = Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
        self.assertEqual(find_iscc(), expected_path)

    @patch('os.environ.get', return_value='')
    @patch('pathlib.Path.is_file', return_value=False)
    def test_find_iscc_not_found(self, mock_is_file, mock_environ):
        """Test that find_iscc returns None when the compiler is not found."""
        self.assertIsNone(find_iscc())

    @patch('shutil.which', return_value='/usr/bin/upx')
    def test_find_upx_found(self, mock_which):
        """Test finding the UPX executable."""
        self.assertEqual(find_upx(), Path('/usr/bin'))

    @patch('shutil.which', return_value=None)
    def test_find_upx_not_found(self, mock_which):
        """Test that find_upx returns None when UPX is not found."""
        self.assertIsNone(find_upx())

    @patch('builtins.open', new_callable=mock_open)
    def test_create_version_file(self, mock_file):
        """Test the creation of the PyInstaller version file."""
        create_version_file("1.2.3")
        mock_file.assert_called_once_with(build.VERSION_FILE, "w", encoding="utf-8")
        handle = mock_file()
        # Check that some key fields are present in the written content
        written_content = handle.write.call_args[0][0]
        self.assertIn("filevers=(1,2,3, 0)", written_content)
        self.assertIn("FileVersion', u'1.2.3'", written_content)
        self.assertIn("ProductName', u'NetPilot'", written_content)

    @patch('build.run_command')
    def test_run_inno_setup_success(self, mock_run_command):
        """Test running Inno Setup successfully."""
        mock_iscc_path = Path('/fake/iscc.exe')
        with patch('pathlib.Path.is_file', side_effect=[True, True]): # setup.iss exists, installer is created
            with patch('pathlib.Path.unlink') as mock_unlink:
                result = run_inno_setup(mock_iscc_path, "1.2.3")
                mock_run_command.assert_called_once_with(
                    [str(mock_iscc_path), '/DAppVersion=1.2.3', str(Path.cwd() / "setup.iss")],
                    "Rakennetaan asennusohjelmaa Inno Setupilla"
                )
                self.assertIn("NetPilot-1.2.3-setup.exe", result)

    @patch('build.run_command')
    def test_run_inno_setup_script_not_found(self, mock_run_command):
        """Test that Inno Setup is skipped if setup.iss is not found."""
        with patch('pathlib.Path.is_file', return_value=False):
            result = run_inno_setup(Path('/fake/iscc.exe'), "1.2.3")
            self.assertIsNone(result)
            mock_run_command.assert_not_called()

    @patch('json.dumps')
    @patch('pathlib.Path.write_text')
    @patch('subprocess.run')
    def test_create_git_info_file_success(self, mock_run, mock_write_text, mock_json_dumps):
        """Test successful creation of git_info.json."""
        mock_run.return_value = MagicMock(stdout="https://github.com/user/repo.git", check_returncode=None)
        create_git_info_file()
        mock_json_dumps.assert_called_once_with({"repository": "user/repo"})
        mock_write_text.assert_called_once()

    @patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, "cmd"))
    def test_create_git_info_file_failure(self, mock_run):
        """Test that git_info.json creation fails gracefully."""
        # Redirect stdout to capture the print output
        with patch('sys.stdout', new_callable=io.StringIO) as mock_stdout:
            create_git_info_file()
            # Check that a warning was printed
            self.assertIn("Varoitus", mock_stdout.getvalue())

    def test_get_pyinstaller_command_without_upx(self):
        """Test that the PyInstaller command is built correctly without UPX."""
        command = get_pyinstaller_command("version.txt", None)
        self.assertNotIn("--upx-dir", command)
        self.assertIn("--onefile", command)
        self.assertIn(f"--name={build.APP_NAME}", command)

    def test_get_pyinstaller_command_with_upx(self):
        """Test that the PyInstaller command includes the UPX directory."""
        upx_path = Path("/path/to/upx")
        command = get_pyinstaller_command("version.txt", upx_path)
        self.assertIn("--upx-dir", command)
        self.assertIn(str(upx_path), command)

    @patch('build.clean_previous_builds')
    @patch('build.get_app_version', return_value="1.0.0")
    @patch('build.create_version_file')
    @patch('build.find_upx', return_value=None)
    @patch('build.get_pyinstaller_command')
    @patch('build.run_command')
    @patch('build.create_git_info_file')
    @patch('build.generate_changelog')
    @patch('build.find_iscc', return_value=None)
    @patch('build.print_summary')
    @patch('os.path.exists', return_value=False)
    @patch('os.remove')
    def test_main_flow(self, mock_os_remove, mock_os_exists, mock_print_summary, mock_find_iscc,
                       mock_gen_changelog, mock_create_git_info, mock_run_cmd,
                       mock_get_py_cmd, mock_find_upx, mock_create_ver,
                       mock_get_ver, mock_clean):
        """Test the main build function orchestrates calls correctly."""
        with patch.object(sys, 'argv', ['build.py']):
             build.main()

        mock_clean.assert_called_once()
        mock_get_ver.assert_called_once()
        mock_create_ver.assert_called_once_with("1.0.0")
        mock_find_upx.assert_called_once()
        mock_get_py_cmd.assert_called_once()
        # run_command is called for PyInstaller
        self.assertEqual(mock_run_cmd.call_count, 1)
        mock_create_git_info.assert_called_once()
        mock_gen_changelog.assert_called_once_with("1.0.0")
        mock_find_iscc.assert_called_once()
        mock_print_summary.assert_called_once()

if __name__ == '__main__':
    unittest.main()