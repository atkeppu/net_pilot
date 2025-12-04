import threading
import subprocess
import time
import logging
import json

from app_logic import get_network_diagnostics, get_raw_network_stats, get_current_wifi_details

logger = logging.getLogger(__name__)

class PollingManager:
    """
    Manages background threads for continuously polling network status,
    diagnostics, and speeds.
    """
    def __init__(self, context):
        self.context = context
        self.controller = context.main_controller
        self.task_queue = context.task_queue
        self.last_stats = {}
        self.last_time = time.time()
        self.diagnostics_interval = 5
        self.speed_interval = 1
        self.is_running = False

    def start_all(self, diagnostics_interval: int, speed_interval: int):
        """Starts all polling threads."""
        self.diagnostics_interval = diagnostics_interval
        self.speed_interval = speed_interval
        # Start the polling loops after a short delay to ensure the main UI is ready.
        self.context.root.after(100, self.start_polling_threads)

    def start_polling_threads(self):
        """Starts the background threads for polling data."""
        if self.is_running: return
        self.is_running = True
        logger.info("Starting polling loops...")
        threading.Thread(target=self._poll_loop, daemon=True).start()
        threading.Thread(target=self._speed_poll_loop_powershell, daemon=True).start()

    def _speed_poll_loop_powershell(self):
        """
        A dedicated loop that runs a single, persistent PowerShell process
        to efficiently stream network statistics.
        """
        logger.info("Starting persistent PowerShell speed polling loop.")
        ps_script = f"""
            while ($true) {{
                $stats = Get-NetAdapterStatistics -Name * -ErrorAction SilentlyContinue | Select-Object Name, ReceivedBytes, SentBytes
                $stats | ConvertTo-Json -Compress
                Start-Sleep -Milliseconds {int(self.speed_interval * 1000)}
            }}
        """
        
        process = subprocess.Popen(['powershell', '-Command', ps_script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW)

        while self.is_running and process.poll() is None:
            line = process.stdout.readline()
            if line:
                # OPTIMIZATION: Only process speeds if an adapter is actually selected in the UI.
                if self.controller.get_selected_adapter_name() is None:
                    # Sleep briefly to prevent this loop from busy-waiting and consuming CPU
                    time.sleep(self.speed_interval)
                    continue
                calculated_speeds = self._calculate_current_speeds(line)
                if calculated_speeds:
                    self.task_queue.put({'type': 'speed_update', 'data': calculated_speeds})
        logger.warning("PowerShell speed polling loop has exited.")

    def _calculate_current_speeds(self, stats_json: str) -> dict:
        """
        Parses JSON from the PowerShell stream and calculates current network speeds
        based on the delta from the last check.
        """
        try:
            stats_list = json.loads(stats_json)
            if isinstance(stats_list, dict):
                stats_list = [stats_list]
            current_stats = {
                stat['Name']: {'received': stat.get('ReceivedBytes') or 0, 'sent': stat.get('SentBytes') or 0}
                for stat in stats_list if isinstance(stat, dict) and 'Name' in stat
            }
        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse speed stats JSON: %s", stats_json)
            return {}

        current_time = time.time()
        time_delta = current_time - self.last_time

        calculated_speeds = self._calculate_speed_delta(current_stats, self.last_stats, time_delta)

        # Update state for the next calculation
        self.last_stats = current_stats
        self.last_time = current_time

        return calculated_speeds

    def _calculate_speed_delta(self, current_stats: dict, last_stats: dict, time_delta: float) -> dict:
        if not last_stats or not current_stats or time_delta <= 0:
            return {}

        calculated_speeds = {}
        for name, stats in current_stats.items():
            if name in last_stats:
                last = last_stats[name]
                
                current_dl_bytes = stats.get('received')
                last_dl_bytes = last.get('received')
                current_ul_bytes = stats.get('sent')
                last_ul_bytes = last.get('sent')

                # Ensure we have valid numbers to work with
                if not all(isinstance(v, (int, float)) for v in [current_dl_bytes, last_dl_bytes, current_ul_bytes, last_ul_bytes]):
                    continue # Skip this adapter if data is invalid

                dl_delta = current_dl_bytes - last_dl_bytes
                ul_delta = current_ul_bytes - last_ul_bytes

                # If delta is negative, the counter likely reset. Skip this interval.
                calculated_speeds[name] = {
                    'download': (dl_delta / time_delta) if dl_delta >= 0 else 0,
                    'upload': (ul_delta / time_delta) if ul_delta >= 0 else 0
                }
        return calculated_speeds

    def _poll_loop(self):
        """
        A single, unified polling loop that handles all heavy data fetching.
        It runs the adapter refresh once, and other tasks periodically.
        """
        logger.info("Starting main poll loop.")
        initial_adapter_load_done = False

        while self.is_running:
            try:
                # --- Task 1: One-time adapter list refresh ---
                if not initial_adapter_load_done:
                    logger.info("Performing initial adapter list refresh...")
                    self.controller.refresh_adapter_list()
                    initial_adapter_load_done = True
                    logger.info("...initial adapter list refresh complete.")

                # --- Task 2: Periodic heavy diagnostics ---
                logger.info("Starting heavy poll task cycle...")

                # Run each slow task in its own sub-thread so they don't block each other.
                def fetch_diagnostics():
                    logger.debug("Fetching network diagnostics...")
                    diag_data = get_network_diagnostics(external_target=self.context.get_ping_target())
                    self.task_queue.put({'type': 'diagnostics_update', 'data': diag_data})
                    logger.debug("...diagnostics fetched.")

                def fetch_wifi_details():
                    logger.debug("Fetching Wi-Fi details...")
                    wifi_data = get_current_wifi_details()
                    self.task_queue.put({'type': 'wifi_status_update', 'data': wifi_data})
                    logger.debug("...Wi-Fi details fetched.")

                threading.Thread(target=fetch_diagnostics, daemon=True).start()
                threading.Thread(target=fetch_wifi_details, daemon=True).start()
            except Exception:
                logger.error("Main polling loop encountered an error.", exc_info=True)
            finally:
                time.sleep(self.diagnostics_interval)