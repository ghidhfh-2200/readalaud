"""
report.py —— 朗读报告生成：汇总每日详情、看板数据与音频分析结果，并输出综合评分。
"""

from __future__ import annotations

import json
import math
import os
import wave
from datetime import datetime

import numpy as np

from .analysis_engine import ANALYSIS_ITEMS, run_selected_analyses
from .daily_detail import fetch_for_daily_data
from .dashboard import refresh_dashboard_data


REPORT_VERSION = 1


def _clamp(value, low, high):
    return max(low, min(high, value))


def _parse_float(value, default=None):
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return default
    text = text.replace(",", "")
    for suffix in ("dB", "DB", "%", "Hz"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    try:
        return float(text)
    except ValueError:
        return default


def _parse_ratio_from_analysis(extra, key_name):
    if not isinstance(extra, dict):
        return None
    raw = extra.get(key_name)
    if raw is None:
        return None
    value = _parse_float(raw, None)
    if value is None:
        return None
    if isinstance(raw, str) and raw.strip().endswith("%"):
        return value / 100.0
    return value if value <= 1.5 else value / 100.0


def _load_wav_as_array(path):
    with wave.open(path, "rb") as wf:
        channels = wf.getnchannels()
        sample_width = wf.getsampwidth()
        sample_rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())

    dtype_map = {1: np.uint8, 2: np.int16, 4: np.int32}
    dtype = dtype_map.get(sample_width, np.int16)
    samples = np.frombuffer(raw, dtype=dtype).astype(np.float64)
    if dtype == np.uint8:
        samples = (samples - 128.0) / 128.0
    else:
        samples /= float(2 ** (sample_width * 8 - 1))
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1)
    return samples, sample_rate


