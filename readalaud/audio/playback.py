"""
playback.py —— 日录音文件的播放、暂停、停止与进度条控制。
"""
import os
import time
import wave
from PySide6 import QtCore


def bind_audio_analasy_api(instance):
    instance.stop_day_audio = lambda reset=False: stop_day_audio(instance, reset)
    instance.play_day_audio = lambda: play_day_audio(instance)
    instance.pause_day_audio = lambda: pause_day_audio(instance)
    instance.seek_day_audio = lambda: seek_day_audio(instance)
    instance.init_audio_state = lambda: init_audio_state(instance)


def init_audio_state(self):
    self._day_audio_state = {
        "path": "",
        "duration": 0.0,
        "offset": 0.0,
        "playing": False,
        "paused": False,
        "play_obj": None,
        "play_start": None,
        "frame_rate": 0,
        "channels": 0,
        "sampwidth": 0,
        "raw": b"",
        "after_id": None,
        "programmatic": False,
    }


# ── 辅助工具 ─────────────────────────────────────────────

def _format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _set_audio_status(self, text="", color="#dc3545"):
    if hasattr(self, "day_audio_status"):
        self.day_audio_status.setText(text)
        self.day_audio_status.setStyleSheet(f"color: {color};")


def _cancel_progress_timer(self):
    st = getattr(self, "_day_audio_state", {})
    timer = st.get("after_id")
    if timer is None:
        return
    try:
        timer.stop()
    except Exception:
        pass
    st["after_id"] = None


def _schedule_progress_tick(self, interval_ms=200):
    st = getattr(self, "_day_audio_state", {})
    _cancel_progress_timer(self)
    parent = getattr(self, "day_detail_container", None)
    timer = QtCore.QTimer(parent)
    timer.setSingleShot(True)
    timer.timeout.connect(lambda: _update_progress_tick(self))
    timer.start(interval_ms)
    st["after_id"] = timer


def get_audio_duration(path):
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            fr = wf.getframerate()
        return frames / fr if fr else 0.0
    except Exception:
        return 0.0


def _load_audio_meta(path):
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            fr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(frames)
        duration = frames / fr if fr else 0.0
        return duration, fr, ch, sw, raw
    except Exception as e:
        print(f"Error loading audio: {e}")
        return 0.0, 0, 0, 0, b""


# ── 播放控制 ─────────────────────────────────────────────

def stop_day_audio(self, reset=False):
    st = getattr(self, "_day_audio_state", {})
    try:
        if st.get("play_obj") is not None:
            st["play_obj"].stop()
    except Exception:
        pass
    st["playing"] = False
    st["paused"] = False
    st["play_obj"] = None
    st["play_start"] = None
    _cancel_progress_timer(self)
    if reset:
        st["offset"] = 0.0
        st["programmatic"] = True
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.setValue(0)
        st["programmatic"] = False


def _update_progress_tick(self):
    st = getattr(self, "_day_audio_state", {})
    if not st.get("playing"):
        return
    elapsed = time.time() - (st.get("play_start") or time.time())
    current = st.get("offset", 0.0) + max(0.0, elapsed)
    if current >= st.get("duration", 0.0) or (st.get("play_obj") and not st["play_obj"].is_playing()):
        stop_day_audio(self, reset=True)
        _set_audio_status(self, "播放完成", "#28a745")
        return
    st["programmatic"] = True
    if hasattr(self, "day_audio_scale"):
        self.day_audio_scale.setValue(int(current))
    st["programmatic"] = False
    _set_audio_status(self, f"{_format_time(current)} / {_format_time(st.get('duration', 0))}", "#6c757d")
    _schedule_progress_tick(self, 200)


def _play_from_offset(self):
    st = getattr(self, "_day_audio_state", {})
    if not st.get("raw"):
        return False
    try:
        import simpleaudio as sa
    except Exception:
        _set_audio_status(self, "缺少播放库，无法播放", "#dc3545")
        return False

    frame_bytes = st["channels"] * st["sampwidth"]
    start_frame = int(st.get("offset", 0.0) * st["frame_rate"]) if st["frame_rate"] else 0
    start_byte = start_frame * frame_bytes
    audio_bytes = st["raw"][start_byte:] if start_byte < len(st["raw"]) else b""
    if not audio_bytes:
        return False

    st["play_obj"] = sa.play_buffer(audio_bytes, st["channels"], st["sampwidth"], st["frame_rate"])
    st["play_start"] = time.time()
    st["playing"] = True
    st["paused"] = False
    _update_progress_tick(self)
    return True


def play_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None:
        return
    if not st.get("path") or not os.path.exists(st["path"]):
        _set_audio_status(self, "无音频", "#dc3545")
        st["programmatic"] = True
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.setValue(0)
        st["programmatic"] = False
        return
    if not st.get("raw"):
        duration, fr, ch, sw, raw = _load_audio_meta(st["path"])
        st.update({"duration": duration, "frame_rate": fr, "channels": ch, "sampwidth": sw, "raw": raw})
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.setRange(0, max(1, int(duration)))
    if st.get("playing"):
        return
    ok = _play_from_offset(self)
    if not ok:
        _set_audio_status(self, "无法播放音频", "#dc3545")


def pause_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None or not st.get("playing"):
        return
    elapsed = time.time() - (st.get("play_start") or time.time())
    st["offset"] = min(st.get("duration", 0.0), st.get("offset", 0.0) + max(0.0, elapsed))
    stop_day_audio(self, reset=False)
    st["paused"] = True
    st["programmatic"] = True
    if hasattr(self, "day_audio_scale"):
        self.day_audio_scale.setValue(int(st["offset"]))
    st["programmatic"] = False
    _set_audio_status(self, f"已暂停 {_format_time(st['offset'])}", "#6c757d")


def seek_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None or st.get("programmatic"):
        return
    try:
        new_val = float(self.day_audio_scale.value())
    except Exception:
        return
    st["offset"] = max(0.0, min(new_val, st.get("duration", 0.0)))
    _set_audio_status(self, f"{_format_time(st['offset'])} / {_format_time(st.get('duration', 0))}", "#6c757d")
    if st.get("playing"):
        stop_day_audio(self, reset=False)
        _play_from_offset(self)
