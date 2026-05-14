"""
数据统计与图表展示页面 GUI：综合面板、每日数据、音频分析。
"""

from PySide6 import QtCore, QtWidgets, QtGui
import os
import shutil
import time
import wave
import traceback
import threading
from datetime import datetime, timedelta
from PIL import Image, ImageQt
from .. import audio_analysis as audio_analasy
from .gui_service import get_gui_service
from .qt_helpers import ValueHolder
from .qt_helpers import run_on_ui


# ══════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════

def _generate_data_gui(self):
    """生成数据展示界面"""
    if self.if_data_form_show == True:
        return
    self.if_data_form_show = True
    self.data_frame = QtWidgets.QWidget()
    self.data_layout = QtWidgets.QVBoxLayout(self.data_frame)
    self.data_layout.setContentsMargins(10, 10, 10, 10)
    self.main_paned_window.addWidget(self.data_frame, 7)
    if self.if_main_window_show == True:
        self.content_frame.deleteLater()
        self.if_main_window_show = False

    # === 全局控件注册表 ===
    self.gui_components = {
        "labels": {},
        "canvases": {},
        "frames": {},
        "buttons": {},
    }

    def register_component(category, key, widget=None):
        """注册或获取界面组件。

        传入 widget 时执行注册；不传 widget 时返回已注册的组件。
        """
        if widget is not None:
            if category in self.gui_components:
                self.gui_components[category][key] = widget
            return widget
        return self.gui_components.get(category, {}).get(key)

    # 创建 Notebook
    notebook = QtWidgets.QTabWidget()
    general_frame = register_component("frames", "tab_general", QtWidgets.QWidget())
    day_frame = register_component("frames", "tab_day", QtWidgets.QWidget())

    notebook.addTab(general_frame, "综合")
    notebook.addTab(day_frame, "每日数据")
    self.data_layout.addWidget(notebook, 1)

    # 1. 综合数据
    _build_general_tab(self, general_frame, register_component)
    # 2. 每日数据
    _build_day_tab(self, day_frame, register_component)

    # 返回按钮
    back_button = register_component(
        "buttons", "global_return",
        QtWidgets.QPushButton("返回")
    )
    back_button.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    back_button.clicked.connect(lambda: [
        self.welcome_page(destroy_window=[self.data_frame, "data_form"]),
        setattr(self, 'if_audio_analysis_running', False),
        setattr(self, 'if_audio_analasy_running', False),
    ])
    self.data_layout.addWidget(back_button)
    refresh_general_dashboard(self)


# ══════════════════════════════════════════════════════════
#  通用辅助
# ══════════════════════════════════════════════════════════

def _bind_mousewheel_to_canvas(_activate_widget, _canvas):
    """Qt uses native scrolling; no-op for compatibility."""
    return


def _load_and_display_image(path, parent_frame, width_hint=None):
    """Auxiliary to load image into a Frame"""
    for child in parent_frame.findChildren(QtWidgets.QWidget):
        if child.parent() == parent_frame:
            child.deleteLater()

    if not path or not os.path.exists(path):
        label = QtWidgets.QLabel("暂无图表数据")
        label.setStyleSheet("color: gray; background: #2b2b2b;")
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        layout = parent_frame.layout() or QtWidgets.QVBoxLayout(parent_frame)
        layout.addWidget(label)
        return

    try:
        pil_img = Image.open(path)
        qt_img = ImageQt.ImageQt(pil_img)
        pix = QtGui.QPixmap.fromImage(qt_img)
        label = QtWidgets.QLabel()
        label.setPixmap(pix)
        label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("background: #2b2b2b;")
        layout = parent_frame.layout() or QtWidgets.QVBoxLayout(parent_frame)
        layout.addWidget(label)

        menu = QtWidgets.QMenu(label)
        menu.addAction("导出图片", lambda: _export_image(path))

        def show_menu(event):
            menu.exec(event.globalPos())

        label.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
        label.customContextMenuRequested.connect(lambda pos: show_menu(QtGui.QContextMenuEvent(QtGui.QContextMenuEvent.Reason.Mouse, pos)))

    except Exception as e:
        print(f"Error loading image {path}: {e}")
        label = QtWidgets.QLabel(f"加载失败: {e}")
        label.setStyleSheet("color: red; background: #2b2b2b;")
        layout = parent_frame.layout() or QtWidgets.QVBoxLayout(parent_frame)
        layout.addWidget(label)

def _export_image(src_path):
    """Export the image to a user-selected location."""
    if not src_path or not os.path.exists(src_path):
        return

    try:
        ext = os.path.splitext(src_path)[1]
        dest_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "导出图片",
            "",
            f"Image files (*{ext});;All files (*.*)"
        )
        if dest_path:
            shutil.copy2(src_path, dest_path)
    except Exception as e:
        print(f"Error exporting image: {e}")


# ══════════════════════════════════════════════════════════
#  Tab 1 – 综合数据
# ══════════════════════════════════════════════════════════

