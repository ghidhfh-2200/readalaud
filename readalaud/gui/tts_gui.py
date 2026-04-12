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
from tkinter import ttk, filedialog
import asyncio
import os
import shutil
import threading
import time
import wave
import pyttsx3
from .. import tts


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
            self.tts_mode_combo.config(state="disabled")
            self.custom_mode_combo.config(state="disabled")
            self.custom_action_button.config(state="disabled")
        else:
            self.add_button.config(state="active")
            self.delete_button.config(state="active")
            self.time_and_text_button.config(state="active")
            self.voice_menu.config(state="readinly")
            self.volume_scale.config(state="active")
            self.speed_scale.config(state="active")
            self.more_web_button.config(state="active")
            self.more_local_button.config(state="active")
            self.tts_mode_combo.config(state="readonly")
            if self.tts_mode_var.get() == "自定义":
                self.custom_mode_combo.config(state="readonly")
                self.custom_action_button.config(state="active")
            else:
                self.custom_mode_combo.config(state="disabled")
                self.custom_action_button.config(state="disabled")
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
            self.tts_mode_combo.config(state="disabled")
            self.custom_mode_combo.config(state="disabled")
            self.custom_action_button.config(state="disabled")
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
            self.tts_mode_combo.config(state="readonly")
            if self.tts_mode_var.get() == "自定义":
                self.custom_mode_combo.config(state="readonly")
                self.custom_action_button.config(state="active")
            else:
                self.custom_mode_combo.config(state="disabled")
                self.custom_action_button.config(state="disabled")


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
        self.gui.info(message="已切换到EdgeTTS！\nEdgeTTS暂不支持更换语音")
        get_tts_selected = self.tts_tree.selection()[0]
        current_values = list(self.tts_tree.item(get_tts_selected, "values"))
        current_values[4] = "EdgeTTS Default"
        current_values[5] = source
        self.tts_tree.item(get_tts_selected, values=current_values)
        self.voice_menu.configure(text="EdgeTTS Default")
        return
    self.if_all_voices_window_showed = True
    self.more_voices_window = self.gui.create_toplevel(
        title="更多音色",
        size=(460, 300),
        parent=self.main_window,
        resizable=(False, False),
        modal=False,
        center=True,
    )

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
        self.gui.warning(message="请先选择一个音色！")
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
        self.gui.warning(message="你还没有选择一个语音提示条目！")


def _destroy_all_voices_window(self):
    self.more_voices_window.destroy()
    self.if_all_voices_window_showed = False


# ──────────────────────── Treeview 操作 ────────────────────────

