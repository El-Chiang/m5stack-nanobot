#!/usr/bin/env python3
"""通过 pyserial paste mode 向 UIFlow 设备发送并执行脚本

UIFlow 固件启动后会运行 m5ucloud 后台进程占据串口。
- 若设备处于 Internet Mode：先 Ctrl+C 中断后台进程，再进入 paste mode
- 若设备处于 USB Mode：重启后直接进入 REPL，无需中断

本工具自动检测两种情况，通过 paste mode (Ctrl+E) 注入代码执行。

用法: python tools/run_on_device.py src/hardware_test.py [串口]
"""

import sys
import time
import serial

DEFAULT_PORT = "/dev/tty.usbserial-5B090280621"
BAUD = 115200


def drain(s):
    """读取并丢弃串口缓冲区"""
    time.sleep(0.1)
    s.read(s.in_waiting or 4096)


def ensure_repl(s):
    """确保设备处于 REPL 状态，返回 True 如果成功"""
    # 先检查是否已在 REPL
    s.write(b"\r\n")
    time.sleep(0.5)
    buf = s.read(s.in_waiting or 4096)
    if b">>>" in buf:
        return True

    # 尝试 Ctrl+C 中断后台进程
    print("Interrupting background process...")
    for _ in range(8):
        s.write(b"\x03")
        time.sleep(0.2)
    time.sleep(1)
    s.read(s.in_waiting or 4096)

    s.write(b"\r\n")
    time.sleep(0.5)
    buf = s.read(s.in_waiting or 4096)
    return b">>>" in buf


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <script.py> [serial_port]")
        sys.exit(1)

    script_path = sys.argv[1]
    port = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PORT

    with open(script_path, "r") as f:
        code = f.read()

    s = serial.Serial(port, BAUD, timeout=2)
    print(f"Connected to {port}")

    # 1. 确保进入 REPL
    if not ensure_repl(s):
        print("ERROR: Could not enter REPL. Try resetting the device.")
        s.close()
        sys.exit(1)
    print("REPL ready")

    # 2. 进入 paste mode (Ctrl+E)
    s.write(b"\x05")
    time.sleep(0.3)
    buf = s.read(s.in_waiting or 4096)
    if b"paste mode" not in buf:
        print(f"WARNING: unexpected paste mode response: {buf[:80]}")

    # 3. 逐行发送代码
    lines = code.split("\n")
    print(f"Sending {len(lines)} lines...")
    for line in lines:
        s.write((line + "\r\n").encode())
        time.sleep(0.01)

    # 4. Ctrl+D 执行
    time.sleep(0.2)
    s.write(b"\x04")
    print("Executing on device...")

    # 5. 跳过 paste mode 回显，读取实际输出
    # paste mode 会回显所有代码行，然后输出执行结果
    print("--- Device Output ---")
    try:
        while True:
            data = s.read(s.in_waiting or 1)
            if data:
                text = data.decode("utf-8", "replace")
                # 过滤掉 paste mode 回显行 (以 "=== " 开头)
                for line in text.split("\n"):
                    stripped = line.strip()
                    if stripped and not stripped.startswith("==="):
                        sys.stdout.write(line + "\n")
                sys.stdout.flush()
            else:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\n--- Stopped (Ctrl+C) ---")

    s.close()


if __name__ == "__main__":
    main()
