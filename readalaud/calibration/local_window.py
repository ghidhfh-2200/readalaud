"""
local_window.py —— 本地 Tk 窗口麦克风校准。

说明：
- 完全不依赖 Web 页面/pywebview。
- 实时显示“原始音量（未校准）”与“应用校准值后的音量”。
- 保存时仅写回 settings.json 中的 calibration（偏移量）。
"""

from __future__ import annotations

import json
import math
import os
import threading
import tkinter as tk
from typing import Optional

import numpy as np

from ..gui.gui_service import get_gui_service

_DEFAULT_CALIBRATION = 94.0
_CHUNK = 1024
_RATE = 16000
_EPS = 1e-12


def bind_calibration_api(instance):
    """绑定校准入口到核心实例。"""
    instance.start_calibration = lambda: start_calibration(instance)


def _settings_path(current_acount: str) -> str:
    return os.path.join(".", "data", current_acount, "settings.json")


def _load_calibration(current_acount: str) -> float:
    path = _settings_path(current_acount)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return float(data.get("calibration", _DEFAULT_CALIBRATION))
    except Exception:
        return float(_DEFAULT_CALIBRATION)


def _save_calibration(current_acount: str, offset: float) -> None:
    path = _settings_path(current_acount)
    payload = {}
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception:
            payload = {}
    payload["calibration"] = float(offset)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


