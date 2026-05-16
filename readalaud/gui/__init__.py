"""
gui 子包 —— 将原 gui.py 按功能拆分为多个模块。

模块说明：
  - main_window.py   : 主窗口创建、欢迎页、窗口切换导航
  - login_gui.py     : 登录 / 注册页面
  - settings_gui.py  : 设置页面（朗读设置、账号、个性化、疑难解答）
  - tts_gui.py       : TTS 语音提示相关辅助（音色窗口、添加/删除/测试、条件配置弹窗）
  - reading_gui.py   : 朗读页面
  - data_gui.py      : 数据统计与图表页面
"""

from .main_window import (
  _generate_main_window,
  check_if_reading,
  _welcome_page,
  _start_sidebar_today_status_monitor,
  _stop_sidebar_today_status_monitor,
)
from .login_gui import (
  _generate_login_gui,
  _set_login_status,
  _start_login_lock_countdown,
  _stop_login_lock_countdown,
)
from .settings_gui import _generate_settings_gui
from .tts_gui import (
    _enable_or_disable_tts_gui,
    _get_web_voice,
    _generate_more_vloices_window,
    _destroy_all_voices_window,
    _tts_add_point,
    _tts_delete_point,
    _pop_up_time_and_text_config_window,
  _on_tts_mode_changed,
  _on_custom_mode_changed,
  _run_custom_action,
  _get_selected_tts_row_id,
  _get_tts_row_values,
  _set_tts_row_values,
)
from .reading_gui import _generate_reading_gui
from .data_gui import _generate_data_gui


def bind_gui(instance):
    """把 GUI 相关的方法绑定到 ReadAlaud 实例上。"""
    instance.generate_main_window = lambda: _generate_main_window(instance)
    instance.welcome_page = lambda destroy_window: _welcome_page(instance, destroy_window)
    instance._start_sidebar_today_status_monitor = lambda: _start_sidebar_today_status_monitor(instance)
    instance._stop_sidebar_today_status_monitor = lambda reset=True: _stop_sidebar_today_status_monitor(instance, reset=reset)
    instance.generate_login_gui = lambda: _generate_login_gui(instance)
    instance.set_login_status = lambda message, level="info": _set_login_status(instance, message, level)
    instance.start_login_lock_countdown = lambda encoded_account, locked_until_ts: _start_login_lock_countdown(instance, encoded_account, locked_until_ts)
    instance.stop_login_lock_countdown = lambda: _stop_login_lock_countdown(instance)
    instance.generate_settings_gui = lambda: _generate_settings_gui(instance)
    instance.generate_reading_gui = lambda: _generate_reading_gui(instance)
    instance.enable_or_disable_tts_gui = lambda state=None: _enable_or_disable_tts_gui(instance, state)
    instance.get_web_voice = lambda: _get_web_voice(instance)
    instance.generate_more_vloices_window = lambda source: _generate_more_vloices_window(instance, source)
    instance.destroy_all_voices_window = lambda window=None: _destroy_all_voices_window(instance)
    instance.tts_add_point = lambda: _tts_add_point(instance)
    instance.tts_delete_point = lambda: _tts_delete_point(instance)
    instance.pop_up_time_and_text_config_window = lambda: _pop_up_time_and_text_config_window(instance)
    instance.on_tts_mode_changed = lambda event=None: _on_tts_mode_changed(instance, event)
    instance.on_custom_mode_changed = lambda event=None: _on_custom_mode_changed(instance, event)
    instance.run_custom_tts_action = lambda: _run_custom_action(instance)
    instance._get_selected_tts_row_id = lambda: _get_selected_tts_row_id(instance)
    instance._get_tts_row_values = lambda row: _get_tts_row_values(instance, row)
    instance._set_tts_row_values = lambda row, values: _set_tts_row_values(instance, row, values)
    instance.generate_data_gui = lambda: _generate_data_gui(instance)
