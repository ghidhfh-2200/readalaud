import argparse
import threading
import traceback
from pathlib import Path

import tkinter as tk
from readalaud.logger.log_manager import init_db, log_system, log_fatal


PROJECT_ROOT = Path(__file__).resolve().parent
ICON_PATH = PROJECT_ROOT / "assets" / "icon.ico"

def show_splash_and_start():
    init_db()
    log_system("启动程序", "show_splash_and_start")
    splash = tk.Tk()
    splash.overrideredirect(True)
    splash.title("正在启动...")
    splash.configure(bg="white")
    splash.attributes("-topmost", True)
    
    # 窗口大小和居中
    width = 300
    height = 300
    screen_width = splash.winfo_screenwidth()
    screen_height = splash.winfo_screenheight()
    x = (screen_width // 2) - (width // 2)
    y = (screen_height // 2) - (height // 2)
    splash.geometry(f"{width}x{height}+{x}+{y}")

    icon_image = None
    
    # 尝试加载图标文件作为背景展示
    try:
        from PIL import Image, ImageTk
        if ICON_PATH.exists():
            img = Image.open(ICON_PATH).convert("RGBA")
            target_size = int(min(width, height) * 0.72)
            img.thumbnail((target_size, target_size), Image.LANCZOS)
            icon_image = ImageTk.PhotoImage(img)
            label = tk.Label(splash, image=icon_image, bg="white")
            label.image = icon_image  # 防止被垃圾回收
            TextLabel = tk.Label(splash, text="告别摸鱼偷懒\n回归大声早读", fg="black", bg="white", font=("宋体", 14))
            TextLabel.pack()
        else:
            raise FileNotFoundError(f"找不到启动图标：{ICON_PATH}")
        label.pack(fill="both", expand=True)
    except Exception as e:
        log_system("加载启动图标失败", str(e))
        # 如果加载失败则显示文本
        label = tk.Label(
            splash,
            text="ReadAlaud 正在启动...\n请稍候",
            font=("微软雅黑", 14),
            bg="white",
        )
        label.pack(pady=100)

    # 刷新窗口强制渲染
    splash.update_idletasks()
    splash.lift()
    splash.update()

    def finish_start(app):
        try:
            splash.attributes("-topmost", False)
        except Exception:
            pass
        splash.destroy()
        app.generate_main_window()

    def init_app():
        try:
            from readalaud.core import ReadAlaud

            app = ReadAlaud()
        except Exception:
            log_fatal("初始化核心失败", traceback.format_exc())
            traceback.print_exc()
            splash.after(0, splash.destroy)
            return

        splash.after(0, lambda: finish_start(app))

    threading.Thread(target=init_app, daemon=True).start()
    splash.mainloop()

def main():
    init_db()
    log_system("调用 main", "program entry")
    parser = argparse.ArgumentParser(description="ReadAlaud 启动程序")
    parser.add_argument("--no-icon", action="store_true", help="启动时不显示应用启动图标")
    args = parser.parse_args()

    if args.no_icon:
        log_system("无启动图标模式", "--no-icon")
        from readalaud.core import ReadAlaud

        r = ReadAlaud()
        r.generate_main_window()
    else:
        show_splash_and_start()

if __name__ == '__main__':
    main()