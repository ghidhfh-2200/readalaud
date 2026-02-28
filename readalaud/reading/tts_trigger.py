"""
tts_trigger.py —— 朗读中 TTS 条件检查与触发。
"""
import os
import threading
import time


def check_tts_conditions(instance, tts_config, current_db, current_pause_duration,
                         left, total_stop, total, real_read_time, max_db, efficiency):
    """根据 tts_config 中的各条件，决定是否触发 TTS 播报。"""
    current_time = time.time()

    for index_key, config in tts_config.items():
        try:
            condition = config.get("condition")
            target_value = float(config.get("value", "0"))
            last_trigger = instance.tts_cooldowns.get(index_key, 0)

            should_trigger = False
            is_one_shot = False

            if condition == "当音量达到":
                if current_db >= target_value and current_time - last_trigger > 10:
                    should_trigger = True

            elif condition == "当音量低于":
                if current_db < target_value and current_time - last_trigger > 10:
                    should_trigger = True

            elif condition == "当达到目标":
                if left <= 0:
                    is_one_shot = True
                    should_trigger = True

            elif condition == "当时间点达到":
                target_seconds = target_value * 60
                if real_read_time >= target_seconds:
                    is_one_shot = True
                    should_trigger = True

            elif condition == "当任务进度达到":
                goal = float(instance.load_settings.get("goal", 0) or 0)
                if goal > 0 and (real_read_time / goal) * 100 >= target_value:
                    is_one_shot = True
                    should_trigger = True

            elif condition == "检测到异常停顿":
                if current_pause_duration >= target_value:
                    if current_time - last_trigger > (target_value + 10):
                        should_trigger = True

            if not should_trigger:
                continue
            if is_one_shot and index_key in instance.tts_triggered_events:
                continue

            instance.tts_cooldowns[index_key] = current_time
            if is_one_shot:
                instance.tts_triggered_events.add(index_key)

            source = config.get("source", "local")
            text = config.get("text", "")
            volume = config.get("volume", "1.0")
            rate = config.get("rate", "1.0")
            voice = config.get("voice", "")

            if source == "web":
                from readalaud.tts.web_tts import play_cached_web_tts
                account_dir = getattr(instance, "current_acount", "default")
                base_path = f"./data/{account_dir}/tts"
                file_path = os.path.abspath(os.path.join(base_path, f"{index_key}.mp3"))
                threading.Thread(
                    target=play_cached_web_tts,
                    args=(text, volume, rate, file_path),
                ).start()
            else:
                from readalaud.tts.local_tts import speak
                speak(text=str(text), volume=float(volume), speed=float(rate), voice_name=str(voice))

        except Exception as e:
            print(f"Error checking TTS condition {index_key}: {e}")
            continue
