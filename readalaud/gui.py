import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import base64
import asyncio
import pyttsx3
import ttkbootstrap as ttkbs
from markdown import markdown
from tkhtmlview import HTMLLabel
from . import settings,tts,reading,calibration,server_manager

def bind_gui(instance):
    """把 GUI 相关的方法绑定到 ReadAlaud 实例上。"""
    instance.generate_main_window = lambda: _generate_main_window(instance)
    instance.welcome_page = lambda destroy_window: _welcome_page(instance, destroy_window)
    instance.generate_login_gui = lambda: _generate_login_gui(instance)
    instance.generate_settings_gui = lambda: _generate_settings_gui(instance)
    instance.generate_reading_gui = lambda: _generate_reading_gui(instance)
    instance.enable_or_disable_tts_gui = lambda state=None: _enable_or_disable_tts_gui(instance, state)
    instance.get_web_voice = lambda: _get_web_voice(instance)
    instance.generate_more_vloices_window = lambda source: _generate_more_vloices_window(instance, source)
    instance.destroy_all_voices_window = lambda window: _destroy_all_voices_window(instance, window)
    instance.tts_add_point = lambda: _tts_add_point(instance)
    instance.tts_delete_point = lambda: _tts_delete_point(instance)
    instance.pop_up_time_and_text_config_window = lambda: _pop_up_time_and_text_config_window(instance)


def _generate_main_window(self):
    self.main_window = tk.Tk()
    # create StringVar instances after the root exists
    if getattr(self, 'login_password_enter', None) is None:
        self.login_password_enter = tk.StringVar()
    if getattr(self, 'login_acount_enter', None) is None:
        self.login_acount_enter = tk.StringVar()
    self.main_window.geometry("800x600")
    self.main_window.title("ReadAlaud——告别摸鱼偷懒，回归大声早读！")
    ttkbs.Style().theme_use(themename="darkly")
    #create a horizontal PanedWindow
    self.main_paned_window = tk.PanedWindow(self.main_window, orient=tk.HORIZONTAL, showhandle=True,sashrelief="sunken")
    self.main_paned_window.pack(fill=tk.BOTH, expand=True)
    # button frame
    button_frame = tk.Frame(self.main_paned_window, width=200, height=600)
    self.main_paned_window.add(button_frame)
    # content frame
    self.content_frame = tk.Frame(self.main_paned_window, width=600, height=600)
    self.main_paned_window.add(self.content_frame)

    title = tk.Label(self.content_frame, text="ReadAlaud\n告别摸鱼偷懒,回归大声早读！", font=self.font)
    title.pack(expand=True, fill=tk.BOTH)
    self.if_main_window_show = True
    #buttons
    login_button = tk.Button(master=button_frame, text="登录（自动注册）", command=lambda:_generate_login_gui(self))
    login_button.pack(fill=tk.BOTH)
    self.current_account_label = tk.Label(master=button_frame, text="当前登录：(未登录)", font=("微软雅黑", 12))
    self.current_account_label.pack(fill=tk.BOTH)
    self.main_window.protocol("WM_DELETE_WINDOW", lambda: check_if_reading(self))
    self.main_window.mainloop()

def check_if_reading(self):
    if self.if_reading == True:
        messagebox.showinfo(title="无法关闭", message="当前正在朗读，请结束朗读后再关闭主窗口！")
    else:
        if_exit = messagebox.askyesno(title="确定要关闭吗？", message="确认要关闭吗?")
        if if_exit == True:
            self.main_window.destroy()
        else:
            pass

def _welcome_page(self, destroy_window):
    destroy_window[0].destroy()
    if destroy_window[1] == "login":
        self.if_login_show = False
    elif destroy_window[1] == "settings":
        self.if_settings_show = False
    elif destroy_window[1] == "reading":
        self.if_reading_show = False
    self.if_main_window_show = True
    self.content_frame = tk.Frame(self.main_paned_window, width=600, height=600)
    self.main_paned_window.add(self.content_frame)
    main_label_frame = tk.LabelFrame(master=self.content_frame, border=0, padx=5, pady=5)
    main_label_frame.place(anchor=tk.CENTER, relx=0.5, rely=0.5)
    title = tk.Label(main_label_frame, text="ReadAlaud\n告别摸鱼偷懒,回归大声早读！", font=self.font)
    title.pack(expand=True, fill=tk.BOTH)
    if self.if_logged_in == False and ttkbs.Style().theme_use() != "darkly":
        ttkbs.Style().theme_use("darkly")
    if self.if_logged_in == True:
        try:
            self.current_account_label.config(text=f"当前登录：{base64.b64decode(self.current_acount).decode('utf-8')}")
        except Exception:
            self.current_account_label.config(text="当前登录：(已登录)")
        settings_button = tk.Button(master=main_label_frame, text="设置",font=self.mainpage_button_font, command=lambda: self.generate_settings_gui())
        settings_button.pack(fill=tk.BOTH, expand=1, pady=5)
        read_button = tk.Button(master=main_label_frame, text="开始朗读",font=self.mainpage_button_font, command=lambda: self.generate_reading_gui())
        read_button.pack(fill=tk.BOTH, expand=1, pady=5)
        calibration_button = tk.Button(master=main_label_frame, text="麦克风校准",font=self.mainpage_button_font,command=lambda: calibration.start_calibration(self))
        calibration_button.pack(fill=tk.BOTH, expand=1, pady=5)
        data_button = tk.Button(master=main_label_frame, text="朗读数据",font=self.mainpage_button_font)
        data_button.pack(fill=tk.BOTH, expand=1, pady=5)
        server_manager_btn = tk.Button(master=main_label_frame,text="服务器管理", font=self.mainpage_button_font, command=lambda:server_manager.start_manager(self))
        server_manager_btn.pack(fill=tk.BOTH, expand=1,pady=1)


