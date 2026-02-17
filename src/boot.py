"""boot.py — 设备启动时自动执行，负责 WiFi 连接和基础初始化"""

from m5stack import *
from lib.wifi import WiFiManager
import config

lcd.clear()
lcd.setColor(lcd.WHITE, lcd.BLACK)
lcd.print("Nanobot starting...", 0, 0)

wifi = WiFiManager(config.WIFI_SSID, config.WIFI_PASSWORD)
if wifi.connect():
    lcd.print("WiFi: " + wifi.get_ip(), 0, 20)
else:
    lcd.print("WiFi FAILED", 0, 20)