def _build_general_tab(self, general_frame, register_component):
    layout = QtWidgets.QVBoxLayout(general_frame)
    scroll = QtWidgets.QScrollArea()
    scroll.setWidgetResizable(True)
    scrollable_data_frame = QtWidgets.QWidget()
    scroll_layout = QtWidgets.QVBoxLayout(scrollable_data_frame)
    scroll_layout.setContentsMargins(0, 0, 0, 0)
    scroll.setWidget(scrollable_data_frame)
    layout.addWidget(scroll)

    ctrl_frame = QtWidgets.QWidget()
    ctrl_layout = QtWidgets.QHBoxLayout(ctrl_frame)
    ctrl_layout.setContentsMargins(0, 0, 0, 0)
    
    register_component(
        "buttons", "general_refresh",
        QtWidgets.QPushButton("⟳ 刷新仪表盘")
    )
    ctrl_btn = register_component("buttons", "general_refresh")
    ctrl_btn.setFont(QtGui.QFont("微软雅黑", 9))
    ctrl_btn.clicked.connect(lambda: refresh_general_dashboard(self, force_refresh=True))
    ctrl_layout.addStretch(1)
    ctrl_layout.addWidget(ctrl_btn)
    scroll_layout.addWidget(ctrl_frame)

    # LabelFrame: 数据概览
    basic_data_lf = register_component(
        "frames", "general_basic_lf",
        QtWidgets.QGroupBox("数据概览"),
    )
    basic_data_lf.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    basic_layout = QtWidgets.QGridLayout(basic_data_lf)
    scroll_layout.addWidget(basic_data_lf)

    headings_row1 = ["朗读总时长（秒）", "朗读总天数", "平均朗读时长", "当前连续朗读天数", "历史最长天数", "平均效率"]
    self.data_labels = {}

    for idx, title in enumerate(headings_row1):
        lbl_title = register_component(
            "labels", f"general_head_{idx}",
            QtWidgets.QLabel(title),
        )
        lbl_title.setFont(QtGui.QFont("微软雅黑", 11))
        basic_layout.addWidget(lbl_title, 0, idx)

        lbl_val = register_component(
            "labels", f"general_val_{idx}",
            QtWidgets.QLabel("--"),
        )
        lbl_val.setFont(QtGui.QFont("微软雅黑", 13, QtGui.QFont.Weight.Bold))
        lbl_val.setStyleSheet("color: #17a2b8;")
        basic_layout.addWidget(lbl_val, 1, idx)
        self.data_labels[title] = lbl_val

    # Separator
    line = QtWidgets.QFrame()
    line.setFrameShape(QtWidgets.QFrame.Shape.HLine)
    line.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
    basic_layout.addWidget(line, 2, 0, 1, 6)

    # Row 2: 记录
    l_eff_t = register_component(
        "labels", "general_rec_eff_title",
        QtWidgets.QLabel("最高效率 (日期)"),
    )
    l_eff_t.setFont(QtGui.QFont("微软雅黑", 11))
    basic_layout.addWidget(l_eff_t, 3, 1)

    lbl_eff = register_component(
        "labels", "general_rec_eff_val",
        QtWidgets.QLabel("-- (----/--/--)"),
    )
    lbl_eff.setFont(QtGui.QFont("微软雅黑", 13, QtGui.QFont.Weight.Bold))
    lbl_eff.setStyleSheet("color: #28a745;")
    basic_layout.addWidget(lbl_eff, 4, 1)
    self.data_labels["最高效率"] = lbl_eff

    l_dur_t = register_component(
        "labels", "general_rec_dur_title",
        QtWidgets.QLabel("最长时长 (日期)"),
    )
    l_dur_t.setFont(QtGui.QFont("微软雅黑", 11))
    basic_layout.addWidget(l_dur_t, 3, 3)

    lbl_dur = register_component(
        "labels", "general_rec_dur_val",
        QtWidgets.QLabel("-- (----/--/--)"),
    )
    lbl_dur.setFont(QtGui.QFont("微软雅黑", 13, QtGui.QFont.Weight.Bold))
    lbl_dur.setStyleSheet("color: #dc3545;")
    basic_layout.addWidget(lbl_dur, 4, 3)
    self.data_labels["最长时长"] = lbl_dur

    # LabelFrame: 数据图表
    charts_lf = register_component(
        "frames", "general_charts_lf",
        QtWidgets.QGroupBox("数据图表"),
    )
    charts_lf.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    charts_layout = QtWidgets.QVBoxLayout(charts_lf)
    scroll_layout.addWidget(charts_lf)

    # 热力图 — 标题 + 年份切换
    heatmap_title_frame = QtWidgets.QWidget()
    heatmap_title_layout = QtWidgets.QHBoxLayout(heatmap_title_frame)
    heatmap_title_layout.setContentsMargins(0, 0, 0, 0)
    title_lbl = QtWidgets.QLabel("打卡热力图")
    title_lbl.setFont(QtGui.QFont("微软雅黑", 12))
    heatmap_title_layout.addWidget(title_lbl)
    heatmap_title_layout.addStretch(1)
    self._heatmap_year_prev_btn = QtWidgets.QPushButton("◀")
    self._heatmap_year_prev_btn.setFont(QtGui.QFont("微软雅黑", 10))
    self._heatmap_year_prev_btn.setEnabled(False)
    self._heatmap_year_prev_btn.clicked.connect(lambda: _switch_heatmap_year(self, -1))
    self._heatmap_year_label = QtWidgets.QLabel("----")
    self._heatmap_year_label.setFont(QtGui.QFont("微软雅黑", 12, QtGui.QFont.Weight.Bold))
    self._heatmap_year_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    self._heatmap_year_next_btn = QtWidgets.QPushButton("▶")
    self._heatmap_year_next_btn.setFont(QtGui.QFont("微软雅黑", 10))
    self._heatmap_year_next_btn.setEnabled(False)
    self._heatmap_year_next_btn.clicked.connect(lambda: _switch_heatmap_year(self, 1))
    heatmap_title_layout.addWidget(self._heatmap_year_prev_btn)
    heatmap_title_layout.addWidget(self._heatmap_year_label)
    heatmap_title_layout.addWidget(self._heatmap_year_next_btn)
    charts_layout.addWidget(heatmap_title_frame)

    heatmap_container = QtWidgets.QFrame()
    heatmap_container.setFixedHeight(200)
    heatmap_container.setStyleSheet("background: #2b2b2b;")
    heatmap_layout = QtWidgets.QVBoxLayout(heatmap_container)
    heatmap_label = QtWidgets.QLabel("[打卡热力图区域]")
    heatmap_label.setStyleSheet("color: #888888;")
    heatmap_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    heatmap_layout.addWidget(heatmap_label)
    charts_layout.addWidget(heatmap_container)
    self.chart_frame_heatmap = heatmap_container

    # 初始化跨年状态
    self._heatmap_years = []
    self._heatmap_paths = {}
    self._heatmap_current_idx = 0

    # 趋势图
    trend_title = register_component(
        "labels", "general_chart_trend_title",
        QtWidgets.QLabel("每日朗读时长变化"),
    )
    trend_title.setFont(QtGui.QFont("微软雅黑", 12))
    charts_layout.addWidget(trend_title)
    duration_container = QtWidgets.QFrame()
    duration_container.setStyleSheet("background: #2b2b2b;")
    charts_layout.addWidget(duration_container)
    register_component(
        "labels", "general_chart_trend_ph",
        QtWidgets.QLabel("[朗读时长趋势图区域]"),
    )
    ph_label = register_component("labels", "general_chart_trend_ph")
    ph_label.setStyleSheet("color: #888888;")
    ph_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    duration_layout = QtWidgets.QVBoxLayout(duration_container)
    duration_layout.addWidget(ph_label)
    self.chart_frame_duration = duration_container


# ══════════════════════════════════════════════════════════
#  Tab 2 – 每日数据
# ══════════════════════════════════════════════════════════

