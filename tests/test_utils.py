import unittest
import sys
import os

# Add the project root to the Python path to allow importing from 'gui'
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from gui.utils import format_speed

class TestFormatSpeed(unittest.TestCase):
    """
    Unit tests for the format_speed utility function.
    """

    def test_speed_formatting_cases(self):
        """Test various speed formatting scenarios using subtests."""
        test_cases = {
            "zero_speed": (0, "0.0 kbps"),
            "kbps_speed": (50000, "400.0 kbps"), # 50,000 Bps = 400.0 kbps
            "kbps_with_rounding": (12345, "98.8 kbps"), # 12345 Bps = 98.76 kbps -> 98.8 kbps
            "mbps_threshold_exact": (125000, "1.00 Mbps"), # 125,000 Bps = 1.00 Mbps
            "mbps_speed": (1500000, "12.00 Mbps"), # 1,500,000 Bps = 12.00 Mbps
            "mbps_with_rounding": (1567890, "12.54 Mbps"), # 1,567,890 Bps = 12.543 Mbps -> 12.54 Mbps
            "just_below_mbps_threshold": (124999, "1000.0 kbps"), # 124,999 Bps = 999.992 kbps -> 1000.0 kbps
            "gbps_speed_shows_as_mbps": (125000000, "1000.00 Mbps") # 1 Gbps shows as 1000 Mbps
        }

        for name, (input_val, expected) in test_cases.items():
            with self.subTest(msg=name):
                self.assertEqual(format_speed(input_val), expected)

    def test_negative_input(self):
        """Test that a negative input is handled gracefully and returns 0.0 kbps."""
        # A speed cannot be negative, so it should be treated as zero.
        self.assertEqual(format_speed(-1000), "0.0 kbps")

    def test_invalid_type_input(self):
        """Test that a non-numeric input raises a TypeError."""
        with self.assertRaises(TypeError):
            format_speed("not a number")
        with self.assertRaises(TypeError):
            format_speed(None)

def format_speed(Bps: float) -> str:
    """Formats speed from Bytes/sec to a readable string (kbps/Mbps)."""
    if not isinstance(Bps, (int, float)) or Bps < 0:
        return "0.0 kbps"
        
    if Bps < 125000:  # Under 1 Mbps (125,000 Bytes/sec)
        return f"{Bps * 8 / 1000:.1f} kbps"
    else:
        return f"{Bps * 8 / 1000000:.2f} Mbps"

if __name__ == '__main__':
    unittest.main()