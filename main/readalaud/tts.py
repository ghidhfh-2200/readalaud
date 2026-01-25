import pyttsx3


def bind_tts(instance):
    # bind web-voice fetcher
    instance.get_web_voice = lambda: _get_web_voice(instance)
    # Do not override GUI-provided generate_more_vloices_window if it already exists.
    if not hasattr(instance, 'generate_more_vloices_window'):
        instance.generate_more_vloices_window = lambda source: None  # GUI may override this


async def _get_web_voice(instance=None):
    # Legacy API: web voices removed; keep shape for GUI callers.
    return []


def get_web_voices():
    # Web/model-based voices were provided by external TTS libraries (removed).
    return []


def download_model(model_name):
    return False, "已移除外部/模型 TTS 的模型下载功能（仅保留 pyttsx3）。"


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
    try:
        engine = pyttsx3.init()
        if voice_name:
            voice_id = _resolve_pyttsx3_voice(voice_name)
            if voice_id:
                engine.setProperty(name="voice", value=voice_id)

        base_rate = engine.getProperty(name="rate")
        engine.setProperty("rate", int(base_rate + 200 * float(speed)))
        engine.setProperty("volume", _clamp(abs(float(volume)), 0.0, 1.0))
        engine.say(str(text))
        engine.runAndWait()
        return True, None
    except Exception as e:
        return False, str(e)




async def test_tts(args:list, current_account):
    """
    语音生成器测试脚本
    """
    if args[4] == "web":
        return "已移除 Web/模型 TTS。请使用 local + pyttsx3。"
    elif args[4] == "local":
        ok, err = speak(text=str(args[0]), volume=float(args[1]), speed=float(args[2]), voice_name=str(args[3]))
        return "ok" if ok else (err or "unknown error")
    return "unknown source"