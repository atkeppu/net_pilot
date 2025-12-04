"""
Facade Module for Application Logic.

This module collects and exposes all the necessary business logic functions
from the `logic` subpackage. This provides a single, clean entry point for the
GUI layer to import from, decoupling it from the internal structure of the
logic package.
"""

# From logic.system
from logic.system import (
    is_admin,
    reset_network_stack,
    flush_dns_cache,
    release_renew_ip,
    terminate_process_by_pid,
    create_github_release
)

# From logic.adapters
from logic.adapters import (
    get_adapter_details,
    set_network_adapter_status_windows
)

# From logic.diagnostics
from logic.diagnostics import (
    get_network_diagnostics,
    get_raw_network_stats,
    get_active_connections,
    run_traceroute
)

# From logic.wifi
from logic.wifi import (
    list_wifi_networks,
    get_current_wifi_details,
    connect_to_wifi_network,
    disconnect_wifi,
    get_saved_wifi_profiles,
    connect_with_profile_name,
    delete_wifi_profile
)