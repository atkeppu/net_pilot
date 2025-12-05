import unittest
from unittest.mock import patch

class TestConstants(unittest.TestCase):
    """Tests for the constants module."""

    @patch('pathlib.Path.read_text', side_effect=FileNotFoundError)
    def test_read_version_file_not_found(self, mock_read_text):
        """
        Test that _read_version returns a default version string when
        the VERSION file is not found.
        """
        # We need to reload the module to re-trigger the _read_version function
        from gui import constants
        import importlib
        importlib.reload(constants)
        
        self.assertEqual(constants.APP_VERSION, "0.0.0-dev")