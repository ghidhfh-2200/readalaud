# ReadAlaud 3.0.0: 告别摸鱼偷懒，回归大声早读！

ReadAlaud 是一个旨在帮助用户建立和保持朗读习惯的跨平台应用程序。它结合了实时语音指导、数据可视化分析和本地服务器扩展功能，为你提供沉浸式的朗读体验。

## 本项目目前还非常不完善，欢迎各位大佬同学们提出批评指正

## 核心亮点 (Features)

*   **沉浸式朗读体验**: 提供实时语音提示 (TTS) 和会话跟踪，确保朗读过程专注且有效。
*   **深度数据分析**: 内置音频分析模块，使用 matplotlib 和 calmap 生成每日活动热力图，支持朗读音频的回放与波形分析。
*   **本地服务器扩展**: 集成 FastAPI 本地服务器，支持状态轮询和 Web 接口扩展，可用于多端联动或远程控制。
*   **多用户管理**: 完善的账户系统，支持本地多用户登录，数据隔离存储，保障个人隐私。
*   **个性化定制**: 支持界面主题切换、语音提示设置及朗读目标管理。

## 安装指南 (Installation)

1.  克隆仓库：
    ```bash
    git clone https://github.com/yourusername/ReadAlaud.git
    ```
2.  进入项目目录：
    `bash
    cd ReadAlaud
    ` 
3.  安装依赖：
    建议使用虚拟环境（venv）：
    `bash
    # Windows
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
    # macOS/Linux
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

## 使用说明 (Usage)

运行以下命令启动应用程序：
```bash
python main.py
``` 
*注意：初次运行请先注册账户，所有数据将保存在本地 data/ 和 details/目录下。*

## 项目结构 (Project Structure)
```
ReadAlaud/
 main.py                  # 程序入口
 requirements.txt         # 依赖列表
 LICENSE                  # MIT 许可证
 README.md                # 项目文档
 readalaud/               # 核心包
    __init__.py
    core.py              # 核心逻辑类
    auth.py              # 用户认证与数据管理
    reading.py           # 朗读会话逻辑
    audio_analasy.py     # 音频分析与可视化
    server.py            # FastAPI 本地服务器
    server_manager.py    # 服务器管理 GUI
    tts.py               # 语音合成模块
    settings.py          # 设置管理
    calibration.py       # 麦克风校准
    gui/                 # 图形界面模块
        __init__.py
        main_window.py   # 主窗口
        login_gui.py     # 登录界面
        reading_gui.py   # 朗读界面
        data_gui.py      # 数据展示界面
        settings_gui.py  # 设置界面
```

## 贡献 (Contributing)

欢迎提交 Issue 或 Pull Request 来改进 ReadAlaud！

1.  Fork 本仓库。
2.  创建一个新分支:
    `bash
    git checkout -b feature/AmazingFeature
    ` 
3.  提交你的更改:
    `bash
    git commit -m "'Add some AmazingFeature"'
    ` 
4.  推送到分支:
    `bash
    git push origin feature/AmazingFeature
    ` 
5.  开启一个 Pull Request。

## 许可证 (License)

本项目基于 MIT 许可证开源。详情请参阅 [LICENSE](LICENSE) 文件。

