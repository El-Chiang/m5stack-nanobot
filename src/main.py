"""M5Stack Nanobot 入口。"""

import sys

# 在同一 REPL 会话反复 run_on_device 时，清掉可能残留的失败模块缓存
for _mod in (
    "lib.nanobot_app",
    "lib.chat_ui",
    "lib.spirit_animator",
):
    if _mod in sys.modules:
        del sys.modules[_mod]

_nanobot_mod = __import__("lib.nanobot_app", None, None, ("NanobotApp",), 0)
NanobotApp = _nanobot_mod.NanobotApp


def main():
    app = NanobotApp()
    app.run()


main()
