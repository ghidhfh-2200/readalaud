import datetime
import json
import queue
from tkinter import messagebox
import tkinter as tk
import os
from multiprocessing import get_context
from . import server,server_manager
import subprocess
import platform
import pathlib
import threading
import time
import csv
import wave
import shutil
import urllib.request
from . import tts

def bind_reading_api(instance):
    instance.reading_data_get = lambda: reading_data_get_and_check(instance)
    instance.generate_tts_prompt = lambda text, voice, volume, speed: generate_tts_prompt(text, voice, volume, speed)

def log(msg, self=None, queue=None):
    text = f"[{datetime.datetime.now()}] {msg}\n"
    if queue:
        # 如果提供了队列，将消息发送到队列
        queue.put(msg)
    elif self:
        try:
            # 在主线程中安全地写入 Text 小部件
            def _append():
                try:
                    self.show_debug.insert(tk.END, text)
                    self.show_debug.see(tk.END)
                except Exception:
                    pass
            try:
                self.show_debug.after(0, _append)
            except Exception:
                # fallback: 直接写入（如果 after 失败）
                try:
                    self.show_debug.insert(tk.END, text)
                    self.show_debug.see(tk.END)
                except Exception:
                    pass
        except Exception as e:
            # 如果在非主线程或 widget 不可用时写入失败，退回到控制台输出以便调试
            print("LOG FAILED:", text, "ERROR:", e, flush=True)
    else:
        # 如果没有队列或 self，直接打印到控制台
        print(text, flush=True)
def reading_data_get_and_check(self):
    self.show_debug.configure(state="normal")
    get_date = datetime.datetime.now().strftime('%Y-%m-%d')
    try:
        with open(f"./data/{self.current_acount}/settings.json", "r", encoding="utf-8") as f_read:
            self.load_settings = json.load(f_read)
        log("已成功加载配置文件！", self)
        if self.load_settings.get('if_tts') == 1:
            try:
                with open(f"./data/{self.current_acount}/tts_config.json", "r", encoding="utf-8") as f_tts:
                    self.tts_read = json.load(f_tts)
                log("成功加载TTS设置文件！", self)
            except FileNotFoundError:
                self.load_settings['if_tts'] = 0
                with open(f"./data/{self.current_acount}/settings.json", "w", encoding="utf-8") as f_read:
                    json.dump(self.load_settings, f_read)
                log("无法读取到TTS设置文件，已自动重置,请重新读取", self)
                try:
                    self.reading_state_label.configure(text="出错！", fg="red")
                    self.reading_state_label.update_idletasks()
                except Exception:
                    pass
        else:
            self.tts_read = None
        print("tts:", self.tts_read)
    except FileNotFoundError:
        try:
            os.mkdir(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}")
        except Exception:
            pass
        write_data = {'goal':0, "stop-dur":0, "db-level":0, "calibration":94, "theme":"darkly", "if_tts":0}
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
            with open(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}/{get_date}.json", "r", encoding="utf-8") as f:
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
                    for lbl in self.information_label_list:
                        try:
                            lbl.update_idletasks()
                        except Exception:
                            pass
                    for lbl in self.labels_list:
                        try:
                            lbl.update_idletasks()
                        except Exception:
                            pass
                except Exception as e:
                    # 如果更新 UI 失败，仍然继续并在控制台打印错误以便调试
                    print("UI update error:", e, flush=True)
                log("一切准备就绪！", self)
                try:
                    self.reading_state_label.configure(text=f"准备就绪!", fg="green")
                    self.reading_state_label.update_idletasks()
                except Exception:
                    pass
                return
        except FileNotFoundError:
            if count >= 3:
                return
            # 最多重试三次，以免卡死
            count += 1
            try:
                os.mkdir(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}")
            except Exception:
                pass
            write_data = {"left": self.load_settings['goal'], "stop_total": 0, "real_read_time": 0, "total": 0, "max_sound": 0, "efficiency": 0.00}
            with open(f"./data/{self.current_acount}/{'-'.join(get_date.split('-')[0:2])}/{get_date}.json", "w", encoding="utf-8") as f:
                json.dump(write_data, f)
            log("未读取到今日朗读数据，已重置!", self)
