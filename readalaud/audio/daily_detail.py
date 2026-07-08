"""
daily_detail.py —— 获取指定日期的详细朗读数据（含音量图、同比昨日）。
"""
import json
import os
import time
from datetime import datetime, timedelta

from .chart_builder import save_volume_chart
from ..settings import get_setting


def _safe_mtime(path):
    try:
        return os.path.getmtime(path)
    except OSError:
        return 0.0


def fetch_for_daily_data(self, date_input, force_refresh=False):
    """
    获取指定日期的详细数据。

    Args:
        date_input (str | datetime.date): 查询日期
        force_refresh (bool): 是否强制刷新缓存

    Returns:
        dict: 当日详细数据
    """
    account = getattr(self, "current_acount", None)
    if not account:
        return {}

    if isinstance(date_input, str):
        try:
            target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            return {}
    elif isinstance(date_input, datetime):
        target_date = date_input.date()
    else:
        target_date = date_input

    date_str = target_date.strftime("%Y-%m-%d")
    month_str = target_date.strftime("%Y-%m")

    json_path = f"./data/{account}/{month_str}/{date_str}.json"
    details_dir = f"./details/{account}/{date_str}"
    db_csv_path = os.path.join(details_dir, "DB.csv")
    vol_chart_path = os.path.join(details_dir, "volume_chart.png")
    cache_path = os.path.join(details_dir, "daily_cache.json")

    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
            cache_time = float(cached.get("timestamp", 0) or 0)
            is_fresh = time.time() - cache_time < 300
            source_mtime = max(_safe_mtime(json_path), _safe_mtime(db_csv_path))
            cache_covers_sources = cache_time >= source_mtime
            db_has_data = os.path.exists(db_csv_path) and os.path.getsize(db_csv_path) > 0
            chart_path = cached.get("volume_chart_path") or ""
            chart_ok = (chart_path and os.path.exists(chart_path)) or not db_has_data
            if is_fresh and cache_covers_sources and chart_ok:
                return cached
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    if not os.path.exists(json_path):
        return {}

    result = {
        "date": date_str,
        "total_duration": 0,
        "pause_duration": 0,
        "efficiency": 0.0,
        "completion": "-",
        "max_volume": 0.0,
        "avg_volume": 0.0,
        "compare_yesterday": "--",
        "volume_chart_path": "",
        "goal": 0,
        "real_read_time": 0,
    }

    get_goal = int(get_setting("goal", 0) or 0)

    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        result["total_duration"] = int(data.get("total", 0))
        result["pause_duration"] = int(data.get("stop_total", 0))
        result["efficiency"] = float(data.get("efficiency", 0.0))
        real_read_time = int(data.get("real_read_time", 0) or 0)
        result["real_read_time"] = real_read_time
        result["goal"] = int(get_goal or 0)
        result["completion"] = f"{(real_read_time / get_goal) * 100:.1f}%" if get_goal > 0 else "None"
        result["max_volume"] = float(data.get("max_sound", 0.0))
    except Exception as e:
        print(f"Error reading daily json: {e}")
        return {}

    if os.path.exists(db_csv_path):
        try:
            with open(db_csv_path, "r") as f:
                content = f.read().replace("\n", ",")
            vol_data = [float(x) for x in content.split(",") if x.strip()]
            if vol_data:
                result["avg_volume"] = sum(vol_data) / len(vol_data)
                chart_missing = not os.path.exists(vol_chart_path)
                chart_stale = _safe_mtime(db_csv_path) > _safe_mtime(vol_chart_path)
                if chart_missing or chart_stale or force_refresh:
                    save_volume_chart(vol_data, vol_chart_path)
                result["volume_chart_path"] = vol_chart_path
        except Exception as e:
            print(f"Error processing volume data: {e}")

    try:
        yst_date = target_date - timedelta(days=1)
        yst_json = f"./data/{account}/{yst_date.strftime('%Y-%m')}/{yst_date.strftime('%Y-%m-%d')}.json"
        if os.path.exists(yst_json):
            with open(yst_json, "r") as f:
                yst_total = int(json.load(f).get("total", 0))
            if yst_total > 0:
                diff = result["total_duration"] - yst_total
                percent = (diff / yst_total) * 100
                sign = "+" if percent >= 0 else ""
                result["compare_yesterday"] = f"{sign}{percent:.1f}%"
            else:
                result["compare_yesterday"] = "+∞" if result["total_duration"] > 0 else "0%"
        else:
            result["compare_yesterday"] = "无记录"
    except Exception as e:
        print(f"Error calculating comparison: {e}")

    result["timestamp"] = time.time()
    try:
        os.makedirs(details_dir, exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(result, f, indent=4)
    except Exception as e:
        print(f"Cache save failed: {e}")

    return result
