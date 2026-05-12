"""
ui_thread.py —— UI 更新线程：将后台数据线程的更新安全推送到 Tkinter。
"""
import datetime
import queue as queue_module


def ui_thread(ui_queue, state_label, information_label_list):
    while True:
        try:
            msg = ui_queue.get()
            msg_type = msg.get("type")

            if msg_type == "stop":
                state_label.after(0, lambda: state_label.config(text="已停止"))
                break

            if msg_type == "update":
                main_text = msg.get("main_label_text")
                info = msg.get("info_data")

                if main_text:
                    state_label.after(0, lambda t=main_text: state_label.config(text=t))

                if info:
                    texts = [
                        f"剩余时长: {datetime.timedelta(seconds=int(info['left']))}",
                        f"停顿总时长: {datetime.timedelta(seconds=int(info['stop_total']))}",
                        f"有效朗读时间: {datetime.timedelta(seconds=int(info['real_read_time']))}",
                        f"总时长: {datetime.timedelta(seconds=int(info['total']))}",
                        f"最大音量: {info['max_sound']}",
                        f"效率: {info['efficiency']}",
                    ]
                    for i, label in enumerate(information_label_list):
                        if i < len(texts):
                            state_label.after(0, lambda lb=label, tx=texts[i]: lb.configure(text=tx))

        except Exception as e:
            print(f"Error in ui_thread: {e}")
            break
