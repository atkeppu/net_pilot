import unittest
from unittest.mock import Mock, MagicMock, patch, call

import gui
from gui.action_handler import ActionHandler
from gui.queue_handler import QueueHandler
from gui.adapter_details_frame import AdapterDetailsFrame
from localization import get_string
from exceptions import NetworkManagerError

class TestActionHandler(unittest.TestCase):
    """Tests for the ActionHandler class."""

    def setUp(self):
        self.mock_context = Mock()
        self.mock_context.root = Mock()
        self.mock_context.task_queue = Mock()
        self.get_selected_adapter_name_func = Mock(return_value="Wi-Fi")
        self.handler = ActionHandler(self.mock_context, self.get_selected_adapter_name_func)

    @patch('gui.action_handler.threading.Thread')
    def test_run_background_task_starts_thread(self, mock_thread):
        """Test that run_background_task creates and starts a thread."""
        mock_task = Mock(__name__='mock_task')
        self.handler.run_background_task(mock_task, "arg1")

        mock_thread.assert_called_once()
        self.assertTrue(mock_thread.call_args[1]['daemon'])
        mock_thread.return_value.start.assert_called_once()

    @patch('gui.action_handler.threading.Thread')
    def test_run_background_task_network_manager_error(self, mock_thread):
        """Test that a NetworkManagerError is put into the queue."""
        task_func = Mock(side_effect=NetworkManagerError("Known error"), __name__='task_func')
        self.handler.run_background_task(task_func)

        # Get the worker function passed to the Thread target
        worker_func = mock_thread.call_args.kwargs['target']
        worker_func()  # Directly call the worker to simulate thread execution

        self.mock_context.task_queue.put.assert_called_with({'type': 'generic_error', 'description': "running task task_func", 'error': unittest.mock.ANY})

    @patch('gui.action_handler.threading.Thread')
    def test_run_background_task_unhandled_error(self, mock_thread):
        """Test that an unhandled exception is put into the queue."""
        task_func = Mock(side_effect=ValueError("Unhandled"), __name__='task_func')
        self.handler.run_background_task(task_func)

        # Check that the thread was started with a worker that calls the task
        # and that the unhandled_error is put to the queue.
        # This is an indirect way to test the worker's behavior.
        worker_func = mock_thread.call_args.kwargs['target']
        worker_func()  # Execute the worker

        self.mock_context.task_queue.put.assert_called_with({'type': 'unhandled_error', 'error': unittest.mock.ANY})

    @patch('gui.action_handler.threading.Thread')
    def test_run_background_task_on_complete_callback(self, mock_thread):
        """Test that the on_complete callback is called via the queue."""
        mock_task = Mock(__name__='mock_task', return_value="task_result")
        mock_on_complete = Mock(__name__='mock_on_complete')

        self.handler.run_background_task(mock_task, on_complete=mock_on_complete)

        # Simulate the worker running
        worker_func = mock_thread.call_args.kwargs['target']
        worker_func()

        # Assert that put was called with a dictionary containing a 'func' key
        self.mock_context.task_queue.put.assert_called_once()
        call_args = self.mock_context.task_queue.put.call_args[0][0]
        self.assertEqual(call_args['type'], 'ui_update')
        # Execute the lambda function that was passed to the queue
        call_args['func']()
        # Now, assert that our original on_complete mock was called with the task's result
        mock_on_complete.assert_called_once_with("task_result")

    @patch('gui.action_handler.messagebox.showwarning')
    @patch('gui.action_handler.messagebox.askyesno', return_value=True)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_toggle_selected_adapter_no_selection(self, mock_run_task, mock_askyesno, mock_showwarning):
        """Test that toggle does nothing if no adapter is selected."""
        self.get_selected_adapter_name_func.return_value = None
        self.handler.toggle_selected_adapter('enable')
        mock_run_task.assert_not_called()
        mock_showwarning.assert_called_once()

    @patch('gui.action_handler.messagebox.askyesno', return_value=False)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_toggle_selected_adapter_user_cancels(self, mock_run_task, mock_askyesno):
        """Test that toggle is cancelled if user selects 'No'."""
        self.handler.toggle_selected_adapter('enable')
        mock_run_task.assert_not_called()
        self.mock_context.root.status_var.set.assert_called_with(get_string('status_op_cancelled'))

    @patch('gui.action_handler.messagebox.askyesno', return_value=True)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_toggle_selected_adapter_user_confirms(self, mock_run_task, mock_askyesno):
        """Test that toggle starts a background task if user confirms."""
        self.handler.toggle_selected_adapter('enable')
        mock_run_task.assert_called_once_with(
            self.handler._execute_toggle_in_thread, "Wi-Fi", 'enable'
        )
        self.mock_context.root.status_var.set.assert_called()

    @patch('gui.action_handler.messagebox.askyesno', return_value=True)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_confirm_reset_network_stack(self, mock_run_task, mock_askyesno):
        """Test that reset network stack action starts a background task."""
        self.handler.confirm_reset_network_stack()
        mock_askyesno.assert_called_once()
        mock_run_task.assert_called_once_with(self.handler._execute_reset_in_thread)
        self.mock_context.root.status_var.set.assert_called()

    @patch('gui.action_handler.messagebox.askyesno', return_value=False)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_confirm_reset_network_stack_user_cancels(self, mock_run_task, mock_askyesno):
        """Test that reset is cancelled if user selects 'No'."""
        self.handler.confirm_reset_network_stack()
        mock_askyesno.assert_called_once()
        mock_run_task.assert_not_called()
        self.mock_context.root.status_var.set.assert_called_with(get_string('status_op_cancelled'))

    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_flush_dns_cache(self, mock_run_task):
        """Test that flush DNS action starts a background task."""
        self.handler.flush_dns_cache()
        mock_run_task.assert_called_once_with(self.handler._execute_flush_dns_in_thread)

    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_release_renew_ip(self, mock_run_task):
        """Test that release and renew action starts a background task."""
        self.handler.release_renew_ip()
        mock_run_task.assert_called_once_with(self.handler._execute_release_renew_in_thread)

    @patch('gui.action_handler.app_logic.reset_network_stack')
    def test_execute_reset_in_thread(self, mock_reset):
        """Test the reset network stack worker method."""
        self.handler._execute_reset_in_thread()
        mock_reset.assert_called_once()
        self.mock_context.task_queue.put.assert_called_once_with({'type': 'reset_stack_success'})

    def test_execute_flush_dns_in_thread(self):
        """Test the flush DNS worker method."""
        self.handler._execute_flush_dns_in_thread()
        self.mock_context.task_queue.put.assert_called_once_with({'type': 'flush_dns_success'})

    def test_execute_release_renew_in_thread(self):
        """Test the release/renew IP worker method."""
        self.handler._execute_release_renew_in_thread()
        self.mock_context.task_queue.put.assert_called_once_with({'type': 'release_renew_success'})

    def test_execute_disconnect_wifi_in_thread(self):
        """Test the disconnect wifi worker method."""
        self.handler._execute_disconnect_wifi_in_thread()
        self.mock_context.task_queue.put.assert_called_once_with({'type': 'disconnect_wifi_success'})

    @patch('gui.action_handler.messagebox.askyesno', return_value=True)
    @patch('gui.action_handler.ActionHandler.run_background_task')
    def test_disconnect_current_wifi(self, mock_run_task, mock_askyesno):
        """Test that disconnect Wi-Fi action starts a background task."""
        self.handler.disconnect_current_wifi()
        mock_askyesno.assert_called_once()
        mock_run_task.assert_called_once_with(self.handler._execute_disconnect_wifi_in_thread)

    @patch('gui.action_handler.app_logic.disconnect_wifi_and_disable_adapter')
    def test_execute_disconnect_and_disable_in_thread(self, mock_disconnect_and_disable):
        """Test the disconnect and disable worker method."""
        mock_disconnect_and_disable.return_value = iter(["Step 1", "Step 2"])
        self.handler._execute_disconnect_and_disable_in_thread("Wi-Fi")
        
        expected_calls = [call({'type': 'status_update', 'text': "Step 1"}), call({'type': 'status_update', 'text': "Step 2"})]
        self.mock_context.task_queue.put.assert_has_calls(expected_calls)

    @patch('gui.action_handler.NetstatWindow')
    def test_show_netstat_window(self, mock_netstat_window):
        """Test that show_netstat_window creates a NetstatWindow instance."""
        self.handler.show_netstat_window()
        mock_netstat_window.assert_called_once_with(self.mock_context)

    @patch('gui.action_handler.TracerouteWindow')
    def test_show_traceroute_window(self, mock_traceroute_window):
        """Test that show_traceroute_window creates a TracerouteWindow instance."""
        self.handler.show_traceroute_window()
        mock_traceroute_window.assert_called_once_with(self.mock_context)

    @patch('gui.action_handler.app_logic.check_github_cli_auth', return_value=(True, ""))
    @patch('gui.action_handler.PublishDialog') 
    def test_show_publish_dialog(self, mock_publish_dialog, mock_check_auth):
        """Test that show_publish_dialog creates a PublishWindow instance."""
        self.handler.show_publish_dialog()
        mock_publish_dialog.assert_called_once_with(self.mock_context)

    @patch('gui.action_handler.app_logic.check_github_cli_auth', return_value=(False, "Auth error"))
    @patch('gui.action_handler.messagebox.showerror') # messagebox is imported directly in action_handler
    @patch('gui.action_handler.PublishDialog')
    def test_show_publish_dialog_auth_fails(self, mock_publish_dialog, mock_showerror, mock_check_auth_app_logic):
        """Test that an error is shown if GitHub auth fails."""
        self.handler.show_publish_dialog()
        mock_check_auth_app_logic.assert_called_once()
        mock_showerror.assert_called_once()
        mock_publish_dialog.assert_not_called()

    @patch('gui.action_handler.ActionHandler.run_background_task')
    @patch('gui.action_handler.app_logic.get_dist_path')
    @patch('tkinter.messagebox.showerror') # Patch messagebox.showerror as it might be called if assets are not found
    def test_publish_release(self, mock_showerror, mock_get_dist_path, mock_run_task):
        """Test that publish_release calls the background task with correct arguments."""
        repo = "owner/repo"
        tag = "v1.0"
        title = "Title"
        notes = "Notes"

        mock_dist_path_obj = MagicMock()
        mock_get_dist_path.return_value = mock_dist_path_obj
        # Mock the __truediv__ method to handle the '/' operator
        mock_dist_path_obj.__truediv__.return_value = Mock(is_file=Mock(return_value=False))

        # Simulate finding an installer file in the 'dist' directory
        mock_dist_path_obj.glob.return_value = iter([Mock(is_file=Mock(return_value=True), __str__=Mock(return_value="dist/NetPilot-setup.exe"))])

        self.handler.publish_release(repo, tag, title, notes)
        
        expected_assets = ["dist/NetPilot-setup.exe"]
        mock_run_task.assert_called_once_with(self.handler._execute_publish_in_thread, repo, tag, title, notes, expected_assets, on_complete=None, on_error=None)

    @patch('gui.action_handler.ActionHandler.run_background_task')
    @patch('gui.action_handler.app_logic.get_dist_path')
    @patch('tkinter.messagebox.showerror')
    def test_publish_release_no_assets_found(self, mock_showerror, mock_get_dist_path, mock_run_task):
        """Test that an error is shown if no release assets are found."""
        repo = "owner/repo"
        tag = "v1.0"
        title = "Title"
        notes = "Notes"

        mock_dist_path_obj = MagicMock()
        mock_get_dist_path.return_value = mock_dist_path_obj
        mock_dist_path_obj.glob.return_value = iter([]) # No installer
        mock_dist_path_obj.__truediv__.return_value = Mock(is_file=Mock(return_value=False)) # No exe

        self.handler.publish_release(repo, tag, title, notes)
        mock_showerror.assert_called_once()
        mock_run_task.assert_not_called()
    
    @patch('app_logic.create_github_release', side_effect=NetworkManagerError("API Error"))
    def test_execute_publish_in_thread_failure(self, mock_create_release):
        """Test that an error during publishing is caught and put to the queue."""
        with self.assertRaises(NetworkManagerError):
            # The error should be re-raised inside the worker and caught by run_background_task
            self.handler._execute_publish_in_thread("owner/repo", "v1.0", "Title", "Notes")
        
        mock_create_release.assert_called_once()