def _frame_signal(samples, frame_len, hop_len):
    if len(samples) < frame_len:
        samples = np.pad(samples, (0, frame_len - len(samples)))
    num_frames = 1 + max(0, (len(samples) - frame_len) // hop_len)
    indices = np.arange(frame_len)[None, :] + np.arange(num_frames)[:, None] * hop_len
    return samples[indices]


def _estimate_f0_values(frames, sr):
    f0_min, f0_max = 80.0, 400.0
    lag_min = max(1, int(sr / f0_max))
    lag_max = min(frames.shape[1] - 1, int(sr / f0_min))
    fft_size = 2 ** int(np.ceil(np.log2(max(2, 2 * frames.shape[1]))))
    pitches = []

    for frame in frames:
        frame = frame - np.mean(frame)
        peak_abs = np.max(np.abs(frame))
        if peak_abs < 1e-6:
            continue
        fft_f = np.fft.rfft(frame, n=fft_size)
        acf = np.fft.irfft(fft_f * np.conj(fft_f))[: frames.shape[1]]
        if acf[0] > 0:
            acf /= acf[0]
        region = acf[lag_min : lag_max + 1]
        if len(region) == 0:
            continue
        peak_idx = int(np.argmax(region)) + lag_min
        if acf[peak_idx] > 0.25:
            pitches.append(sr / peak_idx)

    return np.array(pitches, dtype=np.float64)


def _compute_audio_metrics(audio_path):
    if not audio_path or not os.path.exists(audio_path):
        return {}

    try:
        samples, sr = _load_wav_as_array(audio_path)
    except Exception:
        return {}

    if len(samples) == 0 or sr <= 0:
        return {}

    eps = 1e-12
    frame_len_25 = max(1, int(0.025 * sr))
    hop_len_10 = max(1, int(0.010 * sr))
    frames_25 = _frame_signal(samples, frame_len_25, hop_len_10)

    energy = np.sum(frames_25 ** 2, axis=1)
    rms = np.sqrt(np.mean(frames_25 ** 2, axis=1))
    zcr = np.sum(np.abs(np.diff(np.sign(frames_25), axis=1)), axis=1) / (2 * frame_len_25)

    # 语音占比（近似 VAD）
    energy_mean = float(np.mean(energy)) if len(energy) else 0.0
    vad_threshold = energy_mean * 0.1 if energy_mean > 0 else 1e-10
    speech_ratio = float(np.sum(energy > vad_threshold) / len(energy)) if len(energy) else 0.0

    # 全局 SNR
    sorted_energy = np.sort(energy)
    n_noise = max(1, len(sorted_energy) // 10)
    noise_floor = float(np.mean(sorted_energy[:n_noise])) if len(sorted_energy) else 0.0
    signal_power = float(np.mean(energy)) if len(energy) else 0.0
    snr_db = 10.0 * math.log10((signal_power + eps) / (noise_floor + eps)) if signal_power > 0 else 0.0

    # 频谱熵
    nfft = 2048
    window = np.hanning(frame_len_25)
    if frame_len_25 < nfft:
        window = np.pad(window, (0, nfft - frame_len_25))
    entropy_values = []
    for frame in frames_25:
        segment = frame
        if len(segment) < nfft:
            segment = np.pad(segment, (0, nfft - len(segment)))
        spectrum = np.abs(np.fft.rfft(segment[:frame_len_25] * window[:frame_len_25], n=nfft)) ** 2
        total = float(np.sum(spectrum))
        if total <= 0:
            continue
        p = spectrum / total
        p = p[p > 0]
        if len(p) == 0:
            continue
        entropy = -float(np.sum(p * np.log(p))) / math.log(len(spectrum))
        entropy_values.append(entropy)
    entropy_mean = float(np.mean(np.asarray(entropy_values, dtype=np.float64))) if entropy_values else 0.0

    # Crest factor
    peak = np.max(np.abs(frames_25), axis=1)
    crest_values = 20.0 * np.log10((peak + eps) / (rms + eps))
    crest_mean = float(np.mean(crest_values)) if len(crest_values) else 0.0

    # RMS 稳定性
    rms_mean = float(np.mean(rms)) if len(rms) else 0.0
    rms_std = float(np.std(rms)) if len(rms) else 0.0
    rms_cv = rms_std / rms_mean if rms_mean > eps else 0.0

    # ZCR 平均值
    zcr_mean = float(np.mean(zcr)) if len(zcr) else 0.0

    # 基频变化
    frame_len_40 = max(1, int(0.040 * sr))
    hop_len_20 = max(1, int(0.020 * sr))
    frames_40 = _frame_signal(samples, frame_len_40, hop_len_20)
    f0_values = _estimate_f0_values(frames_40, sr)
    f0_mean = float(np.mean(f0_values)) if len(f0_values) else 0.0
    f0_std = float(np.std(f0_values)) if len(f0_values) else 0.0
    f0_cv = f0_std / f0_mean if f0_mean > eps else 0.0

    return {
        "vad_speech_ratio": speech_ratio,
        "global_snr_db": snr_db,
        "mean_spectral_entropy": entropy_mean,
        "mean_crest_db": crest_mean,
        "rms_mean": rms_mean,
        "rms_std": rms_std,
        "rms_cv": rms_cv,
        "mean_zcr": zcr_mean,
        "f0_mean": f0_mean,
        "f0_std": f0_std,
        "f0_cv": f0_cv,
    }


def _f_eff(efficiency):
    e = _clamp(float(efficiency or 0.0), 0.0, 1.0)
    if e >= 0.85:
        return 15.0
    if e >= 0.30:
        return 15.0 * (e - 0.30) / 0.55
    return 0.0


def _f_vad(ratio):
    r = max(0.0, float(ratio or 0.0))
    if r < 0.60:
        return 10.0 * (r / 0.60)
    if r <= 0.85:
        return 10.0
    return 10.0 * max(0.0, 1.0 - (r - 0.85) / 0.15)


def _f_snr(snr_db):
    s = float(snr_db or 0.0)
    if s >= 30.0:
        return 15.0
    if s >= 20.0:
        return 12.0 + 3.0 * (s - 20.0) / 10.0
    if s >= 10.0:
        return 6.0 + 6.0 * (s - 10.0) / 10.0
    return max(0.0, 6.0 * s / 10.0)


def _f_ent(entropy):
    h = _clamp(float(entropy or 0.0), 0.0, 1.0)
    if h < 0.50:
        return 10.0 * (h / 0.50)
    if h <= 0.80:
        return 10.0
    return 10.0 * max(0.0, (1.0 - h) / 0.20)


def _f_crest(crest):
    c = float(crest or 0.0)
    if c < 10.0:
        return 10.0 * (c / 10.0)
    if c <= 20.0:
        return 10.0
    return 10.0 * max(0.0, 1.0 - (c - 20.0) / 15.0)


def _f_stab(cv_rms):
    cv = max(0.0, float(cv_rms or 0.0))
    if cv < 0.30:
        return 5.0
    if cv < 0.60:
        return 5.0 * (0.60 - cv) / 0.30
    return 0.0


def _f_zcr(zcr):
    z = max(0.0, float(zcr or 0.0))
    if z < 0.05:
        return 8.0 * (z / 0.05)
    if z <= 0.20:
        return 8.0
    return 8.0 * max(0.0, 1.0 - (z - 0.20) / 0.20)


def _f_pitch(cv_f0):
    cv = max(0.0, float(cv_f0 or 0.0))
    if cv > 0.18:
        return 7.0
    if cv >= 0.08:
        return 3.0 + 4.0 * (cv - 0.08) / 0.10
    return 3.0 * cv / 0.08


def _f_goal(goal_rate):
    g = max(0.0, float(goal_rate or 0.0))
    if g >= 1.0:
        return 8.0
    if g >= 0.8:
        return 6.0 + 2.0 * (g - 0.8) / 0.2
    if g >= 0.5:
        return 3.0 + 3.0 * (g - 0.5) / 0.3
    return 3.0 * g / 0.5


def _f_streak(days):
    k = max(0, int(days or 0))
    if k >= 30:
        return 7.0
    if k >= 7:
        return 4.0 + 3.0 * (k - 7) / 23.0
    if k >= 1:
        return 1.0 + 3.0 * (k - 1) / 6.0
    return 0.0


def _f_daily(seconds):
    d = max(0.0, float(seconds or 0.0))
    if d >= 3600.0:
        return 5.0
    if d >= 1800.0:
        return 3.0 + 2.0 * (d - 1800.0) / 1800.0
    if d >= 600.0:
        return 1.0 + 2.0 * (d - 600.0) / 1200.0
    return 1.0 * d / 600.0


def _grade_from_score(score):
    if score >= 90:
        return "⭐⭐⭐⭐⭐ 卓越", "专业播音级别"
    if score >= 75:
        return "⭐⭐⭐⭐ 优秀", "朗读质量很好"
    if score >= 60:
        return "⭐⭐⭐ 良好", "整体不错，有小幅提升空间"
    if score >= 40:
        return "⭐⭐ 一般", "多个维度需要改进"
    return "⭐ 待提升", "基础较差，需要系统练习"


def _build_report_text(report):
    dim = report.get("dimensions", {})
    metrics = report.get("metrics", {})
    grade = report.get("grade", "")
    meaning = report.get("grade_meaning", "")
    lines = [
        f"朗读报告 · {report.get('date', '--')}",
        f"最终评分：{report.get('score', 0):.1f} / 100",
        f"等级：{grade}（{meaning}）",
        "",
        f"流畅度：{dim.get('流畅度', 0):.1f}",
        f"音质清晰度：{dim.get('音质清晰度', 0):.1f}",
        f"音量控制：{dim.get('音量控制', 0):.1f}",
        f"表现力：{dim.get('表现力', 0):.1f}",
        f"坚持力：{dim.get('坚持力', 0):.1f}",
        "",
        "关键指标：",
        f"- 效率：{metrics.get('efficiency', 0.0):.1%}",
        f"- 语音占比：{metrics.get('vad_speech_ratio', 0.0):.1%}",
        f"- 全局 SNR：{metrics.get('global_snr_db', 0.0):.1f} dB",
        f"- 平均频谱熵：{metrics.get('mean_spectral_entropy', 0.0):.3f}",
        f"- 平均峰值因子：{metrics.get('mean_crest_db', 0.0):.1f} dB",
        f"- RMS 变异系数：{metrics.get('rms_cv', 0.0):.3f}",
        f"- 平均过零率：{metrics.get('mean_zcr', 0.0):.3f}",
        f"- F0 变异系数：{metrics.get('f0_cv', 0.0):.3f}",
        "",
        "建议：",
    ]

    weakest = sorted(dim.items(), key=lambda item: item[1])[:2]
    suggestions = []
    for name, _ in weakest:
        if name == "流畅度":
            suggestions.append("减少停顿、提升连贯性，让朗读节奏更稳定。")
        elif name == "音质清晰度":
            suggestions.append("尽量降低环境噪声，并保持麦克风与口部距离稳定。")
        elif name == "音量控制":
            suggestions.append("避免音量忽大忽小，控制爆破音与压缩感。")
        elif name == "表现力":
            suggestions.append("适当加强语调变化与重音处理，提升抑扬顿挫。")
        elif name == "坚持力":
            suggestions.append("保持稳定打卡频率，并延长每日朗读时长。")
    if not suggestions:
        suggestions.append("继续保持当前节奏。")
    lines.extend([f"- {item}" for item in suggestions])
    return "\n".join(lines)


def generate_reading_report(self, date_input, force_refresh=False):
    """生成单日朗读报告，并返回完整报告字典。"""
    account = getattr(self, "current_acount", None)
    if not account or not date_input:
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
    details_dir = f"./details/{account}/{date_str}"
    report_dir = os.path.join(details_dir, "reading_report")
    cache_path = os.path.join(details_dir, "reading_report.json")
    txt_path = os.path.join(details_dir, "reading_report.txt")
    audio_path = os.path.join(details_dir, "recording.wav")
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(details_dir, exist_ok=True)

    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("date") == date_str and cached.get("version") == REPORT_VERSION:
                chart_paths = cached.get("analysis_charts", {})
                charts_ok = True
                if isinstance(chart_paths, dict):
                    for path in chart_paths.values():
                        if path and not os.path.exists(path):
                            charts_ok = False
                            break
                if charts_ok:
                    return cached
        except Exception:
            pass

    detail_data = fetch_for_daily_data(self, target_date, force_refresh=force_refresh)
    dashboard_data = refresh_dashboard_data(self, force_refresh=force_refresh)

    analysis_results = {}
    if os.path.exists(audio_path):
        try:
            analysis_results = run_selected_analyses(audio_path, list(ANALYSIS_ITEMS.keys()), report_dir)
        except Exception:
            analysis_results = {}

    metrics = _compute_audio_metrics(audio_path)

    vad_ratio = _parse_ratio_from_analysis(analysis_results.get("vad", {}).get("extra", {}), "语音占比")
    if vad_ratio is None:
        total_duration = float(detail_data.get("total_duration", 0) or 0)
        pause_duration = float(detail_data.get("pause_duration", 0) or 0)
        vad_ratio = (total_duration - pause_duration) / total_duration if total_duration > 0 else 0.0

    efficiency = float(detail_data.get("efficiency", 0.0) or 0.0)
    snr_db = metrics.get("global_snr_db", 0.0)
    entropy_mean = metrics.get("mean_spectral_entropy", 0.0)
    crest_mean = metrics.get("mean_crest_db", 0.0)
    rms_cv = metrics.get("rms_cv", 0.0)
    zcr_mean = metrics.get("mean_zcr", 0.0)
    f0_cv = metrics.get("f0_cv", 0.0)

    goal = float(detail_data.get("goal", 0) or 0)
    real_read_time = float(detail_data.get("real_read_time", 0) or 0)
    goal_rate = real_read_time / goal if goal > 0 else 0.0
    current_streak = int(dashboard_data.get("current_streak", 0) or 0)
    average_daily = float(dashboard_data.get("average_daily", 0) or 0)

    # 语音占比权重更高：70%，效率 30%
    s1 = _f_eff(efficiency) * 0.30 + _f_vad(vad_ratio) * 0.70
    s2 = _f_snr(snr_db) + _f_ent(entropy_mean)
    s3 = _f_crest(crest_mean) + _f_stab(rms_cv)
    s4 = _f_zcr(zcr_mean) + _f_pitch(f0_cv)
    s5 = _f_goal(goal_rate) + _f_streak(current_streak) + _f_daily(average_daily)
    score = _clamp(s1 * 0.7 + s2 * 0.075 + s3 * 0.075 + s4 * 0.075 + s5 * 0.075, 0.0, 100.0)

    grade, meaning = _grade_from_score(score)

    report = {
        "version": REPORT_VERSION,
        "date": date_str,
        "score": round(score, 1),
        "grade": grade,
        "grade_meaning": meaning,
        "dimensions": {
            "流畅度": round(s1, 1),
            "音质清晰度": round(s2, 1),
            "音量控制": round(s3, 1),
            "表现力": round(s4, 1),
            "坚持力": round(s5, 1),
        },
        "metrics": {
            "efficiency": efficiency,
            "vad_speech_ratio": vad_ratio,
            "global_snr_db": snr_db,
            "mean_spectral_entropy": entropy_mean,
            "mean_crest_db": crest_mean,
            "rms_cv": rms_cv,
            "mean_zcr": zcr_mean,
            "f0_cv": f0_cv,
            "goal_rate": goal_rate,
            "current_streak": current_streak,
            "average_daily": average_daily,
            "goal": goal,
            "real_read_time": real_read_time,
        },
        "detail_data": detail_data,
        "dashboard_data": dashboard_data,
        "analysis_charts": {
            key: value.get("path", "")
            for key, value in analysis_results.items()
            if isinstance(value, dict) and value.get("path")
        },
        "analysis_results": analysis_results,
    }
    report["report_text"] = _build_report_text(report)

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(report["report_text"])
    except Exception:
        pass

    return report


__all__ = ["generate_reading_report"]
