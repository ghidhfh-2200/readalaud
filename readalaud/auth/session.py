"""
session.py —— 登录、注册、注销、删号、重置数据的会话管理逻辑。
"""
import json
import base64
import os
import shutil
import hashlib
import secrets
import time
from .account_io import load_accounts, save_accounts, ensure_user_dir, DEFAULT_SETTINGS


LOGIN_LOCK_DURATIONS = [30, 60, 300, 600, 3600, 10800, 86400]


def _set_login_ui_status(self, message, level="info"):
    try:
        self.set_login_status(message, level)
    except Exception:
        pass


def _start_login_lock_ui_countdown(self, encoded_account, locked_until_ts):
    try:
        self.start_login_lock_countdown(encoded_account, locked_until_ts)
    except Exception:
        pass


def _stop_login_lock_ui_countdown(self):
    try:
        self.stop_login_lock_countdown()
    except Exception:
        pass


def _format_duration(seconds):
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"{seconds}秒"
    if seconds < 3600:
        mins, sec = divmod(seconds, 60)
        return f"{mins}分{sec}秒" if sec else f"{mins}分钟"
    if seconds < 86400:
        hours, rem = divmod(seconds, 3600)
        mins = rem // 60
        return f"{hours}小时{mins}分钟" if mins else f"{hours}小时"
    days, rem = divmod(seconds, 86400)
    hours = rem // 3600
    return f"{days}天{hours}小时" if hours else f"{days}天"


def _get_login_guard(read_json):
    guard = read_json.setdefault("login_guard", {})
    if not isinstance(guard, dict):
        read_json["login_guard"] = {}
        return read_json["login_guard"]
    return guard


def _get_account_guard_state(read_json, encoded_account):
    guard = _get_login_guard(read_json)
    state = guard.get(encoded_account, {})
    if not isinstance(state, dict):
        state = {}
    fail_count = int(state.get("fail_count", 0) or 0)
    lock_level = int(state.get("lock_level", 0) or 0)
    locked_until = float(state.get("locked_until", 0) or 0)
    return {
        "fail_count": max(0, fail_count),
        "lock_level": max(0, lock_level),
        "locked_until": max(0.0, locked_until),
    }


def _save_account_guard_state(read_json, encoded_account, state):
    guard = _get_login_guard(read_json)
    guard[encoded_account] = {
        "fail_count": int(max(0, state.get("fail_count", 0))),
        "lock_level": int(max(0, state.get("lock_level", 0))),
        "locked_until": float(max(0.0, state.get("locked_until", 0))),
    }


def _is_account_locked(read_json, encoded_account):
    state = _get_account_guard_state(read_json, encoded_account)
    now_ts = time.time()
    if state["locked_until"] > now_ts:
        return True, int(state["locked_until"] - now_ts), state
    return False, 0, state


def _record_login_failure(self, encoded_account, read_json):
    state = _get_account_guard_state(read_json, encoded_account)
    state["fail_count"] += 1
    should_lock = (state["fail_count"] % 5 == 0)
    remain_to_lock = 5 - (state["fail_count"] % 5)

    lock_seconds = 0
    if should_lock:
        if state["fail_count"] == 5:
            state["lock_level"] = 0
        else:
            state["lock_level"] = min(state["lock_level"] + 1, len(LOGIN_LOCK_DURATIONS) - 1)
        lock_seconds = LOGIN_LOCK_DURATIONS[state["lock_level"]]
        state["locked_until"] = time.time() + lock_seconds

    _save_account_guard_state(read_json, encoded_account, state)
    try:
        save_accounts(read_json)
    except Exception as e:
        self.log_error("登录限制状态保存失败", str(e))

    return state, should_lock, lock_seconds, remain_to_lock


def _clear_login_failures(self, encoded_account, read_json):
    state = {"fail_count": 0, "lock_level": 0, "locked_until": 0}
    _save_account_guard_state(read_json, encoded_account, state)
    try:
        save_accounts(read_json)
    except Exception as e:
        self.log_error("重置登录限制状态失败", str(e))


def bind_auth(instance):
    instance.login_and_sign_up = lambda: _login_and_sign_up(instance)
    instance.delete_the_account = lambda: _delete_the_account(instance)
    instance.reset_account_data = lambda: _reset_account_data(instance)
    instance.logout = lambda: _logout(instance)


