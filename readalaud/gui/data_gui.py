"""
数据统计与图表展示页面 GUI：综合面板、每日数据、音频分析。
"""

import tkinter as tk
from tkinter import ttk, filedialog
import os
import shutil
import time
import wave
import traceback
import threading
from datetime import datetime, timedelta
from PIL import Image, ImageTk
from .. import audio_analysis as audio_analasy


# ══════════════════════════════════════════════════════════
#  主入口
# ══════════════════════════════════════════════════════════

def _generate_data_gui(self):
    """生成数据展示界面"""
    if self.if_data_form_show == True:
        return
    self.if_data_form_show = True
    self.data_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.data_frame)
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False

    # === 全局控件注册表 ===
    self.gui_components = {
        "labels": {},
        "canvases": {},
        "frames": {},
        "buttons": {},
    }

    def register_component(category, key, widget):
        if category in self.gui_components:
            self.gui_components[category][key] = widget
        return widget

    # 创建 Notebook
    notebook = ttk.Notebook(master=self.data_frame)
    general_frame = register_component("frames", "tab_general", tk.Frame(notebook))
    day_frame = register_component("frames", "tab_day", tk.Frame(notebook))

    notebook.add(general_frame, text="综合")
    notebook.add(day_frame, text="每日数据")
    notebook.pack(fill="both", expand=True)

    # 1. 综合数据
    _build_general_tab(self, general_frame, register_component)
    # 2. 每日数据
    _build_day_tab(self, day_frame, register_component)

    # 返回按钮
    back_button = register_component(
        "buttons", "global_return",
        tk.Button(
            master=self.data_frame, text="返回", font=self.mainpage_button_font,
            command=lambda: [
                self.welcome_page(destroy_window=[self.data_frame, "data_form"]),
                setattr(self, 'if_audio_analasy_running', False),
            ],
        ),
    )
    back_button.pack(fill="x", pady=5)
    refresh_general_dashboard(self)


# ══════════════════════════════════════════════════════════
#  通用辅助
# ══════════════════════════════════════════════════════════

def _bind_mousewheel_to_canvas(activate_widget: tk.Widget, canvas: tk.Canvas):
    """让滚轮在鼠标位于 activate_widget/canvas/其子控件上时都能滚动 canvas。"""
    def _on_mousewheel(event):
        try:
            if getattr(event, "num", None) == 4:
                canvas.yview_scroll(-1, "units")
            elif getattr(event, "num", None) == 5:
                canvas.yview_scroll(1, "units")
            else:
                delta = event.delta
                step = int(-1 * (delta / 120)) if delta else 0
                if step == 0 and delta:
                    step = -1 if delta > 0 else 1
                canvas.yview_scroll(step, "units")
        except tk.TclError:
            pass
        return "break"

    def _bind(_):
        activate_widget.bind_all("<MouseWheel>", _on_mousewheel)
        activate_widget.bind_all("<Button-4>", _on_mousewheel)
        activate_widget.bind_all("<Button-5>", _on_mousewheel)

    def _unbind(_):
        activate_widget.unbind_all("<MouseWheel>")
        activate_widget.unbind_all("<Button-4>")
        activate_widget.unbind_all("<Button-5>")

    activate_widget.bind("<Enter>", _bind)
    activate_widget.bind("<Leave>", _unbind)


def _load_and_display_image(path, parent_frame, width_hint=None):
    """Auxiliary to load image into a Frame"""
    for widget in parent_frame.winfo_children():
        widget.destroy()

    if not path or not os.path.exists(path):
        tk.Label(parent_frame, text="暂无图表数据", bg="#2b2b2b", fg="gray").pack(pady=20)
        return

    try:
        pil_img = Image.open(path)
        tk_img = ImageTk.PhotoImage(pil_img)
        label = tk.Label(parent_frame, image=tk_img, bg="#2b2b2b")
        label.image = tk_img  # keep reference to avoid GC
        label.pack(fill="both", expand=True)

        # Right-click menu for export
        menu = tk.Menu(label, tearoff=0)
        menu.add_command(label="导出图片", command=lambda: _export_image(path))

        def show_menu(event):
            menu.post(event.x_root, event.y_root)

        label.bind("<Button-3>", show_menu)

    except Exception as e:
        print(f"Error loading image {path}: {e}")
        tk.Label(parent_frame, text=f"加载失败: {e}", bg="#2b2b2b", fg="red").pack()

def _export_image(src_path):
    """Export the image to a user-selected location."""
    if not src_path or not os.path.exists(src_path):
        return

    try:
        ext = os.path.splitext(src_path)[1]
        dest_path = filedialog.asksaveasfilename(
            defaultextension=ext,
            filetypes=[("Image files", f"*{ext}"), ("All files", "*.*")],
            title="导出图片"
        )
        if dest_path:
            shutil.copy2(src_path, dest_path)
    except Exception as e:
        print(f"Error exporting image: {e}")


