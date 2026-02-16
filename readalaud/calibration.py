import webview
import os
from multiprocessing import Process, Queue, get_context
import time
import json

def bind_calibration_api(instance):
    instance.start_calibration = lambda: start_calibration(instance)

HTML_FILE = "web/calibration.html"
def start_webview(queue, queue_state, current_acount):
    with open(f"./data/{current_acount}/settings.json", "r") as f:
        read_json = json.load(f)
    get_calibration = read_json['calibration']
    write_temp = {"calibration": get_calibration, "threshold": 0}
    with open("./temp.json","w") as f:
        json.dump(write_temp, f)
    abs_path = os.path.abspath(HTML_FILE)
    url = f"file://{abs_path}"

    # 让 pywebview 嵌入到新窗口
    webview.create_window(
        "语音可视化",
        url,
        width=800,
        height=600,
        js_api=Calibration_API(current_acount),
    )
    webview.start(gui='tkinter', debug=False)

def start_calibration(self):
    ctx = get_context("spawn")
    # 修正属性名：确保你的实例属性是 current_acount（原代码写 current_acount 可能是笔误）
    current_acount = getattr(self, "current_acount", None)
    if not current_acount:
        # 处理找不到账户名的情况
        raise ValueError("current_acount is not set on the caller instance")

    self.queue = ctx.Queue()
    self.queue_state = ctx.Queue()
    # 传递 current_acount 给子进程
    self.process = ctx.Process(target=start_webview, args=(self.queue, self.queue_state, current_acount))
    self.process.start()

class Calibration_API:
    def __init__(self, current_acount):
        self.current_acount = current_acount

    def receive_msg(self, msg):
        print(f"RECEIVE MSG:{msg}")
        # 使用 os.path.join 是更安全的路径组合
        settings_path = os.path.join(".", "data", self.current_acount, "settings.json")
        with open(settings_path, "r", encoding="utf-8") as f:
            read_json = json.load(f)
        read_json['calibration'] = msg
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(read_json, f, ensure_ascii=False, indent=2)
        return "200"

    def destroy_window(self):
        time.sleep(2)
        if webview.windows:
            webview.windows[0].destroy()
        temp = {"calibration": 94, "threshold": 0}
        with open("./temp.json", "w") as f:
            json.dump(temp, f)
        return "closed"