import argparse
import threading
import traceback
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from readalaud.logger.log_manager import init_db, log_system, log_fatal


PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = PROJECT_ROOT / "assets" / "icon.ico"


def show_splash_and_start():
    init_db()
    log_system("启动程序", "show_splash_and_start")
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    width = 300
    height = 300
    pixmap = QtGui.QPixmap(width, height)
    pixmap.fill(QtGui.QColor("white"))
    if ICON_PATH.exists():
        try:
            icon_pix = QtGui.QPixmap(str(ICON_PATH))
            if not icon_pix.isNull():
                target_size = int(min(width, height) * 0.72)
                icon_pix = icon_pix.scaled(
                    target_size, target_size,
                    QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                    QtCore.Qt.TransformationMode.SmoothTransformation,
                )
                painter = QtGui.QPainter(pixmap)
                x = (width - icon_pix.width()) // 2
                y = (height - icon_pix.height()) // 2 - 10
                painter.drawPixmap(x, y, icon_pix)
                painter.setPen(QtGui.QColor("black"))
                painter.setFont(QtGui.QFont("宋体", 14))
                painter.drawText(
                    0, height - 60, width, 40,
                    QtCore.Qt.AlignmentFlag.AlignCenter,
                    "告别摸鱼偷懒\n回归大声早读",
                )
                painter.end()
        except Exception as e:
            log_system("加载启动图标失败", str(e))
    else:
        log_system("加载启动图标失败", f"找不到启动图标：{ICON_PATH}")

    splash = QtWidgets.QSplashScreen(pixmap)
    splash.setWindowFlag(QtCore.Qt.WindowType.WindowStaysOnTopHint, True)
    splash.show()
    app.processEvents()

    # Create the main application on the MAIN thread.
    # Qt widgets (especially QMainWindow) MUST be created
    # on the GUI thread; creating them in a worker thread
    # leads to silent failure – no window appears.
    try:
        from readalaud.core import ReadAlaud

        r = ReadAlaud()
        r.generate_main_window()
    except Exception:
        log_fatal("初始化核心失败", traceback.format_exc())
        traceback.print_exc()
        splash.close()
        return

    splash.close()
    app.processEvents()
    app.exec()


def main():
    init_db()
    log_system("调用 main", "program entry")
    parser = argparse.ArgumentParser(description="ReadAlaud 启动程序")
    parser.add_argument(
        "--no-icon", action="store_true",
        help="启动时不显示应用启动图标",
    )
    args = parser.parse_args()

    if args.no_icon:
        log_system("无启动图标模式", "--no-icon")
        from readalaud.core import ReadAlaud

        app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
        r = ReadAlaud()
        r.generate_main_window()
        app.exec()
    else:
        show_splash_and_start()


if __name__ == '__main__':
    main()
