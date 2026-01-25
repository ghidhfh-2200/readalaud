import json
import base64
import os
import shutil
from tkinter import messagebox


def bind_auth(instance):
    instance.login_and_sign_up = lambda: _login_and_sign_up(instance)
    instance.delete_the_account = lambda: _delete_the_account(instance)
    instance.reset_account_data = lambda: _reset_account_data(instance)
    instance.logout = lambda: _logout(instance)


def _login_and_sign_up(self):
    get_input_acount = self.login_acount_enter.get()
    get_input_password = self.login_password_enter.get()
    if get_input_acount == "" or get_input_acount == None:
        messagebox.showwarning(message="必须输入用户名!", title="警告")
        return
    with open("./data/acounts.json", "r") as f:
        read_json = json.load(f)
        read_names = read_json['names']
        read_passwords = read_json['passwords']
    if read_names == []:
        if_continue = messagebox.askyesno(title="注册新账号？", message="此操作将会注册新账号\n是否继续？")
        if if_continue == True:
            encode_acount = base64.b64encode(get_input_acount.encode("utf-8")).decode("utf-8")
            encode_password = base64.b64encode(get_input_password.encode("utf-8")).decode("utf-8")
            read_json['names'].append(encode_acount)
            read_json['passwords'][encode_acount] = ""
            read_json['passwords'][encode_acount] = encode_password
            self.current_acount = encode_acount
            try:
                with open("./data/acounts.json", "w") as f:
                    json.dump(read_json, f)
            except FileNotFoundError:
                messagebox.showerror(message="无法写入acounts.json\n请勿移动该文件!")
                return
            try:
                os.makedirs(f"./data/{self.current_acount}")
                with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                    write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts": 0}
                    json.dump(write_data, f)
            except Exception as e:
                print(e)
                messagebox.showerror(message="出错啦!无法创建文件夹！\n可能是因为文件夹已存在或权限问题！")
                return
            messagebox.showinfo(message="账号注册成功，现在你可以进行登录！", title="成功注册新账号！")
        else:pass
    else:
        encode_input_acount = base64.b64encode(get_input_acount.encode("utf-8")).decode("utf-8")
        if encode_input_acount in read_names:
            find_passwod = read_passwords[encode_input_acount]
            decode_password = base64.b64decode(find_passwod).decode("utf-8")
            if decode_password == get_input_password:
                self.current_acount= encode_input_acount
                self.if_logged_in = True
                with open(f"./data/{self.current_acount}/settings.json", "r") as f:
                    read_settings = json.load(f)
                self.welcome_page(destroy_window=[self.login_frame, "login"])
                try:
                    import ttkbootstrap as ttkbs
                    ttkbs.Style().theme_use(read_settings['theme'])
                except Exception:
                    pass
            else:
                messagebox.showinfo(message="密码错误！",title="密码错误!")
        else:
            if_continue = messagebox.askyesno(title="注册新账号？", message="此操作将会注册新账号\n是否继续？")
            if if_continue == True:
                encode_acount = base64.b64encode(get_input_acount.encode("utf-8")).decode("utf-8")
                encode_password = base64.b64encode(get_input_password.encode("utf-8")).decode("utf-8")
                read_json['names'].append(encode_acount)
                read_json['passwords'][encode_acount] = ""
                read_json['passwords'][encode_acount] = encode_password
                self.current_acount = encode_acount
                try:
                    with open("./data/acounts.json", "w") as f:
                        json.dump(read_json, f)
                except FileNotFoundError:
                    messagebox.showerror(message="无法写入acounts.json\n请勿移动该文件!")
                    return
                try:
                    print(self.current_acount)
                    os.makedirs(f"./data/{self.current_acount}")
                    with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                        write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                        json.dump(write_data, f)
                except Exception as e:
                    messagebox.showerror(message="出错啦!无法创建文件夹！\n可能是因为文件夹已存在或权限问题！")
                    return
                messagebox.showinfo(message="账号注册成功，现在你可以进行登录！", title="成功注册新账号！")
            else:pass


def _delete_the_account(self):
    try:
        if_continue = messagebox.askyesno(message="确定要注销账号吗？\n你的数据会全部丢失!")
        if if_continue == True:
            with open("./data/acounts.json", "r") as f:
                read_accounts = json.load(f)
            read_accounts['names'].remove(self.current_acount)
            read_accounts['passwords'].pop(self.current_acount)
            with open("./data/acounts.json", "w") as f:
                json.dump(read_accounts, f)
            shutil.rmtree(f"./data/{self.current_acount}")
            self.current_acount = ""
            self.current_account_label.config(text=f"当前登录：(未登录)")
            self.if_logged_in = False
            self.welcome_page(destroy_window=[self.settings_frame, "settings"])
            messagebox.showinfo(message="账户已成功注销!")
    except OSError:
        messagebox.showerror(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")
    except json.decoder.JSONDecodeError:
        messagebox.showerror(message="解析账户配置文件时出错！请不要随意修改data文件夹的内容！")
    except FileNotFoundError:
        messagebox.showerror(message="无法找到账户配置文件!请不要随意移动data文件夹中的文件!")


def _reset_account_data(self):
    try:
        if_continue = messagebox.askyesno(message="确定要重置所有数据吗？\n你的密码会保持不变\n其他数据会全部丢失!")
        if if_continue == True:
            shutil.rmtree(f"./data/{self.current_acount}")
            os.makedirs(f"./data/{self.current_acount}")
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts": 0}
                json.dump(write_data, f)
            self.current_acount = ""
            self.current_account_label.config(text=f"当前登录：(未登录)")
            self.if_logged_in = False
            self.welcome_page(destroy_window=[self.settings_frame, "settings"])
            messagebox.showinfo(message="数据已重置，密码保持不变\n请重新登录！")
    except OSError:
        messagebox.showerror(message="删除文件时出错，可能此文件已经删除,或者权限不足导致无法删除！")


def _logout(self):
    self.current_acount = ""
    self.if_logged_in = False
    try:
        self.current_account_label.config(text=f"当前登录：(未登录)")
        self.welcome_page(destroy_window=[self.settings_frame, "settings"])
    except Exception:
        pass
    messagebox.showinfo(message="已成功退出登录！")

def export_current_account(self):
    return self.current_acount 
