from m5stack import *
import network
import time
import sys

lcd.clear(0x000000)
lcd.font(lcd.FONT_Default)
lcd.setTextColor(0xFFFFFF, 0x000000)

try:
    # run_on_device 在同一 REPL 会话里执行脚本，需避免复用旧 config 缓存
    if "config" in sys.modules:
        del sys.modules["config"]
    config = __import__("config")
    WIFI_SSID = config.WIFI_SSID
    WIFI_PASSWORD = config.WIFI_PASSWORD
    RELAY_SERVER = config.RELAY_SERVER
except Exception:
    WIFI_SSID = "YOUR_WIFI_SSID"
    WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
    RELAY_SERVER = "http://192.168.x.x:8080"

# 1. Check WiFi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
if wlan.isconnected():
    ip = wlan.ifconfig()[0]
    lcd.print("WiFi OK: " + ip, 4, 4)
    print("WiFi OK: " + ip)
else:
    lcd.print("WiFi NOT connected", 4, 4)
    print("WiFi NOT connected")
    # try connect with config.py settings
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)
    for i in range(20):
        if wlan.isconnected():
            break
        time.sleep(0.5)
    if wlan.isconnected():
        ip = wlan.ifconfig()[0]
        lcd.print("WiFi connected: " + ip, 4, 20)
        print("WiFi connected: " + ip)
    else:
        lcd.print("WiFi FAILED", 4, 20)
        print("WiFi FAILED")

lcd.print("Testing: " + RELAY_SERVER, 4, 40)
print("Testing: " + RELAY_SERVER)

try:
    import urequests
    resp = urequests.get(RELAY_SERVER + "/api/health")
    lcd.print("Health: " + str(resp.status_code), 4, 60)
    print("Health status: " + str(resp.status_code))
    print("Body: " + resp.text)
    lcd.print(resp.text[:38], 4, 80)
    resp.close()
except Exception as e:
    err = str(e)
    lcd.print("HTTP ERROR:", 4, 60)
    lcd.print(err[:38], 4, 80)
    print("HTTP ERROR: " + err)
