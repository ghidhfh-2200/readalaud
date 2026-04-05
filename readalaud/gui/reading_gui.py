"""
朗读页面 GUI：信息显示、开始/停止朗读、调试输出。
"""

import tkinter as tk
from ..reading import reading_data_get_and_check, start_reading


def _generate_reading_gui(self):
    if self.if_reading_show == True:
        return
    else:
        self.if_reading_show = True
    self.reading_frame = tk.Frame(master=self.main_window)
    self.main_paned_window.add(self.reading_frame)
    if self.if_main_window_show == True:
        self.content_frame.destroy()
        self.if_main_window_show = False

    # information show bar
    information_show_lbframe = tk.LabelFrame(master=self.reading_frame)
    information_show_lbframe.pack(fill="x", side="top", padx=5, pady=5)

    # 创建三个 Label，使用 grid 布局实现并排排列
    self.labels_list = [
        tk.Label(master=information_show_lbframe, text="朗读目标: 未读取", font=("微软雅黑", 15)),
        tk.Label(master=information_show_lbframe, text="声音阈值：未读取", font=("微软雅黑", 15)),
        tk.Label(master=information_show_lbframe, text="语音提示：未读取", font=("微软雅黑", 15)),
    ]
    # 详细信息标签
    read_detail_show_lb_frame = tk.LabelFrame(master=self.reading_frame, border=0)
    read_detail_show_lb_frame.pack(fill="x")
    read_detail_show_lb_frame.columnconfigure(0, weight=1)
    read_detail_show_lb_frame.columnconfigure(1, weight=1)
    read_detail_show_lb_frame.columnconfigure(2, weight=1)

    self.labels_list[0].grid(row=0, column=0, sticky="w", padx=10)
    self.labels_list[1].grid(row=0, column=1, sticky="n", padx=10)
    self.labels_list[2].grid(row=0, column=2, sticky="e", padx=10)

    self.information_label_list = [
        tk.Label(master=read_detail_show_lb_frame, text="剩余时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="停顿总时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="有效朗读时间: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="总时长: --:--:--", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="最大音量: 未知", font=("微软雅黑", 15)),
        tk.Label(master=read_detail_show_lb_frame, text="效率: 0.00", font=("微软雅黑", 15)),
    ]

    read_detail_show_lb_frame.columnconfigure(0, weight=1)
    read_detail_show_lb_frame.columnconfigure(1, weight=1)
    read_detail_show_lb_frame.columnconfigure(2, weight=1)

    self.information_label_list[0].grid(row=0, column=0, sticky="w", padx=10, pady=5)
    self.information_label_list[1].grid(row=0, column=1, sticky="n", padx=10, pady=5)
    self.information_label_list[2].grid(row=0, column=2, sticky="e", padx=10, pady=5)

    self.information_label_list[3].grid(row=1, column=0, sticky="w", padx=10, pady=5)
    self.information_label_list[4].grid(row=1, column=1, sticky="n", padx=10, pady=5)
    self.information_label_list[5].grid(row=1, column=2, sticky="e", padx=10, pady=5)

    # buttons
    start_button = tk.Button(
        master=self.reading_frame, text="开始朗读", font=("微软雅黑", 15),
        command=lambda: _start_reading(self),
    )
    start_button.pack(fill="x", pady=5)
    back_button = tk.Button(
        master=self.reading_frame, text="返回", font=("微软雅黑", 15),
        command=lambda: _reading_back(self),
    )
    back_button.pack(fill="x", pady=5)

    # state Label
    self.reading_state_label = tk.Label(
        master=self.reading_frame, text="正在准备中...", font=("微软雅黑", 40)
    )
    self.reading_state_label.pack(pady=10, fill="x")

    # debug_show
    self.show_debug = tk.Text(master=self.reading_frame, font=("Consolas", 13))
    debug_scroll = tk.Scrollbar(master=self.show_debug, command=self.show_debug.yview)
    self.show_debug.config(yscrollcommand=debug_scroll.set)
    debug_scroll.pack(side=tk.RIGHT, fill=tk.Y)
    self.show_debug.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    reading_data_get_and_check(self)


# ──────────────────────── 辅助回调 ────────────────────────

def _start_reading(self):
    start_reading(self=self)


def _reading_back(self):
    if self.if_reading == True:
        self.gui.info(
            title="无法退出！",
            message="当前朗读正在进行中，请勿退出朗读界面\n否则可能导致界面更新错误!",
        )
    else:
        self.welcome_page(destroy_window=[self.reading_frame, "reading"])
