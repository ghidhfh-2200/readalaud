"""
主窗口创建、欢迎页面、窗口切换导航。
"""

import tkinter as tk
import base64
import threading
from ..calibration import start_calibration
from ..server import check_if_server_running, server_pid, end_server_process, start_manager
from ..reading.data_io import load_today_reading_status


# ──────────────────────── 主窗口 ────────────────────────

def _generate_main_window(self):
    self.main_window = tk.Tk()
    self._sidebar_status_stop_event = threading.Event()
    self._sidebar_status_thread = None
    try:
        self.main_window.iconbitmap("./assets/icon.ico")
    except Exception:
        pass
    # create StringVar instances after the root exists
    if getattr(self, 'login_password_enter', None) is None:
        self.login_password_enter = tk.StringVar()
    if getattr(self, 'login_acount_enter', None) is None:
        self.login_acount_enter = tk.StringVar()
    self.content = ""
    self.main_window.geometry("800x600")
    self.main_window.title("ReadAlaud——告别摸鱼偷懒，回归大声早读！")
    self.gui.set_theme("darkly")
    # create a horizontal PanedWindow
    self.main_paned_window = tk.PanedWindow(
        self.main_window, orient=tk.HORIZONTAL, showhandle=True, sashrelief="sunken"
    )
    self.main_paned_window.pack(fill=tk.BOTH, expand=True)
    # button frame
    button_frame = tk.Frame(self.main_paned_window, width=300, height=600)
    self.main_paned_window.add(button_frame)
    # content frame
    self.content_frame = tk.Frame(self.main_paned_window, width=600, height=600)
    self.main_paned_window.add(self.content_frame)

    title = tk.Label(
        self.content_frame,
        text="ReadAlaud\n告别摸鱼偷懒,回归大声早读！",
        font=self.font,
    )
    title.pack(expand=True, fill=tk.BOTH)
    self.if_main_window_show = True
    # buttons
    login_button = tk.Button(
        master=button_frame,
        text="登录（自动注册）",
        command=lambda: self.generate_login_gui(),
    )
    login_button.pack(fill=tk.BOTH)
    self.current_account_label = tk.Label(
        master=button_frame, text="当前登录：(未登录)", font=("微软雅黑", 12)
    )
    self.current_account_label.pack(fill=tk.BOTH)

    sidebar_status_frame = tk.LabelFrame(
        master=button_frame,
        text="今日朗读状态",
        padx=6,
        pady=6,
    )
    sidebar_status_frame.pack(fill=tk.BOTH, expand=False, padx=4, pady=(6, 4))

    self.sidebar_status_labels = {
        "state": tk.Label(sidebar_status_frame, text="是否朗读：--", anchor="w", justify="left", wraplength=180),
        "completion": tk.Label(sidebar_status_frame, text="目标达成度：--", anchor="w", justify="left", wraplength=180),
        "total": tk.Label(sidebar_status_frame, text="总时长：--:--:--", anchor="w", justify="left", wraplength=180),
        "efficiency": tk.Label(sidebar_status_frame, text="效率：--", anchor="w", justify="left", wraplength=180),
        "compare": tk.Label(sidebar_status_frame, text="较昨日总时长：--", anchor="w", justify="left", wraplength=180),
    }
    for key in ["state", "completion", "total", "efficiency", "compare"]:
        self.sidebar_status_labels[key].pack(fill=tk.BOTH, anchor="w", pady=1)
    _reset_sidebar_today_status(self)

    self.main_window.protocol("WM_DELETE_WINDOW", lambda: check_if_reading(self))
    self.main_window.mainloop()


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
                self.main_window.destroy()
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
                self.main_window.destroy()
            elif action is False:
                # 保留服务器并退出
                self.main_window.destroy()
            # action is None (取消): 不做任何事
        else:
            if_exit = self.gui.ask_yes_no(title="确定要关闭吗？", message="确认要关闭吗?")
            if if_exit:
                self.main_window.destroy()


# ──────────────────────── 欢迎页 / 导航 ────────────────────────

