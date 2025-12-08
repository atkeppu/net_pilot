import locale
import configparser
from pathlib import Path

# --- Language Configuration ---
LANG_CODE_KEY = 'lang_code' # A special key to get the current language code itself
SUPPORTED_LANGUAGES = ['en', 'fi']
CURRENT_LANGUAGE = 'en'  # Default, will be updated by initialize_language
DEFAULT_LANGUAGE = 'en'

# --- String Definitions ---
STRINGS = {
    'en': {
        LANG_CODE_KEY: 'en',
        # Startup Errors
        'unsupported_os_title': "Unsupported OS",
        'unsupported_os_message': "This application is designed for Windows only.",
        'admin_required_title': "Admin Rights Required",
        'admin_required_relaunch_prompt': "This application requires administrative privileges to function correctly.\n\nDo you want to restart it as an administrator?",
        'language_change_title': "Language Change",
        'language_change_message': "The language will be updated the next time you start the application.",
        'language_restart_prompt_title': "Restart Required",
        'language_restart_prompt_message': "The language has been changed. Do you want to restart the application now for the changes to take effect?",
        'relaunch_failed_title': "Relaunch Failed",
        'relaunch_failed_message': "Could not restart the application with admin rights. Please check the log file for details.",

        # Generic Errors
        'ui_error_title': "UI Error",
        'ui_error_message': "A critical error occurred with the user interface components. Please check the log file for details.",
        'fatal_error_title': "Fatal Error",
        'fatal_error_message': "A critical error occurred and the application must close. Please check the log file for details.",

        # Log file hint
        'log_file_hint': "\n\nFor more details, see the log file:\n{log_file_path}",

        # Main UI
        'app_title': "NetPilot",
        'status_initializing': "Initializing...",
        'status_initial_load': "Loading initial data...",
        'status_op_cancelled': "Operation cancelled.",
        'status_op_cancelled_by_user': "Operation cancelled by user.",
        'status_enable_attempt': "Attempting to enable '{adapter_name}'...",
        'status_disable_attempt': "Attempting to disable '{adapter_name}'...",
        'status_reset_attempt': "Resetting network stack...",
        'status_failed_op': "Failed to change status for '{adapter_name}'.",
        'status_not_needed': "Operation not needed.",
        'status_refreshing_list': "Refreshing list...",
        'status_disconnect_and_disable': "Attempting automated two-step action...",
        'status_reset_success': "Network stack reset. Reboot required.",
        'status_dns_flush_success': "DNS cache flushed.",
        'status_ip_renew_success': "IP addresses renewed.",
        'status_wifi_disconnected': "Wi-Fi disconnected.",
        'status_ready_select_adapter': "Ready. Select an adapter from the list.",
        'status_fetching': "Fetching...",

        # Menu
        'menu_tools': "Tools",
        'menu_reset_stack': "Reset Network Stack...",
        'menu_release_renew': "Release & Renew IP",
        'menu_flush_dns': "Flush DNS Cache",
        'menu_connections': "Active Connections...",
        'menu_traceroute': "Trace Route...",
        'menu_wifi': "Wi-Fi Networks...",
        'menu_language': "Language",
        'menu_lang_en': "English",
        'menu_lang_fi': "Suomi",
        'menu_publish': "Publish Release...",
        'menu_help': "Help",
        'menu_open_log': "Open Log File",
        'menu_about': "About...",

        # Dialogs
        'about_title': "About NetPilot",
        'about_message_content': "{app_name}\n\nVersion: {version}\nAuthor: {author}",
        'publish_title': "Publish New Release",
        'publish_repo': "Repository (owner/repo):",
        'publish_version': "Version / Tag:",
        'publish_version_tooltip': "Must start with 'v', e.g., v1.2.3",
        'publish_release_title': "Release Title:",
        'publish_notes': "Release Notes:",
        'publish_button': "Publish Release",
        'publish_cancel': "Cancel",
        'publish_missing_info': "Missing Information",
        'publish_missing_info_msg': "Repository, Version, and Title fields are required.",

        # UI Frames
        'available_adapters_title': "Available Adapters",
        'no_adapters_found': "No adapters found.",
        'adapter_details_title': "Adapter Details",
        'button_connect': "Enable",
        'button_disconnect': "Disable",
        'context_menu_copy': "Copy",
        'status_copied_to_clipboard': "Copied '{text}' to clipboard.",
        'wifi_status_title': "Current Wi-Fi Connection",
        'diagnostics_title': "Network Diagnostics",

        # Adapter Details Labels
        'details_description': "Description",
        'details_mac': "MAC Address",
        'details_ipv4': "IPv4 Address",
        'details_ipv6': "IPv6 Address",
        'details_link_speed': "Link Speed",
        'details_download_speed': "Download Speed",
        'details_upload_speed': "Upload Speed",
        'details_driver_version': "Driver Version",
        'details_driver_date': "Driver Date",
        'diag_public_ip': "Public IP",
        'diag_gateway': "Gateway",
        'diag_gateway_latency': "Gateway Latency",
        'diag_external_latency': "External Latency",
        'diag_dns_servers': "DNS Servers",
        'diag_ping_target': "Ping Target",
        'wifi_status_ssid': "SSID",
        'wifi_status_signal': "Signal",
        'wifi_status_ip': "IP Address",
        'wifi_status_not_connected': "Not Connected",
        'wifi_button_disconnect': "Disconnect",
        'netstat_title': "Active Connections (netstat)",
        'netstat_filter_by': "Filter by protocol:",
        'netstat_filter_all': "All",
        'netstat_filter_tcp': "TCP",
        'netstat_filter_udp': "UDP",
        'netstat_col_proto': "Proto",
        'netstat_col_local': "Local Address",
        'netstat_col_foreign': "Foreign Address",
        'netstat_col_state': "State",
        'netstat_col_process': "Process Name",
        'netstat_button_refresh': "Refresh",
        'netstat_button_terminate': "Terminate Process",
        'traceroute_title': "Trace Route",
        'traceroute_target': "Target:",
        'traceroute_button_start': "Start",
        'traceroute_starting': "Tracing route to {target}...",
        'wifi_window_title': "Wi-Fi Management",
        'wifi_tab_available': "Available Networks",
        'wifi_tab_saved': "Saved Profiles",
        'wifi_col_ssid': "SSID",
        'wifi_col_signal': "Signal",
        'wifi_col_auth': "Authentication",
        'wifi_col_encrypt': "Encryption",
        'wifi_col_profile': "Profile Name",
        'wifi_col_password': "Password",
        'wifi_button_refresh': "Refresh",
        'wifi_button_connect': "Connect",
        'wifi_button_delete': "Delete Profile",
        'wifi_button_copy_pass': "Copy Password",
        'wifi_button_export': "Export to File...",
        'wifi_password_prompt_title': "Password Required",
        'wifi_password_prompt_msg': "Enter password for {ssid}:",
        'wifi_connect_status': "Connecting to {ssid}...",
        'wifi_delete_confirm_title': "Confirm Deletion",
        'wifi_delete_confirm_msg': "Are you sure you want to delete the profile '{profile_name}'?",
        'wifi_no_networks_found': "No Wi-Fi networks found.",

        # Queue Handler Messages
        'toggle_error_title': "Execution Error",
        'toggle_error_message': "Operation failed:\n\n{error}",
        'toggle_info_title': "Information",
        'toggle_wifi_connected_title': "Action Required",
        'toggle_confirm_enable_title': "Confirm Enable",
        'toggle_confirm_enable_prompt': "Are you sure you want to enable the adapter '{adapter_name}'?",
        'toggle_confirm_disable_title': "Confirm Disable",
        'toggle_confirm_disable_prompt': "Are you sure you want to disable the adapter '{adapter_name}'?",
        'toggle_wifi_connected_prompt': "Could not disable '{adapter}' because it is connected to a network.\n\nDo you want to automatically disconnect from Wi-Fi and then disable the adapter?",
        'reset_stack_success_title': "Success",
        'reset_stack_success_message': "Network stack has been reset.\nPlease reboot your computer for the changes to take effect.",
        'flush_dns_success_title': "Success",
        'flush_dns_success_message': "Successfully flushed the DNS resolver cache.",
        'release_renew_success_title': "Success",
        'release_renew_success_message': "Successfully released and renewed IP addresses. Refreshing adapter list.",
        'disconnect_wifi_success_title': "Success",
        'disconnect_wifi_success_message': "Successfully disconnected from the Wi-Fi network.",
        'netstat_selection_required': "Selection Required",
        'netstat_selection_required_msg': "Please select a connection from the list first.",
        'netstat_process_info_error': "Could not retrieve process information for the selected connection.",
        'netstat_terminate_confirm_title': "Confirm Termination",
        'netstat_terminate_confirm_prompt': "Are you sure you want to terminate the process '{process_name}' (PID: {pid})?",
        'netstat_terminate_success_msg': "Process '{process_name}' (PID: {pid}) has been terminated.",
        'netstat_terminate_failed_title': "Termination Failed",
        'traceroute_input_required': "Input Required",
        'traceroute_input_required_msg': "Please enter a target host or IP address.",
        'wifi_export_success_title': "Export Successful",
        'wifi_export_success_msg': "Saved Wi-Fi profiles exported to {filepath}",
        'publish_ready': "Ready to publish release.",
        'publish_checking_auth': "Checking GitHub authentication...",
        'publish_auth_failed': "GitHub authentication failed. Please run 'gh auth login'.",
        'publish_auth_failed_title': "GitHub Authentication Failed",
        'publish_success': "Successfully created release {tag} on GitHub.",
        'wifi_password_copied': "Password for '{profile_name}' copied to clipboard.",
        'wifi_select_to_connect': "Please select an item from the list to connect.",
        'wifi_select_to_delete': "Please select a profile to delete.",
    },
    'fi': {
        LANG_CODE_KEY: 'fi',
        # Startup Errors
        'unsupported_os_title': "Ei-tuettu käyttöjärjestelmä",
        'unsupported_os_message': "Tämä sovellus on suunniteltu vain Windows-käyttöjärjestelmälle.",
        'admin_required_title': "Järjestelmänvalvojan oikeudet vaaditaan",
        'admin_required_relaunch_prompt': "Tämä sovellus vaatii järjestelmänvalvojan oikeudet toimiakseen oikein.\n\nHaluatko käynnistää sen uudelleen järjestelmänvalvojana?",
        'language_change_title': "Kielen vaihto",
        'language_change_message': "Kieli päivitetään, kun käynnistät sovelluksen seuraavan kerran.",
        'language_restart_prompt_title': "Uudelleenkäynnistys vaaditaan",
        'language_restart_prompt_message': "Kieli on vaihdettu. Haluatko käynnistää sovelluksen uudelleen nyt, jotta muutokset tulevat voimaan?",
        'relaunch_failed_title': "Uudelleenkäynnistys epäonnistui",
        'relaunch_failed_message': "Sovellusta ei voitu käynnistää uudelleen järjestelmänvalvojan oikeuksilla. Tarkista lokitiedostosta lisätietoja.",

        # Generic Errors
        'ui_error_title': "Käyttöliittymän virhe",
        'ui_error_message': "Käyttöliittymäkomponenteissa tapahtui kriittinen virhe. Tarkista lokitiedosto.",
        'fatal_error_title': "Kriittinen virhe",
        'fatal_error_message': "Tapahtui odottamaton virhe ja sovelluksen on sulkeuduttava. Tarkista lokitiedostosta lisätietoja.",

        # Log file hint
        'log_file_hint': "\n\nLisätietoja löydät lokitiedostosta:\n{log_file_path}",

        # Main UI
        'app_title': "NetPilot",
        'status_initializing': "Alustetaan...",
        'status_initial_load': "Ladataan perustietoja...",
        'status_op_cancelled': "Toiminto peruutettu.",
        'status_op_cancelled_by_user': "Käyttäjä peruutti toiminnon.",
        'status_enable_attempt': "Yritetään ottaa käyttöön '{adapter_name}'...",
        'status_disable_attempt': "Yritetään poistaa käytöstä '{adapter_name}'...",
        'status_reset_attempt': "Nollataan verkkopinoa...",
        'status_failed_op': "Tilan muuttaminen sovittimelle '{adapter_name}' epäonnistui.",
        'status_not_needed': "Toimintoa ei tarvita.",
        'status_refreshing_list': "Päivitetään listaa...",
        'status_disconnect_and_disable': "Yritetään automaattista kaksivaiheista toimintoa...",
        'status_reset_success': "Verkkopino nollattu. Uudelleenkäynnistys vaaditaan.",
        'status_dns_flush_success': "DNS-välimuisti tyhjennetty.",
        'status_ip_renew_success': "IP-osoitteet uusittu.",
        'status_wifi_disconnected': "Wi-Fi-yhteys katkaistu.",
        'status_ready_select_adapter': "Valmis. Valitse sovitin listalta.",
        'status_fetching': "Haetaan...",

        # Menu
        'menu_tools': "Työkalut",
        'menu_reset_stack': "Nollaa verkkopino...",
        'menu_release_renew': "Vapauta ja uusi IP",
        'menu_flush_dns': "Tyhjennä DNS-välimuisti",
        'menu_connections': "Aktiiviset yhteydet...",
        'menu_traceroute': "Jäljitä reitti...",
        'menu_wifi': "Wi-Fi-verkot...",
        'menu_language': "Kieli",
        'menu_lang_en': "English",
        'menu_lang_fi': "Suomi",
        'menu_publish': "Julkaise versio...",
        'menu_help': "Ohje",
        'menu_open_log': "Avaa lokitiedosto",
        'menu_about': "Tietoja...",

        # Dialogs
        'about_title': "Tietoja NetPilotista",
        'about_message_content': "{app_name}\n\nVersio: {version}\nTekijä: {author}",
        'publish_title': "Julkaise uusi versio",
        'publish_repo': "Repository (omistaja/repo):",
        'publish_version': "Versio / Tagi:",
        'publish_version_tooltip': "Pitää alkaa 'v'-kirjaimella, esim. v1.2.3",
        'publish_release_title': "Julkaisun otsikko:",
        'publish_notes': "Julkaisutiedot:",
        'publish_button': "Julkaise versio",
        'publish_cancel': "Peruuta",
        'publish_missing_info': "Puutteelliset tiedot",
        'publish_missing_info_msg': "Repository, versio ja otsikko ovat pakollisia kenttiä.",

        # UI Frames
        'available_adapters_title': "Saatavilla olevat sovittimet",
        'no_adapters_found': "Sovittimia ei löytynyt.",
        'adapter_details_title': "Sovittimen tiedot",
        'button_connect': "Ota käyttöön",
        'button_disconnect': "Poista käytöstä",
        'context_menu_copy': "Kopioi",
        'status_copied_to_clipboard': "Kopioitu '{text}' leikepöydälle.",
        'wifi_status_title': "Nykyinen Wi-Fi-yhteys",
        'diagnostics_title': "Verkkodiagnostiikka",

        # Adapter Details Labels
        'details_description': "Kuvaus",
        'details_mac': "MAC-osoite",
        'details_ipv4': "IPv4-osoite",
        'details_ipv6': "IPv6-osoite",
        'details_link_speed': "Linkin nopeus",
        'details_download_speed': "Latausnopeus",
        'details_upload_speed': "Lähetysnopeus",
        'details_driver_version': "Ajurin versio",
        'details_driver_date': "Ajurin päiväys",
        'diag_public_ip': "Julkinen IP",
        'diag_gateway': "Yhdyskäytävä",
        'diag_gateway_latency': "Yhdyskäytävän viive",
        'diag_external_latency': "Ulkoinen viive",
        'diag_dns_servers': "DNS-palvelimet",
        'diag_ping_target': "Ping-kohde",
        'wifi_status_ssid': "SSID",
        'wifi_status_signal': "Signaali",
        'wifi_status_ip': "IP-osoite",
        'wifi_status_not_connected': "Ei yhdistetty",
        'wifi_button_disconnect': "Katkaise yhteys",
        'netstat_title': "Aktiiviset yhteydet (netstat)",
        'netstat_filter_by': "Suodata protokollan mukaan:",
        'netstat_filter_all': "Kaikki",
        'netstat_filter_tcp': "TCP",
        'netstat_filter_udp': "UDP",
        'netstat_col_proto': "Protok.",
        'netstat_col_local': "Paikallinen osoite",
        'netstat_col_foreign': "Etäosoite",
        'netstat_col_state': "Tila",
        'netstat_col_process': "Prosessin nimi",
        'netstat_button_refresh': "Päivitä",
        'netstat_button_terminate': "Lopeta prosessi",
        'traceroute_title': "Jäljitä reitti",
        'traceroute_target': "Kohde:",
        'traceroute_button_start': "Aloita",
        'traceroute_starting': "Jäljetetään reittiä kohteeseen {target}...",
        'wifi_window_title': "Wi-Fi-hallinta",
        'wifi_tab_available': "Saatavilla olevat verkot",
        'wifi_tab_saved': "Tallennetut profiilit",
        'wifi_col_ssid': "SSID",
        'wifi_col_signal': "Signaali",
        'wifi_col_auth': "Todennus",
        'wifi_col_encrypt': "Salaus",
        'wifi_col_profile': "Profiilin nimi",
        'wifi_col_password': "Salasana",
        'wifi_button_refresh': "Päivitä",
        'wifi_button_connect': "Yhdistä",
        'wifi_button_delete': "Poista profiili",
        'wifi_button_copy_pass': "Kopioi salasana",
        'wifi_button_export': "Vie tiedostoon...",
        'wifi_password_prompt_title': "Salasana vaaditaan",
        'wifi_password_prompt_msg': "Anna verkon {ssid} salasana:",
        'wifi_connect_status': "Yhdistetään verkkoon {ssid}...",
        'wifi_delete_confirm_title': "Vahvista poisto",
        'wifi_delete_confirm_msg': "Haluatko varmasti poistaa profiilin '{profile_name}'?",
        'wifi_no_networks_found': "Wi-Fi-verkkoja ei löytynyt.",

        # Queue Handler Messages
        'toggle_error_title': "Suoritusvirhe",
        'toggle_error_message': "Toiminto epäonnistui:\n\n{error}",
        'toggle_info_title': "Tiedoksi",
        'toggle_wifi_connected_title': "Toiminto vaaditaan",
        'toggle_confirm_enable_title': "Vahvista käyttöönotto",
        'toggle_confirm_enable_prompt': "Haluatko varmasti ottaa käyttöön sovittimen '{adapter_name}'?",
        'toggle_confirm_disable_title': "Vahvista käytöstä poisto",
        'toggle_confirm_disable_prompt': "Haluatko varmasti poistaa käytöstä sovittimen '{adapter_name}'?",
        'toggle_wifi_connected_prompt': "Sovittimen '{adapter}' poistaminen käytöstä epäonnistui, koska se on yhdistetty verkkoon.\n\nHaluatko katkaista Wi-Fi-yhteyden automaattisesti ja poistaa sitten sovittimen käytöstä?",
        'reset_stack_success_title': "Onnistui",
        'reset_stack_success_message': "Verkkopino on nollattu.\nKäynnistä tietokone uudelleen, jotta muutokset tulevat voimaan.",
        'flush_dns_success_title': "Onnistui",
        'flush_dns_success_message': "DNS-välimuisti on tyhjennetty onnistuneesti.",
        'release_renew_success_title': "Onnistui",
        'release_renew_success_message': "IP-osoitteet on vapautettu ja uusittu onnistuneesti. Päivitetään sovitinlistaa.",
        'disconnect_wifi_success_title': "Onnistui",
        'disconnect_wifi_success_message': "Wi-Fi-yhteys on katkaistu onnistuneesti.",
        'netstat_selection_required': "Valinta vaaditaan",
        'netstat_selection_required_msg': "Valitse ensin yhteys listalta.",
        'netstat_process_info_error': "Valitun yhteyden prosessitietoja ei voitu hakea.",
        'netstat_terminate_confirm_title': "Vahvista lopetus",
        'netstat_terminate_confirm_prompt': "Haluatko varmasti lopettaa prosessin '{process_name}' (PID: {pid})?",
        'netstat_terminate_success_msg': "Prosessi '{process_name}' (PID: {pid}) on lopetettu.",
        'netstat_terminate_failed_title': "Lopetus epäonnistui",
        'traceroute_input_required': "Syöte vaaditaan",
        'traceroute_input_required_msg': "Anna kohde (isäntänimi tai IP-osoite).",
        'wifi_export_success_title': "Vienti onnistui",
        'wifi_export_success_msg': "Tallennetut Wi-Fi-profiilit viety tiedostoon {filepath}",
        'publish_ready': "Valmis julkaisemaan version.",
        'publish_checking_auth': "Tarkistetaan GitHub-autentikointia...",
        'publish_auth_failed': "GitHub-autentikointi epäonnistui. Suorita 'gh auth login'.",
        'publish_auth_failed_title': "GitHub-autentikointi epäonnistui",
        'publish_success': "Versio {tag} luotu onnistuneesti GitHubiin.",
        'wifi_password_copied': "Verkon '{profile_name}' salasana kopioitu leikepöydälle.",
        'wifi_select_to_connect': "Valitse kohde listalta yhdistääksesi.",
        'wifi_select_to_delete': "Valitse profiili listalta poistaaksesi.",
    }
}

