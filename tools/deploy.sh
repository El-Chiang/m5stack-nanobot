#!/usr/bin/env bash
# 一键上传设备端代码到 M5Stack
# 用法: ./tools/deploy.sh [串口设备路径]

set -e

SERIAL="${1:-/dev/tty.usbserial-5B090280621}"
SRC_DIR="src"
SPIRIT_FRAMES_DIR="assets/spirits/frames"
USE_MPREMOTE=1

show_serial_hint() {
    cat <<'EOF'
Deploy failed while accessing serial port.

Likely causes on M5Stack UIFlow firmware:
1) Device is in Internet Mode (m5ucloud occupies serial with binary protocol)
2) USB Mode was switched but device was not physically rebooted
3) Serial port is busy by another process

Fix:
- On device: Power on + side button -> Setup -> USB Mode
- Physically reboot device (RST button or replug USB)
- Close UIFlow/M5Burner serial monitor if open
- Retry: ./tools/deploy.sh
EOF
}

trap 'show_serial_hint' ERR

ensure_uiflow_repl() {
    python - "$SERIAL" <<'PY'
import sys
import time

try:
    import serial
except Exception:
    print("pyserial is required for REPL preflight: pip install pyserial")
    raise SystemExit(2)

port = sys.argv[1]
s = serial.Serial(port, 115200, timeout=0.8)
try:
    def read_until(wait_s):
        end = time.time() + wait_s
        seen = b""
        while time.time() < end:
            chunk = s.read(s.in_waiting or 1024)
            if chunk:
                seen += chunk
            time.sleep(0.05)
        return seen

    def is_normal_prompt(buf):
        return b">>>" in buf

    def is_raw_prompt(buf):
        if b"raw REPL; CTRL-B to exit" in buf:
            return True
        return buf.rstrip().endswith(b">")

    def enter_normal_from_raw():
        s.write(b"\x02")  # Ctrl+B
        buf = read_until(1.2)
        if is_normal_prompt(buf):
            return True
        s.write(b"\r\n")
        buf = read_until(1.2)
        return is_normal_prompt(buf)

    s.write(b"\r\n")
    buf = read_until(1.2)
    if is_normal_prompt(buf):
        print("REPL preflight: already at prompt")
        raise SystemExit(0)
    if is_raw_prompt(buf):
        if enter_normal_from_raw():
            print("REPL preflight: raw -> normal prompt")
            raise SystemExit(0)

    # UIFlow m5ucloud 进程占串口时，多次 Ctrl+C 打断
    for _ in range(14):
        s.write(b"\x03")
        time.sleep(0.2)

    s.write(b"\r\n")
    buf = read_until(2.5)
    if is_normal_prompt(buf):
        print("REPL preflight: prompt acquired")
        raise SystemExit(0)
    if is_raw_prompt(buf):
        if enter_normal_from_raw():
            print("REPL preflight: raw -> normal prompt")
            raise SystemExit(0)

    print("REPL preflight: prompt not found")
    raise SystemExit(1)
finally:
    s.close()
PY
}

cp_to_device() {
    local src="$1"
    local dst="$2"       # mpremote path, e.g. :main.py
    local dst_plain="${dst#:}"  # for upload_via_repl.py

    if [ "$USE_MPREMOTE" = "1" ]; then
        if mpremote connect "$SERIAL" cp "$src" "$dst"; then
            return 0
        fi

        echo "mpremote cp failed, switching to fallback uploader for remaining files."
        USE_MPREMOTE=0
    fi

    echo "fallback uploader: $src -> $dst_plain"
    python tools/upload_via_repl.py --port "$SERIAL" "$src" "$dst_plain"
}

if [ ! -e "$SERIAL" ]; then
    echo "Serial device not found: $SERIAL"
    echo "Check current port with: ls /dev/tty.usbserial-* /dev/tty.wchusbserial*"
    exit 1
fi

echo "Deploying to $SERIAL ..."
if ! ensure_uiflow_repl; then
    echo "REPL preflight warning: continue and let mpremote try."
fi

# 生成动图帧（若尚未生成）
if [ ! -d "$SPIRIT_FRAMES_DIR" ] || [ -z "$(ls -A "$SPIRIT_FRAMES_DIR" 2>/dev/null)" ]; then
    echo "Spirit frames not found, generating from sprite..."
    python tools/prepare_spirits.py || {
        echo "  spirit frame generation skipped (check Pillow install)."
    }
fi

# 上传 config
cp_to_device "$SRC_DIR/config.py" :config.py
echo "  config.py uploaded"

# 上传 lib 目录
for f in "$SRC_DIR"/lib/*.py; do
    name=$(basename "$f")
    cp_to_device "$f" ":lib/$name"
    echo "  lib/$name uploaded"
done

# 上传 boot.py 和 main.py
cp_to_device "$SRC_DIR/boot.py" :boot.py
echo "  boot.py uploaded"
cp_to_device "$SRC_DIR/main.py" :main.py
echo "  main.py uploaded"

# 上传 spirit 动图帧
if [ -d "$SPIRIT_FRAMES_DIR" ] && [ -n "$(ls -A "$SPIRIT_FRAMES_DIR" 2>/dev/null)" ]; then
    for f in "$SPIRIT_FRAMES_DIR"/*.jpg; do
        name=$(basename "$f")
        cp_to_device "$f" ":spirit/$name"
    done
    echo "  spirit/*.jpg uploaded"
else
    echo "  spirit frames missing, skipped upload"
fi

echo "Deploy complete. Reset device to run."