def _login_and_sign_up(self):
    self.log_operation("调用登录入口", "执行 login_and_sign_up")
    get_input_acount = self.login_acount_enter.get()
    get_input_password = self.login_password_enter.get()
    if not get_input_acount:
        self.log_warning("登录未执行", "用户名为空")
        _set_login_ui_status(self, "必须输入用户名", "warning")
        return

    try:
        read_json = load_accounts()
    except Exception as e:
        self.log_error("读取账户失败", str(e))
        _set_login_ui_status(self, f"读取账户失败：{e}", "error")
        return

    read_names = read_json.get("names", [])
    read_passwords = read_json.get("passwords", {})

    if not read_names:
        _register_new_account(self, get_input_acount, get_input_password, read_json)
    else:
        encode_input_acount = base64.urlsafe_b64encode(get_input_acount.encode("utf-8")).decode("utf-8")
        if encode_input_acount in read_names:
            _try_login(self, encode_input_acount, get_input_password, read_json, read_passwords)
        else:
            _register_new_account(self, get_input_acount, get_input_password, read_json)
    self.login_acount_enter.set("")
    self.login_password_enter.set("")

def _register_new_account(self, username, password, read_json):
    self.log_operation("调用注册流程", f"准备注册账户 {username}")
    if not self.gui.ask_yes_no(title="注册新账号？", message="此操作将会注册新账号\n是否继续？"):
        self.log_warning("取消注册", f"用户取消注册账户 {username}")
        return
    
    encode_acount = base64.urlsafe_b64encode(username.encode("utf-8")).decode("utf-8")
    salt = secrets.token_hex(16)
    hashed_pwd = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    encode_password = f"{salt}${hashed_pwd}"
    
    read_json["names"].append(encode_acount)
    read_json["passwords"][encode_acount] = encode_password
    self.current_acount = encode_acount
    try:
        save_accounts(read_json)
    except FileNotFoundError:
        self.log_error("注册失败", "acounts.json 不可写")
        self.gui.error(message="无法写入acounts.json\n请勿移动该文件!")
        return
    try:
        ensure_user_dir(encode_acount)
    except Exception as e:
        self.log_error("注册失败", f"无法创建用户目录: {e}")
        print(e)
        self.gui.error(message="出错啦!无法创建文件夹！\n可能是因为文件夹已存在或权限问题！")
        return
    _set_login_ui_status(self, "账号注册成功，正在登录...", "success")
    _try_login(self, encode_acount, password, read_json, read_json["passwords"])
    self.log_success("注册成功", f"注册了账户 {username}")

