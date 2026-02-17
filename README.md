# M5Stack Nanobot

基于 M5Stack Fire v2.7（UIFlow MicroPython）的便携式 AI 助手。  
设备通过局域网 HTTP 访问中继服务（`server/`），并在屏幕显示对话与心情动图。

## 1. 环境准备

```bash
pip install -r requirements.txt
pip install pyserial pillow
```

- `pyserial`：`tools/run_on_device.py`、`tools/upload_via_repl.py`、`tools/deploy.sh` 依赖。
- `pillow`：首次生成心情帧图 `assets/spirits/frames/*.jpg` 依赖。

## 2. 设备准备（很重要）

1. 设备切到 `USB Mode`：开机按侧边按钮 -> `Setup` -> `USB Mode`
2. 切换后必须物理重启：按 `RST` 或重新插拔 USB
3. 关闭 UIFlow/M5Burner 的串口监视器

默认串口：`/dev/tty.usbserial-5B090280621`

## 3. 配置 WiFi 与中继地址

编辑 `src/config.py`：

```python
WIFI_SSID = "你的WiFi"
WIFI_PASSWORD = "你的密码"
RELAY_SERVER = "http://你的中继IP:8080"
```

## 4. 一键部署（推荐）

```bash
./tools/deploy.sh
```

`deploy.sh` 当前行为：
- 先做 UIFlow REPL preflight（尝试抢回 `>>>`）
- 尝试 `mpremote cp`
- 若 `mpremote` 失败（如 `could not enter raw repl` / `Operation not permitted`），自动回退到 `tools/upload_via_repl.py`
- 自动上传 `src/` 代码与 `assets/spirits/frames/*.jpg`

部署完成后重启设备运行。

## 5. 常用操作

只更新配置：

```bash
python tools/upload_via_repl.py --port /dev/tty.usbserial-5B090280621 src/config.py config.py
```

运行一个脚本到设备（不落盘）：

```bash
python tools/run_on_device.py src/hardcore_test.py
```

网络诊断：

```bash
python tools/run_on_device.py tools/net_diag.py
```

## 6. 心情动图说明

动图素材源：`assets/空洞骑士/sprite.jpg`  
切帧产物：`assets/spirits/frames/rXX_fYY.jpg`

手动重新生成帧图：

```bash
python tools/prepare_spirits.py
```

状态映射：
- `idle` -> Row 1
- `happy`, `love` -> Row 2
- `excited`, `celebrate` -> Row 3
- `sleepy`, `snoring` -> Row 4
- `working` -> Row 5
- `angry`, `surprised`, `shy` -> Row 6
- `dragging` -> Row 7

## 7. 中继服务启动

```bash
cd server
pip install -r requirements.txt
python main.py
```

## 8. 常见报错

`could not enter raw repl`：
- 通常是 UIFlow 后台进程占串口或状态不稳
- 先确认 `USB Mode + 物理重启`
- 直接重试 `./tools/deploy.sh`（已内置回退）

`\xaa\xab...crc error` 二进制输出：
- 设备还在 Internet Mode 私有协议
- 切换到 USB Mode 并重启
