"""
TTS 语音提示相关 GUI 辅助函数：
  - 启用/禁用 TTS 控件
  - 音色选择窗口
  - 添加/删除时间点
  - 触发条件与语音内容弹窗
  - Treeview 交互回调（选中、音量、语速）
  - 测试语音 & 保存 TTS 设置
"""

import tkinter as tk
from tkinter import ttk, messagebox
import asyncio
import pyttsx3
from .. import tts, settings


# ──────────────────────── 启用 / 禁用 ────────────────────────

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


# ──────────────────────── 获取网络音色（占位） ────────────────────────

def _get_web_voice(self):
    # Use the built-in, stable Baidu voice presets
    return ['EdgeTTS 暂时不支持选择语音']


# ──────────────────────── 更多音色窗口 ────────────────────────

def _generate_more_vloices_window(self, source):
    """生成更多音色窗口"""
    if self.if_all_voices_window_showed == True:
        return
    if source == "web":
        messagebox.showinfo(message="已切换到EdgeTTS！\nEdgeTTS暂不支持更换语音")
        get_tts_selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(get_tts_selected, "values"))
        current_values[4] = "EdgeTTS Default"
        current_values[5] = source
        self.tts_tree.item(get_tts_selected, values=current_values)
        self.voice_menu.configure(text="EdgeTTS Default")
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
    self.voice_listbox = ttk.Treeview(
        master=table_frame, columns=voice_columns, show="headings",
        height=8, yscrollcommand=tree_scroll.set,
    )
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
    if source == "local":
        if self.all_local_voices == None:
            self.pyttsx3_engine = pyttsx3.init()
            self.all_local_voices = self.pyttsx3_engine.getProperty("voices")
        for voice in self.all_local_voices:
            self.voice_listbox.insert(
                "", tk.END, values=(voice.name, voice.gender, voice.languages, "None")
            )
    button_lf = tk.LabelFrame(master=self.more_voices_window, border=0)
    button_lf.pack(fill="x")
    tips_label = tk.Label(button_lf, text="语言zh-CN为中文, en开头为英文")
    tips_label.pack(side="left")
    ok_button = tk.Button(
        master=button_lf, text="确定", width=10,
        command=lambda: _select_voices_ok(self=self, source=source),
    )
    ok_button.pack(side="right")
    self.more_voices_window.protocol(
        "WM_DELETE_WINDOW", lambda: _destroy_all_voices_window(self)
    )


def _select_voices_ok(self, source):
    try:
        selected = self.voice_listbox.selection()[0]
        voice_name = self.voice_listbox.item(selected, "values")[0]
    except IndexError:
        messagebox.showwarning(message="请先选择一个音色！")
    try:
        self.voice_var.set(voice_name)
        get_tts_selected = self.tts_tree.selection()[0]
        _destroy_all_voices_window(self)
        current_values = list(self.tts_tree.item(get_tts_selected, "values"))
        if source == "web":
            current_values[4] = "EdgeTTS Default"
        else:
            current_values[4] = voice_name
        current_values[5] = source
        self.tts_tree.item(get_tts_selected, values=current_values)
    except IndexError as e:
        print(e)
        messagebox.showwarning(message="你还没有选择一个语音提示条目！")


def _destroy_all_voices_window(self):
    self.more_voices_window.destroy()
    self.if_all_voices_window_showed = False


# ──────────────────────── Treeview 操作 ────────────────────────

def _tts_add_point(self):
    """添加时间点"""
    self.tts_tree.insert("", tk.END, values=("", "", 0.0, 0.0, "", ""))


def _tts_delete_point(self):
    """删除时间点"""
    try:
        get_selected = self.tts_tree.selection()[0]
        self.tts_tree.delete(get_selected)
    except IndexError:
        pass


# ──────────────────────── Treeview / Scale 回调 ────────────────────────

def on_treeview_click(self, event, item):
    self.volume_var.set(float(item[2]))
    self.speed_var.set(float(item[3]))
    self.voice_var.set(str(item[4]))
    self.content = str(item[1])


def volume_scale_change(self, event):
    """松开鼠标改变音量"""
    try:
        selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(selected, "values"))
        current_values[2] = f"{self.volume_var.get()}"
        self.tts_tree.item(selected, values=current_values)
    except IndexError:
        pass


def speed_scale_change(self, event):
    """松开鼠标改变语速"""
    try:
        selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(selected, "values"))
        current_values[3] = f"{self.speed_var.get()}"
        self.tts_tree.item(selected, values=current_values)
    except IndexError:
        pass


# ──────────────────────── 触发条件 & 语音内容弹窗 ────────────────────────

def _pop_up_time_and_text_config_window(self):
    """弹出触发条件与语音内容配置窗口"""
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
    trigger_combo = ttk.Combobox(
        top_row, values=trigger_options, textvariable=trigger_var,
        state="readonly", font=self.mainpage_button_font,
    )
    trigger_combo.pack(side="left", fill="x", expand=True, padx=6)

    # Middle: stack of frames for each trigger's specific settings
    stack_holder = tk.Frame(popup_window)
    stack_holder.pack(fill="x", pady=(0, 6))

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
    tk.Entry(content_row, textvariable=content_var, font=self.mainpage_button_font).pack(
        side="left", fill="x", expand=True, padx=6
    )

    # Buttons: Save / Cancel
    btn_row = tk.Frame(popup_window)
    btn_row.pack(fill="x", pady=(6, 0))

    def show_frame_for_trigger(*_):
        sel = trigger_var.get()
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
            self.tts_tree.insert(
                "", tk.END,
                values=(time_display, self.content, self.volume_var.get(),
                        self.speed_var.get(), self.voice_var.get()),
            )
        self.if_time_and_text_config_popup = False
        popup_window.destroy()

    def on_cancel():
        self.if_time_and_text_config_popup = False
        popup_window.destroy()

    save_btn = tk.Button(btn_row, text="保存并关闭", font=self.mainpage_button_font, command=on_save_and_close)
    save_btn.pack(side="right", padx=6)
    cancel_btn = tk.Button(btn_row, text="取消", font=self.mainpage_button_font, command=on_cancel)
    cancel_btn.pack(side="right")


# ──────────────────────── 测试 TTS ────────────────────────

def test_tts(self):
    """语音生成器测试 GUI 对接"""
    if self.if_generating_ttstest == True:
        return
    else:
        self.if_generating_ttstest = True
    ask_if_continue = messagebox.askyesno(
        message="接下来将会生成语音文件进行测试\n请检查参数是否正确\n并决定是否继续"
    )
    if ask_if_continue == True:
        try:
            get_context = self.content
            get_volume = float(self.volume_var.get())
            get_speed = float(self.speed_var.get())
            get_voice = self.voice_var.get()
            selected = self.tts_tree.selection()[0]
            get_source = list(self.tts_tree.item(selected, "values"))[5]
        except IndexError:
            self.if_generating_ttstest = False
            messagebox.showwarning(message="你还没有选择一个语音提示条目！")
            return

        if get_context == "":
            self.if_generating_ttstest = False
            messagebox.showwarning(message="检测到你的语音内容为空！")
            return

        def on_complete():
            self.if_generating_ttstest = False

        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            tts.test_tts(
                args=[get_context, get_volume, get_speed, get_voice, get_source],
                current_account=self.current_acount,
                on_finish=on_complete,
            )
        )
        if result == "ok":
            pass
        else:
            messagebox.showerror(message=f"语音生成模块返回报错:{result}")
    else:
        self.if_generating_ttstest = False


# ──────────────────────── 保存 TTS 设置 ────────────────────────

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
