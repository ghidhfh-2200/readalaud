from . import gui, auth, settings, tts,reading,calibration,server,server_manager, audio_analasy


class ReadAlaud:
    """
    核心类，储存状态并对外暴露入口方法。
    """

    def __init__(self):
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

        self.font=("微软雅黑", 17)
        self.mainpage_button_font = ("微软雅黑", 12)
        self.all_web_voices = None
        self.all_local_voices = None

        # 绑定模块方法到实例上
        gui.bind_gui(self)
        auth.bind_auth(self)
        settings.bind_settings(self)
        tts.bind_tts(self)
        reading.bind_reading_api(self)
        audio_analasy.bind_audio_analasy_api(self)
        calibration.bind_calibration_api(self)
        server.bind_server_api(self)
        server_manager.bind_server_manager_api(self)
        # login StringVars will be created when the GUI root exists (in _generate_main_window)
        self.login_password_enter = None
        self.login_acount_enter = None
        self.if_generating_ttstest = False

