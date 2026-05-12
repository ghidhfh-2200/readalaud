"""
local_tts.py —— pyttsx3 本地语音合成封装。
"""
import pyttsx3
import threading

from .playback_control import should_stop_tts


_ENGINE_LOCK = threading.Lock()
_CURRENT_ENGINE = None


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _resolve_pyttsx3_voice(voice_name):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
    except Exception:
        return None
    for v in voices:
        if getattr(v, "id", None) == voice_name or getattr(v, "name", None) == voice_name:
            return v.id
    return None


def speak(text: str, volume: float, speed: float, voice_name: str):
    """使用 pyttsx3 朗读文本，返回 (bool, error_str_or_None)。"""
    if should_stop_tts():
        return False, "tts stopped"

    engine = None
    try:
        engine = pyttsx3.init()
        with _ENGINE_LOCK:
            global _CURRENT_ENGINE
            _CURRENT_ENGINE = engine
        if voice_name:
            voice_id = _resolve_pyttsx3_voice(voice_name)
            if voice_id:
                engine.setProperty("voice", voice_id)
        base_rate = engine.getProperty("rate")
        engine.setProperty("rate", int(base_rate + 200 * float(speed)))
        engine.setProperty("volume", _clamp(abs(float(volume)), 0.0, 1.0))
        engine.say(str(text))
        engine.runAndWait()
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        with _ENGINE_LOCK:
            if _CURRENT_ENGINE is engine:
                _CURRENT_ENGINE = None


def stop_speaking():
    with _ENGINE_LOCK:
        engine = _CURRENT_ENGINE
    if engine is not None:
        try:
            engine.stop()
        except Exception:
            pass
