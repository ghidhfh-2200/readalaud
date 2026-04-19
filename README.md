# ReadAlaud 3.0.0: 告别摸鱼偷懒，回归大声早读！

ReadAlaud 是一个旨在帮助用户建立和保持朗读习惯的跨平台应用程序。它结合了实时语音指导、数据可视化分析和本地服务器扩展功能，为你提供沉浸式的朗读体验。

> 💡 **项目状态**: 项目在积极开发中，欢迎提交 Issue 和 Pull Request！

## 核心亮点 (Features)

*   **沉浸式朗读体验**: 提供实时语音提示 (TTS) 和会话跟踪，确保朗读过程专注且有效。支持自定义音频上传和TTS停止控制。
*   **深度数据分析**: 内置音频分析模块，使用 matplotlib 和 calmap 生成每日活动热力图，支持朗读音频的回放与波形分析。
*   **本地服务器扩展**: 集成 FastAPI 本地服务器，支持状态轮询和 WebSocket 音频流服务，可用于多端联动或远程控制。
*   **多用户管理**: 完善的账户系统，支持本地多用户登录，登录次数限制，敏感操作密码验证，数据隔离存储，保障个人隐私。
*   **个性化定制**: 支持界面主题切换、语音提示设置及朗读目标管理。
*   **详尽日志系统**: 支持多等级日志记录、日期选择筛选、日志删除功能，帮助用户追踪应用运行状态。
*   **麦克风校准**: 集成音量计校准，支持麦克风参数调优。
*   **侧边栏快览**: 实时展示今日朗读数据统计。

## 系统要求 (Requirements)

- **Python**: 3.8 或更高版本
- **操作系统**: Windows / macOS / Linux
- **麦克风**: 用于录音功能
- **网络**: 仅需在使用 Web TTS (edge-tts) 时联网

## 依赖库 (Dependencies)

关键依赖库：
- **edge-tts**: 微软 Web TTS 引擎
- **pyttsx3**: 本地离线 TTS 
- **pywebview**: 用于校准界面
- **FastAPI + uvicorn**: 本地服务器
- **pandas, numpy**: 数据处理
- **matplotlib, calmap**: 数据可视化
- **PyAudio**: 音频输入输出
- **pydub, simpleaudio**: 音频处理

## 安装指南 (Installation)

1.  克隆仓库：
    ```bash
    git clone https://github.com/yourusername/ReadAlaud.git
    ```
2.  进入项目目录：
    ```bash
    cd ReadAlaud
    ``` 
3.  创建虚拟环境（推荐）：
    
    **Windows:**
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
    
    **macOS/Linux:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```

## 使用说明 (Usage)

### 快速开始

1. 启动应用程序：
    ```bash
    python main.py
    ```

2. **首次运行**：
   - 应用会显示启动界面
   - 进入登录界面后选择"注册"创建新账户
   - 成功注册后系统会自动登录

3. **主要功能**：
   - **朗读模式**: 在网页界面输入或粘贴文本，点击开始录音并朗读
   - **数据分析**: 查看每日统计、月度热力图、音量曲线等
   - **TTS 设置**: 选择语音类型（本地/Web）、调节速度和音量
   - **日志查看**: 查看应用运行日志，支持按等级筛选

### 数据存储

- **用户数据**: 保存在 `data/` 目录（按用户分类）
- **音频分析**: 保存在 `details/` 目录
- **账户信息**: `data/acounts.json`
- **个性化设置**: 每个用户的 `settings.json` 和 `tts_config.json`
- **日志数据**: 保存在`data/`目录下的`system_log.db`


## 项目结构 (Project Structure)

```
ReadAlaud/
 main.py                  # 程序入口，包含启动界面
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
    audio_analysis.py     # from .audio import bind_audio_analysis_api, ...
    calibration.py        # from .calibration import bind_calibration_api, start_calibration

    # 认证与账户
    auth/
        __init__.py       # 导出 bind_auth
        account_io.py     # 账户文件读写 (acounts.json)
        session.py        # 登录 / 注册 / 注销 / 登录次数限制

    # 设置相关
    settings/
        __init__.py       # 导出 bind_settings, _load_settings
        settings_io.py    # 通用设置读写 / 主题切换 / 敏感操作验证
        tts_settings.py   # TTS 设置保存与缓存清理

    # 朗读主流程
    reading/
        __init__.py       # 导出 bind_reading_api, reading_data_get_and_check, start_reading
        session.py        # 会话启动 / 网页打开 / 滚动检测
        data_io.py        # 朗读数据 JSON 读写
        wav_merger.py     # WAV 片段合并
        data_thread.py    # 后台数据轮询线程 (IPC/HTTP)
        ui_thread.py      # UI 刷新线程 / 侧边栏数据更新
        tts_trigger.py    # 朗读中 TTS 触发条件判断

    # 音频播放与分析
    audio/
        __init__.py       # 导出 bind_audio_analysis_api 及分析入口
        playback.py       # 日录音播放 / 暂停 / 跳转 / 进度条
        dashboard.py      # 总时长 / 连胜 / 月视图等统计
        daily_detail.py   # 单日音量曲线与对比分析
        chart_builder.py  # 热力图 / 趋势图 / 音量图 构建
        analysis_engine.py# 深度音频分析 (VAD/RMS/LTAS/ZCR/Pitch/SNR/MFCC/...)

    # TTS 模块
    tts/
        __init__.py       # 导出 bind_tts, speak, test_tts, get_web_voices 等
        local_tts.py      # 本地 pyttsx3 合成 (支持离线)
        web_tts.py        # edge-tts 调用与 WAV 缓存播放 (高质量在线)
        voice_list.py     # 语音列表与 Web 声线获取 / 自定义音频上传
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
        local_window.py   # 本地校准窗口支持

    # 图形界面
    gui/
        __init__.py       # 绑定所有 GUI 入口到 ReadAlaud 实例
        gui_service.py    # GUI 服务接口
        main_window.py    # 主窗口 / 欢迎页
        login_gui.py      # 登录 / 注册界面 (带登录次数限制)
        reading_gui.py    # 朗读界面与进度显示
        data_gui.py       # 数据面板与音频分析界面
        settings_gui.py   # 设置界面 / 主题切换
        tts_gui.py        # TTS 调节与测试界面 / 自定义音频管理

    # 日志系统
    logger/
        __init__.py       # 导出 bind_logger_api, init_db
        log_manager.py    # 日志数据库初始化与记录
        log_viewer.py     # 日志查看 UI (支持日期筛选、等级过滤、删除操作)
