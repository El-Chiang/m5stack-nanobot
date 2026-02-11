"""M5Stack Nanobot 交互界面

自包含脚本 — 通过 tools/run_on_device.py 注入执行。
按钮 A: 发送 "你好，介绍一下你自己"
按钮 B: 发送 "给我讲个笑话"
按钮 C: 清屏 + 重置会话
"""

from m5stack import *
import network
import ujson
import time
import machine

# ---------------------------------------------------------------------------
# 配置 (从 config.py 读取或内联)
# ---------------------------------------------------------------------------
try:
    from config import WIFI_SSID, WIFI_PASSWORD, RELAY_SERVER
except ImportError:
    WIFI_SSID = "YOUR_WIFI_SSID"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    RELAY_SERVER = "http://192.168.1.100:8080"

# ---------------------------------------------------------------------------
# 屏幕常量
# ---------------------------------------------------------------------------
SCREEN_W = 320
SCREEN_H = 240
STATUS_H = 20       # 顶部状态栏高度
BUTTON_H = 20       # 底部按钮提示高度
CHAT_Y = STATUS_H + 2
CHAT_H = SCREEN_H - STATUS_H - BUTTON_H - 4
CHAT_X = 4
CHAT_W = SCREEN_W - 8
LINE_H = 16         # 每行文本高度
FONT_W = 8          # 字符宽度 (FONT_Default)
MAX_CHARS = CHAT_W // FONT_W  # 每行最多字符数

# 颜色
BG_COLOR = 0x000000
STATUS_BG = 0x333333
TEXT_COLOR = 0xFFFFFF
USER_COLOR = 0x00FF00
BOT_COLOR = 0x00BFFF
HINT_COLOR = 0x999999
ERR_COLOR = 0xFF4444

# ---------------------------------------------------------------------------
# 状态
# ---------------------------------------------------------------------------
session_id = None
chat_y_cursor = CHAT_Y  # 当前聊天区域 y 坐标


def draw_status(text, color=TEXT_COLOR):
    """绘制顶部状态栏"""
    lcd.fillRect(0, 0, SCREEN_W, STATUS_H, STATUS_BG)
    lcd.font(lcd.FONT_Default)
    lcd.setTextColor(color, STATUS_BG)
    lcd.print(text, 4, 3)


def draw_buttons():
    """绘制底部按钮提示"""
    y = SCREEN_H - BUTTON_H
    lcd.fillRect(0, y, SCREEN_W, BUTTON_H, STATUS_BG)
    lcd.font(lcd.FONT_Default)
    lcd.setTextColor(HINT_COLOR, STATUS_BG)
    # 三个按钮均分
    lcd.print("[A] Hello", 10, y + 3)
    lcd.print("[B] Joke", 120, y + 3)
    lcd.print("[C] Clear", 230, y + 3)


def clear_chat():
    """清除聊天区域"""
    global chat_y_cursor
    lcd.fillRect(0, CHAT_Y, SCREEN_W, CHAT_H, BG_COLOR)
    chat_y_cursor = CHAT_Y


def wrap_text(text):
    """将文本按屏幕宽度换行，返回行列表"""
    lines = []
    for raw_line in text.split('\n'):
        if not raw_line:
            lines.append('')
            continue
        while len(raw_line) > MAX_CHARS:
            lines.append(raw_line[:MAX_CHARS])
            raw_line = raw_line[MAX_CHARS:]
        lines.append(raw_line)
    return lines


def print_chat(text, color=TEXT_COLOR, prefix=""):
    """在聊天区域打印文本，自动换行，超出时重置"""
    global chat_y_cursor

    if prefix:
        text = prefix + text

    lines = wrap_text(text)

    for line in lines:
        # 检查是否超出聊天区域
        if chat_y_cursor + LINE_H > CHAT_Y + CHAT_H:
            clear_chat()

        lcd.font(lcd.FONT_Default)
        lcd.setTextColor(color, BG_COLOR)
        lcd.print(line, CHAT_X, chat_y_cursor)
        chat_y_cursor += LINE_H


