from PySide6 import QtWidgets, QtCore
from datetime import datetime
from .log_manager import get_logs, get_available_months, delete_logs, delete_logs_by_ids
from ..gui.gui_service import get_gui_service

class ValueHolder:
    def __init__(self, value=None):
        self._value = value
        
    def get(self):
        return self._value
        
    def set(self, val):
        self._value = val

def show_log_viewer(self):
    viewer = get_gui_service(self).create_toplevel(
        title="系统日志查看器 (System Log Viewer)",
        size=(900, 500),
        parent=self.main_window,
        resizable=(True, True),
        modal=False,
        center=True,
    )
    
    # Create the main layout
    main_layout = QtWidgets.QVBoxLayout(viewer)
    main_layout.setContentsMargins(10, 10, 10, 10)
    
    # 顶部控制区
    ctrl_frame = QtWidgets.QWidget()
    ctrl_layout = QtWidgets.QHBoxLayout(ctrl_frame)
    ctrl_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.addWidget(ctrl_frame)

    # 选择月份
    ctrl_layout.addWidget(QtWidgets.QLabel("选择月份:"))
    available_months = get_available_months()
    available_months.insert(0, "全部月份")
    
    month_var = ValueHolder()
    current_month = datetime.now().strftime("%Y-%m")
    if current_month in available_months:
        month_var.set(current_month)
    else:
        month_var.set(available_months[1] if len(available_months) > 1 else "全部月份")

    month_combo = QtWidgets.QComboBox()
    month_combo.addItems(available_months)
    month_combo.setCurrentText(month_var.get())
    ctrl_layout.addWidget(month_combo)
    
    def on_month_changed(text):
        month_var.set(text)
        load_logs()
    month_combo.currentTextChanged.connect(on_month_changed)

    # 选择日志类型
    ctrl_layout.addWidget(QtWidgets.QLabel("日志类型:"))
    type_var = ValueHolder("ALL")
    type_combo = QtWidgets.QComboBox()
    type_combo.addItems(["ALL", "AUDIT", "OPERATION"])
    type_combo.setCurrentText(type_var.get())
    ctrl_layout.addWidget(type_combo)
    
    def on_type_changed(text):
        type_var.set(text)
        load_logs()
    type_combo.currentTextChanged.connect(on_type_changed)

    ctrl_layout.addWidget(QtWidgets.QLabel("等级:"))
    level_var = ValueHolder("ALL")
    level_combo = QtWidgets.QComboBox()
    level_combo.addItems(["ALL", "INFO", "SUCCESS", "WARNING", "ERROR", "FATAL"])
    level_combo.setCurrentText(level_var.get())
    ctrl_layout.addWidget(level_combo)

    def on_level_changed(text):
        level_var.set(text)
        load_logs()
    level_combo.currentTextChanged.connect(on_level_changed)

    def load_logs():
        table.setRowCount(0)
        logs = get_logs(log_type=type_var.get(), month=month_var.get(), level=level_var.get())
        for log in logs:
            log_id = log[0]
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            
            # Store log_id invisibly via QTableWidgetItem user data on the first item
            item0 = QtWidgets.QTableWidgetItem(str(log[1]))
            item0.setData(QtCore.Qt.UserRole, log_id)
            table.setItem(row_idx, 0, item0)
            table.setItem(row_idx, 1, QtWidgets.QTableWidgetItem(str(log[2])))
            table.setItem(row_idx, 2, QtWidgets.QTableWidgetItem(str(log[3])))
            table.setItem(row_idx, 3, QtWidgets.QTableWidgetItem(str(log[4])))
            table.setItem(row_idx, 4, QtWidgets.QTableWidgetItem(str(log[5])))
            table.setItem(row_idx, 5, QtWidgets.QTableWidgetItem(str(log[6])))

    def _confirm_delete(message):
        reply = QtWidgets.QMessageBox.question(
            viewer, "确认删除", message,
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        return reply == QtWidgets.QMessageBox.Yes

    def delete_selected_logs():
        selected_rows = set(item.row() for item in table.selectedItems())
        if not selected_rows:
            QtWidgets.QMessageBox.warning(viewer, "提示", "请先选择要删除的日志")
            return
        if not _confirm_delete(f"确定要删除选中的 {len(selected_rows)} 条日志吗？"):
            return
            
        selected_ids = []
        for row in selected_rows:
            item = table.item(row, 0)
            if item:
                selected_ids.append(item.data(QtCore.Qt.UserRole))
                
        deleted = delete_logs_by_ids(selected_ids)
        load_logs()
        self.log_success("删除日志", f"删除了选中的 {deleted} 条日志")
        QtWidgets.QMessageBox.information(viewer, "完成", f"已删除 {deleted} 条日志")

    def delete_filtered_logs():
        msg = "确定要删除当前筛选条件下的日志吗？\n"
        msg += f"类型：{type_var.get()}\n等级：{level_var.get()}\n月份：{month_var.get()}"
        if not _confirm_delete(msg):
            return
        deleted = delete_logs(log_type=type_var.get(), month=month_var.get(), level=level_var.get())
        load_logs()
        self.log_success("删除日志", f"删除了筛选条件下的 {deleted} 条日志")
        QtWidgets.QMessageBox.information(viewer, "完成", f"已删除 {deleted} 条日志")

    ctrl_layout.addStretch()

    refresh_btn = QtWidgets.QPushButton("刷新")
    refresh_btn.clicked.connect(load_logs)
    ctrl_layout.addWidget(refresh_btn)

    delete_selected_btn = QtWidgets.QPushButton("删除选中")
    delete_selected_btn.clicked.connect(delete_selected_logs)
    ctrl_layout.addWidget(delete_selected_btn)

    delete_filtered_btn = QtWidgets.QPushButton("删除筛选结果")
    delete_filtered_btn.clicked.connect(delete_filtered_logs)
    ctrl_layout.addWidget(delete_filtered_btn)

    # 列表区
    columns = ["时间", "等级", "类型", "账号", "操作", "详细内容"]
    table = QtWidgets.QTableWidget()
    table.setColumnCount(len(columns))
    table.setHorizontalHeaderLabels(columns)
    table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
    table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
    main_layout.addWidget(table)
    
    header = table.horizontalHeader()
    header.resizeSection(0, 150)
    header.resizeSection(1, 90)
    header.resizeSection(2, 100)
    header.resizeSection(3, 120)
    header.resizeSection(4, 160)
    header.setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)

    load_logs()

    # ensure the viewer is shown if it is a widget
    if isinstance(viewer, QtWidgets.QWidget) and not viewer.isVisible():
        viewer.show()