def _generate_login_gui(self):
    if self.if_login_show == True:
        return
    else:
        self.if_login_show = True

    self.login_frame = tk.Frame(master=self.main_window,)
    self.main_paned_window.add(self.login_frame)
    #enpty the previous frame
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
    
    instruection_label = tk.Label(master= self.login_frame, text="请输入账号&密码（没有密码无需输入）\n新账号自动注册", font=self.font)
    instruection_label.place(rely=0.4, anchor=tk.CENTER, relx=0.5)

    #enter username label frame
    enter_user_name = tk.LabelFrame(master=self.login_frame, padx=5, pady=5, border=0, width=50)
    enter_user_name.place(rely=0.5, relx=0.5, anchor=tk.CENTER)
    self.login_enter_acount_label = tk.Label(master=enter_user_name, text="用户名：", font=("微软雅黑", 14))
    self.login_enter_acount_label.pack(side=tk.LEFT)
    self.login_enter_acount_name = tk.Entry(master=enter_user_name, width=30, font=("微软雅黑", 14), textvariable=self.login_acount_enter)
    self.login_enter_acount_name.pack(side=tk.RIGHT)

    #enter password label frame
    enter_password = tk.LabelFrame(master=self.login_frame, border=0, padx=5, pady=5, width=50)
    enter_password.place(anchor=tk.CENTER, relx=0.5, rely=0.57)
    self.login_enter_password_label = tk.Label(master=enter_password, text="密码：", font=("微软雅黑", 14))
    self.login_enter_password_label.pack(side=tk.LEFT)
    self.login_enter_password_entry = tk.Entry(master=enter_password, width=30, font=("微软雅黑", 14), textvariable=self.login_password_enter)
    self.login_enter_password_entry.pack(side=tk.RIGHT)

    #button label frame
    login_button = tk.LabelFrame(master=self.login_frame, border=0, padx=5, pady=5)
    login_button.place(relx=0.5, rely=0.64,anchor="center")
    # login_and_sign_up 定义在 auth 模块
    self.login_button = tk.Button(master=login_button, text="登录/注册", width=15, command=lambda: self.login_and_sign_up())
    self.login_button.pack(side=tk.LEFT)
    self.cancel_button = tk.Button(master=login_button, text="取消", width=15, command=lambda: _welcome_page(destroy_window=[self.login_frame, "login"]))
    self.cancel_button.pack(side=tk.RIGHT)


