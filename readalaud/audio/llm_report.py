"""
llm_report.py —— 调用 LLM（OpenAI 兼容接口）对朗读数据生成 AI 语音评估报告。

功能：
  - get_llm_config(): 从全局设置读取 LLM 配置
  - generate_llm_report(): 自行收集原始数据 + 音频分析图表，打包发送给 LLM，获取评估结果
  - _build_system_prompt(): 构建含参数说明的系统提示词
  - _encode_image_to_base64(): 将图表转为 base64 data URI 嵌入请求

调用格式：OpenAI 兼容 responses.create，支持 enable_thinking 思考模式。
回答格式：JSON，包含 评分、分析、总结 三个字段。
不依赖传统评分算法，完全由 LLM 基于原始数据独立评估。
"""

from __future__ import annotations

import base64
import json
import os
import traceback
from datetime import datetime
from typing import Any

from ..settings import get_setting

# ══════════════════════════════════════════════════════════
#  配置读取
# ══════════════════════════════════════════════════════════

_LLM_CONFIG_KEYS = [
    "llm_api_key",
    "llm_base_url",
    "llm_model",
    "llm_enabled",
]


def get_llm_config() -> dict:
    """从全局设置读取 LLM 配置（API Key / Base URL / Model / 启用状态）。"""
    cfg = {}
    for key in _LLM_CONFIG_KEYS:
        raw = get_setting(key)
        if raw is not None:
            cfg[key] = raw
    cfg.setdefault("llm_enabled", True)
    return cfg


# ══════════════════════════════════════════════════════════
#  图片编码工具
# ══════════════════════════════════════════════════════════

def _encode_image_to_base64(image_path: str) -> str | None:
    """将本地图片文件编码为 base64 data URI 字符串。"""
    if not image_path or not os.path.exists(image_path):
        return None
    try:
        with open(image_path, "rb") as f:
            raw = f.read()
        ext = os.path.splitext(image_path)[1].lower().lstrip(".")
        if ext == "jpg":
            ext = "jpeg"
        mime = f"image/{ext}" if ext in ("png", "jpeg", "gif", "webp") else "image/png"
        b64 = base64.b64encode(raw).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


# ══════════════════════════════════════════════════════════
#  系统提示词
# ══════════════════════════════════════════════════════════

