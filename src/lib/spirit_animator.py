"""Spirit 心情动图播放器。"""

from m5stack import *
import time

from lib.app_constants import (
    ANIM_H,
    ANIM_LABEL_Y,
    ANIM_W,
    ANIM_X,
    ANIM_Y,
    BG_COLOR,
    CHAT_X,
    ERR_COLOR,
    HINT_COLOR,
    MOOD_ALIASES,
    MOOD_ROWS,
    SCREEN_H,
    SPIRIT_COLUMNS,
    SPIRIT_DIR,
    SPIRIT_INTERVAL_MS,
    STATUS_BG,
    STATUS_H,
    BUTTON_H,
)


class SpiritAnimator:

    def __init__(self):
        self.state = "idle"
        self._row = MOOD_ROWS["idle"]
        self._frame_idx = 0
        self._available = True
        self._hold_until = None
        self._next_ms = time.ticks_add(time.ticks_ms(), SPIRIT_INTERVAL_MS)
        self.draw_panel()
        self.render_current()

    def draw_panel(self):
        lcd.fillRect(0, STATUS_H, CHAT_X - 2, SCREEN_H - STATUS_H - BUTTON_H, BG_COLOR)
        lcd.fillRect(CHAT_X - 2, STATUS_H, 2, SCREEN_H - STATUS_H - BUTTON_H, STATUS_BG)
        self.draw_label()

    def draw_label(self):
        lcd.fillRect(4, ANIM_LABEL_Y, CHAT_X - 8, 16, BG_COLOR)
        lcd.font(lcd.FONT_Default)
        lcd.setTextColor(HINT_COLOR, BG_COLOR)
        lcd.print("Mood: " + self.state, 6, ANIM_LABEL_Y)

    def set_mood(self, mood, hold_ms=0):
        if not isinstance(mood, str):
            mood = "idle"
        canonical = MOOD_ALIASES.get(mood.lower().strip(), "idle")
        self.state = canonical
        self._row = MOOD_ROWS[canonical]
        self._frame_idx = 0
        if hold_ms and hold_ms > 0:
            self._hold_until = time.ticks_add(time.ticks_ms(), hold_ms)
        else:
            self._hold_until = None
        self.draw_label()
        self.render_current()

    def update(self):
        now = time.ticks_ms()
        if self._hold_until is not None and time.ticks_diff(self._hold_until, now) <= 0:
            self._hold_until = None
            if self.state != "idle":
                self.set_mood("idle")
                return

        if time.ticks_diff(now, self._next_ms) < 0:
            return

        self._next_ms = time.ticks_add(now, SPIRIT_INTERVAL_MS)
        self._frame_idx += 1
        if self._frame_idx >= SPIRIT_COLUMNS:
            self._frame_idx = 0
        self.render_current()

    def render_current(self):
        if not self._available:
            return

        path = "%s/r%02d_f%02d.jpg" % (SPIRIT_DIR, self._row, self._frame_idx)
        try:
            lcd.image(ANIM_X, ANIM_Y, path)
        except Exception:
            self._available = False
            lcd.fillRect(ANIM_X, ANIM_Y, ANIM_W, ANIM_H, STATUS_BG)
            lcd.font(lcd.FONT_Default)
            lcd.setTextColor(ERR_COLOR, STATUS_BG)
            lcd.print("spirit missing", ANIM_X + 8, ANIM_Y + 48)
            print("Spirit frame load failed:", path)
