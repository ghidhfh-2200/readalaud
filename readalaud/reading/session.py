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
import queue as queue_module
from PySide6 import QtWidgets
from multiprocessing import get_context
from ..gui.gui_service import get_gui_service
from ..logger.log_manager import log_system

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
                    self.show_debug.append(text.rstrip("\n"))
                except Exception:
                    pass
            try:
                from ..gui.qt_helpers import run_on_ui
                run_on_ui(_append)
            except Exception:
                try:
                    self.show_debug.append(text.rstrip("\n"))
                except Exception:
                    pass
        except Exception as e:
            print("LOG FAILED:", text, "ERROR:", e, flush=True)
    else:
        print(text, flush=True)


# ── 读取今日数据 ─────────────────────────────────────────

def reading_data_get_and_check(self):
    self.log_operation("调用朗读数据预检", "执行 reading_data_get_and_check")
    try:
        self.show_debug.setReadOnly(False)
    except Exception:
        pass
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
                    self.reading_state_label.setText("出错！")
                    self.reading_state_label.setStyleSheet("color: red;")
                except Exception:
                    pass
        else:
            self.tts_read = None
    except FileNotFoundError:
        self.log_error("读取朗读设置失败", "settings.json 缺失，已重置默认配置")
        try:
            os.mkdir(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}")
        except Exception:
            pass
        write_data = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}
        with open(f"./data/{self.current_acount}/settings.json", "w", encoding="utf-8") as f:
            json.dump(write_data, f)
        log("无法读取配置文件，已自动重置", self)
        try:
            self.reading_state_label.setText("出错！")
            self.reading_state_label.setStyleSheet("color: red;")
        except Exception:
            pass
        self.load_settings = write_data

    count = 0
    while True:
        try:
            month_str = "-".join(get_date.split("-")[0:2])
            with open(f"./data/{self.current_acount}/{month_str}/{get_date}.json", "r", encoding="utf-8") as f:
                self.read_today_data = json.load(f)
                # 重新计算剩余时长：当朗读目标不为零时，使用目标 - 已读时间
                goal = float(self.load_settings.get("goal", 0) or 0)
                real_read_time = float(self.read_today_data.get("real_read_time", 0) or 0)
                if goal > 0:
                    self.read_today_data["left"] = max(0, goal - real_read_time)
                else:
                    self.read_today_data["left"] = 0
                try:
                    self.information_label_list[0].setText(
                        f"剩余时长: {datetime.timedelta(seconds=float(self.read_today_data['left']))}"
                    )
                    self.information_label_list[1].setText(
                        f"停顿总时长: {datetime.timedelta(seconds=float(self.read_today_data['stop_total']))}"
                    )
                    self.information_label_list[2].setText(
                        f"有效朗读时间: {datetime.timedelta(seconds=float(self.read_today_data['real_read_time']))}"
                    )
                    self.information_label_list[3].setText(
                        f"总时长: {datetime.timedelta(seconds=float(self.read_today_data['total']))}"
                    )
                    self.information_label_list[4].setText(f"最大音量: {float(self.read_today_data['max_sound'])}")
                    self.information_label_list[5].setText(f"效率: {self.read_today_data['efficiency']}")
                    self.labels_list[0].setText(
                        f"朗读目标: {datetime.timedelta(seconds=float(self.load_settings['goal']))}"
                    )
                    self.labels_list[1].setText(f"声音阈值: {self.load_settings['db-level']}")
                    self.labels_list[2].setText(f"语音提示: {self.load_settings['if_tts']}")
                except Exception as e:
                    self.log_error("朗读界面更新失败", str(e))
                    print("UI update error:", e, flush=True)
                log("一切准备就绪！", self)
                try:
                    self.reading_state_label.setText("准备就绪!")
                    self.reading_state_label.setStyleSheet("color: green;")
                except Exception:
                    pass
                return
        except FileNotFoundError:
            if count >= 3:
                self.log_error("读取今日朗读数据失败", "重试次数达到上限")
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
            self.log_operation("初始化今日朗读数据", f"date={get_date}")


# ── 网页打开 ─────────────────────────────────────────────