def start_server(queue):
    # 使用显式 spawn 上下文以避免 Windows 下的子进程重入与 pickle 问题
    ctx = get_context("spawn")
    if_server_running = server_manager.check_if_server_running()
    print(if_server_running)
    if not if_server_running:
        # 启动网页的进程（不要设为 daemon）
        open_web = ctx.Process(target=start_webpage)
        open_web.start()

        # 启动服务器的进程（不要设为 daemon）
        server_process = ctx.Process(target=server.start_socket_server, args=(queue,))
        server_process.start()
        print("ok_sev", "web pid:", getattr(open_web, "pid", None), "server pid:", getattr(server_process, "pid", None))
    else:
        start_webpage()

def start_webpage():
    abs_path = pathlib.Path(__file__).resolve()
    parent_path = abs_path.parent.parent
    file_path = str(parent_path / "web" / "audio_visualizer.html")
    try:
        if platform.system() == "Windows":
            os.startfile(file_path)
        elif platform.system() == "Linux":
            subprocess.call(["xdg-open", file_path])
        elif platform.system() == "Darwin":
            subprocess.call(["open", file_path])
        else:
            messagebox.showerror("您当前操作系统不支持自动打开朗读界面！\n请手动在浏览器打开web目录下的audio_visualizer.html文件")
            print("Unsupported operating system")
    except Exception as e:
        log(f"打开文件失败: {e}")
def start_reading(self):
    # write temp.json to an absolute, predictable location (project root) to avoid
    # issues with the current working directory causing OSError: [Errno 22]
    abs_path = pathlib.Path(__file__).resolve()
    project_root = abs_path.parent.parent
    temp_file = project_root / "temp.json"

    try:
        with open(str(temp_file), "w", encoding="utf-8") as f:
            json.dump({"calibration": self.load_settings['calibration'], "threshold": self.load_settings['db-level']}, f)
    except Exception as e:
        log(f"Unable to write {temp_file}: {e}", self)
        # fallback: try writing to the current working directory as a last resort
        try:
            with open("./temp.json", "w", encoding="utf-8") as f:
                json.dump({"calibration": self.load_settings['calibration'], "threshold": self.load_settings['db-level']}, f)
        except Exception as e2:
            log(f"Retry Failed: {e2}", self=self)
            try:
                messagebox.showerror("写入错误", f"无法创建 temp.json: {e2}")
            except Exception:
                pass
            return
    ctx = get_context("spawn")
    log("正在启动朗读服务器，请稍后...", self=self)
    server_running = server_manager.check_if_server_running()
    # 先关闭旧的 roll_check 线程（如果有）
    if hasattr(self, 'roll_check_threading') and self.roll_check_threading.is_alive():
        self.if_reading = False
        time.sleep(0.2)
    # 轮询线程控制标志

    if server_running:
        ask_restart = messagebox.askyesno(message="服务器正在运行！此操作将会重启服务器，确定继续？")
        if ask_restart:
            self.if_reading = True
            log("发现僵尸服务器进程，正在尝试清除！", self=self)
            get_port = server_manager.server_pid()
            end_task = server_manager.end_server_process(pid=get_port, force=True)
            if end_task == "suc":
                log(f"成功清除了进程ID为 {get_port} 的服务器进程", self=self)
                time.sleep(2)
                gui_update_queue = ctx.Queue()
                server_process = ctx.Process(target=server.start_socket_server, args=(gui_update_queue,))
                server_process.start()
                open_web = ctx.Process(target=start_webpage)
                open_web.start()
                # 启动 roll_check 线程（IPC模式）
                self.roll_check_threading = threading.Thread(target=roll_check, args=(
                                                                              self.reading_state_label,
                                                                              gui_update_queue,
                                                                              self.information_label_list,
                                                                              self,))
                self.roll_check_threading.daemon = True
                self.roll_check_threading.start()
            else:
                log(f"无法清除进程ID为 {get_port} 的服务器进程", self=self)
        else:
            # 服务器已在运行，直接打开网页
            open_web = ctx.Process(target=start_webpage)
            open_web.start()
            # 如果轮询线程未运行，则启动轮询线程
            if not (hasattr(self, 'roll_check_threading') and self.roll_check_threading.is_alive()):
                self.if_reading = True
                # 服务器已在运行但不是本次启动的，无法使用IPC队列，传入None使用HTTP轮询模式
                self.roll_check_threading = threading.Thread(target=roll_check, args=(
                                                                                    self.reading_state_label,
                                                                                    None,
                                                                                    self.information_label_list,
                                                                                    self,))
                self.roll_check_threading.daemon = True
                self.roll_check_threading.start()
    else:
        # 服务器未运行，主进程直接启动服务器和网页，并用IPC队列
        self.if_reading = True
        gui_update_queue = ctx.Queue()
        server_process = ctx.Process(target=server.start_socket_server, args=(gui_update_queue,))
        server_process.start()
        open_web = ctx.Process(target=start_webpage)
        open_web.start()
        self.roll_check_threading = threading.Thread(target=roll_check, args=(
                                                                              self.reading_state_label,
                                                                              gui_update_queue,
                                                                              self.information_label_list,
                                                                              self,))
        self.roll_check_threading.daemon = True
        self.roll_check_threading.start()