```

## 最近更新 (Recent Updates)

### v3.0.0 新增功能（2026年4月）

- ✨ **TTS 自定义音频支持**: 支持用户上传自定义音频，扩展语音选择
- 🔧 **校准功能更新**: 改进了麦克风校准界面与参数设置
- 📊 **侧边栏数据展示**: 实时显示今日朗读统计数据
- 🛡️ **登录次数限制**: 增强安全性，支持敏感操作密码验证
- 📝 **日志系统升级**: 
  - 支持多等级日志（DEBUG/INFO/WARNING/ERROR）
  - 添加日期筛选功能
  - 支持日志删除操作
- 🔊 **朗读体验改进**: 朗读结束后自动停止正在播放的 TTS
- ⏱️ **时长计算修复**: 修复剩余时长计算错误（Fix #27）
- 🚀 **启动画面**: 新增启动图标显示，优化用户体验

## 常见问题 (FAQ)

### Q1: 如何备份和恢复我的数据？
A: 所有数据保存在 `data/` 和 `details/` 目录下，直接备份这两个文件夹即可恢复。

### Q2: 支持哪些语言？
A: 
- **本地 TTS (pyttsx3)**: 取决于系统安装的语音包（通常支持英文、中文等）
- **Web TTS (edge-tts)**: 支持 100+ 种语言和声线

### Q3: 能否在多台设备间同步数据？
A: 目前不支持云同步，但可以通过本地服务器接口进行数据同步。建议后续版本添加此功能。

### Q4: 如何解决 PyAudio 安装失败？
A: 
- **Windows**: 下载对应 Python 版本的 `.whl` 文件，使用 `pip install` 安装
- **macOS**: 使用 `brew install portaudio && pip install PyAudio`
- **Linux**: 使用系统包管理器安装 `portaudio` 开发库

### Q5: 忘记密码怎么办？
A: 直接编辑 `data/acounts.json` 文件删除相应账户，重新注册即可。

## 贡献指南 (Contributing)

欢迎提交 Issue 或 Pull Request 来改进 ReadAlaud！

### 开发流程

1.  Fork 本仓库
2.  创建特性分支:
    ```bash
    git checkout -b feature/your-feature
    ```
3.  提交你的更改:
    ```bash
    git commit -m "feat: 简要描述你的功能"
    ```
4.  推送到分支:
    ```bash
    git push origin feature/your-feature
    ```
5.  开启 Pull Request

### 代码规范

- 遵循 PEP 8 风格指南
- 添加适当的注释和文档字符串
- 确保代码可以正常运行

### 报告 Bug

如遇到问题，请：
1. 检查是否已有相关 Issue
2. 提供详细的错误信息和复现步骤
3. 附上你的系统信息和 Python 版本

## 开发者指南 (Developer Guide)

### 本地开发

```bash
# 克隆仓库
git clone https://github.com/yourusername/ReadAlaud.git
cd ReadAlaud

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # 或 Windows: venv\Scripts\activate

# 安装开发依赖
pip install -r requirements.txt

# 运行程序
python main.py
```

### 模块说明

- **core.py**: 核心类，管理所有模块的生命周期
- **auth/**: 账户认证和会话管理
- **reading/**: 朗读录音主流程
- **audio/**: 音频分析和可视化
- **tts/**: 文本到语音转换
- **server/**: FastAPI 服务器
- **gui/**: Tkinter GUI 界面

## 许可证 (License)

本项目基于 MIT 许可证开源。详情请参阅 [LICENSE](LICENSE) 文件。

## 鸣谢 (Acknowledgments)

感谢以下开源项目和社区的支持：
- [edge-tts](https://github.com/rany2/edge-tts): 微软 Edge TTS 引擎
- [pyttsx3](https://github.com/nateshmbhat/pyttsx3): 跨平台离线 TTS
- [FastAPI](https://github.com/tiangolo/fastapi): 现代 Web 框架
- [Tkinter](https://docs.python.org/3/library/tkinter.html): Python GUI 工具包
- [matplotlib](https://matplotlib.org/): 数据可视化
- 所有为项目提出建议和贡献代码的开发者

## 联系方式 (Contact)

- **项目主页**: https://github.com/yourusername/ReadAlaud
- **Issue Tracker**: https://github.com/yourusername/ReadAlaud/issues
- **讨论区**: https://github.com/yourusername/ReadAlaud/discussions

## 路线图 (Roadmap)

### 计划中的功能 (Planned Features)

- [ ] 更加现代的界面
- [ ] 自动化控制与开机自启动
- [ ] 多实例集成控制
- [ ] 备份与传输
- [ ] 群组与排名功能
- [ ] 性能优化（有可能彻底放弃Python作为开发语言）
