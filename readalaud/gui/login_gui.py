"""
登录 / 注册页面 GUI。
"""

import threading
import time
from PySide6 import QtCore, QtWidgets, QtGui
from .qt_helpers import ValueHolder, run_on_ui


def _set_login_status(self, message, level="info"):
    """更新登录页状态文本，不使用弹窗。"""
    color_map = {
        "info": "#6c757d",
        "success": "#1d6f42",
        "warning": "#ffbf00",
        "error": "#dc3545",
    }
    color = color_map.get(level, color_map["info"])

    try:
        if hasattr(self, "login_status_var") and self.login_status_var is not None:
            self.login_status_var.set(message)
        if hasattr(self, "login_status_label") and self.login_status_label is not None:
            self.login_status_label.setStyleSheet(f"color: {color};")
    except Exception:
        pass


def _stop_login_lock_countdown(self):
    """停止登录锁定倒计时线程。"""
    try:
        evt = getattr(self, "_login_status_stop_event", None)
        if evt is not None:
            evt.set()
    except Exception:
        pass

    thread = getattr(self, "_login_status_thread", None)
    if thread and thread.is_alive():
        thread.join(timeout=0.8)

    self._login_status_thread = None
    self._login_status_stop_event = None
    self._login_status_account = None
    self._login_status_locked_until = 0


def _start_login_lock_countdown(self, encoded_account, locked_until_ts):
    """启动锁定剩余时间实时刷新线程。"""
    _stop_login_lock_countdown(self)
    stop_event = threading.Event()
    self._login_status_stop_event = stop_event
    self._login_status_account = encoded_account
    self._login_status_locked_until = float(locked_until_ts or 0)

    def _worker():
        while not stop_event.is_set():
            remain = int(self._login_status_locked_until - time.time())
            if remain <= 0:
                _post_status("锁定已解除，请重新尝试登录", "success")
                break

            mins, sec = divmod(remain, 60)
            hours, mins = divmod(mins, 60)
            days, hours = divmod(hours, 24)
            if days > 0:
                remain_text = f"{days}天{hours}小时{mins}分{sec}秒"
            elif hours > 0:
                remain_text = f"{hours}小时{mins}分{sec}秒"
            elif mins > 0:
                remain_text = f"{mins}分{sec}秒"
            else:
                remain_text = f"{sec}秒"

            _post_status(f"登录已锁定，剩余时间：{remain_text}", "warning")
            if stop_event.wait(1.0):
                break

    def _post_status(msg, level):
        try:
            run_on_ui(lambda: _set_login_status(self, msg, level))
        except Exception:
            pass

    self._login_status_thread = threading.Thread(target=_worker, daemon=True)
    self._login_status_thread.start()


