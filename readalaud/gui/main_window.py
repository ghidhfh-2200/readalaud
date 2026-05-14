"""
主窗口创建、欢迎页面、窗口切换导航。
"""

import base64
import threading
from PySide6 import QtCore, QtWidgets, QtGui
from ..calibration import start_calibration
from ..server import check_if_server_running, server_pid, end_server_process, start_manager
from ..reading.data_io import load_today_reading_status


# ──────────────────────── 主窗口 ────────────────────────

def _generate_main_window(self):
    self.main_window = QtWidgets.QMainWindow()
    self._sidebar_status_stop_event = threading.Event()
    self._sidebar_status_thread = None
    try:
        self.main_window.setWindowIcon(QtGui.QIcon("./assets/icon.ico"))
    except Exception:
        pass
    # create ValueHolder instances after the root exists
    if getattr(self, 'login_password_enter', None) is None:
        from .qt_helpers import ValueHolder
        self.login_password_enter = ValueHolder("")
    if getattr(self, 'login_acount_enter', None) is None:
        from .qt_helpers import ValueHolder
        self.login_acount_enter = ValueHolder("")
    self.content = ""
    self.main_window.resize(800, 600)
    self.main_window.setWindowTitle("ReadAlaud——告别摸鱼偷懒，回归大声早读！")
    self.gui.set_theme("darkly")
    # create a horizontal layout widget
    self.main_paned_window_widget = QtWidgets.QWidget()
    self.main_paned_window = QtWidgets.QHBoxLayout(self.main_paned_window_widget)
    self.main_paned_window.setContentsMargins(0, 0, 0, 0)
    central = QtWidgets.QWidget()
    central_layout = QtWidgets.QVBoxLayout(central)
    central_layout.setContentsMargins(0, 0, 0, 0)
    central_layout.addWidget(self.main_paned_window_widget)
    self.main_window.setCentralWidget(central)
    # button frame
    button_frame = QtWidgets.QWidget()
    button_layout = QtWidgets.QVBoxLayout(button_frame)
    button_layout.setContentsMargins(6, 6, 6, 6)
    self.main_paned_window.addWidget(button_frame, 2)
    # content frame
    self.content_frame = QtWidgets.QWidget()
    self.content_layout = QtWidgets.QVBoxLayout(self.content_frame)
    self.content_layout.setContentsMargins(6, 6, 6, 6)
    self.main_paned_window.addWidget(self.content_frame, 8)

    title = QtWidgets.QLabel("ReadAlaud\n告别摸鱼偷懒,回归大声早读！")
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title.setFont(QtGui.QFont(self.font[0], self.font[1]))
    self.content_layout.addWidget(title, 1)
    self.if_main_window_show = True
    # buttons
    login_button = QtWidgets.QPushButton("登录（自动注册）")
    login_button.clicked.connect(lambda: self.generate_login_gui())
    button_layout.addWidget(login_button)
    self.current_account_label = QtWidgets.QLabel("当前登录：(未登录)")
    self.current_account_label.setFont(QtGui.QFont("微软雅黑", 12))
    button_layout.addWidget(self.current_account_label)

    sidebar_status_frame = QtWidgets.QGroupBox("今日朗读状态")
    sidebar_layout = QtWidgets.QVBoxLayout(sidebar_status_frame)
    button_layout.addWidget(sidebar_status_frame)

    self.sidebar_status_labels = {
        "state": QtWidgets.QLabel("是否朗读：--"),
        "completion": QtWidgets.QLabel("目标达成度：--"),
        "total": QtWidgets.QLabel("总时长：--:--:--"),
        "efficiency": QtWidgets.QLabel("效率：--"),
        "compare": QtWidgets.QLabel("较昨日总时长：--"),
    }
    for key in ["state", "completion", "total", "efficiency", "compare"]:
        self.sidebar_status_labels[key].setWordWrap(True)
        sidebar_layout.addWidget(self.sidebar_status_labels[key])
    _reset_sidebar_today_status(self)

    def _on_close(event):
        check_if_reading(self)
        event.ignore()
    self.main_window.closeEvent = _on_close
    self.main_window.show()