# ══════════════════════════════════════════════════════════
#  Tab 1 – 综合数据
# ══════════════════════════════════════════════════════════

def _build_general_tab(self, general_frame, register_component):
    general_frame.columnconfigure(0, weight=1)
    general_frame.rowconfigure(0, weight=1)

    data_canvas = register_component("canvases", "general_scroll", tk.Canvas(general_frame))
    data_scrollbar = ttk.Scrollbar(general_frame, orient="vertical", command=data_canvas.yview)
    scrollable_data_frame = tk.Frame(data_canvas)

    scrollable_data_frame.bind(
        "<Configure>", lambda _: data_canvas.configure(scrollregion=data_canvas.bbox("all"))
    )
    canvas_frame_window = data_canvas.create_window((0, 0), window=scrollable_data_frame, anchor="nw")
    data_canvas.bind("<Configure>", lambda e: data_canvas.itemconfig(canvas_frame_window, width=e.width))
    data_canvas.configure(yscrollcommand=data_scrollbar.set)

    data_scrollbar.pack(side="right", fill="y")
    data_canvas.pack(side="left", fill="both", expand=True)

    _bind_mousewheel_to_canvas(general_frame, data_canvas)
    _bind_mousewheel_to_canvas(data_canvas, data_canvas)
    _bind_mousewheel_to_canvas(scrollable_data_frame, data_canvas)

    # Top Control Area
    ctrl_frame = tk.Frame(scrollable_data_frame)
    ctrl_frame.pack(fill="x", padx=10, pady=(10, 0))
    
    register_component(
        "buttons", "general_refresh",
        tk.Button(
            ctrl_frame, text="⟳ 刷新仪表盘", font=("微软雅黑", 9),
            command=lambda: refresh_general_dashboard(self, force_refresh=True)
        )
    ).pack(side="right")

    # LabelFrame: 数据概览
    basic_data_lf = register_component(
        "frames", "general_basic_lf",
        tk.LabelFrame(scrollable_data_frame, text="数据概览", font=self.mainpage_button_font, padx=10, pady=10),
    )
    basic_data_lf.pack(fill="x", padx=10, pady=10)

    for i in range(5):
        basic_data_lf.columnconfigure(i, weight=1)

    headings_row1 = ["朗读总时长（秒）", "朗读总天数", "平均朗读时长", "当前连续朗读天数", "历史最长天数", "平均效率"]
    self.data_labels = {}

    for idx, title in enumerate(headings_row1):
        lbl_title = register_component(
            "labels", f"general_head_{idx}",
            tk.Label(basic_data_lf, text=title, font=("微软雅黑", 11)),
        )
        lbl_title.grid(row=0, column=idx, pady=(0, 5))

        lbl_val = register_component(
            "labels", f"general_val_{idx}",
            tk.Label(basic_data_lf, text="--", font=("微软雅黑", 13, "bold"), fg="#17a2b8"),
        )
        lbl_val.grid(row=1, column=idx, pady=(0, 5))
        self.data_labels[title] = lbl_val

    # Separator
    ttk.Separator(basic_data_lf, orient="horizontal").grid(row=2, column=0, columnspan=5, sticky="ew", pady=15)

    # Row 2: 记录
    l_eff_t = register_component(
        "labels", "general_rec_eff_title",
        tk.Label(basic_data_lf, text="最高效率 (日期)", font=("微软雅黑", 11)),
    )
    l_eff_t.grid(row=3, column=1, pady=(0, 5))

    lbl_eff = register_component(
        "labels", "general_rec_eff_val",
        tk.Label(basic_data_lf, text="-- (----/--/--)", font=("微软雅黑", 13, "bold"), fg="#28a745"),
    )
    lbl_eff.grid(row=4, column=1, pady=(0, 5))
    self.data_labels["最高效率"] = lbl_eff

    l_dur_t = register_component(
        "labels", "general_rec_dur_title",
        tk.Label(basic_data_lf, text="最长时长 (日期)", font=("微软雅黑", 11)),
    )
    l_dur_t.grid(row=3, column=3, pady=(0, 5))

    lbl_dur = register_component(
        "labels", "general_rec_dur_val",
        tk.Label(basic_data_lf, text="-- (----/--/--)", font=("微软雅黑", 13, "bold"), fg="#dc3545"),
    )
    lbl_dur.grid(row=4, column=3, pady=(0, 5))
    self.data_labels["最长时长"] = lbl_dur

    # LabelFrame: 数据图表
    charts_lf = register_component(
        "frames", "general_charts_lf",
        tk.LabelFrame(scrollable_data_frame, text="数据图表", font=self.mainpage_button_font, padx=10, pady=10),
    )
    charts_lf.pack(fill="x", padx=10, pady=10)

    # 热力图 — 标题 + 年份切换
    heatmap_title_frame = tk.Frame(charts_lf)
    heatmap_title_frame.pack(fill="x", pady=(5, 5))
    tk.Label(heatmap_title_frame, text="打卡热力图", font=("微软雅黑", 12)).pack(side="left")

    year_nav = tk.Frame(heatmap_title_frame)
    year_nav.pack(side="right")
    self._heatmap_year_prev_btn = tk.Button(
        year_nav, text="◀", font=("微软雅黑", 10), width=3, relief="flat",
        state="disabled", command=lambda: _switch_heatmap_year(self, -1),
    )
    self._heatmap_year_prev_btn.pack(side="left", padx=2)
    self._heatmap_year_label = tk.Label(
        year_nav, text="----", font=("微软雅黑", 12, "bold"), width=8, anchor="center",
    )
    self._heatmap_year_label.pack(side="left", padx=4)
    self._heatmap_year_next_btn = tk.Button(
        year_nav, text="▶", font=("微软雅黑", 10), width=3, relief="flat",
        state="disabled", command=lambda: _switch_heatmap_year(self, 1),
    )
    self._heatmap_year_next_btn.pack(side="left", padx=2)

    heatmap_container = tk.Frame(charts_lf, height=200, bg="#2b2b2b")
    heatmap_container.pack(fill="x", expand=True, pady=(0, 15))
    heatmap_container.pack_propagate(False)
    tk.Label(heatmap_container, text="[打卡热力图区域]", fg="#888888", bg="#2b2b2b").place(
        relx=0.5, rely=0.5, anchor="center",
    )
    self.chart_frame_heatmap = heatmap_container

    # 初始化跨年状态
    self._heatmap_years = []
    self._heatmap_paths = {}
    self._heatmap_current_idx = 0

    # 趋势图
    register_component(
        "labels", "general_chart_trend_title",
        tk.Label(charts_lf, text="每日朗读时长变化", font=("微软雅黑", 12)),
    ).pack(anchor="w", pady=(0, 5))
    duration_container = tk.Frame(charts_lf, bg="#2b2b2b")
    duration_container.pack(fill="x", expand=True)
    register_component(
        "labels", "general_chart_trend_ph",
        tk.Label(duration_container, text="[朗读时长趋势图区域]", fg="#888888", bg="#2b2b2b"),
    ).place(relx=0.5, rely=0.5, anchor="center")
    self.chart_frame_duration = duration_container


