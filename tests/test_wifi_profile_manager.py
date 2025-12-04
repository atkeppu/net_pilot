import unittest
import sys
import os

# Add the project root to the Python path to allow importing from 'logic'
# This makes the test runnable from the command line.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from logic.wifi_profile_manager import _create_wlan_profile_xml

class TestWifiProfileManager(unittest.TestCase):
    """
    Unit tests for the WLAN profile creation logic.
    """

    def test_create_wpa2_profile(self):
        """Test creating a profile for a WPA2-Personal network."""
        ssid = "MyWPA2Network"
        auth = "WPA2-Personal"
        enc = "CCMP"
        password = "MyPassword123"

        xml_output = _create_wlan_profile_xml(ssid, auth, enc, password)

        self.assertIn(f"<name>{ssid}</name>", xml_output)
        self.assertIn("<authentication>WPA2PSK</authentication>", xml_output)
        self.assertIn("<encryption>AES</encryption>", xml_output)
        self.assertIn("<keyType>passPhrase</keyType>", xml_output)
        self.assertIn(f"<keyMaterial>{password}</keyMaterial>", xml_output)
        self.assertIn("<protected>false</protected>", xml_output)

    def test_create_wpa3_profile(self):
        """Test creating a profile for a WPA3-Personal network."""
        ssid = "MyWPA3Network"
        auth = "WPA3-Personal"
        enc = "CCMP"
        password = "MyWPA3Password"

        xml_output = _create_wlan_profile_xml(ssid, auth, enc, password)

        self.assertIn(f"<name>{ssid}</name>", xml_output)
        self.assertIn("<authentication>WPA3SAE</authentication>", xml_output)
        self.assertIn("<encryption>AES</encryption>", xml_output)
        self.assertIn("<keyType>passPhrase</keyType>", xml_output)
        self.assertIn(f"<keyMaterial>{password}</keyMaterial>", xml_output)

    def test_create_open_profile(self):
        """Test creating a profile for an Open (unsecured) network."""
        ssid = "FreeWifi"
        auth = "Open"
        enc = "None"
        password = None

        xml_output = _create_wlan_profile_xml(ssid, auth, enc, password)

        self.assertIn(f"<name>{ssid}</name>", xml_output)
        self.assertIn("<authentication>open</authentication>", xml_output)
        self.assertIn("<encryption>none</encryption>", xml_output)
        self.assertNotIn("<sharedKey>", xml_output)

    def test_create_wep_profile(self):
        """Test creating a profile for a legacy WEP network."""
        ssid = "OldSchoolWEP"
        auth = "WEP"
        enc = "WEP"
        password = "wepkey"

        # The logic correctly maps WEP's authentication to 'open' in the XML
        xml_output = _create_wlan_profile_xml(ssid, auth, enc, password)

        self.assertIn(f"<name>{ssid}</name>", xml_output)
        self.assertIn("<authentication>open</authentication>", xml_output)
        self.assertIn("<encryption>WEP</encryption>", xml_output)
        self.assertIn("<keyType>networkKey</keyType>", xml_output) # WEP uses 'networkKey'
        self.assertIn(f"<keyMaterial>{password}</keyMaterial>", xml_output)

    def test_unknown_auth_defaults_to_wpa2(self):
        """Test that an unknown authentication type defaults to WPA2-PSK."""
        ssid = "UnknownAuth"
        auth = "WPA4-Enterprise" # A hypothetical future standard
        enc = "CCMP"
        password = "somepassword"

        xml_output = _create_wlan_profile_xml(ssid, auth, enc, password)

        self.assertIn("<authentication>WPA2PSK</authentication>", xml_output)
        self.assertIn("<encryption>AES</encryption>", xml_output)
        self.assertIn("<keyType>passPhrase</keyType>", xml_output)


if __name__ == '__main__':
    unittest.main()