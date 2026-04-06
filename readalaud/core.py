from . import gui
from .auth import bind_auth
from .settings import bind_settings
from .tts import bind_tts
from .reading import bind_reading_api
from .audio import bind_audio_analasy_api
from .calibration import bind_calibration_api
from .server import bind_server_api, bind_server_manager_api
from .logger import bind_logger_api, init_db
from .gui.gui_service import get_gui_service


class ReadAlaud:
    """
    核心类，储存状态并对外暴露入口方法。
    """

    def __init__(self):
        init_db()  # 初始化日志数据库
        try:
            from .logger.log_manager import log_system
            log_system("初始化核心对象", "ReadAlaud.__init__ start")
        except Exception:
            pass
        # 状态变量
        self.if_main_window_show = True
        self.if_settings_show = False
        self.if_reading_show = False
        self.if_calibration_show = False
        self.if_data_form_show = False
        self.if_login_show = False
        self.if_logged_in = False
        self.if_all_voices_window_showed = False
        self.current_acount = ""
        self.if_time_and_text_config_popup = False
        self.if_reading = False
        self.if_audio_analysis_running = False
        # backward-compatibility: historical typo used in data_gui
        self.if_audio_analasy_running = False

        self.font = ("微软雅黑", 17)
        self.mainpage_button_font = ("微软雅黑", 12)
        self.all_web_voices = None
        self.all_local_voices = None
        self.gui = get_gui_service(self)

        # 绑定模块方法到实例上
        gui.bind_gui(self)
        bind_auth(self)
        bind_settings(self)
        bind_tts(self)
        bind_reading_api(self)
        bind_audio_analasy_api(self)
        bind_calibration_api(self)
        bind_server_api(self)
        bind_server_manager_api(self)
        bind_logger_api(self)
        self.log_operation("模块绑定完成", "auth/settings/tts/reading/audio/calibration/server/logger")
        # login StringVars will be created when the GUI root exists (in _generate_main_window)
        self.login_password_enter = None
        self.login_acount_enter = None
        self.if_generating_ttstest = False

