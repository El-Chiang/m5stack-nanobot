#!/usr/bin/env bash
# 一键上传设备端代码到 M5Stack
# 用法: ./tools/deploy.sh [串口设备路径]

set -e

SERIAL="${1:-/dev/tty.usbserial-5B090280621}"
SRC_DIR="src"

echo "Deploying to $SERIAL ..."

# 上传 config
mpremote connect "$SERIAL" cp "$SRC_DIR/config.py" :config.py
echo "  config.py uploaded"

# 上传 lib 目录
mpremote connect "$SERIAL" mkdir :lib 2>/dev/null || true
for f in "$SRC_DIR"/lib/*.py; do
    name=$(basename "$f")
    mpremote connect "$SERIAL" cp "$f" ":lib/$name"
    echo "  lib/$name uploaded"
done

# 上传 boot.py 和 main.py
mpremote connect "$SERIAL" cp "$SRC_DIR/boot.py" :boot.py
echo "  boot.py uploaded"
mpremote connect "$SERIAL" cp "$SRC_DIR/main.py" :main.py
echo "  main.py uploaded"

echo "Deploy complete. Reset device to run."
