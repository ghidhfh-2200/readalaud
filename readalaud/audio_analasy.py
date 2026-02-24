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

matplotlib.use("Agg")

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
    return total_val

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

def _save_heatmap(df, save_dir):
    """为每个有数据的年份（含当前年）生成独立热力图，返回 {year: path} 字典。"""
    if df is None or df.empty:
        return {}

    df_plot = df.copy()
    if not isinstance(df_plot.index, pd.DatetimeIndex):
        if 'date' in df_plot.columns:
            df_plot.index = pd.to_datetime(df_plot['date'])
        else:
            return {}

    years = set(df_plot.index.year.unique())
    if not years:
        return {}

    # 始终包含当前年份，即使当年还没有数据也显示空白热力图
    current_year = datetime.now().year
    years.add(current_year)
    years = sorted(years)

    data = pd.Series(df_plot['duration'].values / 60.0, index=df_plot.index)

    heatmap_paths = {}
    for year in years:
        save_path = os.path.join(save_dir, f"heatmap_{year}.png")
        full_year_idx = pd.date_range(start=f"{year}-01-01",
                                       end=f"{year}-12-31", freq='D')
        year_data = data.reindex(full_year_idx, fill_value=0)
        year_data.index.name = 'date'

        fig = plt.figure(figsize=(10, 3), dpi=100)
        ax = fig.add_subplot(111)
        calmap.yearplot(year_data, year=year, ax=ax, cmap='YlGn',
                        linewidth=1, fillcolor='#dddddd', linecolor='#ffffff')
        ax.set_title(f"{year}年 朗读热力图 (颜色深浅表示时长)",
                     fontproperties="Microsoft YaHei", fontsize=10)

        plt.tight_layout()
        fig.savefig(save_path, bbox_inches='tight', dpi=100)
        plt.close(fig)
        heatmap_paths[year] = save_path

    return heatmap_paths

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
    trend_path = os.path.join(details_dir, "trend.png")
    os.makedirs(details_dir, exist_ok=True)
    
    # --- 1. 节流机制检查 (Throttling Check) ---
    current_ts = time.time()
    
    if not force_refresh and os.path.exists(general_path):
        try:
            with open(general_path, "r") as f:
                cached_data = json.load(f)
                last_time = cached_data.get("last_cal_time")
                
                # Check for validity: < 120s AND charts exist
                cached_hm = cached_data.get("heatmap_paths", {})
                has_heatmaps = any(os.path.exists(p) for p in cached_hm.values())
                if (last_time and (current_ts - last_time < 120) and
                    has_heatmaps and os.path.exists(trend_path)):
                    print("Load cached dashboard data & charts.")
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
    heatmap_results = _save_heatmap(plot_df, details_dir)
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
        "daily_records": [], # 列表过大导致内存问题，改用 get_daily_records_by_month 分页获取
        "heatmap_years": sorted(heatmap_results.keys()),
        "heatmap_paths": {str(k): v for k, v in heatmap_results.items()},
        "trend_path": trend_path,
        "last_cal_time": current_ts     # 本次计算时间戳
    }

    # --- 4. 写入缓存 (Cache Write, excluding specific objects) ---
    cache_dict = result_data.copy()
    # Remove dynamic runtime objects if any, keep paths
    with open(general_path, "w") as f:
        json.dump(cache_dict, f, indent=4)

    return result_data

def get_available_months(self):
    """
    [API] 获取所有有记录的月份 (降序)
    """
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
    """
    [API] 获取指定月份的每日数据记录 (按日期降序)
    """
    if not month_str: return []
    account = getattr(self, "current_acount", None)
    if not account: return []
    data_dir = f"./data/{account}/{month_str}"
    if not os.path.exists(data_dir): return []
    
    records = []
    try:
        files = [f for f in os.listdir(data_dir) if f.endswith(".json")]
        files.sort(reverse=True)
        for file in files:
            try:
                with open(os.path.join(data_dir, file), "r", encoding='utf-8') as f:
                    d = json.load(f)
                    records.append((file.replace(".json", ""), int(d.get('total',0)), int(d.get('stop_total',0)), f"{float(d.get('efficiency',0)):.2f}"))
            except: continue
    except: pass
    return records

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