def _generate_settings_gui(self):
    #The frame for the settings
    if self.if_settings_show == True:
        return
    else:
        self.if_settings_show = True
    #main frame
    self.settings_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.settings_frame)
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False
    #notbooks
    notebook = ttk.Notebook(master=self.settings_frame,)
    account_frame = tk.Frame(notebook,)
    read_frame = tk.Frame(notebook)
    questions_and_answers_frame = tk.Frame(notebook)
    customize_frame = tk.Frame(notebook)
    notebook.add(child=read_frame, text="朗读设置")
    notebook.add(child=questions_and_answers_frame, text="疑难解答")
    notebook.add(child=account_frame, text="账号与安全")
    notebook.add(child=customize_frame, text="个性化")
    notebook.pack(fill="both", expand=1)

    #Q&A frame
    markdown_text = markdown("""
### 语音提示说明
- 当前仅支持本地 TTS（pyttsx3）
- 无需下载模型、无网络依赖
""")
    why_dbFS_label = HTMLLabel(master=questions_and_answers_frame, html=markdown_text)
    why_dbFS_label.pack(fill="x", padx=5, pady=5)
    #account frame
    account_management_label_frame = tk.LabelFrame(
        master=account_frame,
        padx=5,
        pady=5,
        font=self.mainpage_button_font,
        text="账户管理"
    )
    account_management_label_frame.pack(side="top", fill="x", expand=False, anchor="n")
    name_lf = tk.LabelFrame(master=account_management_label_frame, border=0, font=self.mainpage_button_font)
    name_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.account_name_label = tk.Label(master=name_lf, text="账户名称: ", font=("微软雅黑", 17))
    self.account_name_label.pack(side=tk.LEFT)
    self.settings_name_value = tk.StringVar()
    name_entry = tk.Entry(master=name_lf, width=30, textvariable=self.settings_name_value, font=("微软雅黑", 17))
    name_entry.pack(side=tk.LEFT)
    account_ok_button = tk.Button(master=name_lf, text="确定", font=self.mainpage_button_font, width=10, command=lambda: self.save_settings_except_tts("account"))
    account_ok_button.pack(side="right")

    password_lf = tk.LabelFrame(master=account_management_label_frame, border=0, font=self.mainpage_button_font)
    password_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.account_password_label = tk.Label(master=password_lf, text="密码设置：", font=("微软雅黑", 17))
    self.account_password_label.pack(side=tk.LEFT)
    self.settings_password_value = tk.StringVar()
    password_entry = tk.Entry(master=password_lf, width=30, textvariable=self.settings_password_value, font=("微软雅黑", 17))
    password_entry.pack(side=tk.LEFT)
    account_password_ok_button = tk.Button(master=password_lf, text="确定", font=self.mainpage_button_font, width=10, 
                                           command=lambda: self.save_settings_except_tts(option="password"))
    account_password_ok_button.pack(side="right")

    account_operation = tk.LabelFrame(master=account_frame, padx=5, pady=5, font=self.mainpage_button_font, text="账户操作")
    account_operation.pack(side="top", fill="x", expand=False, anchor="n")
    delete_acount = tk.Button(account_operation, text="注销账号", fg="red", font=self.mainpage_button_font, width=20, command=lambda: self.delete_the_account())
    delete_acount.pack(side="left", padx=5)
    reset_acount = tk.Button(account_operation, text="重置全部数据", fg="red", font=self.mainpage_button_font, width=20, command=lambda: self.reset_account_data())
    reset_acount.pack(side="left", padx=5)
    delete_acount = tk.Button(account_operation, text="退出登录", fg="black", font=self.mainpage_button_font, width=20, command=lambda: self.logout())
    delete_acount.pack(side="left", padx=5)

    read_basic_settings_labelframe = tk.LabelFrame(master=read_frame, padx=5, pady=5, font=self.mainpage_button_font, text="基础设置")
    read_basic_settings_labelframe.pack(side="top", fill="x", expand=False, anchor="n")
    goal_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0, font=self.mainpage_button_font, )
    goal_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.settings_goal_label = tk.Label(master=goal_lf, text="目标设定:", font=("微软雅黑", 17))
    self.settings_goal_label.pack(side="left")
    self.settings_goal_value = tk.IntVar()
    goal_entry = tk.Entry(master=goal_lf, textvariable=self.settings_goal_value, width=30, font=("微软雅黑", 17))
    goal_entry.pack(side="left")
    goal_ok_button = tk.Button(master=goal_lf, text="确定", width=10, font=self.mainpage_button_font, command=lambda: self.save_settings_except_tts("goal"))
    goal_ok_button.pack(side="right")

    stop_dur_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0)
    stop_dur_lf.pack(side="top", padx=5, pady=5, expand=False, anchor="n", fill="x")
    self.stop_dur_label = tk.Label(master=stop_dur_lf,  text="停顿容忍间隔(秒):", font=("微软雅黑", 17))
    self.stop_dur_label.pack(side="left")
    self.settings_stop_dur_value = tk.DoubleVar()
    stop_dur_entry = tk.Entry(master=stop_dur_lf, width=30, font=("微软雅黑", 17), textvariable=self.settings_stop_dur_value)
    stop_dur_entry.pack(side="left")
    stop_dur_button = tk.Button(master=stop_dur_lf, text="确定", font=self.mainpage_button_font, width=10, command=lambda: self.save_settings_except_tts("stop_dur"))
    stop_dur_button.pack(side="right")

    db_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0)
    db_lf.pack(side="top", padx=5, pady=5, expand=False, anchor="n", fill="x")
    self.settings_db_label = tk.Label(master=db_lf, text="分贝阈值(dB):", font=("微软雅黑", 17))
    self.settings_db_label.pack(side="left")
    self.settings_db_value = tk.DoubleVar()
    db_entry = tk.Entry(master=db_lf, width=30, font=("微软雅黑", 17), textvariable=self.settings_db_value)
    db_entry.pack(side="left")
    db_ok_button = tk.Button(master=db_lf, text="确定", font=self.mainpage_button_font, width=10, command=lambda: self.save_settings_except_tts("db_level"))
    db_ok_button.pack(side="right")

    read_settings_frame = tk.LabelFrame(master=read_frame, text="语音提示设置", padx=5,font=self.mainpage_button_font)
    read_settings_frame.pack(side="top", fill="x", expand=False, anchor="n")
    checkbox_frame = tk.Frame(read_settings_frame)
    checkbox_frame.pack(fill="x")
    self.if_tts_enabled = tk.BooleanVar()
    self.if_tts_checkbox = tk.Checkbutton(checkbox_frame, text="启用语音提示", variable=self.if_tts_enabled, font=self.mainpage_button_font, command=lambda:self.enable_or_disable_tts_gui())
    self.if_tts_checkbox.pack(side="left", padx=5)

    # TTS settings container
    self.settings_container = tk.Frame(read_settings_frame)
    self.settings_container.pack(fill="both", expand=True, padx=5)

    # Create Treeview frame
    table_frame = tk.Frame(self.settings_container)
    table_frame.pack(fill="both", expand=True)

    # Scrollbar
    tree_scroll = ttk.Scrollbar(table_frame)
    tree_scroll.pack(side="right", fill="y")

    # Treeview 
    columns = ("time","content", "volume", "speed", "voice", "from")
    self.tts_tree = ttk.Treeview(table_frame, columns=columns, show="headings", 
                yscrollcommand=tree_scroll.set, height=5)
    self.tts_tree.bind("<<TreeviewSelect>>", lambda event: on_treeview_click(self, event,self.tts_tree.item(self.tts_tree.selection()[0], "values")))
    # Configure columns
    self.tts_tree.heading("time", text="触发条件")
    self.tts_tree.heading("content", text="语音内容")
    self.tts_tree.heading("volume", text="音量")
    self.tts_tree.heading("speed", text="语速")
    self.tts_tree.heading("voice", text="音色")
    self.tts_tree.heading("from", text="来源")

    # Set column widths
    self.tts_tree.column("time", width=80)
    self.tts_tree.column("content", width=200)
    self.tts_tree.column("volume", width=80)
    self.tts_tree.column("speed", width=80)
    self.tts_tree.column("voice", width=100)
    self.tts_tree.column("from", width=20)

    self.tts_tree.pack(fill="both", expand=True)
    tree_scroll.config(command=self.tts_tree.yview)

    # Buttons frame
    button_frame = tk.Frame(self.settings_container)
    button_frame.pack(fill="x")
    
    self.add_button = tk.Button(button_frame, text="添加时间点", 
                          font=self.mainpage_button_font, command=lambda: self.tts_add_point())
    self.add_button.pack(side="left", padx=5)
    
    self.delete_button = tk.Button(button_frame, text="删除时间点", 
                             font=self.mainpage_button_font, command=lambda: self.tts_delete_point())
    self.delete_button.pack(side="left", padx=5)

    self.time_and_text_button = tk.Button(button_frame, text="时间点&语音内容", font=self.mainpage_button_font,
                                          command=lambda: self.pop_up_time_and_text_config_window())
    self.time_and_text_button.pack(side="left", padx=5)
    # Voice configuration frame
    voice_config_frame = tk.LabelFrame(self.settings_container, text="语音配置",
                                         font=self.mainpage_button_font)
    voice_config_frame.pack(fill="x")

    # Voice options
    voices_frame = tk.Frame(voice_config_frame)
    voices_frame.pack(fill="x")
    
    tk.Label(voices_frame, text="选择音色:", 
            font=self.mainpage_button_font).pack(side="left", padx=5)
    self.voice_var = tk.StringVar()
    self.voice_menu = ttk.Label(voices_frame, text="未选择", textvariable=self.voice_var,
                                 font=self.mainpage_button_font)
    self.voice_menu.pack(side="left", padx=5, fill="x", expand=True)
    self.more_local_button = tk.Button(voices_frame, text="更多(本地)", font=self.mainpage_button_font, command=lambda: self.generate_more_vloices_window("local"))
    self.more_local_button.pack(side="right", padx=5)
    self.more_web_button = tk.Button(voices_frame, text="更多(网络)", font=self.mainpage_button_font, command=lambda: self.generate_more_vloices_window("web"))
    self.more_web_button.pack(side="right", padx=5)
    # Volume control
    volume_frame = tk.Frame(voice_config_frame)
    volume_frame.pack(fill="x")
    
    tk.Label(volume_frame, text="音量:", 
            font=self.mainpage_button_font).pack(side="left")
    self.volume_var = tk.DoubleVar(value=1.0)
    self.volume_scale = tk.Scale(volume_frame, from_=-1.0, to=1.0, 
                          variable=self.volume_var, orient="horizontal",
                          resolution=0.1,
                          font=self.mainpage_button_font)
    self.volume_scale.pack(side="left", fill="x", expand=True)
    # Use the standard Tkinter event string '<ButtonRelease-1>' (not a virtual event like <<...>>)
    # and call the module-level handler with the instance and event.
    self.volume_scale.bind("<ButtonRelease-1>", lambda event: volume_scale_change(self, event))

    # Speed control
    speed_frame = tk.Frame(voice_config_frame)
    speed_frame.pack(fill="x")
    
    tk.Label(speed_frame, text="语速:", 
            font=self.mainpage_button_font).pack(side="left")
    self.speed_var = tk.DoubleVar(value=1.0)
    self.speed_scale = tk.Scale(speed_frame, from_=-1.0, to=1.0, 
                         variable=self.speed_var, orient="horizontal",
                         resolution=0.1,
                         font=self.mainpage_button_font,)
    self.speed_scale.pack(side="left", fill="x", expand=True)
    # Same fix for speed scale: use '<ButtonRelease-1>' and call the module-level handler.
    self.speed_scale.bind("<ButtonRelease-1>", lambda event: speed_scale_change(self, event))

    # Save button
    buttons_frame = tk.LabelFrame(self.settings_container, border=0)
    buttons_frame.pack(fill="x")
    self.test_button = tk.Button(buttons_frame, text="测试语音",font=self.mainpage_button_font, command=lambda: test_tts(self))
    self.test_button.pack(side="right", padx=5)
    self.tts_save_button = tk.Button(buttons_frame, text="保存设置", 
                          font=self.mainpage_button_font,command=lambda:save_tts_setting(self))
    self.tts_save_button.pack(side="right")

    #customize frame
    self.get_style_list = ttkbs.Style().theme_names()
    customize_label_frame = tk.LabelFrame(master=customize_frame, padx=5, pady=5, text="选择样式", font=self.mainpage_button_font)
    customize_label_frame.pack(side="top", fill="x")
    self.customize_listbox = tk.Listbox(master=customize_label_frame,width=20)
    self.customize_listbox.pack(side="top", fill="x")
    for i in self.get_style_list:
        self.customize_listbox.insert(tk.END, i)
    customize_ok_button = tk.Button(master=customize_label_frame, text="确认", width=10)
    customize_ok_button.pack(side="bottom", fill="x")
    customize_ok_button.config(command=self.change_theme)

    back_button = tk.Button(master=self.settings_frame, text="返回", font=self.mainpage_button_font, width=10
                                ,command=lambda: self.welcome_page(destroy_window=[self.settings_frame, "settings"]))
    back_button.pack(side="right")
    settings._load_settings(self=self)


