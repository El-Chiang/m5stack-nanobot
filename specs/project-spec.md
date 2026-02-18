# M5Stack Nanobot — 项目技术规格文档

> 版本: 0.2.0 | 日期: 2026-02-12

---

## 1. 项目概述与目标

**M5Stack Nanobot** 是一个基于 M5Stack Fire v2.7 的便携式 AI 语音助手设备。

### 核心目标

- 连接 nanobot agent 框架，在 M5Stack 屏幕上显示对话内容
- 通过 nanobot gateway 的 HTTP Channel 获得完整 agent 能力（多轮对话、工具调用、会话记忆）
- 支持语音输出（服务端 TTS）— 后续阶段
- 支持语音输入（设备端麦克风录音 → 服务端 STT）— 后续阶段
- 按键触发交互

### 交互流程

```
用户按下按键 → 麦克风录音 → 音频上传至中继服务 → STT 转文字
→ 转发至 Anthropic API → 获取回复 → TTS 生成语音
→ 文字 + 音频返回设备 → 屏幕显示 + 扬声器播放
```

---

## 2. 系统架构

采用 **设备端 + nanobot gateway** 双层架构。M5Stack Fire 不直接调用 LLM API（ESP32 上 TLS 握手内存开销过大），而是通过局域网连接 nanobot gateway 的 HTTP Channel。

nanobot 是一个轻量级 agent 框架（约 4000 行 Python），架构为 Agent Loop + Provider + Tool，支持多轮对话、工具调用、会话记忆、MCP 服务器等完整 agent 能力。通过给 nanobot 新增 HTTP Channel，M5Stack 可以像 Telegram/飞书等聊天客户端一样接入 nanobot gateway。

```
┌─────────────────┐        HTTP        ┌─────────────────────────────────┐       HTTPS       ┌─────────────────┐
│                 │  (局域网, 无 TLS)   │                                 │   (LLM API)       │                 │
│  M5Stack Fire   │ ◄──────────────► │  nanobot gateway                │ ◄──────────────► │  LLM API        │
│  (设备端)        │                    │  (HTTP Channel, port 8080)      │   via LiteLLM     │  (云端)          │
│                 │                    │                                 │                   │                 │
│  - 屏幕显示      │                    │  - HTTP Channel (aiohttp)       │                   │  - LLM 推理      │
│  - 按键输入      │                    │  - AgentLoop (多轮对话)          │                   │                 │
│  - WiFi 通信     │                    │  - 工具调用 / MCP               │                   │                 │
│  - raw socket   │                    │  - 会话记忆 (SessionManager)    │                   │                 │
│    HTTP 客户端   │                    │  - 其他 Channel (Telegram 等)   │                   │                 │
└─────────────────┘                    └─────────────────────────────────┘                   └─────────────────┘
```

### 架构决策理由

| 决策 | 理由 |
|------|------|
| 使用 nanobot gateway 而非独立 FastAPI 中继 | 复用 nanobot 完整 agent 能力（工具、记忆、MCP），无需重复实现 |
| 给 nanobot 新增 HTTP Channel | 最优雅的集成方式，M5Stack 作为一个 channel 接入，与 Telegram 等并列 |
| 设备端使用 raw socket 而非 urequests | MicroPython urequests 与 aiohttp 不兼容（Content-Length 对中文 UTF-8 计算错误），raw socket 完全可控 |
| 不在设备端直连 LLM API | ESP32 TLS 握手需要 ~50KB 额外内存，加上证书校验和 JSON 解析，PSRAM 压力大 |
| 设备与 gateway 间使用 HTTP（非 HTTPS） | 局域网内通信，省去 TLS 开销，降低延迟 |
| 使用 UIFlow 固件而非原生 MicroPython | UIFlow 内置 C 级别硬件驱动（屏幕、LED、IMU），性能远优于纯 Python 驱动 |

---

## 3. 硬件规格 — M5Stack Fire v2.7

### 主控

| 项目 | 规格 |
|------|------|
| SoC | ESP32-D0WDQ6 (双核 Xtensa LX6, 240MHz) |
| Flash | 16MB |
| PSRAM | 8MB |
| USB 转串口 | CP2104 或 CH9102 |

### 屏幕

| 项目 | 规格 |
|------|------|
| 驱动芯片 | ILI9342C |
| 分辨率 | 320 x 240 |
| 接口 | SPI |

### 音频输出

| 项目 | 规格 |
|------|------|
| 功放芯片 | **PAM8303**（模拟功放） |
| 音频通路 | ESP32 内部 DAC → GPIO 25 (DAC1) → PAM8303 → 扬声器 |
| 输出方式 | 模拟 DAC 输出（非 I2S） |

> **注意**: M5Stack Core2 使用 NS4168 I2S 数字功放，但 Fire v2.7 沿用初代 Core 的模拟架构，使用 PAM8303。编码时音频数据需推送到 DAC1/GPIO25。

### 麦克风

| 项目 | 规格 |
|------|------|
| 类型 | 模拟 MEMS 麦克风 |
| ADC 引脚 | GPIO 34 |

