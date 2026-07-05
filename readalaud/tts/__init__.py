"""
tts 子包 —— 本地 (pyttsx3) 与网络 (edge-tts) 语音合成。

Heavy TTS backends are imported lazily so the main window can start quickly.
"""


def speak(*args, **kwargs):
    from .local_tts import speak as _speak

    return _speak(*args, **kwargs)


def play_mp3_win32(*args, **kwargs):
    from .web_tts import play_mp3_win32 as _play_mp3_win32

    if _play_mp3_win32 is None:
        raise RuntimeError("edge_playback is not available")
    return _play_mp3_win32(*args, **kwargs)


def test_tts(*args, **kwargs):
    from .web_tts import test_tts as _test_tts

    return _test_tts(*args, **kwargs)


def bind_tts(instance):
    from .voice_list import bind_tts as _bind_tts

    return _bind_tts(instance)


def get_web_voices(*args, **kwargs):
    from .voice_list import get_web_voices as _get_web_voices

    return _get_web_voices(*args, **kwargs)


__all__ = ["speak", "play_mp3_win32", "test_tts", "bind_tts", "get_web_voices"]
