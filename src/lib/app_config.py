"""运行时配置加载。"""


def load_runtime_config():
    """从 config.py 读取配置，读取失败则返回默认值。"""
    try:
        from config import WIFI_SSID, WIFI_PASSWORD, RELAY_SERVER
        return WIFI_SSID, WIFI_PASSWORD, RELAY_SERVER
    except ImportError:
        return (
            "YOUR_WIFI_SSID",
            "YOUR_WIFI_PASSWORD",
            "http://192.168.1.100:8080",
        )
