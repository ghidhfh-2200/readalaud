"""
settings_io.py —— 全局设置缓存 + 退出异步保存。

架构：
  - _settings_cache: 模块级全局设置字典，加载时初始化，修改时即时更新。
  - 所有 UI 修改直接更新缓存，不再需要「确定/保存」按钮。
  - 退出时异步将缓存落盘到 settings.json。
"""
import base64
import json
import os
import threading

from PySide6 import QtCore, QtWidgets

DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}

# ── 全局设置缓存 ──────────────────────────────────────────

_settings_cache: dict = {}
_current_account: str = ""


def get_settings_cache() -> dict:
    """返回当前设置缓存的浅拷贝。"""
    return _settings_cache.copy()


def get_setting(key, default=None):
    """读取单个设置项。"""
    return _settings_cache.get(key, default)


def update_setting(key, value):
    """即时更新缓存中的某个设置项。"""
    _settings_cache[key] = value


def init_settings_cache(current_account: str) -> dict:
    """从磁盘加载设置文件到全局缓存，返回缓存引用。"""
    global _current_account
    _current_account = current_account
    settings, _rebuilt = load_settings_data(current_account)
    _settings_cache.clear()
    _settings_cache.update(settings)
    return _settings_cache


def load_settings_data(current_account: str):
    """读取指定账号的 settings.json；缺失或损坏时自动重建默认文件。

    返回 (settings_dict, rebuilt_flag)。
    """
    settings_path = f"./data/{current_account}/settings.json"
    try:
        with open(settings_path, "r") as f:
            return json.load(f), False
    except (FileNotFoundError, json.JSONDecodeError):
        try:
            os.makedirs(f"./data/{current_account}")
        except FileExistsError:
            pass
        read_settings = DEFAULT_SETTINGS.copy()
        with open(settings_path, "w") as f:
            json.dump(read_settings, f)
        return read_settings, True


# ── 持久化保存 ───────────────────────────────────────────

def _do_file_io_sync():
    """同步写盘：settings.json + tts_config.json。"""
    from .tts_settings import get_tts_cache, save_tts_config_to_disk

    _save_settings_to_disk(_current_account)

    if _settings_cache.get("if_tts") == 1:
        save_tts_config_to_disk(_current_account, get_tts_cache())
    elif _settings_cache.get("if_tts") == 0:
        tts_path = f"./data/{_current_account}/tts_config.json"
        if os.path.exists(tts_path):
            try:
                os.remove(tts_path)
            except Exception:
                pass


def save_settings_now(instance):
    """即时保存：验证账户变更（如需要）+ 同步写盘。

    供「返回」按钮使用，确保离开设置页面前数据已落盘。
    密码和账户名称的修改需要身份验证，取消验证则跳过这两项。
    """
    _handle_pending_account_changes(instance)
    _do_file_io_sync()


def save_on_exit(instance, on_finish=None):
    """退出时调用：处理账户变更认证 + 异步写盘。

    身份验证在主线程完成（可弹出 UI 对话框），
    文件 I/O 放入后台线程，完成后回调 on_finish。
    """
    _handle_pending_account_changes(instance)

    def _run():
        _do_file_io_sync()
        if on_finish:
            on_finish()

    threading.Thread(target=_run, daemon=True).start()


def _save_settings_to_disk(account: str):
    """将缓存写入 settings.json（后台线程调用）。"""
    if not _settings_cache or not account:
        return
    settings_path = f"./data/{account}/settings.json"
    try:
        os.makedirs(f"./data/{account}", exist_ok=True)
        with open(settings_path, "w") as f:
            json.dump(_settings_cache, f)
    except Exception:
        pass


def _handle_pending_account_changes(instance):
    """处理待定的账户名/密码变更（需身份验证）。"""
    new_name_raw = instance.settings_name_value.get() if hasattr(instance, "settings_name_value") else ""
    new_password = instance.settings_password_value.get() if hasattr(instance, "settings_password_value") else ""

    current_name = ""
    try:
        current_name = base64.urlsafe_b64decode(_current_account).decode("utf-8")
    except Exception:
        pass

    name_changed = new_name_raw and new_name_raw != current_name
    password_changed = bool(new_password)

    if not name_changed and not password_changed:
        return

    # 显示身份验证对话框
    verified = _popup_auth_confirm_sync(instance, name_changed, password_changed)
    if not verified:
        return

    if name_changed:
        _do_rename_account(instance, new_name_raw)
    if password_changed:
        _do_change_password(instance, new_password)


