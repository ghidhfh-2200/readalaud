"""
tts_settings.py —— TTS 语音提示配置的保存与缓存清理。
"""
import json
import os
import re

DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}


def _extract_first_number(text, default=0.0):
    m = re.search(r"[-+]?\d+(?:\.\d+)?", str(text))
    if not m:
        return float(default)
    try:
        return float(m.group(0))
    except Exception:
        return float(default)


def _parse_trigger_display(display_text):
    display_text = str(display_text or "").strip()
    if not display_text:
        return "当时间点达到", "0", "当时间点达到 0 分钟"

    if display_text.startswith("当音量达到"):
        n = _extract_first_number(display_text, 0.0)
        return "当音量达到", str(n), f"当音量达到 {n} DB"
    if display_text.startswith("当音量低于"):
        n = _extract_first_number(display_text, 0.0)
        return "当音量低于", str(n), f"当音量低于 {n} DB"
    if display_text.startswith("当达到目标"):
        return "当达到目标", "0", "当达到目标"
    if display_text.startswith("当时间点达到"):
        n = _extract_first_number(display_text, 0.0)
        return "当时间点达到", str(n), f"当时间点达到 {n} 分钟"
    if display_text.startswith("当任务进度达到"):
        n = _extract_first_number(display_text, 0.0)
        return "当任务进度达到", str(n), f"当任务进度达到 {n} %"
    if display_text.startswith("检测到异常停顿"):
        n = _extract_first_number(display_text, 0.0)
        return "检测到异常停顿", str(n), f"检测到异常停顿 {n} 秒"

    parts = display_text.split()
    if len(parts) >= 2:
        return parts[0], str(_extract_first_number(parts[1], 0.0)), display_text
    return display_text, "0", display_text


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
            for i, row in enumerate(args[1]):
                row = list(row)
                while len(row) < 6:
                    row.append("")
                condition, value, display = _parse_trigger_display(row[0])
                source = row[5] or "local"
                write_list[i] = {
                    "condition": condition,
                    "value":     value,
                    "display":   display,
                    "text":      row[1],
                    "rate":      row[2],
                    "volume":    row[3],
                    "voice":     row[4],
                    "source":    source,
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

        # 先清理被删除条目的音频文件
        old_keys = {str(k) for k in old_config.keys()}
        new_keys = {str(k) for k in new_config.keys()}
        removed_keys = old_keys - new_keys
        for str_i in removed_keys:
            for ext in [".wav", ".mp3"]:
                file_path = f"./data/{self.current_acount}/tts/{str_i}{ext}"
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
                        self.log_error("清理TTS缓存失败", f"{file_path}: {e}")
                        print(f"Error deleting file {file_path}: {e}")

        for i, new_val in new_config.items():
            str_i = str(i)
            if str_i not in old_config:
                continue

            old_val = old_config[str_i]
            old_source = str(old_val.get("source", "local"))
            new_source = str(new_val.get("source", "local"))

            # 自定义音频由用户手工上传/录制，不应因普通配置变更被误删
            if new_source in ("custom_upload", "custom_record", "custom") and old_source in ("custom_upload", "custom_record", "custom"):
                continue

            if old_val != new_val:
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
