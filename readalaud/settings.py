import json
import base64
import os
import tkinter as tk
from tkinter import messagebox
import ttkbootstrap as ttkbs


def bind_settings(instance):
    instance.save_settings_except_tts = lambda option: _save_settings_except_tts(instance, option)
    instance.load_settings = lambda: _load_settings(instance)
    instance.change_theme = lambda: _change_theme(instance)


def _save_settings_except_tts(self, option):
    if option == "account":
        new_name = self.settings_name_value.get()
        new_name = base64.b64encode(new_name.encode("utf-8")).decode("utf-8")
        try:
            with open("./data/acounts.json", "r") as f:
                read_accounts = json.load(f)
            for i in range(len(read_accounts['names'])):
                if read_accounts['names'][i] == self.current_acount:
                    read_accounts['names'][i] = new_name
            read_accounts['passwords'][new_name] = read_accounts['passwords'].pop(self.current_acount)
            with open("./data/acounts.json", "w") as f:
                json.dump(read_accounts,f)
                os.rename(f"./data/{self.current_acount}", f"./data/{new_name}")
            self.current_acount = new_name
            self.current_account_label.config(text=f"当前登录：{base64.b64decode(self.current_acount).decode('utf-8')}")
            messagebox.showinfo(message="账户名称修改成功！")
        except FileNotFoundError:
            with open("./data/acounts.json", "w") as f:
                write_data = {"names": [], "passwords": {}}
                json.dump(write_data, f)
            self.current_acount = ""
            self.if_logged_in = False
            self.welcome_page(destroy_window=self.settings_frame)
            messagebox.showinfo(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")
    elif option == "password":
        new_password = self.settings_password_value.get()
        new_password = base64.b64encode(new_password.encode("utf-8")).decode("utf-8")
        try:
            with open("./data/acounts.json", "r") as f:
                read_accounts = json.load(f)
            read_accounts['passwords'][self.current_acount] = new_password
            with open("./data/acounts.json", "w") as f:
                json.dump(read_accounts,f)
            messagebox.showinfo(message="密码修改成功!")
        except FileNotFoundError:
            with open("./data/acounts.json", "w") as f:
                write_data = {"names": [], "passwords": {}}
            messagebox.showinfo(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")
        except json.decoder.JSONDecodeError:
            messagebox.showinfo(message="账户文件解析失败！")
    elif option == "goal":
        new_goal = self.settings_goal_value.get() * 60
        try:
            with open(f"./data/{self.current_acount}/settings.json", "r") as f:
                read_settings = json.load(f)
                read_settings['goal'] = new_goal
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                json.dump(read_settings, f)
            messagebox.showinfo(message="目标时间修改成功！")
        except FileNotFoundError:
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                json.dump(write_data, f)
            messagebox.showinfo(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
        except json.decoder.JSONDecodeError:
            messagebox.showerror(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")
    elif option == "stop_dur":
        new_stop_dur = self.settings_stop_dur_value.get()
        try:
            with open(f"./data/{self.current_acount}/settings.json", "r") as f:
                read_settings = json.load(f)
                read_settings['stop-dur'] = new_stop_dur
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                json.dump(read_settings, f)
            messagebox.showinfo(message="停顿容忍间隔修改成功！")
        except FileNotFoundError:
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                json.dump(write_data, f)
            messagebox.showinfo(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
        except json.decoder.JSONDecodeError:
            messagebox.showerror(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")
    elif option == "db_level":
        new_db_level = self.settings_db_value.get()
        if new_db_level < 0:
            messagebox.showerror(message="分贝值不能小于0！\n建议阈值为30dB左右")
            return
        try:
            with open(f"./data/{self.current_acount}/settings.json", "r") as f:
                read_settings = json.load(f)
                read_settings['db-level'] = new_db_level
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                json.dump(read_settings, f)
            messagebox.showinfo(message="声音阈值修改成功！")
        except FileNotFoundError:
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                json.dump(write_data, f)
            messagebox.showinfo(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
        except json.decoder.JSONDecodeError:
            messagebox.showerror(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")


def _load_settings(self):
    current_account = self.current_acount
    try:
        with open(f"./data/{current_account}/settings.json", "r") as f:
            read_settings = json.load(f)
    except FileNotFoundError:
        try:
            os.makedirs(f"./data/{current_account}")
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                f.write("")
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                json.dump(write_data, f)
        except FileExistsError:
            with open(f"./data/{self.current_acount}/settings.json", "w") as f:
                write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
                json.dump(write_data, f)
        read_settings = write_data
        messagebox.showinfo(message="无法找到您的设置文件，已将设置全部重置!")
    try:
        with open("./data/acounts.json", "r") as f:
            load_accounts = json.load(f)
        try:
            get_password = base64.b64decode(load_accounts['passwords'][self.current_acount]).decode("utf-8")
        except IndexError:
            with open("./data/acounts.json", "r") as f:
                read_accounts = json.load(f)
            read_accounts['passwords'][self.current_acount] = ""
            with open("./data/accounts.json", "w") as f:
                json.dump(read_accounts,f)
            get_password = ""
            messagebox.showinfo(message="无法找到你的密码！已自动重置为空!")
    except FileNotFoundError:
        with open("./data/acounts.json", "w") as f:
            write_data = {"names": [], "passwords": {}}
            json.dump(write_data, f)
        self.current_acount = ""
        self.if_logged_in = False
        self.welcome_page(destroy_window=self.settings_frame)
        messagebox.showinfo(message="无法找到账户配置文件，已自动重置\n请清空data文件夹中的子文件夹\n重新注册账号！")
    self.settings_goal_value.set(value=int(read_settings['goal']) / 60)
    self.settings_stop_dur_value.set(value=read_settings['stop-dur'])
    self.settings_db_value.set(value=read_settings['db-level'])
    try:
        self.settings_name_value.set(base64.b64decode(self.current_acount).decode("utf-8"))
    except Exception:
        self.settings_name_value.set("")
    self.settings_password_value.set(get_password)
    if read_settings['if_tts'] == 0:
        self.enable_or_disable_tts_gui(state=False)
    elif read_settings['if_tts'] == 1:
        self.enable_or_disable_tts_gui(state=True)
        with open(f"./data/{self.current_acount}/tts_config.json", "r") as f:
            read_tts_settings = json.load(f)
        for key_, vals in read_tts_settings.items():
            for key, values in read_tts_settings[key_].items():
                if key == "condition":condition = values
                elif key == "value":value = values
                elif key == "text": text = values
                elif key == "rate":rate = values
                elif key == "volume": volume = values
                elif key == "voice": voice = values
                elif key == "source": source = values
            self.tts_tree.insert("", tk.END, values=(f"{condition} {value}", text,rate, volume, voice, source))
def _change_theme(self):
    try:
        get_selected = self.customize_listbox.get(self.customize_listbox.curselection())
        ttkbs.Style().theme_use(get_selected)
        with open(f"./data/{self.current_acount}/settings.json", "r") as f:
            read_settings = json.load(f)
        read_settings['theme'] = get_selected
        with open(f"./data/{self.current_acount}/settings.json", "w") as f:
            json.dump(read_settings, f)
    except tk.TclError as e:
        messagebox.showerror(message="请选择一个主题！")

def save_tts_settings(self, args):
    try:
        print(args)
        with open(f"./data/{self.current_acount}/settings.json", "r") as f:
            read_settings = json.load(f)
        read_settings['if_tts'] = args[0]
        with open(f"./data/{self.current_acount}/settings.json", "w") as f:
            json.dump(read_settings, f)
        if args[0] == 0:
            self.enable_or_disable_tts_gui(state=False)
        elif args[0] == 1:
            self.enable_or_disable_tts_gui(state=True)
            write_list ={}
            for i in range(len(args[1])):
                write_list[i] = {"condition":args[1][i][0].split(" ")[0],
                                 "value": args[1][i][0].split(" ")[1], 
                                 "text": args[1][i][1], 
                                 "rate": args[1][i][2], 
                                 "volume": args[1][i][3],
                                 "voice": args[1][i][4],
                                 "source": args[1][i][5]}
            try:
                with open(f"./data/{self.current_acount}/tts_config.json", "w") as f:
                    json.dump(write_list, f)
            except FileNotFoundError:
                with open(f"./data/{self.current_acount}/tts_config.json", "w") as f:
                    json.dump(write_list, f)
    except FileNotFoundError:
        with open(f"./data/{self.current_acount}/settings.json", "w") as f:
            write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":0, "theme":"darkly", "if_tts":0}
            json.dump(write_data, f)
        messagebox.showinfo(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
    except json.decoder.JSONDecodeError:
        messagebox.showerror(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")