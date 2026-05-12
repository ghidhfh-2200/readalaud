"""
audio 子包 —— 音频播放、数据统计与深度分析。

模块说明：
  - playback.py      : 日录音的播放/暂停/停止/进度条控制
  - dashboard.py     : 综合数据看板（总时长、连胜、热力图、趋势图）
  - daily_detail.py  : 单日详情数据（音量图、同比昨日）
  - chart_builder.py : 各类图表（热力图、趋势图、音量图）生成工具
  - analysis_engine.py : 深度音频分析（VAD/RMS/LTAS/ZCR/Pitch/SNR/MFCC/Crest/Entropy/Spectrogram）
"""

from .playback import bind_audio_analasy_api
from .analysis_engine import (
    run_selected_analyses,
    ANALYSIS_ITEMS,
    ANALYSIS_DESCRIPTIONS,
)

__all__ = [
    "bind_audio_analasy_api",
    "run_selected_analyses",
    "ANALYSIS_ITEMS",
    "ANALYSIS_DESCRIPTIONS",
]
