"""
playback_control.py —— TTS 播放全局停止控制。
"""
import threading

_stop_event = threading.Event()
_play_lock = threading.Lock()
_active_play_objs = set()


def clear_stop_request():
    _stop_event.clear()


def request_stop_all_tts():
    """请求停止所有 TTS 播放，并尝试立即停止已注册的播放对象。"""
    _stop_event.set()
    with _play_lock:
        objs = list(_active_play_objs)
    for obj in objs:
        try:
            obj.stop()
        except Exception:
            pass


def should_stop_tts():
    return _stop_event.is_set()


def register_play_obj(play_obj):
    if play_obj is None:
        return
    with _play_lock:
        _active_play_objs.add(play_obj)


def unregister_play_obj(play_obj):
    if play_obj is None:
        return
    with _play_lock:
        _active_play_objs.discard(play_obj)