def _welcome_page(self, destroy_window):
    destroy_window[0].destroy()
    if destroy_window[1] == "login":
        self.if_login_show = False
    elif destroy_window[1] == "settings":
        self.if_settings_show = False
    elif destroy_window[1] == "reading":
        self.if_reading_show = False
    elif destroy_window[1] == "data_form":
        self.if_data_form_show = False
    self.if_main_window_show = True
    self.content_frame = tk.Frame(self.main_paned_window, width=600, height=600)
    self.main_paned_window.add(self.content_frame)
    main_label_frame = tk.LabelFrame(master=self.content_frame, border=0, padx=5, pady=5)
    main_label_frame.place(anchor=tk.CENTER, relx=0.5, rely=0.5)
    title = tk.Label(
        main_label_frame,
        text="ReadAlaud\n告别摸鱼偷懒,回归大声早读！",
        font=self.font,
    )
    title.pack(expand=True, fill=tk.BOTH)
    if self.if_logged_in == False and self.gui.get_theme() != "darkly":
        self.gui.set_theme("darkly")
    if self.if_logged_in == True:
        try:
            self.current_account_label.config(
                text=f"当前登录：{base64.urlsafe_b64decode(self.current_acount).decode('utf-8')}"
            )
        except Exception:
            self.current_account_label.config(text="当前登录：(已登录)")
        settings_button = tk.Button(
            master=main_label_frame,
            text="设置",
            font=self.mainpage_button_font,
            command=lambda: self.generate_settings_gui(),
        )
        settings_button.pack(fill=tk.BOTH, expand=1, pady=5)
        read_button = tk.Button(
            master=main_label_frame,
            text="开始朗读",
            font=self.mainpage_button_font,
            command=lambda: self.generate_reading_gui(),
        )
        read_button.pack(fill=tk.BOTH, expand=1, pady=5)
        calibration_button = tk.Button(
            master=main_label_frame,
            text="麦克风校准",
            font=self.mainpage_button_font,
            command=lambda: start_calibration(self),
        )
        calibration_button.pack(fill=tk.BOTH, expand=1, pady=5)
        data_button = tk.Button(
            master=main_label_frame,
            text="朗读数据",
            font=self.mainpage_button_font,
            command=lambda: self.generate_data_gui(),
        )
        data_button.pack(fill=tk.BOTH, expand=1, pady=5)
        server_manager_btn = tk.Button(
            master=main_label_frame,
            text="服务器管理",
            font=self.mainpage_button_font,
            command=lambda: start_manager(self),
        )
        server_manager_btn.pack(fill=tk.BOTH, expand=1, pady=1)

        _start_sidebar_today_status_monitor(self)


def _reset_sidebar_today_status(self):
    labels = getattr(self, "sidebar_status_labels", None)
    if not labels:
        return
    try:
        labels["state"].config(text="是否朗读：--")
        labels["completion"].config(text="目标达成度：--")
        labels["total"].config(text="总时长：--:--:--")
        labels["efficiency"].config(text="效率：--")
        labels["compare"].config(text="较昨日总时长：--")
    except Exception:
        pass


def _apply_sidebar_today_status(self, status):
    labels = getattr(self, "sidebar_status_labels", None)
    if not labels:
        return
    try:
        if not status:
            _reset_sidebar_today_status(self)
            labels["state"].config(text="是否朗读：未登录")
            return

        total_duration = int(status.get("total_duration", 0) or 0)
        efficiency = float(status.get("efficiency", 0.0) or 0.0)
        completion_ratio = status.get("completion_ratio")
        compare_yesterday = status.get("compare_yesterday")

        labels['state'].config(text=f"是否朗读: {'已朗读' if total_duration > 0 else '未朗读'}")
        if completion_ratio is None:
            labels["completion"].config(text="目标达成度：未设置目标")
        else:
            labels["completion"].config(text=f"目标达成度：{completion_ratio:.1%}")
        labels["total"].config(text=f"总时长：{divmod(total_duration, 3600)[0]:02d}:{divmod(total_duration, 3600)[1]//60:02d}:{total_duration % 60:02d}")
        labels["efficiency"].config(text=f"效率：{efficiency:.0%}")
        if compare_yesterday is None:
            compare_text = "较昨日总时长：无昨日数据"
        elif compare_yesterday > 0:
            compare_text = f"较昨日总时长：增加 {compare_yesterday} 秒"
        elif compare_yesterday < 0:
            compare_text = f"较昨日总时长：减少 {abs(compare_yesterday)} 秒"
        else:
            compare_text = "较昨日总时长：持平"
        labels["compare"].config(text=compare_text)
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

            if hasattr(self, "main_window") and self.main_window.winfo_exists():
                self.main_window.after(0, lambda payload=status: _apply_sidebar_today_status(self, payload))
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
    if not hasattr(self, "main_window") or not self.main_window.winfo_exists():
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
