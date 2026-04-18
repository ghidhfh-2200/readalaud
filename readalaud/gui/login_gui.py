"""
登录 / 注册页面 GUI。
"""

import tkinter as tk
import threading
import time


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
            self.login_status_label.config(fg=color)
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
            if hasattr(self, "main_window") and self.main_window.winfo_exists():
                self.main_window.after(0, lambda: _set_login_status(self, msg, level))
        except Exception:
            pass

    self._login_status_thread = threading.Thread(target=_worker, daemon=True)
    self._login_status_thread.start()


def _generate_login_gui(self):
    if self.if_login_show == True:
        return
    else:
        self.if_login_show = True

    self.login_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.login_frame)
    # empty the previous frame
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False
    elif self.if_settings_show == True:
        self.settings_frame.destroy()
        self.if_settings_show = False
    elif self.if_reading_show == True:
        self.reading_frame.destroy()
        self.if_reading_show = False
    self.if_login_show = True

    instruection_label = tk.Label(
        master=self.login_frame,
        text="请输入账号&密码（没有密码无需输入）\n新账号自动注册",
        font=self.font,
    )
    instruection_label.place(rely=0.4, anchor=tk.CENTER, relx=0.5)

    self.login_status_var = tk.StringVar(value="请输入账号和密码")
    self.login_status_label = tk.Label(
        master=self.login_frame,
        textvariable=self.login_status_var,
        font=("微软雅黑", 10),
        fg="#6c757d",
    )
    self.login_status_label.place(rely=0.46, anchor=tk.CENTER, relx=0.5)

    # enter username label frame
    enter_user_name = tk.LabelFrame(master=self.login_frame, padx=5, pady=5, border=0, width=50)
    enter_user_name.place(rely=0.52, relx=0.5, anchor=tk.CENTER)
    self.login_enter_acount_label = tk.Label(
        master=enter_user_name, text="用户名：", font=("微软雅黑", 14)
    )
    self.login_enter_acount_label.pack(side=tk.LEFT)
    self.login_enter_acount_name = tk.Entry(
        master=enter_user_name, width=30, font=("微软雅黑", 14), textvariable=self.login_acount_enter
    )
    self.login_enter_acount_name.pack(side=tk.RIGHT)

    # enter password label frame
    enter_password = tk.LabelFrame(master=self.login_frame, border=0, padx=5, pady=5, width=50)
    enter_password.place(anchor=tk.CENTER, relx=0.5, rely=0.59)
    self.login_enter_password_label = tk.Label(
        master=enter_password, text="密码：", font=("微软雅黑", 14)
    )
    self.login_enter_password_label.pack(side=tk.LEFT)
    self.login_enter_password_entry = tk.Entry(
        master=enter_password, width=30, font=("微软雅黑", 14), textvariable=self.login_password_enter,show="*"
    )
    self.login_enter_password_entry.pack(side=tk.RIGHT)

    # button label frame
    login_button = tk.LabelFrame(master=self.login_frame, border=0, padx=5, pady=5)
    login_button.place(relx=0.5, rely=0.66, anchor="center")
    # login_and_sign_up 定义在 auth 模块
    self.login_button = tk.Button(
        master=login_button, text="登录/注册", width=15,
        command=lambda: self.login_and_sign_up(),
    )
    self.login_button.pack(side=tk.LEFT)
    self.cancel_button = tk.Button(
        master=login_button, text="取消", width=15,
        command=lambda: self.welcome_page(destroy_window=[self.login_frame, "login"]),
    )
    self.cancel_button.pack(side=tk.RIGHT)

    self.login_frame.bind("<Destroy>", lambda _e: _stop_login_lock_countdown(self))