def _enable_or_disable_tts_gui(self, state=None):
    if state == None:
        if self.if_tts_enabled.get() == False:
            self.add_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.time_and_text_button.config(state="disabled")
            self.voice_menu.config(state="disabled")
            self.volume_scale.config(state="disabled")
            self.speed_scale.config(state="disabled")
            self.more_local_button.config(state="disabled")
            self.more_web_button.config(state="disabled")
        else:
            self.add_button.config(state="active")
            self.delete_button.config(state="active")
            self.time_and_text_button.config(state="active")
            self.voice_menu.config(state="readinly")
            self.volume_scale.config(state="active")
            self.speed_scale.config(state="active")
            self.more_web_button.config(state="active")
            self.more_local_button.config(state="active")
    else:
        if state == False:
            self.if_tts_enabled.set(False)
            self.add_button.config(state="disabled")
            self.delete_button.config(state="disabled")
            self.time_and_text_button.config(state="disabled")
            self.voice_menu.config(state="disabled")
            self.volume_scale.config(state="disabled")
            self.speed_scale.config(state="disabled")
            self.more_local_button.config(state="disabled")
            self.more_web_button.config(state="disabled")
        else:
            self.if_tts_enabled.set(True)
            self.add_button.config(state="active")
            self.delete_button.config(state="active")
            self.time_and_text_button.config(state="active")
            self.voice_menu.config(state="readonly")
            self.volume_scale.config(state="active")
            self.speed_scale.config(state="active")
            self.more_web_button.config(state="active")
            self.more_local_button.config(state="active")


