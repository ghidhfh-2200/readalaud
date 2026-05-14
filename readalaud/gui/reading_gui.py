"""
朗读页面 GUI：信息显示、开始/停止朗读、调试输出。
"""

from PySide6 import QtCore, QtWidgets, QtGui
from ..reading import reading_data_get_and_check, start_reading


def _generate_reading_gui(self):
    if self.if_reading_show == True:
        return
    else:
        self.if_reading_show = True
    self.reading_frame = QtWidgets.QWidget()
    self.reading_layout = QtWidgets.QVBoxLayout(self.reading_frame)
    self.reading_layout.setContentsMargins(10, 10, 10, 10)
    self.main_paned_window.addWidget(self.reading_frame, 7)
    if self.if_main_window_show == True:
        self.content_frame.deleteLater()
        self.if_main_window_show = False

    # information show bar
    information_show_lbframe = QtWidgets.QGroupBox()
    info_layout = QtWidgets.QGridLayout(information_show_lbframe)
    self.reading_layout.addWidget(information_show_lbframe)

    # 创建三个 Label，使用 grid 布局实现并排排列
    self.labels_list = [
        QtWidgets.QLabel("朗读目标: 未读取"),
        QtWidgets.QLabel("声音阈值：未读取"),
        QtWidgets.QLabel("语音提示：未读取"),
    ]
    for lbl in self.labels_list:
        lbl.setFont(QtGui.QFont("微软雅黑", 15))
    # 详细信息标签
    read_detail_show_lb_frame = QtWidgets.QGroupBox()
    detail_layout = QtWidgets.QGridLayout(read_detail_show_lb_frame)
    self.reading_layout.addWidget(read_detail_show_lb_frame)

    info_layout.addWidget(self.labels_list[0], 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    info_layout.addWidget(self.labels_list[1], 0, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
    info_layout.addWidget(self.labels_list[2], 0, 2, QtCore.Qt.AlignmentFlag.AlignRight)

    self.information_label_list = [
        QtWidgets.QLabel("剩余时长: --:--:--"),
        QtWidgets.QLabel("停顿总时长: --:--:--"),
        QtWidgets.QLabel("有效朗读时间: --:--:--"),
        QtWidgets.QLabel("总时长: --:--:--"),
        QtWidgets.QLabel("最大音量: 未知"),
        QtWidgets.QLabel("效率: 0.00"),
    ]
    for lbl in self.information_label_list:
        lbl.setFont(QtGui.QFont("微软雅黑", 15))

    detail_layout.addWidget(self.information_label_list[0], 0, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    detail_layout.addWidget(self.information_label_list[1], 0, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
    detail_layout.addWidget(self.information_label_list[2], 0, 2, QtCore.Qt.AlignmentFlag.AlignRight)
    detail_layout.addWidget(self.information_label_list[3], 1, 0, QtCore.Qt.AlignmentFlag.AlignLeft)
    detail_layout.addWidget(self.information_label_list[4], 1, 1, QtCore.Qt.AlignmentFlag.AlignHCenter)
    detail_layout.addWidget(self.information_label_list[5], 1, 2, QtCore.Qt.AlignmentFlag.AlignRight)

    # buttons
    start_button = QtWidgets.QPushButton("开始朗读")
    start_button.setFont(QtGui.QFont("微软雅黑", 15))
    start_button.clicked.connect(lambda: _start_reading(self))
    self.reading_layout.addWidget(start_button)
    back_button = QtWidgets.QPushButton("返回")
    back_button.setFont(QtGui.QFont("微软雅黑", 15))
    back_button.clicked.connect(lambda: _reading_back(self))
    self.reading_layout.addWidget(back_button)

    # state Label
    self.reading_state_label = QtWidgets.QLabel("正在准备中...")
    self.reading_state_label.setFont(QtGui.QFont("微软雅黑", 40))
    self.reading_state_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
    self.reading_layout.addWidget(self.reading_state_label)

    # debug_show
    self.show_debug = QtWidgets.QTextEdit()
    self.show_debug.setFont(QtGui.QFont("Consolas", 13))
    self.show_debug.setReadOnly(True)
    self.reading_layout.addWidget(self.show_debug, 1)
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
