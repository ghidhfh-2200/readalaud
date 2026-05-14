"""
集中管理 GUI 通用操作：消息框、弹窗创建、窗口居中、主题切换。
"""

from PySide6 import QtCore, QtWidgets, QtGui
from .qt_helpers import ensure_app, run_on_ui, set_dark_palette


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
        ensure_app()
        parent_widget = self._parent(parent)
        return QtWidgets.QMessageBox.information(parent_widget, title, message)

    def warning(self, message, title="提示", parent=None):
        ensure_app()
        parent_widget = self._parent(parent)
        return QtWidgets.QMessageBox.warning(parent_widget, title, message)

    def error(self, message, title="错误", parent=None):
        ensure_app()
        parent_widget = self._parent(parent)
        return QtWidgets.QMessageBox.critical(parent_widget, title, message)

    def ask_yes_no(self, message, title="确认", parent=None):
        ensure_app()
        parent_widget = self._parent(parent)
        res = QtWidgets.QMessageBox.question(parent_widget, title, message)
        return res == QtWidgets.QMessageBox.StandardButton.Yes

    def ask_yes_no_cancel(self, message, title="确认", parent=None):
        ensure_app()
        parent_widget = self._parent(parent)
        res = QtWidgets.QMessageBox.question(
            parent_widget,
            title,
            message,
            QtWidgets.QMessageBox.StandardButton.Yes
            | QtWidgets.QMessageBox.StandardButton.No
            | QtWidgets.QMessageBox.StandardButton.Cancel,
        )
        if res == QtWidgets.QMessageBox.StandardButton.Yes:
            return True
        if res == QtWidgets.QMessageBox.StandardButton.No:
            return False
        return None

    def create_toplevel(self, title, size=None, parent=None, resizable=(False, False), modal=False, center=True):
        ensure_app()
        master = self._parent(parent)
        # Use QDialog for all toplevels so they appear as independent windows
        window = QtWidgets.QDialog(master)
        window.setWindowTitle(title)
        try:
            window.setWindowIcon(QtGui.QIcon("./assets/icon.ico"))
        except Exception:
            pass
        if size:
            width, height = size
            window.resize(width, height)
        if resizable is not None:
            if not (bool(resizable[0]) and bool(resizable[1])):
                window.setFixedSize(window.size())
        if center:
            self.center_window(window=window, parent=master)
        # Ensure modality is set correctly (application modal) if requested
        if modal:
            window.setModal(True)
            try:
                window.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
            except Exception:
                pass
        # Show as a separate dialog window (non-blocking)
        window.show()
        return window

    @staticmethod
    def center_window(window, parent=None):
        if window is None:
            return
        if parent is not None:
            parent_geo = parent.frameGeometry()
            center_point = parent_geo.center()
        else:
            screen = QtWidgets.QApplication.primaryScreen()
            center_point = screen.availableGeometry().center() if screen else QtCore.QPoint(0, 0)
        geo = window.frameGeometry()
        geo.moveCenter(center_point)
        window.move(geo.topLeft())

    @staticmethod
    def set_theme(theme_name):
        app = ensure_app()
        if theme_name == "darkly":
            set_dark_palette(app)
            return
        style = QtWidgets.QStyleFactory.create(theme_name)
        if style is not None:
            app.setStyle(style)

    @staticmethod
    def get_theme():
        app = ensure_app()
        return app.style().objectName() if app else ""

    @staticmethod
    def run_on_ui(callback):
        run_on_ui(callback)


_gui_service_singleton = GUIService()


def get_gui_service(owner=None):
    if owner is not None:
        _gui_service_singleton.bind_owner(owner)
    return _gui_service_singleton