def _build_day_tab(self, day_frame, register_component):
    layout = day_frame.layout() or QtWidgets.QVBoxLayout(day_frame)
    self._report_window = None
    self.day_list_container = QtWidgets.QWidget()
    self.day_list_container_layout = QtWidgets.QVBoxLayout(self.day_list_container)
    layout.addWidget(self.day_list_container)

    # Tool Bar for List
    list_tools = QtWidgets.QWidget()
    list_tools_layout = QtWidgets.QHBoxLayout(list_tools)
    list_tools_layout.setContentsMargins(0, 0, 0, 0)
    self.day_list_container_layout.addWidget(list_tools)
    
    # 月份选择器
    month_frame = QtWidgets.QWidget()
    month_layout = QtWidgets.QHBoxLayout(month_frame)
    month_layout.setContentsMargins(0, 0, 0, 0)
    month_layout.addWidget(QtWidgets.QLabel("选择月份:"))
    
    # 初始化月份选择器状态
    self._selected_month = datetime.now().strftime("%Y-%m")
    self._available_months = []
    
    month_combo = QtWidgets.QComboBox()
    month_combo.setEditable(False)
    month_combo.setMinimumWidth(120)
    month_combo.addItem(self._selected_month)
    month_combo.setCurrentText(self._selected_month)
    month_layout.addWidget(month_combo)
    list_tools_layout.addWidget(month_frame)
    register_component("buttons", "day_month_combo", month_combo)
    
    def _on_month_change(_):
        """处理月份选择变化"""
        selected = month_combo.currentText()
        if selected:
            self._selected_month = selected
            _load_day_tree_for_month(self)
    
    month_combo.currentTextChanged.connect(lambda _v: _on_month_change(None))
    self._month_combo = month_combo
    
    refresh_btn = register_component(
        "buttons", "day_list_refresh",
        QtWidgets.QPushButton("⟳ 刷新历史列表")
    )
    refresh_btn.setFont(QtGui.QFont("微软雅黑", 9))
    refresh_btn.clicked.connect(lambda: refresh_general_dashboard(self, force_refresh=True))
    list_tools_layout.addStretch(1)
    list_tools_layout.addWidget(refresh_btn)

    # Treeview
    day_columns = ("date", "duration", "pause", "progress")
    self.day_tree = QtWidgets.QTableWidget(0, len(day_columns))
    self.day_tree.setHorizontalHeaderLabels(["日期", "总朗读时间", "停顿时间", "任务完成度"])
    self.day_tree.verticalHeader().setVisible(False)
    self.day_tree.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
    self.day_tree.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
    self.day_list_container_layout.addWidget(self.day_tree)

    # Day Detail Container (Hidden initially)
    self.day_detail_container = QtWidgets.QWidget()
    layout.addWidget(self.day_detail_container)
    self.day_detail_container.hide()
    detail_layout = QtWidgets.QVBoxLayout(self.day_detail_container)
    detail_scroll = QtWidgets.QScrollArea()
    detail_scroll.setWidgetResizable(True)
    self.detail_scroll_frame = QtWidgets.QWidget()
    self.detail_scroll_frame_layout = QtWidgets.QVBoxLayout(self.detail_scroll_frame)
    detail_scroll.setWidget(self.detail_scroll_frame)
    detail_layout.addWidget(detail_scroll)

    # Back Button
    button_frame = QtWidgets.QWidget()
    button_layout = QtWidgets.QHBoxLayout(button_frame)
    button_layout.setContentsMargins(0, 0, 0, 0)
    self.detail_scroll_frame_layout.addWidget(button_frame)
    
    back_to_list_btn = register_component(
        "buttons", "day_back",
        QtWidgets.QPushButton("← 返回列表")
    )
    back_to_list_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    back_to_list_btn.clicked.connect(lambda: [
        audio_analasy.stop_day_audio(self=self, reset=True),
        self.day_detail_container.hide(),
        self.day_list_container.show(),
    ])
    button_layout.addWidget(back_to_list_btn)
    
    # Refresh Button
    refresh_btn = register_component(
        "buttons", "day_refresh",
        QtWidgets.QPushButton("⟳ 刷新数据")
    )
    refresh_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    refresh_btn.clicked.connect(lambda: load_detail_data(getattr(self, 'current_view_date', None), force=True))
    button_layout.addWidget(refresh_btn)

    analyze_btn = register_component(
        "buttons", "day_analyze",
        QtWidgets.QPushButton("📊 音频分析")
    )
    analyze_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    analyze_btn.clicked.connect(lambda: _show_analysis_dialog(self))
    button_layout.addWidget(analyze_btn)

    report_btn = register_component(
        "buttons", "day_report",
        QtWidgets.QPushButton("📝 生成朗读报告")
    )
    report_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    report_btn.clicked.connect(lambda: _start_daily_report_generation(self, force_refresh=True))
    button_layout.addWidget(report_btn)

    detail_stats_lf = register_component(
        "frames", "day_detail_lf",
        QtWidgets.QGroupBox("数据详情"),
    )
    detail_stats_lf.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    detail_stats_layout = QtWidgets.QGridLayout(detail_stats_lf)
    self.detail_scroll_frame_layout.addWidget(detail_stats_lf)

    self.detail_val_labels = {}
    stats_titles = ["总时长", "停顿总时长", "效率", "完成度", "最大音量", "平均音量", "同比昨日"]
    for i, title in enumerate(stats_titles):
        row, col = i // 2, i % 2
        title_lbl = register_component(
            "labels", f"day_det_t_{title}",
            QtWidgets.QLabel(f"{title}:")
        )
        title_lbl.setFont(QtGui.QFont("微软雅黑", 11))
        detail_stats_layout.addWidget(title_lbl, row, col * 2)
        lbl = register_component(
            "labels", f"day_det_v_{title}",
            QtWidgets.QLabel("--")
        )
        lbl.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
        lbl.setStyleSheet("color: #17a2b8;")
        detail_stats_layout.addWidget(lbl, row, col * 2 + 1)
        self.detail_val_labels[title] = lbl

    vol_title = register_component(
        "labels", "day_vol_chart_title",
        QtWidgets.QLabel("音量变化趋势")
    )
    vol_title.setFont(QtGui.QFont("微软雅黑", 12))
    self.detail_scroll_frame_layout.addWidget(vol_title)
    self.volume_chart_canvas = register_component(
        "canvases", "day_vol_chart",
        QtWidgets.QFrame()
    )
    self.volume_chart_canvas.setStyleSheet("background: #2b2b2b;")
    self.volume_chart_canvas.setFixedHeight(200)
    self.detail_scroll_frame_layout.addWidget(self.volume_chart_canvas)

    report_lf = register_component(
        "frames", "day_report_lf",
        QtWidgets.QGroupBox("朗读报告"),
    )
    report_lf.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    report_layout = QtWidgets.QVBoxLayout(report_lf)
    self.detail_scroll_frame_layout.addWidget(report_lf)
    report_lf.hide()

    report_head = QtWidgets.QWidget()
    report_head_layout = QtWidgets.QHBoxLayout(report_head)
    report_head_layout.setContentsMargins(0, 0, 0, 0)
    report_head_layout.addWidget(QtWidgets.QLabel("最终评分"))
    self.report_score_label = QtWidgets.QLabel("--")
    self.report_score_label.setFont(QtGui.QFont("微软雅黑", 18, QtGui.QFont.Weight.Bold))
    self.report_score_label.setStyleSheet("color: #0d6efd;")
    report_head_layout.addWidget(self.report_score_label)
    report_head_layout.addSpacing(10)
    report_head_layout.addWidget(QtWidgets.QLabel("等级"))
    self.report_grade_label = QtWidgets.QLabel("--")
    self.report_grade_label.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
    self.report_grade_label.setStyleSheet("color: #198754;")
    report_head_layout.addWidget(self.report_grade_label)
    report_head_layout.addStretch(1)
    report_layout.addWidget(report_head)

    dimension_frame = QtWidgets.QWidget()
    dimension_layout = QtWidgets.QGridLayout(dimension_frame)
    self.report_dimension_labels = {}
    for idx, name in enumerate(["流畅度", "音质清晰度", "音量控制", "表现力", "坚持力"]):
        box = QtWidgets.QFrame()
        box.setFrameShape(QtWidgets.QFrame.Shape.Box)
        box_layout = QtWidgets.QVBoxLayout(box)
        title = QtWidgets.QLabel(name)
        title.setFont(QtGui.QFont("微软雅黑", 9))
        box_layout.addWidget(title)
        lbl = QtWidgets.QLabel("--")
        lbl.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
        lbl.setStyleSheet("color: #17a2b8;")
        box_layout.addWidget(lbl)
        dimension_layout.addWidget(box, 0, idx)
        self.report_dimension_labels[name] = lbl
    report_layout.addWidget(dimension_frame)

    self.report_text = QtWidgets.QTextEdit()
    self.report_text.setFont(QtGui.QFont("微软雅黑", 10))
    self.report_text.setReadOnly(True)
    self.report_text.setText("点击「生成朗读报告」后显示评分结果。")
    report_layout.addWidget(self.report_text)

    # Audio Player
    detail_player_lf = register_component(
        "frames", "day_player_lf",
        QtWidgets.QGroupBox("当日录音回放"),
    )
    detail_player_lf.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    detail_player_layout = QtWidgets.QVBoxLayout(detail_player_lf)
    self.detail_scroll_frame_layout.addWidget(detail_player_lf)
    player_controls_detail = QtWidgets.QWidget()
    player_controls_layout = QtWidgets.QHBoxLayout(player_controls_detail)
    player_controls_layout.setContentsMargins(0, 0, 0, 0)
    self.day_play_btn = QtWidgets.QPushButton("▶")
    self.day_play_btn.clicked.connect(self.play_day_audio)
    self.day_pause_btn = QtWidgets.QPushButton("⏸")
    self.day_pause_btn.clicked.connect(self.pause_day_audio)
    self.day_audio_scale = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
    self.day_audio_scale.setRange(0, 100)
    self.day_audio_scale.sliderReleased.connect(lambda: self.seek_day_audio())
    player_controls_layout.addWidget(self.day_play_btn)
    player_controls_layout.addWidget(self.day_pause_btn)
    player_controls_layout.addWidget(self.day_audio_scale, 1)
    detail_player_layout.addWidget(player_controls_detail)
    self.day_audio_status = QtWidgets.QLabel("")
    self.day_audio_status.setFont(QtGui.QFont("微软雅黑", 10))
    self.day_audio_status.setStyleSheet("color: #dc3545;")
    detail_player_layout.addWidget(self.day_audio_status)

    self.init_audio_state()

    # ─── Audio Analysis Results Container (Hidden initially) ───
    self.day_analysis_container = QtWidgets.QWidget(day_frame)
    analysis_layout = QtWidgets.QVBoxLayout(self.day_analysis_container)
    analysis_scroll = QtWidgets.QScrollArea()
    analysis_scroll.setWidgetResizable(True)
    self._analysis_scroll_content = QtWidgets.QWidget()
    self._analysis_scroll_content_layout = QtWidgets.QVBoxLayout(self._analysis_scroll_content)
    analysis_scroll.setWidget(self._analysis_scroll_content)
    analysis_layout.addWidget(analysis_scroll)

    _ab_frame = QtWidgets.QWidget()
    _ab_layout = QtWidgets.QHBoxLayout(_ab_frame)
    back_btn = register_component(
        "buttons", "analysis_back",
        QtWidgets.QPushButton("← 返回详情")
    )
    back_btn.setFont(QtGui.QFont(self.mainpage_button_font[0], self.mainpage_button_font[1]))
    back_btn.clicked.connect(lambda: [
        self.day_analysis_container.hide(),
        self.day_detail_container.show(),
        setattr(self, 'if_audio_analysis_running', False),
        setattr(self, 'if_audio_analasy_running', False)
    ])
    _ab_layout.addWidget(back_btn)
    self._analysis_scroll_content_layout.addWidget(_ab_frame)

    self._analysis_results_frame = QtWidgets.QWidget()
    self._analysis_results_frame_layout = QtWidgets.QVBoxLayout(self._analysis_results_frame)
    self._analysis_scroll_content_layout.addWidget(self._analysis_results_frame)
    layout.addWidget(self.day_analysis_container)
    self.day_analysis_container.hide()

    # Bindings
    def _ensure_daily_report_window():
        win = getattr(self, "_report_window", None)
        if win is not None:
            try:
                win.show()
                win.raise_()
                win.activateWindow()
                return win
            except Exception:
                pass

        win = get_gui_service(self).create_toplevel(
            title="朗读报告",
            size=(860, 640),
            parent=self.main_window,
            resizable=(True, True),
            modal=False,
            center=True,
        )
        try:
            win.setAttribute(QtCore.Qt.WidgetAttribute.WA_DeleteOnClose, True)
        except Exception:
            pass
        win.destroyed.connect(lambda *_: setattr(self, "_report_window", None))
        self._report_window = win

        root_layout = win.layout() or QtWidgets.QVBoxLayout(win)
        root_layout.setContentsMargins(10, 10, 10, 10)

        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.addWidget(QtWidgets.QLabel("最终评分"))
        self.report_score_label = QtWidgets.QLabel("--")
        self.report_score_label.setFont(QtGui.QFont("微软雅黑", 18, QtGui.QFont.Weight.Bold))
        self.report_score_label.setStyleSheet("color: #0d6efd;")
        header_layout.addWidget(self.report_score_label)
        header_layout.addSpacing(10)
        header_layout.addWidget(QtWidgets.QLabel("等级"))
        self.report_grade_label = QtWidgets.QLabel("--")
        self.report_grade_label.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
        self.report_grade_label.setStyleSheet("color: #198754;")
        header_layout.addWidget(self.report_grade_label)
        header_layout.addStretch(1)
        root_layout.addWidget(header)

        dimension_frame = QtWidgets.QWidget()
        dimension_layout = QtWidgets.QGridLayout(dimension_frame)
        self.report_dimension_labels = {}
        for idx, name in enumerate(["流畅度", "音质清晰度", "音量控制", "表现力", "坚持力"]):
            box = QtWidgets.QFrame()
            box.setFrameShape(QtWidgets.QFrame.Shape.Box)
            box_layout = QtWidgets.QVBoxLayout(box)
            t = QtWidgets.QLabel(name)
            t.setFont(QtGui.QFont("微软雅黑", 9))
            box_layout.addWidget(t)
            v = QtWidgets.QLabel("--")
            v.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
            v.setStyleSheet("color: #17a2b8;")
            box_layout.addWidget(v)
            dimension_layout.addWidget(box, 0, idx)
            self.report_dimension_labels[name] = v
        root_layout.addWidget(dimension_frame)

        self.report_text = QtWidgets.QTextEdit()
        self.report_text.setFont(QtGui.QFont("微软雅黑", 10))
        self.report_text.setReadOnly(True)
        self.report_text.setText("点击「生成朗读报告」后显示评分结果。")
        root_layout.addWidget(self.report_text)

        return win

    def load_detail_data(target_date, force=False):
        """
        Helper to fetch and display daily detail
        """
        if not target_date:
            return
            
        try:
             # Progress state
            for label in self.detail_val_labels.values():
                label.setText("加载中...")
                label.setStyleSheet("color: #888888;")
            _reset_daily_report_view("正在准备报告数据...")
            QtWidgets.QApplication.processEvents()
            
            # Fetch
            detail_data = audio_analasy.fetch_for_daily_data(self, target_date, force_refresh=force)

            # Update audio path & duration for playback (independent of detail data)
            account = getattr(self, "current_acount", "")
            date_str = target_date.strftime("%Y-%m-%d") if hasattr(target_date, "strftime") else str(target_date)
            audio_path = os.path.join("./details", account, date_str, "recording.wav")
            st = self._day_audio_state
            st.update({"path": audio_path, "offset": 0.0, "raw": b""})
            st["duration"] = audio_analasy.get_audio_duration(audio_path) if os.path.exists(audio_path) else 0.0
            self.stop_day_audio(reset=True)
            self.day_audio_scale.setRange(0, max(1, int(st["duration"])))
            if hasattr(self, "day_audio_status"):
                self.day_audio_status.setText("")
                self.day_audio_status.setStyleSheet("color: #dc3545;")
            
            if not detail_data:
                for label in self.detail_val_labels.values():
                    label.setText("无数据")
                    label.setStyleSheet("color: #dc3545;")
                _reset_daily_report_view("当前日期无可用数据，无法生成报告。")
                return

            # Update UI
            self.detail_val_labels["总时长"].setText(f"{detail_data.get('total_duration', 0)} 秒")
            self.detail_val_labels["总时长"].setStyleSheet("color: #17a2b8;")
            self.detail_val_labels["停顿总时长"].setText(f"{detail_data.get('pause_duration', 0)} 秒")
            self.detail_val_labels["停顿总时长"].setStyleSheet("color: #ffc107;")
            self.detail_val_labels["效率"].setText(f"{detail_data.get('efficiency', 0.0):.0%}")
            self.detail_val_labels["效率"].setStyleSheet("color: #28a745;")
            self.detail_val_labels["完成度"].setText(detail_data.get('completion', '--'))
            self.detail_val_labels["完成度"].setStyleSheet("color: #6f42c1;")
            self.detail_val_labels["最大音量"].setText(f"{detail_data.get('max_volume', 0.0):.1f} dB")
            self.detail_val_labels["最大音量"].setStyleSheet("color: #dc3545;")
            self.detail_val_labels["平均音量"].setText(f"{detail_data.get('avg_volume', 0.0):.1f} dB")
            self.detail_val_labels["平均音量"].setStyleSheet("color: #fd7e14;")
            self.detail_val_labels["同比昨日"].setText(detail_data.get('compare_yesterday', '--'))
            self.detail_val_labels["同比昨日"].setStyleSheet("color: #20c997;")
            
             # Chart
            vol_chart_path = detail_data.get('volume_chart_path', '')
            for child in self.volume_chart_canvas.findChildren(QtWidgets.QWidget):
                if child.parent() == self.volume_chart_canvas:
                    child.deleteLater()
            if vol_chart_path and os.path.exists(vol_chart_path):
                _load_and_display_image(vol_chart_path, self.volume_chart_canvas)
            else:
                label = QtWidgets.QLabel("暂无音量数据")
                label.setStyleSheet("color: #888888;")
                label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
                layout = self.volume_chart_canvas.layout() or QtWidgets.QVBoxLayout(self.volume_chart_canvas)
                layout.addWidget(label)

            _reset_daily_report_view("点击「生成朗读报告」后，自动汇总当前日期的数据并评分。")

            QtWidgets.QApplication.processEvents()

        except Exception as e:
            print(f"Error loading daily detail: {e}")
            traceback.print_exc()

    def _reset_daily_report_view(message="点击「生成朗读报告」后显示评分结果。"):
        try:
            self.report_score_label.setText("--")
            self.report_score_label.setStyleSheet("color: #0d6efd;")
            self.report_grade_label.setText("--")
            self.report_grade_label.setStyleSheet("color: #198754;")
            for label in self.report_dimension_labels.values():
                label.setText("--")
                label.setStyleSheet("color: #17a2b8;")
            self.report_text.setText(message)
        except Exception:
            pass

    def _update_daily_report_view(report_data):
        try:
            if not report_data:
                _reset_daily_report_view("朗读报告生成失败，请稍后重试。")
                return

            score = float(report_data.get("score", 0.0) or 0.0)
            self.report_score_label.setText(f"{score:.1f}")
            self.report_score_label.setStyleSheet("color: #0d6efd;")
            self.report_grade_label.setText(f"{report_data.get('grade', '--')}  {report_data.get('grade_meaning', '')}")
            self.report_grade_label.setStyleSheet("color: #198754;")
            dimensions = report_data.get("dimensions", {}) or {}
            for name, label in self.report_dimension_labels.items():
                label.setText(f"{float(dimensions.get(name, 0.0) or 0.0):.1f}")
                label.setStyleSheet("color: #17a2b8;")
            self.report_text.setText(report_data.get("report_text", ""))
        except Exception as e:
            print(f"Error updating report UI: {e}")

    def _start_daily_report_generation(_, force_refresh=False):
        target_date = getattr(self, 'current_view_date', None)
        win = _ensure_daily_report_window()
        try:
            win.show()
            win.raise_()
            win.activateWindow()
        except Exception:
            pass
        if not target_date:
            _reset_daily_report_view("请先在每日列表中打开某一天的详情页。")
            return

        _reset_daily_report_view("正在生成朗读报告，请稍候...")

        def _worker():
            try:
                report_data = audio_analasy.generate_reading_report(self, target_date, force_refresh=force_refresh)
            except Exception as e:
                report_data = {}
                print(f"Error generating report: {e}")

            def _finish():
                if hasattr(self, "report_text"):
                    _update_daily_report_view(report_data)

            try:
                run_on_ui(_finish)
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def on_day_double_click(_):
        """
        双击每日数据列表项，加载并展示该日详情。
        """
        try:
            row = self.day_tree.currentRow()
            if row < 0:
                return
            selected_date = self.day_tree.item(row, 0).text()
            
            # Switch View
            self.day_list_container.hide()
            self.day_detail_container.show()
            
            # Save State & Load
            self.current_view_date = selected_date
            
            self.stop_day_audio(reset=True)
            st = self._day_audio_state
            st.update({"path": "", "duration": 0.0, "offset": 0.0, "raw": b""})
            self.day_audio_scale.setRange(0, 100)
            if hasattr(self, "day_audio_status"):
                self.day_audio_status.setText("")
                self.day_audio_status.setStyleSheet("color: #dc3545;")
            
            load_detail_data(selected_date, force=False)
            
        except Exception as e:
            print(f"Error handling double click: {e}")

    self.day_tree.itemDoubleClicked.connect(lambda _item: on_day_double_click(None))


