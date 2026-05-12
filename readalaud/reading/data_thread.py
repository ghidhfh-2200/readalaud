"""
data_thread.py —— 后台数据线程：处理 IPC 队列或 HTTP 轮询，更新朗读统计数据。
"""
import datetime
import json
import os
import pathlib
import shutil
import time
import urllib.request

from .data_io import write_db_data
from .wav_merger import merge_wav
from .tts_trigger import check_tts_conditions
from ..tts.playback_control import request_stop_all_tts, clear_stop_request, should_stop_tts
from ..tts.local_tts import stop_speaking
from ..logger.log_manager import log_system


def _poll_server_http(url="http://127.0.0.1:8008/poll", timeout=2):
    """通过 HTTP 轮询获取服务器最新状态（IPC 队列不可用时的降级方案）。"""
    try:
        with urllib.request.urlopen(urllib.request.Request(url), timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None


def data_thread(ipc_queue, ui_queue, instance):
    instance.log_operation("启动数据线程", f"ipc_queue={'on' if ipc_queue is not None else 'off'}")
    write_count = 0
    db_list = []
    last_process_time = time.time()

    instance.tts_triggered_events = set()
    instance.tts_cooldowns = {}
    instance.tts_detection_enabled = True
    clear_stop_request()
    current_pause_start = None
    last_ui_update_time = 0

    use_http_poll = ipc_queue is None
    last_poll_broadcast = None

    if use_http_poll:
        initial_poll = _poll_server_http()
        if initial_poll and isinstance(initial_poll, dict):
            if "broadcast" in initial_poll:
                last_poll_broadcast = initial_poll["broadcast"]
        print("[data_thread] HTTP polling mode started, baseline state cleared.", flush=True)
        instance.log_operation("数据线程降级模式", "使用 HTTP 轮询替代 IPC")

    while getattr(instance, "if_reading", True):
        try:
            data = None
            if use_http_poll:
                poll_result = _poll_server_http()
                if poll_result and isinstance(poll_result, dict):
                    if "end_sig" in poll_result:
                        data = {"end_sig": True}
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
                time_delta = min(current_time - last_process_time, 5.0)
                last_process_time = current_time

                db_text = data["broadcast"].get("db", "")
                get_state = data["broadcast"].get("state", "")

                val_db = 0.0
                try:
                    val_db = float(db_text)
                except Exception:
                    pass

                current_pause_duration = 0.0
                if get_state in ["db-paused", "paused", "pre-paused"]:
                    if current_pause_start is None:
                        current_pause_start = current_time
                    current_pause_duration = current_time - current_pause_start
                else:
                    current_pause_start = None

                display_msg = ""
                should_update_stats = False

                if get_state in ("reading", "pre-paused"):
                    display_msg = f"正在朗读   {round(val_db, 1)} dB"
                    if float(round(val_db, 1)) > float(instance.read_today_data["max_sound"]):
                        instance.read_today_data["max_sound"] = float(round(val_db, 1))
                    write_count += 1
                    db_list.append(round(val_db, 3))
                    if write_count >= 10:
                        write_db_data(db_list=db_list, acount=getattr(instance, "current_acount"), date=datetime.datetime.now().strftime("%Y-%m-%d"))
                        write_count = 0
                        db_list = []
                    instance.read_today_data["left"] = max(0, float(instance.read_today_data["left"]) - time_delta)
                    instance.read_today_data["real_read_time"] = float(instance.read_today_data["real_read_time"]) + time_delta
                    should_update_stats = True

                elif get_state == "db-paused":
                    display_msg = f"停顿   {round(val_db, 1)} dB"
                    write_count += 1
                    db_list.append(round(val_db, 3))
                    if write_count >= 10:
                        write_db_data(db_list=db_list, acount=getattr(instance, "current_acount"), date=datetime.datetime.now().strftime("%Y-%m-%d"))
                        write_count = 0
                        db_list = []
                    instance.read_today_data["stop_total"] = float(instance.read_today_data["stop_total"]) + time_delta
                    should_update_stats = True

                elif get_state == "paused":
                    display_msg = "已暂停"
                    should_update_stats = True

                if should_update_stats:
                    instance.read_today_data["total"] = float(instance.read_today_data["total"]) + time_delta
                    if float(instance.read_today_data["total"]) > 0:
                        instance.read_today_data["efficiency"] = round(
                            float(instance.read_today_data["real_read_time"]) / float(instance.read_today_data["total"]), 2
                        )

                if instance.tts_read and getattr(instance, "tts_detection_enabled", True) and not should_stop_tts() and getattr(instance, "if_reading", True):
                    check_tts_conditions(
                        instance=instance,
                        tts_config=instance.tts_read,
                        current_db=val_db,
                        current_pause_duration=current_pause_duration,
                        left=instance.read_today_data["left"],
                        total_stop=instance.read_today_data["stop_total"],
                        total=instance.read_today_data["total"],
                        real_read_time=instance.read_today_data["real_read_time"],
                        max_db=instance.read_today_data["max_sound"],
                        efficiency=instance.read_today_data["efficiency"],
                    )

                update_payload = {"type": "update", "main_label_text": display_msg}
                if current_time - last_ui_update_time >= 0.1:
                    last_ui_update_time = current_time
                    update_payload["info_data"] = {
                        "left":          instance.read_today_data["left"],
                        "stop_total":    instance.read_today_data["stop_total"],
                        "real_read_time": instance.read_today_data["real_read_time"],
                        "total":         instance.read_today_data["total"],
                        "max_sound":     instance.read_today_data["max_sound"],
                        "efficiency":    instance.read_today_data["efficiency"],
                    }
                ui_queue.put(update_payload)

            if "end_sig" in data:
                instance.log_operation("收到结束信号", "准备写回日统计与合并音频")
                instance.tts_detection_enabled = False
                request_stop_all_tts()
                stop_speaking()
                instance.if_reading = False
                ui_queue.put({"type": "stop"})
                current_account = getattr(instance, "current_acount")
                get_date = datetime.datetime.now().strftime("%Y-%m-%d")
                write_data = {
                    "left":          int(instance.read_today_data["left"]),
                    "stop_total":    int(instance.read_today_data["stop_total"]),
                    "real_read_time": int(instance.read_today_data["real_read_time"]),
                    "total":         int(instance.read_today_data["total"]),
                    "max_sound":     float(instance.read_today_data["max_sound"]),
                    "efficiency":    float(instance.read_today_data["efficiency"]),
                }
                print("正在合并缓存...")
                month_str = "-".join(get_date.split("-")[0:2])
                with open(f"./data/{current_account}/{month_str}/{get_date}.json", "w", encoding="utf-8") as f:
                    json.dump(write_data, f)
                time.sleep(2)
                audio_dir = pathlib.Path(__file__).resolve().parent.parent.parent / "audio_chunks"
                if not audio_dir.exists():
                    list_chunks = []
                else:
                    list_chunks = sorted(os.listdir(str(audio_dir)))
                full_paths = [str(audio_dir / name) for name in list_chunks]
                merge_wav(full_paths, f"./details/{current_account}/{get_date}/recording.wav")
                instance.log_operation("朗读数据落盘完成", f"date={get_date}, chunks={len(list_chunks)}")
                try:
                    shutil.rmtree(str(audio_dir))
                except FileNotFoundError:
                    pass
                break

        except Exception as e:
            instance.log_fatal("数据线程异常", str(e))
            log_system("data_thread 崩溃", str(e))
            print(f"Error in data_thread: {e}")
            break

    try:
        instance.tts_detection_enabled = False
        request_stop_all_tts()
        stop_speaking()
    except Exception:
        pass
    instance.log_operation("数据线程退出", "data_thread loop ended")
