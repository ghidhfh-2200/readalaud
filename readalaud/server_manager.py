import tkinter as tk
import sys
import subprocess
import platform
import socket
import threading
import re
import os
from tkinter import messagebox

def bind_server_manager_api(instance):
    instance.start_manager = lambda:start_manager(instance)
    instance.check_if_server_running = lambda:check_if_server_running()

def start_server_op():
    if check_if_server_running():
        messagebox.showinfo("提示", "服务器已经在运行中")
        return
    try:
        # Use sys.executable to run same python interpreter
        # Execute from current working directory which should be project root
        cmd = [sys.executable, "-c", "from readalaud.server import start_socket_server; start_socket_server()"]
        
        # Detach process so it continues running if manager closes
        if platform.system() == "Windows":
            creationflags = subprocess.CREATE_NO_WINDOW
        else:
            creationflags = 0
            
        subprocess.Popen(cmd, cwd=os.getcwd(), creationflags=creationflags)
        messagebox.showinfo("提示", "已发送启动指令，请稍候...")
    except Exception as e:
        messagebox.showerror("错误", f"无法启动: {e}")

def shutdown_server_op():
    pid = server_pid()
    if pid:
        res = end_server_process(pid=pid, force=True)
        if res == "suc":
            messagebox.showinfo("提示", "服务器已关闭")
        else:
             messagebox.showerror("错误", f"关闭失败: {res}")
    else:
        messagebox.showinfo("提示", "服务器未运行")

def kill_selected_task_op(listbox):
    selection = listbox.curselection()
    if not selection:
        messagebox.showinfo("提示", "请选择一个进程")
        return
    item = listbox.get(selection[0])
    # Extract PID. Format "PID: {pid} (Port 8008)"
    match = re.search(r'PID:\s*(\d+)', item)
    if match:
        pid = int(match.group(1))
        res = end_server_process(force=True, pid=pid)
        if res == "suc":
            messagebox.showinfo("成功", f"进程 {pid} 已结束")
            # Refresh list? It will refresh automatically via roll_check
        else:
             messagebox.showerror("失败", f"无法结束进程: {res}")

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
    start_btn = tk.Button(master=operation, text="启动服务器", width=260, height=1, command=start_server_op)
    start_btn.pack(padx=5, pady=5)
    shutdown_btn = tk.Button(master=operation, text="关闭服务器", width=260, height=1, command=shutdown_server_op)
    shutdown_btn.pack(padx=5, pady=5)
    kill_task_btn = tk.Button(master=operation, text="结束选中进程", width=260, height=1, command=lambda: kill_selected_task_op(task_list))
    kill_task_btn.pack(padx=5, pady=5)
    task_manager = tk.LabelFrame(master=server_manager_window, text="端口占用进程管理", width=270, border=1)
    task_manager.pack(padx=5, pady=5, fill="x")
    task_list = tk.Listbox(master=task_manager, width=260, height=6)
    task_list.pack(padx=5, pady=5, fill="x")
    detail_show = tk.LabelFrame(master=task_manager, width=260, border=0)
    detail_show.pack(padx=5, pady=5, fill="x")
    pid_lbl = tk.Label(master=detail_show, text="进程ID", width=270, height=1,justify="left", anchor="w")
    pid_lbl.pack()
    
    # Pass widgets to roll check loop context if possible, or bind them to self
    if self:
        self.task_list = task_list
        self.pid_lbl = pid_lbl
    
    start_state_roll_check(self=self, task_list=task_list, pid_lbl=pid_lbl)
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
def roll_check(self, event, task_list=None, pid_lbl=None):
    while not event.is_set():
        if_server_running = check_if_server_running()
        server_text = "正在运行" if if_server_running else "关闭"
        
        current_pid = server_pid()
        list_items = []
        if current_pid:
            list_items.append(f"PID: {current_pid} (Port 8008)")

        try:
            # Run UI updates on main thread
            def update_ui(s_text=server_text, items=list_items, c_pid=current_pid):
                # Update status label
                label = getattr(self, "state_label", None)
                if label and label.winfo_exists():
                    label.configure(text=s_text)
                
                # Update task list
                if task_list and task_list.winfo_exists():
                    current_items = task_list.get(0, tk.END)
                    if list(current_items) != items:
                        task_list.delete(0, tk.END)
                        for i in items:
                            task_list.insert(tk.END, i)
                
                # Update PID label
                if pid_lbl and pid_lbl.winfo_exists():
                    pid_text = f"进程ID: {c_pid}" if c_pid else "进程ID: -"
                    if pid_lbl.cget("text") != pid_text:
                        pid_lbl.configure(text=pid_text)

            label_widget = getattr(self, "state_label", None)
            if label_widget and label_widget.winfo_exists():
                label_widget.after(0, update_ui)
                
        except tk.TclError:
            pass
        
        event.wait(1)

def start_state_roll_check(self, task_list=None, pid_lbl=None):
    self.event = threading.Event()
    self.check_thread = threading.Thread(target=roll_check, daemon=True, args=(self, self.event, task_list, pid_lbl))
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
