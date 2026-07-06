import argparse
import queue
import sys
import threading
import traceback
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = PROJECT_ROOT / "assets" / "icon.ico"


class _NativeSplash:
    """Tiny Win32 splash window that appears before PySide6 is imported."""

    def __init__(self):
        self._ready = threading.Event()
        self._stop = threading.Event()
        self._thread = None
        self._hwnd = None
        self._error = None

    def start(self):
        if sys.platform != "win32":
            return False
        self._thread = threading.Thread(target=self._run, daemon=True, name="native-splash")
        self._thread.start()
        self._ready.wait(timeout=1.0)
        return self._hwnd is not None

    def close(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

    def _run(self):
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            kernel32 = ctypes.windll.kernel32

            hinstance = kernel32.GetModuleHandleW(None)
            class_name = "ReadAlaudStartupSplash"

            LRESULT = ctypes.c_ssize_t
            WNDPROC = ctypes.WINFUNCTYPE(
                LRESULT,
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            )

            class WNDCLASS(ctypes.Structure):
                _fields_ = [
                    ("style", wintypes.UINT),
                    ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HINSTANCE),
                    ("hIcon", wintypes.HICON),
                    ("hCursor", wintypes.HANDLE),
                    ("hbrBackground", wintypes.HBRUSH),
                    ("lpszMenuName", wintypes.LPCWSTR),
                    ("lpszClassName", wintypes.LPCWSTR),
                ]

            class PAINTSTRUCT(ctypes.Structure):
                _fields_ = [
                    ("hdc", wintypes.HDC),
                    ("fErase", wintypes.BOOL),
                    ("rcPaint", wintypes.RECT),
                    ("fRestore", wintypes.BOOL),
                    ("fIncUpdate", wintypes.BOOL),
                    ("rgbReserved", ctypes.c_byte * 32),
                ]

            width, height = 300, 300

            user32.BeginPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
            user32.BeginPaint.restype = wintypes.HDC
            user32.EndPaint.argtypes = [wintypes.HWND, ctypes.POINTER(PAINTSTRUCT)]
            user32.EndPaint.restype = wintypes.BOOL
            user32.FillRect.argtypes = [wintypes.HDC, ctypes.POINTER(wintypes.RECT), wintypes.HBRUSH]
            user32.FillRect.restype = ctypes.c_int
            user32.DefWindowProcW.argtypes = [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ]
            user32.DefWindowProcW.restype = LRESULT
            user32.CreateWindowExW.restype = wintypes.HWND
            gdi32.GetStockObject.restype = wintypes.HANDLE
            gdi32.CreateSolidBrush.argtypes = [wintypes.COLORREF]
            gdi32.CreateSolidBrush.restype = wintypes.HBRUSH
            gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
            gdi32.DeleteObject.restype = wintypes.BOOL
            gdi32.CreateFontW.restype = wintypes.HFONT
            gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
            gdi32.SelectObject.restype = wintypes.HGDIOBJ
            gdi32.SetBkMode.argtypes = [wintypes.HDC, ctypes.c_int]
            gdi32.SetBkMode.restype = ctypes.c_int
            gdi32.SetTextColor.argtypes = [wintypes.HDC, wintypes.COLORREF]
            gdi32.SetTextColor.restype = wintypes.COLORREF
            user32.DrawIconEx.argtypes = [
                wintypes.HDC, ctypes.c_int, ctypes.c_int, wintypes.HICON,
                ctypes.c_int, ctypes.c_int, wintypes.UINT, wintypes.HBRUSH, wintypes.UINT,
            ]
            user32.DrawIconEx.restype = wintypes.BOOL
            user32.LoadImageW.restype = wintypes.HANDLE
            user32.DestroyIcon.argtypes = [wintypes.HICON]
            user32.DestroyIcon.restype = wintypes.BOOL
            user32.DrawTextW.argtypes = [wintypes.HDC, wintypes.LPCWSTR, ctypes.c_int, ctypes.POINTER(wintypes.RECT), wintypes.UINT]
            user32.DrawTextW.restype = ctypes.c_int

            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == 0x000F:  # WM_PAINT
                    ps = PAINTSTRUCT()
                    hdc = user32.BeginPaint(hwnd, ctypes.byref(ps))
                    try:
                        brush = gdi32.CreateSolidBrush(0x00FFFFFF)
                        rect = wintypes.RECT(0, 0, width, height)
                        user32.FillRect(hdc, ctypes.byref(rect), brush)
                        gdi32.DeleteObject(brush)

                        if ICON_PATH.exists():
                            icon = user32.LoadImageW(
                                None,
                                str(ICON_PATH),
                                1,  # IMAGE_ICON
                                160,
                                160,
                                0x00000010,  # LR_LOADFROMFILE
                            )
                            if icon:
                                user32.DrawIconEx(hdc, 70, 38, icon, 160, 160, 0, None, 0x0003)
                                user32.DestroyIcon(icon)

                        font = gdi32.CreateFontW(
                            22, 0, 0, 0,
                            400, 0, 0, 0,
                            134, 0, 0, 0, 0,
                            "Microsoft YaHei",
                        )
                        old_font = None
                        if font:
                            old_font = gdi32.SelectObject(hdc, font)
                        gdi32.SetBkMode(hdc, 1)
                        gdi32.SetTextColor(hdc, 0x00000000)
                        text_rect = wintypes.RECT(0, 218, width, 280)
                        user32.DrawTextW(
                            hdc,
                            "告别摸鱼偷懒\r\n回归大声早读",
                            -1,
                            ctypes.byref(text_rect),
                            0x0001 | 0x0020 | 0x0800,
                        )
                        if old_font:
                            gdi32.SelectObject(hdc, old_font)
                        if font:
                            gdi32.DeleteObject(font)
                    finally:
                        user32.EndPaint(hwnd, ctypes.byref(ps))
                    return 0
                if msg == 0x0002:  # WM_DESTROY
                    user32.PostQuitMessage(0)
                    return 0
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            self._wnd_proc = WNDPROC(wnd_proc)
            wc = WNDCLASS()
            wc.lpfnWndProc = self._wnd_proc
            wc.hInstance = hinstance
            wc.lpszClassName = class_name
            wc.hbrBackground = gdi32.GetStockObject(0)  # WHITE_BRUSH
            wc.hCursor = user32.LoadCursorW(None, 32512)
            user32.RegisterClassW(ctypes.byref(wc))

            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            x = (screen_w - width) // 2
            y = (screen_h - height) // 2
            hwnd = user32.CreateWindowExW(
                0x00000088,  # WS_EX_TOPMOST | WS_EX_TOOLWINDOW
                class_name,
                "ReadAlaud",
                0x80000000 | 0x10000000,  # WS_POPUP | WS_VISIBLE
                x,
                y,
                width,
                height,
                None,
                None,
                hinstance,
                None,
            )
            self._hwnd = hwnd
            user32.ShowWindow(hwnd, 5)
            user32.UpdateWindow(hwnd)
            self._ready.set()

            msg = wintypes.MSG()
            while not self._stop.is_set():
                while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 1):
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
                kernel32.Sleep(15)

            if self._hwnd:
                user32.DestroyWindow(self._hwnd)
                self._hwnd = None
        except Exception as exc:
            self._error = exc
            self._ready.set()


