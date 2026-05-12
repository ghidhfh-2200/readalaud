"""
dashboard.py —— 综合数据看板：总时长、连胜、热力图、趋势图等聚合统计。
"""
import json
import os
import time
import pandas as pd
from datetime import datetime

from .chart_builder import save_heatmap, save_trend_chart


# ── 连胜算法 ─────────────────────────────────────────────

def calculate_streaks(daily_dates):
    """
    根据日期列表计算当前/最长连续打卡天数。
    O(N log N) 时间复杂度（排序 + 一次遍历）。
    """
    if not daily_dates:
        return 0, 0

    sorted_dates = sorted(set(daily_dates))
    streaks = []
    current_run = 1
    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_run += 1
        else:
            streaks.append(current_run)
            current_run = 1
    streaks.append(current_run)
    max_streak = max(streaks)

    today = datetime.now().date()
    if (today - sorted_dates[-1]).days > 1:
        current_streak = 0
    else:
        current_streak = streaks[-1]
    return current_streak, max_streak


# ── 总时长统计 ────────────────────────────────────────────

def total_time_calculate(self):
    get_current_account = getattr(self, "current_acount")
    base_url = f"./data/{get_current_account}/"
    if not os.path.exists(base_url):
        return
    total_val = 0
    for month in os.listdir(base_url):
        month_path = os.path.join(base_url, month)
        if os.path.isdir(month_path):
            for day_file in os.listdir(month_path):
                file_path = os.path.join(month_path, day_file)
                if os.path.isfile(file_path):
                    try:
                        with open(file_path, "r") as f:
                            total_val += int(json.load(f).get("total", 0))
                    except Exception:
                        pass

    general_dir = f"./details/{get_current_account}"
    os.makedirs(general_dir, exist_ok=True)
    general_path = os.path.join(general_dir, "general.json")
    try:
        read_general = {}
        if os.path.exists(general_path):
            with open(general_path, "r") as f:
                read_general = json.load(f)
        read_general["total"] = total_val
        with open(general_path, "w") as f:
            json.dump(read_general, f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(general_path, "w") as f:
            json.dump({"total": total_val, "last_cal_time": None}, f)
    return total_val


# ── 综合看板刷新 ──────────────────────────────────────────

def refresh_dashboard_data(self, force_refresh=False):
    """
    综合数据看板刷新接口。
    具备缓存节流（120s），计算总时长/天数/均值/连胜并生成图表。
    """
    account = getattr(self, "current_acount", None)
    if not account:
        return {}

    details_dir = f"./details/{account}"
    general_path = os.path.join(details_dir, "general.json")
    trend_path = os.path.join(details_dir, "trend.png")
    os.makedirs(details_dir, exist_ok=True)

    current_ts = time.time()

    if not force_refresh and os.path.exists(general_path):
        try:
            with open(general_path, "r") as f:
                cached_data = json.load(f)
            last_time = cached_data.get("last_cal_time")
            cached_hm = cached_data.get("heatmap_paths", {})
            has_heatmaps = any(os.path.exists(p) for p in cached_hm.values())
            if last_time and (current_ts - last_time < 120) and has_heatmaps and os.path.exists(trend_path):
                cached_data["trend_path"] = trend_path
                return cached_data
        except (json.JSONDecodeError, OSError):
            pass

    base_url = f"./data/{account}/"
    if not os.path.exists(base_url):
        return {}

    total_time = 0
    total_efficiency_acc = 0.0
    valid_dates = []
    max_efficiency_val = 0.0
    max_efficiency_date = "----/--/--"
    max_duration_val = 0.0
    max_duration_date = "----/--/--"
    plot_data_list = []

    for month in [d for d in os.listdir(base_url) if os.path.isdir(os.path.join(base_url, d))]:
        month_path = os.path.join(base_url, month)
        for file in os.listdir(month_path):
            if not file.endswith(".json"):
                continue
            file_path = os.path.join(month_path, file)
            try:
                date_str = file.replace(".json", "")
                date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                with open(file_path, "r") as f:
                    day_data = json.load(f)
                duration = int(day_data.get("total", 0))
                efficiency = float(day_data.get("efficiency", 0))
                pause_time = int(day_data.get("stop_total", 0))
                if duration > 0:
                    total_time += duration
                    total_efficiency_acc += efficiency
                    valid_dates.append(date_obj)
                    if efficiency > max_efficiency_val:
                        max_efficiency_val = efficiency
                        max_efficiency_date = date_str
                    if duration > max_duration_val:
                        max_duration_val = duration
                        max_duration_date = date_str
                    plot_data_list.append({"date": pd.Timestamp(date_obj), "duration": duration, "efficiency": efficiency})
            except Exception:
                continue

    total_days = len(valid_dates)
    average_daily = total_time // total_days if total_days > 0 else 0
    average_efficiency = total_efficiency_acc / total_days if total_days > 0 else 0.0
    current_streak, max_streak = calculate_streaks(valid_dates)

    plot_df = pd.DataFrame(plot_data_list) if plot_data_list else pd.DataFrame(columns=["date", "duration", "efficiency"])
    heatmap_results = save_heatmap(plot_df, details_dir)
    save_trend_chart(plot_df, trend_path)

    result_data = {
        "total": total_time,
        "total_days": total_days,
        "average_daily": average_daily,
        "average_efficiency": round(average_efficiency, 2),
        "current_streak": current_streak,
        "max_streak": max_streak,
        "max_efficiency_val": max_efficiency_val,
        "max_efficiency_date": max_efficiency_date,
        "max_duration_val": max_duration_val,
        "max_duration_date": max_duration_date,
        "daily_records": [],
        "heatmap_years": sorted(heatmap_results.keys()),
        "heatmap_paths": {str(k): v for k, v in heatmap_results.items()},
        "trend_path": trend_path,
        "last_cal_time": current_ts,
    }

    with open(general_path, "w") as f:
        json.dump(result_data, f, indent=4)
    return result_data


# ── 月份/日记录辅助 ──────────────────────────────────────

def get_available_months(self):
    account = getattr(self, "current_acount", None)
    if not account:
        return []
    base_url = f"./data/{account}/"
    if not os.path.exists(base_url):
        return []
    months = []
    try:
        for item in os.listdir(base_url):
            if os.path.isdir(os.path.join(base_url, item)):
                try:
                    datetime.strptime(item, "%Y-%m")
                    months.append(item)
                except ValueError:
                    pass
    except Exception:
        pass
    return sorted(months, reverse=True)


def get_daily_records_by_month(self, month_str):
    if not month_str:
        return []
    account = getattr(self, "current_acount", None)
    if not account:
        return []
    data_dir = f"./data/{account}/{month_str}"
    if not os.path.exists(data_dir):
        return []
    records = []
    try:
        files = sorted([f for f in os.listdir(data_dir) if f.endswith(".json")], reverse=True)
        for file in files:
            try:
                with open(os.path.join(data_dir, file), "r", encoding="utf-8") as f:
                    d = json.load(f)
                records.append((
                    file.replace(".json", ""),
                    int(d.get("total", 0)),
                    int(d.get("stop_total", 0)),
                    f"{float(d.get('efficiency', 0)):.2f}",
                ))
            except Exception:
                continue
    except Exception:
        pass
    return records