# ══════════════════════════════════════════════════════════
#  每日数据 – 音频分析弹窗 & 异步绘制
# ══════════════════════════════════════════════════════════

def _show_analysis_dialog(self):
    """弹出复选框对话框，让用户选择要执行的音频分析项目。"""
    dialog = get_gui_service(self).create_toplevel(
        title="选择音频分析项目",
        size=(420, 560),
        parent=self.main_window,
        resizable=(False, True),
        modal=True,
        center=True,
    )

    # layout setup below

    analysis_options = [
        ("vad",         "语音活动检测 (VAD)",    "检测哪些时刻在说话，分析朗读连贯性"),
        ("rms",         "短时能量 (RMS)",        "音量变化趋势，反映声音的轻重起伏"),
        ("ltas",        "长时平均能量 (10s 切片)", "对比各段频率分布，判断音色稳定性"),
        ("zcr",         "过零率变化",             "清辅音与元音的分布，辅助判断发音清晰度"),
        ("pitch",       "基频变化 (F0)",          "音调高低的变化，反映抑扬顿挫程度"),
        ("snr",         "信噪比 (SNR)",           "录音干净程度，≥20dB 为良好"),
        ("mfcc",        "梅尔倒谱 (MFCC)",        "音色特征矩阵，语音识别核心特征"),
        ("crest",       "峰值因子 (Crest Factor)", "动态范围，检测爆破音与声音压缩"),
        ("entropy",     "频谱熵 (Spectral Entropy)","频谱随机程度，辅助区分语音与噪音"),
        ("spectrogram", "语谱图 (Spectrogram)",   "时频能量全景图，最直观的语音可视化"),
    ]

    cb_vars = {}
    layout = dialog.layout() or QtWidgets.QVBoxLayout(dialog)
    title_lbl = QtWidgets.QLabel("请勾选需要分析的项目：")
    title_lbl.setFont(QtGui.QFont("微软雅黑", 11))
    layout.addWidget(title_lbl)
    tip_lbl = QtWidgets.QLabel(
        "💡 分析完成后，每项结果下方均附有通俗说明，点击「查看指标说明」可展开详细解读。"
    )
    tip_lbl.setStyleSheet("color: #6c757d;")
    tip_lbl.setWordWrap(True)
    tip_lbl.setFont(QtGui.QFont("微软雅黑", 8))
    layout.addWidget(tip_lbl)

    for key, label, hint in analysis_options:
        row = QtWidgets.QWidget()
        row_layout = QtWidgets.QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        var = ValueHolder(True)
        checkbox = QtWidgets.QCheckBox(label)
        checkbox.setChecked(True)
        checkbox.setFont(QtGui.QFont("微软雅黑", 10))
        checkbox.toggled.connect(var.set)
        hint_lbl = QtWidgets.QLabel(hint)
        hint_lbl.setStyleSheet("color: #adb5bd;")
        hint_lbl.setFont(QtGui.QFont("微软雅黑", 8))
        row_layout.addWidget(checkbox)
        row_layout.addWidget(hint_lbl)
        row_layout.addStretch(1)
        layout.addWidget(row)
        cb_vars[key] = var

    # 全选 / 全不选
    sel_frame = QtWidgets.QWidget()
    sel_layout = QtWidgets.QHBoxLayout(sel_frame)
    sel_layout.setContentsMargins(0, 0, 0, 0)
    select_all = QtWidgets.QPushButton("全选")
    select_all.setFont(QtGui.QFont("微软雅黑", 9))
    select_all.clicked.connect(lambda: [v.set(True) for v in cb_vars.values()])
    select_none = QtWidgets.QPushButton("全不选")
    select_none.setFont(QtGui.QFont("微软雅黑", 9))
    select_none.clicked.connect(lambda: [v.set(False) for v in cb_vars.values()])
    sel_layout.addWidget(select_all)
    sel_layout.addWidget(select_none)
    sel_layout.addStretch(1)
    layout.addWidget(sel_frame)

    # 确定 / 取消
    btn_frame = QtWidgets.QWidget()
    btn_layout = QtWidgets.QHBoxLayout(btn_frame)
    btn_layout.setContentsMargins(0, 0, 0, 0)

    def on_confirm():
        selected = [k for k, v in cb_vars.items() if v.get()]
        dialog.close()
        if selected:
            _start_audio_analysis(self, selected)

    ok_btn = QtWidgets.QPushButton("确定")
    ok_btn.setFont(QtGui.QFont("微软雅黑", 10))
    ok_btn.clicked.connect(on_confirm)
    cancel_btn = QtWidgets.QPushButton("取消")
    cancel_btn.setFont(QtGui.QFont("微软雅黑", 10))
    cancel_btn.clicked.connect(dialog.close)
    btn_layout.addWidget(ok_btn)
    btn_layout.addWidget(cancel_btn)
    layout.addWidget(btn_frame)


