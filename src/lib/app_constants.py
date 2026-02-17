"""Nanobot UI 与交互常量。"""

# 屏幕尺寸
SCREEN_W = 320
SCREEN_H = 240
STATUS_H = 20
BUTTON_H = 20

# 左侧动图区
ANIM_X = 6
ANIM_Y = STATUS_H + 6
ANIM_W = 120
ANIM_H = 120
ANIM_LABEL_Y = ANIM_Y + ANIM_H + 6

# 右侧聊天区
CHAT_X = 132
CHAT_Y = STATUS_H + 4
CHAT_W = SCREEN_W - CHAT_X - 4
CHAT_H = SCREEN_H - STATUS_H - BUTTON_H - 6
LINE_H = 16
FONT_W = 8
MAX_CHARS = CHAT_W // FONT_W

# 颜色
BG_COLOR = 0x000000
STATUS_BG = 0x333333
TEXT_COLOR = 0xFFFFFF
USER_COLOR = 0x00FF00
BOT_COLOR = 0x00BFFF
HINT_COLOR = 0x999999
ERR_COLOR = 0xFF4444

# Spirit 动图
SPIRIT_DIR = "spirit"
SPIRIT_COLUMNS = 8
SPIRIT_INTERVAL_MS = 150

# 用户定义状态映射
MOOD_ALIASES = {
    "idle": "idle",
    "happy": "happy",
    "love": "happy",
    "excited": "excited",
    "celebrate": "excited",
    "sleepy": "sleepy",
    "snoring": "sleepy",
    "working": "working",
    "angry": "angry",
    "surprised": "angry",
    "shy": "angry",
    "dragging": "dragging",
}

MOOD_ROWS = {
    "idle": 1,
    "happy": 2,
    "excited": 3,
    "sleepy": 4,
    "working": 5,
    "angry": 6,
    "dragging": 7,
}

# 固定提示语
PROMPT_A = "Hello, introduce yourself briefly. Reply in English only."
PROMPT_B = "Tell me a short joke. Reply in English only."
