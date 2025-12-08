import unittest
from unittest.mock import patch, Mock
import sys
import importlib

class TestMainStartup(unittest.TestCase):
    """Tests for the main.py startup and pre-flight check logic."""

    def setUp(self):
        """
        Import the 'main' module here to ensure mocks are applied correctly
        for each test, avoiding issues with module caching.
        """
        global main
        import main
        # We need to reload it in case it was imported by another test file.
        importlib.reload(main)

    @patch('main.logger_setup.setup_logging')
    @patch('main.initialize_language')
    @patch('main.is_admin', return_value=True)
    @patch('main.AppContext')
    @patch('main.NetworkManagerApp')
    def test_main_success_path(self, mock_app, mock_context, mock_is_admin, mock_init_lang, mock_logging):
        """Test the main function's successful execution path."""
        mock_app_instance = mock_app.return_value
        main.main()
        mock_is_admin.assert_called_once()
        mock_app.assert_called_once_with(mock_context.return_value)
        mock_app_instance.mainloop.assert_called_once()
 
    @patch('main.logger_setup.setup_logging')
    @patch('main.initialize_language')
    @patch('main.messagebox.showerror')
    def test_main_unsupported_os(self, mock_showerror, mock_init_lang, mock_logging):
        """Test that main exits on a non-Windows OS."""
        with patch('sys.platform', 'linux'):
            # We need to reload the module to re-trigger the platform check
            importlib.reload(main)
            main.main() # type: ignore
        mock_showerror.assert_called_once()

    @patch('main.logger_setup.setup_logging')
    @patch('main.initialize_language')
    @patch('main.is_admin', return_value=False)
    @patch('main.relaunch_as_admin')
    @patch('main.NetworkManagerApp')
    def test_main_relaunch_as_admin(self, mock_app, mock_relaunch, mock_is_admin,
                                    mock_init_lang, mock_logging):
        """Test that main attempts to relaunch if not admin."""
        main.main()
        mock_relaunch.assert_called_once()
        mock_app.assert_not_called() # The main app should not start
 
    @patch('main.logger_setup.setup_logging')
    @patch('main.initialize_language')
    @patch('main.is_admin', return_value=False)
    @patch('main.relaunch_as_admin', side_effect=Exception("Relaunch failed"))
    @patch('main.messagebox.showerror')
    def test_main_relaunch_fails(self, mock_showerror, mock_relaunch,
                                 mock_is_admin, mock_init_lang, mock_logging):
        """Test that an error is shown if relaunching fails."""
        main.main()
        mock_relaunch.assert_called_once()
        mock_showerror.assert_called_once()

    @patch('main.logger_setup.setup_logging')
    @patch('main.initialize_language')
    @patch('main.is_admin', return_value=True)
    @patch('main.NetworkManagerApp', side_effect=Exception("Generic unhandled error"))
    @patch('main.messagebox.showerror')
    def test_main_generic_exception_path(self, mock_showerror, mock_app,
                                         mock_is_admin, mock_init_lang, mock_logging):
        """Test that a generic Exception during app initialization is caught."""
        main.main()
        mock_showerror.assert_called_once()
        # Check for the actual translated title string, not the key
        self.assertIn(main.get_string("fatal_error_title"),
                      mock_showerror.call_args.args)