# ──────────────────────────────────────────────────────────
#  各指标通俗说明（面向普通用户）
#
#  每项格式：
#    "title"  —— 标题（同 ANALYSIS_ITEMS）
#    "brief"  —— 一句话简介，显示在图表标题下方
#    "detail" —— 详细说明，解释图表含义及如何判断好坏
#    "extra_tips" —— 额外解读提示（Extra 数据字段的含义）
# ──────────────────────────────────────────────────────────
ANALYSIS_DESCRIPTIONS: dict[str, dict] = {

    # ─── VAD ───────────────────────────────────────────────
    "vad": {
        "title":  "语音活动检测 (VAD)",
        "brief":  "检测录音中哪些时刻在说话、哪些是停顿或噪音。",
        "detail": (
            "图表横轴为时间，绿色填充区域代表检测到的「语音段」，"
            "蓝色折线为归一化能量变化。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 语音占比偏低（< 50%）：停顿过多，可能朗读不够流畅，或录音中有较长的空白段。\n"
            "  • 语音占比偏高（> 90%）：几乎全程在说话，连贯度良好，但要注意是否缺少必要的断句停顿。\n"
            "  • 理想范围：60%–85%。适度的停顿有助于听众理解，也体现了良好的断句节奏。\n"
            "\n"
            "💡 提示：如果图中语音段不连续、频繁中断，建议检查是否存在口误、卡顿或录音噪音触发了误判。"
        ),
        "extra_tips": {
            "语音占比": "实际说话时长 ÷ 总录音时长。越高说明停顿越少、朗读越连贯。",
        },
    },

    # ─── RMS ───────────────────────────────────────────────
    "rms": {
        "title":  "短时能量 (RMS)",
        "brief":  "衡量录音音量（响度）随时间的变化趋势。",
        "detail": (
            "RMS（均方根）反映的是声音的「平均响度」。图中橙色折线越高，说明那一时刻的声音越响亮。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 曲线平稳：音量控制良好，前后段响度均衡。\n"
            "  • 曲线起伏剧烈：音量忽大忽小，可能存在突然大喊或声音衰弱的问题。\n"
            "  • 曲线整体偏低：录音音量不足，建议靠近麦克风或调高录音增益。\n"
            "  • 曲线末段下降明显：朗读后期疲劳，气息支撑不足。\n"
            "\n"
            "💡 提示：朗读全程 RMS 均值建议保持在 0.05–0.3 之间（已归一化）。"
        ),
        "extra_tips": {
            "均值RMS": "整段录音的平均响度。值越大说明整体音量越响亮。",
            "最大RMS": "录音中出现的最大瞬时响度，可用于判断是否有爆音。",
        },
    },

    # ─── LTAS ──────────────────────────────────────────────
    "ltas": {
        "title":  "长时平均能量谱 (LTAS)",
        "brief":  "将录音按每10秒分段，对比各段的频率分布是否一致。",
        "detail": (
            "LTAS（Long-Term Average Spectrum）将录音切分为若干 10 秒的片段，"
            "每条彩色曲线代表一个片段的能量在各频率上的分布。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 各条曲线高度重合：音色稳定，前后发音风格一致，是优质朗读的标志。\n"
            "  • 曲线明显分离：说明不同时间段音色差异较大，可能存在声音疲劳或情绪起伏过大。\n"
            "  • 低频能量（< 500 Hz）远高于高频：低音浑浊，可能麦克风放置过近或有噪音干扰。\n"
            "  • 高频段（> 4000 Hz）完全平坦：高频细节缺失，录音设备或环境可能存在高频截止。\n"
            "\n"
            "💡 提示：正常人声主要能量集中在 300–3400 Hz，图中该区域应有明显的能量隆起。"
        ),
        "extra_tips": {
            "切片数": "录音被均分为多少个 10 秒片段，片段越多说明录音时长越长。",
        },
    },

    # ─── ZCR ───────────────────────────────────────────────
    "zcr": {
        "title":  "过零率变化 (ZCR)",
        "brief":  "反映朗读中清辅音（如 s、sh、z）与元音的分布比例。",
        "detail": (
            "过零率（Zero Crossing Rate）表示信号每帧内穿越零点的次数比例。"
            "高过零率区域通常对应清辅音（摩擦音如 s/sh/f），低过零率对应元音（a/o/e）。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • ZCR 曲线均匀波动：说话节奏自然，元音辅音分布合理。\n"
            "  • ZCR 长时间偏低：可能以元音为主，语音较为流畅但辅音清晰度有待提升。\n"
            "  • ZCR 出现密集的尖峰：对应清辅音密集段，发音清晰有力。\n"
            "  • 静默段 ZCR 偏高：可能存在高频背景噪音（如风扇声、电流声）。\n"
            "\n"
            "💡 提示：ZCR 本身不直接反映朗读好坏，主要用于辅助判断噪音和发音清晰度。"
        ),
        "extra_tips": {
            "平均ZCR": "全程的平均过零率。正常人声一般在 0.05–0.20 之间。",
        },
    },

    # ─── Pitch / F0 ────────────────────────────────────────
    "pitch": {
        "title":  "基频变化 (F0)",
        "brief":  "记录朗读时声调（音调高低）的变化，反映抑扬顿挫程度。",
        "detail": (
            "基频（Fundamental Frequency，F0）即声带振动的频率，决定了音调的高低。"
            "图中每个点代表检测到的瞬时音调，空白处为静默或声音太弱无法检测。\n"
            "\n"
            "📌 参考范围：\n"
            "  • 成年男性：80–180 Hz（平均约 120 Hz）\n"
            "  • 成年女性：160–300 Hz（平均约 220 Hz）\n"
            "  • 儿童：250–400 Hz\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • F0 曲线起伏丰富：朗读有抑扬顿挫，情感表达自然，听感生动。\n"
            "  • F0 曲线几乎水平（单调）：语调平淡，缺乏感情，听感枯燥。\n"
            "  • F0 频繁跳变到极高或极低：可能有破音、嗓音不稳或检测误差。\n"
            "  • 句末 F0 下降：符合普通话陈述句语调规律，是正确断句的标志。\n"
            "\n"
            "💡 提示：F0 的变化幅度（音域跨度）越大，朗读的感染力通常越强。"
        ),
        "extra_tips": {
            "平均F0": "全程有声段的平均音调。可用于粗略判断说话者的音域中心。",
        },
    },

    # ─── SNR ───────────────────────────────────────────────
    "snr": {
        "title":  "信噪比 (SNR)",
        "brief":  "量化录音中人声与背景噪音的比例，数值越高录音越干净。",
        "detail": (
            "信噪比（Signal-to-Noise Ratio）以 dB（分贝）为单位，"
            "正值表示信号比噪音强，负值表示噪音掩盖了信号。"
            "图中蓝色折线为逐帧 SNR，红色虚线为全局平均 SNR。\n"
            "\n"
            "📌 评分参考：\n"
            "  • ≥ 30 dB：优秀，录音非常干净，专业播音水准。\n"
            "  • 20–30 dB：良好，日常朗读的正常水平。\n"
            "  • 10–20 dB：一般，背景噪音有些明显，建议改善录音环境。\n"
            "  •  < 10 dB：较差，噪音严重，严重影响收听体验。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • SNR 曲线平稳且偏高：录音环境安静，全程音质一致。\n"
            "  • SNR 在语音段高、静默段低：属于正常现象，说明检测准确。\n"
            "  • SNR 全程偏低：录音环境嘈杂，建议关闭窗户、远离噪音源，或使用降噪麦克风。\n"
            "\n"
            "💡 提示：本工具使用「最低 10% 能量帧」估算噪底，适合稳态噪音场景。"
        ),
        "extra_tips": {
            "全局SNR": "全段录音的综合信噪比。这是评估录音环境质量最直接的单一指标。",
        },
    },

    # ─── MFCC ──────────────────────────────────────────────
    "mfcc": {
        "title":  "梅尔倒谱系数 (MFCC)",
        "brief":  "模拟人耳感知，提取发音音色特征，是语音识别最核心的特征。",
        "detail": (
            "MFCC（Mel-Frequency Cepstral Coefficients）通过模拟人耳对频率的非线性感知，"
            "将声音压缩为 13 个特征系数的时序矩阵（颜色图）。\n"
            "\n"
            "📌 图表解读：\n"
            "  • 横轴：时间进度；纵轴：MFCC 系数编号（0–12）\n"
            "  • 颜色：暖色（红）= 正值（能量集中），冷色（蓝）= 负值（能量分散）\n"
            "  • 第 0 行（MFCC₀）：主要反映整体能量，类似 RMS。\n"
            "  • 第 1–3 行：反映声音的粗粒度音色（声道共鸣特征）。\n"
            "  • 第 4–12 行：反映细粒度的音色变化（发音方式的细节）。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 颜色块分布均匀、过渡平滑：发音稳定，音色一致。\n"
            "  • 局部出现突变的颜色块：对应特定时刻音色的突变，可能是口误、破音或情绪切换。\n"
            "  • 整体颜色偏蓝（数值偏低）：能量不足，说话声音较弱。\n"
            "\n"
            "💡 提示：MFCC 对普通用户较为专业，重点关注整体颜色是否均匀，有无明显异常区域即可。"
        ),
        "extra_tips": {},
    },

    # ─── Crest Factor ──────────────────────────────────────
    "crest": {
        "title":  "峰值因子 (Crest Factor)",
        "brief":  "衡量声音的动态范围，反映朗读是否有爆破音或声音过于压缩。",
        "detail": (
            "峰值因子 = 瞬时峰值 ÷ RMS 均方根（以 dB 表示）。"
            "它描述了声音中「瞬间最大值」相对于「平均值」的比例，反映音频的动态特性。\n"
            "\n"
            "📌 评分参考：\n"
            "  • 10–20 dB：正常人声的典型范围，动态自然。\n"
            "  •  > 25 dB：存在明显的爆破音（爆破辅音 p/b/t/d 用力过猛）或突发噪音。\n"
            "  •  < 6 dB：动态范围极小，声音过于「压缩」，可能听感沉闷、缺乏活力。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 曲线平稳在 10–20 dB：发音力度均匀，没有爆破。\n"
            "  • 出现尖峰（> 25 dB）：对应特定时刻的爆破音或破音，建议注意「爆破辅音」的气流控制。\n"
            "  • 整体偏低（< 8 dB）：朗读缺乏轻重缓急，建议加强重音与停顿的对比。\n"
            "\n"
            "💡 提示：专业播音中常用防喷罩和压限器来控制峰值因子，保持在合理范围。"
        ),
        "extra_tips": {
            "平均峰值因子": "全段平均动态范围。正常朗读建议保持在 10–20 dB。",
        },
    },

    # ─── Spectral Entropy ──────────────────────────────────
    "entropy": {
        "title":  "频谱熵 (Spectral Entropy)",
        "brief":  "衡量频谱能量的「混乱程度」，可用于区分清晰语音与噪音。",
        "detail": (
            "频谱熵（Spectral Entropy）描述频谱能量分布的随机程度（已归一化到 0–1）。\n"
            "  • 接近 0：能量高度集中在少数频率（如纯音调、清晰元音）\n"
            "  • 接近 1：能量均匀分散在所有频率（如白噪声、摩擦辅音）\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 语音段熵值约 0.5–0.8：属于正常人声范围，频谱结构清晰。\n"
            "  • 语音段熵值持续 > 0.9：语音接近噪音，可能发音含混、漏气声过多，或存在背景噪音。\n"
            "  • 静默段熵值 > 0.85：背景噪音较为均匀（如风声、电流声），应改善录音环境。\n"
            "  • 句尾辅音段熵值升高：属正常现象（辅音频谱本就较为分散）。\n"
            "\n"
            "💡 提示：频谱熵结合 SNR 使用效果更佳——SNR 低而熵值高，通常是背景噪音问题；"
            "SNR 正常而熵值高，可能是发音清晰度问题。"
        ),
        "extra_tips": {
            "平均熵": "全程平均频谱熵（0–1）。理想朗读的有声段均值一般在 0.5–0.75。",
        },
    },

    # ─── Spectrogram ───────────────────────────────────────
    "spectrogram": {
        "title":  "语谱图 (Spectrogram)",
        "brief":  "最直观的语音可视化：同时展示时间、频率、能量三维信息。",
        "detail": (
            "语谱图以「时间×频率」二维颜色图的形式展示录音的全部频率信息。\n"
            "  • 横轴：时间（秒）\n"
            "  • 纵轴：频率（Hz），0 在下方，高频在上方\n"
            "  • 颜色：越亮（橙/白）表示该时刻该频率的能量越强，越暗（黑）表示能量越弱\n"
            "\n"
            "📌 图中常见特征解读：\n"
            "  • 水平亮纹（宽带横条）：元音（a/o/e 等），能量集中且持续。\n"
            "  • 竖向亮纹（瞬态竖条）：爆破辅音（b/p/d/t/g/k），能量短暂且宽频。\n"
            "  • 高频斜纹（斜向条纹）：摩擦辅音（s/sh/f/h），能量分布在高频段。\n"
            "  • 全频短暂空白：停顿或换气。\n"
            "  • 低频持续亮带（< 300 Hz）：房间低频噪音或麦克风震动干扰。\n"
            "\n"
            "📌 如何判断朗读质量：\n"
            "  • 元音段颜色饱和、纹路清晰：发音饱满，共鸣良好。\n"
            "  • 辅音段可见清晰的宽频竖纹：爆破音清晰有力。\n"
            "  • 高频段（> 4000 Hz）一片漆黑：高频泛音不足，声音可能偏沉闷，缺乏亮度。\n"
            "  • 低频段始终有明显噪声带：环境噪声较大，建议降噪处理。\n"
            "\n"
            "💡 提示：语谱图信息最为丰富，建议配合其他指标综合分析。"
        ),
        "extra_tips": {},
    },
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
    """
    语音活动检测 (VAD — Voice Activity Detection)
    ─────────────────────────────────────────────
    算法：基于短时能量阈值法。
      1. 将音频切分为 25ms 帧（步长 10ms）
      2. 计算每帧的短时能量
      3. 以全局平均能量的 10% 作为语音/静默分界阈值
      4. 能量高于阈值的帧标记为「语音段」

    输出指标：
      - 语音占比：有效语音帧数 / 总帧数，越高说明朗读越连贯

    图表说明：
      - 绿色填充区域 = 检测到的语音段
      - 蓝色折线 = 归一化能量曲线
    """
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
    """
    短时能量 (RMS — Root Mean Square)
    ────────────────────────────────────
    算法：将音频切分为 25ms 帧（步长 10ms），对每帧计算均方根值。
      RMS = sqrt( mean(x²) )，其中 x 为帧内采样点

    输出指标：
      - 均值RMS：全程平均响度，反映整体音量水平
      - 最大RMS：峰值响度，用于检测是否有爆音

    图表说明：
      - 橙色折线 = RMS 随时间变化（已归一化到 0–1）
      - 曲线越平稳说明音量控制越好
    """
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
    """
    长时平均能量谱 (LTAS — Long-Term Average Spectrum)
    ─────────────────────────────────────────────────────
    算法：
      1. 将录音切分为若干 10 秒片段
      2. 对每个片段再细分为 2048 点短帧，加 Hanning 窗后做 FFT
      3. 对片段内所有帧的频谱幅度取平均，转换为 dB 表示
      4. 以不同颜色绘制各片段的平均频谱曲线（颜色按时间顺序排列）

    输出指标：
      - 切片数：录音被分为多少个 10 秒片段

    图表说明：
      - 每条彩色曲线代表一个 10 秒片段的频率分布
      - 曲线越重合，说明前后音色越一致
      - 正常人声主要能量集中在 300–3400 Hz
    """
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
    """
    过零率变化 (ZCR — Zero Crossing Rate)
    ────────────────────────────────────────
    算法：将音频切分为 25ms 帧（步长 10ms），统计每帧内信号穿越零点的次数。
      ZCR = count( sign(x[n]) ≠ sign(x[n-1]) ) / (2 × frame_len)

    物理含义：
      - 高 ZCR（> 0.15）：对应清辅音（摩擦音 s/sh/f/z）或背景高频噪声
      - 低 ZCR（< 0.05）：对应元音（a/o/e）或静默段

    输出指标：
      - 平均ZCR：全程平均过零率，正常人声约 0.05–0.20

    图表说明：
      - 粉红色折线 = 过零率随时间变化
      - 尖峰对应清辅音密集区域
    """
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
    """
    基频变化 (F0 — Fundamental Frequency / Pitch)
    ──────────────────────────────────────────────
    算法：FFT 自相关法（ACF via FFT）
      1. 将音频切分为 40ms 帧（步长 20ms）
      2. 对每帧做去均值处理后，利用 FFT 快速计算自相关函数（ACF）
      3. 在 80–400 Hz 对应的滞后范围内寻找 ACF 峰值
      4. 峰值相关系数 > 0.25 时判定为有声段，否则标记为 0（无音调）

    搜索范围：80–400 Hz（覆盖成人男女及儿童人声的全部音域）

    输出指标：
      - 平均F0：有声段的平均基频
        参考：男声约 100–150 Hz，女声约 180–250 Hz

    图表说明：
      - 紫色散点 = 逐帧基频估计值
      - 空白处 = 静默段或声音太弱（无法检测音调）
      - 曲线起伏丰富 → 抑扬顿挫明显，感情饱满
    """
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
    """
    信噪比 (SNR — Signal-to-Noise Ratio)
    ──────────────────────────────────────
    算法：基于噪底估计法（Noise Floor Estimation）
      1. 将音频切分为 25ms 帧（步长 10ms），计算每帧能量
      2. 取能量最低的 10% 帧作为「噪声样本」，计算其平均能量（噪底）
      3. 逐帧 SNR = 10 × log10(帧能量 / 噪底)，限幅在 -20~60 dB
      4. 全局 SNR = 10 × log10(全局平均能量 / 噪底)

    适用场景：稳态背景噪声（如风扇声、空调声、电流声）
    注意：本算法假设噪音功率相对稳定，突发噪音的估计可能不准确。

    输出指标：
      - 全局SNR：综合信噪比
        ≥ 30 dB = 优秀 | 20–30 dB = 良好 | 10–20 dB = 一般 | < 10 dB = 较差

    图表说明：
      - 蓝色折线 = 逐帧信噪比
      - 红色虚线 = 全局平均 SNR
    """
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
    """
    梅尔频率倒谱系数 (MFCC — Mel-Frequency Cepstral Coefficients)
    ──────────────────────────────────────────────────────────────
    算法：手动实现（不依赖 librosa/sklearn）
      1. 将音频切分为 25ms 帧（步长 20ms），加 Hanning 窗
      2. 对每帧做 FFT，计算功率谱
      3. 构建 40 个 Mel 尺度三角滤波器，映射到 Mel 频率
      4. 对 Mel 能量取 log，再做 Type-II DCT，保留前 13 个系数

    参数：n_mfcc=13, n_mels=40, FFT 点数=2048

    物理含义：
      - MFCC₀（第0行）：帧能量，类似 RMS
      - MFCC₁–₃（第1-3行）：声道共鸣特征（音色粗轮廓）
      - MFCC₄–₁₂（第4-12行）：发音细节特征

    图表说明：
      - 热图：横轴=时间，纵轴=系数编号，颜色=系数值
      - 暖色（红）= 正值，冷色（蓝）= 负值
      - 颜色均匀 = 音色稳定；局部突变 = 口误/破音
    """
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
    """
    峰值因子 (Crest Factor)
    ────────────────────────
    算法：
      1. 将音频切分为 25ms 帧（步长 10ms）
      2. 计算每帧的 RMS（均方根）和峰值（绝对值最大值）
      3. 峰值因子 = 20 × log10(峰值 / RMS)，单位 dB

    物理含义：
      峰值因子反映声音的「动态范围」，即瞬间最强音比平均音响了多少。
      - 正常人声：10–20 dB
      - 过高（> 25 dB）：爆破音、破音，气流控制不足
      - 过低（< 6 dB）：动态压缩，声音沉闷缺乏活力

    输出指标：
      - 平均峰值因子：全程平均动态范围，建议 10–20 dB

    图表说明：
      - 棕色折线 = 逐帧峰值因子（dB）
      - 尖峰 = 爆破音或突发噪音的位置
    """
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
    """
    频谱熵 (Spectral Entropy)
    ──────────────────────────
    算法：
      1. 将音频切分为 25ms 帧（步长 20ms），加 Hanning 窗，做 1024 点 FFT
      2. 将功率谱归一化为概率分布：P(f) = X(f)² / Σ X(f)²
      3. 计算 Shannon 熵：H = -Σ P(f) × log₂ P(f)
      4. 除以 log₂(N) 归一化到 0–1

    物理含义（已归一化）：
      - 接近 0：能量集中在少数频率（纯音、清晰元音）
      - 接近 1：能量均匀分散（白噪声、摩擦辅音）
      - 正常有声段：0.5–0.8
      - 静默/噪音段：0.8–0.95

    输出指标：
      - 平均熵：全程平均频谱熵，理想有声段约 0.5–0.75

    图表说明：
      - 绿色折线 = 归一化频谱熵随时间变化
      - 语音段与静默段的熵值差异 → 语音清晰度的间接指标
    """
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
    """
    语谱图 (Spectrogram)
    ──────────────────────
    算法：短时傅里叶变换（STFT）
      1. 将音频切分为 25ms 帧（步长 20ms），加 Hanning 窗
      2. 对每帧做 2048 点 FFT，取幅度谱
      3. 转换为 dB：20 × log10(|X(f,t)|)
      4. 以热图形式展示（显示范围限制在 0–8000 Hz）

    图表解读：
      - 横轴：时间（秒）
      - 纵轴：频率（Hz），0 在下，高频在上
      - 颜色（inferno 配色）：越亮（橙/白）= 能量越强，越暗（黑）= 能量越弱

    典型模式：
      ┌──────────────────────────────────────────────┐
      │ 宽频横纹（持续亮带）  → 元音（a/o/e/i/u）     │
      │ 宽频竖纹（瞬态）     → 爆破辅音（b/p/d/t）    │
      │ 高频斜纹/噪声带      → 摩擦辅音（s/sh/f/h）   │
      │ 全频空白（黑色区域） → 停顿/换气              │
      │ 低频持续亮带(<300Hz) → 环境低频噪声            │
      └──────────────────────────────────────────────┘
    """
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