def WriteCountDbWrite(db_list, acount):
    # Added missing function WriteCountDbWrite to log DB data for the current date
    get_date = datetime.datetime.now().strftime('%Y-%m-%d')
    write_db_data(acount=acount, db=db_list, date=get_date)

def _poll_server_http(url="http://127.0.0.1:8008/poll", timeout=2):
    """当IPC队列不可用时，通过HTTP轮询服务器的/poll端点获取最新状态。"""
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def data_thread(ipc_queue, ui_queue, instance):
    write_count = 0
    db_list = []
    
    # Initialize timing with current time to calculate deltas
    last_process_time = time.time()
    
    # Tracking for TTS
    instance.tts_triggered_events = set()
    instance.tts_cooldowns = {} # key: index, value: last_trigger_time
    current_pause_start = None
    last_ui_update_time = 0
    
    # HTTP轮询模式状态（当ipc_queue为None时使用HTTP轮询代替IPC队列）
    use_http_poll = (ipc_queue is None)
    last_poll_broadcast = None
    
    if use_http_poll:
        # 首次轮询：丢弃上一次会话残留的 end_sig 和旧 broadcast，
        # 确保不会因为陈旧状态立刻触发结束流程
        initial_poll = _poll_server_http()
        if initial_poll and isinstance(initial_poll, dict):
            # 记录当前广播内容作为基线，只有后续变化才会被处理
            if "broadcast" in initial_poll:
                last_poll_broadcast = initial_poll["broadcast"]
            # end_sig 已被服务器的 /poll 端点消费（pop），无需额外处理
        print("[data_thread] HTTP polling mode started, baseline state cleared.", flush=True)
    
    while getattr(instance, 'if_reading', True):
        try:
            data = None
            if use_http_poll:
                # HTTP轮询模式：服务器已在运行，通过HTTP获取最新状态
                poll_result = _poll_server_http()
                if poll_result is not None and isinstance(poll_result, dict):
                    # 检查结束信号
                    if "end_sig" in poll_result:
                        data = {"end_sig": True}
                    # 只处理有变化的广播数据（避免重复累计时间）
                    if "broadcast" in poll_result:
                        current_bc = poll_result["broadcast"]
                        if current_bc != last_poll_broadcast:
                            last_poll_broadcast = current_bc
                            if data is None:
                                data = {}
                            data["broadcast"] = current_bc
                if data is None:
                    time.sleep(0.5)
                    continue
                time.sleep(0.3)
            else:
                try:
                    data = ipc_queue.get(timeout=1)
                except Exception:
                    continue
                
            if not data:
                continue

            if "broadcast" in data:
                current_time = time.time()
                time_delta = current_time - last_process_time
                last_process_time = current_time
                
                # Cap extremely large deltas (e.g., system sleep or long disconnect) to avoid massive jumps
                # Assuming max reasonable lag is 5 seconds.
                if time_delta > 5.0:
                    time_delta = 1.0 # Fallback to 1s if sync lost significantly? Or just cap at 5?
                    # Let's assume valid data flows continuously.

                db_text = data['broadcast'].get('db', '')
                get_state = data['broadcast'].get('state', '')
                
                display_msg = ""
                should_update_stats = False
                
                val_db = 0.0
                try:
                    val_db = float(db_text)
                except:
                    pass
                
                # Update State and Pause Tracking
                current_pause_duration = 0.0
                if get_state in ["db-paused", "paused", "pre-paused"]:
                    if current_pause_start is None:
                        current_pause_start = current_time
                    current_pause_duration = current_time - current_pause_start
                else:
                     current_pause_start = None
                
                if get_state == "reading" or get_state == "pre-paused":
                    display_msg = f"正在朗读   {round(val_db, 1)} dB"
                    if float(round(val_db, 1)) > float(instance.read_today_data['max_sound']):
                        instance.read_today_data['max_sound'] = float(round(val_db, 1))
                    
                    if write_count < 10:
                        write_count += 1
                        db_list.append(round(val_db, 3))
                    elif write_count >= 10:
                        WriteCountDbWrite(db_list=db_list, acount=getattr(instance, "current_acount"))
                        write_count = 0
                        db_list = []
                    
                    instance.read_today_data['left'] = float(instance.read_today_data['left']) - time_delta
                    instance.read_today_data['real_read_time'] = float(instance.read_today_data['real_read_time']) + time_delta
                    should_update_stats = True
                        
                elif get_state == "db-paused":
                    display_msg = f"停顿   {round(val_db, 1)} dB"
                    if write_count < 10:
                        write_count += 1
                        db_list.append(round(val_db, 3))
                    elif write_count >= 10:
                        WriteCountDbWrite(db_list=db_list, acount=getattr(instance, "current_acount"))
                        write_count = 0
                        db_list = []
                        
                    instance.read_today_data['stop_total'] = float(instance.read_today_data['stop_total']) + time_delta
                    should_update_stats = True

                elif get_state == "paused":
                    display_msg = "已暂停"
                    should_update_stats = True

                if should_update_stats:
                    instance.read_today_data['total'] = float(instance.read_today_data['total']) + time_delta
                    if float(instance.read_today_data['total']) > 0:
                        instance.read_today_data['efficiency'] = round(float(instance.read_today_data['real_read_time']) / float(instance.read_today_data['total']), 2)

                # Check TTS Conditions
                if instance.tts_read:
                    check_tts_conditions(
                        instance=instance,
                        tts_config=instance.tts_read,
                        current_db=val_db,
                        current_pause_duration=current_pause_duration,
                        left=instance.read_today_data['left'],
                        total_stop=instance.read_today_data['stop_total'],
                        total=instance.read_today_data['total'],
                        real_read_time=instance.read_today_data['real_read_time'],
                        max_db=instance.read_today_data['max_sound'],
                        efficiency=instance.read_today_data['efficiency']
                    )

                update_payload = {
                    "type": "update",
                    "main_label_text": display_msg
                }

                if current_time - last_ui_update_time >= 0.1:
                    last_ui_update_time = current_time
                    update_payload["info_data"] = {
                        "left": instance.read_today_data['left'],
                        "stop_total": instance.read_today_data['stop_total'],
                        "real_read_time": instance.read_today_data['real_read_time'],
                        "total": instance.read_today_data['total'],
                        "max_sound": instance.read_today_data['max_sound'],
                        "efficiency": instance.read_today_data['efficiency']
                    }

                ui_queue.put(update_payload)

            if "end_sig" in data:
                instance.if_reading = False
                ui_queue.put({"type": "stop"})
                current_account = getattr(instance, "current_acount")
                get_date = datetime.datetime.now().strftime('%Y-%m-%d')
                write_data = write_data = {"left": int(instance.read_today_data['left']), 
                                           "stop_total": int(instance.read_today_data['stop_total']), 
                                           "real_read_time": int(instance.read_today_data['real_read_time']),
                                           "total": int(instance.read_today_data['total']), 
                                           "max_sound": float(instance.read_today_data['max_sound']), 
                                           "efficiency": float(instance.read_today_data['efficiency'])}
                log(msg="正在合并缓存...", self=instance)
                with open(f"./data/{current_account}/{'-'.join(get_date.split('-')[0:2])}/{get_date}.json", "w", encoding="utf-8") as f:
                    json.dump(write_data, f)
                time.sleep(2)
                list_chunks = os.listdir("./audio_chunks")
                merge_wav(list_chunks, f"./details/{current_account}/{get_date}/recording.wav")
                try:
                    shutil.rmtree("./audio_chunks")
                    print(2)
                    log(self=instance, msg="正在清除缓存...")
                except FileNotFoundError:
                    log(self=instance, msg="未找到缓存文件夹")
                break

        except Exception as e:
            print(f"Error in data_thread: {e}")
            break

