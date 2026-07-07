"""
reading 子包 —— 朗读会话全流程管理。

模块说明：
  - session.py      : 朗读会话的启动/停止、网页打开
  - data_io.py      : 朗读数据的读写（JSON 文件 + CSV dB 日志）
  - wav_merger.py   : 多段 WAV 块的合并工具
  - data_thread.py  : 后台数据线程（IPC / HTTP 轮询）
  - ui_thread.py    : UI 更新线程（解耦 Tkinter 更新）
  - tts_trigger.py  : 朗读中 TTS 条件触发检查
"""

from .session import bind_reading_api, reading_data_get_and_check, start_reading
from .data_io import load_today_reading_status
from ..time_utils import format_duration  # re-export for convenience


__all__ = ["bind_reading_api", "reading_data_get_and_check", "start_reading", "load_today_reading_status", "format_duration"]
