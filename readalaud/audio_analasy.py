import os
import json
import time
import wave
import pandas as pd
from datetime import datetime, timedelta, date
import matplotlib
import matplotlib.pyplot as plt
import calmap
import numpy as np
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib import cm as _mpl_cm

def bind_audio_analasy_api(instance):
    instance.stop_day_audio = lambda reset=False: stop_day_audio(instance, reset)
    instance.play_day_audio = lambda: play_day_audio(instance)
    instance.pause_day_audio = lambda: pause_day_audio(instance)
    instance.seek_day_audio = lambda: seek_day_audio(instance)
    instance.init_audio_state = lambda: init_audio_state(instance)

def init_audio_state(self):
    self._day_audio_state = {
        "path": "",
        "duration": 0.0,
        "offset": 0.0,
        "playing": False,
        "paused": False,
        "play_obj": None,
        "play_start": None,
        "frame_rate": 0,
        "channels": 0,
        "sampwidth": 0,
        "raw": b"",
        "after_id": None,
        "programmatic": False,
    }

def _format_time(seconds):
    seconds = max(0, int(seconds))
    return f"{seconds // 60:02d}:{seconds % 60:02d}"

def _set_audio_status(self, text="", color="#dc3545"):
    if hasattr(self, "day_audio_status"):
        self.day_audio_status.config(text=text, fg=color)

def get_audio_duration(path):
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            fr = wf.getframerate()
        return frames / fr if fr else 0.0
    except Exception:
        return 0.0

def _load_audio_meta(path):
    try:
        with wave.open(path, "rb") as wf:
            frames = wf.getnframes()
            fr = wf.getframerate()
            ch = wf.getnchannels()
            sw = wf.getsampwidth()
            raw = wf.readframes(frames)
        duration = frames / fr if fr else 0.0
        return duration, fr, ch, sw, raw
    except Exception as e:
        print(f"Error loading audio: {e}")
        return 0.0, 0, 0, 0, b""

def stop_day_audio(self, reset=False):
    st = getattr(self, "_day_audio_state", {})
    try:
        if st.get("play_obj") is not None:
            st["play_obj"].stop()
    except Exception:
        pass
    st["playing"] = False
    st["paused"] = False
    st["play_obj"] = None
    st["play_start"] = None
    if st.get("after_id"):
        try:
            self.day_detail_container.after_cancel(st["after_id"])
        except Exception:
            pass
        st["after_id"] = None
    if reset:
        st["offset"] = 0.0
        st["programmatic"] = True
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.set(0)
        st["programmatic"] = False

def _update_progress_tick(self):
    st = getattr(self, "_day_audio_state", {})
    if not st.get("playing"):
        return
    elapsed = time.time() - (st.get("play_start") or time.time())
    current = st.get("offset", 0.0) + max(0.0, elapsed)
    if current >= st.get("duration", 0.0) or (st.get("play_obj") and not st["play_obj"].is_playing()):
        stop_day_audio(self, reset=True)
        _set_audio_status(self, "播放完成", "#28a745")
        return
    st["programmatic"] = True
    if hasattr(self, "day_audio_scale"):
        self.day_audio_scale.set(current)
    st["programmatic"] = False
    _set_audio_status(self, f"{_format_time(current)} / {_format_time(st.get('duration', 0))}", "#6c757d")
    st["after_id"] = self.day_detail_container.after(200, lambda: _update_progress_tick(self))

def _play_from_offset(self):
    st = getattr(self, "_day_audio_state", {})
    if not st.get("raw"):
        return False
    try:
        import simpleaudio as sa
    except Exception:
        _set_audio_status(self, "缺少播放库，无法播放", "#dc3545")
        return False

    frame_bytes = st["channels"] * st["sampwidth"]
    start_frame = int(st.get("offset", 0.0) * st["frame_rate"]) if st["frame_rate"] else 0
    start_byte = start_frame * frame_bytes
    audio_bytes = st["raw"][start_byte:] if start_byte < len(st["raw"]) else b""
    if not audio_bytes:
        return False

    st["play_obj"] = sa.play_buffer(audio_bytes, st["channels"], st["sampwidth"], st["frame_rate"])
    st["play_start"] = time.time()
    st["playing"] = True
    st["paused"] = False
    _update_progress_tick(self)
    return True

