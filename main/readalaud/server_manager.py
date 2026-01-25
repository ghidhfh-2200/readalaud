import tkinter as tk
import sys
import subprocess
import platform
import socket
import threading
import re
from tkinter import messagebox

def bind_server_manager_api(instance):
    instance.start_manager = lambda:start_manager(instance)
    instance.check_if_server_running = lambda:check_if_server_running()

def start_manager(self=None):
    if self != None:
        server_manager_window = tk.Toplevel(master=self.main_window)
    else:
        server_manager_window = tk.Tk()
    server_manager_window.title("服务器管理")
    server_manager_window.geometry("300x400")

    state_label_frame = tk.LabelFrame(master=server_manager_window, width=270, height=30, border=1, text="服务器状态")
    state_label_frame.pack(padx=5, pady=5, fill="x")
    self.state_label = tk.Label(master=state_label_frame, fg="black", text="正在查询...", font=(25))
    self.state_label.pack(anchor="center", fill="both")
    operation = tk.LabelFrame(master=server_manager_window, width=270,border=1,text="服务器操作")
    operation.pack(padx=5, pady=5, fill="x")
    start_btn = tk.Button(master=operation, text="启动服务器", width=260, height=1)
    start_btn.pack(padx=5, pady=5)
    shutdown_btn = tk.Button(master=operation, text="关闭服务器", width=260, height=1)
    shutdown_btn.pack(padx=5, pady=5)
    kill_task_btn = tk.Button(master=operation, text="结束选中进程", width=260, height=1)
    kill_task_btn.pack(padx=5, pady=5)
    task_manager = tk.LabelFrame(master=server_manager_window, text="端口占用进程管理", width=270, border=1)
    task_manager.pack(padx=5, pady=5, fill="x")
    task_list = tk.Listbox(master=task_manager, width=260, height=6)
    task_list.pack(padx=5, pady=5, fill="x")
    detail_show = tk.LabelFrame(master=task_manager, width=260, border=0)
    detail_show.pack(padx=5, pady=5, fill="x")
    pid = tk.Label(master=detail_show, text="进程ID", width=270, height=1,justify="left", anchor="w")
    pid.pack()
    memory_use = tk.Label(master=detail_show, text="内存占用", width=270, height=1,justify="left",anchor="w") 
    memory_use.pack()
    cpu_use = tk.Label(master=detail_show, text="CPU占用:", width=270, height=1,justify="left",anchor="w")
    cpu_use.pack()
    start_state_roll_check(self=self)
    # Do not call on_exit here — provide a callable for WM_DELETE_WINDOW
    server_manager_window.protocol("WM_DELETE_WINDOW", lambda: on_exit(self.event, server_manager_window))
    server_manager_window.mainloop()

def on_exit(event, root):
    event.set()
    try:
        root.destroy()
    except tk.TclError:
        pass

def dev_or_pro():
    """判断开发环境还是生产环境"""
    if getattr(sys, 'frozen', False):
        return "ReadAlaud.exe" if sys.platform == "win32" else "ReadAlaud"
    else:
        return "python.exe" if sys.platform == "win32" else "python"

def check_if_server_running(port=8008):
    # Fast, reliable check: try connecting to the port first
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError as ose:
        return False
    # Fallback: original process-name based detection
    process_name = dev_or_pro()
    system = platform.system()
    try:
        if system == "Windows":
            result = subprocess.check_output(
                f'netstat -ano | findstr :{port}', shell=True, encoding='utf-8'
            )
            lines = result.strip().split('\n')
            for line in lines:
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f':{port}'):
                    pid = parts[-1]
                    tasklist = subprocess.check_output(
                        f'tasklist /FI "PID eq {pid}"', shell=True, encoding='utf-8'
                    )
                    if process_name.lower() in tasklist.lower():
                        return True
            return False
        else:
            result = subprocess.check_output(
                f'lsof -i :{port}', shell=True, encoding='utf-8'
            )
            for line in result.strip().split('\n'):
                if process_name in line:
                    return True
            return False
    except subprocess.CalledProcessError:
        return 
def roll_check(self, event):
    while not event.is_set():
        if_server_running = check_if_server_running()
        text = "正在运行" if if_server_running else "关闭"
        try:
            label = getattr(self, "state_label", None)
            if label and label.winfo_exists():
                # schedule UI update on the main thread
                label.after(0, lambda t=text, lbl=label: lbl.configure(text=t))
        except tk.TclError:
            # widget already destroyed or Tk broken; just exit loop next iteration
            pass
        event.wait(1)

def start_state_roll_check(self):
    self.event = threading.Event()
    self.check_thread = threading.Thread(target=roll_check, daemon=True, args=(self, self.event))
    self.check_thread.start()

def server_pid(port=8008):
    system = platform.system()
    if system == "Windows":
        # netstat -ano | findstr :8008
        try:
            result = subprocess.check_output(
                f'netstat -ano | findstr :{port}', shell=True, encoding='utf-8'
            )
            for line in result.strip().split('\n'):
                parts = line.split()
                # 本地地址格式可能为 0.0.0.0:8008 或 127.0.0.1:8008
                if len(parts) >= 5 and parts[1].endswith(f':{port}'):
                    pid = parts[-1]
                    return int(pid)
        except Exception:
            return None
    else:
        # lsof -i :8008
        try:
            result = subprocess.check_output(
                f'lsof -i :{port}', shell=True, encoding='utf-8'
            )
            for line in result.strip().split('\n'):
                if 'LISTEN' in line:
                    # lsof 输出格式: COMMAND PID USER ... TCP ... LISTEN
                    m = re.search(r'\b(\d+)\b', line)
                    if m:
                        return int(m.group(1))
        except Exception:
            return None
    return None

def end_server_process(force=False, pid=None):
    """End the server process which is running improperly"""
    system = platform.system()
    if pid is None:
        return "No PID provided"

    try:
        if system == "Windows":
            if not force:
                result = subprocess.check_output(
                    f"taskkill /pid {pid}", shell=True, encoding="utf-8"
                )
            else:
                result = subprocess.check_output(
                    f"taskkill /pid {pid} /F", shell=True, encoding="utf-8"
                )
        else:
            if not force:
                result = subprocess.check_output(
                    f"kill {pid}", shell=True, encoding="utf-8"
                )
            else:
                result = subprocess.check_output(
                    f"kill -9 {pid}", shell=True, encoding="utf-8"
                )
        return "suc"
    except subprocess.CalledProcessError as e:
        if force:
            messagebox.showerror(message="无法终止已经存在的服务器进程！")
        return str(e)