def _build_system_prompt() -> str:
    """构建包含参数说明的系统提示词。"""
    return """# 角色
你是一名专业的语音评估专家，擅长分析朗读录音数据。你会收到一名用户的朗读录音分析图表和数值指标，请基于这些数据给出专业、客观的评估。

# 参数说明

以下是你将在数据中看到的所有参数及其含义：

## 基础朗读数据
| 参数 | 含义 | 单位 | 理想范围 |
|------|------|------|----------|
| total_duration | 录音总时长（含停顿） | 秒 | 根据目标设定 |
| pause_duration | 累计停顿时长 | 秒 | 越少越好 |
| real_read_time | 真实有效朗读时长 | 秒 | 越长越好 |
| efficiency | 朗读效率 = (总时长-停顿时长)/总时长 | 0~1 | ≥0.85 |
| max_volume | 朗读过程中最大音量 | dB | 70~95 |
| avg_volume | 朗读过程中平均音量 | dB | 55~75 |
| goal | 每日朗读目标时长 | 秒 | 用户自定 |
| completion | 目标完成度 = real_read_time/goal | % | ≥100% |

## 音频分析指标
| 参数 | 含义 | 理想范围 | 说明 |
|------|------|----------|------|
| vad_speech_ratio | 语音活动占比 | 0.60~0.85 | 过低说明噪音/静音过多 |
| global_snr_db | 全局信噪比 | ≥30 dB 优秀，20~30 良好，<10 较差 | 越高录音越干净 |
| mean_spectral_entropy | 平均频谱熵 | 0.5~0.8 | 接近0=能量集中，接近1=噪音 |
| mean_crest_db | 平均峰值因子 | 10~20 dB | >25 爆破音，<6 过于压缩 |
| rms_mean | 短时能量均值（归一化） | 0.05~0.3 | 反映平均响度 |
| rms_std | 短时能量标准差 | 越小越好 | 反映音量波动 |
| rms_cv | RMS 变异系数 | <0.5 稳定，>1.0 波动大 | 核心音量稳定性指标 |
| mean_zcr | 平均过零率 | 0.05~0.20 | 反映清辅音与元音分布 |
| f0_mean | 平均基频 | 男80~180，女160~300 Hz | 音调水平 |
| f0_std | 基频标准差 | 越大越丰富 | 语调变化幅度 |
| f0_cv | F0 变异系数 | >0.18 丰富，<0.08 单一 | 核心表现力指标 |

## 坚持力数据
| 参数 | 含义 |
|------|------|
| current_streak | 当前连续打卡天数 |
| max_streak | 历史最长连续打卡天数 |
| average_daily | 平均每日朗读时长（秒） |
| total_days | 累计朗读天数 |
| goal_rate | 目标完成率（≥1.0 达标） |
| compare_yesterday | 与昨日时长的百分比变化 |

# 评分维度说明（每项 0~20 分）

1. **流畅度**：参考 efficiency、vad_speech_ratio。效率越高、停顿越少分越高。
2. **音质清晰度**：参考 global_snr_db、mean_spectral_entropy。信噪比越高、熵值合理分越高。
3. **音量控制**：参考 rms_cv、mean_crest_db、avg_volume。波动越小分越高。
4. **表现力**：参考 f0_cv、mean_zcr。F0 变化越丰富、过零率合理分越高。
5. **坚持力**：参考 current_streak、goal_rate、average_daily。连续天数越多分越高。

综合评分 = 流畅度×0.35 + 音质清晰度×0.15 + 音量控制×0.15 + 表现力×0.15 + 坚持力×0.20

# 输出格式

严格输出以下 JSON（不要代码块标记）：

{
  "评分": {
    "综合评分": <0~100>,
    "等级": "<⭐⭐⭐⭐⭐ 卓越 | ⭐⭐⭐⭐ 优秀 | ⭐⭐⭐ 良好 | ⭐⭐ 一般 | ⭐ 待提升>",
    "流畅度": <0~20>,
    "音质清晰度": <0~20>,
    "音量控制": <0~20>,
    "表现力": <0~20>,
    "坚持力": <0~20>
  },
  "分析": {
    "亮点": ["..."],
    "待改进": ["..."],
    "维度分析": {
      "流畅度": "...",
      "音质清晰度": "...",
      "音量控制": "...",
      "表现力": "...",
      "坚持力": "..."
    }
  },
  "总结": {
    "建议": ["..."],
    "鼓励": "..."
  }
}

# 注意事项
- 评分客观，引用实际数据值。
- 建议具体可行。
- 图表无法加载时基于数值做判断并注明。
- 不要输出推理过程，只输出 JSON。"""


# ══════════════════════════════════════════════════════════
#  从分析引擎结果提取指标（复用 analysis_engine 算法）
# ══════════════════════════════════════════════════════════

# 定义各分析项 extra 字段到统一指标名的映射
_EXTRA_METRIC_MAP = {
    "vad":     {"语音占比":        "vad_speech_ratio"},
    "rms":     {"均值RMS":          "rms_mean",
                "RMS标准差":        "rms_std",
                "RMS变异系数":      "rms_cv",
                "最大RMS":          "rms_max"},
    "zcr":     {"平均ZCR":          "mean_zcr",
                "ZCR标准差":        "zcr_std"},
    "pitch":   {"平均F0":           "f0_mean",
                "F0标准差":         "f0_std",
                "F0变异系数":       "f0_cv"},
    "snr":     {"全局SNR":          "global_snr_db"},
    "crest":   {"平均峰值因子":     "mean_crest_db"},
    "entropy": {"平均熵":           "mean_spectral_entropy"},
}


