"""
设置页面 GUI：朗读设置、语音提示设置、账号与安全、个性化。

所有修改即时更新全局缓存，退出时异步保存，无需「确定/保存」按钮。
"""
from PySide6 import QtCore, QtWidgets, QtGui
from markdown import markdown
from ..settings import _load_settings, update_setting, get_tts_cache, update_tts_cache
from ..settings.tts_settings import _parse_trigger_display
from .qt_helpers import ValueHolder
from .qt_helpers import run_on_ui
from .tts_gui import (
    on_treeview_click,
    volume_scale_change,
    speed_scale_change,
    test_tts,
    stop_tts_test,
)


def _get_selected_tts_row_values(self):
    try:
        row = self.tts_tree.currentRow()
        if row < 0:
            return None
        return [self.tts_tree.item(row, c).text() for c in range(self.tts_tree.columnCount())]
    except Exception:
        return None


def _build_tts_cache_from_tree(self):
    """从 QTableWidget 构建 TTS 缓存字典（供保存前调用）。"""
    if self.if_tts_enabled.get():
        cache = {}
        for row in range(self.tts_tree.rowCount()):
            row_values = [self.tts_tree.item(row, c).text() if self.tts_tree.item(row, c) else ""
                          for c in range(6)]
            while len(row_values) < 6:
                row_values.append("")
            condition, value, display = _parse_trigger_display(row_values[0])
            source = row_values[5] or "local"
            cache[row] = {
                "condition": condition,
                "value":     value,
                "display":   display,
                "text":      row_values[1],
                "rate":      row_values[2],
                "volume":    row_values[3],
                "voice":     row_values[4],
                "source":    source,
            }
        update_tts_cache(cache)
    else:
        update_tts_cache({})


def _generate_settings_gui(self):
    if self.if_settings_show:
        return
    self.if_settings_show = True

    # main frame
    self.settings_frame = QtWidgets.QWidget()
    self.settings_layout = QtWidgets.QVBoxLayout(self.settings_frame)
    self.settings_layout.setContentsMargins(10, 10, 10, 10)
    self.main_paned_window.addWidget(self.settings_frame, 7)
    if self.if_main_window_show:
        self.content_frame.deleteLater()
        self.if_main_window_show = False

    # notebooks
    notebook = QtWidgets.QTabWidget()
    account_frame = QtWidgets.QWidget()
    read_frame = QtWidgets.QWidget()
    customize_frame = QtWidgets.QWidget()
    llm_frame = QtWidgets.QWidget()
    notebook.addTab(read_frame, "朗读设置")
    notebook.addTab(account_frame, "账号与安全")
    notebook.addTab(customize_frame, "个性化")
    notebook.addTab(llm_frame, "AI 报告")
    self.settings_layout.addWidget(notebook, 1)

    # ── account frame ──
    _build_account_tab(self, account_frame)

    # ── read frame（基础设置 + TTS 设置） ──
    _build_reading_tab(self, read_frame)

    # ── customize frame ──
    _build_customize_tab(self, customize_frame)

    # ── llm frame ──
    _build_llm_tab(self, llm_frame)

    # 返回按钮 — 构建 TTS 缓存，即时保存设置到磁盘，然后导航回去
    def _on_back():
        _build_tts_cache_from_tree(self)
        self.save_settings_now()
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])

    back_button = QtWidgets.QPushButton("返回")
    back_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    back_button.setFixedWidth(120)
    back_button.clicked.connect(_on_back)
    self.settings_layout.addWidget(back_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)
    _load_settings(self=self)


# ═══════════════════════ 账号 Tab ═══════════════════════

