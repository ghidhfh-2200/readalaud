"""
主窗口创建、欢迎页面、窗口切换导航。
"""

import tkinter as tk
from tkinter import messagebox
import base64
import ttkbootstrap as ttkbs
from .. import calibration, server_manager


# ──────────────────────── 主窗口 ────────────────────────

def _generate_main_window(self):
    self.main_window = tk.Tk()
    # create StringVar instances after the root exists
    if getattr(self, 'login_password_enter', None) is None:
        self.login_password_enter = tk.StringVar()
    if getattr(self, 'login_acount_enter', None) is None:
        self.login_acount_enter = tk.StringVar()
    self.content = ""
    self.main_window.geometry("800x600")
    self.main_window.title("ReadAlaud——告别摸鱼偷懒，回归大声早读！")
    ttkbs.Style().theme_use(themename="darkly")
    # create a horizontal PanedWindow
    self.main_paned_window = tk.PanedWindow(
        self.main_window, orient=tk.HORIZONTAL, showhandle=True, sashrelief="sunken"
    )
    self.main_paned_window.pack(fill=tk.BOTH, expand=True)
    # button frame
    button_frame = tk.Frame(self.main_paned_window, width=200, height=600)
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
    self.main_window.protocol("WM_DELETE_WINDOW", lambda: check_if_reading(self))
    self.main_window.mainloop()


# ──────────────────────── 关闭确认 ────────────────────────

def check_if_reading(self):
    if self.if_reading:
        # 双重检查：确认服务器确实还在运行
        server_running = server_manager.check_if_server_running()
        if server_running:
            messagebox.showinfo(title="无法关闭", message="当前正在朗读，请结束朗读后再关闭主窗口！")
        else:
            # 服务器已经不在运行，重置朗读状态
            self.if_reading = False
            if_exit = messagebox.askyesno(title="确定要关闭吗？", message="朗读服务器已停止。确认要关闭吗?")
            if if_exit:
                self.main_window.destroy()
    else:
        # 检查服务器是否仍在后台运行
        server_running = server_manager.check_if_server_running()
        if server_running:
            action = messagebox.askyesnocancel(
                title="服务器仍在运行",
                message="检测到朗读服务器仍在后台运行。\n\n是 - 关闭服务器并退出\n否 - 保留服务器并退出\n取消 - 返回"
            )
            if action is True:
                # 关闭服务器并退出
                pid = server_manager.server_pid()
                if pid:
                    server_manager.end_server_process(pid=pid, force=True)
                self.main_window.destroy()
            elif action is False:
                # 保留服务器并退出
                self.main_window.destroy()
            # action is None (取消): 不做任何事
        else:
            if_exit = messagebox.askyesno(title="确定要关闭吗？", message="确认要关闭吗?")
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
    if self.if_logged_in == False and ttkbs.Style().theme_use() != "darkly":
        ttkbs.Style().theme_use("darkly")
    if self.if_logged_in == True:
        try:
            self.current_account_label.config(
                text=f"当前登录：{base64.b64decode(self.current_acount).decode('utf-8')}"
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
            command=lambda: calibration.start_calibration(self),
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
            command=lambda: server_manager.start_manager(self),
        )
        server_manager_btn.pack(fill=tk.BOTH, expand=1, pady=1)
