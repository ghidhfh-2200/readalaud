"""
readalaud package

说明：
 - 模块划分：
   - core.py: ReadAlaud 主类的基础属性与公共方法。
   - gui.py: 所有 GUI 相关方法（窗口创建、回调、子窗口）。
   - auth.py: 账号登录/注册/注销等函数。
   - settings.py: 读取/保存用户设置、界面上的设置加载/保存逻辑。
  - tts.py: 与语音合成、列出音色相关的函数（pyttsx3 封装）。

如何使用：
 - 保持根目录下的 `ReadAlaud_OOP.py` 为最小启动器（它会从这里导入 ReadAlaud 并启动 GUI）。
 - 如果想调试某个模块，可以直接在该模块中导入并运行其函数（例如从 `readalaud.gui import generate_main_window`）。

本文件会导出 ReadAlaud 类。
"""
from .core import ReadAlaud

__all__ = ["ReadAlaud"]