def _build_account_tab(self, account_frame):
    layout = QtWidgets.QVBoxLayout(account_frame)
    account_management_label_frame = QtWidgets.QGroupBox("账户管理")
    account_management_label_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    layout.addWidget(account_management_label_frame)

    am_layout = QtWidgets.QVBoxLayout(account_management_label_frame)

    # 账户名称行（无确定按钮，退出时自动处理）
    name_row = QtWidgets.QWidget()
    name_layout = QtWidgets.QHBoxLayout(name_row)
    name_layout.setContentsMargins(0, 0, 0, 0)
    self.account_name_label = QtWidgets.QLabel("账户名称: ")
    self.account_name_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_name_value = ValueHolder("")
    name_entry = QtWidgets.QLineEdit()
    name_entry.setFont(QtGui.QFont("微软雅黑", 13))
    name_entry.setMinimumWidth(260)
    self.settings_name_value.changed.connect(name_entry.setText)
    name_entry.setText(self.settings_name_value.get())
    name_entry.textChanged.connect(self.settings_name_value.set)
    name_layout.addWidget(self.account_name_label)
    name_layout.addWidget(name_entry)
    am_layout.addWidget(name_row)

    # 密码行（无确定按钮，退出时自动处理）
    password_row = QtWidgets.QWidget()
    password_layout = QtWidgets.QHBoxLayout(password_row)
    password_layout.setContentsMargins(0, 0, 0, 0)
    password_label = QtWidgets.QLabel("设置新密码：")
    password_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_password_value = ValueHolder("")
    password_entry = QtWidgets.QLineEdit()
    password_entry.setFont(QtGui.QFont("微软雅黑", 13))
    password_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
    password_entry.setMinimumWidth(260)
    self.settings_password_value.changed.connect(password_entry.setText)
    password_entry.setText(self.settings_password_value.get())
    password_entry.textChanged.connect(self.settings_password_value.set)
    password_layout.addWidget(password_label)
    password_layout.addWidget(password_entry)
    am_layout.addWidget(password_row)

    # 账户操作
    account_operation = QtWidgets.QGroupBox("账户操作")
    account_operation.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    layout.addWidget(account_operation)
    op_layout = QtWidgets.QHBoxLayout(account_operation)

    delete_acount = QtWidgets.QPushButton("注销账号")
    delete_acount.setStyleSheet("color: red;")
    delete_acount.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    delete_acount.clicked.connect(lambda: self.delete_the_account())
    reset_acount = QtWidgets.QPushButton("重置全部数据")
    reset_acount.setStyleSheet("color: red;")
    reset_acount.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    reset_acount.clicked.connect(lambda: self.reset_account_data())
    logout_btn = QtWidgets.QPushButton("退出登录")
    logout_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    logout_btn.clicked.connect(lambda: self.logout())
    log_viewer_btn = QtWidgets.QPushButton("系统日志")
    log_viewer_btn.setStyleSheet("color: blue;")
    log_viewer_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    log_viewer_btn.clicked.connect(lambda: self.show_log_viewer())
    op_layout.addWidget(delete_acount)
    op_layout.addWidget(reset_acount)
    op_layout.addWidget(logout_btn)
    op_layout.addWidget(log_viewer_btn)


# ═══════════════════════ 朗读设置 Tab ═══════════════════════

