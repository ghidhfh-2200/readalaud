"""
server 子包 —— FastAPI HTTP/WebSocket 服务器与进程管理。

模块说明：
  - socket_server.py  : FastAPI 服务器定义（HTTP 端点 + WebSocket 音频流）
  - process_manager.py: 服务器进程的查询、启动、终止工具函数
  - manager_window.py : 服务器管理 Tkinter 窗口 UI
"""

from .process_manager import bind_server_manager_api, check_if_server_running, server_pid, end_server_process


def bind_server_api(instance):
    instance.start_server = lambda: start_socket_server()


def start_socket_server(queue=None):
    from .socket_server import start_socket_server as _start_socket_server

    return _start_socket_server(queue)


def start_manager(self):
    from .manager_window import start_manager as _start_manager

    return _start_manager(self)

__all__ = [
    "bind_server_api",
    "start_socket_server",
    "bind_server_manager_api",
    "check_if_server_running",
    "server_pid",
    "end_server_process",
    "start_manager",
]
