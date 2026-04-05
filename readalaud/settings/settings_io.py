"""
settings_io.py —— 读取/保存用户设置（goal、stop-dur、db-level、账号、密码、主题）。
"""
import hashlib
import json
import base64
import os
import secrets
import tkinter as tk

from .tts_settings import save_tts_settings

DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}


def bind_settings(instance):
    instance.save_settings_except_tts = lambda option: _save_settings_except_tts(instance, option)
    instance.load_settings = lambda: _load_settings(instance)
    instance.change_theme = lambda: _change_theme(instance)
    instance.save_tts_settings = lambda args: save_tts_settings(instance, args)


# ── 读取设置 ──────────────────────────────────────────────

def _load_settings(self):
    current_account = self.current_acount
    try:
        with open(f"./data/{current_account}/settings.json", "r") as f:
            read_settings = json.load(f)
    except FileNotFoundError:
        try:
            os.makedirs(f"./data/{current_account}")
        except FileExistsError:
            pass
        read_settings = DEFAULT_SETTINGS.copy()
        with open(f"./data/{self.current_acount}/settings.json", "w") as f:
            json.dump(read_settings, f)
        self.gui.info(message="无法找到您的设置文件，已将设置全部重置!")

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
        try:
            with open(f"./data/{self.current_acount}/tts_config.json", "r") as f:
                read_tts_settings = json.load(f)
            for key_, vals in read_tts_settings.items():
                condition = value = text = rate = volume = voice = source = ""
                for key, values in read_tts_settings[key_].items():
                    if key == "condition":   condition = values
                    elif key == "value":     value = values
                    elif key == "text":      text = values
                    elif key == "rate":      rate = values
                    elif key == "volume":    volume = values
                    elif key == "voice":     voice = values
                    elif key == "source":    source = values
                self.tts_tree.insert("", tk.END, values=(f"{condition} {value}", text, rate, volume, voice, source))
        except Exception:
            pass


# ── 保存各项设置 ──────────────────────────────────────────

def _save_settings_except_tts(self, option):
    # 对于敏感操作（修改账号名、修改密码），先弹出确认框验证身份
    if option in ["account", "password"]:
        _popup_auth_confirm(self, option)
        return

    handlers = {
        "goal":      _save_goal,
        "stop_dur":  _save_stop_dur,
        "db_level":  _save_db_level,
    }
    handler = handlers.get(option)
    if handler:
        handler(self)


def _popup_auth_confirm(self, option):
    """弹出验证窗口"""
    dialog = self.gui.create_toplevel(
        title="身份验证",
        size=(300, 150),
        parent=self.main_window,
        resizable=(False, False),
        modal=True,
        center=True,
    )

    tk.Label(dialog, text="请输入当前账号密码以继续：", font=("微软雅黑", 10)).pack(pady=10)
    pwd_var = tk.StringVar()
    entry = tk.Entry(dialog, textvariable=pwd_var, show="*", width=25)
    entry.pack(pady=5)
    entry.focus_set()

    def on_confirm(event=None):
        pwd = pwd_var.get()
        if not pwd:
            self.gui.warning("密码不能为空", title="提示", parent=dialog)
            return
        
        # 验证密码
        if _verify_current_password(self, pwd):
            dialog.destroy()
            if option == "account":
                _save_account_name(self)
            elif option == "password":
                _save_password(self)
        else:
            self.gui.error("密码错误", title="认证失败", parent=dialog)
            self.log_audit("敏感操作认证失败", f"尝试进行 {option} 修改时密码验证失败")

    btn = tk.Button(dialog, text="验证", command=on_confirm, width=10)
    btn.pack(pady=10)
    dialog.bind("<Return>", on_confirm)


def _verify_current_password(self, input_pwd):
    """内部使用的密码验证函数"""
    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        stored_password = read_accounts["passwords"].get(self.current_acount)
        if not stored_password:
            return False

        if "$" in stored_password:
            salt, expected_hash = stored_password.split("$", 1)
            return hashlib.sha256((salt + input_pwd).encode("utf-8")).hexdigest() == expected_hash
        else:
            if stored_password == hashlib.sha256(input_pwd.encode("utf-8")).hexdigest():
                return True
            try:
                if base64.urlsafe_b64decode(stored_password).decode("utf-8") == input_pwd:
                    return True
            except Exception:
                pass
        return False
    except Exception:
        return False


