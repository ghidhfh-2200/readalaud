"""
session.py —— 登录、注册、注销、删号、重置数据的会话管理逻辑。
"""
import json
import base64
import os
import shutil
import hashlib
from tkinter import messagebox
import secrets
from .account_io import load_accounts, save_accounts, ensure_user_dir, DEFAULT_SETTINGS


def bind_auth(instance):
    instance.login_and_sign_up = lambda: _login_and_sign_up(instance)
    instance.delete_the_account = lambda: _delete_the_account(instance)
    instance.reset_account_data = lambda: _reset_account_data(instance)
    instance.logout = lambda: _logout(instance)


def _login_and_sign_up(self):
    get_input_acount = self.login_acount_enter.get()
    get_input_password = self.login_password_enter.get()
    if not get_input_acount:
        messagebox.showwarning(message="必须输入用户名!", title="警告")
        return

    try:
        read_json = load_accounts()
    except Exception as e:
        messagebox.showerror(message=f"无法创建数据文件夹: {e}")
        return

    read_names = read_json.get("names", [])
    read_passwords = read_json.get("passwords", {})

    if not read_names:
        _register_new_account(self, get_input_acount, get_input_password, read_json)
    else:
        encode_input_acount = base64.b64encode(get_input_acount.encode("utf-8")).decode("utf-8")
        if encode_input_acount in read_names:
            _try_login(self, encode_input_acount, get_input_password, read_json, read_passwords)
        else:
            _register_new_account(self, get_input_acount, get_input_password, read_json)


def _register_new_account(self, username, password, read_json):
    if not messagebox.askyesno(title="注册新账号？", message="此操作将会注册新账号\n是否继续？"):
        return
    
    encode_acount = base64.b64encode(username.encode("utf-8")).decode("utf-8")
    salt = secrets.token_hex(16)
    hashed_pwd = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    encode_password = f"{salt}${hashed_pwd}"
    
    read_json["names"].append(encode_acount)
    read_json["passwords"][encode_acount] = encode_password
    self.current_acount = encode_acount
    try:
        save_accounts(read_json)
    except FileNotFoundError:
        messagebox.showerror(message="无法写入acounts.json\n请勿移动该文件!")
        return
    try:
        ensure_user_dir(encode_acount)
    except Exception as e:
        print(e)
        messagebox.showerror(message="出错啦!无法创建文件夹！\n可能是因为文件夹已存在或权限问题！")
        return
    messagebox.showinfo(message="账号注册成功，现在你可以进行登录！", title="成功注册新账号！")
    self.log_audit("注册成功", f"注册了账户 {username}")

def _try_login(self, encoded_account, raw_password, read_json, read_passwords):
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
            decode_password = base64.b64decode(stored_password).decode("utf-8")
            if decode_password == raw_password:
                is_valid = True
                is_legacy = True
        except Exception:
            pass

    if not is_valid:
        messagebox.showinfo(message="密码错误！", title="密码错误!")
        return

    # Migrate legacy base64 or unsalted sha256 to salted hash
    if "$" not in stored_password:
        
        salt = secrets.token_hex(16)
        hashed_pwd = hashlib.sha256((salt + raw_password).encode("utf-8")).hexdigest()
        read_json["passwords"][encoded_account] = f"{salt}${hashed_pwd}"
        try:
            save_accounts(read_json)
        except Exception as e:
            print(f"Failed to migrate password: {e}")

    self.current_acount = encoded_account
    self.if_logged_in = True

    user_data_path = ensure_user_dir(encoded_account)

    try:
        with open(f"{user_data_path}/settings.json", "r") as f:
            read_settings = json.load(f)
    except FileNotFoundError:
        read_settings = DEFAULT_SETTINGS.copy()
        with open(f"{user_data_path}/settings.json", "w") as f:
            json.dump(read_settings, f)

    self.welcome_page(destroy_window=[self.login_frame, "login"])
    self.log_audit("登录成功", "账户成功登录系统")
    try:
        import ttkbootstrap as ttkbs
        ttkbs.Style().theme_use(read_settings["theme"])
    except Exception:
        pass


def _delete_the_account(self):
    try:
        if not messagebox.askyesno(message="确定要注销账号吗？\n你的数据会全部丢失!"):
            return
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
        self.current_account_label.config(text="当前登录：(未登录)")
        self.if_logged_in = False
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])
        messagebox.showinfo(message="账户已成功注销!")
        self.log_audit("删除账户", "成功注销并删除了当前账户及其数据")
    except OSError:
        messagebox.showerror(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")
    except json.JSONDecodeError:
        messagebox.showerror(message="解析账户配置文件时出错！请不要随意修改data文件夹的内容！")
    except FileNotFoundError:
        messagebox.showerror(message="无法找到账户配置文件!请不要随意移动data文件夹中的文件!")


def _reset_account_data(self):
    try:
        if not messagebox.askyesno(message="确定要重置所有数据吗？\n你的密码会保持不变\n其他数据会全部丢失!"):
            return
        if os.path.exists(f"./data/{self.current_acount}"):
            shutil.rmtree(f"./data/{self.current_acount}")
        if os.path.exists(f"./details/{self.current_acount}"):
            shutil.rmtree(f"./details/{self.current_acount}")
        ensure_user_dir(self.current_acount)
        self.current_acount = ""
        self.current_account_label.config(text="当前登录：(未登录)")
        self.if_logged_in = False
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])
        messagebox.showinfo(message="数据已重置，密码保持不变\n请重新登录！")
        self.log_audit("重置数据", "重置了当前账户的所有数据保留密码")
    except OSError:
        messagebox.showerror(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")


def _logout(self):
    self.current_acount = ""
    self.if_logged_in = False
    try:
        self.current_account_label.config(text="当前登录：(未登录)")
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])
    except Exception:
        pass
    messagebox.showinfo(message="已成功退出登录！")
    self.log_audit("退出登录", "账户正常退出系统")
