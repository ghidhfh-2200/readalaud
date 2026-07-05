"""Backward-compatible lazy facade for the audio package."""


def bind_audio_analasy_api(*args, **kwargs):
    from .audio import bind_audio_analasy_api as _bind_audio_analasy_api

    return _bind_audio_analasy_api(*args, **kwargs)


def run_selected_analyses(*args, **kwargs):
    from .audio.analysis_engine import run_selected_analyses as _run_selected_analyses

    return _run_selected_analyses(*args, **kwargs)


def stop_day_audio(*args, **kwargs):
    from .audio.playback import stop_day_audio as _stop_day_audio

    return _stop_day_audio(*args, **kwargs)


def play_day_audio(*args, **kwargs):
    from .audio.playback import play_day_audio as _play_day_audio

    return _play_day_audio(*args, **kwargs)


def pause_day_audio(*args, **kwargs):
    from .audio.playback import pause_day_audio as _pause_day_audio

    return _pause_day_audio(*args, **kwargs)


def seek_day_audio(*args, **kwargs):
    from .audio.playback import seek_day_audio as _seek_day_audio

    return _seek_day_audio(*args, **kwargs)


def get_audio_duration(*args, **kwargs):
    from .audio.playback import get_audio_duration as _get_audio_duration

    return _get_audio_duration(*args, **kwargs)


def refresh_dashboard_data(*args, **kwargs):
    from .audio.dashboard import refresh_dashboard_data as _refresh_dashboard_data

    return _refresh_dashboard_data(*args, **kwargs)


def get_available_months(*args, **kwargs):
    from .audio.dashboard import get_available_months as _get_available_months

    return _get_available_months(*args, **kwargs)


def get_daily_records_by_month(*args, **kwargs):
    from .audio.dashboard import get_daily_records_by_month as _get_daily_records_by_month

    return _get_daily_records_by_month(*args, **kwargs)


def fetch_for_daily_data(*args, **kwargs):
    from .audio.daily_detail import fetch_for_daily_data as _fetch_for_daily_data

    return _fetch_for_daily_data(*args, **kwargs)


def generate_reading_report(*args, **kwargs):
    from .audio.report import generate_reading_report as _generate_reading_report

    return _generate_reading_report(*args, **kwargs)


def __getattr__(name):
    if name in {"ANALYSIS_ITEMS", "ANALYSIS_DESCRIPTIONS"}:
        from .audio import analysis_engine

        return getattr(analysis_engine, name)
    raise AttributeError(name)


__all__ = [
    "bind_audio_analasy_api",
    "run_selected_analyses",
    "ANALYSIS_ITEMS",
    "ANALYSIS_DESCRIPTIONS",
    "stop_day_audio",
    "play_day_audio",
    "pause_day_audio",
    "seek_day_audio",
    "get_audio_duration",
    "refresh_dashboard_data",
    "get_available_months",
    "get_daily_records_by_month",
    "fetch_for_daily_data",
    "generate_reading_report",
]