def play_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None: return
    
    if not st.get("path") or not os.path.exists(st["path"]):
        _set_audio_status(self, "无音频", "#dc3545")
        st["programmatic"] = True
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.set(0)
        st["programmatic"] = False
        return

    if not st.get("raw"):
        duration, fr, ch, sw, raw = _load_audio_meta(st["path"])
        st.update({"duration": duration, "frame_rate": fr, "channels": ch, "sampwidth": sw, "raw": raw})
        if hasattr(self, "day_audio_scale"):
            self.day_audio_scale.config(from_=0, to=max(1, duration))

    if st.get("playing"):
        return

    ok = _play_from_offset(self)
    if not ok:
        _set_audio_status(self, "无法播放音频", "#dc3545")

def pause_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None or not st.get("playing"):
        return
    elapsed = time.time() - (st.get("play_start") or time.time())
    st["offset"] = min(st.get("duration", 0.0), st.get("offset", 0.0) + max(0.0, elapsed))
    stop_day_audio(self, reset=False)
    st["paused"] = True
    st["programmatic"] = True
    if hasattr(self, "day_audio_scale"):
        self.day_audio_scale.set(st["offset"])
    st["programmatic"] = False
    _set_audio_status(self, f"已暂停 { _format_time(st['offset']) }", "#6c757d")

def seek_day_audio(self):
    st = getattr(self, "_day_audio_state", None)
    if st is None or st.get("programmatic"):
        return
    try:
        new_val = float(self.day_audio_scale.get())
    except Exception:
        return
    st["offset"] = max(0.0, min(new_val, st.get("duration", 0.0)))
    _set_audio_status(self, f"{_format_time(st['offset'])} / {_format_time(st.get('duration', 0))}", "#6c757d")
    if st.get("playing"):
        stop_day_audio(self, reset=False)
        _play_from_offset(self)

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

