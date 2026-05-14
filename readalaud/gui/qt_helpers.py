"""
Qt helper utilities: value holders and UI dispatcher.
"""

from __future__ import annotations

from PySide6 import QtCore, QtWidgets, QtGui


class ValueHolder(QtCore.QObject):
    """Simple value holder with a change signal."""

    changed = QtCore.Signal(object)

    def __init__(self, value=None, parent=None):
        super().__init__(parent)
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        self.changed.emit(value)

    def __repr__(self):
        return f"ValueHolder({self._value!r})"


class UiDispatcher(QtCore.QObject):
    """Thread-safe UI dispatcher."""

    dispatch = QtCore.Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dispatch.connect(self._run)

    @QtCore.Slot(object)
    def _run(self, callback):
        try:
            callback()
        except Exception:
            pass


_dispatcher_singleton = UiDispatcher()


def run_on_ui(callback):
    """Schedule a callback on the Qt UI thread."""
    _dispatcher_singleton.dispatch.emit(callback)


def ensure_app():
    """Ensure a QApplication instance exists."""
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def set_dark_palette(app: QtWidgets.QApplication):
    """Apply a dark palette to the application."""
    palette = QtGui.QPalette()
    palette.setColor(QtGui.QPalette.Window, QtGui.QColor(43, 43, 43))
    palette.setColor(QtGui.QPalette.WindowText, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.Base, QtGui.QColor(30, 30, 30))
    palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(45, 45, 45))
    palette.setColor(QtGui.QPalette.ToolTipBase, QtGui.QColor(255, 255, 255))
    palette.setColor(QtGui.QPalette.ToolTipText, QtGui.QColor(0, 0, 0))
    palette.setColor(QtGui.QPalette.Text, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
    palette.setColor(QtGui.QPalette.ButtonText, QtGui.QColor(220, 220, 220))
    palette.setColor(QtGui.QPalette.BrightText, QtGui.QColor(255, 0, 0))
    palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(45, 140, 240))
    palette.setColor(QtGui.QPalette.HighlightedText, QtGui.QColor(255, 255, 255))
    app.setPalette(palette)
