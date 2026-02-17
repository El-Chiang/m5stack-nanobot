# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

M5Stack Nanobot：基于 M5Stack Fire v2.7 (ESP32) 的便携式 AI 语音助手。设备通过局域网 HTTP 连接本地中继服务，中继服务转发请求到 Anthropic API 并处理 STT/TTS。设备不直接调用 Anthropic API（ESP32 上 TLS 内存开销过大）。

详细技术规格见 `specs/project-spec.md`。

## 架构

双层系统：

- **`src/`** — 设备端固件（UIFlow 定制 MicroPython）。运行在 M5Stack 上，负责屏幕显示、音频 I/O、按键、WiFi 和与中继服务的 HTTP 通信。
- **`server/`** — 中继服务（Python FastAPI）。运行在 PC/服务器上，转发 Anthropic API 请求，运行 STT（语音转文字）和 TTS（文字转语音）。

通信链路：`M5Stack --[HTTP, 局域网]--> 中继服务 --[HTTPS]--> Anthropic API`

## 硬件注意事项

- **功放芯片是 PAM8303（模拟），不是 NS4168（I2S）**。音频输出走 ESP32 内部 DAC GPIO 25，不要使用 I2S 接口。
- **固件是 UIFlow 定制 MicroPython，不是原生 MicroPython**。使用 UIFlow 内置 C 模块如 `import lcd`、`import imu`，不要手写 SPI 驱动。
- 屏幕：ILI9342C 320x240 (SPI)。按键：A=GPIO39, B=GPIO38, C=GPIO37。麦克风：ADC GPIO34。LED：SK6812 x10 GPIO15。

## 开发命令

### 设备端 (M5Stack Fire)

串口：`/dev/tty.usbserial-5B090280621`

**UIFlow 固件 REPL 注意事项：**
- 设备需处于 **USB Mode**（开机时侧面按钮进 Setup 切换），否则串口被 UIFlow 后台进程 (m5ucloud) 占据。
- `mpremote run` 会触发 soft-reset 导致 UIFlow 重新接管串口，**不能直接用**。
- 使用 `tools/run_on_device.py` 替代 mpremote run，它通过 paste mode (Ctrl+E) 注入代码绕过此问题。
- `mpremote cp`（文件上传）在 USB Mode 下通常可用，但有时仍会报 `could not enter raw repl`；优先用 `./tools/deploy.sh`（已内置 REPL preflight/重试）或先 `Ctrl+C` 抢回 `>>>` 再上传。

```bash
# 运行脚本到设备（推荐，兼容 UIFlow 固件）
python tools/run_on_device.py src/hardware_test.py

# 上传单个文件到设备
mpremote connect /dev/tty.usbserial-5B090280621 cp src/main.py :main.py

# 上传整个 lib 目录
mpremote connect /dev/tty.usbserial-5B090280621 cp -r src/lib/ :lib/

# 列出设备文件
mpremote connect /dev/tty.usbserial-5B090280621 ls

# 一键部署所有代码
./tools/deploy.sh
```

### 中继服务

```bash
cd server
pip install -r requirements.txt
python main.py
```

## 已知坑点

### 串口 / REPL

1. **UIFlow 模式下串口输出乱码** — 如果串口收到 `\xaa\xab\xaa\xff\xffcrc error` 之类的二进制帧，说明设备处于 Internet Mode，UIFlow 后台进程 (m5ucloud) 在用私有协议通信。**解决：** 在设备上切换到 USB Mode（开机长按侧面按钮 → Setup → USB Mode → 重启）。
2. **`mpremote run` 不可用** — mpremote 的 `run` 和 `soft-reset` 命令会触发 MicroPython 软重启，UIFlow 的 boot 流程随即接管串口，导致 `could not enter raw repl` 错误。**解决：** 用 `python tools/run_on_device.py <script>` 替代，它先 Ctrl+C 中断后台进程，再通过 paste mode (Ctrl+E) 注入代码。
3. **切换 USB Mode 后需物理重启** — 仅在菜单里切换模式不够，必须让设备完整重启（按复位键或断电重连），否则 m5ucloud 进程仍在运行。
4. **`mpremote cp` 偶发 `could not enter raw repl`** — 即使看到 UIFlow 启动画面（`BOARD NAME: M5STACK-FIRE`），`mpremote` 仍可能拿不到 raw REPL。**解决：** 先多次发送 Ctrl+C 抢回 `>>>`（或直接使用 `./tools/deploy.sh` 的 REPL preflight），再重试上传；若仍失败，确认 USB Mode + 物理重启 + 关闭串口监视器。
5. **`mpremote cp` 可能报 `Operation not permitted`** — 在当前 UIFlow 固件上，即使串口可用，`mpremote cp` 也可能系统性失败。**解决：** 使用 `./tools/deploy.sh`（已在 `mpremote` 失败后自动回退到 `tools/upload_via_repl.py`，通过 paste mode 上传文件）。

### 模块导入

6. **`import rgb` 不存在** — 网上一些 M5Stack 示例使用 `import rgb` 控制 LED 灯条，但该模块在当前 UIFlow 固件中不存在。**正确方式：** 使用标准 `neopixel` 模块：
   ```python
   from neopixel import NeoPixel
   import machine
   np = NeoPixel(machine.Pin(15), 10)
   np.fill((255, 0, 0))
   np.write()
   ```
7. **UIFlow 模块通过 `from m5stack import *` 加载** — 这会注入 `lcd`、`speaker`、`btnA`/`btnB`/`btnC` 等全局对象，不需要单独 import。不要尝试 `import lcd` 会报错。

### 脚本执行

- **`run_on_device.py` 连续执行脚本时可能复用旧模块缓存** — 在同一 REPL 会话里重复运行脚本，`import config` 可能读到旧值（例如 `RELAY_SERVER` 仍是旧配置）。**解决：** 依赖配置的测试脚本里先清理缓存再导入：
  ```python
  import sys
  if "config" in sys.modules:
      del sys.modules["config"]
  config = __import__("config")
  ```
  或者在更新配置后按 `RST` 重启设备再测试。

## 关键约束

- 设备端 MicroPython 内存有限，JSON 载荷尽量小，音频分块传输。
- 设备到中继使用 HTTP（无 TLS，局域网内），中继到 Anthropic 使用 HTTPS。
- 设备与中继间音频格式：16kHz、8-bit unsigned、单声道 PCM。
- UIFlow 固件通过 M5Burner 烧录（非 esptool），当前设备已完成烧录。