async def _get_web_voice(self):
    # Use the built-in, stable Baidu voice presets
    return tts.get_web_voices()


def _generate_more_vloices_window(self, source):
    """
    生成更多音色窗口
    """
    if self.if_all_voices_window_showed == True:
        return
    self.if_all_voices_window_showed = True
    self.more_voices_window = tk.Toplevel(self.main_window)
    self.more_voices_window.title("更多音色")
    self.more_voices_window.geometry("460x300")
    self.more_voices_window.resizable(0, 0)

    table_frame = tk.LabelFrame(master=self.more_voices_window, border=0)
    table_frame.pack(fill="x", expand=True, side="top", padx=5)
    tree_scroll = ttk.Scrollbar(table_frame)
    tree_scroll.pack(side="right", fill="y")
    voice_columns = ("name", "gender", "language", "personalities")
    self.voice_listbox = ttk.Treeview(master=table_frame, columns=voice_columns, show="headings", height=8, yscrollcommand=tree_scroll.set)
    self.voice_listbox.heading("name", text="名称")
    self.voice_listbox.heading("gender", text="性别")
    self.voice_listbox.heading("language", text="语言")
    self.voice_listbox.heading("personalities", text="特征")

    self.voice_listbox.column("name", width=100)
    self.voice_listbox.column("gender", width=50)
    self.voice_listbox.column("language", width=100)
    self.voice_listbox.column("personalities", width=200)
    
    tree_scroll.config(command=self.voice_listbox.yview)

    self.voice_listbox.pack(fill="x", expand=True, side="top", padx=5)
    if source == "web":
        if self.all_web_voices == None:
            try:
                loop = asyncio.get_event_loop()
                voices = loop.run_until_complete(_get_web_voice(self))
                self.all_web_voices = voices
            except Exception:
                messagebox.showerror(message="获取音色失败！\n当前仅支持本地 TTS（pyttsx3），请选用本地音色。")
                self.all_web_voices = None
                return
        for voice in self.all_web_voices:
            self.voice_listbox.insert("", tk.END, values=(voice["ShortName"], voice['Gender'], voice['Locale'], voice['VoiceTag']['VoicePersonalities']))
    elif source == "local":
        if self.all_local_voices == None:
            self.pyttsx3_engine = pyttsx3.init()
            self.all_local_voices = self.pyttsx3_engine.getProperty("voices")
        for voice in self.all_local_voices:
            self.voice_listbox.insert("", tk.END, values=(voice.name, voice.gender, voice.languages, "None"))
    button_lf = tk.LabelFrame(master=self.more_voices_window, border=0)
    button_lf.pack(fill="x")
    if source == "web":
        download_button = tk.Button(master=button_lf, text="下载模型", width=10, command=lambda: download_model_window(self))
        download_button.pack(side="left", padx=5)
        tips_label = tk.Label(button_lf, text="Web/模型音色已移除，仅支持本地 pyttsx3")
        tips_label.pack(side="left")
    else:
        tips_label = tk.Label(button_lf, text="语言zh-CN为中文, en开头为英文")
        tips_label.pack(side="left")
    ok_button = tk.Button(master=button_lf, text="确定", width=10, command=lambda: select_voices_ok(self=self, source=source, window=self.more_voices_window))
    ok_button.pack(side="right")
    self.more_voices_window.protocol("WM_DELETE_WINDOW", lambda: _destroy_all_voices_window(self, window=self.more_voices_window))

