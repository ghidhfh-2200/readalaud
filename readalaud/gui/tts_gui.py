"""
TTS 语音提示相关 GUI 辅助函数：
    - 启用/禁用 TTS 控件
    - 音色选择窗口
    - 添加/删除时间点
    - 触发条件与语音内容弹窗
    - Treeview 交互回调（选中、音量、语速）
    - 测试语音 & 保存 TTS 设置
"""

import asyncio
import os
import shutil
import threading
import time
import wave
import pyttsx3
from PySide6 import QtCore, QtWidgets, QtGui
from .qt_helpers import ValueHolder, run_on_ui
from .. import tts


# ──────────────────────── 启用 / 禁用 ────────────────────────

def _enable_or_disable_tts_gui(self, state=None):
    if state == None:
        if self.if_tts_enabled.get() == False:
            self.add_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.time_and_text_button.setEnabled(False)
            self.voice_menu.setEnabled(False)
            self.volume_scale.setEnabled(False)
            self.speed_scale.setEnabled(False)
            self.more_local_button.setEnabled(False)
            self.more_web_button.setEnabled(False)
            self.tts_mode_combo.setEnabled(False)
            self.custom_mode_combo.setEnabled(False)
            self.custom_action_button.setEnabled(False)
        else:
            self.add_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.time_and_text_button.setEnabled(True)
            self.voice_menu.setEnabled(True)
            self.volume_scale.setEnabled(True)
            self.speed_scale.setEnabled(True)
            self.more_web_button.setEnabled(True)
            self.more_local_button.setEnabled(True)
            self.tts_mode_combo.setEnabled(True)
            if self.tts_mode_var.get() == "自定义":
                self.custom_mode_combo.setEnabled(True)
                self.custom_action_button.setEnabled(True)
            else:
                self.custom_mode_combo.setEnabled(False)
                self.custom_action_button.setEnabled(False)
    else:
        if state == False:
            self.if_tts_enabled.set(False)
            self.if_tts_checkbox.setChecked(False)
            self.add_button.setEnabled(False)
            self.delete_button.setEnabled(False)
            self.time_and_text_button.setEnabled(False)
            self.voice_menu.setEnabled(False)
            self.volume_scale.setEnabled(False)
            self.speed_scale.setEnabled(False)
            self.more_local_button.setEnabled(False)
            self.more_web_button.setEnabled(False)
            self.tts_mode_combo.setEnabled(False)
            self.custom_mode_combo.setEnabled(False)
            self.custom_action_button.setEnabled(False)
        else:
            self.if_tts_enabled.set(True)
            self.if_tts_checkbox.setChecked(True)
            self.add_button.setEnabled(True)
            self.delete_button.setEnabled(True)
            self.time_and_text_button.setEnabled(True)
            self.voice_menu.setEnabled(True)
            self.volume_scale.setEnabled(True)
            self.speed_scale.setEnabled(True)
            self.more_web_button.setEnabled(True)
            self.more_local_button.setEnabled(True)
            self.tts_mode_combo.setEnabled(True)
            if self.tts_mode_var.get() == "自定义":
                self.custom_mode_combo.setEnabled(True)
                self.custom_action_button.setEnabled(True)
            else:
                self.custom_mode_combo.setEnabled(False)
                self.custom_action_button.setEnabled(False)


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

    layout = QtWidgets.QVBoxLayout(self.more_voices_window)
    self.voice_listbox = QtWidgets.QTableWidget(0, 4)
    self.voice_listbox.setHorizontalHeaderLabels(["名称", "性别", "语言", "特征"])
    self.voice_listbox.verticalHeader().setVisible(False)
    self.voice_listbox.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    self.voice_listbox.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    layout.addWidget(self.voice_listbox)
    if source == "local":
        if self.all_local_voices == None:
            self.pyttsx3_engine = pyttsx3.init()
            self.all_local_voices = self.pyttsx3_engine.getProperty("voices")
        for voice in self.all_local_voices:
            row = self.voice_listbox.rowCount()
            self.voice_listbox.insertRow(row)
            self.voice_listbox.setItem(row, 0, QtWidgets.QTableWidgetItem(str(voice.name)))
            self.voice_listbox.setItem(row, 1, QtWidgets.QTableWidgetItem(str(voice.gender)))
            self.voice_listbox.setItem(row, 2, QtWidgets.QTableWidgetItem(str(voice.languages)))
            self.voice_listbox.setItem(row, 3, QtWidgets.QTableWidgetItem("None"))
    button_row = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_row)
    button_layout.setContentsMargins(0, 0, 0, 0)
    tips_label = QtWidgets.QLabel("语言zh-CN为中文, en开头为英文")
    ok_button = QtWidgets.QPushButton("确定")
    ok_button.clicked.connect(lambda: _select_voices_ok(self=self, source=source))
    button_layout.addWidget(tips_label)
    button_layout.addStretch(1)
    button_layout.addWidget(ok_button)
    layout.addWidget(button_row)
    self.more_voices_window.destroyed.connect(lambda _e=None: _destroy_all_voices_window(self))