def _build_reading_tab(self, read_frame):
    layout = QtWidgets.QVBoxLayout(read_frame)
    # ── 基础设置 ──
    read_basic_settings_labelframe = QtWidgets.QGroupBox("基础设置")
    read_basic_settings_labelframe.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    layout.addWidget(read_basic_settings_labelframe)
    basic_layout = QtWidgets.QVBoxLayout(read_basic_settings_labelframe)

    # 目标设定（即时更新缓存，无确定按钮）
    goal_row = QtWidgets.QWidget()
    goal_layout = QtWidgets.QHBoxLayout(goal_row)
    goal_layout.setContentsMargins(0, 0, 0, 0)
    self.settings_goal_label = QtWidgets.QLabel("目标设定(分钟):")
    self.settings_goal_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_goal_value = ValueHolder(0)
    goal_entry = QtWidgets.QLineEdit()
    goal_entry.setFont(QtGui.QFont("微软雅黑", 13))
    goal_entry.setMinimumWidth(260)
    self.settings_goal_value.changed.connect(lambda v: goal_entry.setText(str(v)))
    goal_entry.setText(str(self.settings_goal_value.get()))
    goal_entry.textChanged.connect(lambda t: _on_goal_changed(self, t))
    goal_layout.addWidget(self.settings_goal_label)
    goal_layout.addWidget(goal_entry)
    basic_layout.addWidget(goal_row)

    # 停顿容忍间隔（即时更新缓存，无确定按钮）
    stop_row = QtWidgets.QWidget()
    stop_layout = QtWidgets.QHBoxLayout(stop_row)
    stop_layout.setContentsMargins(0, 0, 0, 0)
    self.stop_dur_label = QtWidgets.QLabel("停顿容忍间隔(秒):")
    self.stop_dur_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_stop_dur_value = ValueHolder(0.0)
    stop_dur_entry = QtWidgets.QLineEdit()
    stop_dur_entry.setFont(QtGui.QFont("微软雅黑", 13))
    stop_dur_entry.setMinimumWidth(260)
    self.settings_stop_dur_value.changed.connect(lambda v: stop_dur_entry.setText(str(v)))
    stop_dur_entry.setText(str(self.settings_stop_dur_value.get()))
    stop_dur_entry.textChanged.connect(lambda t: _on_stop_dur_changed(self, t))
    stop_layout.addWidget(self.stop_dur_label)
    stop_layout.addWidget(stop_dur_entry)
    basic_layout.addWidget(stop_row)

    # 分贝阈值（即时更新缓存，无确定按钮）
    db_row = QtWidgets.QWidget()
    db_layout = QtWidgets.QHBoxLayout(db_row)
    db_layout.setContentsMargins(0, 0, 0, 0)
    self.settings_db_label = QtWidgets.QLabel("分贝阈值(dB):")
    self.settings_db_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_db_value = ValueHolder(0.0)
    db_entry = QtWidgets.QLineEdit()
    db_entry.setFont(QtGui.QFont("微软雅黑", 13))
    db_entry.setMinimumWidth(260)
    self.settings_db_value.changed.connect(lambda v: db_entry.setText(str(v)))
    db_entry.setText(str(self.settings_db_value.get()))
    db_entry.textChanged.connect(lambda t: _on_db_level_changed(self, t))
    db_layout.addWidget(self.settings_db_label)
    db_layout.addWidget(db_entry)
    basic_layout.addWidget(db_row)

    # ── 语音提示设置 ──
    _build_tts_settings_section(self, read_frame)


# ── 即时缓存更新回调 ──────────────────────────────────────

def _on_goal_changed(self, text):
    try:
        val = float(text) if text else 0
    except ValueError:
        return
    self.settings_goal_value.set(val)
    update_setting("goal", int(val * 60))


def _on_stop_dur_changed(self, text):
    try:
        val = float(text) if text else 0.0
    except ValueError:
        return
    self.settings_stop_dur_value.set(val)
    update_setting("stop-dur", val)


def _on_db_level_changed(self, text):
    try:
        val = float(text) if text else 0.0
    except ValueError:
        return
    self.settings_db_value.set(val)
    update_setting("db-level", val)


# ═══════════════════════ TTS 设置区 ═══════════════════════

