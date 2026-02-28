"""
data_io.py —— 朗读数据（JSON 日统计 + CSV dB 日志）的读写封装。
"""
import csv
import json
import os
import datetime


def write_db_data(acount, db, date):
    """将 dB 列表追加写入当日的 DB.csv。"""
    try:
        with open(f"./details/{acount}/{date}/DB.csv", "a", newline="") as f:
            csv.writer(f).writerow(db)
    except FileNotFoundError:
        _ensure_detail_dirs(acount, date)
        write_db_data(acount=acount, db=db, date=date)
    except Exception as e:
        raise e


def _ensure_detail_dirs(acount, date):
    for path in [
        "./details",
        f"./details/{acount}",
        f"./details/{acount}/{date}",
    ]:
        if not os.path.exists(path):
            os.mkdir(path)


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
