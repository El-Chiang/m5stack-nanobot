"""屏幕显示封装 — 基于 UIFlow 内置 lcd 模块"""

import lcd

# 屏幕尺寸
SCREEN_W = 320
SCREEN_H = 240

# 布局
STATUS_BAR_H = 20
CHAT_Y_START = STATUS_BAR_H + 4
LINE_HEIGHT = 18
CHARS_PER_LINE = 26  # 中文约 13 个，英文约 26 个

# 颜色
COLOR_BG = lcd.BLACK
COLOR_STATUS_BG = 0x1A1A2E
COLOR_USER = lcd.CYAN
COLOR_ASSISTANT = lcd.GREEN
COLOR_STATUS = lcd.YELLOW
COLOR_TEXT = lcd.WHITE


class Display:

    def __init__(self):
        lcd.clear(COLOR_BG)
        lcd.setColor(COLOR_TEXT, COLOR_BG)
        self._chat_y = CHAT_Y_START

    def show_text(self, text, x=0, y=0, color=COLOR_TEXT):
        lcd.setColor(color, COLOR_BG)
        lcd.print(text, x, y)

    def show_message(self, role, text):
        """显示对话消息，自动换行和滚动"""
        if role == "user":
            prefix = "> "
            color = COLOR_USER
        else:
            prefix = "< "
            color = COLOR_ASSISTANT

        # 简单自动换行
        lines = self._wrap_text(prefix + text)
        for line in lines:
            if self._chat_y + LINE_HEIGHT > SCREEN_H:
                self._scroll()
            lcd.setColor(color, COLOR_BG)
            lcd.print(line, 4, self._chat_y)
            self._chat_y += LINE_HEIGHT

        self._chat_y += 4  # 消息间距

    def show_status(self, status):
        """状态栏（顶部）"""
        lcd.fillRect(0, 0, SCREEN_W, STATUS_BAR_H, COLOR_STATUS_BG)
        lcd.setColor(COLOR_STATUS, COLOR_STATUS_BG)
        lcd.print(status, 4, 2)

    def clear(self):
        lcd.clear(COLOR_BG)
        self._chat_y = CHAT_Y_START

    def _wrap_text(self, text):
        """按字符数简单换行"""
        lines = []
        while len(text) > CHARS_PER_LINE:
            lines.append(text[:CHARS_PER_LINE])
            text = text[CHARS_PER_LINE:]
        if text:
            lines.append(text)
        return lines

    def _scroll(self):
        """清除聊天区域并重置游标（简单实现）"""
        lcd.fillRect(0, CHAT_Y_START, SCREEN_W, SCREEN_H - CHAT_Y_START, COLOR_BG)
        self._chat_y = CHAT_Y_START