def _select_voices_ok(self, source):
    try:
        row = self.voice_listbox.currentRow()
        if row < 0:
            raise IndexError()
        voice_name = self.voice_listbox.item(row, 0).text()
    except IndexError:
        self.gui.warning(message="请先选择一个音色！")
    try:
        self.voice_var.set(voice_name)
        get_tts_selected = self._get_selected_tts_row_id()
        _destroy_all_voices_window(self)
        current_values = self._get_tts_row_values(get_tts_selected)
        if source == "web":
            current_values[4] = "EdgeTTS Default"
        else:
            current_values[4] = voice_name
        current_values[5] = source
        self._set_tts_row_values(get_tts_selected, current_values)
    except IndexError as e:
        print(e)
        self.gui.warning(message="你还没有选择一个语音提示条目！")


def _destroy_all_voices_window(self):
    try:
        self.more_voices_window.close()
    except Exception:
        pass
    self.if_all_voices_window_showed = False


# ──────────────────────── Treeview 操作 ────────────────────────

def _tts_add_point(self):
    """添加时间点"""
    row = self.tts_tree.rowCount()
    self.tts_tree.insertRow(row)
    values = ["", "", "1.0", "1.0", "", "local"]
    for c, v in enumerate(values):
        self.tts_tree.setItem(row, c, QtWidgets.QTableWidgetItem(str(v)))


def _tts_delete_point(self):
    """删除时间点"""
    try:
        row = self.tts_tree.currentRow()
        if row >= 0:
            self.tts_tree.removeRow(row)
    except IndexError:
        pass


# ──────────────────────── Treeview / Scale 回调 ────────────────────────

def on_treeview_click(self, event, item):
    if not item:
        return
    self.volume_var.set(float(item[2]))
    self.speed_var.set(float(item[3]))
    self.voice_var.set(str(item[4]))
    self.content = str(item[1])
    source = str(item[5]) if len(item) > 5 else "local"
    if source in ("local", "web", ""):
        self.tts_mode_combo.setCurrentText("TTS")
    else:
        self.tts_mode_combo.setCurrentText("自定义")
    if source == "custom_record":
        self.custom_mode_combo.setCurrentText("直接录音")
    else:
        self.custom_mode_combo.setCurrentText("上传音频")
    _on_tts_mode_changed(self)


def volume_scale_change(self, event):
    """松开鼠标改变音量"""
    try:
        row = self.tts_tree.currentRow()
        if row >= 0:
            self.tts_tree.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{self.volume_var.get()}"))
    except IndexError:
        pass


