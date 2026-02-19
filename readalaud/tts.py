import pyttsx3
import edge_tts
import asyncio
import threading
import tempfile
import os
import subprocess
try:
    from edge_playback.win32_playback import play_mp3_win32
except ImportError:
    play_mp3_win32 = None

def bind_tts(instance):
    # bind web-voice fetcher
    instance.get_web_voice = _get_web_voice
    # Do not override GUI-provided generate_more_vloices_window if it already exists.
    if not hasattr(instance, 'generate_more_vloices_window'):
        instance.generate_more_vloices_window = lambda source: None  # GUI may override this


async def _get_web_voice():
    try:
        return await edge_tts.list_voices()
    except Exception:
        return []


def get_web_voices():
    voices = []
    def _run():
        nonlocal voices
        try:
            voices = asyncio.run(_get_web_voice())
        except Exception:
            voices = []

    thread = threading.Thread(target=_run)
    thread.start()
    thread.join()
    return voices


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


def _resolve_pyttsx3_voice(voice_name):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")
    except Exception:
        return None
    for v in voices:
        if getattr(v, "id", None) == voice_name or getattr(v, "name", None) == voice_name:
            return v.id
    return None


def speak(text: str, volume: float, speed: float, voice_name: str):
    try:
        engine = pyttsx3.init()
        if voice_name:
            voice_id = _resolve_pyttsx3_voice(voice_name)
            if voice_id:
                engine.setProperty(name="voice", value=voice_id)

        base_rate = engine.getProperty(name="rate")
        engine.setProperty("rate", int(base_rate + 200 * float(speed)))
        engine.setProperty("volume", _clamp(abs(float(volume)), 0.0, 1.0))
        engine.say(str(text))
        engine.runAndWait()
        return True, None
    except Exception as e:
        return False, str(e)


def _play_web_tts_thread(text, volume, speed, voice_name, on_finish=None):
    if play_mp3_win32 is None:
        print("edge_playback not available")
        if on_finish:
            on_finish()
        return

    # prepare CLI-style rate/volume arguments (e.g. "+10%")
    try:
        vol_str = f"{int((float(volume)) * 100):+d}%"
    except Exception:
        vol_str = "+0%"
    try:
        rate_str = f"{int((float(speed)) * 100):+d}%"
    except Exception:
        rate_str = "+0%"

    # generate temp output file (keep .mp3 so play_mp3_win32 can play it)
    fd, path = tempfile.mkstemp(suffix=".mp3")
    os.close(fd)

    # build command line as list
    cmd = ["edge-tts", "-t", str(text), "--write-media", path, "--rate", rate_str, "--volume", vol_str]
    print(cmd)
    proc = None
    try:
        # run the edge-tts CLI (timeout to avoid hanging indefinitely)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print("edge-tts command timed out")
        proc = None
    except Exception as e:
        print(f"Failed to run edge-tts: {e}")
        proc = None

    try:
        if proc is None:
            return
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip()
            print(f"edge-tts failed (code {proc.returncode}): {stderr}")
            return

        # playback generated file
        try:
            play_mp3_win32(path)
        except Exception as e:
            print(f"Error playing generated media: {e}")
    finally:
        # cleanup temp file
        if os.path.exists(path):
            try:
                os.remove(path)
            except Exception:
                pass
        if on_finish:
            on_finish()


async def test_tts(args:list, current_account, on_finish=None):
    """
    语音生成器测试脚本
    """
    if args[4] == "web":
        if play_mp3_win32 is None:
            if on_finish:
                on_finish()
            return "edge_playback library is missing or not supported on this platform."
        try:
            t = threading.Thread(target=_play_web_tts_thread, args=(str(args[0]), float(args[1]), float(args[2]), str(args[3]), on_finish))
            t.start()
            return "ok"
        except Exception as e:
            if on_finish:
                on_finish()
            return str(e)
    elif args[4] == "local":
        ok, err = speak(text=str(args[0]), volume=float(args[1]), speed=float(args[2]), voice_name=str(args[3]))
        if on_finish:
            on_finish()
        return "ok" if ok else (err or "unknown error")
    if on_finish:
        on_finish()
    return "unknown source"