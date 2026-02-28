# backward-compat shim -- real code is in tts/
from .tts import bind_tts, speak, play_mp3_win32, test_tts, get_web_voices
__all__ = ['bind_tts','speak','play_mp3_win32','test_tts','get_web_voices']