def speed_scale_change(self, event):
    """松开鼠标改变语速"""
    try:
        row = self.tts_tree.currentRow()
        if row >= 0:
            self.tts_tree.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{self.speed_var.get()}"))
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
    popup_window.destroyed.connect(lambda _e=None: setattr(self, 'if_time_and_text_config_popup', False))

    # Try to get current selected tree item values to prefill fields
    get_time = ""
    get_content = ""
    get_source = "local"
    try:
        row = self.tts_tree.currentRow()
        if row >= 0:
            vals = [self.tts_tree.item(row, c).text() for c in range(self.tts_tree.columnCount())]
            get_time = vals[0] or ""
            get_content = vals[1] or ""
            if len(vals) > 5:
                get_source = vals[5] or "local"
    except Exception:
        pass

    # Top: trigger selector
    layout = QtWidgets.QVBoxLayout(popup_window)
    top_row = QtWidgets.QWidget()
    top_layout = QtWidgets.QHBoxLayout(top_row)
    top_layout.setContentsMargins(0, 0, 0, 0)
    top_layout.addWidget(QtWidgets.QLabel("触发条件："))
    trigger_var = ValueHolder("")
    trigger_options = [
        "当音量达到",
        "当音量低于",
        "当达到目标",
        "当时间点达到",
        "当任务进度达到",
        "检测到异常停顿",
    ]
    trigger_combo = QtWidgets.QComboBox()
    trigger_combo.addItems(trigger_options)
    trigger_combo.currentTextChanged.connect(trigger_var.set)
    top_layout.addWidget(trigger_combo, 1)
    layout.addWidget(top_row)

    # Middle: stack of frames for each trigger's specific settings
    stack_holder = QtWidgets.QStackedWidget()
    layout.addWidget(stack_holder)

    def make_frame(label_text, value_holder=None):
        w = QtWidgets.QWidget()
        l = QtWidgets.QHBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.addWidget(QtWidgets.QLabel(label_text))
        if value_holder is not None:
            entry = QtWidgets.QLineEdit()
            entry.setFixedWidth(120)
            entry.textChanged.connect(lambda t: value_holder.set(float(t) if t else 0.0))
            l.addWidget(entry)
        return w

    vol_above_var = ValueHolder(0.0)
    vol_below_var = ValueHolder(0.0)
    time_point_var = ValueHolder(0.0)
    progress_var = ValueHolder(0.0)
    pause_var = ValueHolder(0.0)

    vol_above_frame = make_frame("阈值(dB)：", vol_above_var)
    vol_below_frame = make_frame("阈值(dB)：", vol_below_var)
    goal_frame = make_frame("目标到达触发（无额外参数）")
    time_point_frame = make_frame("时间点(分钟)：", time_point_var)
    progress_frame = make_frame("任务进度(百分比)：", progress_var)
    pause_frame = make_frame("异常停顿时间(秒)：", pause_var)
    for f in (vol_above_frame, vol_below_frame, goal_frame, time_point_frame, progress_frame, pause_frame):
        stack_holder.addWidget(f)

    # Common: content text
    content_row = QtWidgets.QWidget()
    content_layout = QtWidgets.QHBoxLayout(content_row)
    content_layout.setContentsMargins(0, 0, 0, 0)
    content_layout.addWidget(QtWidgets.QLabel("语音内容："))
    content_var = ValueHolder(get_content)
    content_entry = QtWidgets.QLineEdit(get_content)
    content_entry.textChanged.connect(content_var.set)
    content_layout.addWidget(content_entry, 1)
    if get_source in ("custom_upload", "custom_record", "custom"):
        content_entry.setEnabled(False)
    layout.addWidget(content_row)

    # Buttons: Save / Cancel
    btn_row = QtWidgets.QWidget()
    btn_layout = QtWidgets.QHBoxLayout(btn_row)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    btn_layout.addStretch(1)

    def show_frame_for_trigger(*_):
        sel = trigger_var.get()
        mapping = {
            "当音量达到": vol_above_frame,
            "当音量低于": vol_below_frame,
            "当达到目标": goal_frame,
            "当时间点达到": time_point_frame,
            "当任务进度达到": progress_frame,
            "检测到异常停顿": pause_frame,
        }
        stack_holder.setCurrentWidget(mapping.get(sel, vol_above_frame))

    trigger_combo.currentTextChanged.connect(lambda _v: show_frame_for_trigger())

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
            row = self.tts_tree.currentRow()
            get_values = [self.tts_tree.item(row, c).text() for c in range(self.tts_tree.columnCount())]
            get_values[0] = time_display
            get_values[1] = self.content
            self._set_tts_row_values(row, get_values)
        except Exception:
            row = self.tts_tree.rowCount()
            self.tts_tree.insertRow(row)
            values = [time_display, self.content, self.volume_var.get(), self.speed_var.get(), self.voice_var.get(), "local"]
            self._set_tts_row_values(row, values)
        self.if_time_and_text_config_popup = False
        popup_window.close()

    def on_cancel():
        self.if_time_and_text_config_popup = False
        popup_window.destroy()

    save_btn = QtWidgets.QPushButton("保存并关闭")
    save_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    save_btn.clicked.connect(on_save_and_close)
    cancel_btn = QtWidgets.QPushButton("取消")
    cancel_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    cancel_btn.clicked.connect(on_cancel)
    btn_layout.addWidget(save_btn)
    btn_layout.addWidget(cancel_btn)
    layout.addWidget(btn_row)


# ──────────────────────── 测试 TTS ────────────────────────

def test_tts(self):
    """语音生成器测试 GUI 对接"""
    if self.if_generating_ttstest == True:
        return
    else:
        self.if_generating_ttstest = True
    try:
        row = self.tts_tree.currentRow()
        get_source = self.tts_tree.item(row, 5).text()
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
            row = self.tts_tree.currentRow()
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
                    run_on_ui(lambda: self.gui.error(message=f"自定义音频测试失败: {e}"))
                finally:
                    def _finish():
                        self._tts_test_play_obj = None
                        self._tts_test_stop_requested = False
                        self.if_generating_ttstest = False
                    run_on_ui(_finish)

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
    value_list = []
    for row in range(self.tts_tree.rowCount()):
        row_values = [self.tts_tree.item(row, c).text() if self.tts_tree.item(row, c) else "" for c in range(6)]
        while len(row_values) < 6:
            row_values.append("")
        value_list.append(row_values)
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
        row = self.tts_tree.currentRow()
        if row < 0:
            return None, None
        vals = [self.tts_tree.item(row, c).text() for c in range(self.tts_tree.columnCount())]
        return row, vals
    except Exception:
        return None, None


