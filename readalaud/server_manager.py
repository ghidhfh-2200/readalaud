# backward-compat shim -- real code is in server/
from .server import bind_server_manager_api, check_if_server_running, server_pid, end_server_process
from .server.manager_window import start_manager
__all__ = ['bind_server_manager_api', 'check_if_server_running', 'server_pid', 'end_server_process', 'start_manager']