# ══════════════════════════════════════════════════════════
#  Tab 2 – 每日数据
# ══════════════════════════════════════════════════════════

def _build_day_tab(self, day_frame, register_component):
    self.day_list_container = tk.Frame(day_frame)
    self.day_list_container.pack(fill="both", expand=True)

    # Tool Bar for List
    list_tools = tk.Frame(self.day_list_container)
    list_tools.pack(fill="x", padx=10, pady=(5, 0))
    
    # 月份选择器
    month_frame = tk.Frame(list_tools)
    month_frame.pack(side="left", padx=(0, 15))
    
    tk.Label(month_frame, text="选择月份:", font=("微软雅黑", 9)).pack(side="left", padx=(0, 8))
    
    # 初始化月份选择器状态
    self._selected_month = datetime.now().strftime("%Y-%m")
    self._available_months = []
    
    month_combo = ttk.Combobox(
        month_frame, width=12, font=("微软雅黑", 9),
        state="readonly", textvariable=tk.StringVar(value=self._selected_month)
    )
    month_combo.pack(side="left")
    register_component("buttons", "day_month_combo", month_combo)
    
    def _on_month_change(_):
        """处理月份选择变化"""
        selected = month_combo.get()
        if selected:
            self._selected_month = selected
            _load_day_tree_for_month(self)
    
    month_combo.bind("<<ComboboxSelected>>", _on_month_change)
    self._month_combo = month_combo
    
    register_component(
        "buttons", "day_list_refresh",
        tk.Button(
            list_tools, text="⟳ 刷新历史列表", font=("微软雅黑", 9),
            command=lambda: refresh_general_dashboard(self, force_refresh=True)
        )
    ).pack(side="right")

    # Treeview
    day_columns = ("date", "duration", "pause", "progress")
    self.day_tree = ttk.Treeview(self.day_list_container, columns=day_columns, show="headings", height=15)
    for col, txt in zip(day_columns, ["日期", "总朗读时间", "停顿时间", "任务完成度"]):
        self.day_tree.heading(col, text=txt)

    day_scroll = ttk.Scrollbar(self.day_list_container, orient="vertical", command=self.day_tree.yview)
    self.day_tree.configure(yscrollcommand=day_scroll.set)
    day_scroll.pack(side="right", fill="y")
    self.day_tree.pack(side="top", fill="both", expand=True, padx=5, pady=5)

    # Day Detail Container (Hidden initially)
    self.day_detail_container = tk.Frame(day_frame)

    detail_canvas = register_component("canvases", "day_detail_scroll", tk.Canvas(self.day_detail_container))
    detail_vbar = ttk.Scrollbar(self.day_detail_container, orient="vertical", command=detail_canvas.yview)
    self.detail_scroll_frame = tk.Frame(detail_canvas)
    self.detail_scroll_frame.bind(
        "<Configure>", lambda _: detail_canvas.configure(scrollregion=detail_canvas.bbox("all"))
    )
    detail_canvas_window = detail_canvas.create_window((0, 0), window=self.detail_scroll_frame, anchor="nw")
    detail_canvas.bind("<Configure>", lambda e: detail_canvas.itemconfig(detail_canvas_window, width=e.width))
    detail_canvas.configure(yscrollcommand=detail_vbar.set)

    detail_vbar.pack(side="right", fill="y")
    detail_canvas.pack(side="left", fill="both", expand=True)

    _bind_mousewheel_to_canvas(self.day_detail_container, detail_canvas)
    _bind_mousewheel_to_canvas(detail_canvas, detail_canvas)
    _bind_mousewheel_to_canvas(self.detail_scroll_frame, detail_canvas)

    # Back Button
    button_frame = tk.Frame(self.detail_scroll_frame)
    button_frame.pack(anchor="w", padx=10, pady=5, fill="x")
    
    back_to_list_btn = register_component(
        "buttons", "day_back",
        tk.Button(
            button_frame, text="← 返回列表", font=self.mainpage_button_font,
            command=lambda: [
                audio_analasy.stop_day_audio(self=self, reset=True),
                self.day_detail_container.pack_forget(),
                self.day_list_container.pack(fill="both", expand=True),
            ],
        ),
    )
    back_to_list_btn.pack(side="left")
    
    # Refresh Button
    refresh_btn = register_component(
        "buttons", "day_refresh",
        tk.Button(
            button_frame, text="⟳ 刷新数据", font=self.mainpage_button_font,
            command=lambda: load_detail_data(getattr(self, 'current_view_date', None), force=True) 
        )
    )
    refresh_btn.pack(side="left", padx=10)

    analyze_btn = register_component(
        "buttons", "day_analyze",
        tk.Button(
            button_frame, text="📊 音频分析", font=self.mainpage_button_font,
            command=lambda: _show_analysis_dialog(self)
        )
    )
    analyze_btn.pack(side="left", padx=10)

    detail_stats_lf = register_component(
        "frames", "day_detail_lf",
        tk.LabelFrame(self.detail_scroll_frame, text="数据详情", font=self.mainpage_button_font, padx=10, pady=10),
    )
    detail_stats_lf.pack(fill="x", padx=10, pady=5)

    self.detail_val_labels = {}
    stats_titles = ["总时长", "停顿总时长", "效率", "完成度", "最大音量", "平均音量", "同比昨日"]
    for i, title in enumerate(stats_titles):
        row, col = i // 2, i % 2
        register_component(
            "labels", f"day_det_t_{title}",
            tk.Label(detail_stats_lf, text=f"{title}:", font=("微软雅黑", 11)),
        ).grid(row=row, column=col * 2, sticky="w", pady=2)
        lbl = register_component(
            "labels", f"day_det_v_{title}",
            tk.Label(detail_stats_lf, text="--", font=("微软雅黑", 11, "bold"), fg="#17a2b8"),
        )
        lbl.grid(row=row, column=col * 2 + 1, sticky="w", padx=(5, 20), pady=2)
        self.detail_val_labels[title] = lbl

    register_component(
        "labels", "day_vol_chart_title",
        tk.Label(self.detail_scroll_frame, text="音量变化趋势", font=("微软雅黑", 12)),
    ).pack(anchor="w", padx=15, pady=(10, 5))
    self.volume_chart_canvas = register_component(
        "canvases", "day_vol_chart",
        tk.Canvas(self.detail_scroll_frame, height=200, bg="#2b2b2b", highlightthickness=0),
    )
    self.volume_chart_canvas.pack(fill="x", padx=15, pady=5)

    # Audio Player
    detail_player_lf = register_component(
        "frames", "day_player_lf",
        tk.LabelFrame(self.detail_scroll_frame, text="当日录音回放", font=self.mainpage_button_font, padx=10, pady=10),
    )
    detail_player_lf.pack(fill="x", padx=10, pady=15)
    player_controls_detail = tk.Frame(detail_player_lf)
    player_controls_detail.pack(fill="x")
    
    self.day_play_btn = tk.Button(player_controls_detail, text="▶", width=4, command=self.play_day_audio)
    self.day_play_btn.pack(side="left", padx=5)
    self.day_pause_btn = tk.Button(player_controls_detail, text="⏸", width=4, command=self.pause_day_audio)
    self.day_pause_btn.pack(side="left", padx=5)
    
    self.day_audio_scale = ttk.Scale(
        player_controls_detail, from_=0, to=100, orient="horizontal", 
        command=lambda _: self.seek_day_audio()
    )
    self.day_audio_scale.pack(side="left", fill="x", expand=True, padx=10)
    self.day_audio_scale.bind("<ButtonRelease-1>", lambda _: self.seek_day_audio())
    
    self.day_audio_status = tk.Label(detail_player_lf, text="", fg="#dc3545", font=("微软雅黑", 10))
    self.day_audio_status.pack(anchor="w", padx=5, pady=(6, 0))

    self.init_audio_state()

    # ─── Audio Analysis Results Container (Hidden initially) ───
    self.day_analysis_container = tk.Frame(day_frame)

    _analysis_canvas = register_component(
        "canvases", "analysis_scroll", tk.Canvas(self.day_analysis_container)
    )
    _analysis_vbar = ttk.Scrollbar(
        self.day_analysis_container, orient="vertical", command=_analysis_canvas.yview
    )
    self._analysis_scroll_content = tk.Frame(_analysis_canvas)
    self._analysis_scroll_content.bind(
        "<Configure>",
        lambda _: _analysis_canvas.configure(scrollregion=_analysis_canvas.bbox("all")),
    )
    _acw = _analysis_canvas.create_window(
        (0, 0), window=self._analysis_scroll_content, anchor="nw"
    )
    _analysis_canvas.bind(
        "<Configure>", lambda e: _analysis_canvas.itemconfig(_acw, width=e.width)
    )
    _analysis_canvas.configure(yscrollcommand=_analysis_vbar.set)

    _analysis_vbar.pack(side="right", fill="y")
    _analysis_canvas.pack(side="left", fill="both", expand=True)

    _bind_mousewheel_to_canvas(self.day_analysis_container, _analysis_canvas)
    _bind_mousewheel_to_canvas(_analysis_canvas, _analysis_canvas)
    _bind_mousewheel_to_canvas(self._analysis_scroll_content, _analysis_canvas)

    _ab_frame = tk.Frame(self._analysis_scroll_content)
    _ab_frame.pack(anchor="w", padx=10, pady=5, fill="x")

    register_component(
        "buttons", "analysis_back",
        tk.Button(
            _ab_frame, text="← 返回详情", font=self.mainpage_button_font,
            command=lambda: [
                self.day_analysis_container.pack_forget(),
                self.day_detail_container.pack(fill="both", expand=True),
                setattr(self, 'if_audio_analasy_running', False)
            ],
        )
    ).pack(side="left")

    self._analysis_results_frame = tk.Frame(self._analysis_scroll_content)
    self._analysis_results_frame.pack(fill="both", expand=True, padx=10, pady=5)

    # Bindings
    def load_detail_data(target_date, force=False):
        """
        Helper to fetch and display daily detail
        """
        if not target_date:
            return
            
        try:
             # Progress state
            for label in self.detail_val_labels.values():
                label.config(text="加载中...", fg="#888888")
            self.day_detail_container.update_idletasks()
            
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
            self.day_audio_scale.config(from_=0, to=max(1, st["duration"]))
            if hasattr(self, "day_audio_status"):
                 self.day_audio_status.config(text="", fg="#dc3545")
            
            if not detail_data:
                for label in self.detail_val_labels.values():
                    label.config(text="无数据", fg="#dc3545")
                return

            # Update UI
            self.detail_val_labels["总时长"].config(text=f"{detail_data.get('total_duration', 0)} 秒", fg="#17a2b8")
            self.detail_val_labels["停顿总时长"].config(text=f"{detail_data.get('pause_duration', 0)} 秒", fg="#ffc107")
            self.detail_val_labels["效率"].config(text=f"{detail_data.get('efficiency', 0.0):.0%}", fg="#28a745")
            self.detail_val_labels["完成度"].config(text=detail_data.get('completion', '--'), fg="#6f42c1")
            self.detail_val_labels["最大音量"].config(text=f"{detail_data.get('max_volume', 0.0):.1f} dB", fg="#dc3545")
            self.detail_val_labels["平均音量"].config(text=f"{detail_data.get('avg_volume', 0.0):.1f} dB", fg="#fd7e14")
            self.detail_val_labels["同比昨日"].config(text=detail_data.get('compare_yesterday', '--'), fg="#20c997")
            
             # Chart
            vol_chart_path = detail_data.get('volume_chart_path', '')
            self.volume_chart_canvas.delete("all")
            for child in self.volume_chart_canvas.winfo_children():
                child.destroy()
            print("destroyed")
            if vol_chart_path and os.path.exists(vol_chart_path):
                # 先统一清空：Canvas 图元 + 子控件（上一次的图片 Label）
                _load_and_display_image(vol_chart_path, self.volume_chart_canvas)
            else:
                self.volume_chart_canvas.update_idletasks()
                w = self.volume_chart_canvas.winfo_width()
                h = self.volume_chart_canvas.winfo_height()
                if w <= 1 or h <= 1:
                    w, h = 300, 200
                self.volume_chart_canvas.create_text(
                    w // 2, h // 2,
                    text="暂无音量数据",
                    fill="#888888",
                    font=("微软雅黑", 10),
                )

            self.day_detail_container.update_idletasks()

        except Exception as e:
            print(f"Error loading daily detail: {e}")
            traceback.print_exc()

    def on_day_double_click(_):
        """
        双击每日数据列表项，加载并展示该日详情。
        """
        try:
            selection = self.day_tree.selection()
            if not selection:
                return
            item_values = self.day_tree.item(selection[0], 'values')
            if not item_values:
                return
            selected_date = item_values[0]
            
            # Switch View
            self.day_list_container.pack_forget()
            self.day_detail_container.pack(fill="both", expand=True)
            
            # Save State & Load
            self.current_view_date = selected_date
            
            self.stop_day_audio(reset=True)
            st = self._day_audio_state
            st.update({"path": "", "duration": 0.0, "offset": 0.0, "raw": b""})
            self.day_audio_scale.config(from_=0, to=100)
            if hasattr(self, "day_audio_status"):
                 self.day_audio_status.config(text="", fg="#dc3545")
            
            load_detail_data(selected_date, force=False)
            
        except Exception as e:
            print(f"Error handling double click: {e}")

    self.day_tree.bind("<Double-1>", on_day_double_click)