### 按键

| 按键 | GPIO | 位置 |
|------|------|------|
| Button A | GPIO 39 | 左 |
| Button B | GPIO 38 | 中 |
| Button C | GPIO 37 | 右 |

### LED

| 项目 | 规格 |
|------|------|
| 型号 | SK6812 RGB LED × 10（Fire 独有） |
| 控制引脚 | GPIO 15 |

### IMU

| 项目 | 规格 |
|------|------|
| 型号 | MPU6886（加速度计 + 陀螺仪） |
| 接口 | I2C |

---

## 4. 开发环境搭建

### 4.1 固件烧录

使用 **M5Burner** 烧录 UIFlow 定制固件（不使用原生 MicroPython）。

**UIFlow 固件优势:**
- 内置 C 级别 ILI9342C 屏幕驱动（`import lcd` 即可使用，帧率极高）
- 内置 SK6812 LED、MPU6886 传感器驱动
- 默认启用 8MB PSRAM 支持
- 内置中文字库
- 完善的文件系统支持

**烧录步骤:**
1. 下载 M5Burner: https://docs.m5stack.com/en/download
2. 在 M5Burner 中选择 **UIFlow_Fire** 固件
3. 连接设备，点击烧录

### 4.2 USB 驱动（macOS）

根据设备上的 USB 转串口芯片型号安装对应驱动:

- **CP2104**: https://www.silabs.com/developers/usb-to-uart-bridge-vcp-drivers
- **CH9102**: https://www.wch.cn/downloads/CH34XSER_MAC_ZIP.html

验证设备连接:
```bash
ls /dev/tty.usbserial-*      # CP2104
ls /dev/tty.wchusbserial*    # CH9102
```

### 4.3 开发工具

```bash
pip install mpremote    # 文件传输 + REPL 交互
```

**mpremote 常用命令:**
```bash
mpremote connect /dev/tty.usbserial-XXXX repl    # 进入 REPL
mpremote connect /dev/tty.usbserial-XXXX cp src/main.py :main.py   # 上传文件
mpremote connect /dev/tty.usbserial-XXXX ls       # 列出设备文件
mpremote connect /dev/tty.usbserial-XXXX run src/main.py  # 运行脚本（不上传）
```

> 注: 使用 M5Burner 烧录固件时不需要单独安装 `esptool`，M5Burner 内部已集成。

---

## 5. 项目目录结构

```
m5stack-nanobot/
├── src/                    # 设备端 MicroPython 代码
│   ├── main.py             # 主程序（自包含，通过 paste mode 注入执行）
│   ├── config.py           # 配置文件（WiFi 密码、gateway 地址）
│   ├── boot.py             # 启动脚本（保留，demo 不经过 boot）
│   └── lib/                # 功能模块（保留供后续模块化使用）
│       ├── nanobot_app.py  # 主交互流程编排
│       ├── chat_ui.py      # 聊天界面绘制
│       ├── spirit_animator.py # spirit 心情动图播放器
│       ├── wifi.py         # WiFi 连接管理
│       ├── relay_client_raw.py # raw socket HTTP 通信
│       ├── app_config.py   # 运行时配置加载
│       └── app_constants.py # UI/动画常量
├── server/                 # 旧版中继服务（已废弃，由 nanobot gateway 替代）
│   ├── main.py             # 旧版 FastAPI 入口（参考用）
│   ├── llm_proxy.py        # 旧版 Anthropic API 转发
│   ├── tts.py              # 文字转语音（后续可集成到 nanobot）
│   ├── stt.py              # 语音转文字（后续可集成到 nanobot）
│   └── requirements.txt    # Python 依赖
├── specs/                  # 项目规格文档
│   ├── project-spec.md     # 本文档
│   └── nanobot-http-channel.md  # nanobot HTTP Channel 设计文档
├── tools/                  # 部署/辅助脚本
│   ├── run_on_device.py    # 通过 paste mode 注入代码到设备
│   ├── upload_config.py    # 通过 REPL 写入 config.py 到设备
│   ├── net_diag.py         # 网络诊断脚本
│   └── deploy.sh           # 一键上传代码到设备
├── CLAUDE.md               # Claude Code 项目指引
├── .gitignore
├── requirements.txt        # 宿主机 Python 依赖（mpremote 等）
├── LICENSE
└── README.md
```

---

## 6. 通信协议设计

### 6.1 M5Stack ↔ nanobot gateway (HTTP Channel)

设备端通过 raw socket 发送 HTTP/1.0 请求到 nanobot gateway 的 HTTP Channel。

#### 文字对话请求

```
POST /api/chat HTTP/1.0
Host: 192.168.31.84:8080
Content-Type: application/json
Content-Length: <byte length of UTF-8 encoded body>

{
  "message": "Hello, tell me a joke",
  "session_id": "optional-session-id"
}
```

```
HTTP 200 OK
Content-Type: application/json

{
  "reply": "Why did the programmer quit? Because he didn't get arrays.",
  "session_id": "ef797bc7-4de4-47a0-ad95-593d0d816ded"
}
```