def _selected_tts_order_index(self):
    selected, _ = _get_selected_tts_row(self)
    if selected is None:
        return None
    return selected


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
    self._set_tts_row_values(selected, current_values)
    return True


def _on_tts_mode_changed(self, event=None):
    mode = self.tts_mode_combo.currentText()
    row_index = _selected_tts_order_index(self)
    _, current_values = _get_selected_tts_row(self)
    current_source = "local"
    if current_values and len(current_values) > 5:
        current_source = str(current_values[5] or "local")

    if mode == "自定义":
        # TTS -> 自定义：删除该条目已有缓存文件，防止与自定义文件混淆
        if current_source in ("local", "web", ""):
            _delete_tts_audio_by_index(self, row_index)
        self.custom_mode_combo.setEnabled(True)
        self.custom_action_button.setEnabled(True)
        _on_custom_mode_changed(self)
    else:
        # 自定义 -> TTS：删除该条目已上传/录制音频，防止索引错乱
        if current_source in ("custom_upload", "custom_record", "custom"):
            _delete_tts_audio_by_index(self, row_index)
        self.custom_mode_combo.setEnabled(False)
        self.custom_action_button.setEnabled(False)
        if self.if_tts_enabled.get():
            if current_source in ("custom_upload", "custom_record", "custom", ""):
                _set_selected_source(self, "local")


def _on_custom_mode_changed(self, event=None):
    custom_mode = self.custom_mode_combo.currentText()
    if custom_mode == "直接录音":
        self.custom_action_button.setText("开始录音")
        if self.if_tts_enabled.get():
            _set_selected_source(self, "custom_record", "自定义录音")
    else:
        self.custom_action_button.setText("上传音频")
        if self.if_tts_enabled.get():
            _set_selected_source(self, "custom_upload", "自定义音频")


def _upload_custom_tts_audio(self):
    if not self.if_tts_enabled.get():
        return
    row_index = _selected_tts_order_index(self)
    if row_index is None:
        self.gui.warning(message="请先选择一个语音提示条目！")
        return

    picked, _ = QtWidgets.QFileDialog.getOpenFileName(
        self.main_window,
        "选择自定义音频",
        "",
        "音频文件 (*.wav *.mp3)"
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
    layout = QtWidgets.QVBoxLayout(popup)

    status_var = ValueHolder("准备就绪")
    title_lbl = QtWidgets.QLabel("点击开始录音，再点击停止并保存")
    title_lbl.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    status_lbl = QtWidgets.QLabel(status_var.get())
    status_lbl.setStyleSheet("color: #1d6f42;")
    status_var.changed.connect(status_lbl.setText)
    layout.addWidget(title_lbl)
    layout.addWidget(status_lbl)

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
            QtCore.QTimer.singleShot(10000, _auto_stop_if_needed)
        except Exception as e:
            print(e)
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

    btn_row = QtWidgets.QWidget()
    btn_layout = QtWidgets.QHBoxLayout(btn_row)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    start_btn = QtWidgets.QPushButton("开始录音")
    start_btn.clicked.connect(_start)
    stop_btn = QtWidgets.QPushButton("停止并保存")
    stop_btn.clicked.connect(_stop_and_save)
    close_btn = QtWidgets.QPushButton("关闭")
    close_btn.clicked.connect(_close_popup)
    btn_layout.addWidget(start_btn)
    btn_layout.addWidget(stop_btn)
    btn_layout.addWidget(close_btn)
    layout.addWidget(btn_row)
    popup.destroyed.connect(lambda _e=None: _close_popup())


def _run_custom_action(self):
    if self.custom_mode_combo.currentText() == "直接录音":
        _record_custom_tts_audio(self)
    else:
        _upload_custom_tts_audio(self)


def _get_selected_tts_row_id(self):
    row = self.tts_tree.currentRow()
    return row if row >= 0 else None


def _get_tts_row_values(self, row):
    if row is None or row < 0:
        return None
    return [self.tts_tree.item(row, c).text() if self.tts_tree.item(row, c) else "" for c in range(6)]


def _set_tts_row_values(self, row, values):
    if row is None or row < 0:
        return
    while len(values) < 6:
        values.append("")
    for c in range(6):
        self.tts_tree.setItem(row, c, QtWidgets.QTableWidgetItem(str(values[c])))


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
