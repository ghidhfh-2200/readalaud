"""
设置页面 GUI：朗读设置、语音提示设置、账号与安全、疑难解答、个性化。
"""

import tkinter as tk
from tkinter import ttk
import ttkbootstrap as ttkbs
from markdown import markdown
from tkhtmlview import HTMLLabel
from .. import settings
from .tts_gui import (
    on_treeview_click,
    volume_scale_change,
    speed_scale_change,
    test_tts,
    save_tts_setting,
)


def _generate_settings_gui(self):
    # The frame for the settings
    if self.if_settings_show == True:
        return
    else:
        self.if_settings_show = True
    # main frame
    self.settings_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.settings_frame)
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False
    # notebooks
    notebook = ttk.Notebook(master=self.settings_frame)
    account_frame = tk.Frame(notebook)
    read_frame = tk.Frame(notebook)
    questions_and_answers_frame = tk.Frame(notebook)
    customize_frame = tk.Frame(notebook)
    notebook.add(child=read_frame, text="朗读设置")
    notebook.add(child=questions_and_answers_frame, text="疑难解答")
    notebook.add(child=account_frame, text="账号与安全")
    notebook.add(child=customize_frame, text="个性化")
    notebook.pack(fill="both", expand=1)

    # ── Q&A frame ──
    markdown_text = markdown("""
### 语音提示说明
- 当前仅支持本地 TTS（pyttsx3）
- 无需下载模型、无网络依赖
""")
    why_dbFS_label = HTMLLabel(master=questions_and_answers_frame, html=markdown_text)
    why_dbFS_label.pack(fill="x", padx=5, pady=5)

    # ── account frame ──
    _build_account_tab(self, account_frame)

    # ── read frame（基础设置 + TTS 设置） ──
    _build_reading_tab(self, read_frame)

    # ── customize frame ──
    _build_customize_tab(self, customize_frame)

    # 返回按钮
    back_button = tk.Button(
        master=self.settings_frame, text="返回", font=self.mainpage_button_font, width=10,
        command=lambda: self.welcome_page(destroy_window=[self.settings_frame, "settings"]),
    )
    back_button.pack(side="right")
    settings._load_settings(self=self)


# ═══════════════════════ 账号 Tab ═══════════════════════

def _build_account_tab(self, account_frame):
    account_management_label_frame = tk.LabelFrame(
        master=account_frame, padx=5, pady=5, font=self.mainpage_button_font, text="账户管理"
    )
    account_management_label_frame.pack(side="top", fill="x", expand=False, anchor="n")

    name_lf = tk.LabelFrame(master=account_management_label_frame, border=0, font=self.mainpage_button_font)
    name_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.account_name_label = tk.Label(master=name_lf, text="账户名称: ", font=("微软雅黑", 17))
    self.account_name_label.pack(side=tk.LEFT)
    self.settings_name_value = tk.StringVar()
    name_entry = tk.Entry(master=name_lf, width=30, textvariable=self.settings_name_value, font=("微软雅黑", 17))
    name_entry.pack(side=tk.LEFT)
    account_ok_button = tk.Button(
        master=name_lf, text="确定", font=self.mainpage_button_font, width=10,
        command=lambda: self.save_settings_except_tts("account"),
    )
    account_ok_button.pack(side="right")

    password_lf = tk.LabelFrame(master=account_management_label_frame, border=0, font=self.mainpage_button_font)
    password_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.account_password_label = tk.Label(master=password_lf, text="密码设置：", font=("微软雅黑", 17))
    self.account_password_label.pack(side=tk.LEFT)
    self.settings_password_value = tk.StringVar()
    password_entry = tk.Entry(master=password_lf, width=30, textvariable=self.settings_password_value, font=("微软雅黑", 17))
    password_entry.pack(side=tk.LEFT)
    account_password_ok_button = tk.Button(
        master=password_lf, text="确定", font=self.mainpage_button_font, width=10,
        command=lambda: self.save_settings_except_tts(option="password"),
    )
    account_password_ok_button.pack(side="right")

    account_operation = tk.LabelFrame(
        master=account_frame, padx=5, pady=5, font=self.mainpage_button_font, text="账户操作"
    )
    account_operation.pack(side="top", fill="x", expand=False, anchor="n")
    delete_acount = tk.Button(
        account_operation, text="注销账号", fg="red", font=self.mainpage_button_font, width=20,
        command=lambda: self.delete_the_account(),
    )
    delete_acount.pack(side="left", padx=5)
    reset_acount = tk.Button(
        account_operation, text="重置全部数据", fg="red", font=self.mainpage_button_font, width=20,
        command=lambda: self.reset_account_data(),
    )
    reset_acount.pack(side="left", padx=5)
    logout_btn = tk.Button(
        account_operation, text="退出登录", fg="black", font=self.mainpage_button_font, width=20,
        command=lambda: self.logout(),
    )
    logout_btn.pack(side="left", padx=5)