CONFIG_FILE = Path(__file__).parent / 'config.ini'

def _get_system_language() -> str:
    """Detects the OS language as a fallback."""
    try:
        # E.g., 'en_US', 'fi_FI'
        lang_code, _ = locale.getdefaultlocale()
        if lang_code:
            primary_lang = lang_code.split('_')[0]
            if primary_lang in SUPPORTED_LANGUAGES:
                return primary_lang
    except Exception:
        pass
    return DEFAULT_LANGUAGE

def set_language(lang_code: str):
    """Saves the selected language to the config file."""
    if lang_code not in SUPPORTED_LANGUAGES:
        return
    config = configparser.ConfigParser()
    # Lue olemassa oleva tiedosto, jotta muut asetukset säilyvät
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE, encoding='utf-8')
    if 'Settings' not in config:
        config['Settings'] = {}
    config['Settings']['language'] = lang_code
    with CONFIG_FILE.open('w', encoding='utf-8') as configfile:
        config.write(configfile)

def initialize_language():
    """
    Initializes the language by reading from the config file,
    falling back to system language, and finally to the default.
    Updates the global CURRENT_LANGUAGE variable.
    """
    global CURRENT_LANGUAGE
    config = configparser.ConfigParser()
    if CONFIG_FILE.exists():
        config.read(CONFIG_FILE, encoding='utf-8')
        saved_lang = config.get('Settings', 'language', fallback=None)
        if saved_lang in SUPPORTED_LANGUAGES:
            CURRENT_LANGUAGE = saved_lang
            return
    CURRENT_LANGUAGE = _get_system_language()

def get_string(key: str, **kwargs) -> str:
    """
    Retrieves a localized string by its key and formats it with provided arguments.
    If a default is provided, it's used when the key is not found.
    """
    return STRINGS[CURRENT_LANGUAGE].get(key, kwargs.get('default', f"<{key}>")).format(**kwargs)