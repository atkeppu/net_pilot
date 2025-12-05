import unittest

from gui.utils import format_speed

class TestFormatSpeed(unittest.TestCase):
    """Tests for the format_speed utility function."""

    def test_format_speed_kbps(self):
        self.assertEqual(format_speed(12500), "100.0 kbps")

    def test_format_speed_mbps(self):
        self.assertEqual(format_speed(1250000), "10.00 Mbps")

    def test_format_speed_negative_input(self):
        self.assertEqual(format_speed(-1000), "0.0 kbps")

    def test_format_speed_invalid_type(self):
        with self.assertRaises(TypeError):
            format_speed("not a number")