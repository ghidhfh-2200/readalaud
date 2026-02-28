"""
server 子包 —— FastAPI HTTP/WebSocket 服务器与进程管理。

模块说明：
  - socket_server.py  : FastAPI 服务器定义（HTTP 端点 + WebSocket 音频流）
  - process_manager.py: 服务器进程的查询、启动、终止工具函数
  - manager_window.py : 服务器管理 Tkinter 窗口 UI
"""

from .socket_server import bind_server_api, start_socket_server
from .process_manager import bind_server_manager_api, check_if_server_running, server_pid, end_server_process

__all__ = [
    "bind_server_api",
    "start_socket_server",
    "bind_server_manager_api",
    "check_if_server_running",
    "server_pid",
    "end_server_process",
]
