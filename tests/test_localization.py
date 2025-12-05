import unittest
from unittest.mock import patch

import localization

class TestLocalization(unittest.TestCase):
    """Tests for the localization module."""

    def tearDown(self):
        # Reset to default after each test
        localization.CURRENT_LANGUAGE = localization.DEFAULT_LANGUAGE

    @patch('localization.locale.getdefaultlocale', return_value=('fi_FI', 'cp1252'))
    def test_initialize_language_detects_fi(self, mock_getlocale):
        """Test that 'fi' is correctly detected."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('localization.configparser.ConfigParser.get', return_value=None):
            localization.initialize_language()
            self.assertEqual(localization.CURRENT_LANGUAGE, 'fi')

    @patch('localization.locale.getdefaultlocale', return_value=('en_US', 'cp1252'))
    def test_initialize_language_detects_en(self, mock_getlocale):
        """Test that 'en' is correctly detected."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('localization.configparser.ConfigParser.get', return_value=None):
            localization.initialize_language()
            self.assertEqual(localization.CURRENT_LANGUAGE, 'en')

    @patch('localization.locale.getdefaultlocale', return_value=('de_DE', 'cp1252'))
    def test_initialize_language_falls_back_to_default(self, mock_getlocale):
        """Test that an unsupported language falls back to the default ('en')."""
        with patch('pathlib.Path.exists', return_value=False), \
             patch('localization.configparser.ConfigParser.get', return_value=None):
            localization.initialize_language()
            self.assertEqual(localization.CURRENT_LANGUAGE, localization.DEFAULT_LANGUAGE)

    def test_get_string_with_formatting(self):
        """Test that get_string correctly formats a string with keyword arguments."""
        localization.CURRENT_LANGUAGE = 'en'
        result = localization.get_string('log_file_hint', log_file_path="C:\\log.txt")
        self.assertIn("C:\\log.txt", result)

    def test_get_string_missing_key(self):
        """Test that a missing key returns a placeholder."""
        self.assertEqual(localization.get_string('non_existent_key'), '<non_existent_key>')