def _popup_auth_confirm_sync(instance, name_changed, password_changed):
    """同步阻塞式身份验证弹窗。返回 True 表示验证通过。"""
    result_holder = {"verified": False}

    dialog = instance.gui.create_toplevel(
        title="身份验证",
        size=(350, 160),
        parent=instance.main_window if hasattr(instance, "main_window") else None,
        resizable=(False, False),
        modal=True,
        center=True,
    )

    layout = QtWidgets.QVBoxLayout(dialog)

    msg_parts = []
    if name_changed:
        msg_parts.append("修改账户名称")
    if password_changed:
        msg_parts.append("修改密码")
    layout.addWidget(QtWidgets.QLabel(f"即将{'、'.join(msg_parts)}，请输入当前密码以确认："))

    pwd_var = QtWidgets.QLineEdit()
    pwd_var.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
    layout.addWidget(pwd_var)
    pwd_var.setFocus()

    def on_confirm():
        pwd = pwd_var.text()
        if not pwd:
            instance.gui.warning("密码不能为空", title="提示", parent=dialog)
            return

        if _verify_current_password(instance, pwd):
            result_holder["verified"] = True
            dialog.accept()
        else:
            instance.gui.error("密码错误", title="认证失败", parent=dialog)

    def on_cancel():
        dialog.reject()

    btn_row = QtWidgets.QWidget()
    btn_layout = QtWidgets.QHBoxLayout(btn_row)
    btn_layout.setContentsMargins(0, 0, 0, 0)
    confirm_btn = QtWidgets.QPushButton("确认")
    confirm_btn.clicked.connect(on_confirm)
    cancel_btn = QtWidgets.QPushButton("取消")
    cancel_btn.clicked.connect(on_cancel)
    btn_layout.addStretch(1)
    btn_layout.addWidget(confirm_btn)
    btn_layout.addWidget(cancel_btn)
    layout.addWidget(btn_row)

    def _key_press_event(e):
        if e.key() == QtCore.Qt.Key.Key_Return:
            on_confirm()
        elif e.key() == QtCore.Qt.Key.Key_Escape:
            on_cancel()
        else:
            QtWidgets.QDialog.keyPressEvent(dialog, e)

    dialog.keyPressEvent = _key_press_event
    dialog.exec()  # 阻塞等待

    try:
        dialog.deleteLater()
    except Exception:
        pass

    return result_holder["verified"]


def _verify_current_password(instance, input_pwd):
    """验证当前密码。"""
    from ..auth.account_io import verify_password
    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        stored_password = read_accounts["passwords"].get(_current_account)
        if not stored_password:
            return False

        is_valid, upgraded_hash = verify_password(input_pwd, stored_password)
        if is_valid and upgraded_hash:
            read_accounts["passwords"][_current_account] = upgraded_hash
            try:
                with open("./data/acounts.json", "w") as f:
                    json.dump(read_accounts, f)
            except Exception:
                pass
        return is_valid
    except Exception:
        return False