def _try_login(self, encoded_account, raw_password, read_json, read_passwords):
    self.log_operation("调用登录校验", f"账户: {encoded_account}")
    is_locked, remain_seconds, lock_state = _is_account_locked(read_json, encoded_account)
    if is_locked:
        self.log_warning("登录受限", f"账户处于锁定期，剩余 {_format_duration(remain_seconds)}")
        _set_login_ui_status(self, f"登录失败次数过多，请在 {_format_duration(remain_seconds)} 后重试", "warning")
        _start_login_lock_ui_countdown(self, encoded_account, lock_state.get("locked_until", 0))
        return

    if lock_state.get("locked_until", 0) > 0 and remain_seconds <= 0:
        lock_state["locked_until"] = 0
        _save_account_guard_state(read_json, encoded_account, lock_state)
        try:
            save_accounts(read_json)
        except Exception:
            pass
        _stop_login_lock_ui_countdown(self)

    stored_password = read_passwords[encoded_account]

    if "$" in stored_password:
        salt, expected_hash = stored_password.split("$", 1)
        input_password_hash = hashlib.sha256((salt + raw_password).encode("utf-8")).hexdigest()
        is_valid = (expected_hash == input_password_hash)
    else:
        # Legacy passwords
        input_password_hash = hashlib.sha256(raw_password.encode("utf-8")).hexdigest()
        is_valid = (stored_password == input_password_hash)

    is_legacy = False
    if not is_valid and "$" not in stored_password:
        try:
            decode_password = base64.urlsafe_b64decode(stored_password).decode("utf-8")
            if decode_password == raw_password:
                is_valid = True
                is_legacy = True
        except Exception:
            pass

    if not is_valid:
        self.log_warning("登录失败", "密码错误")
        state, just_locked, lock_seconds, remain_to_lock = _record_login_failure(self, encoded_account, read_json)
        if just_locked:
            self.log_warning("登录锁定触发", f"失败 {state['fail_count']} 次，锁定 {_format_duration(lock_seconds)}")
            _set_login_ui_status(self, f"密码错误，已锁定 {_format_duration(lock_seconds)}", "warning")
            _start_login_lock_ui_countdown(self, encoded_account, state.get("locked_until", 0))
        else:
            _set_login_ui_status(self, f"密码错误，再失败 {remain_to_lock} 次将触发下一档锁定", "error")
        return

    _clear_login_failures(self, encoded_account, read_json)
    _stop_login_lock_ui_countdown(self)
    _set_login_ui_status(self, "登录成功", "success")

    # Migrate legacy base64 or unsalted sha256 to salted hash
    if "$" not in stored_password:
        
        salt = secrets.token_hex(16)
        hashed_pwd = hashlib.sha256((salt + raw_password).encode("utf-8")).hexdigest()
        read_json["passwords"][encoded_account] = f"{salt}${hashed_pwd}"
        try:
            save_accounts(read_json)
        except Exception as e:
            self.log_error("密码迁移失败", str(e))
            print(f"Failed to migrate password: {e}")

    self.current_acount = encoded_account
    self.if_logged_in = True

    user_data_path = ensure_user_dir(encoded_account)

    try:
        with open(f"{user_data_path}/settings.json", "r") as f:
            read_settings = json.load(f)
    except FileNotFoundError:
        self.log_warning("设置文件缺失", "登录时自动重建 settings.json")
        read_settings = DEFAULT_SETTINGS.copy()
        with open(f"{user_data_path}/settings.json", "w") as f:
            json.dump(read_settings, f)

    self.welcome_page(destroy_window=[self.login_frame, "login"])
    self.log_success("登录成功", "账户成功登录系统")
    # 清除登录框内容
    try:
        self.login_acount_enter.delete(0, 'end')
        self.login_password_enter.delete(0, 'end')
    except Exception:
        pass
    try:
        self.gui.set_theme(read_settings["theme"])
    except Exception:
        pass