def _save_heatmap(df, save_path):
    try:
        # Data Prep
        if df is None or df.empty:
            return False
            
        df_plot = df.copy()
        if not isinstance(df_plot.index, pd.DatetimeIndex):
            if 'date' in df_plot.columns:
                df_plot.index = pd.to_datetime(df_plot['date'])
            else:
                return False
                
        years = df_plot.index.year.unique()
        if len(years) == 0:
            return False
            
        current_year = datetime.now().year
        target_year = current_year if current_year in years else years.max()
        data = df_plot['duration'] / 60.0 # Minutes

        # Plotting
        # Use a non-interactive backend for file generation if needed, 
        # but here we just create a figure and save.
        fig = plt.figure(figsize=(10, 3), dpi=100) 
        ax = fig.add_subplot(111)
        
        calmap.yearplot(data, year=target_year, ax=ax, cmap='YlGn', 
                        linewidth=1, fillcolor='#dddddd', linecolor='#ffffff')
        ax.set_title(f"{target_year}年 朗读热力图 (颜色深浅表示时长)", 
                     fontproperties="Microsoft YaHei", fontsize=10)
        
        plt.tight_layout()
        fig.savefig(save_path, bbox_inches='tight', dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving heatmap: {e}")
        return False

def _save_trend_chart(df, save_path):
    try:
        if df is None or df.empty:
            return False
            
        df_plot = df.copy()
        if not isinstance(df_plot.index, pd.DatetimeIndex):
            if 'date' in df_plot.columns:
                df_plot.index = pd.to_datetime(df_plot['date'])
        
        df_plot.sort_index(inplace=True)
        is_truncated = False
        if len(df_plot) > 30:
            df_plot = df_plot.tail(30)
            is_truncated = True
        
        fig = plt.figure(figsize=(10, 4), dpi=100)
        ax1 = fig.add_subplot(111)
        
        x = range(len(df_plot))
        durations = df_plot['duration'] / 60.0
        
        ax1.bar(x, durations, color='#007acc', alpha=0.6, label='时长(分钟)', width=0.6)
        ax1.set_ylabel('时长 (分钟)', fontproperties="Microsoft YaHei")
        
        ax2 = ax1.twinx()
        efficiencies = df_plot['efficiency'] * 100
        ax2.plot(x, efficiencies, color='#ff9800', marker='o', markersize=4, linewidth=2, label='效率(%)')
        ax2.set_ylabel('效率 (%)', fontproperties="Microsoft YaHei")
        ax2.set_ylim(0, 110)
        
        ax1.set_xticks(x)
        # Simplify Date Labels
        ax1.set_xticklabels(df_plot.index.strftime('%d'), rotation=0, fontsize=8) 
        ax1.set_xlabel(f"日期 ({df_plot.index[0].strftime('%Y.%m')} - {df_plot.index[-1].strftime('%m')}) [仅显示日]", 
                       fontproperties="Microsoft YaHei")

        title_text = "近期朗读趋势 (时长 & 效率)"
        if is_truncated:
            title_text += " - 近30次"
        ax1.set_title(title_text, fontproperties="Microsoft YaHei", fontsize=10)
        
        plt.tight_layout()
        fig.savefig(save_path, bbox_inches='tight', dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving trend chart: {e}")
        return False

def refresh_dashboard_data(self, force_refresh=False):
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
    heatmap_path = os.path.join(details_dir, "heatmap.png")
    trend_path = os.path.join(details_dir, "trend.png")
    os.makedirs(details_dir, exist_ok=True)
    
    # --- 1. 节流机制检查 (Throttling Check) ---
    current_ts = time.time()
    
    if not force_refresh and os.path.exists(general_path):
        try:
            with open(general_path, "r") as f:
                cached_data = json.load(f)
                last_time = cached_data.get("last_cal_time")
                
                # Check for validity: < 120s AND images exist
                if (last_time and (current_ts - last_time < 120) and 
                    os.path.exists(heatmap_path) and os.path.exists(trend_path)):
                    print("Load cached dashboard data & charts.")
                    cached_data['heatmap_path'] = heatmap_path
                    cached_data['trend_path'] = trend_path
                    return cached_data
        except (json.JSONDecodeError, OSError):
            pass 

    # --- 2. 核心数据计算 (Calculation) ---
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
    
    daily_records = []
    plot_data_list = []

    # 遍历所有月份文件夹
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
                        pause_time = int(day_data.get('stop_total', 0))
                        
                        # 有效朗读时长才计入统计
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
                            
                            # (date, duration, pause, progress/efficiency)
                            daily_records.append((date_str, duration, pause_time, f"{efficiency:.2f}"))
                            plot_data_list.append({'date': pd.Timestamp(date_obj), 'duration': duration, 'efficiency': efficiency})
                except Exception:
                    continue

    # 聚合指标
    total_days = len(valid_dates)
    average_daily = total_time // total_days if total_days > 0 else 0
    average_efficiency = total_efficiency_acc / total_days if total_days > 0 else 0.0
    current_streak, max_streak = _calculate_streaks_logic(valid_dates)
    
    # 构建 Plot Data DataFrame
    if plot_data_list:
        plot_df = pd.DataFrame(plot_data_list)
    else:
        plot_df = pd.DataFrame(columns=['date', 'duration', 'efficiency'])

    # --- 3. 生成并保存图表 (Save Charts) ---
    _save_heatmap(plot_df, heatmap_path)
    _save_trend_chart(plot_df, trend_path)

    # 构建结果字典
    result_data = {
        "total": total_time,            # 总时长 (秒)
        "total_days": total_days,       # 打卡总天数
        "average_daily": average_daily, # 日均时长 (秒)
        "average_efficiency": round(average_efficiency, 2), # 平均效率
        "current_streak": current_streak, # 当前连续天数
        "max_streak": max_streak,       # 历史最长连续天数
        "max_efficiency_val": max_efficiency_val,
        "max_efficiency_date": max_efficiency_date,
        "max_duration_val": max_duration_val,
        "max_duration_date": max_duration_date,
        "daily_records": sorted(daily_records, key=lambda x: x[0], reverse=True),
        # "plot_df": plot_df, # Dataframe NOT returned to GUI anymore for drawing
        "heatmap_path": heatmap_path,
        "trend_path": trend_path,
        "last_cal_time": current_ts     # 本次计算时间戳
    }

    # --- 4. 写入缓存 (Cache Write, excluding specific objects) ---
    cache_dict = result_data.copy()
    # Remove dynamic runtime objects if any, keep paths
    with open(general_path, "w") as f:
        json.dump(cache_dict, f, indent=4)

    return result_data

def _save_volume_chart(data, save_path):
    try:
        if not data:
            return False
            
        fig = plt.figure(figsize=(8, 2), dpi=100)
        ax = fig.add_subplot(111)
        
        # Plot volume data
        ax.plot(data, color='#28a745', linewidth=1, alpha=0.8)
        ax.fill_between(range(len(data)), data, color='#28a745', alpha=0.1)
        
        # Style
        ax.set_title("音量变化趋势 (dB)", fontproperties="Microsoft YaHei", fontsize=10)
        ax.set_ylabel("Volume", fontsize=8)
        ax.set_xticks([]) # Hide time ticks
        
        # Remove borders
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)

        plt.tight_layout()
        fig.savefig(save_path, bbox_inches='tight', dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving volume chart: {e}")
        return False

def fetch_for_daily_data(self, date_input, force_refresh=False):
    """
    [Detailed Data] 获取指定日期的详细数据。
    
    Args:
        date_input (str or datetime.date): 查询日期, "YYYY-MM-DD" 或 date对象
        force_refresh (bool): 是否强制刷新缓存 (Default: False)

    Returns:
        dict: 包含当日详细数据的字典
    """
    account = getattr(self, "current_acount", None)
    if not account:
        return {}

    # 1. 解析日期
    if isinstance(date_input, str):
        try:
            target_date = datetime.strptime(date_input, "%Y-%m-%d").date()
        except ValueError:
            return {} # Invalid format
    elif isinstance(date_input, datetime):
        target_date = date_input.date()
    else:
        target_date = date_input

    date_str = target_date.strftime("%Y-%m-%d")
    month_str = target_date.strftime("%Y-%m")
    
    # 2. 定义路径
    import os
    json_path = f"./data/{account}/{month_str}/{date_str}.json"
    details_dir = f"./details/{account}/{date_str}"
    db_csv_path = os.path.join(details_dir, "DB.csv")
    vol_chart_path = os.path.join(details_dir, "volume_chart.png")
    cache_path = os.path.join(details_dir, "daily_cache.json")
    config_path = f"./data/{account}/settings.json"
    
    # --- Cache Check ---
    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cached = json.load(f)
                # Check 1: Time threshold (5 mins)
                # Check 2: If chart is expected, does it exist?
                is_fresh = (time.time() - cached.get('timestamp', 0) < 300)
                chart_ok = True
                if cached.get('volume_chart_path') and not os.path.exists(cached['volume_chart_path']):
                    chart_ok = False
                
                if is_fresh and chart_ok:
                    print(f"Load cached daily detail for {date_str}")
                    return cached
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    # --- Calculation ---
    if not os.path.exists(json_path):
        return {}
    if not os.path.exists(config_path):
        return {}
    
    # 初始默认数据
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
    }

    try:
        with open(config_path, "r") as f:
            read_config = json.load(f)
            get_goal = read_config.get("goal", 0)
    except json.JSONDecodeError:
        print("Error reading config json: fail to decode the JSON")
        return {}
    # 3. 读取 JSON 基础数据
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
            result["total_duration"] = int(data.get("total", 0))
            result["pause_duration"] = int(data.get("stop_total", 0))
            result["efficiency"] = float(data.get("efficiency", 0.0))
            result["completion"] = f"{(data.get('real_read_time', 0) / get_goal)*100:.1f}%"
            result["max_volume"] = float(data.get("max_sound", 0.0))
    except json.JSONDecodeError:
        print("Error reading daily json: fail to decode the data file")
        return {}
    except Exception as e:
        print(f"Error reading daily json: {e}")
        return {}

    # 4. 处理音量数据 & 生成图表
    vol_data = []
    if os.path.exists(db_csv_path):
        try:
            with open(db_csv_path, 'r') as f:
                content = f.read()
                content = content.replace('\n', ',')
                parts = content.split(',')
                vol_data = [float(x) for x in parts if x.strip()]
            
            if vol_data:
                result["avg_volume"] = sum(vol_data) / len(vol_data)
                
                # Check/Generate Chart
                if not os.path.exists(vol_chart_path) or force_refresh:
                     _save_volume_chart(vol_data, vol_chart_path)
                result["volume_chart_path"] = vol_chart_path
        except Exception as e:
            print(f"Error processing volume data: {e}")

    # 5. 计算同比昨日
    try:
        yst_date = target_date - timedelta(days=1)
        yst_str = yst_date.strftime("%Y-%m-%d")
        yst_month = yst_date.strftime("%Y-%m")
        yst_json_path = f"./data/{account}/{yst_month}/{yst_str}.json"
        
        if os.path.exists(yst_json_path):
            with open(yst_json_path, 'r') as f:
                yst_data = json.load(f)
                yst_total = int(yst_data.get("total", 0))
                
                if yst_total > 0:
                    diff = result["total_duration"] - yst_total
                    percent = (diff / yst_total) * 100
                    sign = "+" if percent >= 0 else ""
                    result["compare_yesterday"] = f"{sign}{percent:.1f}%"
                else:
                    if result["total_duration"] > 0:
                         result["compare_yesterday"] = "+∞" 
                    else:
                         result["compare_yesterday"] = "0%"
        else:
            result["compare_yesterday"] = "无记录"
    except Exception as e:
        print(f"Error calculating comparison: {e}")
    
    # 6. Save Cache
    result['timestamp'] = time.time()
    try:
        import os
        os.makedirs(details_dir, exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(result, f, indent=4)
    except Exception as e:
        print(f"Cache save failed: {e}")

    return result


# ══════════════════════════════════════════════════════════
#  音频分析 – 后端引擎 (Thread-Safe)
# ══════════════════════════════════════════════════════════

ANALYSIS_ITEMS = {
    "vad":         "语音活动检测 (VAD)",
    "rms":         "短时能量 (RMS)",
    "ltas":        "长时平均能量 (10s 切片)",
    "zcr":         "过零率变化",
    "pitch":       "基频变化 (F0)",
    "snr":         "信噪比 (SNR)",
    "mfcc":        "梅尔倒谱 (MFCC)",
    "crest":       "峰值因子 (Crest Factor)",
    "entropy":     "频谱熵 (Spectral Entropy)",
    "spectrogram": "语谱图 (Spectrogram)",
}


# ─── 工具函数 ───

def _load_wav_as_array(path):
    """读取 WAV 文件并返回 (mono float64 归一化采样, 采样率)。"""
    with wave.open(path, 'rb') as wf:
        ch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sw, np.int16)
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if dtype == np.uint8:
        samples = (samples - 128) / 128.0
    else:
        samples /= 2 ** (sw * 8 - 1)
    if ch > 1:
        samples = samples.reshape(-1, ch).mean(axis=1)
    return samples, sr


def _make_fig(w=10, h=3):
    """创建线程安全的 matplotlib Figure（不使用 pyplot）。"""
    fig = Figure(figsize=(w, h), dpi=100, facecolor='white')
    FigureCanvas(fig)
    return fig


def _save_fig(fig, path):
    fig.savefig(path, bbox_inches='tight', dpi=100, facecolor='white')


def _frame_signal(samples, frame_len, hop_len):
    """将信号切分为重叠帧。短于一帧的信号会被补零。"""
    n = len(samples)
    if n < frame_len:
        samples = np.pad(samples, (0, frame_len - n))
        n = frame_len
    num_frames = 1 + (n - frame_len) // hop_len
    indices = (
        np.arange(frame_len)[None, :] + np.arange(num_frames)[:, None] * hop_len
    )
    return samples[indices]


# ─── 各项分析实现 ───

def _analyze_vad(samples, sr, output_path):
    """VAD：基于短时能量的语音活动检测。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    energy = np.sum(frames ** 2, axis=1)

    threshold = np.mean(energy) * 0.1 if np.mean(energy) > 0 else 1e-10
    is_speech = energy > threshold
    times = np.arange(len(energy)) * hop_len / sr

    fig = _make_fig(10, 2.5)
    ax = fig.add_subplot(111)
    e_norm = energy / energy.max() if energy.max() > 0 else energy
    ax.fill_between(times, is_speech.astype(float), alpha=0.4, color='#28a745', label='语音段')
    ax.plot(times, e_norm, color='#007acc', linewidth=0.5, alpha=0.6, label='能量')
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('活动', fontproperties="Microsoft YaHei")
    ax.set_title('语音活动检测 (VAD)', fontproperties="Microsoft YaHei", fontsize=10)
    ax.legend(prop={"family": "Microsoft YaHei", "size": 8})
    ax.set_ylim(-0.05, 1.15)
    fig.tight_layout()
    _save_fig(fig, output_path)

    speech_ratio = np.sum(is_speech) / len(is_speech) if len(is_speech) > 0 else 0
    return {"语音占比": f"{speech_ratio:.1%}"}


def _analyze_rms(samples, sr, output_path):
    """短时 RMS 能量。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    times = np.arange(len(rms)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, rms, color='#ff6f00', linewidth=0.8)
    ax.fill_between(times, rms, alpha=0.2, color='#ff6f00')
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('RMS', fontproperties="Microsoft YaHei")
    ax.set_title('短时能量 (RMS)', fontproperties="Microsoft YaHei", fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"均值RMS": f"{np.mean(rms):.4f}", "最大RMS": f"{np.max(rms):.4f}"}


def _analyze_ltas(samples, sr, output_path):
    """长时平均能量谱 (LTAS)，每 10 秒切片一次。"""
    slice_len = 10 * sr
    n_slices = max(1, len(samples) // slice_len)
    nfft = 2048

    fig = _make_fig(10, 4)
    ax = fig.add_subplot(111)
    colors = _mpl_cm.viridis(np.linspace(0, 1, n_slices))

    for i in range(n_slices):
        start = i * slice_len
        end = min(start + slice_len, len(samples))
        segment = samples[start:end]
        if len(segment) < nfft:
            segment = np.pad(segment, (0, nfft - len(segment)))

        window = np.hanning(nfft)
        n_sub = max(1, len(segment) // nfft)
        spectrum = np.zeros(nfft // 2 + 1)
        for j in range(n_sub):
            chunk = segment[j * nfft: (j + 1) * nfft]
            if len(chunk) < nfft:
                chunk = np.pad(chunk, (0, nfft - len(chunk)))
            spectrum += np.abs(np.fft.rfft(chunk * window))
        spectrum /= n_sub
        spectrum_db = 20 * np.log10(spectrum + 1e-10)
        freqs = np.fft.rfftfreq(nfft, 1.0 / sr)

        label = f"{i*10}-{min((i+1)*10, len(samples)/sr):.0f}s"
        ax.plot(freqs, spectrum_db, color=colors[i], linewidth=0.8, alpha=0.7, label=label)

    ax.set_xlabel('频率 (Hz)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('幅度 (dB)', fontproperties="Microsoft YaHei")
    ax.set_title('长时平均能量谱 (LTAS, 10s 切片)', fontproperties="Microsoft YaHei", fontsize=10)
    if n_slices <= 12:
        ax.legend(prop={"family": "Microsoft YaHei", "size": 7}, loc='upper right', ncol=2)
    ax.set_xlim(0, sr / 2)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"切片数": n_slices}


def _analyze_zcr(samples, sr, output_path):
    """过零率随时间变化。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    zcr = np.sum(np.abs(np.diff(np.sign(frames), axis=1)), axis=1) / (2 * frame_len)
    times = np.arange(len(zcr)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, zcr, color='#e91e63', linewidth=0.7)
    ax.fill_between(times, zcr, alpha=0.15, color='#e91e63')
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('ZCR', fontproperties="Microsoft YaHei")
    ax.set_title('过零率变化', fontproperties="Microsoft YaHei", fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"平均ZCR": f"{np.mean(zcr):.4f}"}


def _analyze_pitch(samples, sr, output_path):
    """基频 (F0) 估计 – FFT 自相关法。"""
    frame_len = int(0.040 * sr)
    hop_len = int(0.020 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)

    f0_min, f0_max = 80, 400
    lag_min = max(1, int(sr / f0_max))
    lag_max = min(frame_len - 1, int(sr / f0_min))
    fft_size = 2 ** int(np.ceil(np.log2(2 * frame_len)))

    pitches = np.zeros(len(frames))
    for i, frame in enumerate(frames):
        frame = frame - np.mean(frame)
        if np.max(np.abs(frame)) < 1e-6:
            continue
        fft_f = np.fft.rfft(frame, n=fft_size)
        acf = np.fft.irfft(fft_f * np.conj(fft_f))[:frame_len]
        if acf[0] > 0:
            acf /= acf[0]
        region = acf[lag_min:lag_max + 1]
        if len(region) == 0:
            continue
        peak_idx = np.argmax(region) + lag_min
        if acf[peak_idx] > 0.25:
            pitches[i] = sr / peak_idx

    times = np.arange(len(pitches)) * hop_len / sr
    pitch_masked = np.where(pitches > 0, pitches, np.nan)

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, pitch_masked, color='#9c27b0', linewidth=0.8, marker='.', markersize=1)
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('频率 (Hz)', fontproperties="Microsoft YaHei")
    ax.set_title('基频变化 (F0)', fontproperties="Microsoft YaHei", fontsize=10)
    ax.set_ylim(f0_min - 20, f0_max + 50)
    fig.tight_layout()
    _save_fig(fig, output_path)

    valid = pitches[pitches > 0]
    mean_f0 = f"{np.mean(valid):.1f} Hz" if len(valid) > 0 else "N/A"
    return {"平均F0": mean_f0}


def _analyze_snr(samples, sr, output_path):
    """信噪比估计：以最低 10% 能量帧为噪声基底。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    energy = np.sum(frames ** 2, axis=1)

    sorted_energy = np.sort(energy)
    n_noise = max(1, len(sorted_energy) // 10)
    noise_floor = np.mean(sorted_energy[:n_noise])
    signal_power = np.mean(energy)
    snr_global = 10 * np.log10(signal_power / (noise_floor + 1e-10))

    snr_frames = 10 * np.log10(energy / (noise_floor + 1e-10))
    snr_frames = np.clip(snr_frames, -20, 60)
    times = np.arange(len(snr_frames)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, snr_frames, color='#00bcd4', linewidth=0.7)
    ax.axhline(y=snr_global, color='#ff5722', linestyle='--', linewidth=1,
               label=f'全局 SNR: {snr_global:.1f} dB')
    ax.fill_between(times, snr_frames, alpha=0.1, color='#00bcd4')
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('SNR (dB)', fontproperties="Microsoft YaHei")
    ax.set_title('信噪比 (SNR)', fontproperties="Microsoft YaHei", fontsize=10)
    ax.legend(prop={"family": "Microsoft YaHei", "size": 8})
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"全局SNR": f"{snr_global:.1f} dB"}


def _analyze_mfcc(samples, sr, output_path):
    """梅尔频率倒谱系数 (MFCC)。"""
    n_mfcc, n_mels, nfft = 13, 40, 2048
    frame_len = int(0.025 * sr)
    hop_len = int(0.020 * sr)

    frames = _frame_signal(samples, frame_len, hop_len)
    window = np.hanning(frame_len)

    # 补零至 nfft
    if frame_len < nfft:
        frames = np.pad(frames, ((0, 0), (0, nfft - frame_len)))
        window = np.pad(window, (0, nfft - frame_len))

    power = np.abs(np.fft.rfft(frames * window, n=nfft)) ** 2

    # Mel 滤波器组
    mel_min = 2595 * np.log10(1 + 0 / 700)
    mel_max = 2595 * np.log10(1 + sr / 2 / 700)
    mel_pts = np.linspace(mel_min, mel_max, n_mels + 2)
    hz_pts = 700 * (10 ** (mel_pts / 2595) - 1)
    bins = np.floor((nfft + 1) * hz_pts / sr).astype(int)

    fbank = np.zeros((n_mels, nfft // 2 + 1))
    for m in range(n_mels):
        for k in range(bins[m], bins[m + 1]):
            if bins[m + 1] > bins[m]:
                fbank[m, k] = (k - bins[m]) / (bins[m + 1] - bins[m])
        for k in range(bins[m + 1], bins[m + 2]):
            if bins[m + 2] > bins[m + 1]:
                fbank[m, k] = (bins[m + 2] - k) / (bins[m + 2] - bins[m + 1])

    mel_spec = np.log(power @ fbank.T + 1e-10)

    # Type-II DCT
    dct_mat = np.zeros((n_mfcc, n_mels))
    for i in range(n_mfcc):
        for j in range(n_mels):
            dct_mat[i, j] = np.cos(np.pi * i * (j + 0.5) / n_mels)
    mfccs = mel_spec @ dct_mat.T  # (n_frames, n_mfcc)

    times = np.arange(mfccs.shape[0]) * hop_len / sr

    fig = _make_fig(10, 4)
    ax = fig.add_subplot(111)
    im = ax.imshow(
        mfccs.T, aspect='auto', origin='lower', cmap='coolwarm',
        extent=[times[0], times[-1], 0, n_mfcc],
    )
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('MFCC 系数', fontproperties="Microsoft YaHei")
    ax.set_title('梅尔倒谱系数 (MFCC)', fontproperties="Microsoft YaHei", fontsize=10)
    fig.colorbar(im, ax=ax, label='幅值')
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {}


def _analyze_crest(samples, sr, output_path):
    """峰值因子 (Crest Factor)。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)

    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    peak = np.max(np.abs(frames), axis=1)
    crest_db = 20 * np.log10(peak / (rms + 1e-10) + 1e-10)
    times = np.arange(len(crest_db)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, crest_db, color='#795548', linewidth=0.7)
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('峰值因子 (dB)', fontproperties="Microsoft YaHei")
    ax.set_title('峰值因子 (Crest Factor)', fontproperties="Microsoft YaHei", fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"平均峰值因子": f"{np.mean(crest_db):.1f} dB"}


def _analyze_entropy(samples, sr, output_path):
    """频谱熵。"""
    frame_len = int(0.025 * sr)
    hop_len = int(0.020 * sr)
    nfft = 1024
    frames = _frame_signal(samples, frame_len, hop_len)
    window = np.hanning(frame_len)

    if frame_len < nfft:
        frames = np.pad(frames, ((0, 0), (0, nfft - frame_len)))
        window = np.pad(window, (0, nfft - frame_len))

    power = np.abs(np.fft.rfft(frames * window, n=nfft)) ** 2
    total = np.sum(power, axis=1, keepdims=True) + 1e-10
    prob = power / total
    entropy = -np.sum(prob * np.log2(prob + 1e-10), axis=1)

    max_entropy = np.log2(power.shape[1])
    entropy_norm = entropy / max_entropy
    times = np.arange(len(entropy_norm)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, entropy_norm, color='#4caf50', linewidth=0.7)
    ax.fill_between(times, entropy_norm, alpha=0.15, color='#4caf50')
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('归一化频谱熵', fontproperties="Microsoft YaHei")
    ax.set_title('频谱熵 (Spectral Entropy)', fontproperties="Microsoft YaHei", fontsize=10)
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"平均熵": f"{np.mean(entropy_norm):.3f}"}


def _analyze_spectrogram(samples, sr, output_path):
    """语谱图 (Spectrogram)。"""
    nfft = 2048
    frame_len = int(0.025 * sr)
    hop_len = int(0.020 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    window = np.hanning(frame_len)

    if frame_len < nfft:
        frames = np.pad(frames, ((0, 0), (0, nfft - frame_len)))
        window = np.pad(window, (0, nfft - frame_len))

    mag_db = 20 * np.log10(np.abs(np.fft.rfft(frames * window, n=nfft)) + 1e-10)
    times = np.arange(mag_db.shape[0]) * hop_len / sr
    freqs = np.fft.rfftfreq(nfft, 1.0 / sr)

    fig = _make_fig(10, 4)
    ax = fig.add_subplot(111)
    im = ax.imshow(
        mag_db.T, aspect='auto', origin='lower', cmap='inferno',
        extent=[times[0], times[-1], freqs[0], freqs[-1]],
    )
    ax.set_xlabel('时间 (s)', fontproperties="Microsoft YaHei")
    ax.set_ylabel('频率 (Hz)', fontproperties="Microsoft YaHei")
    ax.set_title('语谱图 (Spectrogram)', fontproperties="Microsoft YaHei", fontsize=10)
    fig.colorbar(im, ax=ax, label='幅度 (dB)')
    ax.set_ylim(0, min(8000, sr / 2))
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {}


# ─── 分析注册表 & 调度器 ───

_ANALYSIS_FUNCS = {
    "vad":         _analyze_vad,
    "rms":         _analyze_rms,
    "ltas":        _analyze_ltas,
    "zcr":         _analyze_zcr,
    "pitch":       _analyze_pitch,
    "snr":         _analyze_snr,
    "mfcc":        _analyze_mfcc,
    "crest":       _analyze_crest,
    "entropy":     _analyze_entropy,
    "spectrogram": _analyze_spectrogram,
}


def run_selected_analyses(audio_path, selected_keys, output_dir, on_item_done=None):
    """
    [Main Interface] 执行选定的音频分析项目。

    Args:
        audio_path:     WAV 文件路径
        selected_keys:  选中的分析项 key 列表
        output_dir:     图表输出目录
        on_item_done:   可选回调 callback(key, result_dict)，每完成一项调用一次

    Returns:
        dict: {key: {"title", "path", "extra"} | {"title", "error"}}
    """
    os.makedirs(output_dir, exist_ok=True)
    samples, sr = _load_wav_as_array(audio_path)

    results = {}
    for key in selected_keys:
        func = _ANALYSIS_FUNCS.get(key)
        if not func:
            result = {"title": ANALYSIS_ITEMS.get(key, key), "error": "未知分析项"}
            results[key] = result
            if on_item_done:
                on_item_done(key, result)
            continue

        out_path = os.path.join(output_dir, f"analysis_{key}.png")
        try:
            extra = func(samples, sr, out_path)
            result = {"title": ANALYSIS_ITEMS[key], "path": out_path, "extra": extra or {}}
        except Exception as e:
            import traceback
            traceback.print_exc()
            result = {"title": ANALYSIS_ITEMS.get(key, key), "error": str(e)}

        results[key] = result
        if on_item_done:
            on_item_done(key, result)

    return results