def read_wav(file_path):
    wav = wave.open(file_path, 'rb')
    params = wav.getparams()
    frames = wav.readframes(wav.getnframes())
    wav.close()
    return params, frames

def merge_wav(wav_list, output_file):
    print("run")
    merged_params = None
    merged_frames = b''
    print(wav_list)
    for i in range(len(wav_list)):
        wav_list[i] = "./audio_chunks/" + wav_list[i]
    print(wav_list)
    # Ensure the output directory exists before writing
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    # 2. 读取并合并所有wav文件
    for file in wav_list:
        params, frames = read_wav(file)
        if merged_params is None:
            merged_params = params
        merged_frames += frames
    
    if not os.path.exists(output_file):
        print(1)
        merged_wav = wave.open(output_file, 'wb')
        merged_wav.setparams(merged_params)
        merged_wav.writeframes(merged_frames)
        merged_wav.close()
    else:
        # 文件存在，需要合并现有内容和新的内容
        # 读取现有的output_file内容
        params_existing, frames_existing = read_wav(output_file)

        # 合并帧数据：现有文件内容 + 新合并的内容
        combined_frames = frames_existing + merged_frames
        
        # 写入合并后的数据到output_file
        merged_wav = wave.open(output_file, 'wb')
        merged_wav.setparams(params_existing)  # 使用现有文件的参数
        merged_wav.writeframes(combined_frames)  # 写入合并后的帧
        merged_wav.close()
        print("ok")
        
