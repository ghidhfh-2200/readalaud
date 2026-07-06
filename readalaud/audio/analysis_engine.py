"""
analysis_engine.py —— 深度音频分析引擎（VAD/RMS/LTAS/ZCR/Pitch/SNR/MFCC/Crest/Entropy/Spectrogram）。

VAD 基于 WebRTC VAD（webrtcvad）实现，其余分析使用 numpy + matplotlib。
"""
import os
import wave
import numpy as np
import matplotlib
import webrtcvad
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib import cm as _mpl_cm
from matplotlib import font_manager as _font_manager

matplotlib.use("Agg")


def _pick_cjk_font_family() -> str:
    preferred = (
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Noto Sans CJK JP",
        "WenQuanYi Zen Hei",
        "Arial Unicode MS",
    )
    available = {f.name for f in _font_manager.fontManager.ttflist}
    for family in preferred:
        if family in available:
            return family
    return "DejaVu Sans"


_CJK_FONT_FAMILY = _pick_cjk_font_family()
matplotlib.rcParams["font.family"] = [
    _CJK_FONT_FAMILY,
    "DejaVu Sans",
]
matplotlib.rcParams["axes.unicode_minus"] = False


# ══════════════════════════════════════════════════════════
#  分析项目注册表
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

ANALYSIS_DESCRIPTIONS: dict = {
    "vad": {
        "title":  "语音活动检测 (VAD)",
        "brief":  "检测录音中哪些时刻在说话、哪些是停顿或噪音。",
        "detail": (
            "图表横轴为时间，绿色填充区域代表检测到的「语音段」，蓝色折线为归一化能量变化。\n"
            "📌 理想范围：60%–85%。\n"
            "💡 提示：频繁中断可能是口误、卡顿或录音噪音触发了误判。"
        ),
        "extra_tips": {"语音占比": "实际说话时长 ÷ 总录音时长。越高说明停顿越少、朗读越连贯。"},
    },
    "rms": {
        "title":  "短时能量 (RMS)",
        "brief":  "衡量录音音量（响度）随时间的变化趋势。",
        "detail": (
            "RMS 反映「平均响度」。曲线平稳说明音量控制良好；曲线末段下降明显说明朗读后期疲劳。\n"
            "💡 建议 RMS 均值保持在 0.05–0.3（已归一化）。"
        ),
        "extra_tips": {"均值RMS": "整段录音的平均响度。", "最大RMS": "录音中出现的最大瞬时响度。"},
    },
    "ltas": {
        "title":  "长时平均能量谱 (LTAS)",
        "brief":  "将录音按每10秒分段，对比各段的频率分布是否一致。",
        "detail": (
            "各条曲线高度重合说明音色稳定，是优质朗读的标志。\n"
            "💡 正常人声主要能量集中在 300–3400 Hz。"
        ),
        "extra_tips": {"切片数": "录音被均分为多少个 10 秒片段。"},
    },
    "zcr": {
        "title":  "过零率变化 (ZCR)",
        "brief":  "反映朗读中清辅音（如 s、sh、z）与元音的分布比例。",
        "detail": (
            "高 ZCR：清辅音或背景高频噪声；低 ZCR：元音或静默段。\n"
            "💡 正常人声一般在 0.05–0.20 之间。"
        ),
        "extra_tips": {"平均ZCR": "全程的平均过零率。"},
    },
    "pitch": {
        "title":  "基频变化 (F0)",
        "brief":  "记录朗读时声调（音调高低）的变化，反映抑扬顿挫程度。",
        "detail": (
            "男性：80–180 Hz；女性：160–300 Hz；儿童：250–400 Hz。\n"
            "💡 F0 变化幅度越大，朗读的感染力通常越强。"
        ),
        "extra_tips": {"平均F0": "全程有声段的平均音调。"},
    },
    "snr": {
        "title":  "信噪比 (SNR)",
        "brief":  "量化录音中人声与背景噪音的比例，数值越高录音越干净。",
        "detail": (
            "≥30dB 优秀 | 20–30dB 良好 | 10–20dB 一般 | <10dB 较差。\n"
            "💡 本工具使用「最低 10% 能量帧」估算噪底，适合稳态噪音场景。"
        ),
        "extra_tips": {"全局SNR": "全段录音的综合信噪比。"},
    },
    "mfcc": {
        "title":  "梅尔倒谱系数 (MFCC)",
        "brief":  "模拟人耳感知，提取发音音色特征，是语音识别最核心的特征。",
        "detail": (
            "热图：横轴=时间，纵轴=系数编号，暖色=正值，冷色=负值。\n"
            "颜色均匀=音色稳定；局部突变=口误/破音。"
        ),
        "extra_tips": {},
    },
    "crest": {
        "title":  "峰值因子 (Crest Factor)",
        "brief":  "衡量声音的动态范围，反映朗读是否有爆破音或声音过于压缩。",
        "detail": (
            "10–20dB 正常 | >25dB 爆破音 | <6dB 动态压缩。\n"
            "💡 专业播音建议保持在 10–20 dB。"
        ),
        "extra_tips": {"平均峰值因子": "全段平均动态范围。"},
    },
    "entropy": {
        "title":  "频谱熵 (Spectral Entropy)",
        "brief":  "衡量频谱能量的「混乱程度」，可用于区分清晰语音与噪音。",
        "detail": (
            "接近0：能量集中（清晰元音）；接近1：能量分散（白噪声）。\n"
            "正常有声段：0.5–0.8。"
        ),
        "extra_tips": {"平均熵": "全程平均频谱熵（0–1）。"},
    },
    "spectrogram": {
        "title":  "语谱图 (Spectrogram)",
        "brief":  "最直观的语音可视化：同时展示时间、频率、能量三维信息。",
        "detail": (
            "横轴：时间 | 纵轴：频率 | 颜色：越亮能量越强。\n"
            "宽频横纹→元音 | 竖纹→爆破辅音 | 高频斜纹→摩擦辅音 | 全频空白→停顿。"
        ),
        "extra_tips": {},
    },
}