# ═══════════════════════ 朗读设置 Tab ═══════════════════════

def _build_reading_tab(self, read_frame):
    # ── 基础设置 ──
    read_basic_settings_labelframe = tk.LabelFrame(
        master=read_frame, padx=5, pady=5, font=self.mainpage_button_font, text="基础设置"
    )
    read_basic_settings_labelframe.pack(side="top", fill="x", expand=False, anchor="n")

    # 目标设定
    goal_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0, font=self.mainpage_button_font)
    goal_lf.pack(fill="x", expand=1, padx=5, pady=5)
    self.settings_goal_label = tk.Label(master=goal_lf, text="目标设定:", font=("微软雅黑", 17))
    self.settings_goal_label.pack(side="left")
    self.settings_goal_value = tk.IntVar()
    goal_entry = tk.Entry(master=goal_lf, textvariable=self.settings_goal_value, width=30, font=("微软雅黑", 17))
    goal_entry.pack(side="left")
    goal_ok_button = tk.Button(
        master=goal_lf, text="确定", width=10, font=self.mainpage_button_font,
        command=lambda: self.save_settings_except_tts("goal"),
    )
    goal_ok_button.pack(side="right")

    # 停顿容忍间隔
    stop_dur_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0)
    stop_dur_lf.pack(side="top", padx=5, pady=5, expand=False, anchor="n", fill="x")
    self.stop_dur_label = tk.Label(master=stop_dur_lf, text="停顿容忍间隔(秒):", font=("微软雅黑", 17))
    self.stop_dur_label.pack(side="left")
    self.settings_stop_dur_value = tk.DoubleVar()
    stop_dur_entry = tk.Entry(master=stop_dur_lf, width=30, font=("微软雅黑", 17), textvariable=self.settings_stop_dur_value)
    stop_dur_entry.pack(side="left")
    stop_dur_button = tk.Button(
        master=stop_dur_lf, text="确定", font=self.mainpage_button_font, width=10,
        command=lambda: self.save_settings_except_tts("stop_dur"),
    )
    stop_dur_button.pack(side="right")

    # 分贝阈值
    db_lf = tk.LabelFrame(master=read_basic_settings_labelframe, border=0)
    db_lf.pack(side="top", padx=5, pady=5, expand=False, anchor="n", fill="x")
    self.settings_db_label = tk.Label(master=db_lf, text="分贝阈值(dB):", font=("微软雅黑", 17))
    self.settings_db_label.pack(side="left")
    self.settings_db_value = tk.DoubleVar()
    db_entry = tk.Entry(master=db_lf, width=30, font=("微软雅黑", 17), textvariable=self.settings_db_value)
    db_entry.pack(side="left")
    db_ok_button = tk.Button(
        master=db_lf, text="确定", font=self.mainpage_button_font, width=10,
        command=lambda: self.save_settings_except_tts("db_level"),
    )
    db_ok_button.pack(side="right")

    # ── 语音提示设置 ──
    _build_tts_settings_section(self, read_frame)


