"""Nanobot 主交互流程。"""

from m5stack import *
import time

from lib.app_config import load_runtime_config
from lib.app_constants import (
    BOT_COLOR,
    ERR_COLOR,
    HINT_COLOR,
    PROMPT_A,
    PROMPT_B,
    USER_COLOR,
)
from lib.chat_ui import ChatUI
from lib.relay_client_raw import RelayClientRaw
from lib.spirit_animator import SpiritAnimator
from lib.wifi import WiFiManager


class NanobotApp:

    def __init__(self):
        wifi_ssid, wifi_password, relay_server = load_runtime_config()
        self._wifi = WiFiManager(wifi_ssid, wifi_password)
        self._relay = RelayClientRaw(relay_server)
        self._ui = ChatUI()
        self._spirit = None

    def run(self):
        self._ui.init_screen()
        self._spirit = SpiritAnimator()
        self._spirit.set_mood("idle")

        if not self._connect_wifi():
            self._ui.print_chat("WiFi connection failed!", ERR_COLOR)
            self._ui.print_chat("Check config.py", HINT_COLOR)
            return

        self._ui.print_chat("Ready! Press A or B.", HINT_COLOR)
        self._ui.draw_status("Ready")

        while True:
            self._spirit.update()

            if btnA.wasPressed():
                self._handle_chat(PROMPT_A, "happy")
            elif btnB.wasPressed():
                self._handle_chat(PROMPT_B, "excited")
            elif btnC.wasPressed():
                self._relay.clear_session()
                self._ui.clear_chat()
                self._ui.print_chat("Session cleared.", HINT_COLOR)
                self._ui.draw_status("Ready")
                self._spirit.set_mood("idle")

            time.sleep_ms(50)

    def _connect_wifi(self):
        self._ui.draw_status("WiFi connecting...")
        self._spirit.set_mood("working")

        if self._wifi.connect(timeout_s=10):
            self._ui.draw_status("WiFi: " + self._wifi.get_ip())
            self._spirit.set_mood("idle")
            return True

        self._ui.draw_status("WiFi FAILED", ERR_COLOR)
        self._spirit.set_mood("dragging", 2500)
        return False

    def _handle_chat(self, user_message, fallback_mood):
        self._ui.print_chat(user_message, USER_COLOR, "> ")
        self._ui.draw_status("Thinking...")
        self._spirit.set_mood("working")

        try:
            reply, mood = self._relay.send_chat(user_message)
        except Exception as exc:
            self._ui.draw_status("Error: " + str(exc)[:30], ERR_COLOR)
            self._ui.print_chat("Request failed", ERR_COLOR)
            self._spirit.set_mood("angry", 1800)
            return

        self._ui.print_chat(reply, BOT_COLOR)
        self._ui.draw_status("Ready")
        if mood:
            self._spirit.set_mood(mood, 2000)
        else:
            self._spirit.set_mood(fallback_mood, 1600)