# ---------------------------------------------------------------------------
# WiFi
# ---------------------------------------------------------------------------
def connect_wifi():
    """连接 WiFi，返回 True/False"""
    draw_status("WiFi connecting...")
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        draw_status("WiFi: " + ip)
        return True

    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    for i in range(20):
        if wlan.isconnected():
            break
        time.sleep(0.5)

    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        draw_status("WiFi: " + ip)
        return True
    else:
        draw_status("WiFi FAILED", ERR_COLOR)
        return False


# ---------------------------------------------------------------------------
# HTTP 客户端 (raw socket — urequests 与 aiohttp 不兼容)
# ---------------------------------------------------------------------------
def http_post(host, port, path, body):
    """用 raw socket 发送 HTTP POST，返回响应 body 字符串"""
    import socket
    addr = socket.getaddrinfo(host, port)[0][-1]
    s = socket.socket()
    s.connect(addr)

    body_bytes = body.encode("utf-8")
    header = (
        "POST %s HTTP/1.0\r\n"
        "Host: %s:%d\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "\r\n"
    ) % (path, host, port, len(body_bytes))
    s.send(header.encode("utf-8"))
    s.send(body_bytes)

    # 读取完整响应
    chunks = []
    while True:
        chunk = s.recv(1024)
        if not chunk:
            break
        chunks.append(chunk)
    s.close()

    raw = b"".join(chunks).decode()
    # 分离 header 和 body
    idx = raw.find("\r\n\r\n")
    if idx >= 0:
        return raw[idx + 4:]
    return raw


def _parse_relay():
    """从 RELAY_SERVER 解析 host, port"""
    # "http://192.168.31.84:8080" -> ("192.168.31.84", 8080)
    url = RELAY_SERVER.replace("http://", "")
    if ":" in url:
        h, p = url.split(":", 1)
        return h, int(p.split("/")[0])
    return url.split("/")[0], 80


def send_chat(message):
    """发送消息到中继服务，返回 (reply, session_id) 或 (None, None)"""
    global session_id

    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id

    try:
        draw_status("Thinking...")
        host, port = _parse_relay()
        resp_body = http_post(host, port, "/api/chat", ujson.dumps(payload))
        data = ujson.loads(resp_body)

        reply = data.get("reply", "")
        sid = data.get("session_id", session_id)
        return reply, sid

    except Exception as e:
        draw_status("Error: " + str(e)[:30], ERR_COLOR)
        return None, None


# ---------------------------------------------------------------------------
# 主逻辑
# ---------------------------------------------------------------------------
def main():
    global session_id

    # 初始化屏幕
    lcd.clear(BG_COLOR)
    lcd.setBrightness(60)
    draw_status("Nanobot Starting...")
    draw_buttons()
    clear_chat()

    # 连接 WiFi
    if not connect_wifi():
        print_chat("WiFi connection failed!", ERR_COLOR)
        print_chat("Check config.py", HINT_COLOR)
        return

    print_chat("Ready! Press A or B.", HINT_COLOR)
    draw_status("Ready")

    # 主循环
    while True:
        if btnA.wasPressed():
            msg = "Hello, introduce yourself briefly. Reply in English only."
            print_chat(msg, USER_COLOR, "> ")
            reply, sid = send_chat(msg)
            if reply is not None:
                session_id = sid
                print_chat(reply, BOT_COLOR)
                draw_status("Ready")
            else:
                print_chat("Request failed", ERR_COLOR)

        elif btnB.wasPressed():
            msg = "Tell me a short joke. Reply in English only."
            print_chat(msg, USER_COLOR, "> ")
            reply, sid = send_chat(msg)
            if reply is not None:
                session_id = sid
                print_chat(reply, BOT_COLOR)
                draw_status("Ready")
            else:
                print_chat("Request failed", ERR_COLOR)

        elif btnC.wasPressed():
            session_id = None
            clear_chat()
            print_chat("Session cleared.", HINT_COLOR)
            draw_status("Ready")

        time.sleep_ms(50)


main()