def start_webpage():
    url = "http://127.0.0.1:8008/web/audio_visualizer.html"
    log_system("调用打开朗读网页", url)

    # 等待服务器就绪，最多等待 10 秒，避免 WebSocket 竞态条件
    max_wait = 10
    waited = 0
    while waited < max_wait:
        if check_if_server_running():
            log_system("服务器已就绪", f"waited={waited}s")
            break
        time.sleep(0.5)
        waited += 0.5
    else:
        log_system("服务器启动超时", f"waited={max_wait}s, 仍尝试打开网页")

    try:
        import webbrowser
        opened = webbrowser.open(url)
        if not opened:
            app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
            clipboard = app.clipboard()
            clipboard.setText(url)
            get_gui_service().error(
                f"无法自动打开浏览器！\n已成功自动复制链接到剪贴板，请手动去浏览器中粘贴访问：\n{url}",
                title="不支持",
            )
            log_system("打开朗读网页失败", "自动打开浏览器失败，已复制链接")
    except Exception as e:
        log(f"打开网页失败: {e}")
        log_system("打开朗读网页异常", str(e))


# ── 朗读启动 ─────────────────────────────────────────────

def start_reading(self):
    self.log_operation("调用开始朗读", "执行 start_reading")
    abs_path = pathlib.Path(__file__).resolve()
    project_root = abs_path.parent.parent.parent
    temp_file = project_root / "temp.json"

    try:
        with open(str(temp_file), "w", encoding="utf-8") as f:
            json.dump({"calibration": self.load_settings["calibration"], "threshold": self.load_settings["db-level"]}, f)
    except Exception as e:
        self.log_error("写入 temp.json 失败", str(e))
        log(f"Unable to write {temp_file}: {e}", self)
        try:
            with open("./temp.json", "w", encoding="utf-8") as f:
                json.dump({"calibration": self.load_settings["calibration"], "threshold": self.load_settings["db-level"]}, f)
        except Exception as e2:
            self.log_error("写入 temp.json 重试失败", str(e2))
            log(f"Retry Failed: {e2}", self=self)
            try:
                self.gui.error(f"无法创建 temp.json: {e2}", title="写入错误")
            except Exception:
                pass
            return

    ctx = get_context("spawn")
    log("正在启动朗读服务器，请稍后...", self=self)
    server_running = check_if_server_running()
    self.log_operation("检查服务器状态", f"running={server_running}")

    if hasattr(self, "roll_check_threading") and self.roll_check_threading.is_alive():
        self.if_reading = False
        time.sleep(0.2)

    if server_running:
        ask_restart = self.gui.ask_yes_no(message="服务器正在运行！是否重启服务器？")
        self.log_operation("服务器已在运行", f"用户选择重启={ask_restart}")
        if ask_restart:
            self.if_reading = True
            log("发现僵尸服务器进程，正在尝试清除！", self=self)
            get_port = server_pid()
            end_task = end_server_process(pid=get_port, force=True)
            if end_task == "suc":
                log(f"成功清除了进程ID为 {get_port} 的服务器进程", self=self)
                self.log_operation("结束旧服务器进程", f"pid={get_port}")
                time.sleep(2)
                gui_update_queue = ctx.Queue()
                ctx.Process(target=start_socket_server, args=(gui_update_queue,)).start()
                ctx.Process(target=start_webpage).start()
                _start_roll_check(self, gui_update_queue)
            else:
                log(f"无法清除进程ID为 {get_port} 的服务器进程", self=self)
                self.log_error("结束旧服务器进程失败", f"pid={get_port}, result={end_task}")
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
    self.log_operation("启动朗读轮询线程", f"ipc_queue={'on' if ipc_queue is not None else 'off'}")
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
    instance.log_operation("朗读后台线程已启动", "data_thread + ui_thread")

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
    instance.log_operation("朗读后台线程已退出", "roll_check completed")


# ── TTS 提示生成 ─────────────────────────────────────────

def _generate_tts_prompt(text, voice, volume, speed):
    from readalaud.tts.local_tts import speak
    return speak(text=str(text), volume=float(volume), speed=float(speed), voice_name=str(voice))