def ui_thread(ui_queue, state_label, information_label_list):
    while True:
        try:
            msg = ui_queue.get()
            msg_type = msg.get("type")
            
            if msg_type == "stop":
                state_label.after(0, lambda: state_label.config(text="已停止"))
                break
            
            if msg_type == "update":
                main_text = msg.get("main_label_text")
                info = msg.get("info_data")
                
                if main_text:
                    state_label.after(0, lambda t=main_text: state_label.config(text=t))
                
                if info:
                    texts = [
                        f"剩余时长: {datetime.timedelta(seconds=int(info['left']))}",
                        f"停顿总时长: {datetime.timedelta(seconds=int(info['stop_total']))}",
                        f"有效朗读时间: {datetime.timedelta(seconds=int(info['real_read_time']))}",
                        f"总时长: {datetime.timedelta(seconds=int(info['total']))}",
                        f"最大音量: {info['max_sound']}",
                        f"效率: {info['efficiency']}"
                    ]
                    
                    for i, label in enumerate(information_label_list):
                        if i < len(texts):
                            state_label.after(0, lambda lb=label, tx=texts[i]: lb.configure(text=tx))
                            
        except Exception as e:
            print(f"Error in ui_thread: {e}")
            break

def roll_check(state, queue_ipc, information_label_list, instance):
    internal_ui_queue = queue.Queue()
    
    # Assign threads to instance so they can be tracked if needed
    instance.thread_data = threading.Thread(target=data_thread, args=(queue_ipc, internal_ui_queue, instance))
    instance.thread_ui = threading.Thread(target=ui_thread, args=(internal_ui_queue, state, information_label_list))
    
    instance.thread_data.daemon = True
    instance.thread_ui.daemon = True
    
    instance.thread_data.start()
    instance.thread_ui.start()
    
    # Monitor loop instead of blocking join
    # This keeps the roll_check thread alive to satisfy is_alive() checks in start_reading
    # but actively checks for the reading state and worker health.
    while getattr(instance, 'if_reading', True):
        if not instance.thread_data.is_alive():
            # If data thread dies/exits, we should stop
            break
        time.sleep(0.5)

    # Cleanup
    instance.if_reading = False
    # Wait briefly for threads to finish their loops if they are still running
    if instance.thread_data.is_alive():
        instance.thread_data.join(timeout=1.0)
    if instance.thread_ui.is_alive():
        # Optimization: UI thread blocks on queue.get(). 
        # Sending a stop signal is handled by data_thread sending "stop" or we inject it here if needed.
        # But if data_thread is dead, we might need to push 'stop' manually if it crashed.
        internal_ui_queue.put({"type": "stop"})
        instance.thread_ui.join(timeout=1.0)