# ──────────────────────── 关闭确认 ────────────────────────

def check_if_reading(self):
    if self.if_reading:
        # 双重检查：确认服务器确实还在运行
        server_running = check_if_server_running()
        if server_running:
            self.gui.info(title="无法关闭", message="当前正在朗读，请结束朗读后再关闭主窗口！")
        else:
            # 服务器已经不在运行，重置朗读状态
            self.if_reading = False
            if_exit = self.gui.ask_yes_no(title="确定要关闭吗？", message="朗读服务器已停止。确认要关闭吗?")
            if if_exit:
                self.main_window.close()
    else:
        # 检查服务器是否仍在后台运行
        server_running = check_if_server_running()
        if server_running:
            action = self.gui.ask_yes_no_cancel(
                title="服务器仍在运行",
                message="检测到朗读服务器仍在后台运行。\n\n是 - 关闭服务器并退出\n否 - 保留服务器并退出\n取消 - 返回"
            )
            if action is True:
                # 关闭服务器并退出
                pid = server_pid()
                if pid:
                    end_server_process(pid=pid, force=True)
                self.main_window.close()
            elif action is False:
                # 保留服务器并退出
                self.main_window.close()
            # action is None (取消): 不做任何事
        else:
            if_exit = self.gui.ask_yes_no(title="确定要关闭吗？", message="确认要关闭吗?")
            if if_exit:
                self.main_window.close()


# ──────────────────────── 欢迎页 / 导航 ────────────────────────

def _welcome_page(self, destroy_window):
    if destroy_window[1] == "login":
        try:
            self.stop_login_lock_countdown()
        except Exception:
            pass
    try:
        destroy_window[0].deleteLater()
    except Exception:
        pass
    if destroy_window[1] == "login":
        self.if_login_show = False
    elif destroy_window[1] == "settings":
        self.if_settings_show = False
    elif destroy_window[1] == "reading":
        self.if_reading_show = False
    elif destroy_window[1] == "data_form":
        self.if_data_form_show = False
    self.if_main_window_show = True
    self.content_frame = QtWidgets.QWidget()
    self.content_layout = QtWidgets.QVBoxLayout(self.content_frame)
    self.content_layout.setContentsMargins(6, 6, 6, 6)
    self.main_paned_window.addWidget(self.content_frame, 7)
    main_label_frame = QtWidgets.QWidget()
    main_layout = QtWidgets.QVBoxLayout(main_label_frame)
    main_layout.setContentsMargins(5, 5, 5, 5)
    main_layout.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    title = QtWidgets.QLabel("ReadAlaud\n告别摸鱼偷懒,回归大声早读！")
    title.setFont(QtGui.QFont(self.font[0], self.font[1]))
    title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    main_layout.addWidget(title)
    self.content_layout.addWidget(main_label_frame, 1)
    if self.if_logged_in == False and self.gui.get_theme() != "darkly":
        self.gui.set_theme("darkly")
    if self.if_logged_in == True:
        try:
            self.current_account_label.setText(
                f"当前登录：{base64.urlsafe_b64decode(self.current_acount).decode('utf-8')}"
            )
        except Exception:
            self.current_account_label.setText("当前登录：(已登录)")
        settings_button = QtWidgets.QPushButton("设置")
        settings_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
        settings_button.clicked.connect(lambda: self.generate_settings_gui())
        main_layout.addWidget(settings_button)

        read_button = QtWidgets.QPushButton("开始朗读")
        read_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
        read_button.clicked.connect(lambda: self.generate_reading_gui())
        main_layout.addWidget(read_button)

        calibration_button = QtWidgets.QPushButton("麦克风校准")
        calibration_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
        calibration_button.clicked.connect(lambda: start_calibration(self))
        main_layout.addWidget(calibration_button)

        data_button = QtWidgets.QPushButton("朗读数据")
        data_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
        data_button.clicked.connect(lambda: self.generate_data_gui())
        main_layout.addWidget(data_button)

        server_manager_btn = QtWidgets.QPushButton("服务器管理")
        server_manager_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
        server_manager_btn.clicked.connect(lambda: start_manager(self))
        main_layout.addWidget(server_manager_btn)

        _start_sidebar_today_status_monitor(self)


