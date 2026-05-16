"""
voice_list.py —— 获取本地 (pyttsx3) 与网络 (edge-tts) 可用音色列表。
"""
import asyncio
import threading
import edge_tts


def bind_tts(instance):
    instance.get_web_voice = _get_web_voice
    if not hasattr(instance, "generate_more_vloices_window"):
        instance.generate_more_vloices_window = lambda source: None


async def _get_web_voice():
    try:
        return await edge_tts.list_voices()
    except Exception:
        return []


def get_web_voices():
    voices = []

    def _run():
        nonlocal voices
        try:
            voices = asyncio.run(_get_web_voice())
        except Exception:
            voices = []

    thread = threading.Thread(target=_run)
    thread.start()
    return voices