def write_db_data(acount, db, date):
    try:
        with open(f"./details/{acount}/{date}/DB.csv", "a", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(db)
    except FileNotFoundError:
        if_details_exist = os.path.exists("./details") and os.path.isdir("./details")
        if if_details_exist:
            if_acount_exist = os.path.exists(f"./details/{acount}") and os.path.isdir(f"./details/{acount}")
            if if_acount_exist:
                if_date_exist = os.path.exists(f"./details/{acount}/{date}") and os.path.isdir(f"./details/{acount}/{date}")
                if if_date_exist:
                    if_csv_exists = os.path.exists(f"./details/{acount}/{date}/DB.csv") and os.path.isfile(f"./details/{acount}/{date}/DB.csv")
                    if if_csv_exists:
                        write_db_data(acount=acount, db=db, date=date)
                    else:
                        with open(f"./details/{acount}/{date}/DB.csv", "w") as f:
                            f.write("")
                        write_db_data(acount=acount, db=db, date=date)
                else:
                    os.mkdir(f"./details/{acount}/{date}")
            else:
                os.mkdir(f"./details/{acount}")
                write_db_data(acount=acount, db=db,date=date)
        else:
            os.mkdir("./details")
            write_db_data(acount=acount, db=db, date=date)
    except Exception as e:
        raise e
    
def _play_web_tts_cached(text, volume, speed, output_path):
    """
    Generate audio using edge-tts CLI if file doesn't exist, then play it.
    Uses win32_playback from tts module logic if available.
    """
    try:
        from readalaud.tts import play_mp3_win32
    except ImportError:
        play_mp3_win32 = None

    if play_mp3_win32 is None:
        print("edge_playback not available for web TTS")
        return

    # Check if file exists - Play directly if so
    if os.path.exists(output_path):
        try:
            print('directly play')
            play_mp3_win32(output_path)
        except Exception as e:
            print(f"Playback error (cached): {e}")
        return

    # Generate it
    try:
        try:
            vol_str = f"{int((float(volume)) * 100):+d}%"
        except Exception:
            vol_str = "+0%"
        try:
            rate_str = f"{int((float(speed)) * 100):+d}%"
        except Exception:
            rate_str = "+0%"

        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        cmd = ["edge-tts", "-t", str(text), "--write-media", output_path, f"--rate={rate_str}", f"--volume={vol_str}"]
        
        try:
            # Hide console window on Windows
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.run(cmd, check=True, timeout=60, startupinfo=startupinfo, capture_output=True)
        except subprocess.CalledProcessError as e:
            print(f"Failed to generate TTS: {e}")
            return
        except Exception as e:
            print(f"TTS Config Error: {e}")
            return
            
        # Play instantly after generation
        try:
            t = threading.Thread(target=play_mp3_win32, args=(output_path,))
            t.start()
        except Exception as e:
            print(f"Playback error: {e}")
            
    except Exception as e:
        print(f"TTS Process Error: {e}")

def check_tts_conditions(instance, tts_config, current_db, current_pause_duration, 
                         left, total_stop, total, real_read_time, max_db, efficiency):
    """
    检查TTS触发条件
    """
    current_time = time.time()
    
    for index_key, config in tts_config.items():
        try:
            condition = config.get("condition")
            target_value_str = config.get("value", "0")
            target_value = float(target_value_str)
            
            # Cooldown check (default 10s for repetitive events)
            last_trigger = instance.tts_cooldowns.get(index_key, 0)
            
            should_trigger = False
            is_one_shot = False
            
            if condition == "当音量达到":
                if current_db >= target_value:
                    if current_time - last_trigger > 10:
                        should_trigger = True
            
            elif condition == "当音量低于":
                if current_db < target_value:
                    if current_time - last_trigger > 10:
                        should_trigger = True
            
            elif condition == "当达到目标":
                # Assuming 'left' goes to 0 when goal reached. Or compare total/goal.
                # If left <= 0, goal reached.
                if left <= 0:
                    is_one_shot = True
                    should_trigger = True

            elif condition == "当时间点达到":
                # Value is in minutes. Compare with real_read_time (seconds).
                target_seconds = target_value * 60
                # Trigger if we just passed it (within a margin) or if we are past it and haven't triggered yet.
                if real_read_time >= target_seconds:
                    is_one_shot = True
                    should_trigger = True

            elif condition == "当任务进度达到":
                # Value is percentage (0-100).
                # We need goal. instance.load_settings['goal'] should exist.
                # Calculate current %: real_read_time / goal * 100
                goal_str = instance.load_settings.get('goal', 0) 
                goal = float(goal_str) if goal_str else 0
                if goal > 0:
                    current_percent = (real_read_time / goal) * 100
                    if current_percent >= target_value:
                        is_one_shot = True
                        should_trigger = True

            elif condition == "检测到异常停顿":
                # Value is seconds.
                if current_pause_duration >= target_value:
                    if current_time - last_trigger > (target_value + 10): # Cooldown: duration + buffer
                        should_trigger = True

            if should_trigger:
                # Check one-shot history
                if is_one_shot and index_key in instance.tts_triggered_events:
                    continue

                # Execute Trigger
                instance.tts_cooldowns[index_key] = current_time
                if is_one_shot:
                    instance.tts_triggered_events.add(index_key)
                
                # Speak
                source = config.get("source", "local")
                text = config.get("text", "")
                volume = config.get("volume", "1.0")
                rate = config.get("rate", "1.0") # stored as speed
                voice = config.get("voice", "")

                if source == "web":
                    # Generate/Play Web TTS
                    # Path: ./data/{current_account}/tts/{index}.mp3
                    account_dir = getattr(instance, "current_acount", "default")
                    base_path = f"./data/{account_dir}/tts"
                    file_path = os.path.abspath(os.path.join(base_path, f"{index_key}.mp3"))
                    
                    # Run in separate thread to avoid blocking data_thread
                    # Although _play_web_tts_cached spawns a thread for playback, 
                    # the generation (subprocess) might take a moment. 
                    # Better to spawn a worker thread for the whole process.
                    threading.Thread(target=_play_web_tts_cached, 
                                     args=(text, volume, rate, file_path)).start()

                else:
                    # Local
                    generate_tts_prompt(text, voice, volume, rate)

        except Exception as e:
            print(f"Error checking TTS condition {index_key}: {e}")
            continue

def generate_tts_prompt(text, voice, volume, speed):
    """Generate a TTS prompt using local pyttsx3 only."""
    return tts.speak(text=str(text), volume=float(volume), speed=float(speed), voice_name=str(voice))