def _build_tts_settings_section(self, read_frame):
    """构建语音提示设置区域（TTS Treeview + 音色/音量/语速控件），无保存按钮。"""
    read_settings_frame = QtWidgets.QGroupBox("语音提示设置")
    read_settings_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    read_layout = read_frame.layout() or QtWidgets.QVBoxLayout(read_frame)
    read_layout.addWidget(read_settings_frame)
    settings_layout = QtWidgets.QVBoxLayout(read_settings_frame)

    checkbox_frame = QtWidgets.QWidget()
    checkbox_layout = QtWidgets.QHBoxLayout(checkbox_frame)
    checkbox_layout.setContentsMargins(0, 0, 0, 0)
    self.if_tts_enabled = ValueHolder(False)
    self.if_tts_checkbox = QtWidgets.QCheckBox("启用语音提示")
    self.if_tts_checkbox.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.if_tts_checkbox.toggled.connect(lambda v: self.if_tts_enabled.set(v))
    self.if_tts_checkbox.toggled.connect(lambda v: _on_tts_toggled(self, v))
    self.if_tts_checkbox.toggled.connect(lambda _v: self.enable_or_disable_tts_gui())
    checkbox_layout.addWidget(self.if_tts_checkbox)
    settings_layout.addWidget(checkbox_frame)

    # TTS settings container
    self.settings_container = QtWidgets.QWidget()
    self.settings_container_layout = QtWidgets.QVBoxLayout(self.settings_container)
    self.settings_container_layout.setContentsMargins(5, 5, 5, 5)
    settings_layout.addWidget(self.settings_container)

    # Treeview frame
    table_frame = QtWidgets.QWidget()
    table_layout = QtWidgets.QVBoxLayout(table_frame)
    table_layout.setContentsMargins(0, 0, 0, 0)
    self.tts_tree = QtWidgets.QTableWidget(0, 6)
    self.tts_tree.setHorizontalHeaderLabels(["触发条件", "语音内容", "音量", "语速", "音色", "来源"])
    self.tts_tree.verticalHeader().setVisible(False)
    self.tts_tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    self.tts_tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    self.tts_tree.itemSelectionChanged.connect(lambda: on_treeview_click(self, None, _get_selected_tts_row_values(self)))
    table_layout.addWidget(self.tts_tree)
    self.settings_container_layout.addWidget(table_frame, 1)

    # Buttons frame
    button_frame = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_frame)
    button_layout.setContentsMargins(0, 0, 0, 0)

    self.add_button = QtWidgets.QPushButton("添加时间点")
    self.add_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.add_button.clicked.connect(lambda: self.tts_add_point())
    button_layout.addWidget(self.add_button)

    self.delete_button = QtWidgets.QPushButton("删除时间点")
    self.delete_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.delete_button.clicked.connect(lambda: self.tts_delete_point())
    button_layout.addWidget(self.delete_button)

    self.time_and_text_button = QtWidgets.QPushButton("时间点&语音内容")
    self.time_and_text_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.time_and_text_button.clicked.connect(lambda: self.pop_up_time_and_text_config_window())
    button_layout.addWidget(self.time_and_text_button)
    self.settings_container_layout.addWidget(button_frame)

    # Voice configuration frame
    voice_config_frame = QtWidgets.QGroupBox("语音配置")
    voice_config_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    voice_config_layout = QtWidgets.QVBoxLayout(voice_config_frame)
    self.settings_container_layout.addWidget(voice_config_frame)

    voices_frame = QtWidgets.QWidget()
    voices_layout = QtWidgets.QHBoxLayout(voices_frame)
    voices_layout.setContentsMargins(0, 0, 0, 0)

    voices_layout.addWidget(QtWidgets.QLabel("选择音色:"))
    self.voice_var = ValueHolder("")
    self.voice_menu = QtWidgets.QLabel("未选择")
    self.voice_var.changed.connect(self.voice_menu.setText)
    voices_layout.addWidget(self.voice_menu, 1)
    self.more_local_button = QtWidgets.QPushButton("更多(本地)")
    self.more_local_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.more_local_button.clicked.connect(lambda: self.generate_more_vloices_window("local"))
    self.more_web_button = QtWidgets.QPushButton("更多(网络)")
    self.more_web_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.more_web_button.clicked.connect(lambda: self.generate_more_vloices_window("web"))
    voices_layout.addWidget(self.more_web_button)
    voices_layout.addWidget(self.more_local_button)
    voice_config_layout.addWidget(voices_frame)

    source_frame = QtWidgets.QWidget()
    source_layout = QtWidgets.QHBoxLayout(source_frame)
    source_layout.setContentsMargins(0, 0, 0, 0)
    source_layout.addWidget(QtWidgets.QLabel("语音方式:"))

    self.tts_mode_var = ValueHolder("TTS")
    self.tts_mode_combo = QtWidgets.QComboBox()
    self.tts_mode_combo.addItems(["TTS", "自定义"])
    self.tts_mode_combo.currentTextChanged.connect(lambda v: self.tts_mode_var.set(v))
    self.tts_mode_combo.currentTextChanged.connect(lambda _v: self.on_tts_mode_changed(None))
    source_layout.addWidget(self.tts_mode_combo)

    self.custom_mode_var = ValueHolder("上传音频")
    self.custom_mode_combo = QtWidgets.QComboBox()
    self.custom_mode_combo.addItems(["上传音频", "直接录音"])
    self.custom_mode_combo.currentTextChanged.connect(lambda v: self.custom_mode_var.set(v))
    self.custom_mode_combo.currentTextChanged.connect(lambda _v: self.on_custom_mode_changed(None))
    self.custom_mode_combo.setEnabled(False)
    source_layout.addWidget(self.custom_mode_combo)

    self.custom_action_button = QtWidgets.QPushButton("上传音频")
    self.custom_action_button.setEnabled(False)
    self.custom_action_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.custom_action_button.clicked.connect(lambda: self.run_custom_tts_action())
    source_layout.addWidget(self.custom_action_button)
    voice_config_layout.addWidget(source_frame)

    # Volume control
    volume_frame = QtWidgets.QWidget()
    volume_layout = QtWidgets.QHBoxLayout(volume_frame)
    volume_layout.setContentsMargins(0, 0, 0, 0)
    volume_layout.addWidget(QtWidgets.QLabel("音量:"))
    self.volume_var = ValueHolder(1.0)
    self.volume_scale = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    self.volume_scale.setRange(-10, 10)
    self.volume_scale.setValue(10)
    self.volume_scale.valueChanged.connect(lambda v: self.volume_var.set(v / 10))
    self.volume_scale.sliderReleased.connect(lambda: volume_scale_change(self, None))
    volume_layout.addWidget(self.volume_scale, 1)
    voice_config_layout.addWidget(volume_frame)

    # Speed control
    speed_frame = QtWidgets.QWidget()
    speed_layout = QtWidgets.QHBoxLayout(speed_frame)
    speed_layout.setContentsMargins(0, 0, 0, 0)
    speed_layout.addWidget(QtWidgets.QLabel("语速:"))
    self.speed_var = ValueHolder(1.0)
    self.speed_scale = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    self.speed_scale.setRange(-10, 10)
    self.speed_scale.setValue(10)
    self.speed_scale.valueChanged.connect(lambda v: self.speed_var.set(v / 10))
    self.speed_scale.sliderReleased.connect(lambda: speed_scale_change(self, None))
    speed_layout.addWidget(self.speed_scale, 1)
    voice_config_layout.addWidget(speed_frame)

    # Test buttons（只保留测试，移除保存）
    buttons_frame = QtWidgets.QWidget()
    buttons_layout = QtWidgets.QHBoxLayout(buttons_frame)
    buttons_layout.setContentsMargins(0, 0, 0, 0)
    buttons_layout.addStretch(1)
    self.test_button = QtWidgets.QPushButton("测试语音")
    self.test_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.test_button.clicked.connect(lambda: test_tts(self))
    buttons_layout.addWidget(self.test_button)
    self.stop_test_button = QtWidgets.QPushButton("停止测试")
    self.stop_test_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.stop_test_button.clicked.connect(lambda: stop_tts_test(self))
    buttons_layout.addWidget(self.stop_test_button)
    self.settings_container_layout.addWidget(buttons_frame)


