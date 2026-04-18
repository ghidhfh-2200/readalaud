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
    ```bash
    cd ReadAlaud
    ``` 
3.  安装依赖：
    建议使用虚拟环境（venv）
    # Windows
    ```bash
    python -m venv venv
    venv\\Scripts\\activate
    pip install -r requirements.txt
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
 web/                     # 网页前端相关文件 (朗读页面 / 校准页面)
 readalaud/               # 核心 Python 包
    __init__.py
    core.py               # 核心 ReadAlaud 类与模块绑定入口

    # 旧入口 shim（保持向后兼容）
    auth.py               # from .auth import bind_auth
    settings.py           # from .settings import bind_settings, _load_settings
    tts.py                # from .tts import bind_tts, speak, ...
    reading.py            # from .reading import bind_reading_api, ...
    server.py             # from .server import bind_server_api, ...
    server_manager.py     # from .server import bind_server_manager_api, ...
    audio_analasy.py      # from .audio import bind_audio_analasy_api, ...
    calibration.py        # from .calibration import bind_calibration_api, start_calibration

    # 认证与账户
    auth/
        __init__.py       # 导出 bind_auth
        account_io.py     # 账户文件读写 (acounts.json)
        session.py        # 登录 / 注册 / 注销 逻辑

    # 设置相关
    settings/
        __init__.py       # 导出 bind_settings, _load_settings
        settings_io.py    # 通用设置读写 / 主题切换
        tts_settings.py   # TTS 设置保存与缓存清理

    # 朗读主流程
    reading/
        __init__.py       # 导出 bind_reading_api, reading_data_get_and_check, start_reading
        session.py        # 会话启动 / 网页打开 / 滚动检测
        data_io.py        # 朗读数据 JSON 读写
        wav_merger.py     # WAV 片段合并
        data_thread.py    # 后台数据轮询线程 (IPC/HTTP)
        ui_thread.py      # UI 刷新线程
        tts_trigger.py    # 朗读中 TTS 触发条件判断

    # 音频播放与分析
    audio/
        __init__.py       # 导出 bind_audio_analasy_api 及分析入口
        playback.py       # 日录音播放 / 暂停 / 跳转 / 进度条
        dashboard.py      # 总时长 / 连胜 / 月视图等统计
        daily_detail.py   # 单日音量曲线与对比
        chart_builder.py  # 热力图 / 趋势图 / 音量图 构建
        analysis_engine.py# 深度音频分析 (VAD/RMS/LTAS/ZCR/Pitch/SNR/MFCC/...)

    # TTS 模块
    tts/
        __init__.py       # 导出 bind_tts, speak, test_tts, get_web_voices 等
        local_tts.py      # 本地 pyttsx3 合成
        web_tts.py        # edge-tts 调用与 WAV 缓存播放
        voice_list.py     # 语音列表与 Web 声线获取
        playback_control.py # 全局播放控制与停止信号管理

    # 本地服务器与进程管理
    server/
        __init__.py       # 导出 bind_server_api, bind_server_manager_api 等
        socket_server.py  # FastAPI + WebSocket 音频流服务器
        process_manager.py# 检测 / 启停服务器进程
        manager_window.py # 服务器管理 Tk 窗口

    # 麦克风校准
    calibration/
        __init__.py       # 导出 bind_calibration_api, start_calibration
        calibration_api.py# JS ↔ Python 桥接 (保存校准参数)
        webview_process.py# 启动 pywebview 校准窗口 (子进程)

    # 图形界面
    gui/
        __init__.py       # 绑定所有 GUI 入口到 ReadAlaud 实例
        main_window.py    # 主窗口 / 欢迎页
        login_gui.py      # 登录 / 注册界面
        reading_gui.py    # 朗读界面
        data_gui.py       # 数据面板与音频分析界面
        settings_gui.py   # 设置界面
        tts_gui.py        # TTS 调节与测试界面
```

## 贡献 (Contributing)

欢迎提交 Issue 或 Pull Request 来改进 ReadAlaud！

1.  Fork 本仓库。
2.  创建一个新分支:
    ```bash
    git checkout -b feature/AmazingFeature
    ```
3.  提交你的更改:
    ```bash
    git commit -m "'Add some AmazingFeature"'
    ```
4.  推送到分支:
    ```bash
    git push origin feature/AmazingFeature
    ```
5.  开启一个 Pull Request。

## 许可证 (License)

本项目基于 MIT 许可证开源。详情请参阅 [LICENSE](LICENSE) 文件。