def _extract_metrics_from_analysis(analysis_results: dict) -> dict:
    """从 analysis_engine 返回的 analysis_results 中提取统一的音频指标字典。"""
    metrics: dict[str, float] = {}
    for key, map_dict in _EXTRA_METRIC_MAP.items():
        item = analysis_results.get(key, {})
        if not isinstance(item, dict):
            continue
        extra = item.get("extra", {})
        if not isinstance(extra, dict):
            continue
        for extra_key, metric_name in map_dict.items():
            val_str = extra.get(extra_key, "")
            try:
                num_str = str(val_str).replace("%", "").replace("Hz", "").replace("dB", "").replace("s", "").strip()
                metrics[metric_name] = float(num_str)
            except (ValueError, TypeError):
                pass

    # vad_speech_ratio 百分比转换
    speech_ratio = metrics.get("vad_speech_ratio")
    if speech_ratio is not None and speech_ratio > 1:
        metrics["vad_speech_ratio"] = speech_ratio / 100.0

    return metrics


def _collect_raw_data(account: str, date_str: str, force_refresh: bool = False):
    """
    自行收集所有原始数据（daily data、dashboard、音频分析图表、metrics）。
    完全独立于传统评分算法，指标数据复用 analysis_engine 的计算结果。
    """
    from .daily_detail import fetch_for_daily_data
    from .dashboard import refresh_dashboard_data
    from .analysis_engine import ANALYSIS_ITEMS, run_selected_analyses

    class _FakeSelf:
        current_acount = account

    fake_self = _FakeSelf()

    try:
        from datetime import datetime as dt
        target_date = dt.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        target_date = datetime.now().date()

    detail = fetch_for_daily_data(fake_self, target_date, force_refresh=force_refresh)
    dashboard = refresh_dashboard_data(fake_self, force_refresh=force_refresh)

    details_dir = f"./details/{account}/{date_str}"
    report_dir = os.path.join(details_dir, "reading_report")
    os.makedirs(report_dir, exist_ok=True)
    audio_path = os.path.join(details_dir, "recording.wav")

    # ── 通过 analysis_engine 获取所有分析结果（图表 + 指标） ──
    analysis_results = {}
    if os.path.exists(audio_path):
        try:
            analysis_results = run_selected_analyses(
                audio_path, list(ANALYSIS_ITEMS.keys()), report_dir
            )
        except Exception:
            analysis_results = {}

    # ── 从分析结果中提取指标（复用 analysis_engine 的算法） ──
    metrics = _extract_metrics_from_analysis(analysis_results)

    # ── 收集图片路径 ──
    image_paths = []
    vol_path = detail.get("volume_chart_path", "")
    if vol_path and os.path.exists(vol_path):
        image_paths.append(vol_path)
    # 按固定顺序收集分析图表，保证 LLM 看到的顺序一致
    for key in [
        "vad", "rms", "ltas", "zcr", "pitch",
        "snr", "mfcc", "crest", "entropy", "spectrogram",
    ]:
        val = analysis_results.get(key, {})
        if isinstance(val, dict):
            p = val.get("path", "")
            if p and os.path.exists(p):
                image_paths.append(p)

    total_duration = float(detail.get("total_duration", 0) or 0)
    pause_duration = float(detail.get("pause_duration", 0) or 0)
    efficiency = float(detail.get("efficiency", 0.0) or 0.0)
    real_read_time = float(detail.get("real_read_time", 0) or 0)
    goal = float(detail.get("goal", 0) or 0)
    goal_rate = real_read_time / goal if goal > 0 else 0.0
    current_streak = int(dashboard.get("current_streak", 0) or 0)
    average_daily = float(dashboard.get("average_daily", 0) or 0)

    return {
        "date": date_str,
        "detail": detail,
        "dashboard": dashboard,
        "metrics": metrics,
        "image_paths": image_paths,
        "total_duration": total_duration,
        "pause_duration": pause_duration,
        "efficiency": efficiency,
        "real_read_time": real_read_time,
        "goal": goal,
        "goal_rate": goal_rate,
        "current_streak": current_streak,
        "average_daily": average_daily,
    }