def _start_audio_analysis(self, selected_keys):
    """切换到分析结果 Frame 并启动后台线程异步绘图。"""
    st = getattr(self, "_day_audio_state", {})
    audio_path = st.get("path", "")
    date_str = getattr(self, "current_view_date", "")

    # 切换视图: 详情 → 分析
    self.day_detail_container.hide()
    self.day_analysis_container.show()

    # 清除上次分析结果
    for w in self._analysis_results_frame.findChildren(QtWidgets.QWidget):
        if w.parent() == self._analysis_results_frame:
            w.deleteLater()

    if not audio_path or not os.path.exists(audio_path):
        label = QtWidgets.QLabel("⚠ 当前日期无可用音频文件，无法进行分析。")
        label.setStyleSheet("color: #dc3545;")
        label.setFont(QtGui.QFont("微软雅黑", 12))
        self._analysis_results_frame.layout().addWidget(label)
        return

    # 停止播放
    audio_analasy.stop_day_audio(self, reset=True)

    # 创建加载占位
    placeholders = {}
    for key in selected_keys:
        desc = audio_analasy.ANALYSIS_DESCRIPTIONS.get(key, {})
        title = audio_analasy.ANALYSIS_ITEMS.get(key, key)
        brief = desc.get("brief", "")

        lf = QtWidgets.QGroupBox(title)
        lf.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
        lf_layout = QtWidgets.QVBoxLayout(lf)
        self._analysis_results_frame.layout().addWidget(lf)

        # Brief description row
        if brief:
            brief_label = QtWidgets.QLabel(brief)
            brief_label.setStyleSheet("color: #6c757d;")
            brief_label.setFont(QtGui.QFont("微软雅黑", 9))
            brief_label.setWordWrap(True)
            lf_layout.addWidget(brief_label)

        loading = QtWidgets.QLabel("⏳ 分析中…")
        loading.setStyleSheet("color: #888888;")
        loading.setFont(QtGui.QFont("微软雅黑", 10))
        lf_layout.addWidget(loading)
        placeholders[key] = lf

    # 异步后台分析
    account = getattr(self, "current_acount", "")
    output_dir = os.path.join("./details", account, str(date_str))

    def _bg_worker():
        if getattr(self, "if_audio_analysis_running", False) == True:
            return
        self.if_audio_analysis_running = True
        self.if_audio_analasy_running = True
        time.sleep(0.2)  # 等待 GUI 渲染完成

        def _on_done(key, result):
            run_on_ui(lambda k=key, r=result: _on_single_analysis_done(self, k, r, placeholders))

        audio_analasy.run_selected_analyses(
            audio_path, selected_keys, output_dir, on_item_done=_on_done
        )

    threading.Thread(target=_bg_worker, daemon=True).start()


