import tkinter as tk
from tkinter import ttk
from datetime import datetime
from .log_manager import get_logs, get_available_months
from ..gui.gui_service import get_gui_service

def show_log_viewer(self):
    viewer = get_gui_service(self).create_toplevel(
        title="系统日志查看器 (System Log Viewer)",
        size=(900, 500),
        parent=self.main_window,
        resizable=(True, True),
        modal=False,
        center=True,
    )

    # 顶部控制区
    ctrl_frame = tk.Frame(viewer)
    ctrl_frame.pack(fill="x", padx=10, pady=10)

    # 选择月份
    tk.Label(ctrl_frame, text="选择月份:", font=("微软雅黑", 10)).pack(side="left")
    available_months = get_available_months()
    available_months.insert(0, "全部月份")
    
    month_var = tk.StringVar()
    # 默认选中当月
    current_month = datetime.now().strftime("%Y-%m")
    if current_month in available_months:
        month_var.set(current_month)
    else:
        month_var.set(available_months[1] if len(available_months) > 1 else "全部月份")

    month_combo = ttk.Combobox(ctrl_frame, textvariable=month_var, values=available_months, state="readonly", width=12, font=("微软雅黑", 10))
    month_combo.pack(side="left", padx=(5, 15))

    # 选择日志类型
    tk.Label(ctrl_frame, text="日志类型:", font=("微软雅黑", 10)).pack(side="left")
    type_var = tk.StringVar(value="ALL")
    type_combo = ttk.Combobox(ctrl_frame, textvariable=type_var, values=["ALL", "AUDIT", "OPERATION"], state="readonly", width=12, font=("微软雅黑", 10))
    type_combo.pack(side="left", padx=5)

    def load_logs(*args):
        for item in tree.get_children():
            tree.delete(item)
        logs = get_logs(log_type=type_var.get(), month=month_var.get())
        for log in logs:
            tree.insert("", "end", values=log)

    refresh_btn = tk.Button(ctrl_frame, text="刷新", font=("微软雅黑", 10), command=load_logs)
    refresh_btn.pack(side="left", padx=15)

    # 列表区
    columns = ("timestamp", "log_type", "account", "action", "details")
    tree = ttk.Treeview(viewer, columns=columns, show="headings")
    tree.heading("timestamp", text="时间")
    tree.heading("log_type", text="类型")
    tree.heading("account", text="账号")
    tree.heading("action", text="操作")
    tree.heading("details", text="详细内容")

    tree.column("timestamp", width=150, anchor="center")
    tree.column("log_type", width=100, anchor="center")
    tree.column("account", width=120, anchor="center")
    tree.column("action", width=160, anchor="center")
    tree.column("details", width=330, anchor="w")

    vsb = ttk.Scrollbar(viewer, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    type_combo.bind("<<ComboboxSelected>>", load_logs)
    month_combo.bind("<<ComboboxSelected>>", load_logs)
    load_logs()
