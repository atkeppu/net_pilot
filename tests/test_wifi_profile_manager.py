import unittest
from unittest.mock import patch, call, mock_open

from logic.wifi_profile_manager import (_create_wlan_profile_xml,
                                        connect_to_wifi_network,
                                        connect_with_profile_name, delete_wifi_profile)
from exceptions import NetworkManagerError


class TestCreateProfileXML(unittest.TestCase):
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
        self.assertIn("<keyType>networkKey</keyType>", xml_output)
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


class TestProfileConnection(unittest.TestCase):
    """Tests for connecting to and deleting Wi-Fi profiles."""

    @patch('logic.wifi_profile_manager.os.path.exists', return_value=True)
    @patch('logic.wifi_profile_manager.os.remove')
    @patch('logic.wifi_profile_manager.run_system_command')
    @patch('logic.wifi_profile_manager.tempfile.NamedTemporaryFile')
    def test_connect_to_wifi_network_success(self, mock_tempfile, mock_run_command, mock_os_remove, mock_os_path_exists):
        """Test a successful connection workflow using a new profile."""
        # Arrange
        mock_file = mock_open()
        mock_tempfile.return_value.__enter__.return_value = mock_file.return_value
        mock_file.return_value.name = "C:\\temp\\profile.xml"

        # Act
        connect_to_wifi_network("TestSSID", "WPA2-Personal", "CCMP", "password123")

        # Assert
        # 1. A temp file was created and written to.
        mock_file().write.assert_called_once()
        self.assertIn("<name>TestSSID</name>", mock_file().write.call_args[0][0])

        # 2. `netsh wlan add profile` and `netsh wlan connect` were called.
        expected_calls = [
            call(['netsh', 'wlan', 'add', 'profile',
                  'filename="C:\\temp\\profile.xml"'], "Failed to add Wi-Fi profile for TestSSID"),
            call(['netsh', 'wlan', 'connect', 'name="TestSSID"'],
                 "Failed to connect using profile TestSSID")
        ]
        mock_run_command.assert_has_calls(expected_calls)

        # 3. The temporary file was deleted.
        mock_os_remove.assert_called_once_with("C:\\temp\\profile.xml")

    @patch('logic.wifi_profile_manager.run_system_command')
    def test_connect_with_profile_name_invalid_key(self, mock_run_command):
        """Test that an invalid key error is correctly identified and re-raised."""
        # Arrange
        error_message = "The network security key is not correct"
        mock_run_command.side_effect = NetworkManagerError(error_message)

        # Act & Assert
        with self.assertRaises(NetworkManagerError) as cm:
            connect_with_profile_name("MyProfile")

        self.assertEqual(cm.exception.code, 'WIFI_INVALID_KEY')
        self.assertIn("The password is incorrect", str(cm.exception))

    @patch('logic.wifi_profile_manager.run_system_command')
    def test_delete_wifi_profile(self, mock_run_command):
        """Test that the delete profile command is called correctly."""
        # Arrange
        profile_name = "OldProfile"

        # Act
        delete_wifi_profile(profile_name)

        # Assert
        mock_run_command.assert_called_once_with(
            ['netsh', 'wlan', 'delete', 'profile',
             f'name="{profile_name}"'], f"Failed to delete profile {profile_name}")

if __name__ == '__main__':
    unittest.main()