# ══════════════════════════════════════════════════════════
#  每日数据 – 音频分析弹窗 & 异步绘制
# ══════════════════════════════════════════════════════════

def _show_analysis_dialog(self):
    """弹出复选框对话框，让用户选择要执行的音频分析项目。"""
    dialog = tk.Toplevel(self.main_window)
    dialog.title("选择音频分析项目")
    dialog.geometry("420x560")
    dialog.resizable(False, True)
    dialog.transient(self.main_window)
    dialog.grab_set()

    # 居中于主窗口
    dialog.update_idletasks()
    px = self.main_window.winfo_rootx() + (self.main_window.winfo_width() - 420) // 2
    py = self.main_window.winfo_rooty() + (self.main_window.winfo_height() - 560) // 2
    dialog.geometry(f"+{max(0, px)}+{max(0, py)}")

    tk.Label(
        dialog, text="请勾选需要分析的项目：", font=("微软雅黑", 11)
    ).pack(anchor="w", padx=15, pady=(12, 2))
    tk.Label(
        dialog,
        text="💡 分析完成后，每项结果下方均附有通俗说明，点击「查看指标说明」可展开详细解读。",
        fg="#6c757d", font=("微软雅黑", 8),
        wraplength=390, justify="left",
    ).pack(anchor="w", padx=15, pady=(0, 8))

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
    for key, label, hint in analysis_options:
        row = tk.Frame(dialog)
        row.pack(fill="x", padx=12, pady=1)
        var = tk.BooleanVar(value=True)
        tk.Checkbutton(
            row, text=label, variable=var, font=("微软雅黑", 10), anchor="w",
        ).pack(side="left")
        tk.Label(
            row, text=hint, fg="#adb5bd", font=("微软雅黑", 8), anchor="w",
        ).pack(side="left", padx=(4, 0))
        cb_vars[key] = var

    # 全选 / 全不选
    sel_frame = tk.Frame(dialog)
    sel_frame.pack(fill="x", padx=20, pady=(8, 0))
    tk.Button(
        sel_frame, text="全选", font=("微软雅黑", 9),
        command=lambda: [v.set(True) for v in cb_vars.values()],
    ).pack(side="left", padx=(0, 6))
    tk.Button(
        sel_frame, text="全不选", font=("微软雅黑", 9),
        command=lambda: [v.set(False) for v in cb_vars.values()],
    ).pack(side="left")

    # 确定 / 取消
    btn_frame = tk.Frame(dialog)
    btn_frame.pack(side="bottom", pady=14)

    def on_confirm():
        selected = [k for k, v in cb_vars.items() if v.get()]
        dialog.destroy()
        if selected:
            _start_audio_analysis(self, selected)

    tk.Button(
        btn_frame, text="确定", width=10, font=("微软雅黑", 10), command=on_confirm
    ).pack(side="left", padx=8)
    tk.Button(
        btn_frame, text="取消", width=10, font=("微软雅黑", 10), command=dialog.destroy
    ).pack(side="left", padx=8)