def _tts_add_point(self):
    """添加时间点"""
    self.tts_tree.insert("", tk.END, values=("", "", 1.0, 1.0, "", "local"))


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
    source = str(item[5]) if len(item) > 5 else "local"
    if source in ("local", "web", ""):
        self.tts_mode_var.set("TTS")
    else:
        self.tts_mode_var.set("自定义")
    if source == "custom_record":
        self.custom_mode_var.set("直接录音")
    else:
        self.custom_mode_var.set("上传音频")
    _on_tts_mode_changed(self)


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
    popup_window = self.gui.create_toplevel(
        title="触发条件与语音内容配置",
        size=(400, 200),
        parent=self.main_window,
        resizable=(False, False),
        modal=False,
        center=True,
    )
    popup_window.bind("<Destroy>", lambda e: setattr(self, 'if_time_and_text_config_popup', False))

    # Try to get current selected tree item values to prefill fields
    get_time = ""
    get_content = ""
    get_source = "local"
    try:
        sel = self.tts_tree.selection()[0]
        vals = self.tts_tree.item(sel, "values")
        get_time = vals[0] or ""
        get_content = vals[1] or ""
        if len(vals) > 5:
            get_source = vals[5] or "local"
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
    content_entry = tk.Entry(content_row, textvariable=content_var, font=self.mainpage_button_font)
    content_entry.pack(
        side="left", fill="x", expand=True, padx=6
    )
    if get_source in ("custom_upload", "custom_record", "custom"):
        content_entry.config(state="disabled")

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
                        self.speed_var.get(), self.voice_var.get(), "local"),
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
    try:
        selected = self.tts_tree.selection()[0]
        get_source = list(self.tts_tree.item(selected, "values"))[5]
    except Exception:
        self.if_generating_ttstest = False
        self.gui.warning(message="你还没有选择一个语音提示条目！")
        return

    if get_source in ("custom_upload", "custom_record", "custom"):
        ask_if_continue = self.gui.ask_yes_no(
            message="接下来将会播放音频文件进行测试\n请检查参数是否正确\n并决定是否继续"
        )
    else:
        ask_if_continue = self.gui.ask_yes_no(
            message="接下来将会生成语音文件进行测试\n请检查参数是否正确\n并决定是否继续"
        )
    if ask_if_continue == True:
        try:
            get_context = self.content
            get_volume = float(self.volume_var.get())
            get_speed = float(self.speed_var.get())
            get_voice = self.voice_var.get()
            selected = self.tts_tree.selection()[0]
        except IndexError:
            self.if_generating_ttstest = False
            self.gui.warning(message="你还没有选择一个语音提示条目！")
            return

        if get_context == "" and get_source not in ("custom_upload", "custom_record", "custom"):
            self.if_generating_ttstest = False
            self.gui.warning(message="检测到你的语音内容为空！")
            return

        if get_source in ("custom_upload", "custom_record", "custom"):
            row_index = _selected_tts_order_index(self)
            if row_index is None:
                self.if_generating_ttstest = False
                self.gui.warning(message="你还没有选择一个语音提示条目！")
                return

            base_dir = os.path.join(".", "data", self.current_acount, "tts")
            wav_path = os.path.join(base_dir, f"{row_index}.wav")

            def _play_custom_preview():
                try:
                    if os.path.exists(wav_path):
                        import simpleaudio as sa
                        with wave.open(wav_path, "rb") as wf:
                            channels = wf.getnchannels()
                            sampwidth = wf.getsampwidth()
                            framerate = wf.getframerate()
                            raw = wf.readframes(wf.getnframes())
                        play_obj = sa.play_buffer(raw, channels, sampwidth, framerate)
                        self._tts_test_play_obj = play_obj
                        while play_obj.is_playing():
                            if getattr(self, "_tts_test_stop_requested", False):
                                try:
                                    play_obj.stop()
                                except Exception:
                                    pass
                                break
                            time.sleep(0.05)
                    else:
                        raise FileNotFoundError("未找到对应的自定义音频，请先上传或录音")
                except Exception as e:
                    self.main_window.after(0, lambda: self.gui.error(message=f"自定义音频测试失败: {e}"))
                finally:
                    def _finish():
                        self._tts_test_play_obj = None
                        self._tts_test_stop_requested = False
                        self.if_generating_ttstest = False
                    self.main_window.after(0, _finish)

            threading.Thread(target=_play_custom_preview, daemon=True).start()
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
            self.gui.error(message=f"语音生成模块返回报错:{result}")
    else:
        self.if_generating_ttstest = False


# ──────────────────────── 保存 TTS 设置 ────────────────────────

def save_tts_setting(self):
    items = self.tts_tree.get_children()
    value_list = []
    for i in items:
        row = list(self.tts_tree.item(i)["values"])
        while len(row) < 6:
            row.append("")
        value_list.append(row)
    if self.if_tts_enabled.get() == True:
        final_list = [1, value_list]
    elif self.if_tts_enabled.get() == False:
        final_list = [0, value_list]
    self.save_tts_settings(final_list)


def stop_tts_test(self):
    """停止测试音频播放（当前支持自定义 WAV 预览）。"""
    if not getattr(self, "if_generating_ttstest", False):
        self.gui.info(message="当前没有正在播放的测试音频")
        return

    self._tts_test_stop_requested = True
    play_obj = getattr(self, "_tts_test_play_obj", None)
    if play_obj is not None:
        try:
            play_obj.stop()
        except Exception:
            pass


# ──────────────────────── 自定义语音（上传 / 录音） ────────────────────────

def _get_selected_tts_row(self):
    try:
        selected = self.tts_tree.selection()[0]
        return selected, list(self.tts_tree.item(selected, "values"))
    except Exception:
        return None, None


def _selected_tts_order_index(self):
    selected, _ = _get_selected_tts_row(self)
    if selected is None:
        return None
    children = list(self.tts_tree.get_children())
    try:
        return children.index(selected)
    except ValueError:
        return None


def _delete_tts_audio_by_index(self, row_index):
    if row_index is None:
        return
    base_dir = os.path.join(".", "data", self.current_acount, "tts")
    for ext in (".wav", ".mp3"):
        p = os.path.join(base_dir, f"{row_index}{ext}")
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception as e:
                try:
                    self.log_error("删除TTS文件失败", f"{p}: {e}")
                except Exception:
                    pass