def _build_tts_settings_section(self, read_frame):
    """构建语音提示设置区域（TTS Treeview + 音色/音量/语速控件）"""
    read_settings_frame = tk.LabelFrame(
        master=read_frame, text="语音提示设置", padx=5, font=self.mainpage_button_font
    )
    read_settings_frame.pack(side="top", fill="x", expand=False, anchor="n")

    checkbox_frame = tk.Frame(read_settings_frame)
    checkbox_frame.pack(fill="x")
    self.if_tts_enabled = tk.BooleanVar()
    self.if_tts_checkbox = tk.Checkbutton(
        checkbox_frame, text="启用语音提示", variable=self.if_tts_enabled,
        font=self.mainpage_button_font,
        command=lambda: self.enable_or_disable_tts_gui(),
    )
    self.if_tts_checkbox.pack(side="left", padx=5)

    # TTS settings container
    self.settings_container = tk.Frame(read_settings_frame)
    self.settings_container.pack(fill="both", expand=True, padx=5)

    # Treeview frame
    table_frame = tk.Frame(self.settings_container)
    table_frame.pack(fill="both", expand=True)

    tree_scroll = ttk.Scrollbar(table_frame)
    tree_scroll.pack(side="right", fill="y")

    columns = ("time", "content", "volume", "speed", "voice", "from")
    self.tts_tree = ttk.Treeview(
        table_frame, columns=columns, show="headings",
        yscrollcommand=tree_scroll.set, height=5,
    )
    self.tts_tree.bind(
        "<<TreeviewSelect>>",
        lambda event: on_treeview_click(
            self, event, self.tts_tree.item(self.tts_tree.selection()[0], "values")
        ),
    )
    # Configure columns
    self.tts_tree.heading("time", text="触发条件")
    self.tts_tree.heading("content", text="语音内容")
    self.tts_tree.heading("volume", text="音量")
    self.tts_tree.heading("speed", text="语速")
    self.tts_tree.heading("voice", text="音色")
    self.tts_tree.heading("from", text="来源")

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

    self.add_button = tk.Button(
        button_frame, text="添加时间点", font=self.mainpage_button_font,
        command=lambda: self.tts_add_point(),
    )
    self.add_button.pack(side="left", padx=5)

    self.delete_button = tk.Button(
        button_frame, text="删除时间点", font=self.mainpage_button_font,
        command=lambda: self.tts_delete_point(),
    )
    self.delete_button.pack(side="left", padx=5)

    self.time_and_text_button = tk.Button(
        button_frame, text="时间点&语音内容", font=self.mainpage_button_font,
        command=lambda: self.pop_up_time_and_text_config_window(),
    )
    self.time_and_text_button.pack(side="left", padx=5)

    # Voice configuration frame
    voice_config_frame = tk.LabelFrame(
        self.settings_container, text="语音配置", font=self.mainpage_button_font
    )
    voice_config_frame.pack(fill="x")

    voices_frame = tk.Frame(voice_config_frame)
    voices_frame.pack(fill="x")

    tk.Label(voices_frame, text="选择音色:", font=self.mainpage_button_font).pack(side="left", padx=5)
    self.voice_var = tk.StringVar()
    self.voice_menu = ttk.Label(
        voices_frame, text="未选择", textvariable=self.voice_var, font=self.mainpage_button_font
    )
    self.voice_menu.pack(side="left", padx=5, fill="x", expand=True)
    self.more_local_button = tk.Button(
        voices_frame, text="更多(本地)", font=self.mainpage_button_font,
        command=lambda: self.generate_more_vloices_window("local"),
    )
    self.more_local_button.pack(side="right", padx=5)
    self.more_web_button = tk.Button(
        voices_frame, text="更多(网络)", font=self.mainpage_button_font,
        command=lambda: self.generate_more_vloices_window("web"),
    )
    self.more_web_button.pack(side="right", padx=5)

    # Volume control
    volume_frame = tk.Frame(voice_config_frame)
    volume_frame.pack(fill="x")

    tk.Label(volume_frame, text="音量:", font=self.mainpage_button_font).pack(side="left")
    self.volume_var = tk.DoubleVar(value=1.0)
    self.volume_scale = tk.Scale(
        volume_frame, from_=-1.0, to=1.0, variable=self.volume_var,
        orient="horizontal", resolution=0.1, font=self.mainpage_button_font,
    )
    self.volume_scale.pack(side="left", fill="x", expand=True)
    self.volume_scale.bind("<ButtonRelease-1>", lambda event: volume_scale_change(self, event))

    # Speed control
    speed_frame = tk.Frame(voice_config_frame)
    speed_frame.pack(fill="x")

    tk.Label(speed_frame, text="语速:", font=self.mainpage_button_font).pack(side="left")
    self.speed_var = tk.DoubleVar(value=1.0)
    self.speed_scale = tk.Scale(
        speed_frame, from_=-1.0, to=1.0, variable=self.speed_var,
        orient="horizontal", resolution=0.1, font=self.mainpage_button_font,
    )
    self.speed_scale.pack(side="left", fill="x", expand=True)
    self.speed_scale.bind("<ButtonRelease-1>", lambda event: speed_scale_change(self, event))

    # Save / Test buttons
    buttons_frame = tk.LabelFrame(self.settings_container, border=0)
    buttons_frame.pack(fill="x")
    self.test_button = tk.Button(
        buttons_frame, text="测试语音", font=self.mainpage_button_font,
        command=lambda: test_tts(self),
    )
    self.test_button.pack(side="right", padx=5)
    self.tts_save_button = tk.Button(
        buttons_frame, text="保存设置", font=self.mainpage_button_font,
        command=lambda: save_tts_setting(self),
    )
    self.tts_save_button.pack(side="right")


# ═══════════════════════ 个性化 Tab ═══════════════════════

def _build_customize_tab(self, customize_frame):
    self.get_style_list = ttkbs.Style().theme_names()
    customize_label_frame = tk.LabelFrame(
        master=customize_frame, padx=5, pady=5, text="选择样式", font=self.mainpage_button_font
    )
    customize_label_frame.pack(side="top", fill="x")
    self.customize_listbox = tk.Listbox(master=customize_label_frame, width=20)
    self.customize_listbox.pack(side="top", fill="x")
    for i in self.get_style_list:
        self.customize_listbox.insert(tk.END, i)
    customize_ok_button = tk.Button(master=customize_label_frame, text="确认", width=10)
    customize_ok_button.pack(side="bottom", fill="x")
    customize_ok_button.config(command=self.change_theme)
