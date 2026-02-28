"""
web_tts.py —— edge-tts CLI + edge_playback 网络语音合成封装。
"""
import os
import subprocess
import platform
import tempfile
import threading

try:
    from edge_playback.win32_playback import play_mp3_win32
except ImportError:
    play_mp3_win32 = None


def _build_rate_str(speed):
    try:
        return f"{int(float(speed) * 100):+d}%"
    except Exception:
        return "+0%"


def _build_vol_str(volume):
    try:
        return f"{int(float(volume) * 100):+d}%"
    except Exception:
        return "+0%"


def _run_edge_tts_cli(text, volume, speed, voice_name, output_path):
    """运行 edge-tts CLI 生成音频文件，返回是否成功。"""
    cmd = [
        "edge-tts",
        "-t", str(text),
        "--write-media", output_path,
        f"--rate={_build_rate_str(speed)}",
        f"--volume={_build_vol_str(volume)}",
    ]
    if voice_name:
        cmd += ["--voice", str(voice_name)]

    startupinfo = None
    if platform.system() == "Windows":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        proc = subprocess.run(cmd, check=True, timeout=60, startupinfo=startupinfo, capture_output=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"edge-tts failed: {e}")
        return False
    except Exception as e:
        print(f"edge-tts error: {e}")
        return False


def _play_web_tts_thread(text, volume, speed, voice_name, on_finish=None):
    """在当前线程中生成临时音频并播放（适合新线程调用）。"""
    if play_mp3_win32 is None:
        print("edge_playback not available")
        if on_finish:
            on_finish()
        return

    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    try:
        ok = _run_edge_tts_cli(text, volume, speed, voice_name, path)
        if not ok:
            return
        try:
            play_mp3_win32(path)
        except Exception as e:
            print(f"Error playing generated media: {e}")
    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        if on_finish:
            on_finish()


def play_cached_web_tts(text, volume, speed, output_path):
    """
    如果缓存文件已存在则直接播放，否则先生成再播放。
    在后台线程中处理生成步骤，返回后立即回到调用方。
    """
    if play_mp3_win32 is None:
        print("edge_playback not available for web TTS")
        return

    if os.path.exists(output_path):
        try:
            play_mp3_win32(output_path)
        except Exception as e:
            print(f"Playback error (cached): {e}")
        return

    def _generate_and_play():
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        ok = _run_edge_tts_cli(text, volume, speed, voice_name=None, output_path=output_path)
        if ok:
            try:
                t = threading.Thread(target=play_mp3_win32, args=(output_path,))
                t.start()
            except Exception as e:
                print(f"Playback error: {e}")

    threading.Thread(target=_generate_and_play).start()


async def test_tts(args: list, current_account, on_finish=None):
    """语音生成器测试（GUI 回调用）。"""
    source = args[4] if len(args) > 4 else "local"
    if source == "web":
        if play_mp3_win32 is None:
            if on_finish:
                on_finish()
            return "edge_playback library is missing or not supported on this platform."
        try:
            t = threading.Thread(
                target=_play_web_tts_thread,
                args=(str(args[0]), float(args[1]), float(args[2]), str(args[3]), on_finish),
            )
            t.start()
            return "ok"
        except Exception as e:
            if on_finish:
                on_finish()
            return str(e)
    elif source == "local":
        from .local_tts import speak
        ok, err = speak(text=str(args[0]), volume=float(args[1]), speed=float(args[2]), voice_name=str(args[3]))
        if on_finish:
            on_finish()
        return "ok" if ok else (err or "unknown error")
    if on_finish:
        on_finish()
    return "unknown source"