def _delete_the_account(self):
    self.log_operation("调用删除账户", "执行 delete_the_account")
    try:
        if not self.gui.ask_yes_no(message="确定要注销账号吗？\n你的数据会全部丢失!"):
            self.log_warning("取消删除账户", "用户取消删除账户")
            return

        # 弹出密码确认对话框
        try:
            from PySide6 import QtWidgets
            parent = getattr(self, "main_window", None)
            pwd, ok = QtWidgets.QInputDialog.getText(parent, "密码确认", "请输入当前密码以确认注销：", QtWidgets.QLineEdit.EchoMode.Password)
        except Exception:
            pwd, ok = None, False

        if not ok or not pwd:
            self.gui.info(message="已取消：未输入密码或已取消操作")
            return

        # 验证密码是否正确
        try:
            accounts = load_accounts()
            stored_password = accounts.get("passwords", {}).get(self.current_acount)
            if not stored_password:
                self.gui.error(message="无法验证密码（账户数据缺失）")
                return
            is_valid = False
            if "$" in stored_password:
                salt, expected_hash = stored_password.split("$", 1)
                input_hash = hashlib.sha256((salt + pwd).encode("utf-8")).hexdigest()
                is_valid = (input_hash == expected_hash)
            else:
                # legacy
                input_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
                if stored_password == input_hash:
                    is_valid = True
                else:
                    try:
                        if base64.urlsafe_b64decode(stored_password).decode("utf-8") == pwd:
                            is_valid = True
                    except Exception:
                        pass
            if not is_valid:
                self.gui.error(message="密码错误，操作已取消")
                return
        except Exception as e:
            self.log_error("删除账户前密码验证失败", str(e))
            self.gui.error(message="验证密码时发生错误，已取消操作")
            return
        try:
            self._stop_sidebar_today_status_monitor()
        except Exception:
            pass
        read_accounts = load_accounts()
        read_accounts["names"].remove(self.current_acount)
        read_accounts["passwords"].pop(self.current_acount)
        save_accounts(read_accounts)
        try:
            shutil.rmtree(f"./data/{self.current_acount}")
            shutil.rmtree(f"./details/{self.current_acount}")
        except FileNotFoundError:
            pass
        self.current_acount = ""
        try:
            self.current_account_label.setText("当前登录：(未登录)")
        except Exception:
            try:
                self.current_account_label.config(text="当前登录：(未登录)")
            except Exception:
                pass
        self.if_logged_in = False
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])
        self.gui.info(message="账户已成功注销!")
        self.log_success("删除账户", "成功注销并删除了当前账户及其数据")
    except OSError:
        self.log_error("删除账户失败", "删除文件时发生 OSError")
        self.gui.error(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")
    except json.JSONDecodeError:
        self.log_error("删除账户失败", "账户配置文件 JSON 解析失败")
        self.gui.error(message="解析账户配置文件时出错！请不要随意修改data文件夹的内容！")
    except FileNotFoundError:
        self.log_error("删除账户失败", "账户配置文件缺失")
        self.gui.error(message="无法找到账户配置文件!请不要随意移动data文件夹中的文件!")


def _reset_account_data(self):
    self.log_operation("调用重置账户数据", "执行 reset_account_data")
    try:
        if not self.gui.ask_yes_no(message="确定要重置所有数据吗？\n你的密码会保持不变\n其他数据会全部丢失!"):
            self.log_warning("取消重置账户数据", "用户取消重置")
            return

        # 弹出密码确认
        try:
            from PySide6 import QtWidgets
            parent = getattr(self, "main_window", None)
            pwd, ok = QtWidgets.QInputDialog.getText(parent, "密码确认", "请输入当前密码以确认重置：", QtWidgets.QLineEdit.EchoMode.Password)
        except Exception:
            pwd, ok = None, False

        if not ok or not pwd:
            self.gui.info(message="已取消：未输入密码或已取消操作")
            return

        # 验证密码
        try:
            accounts = load_accounts()
            stored_password = accounts.get("passwords", {}).get(self.current_acount)
            if not stored_password:
                self.gui.error(message="无法验证密码（账户数据缺失）")
                return
            is_valid = False
            if "$" in stored_password:
                salt, expected_hash = stored_password.split("$", 1)
                input_hash = hashlib.sha256((salt + pwd).encode("utf-8")).hexdigest()
                is_valid = (input_hash == expected_hash)
            else:
                input_hash = hashlib.sha256(pwd.encode("utf-8")).hexdigest()
                if stored_password == input_hash:
                    is_valid = True
                else:
                    try:
                        if base64.urlsafe_b64decode(stored_password).decode("utf-8") == pwd:
                            is_valid = True
                    except Exception:
                        pass
            if not is_valid:
                self.gui.error(message="密码错误，操作已取消")
                return
        except Exception as e:
            self.log_error("重置数据前密码验证失败", str(e))
            self.gui.error(message="验证密码时发生错误，已取消操作")
            return
        try:
            self._stop_sidebar_today_status_monitor()
        except Exception:
            pass
        if os.path.exists(f"./data/{self.current_acount}"):
            shutil.rmtree(f"./data/{self.current_acount}")
        if os.path.exists(f"./details/{self.current_acount}"):
            shutil.rmtree(f"./details/{self.current_acount}")
        ensure_user_dir(self.current_acount)
        self.current_acount = ""
        try:
            self.current_account_label.setText("当前登录：(未登录)")
        except Exception:
            try:
                self.current_account_label.config(text="当前登录：(未登录)")
            except Exception:
                pass
        self.if_logged_in = False
        try:
            self.welcome_page(destroy_window=[self.settings_frame, "settings"])
        except Exception:
            pass
        self.gui.info(message="数据已重置，密码保持不变\n请重新登录！")
        self.log_success("重置数据", "重置了当前账户的所有数据保留密码")
    except OSError:
        self.log_error("重置数据失败", "删除目录时发生 OSError")
        self.gui.error(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")


def _logout(self):
    self.log_operation("调用退出登录", "执行 logout")
    try:
        self._stop_sidebar_today_status_monitor()
    except Exception:
        pass
    self.current_acount = ""
    self.if_logged_in = False
    try:
        try:
            # Qt QLabel
            self.current_account_label.setText("当前登录：(未登录)")
        except Exception:
            try:
                # tkinter fallback
                self.current_account_label.config(text="当前登录：(未登录)")
            except Exception:
                pass
        try:
            self.welcome_page(destroy_window=[self.settings_frame, "settings"])
        except Exception:
            pass
    except Exception:
        pass
    self.gui.info(message="已成功退出登录！")
    self.log_success("退出登录", "账户正常退出系统")