def select_voices_ok(self, source, window):
    try:
        selected = self.voice_listbox.selection()[0]
        voice_name = self.voice_listbox.item(selected, "values")[0]
    except IndexError:
        messagebox.showwarning(message="请先选择一个音色！")
    try:
        self.voice_var.set(voice_name)
        get_tts_selected = self.tts_tree.selection()[0]
        _destroy_all_voices_window(self, window=window)
        current_values = list(self.tts_tree.item(get_tts_selected, "values"))
        current_values[4] = voice_name
        current_values[5] = source
        self.tts_tree.item(get_tts_selected, values=current_values)
    except IndexError as e:
        print(e)
        messagebox.showwarning(message="你还没有选择一个语音提示条目！")

def _destroy_all_voices_window(self):
    self.more_voices_window.destroy()
def download_model_window(self):
    messagebox.showinfo("提示", "已移除外部/模型 TTS 的模型下载功能（仅保留 pyttsx3）。")
    return


def _tts_add_point(self):
    """
    添加时间点
    """
    new_item = self.tts_tree.insert("", tk.END, values=("","",0.0,0.0,"",""))

def on_treeview_click(self, event, item):
    self.volume_var.set(float(item[2]))
    self.speed_var.set(float(item[3]))
    self.voice_var.set(str(item[4]))

def volume_scale_change(self, event):
    """
    松开鼠标改变音量，对应绑定320行
    """
    try:
        selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(selected, "values"))
        current_values[2] = f"{self.volume_var.get()}"
        self.tts_tree.item(selected, values=current_values)
    except IndexError:
        print("inex")
        pass

def speed_scale_change(self,event):
    """
    松开鼠标改变语速，对应绑定334行
    """
    try:
        selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(selected, "values"))
        current_values[3] = f"{self.speed_var.get()}"
        self.tts_tree.item(selected, values=current_values)
    except IndexError:
        pass

def _tts_delete_point(self):
    """
    删除时间点
    """
    try:
        get_selected = self.tts_tree.selection()[0]
        self.tts_tree.delete(get_selected)
    except IndexError:
        pass


