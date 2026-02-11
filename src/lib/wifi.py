"""WiFi 连接管理"""

import network
import time


class WiFiManager:

    def __init__(self, ssid, password):
        self._ssid = ssid
        self._password = password
        self._wlan = network.WLAN(network.STA_IF)

    def connect(self, timeout_s=15):
        """连接 WiFi，返回是否成功"""
        self._wlan.active(True)
        if self._wlan.isconnected():
            return True

        self._wlan.connect(self._ssid, self._password)

        start = time.time()
        while not self._wlan.isconnected():
            if time.time() - start > timeout_s:
                return False
            time.sleep(0.5)
        return True

    def is_connected(self):
        return self._wlan.isconnected()

    def get_ip(self):
        if self._wlan.isconnected():
            return self._wlan.ifconfig()[0]
        return ""

    def disconnect(self):
        self._wlan.disconnect()
        self._wlan.active(False)
