"""
设置页面 GUI：朗读设置、语音提示设置、账号与安全、疑难解答、个性化。
"""

from PySide6 import QtCore, QtWidgets, QtGui
from markdown import markdown
from ..settings import _load_settings
from .qt_helpers import ValueHolder
from .tts_gui import (
    on_treeview_click,
    volume_scale_change,
    speed_scale_change,
    test_tts,
    stop_tts_test,
    save_tts_setting,
)


def _get_selected_tts_row_values(self):
    try:
        row = self.tts_tree.currentRow()
        if row < 0:
            return None
        return [self.tts_tree.item(row, c).text() for c in range(self.tts_tree.columnCount())]
    except Exception:
        return None


def _generate_settings_gui(self):
    # The frame for the settings
    if self.if_settings_show == True:
        return
    else:
        self.if_settings_show = True
    # main frame
    self.settings_frame = QtWidgets.QWidget()
    self.settings_layout = QtWidgets.QVBoxLayout(self.settings_frame)
    self.settings_layout.setContentsMargins(10, 10, 10, 10)
    self.main_paned_window.addWidget(self.settings_frame, 7)
    if self.if_main_window_show == True:
        self.content_frame.deleteLater()
        self.if_main_window_show = False
    # notebooks
    notebook = QtWidgets.QTabWidget()
    account_frame = QtWidgets.QWidget()
    read_frame = QtWidgets.QWidget()
    customize_frame = QtWidgets.QWidget()
    notebook.addTab(read_frame, "朗读设置")
    notebook.addTab(account_frame, "账号与安全")
    notebook.addTab(customize_frame, "个性化")
    self.settings_layout.addWidget(notebook, 1)

    # ── account frame ──
    _build_account_tab(self, account_frame)

    # ── read frame（基础设置 + TTS 设置） ──
    _build_reading_tab(self, read_frame)

    # ── customize frame ──
    _build_customize_tab(self, customize_frame)

    def _save_tts_and_back():
        try:
            save_tts_setting(self)
        except Exception as e:
            try:
                self.log_error("返回前自动保存TTS失败", str(e))
            except Exception:
                pass
            self.gui.error(message=f"自动保存TTS失败：{e}")
            return
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])

    # 返回按钮
    back_button = QtWidgets.QPushButton("返回")
    back_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    back_button.setFixedWidth(120)
    back_button.clicked.connect(_save_tts_and_back)
    self.settings_layout.addWidget(back_button, 0, QtCore.Qt.AlignmentFlag.AlignRight)
    _load_settings(self=self)


# ═══════════════════════ 账号 Tab ═══════════════════════

def _build_account_tab(self, account_frame):
    layout = QtWidgets.QVBoxLayout(account_frame)
    account_management_label_frame = QtWidgets.QGroupBox("账户管理")
    account_management_label_frame.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    layout.addWidget(account_management_label_frame)

    am_layout = QtWidgets.QVBoxLayout(account_management_label_frame)

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
    account_ok_button = QtWidgets.QPushButton("确定")
    account_ok_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    account_ok_button.clicked.connect(lambda: self.save_settings_except_tts("account"))
    name_layout.addWidget(self.account_name_label)
    name_layout.addWidget(name_entry)
    name_layout.addWidget(account_ok_button)
    am_layout.addWidget(name_row)

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
    account_password_ok_button = QtWidgets.QPushButton("确定")
    account_password_ok_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    account_password_ok_button.clicked.connect(lambda: self.save_settings_except_tts(option="password"))
    password_layout.addWidget(password_label)
    password_layout.addWidget(password_entry)
    password_layout.addWidget(account_password_ok_button)
    am_layout.addWidget(password_row)

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

    # 目标设定
    goal_row = QtWidgets.QWidget()
    goal_layout = QtWidgets.QHBoxLayout(goal_row)
    goal_layout.setContentsMargins(0, 0, 0, 0)
    self.settings_goal_label = QtWidgets.QLabel("目标设定:")
    self.settings_goal_label.setFont(QtGui.QFont("微软雅黑", 13))
    self.settings_goal_value = ValueHolder(0)
    goal_entry = QtWidgets.QLineEdit()
    goal_entry.setFont(QtGui.QFont("微软雅黑", 13))
    goal_entry.setMinimumWidth(260)
    self.settings_goal_value.changed.connect(lambda v: goal_entry.setText(str(v)))
    goal_entry.setText(str(self.settings_goal_value.get()))
    goal_entry.textChanged.connect(lambda t: self.settings_goal_value.set(float(t) if t else 0))
    goal_ok_button = QtWidgets.QPushButton("确定")
    goal_ok_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    goal_ok_button.clicked.connect(lambda: self.save_settings_except_tts("goal"))
    goal_layout.addWidget(self.settings_goal_label)
    goal_layout.addWidget(goal_entry)
    goal_layout.addWidget(goal_ok_button)
    basic_layout.addWidget(goal_row)

    # 停顿容忍间隔
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
    stop_dur_entry.textChanged.connect(lambda t: self.settings_stop_dur_value.set(float(t) if t else 0.0))
    stop_dur_button = QtWidgets.QPushButton("确定")
    stop_dur_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    stop_dur_button.clicked.connect(lambda: self.save_settings_except_tts("stop_dur"))
    stop_layout.addWidget(self.stop_dur_label)
    stop_layout.addWidget(stop_dur_entry)
    stop_layout.addWidget(stop_dur_button)
    basic_layout.addWidget(stop_row)

    # 分贝阈值
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
    db_entry.textChanged.connect(lambda t: self.settings_db_value.set(float(t) if t else 0.0))
    db_ok_button = QtWidgets.QPushButton("确定")
    db_ok_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    db_ok_button.clicked.connect(lambda: self.save_settings_except_tts("db_level"))
    db_layout.addWidget(self.settings_db_label)
    db_layout.addWidget(db_entry)
    db_layout.addWidget(db_ok_button)
    basic_layout.addWidget(db_row)

    # ── 语音提示设置 ──
    _build_tts_settings_section(self, read_frame)


def _build_tts_settings_section(self, read_frame):
    """构建语音提示设置区域（TTS Treeview + 音色/音量/语速控件）"""
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
    self.tts_tree.itemSelectionChanged.connect(lambda: on_treeview_click(self, None, self._get_selected_tts_row_values()))
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

    # Save / Test buttons
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
    self.tts_save_button = QtWidgets.QPushButton("保存设置")
    self.tts_save_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    self.tts_save_button.clicked.connect(lambda: save_tts_setting(self))
    buttons_layout.addWidget(self.tts_save_button)
    self.settings_container_layout.addWidget(buttons_frame)


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
    customize_ok_button = QtWidgets.QPushButton("确认")
    customize_ok_button.clicked.connect(self.change_theme)
    box_layout.addWidget(customize_ok_button)