def _pop_up_time_and_text_config_window(self):
    """
    弹出触发条件与语音内容配置窗口
    """
    # Create a popup window
    if self.if_time_and_text_config_popup == True:
        return
    self.if_time_and_text_config_popup = True
    popup_window = tk.Toplevel(self.main_window)
    popup_window.title("触发条件与语音内容配置")
    popup_window.geometry("400x200")
    popup_window.resizable(False, False)
    popup_window.bind("<Destroy>", lambda e: setattr(self, 'if_time_and_text_config_popup', False))

    # Try to get current selected tree item values to prefill fields
    get_time = ""
    get_content = ""
    try:
        sel = self.tts_tree.selection()[0]
        vals = self.tts_tree.item(sel, "values")
        get_time = vals[0] or ""
        get_content = vals[1] or ""
    except Exception:
        pass

    # Top: trigger selector
    top_row = tk.Frame(popup_window)
    top_row.pack(fill="x", pady=(10, 6))

    tk.Label(top_row, text="触发条件：", font=self.mainpage_button_font).pack(side="left")
    trigger_var = tk.StringVar()
    trigger_options = [
        "当音量达到",
        "当音量低于",
        "当达到目标",
        "当时间点达到",
        "当任务进度达到",
        "检测到异常停顿",
    ]
    trigger_combo = ttk.Combobox(top_row, values=trigger_options, textvariable=trigger_var, state="readonly", font=self.mainpage_button_font)
    trigger_combo.pack(side="left", fill="x", expand=True, padx=6)

    # Middle: stack of frames for each trigger's specific settings (only one visible at a time)
    stack_holder = tk.Frame(popup_window)
    stack_holder.pack(fill="x", pady=(0, 6))

    # Helper to create frames
    def make_frame():
        f = tk.Frame(stack_holder)
        f.pack_forget()
        return f

    vol_above_frame = make_frame()
    tk.Label(vol_above_frame, text="阈值(dB)：", font=self.mainpage_button_font).pack(side="left")
    vol_above_var = tk.DoubleVar(value=0.0)
    tk.Entry(vol_above_frame, textvariable=vol_above_var, font=self.mainpage_button_font, width=10).pack(side="left", padx=6)

    vol_below_frame = make_frame()
    tk.Label(vol_below_frame, text="阈值(dB)：", font=self.mainpage_button_font).pack(side="left")
    vol_below_var = tk.DoubleVar(value=0.0)
    tk.Entry(vol_below_frame, textvariable=vol_below_var, font=self.mainpage_button_font, width=10).pack(side="left", padx=6)

    goal_frame = make_frame()
    tk.Label(goal_frame, text="目标到达触发（无额外参数）", font=self.mainpage_button_font).pack(side="left")

    time_point_frame = make_frame()
    tk.Label(time_point_frame, text="时间点(分钟)：", font=self.mainpage_button_font).pack(side="left")
    time_point_var = tk.DoubleVar(value=0.0)
    tk.Entry(time_point_frame, textvariable=time_point_var, font=self.mainpage_button_font, width=10).pack(side="left", padx=6)

    progress_frame = make_frame()
    tk.Label(progress_frame, text="任务进度(百分比)：", font=self.mainpage_button_font).pack(side="left")
    progress_var = tk.DoubleVar(value=0.0)
    tk.Entry(progress_frame, textvariable=progress_var, font=self.mainpage_button_font, width=10).pack(side="left", padx=6)

    pause_frame = make_frame()
    tk.Label(pause_frame, text="异常停顿时间(秒)：", font=self.mainpage_button_font).pack(side="left")
    pause_var = tk.DoubleVar(value=0.0)
    tk.Entry(pause_frame, textvariable=pause_var, font=self.mainpage_button_font, width=10).pack(side="left", padx=6)

    # Common: content text
    content_row = tk.Frame(popup_window)
    content_row.pack(fill="x", pady=(0, 6))
    tk.Label(content_row, text="语音内容：", font=self.mainpage_button_font).pack(side="left")
    content_var = tk.StringVar(value=get_content)
    tk.Entry(content_row, textvariable=content_var, font=self.mainpage_button_font).pack(side="left", fill="x", expand=True, padx=6)

    # Buttons: Save / Cancel
    btn_row = tk.Frame(popup_window)
    btn_row.pack(fill="x", pady=(6, 0))

    def show_frame_for_trigger(*_):
        sel = trigger_var.get()
        # hide all
        for f in (vol_above_frame, vol_below_frame, goal_frame, time_point_frame, progress_frame, pause_frame):
            f.pack_forget()
        if sel == "当音量达到":
            vol_above_frame.pack(fill="x")
        elif sel == "当音量低于":
            vol_below_frame.pack(fill="x")
        elif sel == "当达到目标":
            goal_frame.pack(fill="x")
        elif sel == "当时间点达到":
            time_point_frame.pack(fill="x")
        elif sel == "当任务进度达到":
            progress_frame.pack(fill="x")
        elif sel == "检测到异常停顿":
            pause_frame.pack(fill="x")

    trigger_combo.bind("<<ComboboxSelected>>", show_frame_for_trigger)

    if get_time:
        for opt in trigger_options:
            if get_time.startswith(opt):
                trigger_var.set(opt)
                break
        else:
            try:
                float(get_time)
                trigger_var.set("当时间点达到")
                time_point_var.set(float(get_time))
            except Exception:
                trigger_var.set(trigger_options[0])
    else:
        trigger_var.set(trigger_options[0])
    show_frame_for_trigger()

    def build_time_display():
        sel = trigger_var.get()
        if sel == "当音量达到":
            return f"{sel} {vol_above_var.get()} DB"
        if sel == "当音量低于":
            return f"{sel} {vol_below_var.get()} DB"
        if sel == "当达到目标":
            return sel
        if sel == "当时间点达到":
            return f"{sel} {time_point_var.get()} 分钟"
        if sel == "当任务进度达到":
            return f"{sel} {progress_var.get()} %"
        if sel == "检测到异常停顿":
            return f"{sel} {pause_var.get()} 秒"
        return sel

    def on_save_and_close():
        time_display = build_time_display()
        self.content = content_var.get()
        try:
            selected = self.tts_tree.selection()[0]
            get_values = list(self.tts_tree.item(selected, "values"))
            get_values[0] = time_display
            get_values[1] = self.content
            self.tts_tree.item(selected, values=get_values)
        except Exception:
            self.tts_tree.insert("", tk.END, values=(time_display, self.content, self.volume_var.get(), self.speed_var.get(), self.voice_var.get()))
        self.if_time_and_text_config_popup = False
        popup_window.destroy()

    def on_cancel():
        self.if_time_and_text_config_popup = False
        popup_window.destroy()

    save_btn = tk.Button(btn_row, text="保存并关闭", font=self.mainpage_button_font, command=on_save_and_close)
    save_btn.pack(side="right", padx=6)
    cancel_btn = tk.Button(btn_row, text="取消", font=self.mainpage_button_font, command=on_cancel)
    cancel_btn.pack(side="right")

