"""
calibration_api.py —— pywebview 的 JS ↔ Python 桥接类。
"""
import json
import os
import time
import webview

from ..settings import update_setting


class CalibrationAPI:
    """通过 pywebview 暴露给 JavaScript 的 API 对象。"""

    def __init__(self, current_acount):
        self.current_acount = current_acount

    def receive_msg(self, msg):
        print(f"RECEIVE MSG:{msg}")
        update_setting("calibration", msg)
        return "200"

    def destroy_window(self):
        time.sleep(2)
        if webview.windows:
            webview.windows[0].destroy()
        temp = {"calibration": 94, "threshold": 0}
        with open("./temp.json", "w") as f:
            json.dump(temp, f)
        return "closed"
