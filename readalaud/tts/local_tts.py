"""
local_tts.py —— pyttsx3 本地语音合成封装（单引擎后台 worker）。

实现要点：
- 只初始化一次 pyttsx3 引擎（降低开销）
- 引擎运行在后台线程中，主线程通过队列提交朗读请求
- `speak()` 保持同步语义：提交请求并等待完成事件
- `stop_speaking()` 会调用引擎的 `stop()` 并清空队列
"""
import pyttsx3
import threading
import queue
import time

from .playback_control import should_stop_tts


_ENGINE_LOCK = threading.Lock()
_CURRENT_ENGINE = None
_ENGINE_QUEUE = queue.Queue()
_ENGINE_THREAD = None
_ENGINE_RUNNING = False


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _resolve_pyttsx3_voice(voice_name, engine=None):
    """在给定引擎上查找 voice id；若未提供引擎则使用短期引擎尝试。"""
    created = False
    e = engine
    try:
        if e is None:
            e = pyttsx3.init()
            created = True
        voices = e.getProperty("voices") or []
    except Exception:
        try:
            if created:
                e.stop()
        except Exception:
            pass
        return None

    if not hasattr(voices, "__iter__"):
        try:
            if created:
                e.stop()
        except Exception:
            pass
        return None

    for v in voices:
        if getattr(v, "id", None) == voice_name or getattr(v, "name", None) == voice_name:
            vid = getattr(v, "id", None)
            try:
                if created:
                    e.stop()
            except Exception:
                pass
            return vid

    try:
        if created:
            e.stop()
    except Exception:
        pass
    return None


def _engine_worker():
    """后台线程：持有单个 engine，顺序处理队列中的朗读请求。"""
    global _CURRENT_ENGINE, _ENGINE_RUNNING
    try:
        e = pyttsx3.init()
    except Exception:
        return

    with _ENGINE_LOCK:
        _CURRENT_ENGINE = e
    _ENGINE_RUNNING = True

    while True:
        try:
            item = _ENGINE_QUEUE.get()
        except Exception:
            continue

        if item is None:
            break

        text, volume, speed, voice_name, done_event = item
        try:
            if should_stop_tts():
                if done_event:
                    done_event.set()
                continue

            if voice_name:
                voice_id = _resolve_pyttsx3_voice(voice_name, engine=e)
                if voice_id:
                    try:
                        e.setProperty("voice", voice_id)
                    except Exception:
                        pass

            try:
                base_rate = float(e.getProperty("rate") or 200.0)
            except Exception:
                base_rate = 200.0
            try:
                e.setProperty("rate", int(base_rate + 200.0 * float(speed)))
            except Exception:
                pass
            try:
                e.setProperty("volume", _clamp(abs(float(volume)), 0.0, 1.0))
            except Exception:
                pass

            e.say(str(text))
            e.runAndWait()
        except Exception:
            pass
        finally:
            try:
                if done_event:
                    done_event.set()
            except Exception:
                pass

    try:
        e.stop()
    except Exception:
        pass
    with _ENGINE_LOCK:
        _CURRENT_ENGINE = None
    _ENGINE_RUNNING = False


def _start_engine_worker():
    """启动后台引擎线程（幂等）。"""
    global _ENGINE_THREAD, _ENGINE_RUNNING
    if _ENGINE_RUNNING:
        return True
    _ENGINE_THREAD = threading.Thread(target=_engine_worker, daemon=True)
    _ENGINE_THREAD.start()

    # 等待短时间以确保引擎可用
    timeout = 1.0
    waited = 0.0
    interval = 0.05
    while waited < timeout:
        if _ENGINE_RUNNING:
            return True
        time.sleep(interval)
        waited += interval
    return _ENGINE_RUNNING


def speak(text: str, volume: float, speed: float, voice_name: str):
    """提交朗读请求并阻塞直到完成。返回 (bool, error_str_or_None)。"""
    if should_stop_tts():
        return False, "tts stopped"

    started = _start_engine_worker()
    if not started:
        return False, "failed to start tts engine"

    done_event = threading.Event()
    try:
        _ENGINE_QUEUE.put((text, volume, speed, voice_name, done_event))
    except Exception as e:
        return False, str(e)

    try:
        done_event.wait()
    except Exception:
        pass
    return True, None


def stop_speaking():
    """停止当前播放并清空队列中的待播项。"""
    with _ENGINE_LOCK:
        engine = _CURRENT_ENGINE
    if engine is not None:
        try:
            engine.stop()
        except Exception:
            pass

    # 清空队列中的待播请求
    try:
        while True:
            _ENGINE_QUEUE.get_nowait()
    except Exception:
        pass

