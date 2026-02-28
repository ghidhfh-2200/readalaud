"""
webview_process.py —— 启动独立子进程运行 pywebview 校准窗口。
"""
import json
import os
import pathlib
from multiprocessing import get_context

_abs_path = pathlib.Path(__file__).resolve()
_HTML_FILE = str(_abs_path.parent.parent.parent / "web" / "calibration.html")


def bind_calibration_api(instance):
    instance.start_calibration = lambda: start_calibration(instance)


def _start_webview(queue, queue_state, current_acount):
    import webview
    from .calibration_api import CalibrationAPI

    with open(f"./data/{current_acount}/settings.json", "r") as f:
        read_json = json.load(f)
    get_calibration = read_json["calibration"]
    write_temp = {"calibration": get_calibration, "threshold": 0}
    with open("./temp.json", "w") as f:
        json.dump(write_temp, f)

    abs_path = os.path.abspath(_HTML_FILE)
    url = f"file://{abs_path}"
    webview.create_window(
        "语音可视化",
        url,
        width=800,
        height=600,
        js_api=CalibrationAPI(current_acount),
    )
    webview.start(gui="tkinter", debug=False)


def start_calibration(self):
    current_acount = getattr(self, "current_acount", None)
    if not current_acount:
        raise ValueError("current_acount is not set on the caller instance")
    ctx = get_context("spawn")
    self.queue = ctx.Queue()
    self.queue_state = ctx.Queue()
    self.process = ctx.Process(
        target=_start_webview,
        args=(self.queue, self.queue_state, current_acount),
    )
    self.process.start()