def _on_tts_toggled(self, enabled):
    """TTS 开关切换时即时更新缓存。"""
    update_setting("if_tts", 1 if enabled else 0)
    if not enabled:
        update_tts_cache({})


# ═══════════════════════ 个性化 Tab ═══════════════════════

def _build_customize_tab(self, customize_frame):
    self.get_style_list = QtWidgets.QStyleFactory.keys()
    layout = QtWidgets.QVBoxLayout(customize_frame)
    customize_label_frame = QtWidgets.QGroupBox("选择样式")
    customize_label_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    layout.addWidget(customize_label_frame)
    box_layout = QtWidgets.QVBoxLayout(customize_label_frame)
    self.customize_listbox = QtWidgets.QListWidget()
    for i in self.get_style_list:
        self.customize_listbox.addItem(i)
    box_layout.addWidget(self.customize_listbox)
    # 选择即切换，无确认按钮
    self.customize_listbox.currentRowChanged.connect(lambda _: self.change_theme())


# ═══════════════════════ AI 报告 (LLM) Tab ═══════════════════════

def _build_llm_tab(self, llm_frame):
    """构建 LLM / AI 朗读报告设置页面（OpenAI 兼容接口）。"""
    from ..audio.llm_report import get_llm_config

    layout = QtWidgets.QVBoxLayout(llm_frame)
    layout.setSpacing(12)

    cfg = get_llm_config()

    # ── 启用开关 ──
    enable_frame = QtWidgets.QWidget()
    enable_layout = QtWidgets.QHBoxLayout(enable_frame)
    enable_layout.setContentsMargins(0, 0, 0, 0)
    self.settings_llm_enabled = ValueHolder(cfg.get("llm_enabled", True))
    llm_checkbox = QtWidgets.QCheckBox("启用 AI 朗读报告（需要大模型 API）")
    llm_checkbox.setFont(QtGui.QFont("微软雅黑", 12))
    llm_checkbox.setChecked(self.settings_llm_enabled.get())
    llm_checkbox.toggled.connect(lambda v: self.settings_llm_enabled.set(v))
    llm_checkbox.toggled.connect(lambda v: update_setting("llm_enabled", v))
    enable_layout.addWidget(llm_checkbox)
    layout.addWidget(enable_frame)

    # ── 说明 ──
    info_label = QtWidgets.QLabel(
        "💡 AI 报告通过 OpenAI 兼容接口调用大模型（如 Qwen、DeepSeek、GPT 等）分析朗读数据。\n"
        "请填写你的 API Key、Base URL 和模型名称。支持任何兼容 OpenAI responses.create 的接口。"
    )
    info_label.setWordWrap(True)
    info_label.setStyleSheet("color: #6c757d; font-size: 11px;")
    layout.addWidget(info_label)

    # ── API 配置 ──
    api_frame = QtWidgets.QGroupBox("API 配置")
    api_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    api_layout = QtWidgets.QVBoxLayout(api_frame)

    # API Key 行
    key_row = QtWidgets.QWidget()
    key_layout = QtWidgets.QHBoxLayout(key_row)
    key_layout.setContentsMargins(0, 0, 0, 0)
    key_label = QtWidgets.QLabel("API Key:")
    key_label.setFont(QtGui.QFont("微软雅黑", 12))
    key_label.setMinimumWidth(100)
    self.settings_llm_api_key = ValueHolder(cfg.get("llm_api_key", ""))
    key_entry = QtWidgets.QLineEdit()
    key_entry.setFont(QtGui.QFont("微软雅黑", 11))
    key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
    key_entry.setPlaceholderText("必填：输入 API Key，如 sk-...")
    key_entry.setText(self.settings_llm_api_key.get())
    key_entry.textChanged.connect(lambda t: self.settings_llm_api_key.set(t))
    key_entry.textChanged.connect(lambda t: update_setting("llm_api_key", t))
    key_layout.addWidget(key_label)
    key_layout.addWidget(key_entry, 1)

    show_key_btn = QtWidgets.QPushButton("👁")
    show_key_btn.setFixedWidth(36)
    show_key_btn.setToolTip("显示/隐藏 API Key")
    def _toggle_key_visibility():
        if key_entry.echoMode() == QtWidgets.QLineEdit.EchoMode.Password:
            key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Normal)
            show_key_btn.setText("🙈")
        else:
            key_entry.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
            show_key_btn.setText("👁")
    show_key_btn.clicked.connect(_toggle_key_visibility)
    key_layout.addWidget(show_key_btn)

    api_layout.addWidget(key_row)

    # Base URL 行
    url_row = QtWidgets.QWidget()
    url_layout = QtWidgets.QHBoxLayout(url_row)
    url_layout.setContentsMargins(0, 0, 0, 0)
    url_label = QtWidgets.QLabel("Base URL:")
    url_label.setFont(QtGui.QFont("微软雅黑", 12))
    url_label.setMinimumWidth(100)
    self.settings_llm_base_url = ValueHolder(cfg.get("llm_base_url", ""))
    url_entry = QtWidgets.QLineEdit()
    url_entry.setFont(QtGui.QFont("微软雅黑", 11))
    url_entry.setPlaceholderText("必填：如 https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1")
    url_entry.setText(self.settings_llm_base_url.get())
    url_entry.textChanged.connect(lambda t: self.settings_llm_base_url.set(t))
    url_entry.textChanged.connect(lambda t: update_setting("llm_base_url", t))
    url_layout.addWidget(url_label)
    url_layout.addWidget(url_entry, 1)
    api_layout.addWidget(url_row)

    # Model 行
    model_row = QtWidgets.QWidget()
    model_layout = QtWidgets.QHBoxLayout(model_row)
    model_layout.setContentsMargins(0, 0, 0, 0)
    model_label = QtWidgets.QLabel("模型名称:")
    model_label.setFont(QtGui.QFont("微软雅黑", 12))
    model_label.setMinimumWidth(100)
    self.settings_llm_model = ValueHolder(cfg.get("llm_model", ""))
    model_entry = QtWidgets.QLineEdit()
    model_entry.setFont(QtGui.QFont("微软雅黑", 11))
    model_entry.setPlaceholderText("必填：如 qwen3.7-plus / deepseek-chat / gpt-4o")
    model_entry.setText(self.settings_llm_model.get())
    model_entry.textChanged.connect(lambda t: self.settings_llm_model.set(t))
    model_entry.textChanged.connect(lambda t: update_setting("llm_model", t))
    model_layout.addWidget(model_label)
    model_layout.addWidget(model_entry, 1)
    api_layout.addWidget(model_row)

    layout.addWidget(api_frame)

    # ── 预设快速切换 ──
    presets_frame = QtWidgets.QGroupBox("快速配置预设（仅填充 URL 和模型，Key 需自行填写）")
    presets_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    presets_layout = QtWidgets.QHBoxLayout(presets_frame)

    presets = [
        ("阿里云百炼 Qwen3.7", "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1", "qwen3.7-plus"),
        ("阿里云百炼 Qwen-Max", "https://dashscope.aliyuncs.com/api/v2/apps/protocols/compatible-mode/v1", "qwen-max"),
        ("DeepSeek 官方", "https://api.deepseek.com", "deepseek-chat"),
        ("OpenAI 官方", "https://api.openai.com/v1", "gpt-4o"),
    ]

    for name, base_url, model in presets:
        btn = QtWidgets.QPushButton(name)
        btn.setFont(QtGui.QFont("微软雅黑", 9))
        btn.clicked.connect(lambda _checked, u=base_url, m=model: (
            url_entry.setText(u),
            model_entry.setText(m),
            update_setting("llm_base_url", u),
            update_setting("llm_model", m),
        ))
        presets_layout.addWidget(btn)

    layout.addWidget(presets_frame)

    # ── 测试连接按钮 ──
    test_frame = QtWidgets.QWidget()
    test_layout = QtWidgets.QHBoxLayout(test_frame)
    test_layout.setContentsMargins(0, 0, 0, 0)

    self.llm_test_result = QtWidgets.QLabel("")
    self.llm_test_result.setFont(QtGui.QFont("微软雅黑", 10))

    test_btn = QtWidgets.QPushButton("🔌 测试连接")
    test_btn.setFont(QtGui.QFont("微软雅黑", 11))
    test_btn.clicked.connect(lambda: _test_llm_connection(self))
    test_layout.addWidget(test_btn)
    test_layout.addWidget(self.llm_test_result, 1)
    layout.addWidget(test_frame)

    layout.addStretch(1)