def _start_audio_analysis(self, selected_keys):
    """切换到分析结果 Frame 并启动后台线程异步绘图。"""
    st = getattr(self, "_day_audio_state", {})
    audio_path = st.get("path", "")
    date_str = getattr(self, "current_view_date", "")

    # 切换视图: 详情 → 分析
    self.day_detail_container.pack_forget()
    self.day_analysis_container.pack(fill="both", expand=True)

    # 清除上次分析结果
    for w in self._analysis_results_frame.winfo_children():
        w.destroy()

    if not audio_path or not os.path.exists(audio_path):
        tk.Label(
            self._analysis_results_frame,
            text="⚠ 当前日期无可用音频文件，无法进行分析。",
            fg="#dc3545", font=("微软雅黑", 12),
        ).pack(pady=30)
        return

    # 停止播放
    audio_analasy.stop_day_audio(self, reset=True)

    # 创建加载占位
    placeholders = {}
    for key in selected_keys:
        desc = audio_analasy.ANALYSIS_DESCRIPTIONS.get(key, {})
        title = audio_analasy.ANALYSIS_ITEMS.get(key, key)
        brief = desc.get("brief", "")

        lf = tk.LabelFrame(
            self._analysis_results_frame, text=title,
            font=("微软雅黑", 11, "bold"), padx=8, pady=8,
        )
        lf.pack(fill="x", pady=6)

        # Brief description row
        if brief:
            tk.Label(
                lf, text=brief, fg="#6c757d", font=("微软雅黑", 9),
                wraplength=700, justify="left",
            ).pack(anchor="w", pady=(0, 4))

        tk.Label(lf, text="⏳ 分析中…", fg="#888888", font=("微软雅黑", 10)).pack(anchor="w")
        placeholders[key] = lf

    # 异步后台分析
    account = getattr(self, "current_acount", "")
    output_dir = os.path.join("./details", account, str(date_str))

    def _bg_worker():
        if self.if_audio_analasy_running==True:
            return
        self.if_audio_analasy_running = True
        time.sleep(0.2)  # 等待 GUI 渲染完成

        def _on_done(key, result):
            self.day_analysis_container.after(
                0, lambda k=key, r=result: _on_single_analysis_done(self, k, r, placeholders)
            )

        audio_analasy.run_selected_analyses(
            audio_path, selected_keys, output_dir, on_item_done=_on_done
        )

    threading.Thread(target=_bg_worker, daemon=True).start()


