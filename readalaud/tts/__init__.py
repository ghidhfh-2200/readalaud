"""
tts 子包 —— 本地 (pyttsx3) 与网络 (edge-tts) 语音合成。

模块说明：
  - local_tts.py : pyttsx3 本地 TTS 封装
  - web_tts.py   : edge-tts CLI + edge_playback 网络 TTS 封装
  - voice_list.py: 获取本地和网络可用音色列表
"""

from .local_tts import speak
from .web_tts import play_mp3_win32, test_tts
from .voice_list import bind_tts, get_web_voices

__all__ = ["speak", "play_mp3_win32", "test_tts", "bind_tts", "get_web_voices"]
