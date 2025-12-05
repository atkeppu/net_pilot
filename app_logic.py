"""
Facade Module for Application Logic.

This module collects and exposes all the necessary business logic functions
from the `logic` subpackage. This provides a single, clean entry point for the
GUI layer to import from, decoupling it from the internal structure of the
logic package.
"""

# From logic.system
from logic.system import (
    flush_dns_cache,
    is_admin,
    release_renew_ip,
    reset_network_stack,
    terminate_process_by_pid,
)

# From logic.adapters
from logic.adapters import (
    disconnect_wifi_and_disable_adapter,
    get_adapter_details,
    set_network_adapter_status_windows,
)

# From logic.diagnostics
from logic.diagnostics import (
    get_active_connections,
    get_network_diagnostics,
    get_raw_network_stats,
    run_traceroute
)

# From logic.wifi
from logic.wifi import (
    disconnect_wifi,
    get_current_wifi_details,
    get_saved_wifi_profiles,
    list_wifi_networks,
)

# From logic.wifi_profile_manager
from logic.wifi_profile_manager import (
    connect_to_wifi_network,
    connect_with_profile_name,
    delete_wifi_profile
)

# From github_integration
from github_integration import (
    create_github_release,
    get_repo_from_git_config,
    check_github_cli_auth
)

# Explicitly define the public API of this facade module.
__all__ = [
    # system
    'flush_dns_cache',
    'is_admin',
    'release_renew_ip',
    'reset_network_stack',
    'terminate_process_by_pid',
    # adapters
    'disconnect_wifi_and_disable_adapter',
    'get_adapter_details',
    'set_network_adapter_status_windows',
    # diagnostics
    'get_active_connections',
    'get_network_diagnostics',
    'get_raw_network_stats',
    'run_traceroute',
    # wifi
    'disconnect_wifi',
    'get_current_wifi_details',
    'get_saved_wifi_profiles',
    'list_wifi_networks',
    # wifi_profile_manager
    'connect_to_wifi_network',
    'connect_with_profile_name',
    'delete_wifi_profile',
    # github_integration
    'create_github_release',
    'get_repo_from_git_config',
    'check_github_cli_auth'
]