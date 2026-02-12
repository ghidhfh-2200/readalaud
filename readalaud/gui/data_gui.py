"""
数据统计与图表展示页面 GUI：综合面板、每日数据、音频分析。
"""

import tkinter as tk
from tkinter import ttk
import os
import traceback
from PIL import Image, ImageTk
from .. import audio_analasy


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
    audio_frame = register_component("frames", "tab_audio", tk.Frame(notebook))

    notebook.add(general_frame, text="综合")
    notebook.add(day_frame, text="每日数据")
    notebook.add(audio_frame, text="音频分析")
    notebook.pack(fill="both", expand=True)

    # 1. 综合数据
    _build_general_tab(self, general_frame, register_component)
    # 2. 每日数据
    _build_day_tab(self, day_frame, register_component)
    # 3. 音频分析
    _build_audio_tab(self, audio_frame, register_component)

    # 返回按钮
    back_button = register_component(
        "buttons", "global_return",
        tk.Button(
            master=self.data_frame, text="返回", font=self.mainpage_button_font,
            command=lambda: self.welcome_page(destroy_window=[self.data_frame, "data_form"]),
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
    except Exception as e:
        print(f"Error loading image {path}: {e}")
        tk.Label(parent_frame, text=f"加载失败: {e}", bg="#2b2b2b", fg="red").pack()


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

    # 热力图
    register_component(
        "labels", "general_chart_heat_title",
        tk.Label(charts_lf, text="打卡热力图", font=("微软雅黑", 12)),
    ).pack(anchor="w", pady=(5, 5))
    heatmap_container = tk.Frame(charts_lf, height=200, bg="#2b2b2b")
    heatmap_container.pack(fill="x", expand=True, pady=(0, 15))
    heatmap_container.pack_propagate(False)
    register_component(
        "labels", "general_chart_heat_ph",
        tk.Label(heatmap_container, text="[打卡热力图区域]", fg="#888888", bg="#2b2b2b"),
    ).place(relx=0.5, rely=0.5, anchor="center")
    self.chart_frame_heatmap = heatmap_container

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
    back_to_list_btn = register_component(
        "buttons", "day_back",
        tk.Button(
            self.detail_scroll_frame, text="← 返回列表", font=self.mainpage_button_font,
            command=lambda: [
                self.day_detail_container.pack_forget(),
                self.day_list_container.pack(fill="both", expand=True),
            ],
        ),
    )
    back_to_list_btn.pack(anchor="w", padx=10, pady=5)

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

    detail_player_lf = register_component(
        "frames", "day_player_lf",
        tk.LabelFrame(self.detail_scroll_frame, text="当日录音回放", font=self.mainpage_button_font, padx=10, pady=10),
    )
    detail_player_lf.pack(fill="x", padx=10, pady=15)
    player_controls_detail = tk.Frame(detail_player_lf)
    player_controls_detail.pack(fill="x")
    tk.Button(player_controls_detail, text="▶", width=4).pack(side="left", padx=5)
    tk.Button(player_controls_detail, text="⏸", width=4).pack(side="left", padx=5)
    ttk.Scale(player_controls_detail, from_=0, to=100, orient="horizontal").pack(
        side="left", fill="x", expand=True, padx=10
    )

    # Bindings
    def on_day_double_click(_):
        self.day_list_container.pack_forget()
        self.day_detail_container.pack(fill="both", expand=True)
        get_choice = self.day_tree.selection()[0]
        select_value = self.day_tree.item(get_choice)
        print(select_value)

    self.day_tree.bind("<Double-1>", on_day_double_click)


# ══════════════════════════════════════════════════════════
#  Tab 3 – 音频分析
# ══════════════════════════════════════════════════════════

def _build_audio_tab(self, audio_frame, register_component):
    audio_canvas = register_component(
        "canvases", "audio_scroll",
        tk.Canvas(audio_frame, bg="white", highlightthickness=0),
    )
    audio_scrollbar = ttk.Scrollbar(audio_frame, orient="vertical", command=audio_canvas.yview)
    audio_scroll_content = tk.Frame(audio_canvas, bg="white")

    audio_canvas_window = audio_canvas.create_window((0, 0), window=audio_scroll_content, anchor="nw")
    audio_canvas.configure(yscrollcommand=audio_scrollbar.set)
    audio_canvas.pack(side="left", fill="both", expand=True)
    audio_scrollbar.pack(side="right", fill="y")

    audio_scroll_content.bind(
        "<Configure>", lambda _: audio_canvas.configure(scrollregion=audio_canvas.bbox("all"))
    )
    audio_canvas.bind("<Configure>", lambda e: audio_canvas.itemconfig(audio_canvas_window, width=e.width))
    _bind_mousewheel_to_canvas(audio_frame, audio_canvas)
    _bind_mousewheel_to_canvas(audio_canvas, audio_canvas)
    _bind_mousewheel_to_canvas(audio_scroll_content, audio_canvas)

    section_title_font = ("微软雅黑", 12, "bold")
    subsection_font = ("微软雅黑", 10, "bold")

    def add_section(parent, title, key=""):
        frame = tk.LabelFrame(parent, text=title, font=section_title_font, bg="white", fg="#333", padx=10, pady=10)
        frame.pack(fill="x", padx=10, pady=10)
        if key:
            register_component("frames", key, frame)
        return frame

    def add_canvas(parent, height, key_name, bg="#202020"):
        canvas = tk.Canvas(parent, height=height, bg=bg, highlightthickness=0)
        canvas.pack(fill="x", pady=6)
        register_component("canvases", key_name, canvas)
        return canvas

    # (1) VAD
    vad_section = add_section(audio_scroll_content, "语音活动检测 (Voice Activity Detection)", "audio_sct_vad")
    register_component(
        "labels", "audio_vad_hint",
        tk.Label(vad_section, text="静默时间点 (Time-Line)", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(0, 6))

    vad_cols = ("start", "end", "duration")
    self.vad_silence_tree = ttk.Treeview(vad_section, columns=vad_cols, show="headings", height=6)
    for col, txt, w in zip(vad_cols, ("开始时间", "结束时间", "持续时长"), (110, 110, 100)):
        self.vad_silence_tree.heading(col, text=txt)
        self.vad_silence_tree.column(col, width=w, anchor="center")
    vad_scroll = ttk.Scrollbar(vad_section, orient="vertical", command=self.vad_silence_tree.yview)
    self.vad_silence_tree.configure(yscrollcommand=vad_scroll.set)
    self.vad_silence_tree.pack(side="left", fill="both", expand=True)
    vad_scroll.pack(side="right", fill="y")

    # (2) Quality Assessment
    quality_section = add_section(audio_scroll_content, "朗读质量评估", "audio_sct_qual")

    register_component(
        "labels", "audio_rms_t",
        tk.Label(quality_section, text="短时能量 (RMS) ", font=subsection_font, bg="white"),
    ).pack(anchor="w")
    self.rms_canvas = add_canvas(quality_section, 120, "audio_rms")

    register_component(
        "labels", "audio_zcr_t",
        tk.Label(quality_section, text="过零率与分贝叠加图", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(12, 0))
    self.zcr_db_canvas = add_canvas(quality_section, 140, "audio_zcr")

    register_component(
        "labels", "audio_zcr_list_t",
        tk.Label(quality_section, text="高过零率时间点", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(6, 0))
    zcr_cols = ("time", "zcr", "db")
    self.high_zcr_tree = ttk.Treeview(quality_section, columns=zcr_cols, show="headings", height=4)
    for col, txt, w in zip(zcr_cols, ("时间", "ZCR", "dB"), (120, 80, 80)):
        self.high_zcr_tree.heading(col, text=txt)
        self.high_zcr_tree.column(col, width=w, anchor="center")
    self.high_zcr_tree.pack(fill="x", pady=(2, 8))

    register_component(
        "labels", "audio_crest_t",
        tk.Label(quality_section, text="峰值因子 (Crest Factor) 谱", font=subsection_font, bg="white"),
    ).pack(anchor="w")
    self.crest_canvas = add_canvas(quality_section, 120, "audio_crest")

    register_component(
        "labels", "audio_ltas_t",
        tk.Label(quality_section, text="长时平均能量 (LTAS)", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(12, 4))
    ltas_cols = ("band", "energy")
    self.long_term_energy_tree = ttk.Treeview(quality_section, columns=ltas_cols, show="headings", height=5)
    for col, txt, w in zip(ltas_cols, ("频段", "能量值"), (140, 160)):
        self.long_term_energy_tree.heading(col, text=txt)
        self.long_term_energy_tree.column(col, width=w, anchor="center")
    self.long_term_energy_tree.pack(fill="x", pady=(0, 8))

    register_component(
        "labels", "audio_spec_t",
        tk.Label(quality_section, text="语谱图 (Spectrogram)", font=subsection_font, bg="white"),
    ).pack(anchor="w")
    self.spectrogram_canvas = add_canvas(quality_section, 160, "audio_spectrogram")

    register_component(
        "labels", "audio_env_t",
        tk.Label(quality_section, text="音量包络 (Energy Envelope)", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(12, 0))
    self.envelope_canvas = add_canvas(quality_section, 100, "audio_envelope")

    register_component(
        "labels", "audio_entr_t",
        tk.Label(quality_section, text="频谱熵 (Spectral Entropy)", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(12, 0))
    self.spectral_entropy_canvas = add_canvas(quality_section, 120, "audio_entropy")

    register_component(
        "labels", "audio_pitch_t",
        tk.Label(quality_section, text="音高曲线 (Pitch Contour)", font=subsection_font, bg="white"),
    ).pack(anchor="w", pady=(12, 0))
    self.pitch_canvas = add_canvas(quality_section, 120, "audio_pitch")

    audio_scroll_content.update_idletasks()
    audio_canvas.configure(scrollregion=audio_canvas.bbox("all"))


# ══════════════════════════════════════════════════════════
#  数据面板刷新
# ══════════════════════════════════════════════════════════

def refresh_general_dashboard(self):
    try:
        # Fetch fresh analysis data
        dashboard_data = audio_analasy.refresh_dashboard_data(self)

        # --- Update Basic Stats in General Tab ---
        if isinstance(dashboard_data, dict):
            self.data_labels["朗读总天数"].config(text=str(dashboard_data.get('total_days', '--')))
            self.data_labels["朗读总时长（秒）"].config(text=f"{dashboard_data.get('total', 0):.2f}")
            self.data_labels["平均朗读时长"].config(text=f"{dashboard_data.get('average_daily', 0):.2f}")
            self.data_labels["当前连续朗读天数"].config(text=str(dashboard_data.get('current_streak', '--')))
            self.data_labels["历史最长天数"].config(text=str(dashboard_data.get('max_streak', '--')))
            self.data_labels["平均效率"].config(text=str(dashboard_data.get('average_efficiency', '--')))
        else:
            print("Error: dashboard_data is not a dictionary.")

        # Update Records
        eff_date = dashboard_data.get('max_efficiency_date', '----/--/--')
        eff_val = dashboard_data.get('max_efficiency_val', 0.0)
        self.data_labels["最高效率"].config(text=f"{eff_val:.0%} ({eff_date})")

        dur_date = dashboard_data.get('max_duration_date', '----/--/--')
        dur_val = dashboard_data.get('max_duration_val', 0.0)
        self.data_labels["最长时长"].config(text=f"{dur_val:.0f}s ({dur_date})")

        # --- Update Charts (Heatmap & Trend) ---
        heatmap_path = dashboard_data.get('heatmap_path')
        trend_path = dashboard_data.get('trend_path')

        if hasattr(self, 'chart_frame_heatmap') and heatmap_path:
            _load_and_display_image(heatmap_path, self.chart_frame_heatmap)

        if hasattr(self, 'chart_frame_duration'):
            _load_and_display_image(trend_path, self.chart_frame_duration)

        # --- Update Day List Treeview ---
        if hasattr(self, 'day_tree'):
            for item in self.day_tree.get_children():
                self.day_tree.delete(item)

            for record in dashboard_data.get('daily_records', []):
                self.day_tree.insert("", tk.END, values=record)

    except Exception as e:
        print(f"Error refreshing dashboard: {e}")
        traceback.print_exc()
