from m5stack import *
import network
import time

lcd.clear(0x000000)
lcd.font(lcd.FONT_Default)
lcd.setTextColor(0xFFFFFF, 0x000000)

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
    # try connect
    try:
        from config import WIFI_SSID, WIFI_PASSWORD, RELAY_SERVER
    except:
        WIFI_SSID = "1002"
        WIFI_PASSWORD = "10000002"
        RELAY_SERVER = "http://192.168.31.84:8080"
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

# 2. Try HTTP request
try:
    from config import RELAY_SERVER
except:
    RELAY_SERVER = "http://192.168.31.84:8080"

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
