"""
登录 / 注册页面 GUI。
"""

import tkinter as tk


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

    # enter username label frame
    enter_user_name = tk.LabelFrame(master=self.login_frame, padx=5, pady=5, border=0, width=50)
    enter_user_name.place(rely=0.5, relx=0.5, anchor=tk.CENTER)
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
    enter_password.place(anchor=tk.CENTER, relx=0.5, rely=0.57)
    self.login_enter_password_label = tk.Label(
        master=enter_password, text="密码：", font=("微软雅黑", 14)
    )
    self.login_enter_password_label.pack(side=tk.LEFT)
    self.login_enter_password_entry = tk.Entry(
        master=enter_password, width=30, font=("微软雅黑", 14), textvariable=self.login_password_enter
    )
    self.login_enter_password_entry.pack(side=tk.RIGHT)

    # button label frame
    login_button = tk.LabelFrame(master=self.login_frame, border=0, padx=5, pady=5)
    login_button.place(relx=0.5, rely=0.64, anchor="center")
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