# ══════════════════════════════════════════════════════════
#  内部工具函数
# ══════════════════════════════════════════════════════════

def _load_wav_as_array(path):
    """读取 WAV 文件，返回 (mono float64 归一化采样数组, 采样率)。"""
    with wave.open(path, "rb") as wf:
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
    """创建线程安全的 matplotlib Figure（不使用 pyplot 全局状态）。"""
    fig = Figure(figsize=(w, h), dpi=100, facecolor="white")
    FigureCanvas(fig)
    return fig


def _save_fig(fig, path):
    fig.savefig(path, bbox_inches="tight", dpi=100, facecolor="white")


def _frame_signal(samples, frame_len, hop_len):
    """将信号切分为重叠帧，短于一帧的信号会被补零。"""
    n = len(samples)
    if n < frame_len:
        samples = np.pad(samples, (0, frame_len - n))
        n = frame_len
    num_frames = 1 + (n - frame_len) // hop_len
    indices = np.arange(frame_len)[None, :] + np.arange(num_frames)[:, None] * hop_len
    return samples[indices]


# ══════════════════════════════════════════════════════════
#  各项分析实现
# ══════════════════════════════════════════════════════════

def _analyze_vad(samples, sr, output_path):
    """
    基于 WebRTC VAD（webrtcvad）的语音活动检测。

    webrtcvad 要求：
      - 采样率：8000 / 16000 / 32000 / 48000
      - 帧长：10ms / 20ms / 30ms（对应 160/320/480 样本 @ 16kHz）
      - 输入：int16 单声道 PCM

    策略：将音频重采样至 16kHz，以 30ms 帧进行 VAD，结果映射回原始时间轴。
    """

    # 1. 选择 VAD 工作采样率（优先 16kHz，兼顾精度与性能）
    vad_sr = 16000
    if sr <= 8000:
        vad_sr = 8000
    elif sr <= 16000:
        vad_sr = 16000
    elif sr <= 32000:
        vad_sr = 32000
    else:
        vad_sr = 48000

    # 2. 重采样到 VAD 工作采样率（线性插值，无 scipy 依赖）
    if sr != vad_sr:
        import math
        ratio = vad_sr / sr
        out_len = max(1, int(len(samples) * ratio))
        indices = np.linspace(0, len(samples) - 1, out_len)
        lo = np.floor(indices).astype(int)
        hi = np.clip(lo + 1, 0, len(samples) - 1)
        frac = indices - lo.astype(float)
        vad_samples = samples[lo] * (1 - frac) + samples[hi] * frac
    else:
        vad_samples = samples.copy()

    # 3. 转换为 int16 PCM（webrtcvad 要求的格式）
    vad_samples_f64 = np.clip(vad_samples, -1.0, 1.0)
    pcm_int16 = (vad_samples_f64 * 32767).astype(np.int16)

    # 4. 配置 VAD
    #    mode: 0=Normal, 1=Low Bitrate, 2=Aggressive, 3=Very Aggressive
    #    朗读场景使用 2（Aggressive），避免环境噪声被误判为语音
    vad = webrtcvad.Vad(2)

    # 5. 以 30ms 帧长进行 VAD（30ms = 960 样本 @ 32kHz 对应的 480 @ 16kHz）
    frame_ms = 30
    frame_size = int(vad_sr * frame_ms / 1000)

    total_frames = len(pcm_int16) // frame_size
    if total_frames == 0:
        # 音频太短，不足一帧
        is_speech = np.array([False])
        times = np.array([0.0])
    else:
        speech_per_frame = []
        for i in range(total_frames):
            chunk = pcm_int16[i * frame_size: (i + 1) * frame_size]
            try:
                is_speech_flag = vad.is_speech(chunk.tobytes(), vad_sr)
            except Exception:
                is_speech_flag = False
            speech_per_frame.append(is_speech_flag)
        is_speech = np.array(speech_per_frame)

    # 6. 映射回原始时间轴
    #    VAD 帧时间轴（秒，按原始时长映射）
    vad_times = np.arange(len(is_speech)) * frame_ms / 1000.0

    #    计算能量曲线用于图表叠加（在原始采样率下）
    orig_frame_len = int(0.025 * sr)
    orig_hop_len = int(0.010 * sr)
    orig_frames = _frame_signal(samples, orig_frame_len, orig_hop_len)
    energy = np.sum(orig_frames ** 2, axis=1)
    times = np.arange(len(energy)) * orig_hop_len / sr

    # 7. 将 VAD 决策映射到能量帧时间轴
    #    每个能量帧对应一个时间点，查找最近的 VAD 帧决策
    if len(is_speech) > 0 and len(times) > 0:
        vad_frame_indices = np.clip(
            (times / (frame_ms / 1000.0)).astype(int), 0, len(is_speech) - 1
        )
        is_speech_mapped = is_speech[vad_frame_indices]
    else:
        is_speech_mapped = np.zeros(len(times), dtype=bool)

    # 8. 绘制图表
    fig = _make_fig(10, 2.5)
    ax = fig.add_subplot(111)
    e_norm = energy / energy.max() if energy.max() > 0 else energy
    ax.fill_between(
        times, is_speech_mapped.astype(float),
        alpha=0.4, color="#28a745", label="语音段 (WebRTC VAD)"
    )
    ax.plot(times, e_norm, color="#007acc", linewidth=0.5, alpha=0.6, label="能量")
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("活动", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title(
        f"语音活动检测 (WebRTC VAD, mode=2, {vad_sr}Hz/{frame_ms}ms)",
        fontproperties=_CJK_FONT_FAMILY, fontsize=10,
    )
    ax.legend(prop={"family": _CJK_FONT_FAMILY, "size": 8})
    ax.set_ylim(-0.05, 1.15)
    fig.tight_layout()
    _save_fig(fig, output_path)

    # 9. 统计指标
    speech_ratio = (
        float(np.sum(is_speech_mapped) / len(is_speech_mapped))
        if len(is_speech_mapped) > 0 else 0.0
    )

    # 计算语音段个数和平均段长（基于原始 is_speech 而非映射后的）
    changes = np.diff(np.concatenate(([False], is_speech, [False])).astype(int))
    speech_starts = np.where(changes == 1)[0]
    speech_ends = np.where(changes == -1)[0]
    speech_durations = speech_ends - speech_starts
    avg_segment_len = float(np.mean(speech_durations)) if len(speech_durations) > 0 else 0.0
    num_segments = len(speech_durations)

    return {
        "语音占比": f"{speech_ratio:.1%}",
        "语音段数": str(num_segments),
        "平均段长": f"{avg_segment_len * frame_ms / 1000.0:.1f}s",
        "VAD采样率": f"{vad_sr} Hz",
    }


def _analyze_rms(samples, sr, output_path):
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    times = np.arange(len(rms)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, rms, color="#ff6f00", linewidth=0.8)
    ax.fill_between(times, rms, alpha=0.2, color="#ff6f00")
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("RMS", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("短时能量 (RMS)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    rms_mean = float(np.mean(rms))
    rms_std = float(np.std(rms))
    rms_cv = rms_std / rms_mean if rms_mean > 1e-12 else 0.0
    rms_max = float(np.max(rms))
    return {
        "均值RMS": f"{rms_mean:.4f}",
        "RMS标准差": f"{rms_std:.4f}",
        "RMS变异系数": f"{rms_cv:.3f}",
        "最大RMS": f"{rms_max:.4f}",
    }


def _analyze_ltas(samples, sr, output_path):
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

    ax.set_xlabel("频率 (Hz)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("幅度 (dB)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("长时平均能量谱 (LTAS, 10s 切片)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    if n_slices <= 12:
        ax.legend(prop={"family": _CJK_FONT_FAMILY, "size": 7}, loc="upper right", ncol=2)
    ax.set_xlim(0, sr / 2)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"切片数": n_slices}


def _analyze_zcr(samples, sr, output_path):
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    zcr = np.sum(np.abs(np.diff(np.sign(frames), axis=1)), axis=1) / (2 * frame_len)
    times = np.arange(len(zcr)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, zcr, color="#e91e63", linewidth=0.7)
    ax.fill_between(times, zcr, alpha=0.15, color="#e91e63")
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("ZCR", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("过零率变化", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    zcr_mean = float(np.mean(zcr))
    zcr_std = float(np.std(zcr))
    return {"平均ZCR": f"{zcr_mean:.4f}", "ZCR标准差": f"{zcr_std:.4f}"}


def _analyze_pitch(samples, sr, output_path):
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
    ax.plot(times, pitch_masked, color="#9c27b0", linewidth=0.8, marker=".", markersize=1)
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("频率 (Hz)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("基频变化 (F0)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    ax.set_ylim(f0_min - 20, f0_max + 50)
    fig.tight_layout()
    _save_fig(fig, output_path)
    valid = pitches[pitches > 0]
    if len(valid) > 0:
        f0_mean = float(np.mean(valid))
        f0_std = float(np.std(valid))
        f0_cv = f0_std / f0_mean if f0_mean > 1e-12 else 0.0
        return {
            "平均F0": f"{f0_mean:.1f} Hz",
            "F0标准差": f"{f0_std:.1f}",
            "F0变异系数": f"{f0_cv:.3f}",
        }
    return {"平均F0": "N/A", "F0标准差": "N/A", "F0变异系数": "N/A"}


def _analyze_snr(samples, sr, output_path):
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    energy = np.sum(frames ** 2, axis=1)
    sorted_energy = np.sort(energy)
    n_noise = max(1, len(sorted_energy) // 10)
    noise_floor = np.mean(sorted_energy[:n_noise])
    signal_power = np.mean(energy)
    safe_noise_floor = max(float(noise_floor), 1e-10)
    safe_signal_power = max(float(signal_power), 1e-10)
    with np.errstate(divide="ignore", invalid="ignore"):
        snr_global = 10 * np.log10(safe_signal_power / safe_noise_floor)
        snr_frames = np.clip(10 * np.log10(np.maximum(energy, 1e-10) / safe_noise_floor), -20, 60)
    times = np.arange(len(snr_frames)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, snr_frames, color="#00bcd4", linewidth=0.7)
    ax.axhline(y=snr_global, color="#ff5722", linestyle="--", linewidth=1,
               label=f"全局 SNR: {snr_global:.1f} dB")
    ax.fill_between(times, snr_frames, alpha=0.1, color="#00bcd4")
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("SNR (dB)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("信噪比 (SNR)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    ax.legend(prop={"family": _CJK_FONT_FAMILY, "size": 8})
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"全局SNR": f"{snr_global:.1f} dB"}


def _analyze_mfcc(samples, sr, output_path):
    n_mfcc, n_mels, nfft = 13, 40, 2048
    frame_len = int(0.025 * sr)
    hop_len = int(0.020 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    window = np.hanning(frame_len)
    if frame_len < nfft:
        frames = np.pad(frames, ((0, 0), (0, nfft - frame_len)))
        window = np.pad(window, (0, nfft - frame_len))
    power = np.abs(np.fft.rfft(frames * window, n=nfft)) ** 2

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
    dct_mat = np.array([[np.cos(np.pi * i * (j + 0.5) / n_mels) for j in range(n_mels)] for i in range(n_mfcc)])
    mfccs = mel_spec @ dct_mat.T
    times = np.arange(mfccs.shape[0]) * hop_len / sr

    fig = _make_fig(10, 4)
    ax = fig.add_subplot(111)
    im = ax.imshow(mfccs.T, aspect="auto", origin="lower", cmap="coolwarm",
                   extent=[times[0], times[-1], 0, n_mfcc])
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("MFCC 系数", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("梅尔倒谱系数 (MFCC)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    fig.colorbar(im, ax=ax, label="幅值")
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {}


def _analyze_crest(samples, sr, output_path):
    frame_len = int(0.025 * sr)
    hop_len = int(0.010 * sr)
    frames = _frame_signal(samples, frame_len, hop_len)
    rms = np.sqrt(np.mean(frames ** 2, axis=1))
    peak = np.max(np.abs(frames), axis=1)
    crest_db = 20 * np.log10(peak / (rms + 1e-10) + 1e-10)
    times = np.arange(len(crest_db)) * hop_len / sr

    fig = _make_fig(10, 3)
    ax = fig.add_subplot(111)
    ax.plot(times, crest_db, color="#795548", linewidth=0.7)
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("峰值因子 (dB)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("峰值因子 (Crest Factor)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    fig.tight_layout()
    _save_fig(fig, output_path)
    crest_mean = float(np.mean(crest_db))
    crest_std = float(np.std(crest_db))
    return {"平均峰值因子": f"{crest_mean:.1f} dB", "峰值因子标准差": f"{crest_std:.1f} dB"}


def _analyze_entropy(samples, sr, output_path):
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
    ax.plot(times, entropy_norm, color="#4caf50", linewidth=0.7)
    ax.fill_between(times, entropy_norm, alpha=0.15, color="#4caf50")
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("归一化频谱熵", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("频谱熵 (Spectral Entropy)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    ax.set_ylim(0, 1.05)
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {"平均熵": f"{np.mean(entropy_norm):.3f}"}


def _analyze_spectrogram(samples, sr, output_path):
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
    im = ax.imshow(mag_db.T, aspect="auto", origin="lower", cmap="inferno",
                   extent=[times[0], times[-1], freqs[0], freqs[-1]])
    ax.set_xlabel("时间 (s)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_ylabel("频率 (Hz)", fontproperties=_CJK_FONT_FAMILY)
    ax.set_title("语谱图 (Spectrogram)", fontproperties=_CJK_FONT_FAMILY, fontsize=10)
    fig.colorbar(im, ax=ax, label="幅度 (dB)")
    ax.set_ylim(0, min(8000, sr / 2))
    fig.tight_layout()
    _save_fig(fig, output_path)
    return {}


# ══════════════════════════════════════════════════════════
#  分析注册表 & 调度器
# ══════════════════════════════════════════════════════════

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
    执行选定的音频分析项目。

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