def _set_selected_source(self, source, voice_text=None):
    selected, current_values = _get_selected_tts_row(self)
    if selected is None:
        self.gui.warning(message="请先选择一个语音提示条目！")
        return False
    while len(current_values) < 6:
        current_values.append("")
    current_values[5] = source
    if voice_text is not None:
        current_values[4] = voice_text
        self.voice_var.set(voice_text)
    self.tts_tree.item(selected, values=current_values)
    return True


def _on_tts_mode_changed(self, event=None):
    mode = self.tts_mode_var.get()
    row_index = _selected_tts_order_index(self)
    _, current_values = _get_selected_tts_row(self)
    current_source = "local"
    if current_values and len(current_values) > 5:
        current_source = str(current_values[5] or "local")

    if mode == "自定义":
        # TTS -> 自定义：删除该条目已有缓存文件，防止与自定义文件混淆
        if current_source in ("local", "web", ""):
            _delete_tts_audio_by_index(self, row_index)
        self.custom_mode_combo.config(state="readonly")
        self.custom_action_button.config(state="active")
        _on_custom_mode_changed(self)
    else:
        # 自定义 -> TTS：删除该条目已上传/录制音频，防止索引错乱
        if current_source in ("custom_upload", "custom_record", "custom"):
            _delete_tts_audio_by_index(self, row_index)
        self.custom_mode_combo.config(state="disabled")
        self.custom_action_button.config(state="disabled")
        if self.if_tts_enabled.get():
            if current_source in ("custom_upload", "custom_record", "custom", ""):
                _set_selected_source(self, "local")


def _on_custom_mode_changed(self, event=None):
    custom_mode = self.custom_mode_var.get()
    if custom_mode == "直接录音":
        self.custom_action_button.config(text="开始录音")
        if self.if_tts_enabled.get():
            _set_selected_source(self, "custom_record", "自定义录音")
    else:
        self.custom_action_button.config(text="上传音频")
        if self.if_tts_enabled.get():
            _set_selected_source(self, "custom_upload", "自定义音频")


def _upload_custom_tts_audio(self):
    if not self.if_tts_enabled.get():
        return
    row_index = _selected_tts_order_index(self)
    if row_index is None:
        self.gui.warning(message="请先选择一个语音提示条目！")
        return

    picked = filedialog.askopenfilename(
        title="选择自定义音频",
        filetypes=[("音频文件", "*.wav *.mp3"), ("WAV", "*.wav"), ("MP3(将转为WAV)", "*.mp3")],
        parent=self.main_window,
    )
    if not picked:
        return

    ext = os.path.splitext(picked)[1].lower()
    if ext not in (".wav", ".mp3"):
        self.gui.warning(message="仅支持 .wav 或 .mp3 文件")
        return

    base_dir = os.path.join(".", "data", self.current_acount, "tts")
    os.makedirs(base_dir, exist_ok=True)
    target_path = os.path.join(base_dir, f"{row_index}.wav")

    for old_ext in (".wav", ".mp3"):
        old_path = os.path.join(base_dir, f"{row_index}{old_ext}")
        if old_path != target_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except Exception:
                pass

    try:
        _save_audio_max_10s(picked, target_path)
        _set_selected_source(self, "custom_upload", "自定义音频")
        self.gui.info(message=f"音频已导入(最多10秒，WAV): {target_path}")
    except Exception as e:
        self.gui.error(message=f"上传失败: {e}")


