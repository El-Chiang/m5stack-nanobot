"""聊天界面绘制。"""

from m5stack import *

from lib.app_constants import (
    BG_COLOR,
    BOT_COLOR,
    BUTTON_H,
    CHAT_H,
    CHAT_W,
    CHAT_X,
    CHAT_Y,
    HINT_COLOR,
    LINE_H,
    MAX_CHARS,
    SCREEN_H,
    SCREEN_W,
    STATUS_BG,
    STATUS_H,
    TEXT_COLOR,
)


class ChatUI:

    def __init__(self):
        self._chat_y_cursor = CHAT_Y

    def init_screen(self):
        lcd.clear(BG_COLOR)
        lcd.setBrightness(60)
        self.draw_status("Nanobot Starting...")
        self.draw_buttons()
        self.clear_chat()

    def draw_status(self, text, color=TEXT_COLOR):
        lcd.fillRect(0, 0, SCREEN_W, STATUS_H, STATUS_BG)
        lcd.font(lcd.FONT_Default)
        lcd.setTextColor(color, STATUS_BG)
        lcd.print(text, 4, 3)

    def draw_buttons(self):
        y = SCREEN_H - BUTTON_H
        lcd.fillRect(0, y, SCREEN_W, BUTTON_H, STATUS_BG)
        lcd.font(lcd.FONT_Default)
        lcd.setTextColor(HINT_COLOR, STATUS_BG)
        lcd.print("[A] Hello", 10, y + 3)
        lcd.print("[B] Joke", 120, y + 3)
        lcd.print("[C] Clear", 230, y + 3)

    def clear_chat(self):
        lcd.fillRect(CHAT_X, CHAT_Y, CHAT_W, CHAT_H, BG_COLOR)
        self._chat_y_cursor = CHAT_Y

    def print_chat(self, text, color=BOT_COLOR, prefix=""):
        if prefix:
            text = prefix + text

        lines = self._wrap_text(text)
        for line in lines:
            if self._chat_y_cursor + LINE_H > CHAT_Y + CHAT_H:
                self.clear_chat()

            lcd.font(lcd.FONT_Default)
            lcd.setTextColor(color, BG_COLOR)
            lcd.print(line, CHAT_X, self._chat_y_cursor)
            self._chat_y_cursor += LINE_H

    def _wrap_text(self, text):
        lines = []
        for raw_line in text.split("\n"):
            if not raw_line:
                lines.append("")
                continue
            while len(raw_line) > MAX_CHARS:
                lines.append(raw_line[:MAX_CHARS])
                raw_line = raw_line[MAX_CHARS:]
            lines.append(raw_line)
        return lines