def _on_single_analysis_done(self, key, result, placeholders):
    """后台单项分析完成后在主线程刷新对应区域。"""
    lf = placeholders.get(key)
    if not lf or not lf.winfo_exists():
        return

    # 清空占位内容（保留 brief 标签，即第一个子控件）
    children = lf.winfo_children()
    # brief label is the first child if it exists, keep it; remove the rest
    for w in children[1:] if len(children) > 0 else children:
        w.destroy()
    # Also remove the loading label (always the last child at this point)
    remaining = lf.winfo_children()
    for w in remaining:
        # destroy non-brief labels (the ⏳ loading label)
        if isinstance(w, tk.Label) and "⏳" in (w.cget("text") or ""):
            w.destroy()

    if "error" in result:
        tk.Label(
            lf, text=f"❌ 分析失败: {result['error']}",
            fg="#dc3545", font=("微软雅黑", 10),
        ).pack(anchor="w")
        return

    # 加载图表
    chart_path = result.get("path", "")
    if chart_path and os.path.exists(chart_path):
        try:
            pil_img = Image.open(chart_path)
            tk_img = ImageTk.PhotoImage(pil_img)
            img_label = tk.Label(lf, image=tk_img)
            img_label.image = tk_img  # prevent GC
            img_label.pack(fill="x", expand=True)

            # Right-click menu for export
            menu = tk.Menu(img_label, tearoff=0)
            menu.add_command(label="导出图片", command=lambda: _export_image(chart_path))

            def show_menu(event):
                menu.post(event.x_root, event.y_root)

            img_label.bind("<Button-3>", show_menu)

        except Exception as e:
            tk.Label(
                lf, text=f"图表加载失败: {e}", fg="#dc3545", font=("微软雅黑", 10),
            ).pack(anchor="w")
    else:
        tk.Label(lf, text="无图表数据", fg="gray", font=("微软雅黑", 10)).pack(anchor="w")

    # ── 指标数值区域 ──
    extra = result.get("extra", {})
    desc = audio_analasy.ANALYSIS_DESCRIPTIONS.get(key, {})
    extra_tips = desc.get("extra_tips", {})
    detail_text = desc.get("detail", "")

    if extra:
        metrics_frame = tk.Frame(lf)
        metrics_frame.pack(anchor="w", fill="x", pady=(6, 0))
        for idx, (k, v) in enumerate(extra.items()):
            tip = extra_tips.get(k, "")
            # 指标值标签
            val_lf = tk.Frame(metrics_frame, relief="groove", bd=1, padx=6, pady=4)
            val_lf.grid(row=0, column=idx, padx=(0, 8), sticky="w")
            tk.Label(
                val_lf, text=k, fg="#6c757d", font=("微软雅黑", 8),
            ).pack(anchor="w")
            tk.Label(
                val_lf, text=str(v), fg="#17a2b8", font=("微软雅黑", 11, "bold"),
            ).pack(anchor="w")
            if tip:
                tk.Label(
                    val_lf, text=tip, fg="#adb5bd", font=("微软雅黑", 8),
                    wraplength=200, justify="left",
                ).pack(anchor="w", pady=(2, 0))

    # ── 可展开的详细说明 ──
    if detail_text:
        detail_visible = tk.BooleanVar(value=False)
        detail_content = tk.Frame(lf, bg="#f8f9fa", padx=8, pady=6, relief="flat", bd=1)
        detail_label = tk.Label(
            detail_content,
            text=detail_text,
            fg="#495057", bg="#f8f9fa",
            font=("微软雅黑", 9),
            justify="left",
            wraplength=700,
            anchor="nw",
        )
        detail_label.pack(fill="x", anchor="w")

        toggle_btn = tk.Button(
            lf, text="📖 查看指标说明 ▼",
            font=("微软雅黑", 9), relief="flat", fg="#007bff",
            cursor="hand2",
        )
        toggle_btn.pack(anchor="w", pady=(6, 0))

        def _toggle_detail(btn=toggle_btn, frame=detail_content, var=detail_visible):
            if var.get():
                frame.pack_forget()
                btn.config(text="📖 查看指标说明 ▼")
                var.set(False)
            else:
                frame.pack(fill="x", pady=(4, 0))
                btn.config(text="📖 收起说明 ▲")
                var.set(True)

        toggle_btn.config(command=_toggle_detail)

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
        self._heatmap_year_label.config(text="----")
        self._heatmap_year_prev_btn.config(state="disabled")
        self._heatmap_year_next_btn.config(state="disabled")
        return

    year = self._heatmap_years[self._heatmap_current_idx]
    self._heatmap_year_label.config(text=f"{year} 年")

    self._heatmap_year_prev_btn.config(
        state="normal" if self._heatmap_current_idx > 0 else "disabled"
    )
    self._heatmap_year_next_btn.config(
        state="normal" if self._heatmap_current_idx < len(self._heatmap_years) - 1 else "disabled"
    )

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
                 label.configure(text="加载中...")
             except Exception:
                 pass

    def _worker():
        try:
            # Fetch fresh analysis data
            dashboard_data = audio_analasy.refresh_dashboard_data(self, force_refresh=force_refresh)
            
            # Schedule UI update
            if hasattr(self, "data_frame") and self.data_frame.winfo_exists():
                self.data_frame.after(0, lambda: _update_dashboard_ui(self, dashboard_data))
        except Exception as e:
            print(f"Error refreshing dashboard: {e}")
            traceback.print_exc()

    threading.Thread(target=_worker, daemon=True).start()