def test_tts(self):
    """
    语音生成器测试GUI对接
    """
    ask_if_continue = messagebox.askyesno(message=f"接下来将会生成语音文件进行测试\n请检查参数是否正确\n并决定是否继续")
    if ask_if_continue == True:
        get_context = self.content
        get_volume = float(self.volume_var.get())
        get_speed = float(self.speed_var.get())
        get_voice = self.voice_var.get()
        get_source = self.tts_tree.selection()[0]
        get_source = list(self.tts_tree.item(get_source, "values"))[5]
        if get_context == "":
            messagebox.showwarning(message="检测到你的语音内容为空！")
            return
        loop = asyncio.get_event_loop()  
        result =loop.run_until_complete(tts.test_tts(args=[get_context, get_volume, get_speed, get_voice, get_source], current_account=self.current_acount))
        if result == "ok":
            pass
        else:
            messagebox.showerror(message=f"语音生成模块返回报错:{result}")
    else:
        pass

def save_tts_setting(self):
    items = self.tts_tree.get_children()
    value_list = []
    for i in items:
        value_list.append(self.tts_tree.item(i)['values'])
    if self.if_tts_enabled.get() == True:
        final_list = [1, value_list]
    elif self.if_tts_enabled.get() == False:
        final_list = [0, value_list]
    settings.save_tts_settings(self=self, args=final_list)

def _generate_reading_gui(self):
    if self.if_reading_show == True:
        return
    else:
        self.if_reading_show == True
    self.reading_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.reading_frame)
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False
    
    #information show bar
    information_show_lbframe = tk.LabelFrame(master=self.reading_frame)
    information_show_lbframe.pack(fill="x", side="top", padx=5, pady=5)
    
    # 创建三个Label，使用grid布局实现并排排列
    self.labels_list = [
        tk.Label(master=information_show_lbframe, text="朗读目标: 未读取", font=("微软雅黑", 15)),
        tk.Label(master=information_show_lbframe, text="声音阈值：未读取", font=("微软雅黑", 15)),
        tk.Label(master=information_show_lbframe, text="语音提示：未读取", font=("微软雅黑", 15))
    ]
    # 使用grid布局，让三个标签分别位于左、中、右
    read_detail_show_lb_frame = tk.LabelFrame(master=self.reading_frame, border=0)
    read_detail_show_lb_frame.pack(fill="x")
    read_detail_show_lb_frame.columnconfigure(0, weight=1)  # 左列
    read_detail_show_lb_frame.columnconfigure(1, weight=1)  # 中列
    read_detail_show_lb_frame.columnconfigure(2, weight=1)  # 右列
    
    self.labels_list[0].grid(row=0, column=0, sticky="w", padx=10)   # 左侧对齐
    self.labels_list[1].grid(row=0, column=1, sticky="n", padx=10)   # 中间对齐
    self.labels_list[2].grid(row=0, column=2, sticky="e", padx=10)   # 右侧对齐

    self.information_label_list = [
        tk.Label(master=read_detail_show_lb_frame, text="剩余时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="停顿总时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="有效朗读时间: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="总时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="最大音量: 未知", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="效率: 0.00", font=("微软雅黑", 15))
    ]
    
    # 配置grid布局 - 3列，每列权重为1
    read_detail_show_lb_frame.columnconfigure(0, weight=1)
    read_detail_show_lb_frame.columnconfigure(1, weight=1) 
    read_detail_show_lb_frame.columnconfigure(2, weight=1)
    
    # 第一行（行0）- 三个标签分别左、中、右对齐
    self.information_label_list[0].grid(row=0, column=0, sticky="w", padx=10, pady=5)
    self.information_label_list[1].grid(row=0, column=1, sticky="n", padx=10, pady=5)
    self.information_label_list[2].grid(row=0, column=2, sticky="e", padx=10, pady=5)
    
    # 第二行（行1）- 三个标签分别左、中、右对齐  
    self.information_label_list[3].grid(row=1, column=0, sticky="w", padx=10, pady=5)
    self.information_label_list[4].grid(row=1, column=1, sticky="n", padx=10, pady=5)
    self.information_label_list[5].grid(row=1, column=2, sticky="e", padx=10, pady=5)

    #btns
    start_button = tk.Button(master=self.reading_frame, text="开始朗读", font=("微软雅黑", 15), command=lambda:start_reading(self))
    start_button.pack(fill="x", pady=5)
    back_button = tk.Button(master=self.reading_frame, text="返回",font=("微软雅黑", 15),
                             command=lambda: reading_back(self))
    back_button.pack(fill="x", pady=5)

    #state Label - 单独放在下面
    self.reading_state_label = tk.Label(master=self.reading_frame, text="正在准备中...", font=("微软雅黑", 40))
    self.reading_state_label.pack(pady=10, fill="x")

    # debug_show
    self.show_debug = tk.Text(master=self.reading_frame,font=("Consolas",13))
    debug_scroll = tk.Scrollbar(master=self.show_debug, command=self.show_debug.yview)
    self.show_debug.config(yscrollcommand=debug_scroll.set)
    debug_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    self.show_debug.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    reading.reading_data_get_and_check(self)

def start_reading(self):
    reading.start_reading(self=self)

def reading_back(self):
    if self.if_reading == True:
        messagebox.showinfo(title="无法退出！", message="当前朗读正在进行中，请勿退出朗读界面\n否则可能导致界面更新错误!")
    else:
        self.welcome_page(destroy_window=[self.reading_frame, "reading"])