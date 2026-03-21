"""
session.py —— 朗读会话的入口：数据加载、服务器启动、网页打开、轮询线程调度。
"""
import datetime
import json
import os
import platform
import subprocess
import pathlib
import threading
import time
import tkinter as tk
import queue as queue_module
from multiprocessing import get_context
from tkinter import messagebox

from readalaud.server import start_socket_server, check_if_server_running, server_pid, end_server_process


def bind_reading_api(instance):
    instance.reading_data_get = lambda: reading_data_get_and_check(instance)
    instance.generate_tts_prompt = lambda text, voice, volume, speed: _generate_tts_prompt(text, voice, volume, speed)


# ── 日志辅助 ─────────────────────────────────────────────

def log(msg, self=None, queue=None):
    text = f"[{datetime.datetime.now()}] {msg}\n"
    if queue:
        queue.put(msg)
    elif self:
        try:
            def _append():
                try:
                    self.show_debug.insert(tk.END, text)
                    self.show_debug.see(tk.END)
                except Exception:
                    pass
            try:
                self.show_debug.after(0, _append)
            except Exception:
                try:
                    self.show_debug.insert(tk.END, text)
                    self.show_debug.see(tk.END)
                except Exception:
                    pass
        except Exception as e:
            print("LOG FAILED:", text, "ERROR:", e, flush=True)
    else:
        print(text, flush=True)


# ── 读取今日数据 ─────────────────────────────────────────

def reading_data_get_and_check(self):
    self.show_debug.configure(state="normal")
    get_date = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        with open(f"./data/{self.current_acount}/settings.json", "r", encoding="utf-8") as f:
            self.load_settings = json.load(f)
        log("已成功加载配置文件！", self)
        if self.load_settings.get("if_tts") == 1:
            try:
                with open(f"./data/{self.current_acount}/tts_config.json", "r", encoding="utf-8") as f:
                    self.tts_read = json.load(f)
                log("成功加载TTS设置文件！", self)
            except FileNotFoundError:
                self.load_settings["if_tts"] = 0
                with open(f"./data/{self.current_acount}/settings.json", "w", encoding="utf-8") as f:
                    json.dump(self.load_settings, f)
                log("无法读取到TTS设置文件，已自动重置,请重新读取", self)
                try:
                    self.reading_state_label.configure(text="出错！", fg="red")
                    self.reading_state_label.update_idletasks()
                except Exception:
                    pass
        else:
            self.tts_read = None
    except FileNotFoundError:
        try:
            os.mkdir(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}")
        except Exception:
            pass
        write_data = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}
        with open(f"./data/{self.current_acount}/settings.json", "w", encoding="utf-8") as f:
            json.dump(write_data, f)
        log("无法读取配置文件，已自动重置", self)
        try:
            self.reading_state_label.configure(text="出错！", fg="red")
            self.reading_state_label.update_idletasks()
        except Exception:
            pass
        self.load_settings = write_data

    count = 0
    while True:
        try:
            month_str = "-".join(get_date.split("-")[0:2])
            with open(f"./data/{self.current_acount}/{month_str}/{get_date}.json", "r", encoding="utf-8") as f:
                self.read_today_data = json.load(f)
                try:
                    self.information_label_list[0].configure(text=f"剩余时长: {datetime.timedelta(seconds=float(self.read_today_data['left']))}")
                    self.information_label_list[1].configure(text=f"停顿总时长: {datetime.timedelta(seconds=float(self.read_today_data['stop_total']))}")
                    self.information_label_list[2].configure(text=f"有效朗读时间: {datetime.timedelta(seconds=float(self.read_today_data['real_read_time']))}")
                    self.information_label_list[3].configure(text=f"总时长: {datetime.timedelta(seconds=float(self.read_today_data['total']))}")
                    self.information_label_list[4].configure(text=f"最大音量: {float(self.read_today_data['max_sound'])}")
                    self.information_label_list[5].configure(text=f"效率: {self.read_today_data['efficiency']}")
                    self.labels_list[0].configure(text=f"朗读目标: {datetime.timedelta(seconds=float(self.load_settings['goal']))}")
                    self.labels_list[1].configure(text=f"声音阈值: {self.load_settings['db-level']}")
                    self.labels_list[2].configure(text=f"语音提示: {self.load_settings['if_tts']}")
                    for lbl in self.information_label_list + self.labels_list:
                        try:
                            lbl.update_idletasks()
                        except Exception:
                            pass
                except Exception as e:
                    print("UI update error:", e, flush=True)
                log("一切准备就绪！", self)
                try:
                    self.reading_state_label.configure(text="准备就绪!", fg="green")
                    self.reading_state_label.update_idletasks()
                except Exception:
                    pass
                return
        except FileNotFoundError:
            if count >= 3:
                return
            count += 1
            try:
                os.mkdir(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}")
            except Exception:
                pass
            write_data = {"left": self.load_settings["goal"], "stop_total": 0, "real_read_time": 0, "total": 0, "max_sound": 0, "efficiency": 0.00}
            month_str = "-".join(get_date.split("-")[0:2])
            with open(f"./data/{self.current_acount}/{month_str}/{get_date}.json", "w", encoding="utf-8") as f:
                json.dump(write_data, f)
            log("未读取到今日朗读数据，已重置!", self)