def _on_single_analysis_done(self, key, result, placeholders):
    """后台单项分析完成后在主线程刷新对应区域。"""
    lf = placeholders.get(key)
    if not lf:
        return

    # 清空占位内容（保留 brief 标签，即第一个子控件）
    layout = lf.layout() or QtWidgets.QVBoxLayout(lf)
    children = []
    for i in range(layout.count()):
        item = layout.itemAt(i)
        if item is None:
            continue
        widget = item.widget()
        if widget is not None:
            children.append(widget)
    for w in children[1:]:
        if w is not None:
            w.deleteLater()
    for w in children:
        if isinstance(w, QtWidgets.QLabel) and "⏳" in (w.text() or ""):
            w.deleteLater()

    if "error" in result:
        err = QtWidgets.QLabel(f"❌ 分析失败: {result['error']}")
        err.setStyleSheet("color: #dc3545;")
        err.setFont(QtGui.QFont("微软雅黑", 10))
        layout.addWidget(err)
        return

    # 加载图表
    chart_path = result.get("path", "")
    if chart_path and os.path.exists(chart_path):
        try:
            pil_img = Image.open(chart_path)
            qt_img = ImageQt.ImageQt(pil_img)
            pix = QtGui.QPixmap.fromImage(qt_img)
            img_label = QtWidgets.QLabel()
            img_label.setPixmap(pix)
            img_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(img_label)

            menu = QtWidgets.QMenu(img_label)
            menu.addAction("导出图片", lambda: _export_image(chart_path))
            img_label.setContextMenuPolicy(QtCore.Qt.ContextMenuPolicy.CustomContextMenu)
            img_label.customContextMenuRequested.connect(lambda pos: menu.exec(img_label.mapToGlobal(pos)))

        except Exception as e:
            label = QtWidgets.QLabel(f"图表加载失败: {e}")
            label.setStyleSheet("color: #dc3545;")
            label.setFont(QtGui.QFont("微软雅黑", 10))
            layout.addWidget(label)
    else:
        label = QtWidgets.QLabel("无图表数据")
        label.setStyleSheet("color: gray;")
        label.setFont(QtGui.QFont("微软雅黑", 10))
        layout.addWidget(label)

    # ── 指标数值区域 ──
    extra = result.get("extra", {})
    desc = audio_analasy.ANALYSIS_DESCRIPTIONS.get(key, {})
    extra_tips = desc.get("extra_tips", {})
    detail_text = desc.get("detail", "")

    if extra:
        metrics_frame = QtWidgets.QWidget()
        metrics_layout = QtWidgets.QHBoxLayout(metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(metrics_frame)
        for idx, (k, v) in enumerate(extra.items()):
            tip = extra_tips.get(k, "")
            # 指标值标签
            val_lf = QtWidgets.QFrame()
            val_lf.setFrameShape(QtWidgets.QFrame.Shape.Panel)
            val_layout = QtWidgets.QVBoxLayout(val_lf)
            label_key = QtWidgets.QLabel(k)
            label_key.setStyleSheet("color: #6c757d;")
            label_key.setFont(QtGui.QFont("微软雅黑", 8))
            label_val = QtWidgets.QLabel(str(v))
            label_val.setStyleSheet("color: #17a2b8;")
            label_val.setFont(QtGui.QFont("微软雅黑", 11, QtGui.QFont.Weight.Bold))
            val_layout.addWidget(label_key)
            val_layout.addWidget(label_val)
            if tip:
                tip_lbl = QtWidgets.QLabel(tip)
                tip_lbl.setStyleSheet("color: #adb5bd;")
                tip_lbl.setFont(QtGui.QFont("微软雅黑", 8))
                tip_lbl.setWordWrap(True)
                val_layout.addWidget(tip_lbl)
            metrics_layout.addWidget(val_lf)

    # ── 可展开的详细说明 ──
    if detail_text:
        detail_visible = ValueHolder(False)
        detail_content = QtWidgets.QFrame()
        detail_content.setStyleSheet("background: #f8f9fa;")
        detail_layout = QtWidgets.QVBoxLayout(detail_content)
        detail_label = QtWidgets.QLabel(detail_text)
        detail_label.setStyleSheet("color: #495057;")
        detail_label.setFont(QtGui.QFont("微软雅黑", 9))
        detail_label.setWordWrap(True)
        detail_layout.addWidget(detail_label)

        toggle_btn = QtWidgets.QPushButton("📖 查看指标说明 ▼")
        toggle_btn.setFont(QtGui.QFont("微软雅黑", 9))
        toggle_btn.setStyleSheet("color: #007bff;")
        layout.addWidget(toggle_btn)

        def _toggle_detail():
            if detail_visible.get():
                detail_content.hide()
                toggle_btn.setText("📖 查看指标说明 ▼")
                detail_visible.set(False)
            else:
                detail_content.show()
                toggle_btn.setText("📖 收起说明 ▲")
                detail_visible.set(True)

        toggle_btn.clicked.connect(_toggle_detail)
        detail_content.hide()
        layout.addWidget(detail_content)

# ══════════════════════════════════════════════════════════
#  热力图年份切换
# ══════════════════════════════════════════════════════════

def _switch_heatmap_year(self, direction):
    """切换热力图年份。direction: -1 上一年, +1 下一年。"""
    if not self._heatmap_years:
        return
    new_idx = self._heatmap_current_idx + direction
    if new_idx < 0 or new_idx >= len(self._heatmap_years):
        return
    self._heatmap_current_idx = new_idx
    _refresh_heatmap_display(self)


def _refresh_heatmap_display(self):
    """根据当前选中年份刷新热力图图片和按钮状态。"""
    if not self._heatmap_years:
        self._heatmap_year_label.setText("----")
        self._heatmap_year_prev_btn.setEnabled(False)
        self._heatmap_year_next_btn.setEnabled(False)
        return

    year = self._heatmap_years[self._heatmap_current_idx]
    self._heatmap_year_label.setText(f"{year} 年")

    self._heatmap_year_prev_btn.setEnabled(self._heatmap_current_idx > 0)
    self._heatmap_year_next_btn.setEnabled(self._heatmap_current_idx < len(self._heatmap_years) - 1)

    path = self._heatmap_paths.get(year) or self._heatmap_paths.get(str(year), "")
    _load_and_display_image(path, self.chart_frame_heatmap)


# ══════════════════════════════════════════════════════════
#  数据面板刷新
# ══════════════════════════════════════════════════════════

def refresh_general_dashboard(self, force_refresh=False):
    # Show loading state
    if hasattr(self, "data_labels"):
        for label in self.data_labels.values():
             try:
                 label.setText("加载中...")
             except Exception:
                 pass

    def _worker():
        try:
            # Fetch fresh analysis data
            dashboard_data = audio_analasy.refresh_dashboard_data(self, force_refresh=force_refresh)
            
            # Schedule UI update
            if hasattr(self, "data_frame"):
                run_on_ui(lambda payload=dashboard_data: _update_dashboard_ui(self, payload))
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            traceback.print_exc()

    threading.Thread(target=_worker, daemon=True).start()

def _update_dashboard_ui(self, dashboard_data):
    try:
        # --- Update Basic Stats in General Tab ---
        if isinstance(dashboard_data, dict):
            self.data_labels["朗读总天数"].setText(str(dashboard_data.get('total_days', '--')))
            self.data_labels["朗读总时长（秒）"].setText(f"{dashboard_data.get('total', 0):.2f}")
            self.data_labels["平均朗读时长"].setText(f"{dashboard_data.get('average_daily', 0):.2f}")
            self.data_labels["当前连续朗读天数"].setText(str(dashboard_data.get('current_streak', '--')))
            self.data_labels["历史最长天数"].setText(str(dashboard_data.get('max_streak', '--')))
            self.data_labels["平均效率"].setText(str(dashboard_data.get('average_efficiency', '--')))
        else:
            print("Error: dashboard_data is not a dictionary.")

        # Update Records
        eff_date = dashboard_data.get('max_efficiency_date', '----/--/--')
        eff_val = dashboard_data.get('max_efficiency_val', 0.0)
        self.data_labels["最高效率"].setText(f"{eff_val:.0%} ({eff_date})")

        dur_date = dashboard_data.get('max_duration_date', '----/--/--')
        dur_val = dashboard_data.get('max_duration_val', 0.0)
        self.data_labels["最长时长"].setText(f"{dur_val:.0f}s ({dur_date})")

        # --- Update Charts (Heatmap & Trend) ---
        heatmap_paths_raw = dashboard_data.get('heatmap_paths', {})
        trend_path = dashboard_data.get('trend_path')

        if hasattr(self, '_heatmap_years'):
            # JSON 序列化会把 int key 转成 str，统一还原为 int
            self._heatmap_paths = {}
            for k, v in heatmap_paths_raw.items():
                try:
                    self._heatmap_paths[int(k)] = v
                except (ValueError, TypeError):
                    self._heatmap_paths[k] = v
            self._heatmap_years = sorted(self._heatmap_paths.keys())

            # 默认定位到当前年份，若不存在则定位到最近一年
            current_year = time.localtime().tm_year
            if current_year in self._heatmap_years:
                self._heatmap_current_idx = self._heatmap_years.index(current_year)
            elif self._heatmap_years:
                self._heatmap_current_idx = len(self._heatmap_years) - 1
            else:
                self._heatmap_current_idx = 0

            _refresh_heatmap_display(self)

        if hasattr(self, 'chart_frame_duration'):
            _load_and_display_image(trend_path, self.chart_frame_duration)

        # --- Update Day List Treeview (按需加载月份) ---
        if hasattr(self, 'day_tree'):
            # 1. 获取所有有数据的月份
            available_months = audio_analasy.get_available_months(self)
            self._available_months = available_months
            
            # 2. 更新月份选择器
            current_month = datetime.now().strftime("%Y-%m")
            if hasattr(self, '_month_combo'):
                self._month_combo.clear()
                self._month_combo.addItems(available_months)
                
                # 如果当前已有选中项且在列表内，保持不变；否则默认选中当月或最新月
                current_selected = getattr(self, '_selected_month', None)
                if current_selected and current_selected in available_months:
                     pass # keep it
                elif current_month in available_months:
                    self._selected_month = current_month
                    self._month_combo.setCurrentText(current_month)
                elif available_months:
                    self._selected_month = available_months[0]
                    self._month_combo.setCurrentText(available_months[0])
                else:
                    self._selected_month = current_month # No data case
            
            # 3. 加载当前月份的数据
            _load_day_tree_for_month(self)

    except Exception as e:
        print(f"Error updating dashboard UI: {e}")
        traceback.print_exc()


def _load_day_tree_for_month(self):
    """加载指定月份的每日数据到 TreeView"""
    if not hasattr(self, 'day_tree'):
        return
    
    # 清空树
    self.day_tree.setRowCount(0)
    
    # 获取选中的月份
    selected_month = getattr(self, '_selected_month', None)
    if not selected_month:
        return

    # 调用后端新接口只获取该月数据
    records = audio_analasy.get_daily_records_by_month(self, selected_month)
    
    # 添加数据到树
    for record in records:
        row = self.day_tree.rowCount()
        self.day_tree.insertRow(row)
        for col, val in enumerate(record):
            self.day_tree.setItem(row, col, QtWidgets.QTableWidgetItem(str(val)))