# ══════════════════════════════════════════════════════════
#  用户消息构建
# ══════════════════════════════════════════════════════════

def _build_user_content(raw: dict) -> list[dict]:
    detail = raw["detail"]
    dashboard = raw["dashboard"]
    metrics = raw["metrics"]
    image_paths = raw["image_paths"]

    content: list[dict] = []

    text_parts = [
        f"## 朗读原始数据 · {raw['date']}",
        "",
        "### 📋 基础数据",
        f"- 日期：{detail.get('date', raw['date'])}",
        f"- 总朗读时长：{raw['total_duration']:.0f} 秒",
        f"- 停顿时长：{raw['pause_duration']:.0f} 秒",
        f"- 真实朗读时长：{raw['real_read_time']:.0f} 秒",
        f"- 朗读效率：{raw['efficiency']:.1%}",
        f"- 目标完成度：{detail.get('completion', '--')}",
        f"- 最大音量：{detail.get('max_volume', 0)} dB",
        f"- 平均音量：{detail.get('avg_volume', 0):.1f} dB",
        f"- 同比昨日：{detail.get('compare_yesterday', '--')}",
        "",
        "### 🎤 音频分析指标（原始数值）",
        f"- 语音占比 (VAD)：{metrics.get('vad_speech_ratio', 0):.3f}",
        f"- 全局信噪比 (SNR)：{metrics.get('global_snr_db', 0):.1f} dB",
        f"- 平均频谱熵：{metrics.get('mean_spectral_entropy', 0):.3f}",
        f"- 平均峰值因子：{metrics.get('mean_crest_db', 0):.1f} dB",
        f"- RMS 均值：{metrics.get('rms_mean', 0):.4f}",
        f"- RMS 标准差：{metrics.get('rms_std', 0):.4f}",
        f"- RMS 变异系数：{metrics.get('rms_cv', 0):.3f}",
        f"- 平均过零率 (ZCR)：{metrics.get('mean_zcr', 0):.3f}",
        f"- F0 均值（基频）：{metrics.get('f0_mean', 0):.1f} Hz",
        f"- F0 标准差：{metrics.get('f0_std', 0):.1f}",
        f"- F0 变异系数：{metrics.get('f0_cv', 0):.3f}",
        "",
        "### 📊 坚持力数据",
        f"- 当前连续打卡：{raw['current_streak']} 天",
        f"- 累计朗读天数：{dashboard.get('total_days', 0)} 天",
        f"- 历史最长连续：{dashboard.get('max_streak', 0)} 天",
        f"- 平均每日时长：{raw['average_daily']:.0f} 秒",
        f"- 目标完成率：{raw['goal_rate']:.1%}",
        "",
        "以下是该日朗读录音的音频分析图表，请结合图表和上述原始数据进行综合评估：",
    ]
    content.append({"type": "input_text", "text": "\n".join(text_parts)})

    for path in image_paths:
        b64 = _encode_image_to_base64(path)
        if b64:
            content.append({"type": "input_image", "image_url": b64})

    return content


# ══════════════════════════════════════════════════════════
#  核心：调用 LLM 生成报告
# ══════════════════════════════════════════════════════════

