"""
process_manager.py —— 检查、查询 PID、终止服务器进程的工具函数。
"""
import sys
import subprocess
import platform
import socket
import re
from tkinter import messagebox


def bind_server_manager_api(instance):
    instance.start_manager = lambda: _start_manager_window(instance)
    instance.check_if_server_running = lambda: check_if_server_running()


# ── 公共工具 ──────────────────────────────────────────────

def dev_or_pro():
    if getattr(sys, "frozen", False):
        return "ReadAlaud.exe" if sys.platform == "win32" else "ReadAlaud"
    else:
        return "python.exe" if sys.platform == "win32" else "python"


def check_if_server_running(port=8008):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=0.5):
            return True
    except OSError:
        return False


def server_pid(port=8008):
    system = platform.system()
    if system == "Windows":
        try:
            result = subprocess.check_output(
                f"netstat -ano | findstr :{port}", shell=True, encoding="utf-8"
            )
            for line in result.strip().split("\n"):
                parts = line.split()
                if len(parts) >= 5 and parts[1].endswith(f":{port}"):
                    return int(parts[-1])
        except Exception:
            return None
    else:
        try:
            result = subprocess.check_output(
                f"lsof -i :{port}", shell=True, encoding="utf-8"
            )
            for line in result.strip().split("\n"):
                if "LISTEN" in line:
                    m = re.search(r"\b(\d+)\b", line)
                    if m:
                        return int(m.group(1))
        except Exception:
            return None
    return None


def end_server_process(force=False, pid=None):
    if pid is None:
        return "No PID provided"
    system = platform.system()
    flag = "/F" if force else ""
    try:
        if system == "Windows":
            cmd = f"taskkill /pid {pid} {flag}".strip()
        else:
            cmd = f"kill {'-9 ' if force else ''}{pid}".strip()
        subprocess.check_output(cmd, shell=True, encoding="utf-8")
        return "suc"
    except subprocess.CalledProcessError as e:
        if force:
            messagebox.showerror(message="无法终止已经存在的服务器进程！")
        return str(e)


# ── 内部导入（避免循环） ──────────────────────────────────

def _start_manager_window(self):
    from .manager_window import start_manager
    start_manager(self)