def _reset_sidebar_today_status(self):
    labels = getattr(self, "sidebar_status_labels", None)
    if not labels:
        return
    try:
        labels["state"].setText("是否朗读：--")
        labels["completion"].setText("目标达成度：--")
        labels["total"].setText("总时长：--:--:--")
        labels["efficiency"].setText("效率：--")
        labels["compare"].setText("较昨日总时长：--")
    except Exception:
        pass


def _apply_sidebar_today_status(self, status):
    labels = getattr(self, "sidebar_status_labels", None)
    if not labels:
        return
    try:
        if not status:
            _reset_sidebar_today_status(self)
            labels["state"].setText("是否朗读：未登录")
            return

        total_duration = int(status.get("total_duration", 0) or 0)
        efficiency = float(status.get("efficiency", 0.0) or 0.0)
        completion_ratio = status.get("completion_ratio")
        compare_yesterday = status.get("compare_yesterday")

        labels['state'].setText(f"是否朗读: {'已朗读' if total_duration > 0 else '未朗读'}")
        if completion_ratio is None:
            labels["completion"].setText("目标达成度：未设置目标")
        else:
            labels["completion"].setText(f"目标达成度：{completion_ratio:.1%}")
        labels["total"].setText(f"总时长：{divmod(total_duration, 3600)[0]:02d}:{divmod(total_duration, 3600)[1]//60:02d}:{total_duration % 60:02d}")
        labels["efficiency"].setText(f"效率：{efficiency:.0%}")
        if compare_yesterday is None:
            compare_text = "较昨日总时长：无昨日数据"
        elif compare_yesterday > 0:
            compare_text = f"较昨日总时长：增加 {compare_yesterday} 秒"
        elif compare_yesterday < 0:
            compare_text = f"较昨日总时长：减少 {abs(compare_yesterday)} 秒"
        else:
            compare_text = "较昨日总时长：持平"
        labels["compare"].setText(compare_text)
    except Exception:
        pass


def _sidebar_today_status_worker(self, stop_event):
    while not stop_event.is_set():
        try:
            if not getattr(self, "if_logged_in", False) or not getattr(self, "current_acount", ""):
                status = None
            else:
                status = load_today_reading_status(self.current_acount)
                status["is_reading"] = bool(getattr(self, "if_reading", False))

            if hasattr(self, "main_window"):
                from .qt_helpers import run_on_ui
                run_on_ui(lambda payload=status: _apply_sidebar_today_status(self, payload))
        except Exception:
            pass

        if stop_event.wait(10):
            break


def _start_sidebar_today_status_monitor(self):
    thread = getattr(self, "_sidebar_status_thread", None)
    if thread and thread.is_alive():
        return

    _stop_sidebar_today_status_monitor(self, reset=False)
    if not getattr(self, "if_logged_in", False):
        _reset_sidebar_today_status(self)
        return
    if not hasattr(self, "main_window") or not self.main_window.isVisible():
        return

    stop_event = threading.Event()
    self._sidebar_status_stop_event = stop_event
    thread = threading.Thread(
        target=_sidebar_today_status_worker,
        args=(self, stop_event),
        daemon=True,
        name="sidebar-today-status-monitor",
    )
    self._sidebar_status_thread = thread
    thread.start()


def _stop_sidebar_today_status_monitor(self, reset=True):
    stop_event = getattr(self, "_sidebar_status_stop_event", None)
    if stop_event:
        stop_event.set()

    thread = getattr(self, "_sidebar_status_thread", None)
    if thread and thread.is_alive() and thread is not threading.current_thread():
        thread.join(timeout=0.3)

    self._sidebar_status_thread = None
    if reset:
        _reset_sidebar_today_status(self)