# ── 网页打开 ─────────────────────────────────────────────

def start_webpage():
    abs_path = pathlib.Path(__file__).resolve()
    parent_path = abs_path.parent.parent.parent
    file_path = str(parent_path / "web" / "audio_visualizer.html")
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Linux":
            subprocess.call(["xdg-open", file_path])
        elif platform.system() == "Darwin":
            subprocess.call(["open", file_path])
        else:
            messagebox.showerror("不支持", "您当前操作系统不支持自动打开朗读界面！\n请手动在浏览器打开web目录下的audio_visualizer.html文件")
    except Exception as e:
        log(f"打开文件失败: {e}")


# ── 朗读启动 ─────────────────────────────────────────────

def start_reading(self):
    abs_path = pathlib.Path(__file__).resolve()
    project_root = abs_path.parent.parent.parent
    temp_file = project_root / "temp.json"

    try:
        with open(str(temp_file), "w", encoding="utf-8") as f:
            json.dump({"calibration": self.load_settings["calibration"], "threshold": self.load_settings["db-level"]}, f)
    except Exception as e:
        log(f"Unable to write {temp_file}: {e}", self)
        try:
            with open("./temp.json", "w", encoding="utf-8") as f:
                json.dump({"calibration": self.load_settings["calibration"], "threshold": self.load_settings["db-level"]}, f)
        except Exception as e2:
            log(f"Retry Failed: {e2}", self=self)
            try:
                messagebox.showerror("写入错误", f"无法创建 temp.json: {e2}")
            except Exception:
                pass
            return

    ctx = get_context("spawn")
    log("正在启动朗读服务器，请稍后...", self=self)
    server_running = check_if_server_running()

    if hasattr(self, "roll_check_threading") and self.roll_check_threading.is_alive():
        self.if_reading = False
        time.sleep(0.2)

    if server_running:
        ask_restart = messagebox.askyesno(message="服务器正在运行！此操作将会重启服务器，确定继续？")
        if ask_restart:
            self.if_reading = True
            log("发现僵尸服务器进程，正在尝试清除！", self=self)
            get_port = server_pid()
            end_task = end_server_process(pid=get_port, force=True)
            if end_task == "suc":
                log(f"成功清除了进程ID为 {get_port} 的服务器进程", self=self)
                time.sleep(2)
                gui_update_queue = ctx.Queue()
                ctx.Process(target=start_socket_server, args=(gui_update_queue,)).start()
                ctx.Process(target=start_webpage).start()
                _start_roll_check(self, gui_update_queue)
            else:
                log(f"无法清除进程ID为 {get_port} 的服务器进程", self=self)
        else:
            ctx.Process(target=start_webpage).start()
            if not (hasattr(self, "roll_check_threading") and self.roll_check_threading.is_alive()):
                self.if_reading = True
                _start_roll_check(self, None)
    else:
        self.if_reading = True
        self.log_operation("开始朗读", "启动了朗读服务器并打开可视化网页")
        gui_update_queue = ctx.Queue()
        ctx.Process(target=start_socket_server, args=(gui_update_queue,)).start()
        ctx.Process(target=start_webpage).start()
        _start_roll_check(self, gui_update_queue)


def _start_roll_check(self, ipc_queue):
    self.roll_check_threading = threading.Thread(
        target=roll_check,
        args=(self.reading_state_label, ipc_queue, self.information_label_list, self),
        daemon=True,
    )
    self.roll_check_threading.start()


# ── 轮询协调线程 ─────────────────────────────────────────

def roll_check(state, queue_ipc, information_label_list, instance):
    from .data_thread import data_thread
    from .ui_thread import ui_thread

    internal_ui_queue = queue_module.Queue()
    instance.thread_data = threading.Thread(target=data_thread, args=(queue_ipc, internal_ui_queue, instance), daemon=True)
    instance.thread_ui = threading.Thread(target=ui_thread, args=(internal_ui_queue, state, information_label_list), daemon=True)
    instance.thread_data.start()
    instance.thread_ui.start()

    while getattr(instance, "if_reading", True):
        if not instance.thread_data.is_alive():
            break
        time.sleep(0.5)

    instance.if_reading = False
    if instance.thread_data.is_alive():
        instance.thread_data.join(timeout=1.0)
    if instance.thread_ui.is_alive():
        internal_ui_queue.put({"type": "stop"})
        instance.thread_ui.join(timeout=1.0)


# ── TTS 提示生成 ─────────────────────────────────────────

def _generate_tts_prompt(text, voice, volume, speed):
    from readalaud.tts.local_tts import speak
    return speak(text=str(text), volume=float(volume), speed=float(speed), voice_name=str(voice))