def _init_readalaud(result_queue):
    try:
        from readalaud.logger.log_manager import init_db, log_system

        init_db()
        log_system("启动程序", "background init")

        from readalaud.core import ReadAlaud

        result_queue.put(("ok", ReadAlaud()))
    except Exception:
        try:
            from readalaud.logger.log_manager import log_fatal

            log_fatal("初始化核心失败", traceback.format_exc())
        except Exception:
            pass
        result_queue.put(("error", traceback.format_exc()))


def _finish_startup(app, splash, result_queue, timer):
    from PySide6 import QtWidgets

    try:
        status, payload = result_queue.get_nowait()
    except queue.Empty:
        return

    timer.stop()

    if status == "ok":
        try:
            payload.generate_main_window()
            splash.close()
            app.processEvents()
            return
        except Exception:
            payload = traceback.format_exc()
            try:
                from readalaud.logger.log_manager import log_fatal

                log_fatal("创建主窗口失败", payload)
            except Exception:
                pass

    splash.close()
    QtWidgets.QMessageBox.critical(None, "启动失败", payload)
    app.quit()


def show_splash_and_start():
    splash = _NativeSplash()
    native_shown = splash.start()

    from PySide6 import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    try:
        from readalaud.gui.qt_helpers import init_ui_dispatcher

        init_ui_dispatcher()
    except Exception:
        pass

    if not native_shown:
        splash = _QtSplash()
        splash.start()
        app.processEvents()

    result_queue = queue.Queue(maxsize=1)
    worker = threading.Thread(target=_init_readalaud, args=(result_queue,), daemon=True)
    worker.start()

    timer = QtCore.QTimer()
    timer.setInterval(30)
    timer.timeout.connect(lambda: _finish_startup(app, splash, result_queue, timer))
    timer.start()
    app.exec()


class _QtSplash:
    def __init__(self):
        self._splash = None

    def start(self):
        from PySide6 import QtCore, QtGui, QtWidgets

        width = 300
        height = 300
        pixmap = QtGui.QPixmap(width, height)
        pixmap.fill(QtGui.QColor("white"))
        if ICON_PATH.exists():
            icon_pix = QtGui.QPixmap(str(ICON_PATH))
            if not icon_pix.isNull():
                target_size = int(min(width, height) * 0.72)
                icon_pix = icon_pix.scaled(
                    target_size,
                    target_size,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                painter = QtGui.QPainter(pixmap)
                painter.drawPixmap((width - icon_pix.width()) // 2, 28, icon_pix)
                painter.setPen(QtGui.QColor("black"))
                painter.setFont(QtGui.QFont("宋体", 14))
                painter.drawText(
                    0,
                    height - 60,
                    width,
                    40,
                    QtCore.Qt.AlignmentFlag.AlignCenter,
                    "告别摸鱼偷懒\n回归大声早读",
                )
                painter.end()
        self._splash = QtWidgets.QSplashScreen(pixmap)
        self._splash.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
        self._splash.show()
        return True

    def close(self):
        if self._splash is not None:
            self._splash.close()


def start_without_splash():
    from readalaud.logger.log_manager import init_db, log_system

    init_db()
    log_system("无启动图标模式", "--no-icon")

    from PySide6 import QtWidgets

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    from readalaud.gui.qt_helpers import init_ui_dispatcher

    init_ui_dispatcher()

    from readalaud.core import ReadAlaud

    r = ReadAlaud()
    r.generate_main_window()
    app.exec()


def main():
    parser = argparse.ArgumentParser(description="ReadAlaud 启动程序")
    parser.add_argument(
        "--no-icon",
        action="store_true",
        help="启动时不显示应用启动图标",
    )
    args = parser.parse_args()

    if args.no_icon:
        start_without_splash()
    else:
        show_splash_and_start()


if __name__ == "__main__":
    main()
