import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from .log_manager import get_logs, get_available_months, delete_logs, delete_logs_by_ids
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

    tk.Label(ctrl_frame, text="等级:", font=("微软雅黑", 10)).pack(side="left", padx=(10, 0))
    level_var = tk.StringVar(value="ALL")
    level_combo = ttk.Combobox(ctrl_frame, textvariable=level_var, values=["ALL", "INFO", "SUCCESS", "WARNING", "ERROR", "FATAL"], state="readonly", width=12, font=("微软雅黑", 10))
    level_combo.pack(side="left", padx=5)

    def load_logs(*args):
        for item in tree.get_children():
            tree.delete(item)
        logs = get_logs(log_type=type_var.get(), month=month_var.get(), level=level_var.get())
        for log in logs:
            log_id = log[0]
            tree.insert("", "end", iid=str(log_id), values=log[1:])

    def _confirm_delete(message):
        return messagebox.askyesno("确认删除", message)

    def delete_selected_logs():
        selected = list(tree.selection())
        if not selected:
            messagebox.showwarning("提示", "请先选择要删除的日志")
            return
        if not _confirm_delete(f"确定要删除选中的 {len(selected)} 条日志吗？"):
            return
        deleted = delete_logs_by_ids(selected)
        load_logs()
        self.log_success("删除日志", f"删除了选中的 {deleted} 条日志")
        messagebox.showinfo("完成", f"已删除 {deleted} 条日志")

    def delete_filtered_logs():
        msg = "确定要删除当前筛选条件下的日志吗？\n"
        msg += f"类型：{type_var.get()}\n等级：{level_var.get()}\n月份：{month_var.get()}"
        if not _confirm_delete(msg):
            return
        deleted = delete_logs(log_type=type_var.get(), month=month_var.get(), level=level_var.get())
        load_logs()
        self.log_success("删除日志", f"删除了筛选条件下的 {deleted} 条日志")
        messagebox.showinfo("完成", f"已删除 {deleted} 条日志")

    refresh_btn = tk.Button(ctrl_frame, text="刷新", font=("微软雅黑", 10), command=load_logs)
    refresh_btn.pack(side="left", padx=15)

    delete_selected_btn = tk.Button(ctrl_frame, text="删除选中", font=("微软雅黑", 10), command=delete_selected_logs)
    delete_selected_btn.pack(side="left", padx=(0, 10))

    delete_filtered_btn = tk.Button(ctrl_frame, text="删除筛选结果", font=("微软雅黑", 10), command=delete_filtered_logs)
    delete_filtered_btn.pack(side="left")

    # 列表区
    columns = ("timestamp", "log_level", "log_type", "account", "action", "details")
    tree = ttk.Treeview(viewer, columns=columns, show="headings")
    tree.heading("timestamp", text="时间")
    tree.heading("log_level", text="等级")
    tree.heading("log_type", text="类型")
    tree.heading("account", text="账号")
    tree.heading("action", text="操作")
    tree.heading("details", text="详细内容")

    tree.column("timestamp", width=150, anchor="center")
    tree.column("log_level", width=90, anchor="center")
    tree.column("log_type", width=100, anchor="center")
    tree.column("account", width=120, anchor="center")
    tree.column("action", width=160, anchor="center")
    tree.column("details", width=300, anchor="w")

    vsb = ttk.Scrollbar(viewer, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    type_combo.bind("<<ComboboxSelected>>", load_logs)
    month_combo.bind("<<ComboboxSelected>>", load_logs)
    level_combo.bind("<<ComboboxSelected>>", load_logs)
    load_logs()
