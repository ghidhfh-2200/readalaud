"""
manager_window.py —— 服务器管理窗口。
"""
import sys
import subprocess
import platform
import threading
import re
from PySide6 import QtCore, QtWidgets, QtGui
from ..gui.gui_service import get_gui_service
from ..gui.qt_helpers import run_on_ui

from .process_manager import check_if_server_running, server_pid, end_server_process


# ── 按钮操作 ─────────────────────────────────────────────

def _start_server_op():
    if check_if_server_running():
        get_gui_service().info("服务器已经在运行中", title="提示")
        return
    try:
        cmd = [sys.executable, "-c", "from readalaud.server import start_socket_server; start_socket_server()"]
        creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        subprocess.Popen(cmd, creationflags=creationflags)
        get_gui_service().info("已发送启动指令，请稍候...", title="提示")
    except Exception as e:
        get_gui_service().error(f"无法启动: {e}", title="错误")


def _shutdown_server_op():
    pid = server_pid()
    if pid:
        res = end_server_process(pid=pid, force=True)
        if res == "suc":
            get_gui_service().info("服务器已关闭", title="提示")
        else:
            get_gui_service().error(f"关闭失败: {res}", title="错误")
    else:
        get_gui_service().info("服务器未运行", title="提示")


def _kill_selected_task_op(listbox):
    row = listbox.currentRow()
    if row < 0:
        get_gui_service().info("请选择一个进程", title="提示")
        return
    item = listbox.item(row).text()
    match = re.search(r"PID:\s*(\d+)", item)
    if match:
        pid = int(match.group(1))
        res = end_server_process(force=True, pid=pid)
        if res == "suc":
            get_gui_service().info(f"进程 {pid} 已结束", title="成功")
        else:
            get_gui_service().error(f"无法结束进程: {res}", title="失败")


# ── 滚动检查线程 ─────────────────────────────────────────

def _roll_check(self, event, task_list=None, pid_lbl=None):
    while not event.is_set():
        if_server_running = check_if_server_running()
        server_text = "正在运行" if if_server_running else "关闭"
        current_pid = server_pid()
        list_items = [f"PID: {current_pid} (Port 8008)"] if current_pid else []

        try:
            def update_ui(s_text=server_text, items=list_items, c_pid=current_pid):
                label = getattr(self, "state_label", None)
                if label:
                    label.setText(s_text)
                if task_list:
                    current_items = [task_list.item(i).text() for i in range(task_list.count())]
                    if list(current_items) != items:
                        task_list.clear()
                        for i in items:
                            task_list.addItem(i)
                if pid_lbl:
                    pid_text = f"进程ID: {c_pid}" if c_pid else "进程ID: -"
                    if pid_lbl.text() != pid_text:
                        pid_lbl.setText(pid_text)

            # Use the shared Qt UI dispatcher so the callback always executes on the main thread.
            run_on_ui(update_ui)
        except Exception:
            pass

        event.wait(1)


def _start_state_roll_check(self, task_list=None, pid_lbl=None):
    if getattr(self, "event", None) is not None:
        try:
            self.event.set()
        except Exception:
            pass
    self.event = threading.Event()
    self.check_thread = threading.Thread(
        target=_roll_check, daemon=True,
        args=(self, self.event, task_list, pid_lbl),
    )
    self.check_thread.start()


def _on_exit(event, root):
    event.set()
    try:
        if root is not None and hasattr(root, "close"):
            root.close()
    except Exception:
        pass
    try:
        if root is not None:
            root.deleteLater()
    except Exception:
        pass
    try:
        root.close()
    except Exception:
        pass


# ── 主窗口 ───────────────────────────────────────────────

def start_manager(self=None):
    gui = get_gui_service(self)
    if self is not None:
        server_manager_window = gui.create_toplevel(
            title="服务器管理",
            size=(300, 400),
            parent=self.main_window,
            resizable=(True, True),
            modal=False,
            center=True,
        )
    else:
        server_manager_window = QtWidgets.QWidget()
        try:
            server_manager_window.setWindowIcon(QtGui.QIcon("./assets/icon.ico"))
        except Exception:
            pass
        server_manager_window.setWindowTitle("服务器管理")
        server_manager_window.resize(300, 400)

    layout = QtWidgets.QVBoxLayout(server_manager_window)
    state_label_frame = QtWidgets.QGroupBox("服务器状态")
    state_layout = QtWidgets.QVBoxLayout(state_label_frame)
    layout.addWidget(state_label_frame)
    if self:
        self.state_label = QtWidgets.QLabel("正在查询...")
        self.state_label.setFont(QtGui.QFont("微软雅黑", 16))
        self.state_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        state_layout.addWidget(self.state_label)

    operation = QtWidgets.QGroupBox("服务器操作")
    operation_layout = QtWidgets.QVBoxLayout(operation)
    layout.addWidget(operation)
    start_btn = QtWidgets.QPushButton("启动服务器")
    start_btn.clicked.connect(_start_server_op)
    stop_btn = QtWidgets.QPushButton("关闭服务器")
    stop_btn.clicked.connect(_shutdown_server_op)
    operation_layout.addWidget(start_btn)
    operation_layout.addWidget(stop_btn)

    task_manager = QtWidgets.QGroupBox("端口占用进程管理")
    task_layout = QtWidgets.QVBoxLayout(task_manager)
    layout.addWidget(task_manager)
    task_list = QtWidgets.QListWidget()
    task_layout.addWidget(task_list)
    kill_btn = QtWidgets.QPushButton("结束选中进程")
    kill_btn.clicked.connect(lambda: _kill_selected_task_op(task_list))
    task_layout.addWidget(kill_btn)

    detail_show = QtWidgets.QWidget()
    detail_layout = QtWidgets.QVBoxLayout(detail_show)
    pid_lbl = QtWidgets.QLabel("进程ID")
    detail_layout.addWidget(pid_lbl)
    task_layout.addWidget(detail_show)

    if self:
        self.task_list = task_list
        self.pid_lbl = pid_lbl

    # 初始同步检查一次服务器状态，立刻更新 UI（避免等待后台线程首个周期）
    try:
        if_server_running = check_if_server_running()
        server_text = "正在运行" if if_server_running else "关闭"
        current_pid = server_pid()
        list_items = [f"PID: {current_pid} (Port 8008)"] if current_pid else []
        if self:
            if getattr(self, "state_label", None):
                self.state_label.setText(server_text)
        # 更新本地列表控件
        try:
            current_items = [task_list.item(i).text() for i in range(task_list.count())]
        except Exception:
            current_items = []
        if list(current_items) != list_items:
            task_list.clear()
            for i in list_items:
                task_list.addItem(i)
        if pid_lbl:
            pid_text = f"进程ID: {current_pid}" if current_pid else "进程ID: -"
            pid_lbl.setText(pid_text)
    except Exception:
        pass

    _start_state_roll_check(self=self, task_list=task_list, pid_lbl=pid_lbl)
    server_manager_window.destroyed.connect(lambda _e=None: _on_exit(self.event, server_manager_window))
    server_manager_window.show()
