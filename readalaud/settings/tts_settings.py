"""
tts_settings.py —— TTS 语音提示配置的缓存与异步保存。
"""
import json
import os
import re

from .settings_io import update_setting

DEFAULT_SETTINGS = {"goal": 0, "stop-dur": 0, "db-level": 0, "calibration": 94, "theme": "darkly", "if_tts": 0}

# ── TTS 配置缓存 ──────────────────────────────────────────

_tts_cache: dict = {}


def get_tts_cache() -> dict:
    return _tts_cache


def update_tts_cache(config: dict):
    global _tts_cache
    _tts_cache = config


def init_tts_cache(current_account: str) -> dict:
    """从磁盘加载 TTS 配置到缓存。"""
    global _tts_cache
    try:
        with open(f"./data/{current_account}/tts_config.json", "r") as f:
            _tts_cache = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        _tts_cache = {}
    return _tts_cache


# ── 解析触发条件 ──────────────────────────────────────────

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


# ── 即时更新缓存（不写磁盘） ───────────────────────────────

def save_tts_settings(self, args):
    """更新 TTS 缓存（UI 修改时调用，不写磁盘）。"""
    self.log_operation("调用更新TTS缓存", f"if_tts={args[0] if args else 'unknown'}")

    update_setting("if_tts", args[0])

    if args[0] == 0:
        self.enable_or_disable_tts_gui(state=False)
        _tts_cache.clear()
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
        _tts_cache.clear()
        _tts_cache.update(write_list)


# ── 退出时将 TTS 缓存落盘 ──────────────────────────────────

def save_tts_config_to_disk(current_account: str, config: dict):
    """将 TTS 配置写入磁盘，附带缓存清理（后台线程调用）。"""
    if not config or not current_account:
        return

    _clean_outdated_tts_cache(current_account, config)

    tts_config_path = f"./data/{current_account}/tts_config.json"
    try:
        with open(tts_config_path, "w") as f:
            json.dump(config, f)
    except Exception:
        pass


def _clean_outdated_tts_cache(current_account: str, new_config: dict):
    """当 TTS 配置变更时，删除对应的旧缓存音频文件。"""
    tts_config_path = f"./data/{current_account}/tts_config.json"
    try:
        with open(tts_config_path, "r") as f:
            old_config = json.load(f)

        # 先清理被删除条目的音频文件
        old_keys = {str(k) for k in old_config.keys()}
        new_keys = {str(k) for k in new_config.keys()}
        removed_keys = old_keys - new_keys
        for str_i in removed_keys:
            for ext in [".wav", ".mp3"]:
                file_path = f"./data/{current_account}/tts/{str_i}{ext}"
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                    except Exception as e:
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
                    file_path = f"./data/{current_account}/tts/{i}{ext}"
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                        except Exception as e:
                            print(f"Error deleting file {file_path}: {e}")
    except (FileNotFoundError, json.JSONDecodeError):
        pass
