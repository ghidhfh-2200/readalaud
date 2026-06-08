"""
data_io.py —— 朗读数据（JSON 日统计 + CSV dB 日志）的读写封装。
"""
import csv
import json
import os
import datetime

from ..settings import get_settings_cache


def _read_day_json(acount, date_obj):
    month_str = date_obj.strftime("%Y-%m")
    day_str = date_obj.strftime("%Y-%m-%d")
    data_path = f"./data/{acount}/{month_str}/{day_str}.json"
    if not os.path.exists(data_path):
        return None
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def write_db_data(acount, db=None, date=None, db_list=None):
    """将 dB 列表追加写入当日的 DB.csv。

    兼容历史调用：支持 db=... 和 db_list=... 两种参数名。
    """
    if db is None:
        db = db_list
    if db is None or date is None:
        return
    try:
        with open(f"./details/{acount}/{date}/DB.csv", "a", newline="") as f:
            csv.writer(f).writerow(db)
    except FileNotFoundError:
        _ensure_detail_dirs(acount, date)
        write_db_data(acount=acount, db=db, date=date)
    except Exception as e:
        raise e


def _ensure_detail_dirs(acount, date):
    os.makedirs(f"./details/{acount}/{date}", exist_ok=True)


def load_today_data(current_acount, load_settings, show_debug=None):
    """
    加载今日 JSON 数据；不存在则初始化。
    返回 read_today_data 字典。
    """
    from .session import log
    get_date = datetime.datetime.now().strftime("%Y-%m-%d")
    month_str = "-".join(get_date.split("-")[0:2])
    data_path = f"./data/{current_acount}/{month_str}/{get_date}.json"
    count = 0
    while True:
        try:
            with open(data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            if count >= 3:
                return None
            count += 1
            try:
                os.mkdir(f"./data/{current_acount}/{month_str}")
            except Exception:
                pass
            write_data = {
                "left": load_settings["goal"],
                "stop_total": 0,
                "real_read_time": 0,
                "total": 0,
                "max_sound": 0,
                "efficiency": 0.00,
            }
            with open(data_path, "w", encoding="utf-8") as f:
                json.dump(write_data, f)


def load_today_reading_status(current_acount, load_settings=None):
    """读取当日/昨日朗读状态，供侧边栏展示使用。

    返回一个字典，包含：是否朗读、目标达成度、总时长、效率、与昨日总时长差值等信息。
    """
    if not current_acount:
        return {}

    if load_settings is None:
        load_settings = get_settings_cache()

    today = datetime.datetime.now().date()
    today_data = _read_day_json(current_acount, today) or {}
    yesterday_data = _read_day_json(current_acount, today - datetime.timedelta(days=1)) or {}

    goal = int(load_settings.get("goal", 0) or 0)
    total_duration = int(today_data.get("total", 0) or 0)
    real_read_time = int(today_data.get("real_read_time", 0) or 0)
    efficiency = float(today_data.get("efficiency", 0.0) or 0.0)
    compare_yesterday = None
    if yesterday_data:
        compare_yesterday = total_duration - int(yesterday_data.get("total", 0) or 0)

    completion_ratio = None
    if goal > 0:
        completion_ratio = real_read_time / goal

    return {
        "goal": goal,
        "is_reading": False,
        "has_today_data": bool(today_data),
        "total_duration": total_duration,
        "real_read_time": real_read_time,
        "efficiency": efficiency,
        "completion_ratio": completion_ratio,
        "compare_yesterday": compare_yesterday,
    }