class _CalibrationWindowController:
    """管理本地校准窗口与麦克风采样线程。"""

    def __init__(self, owner):
        self.owner = owner
        self.gui = get_gui_service(owner)
        self.window: Optional[tk.Toplevel] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_raw_db: Optional[float] = None

        self.raw_var = tk.StringVar(value="-- dB")
        self.calibrated_var = tk.StringVar(value="-- dB")
        self.status_var = tk.StringVar(value="准备就绪")
        self.offset_var = tk.StringVar(value="0")

    def open(self):
        current_acount = getattr(self.owner, "current_acount", "")
        if not current_acount:
            self.gui.warning(message="未检测到登录账号，无法进行校准", title="提示")
            return

        self.offset_var.set(f"{_load_calibration(current_acount):.2f}")

        self.window = self.gui.create_toplevel(
            title="麦克风校准",
            size=(520, 280),
            parent=getattr(self.owner, "main_window", None),
            resizable=(False, False),
            modal=False,
            center=True,
        )
        self.owner.if_calibration_show = True
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.window.bind("<Destroy>", self._on_destroy)

        self._build_ui()
        self._ensure_focus()
        self._start_meter_thread()

    def focus(self):
        if self.window and self.window.winfo_exists():
            self.window.deiconify()
            self.window.lift()
            self.window.focus_force()

    def _ensure_focus(self):
        """窗口创建后主动抢占焦点，确保可立即开始校准。"""
        if not self.window or not self.window.winfo_exists():
            return

        def _focus_once():
            if not self.window or not self.window.winfo_exists():
                return
            try:
                self.window.deiconify()
                self.window.lift()
                self.window.attributes("-topmost", True)
                self.window.focus_force()
                self.window.after(120, lambda: self.window and self.window.winfo_exists() and self.window.attributes("-topmost", False))
            except Exception:
                pass

        _focus_once()
        self.window.after(80, _focus_once)
        self.window.after(220, _focus_once)

    def close(self):
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self.window and self.window.winfo_exists():
            self.window.destroy()

    def _on_destroy(self, _event=None):
        self._stop_event.set()
        self.owner.if_calibration_show = False
        setattr(self.owner, "_calibration_controller", None)

    def _build_ui(self):
        assert self.window is not None

        main = tk.Frame(self.window, padx=12, pady=10)
        main.pack(fill="both", expand=True)

        meter_row = tk.Frame(main)
        meter_row.pack(fill="x", pady=(0, 10))

        raw_frame = tk.LabelFrame(meter_row, text="校准前音量（原始）", padx=10, pady=10)
        raw_frame.pack(side="left", fill="both", expand=True, padx=(0, 6))
        tk.Label(raw_frame, textvariable=self.raw_var, font=("微软雅黑", 24, "bold"), fg="#2e86de").pack()

        calibrated_frame = tk.LabelFrame(meter_row, text="校准后音量（原始 + 校准值）", padx=10, pady=10)
        calibrated_frame.pack(side="left", fill="both", expand=True, padx=(6, 0))
        tk.Label(calibrated_frame, textvariable=self.calibrated_var, font=("微软雅黑", 24, "bold"), fg="#1d6f42").pack()

        input_row = tk.Frame(main)
        input_row.pack(fill="x", pady=(2, 8))
        tk.Label(input_row, text="校准值（dB）：", font=self.owner.mainpage_button_font).pack(side="left")
        entry = tk.Entry(input_row, textvariable=self.offset_var, width=14, font=self.owner.mainpage_button_font)
        entry.pack(side="left", padx=(6, 0))
        entry.bind("<KeyRelease>", lambda _e: self._refresh_calibrated_preview())

        tk.Label(main, textvariable=self.status_var, font=self.owner.mainpage_button_font, anchor="w").pack(fill="x")

        button_row = tk.Frame(main)
        button_row.pack(fill="x", pady=(12, 0))
        tk.Button(button_row, text="保存", width=10, command=self._save).pack(side="right", padx=(6, 0))
        tk.Button(button_row, text="关闭", width=10, command=self.close).pack(side="right")

    def _parse_offset(self) -> Optional[float]:
        raw = self.offset_var.get().strip()
        if raw == "":
            return None
        try:
            return float(raw)
        except Exception:
            return None

    def _refresh_calibrated_preview(self):
        offset = self._parse_offset()
        if self._latest_raw_db is None:
            self.calibrated_var.set("-- dB")
            return
        if offset is None:
            self.calibrated_var.set("输入无效")
            return
        self.calibrated_var.set(f"{self._latest_raw_db + offset:.1f} dB")

    def _save(self):
        current_acount = getattr(self.owner, "current_acount", "")
        if not current_acount:
            self.gui.warning(message="未检测到登录账号，无法保存校准值", title="提示")
            return

        offset = self._parse_offset()
        if offset is None:
            self.gui.warning(message="请输入有效的校准值（数字）", title="输入无效")
            return

        try:
            _save_calibration(current_acount, offset)
            if isinstance(getattr(self.owner, "load_settings", None), dict):
                self.owner.load_settings["calibration"] = float(offset)
            try:
                self.owner.log_operation("保存麦克风校准", f"calibration={offset}")
            except Exception:
                pass
            self.status_var.set("校准值已保存")
        except Exception as e:
            try:
                self.owner.log_error("保存麦克风校准失败", str(e))
            except Exception:
                pass
            self.gui.error(message=f"保存失败：{e}", title="错误")

    def _start_meter_thread(self):
        self._thread = threading.Thread(target=self._meter_loop, daemon=True)
        self._thread.start()

    def _meter_loop(self):
        pa = None
        stream = None
        try:
            import pyaudio

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=_RATE,
                input=True,
                frames_per_buffer=_CHUNK,
            )
            self._safe_ui_call(lambda: self.status_var.set("正在采集麦克风音量..."))

            while not self._stop_event.is_set():
                try:
                    frame = stream.read(_CHUNK, exception_on_overflow=False)
                except Exception:
                    continue

                samples = np.frombuffer(frame, dtype=np.int16)
                if samples.size == 0:
                    continue
                normalized = samples.astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(normalized * normalized)))
                raw_db = 20.0 * math.log10(max(rms, _EPS))
                self._latest_raw_db = raw_db
                self._safe_ui_call(lambda v=raw_db: self._update_meter_values(v))
        except Exception as e:
            self._safe_ui_call(lambda: self.status_var.set(f"麦克风初始化失败：{e}"))
        finally:
            try:
                if stream is not None:
                    stream.stop_stream()
                    stream.close()
            except Exception:
                pass
            try:
                if pa is not None:
                    pa.terminate()
            except Exception:
                pass

    def _update_meter_values(self, raw_db: float):
        self.raw_var.set(f"{raw_db:.1f} dB")
        self._refresh_calibrated_preview()

    def _safe_ui_call(self, callback):
        try:
            if self.window and self.window.winfo_exists():
                self.window.after(0, callback)
        except Exception:
            pass


def start_calibration(self):
    """启动本地 Tk 校准窗口（单实例）。"""
    existing = getattr(self, "_calibration_controller", None)
    if existing is not None and getattr(existing, "window", None) is not None:
        try:
            if existing.window.winfo_exists():
                existing.focus()
                return
        except Exception:
            pass

    controller = _CalibrationWindowController(self)
    setattr(self, "_calibration_controller", controller)
    controller.open()
