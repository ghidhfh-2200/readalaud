import tkinter as tk
from tkinter import ttk
from .log_manager import get_logs

def show_log_viewer(self):
    viewer = tk.Toplevel(self.main_window)
    viewer.title("系统日志查看器 (System Log Viewer)")
    viewer.geometry("800x500")
    # 居中显示
    viewer.update_idletasks()
    px = self.main_window.winfo_rootx() + (self.main_window.winfo_width() - 800) // 2
    py = self.main_window.winfo_rooty() + (self.main_window.winfo_height() - 500) // 2
    viewer.geometry(f"+{max(0, px)}+{max(0, py)}")

    # 顶部控制区
    ctrl_frame = tk.Frame(viewer)
    ctrl_frame.pack(fill="x", padx=10, pady=10)

    tk.Label(ctrl_frame, text="日志类型:", font=("微软雅黑", 10)).pack(side="left")
    type_var = tk.StringVar(value="ALL")
    type_combo = ttk.Combobox(ctrl_frame, textvariable=type_var, values=["ALL", "AUDIT", "OPERATION"], state="readonly", width=12, font=("微软雅黑", 10))
    type_combo.pack(side="left", padx=5)

    def load_logs(*args):
        for item in tree.get_children():
            tree.delete(item)
        logs = get_logs(type_var.get())
        for log in logs:
            tree.insert("", "end", values=log)

    refresh_btn = tk.Button(ctrl_frame, text="刷新", font=("微软雅黑", 10), command=load_logs)
    refresh_btn.pack(side="left", padx=10)

    # 列表区
    columns = ("timestamp", "log_type", "account", "action", "details")
    tree = ttk.Treeview(viewer, columns=columns, show="headings")
    tree.heading("timestamp", text="时间")
    tree.heading("log_type", text="类型")
    tree.heading("account", text="账号")
    tree.heading("action", text="操作")
    tree.heading("details", text="详细内容")

    tree.column("timestamp", width=140, anchor="center")
    tree.column("log_type", width=80, anchor="center")
    tree.column("account", width=100, anchor="center")
    tree.column("action", width=150, anchor="center")
    tree.column("details", width=300, anchor="w")

    vsb = ttk.Scrollbar(viewer, orient="vertical", command=tree.yview)
    vsb.pack(side="right", fill="y")
    tree.configure(yscrollcommand=vsb.set)
    tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    type_combo.bind("<<ComboboxSelected>>", load_logs)
    load_logs()