def _test_llm_connection(self):
    """测试 LLM 连接是否正常。"""
    import threading

    self.llm_test_result.setText("⏳ 正在测试连接...")
    self.llm_test_result.setStyleSheet("color: #ffc107;")

    def _worker():
        try:
            from ..audio.llm_report import get_llm_config
            from openai import OpenAI

            cfg = get_llm_config()
            if not cfg.get("llm_api_key") or not cfg.get("llm_base_url") or not cfg.get("llm_model"):
                def _need_config():
                    self.llm_test_result.setText("❌ 请先填写 API Key、Base URL 和模型名称")
                    self.llm_test_result.setStyleSheet("color: #dc3545;")
                run_on_ui(_need_config)
                return

            client = OpenAI(api_key=cfg["llm_api_key"], base_url=cfg["llm_base_url"])

            response = client.responses.create(
                model=cfg["llm_model"],
                input="Hi",
            )

            def _ok():
                self.llm_test_result.setText("✅ 连接成功！模型可用")
                self.llm_test_result.setStyleSheet("color: #28a745;")
            run_on_ui(_ok)

        except Exception as e:
            msg = str(e)[:120]

            def _fail():
                self.llm_test_result.setText(f"❌ 连接失败：{msg}")
                self.llm_test_result.setStyleSheet("color: #dc3545;")
            run_on_ui(_fail)

    threading.Thread(target=_worker, daemon=True).start()