def _do_rename_account(instance, new_name_raw):
    """执行账户重命名（目录重命名 + acounts.json 更新）。"""
    new_encoded = base64.urlsafe_b64encode(new_name_raw.encode("utf-8")).decode("utf-8")
    global _current_account

    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        for i in range(len(read_accounts["names"])):
            if read_accounts["names"][i] == _current_account:
                read_accounts["names"][i] = new_encoded
        read_accounts["passwords"][new_encoded] = read_accounts["passwords"].pop(_current_account)
        with open("./data/acounts.json", "w") as f:
            json.dump(read_accounts, f)
        os.rename(f"./data/{_current_account}", f"./data/{new_encoded}")
        _current_account = new_encoded
        instance.current_acount = new_encoded
        try:
            instance.current_account_label.setText(
                f"当前登录：{base64.urlsafe_b64decode(instance.current_acount).decode('utf-8')}"
            )
        except Exception:
            pass
        instance.gui.info(message="账户名称修改成功！")
    except FileNotFoundError:
        with open("./data/acounts.json", "w") as f:
            json.dump({"names": [], "passwords": {}}, f)
        instance.current_acount = ""
        instance.if_logged_in = False
        instance.gui.info(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")


def _do_change_password(instance, new_password):
    """执行密码修改。"""
    from ..auth.account_io import hash_password
    if not new_password:
        instance.gui.warning(message="新密码不能为空!")
        return

    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        read_accounts["passwords"][_current_account] = hash_password(new_password)
        with open("./data/acounts.json", "w") as f:
            json.dump(read_accounts, f)
        instance.settings_password_value.set("")
        instance.gui.info(message="密码修改成功!")
    except FileNotFoundError:
        with open("./data/acounts.json", "w") as f:
            json.dump({"names": [], "passwords": {}}, f)
        instance.gui.info(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")


# ── 绑定到实例 ────────────────────────────────────────────

def bind_settings(instance):
    instance.init_settings_cache = lambda: init_settings_cache(instance.current_acount)
    instance.load_settings = lambda: _load_settings(instance)
    instance.change_theme = lambda: _change_theme(instance)
    instance.save_settings_now = lambda: save_settings_now(instance)
    instance.save_settings_on_exit = lambda on_finish=None: save_on_exit(instance, on_finish)


# ── 读取设置到 UI ─────────────────────────────────────────

def _load_settings(self):
    self.log_operation("调用加载设置", "执行 load_settings")

    # 使用缓存（如果已初始化），否则从磁盘加载
    if not _settings_cache:
        init_settings_cache(self.current_acount)

    read_settings = get_settings_cache()

    self.settings_goal_value.set(value=int(read_settings["goal"]) / 60)
    self.settings_stop_dur_value.set(value=read_settings["stop-dur"])
    self.settings_db_value.set(value=read_settings["db-level"])
    try:
        self.settings_name_value.set(base64.urlsafe_b64decode(self.current_acount).decode("utf-8"))
    except Exception:
        self.settings_name_value.set("")
    self.settings_password_value.set("")

    if read_settings["if_tts"] == 0:
        self.enable_or_disable_tts_gui(state=False)
    elif read_settings["if_tts"] == 1:
        self.enable_or_disable_tts_gui(state=True)
        # 从缓存或磁盘加载 TTS 配置填充树
        from .tts_settings import get_tts_cache, init_tts_cache
        tts_config = get_tts_cache()
        if not tts_config:
            tts_config = init_tts_cache(self.current_acount)
        try:
            for key_ in sorted(tts_config.keys(), key=lambda k: int(k) if k.isdigit() else 0):
                vals = tts_config[key_]
                condition = vals.get("condition", "")
                value = vals.get("value", "")
                display = vals.get("display", "")
                text = vals.get("text", "")
                rate = vals.get("rate", "")
                volume = vals.get("volume", "")
                voice = vals.get("voice", "")
                source = vals.get("source", "local")
                trigger_text = display if display else f"{condition} {value}".strip()
                row = self.tts_tree.rowCount()
                self.tts_tree.insertRow(row)
                row_values = [trigger_text, text, rate, volume, voice, source or "local"]
                for c, v in enumerate(row_values):
                    self.tts_tree.setItem(row, c, QtWidgets.QTableWidgetItem(str(v)))
        except Exception:
            self.log_error("加载 TTS 设置失败", "tts_config.json 不可读或格式错误")
            pass

    return read_settings


# ── 主题切换 ──────────────────────────────────────────────

def _change_theme(self):
    self.log_operation("调用主题切换", "执行 change_theme")
    try:
        current_row = getattr(self.customize_listbox, "currentRow", lambda: -1)()
        if current_row < 0:
            self.log_warning("主题切换未执行", "未选择主题")
            self.gui.error(message="请先选择一个样式")
            return

        item = self.customize_listbox.item(current_row)
        if not item:
            return

        get_selected = item.text()
        self.gui.set_theme(get_selected)
        update_setting("theme", get_selected)
    except Exception as e:
        self.log_error("主题切换失败", f"Qt 组件状态异常: {e}")
        self.gui.error(message="切换样式时出错")
