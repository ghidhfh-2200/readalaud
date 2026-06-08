"""
settings 子包 —— 用户设置缓存、异步保存与主题切换。

模块说明：
  - settings_io.py  : 全局设置缓存 + 退出异步保存（settings.json / acounts.json）
  - tts_settings.py : TTS 配置缓存 + 异步落盘与缓存清理
"""

from .settings_io import (
    bind_settings,
    get_settings_cache,
    get_setting,
    update_setting,
    init_settings_cache,
    save_settings_now,
    save_on_exit,
    _load_settings,
    load_settings_data,
)
from .tts_settings import (
    get_tts_cache,
    update_tts_cache,
    init_tts_cache,
    save_tts_settings,
    save_tts_config_to_disk,
)

__all__ = [
    "bind_settings",
    "get_settings_cache",
    "get_setting",
    "update_setting",
    "init_settings_cache",
    "save_settings_now",
    "save_on_exit",
    "_load_settings",
    "load_settings_data",
    "get_tts_cache",
    "update_tts_cache",
    "init_tts_cache",
    "save_tts_settings",
    "save_tts_config_to_disk",
]