def generate_llm_report(
    account: str,
    date_str: str,
    force_refresh: bool = False,
    on_progress: Any = None,
) -> dict:
    """
    自行收集原始数据，调用 LLM 生成 AI 语音评估报告。

    Args:
        account:       当前账号（base64 编码的用户名）
        date_str:      目标日期，如 "2026-07-04"
        force_refresh: 是否强制刷新缓存
        on_progress:   可选进度回调 callback(status_text: str)

    Returns:
        dict: {"date", "report_text", "llm_response", "error", "image_paths", "metrics_summary", ...}
    """
    cfg = get_llm_config()

    if not cfg.get("llm_enabled", True):
        return {"error": "LLM 报告功能未启用", "report_text": ""}
    if not cfg.get("llm_api_key"):
        return {"error": "未配置 API Key", "report_text": ""}
    if not cfg.get("llm_base_url"):
        return {"error": "未配置 Base URL", "report_text": ""}
    if not cfg.get("llm_model"):
        return {"error": "未配置模型名称", "report_text": ""}

    # ── 检查缓存 ──
    cache_dir = f"./details/{account}/{date_str}"
    os.makedirs(cache_dir, exist_ok=True)
    cache_path = os.path.join(cache_dir, "llm_report_cache.json")

    if not force_refresh and os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached = json.load(f)
            if cached.get("date") == date_str and cached.get("error") is None:
                return cached
        except Exception:
            pass

    if on_progress:
        try:
            on_progress("⏳ 正在收集原始数据...")
        except Exception:
            pass

    # ── 收集原始数据 ──
    try:
        raw = _collect_raw_data(account, date_str, force_refresh=force_refresh)
    except Exception as e:
        traceback.print_exc()
        return {"error": f"数据收集失败：{str(e)[:200]}", "report_text": "", "date": date_str}

    if on_progress:
        try:
            on_progress("⏳ 正在调用 AI 模型分析朗读数据...")
        except Exception:
            pass

    # ── 调用 LLM ──
    system_prompt = _build_system_prompt()
    user_content = _build_user_content(raw)

    llm_result = None
    error_msg = None

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=cfg["llm_api_key"],
            base_url=cfg["llm_base_url"],
        )

        response = client.responses.create(
            model=cfg["llm_model"],
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},  # type: ignore[arg-type]
            ],
            extra_body={"enable_thinking": True},
        )

        for item in response.output:
            if getattr(item, "type", None) == "message":
                content_list = getattr(item, "content", [])
                if content_list:
                    first_content = content_list[0]
                    llm_result = getattr(first_content, "text", None)
                    if llm_result:
                        break

        if llm_result is None:
            error_msg = "LLM 返回了空的响应"
        else:
            llm_result = _extract_json(str(llm_result))

    except Exception as e:
        traceback.print_exc()
        error_msg = f"LLM 调用失败：{str(e)[:300]}"

    # ── 解析 JSON ──
    json_data = None
    if llm_result:
        try:
            json_data = json.loads(llm_result)
        except json.JSONDecodeError:
            error_msg = f"LLM 返回格式无法解析为 JSON，原始响应：{llm_result[:500]}"

    report_text = ""
    if json_data and not error_msg:
        report_text = _format_llm_report_text(json_data, date_str)
    elif error_msg:
        report_text = f"## ❌ AI 报告生成失败\n\n{error_msg}"

    # ── metrics_summary ──
    metrics = raw["metrics"]
    detail = raw["detail"]
    dashboard = raw["dashboard"]
    metrics_summary = "\n".join([
        "## 📈 朗读数据摘要", "",
        f"- 📅 日期：{date_str}",
        f"- ⏱ 总朗读时长：{raw['total_duration']:.0f} 秒",
        f"- ⏸ 停顿总时长：{raw['pause_duration']:.0f} 秒",
        f"- 📊 朗读效率：{raw['efficiency']:.1%}",
        f"- 🎯 目标完成度：{detail.get('completion', '--')}",
        f"- 🔊 最大音量：{detail.get('max_volume', 0)} dB",
        f"- 📢 平均音量：{detail.get('avg_volume', 0):.1f} dB",
        f"- 📅 同比昨日：{detail.get('compare_yesterday', '--')}",
        "",
        "### 综合数据",
        f"- 📚 累计朗读天数：{dashboard.get('total_days', 0)} 天",
        f"- 🔥 当前连续打卡：{raw['current_streak']} 天",
        f"- 🏅 历史最长连续：{dashboard.get('max_streak', 0)} 天",
        f"- 📈 平均每日时长：{raw['average_daily']:.0f} 秒",
        f"- 📊 平均效率：{dashboard.get('average_efficiency', 0):.1%}",
        "",
        "### 音频指标",
        f"- 语音占比：{metrics.get('vad_speech_ratio', 0):.3f}",
        f"- 全局信噪比：{metrics.get('global_snr_db', 0):.3f}",
        f"- 平均频谱熵：{metrics.get('mean_spectral_entropy', 0):.3f}",
        f"- 平均峰值因子：{metrics.get('mean_crest_db', 0):.3f}",
        f"- RMS 变异系数：{metrics.get('rms_cv', 0):.3f}",
        f"- 平均过零率：{metrics.get('mean_zcr', 0):.3f}",
        f"- F0 变异系数：{metrics.get('f0_cv', 0):.3f}",
    ])

    result = {
        "date": date_str,
        "report_text": report_text,
        "llm_response": json_data,
        "error": error_msg,
        "image_paths": raw["image_paths"],
        "metrics_summary": metrics_summary,
        "detail_data": detail,
        "dashboard_data": dashboard,
    }

    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    if on_progress:
        try:
            on_progress("✅ AI 报告生成完成" if not error_msg else f"❌ {error_msg[:100]}")
        except Exception:
            pass

    return result