def _update_dashboard_ui(self, dashboard_data):
    try:
        # --- Update Basic Stats in General Tab ---
        if isinstance(dashboard_data, dict):
            self.data_labels["朗读总天数"].configure(text=str(dashboard_data.get('total_days', '--')))
            self.data_labels["朗读总时长（秒）"].configure(text=f"{dashboard_data.get('total', 0):.2f}")
            self.data_labels["平均朗读时长"].configure(text=f"{dashboard_data.get('average_daily', 0):.2f}")
            self.data_labels["当前连续朗读天数"].configure(text=str(dashboard_data.get('current_streak', '--')))
            self.data_labels["历史最长天数"].configure(text=str(dashboard_data.get('max_streak', '--')))
            self.data_labels["平均效率"].configure(text=str(dashboard_data.get('average_efficiency', '--')))
        else:
            print("Error: dashboard_data is not a dictionary.")

        # Update Records
        eff_date = dashboard_data.get('max_efficiency_date', '----/--/--')
        eff_val = dashboard_data.get('max_efficiency_val', 0.0)
        self.data_labels["最高效率"].configure(text=f"{eff_val:.0%} ({eff_date})")

        dur_date = dashboard_data.get('max_duration_date', '----/--/--')
        dur_val = dashboard_data.get('max_duration_val', 0.0)
        self.data_labels["最长时长"].configure(text=f"{dur_val:.0f}s ({dur_date})")

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
                self._month_combo['values'] = available_months
                
                # 如果当前已有选中项且在列表内，保持不变；否则默认选中当月或最新月
                current_selected = getattr(self, '_selected_month', None)
                if current_selected and current_selected in available_months:
                     pass # keep it
                elif current_month in available_months:
                    self._selected_month = current_month
                    self._month_combo.set(current_month)
                elif available_months:
                    self._selected_month = available_months[0]
                    self._month_combo.set(available_months[0])
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
    for item in self.day_tree.get_children():
        self.day_tree.delete(item)
    
    # 获取选中的月份
    selected_month = getattr(self, '_selected_month', None)
    if not selected_month:
        return

    # 调用后端新接口只获取该月数据
    records = audio_analasy.get_daily_records_by_month(self, selected_month)
    
    # 添加数据到树
    for record in records:
        self.day_tree.insert("", tk.END, values=record)