def _save_account_name(self):
    new_name = base64.urlsafe_b64encode(self.settings_name_value.get().encode("utf-8")).decode("utf-8")
    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        for i in range(len(read_accounts["names"])):
            if read_accounts["names"][i] == self.current_acount:
                read_accounts["names"][i] = new_name
        read_accounts["passwords"][new_name] = read_accounts["passwords"].pop(self.current_acount)
        with open("./data/acounts.json", "w") as f:
            json.dump(read_accounts, f)
        os.rename(f"./data/{self.current_acount}", f"./data/{new_name}")
        self.current_acount = new_name
        self.current_account_label.config(
            text=f"当前登录：{base64.urlsafe_b64decode(self.current_acount).decode('utf-8')}"
        )
        self.gui.info(message="账户名称修改成功！")
        self.log_operation("修改账户名", "账户名称已被更改")
    except FileNotFoundError:
        with open("./data/acounts.json", "w") as f:
            json.dump({"names": [], "passwords": {}}, f)
        self.current_acount = ""
        self.if_logged_in = False
        self.welcome_page(destroy_window=self.settings_frame)
        self.gui.info(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")


def _save_password(self):
    new_password = self.settings_password_value.get()
    if not new_password:
        self.gui.warning(message="新密码不能为空!")
        return
    
    try:
        with open("./data/acounts.json", "r") as f:
            read_accounts = json.load(f)
        
        # 加盐保存新密码
        new_salt = secrets.token_hex(16)
        new_hashed_pwd = hashlib.sha256((new_salt + new_password).encode("utf-8")).hexdigest()
        read_accounts["passwords"][self.current_acount] = f"{new_salt}${new_hashed_pwd}"
        
        with open("./data/acounts.json", "w") as f:
            json.dump(read_accounts, f)
        
        self.settings_password_value.set("")
        self.gui.info(message="密码修改成功!")
        self.log_audit("敏感操作成功", "通过验证后成功修改了账户密码")
    except FileNotFoundError:
        with open("./data/acounts.json", "w") as f:
            json.dump({"names": [], "passwords": {}}, f)
        self.gui.info(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")
    except json.JSONDecodeError:
        self.gui.info(message="账户文件解析失败！")


def _save_goal(self):
    new_goal = self.settings_goal_value.get() * 60
    _write_single_setting(self, "goal", new_goal, "目标时间修改成功！")


def _save_stop_dur(self):
    new_stop_dur = self.settings_stop_dur_value.get()
    _write_single_setting(self, "stop-dur", new_stop_dur, "停顿容忍间隔修改成功！")


def _save_db_level(self):
    new_db_level = self.settings_db_value.get()
    if new_db_level < 0:
        self.gui.error(message="分贝值不能小于0！\n建议阈值为30dB左右")
        return
    _write_single_setting(self, "db-level", new_db_level, "声音阈值修改成功！")


def _write_single_setting(self, key, value, success_msg):
    settings_path = f"./data/{self.current_acount}/settings.json"
    try:
        with open(settings_path, "r") as f:
            read_settings = json.load(f)
        read_settings[key] = value
        with open(settings_path, "w") as f:
            json.dump(read_settings, f)
        self.gui.info(message=success_msg)
        self.log_operation("修改设置", f"修改了设置项: {key} 为 {value}")
    except FileNotFoundError:
        with open(settings_path, "w") as f:
            json.dump(DEFAULT_SETTINGS.copy(), f)
        self.gui.info(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
    except json.JSONDecodeError:
        self.gui.error(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")


# ── 主题切换 ──────────────────────────────────────────────

def _change_theme(self):
    try:
        selection = self.customize_listbox.curselection()
        if not selection:
            self.gui.error(message="请先选择一个样式")
            return

        get_selected = self.customize_listbox.get(selection[0])
        self.gui.set_theme(get_selected)
        settings_path = f"./data/{self.current_acount}/settings.json"
        with open(settings_path, "r") as f:
            read_settings = json.load(f)
        read_settings["theme"] = get_selected
        with open(settings_path, "w") as f:
            json.dump(read_settings, f)
    except tk.TclError:
        self.gui.error(message="请先选择一个样式")
