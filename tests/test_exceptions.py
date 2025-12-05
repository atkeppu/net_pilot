import unittest

from exceptions import NetworkManagerError

class TestNetworkManagerError(unittest.TestCase):
    """
    Unit tests for the NetworkManagerError custom exception.
    """

    def test_initialization_without_code(self):
        """Test that the exception initializes correctly without a code."""
        message = "A standard error occurred."
        error = NetworkManagerError(message)
        self.assertEqual(error.args[0], message)
        self.assertIsNone(error.code)

    def test_initialization_with_code(self):
        """Test that the exception initializes correctly with a code."""
        message = "A specific error occurred."
        code = "SPECIFIC_ERROR"
        error = NetworkManagerError(message, code=code)
        self.assertEqual(error.args[0], message)
        self.assertEqual(error.code, code)

    def test_str_representation_without_code(self):
        """Test the string representation when no code is provided."""
        message = "A standard error."
        error = NetworkManagerError(message)
        self.assertEqual(str(error), message)

    def test_str_representation_with_code(self):
        """Test the string representation when a code is provided."""
        message = "A specific error."
        code = "ERROR_CODE_123"
        error = NetworkManagerError(message, code=code)
        expected_str = f"{message} (code: {code})"
        self.assertEqual(str(error), expected_str)

if __name__ == '__main__':
    unittest.main()