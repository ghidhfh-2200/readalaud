"""
local_window.py —— 本地 Tk 窗口麦克风校准。

说明：
- 完全不依赖 Web 页面/pywebview。
- 实时显示“原始音量（未校准）”与“应用校准值后的音量”。
- 保存时仅写回 settings.json 中的 calibration（偏移量）。
"""

from __future__ import annotations

import math
import threading
from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui

import numpy as np

from ..gui.gui_service import get_gui_service
from ..gui.qt_helpers import run_on_ui
from ..settings import get_setting, update_setting

_DEFAULT_CALIBRATION = 94.0
_CHUNK = 1024
_RATE = 16000
_EPS = 1e-12


def bind_calibration_api(instance):
    """绑定校准入口到核心实例。"""
    instance.start_calibration = lambda: start_calibration(instance)


def _load_calibration(current_acount: str) -> float:
    try:
        return float(get_setting("calibration", _DEFAULT_CALIBRATION))
    except Exception:
        return float(_DEFAULT_CALIBRATION)


def _save_calibration(current_acount: str, offset: float) -> None:
    update_setting("calibration", float(offset))


class _CalibrationWindowController:
    """管理本地校准窗口与麦克风采样线程。"""

    def __init__(self, owner):
        self.owner = owner
        self.gui = get_gui_service(owner)
        self.window: Optional[QtWidgets.QWidget] = None
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._latest_raw_db: Optional[float] = None
        self._destroying = False

        from ..gui.qt_helpers import ValueHolder
        self.raw_var = ValueHolder("-- dB")
        self.calibrated_var = ValueHolder("-- dB")
        self.status_var = ValueHolder("准备就绪")
        self.offset_var = ValueHolder("0")

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
            show=False,
        )
        try:
            # Make dialog a regular top-level window so it won't be auto-closed
            # Use Qt.Window as a flag; fallback if attribute names differ across PySide versions
            # PySide6 enum names vary; try to access common alternatives
            flag_window = getattr(QtCore.Qt, "Window", None) or getattr(QtCore.Qt, "WindowType", None)
            if flag_window is None:
                # last resort: use integer value for Qt::Window (0x00000000)
                flag_window = 0
            self.window.setWindowFlags(self.window.windowFlags() | flag_window)
            # Ensure the widget is not auto-deleted on close (we manage lifecycle)
            try:
                self.window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, False)
            except Exception:
                pass
            # Now that flags are set, show the window
            try:
                self.window.show()
            except Exception:
                pass
        except Exception:
            pass
        self.owner.if_calibration_show = True
        try:
            self.window.destroyed.connect(self._on_destroy)
        except Exception:
            pass

        self._build_ui()
        self._ensure_focus()
        self.status_var.set("正在启动麦克风校准...")
        self._start_meter_thread()

    def focus(self):
        if self.window:
            self.window.show()
            self.window.raise_()
            self.window.activateWindow()

    def _window_exists(self) -> bool:
        """判断窗口对象是否仍然有效。"""
        window = self.window
        if window is None:
            return False
        try:
            return bool(window.isVisible() or window.isEnabled() or window.isActiveWindow() or window.winId())
        except RuntimeError:
            return False
        except Exception:
            return False

    def _ensure_focus(self):
        """窗口创建后主动抢占焦点，确保可立即开始校准。"""
        window = self.window
        if not window:
            return

        def _focus_once():
            current_window = self.window
            if current_window is None:
                return
            if not self._window_exists():
                return
            try:
                current_window.show()
                current_window.raise_()
                current_window.activateWindow()
                current_window.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
                current_window.show()
                QtCore.QTimer.singleShot(120, lambda win=current_window: win.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, False) if win is not None else None)
            except Exception:
                pass

        _focus_once()
        QtCore.QTimer.singleShot(80, _focus_once)
        QtCore.QTimer.singleShot(220, _focus_once)

    def close(self):
        if self._destroying:
            return
        self._destroying = True
        try:
            try:
                if self.owner and hasattr(self.owner, "log_operation"):
                    self.owner.log_operation("关闭校准窗口", "开始关闭并停止采样线程")
            except Exception:
                pass
            self._stop_event.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=1.0)
            try:
                if self.window:
                    self.window.close()
            except Exception:
                pass
            self.window = None
        finally:
            self._destroying = False

    def _on_destroy(self, _event=None):
        # Ensure a clean shutdown when the widget is destroyed
        try:
            if not self._destroying:
                self.close()
        except Exception:
            pass
        try:
            self.owner.if_calibration_show = False
        except Exception:
            pass
        try:
            setattr(self.owner, "_calibration_controller", None)
        except Exception:
            pass

    def _build_ui(self):
        assert self.window is not None
        layout = QtWidgets.QVBoxLayout(self.window)
        layout.setContentsMargins(12, 10, 12, 10)

        meter_row = QtWidgets.QWidget()
        meter_layout = QtWidgets.QHBoxLayout(meter_row)
        meter_layout.setContentsMargins(0, 0, 0, 0)

        raw_frame = QtWidgets.QGroupBox("校准前音量（原始）")
        raw_layout = QtWidgets.QVBoxLayout(raw_frame)
        raw_label = QtWidgets.QLabel(self.raw_var.get())
        raw_label.setFont(QtGui.QFont("微软雅黑", 24, QtGui.QFont.Weight.Bold))
        raw_label.setStyleSheet("color: #2e86de;")
        self.raw_var.changed.connect(raw_label.setText)
        raw_layout.addWidget(raw_label)

        calibrated_frame = QtWidgets.QGroupBox("校准后音量（原始 + 校准值）")
        cal_layout = QtWidgets.QVBoxLayout(calibrated_frame)
        cal_label = QtWidgets.QLabel(self.calibrated_var.get())
        cal_label.setFont(QtGui.QFont("微软雅黑", 24, QtGui.QFont.Weight.Bold))
        cal_label.setStyleSheet("color: #1d6f42;")
        self.calibrated_var.changed.connect(cal_label.setText)
        cal_layout.addWidget(cal_label)

        meter_layout.addWidget(raw_frame)
        meter_layout.addWidget(calibrated_frame)
        layout.addWidget(meter_row)

        input_row = QtWidgets.QWidget()
        input_layout = QtWidgets.QHBoxLayout(input_row)
        input_layout.setContentsMargins(0, 0, 0, 0)
        input_layout.addWidget(QtWidgets.QLabel("校准值（dB）："))
        entry = QtWidgets.QLineEdit(self.offset_var.get())
        entry.setFont(QtGui.QFont(self.owner.mainpage_button_font[0], self.owner.mainpage_button_font[1]))
        entry.setFixedWidth(140)
        entry.textChanged.connect(self.offset_var.set)
        entry.textChanged.connect(lambda _e: self._refresh_calibrated_preview())
        input_layout.addWidget(entry)
        layout.addWidget(input_row)

        status_label = QtWidgets.QLabel(self.status_var.get())
        status_label.setFont(QtGui.QFont(self.owner.mainpage_button_font[0], self.owner.mainpage_button_font[1]))
        self.status_var.changed.connect(status_label.setText)
        layout.addWidget(status_label)

        button_row = QtWidgets.QWidget()
        button_layout = QtWidgets.QHBoxLayout(button_row)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addStretch(1)
        save_btn = QtWidgets.QPushButton("保存")
        save_btn.clicked.connect(self._save)
        close_btn = QtWidgets.QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(close_btn)
        layout.addWidget(button_row)

    def _parse_offset(self) -> Optional[float]:
        raw = str(self.offset_var.get()).strip()
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
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._meter_loop, daemon=True)
        try:
            if self.owner and hasattr(self.owner, "log_operation"):
                try:
                    self.owner.log_operation("校准线程", "启动麦克风采样线程")
                except Exception:
                    pass
        except Exception:
            pass
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
                    # transient read error; give small pause to avoid busy loop
                    import time

                    time.sleep(0.05)
                    continue

                samples = np.frombuffer(frame, dtype=np.int16)
                if samples.size == 0:
                    continue
                normalized = samples.astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(normalized * normalized)))
                raw_db = 20.0 * math.log10(max(rms, _EPS))
                self._latest_raw_db = raw_db
                try:
                    self._safe_ui_call(lambda v=raw_db: self._update_meter_values(v))
                except Exception:
                    # UI dispatch failed — log and continue
                    try:
                        if self.owner and hasattr(self.owner, "log_error"):
                            self.owner.log_error("校准UI更新失败", "_safe_ui_call 或 _update_meter_values 异常")
                    except Exception:
                        pass
                    continue
        except Exception as e:
            try:
                if self.owner and hasattr(self.owner, "log_error"):
                    self.owner.log_error("麦克风采样线程异常", str(e))
            except Exception:
                pass
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
            if self.window:
                run_on_ui(callback)
        except Exception:
            pass


def start_calibration(self):
    """启动本地 Tk 校准窗口（单实例）。"""
    existing = getattr(self, "_calibration_controller", None)
    if existing is not None and getattr(existing, "window", None) is not None:
        try:
            if existing._window_exists():
                existing.focus()
    
                existing.status_var.set("正在启动麦克风校准...")
                existing._start_meter_thread()
                return
        except Exception:
            pass

    controller = _CalibrationWindowController(self)
    setattr(self, "_calibration_controller", controller)
    controller.open()