def _record_custom_tts_audio(self):
    if not self.if_tts_enabled.get():
        return

    row_index = _selected_tts_order_index(self)
    if row_index is None:
        self.gui.warning(message="请先选择一个语音提示条目！")
        return

    base_dir = os.path.join(".", "data", self.current_acount, "tts")
    os.makedirs(base_dir, exist_ok=True)
    target_path = os.path.join(base_dir, f"{row_index}.wav")

    popup = self.gui.create_toplevel(
        title="录制自定义音频",
        size=(360, 180),
        parent=self.main_window,
        resizable=(False, False),
        modal=False,
        center=True,
    )

    status_var = tk.StringVar(value="准备就绪")
    tk.Label(popup, text="点击开始录音，再点击停止并保存", font=self.mainpage_button_font).pack(pady=(15, 8))
    tk.Label(popup, textvariable=status_var, fg="#1d6f42", font=self.mainpage_button_font).pack()

    rec_state = {
        "recording": False,
        "frames": [],
        "thread": None,
        "stream": None,
        "pa": None,
        "rate": 16000,
        "chunk": 1024,
        "auto_stopped": False,
    }

    def _reader_loop():
        try:
            while rec_state["recording"]:
                rec_state["frames"].append(rec_state["stream"].read(rec_state["chunk"], exception_on_overflow=False))
        except Exception as e:
            status_var.set(f"录音失败: {e}")

    def _start():
        if rec_state["recording"]:
            return
        try:
            import pyaudio
            rec_state["pa"] = pyaudio.PyAudio()
            rec_state["stream"] = rec_state["pa"].open(
                format=pyaudio.paInt16,
                channels=1,
                rate=rec_state["rate"],
                input=True,
                frames_per_buffer=rec_state["chunk"],
            )
            rec_state["frames"] = []
            rec_state["recording"] = True
            rec_state["auto_stopped"] = False
            rec_state["thread"] = threading.Thread(target=_reader_loop, daemon=True)
            rec_state["thread"].start()
            status_var.set("录音中...")
            popup.after(10000, _auto_stop_if_needed)
        except Exception as e:
            status_var.set(f"录音启动失败: {e}")

    def _auto_stop_if_needed():
        if rec_state["recording"]:
            rec_state["auto_stopped"] = True
            _stop_and_save()

    def _stop_and_save():
        if not rec_state["recording"]:
            return
        rec_state["recording"] = False
        try:
            if rec_state["thread"]:
                rec_state["thread"].join(timeout=1.5)
        except Exception:
            pass
        try:
            if rec_state["stream"]:
                rec_state["stream"].stop_stream()
                rec_state["stream"].close()
        except Exception:
            pass

        sample_width = 2
        try:
            import pyaudio
            if rec_state["pa"]:
                sample_width = rec_state["pa"].get_sample_size(pyaudio.paInt16)
        except Exception:
            pass

        try:
            with wave.open(target_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(sample_width)
                wf.setframerate(rec_state["rate"])
                wf.writeframes(b"".join(rec_state["frames"]))
            old_mp3 = os.path.join(base_dir, f"{row_index}.mp3")
            if os.path.exists(old_mp3):
                try:
                    os.remove(old_mp3)
                except Exception:
                    pass
            _set_selected_source(self, "custom_record", "自定义录音")
            if rec_state.get("auto_stopped"):
                status_var.set(f"已达到10秒上限，自动保存: {target_path}")
            else:
                status_var.set(f"已保存: {target_path}")
        except Exception as e:
            status_var.set(f"保存失败: {e}")
        finally:
            try:
                if rec_state["pa"]:
                    rec_state["pa"].terminate()
            except Exception:
                pass

    def _close_popup():
        if rec_state["recording"]:
            _stop_and_save()
        popup.destroy()

    btn_row = tk.Frame(popup)
    btn_row.pack(pady=12)
    tk.Button(btn_row, text="开始录音", width=10, command=_start).pack(side="left", padx=6)
    tk.Button(btn_row, text="停止并保存", width=10, command=_stop_and_save).pack(side="left", padx=6)
    tk.Button(btn_row, text="关闭", width=8, command=_close_popup).pack(side="left", padx=6)

    popup.protocol("WM_DELETE_WINDOW", _close_popup)


def _run_custom_action(self):
    if self.custom_mode_var.get() == "直接录音":
        _record_custom_tts_audio(self)
    else:
        _upload_custom_tts_audio(self)


def _save_audio_max_10s(src_path, dst_path):
    """保存音频到 WAV(dst_path)，长度限制为前 10 秒。"""
    ext = os.path.splitext(dst_path)[1].lower()
    if ext != ".wav":
        raise ValueError("目标文件必须是 .wav")

    # 优先尝试 pydub（支持多格式）
    try:
        from pydub import AudioSegment
        seg = AudioSegment.from_file(src_path)
        seg = seg[:10000] if len(seg) > 10000 else seg
        seg.export(dst_path, format="wav")
        return
    except Exception:
        pass

    # 兜底：仅处理 WAV
    with wave.open(src_path, "rb") as rf:
        nch = rf.getnchannels()
        sw = rf.getsampwidth()
        fr = rf.getframerate()
        max_frames = int(fr * 10)
        frames = rf.readframes(max_frames)
    with wave.open(dst_path, "wb") as wf:
        wf.setnchannels(nch)
        wf.setsampwidth(sw)
        wf.setframerate(fr)
        wf.writeframes(frames)