> **注意**: Content-Length 必须是 body UTF-8 编码后的字节数（非字符数），否则中文等多字节字符会导致 aiohttp 报 `Data after Connection: close` 错误。

#### 健康检查

```
GET /api/health

HTTP 200 OK
{"status": "ok"}
```

### 6.2 nanobot gateway ↔ LLM API

nanobot 通过 LiteLLM 统一调用各 LLM provider（Anthropic、OpenAI、本地模型等），配置在 `~/.nanobot/config.json`。

---

## 7. 各模块接口定义

### 7.1 界面模块 — `src/lib/chat_ui.py`

基于 UIFlow 内置 `lcd` 模块绘制状态栏、聊天区、按键栏。

```python
class ChatUI:
    """聊天界面绘制"""

    def init_screen(self):
        """初始化屏幕"""

    def draw_status(self, text: str, color=TEXT_COLOR):
        """绘制顶部状态栏"""

    def draw_buttons(self):
        """绘制底部按钮提示"""

    def clear_chat(self):
        """清空聊天区"""

    def print_chat(self, text: str, color=BOT_COLOR, prefix: str = ""):
        """写入一条聊天消息（自动换行）"""
```

### 7.2 Spirit 动画模块 — `src/lib/spirit_animator.py`

负责按 mood 行号播放 `spirit/rXX_fYY.jpg` 帧图。

```python
class SpiritAnimator:
    """Spirit 心情动图播放器"""

    def set_mood(self, mood: str, hold_ms: int = 0):
        """切换心情并可选保持一段时间"""

    def update(self):
        """按固定间隔推进动画帧"""

    def render_current(self):
        """渲染当前帧"""
```

### 7.3 WiFi 模块 — `src/lib/wifi.py`

```python
class WiFiManager:
    """WiFi 连接管理"""

    def init(self, ssid: str, password: str):
        """初始化 WiFi 配置"""

    def connect(self) -> bool:
        """连接 WiFi，返回是否成功"""

    def is_connected(self) -> bool:
        """检查连接状态"""

    def get_ip(self) -> str:
        """获取本机 IP 地址"""

    def disconnect(self):
        """断开连接"""
```

### 7.4 Relay 通信模块 — `src/lib/relay_client_raw.py`

```python
class RelayClientRaw:
    """与中继服务通信（raw socket HTTP）"""

    def clear_session(self):
        """清除当前会话 session_id"""

    def send_chat(self, message: str):
        """发送消息到 /api/chat，返回 (reply, mood)"""
```

### 7.5 应用编排模块 — `src/lib/nanobot_app.py`

```python
class NanobotApp:
    def run(self):
        """初始化 UI/Spirit/WiFi 后进入主循环"""
```

### 7.6 按键处理

按键处理集成在 `main.py` 主循环中:

```python
# 按键映射
# Button A (GPIO 39): 发送预设消息 A
# Button B (GPIO 38): 发送预设消息 B
# Button C (GPIO 37): 清空会话并回到 idle
```

---

## 8. 实施阶段划分

### 第一阶段 — 环境搭建与基础验证 ✅

- 安装 M5Burner，烧录 UIFlow_Fire 固件
- 安装 USB 驱动，确认设备可被识别
- 安装 mpremote，验证 REPL 连接
- 编写 `tools/run_on_device.py` 解决 UIFlow 固件下 mpremote run 不可用的问题
- Hello World: WiFi 连接 + 屏幕显示文字

**验收标准:** 设备屏幕显示文字 + WiFi IP 地址 ✅

### 第二阶段 — nanobot 集成 ✅

- 给 nanobot 新增 HTTP Channel（独立 PR，见 `specs/nanobot-http-channel.md`）
- nanobot gateway 启动后监听 HTTP 端口（`0.0.0.0:8080`）
- 设备端通过 raw socket HTTP 客户端连接 gateway
- 按钮 A/B 发送预设消息，屏幕显示 AI 回复
- 按钮 C 清屏 + 重置会话

**验收标准:** 按下按钮，屏幕显示 nanobot agent 回复 ✅

### 第三阶段 — 中文显示与 UI 优化

- 加载中文字库（TTF/BDF），支持中文显示
- 屏幕 UI 美化（对话气泡、滚动）
- LED 状态指示（思考中/就绪）

**验收标准:** 屏幕正确显示中文回复，UI 流畅

### 第四阶段 — 语音输出

- 实现 DAC 音频播放模块
- 集成 TTS 服务到 nanobot（MCP server 或自定义 tool）
- 对话回复后自动播放 TTS 音频

**验收标准:** 按键触发对话后，扬声器播放 AI 回复语音

### 第五阶段 — 语音输入

- 实现麦克风 ADC 录音模块
- 按住 Button A 录音，松开后上传
- 集成 STT 服务到 nanobot
- 完整语音对话流程打通

**验收标准:** 按住按键说话 → 屏幕显示识别文字 + AI 回复 → 扬声器播放回复语音

### 第六阶段 — 体验优化

- 错误处理与断线重连
- 低电量/网络异常提示
- 设备端代码模块化（拆分到 `src/lib/`）
