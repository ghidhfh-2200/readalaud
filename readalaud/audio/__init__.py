"""
audio 子包 —— 音频播放、数据统计与深度分析。

Heavy analysis/chart modules are imported lazily to keep application startup fast.
"""


def bind_audio_analasy_api(*args, **kwargs):
    from .playback import bind_audio_analasy_api as _bind_audio_analasy_api

    return _bind_audio_analasy_api(*args, **kwargs)


def run_selected_analyses(*args, **kwargs):
    from .analysis_engine import run_selected_analyses as _run_selected_analyses

    return _run_selected_analyses(*args, **kwargs)


def generate_llm_report(*args, **kwargs):
    from .llm_report import generate_llm_report as _generate_llm_report

    return _generate_llm_report(*args, **kwargs)


def get_llm_config(*args, **kwargs):
    from .llm_report import get_llm_config as _get_llm_config

    return _get_llm_config(*args, **kwargs)


def __getattr__(name):
    if name in {"ANALYSIS_ITEMS", "ANALYSIS_DESCRIPTIONS"}:
        from . import analysis_engine

        return getattr(analysis_engine, name)
    raise AttributeError(name)


__all__ = [
    "bind_audio_analasy_api",
    "run_selected_analyses",
    "ANALYSIS_ITEMS",
    "ANALYSIS_DESCRIPTIONS",
    "generate_llm_report",
    "get_llm_config",
]