class TestQueueHandler(unittest.TestCase):
    """Tests for the QueueHandler class."""

    def setUp(self):
        self.mock_context = Mock()
        self.mock_context.root = Mock()
        self.mock_context.action_handler = Mock()
        self.mock_context.open_windows = {}
        self.mock_ui_frames = {
            'diagnostics': Mock(),
            'adapter_list': Mock(),
            'adapter_details': Mock(),
            'wifi_status': Mock()
        }
        self.mock_context.main_controller.refresh_adapter_list = Mock()
        self.handler = QueueHandler(self.mock_context, self.mock_ui_frames)

    def test_process_message_delegates_to_wifi_handler(self):
        """Test that Wi-Fi related messages are handled by the wifi_handler."""
        self.handler.wifi_handler.process_message = Mock(return_value=True)
        self.handler.process_message({'type': 'wifi_list_success'})
        self.handler.wifi_handler.process_message.assert_called_once()

    def test_process_message_unknown_type(self):
        """Test that an unknown message type is logged as a warning."""
        with self.assertLogs('gui.queue_handler', level='WARNING') as cm:
            self.handler.process_message({'type': 'unknown_message'})
            self.assertIn("No handler found for queue message type: unknown_message", cm.output[0])

    def test_handle_toggle_error_already_in_state(self):
        """Test info messagebox for 'already in state' errors."""
        message = {
            'type': 'toggle_error',
            'adapter_name': 'Wi-Fi',
            'action': 'enable',
            'error': NetworkManagerError("Adapter is already enabled.")
        }
        with patch('gui.queue_handler.messagebox.showinfo') as mock_showinfo:
            self.handler.process_message(message)
            mock_showinfo.assert_called_once()
            self.mock_context.root.status_var.set.assert_called()

    @patch('gui.queue_handler.messagebox.askyesno', return_value=True)
    def test_handle_toggle_error_wifi_connected(self, mock_askyesno):
        """Test the specific flow for the WIFI_CONNECTED_DISABLE_FAILED error."""
        message = {
            'type': 'toggle_error',
            'adapter_name': 'Wi-Fi',
            'action': 'disable',
            'error': NetworkManagerError("Cannot disable", code='WIFI_CONNECTED_DISABLE_FAILED')
        }
        self.handler.process_message(message)
        self.mock_context.action_handler.execute_disconnect_and_disable.assert_called_once_with('Wi-Fi')

    @patch('gui.queue_handler.messagebox.askyesno', return_value=False)
    def test_handle_toggle_error_wifi_connected_user_declines(self, mock_askyesno):
        """Test that nothing happens if user declines the auto-disconnect prompt."""
        message = {
            'type': 'toggle_error',
            'adapter_name': 'Wi-Fi',
            'action': 'disable',
            'error': NetworkManagerError("Cannot disable", code='WIFI_CONNECTED_DISABLE_FAILED')
        }
        self.handler.process_message(message)
        self.mock_context.action_handler.execute_disconnect_and_disable.assert_not_called()
        self.mock_context.root.status_var.set.assert_called()

    @patch('gui.queue_handler.messagebox.showerror')
    def test_handle_toggle_error_generic(self, mock_showerror):
        """Test the generic error path for toggle failures."""
        message = {
            'type': 'toggle_error',
            'adapter_name': 'Wi-Fi',
            'action': 'disable',
            'error': NetworkManagerError("A generic failure.")
        }
        self.handler.process_message(message)
        mock_showerror.assert_called_once()
        self.mock_context.root.status_var.set.assert_called()
        self.mock_context.main_controller.refresh_adapter_list.assert_called_once()

    def test_handle_generic_error_location_permission(self):
        """Test specific handling for location permission error."""
        message = {
            'type': 'generic_error',
            'description': 'scanning wifi',
            'error': NetworkManagerError("Enable location", code="LOCATION_PERMISSION_DENIED")
        }
        with patch('gui.queue_handler.messagebox.askyesno', return_value=True) as mock_ask, \
             patch('gui.queue_handler.os.startfile') as mock_startfile:
            self.handler.process_message(message)
            mock_ask.assert_called_once()
            mock_startfile.assert_called_once_with("ms-settings:privacy-location")

    def test_handle_generic_error_no_code(self):
        """Test the generic error handler for an error without a special code."""
        message = {
            'type': 'generic_error',
            'description': 'doing something',
            'error': NetworkManagerError("A plain error.")
        }
        with patch('gui.queue_handler.messagebox.showerror') as mock_showerror:
            self.handler.process_message(message)
            mock_showerror.assert_called_once()

    def test_handle_ui_update(self):
        """Test that a callable function in a 'ui_update' message is executed."""
        mock_func = Mock()
        message = {'type': 'ui_update', 'func': mock_func}
        self.handler.process_message(message)
        mock_func.assert_called_once()

    def test_handle_speed_update_with_selection(self):
        """Test speed update when an adapter is selected."""
        self.mock_context.main_controller.get_speed_for_selected_adapter.return_value = {'download': 100, 'upload': 50}
        message = {'type': 'speed_update', 'data': {'Wi-Fi': {'download': 100, 'upload': 50}}}
        self.handler.process_message(message)
        self.mock_ui_frames['adapter_details'].update_speeds.assert_called_once_with(100, 50)

    def test_handle_speed_update_no_selection(self):
        """Test speed update does nothing if no adapter is selected."""
        self.mock_context.main_controller.get_speed_for_selected_adapter.return_value = None
        message = {'type': 'speed_update', 'data': {'Wi-Fi': {'download': 100}}}
        self.handler.process_message(message)
        # It should reset speeds to 0
        self.mock_ui_frames['adapter_details'].update_speeds.assert_called_once_with(0, 0)

    @patch('gui.queue_handler.messagebox.showinfo')
    def test_handle_reset_stack_success(self, mock_showinfo):
        """Test the handler for a successful network stack reset."""
        self.handler.process_message({'type': 'reset_stack_success'})
        mock_showinfo.assert_called_once()
        self.assertIn("reboot your computer", mock_showinfo.call_args[0][1])

    @patch('gui.queue_handler.messagebox.showinfo')
    def test_handle_release_renew_success(self, mock_showinfo):
        """Test the handler for a successful IP renew."""
        self.handler.process_message({'type': 'release_renew_success'})
        mock_showinfo.assert_called_once()
        self.mock_context.main_controller.refresh_adapter_list.assert_called_once()

    def test_handle_diagnostics_update(self):
        """Test that diagnostics data is passed to the correct UI frame."""
        message = {'type': 'diagnostics_update', 'data': {'Public IP': '1.1.1.1'}}
        self.handler.process_message(message)
        self.mock_ui_frames['diagnostics'].update_diagnostics.assert_called_once_with(message['data'])

    def test_handle_disconnect_wifi_error(self):
        """Test that a disconnect error is handled and the button is re-enabled."""
        message = {'type': 'disconnect_wifi_error', 'error': NetworkManagerError("test error")}
        with patch('gui.queue_handler.messagebox.showerror') as mock_showerror:
            self.handler.process_message(message)
            mock_showerror.assert_called_once()

    def test_handle_toggle_success(self,):
        """Test that a toggle success message triggers a UI refresh."""
        message = {'type': 'toggle_success', 'adapter_name': 'Wi-Fi', 'action': 'enabled'}
        with patch.object(self.mock_context.root, 'after') as mock_after:
            self.handler.process_message(message)
            mock_after.assert_called_once_with(500, self.mock_context.main_controller.refresh_adapter_list)

    @patch('gui.queue_handler.messagebox.showinfo')
    def test_handle_disconnect_wifi_success_no_window_open(self, mock_showinfo):
        """Test disconnect success handler when the wifi window is not open."""
        # Arrange: Ensure no window is registered
        self.mock_context.open_windows = {}
        message = {'type': 'disconnect_wifi_success'}
        # Act
        self.handler.process_message(message)
        # Assert
        mock_showinfo.assert_called_once_with("Success", "Successfully disconnected from the Wi-Fi network.", parent=self.mock_context.root)

    def test_wifi_handler_does_nothing_if_window_not_open(self):
        """Test that Wi-Fi message handlers do nothing if the window is not open."""
        # Arrange: Ensure the wifi window is not in open_windows
        self.handler.wifi_handler.context.open_windows = {}
        
        # Act: Process messages that would normally update the window
        self.handler.process_message({'type': 'wifi_list_success', 'data': [], 'current_ssid': ''})
        self.handler.process_message({'type': 'wifi_connect_success', 'ssid': 'TestNet'})
        self.handler.process_message({'type': 'wifi_saved_profiles_success', 'data': []})
        self.handler.process_message({'type': 'wifi_delete_profile_success', 'profile_name': 'TestProfile'})
        # No assertion is needed; the test passes if no exceptions are raised.

if __name__ == '__main__':
    unittest.main()