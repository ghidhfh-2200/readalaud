"""
manager_window.py —— 服务器管理 Tkinter 窗口。
"""
import sys
import subprocess
import platform
import threading
import re
import tkinter as tk
from ..gui.gui_service import get_gui_service

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
    selection = listbox.curselection()
    if not selection:
        get_gui_service().info("请选择一个进程", title="提示")
        return
    item = listbox.get(selection[0])
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
                if label and label.winfo_exists():
                    label.configure(text=s_text)
                if task_list and task_list.winfo_exists():
                    current_items = task_list.get(0, tk.END)
                    if list(current_items) != items:
                        task_list.delete(0, tk.END)
                        for i in items:
                            task_list.insert(tk.END, i)
                if pid_lbl and pid_lbl.winfo_exists():
                    pid_text = f"进程ID: {c_pid}" if c_pid else "进程ID: -"
                    if pid_lbl.cget("text") != pid_text:
                        pid_lbl.configure(text=pid_text)

            label_widget = getattr(self, "state_label", None)
            if label_widget and label_widget.winfo_exists():
                label_widget.after(0, update_ui)
        except tk.TclError:
            pass

        event.wait(1)


def _start_state_roll_check(self, task_list=None, pid_lbl=None):
    self.event = threading.Event()
    self.check_thread = threading.Thread(
        target=_roll_check, daemon=True,
        args=(self, self.event, task_list, pid_lbl),
    )
    self.check_thread.start()


def _on_exit(event, root):
    event.set()
    try:
        root.destroy()
    except tk.TclError:
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
        server_manager_window = tk.Tk()
        try:
            server_manager_window.iconbitmap("./assets/icon.ico")
        except Exception:
            pass
        server_manager_window.title("服务器管理")
        server_manager_window.geometry("300x400")

    state_label_frame = tk.LabelFrame(master=server_manager_window, width=270, height=30, border=1, text="服务器状态")
    state_label_frame.pack(padx=5, pady=5, fill="x")
    if self:
        self.state_label = tk.Label(master=state_label_frame, fg="black", text="正在查询...", font=(25))
        self.state_label.pack(anchor="center", fill="both")

    operation = tk.LabelFrame(master=server_manager_window, width=270, border=1, text="服务器操作")
    operation.pack(padx=5, pady=5, fill="x")
    tk.Button(master=operation, text="启动服务器", width=260, height=1, command=_start_server_op).pack(padx=5, pady=5)
    tk.Button(master=operation, text="关闭服务器", width=260, height=1, command=_shutdown_server_op).pack(padx=5, pady=5)

    task_manager = tk.LabelFrame(master=server_manager_window, text="端口占用进程管理", width=270, border=1)
    task_manager.pack(padx=5, pady=5, fill="x")
    task_list = tk.Listbox(master=task_manager, width=260, height=6)
    task_list.pack(padx=5, pady=5, fill="x")
    tk.Button(
        master=operation, text="结束选中进程", width=260, height=1,
        command=lambda: _kill_selected_task_op(task_list),
    ).pack(padx=5, pady=5)

    detail_show = tk.LabelFrame(master=task_manager, width=260, border=0)
    detail_show.pack(padx=5, pady=5, fill="x")
    pid_lbl = tk.Label(master=detail_show, text="进程ID", width=270, height=1, justify="left", anchor="w")
    pid_lbl.pack()

    if self:
        self.task_list = task_list
        self.pid_lbl = pid_lbl

    _start_state_roll_check(self=self, task_list=task_list, pid_lbl=pid_lbl)
    server_manager_window.protocol("WM_DELETE_WINDOW", lambda: _on_exit(self.event, server_manager_window))
    server_manager_window.mainloop()
