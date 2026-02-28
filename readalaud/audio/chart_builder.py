"""
chart_builder.py —— 热力图、趋势图、音量图的生成与保存。
"""
import os
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import calmap
from matplotlib import cm as _mpl_cm

matplotlib.use("Agg")


def save_heatmap(df, save_dir):
    """为每个有数据的年份（含当前年）生成独立热力图，返回 {year: path} 字典。"""
    from datetime import datetime
    if df is None or df.empty:
        return {}

    df_plot = df.copy()
    if not isinstance(df_plot.index, pd.DatetimeIndex):
        if "date" in df_plot.columns:
            df_plot.index = pd.to_datetime(df_plot["date"])
        else:
            return {}

    years = set(df_plot.index.year.unique())
    current_year = datetime.now().year
    years.add(current_year)
    years = sorted(years)

    data = pd.Series(df_plot["duration"].values / 60.0, index=df_plot.index)
    heatmap_paths = {}
    for year in years:
        save_path = os.path.join(save_dir, f"heatmap_{year}.png")
        full_year_idx = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31", freq="D")
        year_data = data.reindex(full_year_idx, fill_value=0)
        year_data.index.name = "date"

        fig = plt.figure(figsize=(10, 3), dpi=100)
        ax = fig.add_subplot(111)
        calmap.yearplot(year_data, year=year, ax=ax, cmap="YlGn",
                        linewidth=1, fillcolor="#dddddd", linecolor="#ffffff")
        ax.set_title(f"{year}年 朗读热力图 (颜色深浅表示时长)",
                     fontproperties="Microsoft YaHei", fontsize=10)
        plt.tight_layout()
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
        plt.close(fig)
        heatmap_paths[year] = save_path
    return heatmap_paths


def save_trend_chart(df, save_path):
    try:
        if df is None or df.empty:
            return False
        df_plot = df.copy()
        if not isinstance(df_plot.index, pd.DatetimeIndex):
            if "date" in df_plot.columns:
                df_plot.index = pd.to_datetime(df_plot["date"])
        df_plot.sort_index(inplace=True)
        is_truncated = False
        if len(df_plot) > 30:
            df_plot = df_plot.tail(30)
            is_truncated = True

        fig = plt.figure(figsize=(10, 4), dpi=100)
        ax1 = fig.add_subplot(111)
        x = range(len(df_plot))
        durations = df_plot["duration"] / 60.0

        ax1.bar(x, durations, color="#007acc", alpha=0.6, label="时长(分钟)", width=0.6)
        ax1.set_ylabel("时长 (分钟)", fontproperties="Microsoft YaHei")

        ax2 = ax1.twinx()
        efficiencies = df_plot["efficiency"] * 100
        ax2.plot(x, efficiencies, color="#ff9800", marker="o", markersize=4, linewidth=2, label="效率(%)")
        ax2.set_ylabel("效率 (%)", fontproperties="Microsoft YaHei")
        ax2.set_ylim(0, 110)

        ax1.set_xticks(x)
        ax1.set_xticklabels(df_plot.index.strftime("%d"), rotation=0, fontsize=8)
        ax1.set_xlabel(
            f"日期 ({df_plot.index[0].strftime('%Y.%m')} - {df_plot.index[-1].strftime('%m')}) [仅显示日]",
            fontproperties="Microsoft YaHei",
        )
        title_text = "近期朗读趋势 (时长 & 效率)"
        if is_truncated:
            title_text += " - 近30次"
        ax1.set_title(title_text, fontproperties="Microsoft YaHei", fontsize=10)
        plt.tight_layout()
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving trend chart: {e}")
        return False


def save_volume_chart(data, save_path):
    try:
        if not data:
            return False
        fig = plt.figure(figsize=(8, 2), dpi=100)
        ax = fig.add_subplot(111)
        ax.plot(data, color="#28a745", linewidth=1, alpha=0.8)
        ax.fill_between(range(len(data)), data, color="#28a745", alpha=0.1)
        ax.set_title("音量变化趋势 (dB)", fontproperties="Microsoft YaHei", fontsize=10)
        ax.set_ylabel("Volume", fontsize=8)
        ax.set_xticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        plt.tight_layout()
        fig.savefig(save_path, bbox_inches="tight", dpi=100)
        plt.close(fig)
        return True
    except Exception as e:
        print(f"Error saving volume chart: {e}")
        return False
