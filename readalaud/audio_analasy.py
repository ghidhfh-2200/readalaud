import os
import json
import time
from datetime import datetime

def bind_audio_analasy_api(instance):
    pass

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
                    with open(file_path, "r") as f:
                        total_val += int(json.load(f).get('total', 0))
    
    general_dir = f"./details/{get_current_account}"
    os.makedirs(general_dir, exist_ok=True)
    general_path = os.path.join(general_dir, "general.json")
    try:
        read_general = {}
        if os.path.exists(general_path):
            with open(general_path, "r") as f:
                read_general = json.load(f)
        read_general['total'] = total_val
        with open(general_path, "w") as f:
            json.dump(read_general, f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(general_path, "w") as f:
            json.dump({"total": total_val, "last_cal_time": None}, f)
    return sum

def _calculate_streaks_logic(daily_dates):
    """
    [Core Algorithm] 根据日期列表计算连续打卡数据。
    
    Performance Note:
    时间复杂度为 O(N log N) 由于排序，去重和遍历为 O(N)。
    对于个人这种规模的数据（数千天），Python原生的列表和日期操作极快，耗时在微秒级，
    无需使用 C/C++ 扩展。若数据量达到百万级，建议使用 Numpy 或 Pandas。

    Args:
        daily_dates (list): datetime.date 对象的列表

    Returns:
        tuple: (current_streak, max_streak)
    """
    if not daily_dates:
        return 0, 0
    
    # 去重并排序
    sorted_dates = sorted(list(set(daily_dates)))
    
    max_streak = 0
    current_run = 0
    streaks = []

    if sorted_dates:
        current_run = 1
        for i in range(1, len(sorted_dates)):
            # 判断是否连续（相差1天）
            delta = sorted_dates[i] - sorted_dates[i-1]
            if delta.days == 1:
                current_run += 1
            else:
                streaks.append(current_run)
                current_run = 1
        streaks.append(current_run)
        max_streak = max(streaks)

    # 计算当前连胜：必须包含今天或昨天才算连续
    today = datetime.now().date()
    last_record_date = sorted_dates[-1]
    
    # 如果最后一次打卡距离今天超过1天（即昨天也没打卡），则当前连胜中断归零
    if (today - last_record_date).days > 1:
        current_streak = 0
    else:
        # 当前连胜即为最后一段连续记录的长度
        current_streak = streaks[-1]

    return current_streak, max_streak

def refresh_dashboard_data(self):
    """
    [Main Interface] 综合数据看板刷新接口。
    
    功能描述：
    1. 性能优先：具备缓存节流机制（Throttling），调用频率限制为每分钟一次。
    2. 全量统计：计算 总时长、总天数、日均时长、平均效率、当前连胜、最长连胜。
    3. 数据持久化：结果存入 details/{account}/general.json。

    前端 UI 调用此方法即可获取最新数据字典。
    """
    # 获取当前账户
    account = getattr(self, "current_acount", None)
    if not account:
        return {}
    
    # 定义路径
    details_dir = f"./details/{account}"
    general_path = os.path.join(details_dir, "general.json")
    os.makedirs(details_dir, exist_ok=True)
    
    # --- 1. 节流机制检查 (Throttling Check) ---
    current_ts = time.time()
    cached_data = {}
    
    if os.path.exists(general_path):
        try:
            with open(general_path, "r") as f:
                cached_data = json.load(f)
                last_time = cached_data.get("last_cal_time")
                # 如果距离上次计算不足 60 秒，直接返回缓存数据，避免频繁 IO
                if last_time and (current_ts - last_time < 60):
                    return cached_data
        except (json.JSONDecodeError, OSError):
            pass # 若文件损坏则重新计算

    # --- 2. 核心数据计算 (Calculation) ---
    base_url = f"./data/{account}/"
    if not os.path.exists(base_url):
        return {}

    total_time = 0
    total_efficiency_acc = 0.0
    valid_dates = []

    # 遍历所有月份文件夹
    # IO Bound 操作，Python 效率完全足够。
    month_dirs = [d for d in os.listdir(base_url) if os.path.isdir(os.path.join(base_url, d))]
    
    for month in month_dirs:
        month_path = os.path.join(base_url, month)
        for file in os.listdir(month_path):
            if file.endswith(".json"):
                file_path = os.path.join(month_path, file)
                try:
                    # 从文件名解析日期
                    date_str = file.replace(".json", "")
                    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
                    
                    with open(file_path, "r") as f:
                        day_data = json.load(f)
                        duration = int(day_data.get('total', 0))
                        efficiency = float(day_data.get('efficiency', 0))
                        
                        # 有效朗读时长才计入统计
                        if duration > 0:
                            print(duration)
                            total_time += duration
                            total_efficiency_acc += efficiency
                            valid_dates.append(date_obj)
                except Exception:
                    continue

    # 聚合指标
    total_days = len(valid_dates)
    average_daily = total_time // total_days if total_days > 0 else 0
    average_efficiency = total_efficiency_acc / total_days if total_days > 0 else 0.0
    current_streak, max_streak = _calculate_streaks_logic(valid_dates)

    # 构建结果字典
    result_data = {
        "total": total_time,            # 总时长 (秒)
        "total_days": total_days,       # 打卡总天数
        "average_daily": average_daily, # 日均时长 (秒)
        "average_efficiency": round(average_efficiency, 2), # 平均效率
        "current_streak": current_streak, # 当前连续天数
        "max_streak": max_streak,       # 历史最长连续天数
        "last_cal_time": current_ts     # 本次计算时间戳
    }

    # --- 3. 写入缓存 (Cache Write) ---
    with open(general_path, "w") as f:
        json.dump(result_data, f, indent=4)

    return result_data