# ══════════════════════════════════════════════════════════
#  辅助函数
# ══════════════════════════════════════════════════════════

def _extract_json(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines)
    return text.strip()


def _format_llm_report_text(json_data: dict, date_str: str) -> str:
    score = json_data.get("评分", {})
    analysis = json_data.get("分析", {})
    summary = json_data.get("总结", {})

    lines = [
        f"## 📊 AI 综合评分：{score.get('综合评分', '--')}/100",
        "",
        f"## 🏆 等级：{score.get('等级', '--')}",
        "",
        "### 📋 各维度评分",
        "| 维度 | 评分 | 简评 |",
        "|------|------|------|",
    ]

    dim_analysis = analysis.get("维度分析", {})
    for dim_name in ["流畅度", "音质清晰度", "音量控制", "表现力", "坚持力"]:
        dim_score = score.get(dim_name, "--")
        dim_comment = dim_analysis.get(dim_name, "--")
        short = dim_comment[:60] + "..." if len(dim_comment) > 60 else dim_comment
        lines.append(f"| {dim_name} | {dim_score}/20 | {short} |")

    highlights = analysis.get("亮点", [])
    if highlights:
        lines.append("")
        lines.append("### 💡 亮点")
        for item in highlights:
            lines.append(f"- {item}")

    improvements = analysis.get("待改进", [])
    if improvements:
        lines.append("")
        lines.append("### ⚠ 待改进")
        for item in improvements:
            lines.append(f"- {item}")

    if dim_analysis:
        lines.append("")
        lines.append("### 🔍 维度详细分析")
        for dim_name in ["流畅度", "音质清晰度", "音量控制", "表现力", "坚持力"]:
            if dim_name in dim_analysis:
                lines.append(f"**{dim_name}**：{dim_analysis[dim_name]}")

    suggestions = summary.get("建议", [])
    if suggestions:
        lines.append("")
        lines.append("### 🎯 建议")
        for item in suggestions:
            lines.append(f"- {item}")

    encouragement = summary.get("鼓励", "")
    if encouragement:
        lines.append("")
        lines.append("### 🌟 鼓励")
        lines.append(f"> {encouragement}")

    return "\n".join(lines)


__all__ = ["get_llm_config", "generate_llm_report"]
