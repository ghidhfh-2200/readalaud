"""
settings 子包 —— 用户设置读写与主题切换。

模块说明：
  - settings_io.py  : 设置文件的读写（settings.json / acounts.json）
  - tts_settings.py : TTS 相关设置的保存与缓存清理
"""

from .settings_io import bind_settings, _load_settings

__all__ = ["bind_settings", "_load_settings"]
__all__ = ["bind_settings"]
