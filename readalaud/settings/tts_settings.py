"""
tts_settings.py —— TTS 语音提示配置的保存与缓存清理。
"""
import json
import os

DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}


def save_tts_settings(self, args):
    self.log_operation("调用保存TTS设置", f"if_tts={args[0] if args else 'unknown'}")
    try:
        settings_path = f"./data/{self.current_acount}/settings.json"
        with open(settings_path, "r") as f:
            read_settings = json.load(f)
        read_settings["if_tts"] = args[0]
        with open(settings_path, "w") as f:
            json.dump(read_settings, f)

        if args[0] == 0:
            self.enable_or_disable_tts_gui(state=False)
        elif args[0] == 1:
            self.enable_or_disable_tts_gui(state=True)
            write_list = {}
            for i in range(len(args[1])):
                write_list[i] = {
                    "condition": args[1][i][0].split(" ")[0],
                    "value":     args[1][i][0].split(" ")[1],
                    "text":      args[1][i][1],
                    "rate":      args[1][i][2],
                    "volume":    args[1][i][3],
                    "voice":     args[1][i][4],
                    "source":    args[1][i][5],
                }
            _clean_outdated_tts_cache(self, write_list)
            tts_config_path = f"./data/{self.current_acount}/tts_config.json"
            with open(tts_config_path, "w") as f:
                json.dump(write_list, f)
    except FileNotFoundError:
        self.log_error("保存TTS设置失败", "settings.json 不存在，已重建默认配置")
        settings_path = f"./data/{self.current_acount}/settings.json"
        with open(settings_path, "w") as f:
            json.dump(DEFAULT_SETTINGS.copy(), f)
        self.gui.info(message="无法找到你的设置文件！\n已自动重置，请重新完成所有设置!")
    except json.JSONDecodeError:
        self.log_error("保存TTS设置失败", "settings.json JSON 解析失败")
        self.gui.error(message="设置文件解析失败！\n请不要随意修改data文件夹中的文件！")


def _clean_outdated_tts_cache(self, new_config):
    """当 TTS 配置变更时，删除对应的旧缓存音频文件。"""
    tts_config_path = f"./data/{self.current_acount}/tts_config.json"
    try:
        with open(tts_config_path, "r") as f:
            old_config = json.load(f)
        for i, new_val in new_config.items():
            str_i = str(i)
            if str_i in old_config and old_config[str_i] != new_val:
                for ext in [".wav", ".mp3"]:
                    file_path = f"./data/{self.current_acount}/tts/{i}{ext}"
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            self.log_error("清理TTS缓存失败", f"{file_path}: {e}")
                            print(f"Error deleting file {file_path}: {e}")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
