"""
集中管理 GUI 通用操作：消息框、弹窗创建、窗口居中、主题切换。
"""

import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkbs


class GUIService:
    """统一 GUI 服务层，供业务模块调用，避免散落的 tkinter 操作。"""

    def __init__(self, owner=None):
        self.owner = owner

    def bind_owner(self, owner):
        self.owner = owner
        return self

    def _parent(self, parent=None):
        if parent is not None:
            return parent
        return getattr(self.owner, "main_window", None)

    def info(self, message, title="提示", parent=None):
        kwargs = {"message": message, "title": title}
        resolved_parent = self._parent(parent)
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        return messagebox.showinfo(**kwargs)

    def warning(self, message, title="提示", parent=None):
        kwargs = {"message": message, "title": title}
        resolved_parent = self._parent(parent)
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        return messagebox.showwarning(**kwargs)

    def error(self, message, title="错误", parent=None):
        kwargs = {"message": message, "title": title}
        resolved_parent = self._parent(parent)
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        return messagebox.showerror(**kwargs)

    def ask_yes_no(self, message, title="确认", parent=None):
        kwargs = {"message": message, "title": title}
        resolved_parent = self._parent(parent)
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        return messagebox.askyesno(**kwargs)

    def ask_yes_no_cancel(self, message, title="确认", parent=None):
        kwargs = {"message": message, "title": title}
        resolved_parent = self._parent(parent)
        if resolved_parent is not None:
            kwargs["parent"] = resolved_parent
        return messagebox.askyesnocancel(**kwargs)

    def create_toplevel(self, title, size=None, parent=None, resizable=(False, False), modal=False, center=True):
        master = self._parent(parent)
        window = tk.Toplevel(master=master) if master is not None else tk.Toplevel()
        window.title(title)
        if size:
            width, height = size
            window.geometry(f"{width}x{height}")
        if resizable is not None:
            window.resizable(bool(resizable[0]), bool(resizable[1]))
        if master is not None:
            window.transient(master)
        if modal:
            window.grab_set()
        if center:
            self.center_window(window=window, parent=master)
        return window

    @staticmethod
    def center_window(window, parent=None):
        window.update_idletasks()
        width = window.winfo_width()
        height = window.winfo_height()

        if parent is not None and parent.winfo_exists():
            px = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
            py = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        else:
            sw = window.winfo_screenwidth()
            sh = window.winfo_screenheight()
            px = (sw - width) // 2
            py = (sh - height) // 2

        window.geometry(f"+{max(0, px)}+{max(0, py)}")

    @staticmethod
    def set_theme(theme_name):
        ttkbs.Style().theme_use(theme_name)

    @staticmethod
    def get_theme():
        return ttkbs.Style().theme_use()


_gui_service_singleton = GUIService()


def get_gui_service(owner=None):
    if owner is not None:
        _gui_service_singleton.bind_owner(owner)
    return _gui_service_singleton
