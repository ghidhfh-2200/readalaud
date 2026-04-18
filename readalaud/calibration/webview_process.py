"""
webview_process.py —— 兼容层。

说明：
- 历史上该模块通过 pywebview + Web 页面完成校准。
- 现已切换为本地 Tk 校准窗口（见 local_window.py）。
"""

from .local_window import bind_calibration_api, start_calibration

__all__ = ["bind_calibration_api", "start_calibration"]