def _generate_login_gui(self):
    if self.if_login_show == True:
        return
    else:
        self.if_login_show = True

    self.login_frame = QtWidgets.QWidget()
    self.login_layout = QtWidgets.QVBoxLayout(self.login_frame)
    self.login_layout.setContentsMargins(10, 10, 10, 10)
    self.main_paned_window.addWidget(self.login_frame, 7)
    # empty the previous frame
    if self.if_main_window_show == True:
        self.content_frame.deleteLater()
        self.if_main_window_show = False
    elif self.if_settings_show == True:
        self.settings_frame.deleteLater()
        self.if_settings_show = False
    elif self.if_reading_show == True:
        self.reading_frame.deleteLater()
        self.if_reading_show = False
    self.if_login_show = True

    instruection_label = QtWidgets.QLabel("请输入账号&密码（没有密码无需输入）\n新账号自动注册")
    instruection_label.setFont(QtGui.QFont(self.font[0], self.font[1]))
    instruection_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    self.login_layout.addStretch(1)
    self.login_layout.addWidget(instruection_label)

    self.login_status_var = ValueHolder("请输入账号和密码")
    self.login_status_label = QtWidgets.QLabel(self.login_status_var.get())
    self.login_status_label.setFont(QtGui.QFont("微软雅黑", 10))
    self.login_status_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    self.login_status_label.setStyleSheet("color: #6c757d;")
    self.login_status_var.changed.connect(self.login_status_label.setText)
    self.login_layout.addWidget(self.login_status_label, alignment=QtCore.Qt.AlignmentFlag.AlignHCenter)

    def _update_login_input_width():
        """保持登录输入区域居中并占据登录页宽度的一半。"""
        try:
            frame_width = max(0, self.login_frame.width())
            target_width = max(260, int(frame_width * 0.5))
            for widget in (
                getattr(self, "login_enter_acount_name", None),
                getattr(self, "login_enter_password_entry", None),
            ):
                if widget is not None:
                    widget.setMinimumWidth(target_width)
                    widget.setMaximumWidth(target_width)
        except Exception:
            pass

    self._update_login_input_width = _update_login_input_width

    # enter username row
    enter_user_name = QtWidgets.QWidget()
    enter_user_layout = QtWidgets.QHBoxLayout(enter_user_name)
    enter_user_layout.setContentsMargins(0, 0, 0, 0)
    enter_user_layout.addStretch(1)
    self.login_enter_acount_label = QtWidgets.QLabel("用户名：")
    self.login_enter_acount_label.setFont(QtGui.QFont("微软雅黑", 14))
    self.login_enter_acount_name = QtWidgets.QLineEdit()
    self.login_enter_acount_name.setFont(QtGui.QFont("微软雅黑", 14))
    self.login_enter_acount_name.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
    self.login_enter_acount_name.setMinimumWidth(260)
    if isinstance(self.login_acount_enter, ValueHolder):
        self.login_enter_acount_name.setText(self.login_acount_enter.get() or "")
        self.login_enter_acount_name.textChanged.connect(self.login_acount_enter.set)
    enter_user_layout.addWidget(self.login_enter_acount_label)
    enter_user_layout.addWidget(self.login_enter_acount_name)
    enter_user_layout.addStretch(1)
    self.login_layout.addWidget(enter_user_name)

    # enter password row
    enter_password = QtWidgets.QWidget()
    enter_pwd_layout = QtWidgets.QHBoxLayout(enter_password)
    enter_pwd_layout.setContentsMargins(0, 0, 0, 0)
    enter_pwd_layout.addStretch(1)
    self.login_enter_password_label = QtWidgets.QLabel("密码：")
    self.login_enter_password_label.setFont(QtGui.QFont("微软雅黑", 14))
    self.login_enter_password_entry = QtWidgets.QLineEdit()
    self.login_enter_password_entry.setFont(QtGui.QFont("微软雅黑", 14))
    self.login_enter_password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
    self.login_enter_password_entry.setSizePolicy(QtWidgets.QSizePolicy.Policy.Fixed, QtWidgets.QSizePolicy.Policy.Fixed)
    self.login_enter_password_entry.setMinimumWidth(260)
    if isinstance(self.login_password_enter, ValueHolder):
        self.login_enter_password_entry.setText(self.login_password_enter.get() or "")
        self.login_enter_password_entry.textChanged.connect(self.login_password_enter.set)
    enter_pwd_layout.addWidget(self.login_enter_password_label)
    enter_pwd_layout.addWidget(self.login_enter_password_entry)
    enter_pwd_layout.addStretch(1)
    self.login_layout.addWidget(enter_password)

    # buttons
    button_row = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_row)
    button_layout.setContentsMargins(0, 0, 0, 0)
    self.login_button = QtWidgets.QPushButton("登录/注册")
    self.login_button.setFixedWidth(150)
    self.login_button.clicked.connect(lambda: self.login_and_sign_up())
    self.cancel_button = QtWidgets.QPushButton("取消")
    self.cancel_button.setFixedWidth(150)
    self.cancel_button.clicked.connect(lambda: self.welcome_page(destroy_window=[self.login_frame, "login"]))
    button_layout.addWidget(self.login_button)
    button_layout.addWidget(self.cancel_button)
    self.login_layout.addWidget(button_row)
    self.login_layout.addStretch(1)

    self.login_frame.destroyed.connect(lambda _e=None: _stop_login_lock_countdown(self))

    login_frame_ref = self.login_frame

    class _LoginFrameResizeFilter(QtCore.QObject):
        def eventFilter(self, obj, event):
            if obj is login_frame_ref and event.type() == QtCore.QEvent.Type.Resize:
                _update_login_input_width()
            return False

    try:
        self._login_frame_resize_filter = _LoginFrameResizeFilter(self.login_frame)
        self.login_frame.installEventFilter(self._login_frame_resize_filter)
    except Exception:
        pass
    _update_login_input_width()
